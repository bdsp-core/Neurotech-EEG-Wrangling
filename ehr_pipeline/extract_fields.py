#!/usr/bin/env python3
"""
Stage 3 of the EHR extraction pipeline: structured field extraction.

For each PDF packet that has a *.sections.json file, walks each sub-document,
extracts the relevant page text from raw.jsonl, and runs a type-specific
extractor:

  - tech_scan_report      -> regex (deterministic)
  - eeg_order             -> regex
  - trackit_monitoring_log-> regex/parser (summary counts only for now)
  - clinical_progress_note-> local on-device LLM with structured output
  - history_and_physical  -> local on-device LLM
  - imaging_report        -> local on-device LLM
  - eeg_intake_form       -> local on-device LLM (text-only; vision pass later)
  - patient_event_log     -> local on-device LLM
  - lab_results           -> local on-device LLM
  - hipaa_consent         -> skipped (no clinical value)

Narrative (LLM) doc types are processed by a LOCALLY HOSTED open-weight model
(Qwen via Apple MLX) — clinical text is processed on-device. See llm_client.local_generate.

Output, written next to each source PDF:
    <stem>.fields.json    one record per identified sub-document

Global summary, written to STATE_DIR:
    fields_manifest.tsv   per-section completion record (resumable)
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterator, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from clean_findings import clean_finding  # type: ignore
    from progress import ProgressTracker  # type: ignore
    from llm_client import (
        local_generate,
        LLMResult,
        LLMError,
        parse_json_lenient,
        LOCAL_DEFAULT_MODEL,
    )
else:
    from .progress import ProgressTracker
    from .llm_client import (
        local_generate,
        LLMResult,
        LLMError,
        parse_json_lenient,
        LOCAL_DEFAULT_MODEL,
    )

SRC_ROOT = Path("/Volumes/Extreme SSD/neurotech-data")
STATE_DIR = Path("/Users/mbwest/Desktop/GithubRepos/neurotech_wrangling/output/ehr")
MANIFEST_PATH = STATE_DIR / "fields_manifest.tsv"
LOG_PATH = STATE_DIR / "extract_fields.log"
# Output filename suffix for per-packet field files. Override with --fields-suffix so a
# a tagged run writes e.g. ".fields.qwen.json" and NEVER overwrites an existing ".fields.json".
FIELDS_SUFFIX = ".fields.json"
# When set (via --packets-file), only process these *.sections.json paths (targeted re-run).
PACKETS_FILTER = None

PIPELINE_VERSION = "0.1"
# Extraction backend: a LOCALLY HOSTED open-weight model — clinical text is processed
# on-device and never leaves the machine.
DEFAULT_MODEL = LOCAL_DEFAULT_MODEL


def dispatch_generate(prompt: str, *, model: str, **kw) -> LLMResult:
    """Run the local on-device extraction backend."""
    return local_generate(prompt, model=model, **kw)

# Doc types we send to the LLM (everything else goes to a regex extractor or is skipped)
LLM_DOC_TYPES = {
    "clinical_progress_note",
    "history_and_physical",
    "imaging_report",
    "eeg_intake_form",
    "patient_event_log",
    "lab_results",
}

REGEX_DOC_TYPES = {
    "tech_scan_report",
    "eeg_order",
    "trackit_monitoring_log",
}

SKIP_DOC_TYPES = {
    "hipaa_consent",
    "unknown",
}

MANIFEST_COLUMNS = [
    "src_path",
    "section_idx",
    "doc_type",
    "method",
    "page_start",
    "page_end",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "status",
    "error",
    "processed_at",
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
# Regex extractors
# ---------------------------------------------------------------------------

def _first(text: str, pattern: str, group: int = 1, flags: int = 0) -> Optional[str]:
    m = re.search(pattern, text, flags)
    if m and m.lastindex and m.lastindex >= group:
        return m.group(group).strip()
    return None


def _strip_inline(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip() or None


def _extract_between(text: str, start_pat: str, end_pats: list[str]) -> Optional[str]:
    """Extract text between start_pat and the FIRST occurrence of any end_pat.

    This avoids the greedy-match-across-repeated-sections bug that caused
    the seizures field to bleed into the second copy of the report.
    """
    m = re.search(start_pat, text, re.IGNORECASE)
    if not m:
        return None
    content_start = m.end()
    # Find the earliest end boundary
    earliest_end = len(text)
    for ep in end_pats:
        em = re.search(ep, text[content_start:], re.IGNORECASE)
        if em and content_start + em.start() < earliest_end:
            earliest_end = content_start + em.start()
    result = text[content_start:earliest_end].strip()
    return result if result else None


# Section header patterns that delimit the tech scan report's major sections.
# Order matters — each section runs until it hits one of these or end-of-text.
_TSR_SECTION_BOUNDARIES = [
    r"^BACKGROUND\b",
    r"^Awake\b",
    r"^ACTIVATIONS\b",
    r"^Photic Stimulation\b",
    r"^ABNORMALITIES\b",
    r"^(?:Abnormal\s+)?Slowing\b",
    r"^(?:Interictal\s+)?Epileptiform\b",
    r"^(?:Other Abnormal Patterns)\b",
    r"^Seizures?\b",
    r"^TECHNOLOGIST IMPRESSION\b",
    r"^SCANNING TECHNOLOGIST\b",
    r"^Technical Description\b",
    # Stop at second report instance
    r"^Technologist Scan Report\b",
    r"^Patient Name:\s",
    r"^Duration/Type of Test\b",
    r"^Type of Test Performed\b",
]


def extract_tech_scan_report(text: str) -> dict[str, Any]:
    """Pull every reliably-labeled field out of a Technologist Scan Report.

    Uses a section-splitting approach: find each section header, extract content
    up to the next header. This avoids the greedy regex bleeding that caused
    the seizures field to capture the entire remainder of a multi-section report.
    """
    fields: dict[str, Any] = {}

    # --- Header fields (simple key: value on one line) ---
    fields["patient_name"] = _strip_inline(
        _first(text, r"Patient Name:\s*([^\n]+)")
    )
    fields["test_type"] = _strip_inline(
        _first(text, r"(?:Duration/)?Type of Test Performed:\s*([^\n]+)")
    )
    fields["total_time"] = _strip_inline(
        _first(text, r"Total Time[:\s]+([^\n]+)")
    )
    fields["eeg_start_time"] = _first(text, r"EEG Start Time:\s*([0-9:]{4,8})")
    fields["eeg_end_time"]   = _first(text, r"EEG End Time:\s*([0-9:]{4,8})")
    fields["eeg_start_date"] = _first(text, r"EEG Start Date:\s*([0-9/]{8,10})")
    fields["eeg_end_date"]   = _first(text, r"EEG End Date:\s*([0-9/]{8,10})")

    n_events = _first(text, r"Number of Patient Events:\s*(\d+)")
    fields["n_patient_events"] = int(n_events) if n_events else None
    n_video = _first(text, r"Number of Patient Events captured on video:\s*([^\n]+)")
    fields["n_patient_events_video"] = _strip_inline(n_video)

    fields["tech_comments"] = _strip_inline(
        _first(text, r"Tech Comments:\s*([\s\S]+?)(?:\n\s*(?:Total number|Was video|Were there|Number of Tech|Automated|Tech Events)|\Z)")
    )

    n_tech = _first(text, r"(?:Total number of Tech Events|Tech Events Total #):\s*(\d+)")
    fields["n_tech_events"] = int(n_tech) if n_tech else None
    auto_sz = _first(text, r"Automated Seizure (?:Detection|Detections):\s*(\d+)")
    fields["automated_seizures"] = int(auto_sz) if auto_sz else None
    auto_sp = _first(text, r"Automated Spike (?:Detection|Detections):?\s*(\d+)")
    fields["automated_spikes"] = int(auto_sp) if auto_sp else None
    if fields["automated_spikes"] is None:
        sp2 = _first(text, r"\bSpikes:\s*(\d+)")
        fields["automated_spikes"] = int(sp2) if sp2 else None

    # --- Event descriptions table ---
    # "Number of events  Description" rows like:
    #   1  12  Tech Event Type 1: Sharply contoured slowing
    events_table: list[dict] = []
    for m in re.finditer(
        r"(?:^\s*\d+\s+)?(\d+)\s+(Tech Event Type \d+:\s*(.+)|(.+))",
        text, re.MULTILINE
    ):
        count = int(m.group(1))
        desc = (m.group(3) or m.group(4) or "").strip()
        if desc and count > 0:
            events_table.append({"count": count, "description": desc})
    if events_table:
        fields["event_descriptions"] = events_table

    # --- Patient events with timestamps ---
    patient_events: list[dict] = []
    for m in re.finditer(
        r"(?:Patient\s+)?Event\s*#?\s*(\d+)\s*[-:]?\s*"
        r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)\s*"
        r"(?:@|at\s*)?\s*(\d{1,2}:\d{2}(?::\d{2})?)\s*"
        r"(?:\"([^\"]*)\"|(.*))",
        text, re.IGNORECASE
    ):
        ev = {
            "event_number": int(m.group(1)),
            "date": m.group(2),
            "time": m.group(3),
            "description": (m.group(4) or m.group(5) or "").strip() or None,
        }
        patient_events.append(ev)
    if patient_events:
        fields["patient_events"] = patient_events

    # --- Major sections: use _extract_between with boundary list ---

    # BACKGROUND
    # Format 2: "BACKGROUND\n..." or "Awake\nBackground: X Hz; ..."
    # Format 1: "Awake (if normal...)\nThe posterior dominant rhythm..."
    # Also: "Awake\nPosterior dominant rhythm..." or "Awake\nThe background..."
    end_pats_bg = [
        r"\nACTIVATION", r"\nPhotic Stimulation\b", r"\nABNORMALITIES\b",
        r"\nTECHNOLOGIST IMPRESSION\b", r"\nTechnical Description\b",
        r"\nTechnologist Scan Report\b", r"\nPatient Name:\s",
    ]
    bg = _extract_between(text, r"(?:BACKGROUND|Awake\b)[^\n]*\n", end_pats_bg)
    fields["background"] = _strip_inline(bg)

    # ACTIVATIONS: Photic Stimulation
    photic_ends = [
        r"\nHV\b", r"\nHyperventilation\b", r"\nPain\b", r"\nABNORMALITIES\b",
        r"\nTECHNOLOGIST IMPRESSION\b", r"\nTechnical Description\b",
    ]
    photic = _extract_between(text, r"Photic Stimulation[:\s]*", photic_ends)
    fields["photic_stimulation"] = _strip_inline(photic)

    # ACTIVATIONS: Hyperventilation
    hv_ends = [
        r"\nPain Stimulation\b", r"\nABNORMALITIES\b", r"\nPhotic\b",
        r"\nTECHNOLOGIST IMPRESSION\b",
    ]
    hv = _extract_between(text, r"\bHV[:\s]+", hv_ends)
    fields["hyperventilation"] = _strip_inline(hv)

    # ABNORMALITIES: Slowing
    slow_ends = [
        r"\n(?:Interictal\s+)?Epileptiform\b", r"\nOther Abnormal\b",
        r"\nSeizures?\b", r"\nTECHNOLOGIST IMPRESSION\b",
        r"\nBreach\b", r"\nTechnical Description\b",
    ]
    slowing = _extract_between(
        text, r"(?:Abnormal\s+)?Slowing[:\s]*", slow_ends
    )
    fields["slowing"] = clean_finding(_strip_inline(slowing))

    # ABNORMALITIES: Epileptiform
    epi_ends = [
        r"\nOther Abnormal\b", r"\nSeizures?\b",
        r"\nBreach\b", r"\nTECHNOLOGIST IMPRESSION\b",
        r"\nTechnical Description\b",
    ]
    epi = _extract_between(
        text, r"(?:Interictal\s+)?Epileptiform (?:Discharges|Activity)[:\s]*", epi_ends
    )
    fields["epileptiform_discharges"] = clean_finding(_strip_inline(epi))

    # ABNORMALITIES: Other Abnormal Patterns
    other_ends = [
        r"\nSeizures?\b", r"\nTECHNOLOGIST IMPRESSION\b",
        r"\nBreach\b", r"\nTechnical Description\b",
    ]
    other = _extract_between(text, r"Other Abnormal Patterns[:\s]*", other_ends)
    fields["other_abnormal_patterns"] = _strip_inline(other)

    # ABNORMALITIES: Seizures — THE FIX for the bleeding bug.
    # Must only match "Seizure:" or "Seizures:" in the ABNORMALITIES section, NOT
    # "Automated Seizure Detections:" in the header. Use a negative lookbehind.
    sz_ends = [
        r"TECHNOLOGIST IMPRESSION\b",   # no \n prefix — catches same-line bleed
        r"\nSCANNING TECHNOLOGIST\b",
        r"\nTechnical Description\b",
        r"\nTechnologist Scan Report\b",
        r"\nPatient Name:\s",
        r"\nBreach\b",
    ]
    # Match "Seizure:" or "Seizures:" NOT preceded by "Automated "
    sz = _extract_between(text, r"(?<!Automated )(?<!Detection)\bSeizures?\s*:\s*\n?", sz_ends)
    fields["seizures"] = clean_finding(_strip_inline(sz))

    # TECHNOLOGIST IMPRESSION
    imp_ends = [
        r"\nSCANNING TECHNOLOGIST\b",
        r"\nTechnical Description\b",
        r"\nTechnologist Scan Report\b",
    ]
    impression = _extract_between(
        text, r"TECHNOLOGIST IMPRESSION\s*\n+", imp_ends
    )
    fields["technologist_impression"] = _strip_inline(impression)

    fields["scanning_technologist"] = _strip_inline(
        _first(text, r"SCANNING TECHNOLOGIST:\s*([^\n]+)")
    )

    fields["extraction_method"] = "regex_v2"
    return fields


def extract_eeg_order(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    fields["accession_number"] = _first(text, r"Accession number:\s*(\d+)")
    fields["ordering_provider"] = _strip_inline(
        _first(text, r"Ordering provider:\s*([^\n]+?)(?:\s+\d{2}/\d{2}/\d{2,4}|\n)")
    )
    fields["procedure"] = _strip_inline(
        _first(text, r"(Ambulatory EEG \d+-\d+ Hours[^\n]*)")
    )
    fields["department"] = _strip_inline(
        _first(text, r"OCC:\s*([^\n]+)")
    )
    fields["primary_diagnosis"] = _strip_inline(
        _first(text, r"Primary diagnosis:\s*([^\n]+)")
    )
    fields["extraction_method"] = "regex"
    return fields


def extract_trackit_log(text: str) -> dict[str, Any]:
    """Parse the full TrackIT hourly monitoring table, extracting both the
    summary counts AND the individual hourly rows and timestamped events.
    """
    fields: dict[str, Any] = {}

    # --- Summary counts (same as before) ---
    fields["n_eeg_reviewed_notes"] = len(re.findall(r"EEGReview\s*ed:", text))
    fields["n_general_notes"]      = len(re.findall(r"GeneralNote:", text))
    fields["n_equipment_failures"] = len(re.findall(r"EquipmentFailure:", text))

    dates = re.findall(r"\b(\d{2}/\d{2})\b(?=\s+\d{1,2}:\d{2})", text)
    fields["date_range_first"] = dates[0] if dates else None
    fields["date_range_last"]  = dates[-1] if dates else None
    fields["n_distinct_days"]  = len(set(dates)) if dates else 0

    revs = re.findall(r"\b([A-Za-z][a-zA-Z]{2,})\s*[-]\s*\d{2}/\d{2}/\d{2,4}", text)
    fields["distinct_reviewers"] = sorted(set(revs))[:25]

    # --- Parse hourly rows ---
    # Format: "MM/DD   HH:MM AM/PM - HH:MM AM/PM TZ   Yes/No   impedance   ..."
    # Followed by optional "LastUpdate" field: "username - MM/DD/YYYY HH:MM AM/PM"
    # Then optionally one or more event lines: "EEGReviewed:", "GeneralNote:", etc.
    hourly_row_re = re.compile(
        r"(\d{2}/\d{2})\s+"
        r"(\d{1,2}:\d{2}\s*(?:AM|PM))\s*-\s*(\d{1,2}:\d{2}\s*(?:AM|PM))\s*"
        r"(CST|CDT|EST|EDT|MST|MDT|PST|PDT)?\s+"
        r"(Yes|No)",
        re.IGNORECASE,
    )

    # "reviewer - MM/DD/YYYY HH:MM AM/PM" or "reviewer - MM/DD/YYYY HH:MM:SS AM/PM"
    reviewer_re = re.compile(
        r"([A-Za-z][A-Za-z]{1,20})\s*-\s*(\d{2}/\d{2}/\d{2,4})\s+(\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM))",
        re.IGNORECASE,
    )

    # Event lines that follow hourly rows
    event_re = re.compile(
        r"(EEGReview\s*ed|GeneralNote|EquipmentFailure|SpikeDetection|SeizureDetection):\s*(.*)",
        re.IGNORECASE,
    )

    # Battery percentage
    battery_re = re.compile(r"\b(100|\d{1,2})\s*$")

    hourly_rows: list[dict] = []
    events: list[dict] = []
    lines = text.split("\n")
    current_hour: Optional[dict] = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Try to match an hourly row
        hm = hourly_row_re.search(line_stripped)
        if hm:
            current_hour = {
                "date": hm.group(1),
                "time_start": hm.group(2).strip(),
                "time_end": hm.group(3).strip(),
                "timezone": (hm.group(4) or "").strip() or None,
                "recording_on": hm.group(5).strip().lower() == "yes",
                "impedance": None,
                "battery_pct": None,
                "reviewer_name": None,
                "review_timestamp": None,
            }
            # Extract impedance (text between "Yes/No" and common end markers)
            remainder = line_stripped[hm.end():].strip()
            # Look for reviewer pattern in remainder
            rm = reviewer_re.search(remainder)
            if rm:
                current_hour["reviewer_name"] = rm.group(1)
                current_hour["review_timestamp"] = f"{rm.group(2)} {rm.group(3)}"
                imp_text = remainder[:rm.start()].strip()
            else:
                imp_text = remainder

            # Battery % is sometimes at the very end
            bm = battery_re.search(imp_text)
            if bm:
                current_hour["battery_pct"] = int(bm.group(1))
                imp_text = imp_text[:bm.start()].strip()

            # Clean up impedance
            imp_text = re.sub(r"\b(Yes|No)\b", "", imp_text).strip().rstrip("-").strip()
            if imp_text:
                current_hour["impedance"] = imp_text
            hourly_rows.append(current_hour)
            continue

        # Try reviewer on its own line (sometimes split from the hour row)
        if current_hour and not current_hour.get("reviewer_name"):
            rm = reviewer_re.search(line_stripped)
            if rm:
                current_hour["reviewer_name"] = rm.group(1)
                current_hour["review_timestamp"] = f"{rm.group(2)} {rm.group(3)}"
                continue

        # Try battery on its own line
        if current_hour and current_hour.get("battery_pct") is None:
            bm = re.match(r"^\s*(100|\d{1,2})\s*$", line_stripped)
            if bm:
                current_hour["battery_pct"] = int(bm.group(1))
                continue

        # Try event line
        em = event_re.search(line_stripped)
        if em:
            event_type_raw = em.group(1).strip()
            event_type_map = {
                "EEGReview ed": "eeg_reviewed",
                "EEGReviewed": "eeg_reviewed",
                "GeneralNote": "general_note",
                "EquipmentFailure": "equipment_failure",
                "SpikeDetection": "spike_detection",
                "SeizureDetection": "seizure_detection",
            }
            et = "eeg_reviewed" if "EEGReview" in event_type_raw else event_type_map.get(event_type_raw, event_type_raw.lower())
            ev = {
                "event_type": et,
                "description": em.group(2).strip(),
            }
            # Attach the timestamp from the current hourly row if available
            if current_hour:
                ev["date"] = current_hour["date"]
                ev["hour_start"] = current_hour["time_start"]
                ev["reviewer_name"] = None
                # Try to extract reviewer from the event description
                # e.g., "W NL, BB REEGT" or "Felicia Manes R. EEG T"
                desc = ev["description"]
                rm2 = re.search(r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\s+(?:R\.?\s*EEG\s*T|REEGT|RPSGT|CLTM)", desc)
                if rm2:
                    ev["reviewer_name"] = rm2.group(1)
            events.append(ev)

    fields["hourly_rows"] = hourly_rows
    fields["n_hours_total"] = len(hourly_rows)
    fields["n_hours_recording_on"] = sum(1 for h in hourly_rows if h.get("recording_on"))
    fields["n_hours_recording_off"] = sum(1 for h in hourly_rows if not h.get("recording_on"))
    fields["events"] = events
    fields["n_events"] = len(events)

    fields["extraction_method"] = "regex_v2"
    return fields


REGEX_EXTRACTORS = {
    "tech_scan_report": extract_tech_scan_report,
    "eeg_order": extract_eeg_order,
    "trackit_monitoring_log": extract_trackit_log,
}


# ---------------------------------------------------------------------------
# LLM extractor — clinical narrative documents
# ---------------------------------------------------------------------------

LLM_PROMPTS: dict[str, str] = {
    "clinical_progress_note": """You are extracting structured fields from a clinical progress note for an
ambulatory EEG patient. Be conservative -- if a field isn't clearly present, return null.
For lists, return [] when nothing is found.

Return exactly this JSON shape:
{
  "note_date": string|null,                            // ISO YYYY-MM-DD if possible
  "provider_name": string|null,
  "provider_specialty": string|null,
  "department": string|null,
  "chief_complaint": string|null,
  "reason_for_consultation": string|null,
  "hpi_summary": string|null,                          // 1-3 sentences
  "past_medical_history": [string],                    // condition names
  "current_medications": [{"name": string, "dose": string|null, "frequency": string|null}],
  "neurological_exam": string|null,                    // 1-2 sentences
  "assessment_plan": string|null,                      // 1-3 sentences
  "icd10_codes": [{"code": string, "description": string|null}],
  "follow_up": string|null
}

Note text:
""",
    "history_and_physical": """Extract structured fields from this History and Physical.
Return JSON:
{
  "encounter_date": string|null,
  "provider_name": string|null,
  "department": string|null,
  "chief_complaint": string|null,
  "history_of_present_illness": string|null,
  "past_medical_history": [string],
  "current_medications": [{"name": string, "dose": string|null, "frequency": string|null}],
  "allergies": [string],
  "review_of_systems": string|null,
  "physical_exam": string|null,
  "assessment": string|null,
  "plan": string|null,
  "icd10_codes": [{"code": string, "description": string|null}]
}

Document text:
""",
    "imaging_report": """Extract fields from this imaging report. Return JSON:
{
  "modality": string|null,                             // MRI, CT, etc.
  "anatomy": string|null,                              // "Brain", etc.
  "study_date": string|null,
  "indication": string|null,
  "findings": string|null,                             // 1-3 sentences
  "impression": string|null,                           // 1-2 sentences
  "radiologist": string|null
}

Report text:
""",
    "eeg_intake_form": """Extract fields from this Long Term EEG Medical Necessity / intake form.
The form is often handwritten so OCR text may be noisy -- only fill in fields
where you're confident. Return JSON:
{
  "patient_name": string|null,
  "dob": string|null,
  "sex": string|null,
  "address": string|null,
  "phone": string|null,
  "insurance": string|null,
  "referring_physician": string|null,
  "referring_phone": string|null,
  "diagnosis_codes": [string],                         // ICD-10 like G40.x
  "duration_hours_ordered": number|null,               // 24, 48, 72, 96 etc.
  "additional_services": {                             // booleans
    "video": boolean|null,
    "photic_stimulation": boolean|null,
    "hyperventilation": boolean|null,
    "sleep_deprivation": boolean|null,
    "a1_a2_electrodes": boolean|null
  },
  "interpreting_physician": string|null,
  "form_date": string|null
}

Form text (may be OCR-noisy):
""",
    "patient_event_log": """Extract patient-reported events. Return JSON:
{
  "events": [
    {"date": string|null, "time": string|null, "description": string|null, "duration_sec": number|null}
  ],
  "n_events": number
}

Log text:
""",
    "lab_results": """Extract lab result fields. Return JSON:
{
  "panel_name": string|null,
  "draw_date": string|null,
  "abnormal_findings": [{"analyte": string, "value": string, "flag": string|null}],
  "ordering_provider": string|null
}

Lab document:
""",
}


def _repair_truncated_json(text: str) -> str:
    """Best-effort repair of a JSON string truncated mid-output by the LLM.

    Strategy: strip trailing garbage, close any open string literals, then
    close open brackets/braces from inside out.
    """
    s = text.strip()
    # Strip markdown fences
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
    if s.endswith("```"):
        s = s[:-3].strip()

    # If it ends mid-string (odd number of unescaped quotes), close the string
    in_string = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and in_string:
            i += 2
            continue
        if c == '"':
            in_string = not in_string
        i += 1
    if in_string:
        s += '"'

    # Trim any trailing comma
    s = s.rstrip().rstrip(",")

    # Count unmatched brackets/braces and close them
    stack: list[str] = []
    in_str = False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and in_str:
            i += 2
            continue
        if c == '"':
            in_str = not in_str
        elif not in_str:
            if c in "{[":
                stack.append(c)
            elif c == "}" and stack and stack[-1] == "{":
                stack.pop()
            elif c == "]" and stack and stack[-1] == "[":
                stack.pop()
        i += 1

    closers = {"[": "]", "{": "}"}
    for opener in reversed(stack):
        s += closers.get(opener, "")

    return s


def extract_with_llm(
    doc_type: str,
    text: str,
    *,
    model: str = DEFAULT_MODEL,
    max_input_chars: int = 20000,
) -> tuple[dict[str, Any], LLMResult]:
    """Extract structured fields from a sub-document's text with the configured backend.

    Default backend is the on-device local model (no PHI leaves the host)."""
    prompt_template = LLM_PROMPTS.get(doc_type)
    if prompt_template is None:
        raise ValueError(f"No LLM prompt for doc_type={doc_type}")

    snippet = text[:max_input_chars]
    truncated = len(text) > max_input_chars
    prompt = prompt_template + snippet + "\n\nReturn JSON only, no commentary."

    result = dispatch_generate(
        prompt,
        model=model,
        temperature=0.0,
        max_output_tokens=2048,   # structured extractions are short (~150 tok); cap runaway decode
    )

    # Attempt to parse JSON; if truncated, try to repair by closing open strings/braces
    raw_text = result.text
    try:
        fields = parse_json_lenient(raw_text)
    except json.JSONDecodeError:
        # Common failure: the model's output was truncated mid-string.
        # Try to repair by closing open strings and braces.
        repaired = _repair_truncated_json(raw_text)
        try:
            fields = parse_json_lenient(repaired)
        except json.JSONDecodeError as e:
            raise LLMError(f"failed to parse JSON: {e}; got: {raw_text[:300]}")
    if not isinstance(fields, dict):
        raise LLMError(f"LLM returned non-dict: {type(fields).__name__}")

    fields["extraction_method"] = f"llm:{model}"
    if truncated:
        fields["_input_truncated"] = True
    return fields, result


# ---------------------------------------------------------------------------
# Per-section dispatch
# ---------------------------------------------------------------------------

def text_for_section(pages: list[dict], page_start: int, page_end: int) -> str:
    parts = []
    for rec in pages:
        p = rec.get("page", 0)
        if page_start <= p <= page_end:
            parts.append(rec.get("text", ""))
    return "\f".join(parts)


def process_section(
    section: dict,
    pages: list[dict],
    *,
    use_llm: bool,
    model: str,
) -> dict[str, Any]:
    doc_type = section.get("doc_type", "unknown")
    page_start = section["page_start"]
    page_end = section["page_end"]
    text = text_for_section(pages, page_start, page_end)

    record: dict[str, Any] = {
        "doc_type": doc_type,
        "page_start": page_start,
        "page_end": page_end,
        "n_pages": section.get("n_pages", page_end - page_start + 1),
        "section_confidence": section.get("confidence", "low"),
        "method": "skip",
        "fields": None,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_usd": 0.0,
        "elapsed_sec": 0.0,
    }

    if doc_type in SKIP_DOC_TYPES:
        record["method"] = "skip"
        return record

    if doc_type in REGEX_EXTRACTORS:
        try:
            fields = REGEX_EXTRACTORS[doc_type](text)
            record["method"] = "regex"
            record["fields"] = fields
        except Exception as e:  # noqa: BLE001
            record["method"] = "regex_error"
            record["error"] = repr(e)[:300]
        return record

    if doc_type in LLM_DOC_TYPES:
        if not use_llm:
            record["method"] = "llm_disabled"
            return record
        try:
            fields, llm_result = extract_with_llm(doc_type, text, model=model)
            record["method"] = f"llm:{model}"
            record["fields"] = fields
            record["tokens_in"] = llm_result.tokens_in
            record["tokens_out"] = llm_result.tokens_out
            record["cost_usd"] = llm_result.cost_usd
            record["elapsed_sec"] = llm_result.elapsed_sec
        except Exception as e:  # noqa: BLE001
            record["method"] = "llm_error"
            record["error"] = repr(e)[:300]
        return record

    record["method"] = "no_extractor"
    return record


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def iter_sections_files(
    src_root: Path, only_patient: Optional[str]
) -> Iterator[tuple[str, Path, Path]]:
    """Yield (patient_folder, sections_path, raw_jsonl_path) triples."""
    if not src_root.exists():
        return
    for patient_dir in sorted(src_root.iterdir()):
        if not patient_dir.is_dir() or patient_dir.name.startswith("."):
            continue
        if only_patient and not fnmatch.fnmatch(patient_dir.name, only_patient):
            continue
        for sections in sorted(patient_dir.rglob("*.sections.json")):
            if PACKETS_FILTER is not None and str(sections) not in PACKETS_FILTER:
                continue
            base = sections.name[: -len(".sections.json")]
            jsonl = sections.parent / f"{base}.raw.jsonl"
            if not jsonl.exists():
                continue
            yield patient_dir.name, sections, jsonl


def fields_path_for(sections_path: Path) -> Path:
    base = sections_path.name[: -len(".sections.json")]
    return sections_path.parent / f"{base}{FIELDS_SUFFIX}"


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


def load_sections(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fields_manifest() -> dict[str, dict]:
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
            key = f"{row['src_path']}#{row['section_idx']}"
            rows[key] = row
    return rows


def write_fields_manifest(rows: dict[str, dict]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(".tsv.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\t".join(MANIFEST_COLUMNS) + "\n")
        for key in sorted(rows):
            row = rows[key]
            fh.write("\t".join(str(row.get(c, "")) for c in MANIFEST_COLUMNS) + "\n")
    tmp.replace(MANIFEST_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--limit", type=int, default=None,
                    help="Process at most N packets")
    ap.add_argument("--only-patient", type=str, default=None,
                    help="Glob restricting patient folders, e.g. 'Ab*'")
    ap.add_argument("--reprocess", action="store_true",
                    help="Re-extract sections even if already processed")
    ap.add_argument("--skip-llm", action="store_true",
                    help="Run only regex extractors; mark LLM types as 'llm_disabled'")
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL,
                    help="Extraction model. Default is a local on-device MLX model "
                         "(no PHI egress); pass a cloud model id only for non-PHI dev.")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="Concurrent packets processed (threads, LLM calls are I/O-bound)")
    ap.add_argument("--src-root", type=Path, default=SRC_ROOT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--watch",
        action="store_true",
        help="Run continuously: rescan for new sections.json files every --watch-interval seconds",
    )
    ap.add_argument("--watch-interval", type=int, default=30,
                    help="Seconds between rescans in --watch mode (default 30)")
    ap.add_argument("--fields-suffix", type=str, default=".fields.json",
                    help="Output filename suffix per packet (default .fields.json). Use "
                         ".fields.qwen.json for a tagged run that must not overwrite an existing extraction.")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="Manifest path (use a separate file for a tagged run).")
    ap.add_argument("--packets-file", type=Path, default=None,
                    help="Process only the packets listed in this file (one path per line; "
                         "*.sections.json or *.fields*.json paths accepted). For targeted re-runs.")
    args = ap.parse_args()

    # Apply output-namespace overrides so a tagged (e.g. Qwen) run is fully isolated.
    global FIELDS_SUFFIX, MANIFEST_PATH, PACKETS_FILTER
    FIELDS_SUFFIX = args.fields_suffix
    if args.manifest is not None:
        MANIFEST_PATH = args.manifest
    if args.packets_file is not None:
        raw = args.packets_file.read_text().splitlines()
        # normalize any *.fields*.json path back to its *.sections.json sibling
        PACKETS_FILTER = set()
        for ln in raw:
            ln = ln.strip()
            if not ln:
                continue
            PACKETS_FILTER.add(re.sub(r"\.fields[^/]*\.json$", ".sections.json", ln))
        log(f"Targeted run: {len(PACKETS_FILTER)} packets from {args.packets_file}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    initial_sources = list(iter_sections_files(args.src_root, args.only_patient))
    log(f"Found {len(initial_sources)} segmented packets under {args.src_root}")

    manifest = load_fields_manifest()
    log(f"Loaded fields manifest: {len(manifest)} existing rows")

    if args.limit is not None:
        initial_sources = initial_sources[: args.limit]
        log(f"Limited to {len(initial_sources)} packets")

    if args.dry_run:
        for p, sec, jl in initial_sources:
            log(f"  DRY: {p} :: {sec.name}")
        return 0

    tracker = ProgressTracker(stage="extract_fields", total=len(initial_sources))
    tracker.start()
    sources = initial_sources

    t0 = time.time()
    counters = {
        "n_packets_ok": 0,
        "n_packets_err": 0,
        "n_sections_total": 0,
        "total_cost": 0.0,
        "total_tokens_in": 0,
        "total_tokens_out": 0,
        "total_llm_calls": 0,
    }
    manifest_lock = threading.Lock()
    counters_lock = threading.Lock()

    def process_packet(patient: str, sections_path: Path, jsonl: Path) -> None:
        """Process one packet. Runs on a worker thread -- must be thread-safe."""
        pdf_filename = sections_path.name[: -len(".sections.json")] + ".pdf"
        try:
            sections_obj = load_sections(sections_path)
            pages = load_pages(jsonl)
            sections = sections_obj.get("sections", [])

            # Per-packet local deltas (no lock needed; local to this thread)
            packet_cost = 0.0
            packet_tokens_in = 0
            packet_tokens_out = 0
            packet_llm_calls = 0
            packet_new_sections = 0
            per_section_manifest_updates: list[tuple[str, dict]] = []

            # Split into (a) sections to skip, (b) fast regex ones, (c) LLM ones
            todo_regex: list[tuple[int, dict]] = []
            todo_llm: list[tuple[int, dict]] = []
            skipped: dict[int, dict] = {}
            for idx, sec in enumerate(sections):
                key = f"{sections_path}#{idx}"
                with manifest_lock:
                    already = (
                        not args.reprocess
                        and key in manifest
                        and manifest[key].get("status") == "ok"
                    )
                if already:
                    skipped[idx] = {
                        "doc_type": sec.get("doc_type"),
                        "page_start": sec.get("page_start"),
                        "page_end": sec.get("page_end"),
                        "method": manifest[key].get("method"),
                        "skipped_reason": "already_in_manifest",
                    }
                    continue
                dt = sec.get("doc_type", "")
                if dt in LLM_DOC_TYPES and not args.skip_llm:
                    todo_llm.append((idx, sec))
                else:
                    todo_regex.append((idx, sec))

            # Process regex sections inline (nearly free)
            done_recs: dict[int, dict] = {}
            for idx, sec in todo_regex:
                done_recs[idx] = process_section(
                    sec, pages, use_llm=not args.skip_llm, model=args.model
                )

            # Process LLM sections concurrently (within the packet) -- 2-4 per packet typical
            if todo_llm:
                with ThreadPoolExecutor(max_workers=min(len(todo_llm), 4)) as inner_pool:
                    futs = {
                        inner_pool.submit(
                            process_section, sec, pages,
                            use_llm=not args.skip_llm, model=args.model,
                        ): idx
                        for idx, sec in todo_llm
                    }
                    for fut in as_completed(futs):
                        done_recs[futs[fut]] = fut.result()

            # Reassemble in original order; fold counters + manifest rows
            section_records: list[dict] = []
            for idx in range(len(sections)):
                if idx in skipped:
                    section_records.append(skipped[idx])
                    continue
                sec = sections[idx]
                rec = done_recs[idx]
                section_records.append(rec)
                packet_new_sections += 1
                rec_cost = rec.get("cost_usd", 0.0) or 0.0
                rec_tin = rec.get("tokens_in", 0) or 0
                rec_tout = rec.get("tokens_out", 0) or 0
                packet_cost += rec_cost
                packet_tokens_in += rec_tin
                packet_tokens_out += rec_tout
                if str(rec.get("method", "")).startswith("llm:"):
                    packet_llm_calls += 1

                per_section_manifest_updates.append((
                    f"{sections_path}#{idx}",
                    {
                        "src_path": str(sections_path),
                        "section_idx": idx,
                        "doc_type": sec.get("doc_type", ""),
                        "method": rec.get("method", ""),
                        "page_start": sec.get("page_start", ""),
                        "page_end": sec.get("page_end", ""),
                        "tokens_in": rec.get("tokens_in", 0),
                        "tokens_out": rec.get("tokens_out", 0),
                        "cost_usd": round(rec.get("cost_usd", 0.0), 6),
                        "status": "ok" if "error" not in rec else "error",
                        "error": rec.get("error", ""),
                        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    },
                ))

            out = {
                "pdf_filename": pdf_filename,
                "patient_folder": patient,
                "n_sections": len(sections),
                "section_records": section_records,
                "pipeline_version": PIPELINE_VERSION,
                "processed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            fields_path_for(sections_path).write_text(
                json.dumps(out, indent=2), encoding="utf-8"
            )

            # Publish manifest and counter updates atomically
            with manifest_lock:
                for key, row in per_section_manifest_updates:
                    manifest[key] = row
            with counters_lock:
                counters["n_packets_ok"] += 1
                counters["n_sections_total"] += packet_new_sections
                counters["total_cost"] += packet_cost
                counters["total_tokens_in"] += packet_tokens_in
                counters["total_tokens_out"] += packet_tokens_out
                counters["total_llm_calls"] += packet_llm_calls
                cur_total = counters["total_cost"]

            tracker.update(
                ok=True,
                llm_calls=packet_llm_calls,
                tokens_in=packet_tokens_in,
                tokens_out=packet_tokens_out,
                cost_usd=packet_cost,
                log_line=f"{patient} :: {pdf_filename} ({len(sections)} sec, ${cur_total:.4f})",
                current=f"{patient} :: {pdf_filename}",
            )
        except Exception as e:  # noqa: BLE001
            with counters_lock:
                counters["n_packets_err"] += 1
            log(f"  ERROR: {patient} :: {pdf_filename}: {e!r}")
            tracker.update(ok=False, error=True, log_line=f"ERROR {patient}: {e!r}")

    def run_batch(batch: list[tuple[str, Path, Path]]) -> None:
        if not batch:
            return
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
            futures = [
                pool.submit(process_packet, p, sec, jl)
                for p, sec, jl in batch
            ]
            written_since = 0
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001
                    log(f"  worker exception: {e!r}")
                written_since += 1
                if written_since % 10 == 0:
                    with manifest_lock:
                        write_fields_manifest(manifest)
        with manifest_lock:
            write_fields_manifest(manifest)

    # Initial pass (parallel)
    log(f"Processing {len(sources)} packets with concurrency={args.concurrency}")
    run_batch(sources)

    # Watch loop: rescan periodically until interrupted
    if args.watch:
        log(f"Entering watch mode (interval={args.watch_interval}s). Ctrl-C to stop.")
        try:
            while True:
                time.sleep(args.watch_interval)
                rescanned = list(iter_sections_files(args.src_root, args.only_patient))
                tracker.set_total(len(rescanned))
                # Pending = packets we haven't fully processed yet (any section
                # missing from manifest counts the packet as pending).
                pending = []
                with manifest_lock:
                    manifest_snapshot = dict(manifest)
                for p, sec, jl in rescanned:
                    try:
                        sec_obj = load_sections(sec)
                    except Exception:
                        continue
                    n_secs = len(sec_obj.get("sections", []))
                    n_done = sum(
                        1
                        for i in range(n_secs)
                        if f"{sec}#{i}" in manifest_snapshot
                        and manifest_snapshot[f"{sec}#{i}"].get("status") == "ok"
                    )
                    if n_done < n_secs:
                        pending.append((p, sec, jl))
                if pending:
                    log(f"watch: {len(pending)} packets need fields extraction")
                    run_batch(pending)
        except KeyboardInterrupt:
            log("watch: interrupted by user")

    tracker.finish()
    dt = time.time() - t0
    log(
        f"Done. packets ok={counters['n_packets_ok']} err={counters['n_packets_err']} "
        f"sections={counters['n_sections_total']} llm_calls={counters['total_llm_calls']} "
        f"tokens_in={counters['total_tokens_in']} tokens_out={counters['total_tokens_out']} "
        f"cost=${counters['total_cost']:.4f} elapsed={dt:.1f}s"
    )
    return 0 if counters["n_packets_err"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
