# Neurotech EEG Dataset — Handoff (2026-07-03)

Picking up on a different computer to **finish the manuscript**. This explains what's done, the one remaining task, and where everything lives.

---

## TL;DR — the only task left
**Update the manuscript prose to the full A–Z cohort numbers.** The de-identified dataset is published, the EHR is reprocessed, and all tables/figures are regenerated with A–Z numbers. But `manuscript-materials/manuscript-draft.md` still has the **old A–H numbers hard-coded in the prose** (abstract, Background, Data Records, Table 1). The auto-fill script can't help — its `{NEW:}` placeholders were already consumed in a prior run.

**Do this:** edit the prose numbers to match the regenerated tables in `manuscript-materials/tables/` (source of truth), then rebuild the `.docx` with `manuscript-materials/md_to_docx.py`.

### Old → New headline numbers (from `tables/table2_patient_characteristics.csv`)
| | A–H (in the draft now) | **A–Z (correct)** |
|---|---|---|
| Unique patients | 1,741 | **4,914** |
| EEG recordings (signal) | 8,040 | **23,607** |
| Recording hours | 74,321 | **212,186** |
| EEG data size | 3.95 TB | **~11.2 TB** |
| Patients w/ clinical docs | (bugged "277%") | **4,844 (99%)** |
| Age median / n | 954 | median 26.8, **n=2,932** |
| Sex n | 924 | **n=3,037** (M 1,389 / F 1,637) |
| Epilepsy referrals (G40) | 2,105 | **7,084 (54%)** |

Also fix the abstract's TB/hours/counts and the Table 1 comparison row. The `.docx`/`.pdf` in the repo are stale — regenerate after editing.

---

## Status of every phase
- **Phase 1–2 (inventory + linking):** done. Final batch = surnames H–Z, 3,652 folders, 19 TB drive.
- **Phase 3–4 (EEG → BIDS → S3):** ✅ **PUBLISHED.** `s3://bdsp-opendata-repository/EEG/bids/Neurotech/` — **4,915 subjects, 54,319 EDFs, ~11.2 TB.** De-id verified; `participants.tsv` regenerated (complete, 4,915). Completeness audited: only 107 unrecoverable 4 KB corrupt fragments missing (no real gaps).
- **Phase 5 (video):** **DROPPED** (clip quality too low). A full synthetic-face de-id pipeline was built (`video_deid.py`, `VIDEO_DEID_PLAN.md`) if ever revived. Raw video (4.28 TB) backed up to Box.
- **Phase 6 (EHR):** ✅ done. Reprocessed all 10,044 packets (0 errors, 603 LLM failures cleared). **Seizures-field bleeding fixed** (`ehr_pipeline/clean_findings.py`; max 30 k→3 k chars). De-id re-run (7,300 patients). Crosswalk refreshed (100% match).
- **Phase 7 (manuscript):** tables + figures ✅ regenerated for A–Z; **prose = the remaining task above.**
- **Phase 8 (completeness):** ✅ Charles confirmed this is the complete dataset.

---

## ⚠️ Important gaps / decisions
1. **EHR clinical metadata is NOT on S3 yet.** Only the EEG BIDS + `participants.tsv/json` are published. The de-identified EHR tables (`output/ehr_deid/`) are local only. Decide whether/how to attach them to the release (e.g., `_clinical_metadata.json` sidecars, or a separate `clinical/` prefix). See `ehr_pipeline/PIPELINE_WALKTHROUGH.md` (local; gitignored because it embeds credentials).
2. **PHI in git history.** `output/linking_table.csv` and `output/bids_progress.tsv` (real patient names) were committed in earlier history. They are now untracked + gitignored, but **still exist in past commits.** Decide whether to scrub history (`git filter-repo`) — the repo is private, but this is a compliance call.
3. The `.docx`/`.pdf` manuscript builds are stale until the prose edit + `md_to_docx.py`.

---

## Where things live (most PHI/secrets are gitignored — NOT in this repo)
| Thing | Location |
|---|---|
| Published EEG dataset | `s3://bdsp-opendata-repository/EEG/bids/Neurotech/` (AWS write keys: Box `Brandon - PHI/AWSKeys/`) |
| Regenerated tables (A–Z, source of truth) | `manuscript-materials/tables/` |
| Regenerated figures | `manuscript-materials/figures/` |
| EEG stats used for tables | `output/s3_recordings.csv` (A–Z, de-identified — in git) |
| **Linking table (name↔BDSP-ID, PHI)** | local `output/linking_table.csv` + `output/batch2_IZ/linking_table_batch2.csv`; backed up to Box `zz_neuroTech/critical_linking_phi_backup.tar` (gitignored) |
| EHR structured tables (A–Z, PHI names) | local `output/ehr/` (gitignored) |
| De-identified EHR | local `output/ehr_deid/` (gitignored) |
| EHR source PDFs + extraction | `/Volumes/Extreme SSD/neurotech-data/` |
| Raw video backup (4.28 TB) | Box `Brandon - PHI/Datasets/zz_neuroTech/video_backup/` |
| AWS keys | `~/Desktop/GithubRepos/` (gitignored) and Box. EHR extraction runs on a local on-device model — no LLM API keys needed. |

## Environment / how to run
- `.venv` (Python 3.9) with pyedflib, edfio, pandas, ultralytics, insightface, diffusers, awscli.
- EHR pipeline: `ehr_pipeline/run_full_pipeline.sh` (Stages: extract_text → segment → extract_fields → build_csvs → build_crosswalk → deidentify_ehr → manuscript). Paths were updated for this machine (`/Users/mbwest/...`, SSD source, keys dir); adjust if on a different machine.
- Regenerate manuscript tables/figures: `.venv/bin/python manuscript-materials/generate_tables_and_figures.py` (reads `output/s3_recordings.csv` + `output/ehr/*.csv`).
- Full project roadmap: `MASTER_PLAN.md`.
