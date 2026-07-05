#!/usr/bin/env python3
"""
Replace {NEW: ...} placeholders in manuscript-draft.md with current values
from the regenerated CSVs and computed demographics.

After the pipeline finishes, run:
    python manuscript-materials/fill_manuscript_placeholders.py

This produces an in-place edit of manuscript-draft.md AND prints a diff of
what changed, so you can sanity-check before regenerating the docx.

Idempotent: re-running on a file with no placeholders is a no-op. Re-running
after pipeline updates picks up new values.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from datetime import datetime
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# LEGACY: the manuscript no longer contains {NEW: ...} placeholders, so main()
# early-returns and never reads these. Paths point at committed de-identified tables
# (no PHI, no /Volumes drive) so a re-run can never touch source data.
EHR_DIR = ROOT / "output" / "ehr_deid_tables"
DEID_DIR = ROOT / "output" / "ehr_deid_tables"
EHR_SOURCE = ROOT / "output" / "ehr_deid_tables"
MD_PATH = ROOT / "manuscript-materials" / "manuscript-draft.md"

PLACEHOLDER_RE = re.compile(r"\{NEW:\s*([a-zA-Z0-9_]+)\}")


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    delim = "\t" if path.suffix == ".tsv" else ","
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=delim))


def median_iqr(values: list[float], decimals: int = 1) -> str:
    if not values:
        return "N/A"
    arr = sorted(values)
    n = len(arr)
    med = arr[n // 2] if n % 2 else (arr[n // 2 - 1] + arr[n // 2]) / 2
    q1 = arr[n // 4]
    q3 = arr[3 * n // 4]
    if decimals == 0:
        return f"{int(med)} ({int(q1)}-{int(q3)})"
    return f"{med:.{decimals}f} ({q1:.{decimals}f}-{q3:.{decimals}f})"


def parse_date(s: str):
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def compute_ages_and_sex():
    patient_dob, patient_sex, patient_first_eeg = {}, {}, {}
    for ff in EHR_SOURCE.rglob("*.fields.json"):
        try:
            d = json.loads(ff.read_text())
        except Exception:
            continue
        nk = re.sub(r"-\d+$", "", d.get("patient_folder", "")).strip().lower()
        for rec in d.get("section_records", []):
            flds = rec.get("fields") or {}
            if rec.get("doc_type") == "eeg_intake_form":
                dob_s = flds.get("dob")
                if dob_s:
                    dob = parse_date(str(dob_s))
                    if dob and 1920 < dob.year < 2026 and nk not in patient_dob:
                        patient_dob[nk] = dob
                sex_s = (flds.get("sex") or "").lower().strip()
                if sex_s in ("male", "m", "boy") and nk not in patient_sex:
                    patient_sex[nk] = "Male"
                elif sex_s in ("female", "f", "girl") and nk not in patient_sex:
                    patient_sex[nk] = "Female"
            if rec.get("doc_type") == "tech_scan_report":
                sd = flds.get("eeg_start_date")
                if sd:
                    dp = parse_date(str(sd))
                    if dp and (nk not in patient_first_eeg or dp < patient_first_eeg[nk]):
                        patient_first_eeg[nk] = dp
    ages = []
    for nk, dob in patient_dob.items():
        eeg = patient_first_eeg.get(nk)
        if eeg and eeg > dob:
            age = (eeg - dob).days / 365.25
            if 0 < age < 120:
                ages.append(age)
    return ages, patient_sex, patient_dob


def main():
    if not MD_PATH.exists():
        sys.exit(f"manuscript not found at {MD_PATH}")

    text = MD_PATH.read_text()
    placeholders = sorted(set(PLACEHOLDER_RE.findall(text)))
    print(f"Placeholders to fill: {placeholders}")
    if not placeholders:
        print("No placeholders found. Done.")
        return

    # Load source data
    studies = load_csv(EHR_DIR / "studies.csv")
    diag = load_csv(EHR_DIR / "diagnosis_codes.csv")
    epi = load_csv(EHR_DIR / "eeg_epileptiform.csv")
    sz = load_csv(EHR_DIR / "eeg_seizures.csv")
    bg = load_csv(EHR_DIR / "eeg_background.csv")
    imp = load_csv(EHR_DIR / "technologist_impression.csv")
    enc = load_csv(EHR_DIR / "clinical_encounters.csv")
    meds = load_csv(EHR_DIR / "medications.csv")
    sumtbl = load_csv(EHR_DIR / "sections_summary.tsv") if (EHR_DIR / "sections_summary.tsv").exists() else []
    crosswalk = load_csv(EHR_DIR / "ehr_eeg_crosswalk.csv")
    monitoring_summary = load_csv(EHR_DIR / "monitoring_summary.csv")
    monitoring_hours = load_csv(EHR_DIR / "monitoring_hours.csv")
    monitoring_events = load_csv(EHR_DIR / "monitoring_events.csv")

    # Demographics
    ages, sex_map, dob_map = compute_ages_and_sex()

    # Counts
    n_studies = len(studies)
    n_dx = len(diag)
    n_pdr = sum(1 for r in bg if r.get("pdr_frequency_hz"))
    n_ied = len(epi)
    n_seizures_studies = len(sz)
    seizure_pct = round(n_seizures_studies / max(n_studies, 1) * 100)
    n_imp = len(imp)
    n_normal = sum(1 for r in imp if r.get("classification") == "normal")
    n_abnormal = sum(1 for r in imp if r.get("classification") == "abnormal")
    abnormal_pct = round(n_abnormal / max(n_imp, 1) * 100)

    # ICD code group rates
    g40_n = sum(1 for r in diag if r.get("code", "").upper().startswith("G40"))
    r56_n = sum(1 for r in diag if r.get("code", "").upper().startswith("R56"))
    r25_n = sum(1 for r in diag if r.get("code", "").upper().startswith("R25"))
    g40_pct = round(g40_n / max(n_dx, 1) * 100)
    r56_pct = round(r56_n / max(n_dx, 1) * 100)
    r25_pct = round(r25_n / max(n_dx, 1) * 100)

    # Crosswalk match rate (per unique patient)
    cw_unique = {}
    for r in crosswalk:
        nk = (r.get("ehr_last_name", "") + "|" + r.get("ehr_first_name", "")).lower()
        if nk not in cw_unique:
            cw_unique[nk] = r
    n_cw_total = len(cw_unique)
    n_cw_matched = sum(1 for r in cw_unique.values()
                        if r.get("BDSPPatientID") and r.get("match_confidence") in ("high", "medium"))
    crosswalk_match_pct = round(n_cw_matched / max(n_cw_total, 1) * 100, 1)
    n_unmatched_or_low = n_cw_total - n_cw_matched
    n_total_ehr_folders = len(crosswalk)  # all folders, not unique patients
    unmatched_pct = round(100 - crosswalk_match_pct, 1)

    # EHR coverage (unique patients with extracted data, vs 1,741 BIDS patients)
    n_ehr_patients = n_cw_matched
    ehr_coverage_pct = round(n_ehr_patients / 1741 * 100)

    # Sub-document count from sections_summary.tsv (one row per sub-document)
    n_subdocs = len(sumtbl) if sumtbl else 0
    if not n_subdocs:
        # Fallback: count from fields.json files
        n_subdocs = sum(
            len(json.loads(ff.read_text()).get("section_records", []))
            for ff in list(EHR_SOURCE.rglob("*.fields.json"))[:100]
        ) * (len(list(EHR_SOURCE.rglob("*.fields.json"))) / 100) if list(EHR_SOURCE.rglob("*.fields.json")) else 0

    # OCR percentage from manifest (TSV)
    manifest = load_csv(EHR_DIR / "manifest.tsv")
    if manifest:
        n_ok = sum(1 for r in manifest if r.get("status") == "ok")
        n_ocr = sum(1 for r in manifest if r.get("ocr_applied") == "yes")
        ocr_pct = round(n_ocr / max(n_ok, 1) * 100) if n_ok else 80
    else:
        ocr_pct = 80

    # Coverage percentages: denominator = unique patients with extracted EHR data
    # (study_ids in clinical encounters / studies / etc. are the unique EHR patients we have data for)
    n_ehr_studied = len(set(r["study_id"] for r in studies))
    if n_ehr_studied == 0:
        n_ehr_studied = n_ehr_patients
    age_pct = min(100, round(len(ages) / max(n_ehr_studied, 1) * 100))
    sex_pct = min(100, round(len(sex_map) / max(n_ehr_studied, 1) * 100))
    dx_pct = min(100, round(len(set(r["study_id"] for r in diag)) / max(n_ehr_studied, 1) * 100))
    asm_names = {"levetiracetam","keppra","lamotrigine","lamictal","valproate","clobazam","onfi",
                  "lacosamide","vimpat","diazepam","zonisamide","topiramate","topamax","carbamazepine",
                  "tegretol","oxcarbazepine","trileptal","phenytoin","gabapentin","brivaracetam",
                  "perampanel","ethosuximide","cenobamate","clonazepam","klonopin","pregabalin",
                  "phenobarbital","primidone","cannabidiol","epidiolex"}
    asm_patients = set()
    for r in meds:
        n = r.get("name_as_stated", "").lower()
        if any(a in n for a in asm_names):
            asm_patients.add(r.get("study_id", ""))
    asm_pct = min(100, round(len(asm_patients) / max(n_ehr_studied, 1) * 100))

    # Age stats
    age_median = int(round(sorted(ages)[len(ages) // 2])) if ages else 0
    if ages:
        arr = sorted(ages)
        q1 = int(round(arr[len(arr) // 4]))
        q3 = int(round(arr[3 * len(arr) // 4]))
        age_iqr = f"{q1}-{q3}"
    else:
        age_iqr = "N/A"

    # Monitoring metrics
    n_monitoring_studies = len(monitoring_summary)
    total_monitoring_hours = len(monitoring_hours)
    hours_active = sum(1 for r in monitoring_hours if r.get("recording_on") == "True")
    hours_gap = total_monitoring_hours - hours_active
    active_pct = round(hours_active / max(total_monitoring_hours, 1) * 100)
    gap_pct = 100 - active_pct
    n_mon_evt = len(monitoring_events)
    evt_types = Counter(r.get("event_type") for r in monitoring_events)
    n_reviewed = evt_types.get("eeg_reviewed", 0)
    n_general_notes = evt_types.get("general_note", 0)
    n_equipment_failures = evt_types.get("equipment_failure", 0)
    revs_per_study = [int(r.get("n_distinct_reviewers", 0) or 0) for r in monitoring_summary]
    reviewers_iqr = median_iqr([float(v) for v in revs_per_study], decimals=1) if revs_per_study else "N/A"

    # Build replacement map
    repl = {
        "n_ehr_patients": f"{n_ehr_patients:,}",
        "ehr_coverage_pct": str(ehr_coverage_pct),
        "ocr_pct": str(ocr_pct),
        "n_subdocs": f"{int(n_subdocs):,}",
        "crosswalk_match_pct": f"{crosswalk_match_pct:.1f}",
        "unmatched_pct": f"{unmatched_pct:.1f}",
        "n_unmatched_or_low": f"{n_unmatched_or_low:,}",
        "n_total_ehr_folders": f"{n_total_ehr_folders:,}",
        "n_ages": f"{len(ages):,}",
        "n_sex": f"{len(sex_map):,}",
        "age_median": str(age_median),
        "age_iqr": age_iqr,
        "age_pct": str(age_pct),
        "sex_pct": str(sex_pct),
        "dx_pct": str(dx_pct),
        "asm_pct": str(asm_pct),
        "g40_pct": str(g40_pct),
        "r56_pct": str(r56_pct),
        "r25_pct": str(r25_pct),
        "abnormal_pct": str(abnormal_pct),
        "n_dx_codes": f"{n_dx:,}",
        "n_pdr": f"{n_pdr:,}",
        "n_ied": f"{n_ied:,}",
        "n_seizures": f"{n_seizures_studies:,}",
        "n_studies": f"{n_studies:,}",
        "seizure_pct": str(seizure_pct),
        "n_monitoring_studies": f"{n_monitoring_studies:,}",
        "total_monitoring_hours": f"{total_monitoring_hours:,}",
        "hours_active": f"{hours_active:,}",
        "hours_gap": f"{hours_gap:,}",
        "active_pct": str(active_pct),
        "gap_pct": str(gap_pct),
        "n_monitoring_events": f"{n_mon_evt:,}",
        "n_reviewed": f"{n_reviewed:,}",
        "n_general_notes": f"{n_general_notes:,}",
        "n_equipment_failures": str(n_equipment_failures),
        "reviewers_iqr": reviewers_iqr,
    }

    # Apply replacements
    missing = []
    def replace(m):
        key = m.group(1)
        if key in repl:
            return repl[key]
        missing.append(key)
        return m.group(0)

    new_text = PLACEHOLDER_RE.sub(replace, text)

    if missing:
        print(f"\n  WARNING: {len(set(missing))} placeholder keys had no value mapping:")
        for k in sorted(set(missing)):
            print(f"    {{NEW: {k}}}")

    # Print value summary for sanity check
    print("\n  Resolved values:")
    for key in sorted(placeholders):
        val = repl.get(key, "(unresolved)")
        print(f"    {key:>25} = {val}")

    # Write back (create backup first)
    if new_text != text:
        backup = MD_PATH.with_suffix(".md.bak")
        shutil.copy2(MD_PATH, backup)
        MD_PATH.write_text(new_text)
        print(f"\n  Wrote: {MD_PATH}")
        print(f"  Backup: {backup}")
    else:
        print("\n  No changes made.")


if __name__ == "__main__":
    main()
