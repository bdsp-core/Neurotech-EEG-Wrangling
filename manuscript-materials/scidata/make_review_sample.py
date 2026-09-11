#!/usr/bin/env python3
"""Assemble a reviewer sample of the published release (download only; nothing is uploaded).

Scientific Data requires that reviewers can download a representative sample of a
controlled-access dataset anonymously and instantly. This script picks subjects that
span routine (<1 h), ambulatory (1-24 h), and multi-day (>24 h) segments while keeping
the total under a size cap, then copies their complete BIDS directories plus the
dataset-level files from S3 (rclone remote `s3`) into scidata/review_sample/ and zips it.

Where the zip is hosted for reviewers is a separate decision (see SUBMISSION_CHECKLIST.md).

Run:  .venv/bin/python manuscript-materials/scidata/make_review_sample.py --max-gb 3 --per-class 3
"""
from __future__ import annotations

import argparse
import csv
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / "output" / "s3_recordings.csv"
REMOTE = "s3:bdsp-opendata-repository/EEG/bids/Neurotech/"
OUT = Path(__file__).resolve().parent / "review_sample"
TOP = ["dataset_description.json", "README", "participants.tsv", "participants.json"]


def pick_subjects(max_gb: float, per_class: int) -> list[str]:
    by_subj = defaultdict(lambda: {"hours": [], "bytes": 0.0})
    with open(REC) as f:
        for r in csv.DictReader(f):
            if int(r.get("n_records", 0) or 0) <= 0:
                continue
            s = by_subj[r["subject"]]
            s["hours"].append(float(r.get("duration_hours") or 0))
            s["bytes"] += float(r.get("file_size_bytes") or r.get("size_bytes") or 0)
    classes = {"routine": [], "ambulatory": [], "multiday": []}
    for subj, s in by_subj.items():
        mx = max(s["hours"])
        cls = "routine" if mx < 1 else ("ambulatory" if mx <= 24 else "multiday")
        classes[cls].append((s["bytes"], subj))
    chosen, total = [], 0.0
    cap = max_gb * 1e9
    for cls, lst in classes.items():
        for b, subj in sorted(lst)[: per_class * 5]:  # smallest first, some headroom
            if len([c for c in chosen if c[0] == cls]) >= per_class:
                break
            if total + b > cap:
                continue
            chosen.append((cls, subj, b))
            total += b
    print(f"chosen {len(chosen)} subjects, ~{total/1e9:.2f} GB (size column may be absent; verify after download)")
    for cls, subj, b in chosen:
        print(f"  {cls:11s} {subj:20s} {b/1e6:8.1f} MB")
    return [subj for _, subj, _ in chosen]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-gb", type=float, default=3.0)
    ap.add_argument("--per-class", type=int, default=3)
    ap.add_argument("--zip", action="store_true", help="zip the sample after download")
    args = ap.parse_args()
    subjects = pick_subjects(args.max_gb, args.per_class)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in TOP:
        subprocess.run(["rclone", "copyto", REMOTE + name, str(OUT / name)], check=True)
    subprocess.run(["rclone", "copy", REMOTE + "phenotype/", str(OUT / "phenotype")], check=True)
    for subj in subjects:
        subprocess.run(["rclone", "copy", f"{REMOTE}{subj}/", str(OUT / subj), "--transfers", "8"], check=True)
        print("  downloaded", subj)
    (OUT / "REVIEWER_README.txt").write_text(
        "Reviewer sample of the Neurotech EEG Dataset (https://doi.org/10.60508/v99k-ek82).\n"
        "Verbatim subset of the published BIDS release: all dataset-level files, the full phenotype/ tables,\n"
        f"and the complete directories of {len(subjects)} subjects: {', '.join(subjects)}.\n")
    if args.zip:
        subprocess.run(["zip", "-r", "-q", str(OUT.with_suffix(".zip")), OUT.name], cwd=OUT.parent, check=True)
        print("zip:", OUT.with_suffix(".zip"))


if __name__ == "__main__":
    main()
