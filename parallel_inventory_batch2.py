"""
Parallel, resumable inventory of the batch-2 (~H->Z) drive.

- Reuses extract_inventory.process_folder UNCHANGED (identical output semantics
  to the A-H run), but fans folders across a process pool because the per-folder
  stat() sweep over USB is ~20s/folder serially (~23h for 3,653 folders).
- Writes to output/batch2_IZ/ (never the A-H files).
- Resumable: a done-set (done.txt) lets a re-run skip completed folders after a
  USB disconnect / crash. Checkpoints CSVs every CHECKPOINT_EVERY folders.

Run:    .venv/bin/python parallel_inventory_batch2.py [N_WORKERS]
Resume: just run it again; completed folders are skipped.
"""
import os
import sys
import time
import traceback
from pathlib import Path
from multiprocessing import Pool

import pandas as pd
import extract_inventory as ei

DRIVE = Path("/Volumes/Padlock_DT")
OUT = Path(__file__).resolve().parent / "output" / "batch2_IZ"
CHECKPOINT_EVERY = 200
N_WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 8


def list_folders():
    items = sorted(DRIVE.iterdir())
    return [p for p in items
            if p.is_dir() and not p.name.startswith("$") and not p.name.startswith(".")]


def process_one(folder_path_str):
    folder = Path(folder_path_str)
    try:
        recs, anns, pat = ei.process_folder(folder, folder.name)
        return {"folder": folder.name, "recs": recs, "anns": anns, "pat": pat, "error": ""}
    except Exception as e:
        return {"folder": folder.name, "recs": [], "anns": [], "pat": None,
                "error": str(e), "trace": traceback.format_exc()}


def load_done():
    f = OUT / "done.txt"
    if f.exists():
        return set(f.read_text().splitlines())
    return set()


def write_checkpoint(recs, anns, pats, errs):
    if recs:
        pd.DataFrame(recs).to_csv(OUT / "recordings.csv", index=False)
    if anns:
        pd.DataFrame(anns).to_csv(OUT / "annotations.csv", index=False)
    if pats:
        pd.DataFrame(pats).to_csv(OUT / "patients.csv", index=False)
    if errs:
        pd.DataFrame(errs).to_csv(OUT / "errors.csv", index=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_folders = list_folders()
    done = load_done()
    todo = [str(p) for p in all_folders if p.name not in done]
    print(f"Total folders: {len(all_folders)}  already done: {len(done)}  to do: {len(todo)}", flush=True)
    print(f"Workers: {N_WORKERS}  output: {OUT}", flush=True)

    # Load any existing partial results so checkpoints stay cumulative on resume.
    def _load(name):
        p = OUT / name
        return pd.read_csv(p).to_dict("records") if p.exists() else []
    recs_all = _load("recordings.csv")
    anns_all = _load("annotations.csv")
    pats_all = _load("patients.csv")
    errs_all = _load("errors.csv")

    done_fh = open(OUT / "done.txt", "a")
    t0 = time.time()
    n = 0
    with Pool(N_WORKERS) as pool:
        for r in pool.imap_unordered(process_one, todo, chunksize=1):
            n += 1
            recs_all.extend(r["recs"])
            anns_all.extend(r["anns"])
            if r["pat"] is not None:
                pats_all.append(r["pat"])
            if r["error"]:
                errs_all.append({"folder": r["folder"], "error": r["error"],
                                 "trace": r.get("trace", "")})
            done_fh.write(r["folder"] + "\n")

            if n % 25 == 0 or n == 1:
                el = time.time() - t0
                rate = n / el if el else 0
                rem = (len(todo) - n) / rate if rate else 0
                done_fh.flush()
                print(f"  [{n}/{len(todo)}] {el:.0f}s elapsed, ~{rem/60:.1f}min left, "
                      f"{rate*60:.1f} folders/min :: {r['folder'][:40]}", flush=True)
            if n % CHECKPOINT_EVERY == 0:
                write_checkpoint(recs_all, anns_all, pats_all, errs_all)
                print(f"  -- checkpoint at {n} (recs={len(recs_all)} anns={len(anns_all)})", flush=True)

    done_fh.close()
    write_checkpoint(recs_all, anns_all, pats_all, errs_all)
    el = time.time() - t0
    print(f"\n--- DONE ---\nProcessed {n} new folders in {el/60:.1f}min  "
          f"recordings={len(recs_all)} annotations={len(anns_all)} "
          f"patients={len(pats_all)} errors={len(errs_all)}", flush=True)


if __name__ == "__main__":
    main()
