#!/usr/bin/env python3
"""Local half of the Manufacturer fix (rclone-based alternative to patch_s3_manufacturer.py).

  1. rclone copy s3:.../Neurotech/ <orig>/ --files-from output/s3_eeg_json_sidecars.txt --no-traverse
  2. python patch_sidecars_local.py <orig> <patched>        # this script
  3. rclone copy <patched>/ s3:.../Neurotech/ --no-traverse --transfers 64
  4. python patch_s3_manufacturer.py --list output/s3_eeg_json_sidecars.txt --verify 300   (read-only)

Writes a patched copy (same relative path, same formatting as build_bids.write_eeg_json:
indent=4 + trailing newline) only for sidecars whose Manufacturer is "Natus/Xltek".
"""
import json
import sys
from pathlib import Path

OLD, NEW = "Natus/Xltek", "Lifelines/EMS"


def main(orig: Path, patched: Path):
    n = {"patched": 0, "already": 0, "other": 0, "bad": 0}
    for src in orig.rglob("*_eeg.json"):
        try:
            data = json.loads(src.read_text())
        except json.JSONDecodeError:
            n["bad"] += 1
            print("BAD JSON", src.relative_to(orig))
            continue
        cur = data.get("Manufacturer")
        if cur == NEW:
            n["already"] += 1
            continue
        if cur != OLD:
            n["other"] += 1
            print("UNEXPECTED", src.relative_to(orig), repr(cur))
            continue
        data["Manufacturer"] = NEW
        dst = patched / src.relative_to(orig)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(data, indent=4) + "\n")
        n["patched"] += 1
    print(n)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
