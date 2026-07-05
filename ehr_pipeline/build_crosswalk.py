#!/usr/bin/env python3
"""
Build a crosswalk table linking EHR patient folders to BDSP de-identified
patient IDs via the EEG linking table.

IMPORTANT: This script READS the linking table but NEVER WRITES to it.

Join strategy (applied in order, first match wins):
  1. Exact name match: last|first (lowercased, stripped)
  2. Normalized match: remove punctuation, suffixes (Jr/Sr/II/III/IV), extra spaces
  3. First-root match: normalized last + first word of first name only
  4. Levenshtein fuzzy match: edit distance ≤ 2 on the normalized key

Output:
  output/ehr/ehr_eeg_crosswalk.csv

Usage:
  python ehr_pipeline/build_crosswalk.py
"""

from __future__ import annotations

import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKING_TABLE = ROOT / "output" / "linking_table.csv"
LINKING_TABLE_PENDING = ROOT / "output" / "linking_table_pending_eeg.csv"
EHR_STUDIES = ROOT / "output" / "ehr" / "studies.csv"
EHR_ROOT = Path("/Volumes/Extreme SSD/neurotech-data")
OUT_PATH = ROOT / "output" / "ehr" / "ehr_eeg_crosswalk.csv"

CROSSWALK_COLUMNS = [
    "ehr_study_id",
    "ehr_last_name",
    "ehr_first_name",
    "ehr_neurotech_id",
    "BDSPPatientID",
    "shift_days",
    "match_method",
    "match_confidence",
    "match_source",        # "linking_table" or "pending_extension"
    "lt_original_folder",
    "lt_case_id",
]


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Parse EHR folder names
# ---------------------------------------------------------------------------

def parse_ehr_folder(folder_name: str) -> dict:
    """Parse 'Last, First-NNNNNNNNNN' into components."""
    m = re.match(r"^(.+?)-(\d{8,})$", folder_name)
    if m:
        name_part = m.group(1)
        neurotech_id = m.group(2)
    else:
        name_part = folder_name
        neurotech_id = ""

    parts = name_part.split(",", 1)
    if len(parts) == 2:
        last = parts[0].strip()
        first = parts[1].strip()
    else:
        last = name_part.strip()
        first = ""

    return {
        "last": last,
        "first": first,
        "neurotech_id": neurotech_id,
        "exact_key": f"{last.lower().strip()}|{first.lower().strip()}",
        "norm_key": f"{normalize(last)}|{normalize(first)}",
        "root_key": f"{normalize(last)}|{first_root(first)}",
    }


# ---------------------------------------------------------------------------
# Build linking table indexes
# ---------------------------------------------------------------------------

def load_linking_table() -> tuple[list[dict], dict, dict, dict, dict]:
    """Load both the original linking table AND the pending-EEG extension.

    Returns (rows, by_exact, by_norm, by_root, source_map) where each name-key
    index maps to a list of linking table rows, and source_map[(name_key, folder)]
    gives "linking_table" or "pending_extension" so we can flag patients whose
    EEG hasn't arrived yet.
    """
    rows: list[dict] = []
    source_map: dict[int, str] = {}  # row identity → source file label

    # Primary table (READ-ONLY — never modify)
    if LINKING_TABLE.exists():
        with open(LINKING_TABLE, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                source_map[id(r)] = "linking_table"
                rows.append(r)

    # Extension table (created by extend_linking_table.py for EHR-only patients)
    if LINKING_TABLE_PENDING.exists():
        with open(LINKING_TABLE_PENDING, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                source_map[id(r)] = "pending_extension"
                rows.append(r)

    by_exact: dict[str, list[dict]] = defaultdict(list)
    by_norm: dict[str, list[dict]] = defaultdict(list)
    by_root: dict[str, list[dict]] = defaultdict(list)

    for r in rows:
        ek = f"{r['last_name'].lower().strip()}|{r['first_name'].lower().strip()}"
        nk = f"{normalize(r['last_name'])}|{normalize(r['first_name'])}"
        rk = f"{normalize(r['last_name'])}|{first_root(r['first_name'])}"
        by_exact[ek].append(r)
        by_norm[nk].append(r)
        by_root[rk].append(r)

    return rows, by_exact, by_norm, by_root, source_map


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def match_ehr_patient(
    ehr: dict,
    by_exact: dict[str, list[dict]],
    by_norm: dict[str, list[dict]],
    by_root: dict[str, list[dict]],
    all_norm_keys: list[tuple[str, dict]],
    source_map: dict[int, str],
) -> dict:
    """Try to match one EHR patient to the linking table. Returns crosswalk row."""

    base = {
        "ehr_study_id": ehr["folder"],
        "ehr_last_name": ehr["last"],
        "ehr_first_name": ehr["first"],
        "ehr_neurotech_id": ehr["neurotech_id"],
    }

    def make_result(lt_rows: list[dict], method: str, confidence: str) -> dict:
        # Use the first row's BDSPPatientID (same for all rows of same patient)
        r = lt_rows[0]
        return {
            **base,
            "BDSPPatientID": r["BDSPPatientID"],
            "shift_days": r["shift_days"],
            "match_method": method,
            "match_confidence": confidence,
            "match_source": source_map.get(id(r), "linking_table"),
            "lt_original_folder": r["original_folder"],
            "lt_case_id": r["case_id"],
        }

    # 1. Exact
    if ehr["exact_key"] in by_exact:
        return make_result(by_exact[ehr["exact_key"]], "exact", "high")

    # 2. Normalized
    if ehr["norm_key"] in by_norm:
        return make_result(by_norm[ehr["norm_key"]], "normalized", "high")

    # 3. First-root
    if ehr["root_key"] in by_root:
        return make_result(by_root[ehr["root_key"]], "first_root", "medium")

    # 4. Levenshtein fuzzy (only on normalized key, max distance 2)
    best_dist = 999
    best_match = None
    ehr_nk = ehr["norm_key"]
    # Only consider candidates whose last name starts with the same letter
    # (optimization to avoid O(n^2) on the full set)
    first_letter = ehr_nk[0] if ehr_nk else ""
    for lt_nk, lt_row in all_norm_keys:
        if lt_nk and lt_nk[0] != first_letter:
            continue
        d = levenshtein(ehr_nk, lt_nk)
        if d < best_dist:
            best_dist = d
            best_match = lt_row
    if best_dist <= 2 and best_match:
        confidence = "medium" if best_dist == 1 else "low"
        return make_result(
            [best_match], f"levenshtein_d{best_dist}", confidence
        )

    # 5. No match
    return {
        **base,
        "BDSPPatientID": "",
        "shift_days": "",
        "match_method": "unmatched",
        "match_confidence": "",
        "match_source": "",
        "lt_original_folder": "",
        "lt_case_id": "",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading linking table (READ-ONLY)...")
    lt_rows, by_exact, by_norm, by_root, source_map = load_linking_table()
    n_primary = sum(1 for r in lt_rows if source_map.get(id(r)) == "linking_table")
    n_pending = sum(1 for r in lt_rows if source_map.get(id(r)) == "pending_extension")
    print(f"  Primary linking_table.csv: {n_primary} rows")
    print(f"  Pending-EEG extension:     {n_pending} rows")
    print(f"  Total: {len(lt_rows)} rows, {len(by_exact)} exact keys")

    # Build flat list for Levenshtein search
    # Use one representative row per normalized key
    seen_nk: dict[str, dict] = {}
    for r in lt_rows:
        nk = f"{normalize(r['last_name'])}|{normalize(r['first_name'])}"
        if nk not in seen_nk:
            seen_nk[nk] = r
    all_norm_keys = list(seen_nk.items())
    print(f"  {len(all_norm_keys)} unique normalized keys for fuzzy matching")

    # Enumerate EHR patient folders
    print("\nScanning EHR folders...")
    ehr_patients: dict[str, dict] = {}  # folder_name → parsed info
    for d in sorted(EHR_ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        parsed = parse_ehr_folder(d.name)
        parsed["folder"] = d.name
        ehr_patients[d.name] = parsed
    print(f"  {len(ehr_patients)} EHR folders")

    # Deduplicate by patient name (same person, multiple visits)
    unique_by_name: dict[str, list[dict]] = defaultdict(list)
    for ehr in ehr_patients.values():
        unique_by_name[ehr["exact_key"]].append(ehr)
    print(f"  {len(unique_by_name)} unique patient names")

    # Match each unique patient
    print("\nMatching...")
    t0 = time.time()
    crosswalk_rows: list[dict] = []
    method_counts = defaultdict(int)

    for name_key, ehr_folders in sorted(unique_by_name.items()):
        # Match once per patient name, then apply to all their folders
        result = match_ehr_patient(
            ehr_folders[0], by_exact, by_norm, by_root, all_norm_keys, source_map
        )
        method_counts[result["match_method"]] += 1

        # Create one crosswalk row per EHR folder for this patient
        for ehr in ehr_folders:
            row = {
                **result,
                "ehr_study_id": ehr["folder"],
                "ehr_neurotech_id": ehr["neurotech_id"],
            }
            crosswalk_rows.append(row)

    dt = time.time() - t0
    print(f"  Matched in {dt:.1f}s")

    # Write crosswalk
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CROSSWALK_COLUMNS)
        w.writeheader()
        w.writerows(crosswalk_rows)

    # Report
    n_matched = sum(1 for r in crosswalk_rows if r["BDSPPatientID"])
    n_unmatched = sum(1 for r in crosswalk_rows if not r["BDSPPatientID"])
    unique_bdsp = len(set(r["BDSPPatientID"] for r in crosswalk_rows if r["BDSPPatientID"]))

    print(f"\n=== CROSSWALK RESULTS ===")
    print(f"  Total EHR folders: {len(crosswalk_rows)}")
    print(f"  Matched to BDSP ID: {n_matched} ({n_matched/len(crosswalk_rows)*100:.1f}%)")
    print(f"  Unmatched: {n_unmatched} ({n_unmatched/len(crosswalk_rows)*100:.1f}%)")
    print(f"  Unique BDSP patients linked: {unique_bdsp}")
    print(f"\n  Match method breakdown (per unique patient name):")
    for method, count in sorted(method_counts.items(), key=lambda x: -x[1]):
        print(f"    {method:>20}: {count}")
    print(f"\n  Output: {OUT_PATH}")


if __name__ == "__main__":
    main()
