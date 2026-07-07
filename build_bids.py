"""
Step 3: Build BIDS directory structure with de-identified EDF files.

Reads the linking table, then for each patient:
  - Creates sub-Neurotech{N}/ses-{M}/eeg/ directories
  - Copies EDF files with de-identified headers (using edfio lazy loading)
  - Generates _eeg.json, _channels.tsv, _Xltek.csv, _scans.tsv sidecars
  - Generates dataset-level files (dataset_description.json, participants.tsv, etc.)
"""

import os
import re
import json
import csv
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta

import functools
import pandas as pd
from edfio import read_edf, EdfSignal

print = functools.partial(print, flush=True)

_REPO = Path(__file__).resolve().parent
DRIVE_PATH = Path(os.environ.get("NT_DRIVE_PATH", "/Volumes/Padlock_DT"))
OUTPUT_DIR = Path(os.environ.get("NT_OUTPUT_DIR", str(_REPO / "output")))
BIDS_ROOT = Path(os.environ.get("NT_BIDS_ROOT", str(_REPO / "bids_output/Neurotech")))
# Which linking table to convert (default the A-H one; batch-2 overrides via env).
LINKING_PATH = Path(os.environ.get("NT_LINKING_TABLE", str(OUTPUT_DIR / "linking_table.csv")))
DASHBOARD_DIR = Path(os.environ.get("NT_DASHBOARD_DIR", str(_REPO / "dashboard")))
S3_BUCKET = "bdsp-opendata-repository"
S3_PREFIX = "EEG/bids/Neurotech"

# Set via environment or defaults
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

TASK_LABEL = "EEG"
UPLOAD_TO_S3 = os.environ.get("NT_UPLOAD_TO_S3", "1") == "1"  # Set NT_UPLOAD_TO_S3=0 to only build locally
DELETE_AFTER_UPLOAD = os.environ.get("NT_DELETE_AFTER_UPLOAD", "1") == "1"  # delete local after upload
# Skip writing/uploading dataset-level files (participants.tsv etc). Use for
# incremental batch runs so we don't overwrite the published metadata with a
# partial list — regenerate a complete one separately at the end.
WRITE_DATASET_FILES = os.environ.get("NT_WRITE_DATASET_FILES", "1") == "1"

# Channel type classification
CHANNEL_TYPES = {
    "Fp1": "EEG", "Fp2": "EEG", "F3": "EEG", "F4": "EEG",
    "C3": "EEG", "C4": "EEG", "P3": "EEG", "P4": "EEG",
    "O1": "EEG", "O2": "EEG", "F7": "EEG", "F8": "EEG",
    "T3": "EEG", "T4": "EEG", "T5": "EEG", "T6": "EEG",
    "Fz": "EEG", "Pz": "EEG", "Cz": "EEG",
    "A1": "EEG", "A2": "EEG",
    "T1": "EEG", "T2": "EEG",
    "F11": "EEG", "F12": "EEG",
    "Fpz": "EEG",
    "ECG": "ECG", "ECG1": "ECG", "ECG2": "ECG",
    "ECGL": "ECG", "ECGR": "ECG",
    "EOG": "EOG", "LOC": "EOG", "ROC": "EOG",
    "EMG": "EMG", "CHIN1": "EMG", "CHIN2": "EMG",
    "Digi": "MISC", "OSAT": "MISC", "PR": "MISC",
    "FLOW": "MISC", "SNORE": "MISC", "POS": "MISC",
    "CHEST": "MISC", "ABD": "MISC",
    "EDF Annotations": "ANNO",
}


def classify_channel(label):
    """Classify a channel label into BIDS type."""
    label_clean = label.strip()
    # Strip "EEG " prefix that Natus sometimes adds
    if label_clean.startswith("EEG "):
        label_clean = label_clean[4:]
    if label_clean in CHANNEL_TYPES:
        return CHANNEL_TYPES[label_clean]
    # Try case-insensitive
    for key, val in CHANNEL_TYPES.items():
        if label_clean.lower() == key.lower():
            return val
    # Default patterns
    if "ecg" in label_clean.lower() or "ekg" in label_clean.lower():
        return "ECG"
    if "eog" in label_clean.lower():
        return "EOG"
    if "emg" in label_clean.lower():
        return "EMG"
    if "dc" in label_clean.lower() or "digi" in label_clean.lower():
        return "MISC"
    return "EEG"


def channel_description(ch_type):
    """Return BIDS description for channel type."""
    return {
        "EEG": "ElectroEncephaloGram",
        "ECG": "ElectroCardioGram",
        "EOG": "ElectroOculoGram",
        "EMG": "ElectroMyoGram",
        "MISC": "Miscellaneous",
    }.get(ch_type, "ElectroEncephaloGram")


def build_name_scrubber(linking_table_path):
    """
    Build a set of names to scrub from annotation text.
    Uses all patient first/last names from the linking table.
    Returns (name_set, per_patient_names_dict).
    """
    df = pd.read_csv(linking_table_path)

    all_first = set()
    all_last = set()
    per_folder = {}

    for _, row in df.iterrows():
        first = str(row.get("first_name", "")).strip()
        last = str(row.get("last_name", "")).strip()
        folder = str(row.get("original_folder", ""))

        if first and first.lower() != "nan":
            all_first.add(first.lower())
        if last and last.lower() != "nan":
            all_last.add(last.lower())

        per_folder[folder] = {
            "first": first.lower() if first else "",
            "last": last.lower() if last else "",
        }

    # Words that are also names but are common in EEG/medical text — skip these
    # for the broad dictionary pass (they'll still be caught in per-patient pass)
    ambiguous = {
        "mark", "sharp", "chase", "grant", "grace", "faith", "hope", "dawn",
        "cole", "clay", "reed", "bell", "ward", "wells", "west", "young",
        "long", "best", "lane", "park", "page", "love", "cross", "rice",
        "field", "burns", "ball", "good", "poor", "fair", "fine", "free",
        "gray", "green", "brown", "black", "white", "rose", "wolf", "ford",
        "stone", "wood", "hand", "arms", "head", "duke", "king", "hardy",
        "terry", "ruby", "pearl", "angel", "autumn", "april", "august",
        "summer", "winter", "aurora", "delta", "iris", "jade", "amber",
        "olive", "violet", "penny", "miles", "chance", "pace", "flow",
        "burst", "spike", "arch", "base", "band", "flex", "moss", "horn",
    }

    # For broad matching: 4+ char names that aren't ambiguous
    broad_names = set()
    for n in (all_first | all_last):
        if len(n) >= 4 and n not in ambiguous:
            broad_names.add(n)

    return broad_names, per_folder


def scrub_names_from_text(text, broad_names, patient_first="", patient_last=""):
    """
    Remove names from annotation text.

    Tier 1: Always scrub this patient's own first and last name (any length).
    Tier 2: Scrub any word matching 4+ char names from the full dataset.
    """
    if not text:
        return text

    # Tier 1: This patient's own names (exact word match, case-insensitive)
    for name in (patient_first, patient_last):
        if name and len(name) >= 2:
            text = re.sub(
                r'\b' + re.escape(name) + r'\b',
                '[NAME]',
                text,
                flags=re.IGNORECASE,
            )

    # Tier 2: Broad dataset name dictionary
    words = re.findall(r'\b[A-Za-z]{4,}\b', text)
    for word in words:
        if word.lower() in broad_names:
            text = re.sub(
                r'\b' + re.escape(word) + r'\b',
                '[NAME]',
                text,
                flags=re.IGNORECASE,
            )

    return text


def shift_dates_in_text(text, shift_days):
    """Find and shift any dates embedded in annotation free text."""
    if shift_days == 0:
        return text

    delta = timedelta(days=shift_days)

    # Pattern: MM/DD/YYYY or MM/DD/YY
    def replace_date(match):
        date_str = match.group(0)
        for fmt_in, fmt_out in [
            ("%m/%d/%Y", "%m/%d/%Y"),
            ("%m/%d/%y", "%m/%d/%y"),
        ]:
            try:
                dt = datetime.strptime(date_str, fmt_in)
                shifted = dt + delta
                return shifted.strftime(fmt_out)
            except ValueError:
                continue
        return date_str  # Return unchanged if can't parse

    text = re.sub(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', replace_date, text)

    # Pattern: MM.DD.YYYY or DD.MM.YYYY (ambiguous but common in European format)
    def replace_dot_date(match):
        date_str = match.group(0)
        for fmt_in, fmt_out in [
            ("%m.%d.%Y", "%m.%d.%Y"),
            ("%d.%m.%Y", "%d.%m.%Y"),
        ]:
            try:
                dt = datetime.strptime(date_str, fmt_in)
                if dt.year > 2000:  # Sanity check
                    shifted = dt + delta
                    return shifted.strftime(fmt_out)
            except ValueError:
                continue
        return date_str

    text = re.sub(r'\b\d{2}\.\d{2}\.\d{4}\b', replace_dot_date, text)

    return text


def parse_lay_file(lay_path):
    """Parse a .lay annotation file and return list of annotation dicts."""
    annotations = []
    in_comments = False
    try:
        with open(lay_path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if line == "[Comments]":
                    in_comments = True
                    continue
                if line.startswith("[") and line.endswith("]"):
                    in_comments = False
                    continue
                if in_comments and line:
                    parts = line.split(",", 4)
                    if len(parts) >= 5:
                        annotations.append({
                            "onset_sec": float(parts[0]),
                            "text": parts[4].strip().strip('"'),
                        })
    except Exception:
        pass
    return annotations


def patch_edf_header(filepath, shifted_date):
    """
    Directly patch the EDF header bytes in-place to de-identify and apply date shift.
    This is O(1) in memory — only touches the first 256 bytes.

    EDF header layout:
      Bytes 8-87:   Local patient identification (80 bytes)
      Bytes 88-167: Local recording identification (80 bytes)
      Bytes 168-175: Start date dd.mm.yy (8 bytes)
      Bytes 176-183: Start time hh.mm.ss (8 bytes) — preserved
    """
    with open(filepath, "r+b") as f:
        # Clear patient identification
        f.seek(8)
        f.write(b"X X X X".ljust(80))

        # Set recording identification with shifted date
        if shifted_date:
            month_abbr = shifted_date.strftime("%b").upper()
            rec_date = f"{shifted_date.day:02d}-{month_abbr}-{shifted_date.year}"
            rec_id = f"Startdate {rec_date} X X X"
        else:
            rec_id = "Startdate X X X X"
        f.seek(88)
        f.write(rec_id.encode("ascii").ljust(80))

        # Set start date field
        if shifted_date:
            date_str = shifted_date.strftime("%d.%m.%y")
        else:
            date_str = "01.01.85"
        f.seek(168)
        f.write(date_str.encode("ascii").ljust(8))
        # Start time (bytes 176-183) is NOT modified


def deidentify_and_copy_edf(src_path, dst_path, shift_days):
    """
    Copy an EDF file, then patch the header to de-identify.
    Uses edfio for metadata extraction (lazy, no signal loading),
    then shutil.copy2 + binary header patch for the actual file.
    Returns metadata dict.
    """
    import shutil

    # Step 1: Extract metadata using edfio (lazy — no signal data loaded)
    try:
        edf = read_edf(src_path, lazy_load_data=True)
    except Exception as e:
        # Try a raw copy anyway for files edfio can't parse
        return {"error": f"Failed to read metadata: {e}"}

    try:
        startdate = edf.startdate
    except Exception:
        startdate = None
    try:
        starttime = edf.starttime
    except Exception:
        starttime = None
    try:
        recording_duration = edf.duration
    except Exception:
        recording_duration = 0

    # Convert time to string
    if starttime is not None:
        try:
            starttime_str = starttime.strftime("%H:%M:%S")
        except Exception:
            starttime_str = str(starttime)
    else:
        starttime_str = "00:00:00"

    # Date shift
    shifted_date = None
    if startdate and shift_days:
        try:
            shifted_date = startdate + timedelta(days=shift_days)
        except Exception:
            shifted_date = startdate

    # Gather channel info
    channels = []
    eeg_count = ecg_count = eog_count = emg_count = misc_count = 0
    for signal in edf.signals:
        label = signal.label.strip()
        ch_type = classify_channel(label)
        if ch_type == "ANNO":
            continue
        sampling_freq = signal.sampling_frequency
        # Strip "EEG " prefix for cleaner channel names
        display_name = label[4:] if label.startswith("EEG ") else label
        channels.append({
            "name": display_name,
            "type": ch_type,
            "units": "uV",
            "low_cutoff": 0.0,
            "high_cutoff": sampling_freq / 2.0,
            "description": channel_description(ch_type),
            "sampling_frequency": sampling_freq,
            "status": "good",
            "status_description": "n/a",
        })
        if ch_type == "EEG":
            eeg_count += 1
        elif ch_type == "ECG":
            ecg_count += 1
        elif ch_type == "EOG":
            eog_count += 1
        elif ch_type == "EMG":
            emg_count += 1
        else:
            misc_count += 1

    primary_sr = channels[0]["sampling_frequency"] if channels else 256.0

    # Close the edfio reader
    del edf

    # Step 2: Copy the file, then patch the header
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src_path), str(dst_path))
    except Exception as e:
        return {"error": f"Failed to copy: {e}"}

    try:
        patch_edf_header(dst_path, shifted_date)
    except Exception as e:
        return {"error": f"Failed to patch header: {e}"}

    return {
        "startdate": str(startdate) if startdate else "n/a",
        "starttime": starttime_str,
        "shifted_date": str(shifted_date) if shifted_date else "n/a",
        "duration_sec": recording_duration,
        "n_channels_total": len(channels),
        "eeg_count": eeg_count,
        "ecg_count": ecg_count,
        "eog_count": eog_count,
        "emg_count": emg_count,
        "misc_count": misc_count,
        "primary_sample_rate": primary_sr,
        "channels": channels,
        "error": "",
    }


def write_eeg_json(path, metadata):
    """Write _eeg.json sidecar."""
    data = {
        "TaskName": TASK_LABEL,
        "Manufacturer": "Natus/Xltek",
        "PowerLineFrequency": 60,
        "SamplingFrequency": metadata["primary_sample_rate"],
        "SoftwareFilters": "n/a",
        "RecordingDuration": metadata["duration_sec"],
        "RecordingType": "continuous",
        "EEGReference": "n/a",
        "EEGGround": "n/a",
        "EEGPlacementScheme": "10-20",
        "EEGChannelCount": metadata["eeg_count"],
        "EOGChannelCount": metadata["eog_count"],
        "ECGChannelCount": metadata["ecg_count"],
        "EMGChannelCount": metadata["emg_count"],
        "MiscChannelCount": metadata["misc_count"],
        "TriggerChannelCount": 0,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def write_channels_tsv(path, channels):
    """Write _channels.tsv sidecar."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "type", "units", "low_cutoff", "high_cutoff",
                         "description", "sampling_frequency", "status", "status_description"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(channels)


def write_xltek_csv(path, annotations, recording_start_dt, shift_days=0,
                    broad_names=None, patient_first="", patient_last=""):
    """Write _Xltek.csv from .lay annotations with shifted absolute timestamps."""
    if broad_names is None:
        broad_names = set()
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Text", "CreationTime"])
        for ann in annotations:
            ts = recording_start_dt + timedelta(seconds=ann["onset_sec"])
            text = ann["text"]
            # Scrub names from free text
            text = scrub_names_from_text(text, broad_names, patient_first, patient_last)
            # Shift any dates embedded in the annotation free text
            text = shift_dates_in_text(text, shift_days)
            writer.writerow([text, ts.strftime("%Y-%m-%dT%H:%M:%S.%f")])


def write_scans_tsv(path, eeg_filename, acq_time_str):
    """Write _scans.tsv."""
    with open(path, "w") as f:
        f.write("filename\tacq_time\n")
        f.write(f"eeg/{eeg_filename}\t{acq_time_str}\n")


def write_dataset_description(bids_root):
    """Write dataset_description.json."""
    data = {
        "Name": "Neurotech EEG Dataset",
        "BIDSVersion": "1.7.0",
        "DatasetType": "raw",
        "License": "CC BY-NC 4.0",
        "Authors": [
            "Keith Morgan", "Charles Pickering", "Matthew Goodwin", "Han Wu",
            "Manohar Ghanta", "Aditya Gupta", "Daniel Goldenholz", "M. Brandon Westover",
        ],
    }
    with open(bids_root / "dataset_description.json", "w") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def write_participants_files(bids_root, participants_data):
    """Write participants.tsv and participants.json."""
    # participants.tsv
    with open(bids_root / "participants.tsv", "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["participant_id", "age", "sex"],
            delimiter="\t",
        )
        writer.writeheader()
        for row in participants_data:
            writer.writerow(row)

    # participants.json
    desc = {
        "participant_id": {"Description": "Unique participant identifier"},
        "age": {"Description": "Age of participant at time of recording", "Units": "years"},
        "sex": {"Description": "Sex of participant", "Levels": {"M": "male", "F": "female", "n/a": "not available"}},
    }
    with open(bids_root / "participants.json", "w") as f:
        json.dump(desc, f, indent=4)
        f.write("\n")


def upload_to_s3(local_path, s3_key, max_retries=3):
    """Upload a local file to S3. Retries on failure. Returns True on success."""
    import subprocess
    file_size_mb = Path(local_path).stat().st_size / 1048576
    # Scale timeout with file size: 30s base + 1s per MB, minimum 120s
    timeout = max(120, int(30 + file_size_mb))
    cmd = [
        "aws", "s3", "cp", str(local_path),
        f"s3://{S3_BUCKET}/{s3_key}",
        "--region", AWS_REGION,
    ]
    for attempt in range(max_retries):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return True
            print(f"    S3 upload failed (attempt {attempt+1}): {result.stderr.strip()[:100]}")
        except subprocess.TimeoutExpired:
            print(f"    S3 upload timed out (attempt {attempt+1}, {timeout}s, {file_size_mb:.0f}MB)")
        except Exception as e:
            print(f"    S3 upload error (attempt {attempt+1}): {e}")
    return False


def upload_session_to_s3(sub_label, ses_label, ses_dir):
    """Upload all files in a session directory to S3, preserving structure."""
    success = True
    for filepath in sorted(ses_dir.rglob("*")):
        if filepath.is_file():
            # Build S3 key: Neurotech/sub-X/ses-Y/...
            relative = filepath.relative_to(BIDS_ROOT)
            s3_key = f"{S3_PREFIX}/{relative}"
            if not upload_to_s3(filepath, s3_key):
                success = False
    return success


def write_readme(bids_root):
    """Write README."""
    with open(bids_root / "README", "w") as f:
        f.write("# Neurotech EEG Dataset\n\n")
        f.write("De-identified EEG recordings from Neurotech, converted to BIDS format.\n\n")
        f.write("## Format\n")
        f.write("- EEG data in EDF+ format\n")
        f.write("- Sampling rate: 256 Hz\n")
        f.write("- Channel placement: 10-20 system\n")
        f.write("- Annotations from Natus/Xltek system in _Xltek.csv files\n\n")
        f.write("## De-identification\n")
        f.write("- All dates have been shifted by a random offset per patient\n")
        f.write("- Patient identifiers have been removed from EDF headers\n")
        f.write("- Times of day are preserved (only dates are shifted)\n")


def main():
    # Load linking table
    linking_path = LINKING_PATH
    if not linking_path.exists():
        print(f"ERROR: linking table not found: {linking_path}")
        sys.exit(1)
    print(f"Linking table: {linking_path}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    linking = pd.read_csv(linking_path)
    print(f"Loaded linking table: {len(linking)} rows, {linking['BDSPPatientID'].nunique()} patients")

    # Build name scrubber from the full linking table
    print("Building name scrubber...")
    broad_names, per_folder_names = build_name_scrubber(linking_path)
    print(f"  Broad name dictionary: {len(broad_names)} names")

    # Filter to folders with EDF files
    linking = linking[linking["n_edf_files"] > 0].copy()
    print(f"Folders with EDFs: {len(linking)}")

    # Create BIDS root
    BIDS_ROOT.mkdir(parents=True, exist_ok=True)

    # Track participants for dataset-level files
    participants_data = []
    all_errors = []

    # Track which subjects have been created (for progress file)
    progress_file = OUTPUT_DIR / "bids_progress.tsv"
    # Also check for old .csv and migrate
    old_progress = OUTPUT_DIR / "bids_progress.csv"
    completed = set()
    for pf in [progress_file, old_progress]:
        if pf.exists():
            sep = "\t" if pf.suffix == ".tsv" else ","
            try:
                prog_df = pd.read_csv(pf, sep=sep)
                if "folder_name" in prog_df.columns:
                    completed.update(prog_df["folder_name"].dropna().values)
            except Exception:
                # Fallback: read BDSPPatientID column and match back to linking table
                try:
                    prog_df = pd.read_csv(pf, sep=sep)
                    if "BDSPPatientID" in prog_df.columns:
                        done_ids = set(prog_df["BDSPPatientID"].dropna().values)
                        done_folders = linking[linking["BDSPPatientID"].isin(done_ids)]["original_folder"].values
                        completed.update(done_folders)
                except Exception:
                    pass
    if completed:
        print(f"Resuming: {len(completed)} folders already processed")

    start_time = time.time()
    total = len(linking)

    # Dashboard progress tracking
    dashboard_dir = DASHBOARD_DIR
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    progress_json_path = dashboard_dir / "progress.json"
    edfs_total = int(linking["n_edf_files"].sum())
    history = []
    recent_log = []

    # Initialize counters from previously completed work
    if completed:
        completed_rows = linking[linking["original_folder"].isin(completed)]
        edfs_prior = int(completed_rows["n_edf_files"].sum())
        # Try to load prior bytes from last progress.json
        bytes_prior = 0
        try:
            with open(progress_json_path, "r") as f:
                prior = json.load(f)
                bytes_prior = prior.get("bytes_uploaded", 0)
        except Exception:
            pass
        edfs_processed = edfs_prior
        edfs_uploaded = edfs_prior  # assume all prior were uploaded
        bytes_uploaded = bytes_prior
        recent_log.append(f"Resumed: {len(completed)} folders, {edfs_prior} EDFs, {bytes_prior/1073741824:.1f} GB already done")
        print(f"  Prior progress: {edfs_prior} EDFs, {bytes_prior/1073741824:.1f} GB uploaded")
    else:
        edfs_processed = 0
        edfs_uploaded = 0
        bytes_uploaded = 0

    def update_dashboard(folders_done, complete=False):
        elapsed = time.time() - start_time
        # Add history point every ~30 seconds or on completion
        if not history or elapsed - history[-1].get("elapsed", 0) >= 30 or complete:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            history.append({
                "time": f"{mins}:{secs:02d}",
                "done": folders_done,
                "edfs_done": edfs_processed,
                "errors": len(all_errors),
                "elapsed": elapsed,
            })
        data = {
            "folders_done": folders_done,
            "folders_total": total,
            "edfs_processed": edfs_processed,
            "edfs_uploaded": edfs_uploaded,
            "edfs_total": edfs_total,
            "bytes_uploaded": bytes_uploaded,
            "errors": len(all_errors),
            "elapsed_sec": elapsed,
            "complete": complete,
            "history": history[-200:],
            "recent_log": recent_log[-30:],
        }
        try:
            with open(progress_json_path, "w") as f:
                json.dump(data, f)
        except Exception:
            pass

    folders_completed = len(completed)
    folders_done_this_session = 0

    for idx, (_, row) in enumerate(linking.iterrows()):
        folder_name = row["original_folder"]
        patient_id = row["BDSPPatientID"]

        if folder_name in completed:
            continue

        if folders_done_this_session % 5 == 0:
            elapsed = time.time() - start_time
            total_done = folders_completed + folders_done_this_session
            if elapsed > 0 and folders_done_this_session > 0:
                rate = folders_done_this_session / elapsed
                remaining_folders = total - total_done
                remaining_sec = remaining_folders / rate
            else:
                remaining_sec = 0
            msg_log = f"[{total_done}/{total}] ({elapsed:.0f}s, ~{remaining_sec:.0f}s left) {patient_id}"
            msg_console = f"[{total_done}/{total}] ({elapsed:.0f}s, ~{remaining_sec:.0f}s left) {folder_name[:50]}..."
            print(f"  {msg_console}")
            recent_log.append(msg_log)
            update_dashboard(total_done)

        sub_label = patient_id.replace("-", "")  # sub-Neurotech1
        shift_days = int(row["shift_days"])
        session_start = int(row["session_start"])

        folder_path = DRIVE_PATH / folder_name
        if not folder_path.exists():
            all_errors.append({"folder": folder_name, "error": "Folder not found"})
            continue

        # Get EDF files (use glob, not iterdir — much faster on USB with many files)
        edf_files = sorted(folder_path.glob("*.edf"), key=lambda p: p.name)

        # Get .lay files
        lay_files = {
            p.stem: p
            for p in folder_path.glob("*.lay")
            if ".backup" not in p.name
        }

        patient_added = False

        for edf_idx, edf_path in enumerate(edf_files):
            ses_num = session_start + edf_idx
            ses_label = f"ses-{ses_num}"
            prefix = f"sub-{sub_label}_{ses_label}_task-{TASK_LABEL}"

            sub_dir = BIDS_ROOT / f"sub-{sub_label}"
            ses_dir = sub_dir / ses_label
            eeg_dir = ses_dir / "eeg"
            eeg_dir.mkdir(parents=True, exist_ok=True)

            # Skip zero-byte and tiny EDF files (corrupt/empty stubs)
            try:
                edf_size = edf_path.stat().st_size
            except OSError:
                edf_size = 0
            if edf_size < 512:  # Less than one EDF header = certainly empty
                edfs_processed += 1
                # Clean up empty dirs
                if eeg_dir.exists() and not any(eeg_dir.iterdir()):
                    eeg_dir.rmdir()
                if ses_dir.exists() and not any(ses_dir.iterdir()):
                    ses_dir.rmdir()
                continue

            # De-identify and copy EDF
            dst_edf = eeg_dir / f"{prefix}_eeg.edf"
            if dst_edf.exists():
                # Already processed (from a previous partial run)
                continue

            metadata = deidentify_and_copy_edf(edf_path, dst_edf, shift_days)
            edfs_processed += 1
            update_dashboard(idx + 1)

            if metadata.get("error"):
                all_errors.append({
                    "folder": folder_name,
                    "edf": edf_path.name,
                    "session": ses_label,
                    "error": metadata["error"],
                })
                # Clean up empty dirs if EDF failed
                if dst_edf.exists():
                    dst_edf.unlink()
                if eeg_dir.exists() and not any(eeg_dir.iterdir()):
                    eeg_dir.rmdir()
                if ses_dir.exists() and not any(ses_dir.iterdir()):
                    ses_dir.rmdir()
                continue

            # Write _eeg.json
            write_eeg_json(eeg_dir / f"{prefix}_eeg.json", metadata)

            # Write _channels.tsv
            write_channels_tsv(eeg_dir / f"{prefix}_channels.tsv", metadata["channels"])

            # Write _Xltek.csv if .lay annotations exist
            edf_stem = edf_path.stem
            if edf_stem in lay_files:
                annotations = parse_lay_file(lay_files[edf_stem])
                if annotations:
                    # Build shifted recording start datetime
                    try:
                        shifted_date = metadata["shifted_date"]
                        start_time_str = metadata["starttime"]
                        if shifted_date != "n/a" and start_time_str != "n/a":
                            # Parse shifted date and original time
                            sd = datetime.strptime(str(shifted_date), "%Y-%m-%d")
                            # starttime could be HH:MM:SS or datetime.time
                            st_str = str(start_time_str)
                            if ":" in st_str:
                                parts = st_str.split(":")
                                hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0
                            else:
                                hour, minute, second = 0, 0, 0
                            rec_start = sd.replace(hour=hour, minute=minute, second=second)
                        else:
                            rec_start = datetime(1985, 1, 1, 0, 0, 0)
                    except Exception:
                        rec_start = datetime(1985, 1, 1, 0, 0, 0)

                    # Get this patient's names for tier-1 scrubbing
                    pfn = per_folder_names.get(folder_name, {})
                    write_xltek_csv(
                        eeg_dir / f"{prefix}_Xltek.csv",
                        annotations,
                        rec_start,
                        shift_days=shift_days,
                        broad_names=broad_names,
                        patient_first=pfn.get("first", ""),
                        patient_last=pfn.get("last", ""),
                    )

            # Write _scans.tsv
            acq_time = metadata.get("shifted_date", "1985-01-01")
            acq_time_str = f"{acq_time}T{metadata.get('starttime', '00:00:00')}"
            # Clean up the acq_time_str
            acq_time_str = acq_time_str.replace(" ", "T") if "T" not in acq_time_str else acq_time_str
            write_scans_tsv(ses_dir / f"sub-{sub_label}_{ses_label}_scans.tsv",
                            f"{prefix}_eeg.edf", acq_time_str)

            # Upload session to S3 and clean up local files
            if UPLOAD_TO_S3:
                try:
                    session_bytes = sum(f.stat().st_size for f in ses_dir.rglob("*") if f.is_file())
                    upload_ok = upload_session_to_s3(sub_label, ses_label, ses_dir)
                    if upload_ok:
                        edfs_uploaded += 1
                        bytes_uploaded += session_bytes
                    else:
                        all_errors.append({
                            "folder": folder_name,
                            "edf": edf_path.name,
                            "session": ses_label,
                            "error": "S3 upload failed after retries",
                        })
                    if upload_ok and DELETE_AFTER_UPLOAD:
                        import shutil as _shutil
                        _shutil.rmtree(ses_dir)
                except Exception as e:
                    print(f"    Upload error: {e}")
                    all_errors.append({
                        "folder": folder_name,
                        "edf": edf_path.name,
                        "session": ses_label,
                        "error": f"Upload exception: {e}",
                    })

            # Add to participants list (once per patient)
            if not patient_added:
                participants_data.append({
                    "participant_id": f"sub-{sub_label}",
                    "age": "n/a",
                    "sex": "n/a",
                })
                patient_added = True

        # Clean up empty subject dir after all sessions uploaded
        if UPLOAD_TO_S3 and DELETE_AFTER_UPLOAD:
            sub_dir = BIDS_ROOT / f"sub-{sub_label}"
            if sub_dir.exists():
                try:
                    sub_dir.rmdir()  # Only works if empty
                except OSError:
                    pass

        folders_done_this_session += 1
        update_dashboard(folders_completed + folders_done_this_session)

        # Record progress (tab-separated since folder names contain commas)
        with open(progress_file, "a") as f:
            if f.tell() == 0:
                f.write("folder_name\tBDSPPatientID\ttimestamp\n")
            f.write(f"{folder_name}\t{patient_id}\t{datetime.now().isoformat()}\n")

    # Write dataset-level files (skipped for incremental batch runs to avoid
    # overwriting published metadata with a partial list — see WRITE_DATASET_FILES).
    if WRITE_DATASET_FILES:
        print("\nWriting dataset-level files...")
        write_dataset_description(BIDS_ROOT)
        write_participants_files(BIDS_ROOT, participants_data)
        write_readme(BIDS_ROOT)
        if UPLOAD_TO_S3:
            print("Uploading dataset-level files to S3...")
            for f in ["dataset_description.json", "participants.tsv", "participants.json", "README"]:
                fp = BIDS_ROOT / f
                if fp.exists():
                    upload_to_s3(fp, f"{S3_PREFIX}/{f}")
    else:
        print("\nSkipping dataset-level files (WRITE_DATASET_FILES=0); regenerate A–Z set separately.")

    # Save errors
    if all_errors:
        err_df = pd.DataFrame(all_errors)
        err_df.to_csv(OUTPUT_DIR / "bids_errors.csv", index=False)
        print(f"Errors: {len(all_errors)} (saved to bids_errors.csv)")

    elapsed = time.time() - start_time
    print(f"\n--- BIDS Conversion Summary ---")
    print(f"Time: {elapsed:.0f}s")
    print(f"Subjects created: {len(participants_data)}")
    print(f"EDFs processed: {edfs_processed}")
    print(f"EDFs uploaded: {edfs_uploaded}")
    print(f"Data uploaded: {bytes_uploaded/1073741824:.1f} GB")
    print(f"Errors: {len(all_errors)}")
    print(f"Output: {BIDS_ROOT}")

    update_dashboard(total, complete=True)


if __name__ == "__main__":
    main()
