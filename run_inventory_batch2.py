"""
Wrapper to run extract_inventory on the new (batch 2, ~H->Z) drive WITHOUT
clobbering the existing A-H output files.

- Reuses extract_inventory's logic unchanged.
- Overrides OUTPUT_DIR -> output/batch2_IZ/ (the committed script hardcodes the
  old /Users/mwestover path and the A-H output dir).
- Supports NT_LIMIT env var for a quick smoke test on the first N folders.

Run:  .venv/bin/python run_inventory_batch2.py
Smoke: NT_LIMIT=5 .venv/bin/python run_inventory_batch2.py
"""
import os
import time
import traceback
from pathlib import Path

import pandas as pd
import extract_inventory as ei

REPO = Path(__file__).resolve().parent
ei.DRIVE_PATH = Path("/Volumes/Padlock_DT")
ei.OUTPUT_DIR = REPO / "output" / "batch2_IZ"


def main():
    out = ei.OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    all_items = sorted(ei.DRIVE_PATH.iterdir())
    patient_folders = [
        p for p in all_items
        if p.is_dir() and not p.name.startswith("$") and not p.name.startswith(".")
    ]

    limit = os.environ.get("NT_LIMIT")
    if limit:
        patient_folders = patient_folders[: int(limit)]

    print(f"Found {len(patient_folders)} folders to process -> {out}")

    recs_all, anns_all, pats_all, errors = [], [], [], []
    t0 = time.time()
    for i, folder in enumerate(patient_folders):
        if (i + 1) % 25 == 0 or i == 0:
            el = time.time() - t0
            rate = (i + 1) / el if el > 0 else 0
            rem = (len(patient_folders) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(patient_folders)}] {el:.0f}s elapsed, ~{rem:.0f}s left :: {folder.name[:48]}", flush=True)
        try:
            recs, anns, pat = ei.process_folder(folder, folder.name)
            recs_all.extend(recs)
            anns_all.extend(anns)
            pats_all.append(pat)
        except Exception as e:
            errors.append({"folder": folder.name, "error": str(e), "trace": traceback.format_exc()})
            print(f"  ERROR on {folder.name}: {e}", flush=True)

    print(f"\nSaving to {out}/ ...")
    if recs_all:
        pd.DataFrame(recs_all).to_csv(out / "recordings.csv", index=False)
        print(f"  recordings.csv: {len(recs_all)} rows")
    if anns_all:
        pd.DataFrame(anns_all).to_csv(out / "annotations.csv", index=False)
        print(f"  annotations.csv: {len(anns_all)} rows")
    if pats_all:
        pd.DataFrame(pats_all).to_csv(out / "patients.csv", index=False)
        print(f"  patients.csv: {len(pats_all)} rows")
    if errors:
        pd.DataFrame(errors).to_csv(out / "errors.csv", index=False)
        print(f"  errors.csv: {len(errors)} rows")

    el = time.time() - t0
    print(f"\n--- Summary ---\nFolders: {len(patient_folders)}  Recordings: {len(recs_all)}  "
          f"Annotations: {len(anns_all)}  Errors: {len(errors)}  Time: {el:.0f}s")


if __name__ == "__main__":
    main()
