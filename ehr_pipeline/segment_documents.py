#!/usr/bin/env python3
"""
Stage 2 of the EHR extraction pipeline: document segmentation.

Each source PDF is a "packet" containing several stapled-together sub-documents
(Technologist Scan Report, TrackIT monitoring log, Medical Necessity form,
clinical consult notes, HIPAA boilerplate, ...). Stage 1 produced a raw.jsonl
with one text object per page. This stage classifies each page by landmark
regex, then collapses consecutive same-class pages into document ranges.

Output, written next to the source PDF:
    <stem>.sections.json      per-PDF document boundary list

Global summary (into STATE_DIR):
    sections_summary.tsv      one row per sub-document across the whole corpus

Usage:
  python ehr_pipeline/segment_documents.py
  python ehr_pipeline/segment_documents.py --only-patient "Abbas*"
  python ehr_pipeline/segment_documents.py --dry-run
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import time
from pathlib import Path
from typing import Iterator, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from progress import ProgressTracker  # type: ignore
else:
    from .progress import ProgressTracker

SRC_ROOT = Path("/Volumes/Extreme SSD/neurotech-data")
STATE_DIR = Path("/Users/mbwest/Desktop/GithubRepos/neurotech_wrangling/output/ehr")
SUMMARY_PATH = STATE_DIR / "sections_summary.tsv"
LOG_PATH = STATE_DIR / "segment_documents.log"

PIPELINE_VERSION = "0.1"


# ---------------------------------------------------------------------------
# Document-type rules
# ---------------------------------------------------------------------------
#
# Each rule has:
#   name: the canonical document type
#   patterns: iterable of regex patterns (case-insensitive, searched per-page)
#   weight: points awarded per matching pattern (higher = stronger signal)
#
# A page's doc_type is the rule with the highest total score. Pages with no
# matches carry their type forward from the previous classified page (up to
# MAX_CARRY_FORWARD pages), since most sub-documents span multiple pages and
# only the first page reliably contains the identifying landmark.

MAX_CARRY_FORWARD = 12  # pages: any sub-document longer than this should re-ID

RULES: list[tuple[str, list[str], int]] = [
    (
        "tech_scan_report",
        [
            r"Technologist Scan Report",
            r"TECHNOLOGIST IMPRESSION",
            r"SCANNING TECHNOLOGIST",
            r"Duration/Type of Test Performed",
            r"Type of Test Performed",
            r"Abnormal Slowing",
            r"Interictal Epileptiform Discharges",
            r"Photic Stimulation",
            r"Patient Event\(s\) log description",
            r"Automated Seizure Detection",
        ],
        3,
    ),
    (
        "trackit_monitoring_log",
        [
            r"Trackit\s*[\r\n]+\s*Record On",
            r"EEGReview\s*ed:",
            r"GeneralNote:",
            r"TrackIT\s*Battery",
            r"Record On\s+Impedence",
            r"Record On\s+Impedance",
            r"EquipmentFailure:",
        ],
        3,
    ),
    (
        "eeg_intake_form",
        [
            r"Long Term EEG Medical Necessity Form",
            r"NEUROTECH[^\n]{0,50}EEG Specialists",
            r"In[- ]Home\s+EEG\s+Specialists",
            r"Ambulatory EEG Notes",
            r"\b95700\b.*EEG hookup",
            r"Subscriber ID:",
            r"Referring Physician",
            r"Diagnosis Code \(",
            r"Parent/Guardian Name",
        ],
        3,
    ),
    (
        "eeg_order",
        [
            r"Accession number:\s*\d",
            r"Ordering provider:",
            r"Ambulatory EEG \d+-\d+ Hours \(Order",
            r"Order #:",
            r"Procedure:\s*EEG",
            r"OCC:\s*Neurology Clinic",
        ],
        3,
    ),
    (
        "clinical_progress_note",
        [
            r"Progress Notes\s+\w",
            r"Progress Note\s*$",
            r"Chief [Cc]omplaint:",
            r"Reason for Consultation",
            r"History of Present Illness",
            r"HISTORY OF PRESENT ILLNESS",
            r"PAST MEDICAL HISTORY",
            r"Past Medical History",
            r"Current AEDs? prescription",
            r"Assessment\s*/\s*Plan",
            r"Assessment and Plan",
            r"Impression and Plan",
            r"Physical Exam(?:ination)?",
            r"Review of Systems",
        ],
        2,
    ),
    (
        "history_and_physical",
        [
            r"History and Physical",
            r"H&P",
            r"Admission History",
        ],
        3,
    ),
    (
        "imaging_report",
        [
            r"MR\s+BRAIN",
            r"CT\s+HEAD",
            r"Brain MRI\b",
            r"RADIOLOGY REPORT",
            r"IMPRESSION:.*\n.*(brain|intracranial|white matter|ventricle)",
            r"Findings:.*\n.*(T1|T2|FLAIR|DWI)",
        ],
        3,
    ),
    (
        "hipaa_consent",
        [
            r"Health Insurance Portability",
            r"\bHIPAA\b",
            r"\bHIPPA\b",
            r"Notice of Privacy Practices",
            r"Authorization to (?:Release|Disclose)",
            r"Patient Acknowledgment of Notice",
        ],
        2,
    ),
    (
        "patient_event_log",
        [
            r"Patient Event Log",
            r"Event Diary",
            r"Seizure Diary",
            r"Patient Reported Event",
        ],
        3,
    ),
    (
        "lab_results",
        [
            r"LABORATORY RESULTS",
            r"Lab Results",
            r"CMP\s+Result",
            r"CBC\s+Result",
        ],
        3,
    ),
]

COMPILED_RULES: list[tuple[str, list[re.Pattern], int]] = [
    (name, [re.compile(p, re.IGNORECASE) for p in pats], weight)
    for name, pats, weight in RULES
]


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
# Core
# ---------------------------------------------------------------------------

def classify_page(text: str) -> tuple[Optional[str], int, dict[str, int]]:
    """Return (best_type, best_score, per_rule_score) for a single page."""
    scores: dict[str, int] = {}
    for name, pats, weight in COMPILED_RULES:
        hits = sum(1 for p in pats if p.search(text))
        if hits:
            scores[name] = hits * weight
    if not scores:
        return None, 0, scores
    best = max(scores.items(), key=lambda kv: kv[1])
    return best[0], best[1], scores


def segment_packet(pages: list[dict]) -> list[dict]:
    """Given ordered page records, return a list of sub-document ranges."""
    # Step 1: per-page classification
    page_types: list[Optional[str]] = []
    page_scores: list[int] = []
    for rec in pages:
        t, s, _ = classify_page(rec.get("text", ""))
        page_types.append(t)
        page_scores.append(s)

    # Step 2: forward-fill unknown pages from the last known type
    filled: list[Optional[str]] = list(page_types)
    last_known: Optional[str] = None
    carry = 0
    for i, t in enumerate(filled):
        if t is not None:
            last_known = t
            carry = 0
        else:
            if last_known is not None and carry < MAX_CARRY_FORWARD:
                filled[i] = last_known
                carry += 1
            else:
                last_known = None  # carry expired
                carry = 0

    # Step 3: collapse consecutive same-type pages into ranges
    sections: list[dict] = []
    if not filled:
        return sections

    start = 0
    cur = filled[0]
    for i in range(1, len(filled)):
        if filled[i] != cur:
            sections.append(_make_section(pages, start, i - 1, cur, page_scores))
            start = i
            cur = filled[i]
    sections.append(_make_section(pages, start, len(filled) - 1, cur, page_scores))
    return sections


def _make_section(
    pages: list[dict],
    start: int,
    end: int,
    doc_type: Optional[str],
    page_scores: list[int],
) -> dict:
    """Build one section record spanning pages[start..end] inclusive."""
    page_nums = [pages[i]["page"] for i in range(start, end + 1)]
    total_chars = sum(pages[i].get("chars", len(pages[i].get("text", ""))) for i in range(start, end + 1))
    max_score = max(page_scores[start : end + 1]) if end >= start else 0
    return {
        "doc_type": doc_type or "unknown",
        "page_start": page_nums[0],
        "page_end": page_nums[-1],
        "n_pages": len(page_nums),
        "total_chars": total_chars,
        "max_landmark_score": max_score,
        "confidence": "high" if max_score >= 6 else ("medium" if max_score >= 3 else "low"),
    }


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def iter_raw_jsonls(src_root: Path, only_patient: Optional[str]) -> Iterator[tuple[str, Path]]:
    """Yield (patient_folder, raw_jsonl_path) pairs."""
    if not src_root.exists():
        return
    for patient_dir in sorted(src_root.iterdir()):
        if not patient_dir.is_dir() or patient_dir.name.startswith("."):
            continue
        if only_patient and not fnmatch.fnmatch(patient_dir.name, only_patient):
            continue
        for jsonl in sorted(patient_dir.rglob("*.raw.jsonl")):
            yield patient_dir.name, jsonl


def load_pages(jsonl_path: Path) -> list[dict]:
    pages: list[dict] = []
    with open(jsonl_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                pages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return pages


def sections_path_for(jsonl_path: Path) -> Path:
    # Patient, Example Documents.raw.jsonl -> Patient, Example Documents.sections.json
    name = jsonl_path.name
    if name.endswith(".raw.jsonl"):
        base = name[: -len(".raw.jsonl")]
    else:
        base = jsonl_path.stem
    return jsonl_path.parent / f"{base}.sections.json"


def pdf_name_from(jsonl_path: Path) -> str:
    name = jsonl_path.name
    if name.endswith(".raw.jsonl"):
        return name[: -len(".raw.jsonl")] + ".pdf"
    return jsonl_path.with_suffix(".pdf").name


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SUMMARY_COLUMNS = [
    "patient_folder",
    "pdf_filename",
    "doc_type",
    "page_start",
    "page_end",
    "n_pages",
    "total_chars",
    "max_landmark_score",
    "confidence",
]


def _is_already_segmented(jsonl: Path) -> bool:
    """Skip raw.jsonls whose sections.json already exists and is newer."""
    sec = sections_path_for(jsonl)
    if not sec.exists():
        return False
    try:
        return sec.stat().st_mtime >= jsonl.stat().st_mtime
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument(
        "--only-patient",
        type=str,
        default=None,
        help="Glob restricting patient folders, e.g. 'Ab*'",
    )
    ap.add_argument(
        "--src-root",
        type=Path,
        default=SRC_ROOT,
        help=f"Source EHR root (default: {SRC_ROOT})",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--watch",
        action="store_true",
        help="Run continuously: rescan for new raw.jsonl files every --watch-interval seconds",
    )
    ap.add_argument("--watch-interval", type=int, default=5,
                    help="Seconds between rescans in --watch mode (default 5)")
    ap.add_argument("--reprocess", action="store_true",
                    help="Re-segment files even if a sections.json already exists")
    args = ap.parse_args()

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    all_sources = list(iter_raw_jsonls(args.src_root, args.only_patient))
    log(f"Found {len(all_sources)} raw.jsonl files under {args.src_root}")

    if args.dry_run:
        for patient, path in all_sources:
            log(f"  DRY: {patient} :: {path.name}")
        return 0

    sources = all_sources if args.reprocess else [
        (p, j) for p, j in all_sources if not _is_already_segmented(j)
    ]
    n_already_done = len(all_sources) - len(sources)
    log(f"{len(sources)} packets need segmentation "
        f"({n_already_done} already done from prior runs)")

    tracker = ProgressTracker(stage="segment_documents", total=len(all_sources))
    tracker.start()
    # Pre-credit the already-segmented files so the dashboard percentage
    # reflects overall progress (done / total of full corpus), not just
    # progress within this single run.
    if n_already_done:
        tracker.mark_already_done(n_already_done)

    t0 = time.time()
    n_files = 0
    n_sections = 0
    type_counts: dict[str, int] = {}
    summary_rows: list[list[str]] = []

    def process_one_file(patient: str, jsonl: Path) -> bool:
        """Returns True on success, False on skip/error."""
        nonlocal n_files, n_sections
        pages = load_pages(jsonl)
        if not pages:
            tracker.update(ok=False, error=True, log_line=f"SKIP (no pages): {jsonl.name}")
            return False
        sections = segment_packet(pages)
        out_path = sections_path_for(jsonl)
        pdf_name = pdf_name_from(jsonl)
        out_obj = {
            "pdf_filename": pdf_name,
            "patient_folder": patient,
            "n_pages": len(pages),
            "n_sections": len(sections),
            "sections": sections,
            "pipeline_version": PIPELINE_VERSION,
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        out_path.write_text(json.dumps(out_obj, indent=2), encoding="utf-8")

        n_files += 1
        n_sections += len(sections)
        this_types: dict[str, int] = {}
        for sec in sections:
            type_counts[sec["doc_type"]] = type_counts.get(sec["doc_type"], 0) + 1
            this_types[sec["doc_type"]] = this_types.get(sec["doc_type"], 0) + 1
            summary_rows.append(
                [
                    patient,
                    pdf_name,
                    sec["doc_type"],
                    str(sec["page_start"]),
                    str(sec["page_end"]),
                    str(sec["n_pages"]),
                    str(sec["total_chars"]),
                    str(sec["max_landmark_score"]),
                    sec["confidence"],
                ]
            )
        tracker.update(
            ok=True,
            sections=len(sections),
            sections_by_type=this_types,
            log_line=f"{patient} :: {pdf_name} ({len(sections)} sections)",
            current=f"{patient} :: {pdf_name}",
        )
        return True

    def write_summary() -> None:
        with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
            fh.write("\t".join(SUMMARY_COLUMNS) + "\n")
            for row in summary_rows:
                fh.write("\t".join(row) + "\n")

    # Initial pass
    for patient, jsonl in sources:
        process_one_file(patient, jsonl)
    write_summary()

    # Watch loop: rescan periodically until interrupted
    if args.watch:
        log(f"Entering watch mode (interval={args.watch_interval}s). Ctrl-C to stop.")
        prev_total = len(all_sources)
        try:
            while True:
                time.sleep(args.watch_interval)
                rescanned = list(iter_raw_jsonls(args.src_root, args.only_patient))
                # New files appeared since the last rescan?
                if len(rescanned) > prev_total:
                    new_files = len(rescanned) - prev_total
                    tracker.set_total(len(rescanned))
                    # Of the new files, how many were already segmented (e.g.
                    # by another concurrent process) and don't need work here?
                    pending_new = [
                        (p, j) for p, j in rescanned[-new_files:]
                        if not _is_already_segmented(j)
                    ]
                    pre_credit = new_files - len(pending_new)
                    if pre_credit:
                        tracker.mark_already_done(pre_credit)
                    prev_total = len(rescanned)
                pending = [
                    (p, j) for p, j in rescanned
                    if not _is_already_segmented(j)
                ]
                if pending:
                    log(f"watch: {len(pending)} new packets to segment")
                    for patient, jsonl in pending:
                        process_one_file(patient, jsonl)
                    write_summary()
        except KeyboardInterrupt:
            log("watch: interrupted by user")

    tracker.finish()
    dt = time.time() - t0
    log(f"Done. files={n_files} sections={n_sections} elapsed={dt:.1f}s")
    log(f"Summary: {SUMMARY_PATH}")
    log("Doc type distribution (section count):")
    for t, c in sorted(type_counts.items(), key=lambda kv: -kv[1]):
        log(f"  {t:>26}: {c}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
