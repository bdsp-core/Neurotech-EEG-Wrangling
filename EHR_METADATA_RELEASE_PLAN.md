# Plan — attaching de-identified EHR clinical metadata to the S3 release

## STATUS (2026-07-06) — ✅ PUBLISHED to S3
Uploaded via `rclone` (remote `s3:`) to `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`:
`phenotype/` (demographics, diagnoses, comorbidities, medications, eeg_findings, monitoring — each
`.tsv` + `.json`), plus `participants.tsv` (age/sex filled for 2,691 subjects; was all `n/a`) and
updated `participants.json`. Final PHI audit passed (0 dates, valid IDs, age top-coded at 90). The BIDS
`sub-*` recordings and `dataset_description.json` were left untouched. Regenerate with
`ehr_pipeline/build_bids_phenotype.py`.

<details><summary>pre-upload status (retained)</summary>
**Decisions (locked, per sign-off):** BIDS `phenotype/` + `participants.tsv` scalars · **patient-level only**
(study rows aggregated per patient) · ages >89 **top-coded to 90** · **full ICD-10 codes** · credentialed
access, **no DUA change** · **Brandon runs the upload**. Per-patient date shift confirmed present
(`shift_days` in crosswalk / `date_shift` in linking table); release tables carry **no dates** (age + flags only).

**Done:** `ehr_pipeline/build_bids_phenotype.py` generates the patient-level phenotype tables into
`output/bids_phenotype/` (demographics, diagnoses, comorbidities, medications, eeg_findings, monitoring —
each `.tsv` + `.json`), keyed `sub-NeurotechN`, restricted to published subjects. **PHI audit passed**
(0 dates, valid IDs, age capped at 90, free-text event-years scrubbed). Coverage of the 4,914 published
subjects: demographics 55%, diagnoses 66%, eeg_findings 90%, monitoring 84% — clinical metadata is an
explicit subset (documented in the JSON sidecars).

**Blocked:** the AWS write keys (`Box/Brandon - PHI/AWSKeys/…`) are **not on this machine** and no creds are
configured, so the S3 sync can't run here. To finish: either sync Box / `aws configure` on this machine and
I run it, or run the upload on the machine that has the keys. Remaining upload steps: fetch live
`participants.tsv`, merge the scalar columns (`participants_clinical.tsv`), write `participants.json`, update
`dataset_description.json`/README, `bids-validator`, then `aws s3 sync phenotype/ + participants.*`.
</details>

---

**Status:** proposal (no upload performed). Addresses the open item in `handoff.md`:
> "EHR clinical metadata is NOT on S3 yet. Only the EEG BIDS + participants.tsv/json are
> published. The de-identified EHR tables are local only. Decide whether/how to attach them."

---

## What we have to publish
The committed, PHI-free tables in `output/ehr_deid_tables/` (keyed by `bdsp_id = Neurotech-<N>`).
Two granularities:

- **Patient-level:** `demographics` (age, sex), `diagnosis_codes` (ICD-10), `comorbidities`, `medications`.
- **Study/session-level:** `studies`, `eeg_background` (PDR), `eeg_epileptiform` (categorical flags),
  `eeg_seizures`, `eeg_slowing`, `technologist_impression`, `monitoring_summary`, `patient_events`.
- **Dataset-level aggregates:** `monitoring_event_counts`, `monitoring_hour_of_day` (not per-subject —
  keep out of the per-subject release; they already back Supp Fig 4).

>> i don't understand what you mean here by "not per-subject..." <-- we definitely want per-subject data, just not PHI 

## Key mapping — clean join, no crosswalk needed
EHR `Neurotech-<N>` ↔ BIDS `sub-Neurotech<N>` (hyphen-normalize only). Verified:
- BIDS: **4,914** subjects (IDs 1–5321). EHR demographics: **3,605** subjects (IDs 1–4964).
- **3,297 of 4,914 published subjects have EHR demographics** → clinical metadata is an explicit
  *subset* of the released cohort. 308 EHR-only patients have no BIDS subject (their EEG wasn't
  published) → **exclude** from the BIDS release (nothing to attach them to).

>> ok, that makes sense
>> not sure what you're talking about with the crosswalk though... obviously the crosswalk should be backed up on box, but not published to aws. 

## Recommended approach: BIDS `phenotype/` + a few `participants.tsv` scalars
BIDS already has a standard slot for exactly this — the top-level **`phenotype/`** directory (per-measure
TSVs each with a JSON data dictionary, keyed by `participant_id`). It keeps EEG and clinical data in one
BIDS dataset, stays tool-compatible, and is self-documenting.

>> ok, great. 

1. **`phenotype/*.tsv` (+ `.json` sidecars)** — one file per de-id table, `participant_id = sub-Neurotech<N>`,
   restricted to the intersection with published BIDS subjects. Patient-level tables → one row per subject;
   study-level tables → one row per study with a `study_index` column. Each `.json` documents columns,
   units, categorical levels, coverage (n subjects), and provenance ("technologist scan reports / intake
   forms, LLM-extracted, structured fields only").
2. **`participants.tsv` scalar columns** — add `age`, `sex`, `n_recordings`, `any_epileptiform`,
   `any_seizure`, `primary_referral_icd_category` for at-a-glance filtering, with `participants.json`
   dictionary. (participants.tsv only fits per-subject scalars — the multi-row detail lives in `phenotype/`.)

**Rejected alternatives:** per-subject `_clinical.json` sidecars (non-standard for phenotype, hard to
analyze across cohort); a separate `clinical/` S3 prefix outside BIDS (divorces it from BIDS tooling).

## Implementation (all local; upload gated on your OK)
1. New `ehr_pipeline/build_bids_phenotype.py`: reads `output/ehr_deid_tables/*.csv` → writes
   `phenotype/*.tsv` + `*.json`, remaps IDs, restricts to published subjects, applies the PHI gates below.
2. Extend `build_bids.py: write_participants_files()` with the scalar columns + `participants.json`.
3. Validate locally with `bids-validator`; re-run `reproduce_manuscript_numbers.py` (numbers unchanged).
4. **Upload only after sign-off:** `aws s3 sync phenotype/ + participants.*` →
   `s3://bdsp-opendata-repository/EEG/bids/Neurotech/` (keys in Box `Brandon - PHI/AWSKeys/`).

## ⚠️ PHI / compliance gates before any upload
- **Ages >89 → "90+" (HIPAA safe harbor).** `demographics.csv` currently has **8 subjects >89 (max 100.8)**
  in raw years — must be capped to a "90+" bin (or dropped) in the published table. *(Manuscript median/IQR
  is unaffected; this is specifically about the per-subject released file.)*

>> yes pleae do round these ones to 90

- **No dates, no free text.** Confirm the phenotype TSVs carry only structured/categorical fields + age in
  years — no raw dates, names, or `raw_*` text. (The de-id tables already exclude these; re-audit the output.)

>> actually, this does not sound right. 
>> we should have created an integer date shift for each patient. it should be stored in the crosswalk/linking table. is this not done??

- **ICD granularity.** `diagnosis_codes.csv` holds full ICD-10 codes (not PHI) — confirm full codes vs
  category-only is the intended release granularity.
>> full ICD codes, please. 

- **Governance / DUA.** Confirm with BDSP that adding clinical metadata does not change the Data Use
  Agreement terms, and update `dataset_description.json` / README accordingly.

>> it does not. this data is being published as credentialed access. 

## Decisions needed from the team
1. Go with **phenotype/ + participants.tsv scalars** (recommended), or a lighter subset?

>> i don't understand this question. 

2. Publish study-level tables (per-study rows), or only patient-level summaries?

>> patient level data, please. 

3. Cap ages at 90 (recommended) vs. drop the 8 >89 subjects' age?
>> cap at 90

4. Who runs the S3 upload, and when (needs the AWS keys + a governance/DUA green light)?
>> you run this. with my help. 