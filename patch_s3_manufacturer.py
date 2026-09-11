#!/usr/bin/env python3
"""Patch the `Manufacturer` field in every published `*_eeg.json` sidecar on S3.

The published BIDS release (s3://bdsp-opendata-repository/EEG/bids/Neurotech/) was
built when build_bids.py hard-coded "Natus/Xltek". The provider confirmed the
recordings come from Lifelines or EMS ambulatory equipment, and build_bids.py now
writes "Lifelines/EMS". This script brings the already-published sidecars in line.

Credentials are read from the local rclone config (remote `s3`), so no keys are
stored here. Objects are rewritten in place with the same formatting build_bids.py
uses (indent=4 + trailing newline). Sidecars that already carry the new value are
left untouched, so the script is idempotent.

Usage:
  .venv/bin/python patch_s3_manufacturer.py --list sidecars.txt --dry-run --limit 5
  .venv/bin/python patch_s3_manufacturer.py --list sidecars.txt --limit 1        # real, one file
  .venv/bin/python patch_s3_manufacturer.py --list sidecars.txt                  # all
  .venv/bin/python patch_s3_manufacturer.py --list sidecars.txt --verify 200     # sample check
"""
from __future__ import annotations

import argparse
import configparser
import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from botocore.config import Config

BUCKET = "bdsp-opendata-repository"
PREFIX = "EEG/bids/Neurotech/"
OLD = "Natus/Xltek"
NEW = "Lifelines/EMS"


def s3_client():
    cfg = configparser.ConfigParser()
    cfg.read(Path.home() / ".config" / "rclone" / "rclone.conf")
    s = cfg["s3"]
    return boto3.client(
        "s3",
        aws_access_key_id=s["access_key_id"],
        aws_secret_access_key=s["secret_access_key"],
        region_name=s.get("region", "us-east-1"),
        config=Config(max_pool_connections=64, retries={"max_attempts": 8, "mode": "adaptive"}),
    )


def patch_one(client, key: str, dry_run: bool) -> tuple[str, str]:
    obj = client.get_object(Bucket=BUCKET, Key=key)
    raw = obj["Body"].read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return key, f"SKIP invalid-json ({e})"
    cur = data.get("Manufacturer")
    if cur == NEW:
        return key, "already"
    if cur != OLD:
        return key, f"SKIP unexpected Manufacturer={cur!r}"
    data["Manufacturer"] = NEW
    body = (json.dumps(data, indent=4) + "\n").encode()
    if dry_run:
        return key, "would-patch"
    client.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType="application/json")
    return key, "patched"


def verify_one(client, key: str) -> tuple[str, str]:
    obj = client.get_object(Bucket=BUCKET, Key=key)
    data = json.loads(obj["Body"].read())
    return key, data.get("Manufacturer")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True, help="file with one sidecar path per line, relative to the Neurotech/ prefix")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=32)
    ap.add_argument("--verify", type=int, default=0, help="instead of patching, re-read N random sidecars and report Manufacturer values")
    ap.add_argument("--log", default="patch_s3_manufacturer.log")
    args = ap.parse_args()

    keys = [PREFIX + line.strip() for line in Path(args.list).read_text().splitlines() if line.strip()]
    if args.limit:
        keys = keys[: args.limit]
    client = s3_client()

    if args.verify:
        sample = random.sample(keys, min(args.verify, len(keys)))
        counts: dict[str, int] = {}
        with ThreadPoolExecutor(args.workers) as ex:
            for fut in as_completed([ex.submit(verify_one, client, k) for k in sample]):
                _, val = fut.result()
                counts[val] = counts.get(val, 0) + 1
        print(f"verified {len(sample)} random sidecars: {counts}")
        return

    t0 = time.time()
    counts = {"patched": 0, "would-patch": 0, "already": 0, "skip": 0, "error": 0}
    with open(args.log, "a") as log, ThreadPoolExecutor(args.workers) as ex:
        futs = {ex.submit(patch_one, client, k, args.dry_run): k for k in keys}
        for i, fut in enumerate(as_completed(futs), 1):
            k = futs[fut]
            try:
                _, status = fut.result()
            except Exception as e:  # noqa: BLE001
                status = f"ERROR {e}"
            if status.startswith("SKIP"):
                counts["skip"] += 1
            elif status.startswith("ERROR"):
                counts["error"] += 1
            else:
                counts[status] += 1
            if status not in ("patched", "already", "would-patch"):
                log.write(f"{k}\t{status}\n")
            if i % 2000 == 0 or i == len(keys):
                el = time.time() - t0
                print(f"{i}/{len(keys)}  {counts}  {el:.0f}s", flush=True)
    print("done", counts, f"{time.time()-t0:.0f}s")
    if counts["error"] or counts["skip"]:
        print(f"see {args.log} for skipped/errored keys")
        sys.exit(1)


if __name__ == "__main__":
    main()
