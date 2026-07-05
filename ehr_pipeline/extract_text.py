#!/usr/bin/env python3
"""
Stage 1 of the EHR extraction pipeline: raw text extraction.

For each PDF under SRC_ROOT:
  1. Run `pdftotext -layout` to get layout-preserved text.
  2. If text density is low enough to suggest image pages, run
     `ocrmypdf --skip-text` to add a text layer, then re-extract.
  3. Write per-PDF outputs:
       <out>/patients/<patient_folder>/<pdf_stem>/raw.txt    (form-feed separated)
       <out>/patients/<patient_folder>/<pdf_stem>/raw.jsonl  (one page per line)
       <out>/patients/<patient_folder>/<pdf_stem>/meta.json
  4. Append a row to output/ehr/manifest.tsv.

Re-runs are idempotent: files whose sha1 is unchanged and whose status is "ok"
are skipped unless --reprocess is passed.

Usage:
  python ehr_pipeline/extract_text.py --limit 50
  python ehr_pipeline/extract_text.py --only-patient "Ab*"
  python ehr_pipeline/extract_text.py --reprocess --only-patient "Abbas*"
  python ehr_pipeline/extract_text.py --dry-run
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Iterator, Optional

# Allow running this file directly (python ehr_pipeline/extract_text.py) OR as a module
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from progress import ProgressTracker  # type: ignore
else:
    from .progress import ProgressTracker

# ---------------------------------------------------------------------------
# Paths and policy
# ---------------------------------------------------------------------------

# Derived artifacts (raw.txt / raw.jsonl / meta.json) are written next to the
# source PDF: for <patient>/Patient Forms/Foo.pdf we create Foo.raw.txt, etc.
# Only the cross-corpus manifest + log live under STATE_DIR.
SRC_ROOT = Path("/Volumes/Extreme SSD/neurotech-data")
STATE_DIR = Path("/Users/mbwest/Desktop/GithubRepos/neurotech_wrangling/output/ehr")
MANIFEST_PATH = STATE_DIR / "manifest.tsv"
LOG_PATH = STATE_DIR / "extract_text.log"

# Suffixes we write alongside each source PDF (used both for writing and cleanup)
DERIVED_SUFFIXES = (".raw.txt", ".raw.jsonl", ".meta.json")

# OCR trigger: if the average chars-per-page is below this, we assume most pages
# are images and run ocrmypdf. `--skip-text` then OCRs only image pages.
OCR_AVG_CPP_THRESHOLD = 50

# Also trigger OCR if more than this fraction of pages have near-zero text
OCR_EMPTY_PAGE_FRACTION = 0.5
OCR_EMPTY_PAGE_CHARS = 20

SHA1_CHUNK = 1 << 20  # 1 MB

MANIFEST_COLUMNS = [
    "sha1",
    "src_path",
    "src_bytes",
    "src_mtime",
    "pages",
    "total_chars",
    "chars_per_page",
    "ocr_applied",
    "status",
    "error",
    "out_dir",
    "processed_at",
]

PIPELINE_VERSION = "0.1"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------------------
# Shell helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kwargs)


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(SHA1_CHUNK)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# PDF operations
# ---------------------------------------------------------------------------

def pdf_page_count(pdf: Path) -> int:
    res = run(["pdfinfo", str(pdf)])
    if res.returncode != 0:
        return 0
    for line in res.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


def pdftotext_layout(pdf: Path) -> str:
    """Run `pdftotext -layout` and return all pages concatenated (form-feed separated)."""
    res = run(["pdftotext", "-layout", "-q", str(pdf), "-"])
    return res.stdout or ""


def split_pages(full_text: str) -> list[str]:
    """Split pdftotext output on form-feed (\\x0c) into per-page strings."""
    if not full_text:
        return []
    pages = full_text.split("\x0c")
    if pages and pages[-1] == "":
        pages.pop()
    return pages


def should_ocr(pages_text: list[str], n_pages: int) -> bool:
    if n_pages == 0:
        return False
    total = sum(len(p) for p in pages_text)
    avg = total / n_pages
    if avg < OCR_AVG_CPP_THRESHOLD:
        return True
    empty = sum(1 for p in pages_text if len(p) < OCR_EMPTY_PAGE_CHARS)
    if empty / n_pages > OCR_EMPTY_PAGE_FRACTION:
        return True
    return False


def run_ocrmypdf(src: Path, dst: Path, jobs: int = 1) -> None:
    """OCR image pages in `src`, write result to `dst`. Leaves existing text alone."""
    cmd = [
        "ocrmypdf",
        "--skip-text",          # leave pages that already have a text layer alone
        "--rotate-pages",       # auto-detect and correct page rotation
        "--deskew",             # straighten skewed scans
        "--optimize", "0",      # speed > size
        "--tesseract-oem", "1", # LSTM engine only (fastest)
        "--jobs", str(jobs),    # ocrmypdf-internal parallelism
        "--language", "eng",
        "--output-type", "pdf",
        "--quiet",
        str(src),
        str(dst),
    ]
    res = run(cmd)
    if res.returncode != 0:
        raise RuntimeError(
            f"ocrmypdf rc={res.returncode}: {(res.stderr or '').strip()[:500]}"
        )


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

_SAFE_RE = re.compile(r"[/\\:]")


def safe_name(name: str) -> str:
    return _SAFE_RE.sub("_", name).strip()


def iter_source_pdfs(
    src_root: Path, only_patient: Optional[str] = None
) -> Iterator[tuple[str, Path]]:
    """Yield (patient_folder_name, pdf_path) pairs."""
    if not src_root.exists():
        return
    for patient_dir in sorted(src_root.iterdir()):
        if not patient_dir.is_dir() or patient_dir.name.startswith("."):
            continue
        if only_patient and not fnmatch.fnmatch(patient_dir.name, only_patient):
            continue
        for pdf in sorted(patient_dir.rglob("*.pdf")):
            # skip any hidden files/dirs inside, and our own OCR temp files
            rel_parts = pdf.relative_to(patient_dir).parts
            if any(p.startswith(".") for p in rel_parts):
                continue
            if pdf.name.endswith("._ocr.pdf"):
                continue
            yield patient_dir.name, pdf


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def load_manifest() -> dict[str, dict]:
    if not MANIFEST_PATH.exists():
        return {}
    rows: dict[str, dict] = {}
    with open(MANIFEST_PATH, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split("\t")
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != len(header):
                continue
            row = dict(zip(header, parts))
            rows[row["src_path"]] = row
    return rows


def write_manifest(rows: dict[str, dict]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(".tsv.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\t".join(MANIFEST_COLUMNS) + "\n")
        for key in sorted(rows):
            row = rows[key]
            fh.write("\t".join(str(row.get(c, "")) for c in MANIFEST_COLUMNS) + "\n")
    tmp.replace(MANIFEST_PATH)


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def derived_paths(pdf_path: Path) -> dict[str, Path]:
    """Return the three derived file paths for a source PDF, co-located with it."""
    base = pdf_path.with_suffix("")  # strip .pdf
    return {
        "raw_txt": base.with_suffix(base.suffix + ".raw.txt"),
        "raw_jsonl": base.with_suffix(base.suffix + ".raw.jsonl"),
        "meta_json": base.with_suffix(base.suffix + ".meta.json"),
    }


def process_one(pdf_path: Path, patient_name: str, ocr_jobs: int = 1) -> dict:
    started = time.strftime("%Y-%m-%dT%H:%M:%S")
    src_bytes = pdf_path.stat().st_size
    src_mtime = int(pdf_path.stat().st_mtime)
    try:
        sha1 = sha1_of(pdf_path)
        out_paths = derived_paths(pdf_path)
        pdf_dir = pdf_path.parent

        pages = pdf_page_count(pdf_path)
        text = pdftotext_layout(pdf_path)
        page_texts = split_pages(text)
        ocr_applied = "no"

        if pages > 0 and should_ocr(page_texts, pages):
            tmp_ocr = pdf_dir / f".{pdf_path.stem}._ocr.pdf"
            try:
                run_ocrmypdf(pdf_path, tmp_ocr, jobs=ocr_jobs)
                text = pdftotext_layout(tmp_ocr)
                page_texts = split_pages(text)
                ocr_applied = "yes"
            finally:
                tmp_ocr.unlink(missing_ok=True)

        total_chars = len(text)
        cpp = total_chars // max(pages, 1)

        # raw.txt: full layout-preserved text (form-feed between pages)
        out_paths["raw_txt"].write_text(text, encoding="utf-8")

        # raw.jsonl: one JSON object per page
        with open(out_paths["raw_jsonl"], "w", encoding="utf-8") as fh:
            for i, pt in enumerate(page_texts, start=1):
                rec = {
                    "page": i,
                    "chars": len(pt),
                    "ocr_used": ocr_applied == "yes",
                    "text": pt,
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # meta.json: small blob for humans + downstream stages
        meta = {
            "sha1": sha1,
            "src_path": str(pdf_path),
            "patient_folder": patient_name,
            "pdf_filename": pdf_path.name,
            "src_bytes": src_bytes,
            "src_mtime": src_mtime,
            "pages": pages,
            "total_chars": total_chars,
            "chars_per_page": cpp,
            "ocr_applied": ocr_applied,
            "processed_at": started,
            "pipeline_version": PIPELINE_VERSION,
        }
        out_paths["meta_json"].write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        return {
            "sha1": sha1,
            "src_path": str(pdf_path),
            "src_bytes": src_bytes,
            "src_mtime": src_mtime,
            "pages": pages,
            "total_chars": total_chars,
            "chars_per_page": cpp,
            "ocr_applied": ocr_applied,
            "status": "ok",
            "error": "",
            "out_dir": str(pdf_dir),
            "processed_at": started,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "sha1": "",
            "src_path": str(pdf_path),
            "src_bytes": src_bytes,
            "src_mtime": src_mtime,
            "pages": "",
            "total_chars": "",
            "chars_per_page": "",
            "ocr_applied": "",
            "status": "error",
            "error": repr(e)[:300],
            "out_dir": "",
            "processed_at": started,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--limit", type=int, default=None, help="Process at most N PDFs")
    ap.add_argument(
        "--only-patient",
        type=str,
        default=None,
        help="Glob pattern restricting patient folders, e.g. 'Ab*' or '*Waleed*'",
    )
    ap.add_argument(
        "--reprocess",
        action="store_true",
        help="Re-extract even if the manifest already has an ok entry for the PDF",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List what would be processed, but don't extract",
    )
    ap.add_argument(
        "--src-root",
        type=Path,
        default=SRC_ROOT,
        help=f"Source EHR root (default: {SRC_ROOT})",
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=max(1, (os.cpu_count() or 2) - 2),
        help="Number of parallel worker processes (default: cpu_count - 2)",
    )
    ap.add_argument(
        "--ocr-jobs",
        type=int,
        default=1,
        help="ocrmypdf --jobs value per worker (default: 1)",
    )
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    log(f"Loaded manifest: {len(manifest)} existing rows")

    all_pdfs = list(iter_source_pdfs(args.src_root, args.only_patient))
    log(f"Source scan: {len(all_pdfs)} PDFs found under {args.src_root}")

    to_process: list[tuple[str, Path]] = []
    for patient, pdf in all_pdfs:
        key = str(pdf)
        existing = manifest.get(key)
        if args.reprocess or existing is None or existing.get("status") != "ok":
            to_process.append((patient, pdf))

    log(f"{len(to_process)} PDFs queued (reprocess={args.reprocess})")
    if args.limit is not None:
        to_process = to_process[: args.limit]
        log(f"Limited to {len(to_process)} PDFs")

    if args.dry_run:
        for p, pdf in to_process:
            log(f"  DRY: {p} :: {pdf.name}")
        return 0

    workers = max(1, args.workers)
    log(f"Dispatching to {workers} worker process(es), ocr_jobs={args.ocr_jobs} each")

    tracker = ProgressTracker(
        stage="extract_text",
        total=len(to_process),
        workers=workers,
    )
    tracker.start()

    t0 = time.time()
    n_ok = n_err = n_ocr = 0
    completed = 0
    total = len(to_process)

    if workers == 1:
        # Serial path (easier to debug and profile)
        for patient, pdf in to_process:
            completed += 1
            tracker.set_current(f"{patient} :: {pdf.name}")
            log(f"[{completed}/{total}] {patient} :: {pdf.name}")
            row = process_one(pdf, patient, ocr_jobs=args.ocr_jobs)
            manifest[str(pdf)] = row
            is_ok = row["status"] == "ok"
            is_ocr = row.get("ocr_applied") == "yes"
            if is_ok:
                n_ok += 1
                if is_ocr:
                    n_ocr += 1
            else:
                n_err += 1
                log(f"  ERROR: {row['error']}")
            tracker.update(
                ok=is_ok,
                error=not is_ok,
                ocr=is_ocr,
                pages=int(row.get("pages", 0) or 0),
                chars=int(row.get("total_chars", 0) or 0),
                log_line=f"[{completed}/{total}] {'OCR' if is_ocr else '   '} {patient} :: {pdf.name}",
                current=f"{patient} :: {pdf.name}",
            )
            if completed % 10 == 0:
                write_manifest(manifest)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(process_one, pdf, patient, args.ocr_jobs): (patient, pdf)
                for patient, pdf in to_process
            }
            for fut in as_completed(futures):
                patient, pdf = futures[fut]
                completed += 1
                try:
                    row = fut.result()
                except Exception as e:  # noqa: BLE001
                    row = {
                        "sha1": "",
                        "src_path": str(pdf),
                        "src_bytes": pdf.stat().st_size if pdf.exists() else "",
                        "src_mtime": int(pdf.stat().st_mtime) if pdf.exists() else "",
                        "pages": "",
                        "total_chars": "",
                        "chars_per_page": "",
                        "ocr_applied": "",
                        "status": "error",
                        "error": f"worker exception: {e!r}"[:300],
                        "out_dir": "",
                        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                manifest[str(pdf)] = row
                is_ok = row["status"] == "ok"
                is_ocr = row.get("ocr_applied") == "yes"
                tag = "OCR" if is_ocr else "   "
                if is_ok:
                    n_ok += 1
                    if is_ocr:
                        n_ocr += 1
                else:
                    n_err += 1
                log(
                    f"[{completed}/{total}] {tag} "
                    f"{row.get('pages','?'):>3}p "
                    f"{row.get('chars_per_page','?'):>5}cpp "
                    f"{patient} :: {pdf.name}"
                )
                if row["status"] == "error":
                    log(f"    ERROR: {row['error']}")
                tracker.update(
                    ok=is_ok,
                    error=not is_ok,
                    ocr=is_ocr,
                    pages=int(row.get("pages", 0) or 0),
                    chars=int(row.get("total_chars", 0) or 0),
                    log_line=f"[{completed}/{total}] {tag} {patient} :: {pdf.name}",
                    current=f"{patient} :: {pdf.name}",
                )
                if completed % 10 == 0:
                    write_manifest(manifest)

    write_manifest(manifest)
    tracker.finish()
    dt = time.time() - t0
    rate = total / dt if dt > 0 else 0
    log(
        f"Done. ok={n_ok} err={n_err} ocr_applied={n_ocr} "
        f"elapsed={dt:.1f}s ({rate:.2f} pdf/s, {workers} workers)"
    )
    return 0 if n_err == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
