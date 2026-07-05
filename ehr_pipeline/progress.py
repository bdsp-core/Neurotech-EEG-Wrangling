"""
Shared progress tracker for the EHR pipeline stages.

Each stage instantiates a `ProgressTracker` with its stage id, total item count,
and optional metadata. Workers call `tracker.update(...)` as items finish, and
the tracker periodically flushes a JSON snapshot to
`dashboard_ehr/progress_<stage>.json`.

The dashboard HTML polls those files every few seconds to render a
per-stage view of overall pipeline progress.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Optional

DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard_ehr"

# How often to persist progress.json to disk (in seconds)
FLUSH_INTERVAL_SEC = 2.0
# Snapshot cadence for the burndown history (in seconds between samples)
HISTORY_INTERVAL_SEC = 15.0
# How many history points to keep (older points get dropped)
HISTORY_MAX_POINTS = 500
# Recent log tail length
RECENT_LOG_MAX = 40


STAGE_LABELS = {
    "extract_text": "Stage 1 · Extract raw text (pdftotext + OCR)",
    "segment_documents": "Stage 2 · Segment documents",
    "extract_fields": "Stage 3 · Extract structured fields (LLM)",
    "deidentify": "Stage 6 · De-identify EHR data",
}


# ---------------------------------------------------------------------------
# PHI sanitization
# ---------------------------------------------------------------------------
#
# The dashboard JSON files may be exposed publicly (via cloudflared / ngrok),
# so we MUST scrub patient identifiers before they touch disk. This module
# applies sanitization at write time as a safety net -- callers don't have to
# remember to do it.
#
# Strategy:
#   1. Replace "Last, First" name patterns with stable short hashes ("pt-7a3f1c").
#   2. Strip 8+ digit identifiers that look like MRNs / case IDs.
#   3. Strip phone numbers, dates of birth, street addresses (numeric prefix).
#
# We deliberately keep the doc *type* and *file extension* visible so the
# dashboard remains useful operationally.

# "Last, First" or "Last Suffix, First Middle" with optional middle/suffix
# Note: only the LAST-name part allows hyphens; the post-comma first/middle
# section uses no \- in its character classes, so a trailing "-NNNNNN" suffix
# (Neurotech case ID) is left intact for the long-number regex to catch.
_NAME_RE = re.compile(
    r"\b([A-Z][a-zA-Z'’\-]+(?:\s+(?:Jr|Sr|II|III|IV))?\.?"
    r"(?:\s+[A-Z][a-zA-Z'’\-]+){0,2}"
    r",\s*[A-Z][a-zA-Z'’]+(?:\s+[A-Z][a-zA-Z'’]+){0,3})"
)
# 8+ contiguous digits (MRNs, case IDs)
_LONG_NUM_RE = re.compile(r"\b\d{8,}\b")
# US-ish phone numbers
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")
# MM/DD/YYYY style dates (often DOB)
_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
# Any *.pdf / *.docx filename whose stem isn't already a hash placeholder.
# Patient PDFs sometimes have stems like "JA docs.pdf" (initials) that the
# Last,First name regex misses.
_DOC_FILE_RE = re.compile(r"\b([\w\s,'’\-\.]{1,80}?)\.(pdf|docx?|jsonl?|txt)\b", re.IGNORECASE)


def _short_hash(s: str) -> str:
    return hashlib.sha1(s.lower().strip().encode("utf-8")).hexdigest()[:6]


def _replace_doc_file(m: "re.Match[str]") -> str:
    stem, ext = m.group(1), m.group(2)
    # Already-hashed stems pass through unchanged
    if stem.startswith("pt-"):
        return f"{stem}.{ext}"
    return f"file-{_short_hash(stem)}.{ext}"


def sanitize_text(text: Optional[str]) -> Optional[str]:
    """Strip patient identifiers from a string before it lands in progress.json."""
    if text is None or not text:
        return text
    out = _NAME_RE.sub(lambda m: f"pt-{_short_hash(m.group(1))}", text)
    out = _LONG_NUM_RE.sub("[id]", out)
    out = _PHONE_RE.sub("[phone]", out)
    out = _DATE_RE.sub("[date]", out)
    out = _DOC_FILE_RE.sub(_replace_doc_file, out)
    return out


class ProgressTracker:
    def __init__(
        self,
        stage: str,
        total: int,
        *,
        workers: int = 1,
        extra: Optional[dict[str, Any]] = None,
        dashboard_dir: Path = DASHBOARD_DIR,
    ) -> None:
        self.stage = stage
        self.stage_label = STAGE_LABELS.get(stage, stage)
        self.total = int(total)
        self.workers = int(workers)
        self.extra_static = dict(extra or {})

        self.dashboard_dir = dashboard_dir
        self.dashboard_dir.mkdir(parents=True, exist_ok=True)
        self.progress_path = self.dashboard_dir / f"progress_{stage}.json"

        now = time.time()
        self.start_ts = now
        self.last_flush_ts = 0.0
        self.last_history_ts = now
        self.history: list[dict[str, Any]] = []
        self.recent_log: deque[str] = deque(maxlen=RECENT_LOG_MAX)

        # running counters
        self.done = 0
        self.ok = 0
        self.errors = 0
        self.ocr = 0
        self.pages = 0
        self.chars = 0
        self.sections_total = 0
        self.sections_by_type: dict[str, int] = {}
        self.llm_calls = 0
        self.tokens_in = 0
        self.tokens_out = 0
        self.cost_usd = 0.0

        self.current_item: Optional[str] = None
        self.running = False
        self.complete = False
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ API

    def start(self) -> None:
        self.running = True
        self.complete = False
        self.start_ts = time.time()
        self._record_history(force=True)
        self._flush(force=True)

    def set_total(self, total: int) -> None:
        """Update the running total. Useful for watch-mode stages whose input
        set grows over time as upstream stages produce more files."""
        self.total = int(total)
        self._flush(force=True)

    def mark_already_done(self, n: int) -> None:
        """Pre-credit `n` items as already-completed (e.g. files that were
        finished in a previous run and don't need to be reprocessed). Bumps
        `done` and `ok` so the dashboard percentage accurately reflects the
        true overall progress, not just what this run is doing.
        """
        with self._lock:
            self.done += int(n)
            self.ok += int(n)
        self._flush(force=True)

    def finish(self) -> None:
        self.running = False
        self.complete = True
        self.current_item = None
        self._record_history(force=True)
        self._flush(force=True)

    def abort(self, reason: str) -> None:
        self.running = False
        self.complete = False
        self.log(f"ABORT: {reason}")
        self._flush(force=True)

    def set_current(self, label: Optional[str]) -> None:
        self.current_item = sanitize_text(label)

    def log(self, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.recent_log.append(f"[{ts}] {sanitize_text(msg)}")

    def update(
        self,
        *,
        ok: bool = True,
        error: bool = False,
        ocr: bool = False,
        pages: int = 0,
        chars: int = 0,
        sections: int = 0,
        sections_by_type: Optional[dict[str, int]] = None,
        llm_calls: int = 0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd: float = 0.0,
        log_line: Optional[str] = None,
        current: Optional[str] = None,
    ) -> None:
        with self._lock:
            self.done += 1
            if error:
                self.errors += 1
            elif ok:
                self.ok += 1
            if ocr:
                self.ocr += 1
            self.pages += int(pages or 0)
            self.chars += int(chars or 0)
            self.sections_total += int(sections or 0)
            if sections_by_type:
                for k, v in sections_by_type.items():
                    self.sections_by_type[k] = self.sections_by_type.get(k, 0) + v
            self.llm_calls += int(llm_calls or 0)
            self.tokens_in += int(tokens_in or 0)
            self.tokens_out += int(tokens_out or 0)
            self.cost_usd += float(cost_usd or 0.0)
            if current is not None:
                self.current_item = sanitize_text(current)
            if log_line:
                ts = time.strftime("%H:%M:%S")
                self.recent_log.append(f"[{ts}] {sanitize_text(log_line)}")
            self._record_history()
        self._flush()

    # --------------------------------------------------------------- internal

    def _snapshot(self) -> dict[str, Any]:
        elapsed = time.time() - self.start_ts
        return {
            "stage": self.stage,
            "stage_label": self.stage_label,
            "total": self.total,
            "done": self.done,
            "ok": self.ok,
            "errors": self.errors,
            "ocr": self.ocr,
            "pages_done": self.pages,
            "chars_done": self.chars,
            "sections_total": self.sections_total,
            "sections_by_type": dict(self.sections_by_type),
            "llm_calls": self.llm_calls,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": round(self.cost_usd, 4),
            "workers": self.workers,
            "running": self.running,
            "complete": self.complete,
            "elapsed_sec": round(elapsed, 1),
            "start_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.start_ts)),
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "current_item": self.current_item,
            "history": list(self.history),
            "recent_log": list(self.recent_log),
            **self.extra_static,
        }

    def _record_history(self, force: bool = False) -> None:
        now = time.time()
        if not force and (now - self.last_history_ts) < HISTORY_INTERVAL_SEC:
            return
        self.last_history_ts = now
        self.history.append(
            {
                "time": time.strftime("%H:%M:%S", time.localtime(now)),
                "elapsed": round(now - self.start_ts, 1),
                "done": self.done,
                "ok": self.ok,
                "errors": self.errors,
                "ocr": self.ocr,
                "sections": self.sections_total,
                "llm_calls": self.llm_calls,
            }
        )
        if len(self.history) > HISTORY_MAX_POINTS:
            # decimate: keep every other sample to cap memory/file size
            self.history = self.history[::2]

    def _flush(self, force: bool = False) -> None:
        with self._lock:
            now = time.time()
            if not force and (now - self.last_flush_ts) < FLUSH_INTERVAL_SEC:
                return
            self.last_flush_ts = now
            snap = self._snapshot()
        # Belt-and-suspenders: re-sanitize the snapshot's free-text fields
        # right before writing, so even if a future caller adds new fields
        # that weren't routed through set_current/log, they get scrubbed.
        snap["current_item"] = sanitize_text(snap.get("current_item"))
        snap["recent_log"] = [sanitize_text(line) for line in snap.get("recent_log", [])]
        try:
            tmp = self.progress_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
            tmp.replace(self.progress_path)
        except OSError:
            pass  # dashboard is a convenience, not a hard dependency
