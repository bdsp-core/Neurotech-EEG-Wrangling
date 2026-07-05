"""
Fast, parallel, resumable inventory of the batch-2 (~H->Z) drive.

Why this exists: extract_inventory.process_folder stat()s EVERY file in each
folder to compute total_size_mb. Monitoring folders hold tens of thousands of
tiny Persyst .raw/.ar trend files, so that stat sweep is ~10-20s/folder over the
encrypted USB HDD (~10h for 3,652 folders). Here we do ONE scandir pass and
stat ONLY the files whose size we actually want (.edf + video). The .raw/.ar/
.vinfo bulk is counted by name, never stat'd.

Outputs (to output/batch2_IZ/, never the A-H files):
  recordings.csv   - one row per EDF (same schema as A-H run; via ei.read_edf_header)
  annotations.csv  - one row per .lay / EDF-embedded annotation (same as A-H)
  patients.csv     - per-folder summary PLUS a video manifest:
                     video_files, video_gb, audio_files, edf_gb (video excluded
                     from BIDS/S3, but tallied per the user's decision).

Resumable: done.txt lets a re-run skip completed folders after a USB drop.
Run:    .venv/bin/python fast_inventory_batch2.py [N_WORKERS]
Test:   NT_LIMIT=25 .venv/bin/python fast_inventory_batch2.py 8
"""
import os
import sys
import time
import traceback
from pathlib import Path
from collections import Counter
from multiprocessing import Pool

import pandas as pd
import extract_inventory as ei

DRIVE = Path("/Volumes/Padlock_DT")
OUT = Path(__file__).resolve().parent / "output" / "batch2_IZ"
CHECKPOINT_EVERY = 200
N_WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 8

VIDEO_EXTS = {".asf", ".avi", ".mp4", ".mov", ".m4v", ".wmv", ".mpg", ".mpeg",
              ".mts", ".m2ts", ".vob", ".mkv", ".flv"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a"}

# EDF embedded annotations in this dataset are ~63% junk ("Serial number : 0000")
# and reading them (pyedflib.readAnnotations scans the annotation channel across
# every data record) is the dominant cost on large EDFs over USB. Clinical
# annotations come from .lay files. Set NT_SKIP_EDF_ANN=1 to skip the scan.
SKIP_EDF_ANN = bool(os.environ.get("NT_SKIP_EDF_ANN"))

import pyedflib


def read_edf_header_light(edf_path):
    """EDF header metadata WITHOUT readAnnotations (much faster on large files)."""
    try:
        f = pyedflib.EdfReader(str(edf_path))
    except Exception as e:
        return {"error": str(e)}
    try:
        header = f.getHeader()
        n = f.signals_in_file
        labels = [f.getLabel(i) for i in range(n)]
        srates = [f.getSampleFrequency(i) for i in range(n)]
        dur = f.file_duration
        return {
            "patient_name": header.get("patientname", ""), "patient_id": header.get("patientcode", ""),
            "gender": header.get("gender", ""), "birthdate": str(header.get("birthdate", "")),
            "startdate": str(header.get("startdate", "")), "starttime": str(header.get("starttime", "")),
            "recording_additional": header.get("recording_additional", ""),
            "patient_additional": header.get("patient_additional", ""),
            "technician": header.get("technician", ""), "equipment": header.get("equipment", ""),
            "filetype": header.get("filetype", ""), "n_channels": n,
            "n_data_records": f.datarecords_in_file, "duration_sec": dur,
            "duration_hours": round(dur / 3600, 2), "channel_labels": "|".join(labels),
            "sample_rates": "|".join(str(int(s)) for s in srates),
            "primary_sample_rate": int(max(set(srates), key=srates.count)) if srates else 0,
            "n_edf_annotations": 0, "edf_annotations": [], "error": "",
        }
    finally:
        f.close()


def fast_process_folder(folder: Path, folder_name: str):
    """Like ei.process_folder but stats only EDF + video/audio files."""
    patient_info = ei.parse_folder_name(folder_name)

    type_counts = Counter()
    edf_paths, lay_paths = [], []
    video_files = video_bytes = audio_files = audio_bytes = 0
    edf_bytes = 0
    n_total = 0

    with os.scandir(folder) as it:
        for ent in it:
            n_total += 1
            name = ent.name
            ext = os.path.splitext(name)[1].lower() or "(none)"
            # collapse persyst trend chunks like the original did
            key = ".mg2_trend" if (".mg2." in name and ext in (".raw", ".ar")) else ext
            type_counts[key] += 1

            if ext == ".edf":
                edf_paths.append(Path(ent.path))
                try:
                    edf_bytes += ent.stat().st_size
                except OSError:
                    pass
            elif ext == ".lay" and ".backup" not in name:
                lay_paths.append(Path(ent.path))
            elif ext in VIDEO_EXTS:
                video_files += 1
                try:
                    video_bytes += ent.stat().st_size
                except OSError:
                    pass
            elif ext in AUDIO_EXTS:
                audio_files += 1
                try:
                    audio_bytes += ent.stat().st_size
                except OSError:
                    pass

    recordings, annotations = [], []

    for edf_path in sorted(edf_paths):
        try:
            sz = edf_path.stat().st_size
        except OSError:
            sz = 0
        header = read_edf_header_light(edf_path) if SKIP_EDF_ANN else ei.read_edf_header(edf_path)
        edf_anns = header.pop("edf_annotations", [])
        recordings.append({
            "folder_name": folder_name,
            "edf_filename": edf_path.name,
            "edf_size_mb": round(sz / 1048576, 1),
            **patient_info,
            **header,
        })
        for ann in edf_anns:
            if ann["text"].strip():
                annotations.append({
                    "folder_name": folder_name, "source_file": edf_path.name,
                    "source_type": "edf_embedded", "case_id": patient_info["case_id"],
                    "onset_sec": ann["onset_sec"], "duration_sec": ann["duration_sec"],
                    "text": ann["text"], "category": ei.classify_annotation(ann["text"]),
                    "lateralization": ei.extract_lateralization(ann["text"]),
                })

    for lay_path in sorted(lay_paths):
        for ann in ei.parse_lay_file(lay_path):
            annotations.append({
                "folder_name": folder_name, "source_file": lay_path.name,
                "source_type": "lay_file", "matched_edf": f"{lay_path.stem}.edf",
                "case_id": patient_info["case_id"],
                "onset_sec": ann["onset_sec"], "duration_sec": ann["duration_sec"],
                "text": ann["text"], "category": ei.classify_annotation(ann["text"]),
                "lateralization": ei.extract_lateralization(ann["text"]),
            })

    patient = {
        "folder_name": folder_name, **patient_info,
        "n_edf_files": len(edf_paths), "n_lay_files": len(lay_paths),
        "n_lay_annotations": sum(1 for a in annotations if a.get("source_type") == "lay_file"),
        "n_edf_annotations": sum(1 for a in annotations if a.get("source_type") == "edf_embedded"),
        "edf_gb": round(edf_bytes / 1e9, 3),
        "video_files": video_files, "video_gb": round(video_bytes / 1e9, 3),
        "audio_files": audio_files,
        "n_total_files": n_total,
        "file_types": str(dict(type_counts)),
    }
    return recordings, annotations, patient


def process_one(folder_path_str):
    folder = Path(folder_path_str)
    try:
        recs, anns, pat = fast_process_folder(folder, folder.name)
        return {"folder": folder.name, "recs": recs, "anns": anns, "pat": pat, "error": ""}
    except Exception as e:
        return {"folder": folder.name, "recs": [], "anns": [], "pat": None,
                "error": str(e), "trace": traceback.format_exc()}


def list_folders():
    items = sorted(DRIVE.iterdir())
    return [p for p in items
            if p.is_dir() and not p.name.startswith("$") and not p.name.startswith(".")]


def load_done():
    f = OUT / "done.txt"
    return set(f.read_text().splitlines()) if f.exists() else set()


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
    limit = os.environ.get("NT_LIMIT")
    if limit:
        todo = todo[: int(limit)]
    print(f"Total: {len(all_folders)}  done: {len(done)}  todo: {len(todo)}  workers: {N_WORKERS}", flush=True)

    def _load(name):
        p = OUT / name
        return pd.read_csv(p).to_dict("records") if p.exists() else []
    recs_all, anns_all, pats_all, errs_all = (_load("recordings.csv"), _load("annotations.csv"),
                                              _load("patients.csv"), _load("errors.csv"))

    done_fh = open(OUT / "done.txt", "a")
    t0 = time.time(); n = 0
    with Pool(N_WORKERS) as pool:
        for r in pool.imap_unordered(process_one, todo, chunksize=1):
            n += 1
            recs_all.extend(r["recs"]); anns_all.extend(r["anns"])
            if r["pat"] is not None:
                pats_all.append(r["pat"])
            if r["error"]:
                errs_all.append({"folder": r["folder"], "error": r["error"], "trace": r.get("trace", "")})
            done_fh.write(r["folder"] + "\n")
            if n % 25 == 0 or n == 1:
                el = time.time() - t0; rate = n / el if el else 0
                rem = (len(todo) - n) / rate if rate else 0
                done_fh.flush()
                print(f"  [{n}/{len(todo)}] {el:.0f}s, ~{rem/60:.1f}min left, "
                      f"{rate*60:.1f} fld/min :: {r['folder'][:38]}", flush=True)
            if n % CHECKPOINT_EVERY == 0:
                write_checkpoint(recs_all, anns_all, pats_all, errs_all)
                print(f"  -- checkpoint {n} (recs={len(recs_all)} anns={len(anns_all)})", flush=True)
    done_fh.close()
    write_checkpoint(recs_all, anns_all, pats_all, errs_all)
    el = time.time() - t0
    print(f"\n--- DONE --- {n} folders in {el/60:.1f}min | recs={len(recs_all)} "
          f"anns={len(anns_all)} pats={len(pats_all)} errs={len(errs_all)}", flush=True)


if __name__ == "__main__":
    main()
