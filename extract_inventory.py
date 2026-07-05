"""
Extract inventory and annotations from Natus/Xltek NeuroWorks EEG dataset.

Scans patient folders on the external drive, reads EDF headers and .lay
annotation files, and produces:
  1. recordings.csv  — one row per EDF file (metadata + channel info)
  2. annotations.csv — one row per annotation event from .lay files
  3. patients.csv    — one row per patient folder (summary)
"""

import os
import re
import csv
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime

import pyedflib
import pandas as pd

DRIVE_PATH = Path("/Volumes/Padlock_DT")
OUTPUT_DIR = Path("/Users/mwestover/GithubRepos/NeuroTech-Wrangling/output")

# Regex to parse folder names like "LastName, FirstName 25-06077 EMS"
FOLDER_PATTERN = re.compile(
    r"^(?P<last_name>[^,]+),\s*(?P<first_name>[^\d]+?)\s+"
    r"(?P<case_id>\d{2}-\d{4,5})\s*(?P<suffix>.*)$"
)


def parse_folder_name(folder_name):
    """Extract patient name and case ID from folder name."""
    m = FOLDER_PATTERN.match(folder_name)
    if m:
        return {
            "last_name": m.group("last_name").strip(),
            "first_name": m.group("first_name").strip(),
            "case_id": m.group("case_id").strip(),
            "suffix": m.group("suffix").strip(),
        }
    return {
        "last_name": "",
        "first_name": "",
        "case_id": "",
        "suffix": folder_name,
    }


def read_edf_header(edf_path):
    """Read EDF header and return metadata dict. Does not load signal data."""
    try:
        f = pyedflib.EdfReader(str(edf_path))
    except Exception as e:
        return {"error": str(e)}

    try:
        header = f.getHeader()
        n_channels = f.signals_in_file
        n_data_records = f.datarecords_in_file
        file_duration_sec = f.file_duration

        channel_labels = []
        sample_rates = []
        for i in range(n_channels):
            channel_labels.append(f.getLabel(i))
            sample_rates.append(f.getSampleFrequency(i))

        # Get EDF+ annotations if present
        edf_annotations = []
        try:
            annotations = f.readAnnotations()
            if annotations and len(annotations[0]) > 0:
                for onset, duration, text in zip(
                    annotations[0], annotations[1], annotations[2]
                ):
                    edf_annotations.append(
                        {
                            "onset_sec": float(onset),
                            "duration_sec": float(duration),
                            "text": str(text),
                        }
                    )
        except Exception:
            pass

        return {
            "patient_name": header.get("patientname", ""),
            "patient_id": header.get("patientcode", ""),
            "gender": header.get("gender", ""),
            "birthdate": str(header.get("birthdate", "")),
            "startdate": str(header.get("startdate", "")),
            "starttime": str(header.get("starttime", "")),
            "recording_additional": header.get("recording_additional", ""),
            "patient_additional": header.get("patient_additional", ""),
            "technician": header.get("technician", ""),
            "equipment": header.get("equipment", ""),
            "filetype": header.get("filetype", ""),
            "n_channels": n_channels,
            "n_data_records": n_data_records,
            "duration_sec": file_duration_sec,
            "duration_hours": round(file_duration_sec / 3600, 2),
            "channel_labels": "|".join(channel_labels),
            "sample_rates": "|".join(str(int(s)) for s in sample_rates),
            "primary_sample_rate": int(max(set(sample_rates), key=sample_rates.count))
            if sample_rates
            else 0,
            "n_edf_annotations": len(edf_annotations),
            "edf_annotations": edf_annotations,
            "error": "",
        }
    finally:
        f.close()


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
                    # Format: timestamp,duration,unknown1,unknown2,text
                    parts = line.split(",", 4)
                    if len(parts) >= 5:
                        annotations.append(
                            {
                                "onset_sec": float(parts[0]),
                                "duration_sec": float(parts[1]),
                                "field3": parts[2],
                                "field4": parts[3],
                                "text": parts[4].strip().strip('"'),
                            }
                        )
                    elif len(parts) >= 1:
                        annotations.append(
                            {
                                "onset_sec": 0,
                                "duration_sec": 0,
                                "field3": "",
                                "field4": "",
                                "text": line,
                            }
                        )
    except Exception as e:
        annotations.append(
            {
                "onset_sec": 0,
                "duration_sec": 0,
                "field3": "",
                "field4": "",
                "text": f"ERROR reading file: {e}",
            }
        )

    return annotations


def classify_annotation(text):
    """Classify annotation text into categories."""
    text_lower = text.lower()
    categories = []

    if "@spike" in text_lower or "spike" in text_lower:
        categories.append("spike")
    if "s/w" in text_lower or "spike-wave" in text_lower or "spike and wave" in text_lower:
        categories.append("spike_wave")
    if "@seizure" in text_lower or "seizure" in text_lower or "sz " in text_lower:
        categories.append("seizure")
    if "sharp" in text_lower:
        categories.append("sharp_wave")
    if "@clip" in text_lower:
        categories.append("clip")
    if "eyes closed" in text_lower or "eyes open" in text_lower:
        categories.append("activation")
    if "pdr" in text_lower:
        categories.append("pdr")
    if "slow" in text_lower:
        categories.append("slowing")
    if "periodic" in text_lower:
        categories.append("periodic")
    if "burst" in text_lower or "suppression" in text_lower:
        categories.append("burst_suppression")
    if "artifact" in text_lower:
        categories.append("artifact")
    if "normal" in text_lower:
        categories.append("normal")
    if "abnormal" in text_lower:
        categories.append("abnormal")
    if "epilep" in text_lower:
        categories.append("epileptiform")
    if "focal" in text_lower:
        categories.append("focal")
    if "generalized" in text_lower:
        categories.append("generalized")
    if "nt-" in text_lower:
        categories.append("neurotech_comment")

    if not categories:
        categories.append("other")

    return "|".join(categories)


def extract_lateralization(text):
    """Extract lateralization info from annotation text."""
    text_lower = text.lower()
    parts = []
    if "left" in text_lower:
        parts.append("left")
    if "right" in text_lower:
        parts.append("right")
    if "bilateral" in text_lower or "bi-" in text_lower:
        parts.append("bilateral")

    # Regions
    for region in [
        "frontal",
        "temporal",
        "parietal",
        "occipital",
        "central",
        "parasagittal",
    ]:
        if region in text_lower:
            parts.append(region)

    return "|".join(parts) if parts else ""


def process_folder(folder_path, folder_name):
    """Process a single patient folder. Returns (recordings, annotations)."""
    recordings = []
    annotations = []

    patient_info = parse_folder_name(folder_name)

    # Find all EDF files
    edf_files = sorted(folder_path.glob("*.edf"))
    # Find all .lay files (non-backup)
    lay_files = sorted(
        p for p in folder_path.glob("*.lay") if ".backup" not in p.name
    )

    # Count other file types
    all_files = list(folder_path.iterdir()) if folder_path.is_dir() else []
    file_type_counts = {}
    total_size_bytes = 0
    for f in all_files:
        if f.is_file():
            ext = f.suffix.lower() if f.suffix else "(none)"
            # For .mg2.xxx.raw etc, simplify
            name = f.name
            if ".mg2." in name and ext in (".raw", ".ar"):
                ext = ".mg2_trend"
            file_type_counts[ext] = file_type_counts.get(ext, 0) + 1
            try:
                total_size_bytes += f.stat().st_size
            except OSError:
                pass

    # Process EDF files
    for edf_path in edf_files:
        edf_size = 0
        try:
            edf_size = edf_path.stat().st_size
        except OSError:
            pass

        header = read_edf_header(edf_path)
        edf_annotations_list = header.pop("edf_annotations", [])

        rec = {
            "folder_name": folder_name,
            "edf_filename": edf_path.name,
            "edf_size_mb": round(edf_size / 1048576, 1),
            **patient_info,
            **header,
        }
        recordings.append(rec)

        # Add EDF+ embedded annotations
        for ann in edf_annotations_list:
            if ann["text"].strip():  # skip empty annotations
                annotations.append(
                    {
                        "folder_name": folder_name,
                        "source_file": edf_path.name,
                        "source_type": "edf_embedded",
                        "case_id": patient_info["case_id"],
                        "onset_sec": ann["onset_sec"],
                        "duration_sec": ann["duration_sec"],
                        "text": ann["text"],
                        "category": classify_annotation(ann["text"]),
                        "lateralization": extract_lateralization(ann["text"]),
                    }
                )

    # Process .lay files
    for lay_path in lay_files:
        lay_annotations = parse_lay_file(lay_path)
        # Try to match lay file to an EDF
        base = lay_path.stem  # e.g. 2_0_1D20251024105446
        matched_edf = f"{base}.edf"

        for ann in lay_annotations:
            annotations.append(
                {
                    "folder_name": folder_name,
                    "source_file": lay_path.name,
                    "source_type": "lay_file",
                    "matched_edf": matched_edf,
                    "case_id": patient_info["case_id"],
                    "onset_sec": ann["onset_sec"],
                    "duration_sec": ann["duration_sec"],
                    "text": ann["text"],
                    "category": classify_annotation(ann["text"]),
                    "lateralization": extract_lateralization(ann["text"]),
                }
            )

    # Patient summary
    patient_summary = {
        "folder_name": folder_name,
        **patient_info,
        "n_edf_files": len(edf_files),
        "n_lay_files": len(lay_files),
        "n_lay_annotations": sum(
            1 for a in annotations if a.get("source_type") == "lay_file"
        ),
        "n_edf_annotations": sum(
            1 for a in annotations if a.get("source_type") == "edf_embedded"
        ),
        "total_size_mb": round(total_size_bytes / 1048576, 1),
        "file_types": str(file_type_counts),
    }

    return recordings, annotations, patient_summary


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get all patient folders
    all_items = sorted(DRIVE_PATH.iterdir())
    patient_folders = [
        p
        for p in all_items
        if p.is_dir() and not p.name.startswith("$") and not p.name.startswith(".")
    ]

    print(f"Found {len(patient_folders)} folders to process")

    all_recordings = []
    all_annotations = []
    all_patients = []
    errors = []

    start_time = time.time()
    for i, folder in enumerate(patient_folders):
        if (i + 1) % 50 == 0 or i == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(patient_folders) - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i+1}/{len(patient_folders)}] "
                f"({elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining) "
                f"Processing: {folder.name[:50]}..."
            )

        try:
            recs, anns, patient = process_folder(folder, folder.name)
            all_recordings.extend(recs)
            all_annotations.extend(anns)
            all_patients.append(patient)
        except Exception as e:
            errors.append({"folder": folder.name, "error": str(e), "trace": traceback.format_exc()})
            print(f"  ERROR on {folder.name}: {e}")

    # Save results
    print(f"\nSaving results to {OUTPUT_DIR}/...")

    if all_recordings:
        df_rec = pd.DataFrame(all_recordings)
        df_rec.to_csv(OUTPUT_DIR / "recordings.csv", index=False)
        print(f"  recordings.csv: {len(df_rec)} rows")

    if all_annotations:
        df_ann = pd.DataFrame(all_annotations)
        df_ann.to_csv(OUTPUT_DIR / "annotations.csv", index=False)
        print(f"  annotations.csv: {len(df_ann)} rows")

    if all_patients:
        df_pat = pd.DataFrame(all_patients)
        df_pat.to_csv(OUTPUT_DIR / "patients.csv", index=False)
        print(f"  patients.csv: {len(df_pat)} rows")

    if errors:
        df_err = pd.DataFrame(errors)
        df_err.to_csv(OUTPUT_DIR / "errors.csv", index=False)
        print(f"  errors.csv: {len(df_err)} rows")

    # Print summary
    elapsed = time.time() - start_time
    print(f"\n--- Summary ---")
    print(f"Processed {len(patient_folders)} folders in {elapsed:.0f}s")
    print(f"Recordings: {len(all_recordings)}")
    print(f"Annotations: {len(all_annotations)}")
    print(f"Errors: {len(errors)}")

    if all_annotations:
        # Category breakdown
        df_ann = pd.DataFrame(all_annotations)
        print(f"\nAnnotation category breakdown:")
        cats = df_ann["category"].str.split("|").explode().value_counts()
        for cat, count in cats.head(20).items():
            print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
