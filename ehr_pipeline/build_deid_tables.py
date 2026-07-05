#!/usr/bin/env python3
"""
Build the committed, de-identified aggregate tables in output/ehr_deid_tables/.

These are the ONLY EHR tables committed to the repository, and every EHR number
in the manuscript must be reproducible from them (see reproduce_manuscript_numbers.py
and REPRODUCIBILITY.md). This script is the missing pipeline stage that produces them.

Inputs (PHI, gitignored, produced by build_csvs.py at pipeline Stage 4):
  output/ehr/studies.csv                 (needs patient_dob, patient_sex columns —
                                          added to build_csvs.py; re-run Stage 4)
  output/ehr/diagnosis_codes.csv
  output/ehr/conditions.csv
  output/ehr/medications.csv
  output/ehr/eeg_background.csv
  output/ehr/eeg_epileptiform.csv
  output/ehr/eeg_seizures.csv
  output/ehr/eeg_slowing.csv
  output/ehr/technologist_impression.csv
  output/ehr/monitoring_summary.csv
  output/ehr/ehr_eeg_crosswalk.csv       (study_id -> BDSPPatientID, from build_crosswalk.py)

Outputs (de-identified, COMMITTED):
  output/ehr_deid_tables/*.csv           (keyed by bdsp_id; structured columns only —
                                          NO names, NO raw dates/DOB, NO free text)

De-identification guarantees enforced here:
  - study_id (an EHR folder name containing the patient name) is replaced by BDSPPatientID.
  - Only the whitelisted structured columns in SPEC below are emitted. Free-text columns
    (raw_description, raw_background_text, raw_text, tech_comments, patient_name,
    scanning_technologist, source_pdf) and raw dates/DOB are dropped.
  - Age is emitted as an integer-ish year value derived from (eeg_start_date - dob); the
    raw dates themselves are never written.

This fixes the defects in the previous (uncommitted, hand-run) reduction:
  * diagnosis_codes.csv had the ICD `code` column stripped  -> restored (ICD category is
    not PHI and is needed for Figure 3A / referral indications).
  * monitoring hour counts were dropped                     -> restored.
  * comorbidities and medications tables were missing       -> added.

Run (on the machine with output/ehr/ populated):
  .venv/bin/python ehr_pipeline/build_deid_tables.py
Then validate:
  .venv/bin/python reproduce_manuscript_numbers.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EHR = ROOT / "output" / "ehr"
XWALK = EHR / "ehr_eeg_crosswalk.csv"
OUT = ROOT / "output" / "ehr_deid_tables"
# Per-packet field-file glob for demographics (override for an isolated Qwen run).
FIELDS_GLOB = "*.fields.json"

# Only crosswalk rows at these confidences are de-identified/released
# (mirrors deidentify_ehr.py eligibility).
ELIGIBLE_CONFIDENCE = {"high", "medium"}

# For each output table: source CSV under output/ehr/ and the structured, non-PHI
# columns to keep. The join key (study_id) is always mapped to bdsp_id and is implied.
SPEC = {
    "studies.csv": ("studies.csv", [
        "duration_hours", "has_video", "is_ambulatory", "n_patient_events",
        "automated_seizure_detections", "automated_spike_detections",
    ]),
    "diagnosis_codes.csv": ("diagnosis_codes.csv", ["code"]),          # FIX: keep ICD code
    "eeg_background.csv": ("eeg_background.csv", [
        "pdr_frequency_hz", "pdr_symmetry", "pdr_reactivity",
    ]),
    # eeg_epileptiform is built separately (build_epileptiform_flags) — it derives
    # non-PHI categorical flags from raw_description, then drops the free text.
    "eeg_seizures.csv": ("eeg_seizures.csv", []),
    "eeg_slowing.csv": ("eeg_slowing.csv", []),
    "technologist_impression.csv": ("technologist_impression.csv", ["classification"]),
    "monitoring_summary.csv": ("monitoring_summary.csv", [            # FIX: keep hour counts
        "n_hours_total", "n_hours_recording_on", "n_hours_recording_off",
        "n_distinct_days",
    ]),
}


def load(name: str) -> pd.DataFrame:
    p = EHR / name
    if not p.exists():
        print(f"  ! missing input: {p}")
        return pd.DataFrame()
    return pd.read_csv(p, dtype=str, keep_default_na=False)


def build_crosswalk_map() -> dict[str, str]:
    xw = pd.read_csv(XWALK, dtype=str, keep_default_na=False)
    xw = xw[(xw["BDSPPatientID"] != "") & (xw["match_confidence"].isin(ELIGIBLE_CONFIDENCE))]
    # ehr_study_id is the studies.csv study_id (== patient_folder name)
    return dict(zip(xw["ehr_study_id"], xw["BDSPPatientID"]))


def remap(df: pd.DataFrame, id2bdsp: dict[str, str], keep: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["bdsp_id"] = df["study_id"].map(id2bdsp)
    df = df[df["bdsp_id"].notna() & (df["bdsp_id"] != "")]
    cols = ["bdsp_id"] + [c for c in keep if c in df.columns]
    missing = [c for c in keep if c not in df.columns]
    if missing:
        print(f"    (warning: columns not found, skipped: {missing})")
    return df[cols]


# Any date more specific than a year is a HIPAA identifier. LLM-extracted free-text
# condition/medication names occasionally carry a raw (un-shifted) date; strip them.
_DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b|\b\d{4}-\d{1,2}-\d{1,2}\b")


def scrub_dates(s: str) -> str:
    """Remove MM/DD/YY(YY)-style dates from a free-text string (HIPAA safe-harbor)."""
    return _DATE_RE.sub("", s or "")


def normalize_name(s: str) -> str:
    """Normalize a drug / condition name: scrub dates, strip dose/qualifiers, title-case."""
    s = scrub_dates((s or "").strip())
    s = re.split(r"[\(,;]| \d", s, 1)[0]          # cut at dose/paren/comma
    s = re.sub(r"\s+", " ", s).strip(" -")        # trim leading/trailing sep, keep internal hyphens
    return s.title()


def build_age_sex(id2bdsp: dict[str, str]) -> pd.DataFrame:
    """demographics.csv: age at first EEG + sex, keyed by bdsp_id. No raw dates.

    Reads fields.json at build time (SSD) using the SAME validated date parser as the
    figure pipeline (generate_tables_and_figures.parse_date) so the committed table
    matches the manuscript's demographics exactly. dob is on eeg_intake_form; the first
    EEG date is the earliest eeg_start_date across the patient's tech reports; both share
    the per-patient date shift, so their difference (age) is exact and no date is emitted.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "manuscript-materials"))
    from generate_tables_and_figures import parse_date, normalize_sex  # validated parsers
    SRC = Path("/Volumes/Extreme SSD/neurotech-data")
    nk2bdsp = {}
    for sid, b in id2bdsp.items():
        nk2bdsp.setdefault(re.sub(r"-\d+$", "", str(sid)).strip().lower(), b)
    dob, sex, first = {}, {}, {}
    for ff in sorted(SRC.rglob(FIELDS_GLOB)):   # sorted -> deterministic first-seen
        try:
            d = json.loads(ff.read_text(encoding="utf-8"))
        except Exception:
            continue
        nk = re.sub(r"-\d+$", "", d.get("patient_folder", "")).strip().lower()
        for r in d.get("section_records", []):
            f = r.get("fields") or {}
            if r.get("doc_type") == "eeg_intake_form":
                if f.get("dob") and nk not in dob:
                    dd = parse_date(str(f["dob"]))
                    if dd and 1920 < dd.year < 2025:
                        dob[nk] = dd
                if f.get("sex") and nk not in sex:
                    s = normalize_sex(str(f["sex"]))
                    if s:
                        sex[nk] = s
            elif r.get("doc_type") == "tech_scan_report" and f.get("eeg_start_date"):
                dp = parse_date(str(f["eeg_start_date"]))
                if dp and (nk not in first or dp < first[nk]):
                    first[nk] = dp
    rows = []
    for nk in sorted(set(list(dob) + list(sex))):   # sorted -> stable dedup on bdsp_id
        b = nk2bdsp.get(nk)
        if not b:
            continue
        age = ""
        if nk in dob and nk in first and first[nk] > dob[nk]:
            a = round((first[nk] - dob[nk]).days / 365.25, 1)   # round first, then bound-check
            if 0 < a < 120:
                age = a
        s = sex.get(nk, "")
        rows.append({"bdsp_id": b, "age_years": age,
                     "sex": "M" if s in ("M", "Male") else ("F" if s in ("F", "Female") else "")})
    return pd.DataFrame(rows).drop_duplicates("bdsp_id")


def _unused_build_age_sex(studies: pd.DataFrame, id2bdsp: dict[str, str]) -> pd.DataFrame:
    if studies.empty:
        return pd.DataFrame(columns=["bdsp_id", "age_years", "sex"])
    df = studies.copy()
    df["bdsp_id"] = df["study_id"].map(id2bdsp)
    df = df[df["bdsp_id"].notna() & (df["bdsp_id"] != "")]
    df["dob"] = pd.to_datetime(df.get("patient_dob", ""), errors="coerce")
    df["eeg"] = pd.to_datetime(df.get("eeg_start_date", ""), errors="coerce")
    df["sexn"] = (df.get("patient_sex", "").astype(str).str.strip().str.upper().str[:1]
                    .map({"M": "M", "F": "F"}))
    # One row per patient: dob/sex from ANY of their studies that record it, age from
    # the EARLIEST EEG. dob and eeg_start_date share the same per-patient date shift, so
    # (eeg - dob) is exact; raw dates are never emitted.
    rows = []
    for bid, g in df.groupby("bdsp_id"):
        dob = g["dob"].dropna().min()
        eeg = g["eeg"].dropna().min()
        sx = g["sexn"].dropna()
        age = ""
        if pd.notna(dob) and pd.notna(eeg) and eeg > dob:
            a = (eeg - dob).days / 365.25
            if 0 < a < 120:
                age = round(a, 1)
        rows.append({"bdsp_id": bid, "age_years": age, "sex": sx.iloc[0] if len(sx) else ""})
    return pd.DataFrame(rows)


# Categorical IED flags derived from raw_description. These are clinical
# categorizations (morphology / distribution / laterality / region), NOT PHI —
# they let Figure 4B and Supp Table 4 be reproduced from committed data while the
# underlying free-text description is dropped. Patterns mirror the ones in
# manuscript-materials/generate_tables_and_figures.py exactly.
IED_FLAGS = [
    ("is_spike", r"\bspike\b"), ("is_sharp_wave", r"sharp wave|sharps"),
    ("is_spike_wave", r"spike.and.wave|spike.wave"), ("is_polyspike", r"polyspike"),
    ("is_generalized", r"generalized"), ("is_focal", r"focal"),
    ("is_multifocal", r"multifocal"), ("is_bilateral", r"bilateral"),
    ("is_bilateral_independent", r"bilateral.independent"),
    ("is_left", r"left"), ("is_right", r"right"),
    ("is_temporal", r"temporal"), ("is_frontal", r"frontal"),
    ("is_central", r"central"), ("is_parietal", r"parietal"),
    ("is_occipital", r"occipital"),
]


def build_epileptiform_flags(id2bdsp: dict[str, str]) -> pd.DataFrame:
    """eeg_epileptiform.csv: bdsp_id + non-PHI categorical flags (raw text dropped)."""
    df = load("eeg_epileptiform.csv")
    if df.empty:
        return pd.DataFrame(columns=["bdsp_id"])
    df = df.copy()
    df["bdsp_id"] = df["study_id"].map(id2bdsp)
    df = df[df["bdsp_id"].notna() & (df["bdsp_id"] != "")]
    desc = df.get("raw_description", "").astype(str).str.lower()
    out = pd.DataFrame({"bdsp_id": df["bdsp_id"].values})
    for col, pat in IED_FLAGS:
        out[col] = desc.str.contains(pat, regex=True, na=False).astype(int).values
    return out


def build_monitoring_hour_of_day() -> pd.DataFrame:
    """24-row hour-of-day histogram from monitoring_hours (aggregate, no patient id)."""
    mh = load("monitoring_hours.csv")
    logged, on = {h: 0 for h in range(24)}, {h: 0 for h in range(24)}
    if not mh.empty:
        for ts, rec in zip(mh.get("time_start", ""), mh.get("recording_on", "")):
            m = re.match(r"(\d{1,2}):\d{2}\s*(AM|PM)", str(ts), re.I)
            if not m:
                continue
            h = int(m.group(1)) % 12 + (12 if m.group(2).upper() == "PM" else 0)
            logged[h] += 1
            if str(rec) == "True":
                on[h] += 1
    return pd.DataFrame({"hour": list(range(24)),
                         "n_logged": [logged[h] for h in range(24)],
                         "n_recording_on": [on[h] for h in range(24)]})


def build_monitoring_event_counts() -> pd.DataFrame:
    """Aggregate monitoring-event-type counts (no patient id)."""
    me = load("monitoring_events.csv")
    if me.empty or "event_type" not in me.columns:
        return pd.DataFrame(columns=["event_type", "n"])
    vc = me["event_type"].value_counts()
    return pd.DataFrame({"event_type": vc.index, "n": vc.values})


def build_patient_events(id2bdsp: dict[str, str]) -> pd.DataFrame:
    """patient_events.csv: bdsp_id + has_timestamp flag (raw text/time dropped)."""
    df = load("patient_events.csv")
    if df.empty:
        return pd.DataFrame(columns=["bdsp_id", "has_timestamp"])
    df = df.copy()
    df["bdsp_id"] = df["study_id"].map(id2bdsp)
    df = df[df["bdsp_id"].notna() & (df["bdsp_id"] != "")]
    has_ts = df.get("time", "").astype(str).str.strip().ne("").astype(int)
    return pd.DataFrame({"bdsp_id": df["bdsp_id"].values, "has_timestamp": has_ts.values})


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Build committed de-identified aggregate tables.")
    ap.add_argument("--ehr-dir", type=Path, default=None,
                    help="Input dir of PHI aggregate CSVs (default output/ehr).")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="Output dir for de-id tables (default output/ehr_deid_tables).")
    ap.add_argument("--fields-glob", default=None,
                    help="Per-packet field-file glob for demographics (e.g. *.fields.qwen.json).")
    args = ap.parse_args()

    global EHR, XWALK, OUT, FIELDS_GLOB
    if args.ehr_dir is not None:
        EHR = args.ehr_dir
        XWALK = EHR / "ehr_eeg_crosswalk.csv"
    if args.out_dir is not None:
        OUT = args.out_dir
    if args.fields_glob is not None:
        FIELDS_GLOB = args.fields_glob

    if not XWALK.exists():
        print(f"ERROR: crosswalk not found at {XWALK}\n"
              f"Run ehr_pipeline/build_crosswalk.py first (needs studies.csv in the EHR dir).")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    id2bdsp = build_crosswalk_map()
    print(f"crosswalk: {len(id2bdsp)} eligible study_id -> bdsp_id mappings")

    # 1) whitelist-reduce the straightforward tables
    for out_name, (src_name, keep) in SPEC.items():
        df = remap(load(src_name), id2bdsp, keep)
        # Defense-in-depth: scrub any raw date from free-text-capable columns.
        for col in ("code",):
            if col in df.columns:
                df[col] = df[col].map(scrub_dates).str.strip()
        df.to_csv(OUT / out_name, index=False)
        print(f"  {out_name:32s} {len(df):>7,} rows  (cols: {list(df.columns)})")

    # 2) demographics (derived age + sex; no raw dates)
    demo = build_age_sex(id2bdsp)
    demo.to_csv(OUT / "demographics.csv", index=False)
    print(f"  {'demographics.csv':32s} {len(demo):>7,} rows  "
          f"(age n={demo['age_years'].notna().sum()}, sex n={(demo['sex']!='').sum()})")

    # 3) comorbidities (from conditions.csv) and medications (normalized names) — NEW
    cond = remap(load("conditions.csv"), id2bdsp, ["condition_name"])
    if not cond.empty:
        cond["condition_name"] = cond["condition_name"].map(normalize_name)
        cond = cond[cond["condition_name"] != ""]
    cond.to_csv(OUT / "comorbidities.csv", index=False)
    print(f"  {'comorbidities.csv':32s} {len(cond):>7,} rows")

    med = remap(load("medications.csv"), id2bdsp, ["name_as_stated"])
    if not med.empty:
        med["name"] = med["name_as_stated"].map(normalize_name)
        med = med[["bdsp_id", "name"]]
        med = med[med["name"] != ""]
    med.to_csv(OUT / "medications.csv", index=False)
    print(f"  {'medications.csv':32s} {len(med):>7,} rows")

    # 4) eeg_epileptiform with derived categorical flags (raw text dropped) — NEW
    epi = build_epileptiform_flags(id2bdsp)
    epi.to_csv(OUT / "eeg_epileptiform.csv", index=False)
    print(f"  {'eeg_epileptiform.csv':32s} {len(epi):>7,} rows  (flags: {len(IED_FLAGS)})")

    # 5) monitoring aggregates for Supp Fig 4B / Supp Table 5 (no patient id) — NEW
    hod = build_monitoring_hour_of_day()
    hod.to_csv(OUT / "monitoring_hour_of_day.csv", index=False)
    print(f"  {'monitoring_hour_of_day.csv':32s} {len(hod):>7,} rows  "
          f"(logged={int(hod.n_logged.sum()):,}, on={int(hod.n_recording_on.sum()):,})")
    evc = build_monitoring_event_counts()
    evc.to_csv(OUT / "monitoring_event_counts.csv", index=False)
    print(f"  {'monitoring_event_counts.csv':32s} {len(evc):>7,} rows")

    # 6) patient_events presence + timestamp flag — NEW
    pe = build_patient_events(id2bdsp)
    pe.to_csv(OUT / "patient_events.csv", index=False)
    print(f"  {'patient_events.csv':32s} {len(pe):>7,} rows  "
          f"(with timestamp={int(pe.has_timestamp.sum()) if len(pe) else 0:,})")

    print("\nDone. Validate with: .venv/bin/python reproduce_manuscript_numbers.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
