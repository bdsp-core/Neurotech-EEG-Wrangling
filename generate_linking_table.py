"""
Step 2: Generate linking table and subject assignments.

Scans the external drive directly (not relying on the inventory CSVs)
to build a complete linking table with de-identification info.
"""

import os
import re
import random
import csv
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd

# Force unbuffered output
import functools
print = functools.partial(print, flush=True)

DRIVE_PATH = Path("/Volumes/Padlock_DT")
OUTPUT_DIR = Path("/Users/mwestover/GithubRepos/NeuroTech-Wrangling/output")

FOLDER_PATTERN = re.compile(
    r"^(?P<last_name>[^,.]+)[,.\s]+\s*(?P<first_name>[^\d]+?)\s+"
    r"(?P<case_id>\d{2}\s*-+\s*\d{4,5})\s*(?P<suffix>.*)$"
)

# Non-patient items to skip
SKIP_NAMES = {
    "$RECYCLE.BIN",
    "128 Flatline test",
    "Aegis_Padlock_DT_benutzerhandbuch.pdf",
    "Aegis_Padlock_DT_guía_de_inicio_rápido.pdf",
    "Aegis_Padlock_DT_manual.pdf",
    "Aegis_Padlock_DT_manuale_dellutente.pdf",
    "Aegis_Padlock_DT_mode_d'emploi.pdf",
    "Aegis_Padlock_DT_マニュアル.pdf",
    "Apricorn-product-sales-agreement1.pdf",
}


FALLBACK_FOLDER_PATTERN = re.compile(
    r"^(?P<last_name>[^,]+),\s*(?P<first_name>\S+)\s+(?P<suffix>.*)$"
)


def parse_folder_name(name):
    m = FOLDER_PATTERN.match(name)
    if m:
        return {
            "last_name": m.group("last_name").strip(),
            "first_name": m.group("first_name").strip(),
            "case_id": m.group("case_id").strip().replace(" ", ""),
            "suffix": m.group("suffix").strip(),
        }
    # Fallback for folders without case IDs
    m2 = FALLBACK_FOLDER_PATTERN.match(name)
    if m2:
        return {
            "last_name": m2.group("last_name").strip(),
            "first_name": m2.group("first_name").strip(),
            "case_id": "UNKNOWN",
            "suffix": m2.group("suffix").strip(),
        }
    return None


def scan_folder_edfs(folder_path):
    """Return list of EDF files in a folder, sorted by name."""
    try:
        return sorted(folder_path.glob("*.edf"), key=lambda p: p.name)
    except OSError:
        return []


def scan_folder_lays(folder_path):
    """Return list of .lay files (non-backup) in a folder."""
    try:
        return sorted(
            p for p in folder_path.glob("*.lay") if ".backup" not in p.name
        )
    except OSError:
        return []


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)  # Reproducible shifts

    # Scan all folders on the drive
    print("Scanning drive for patient folders...")
    all_items = sorted(DRIVE_PATH.iterdir())
    patient_folders = []

    for item in all_items:
        if not item.is_dir():
            continue
        if item.name in SKIP_NAMES:
            continue
        if item.name.startswith("$") or item.name.startswith("."):
            continue

        info = parse_folder_name(item.name)
        if info is None:
            print(f"  SKIP (no match): {item.name}")
            continue

        # Count EDFs and .lay files
        edfs = scan_folder_edfs(item)
        lays = scan_folder_lays(item)

        patient_folders.append({
            "folder_name": item.name,
            "folder_path": str(item),
            **info,
            "n_edf_files": len(edfs),
            "n_lay_files": len(lays),
            "edf_filenames": "|".join(e.name for e in edfs),
            "lay_filenames": "|".join(l.name for l in lays),
        })

    print(f"Found {len(patient_folders)} patient folders")

    # Group by patient name to handle duplicates
    df = pd.DataFrame(patient_folders)
    df["name_key"] = df["last_name"].str.lower().str.strip() + "|" + df["first_name"].str.lower().str.strip()

    # Assign BDSPPatientID — same patient gets same ID
    # Sort by name_key, then case_id for deterministic ordering
    unique_names = sorted(df["name_key"].unique())
    name_to_id = {}
    name_to_shift = {}
    for i, name in enumerate(unique_names, start=1):
        name_to_id[name] = f"Neurotech-{i}"
        name_to_shift[name] = random.randint(-365, 365)

    df["BDSPPatientID"] = df["name_key"].map(name_to_id)
    df["shift_days"] = df["name_key"].map(name_to_shift)

    # Report duplicates
    dupes = df[df.duplicated("name_key", keep=False)]
    n_dupe_patients = dupes["name_key"].nunique()
    print(f"\nDuplicate patients (same name, multiple folders): {n_dupe_patients}")
    print(f"Total folders for duplicate patients: {len(dupes)}")

    # Assign session numbers — for patients with multiple folders,
    # sessions continue sequentially across folders (sorted by case_id)
    df = df.sort_values(["BDSPPatientID", "case_id", "folder_name"])
    session_counter = {}
    session_starts = []

    for _, row in df.iterrows():
        pid = row["BDSPPatientID"]
        if pid not in session_counter:
            session_counter[pid] = 1
        session_starts.append(session_counter[pid])
        n_edfs = row["n_edf_files"]
        session_counter[pid] += max(n_edfs, 0)

    df["session_start"] = session_starts

    # Build the linking table
    linking_rows = []
    for _, row in df.iterrows():
        linking_rows.append({
            "BDSPPatientID": row["BDSPPatientID"],
            "original_folder": row["folder_name"],
            "last_name": row["last_name"],
            "first_name": row["first_name"],
            "case_id": row["case_id"],
            "suffix": row["suffix"],
            "DOB_unshifted": "",  # Not reliably available from EDF headers
            "DOB_shifted": "",
            "sex": "",  # Not available in these files
            "ethnicity": "",
            "race": "",
            "shift_days": row["shift_days"],
            "n_edf_files": row["n_edf_files"],
            "n_lay_files": row["n_lay_files"],
            "session_start": row["session_start"],
            "edf_filenames": row["edf_filenames"],
            "lay_filenames": row["lay_filenames"],
        })

    linking_df = pd.DataFrame(linking_rows)
    linking_path = OUTPUT_DIR / "linking_table.csv"
    linking_df.to_csv(linking_path, index=False)
    print(f"\nLinking table saved: {linking_path}")
    print(f"  Total rows: {len(linking_df)}")
    print(f"  Unique patients: {linking_df['BDSPPatientID'].nunique()}")
    print(f"  Total EDF files: {linking_df['n_edf_files'].sum()}")
    print(f"  Folders with EDFs: {(linking_df['n_edf_files'] > 0).sum()}")
    print(f"  Folders with annotations: {(linking_df['n_lay_files'] > 0).sum()}")

    # Also save a summary for quick reference
    summary = linking_df.groupby("BDSPPatientID").agg(
        n_folders=("original_folder", "count"),
        n_edf_total=("n_edf_files", "sum"),
        n_lay_total=("n_lay_files", "sum"),
        shift_days=("shift_days", "first"),
    ).reset_index()
    summary.to_csv(OUTPUT_DIR / "patient_summary.csv", index=False)
    print(f"  Patient summary saved: {OUTPUT_DIR / 'patient_summary.csv'}")


if __name__ == "__main__":
    main()
