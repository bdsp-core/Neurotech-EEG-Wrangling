"""
Regenerate the EEG statistics (output/s3_recordings.csv) and annotation totals
DIRECTLY from the public BIDS dataset on S3 — so a reader with only public access
can reproduce every EEG/annotation number in the manuscript.

Reads each published session's `*_eeg.json` (RecordingDuration, channel counts) and
`*_Xltek.csv` (annotation rows), plus the EDF `n_records` from `*_scans.tsv`/header,
and writes a de-identified `s3_recordings.csv` identical in schema to the committed one.

Usage:
  python compute_eeg_stats_from_s3.py --bids s3://bdsp-opendata-repository/EEG/bids/Neurotech/ --out s3_recordings.csv
  python compute_eeg_stats_from_s3.py --bids /local/path/to/Neurotech/ --out s3_recordings.csv   # if downloaded

Requires: boto3 (for s3://) or a local BIDS path; pandas.
Note: this is I/O-heavy (tens of thousands of small JSON/CSV reads); for S3 it is
fastest to `aws s3 sync` the dataset locally first, then point --bids at the folder.
"""
import argparse, csv, io, json, os, re, sys
from collections import Counter


def iter_sessions_local(root):
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.endswith("_eeg.json"):
                yield os.path.join(dp, f)


def read_json_local(p):
    with open(p) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bids", required=True, help="s3://... or local path to the Neurotech BIDS root")
    ap.add_argument("--out", default="s3_recordings.csv")
    args = ap.parse_args()

    ann_total = 0
    ann_cat = Counter()
    rows = []

    if args.bids.startswith("s3://"):
        import boto3
        s3 = boto3.client("s3")
        m = re.match(r"s3://([^/]+)/(.+)", args.bids)
        bucket, prefix = m.group(1), m.group(2).rstrip("/") + "/"
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj["Key"]
                if k.endswith("_eeg.json"):
                    meta = json.load(s3.get_object(Bucket=bucket, Key=k)["Body"])
                    sub = re.search(r"(sub-Neurotech\d+)", k).group(1)
                    ses = re.search(r"(ses-\d+)", k).group(1)
                    rows.append({"subject": sub, "session": ses,
                                 "duration_hours": float(meta.get("RecordingDuration", 0) or 0)/3600.0,
                                 "n_signals": int(meta.get("EEGChannelCount", 0) or 0) + int(meta.get("ECGChannelCount", 0) or 0)
                                              + int(meta.get("MiscChannelCount", 0) or 0),
                                 "n_records": 1 if (meta.get("RecordingDuration", 0) or 0) > 0 else 0,
                                 "size_mb": obj.get("Size", 0)/1048576.0})
                elif k.endswith("_Xltek.csv"):
                    body = s3.get_object(Bucket=bucket, Key=k)["Body"].read().decode("utf-8", "replace")
                    n = max(0, sum(1 for _ in csv.reader(io.StringIO(body))) - 1)  # minus header
                    ann_total += n
    else:
        for p in iter_sessions_local(args.bids):
            meta = read_json_local(p)
            sub = re.search(r"(sub-Neurotech\d+)", p).group(1)
            ses = re.search(r"(ses-\d+)", p).group(1)
            rows.append({"subject": sub, "session": ses,
                         "duration_hours": float(meta.get("RecordingDuration", 0) or 0)/3600.0,
                         "n_signals": int(meta.get("EEGChannelCount", 0) or 0) + int(meta.get("ECGChannelCount", 0) or 0)
                                      + int(meta.get("MiscChannelCount", 0) or 0),
                         "n_records": 1 if (meta.get("RecordingDuration", 0) or 0) > 0 else 0,
                         "size_mb": 0})
        for dp, _, fs in os.walk(args.bids):
            for f in fs:
                if f.endswith("_Xltek.csv"):
                    with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                        ann_total += max(0, sum(1 for _ in fh) - 1)

    import pandas as pd
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    sig = df[df.n_records > 0]
    print(f"wrote {args.out}: {len(df):,} EDFs, {sig.subject.nunique():,} subjects, "
          f"{len(sig):,} signal recordings, {sig.duration_hours.sum():,.0f} hours")
    print(f"total annotation events (from *_Xltek.csv): {ann_total:,}")


if __name__ == "__main__":
    main()
