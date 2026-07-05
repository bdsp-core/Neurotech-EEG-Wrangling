#!/usr/bin/env python3
"""
Build global summary CSVs from per-patient fields.json files.

Reads all *.fields.json under SRC_ROOT and produces:
  output/ehr/studies.csv
  output/ehr/diagnosis_codes.csv
  output/ehr/eeg_background.csv
  output/ehr/eeg_activations.csv
  output/ehr/eeg_slowing.csv
  output/ehr/eeg_epileptiform.csv
  output/ehr/eeg_seizures.csv
  output/ehr/technologist_impression.csv
  output/ehr/clinical_encounters.csv
  output/ehr/conditions.csv
  output/ehr/medications.csv
  output/ehr/monitoring_summary.csv
  output/ehr/monitoring_hours.csv
  output/ehr/monitoring_events.csv
  output/ehr/patient_events.csv
  output/ehr/imaging.csv
  output/ehr/lab_results.csv
"""

from __future__ import annotations

import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

SRC_ROOT = Path("/Volumes/Extreme SSD/neurotech-data")
OUT_DIR = Path("/Users/mbwest/Desktop/GithubRepos/neurotech_wrangling/output/ehr")


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ------------------------------------------------------------------ helpers

def safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return str(v)


def safe_int(v: Any) -> str:
    if v is None:
        return ""
    try:
        return str(int(v))
    except (ValueError, TypeError):
        return ""


def safe_float(v: Any) -> str:
    if v is None:
        return ""
    try:
        return str(round(float(v), 4))
    except (ValueError, TypeError):
        return ""


def parse_pdr(bg_text: str) -> dict[str, str]:
    """Extract PDR frequency from background text."""
    if not bg_text:
        return {"pdr_frequency_hz": "", "pdr_symmetry": "", "pdr_reactivity": ""}
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-\s*(\d+(?:\.\d+)?))?\s*Hz", bg_text)
    freq = ""
    if m:
        freq = m.group(1) if not m.group(2) else f"{m.group(1)}-{m.group(2)}"
    sym = "symmetric" if re.search(r"\bsymmetric\b", bg_text, re.I) else (
        "asymmetric" if re.search(r"\basymmetric\b", bg_text, re.I) else ""
    )
    react = "reactive" if re.search(r"\breactive\b", bg_text, re.I) else (
        "non_reactive" if re.search(r"\bnon.reactive\b", bg_text, re.I) else ""
    )
    return {"pdr_frequency_hz": freq, "pdr_symmetry": sym, "pdr_reactivity": react}


def classify_impression(imp: str) -> str:
    if not imp:
        return ""
    if re.search(r"(?i)within normal limits|is normal|was normal", imp):
        return "normal"
    if re.search(r"(?i)abnormal", imp):
        return "abnormal"
    if re.search(r"(?i)question", imp):
        return "questionably_abnormal"
    return "indeterminate"


def parse_test_type(tt: str) -> dict[str, str]:
    if not tt:
        return {"duration_hours": "", "has_video": "", "is_ambulatory": ""}
    dur_m = re.search(r"(\d+)\s*(?:Hr|Hour|hour)", tt, re.I)
    dur = dur_m.group(1) if dur_m else ""
    video = "true" if re.search(r"(?i)video|VEEG", tt) else "false"
    amb = "true" if re.search(r"(?i)ambulatory|amb", tt) else "false"
    return {"duration_hours": dur, "has_video": video, "is_ambulatory": amb}


# ------------------------------------------------------------------ writers

class CSVWriter:
    def __init__(self, path: Path, columns: list[str]):
        self.path = path
        self.columns = columns
        self.fh = open(path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.fh)
        self.writer.writerow(columns)
        self.count = 0

    def write(self, row: dict[str, str]) -> None:
        self.writer.writerow([row.get(c, "") for c in self.columns])
        self.count += 1

    def close(self) -> None:
        self.fh.close()
        log(f"  {self.path.name}: {self.count:,} rows")


# ------------------------------------------------------------------ main

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Aggregate per-packet field files into CSVs.")
    ap.add_argument("--fields-glob", default="*.fields.json",
                    help="Glob for per-packet field files (e.g. *.fields.qwen.json for a Qwen run).")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Output dir for the aggregate CSVs (default output/ehr).")
    args = ap.parse_args()

    global OUT_DIR
    if args.out_dir is not None:
        OUT_DIR = args.out_dir
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fields_files = sorted(SRC_ROOT.rglob(args.fields_glob))
    log(f"Found {len(fields_files)} {args.fields_glob} files -> {OUT_DIR}")

    # Pre-pass: map patient (name-key = folder without the numeric suffix) -> dob/sex
    # from ALL intake forms, so a patient's demographics attach to every one of their
    # study rows — dob/sex may be recorded on a different visit's packet than a given
    # tech report (and intake-only packets contribute no study row of their own).
    nk_dob, nk_sex = {}, {}
    for ff in fields_files:
        try:
            _d = json.loads(ff.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        _nk = re.sub(r"-\d+$", "", _d.get("patient_folder", "")).strip().lower()
        for _r in _d.get("section_records", []):
            if _r.get("doc_type") == "eeg_intake_form" and _r.get("fields"):
                _f = _r["fields"]
                if _f.get("dob") and _nk not in nk_dob:
                    nk_dob[_nk] = safe_str(_f.get("dob"))
                if _f.get("sex") and _nk not in nk_sex:
                    nk_sex[_nk] = safe_str(_f.get("sex"))
    log(f"Pre-pass demographics: {len(nk_dob)} patients w/ dob, {len(nk_sex)} w/ sex")

    # Initialize all CSV writers
    studies = CSVWriter(OUT_DIR / "studies.csv", [
        "study_id", "patient_name", "patient_dob", "patient_sex",
        "eeg_start_date", "eeg_start_time",
        "eeg_end_date", "eeg_end_time", "test_type_raw", "duration_hours",
        "has_video", "is_ambulatory", "n_patient_events", "n_patient_events_video",
        "n_tech_events", "automated_seizure_detections", "automated_spike_detections",
        "tech_comments", "scanning_technologist", "source_pdf",
    ])
    diag = CSVWriter(OUT_DIR / "diagnosis_codes.csv", [
        "study_id", "code", "source",
    ])
    bg_csv = CSVWriter(OUT_DIR / "eeg_background.csv", [
        "study_id", "pdr_frequency_hz", "pdr_symmetry", "pdr_reactivity",
        "raw_background_text",
    ])
    act_csv = CSVWriter(OUT_DIR / "eeg_activations.csv", [
        "study_id", "photic_stimulation", "hyperventilation",
    ])
    slow_csv = CSVWriter(OUT_DIR / "eeg_slowing.csv", [
        "study_id", "raw_description",
    ])
    epi_csv = CSVWriter(OUT_DIR / "eeg_epileptiform.csv", [
        "study_id", "raw_description",
    ])
    sz_csv = CSVWriter(OUT_DIR / "eeg_seizures.csv", [
        "study_id", "raw_description",
    ])
    imp_csv = CSVWriter(OUT_DIR / "technologist_impression.csv", [
        "study_id", "classification", "raw_text",
    ])
    enc_csv = CSVWriter(OUT_DIR / "clinical_encounters.csv", [
        "study_id", "encounter_type", "encounter_date", "provider_name",
        "provider_specialty", "department", "chief_complaint",
        "reason_for_consultation", "hpi_summary", "neurological_exam",
        "assessment_plan", "follow_up",
    ])
    cond_csv = CSVWriter(OUT_DIR / "conditions.csv", [
        "study_id", "encounter_type", "condition_name",
    ])
    med_csv = CSVWriter(OUT_DIR / "medications.csv", [
        "study_id", "encounter_type", "name_as_stated", "dose", "frequency",
    ])
    mon_sum = CSVWriter(OUT_DIR / "monitoring_summary.csv", [
        "study_id", "n_hours_total", "n_hours_recording_on", "n_hours_recording_off",
        "n_eeg_reviewed_notes", "n_general_notes", "n_equipment_failures",
        "date_range_first", "date_range_last", "n_distinct_days",
        "n_distinct_reviewers", "distinct_reviewers",
    ])
    mon_hrs = CSVWriter(OUT_DIR / "monitoring_hours.csv", [
        "study_id", "date", "time_start", "time_end", "timezone",
        "recording_on", "impedance", "battery_pct",
        "reviewer_name", "review_timestamp",
    ])
    mon_evt = CSVWriter(OUT_DIR / "monitoring_events.csv", [
        "study_id", "event_type", "date", "hour_start",
        "reviewer_name", "description",
    ])
    pat_evt = CSVWriter(OUT_DIR / "patient_events.csv", [
        "study_id", "event_number", "date", "time", "description",
    ])
    img_csv = CSVWriter(OUT_DIR / "imaging.csv", [
        "study_id", "modality", "anatomy", "study_date",
        "indication", "findings", "impression",
    ])
    lab_csv = CSVWriter(OUT_DIR / "lab_results.csv", [
        "study_id", "panel_name", "draw_date", "ordering_provider",
        "abnormal_findings",
    ])

    all_writers = [
        studies, diag, bg_csv, act_csv, slow_csv, epi_csv, sz_csv, imp_csv,
        enc_csv, cond_csv, med_csv, mon_sum, mon_hrs, mon_evt, pat_evt,
        img_csv, lab_csv,
    ]

    for fi, ff in enumerate(fields_files):
        if fi % 500 == 0 and fi > 0:
            log(f"  processed {fi}/{len(fields_files)}...")

        try:
            data = json.loads(ff.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        study_id = data.get("patient_folder", ff.parent.parent.name)
        pdf_name = data.get("pdf_filename", "")

        # dob/sex come from this patient's intake form (any visit) via the pre-pass map.
        _nk = re.sub(r"-\d+$", "", study_id).strip().lower()
        packet_dob = nk_dob.get(_nk, "")
        packet_sex = nk_sex.get(_nk, "")

        for rec in data.get("section_records", []):
            dt = rec.get("doc_type", "")
            flds = rec.get("fields")
            if not flds:
                continue

            if dt == "tech_scan_report":
                # Skip ghost sections (segmentation artifact: all key fields null)
                key_vals = [flds.get(k) for k in ("patient_name", "eeg_start_date", "background", "technologist_impression")]
                if all(v is None for v in key_vals):
                    continue
                tt = parse_test_type(safe_str(flds.get("test_type")))
                studies.write({
                    "study_id": study_id,
                    "patient_name": safe_str(flds.get("patient_name")),
                    "patient_dob": packet_dob,
                    "patient_sex": packet_sex,
                    "eeg_start_date": safe_str(flds.get("eeg_start_date")),
                    "eeg_start_time": safe_str(flds.get("eeg_start_time")),
                    "eeg_end_date": safe_str(flds.get("eeg_end_date")),
                    "eeg_end_time": safe_str(flds.get("eeg_end_time")),
                    "test_type_raw": safe_str(flds.get("test_type")),
                    "duration_hours": tt["duration_hours"],
                    "has_video": tt["has_video"],
                    "is_ambulatory": tt["is_ambulatory"],
                    "n_patient_events": safe_int(flds.get("n_patient_events")),
                    "n_patient_events_video": safe_str(flds.get("n_patient_events_video")),
                    "n_tech_events": safe_int(flds.get("n_tech_events")),
                    "automated_seizure_detections": safe_int(flds.get("automated_seizures")),
                    "automated_spike_detections": safe_int(flds.get("automated_spikes")),
                    "tech_comments": safe_str(flds.get("tech_comments")),
                    "scanning_technologist": safe_str(flds.get("scanning_technologist")),
                    "source_pdf": pdf_name,
                })

                pdr = parse_pdr(safe_str(flds.get("background")))
                bg_csv.write({
                    "study_id": study_id,
                    "pdr_frequency_hz": pdr["pdr_frequency_hz"],
                    "pdr_symmetry": pdr["pdr_symmetry"],
                    "pdr_reactivity": pdr["pdr_reactivity"],
                    "raw_background_text": safe_str(flds.get("background")),
                })

                act_csv.write({
                    "study_id": study_id,
                    "photic_stimulation": safe_str(flds.get("photic_stimulation")),
                    "hyperventilation": safe_str(flds.get("hyperventilation")),
                })

                sl = safe_str(flds.get("slowing"))
                if sl and not re.match(r"(?i)^(no|none)", sl):
                    slow_csv.write({"study_id": study_id, "raw_description": sl})

                ep = safe_str(flds.get("epileptiform_discharges"))
                if ep and not re.match(r"(?i)^(no|none)", ep):
                    epi_csv.write({"study_id": study_id, "raw_description": ep})

                szr = safe_str(flds.get("seizures"))
                if szr and not re.match(r"(?i)^(no|none)", szr):
                    sz_csv.write({"study_id": study_id, "raw_description": szr})

                imp = safe_str(flds.get("technologist_impression"))
                imp_csv.write({
                    "study_id": study_id,
                    "classification": classify_impression(imp),
                    "raw_text": imp,
                })

                # Patient events with timestamps from the tech report
                for ev in flds.get("patient_events") or []:
                    pat_evt.write({
                        "study_id": study_id,
                        "event_number": safe_int(ev.get("event_number")),
                        "date": safe_str(ev.get("date")),
                        "time": safe_str(ev.get("time")),
                        "description": safe_str(ev.get("description")),
                    })

            elif dt == "eeg_intake_form":
                for code in flds.get("diagnosis_codes") or []:
                    if isinstance(code, str) and code.strip():
                        diag.write({
                            "study_id": study_id,
                            "code": code.strip(),
                            "source": "intake_form",
                        })

            elif dt == "trackit_monitoring_log":
                mon_sum.write({
                    "study_id": study_id,
                    "n_hours_total": safe_int(flds.get("n_hours_total")),
                    "n_hours_recording_on": safe_int(flds.get("n_hours_recording_on")),
                    "n_hours_recording_off": safe_int(flds.get("n_hours_recording_off")),
                    "n_eeg_reviewed_notes": safe_int(flds.get("n_eeg_reviewed_notes")),
                    "n_general_notes": safe_int(flds.get("n_general_notes")),
                    "n_equipment_failures": safe_int(flds.get("n_equipment_failures")),
                    "date_range_first": safe_str(flds.get("date_range_first")),
                    "date_range_last": safe_str(flds.get("date_range_last")),
                    "n_distinct_days": safe_int(flds.get("n_distinct_days")),
                    "n_distinct_reviewers": str(len(flds.get("distinct_reviewers") or [])),
                    "distinct_reviewers": safe_str(flds.get("distinct_reviewers")),
                })

                for hr in flds.get("hourly_rows") or []:
                    mon_hrs.write({
                        "study_id": study_id,
                        "date": safe_str(hr.get("date")),
                        "time_start": safe_str(hr.get("time_start")),
                        "time_end": safe_str(hr.get("time_end")),
                        "timezone": safe_str(hr.get("timezone")),
                        "recording_on": safe_str(hr.get("recording_on")),
                        "impedance": safe_str(hr.get("impedance")),
                        "battery_pct": safe_int(hr.get("battery_pct")),
                        "reviewer_name": safe_str(hr.get("reviewer_name")),
                        "review_timestamp": safe_str(hr.get("review_timestamp")),
                    })

                for ev in flds.get("events") or []:
                    mon_evt.write({
                        "study_id": study_id,
                        "event_type": safe_str(ev.get("event_type")),
                        "date": safe_str(ev.get("date")),
                        "hour_start": safe_str(ev.get("hour_start")),
                        "reviewer_name": safe_str(ev.get("reviewer_name")),
                        "description": safe_str(ev.get("description")),
                    })

            elif dt in ("clinical_progress_note", "history_and_physical"):
                enc_csv.write({
                    "study_id": study_id,
                    "encounter_type": dt,
                    "encounter_date": safe_str(flds.get("note_date") or flds.get("encounter_date")),
                    "provider_name": safe_str(flds.get("provider_name")),
                    "provider_specialty": safe_str(flds.get("provider_specialty")),
                    "department": safe_str(flds.get("department")),
                    "chief_complaint": safe_str(flds.get("chief_complaint")),
                    "reason_for_consultation": safe_str(flds.get("reason_for_consultation")),
                    "hpi_summary": safe_str(flds.get("hpi_summary") or flds.get("history_of_present_illness")),
                    "neurological_exam": safe_str(flds.get("neurological_exam") or flds.get("physical_exam")),
                    "assessment_plan": safe_str(flds.get("assessment_plan") or flds.get("assessment")),
                    "follow_up": safe_str(flds.get("follow_up") or flds.get("plan")),
                })

                for cond in flds.get("past_medical_history") or []:
                    if isinstance(cond, str) and cond.strip():
                        cond_csv.write({
                            "study_id": study_id,
                            "encounter_type": dt,
                            "condition_name": cond.strip(),
                        })

                for med in flds.get("current_medications") or []:
                    if isinstance(med, dict):
                        med_csv.write({
                            "study_id": study_id,
                            "encounter_type": dt,
                            "name_as_stated": safe_str(med.get("name")),
                            "dose": safe_str(med.get("dose")),
                            "frequency": safe_str(med.get("frequency")),
                        })

                for code_obj in flds.get("icd10_codes") or []:
                    if isinstance(code_obj, dict):
                        c = safe_str(code_obj.get("code"))
                        if c:
                            diag.write({
                                "study_id": study_id,
                                "code": c,
                                "source": dt,
                            })

            elif dt == "imaging_report":
                img_csv.write({
                    "study_id": study_id,
                    "modality": safe_str(flds.get("modality")),
                    "anatomy": safe_str(flds.get("anatomy")),
                    "study_date": safe_str(flds.get("study_date")),
                    "indication": safe_str(flds.get("indication")),
                    "findings": safe_str(flds.get("findings")),
                    "impression": safe_str(flds.get("impression")),
                })

            elif dt == "lab_results":
                abnormal = flds.get("abnormal_findings") or []
                img_str = "; ".join(
                    f"{a.get('analyte','?')}: {a.get('value','?')} [{a.get('flag','')}]"
                    for a in abnormal if isinstance(a, dict)
                ) if abnormal else ""
                lab_csv.write({
                    "study_id": study_id,
                    "panel_name": safe_str(flds.get("panel_name")),
                    "draw_date": safe_str(flds.get("draw_date")),
                    "ordering_provider": safe_str(flds.get("ordering_provider")),
                    "abnormal_findings": img_str,
                })

            elif dt == "patient_event_log":
                for ev in flds.get("events") or []:
                    if isinstance(ev, dict):
                        pat_evt.write({
                            "study_id": study_id,
                            "event_number": "",
                            "date": safe_str(ev.get("date")),
                            "time": safe_str(ev.get("time")),
                            "description": safe_str(ev.get("description")),
                        })

    for w in all_writers:
        w.close()

    log("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
