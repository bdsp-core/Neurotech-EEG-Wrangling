#!/usr/bin/env python3
"""Release gate for the Scientific Data submission. Exit 0 only when everything is ready.

Checks (1) the manuscript passes check_scidata.py, (2) every number printed by
reproduce_manuscript_numbers.py that matters appears in the manuscript, (3) no stale
built-release numbers remain in any deliverable, (4) figures/docx/pdf are newer than the
markdown source, (5) the Downloads package is complete, (6) the S3 release matches the
manuscript (participants rows; orphan sessions gone) — S3 checks are read-only and can be
skipped with --no-s3.

Run:  .venv/bin/python manuscript-materials/scidata/release_gate.py [--no-s3] [--downloads DIR]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MM = ROOT / "manuscript-materials"
SD = MM / "scidata"
PY = ROOT / ".venv" / "bin" / "python"

STALE = ["4,914", "23,607", "212,186", "30,819", "54,426", "14,517", "226,486", "50,482", "6,892",
         "21,330", "19,401", "15,746", "53,469", "3 to 21", "1.13 annotations", "0.47 to 2.78", "232,000", "Natus/Xltek"]
DELIVERABLES = [MM / "manuscript-scidata.md", SD / "cover_letter.md", SD / "reviewer_data_access_note.md",
                SD / "human_data_checklist_answers.md", MM / "bdsp_listing_draft.md"]
PACKAGE = ["Neurotech_EEG_Dataset_SciData.docx", "Neurotech_EEG_Dataset_SciData.pdf", "figures/Figure1.png",
           "figures/Figure2.png", "figures/Figure3.png", "figures/Figure4.png", "cover_letter.md", "cover_letter.docx",
           "Human_Data_Checklist_FILLED.docx", "reviewer_data_access_note.docx", "README_SUBMISSION.md"]

ok = True


def report(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg)
    ok &= bool(cond)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-s3", action="store_true")
    ap.add_argument("--downloads", type=Path, default=None)
    args = ap.parse_args()

    # 1) format checks
    r = subprocess.run([str(PY), str(MM / "check_scidata.py")], capture_output=True, text=True)
    report(r.returncode == 0 and "ALL PASS" in r.stdout, "check_scidata.py passes")

    # 2) reproduced numbers present in the manuscript
    rep = subprocess.run([str(PY), str(ROOT / "reproduce_manuscript_numbers.py")], capture_output=True, text=True).stdout
    md = (MM / "manuscript-scidata.md").read_text()
    want = {}
    for line in rep.splitlines():
        m = re.match(r"\s{2}(.+?)\s{2,}(.+)$", line)
        if m:
            want[m.group(1).strip()] = m.group(2).strip()
    keys = ["Unique subjects", "Recordings with signal", "Header-only stubs", "Total EDF files (BIDS)", "Total recording hours",
            "Total annotation events", "Annotated recordings (files)", "Spike markers", "Seizure markers", "Sharp waves",
            "Technician clips", "Activation procedures", "Slowing", "Patients with clinical docs", "Referral ICD codes (total)",
            "With epileptiform discharges", "With seizures captured", "PDR extractable"]
    for k in keys:
        v = want.get(k, "")
        num = re.match(r"[\d,\.]+", v)
        report(bool(num) and num.group(0) in md, f"reproduced '{k}' = {v} appears in manuscript")

    # 3) stale numbers
    for f in DELIVERABLES:
        t = f.read_text()
        bad = [s for s in STALE if s in t]
        report(not bad, f"no stale numbers in {f.relative_to(ROOT)} {bad if bad else ''}")

    # 4) build freshness
    src = (MM / "manuscript-scidata.md").stat().st_mtime
    for out in ["Neurotech_EEG_Dataset_SciData.docx", "Neurotech_EEG_Dataset_SciData.pdf"]:
        p = SD / out
        report(p.exists() and p.stat().st_mtime >= src, f"{out} is newer than the markdown source")
    for i in range(1, 5):
        report((SD / "figures" / f"Figure{i}.png").exists(), f"Figure{i}.png exists")

    # 5) downloads package
    if args.downloads:
        for name in PACKAGE:
            report((args.downloads / name).exists(), f"package has {name}")

    # 6) S3 state (read-only)
    if not args.no_s3:
        rem = "s3:bdsp-opendata-repository/EEG/bids/Neurotech/"
        n = subprocess.run(["rclone", "cat", rem + "participants.tsv"], capture_output=True, text=True).stdout.count("\n") - 1
        report(n == 4912, f"S3 participants.tsv has {n} rows (expect 4912)")
        gone = True
        for s in ["sub-Neurotech934", "sub-Neurotech970", "sub-Neurotech1028"]:
            lst = subprocess.run(["rclone", "lsf", "-R", "--files-only", rem + s + "/"], capture_output=True, text=True).stdout
            if lst.strip():
                gone = False
        report(gone, "orphan-only subject directories removed from S3")
        js = subprocess.run(["rclone", "cat", rem + "sub-Neurotech1/ses-1/eeg/sub-Neurotech1_ses-1_task-EEG_eeg.json"],
                            capture_output=True, text=True).stdout
        report('"Manufacturer": "Lifelines/EMS"' in js, "sidecar Manufacturer is Lifelines/EMS")

    print("\nRELEASE GATE: " + ("READY" if ok else "NOT READY"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
