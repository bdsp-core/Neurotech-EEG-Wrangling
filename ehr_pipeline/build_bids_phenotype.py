#!/usr/bin/env python3
"""
Build BIDS phenotype/ tables (PATIENT-LEVEL) for the public Neurotech EEG release.

Attaches the committed, de-identified EHR clinical metadata to the published BIDS
dataset as a top-level `phenotype/` directory (per-measure TSV + JSON data dictionary,
keyed by participant_id), per EHR_METADATA_RELEASE_PLAN.md.

Inputs (committed, PHI-free):
  output/ehr_deid_tables/*.csv   (keyed by bdsp_id = Neurotech-<N>)
  output/s3_recordings.csv       (the published BIDS subjects + recording counts)

Outputs (de-identified, patient-level; -> later synced to S3):
  output/bids_phenotype/phenotype/*.tsv + *.json
  output/bids_phenotype/participants_clinical.tsv   (scalar columns to merge into participants.tsv)

Decisions baked in (from EHR_METADATA_RELEASE_PLAN.md sign-off):
  - PATIENT-LEVEL only: study-level rows are aggregated to one row per patient.
  - Ages >89 are top-coded to 90 (HIPAA safe harbor).
  - Full ICD-10 codes retained.
  - Restricted to subjects actually published in the BIDS dataset.
  - No dates, names, or free text (the source de-id tables already exclude these; re-audited here).

Run:  .venv/bin/python ehr_pipeline/build_bids_phenotype.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEID = ROOT / "output" / "ehr_deid_tables"
REC = ROOT / "output" / "s3_recordings.csv"
OUT = ROOT / "output" / "bids_phenotype"
PHENO = OUT / "phenotype"
AGE_CAP = 90  # HIPAA: ages >89 top-coded

PROVENANCE = ("De-identified structured fields extracted from technologist scan reports and "
              "intake forms (LLM-assisted). Patient-level; no dates, names, or free text.")


def bdsp_to_participant(bdsp_id: str) -> str:               # Neurotech-123 -> sub-Neurotech123
    return "sub-" + str(bdsp_id).replace("-", "")


def load(name: str) -> pd.DataFrame:
    p = DEID / name
    return pd.read_csv(p, dtype=str, keep_default_na=False) if p.exists() else pd.DataFrame()


def published_participants() -> set[str]:
    rec = pd.read_csv(REC)
    return {str(s) for s in rec["subject"].unique()}         # sub-NeurotechN


def write_tsv_json(df: pd.DataFrame, name: str, descriptions: dict):
    PHENO.mkdir(parents=True, exist_ok=True)
    df.to_csv(PHENO / f"{name}.tsv", sep="\t", index=False, na_rep="n/a")
    meta = {"MeasurementToolMetadata": {"Description": PROVENANCE},
            "participant_id": {"Description": "BIDS participant identifier (sub-NeurotechN)."}}
    meta.update(descriptions)
    with open(PHENO / f"{name}.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  phenotype/{name}.tsv  {len(df):>6,} rows  ({df['participant_id'].nunique():,} patients)")


# Strip standalone 4-digit years (historical event years incidentally captured in
# free-text condition/medication names). Conservative: won't touch years embedded in
# alphanumeric tokens like the chromosome locus "Xq11.1911.2".
_YEAR = re.compile(r'(?<![\w.])(19|20)\d{2}(?![\w.])')


def clean_text(s: str) -> str:
    s = _YEAR.sub("", str(s))
    s = re.sub(r'[~"“”]', "", s)
    return re.sub(r"\s+", " ", s).strip(" -–—.,;")


def keyed(df: pd.DataFrame, pub: set[str]) -> pd.DataFrame:
    """Map bdsp_id -> participant_id and restrict to published subjects."""
    if df.empty:
        return df
    df = df.copy()
    df["participant_id"] = df["bdsp_id"].map(bdsp_to_participant)
    return df[df["participant_id"].isin(pub)].drop(columns=["bdsp_id"])


def main() -> int:
    pub = published_participants()
    print(f"Published BIDS subjects: {len(pub):,}")
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- demographics (age top-coded, sex) --------------------------------
    demo = keyed(load("demographics.csv"), pub)
    demo["age"] = pd.to_numeric(demo["age_years"], errors="coerce").clip(upper=AGE_CAP)
    demo = demo[["participant_id", "age", "sex"]].dropna(subset=["age"]).drop_duplicates("participant_id")
    write_tsv_json(demo, "demographics", {
        "age": {"Description": f"Age at first EEG (years). Ages >89 top-coded to {AGE_CAP}.", "Units": "years"},
        "sex": {"Description": "Reported sex.", "Levels": {"M": "male", "F": "female"}}})

    # ---- diagnoses / comorbidities / medications (long, unique per patient) -
    diag = keyed(load("diagnosis_codes.csv"), pub)[["participant_id", "code"]].rename(
        columns={"code": "icd10_code"}).query("icd10_code != ''").drop_duplicates()
    write_tsv_json(diag, "diagnoses", {
        "icd10_code": {"Description": "Full ICD-10 referral/diagnosis code (one row per patient-code)."}})

    com = keyed(load("comorbidities.csv"), pub)[["participant_id", "condition_name"]].rename(
        columns={"condition_name": "condition"})
    com["condition"] = com["condition"].map(clean_text)
    com = com.query("condition != ''").drop_duplicates()
    write_tsv_json(com, "comorbidities", {
        "condition": {"Description": "Comorbid condition from clinical notes (one row per patient-condition)."}})

    med = keyed(load("medications.csv"), pub)[["participant_id", "name"]].rename(
        columns={"name": "medication"})
    med["medication"] = med["medication"].map(clean_text)
    med = med.query("medication != ''").drop_duplicates()
    write_tsv_json(med, "medications", {
        "medication": {"Description": "Medication (normalized name; one row per patient-medication)."}})

    # ---- EEG findings, aggregated study-level -> patient-level -------------
    def pids(tbl):
        d = keyed(load(tbl), pub)
        return set(d["participant_id"]) if not d.empty else set()
    epi, sz, slw = pids("eeg_epileptiform.csv"), pids("eeg_seizures.csv"), pids("eeg_slowing.csv")
    imp = keyed(load("technologist_impression.csv"), pub)
    abn = set(imp[imp["classification"] == "abnormal"]["participant_id"])
    bg = keyed(load("eeg_background.csv"), pub)
    bg["pdr"] = pd.to_numeric(bg["pdr_frequency_hz"].str.split("-").str[0], errors="coerce")
    pdr_med = bg.groupby("participant_id")["pdr"].median()

    find = pd.DataFrame({"participant_id": sorted(pub & (
        set(imp["participant_id"]) | epi | sz | slw | set(bg["participant_id"])))})
    find["ever_abnormal"] = find["participant_id"].isin(abn).astype(int)
    find["any_epileptiform"] = find["participant_id"].isin(epi).astype(int)
    find["any_seizure"] = find["participant_id"].isin(sz).astype(int)
    find["any_slowing"] = find["participant_id"].isin(slw).astype(int)
    find["median_pdr_hz"] = find["participant_id"].map(pdr_med).round(1)
    write_tsv_json(find, "eeg_findings", {
        "ever_abnormal": {"Description": "Any study read as abnormal (0/1)."},
        "any_epileptiform": {"Description": "Any interictal epileptiform discharges documented (0/1)."},
        "any_seizure": {"Description": "Any electrographic seizure captured (0/1)."},
        "any_slowing": {"Description": "Any focal/generalized slowing documented (0/1)."},
        "median_pdr_hz": {"Description": "Median posterior dominant rhythm across the patient's studies.",
                          "Units": "Hz"}})

    # ---- monitoring (per-patient totals) ----------------------------------
    mon = keyed(load("monitoring_summary.csv"), pub)
    if not mon.empty:
        for c in ["n_hours_total", "n_distinct_days"]:
            mon[c] = pd.to_numeric(mon[c], errors="coerce")
        mon = mon.groupby("participant_id", as_index=False).agg(
            total_monitoring_hours=("n_hours_total", "sum"),
            monitoring_days=("n_distinct_days", "sum"))
        write_tsv_json(mon, "monitoring", {
            "total_monitoring_hours": {"Description": "Total documented monitoring hours.", "Units": "hours"},
            "monitoring_days": {"Description": "Total distinct monitoring days."}})

    # ---- participants.tsv scalar columns (to merge into the live file) -----
    part = demo.merge(find[["participant_id", "ever_abnormal", "any_epileptiform", "any_seizure"]],
                      on="participant_id", how="outer")
    part.to_csv(OUT / "participants_clinical.tsv", sep="\t", index=False, na_rep="n/a")
    print(f"  participants_clinical.tsv  {len(part):,} rows (columns to merge into participants.tsv)")
    print(f"\nWrote to {OUT}. Next: PHI audit, then merge participants + sync to S3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
