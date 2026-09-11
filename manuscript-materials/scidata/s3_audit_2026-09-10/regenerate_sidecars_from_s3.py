#!/usr/bin/env python3
"""Rebuild missing BIDS sidecars (_eeg.json, _channels.tsv, _scans.tsv) for sessions whose
de-identified EDF is already on S3, using only the EDF header (fetched with `rclone cat --count`).

The sidecars are produced with the same helper functions build_bids.py uses, from the same
header fields edfio would expose, so they match the rest of the release. Output is staged
locally under ./staged/ mirroring the S3 layout; upload with:

  rclone copy staged/ s3:bdsp-opendata-repository/EEG/bids/Neurotech/ -P

Run:  .venv/bin/python manuscript-materials/scidata/s3_audit_2026-09-10/regenerate_sidecars_from_s3.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
import build_bids as bb  # noqa: E402

REMOTE = "s3:bdsp-opendata-repository/EEG/bids/Neurotech/"
STAGED = HERE / "staged"


def fetch(path: str, n: int) -> bytes:
    return subprocess.run(["rclone", "cat", "--count", str(n), REMOTE + path], capture_output=True, check=True).stdout


def parse_header(path: str) -> dict:
    h = fetch(path, 256)
    ns = int(h[252:256])
    full = fetch(path, 256 + 256 * ns)
    f = lambda a, b: full[a:b].decode("latin1")  # noqa: E731
    startdate, starttime = f(168, 176), f(176, 184)
    n_records, rec_dur = int(f(236, 244)), float(f(244, 252))
    o = 256
    labels = [f(o + 16 * i, o + 16 * (i + 1)).strip() for i in range(ns)]
    o += ns * (16 + 80 + 8 + 8 + 8 + 8 + 8 + 80)
    nsamp = [int(f(o + 8 * i, o + 8 * (i + 1))) for i in range(ns)]
    # 4-digit year from the recording field ("Startdate DD-MMM-YYYY ..."), else EDF 2-digit rule
    m = re.search(r"Startdate (\d{2})-([A-Z]{3})-(\d{4})", f(88, 168))
    if m:
        sd = datetime.strptime(f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "%d-%b-%Y").date()
    else:
        d, mo, y = (int(x) for x in startdate.split("."))
        sd = date(1900 + y if y >= 85 else 2000 + y, mo, d)
    st = starttime.replace(".", ":")
    return {"ns": ns, "labels": labels, "nsamp": nsamp, "n_records": n_records, "rec_dur": rec_dur,
            "startdate": sd, "starttime": st}


def metadata_from_header(hd: dict) -> dict:
    channels, counts = [], {"EEG": 0, "ECG": 0, "EOG": 0, "EMG": 0, "MISC": 0}
    for label, nsamp in zip(hd["labels"], hd["nsamp"]):
        ch_type = bb.classify_channel(label)
        if ch_type == "ANNO":
            continue
        sr = nsamp / hd["rec_dur"] if hd["rec_dur"] else 0.0
        channels.append({
            "name": label[4:] if label.startswith("EEG ") else label, "type": ch_type, "units": "uV",
            "low_cutoff": 0.0, "high_cutoff": sr / 2.0, "description": bb.channel_description(ch_type),
            "sampling_frequency": sr, "status": "good", "status_description": "n/a",
        })
        counts[ch_type if ch_type in counts else "MISC"] += 1
    n_rec = max(hd["n_records"], 0)
    return {
        "duration_sec": n_rec * hd["rec_dur"], "eeg_count": counts["EEG"], "ecg_count": counts["ECG"],
        "eog_count": counts["EOG"], "emg_count": counts["EMG"], "misc_count": counts["MISC"],
        "primary_sample_rate": channels[0]["sampling_frequency"] if channels else 256.0, "channels": channels,
        "shifted_date": str(hd["startdate"]), "starttime": hd["starttime"],
    }


def main():
    wanted = [l.strip() for l in (HERE / "missing_sidecar_paths.txt").read_text().splitlines() if l.strip()]
    sessions = {}
    for p in wanted:
        m = re.match(r"(sub-Neurotech\d+)/(ses-\d+)/", p)
        sessions.setdefault((m.group(1), m.group(2)), []).append(p)
    made, skipped = [], []
    for (sub, ses), paths in sorted(sessions.items()):
        if any(p.endswith("_eeg.edf") for p in paths):
            skipped.append((sub, ses, "EDF itself is missing; needs the source drive"))
            continue
        edf_rel = f"{sub}/{ses}/eeg/{sub}_{ses}_task-EEG_eeg.edf"
        try:
            hd = parse_header(edf_rel)
        except Exception as e:  # noqa: BLE001
            skipped.append((sub, ses, f"header unreadable: {e}"))
            continue
        meta = metadata_from_header(hd)
        prefix = f"{sub}_{ses}_task-EEG"
        eeg_dir = STAGED / sub / ses / "eeg"
        eeg_dir.mkdir(parents=True, exist_ok=True)
        for p in paths:
            if p.endswith("_eeg.json"):
                bb.write_eeg_json(eeg_dir / f"{prefix}_eeg.json", meta)
            elif p.endswith("_channels.tsv"):
                bb.write_channels_tsv(eeg_dir / f"{prefix}_channels.tsv", meta["channels"])
            elif p.endswith("_scans.tsv"):
                bb.write_scans_tsv(STAGED / sub / ses / f"{sub}_{ses}_scans.tsv", f"{prefix}_eeg.edf",
                                   f"{meta['shifted_date']}T{meta['starttime']}")
            made.append(p)
        print(f"  {sub}/{ses}: ns={hd['ns']} n_records={hd['n_records']} dur={meta['duration_sec']:.0f}s "
              f"start={meta['shifted_date']}T{meta['starttime']} -> {[Path(p).name.split('_task-EEG_')[-1] if '_task-EEG_' in p else 'scans.tsv' for p in paths]}")
    print(f"\nstaged {len(made)} files under {STAGED}")
    for s in skipped:
        print("  skipped", *s)


if __name__ == "__main__":
    main()
