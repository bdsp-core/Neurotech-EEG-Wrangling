#!/usr/bin/env python3
"""Regenerate specific BIDS sessions that never reached S3, from the source export drive.

Reuses build_bids.py's own functions (de-identification, sidecars, annotation scrubbing) and its
session-numbering rule (ses = session_start + index in the name-sorted *.edf list of the source
folder), so the regenerated files carry exactly the keys the release already expects.

Safety: before converting anything for a subject, every session of that subject that IS already on
S3 is checked: the source EDF at the same index must have the same byte size as the published one
(sizes from output/s3_recordings.csv). A mismatch means the numbering would not line up, and the
subject is skipped and reported. Nothing is uploaded by this script; it prints the rclone command.

Usage:
  .venv/bin/python restore_missing_sessions.py --targets manuscript-materials/scidata/s3_audit_2026-09-10 \
      --linking output/linking_table_pending_eeg.csv [--linking output/linking_table.csv] \
      --drive /Volumes/Padlock_DT --out "/Volumes/Extreme SSD/neurotech-restore/Neurotech" [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import build_bids as bb  # noqa: E402


def load_targets(audit_dir: Path) -> dict[str, set[str]]:
    """{subject: {ses-N, ...}} from the audit lists: absent sessions + EDF-less sessions."""
    targets: dict[str, set[str]] = {}
    for name, only_edf in (("missing_edf_paths.txt", False), ("missing_sidecar_paths.txt", True)):
        for line in (audit_dir / name).read_text().splitlines():
            line = line.strip()
            if not line or (only_edf and not line.endswith("_eeg.edf")):
                continue
            m = re.match(r"(sub-Neurotech\d+)/(ses-\d+)/", line)
            targets.setdefault(m.group(1), set()).add(m.group(2))
    return targets


def load_linking(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in paths]
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["BDSPPatientID"], keep="first")
    return df


def published_sizes(csv_path: Path) -> dict[tuple[str, str], int]:
    out = {}
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            ses = r["session"] if r["session"].startswith("ses-") else "ses-" + r["session"]
            try:
                out[(r["subject"], ses)] = int(float(r["size_bytes"]))
            except (TypeError, ValueError):
                pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", type=Path, required=True, help="audit dir with missing_edf_paths.txt / missing_sidecar_paths.txt")
    ap.add_argument("--linking", type=Path, action="append", required=True)
    ap.add_argument("--drive", type=Path, default=bb.DRIVE_PATH)
    ap.add_argument("--out", type=Path, required=True, help="scratch BIDS root (…/Neurotech)")
    ap.add_argument("--recordings", type=Path, default=ROOT / "output" / "s3_recordings.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    targets = load_targets(args.targets)
    linking = load_linking(args.linking)
    linking = linking.set_index("BDSPPatientID")
    sizes = published_sizes(args.recordings)
    print(f"targets: {sum(len(v) for v in targets.values())} sessions in {len(targets)} subjects; linking rows: {len(linking)}")

    broad_names, per_folder_names = None, None
    if not args.dry_run:
        # name scrubber needs the linking table(s); build from the first that exists (all rows concatenated)
        tmp = args.out.parent / "_linking_concat.csv"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        linking.reset_index().to_csv(tmp, index=False)
        broad_names, per_folder_names = bb.build_name_scrubber(tmp)
        tmp.unlink()

    done, skipped = [], []
    for sub, sessions in sorted(targets.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]))):
        pid = "Neurotech-" + re.sub(r"\D", "", sub)
        if pid not in linking.index:
            skipped.append((sub, "no linking row"))
            continue
        row = linking.loc[pid]
        folder = args.drive / str(row["original_folder"])
        if not folder.exists():
            skipped.append((sub, "source folder not found on drive"))
            continue
        shift_days, session_start = int(row["shift_days"]), int(row["session_start"])
        edf_files = sorted(folder.glob("*.edf"), key=lambda p: p.name)
        lay_files = {p.stem: p for p in folder.glob("*.lay") if ".backup" not in p.name}

        # numbering check against every published session of this subject
        mismatch = []
        checked = 0
        for (s, ses), size in sizes.items():
            if s != sub or ses in sessions:
                continue
            idx = int(ses.split("-")[1]) - session_start
            if idx < 0 or idx >= len(edf_files):
                mismatch.append(f"{ses}: index {idx} out of range ({len(edf_files)} source EDFs)")
                continue
            src_size = edf_files[idx].stat().st_size
            if src_size != size:
                mismatch.append(f"{ses}: source {src_size} B vs published {size} B")
            checked += 1
        if mismatch:
            skipped.append((sub, f"numbering check failed ({len(mismatch)} of {checked + len(mismatch)}): {mismatch[:3]}"))
            continue

        for ses in sorted(sessions, key=lambda s: int(s.split("-")[1])):
            idx = int(ses.split("-")[1]) - session_start
            if idx < 0 or idx >= len(edf_files):
                skipped.append((f"{sub}/{ses}", f"index {idx} out of range ({len(edf_files)} source EDFs)"))
                continue
            edf_path = edf_files[idx]
            if edf_path.stat().st_size < 512:
                skipped.append((f"{sub}/{ses}", "source EDF < 512 B (builder skips these)"))
                continue
            if args.dry_run:
                done.append((f"{sub}/{ses}", edf_path.name, edf_path.stat().st_size))
                continue
            prefix = f"{sub}_{ses}_task-{bb.TASK_LABEL}"
            ses_dir = args.out / sub / ses
            eeg_dir = ses_dir / "eeg"
            eeg_dir.mkdir(parents=True, exist_ok=True)
            dst_edf = eeg_dir / f"{prefix}_eeg.edf"
            meta = bb.deidentify_and_copy_edf(edf_path, dst_edf, shift_days)
            if meta.get("error"):
                skipped.append((f"{sub}/{ses}", meta["error"]))
                if dst_edf.exists():
                    dst_edf.unlink()
                continue
            bb.write_eeg_json(eeg_dir / f"{prefix}_eeg.json", meta)
            bb.write_channels_tsv(eeg_dir / f"{prefix}_channels.tsv", meta["channels"])
            if edf_path.stem in lay_files:
                annotations = bb.parse_lay_file(lay_files[edf_path.stem])
                if annotations:
                    try:
                        sd = datetime.strptime(str(meta["shifted_date"]), "%Y-%m-%d")
                        h, mi, s = (int(x) for x in str(meta["starttime"]).split(":")[:3])
                        rec_start = sd.replace(hour=h, minute=mi, second=s)
                    except Exception:  # noqa: BLE001
                        rec_start = datetime(1985, 1, 1)
                    pfn = per_folder_names.get(str(row["original_folder"]), {})
                    bb.write_xltek_csv(eeg_dir / f"{prefix}_Xltek.csv", annotations, rec_start, shift_days=shift_days,
                                       broad_names=broad_names, patient_first=pfn.get("first", ""), patient_last=pfn.get("last", ""))
            acq = f"{meta.get('shifted_date', '1985-01-01')}T{meta.get('starttime', '00:00:00')}".replace(" ", "T")
            bb.write_scans_tsv(ses_dir / f"{sub}_{ses}_scans.tsv", f"{prefix}_eeg.edf", acq)
            done.append((f"{sub}/{ses}", edf_path.name, dst_edf.stat().st_size))
            print(f"  regenerated {sub}/{ses}  ({dst_edf.stat().st_size/1e6:.1f} MB)")

    print(f"\n{'would regenerate' if args.dry_run else 'regenerated'}: {len(done)} sessions, {sum(d[2] for d in done)/1e9:.2f} GB")
    for s in skipped:
        print("  SKIPPED", *s)
    if not args.dry_run and done:
        print(f"\nupload (adds files only):\n  rclone copy \"{args.out}\" s3:bdsp-opendata-repository/EEG/bids/Neurotech/ --ignore-existing --transfers 8 -P")


if __name__ == "__main__":
    main()
