#!/usr/bin/env python3
"""
Recover the recording equipment (Lifelines vs EMS) per recording.

RUN THIS ON THE MACHINE WITH THE SOURCE DATA / INVENTORY (the SSD machine).
The published S3 EDFs have the equipment field scrubbed; the real value survives in
the inventory CSVs that the inventory step already captured (extract_inventory.py /
fast_inventory_batch2.py both wrote an `equipment` column). So this is usually a few
seconds of tabulation, NOT an overnight EDF re-scan.

What it does:
  1. Loads output/recordings.csv (A-H) and output/batch2_IZ/recordings.csv (I-Z) if present.
  2. Shows the DISTINCT raw `equipment` values (so we see what the device actually wrote).
  3. Classifies each into Lifelines / EMS / other / blank and prints per-file and
     per-patient counts.

If the `equipment` column is populated and distinguishes the two, we have our accurate
count. If it is blank/uninformative, headers can't give us the split (report that back).

Fallback (only if the inventory column is blank): re-read the SOURCE EDF headers directly
(overnight is fine) — uncomment read_from_source_edfs() and point SRC at the drive.
"""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATES = [ROOT / "output" / "recordings.csv",
              ROOT / "output" / "batch2_IZ" / "recordings.csv"]


def classify(v: str) -> str:
    s = str(v or "").lower()
    if "lifeline" in s: return "Lifelines"
    if re.search(r"\bems\b|e\.m\.s|embla|natus", s):  # keep an eye out for stray Natus too
        return "Natus" if "natus" in s else "EMS"
    return "blank" if not s.strip() else "other"


def main() -> int:
    frames = []
    for p in CANDIDATES:
        if p.exists():
            df = pd.read_csv(p, dtype=str, keep_default_na=False)
            df["_src"] = p.name if p.parent.name == "output" else p.parent.name
            frames.append(df)
            print(f"loaded {p}  ({len(df)} rows, cols: {list(df.columns)[:12]}...)")
    if not frames:
        print("No recordings.csv found. Run this on the machine where inventory was built,"
              " or re-run extract_inventory.py / fast_inventory_batch2.py first.")
        return 1
    df = pd.concat(frames, ignore_index=True)
    if "equipment" not in df.columns:
        print("!! no 'equipment' column — check the inventory schema.")
        return 1

    print(f"\n=== RAW distinct `equipment` values (top 30 of {df['equipment'].nunique()}) ===")
    print(df["equipment"].value_counts(dropna=False).head(30).to_string())

    df["device"] = df["equipment"].map(classify)
    print("\n=== per-EDF-file device counts ===")
    print(df["device"].value_counts(dropna=False).to_string())
    print(f"  populated (non-blank): {(df['device']!='blank').mean()*100:.1f}% of files")

    # per-patient, if a folder/patient/path column exists
    keycol = next((c for c in ("patient", "patient_folder", "folder", "subject", "path", "file")
                   if c in df.columns), None)
    if keycol:
        pk = df[keycol].astype(str)
        if keycol in ("path", "file"):  # derive the patient folder from the path
            pk = pk.str.replace(r"[\\/].*$", "", regex=True)
        per_pat = df.assign(_pat=pk).groupby("_pat")["device"].agg(lambda s: s.mode().iat[0] if len(s.mode()) else "blank")
        print(f"\n=== per-patient dominant device (grouped by {keycol}) ===")
        print(per_pat.value_counts(dropna=False).to_string())

    print("\nIf Lifelines/EMS are well-populated above, that's the accurate split for the paper.")
    print("If it's mostly 'blank', the device isn't in the header and can't be recovered this way.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
