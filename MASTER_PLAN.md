# Neurotech EEG Dataset — Master Plan (final batch → publish → manuscript)

_Last updated 2026-06-30. Consolidates the original `PLAN.md` (EEG→BIDS), the EHR
pipeline, the NEW video-skeleton de-identification track, and manuscript
finalization. End goal: the **complete A–Z dataset** published on bdsp.io and the
**manuscript finalized** for submission (Scientific Data data descriptor)._

## End state (definition of done)
1. Complete **A–Z** de-identified BIDS-EEG dataset live at `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`.
2. **Video-derived skeleton/pose** data published as a de-identified derivative (coordinates only, no pixels) — NEW.
3. Structured **EHR** tables finalized and linked to BDSP IDs.
4. **Manuscript** updated to full-cohort numbers + the new video modality, tables/figures regenerated, ready to submit.
5. Dataset completeness **confirmed with Neurotech** (this is stated to be the final batch).

---

## Where we are
- **Published (A–H):** 1,748 patients, 8,410 recordings, ~77.6k h, 3.95 TB on S3.
- **Final batch (H→Z):** drive `/Volumes/Padlock_DT`, **3,652 folders, 19 TB**. Pre-assigned IDs `Neurotech-1749…4964` + date shifts already in `output/linking_table_pending_eeg.csv`.
- Combined target cohort ≈ **4,986 unique patients** (pending Neurotech confirmation).

---

## Phase 0 — Environment setup ✅ DONE (2026-06-30)
Repo rcloned from Box → `~/Desktop/GithubRepos/neurotech_wrangling`; `.venv` (py3.9 + pyedflib/pandas); drive confirmed H→Z.

## Phase 1 — Inventory the final batch  ▶ COMPLETE
`fast_inventory_batch2.py` (parallel, resumable, single-scandir pass) → `output/batch2_IZ/{recordings,annotations,patients}.csv`. Also emits a **video manifest** (`video_files`, `video_gb` per patient). Does NOT touch the A–H outputs.

## Phase 2 — Reconcile & extend the linking table
- Match drive patients (by `last_name,first_name`) to `linking_table_pending_eeg.csv`; **honor pre-assigned `Neurotech-N` IDs + `shift_days`**.
- Dedup the **H-boundary overlap** against the already-published A–H (`linking_table.csv` is READ-ONLY — never modify).
- Handle: multi-folder/same-patient (one ID, one shift), EEG-on-drive patients absent from the pending table (assign next free IDs ≥4965), and pending patients with no EEG on the drive (PDF-only).
- Output a merged, complete **A–Z linking table** + a reconciliation report (matched / unmatched / new / conflicts).

## Phase 3 — De-identify + BIDS-convert the new EEG
- `build_bids.py` (edfio, lazy load): scrub EDF header PHI, per-patient date-shift, `.lay`→`_Xltek.csv`, generate sidecars/scans/channels.
- **Disk constraint:** local free space (~7 TB) < source (19 TB) → **batch-stream**: convert a batch → upload → delete local → repeat (do NOT build the full tree locally). Resumable; skip already-done.
- **PHI scan** of all annotation free-text (names/MRNs/dates) before release.
- Video (`.asf`) is **excluded** from BIDS (PHI; consistent with A–H).

## Phase 4 — Validate + upload EEG
- `bids-validator`; re-read de-identified EDF headers to confirm `X X X X` + shifted dates.
- AWS CLI + creds (pull `bdsp_opendata_write_accessKeys.csv` from Box when needed) → `aws s3 sync` to the Neurotech BIDS prefix. Verify counts/sizes.

## Phase 5 — Video → skeleton de-identification  ★ NEW
Turn the ~TBs of un-shareable `.asf` video into a publishable, de-identified **motion** resource.
- **Approach:** extract pose/keypoints (2D and/or 3D SMPL body) → **publish coordinates only, discard pixels** → optional re-rendered stick-figure/avatar for viewing. Strip `.wav` audio; mask burned-in timestamps; remove room/visitors.
- **Candidate tools:** ViTPose / MMPose / YOLO-pose (2D); 4D-Humans (PHALP), SMPLer-X (3D mesh); SAM2 for segmentation. (Final choice pending the deep-research pass — see `VIDEO_DEID_PLAN.md` once written.)
- **Reliability rule:** detection failures yield a bad skeleton, never an exposed face — because originals are never released. Human QC on a sample.
- **Compute:** GPU needed; likely cloud (this Mac has none). Scope as its own sub-project.
- **Packaging:** publish as a BIDS derivative (e.g. `derivatives/motion/` keypoint time series) aligned to each `sub-Neurotech*` session; never leaves the de-id boundary.
- **IRB note:** confirm the existing protocol/DUA covers releasing pose-derived motion; likely fine (no pixels), but verify.

## Phase 6 — Finish the EHR pipeline
3-stage pipeline in `ehr_pipeline/`. Known issues to clear: seizures-field regex bleeding; ~603 truncated-JSON LLM extractions to retry. Re-link all EHR patients to A–Z BDSP IDs; regenerate `output/ehr/` structured tables (incl. supp tables 4 & 5 CSVs).

## Phase 7 — Finalize the manuscript
`manuscript-materials/manuscript-draft.md` → regenerate everything for the **full A–Z cohort**:
- Update all counts (patients ≈4,986; recordings; hours; TB; annotations) via `generate_tables_and_figures.py` + `fill_manuscript_placeholders.py`.
- **Fix existing bugs**: the "n=4,831 of 1,741 patients (277%)" denominator error and similar; reconcile abstract vs Table 2 vs supp-table totals.
- **Add the video modality**: new Data Records subsection + Methods (skeleton de-id) + a Future/Usage note; update Figure 1 pipeline.
- Refresh Table 1 (dataset comparison) with final numbers; regenerate figures/tables; rebuild `.docx`/`.pdf` via `md_to_docx.py`.
- Update BDSP listing (`bdsp_listing_draft.md`), co-author email.

## Phase 8 — Confirm completeness with Neurotech
Send the drafted clarification email to Charles Pickering: confirm this drive = the final EEG batch, get a definitive total patient/study count or manifest, and resolve the ~15,000-vs-~4,986 discrepancy before declaring done.

---

## Cross-cutting
- **Resumability** everywhere (USB can drop; S3 syncs resume).
- **PHI discipline:** linking table never published; video pixels never leave; audit before every upload.
- **Order:** Phases 2–4 (EEG) and 5 (video) and 6 (EHR) can largely run in parallel; Phase 7 depends on 2–6; Phase 8 can start now.
