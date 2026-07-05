#!/usr/bin/env python3
"""
Extend the BDSP linking table to cover EHR-only patients (no EEG yet).

Why: many EHR PDFs in the local Neurotech-EHR/ tree correspond to patients
whose EEG signal data hasn't arrived yet (coming on a hard drive). To
de-identify the EHR data NOW without waiting for the EEG, we pre-assign
each new patient a BDSPPatientID and a date_shift integer. When the EEG
drive arrives, the BIDS conversion will use these same IDs and shifts so
the two streams stay aligned.

IMPORTANT: This script never modifies output/linking_table.csv. Instead it
writes output/linking_table_pending_eeg.csv with new entries for EHR-only
patients. Downstream scripts (build_crosswalk.py, deidentify_ehr.py) read
BOTH tables.

Algorithm:
  1. Read existing linking table (read-only). Note next available
     Neurotech-N number.
  2. Walk Neurotech-EHR/ folders. For each folder, parse (last, first).
  3. Match against existing linking table using the same 4-tier strategy
     as build_crosswalk.py. If matched, skip (no new ID needed).
  4. For unmatched patients (PDF-only), group by (last, first) so multi-
     visit patients get the same ID. Assign new BDSPPatientIDs sequentially.
  5. Generate per-patient shift_days uniformly in [-365, +365] using
     random seed 43 (one increment from the existing table's seed=42 to
     avoid any chance of correlation).
  6. Write output/linking_table_pending_eeg.csv with the same schema as
     linking_table.csv. Fields not knowable yet (n_edf_files, edf_filenames,
     etc.) are left blank — the BIDS conversion will fill them in when the
     EEG drive lands.

Usage:
  python ehr_pipeline/extend_linking_table.py
  python ehr_pipeline/extend_linking_table.py --dry-run

When the EEG drive arrives, the maintainer should either:
  (a) manually concatenate linking_table_pending_eeg.csv into a fresh
      linking_table.csv after running generate_linking_table.py, OR
  (b) extend generate_linking_table.py to honor pre-assigned IDs from this
      pending file.
"""

from __future__ import annotations

import argparse
import csv
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKING_TABLE = ROOT / "output" / "linking_table.csv"
EXTENSION_TABLE = ROOT / "output" / "linking_table_pending_eeg.csv"
EHR_ROOT = Path("/Volumes/Extreme SSD/neurotech-data")

LINKING_COLUMNS = [
    "BDSPPatientID", "original_folder", "last_name", "first_name", "case_id",
    "suffix", "DOB_unshifted", "DOB_shifted", "sex", "ethnicity", "race",
    "shift_days", "n_edf_files", "n_lay_files", "session_start",
    "edf_filenames", "lay_filenames",
]


# ---- Name normalization (must match build_crosswalk.py exactly) ------------

def normalize(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[,.\-''\"()\[\]]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s).strip()
    return s


def first_root(s: str) -> str:
    return normalize(s).split()[0] if s.strip() else ""


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[len(b)]


def parse_ehr_folder(name: str) -> dict:
    m = re.match(r"^(.+?)-(\d{8,})$", name)
    name_part = m.group(1) if m else name
    neurotech_id = m.group(2) if m else ""
    parts = name_part.split(",", 1)
    if len(parts) == 2:
        last, first = parts[0].strip(), parts[1].strip()
    else:
        last, first = name_part.strip(), ""
    return {
        "folder": name,
        "last": last,
        "first": first,
        "neurotech_id": neurotech_id,
        "exact_key": f"{last.lower().strip()}|{first.lower().strip()}",
        "norm_key": f"{normalize(last)}|{normalize(first)}",
        "root_key": f"{normalize(last)}|{first_root(first)}",
    }


# ---- Match against existing linking table -----------------------------------

def is_already_matched(
    ehr: dict,
    by_exact: dict,
    by_norm: dict,
    by_root: dict,
    all_norm_keys: list,
) -> bool:
    if ehr["exact_key"] in by_exact:
        return True
    if ehr["norm_key"] in by_norm:
        return True
    if ehr["root_key"] in by_root:
        return True
    # Levenshtein d<=2 against same first letter
    ehr_nk = ehr["norm_key"]
    first_letter = ehr_nk[0] if ehr_nk else ""
    for lt_nk in all_norm_keys:
        if lt_nk and lt_nk[0] != first_letter:
            continue
        if levenshtein(ehr_nk, lt_nk) <= 2:
            return True
    return False


# ---- Main ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Read existing linking table (READ-ONLY)
    print(f"Reading existing linking table: {LINKING_TABLE}")
    with open(LINKING_TABLE, encoding="utf-8") as f:
        existing_rows = list(csv.DictReader(f))
    print(f"  {len(existing_rows)} rows, "
          f"{len(set(r['BDSPPatientID'] for r in existing_rows))} unique patients")

    # Find next available Neurotech-N
    nums = []
    for r in existing_rows:
        m = re.match(r"Neurotech-(\d+)", r["BDSPPatientID"])
        if m:
            nums.append(int(m.group(1)))
    next_id = max(nums) + 1 if nums else 1
    print(f"  Next available BDSPPatientID: Neurotech-{next_id}")

    # Build name indexes for matching
    by_exact, by_norm, by_root = {}, {}, {}
    seen_norm = set()
    for r in existing_rows:
        ek = f"{r['last_name'].lower().strip()}|{r['first_name'].lower().strip()}"
        nk = f"{normalize(r['last_name'])}|{normalize(r['first_name'])}"
        rk = f"{normalize(r['last_name'])}|{first_root(r['first_name'])}"
        by_exact[ek] = r
        by_norm[nk] = r
        by_root[rk] = r
        seen_norm.add(nk)
    all_norm_keys = list(seen_norm)

    # Walk EHR folders, find unmatched ones
    print(f"\nWalking EHR folders under {EHR_ROOT}...")
    ehr_folders = []
    for d in sorted(EHR_ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        ehr_folders.append(parse_ehr_folder(d.name))
    print(f"  {len(ehr_folders)} EHR folders")

    unmatched = [e for e in ehr_folders if not is_already_matched(
        e, by_exact, by_norm, by_root, all_norm_keys
    )]
    print(f"  Unmatched (no EEG yet): {len(unmatched)}")

    # Group unmatched by (last, first) so multi-visit gets same ID
    by_name: dict[str, list[dict]] = defaultdict(list)
    for e in unmatched:
        by_name[e["norm_key"]].append(e)
    print(f"  Unique unmatched patients (by name): {len(by_name)}")

    # Also check for collisions with the extension table itself
    # (in case this script is re-run incrementally)
    existing_extension: dict[str, dict] = {}
    if EXTENSION_TABLE.exists():
        print(f"\nFound existing extension at {EXTENSION_TABLE}")
        with open(EXTENSION_TABLE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing_extension[r["BDSPPatientID"]] = r
        print(f"  {len(existing_extension)} prior extension rows; will preserve their IDs")
        # Preserve the highest used ID even from extension
        for k in existing_extension:
            m = re.match(r"Neurotech-(\d+)", k)
            if m:
                next_id = max(next_id, int(m.group(1)) + 1)

        # Build name lookup for extension to reuse IDs/shifts on re-runs
        ext_by_norm: dict[str, dict] = {}
        for r in existing_extension.values():
            nk = f"{normalize(r['last_name'])}|{normalize(r['first_name'])}"
            ext_by_norm[nk] = r
    else:
        ext_by_norm = {}

    # Assign new IDs and shifts (deterministic with seed 43)
    rng = random.Random(43)

    # Sort name keys deterministically so re-runs assign IDs in the same order
    sorted_names = sorted(by_name.keys())

    new_rows: list[dict] = []
    n_new_patients = 0
    n_reused = 0
    name_to_pid: dict[str, str] = {}
    name_to_shift: dict[str, int] = {}

    for nk in sorted_names:
        # Re-use prior assignment if this name was already in the extension
        if nk in ext_by_norm:
            prior = ext_by_norm[nk]
            pid = prior["BDSPPatientID"]
            shift = int(prior["shift_days"])
            n_reused += 1
        else:
            pid = f"Neurotech-{next_id}"
            next_id += 1
            shift = rng.randint(-365, 365)
            n_new_patients += 1
        name_to_pid[nk] = pid
        name_to_shift[nk] = shift

    print(f"\n  New patients assigned: {n_new_patients}")
    print(f"  Re-used from prior extension: {n_reused}")

    # One row per EHR folder (matches the original table's per-visit structure)
    for nk in sorted_names:
        for ehr in by_name[nk]:
            new_rows.append({
                "BDSPPatientID": name_to_pid[nk],
                "original_folder": ehr["folder"],
                "last_name": ehr["last"],
                "first_name": ehr["first"],
                # case_id and EEG-side fields are unknown until the drive arrives
                "case_id": "",
                "suffix": "",
                "DOB_unshifted": "",
                "DOB_shifted": "",
                "sex": "",
                "ethnicity": "",
                "race": "",
                "shift_days": name_to_shift[nk],
                "n_edf_files": "",
                "n_lay_files": "",
                "session_start": "",
                "edf_filenames": "",
                "lay_filenames": "",
            })

    print(f"\n  Total extension rows (one per EHR folder): {len(new_rows)}")
    print(f"  Final BDSPPatientID range: Neurotech-{next_id - n_new_patients} "
          f"... Neurotech-{next_id - 1}")

    if args.dry_run:
        print("\n  Dry run — not writing.")
        return 0

    EXTENSION_TABLE.parent.mkdir(parents=True, exist_ok=True)
    tmp = EXTENSION_TABLE.with_suffix(".csv.tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LINKING_COLUMNS)
        w.writeheader()
        w.writerows(new_rows)
    tmp.replace(EXTENSION_TABLE)
    print(f"\n  Wrote: {EXTENSION_TABLE}")
    print(f"\nWhen EEG drive arrives, append this file's rows to a regenerated "
          f"linking_table.csv (keying on BDSPPatientID); the BIDS conversion will "
          f"then use the same IDs and date shifts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
