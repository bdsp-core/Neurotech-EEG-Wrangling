# Fact-correction plan — Neurotech EEG Dataset (manuscript + published dataset)

Keith Morgan (Neurotech, data provider) flagged several **factual errors** in the manuscript
that are **also live in the published dataset**. This plan catalogs every place each correction
must land so it's turnkey once Neurotech's team (Danielle / Christina / Charles) returns the
validated specifics. **Do not apply the factual items until Neurotech confirms the exact values.**

> Status of the *safe* review edits (already applied 2026-08): Dan Goldenholz's COI / funding
> (R21NS142800, ABPN) / affiliation (Waukesha, WI), the "will→may / plan→hope" softening, and the
> Word caret→superscript rendering fix are done and the .docx/.pdf are rebuilt. The items below are
> the *pending factual corrections*.

---

## 1. Hardware: NOT Natus/Xltek  → Lifelines and/or EMS ambulatory equipment + Persyst detection
Keith: *"We would have used Lifelines and/or EMS ambulatory equipment with Persyst spike and seizure
detection."* Root cause: **"Natus/Xltek" was hard-coded**, never read from the data
(`build_bids.py:416`). Need Neurotech's exact acquisition-hardware name(s) and software/version.

**Manuscript** (`manuscript-materials/manuscript-draft.md`): abstract novelty #2 (line ~24);
Table 1 "Hardware" column (line ~35); Methods "Recording" (line ~45, "Natus/Xltek NeuroWorks");
Data Records (line ~125, "Natus/Xltek source export"); Technical Validation (line ~135); Limitations
(line ~160). Then rebuild .docx/.pdf via `md_to_docx.py`.

**Pipeline code**: `build_bids.py:416` (`"Manufacturer": "Natus/Xltek"`); README string (`build_bids.py:562`);
annotation CSV naming `*_Xltek.csv` (`build_bids.py:450, 817`) — **decide whether to rename** (e.g.
`*_annotations.csv`); renaming changes the published BIDS layout.

**Published dataset (S3 `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`)**:
- **All 23,607 `_eeg.json` sidecars** carry `"Manufacturer": "Natus/Xltek"` → patch + re-upload (rclone).
- Top-level `README` ("Annotations from Natus/Xltek system").
- (If renaming `_Xltek.csv`: ~14,517 files — heavy; likely defer or do at a version bump.)

**bdsp.io listing** (live PublishedProject `nf89816gtxbon11kbr9a` + `manuscript-materials/bdsp_listing_draft.md`):
abstract, Methods, Data Description "Hardware" row, topic tags (`natus-xltek`). Edit the PublishedProject
content fields on prod Django (see [[bdsp.io dataset publishing (production)]]).

## 2. No ICU/EMU inpatient data  → ambulatory (home) + routine (some routine inpatient bedside)
Keith: *"We don't have any inpatient data… no EMU data recorded inpatient. There may be some routine
inpatient EEG bedside."* The ">24 h = 11% prolonged continuous ICU/EMU monitoring" framing is wrong —
those are **multi-day home ambulatory** studies. **(This reverses the ICU/EMU wording added for
Chenxi's consistency note — the correct fix is to remove ICU/EMU, which strengthens the home/ambulatory
novelty.)**

**Manuscript**: Table 1 recording types (line ~35, currently "Routine + ambulatory + ICU/EMU");
Methods line ~41 ("intensive care units and epilepsy monitoring units" + ">24 h ICU/EMU"); Data Records
line ~125 (reframe >24 h as multi-day ambulatory); Results line ~156 ("routine, ambulatory, ICU");
Limitations line ~160 ("hospital ICUs and epilepsy monitoring units"). Keep HEEDB's EMU/ICU description
(that's about HEEDB, correct).

**bdsp.io listing**: abstract + Methods + Data Description recording-type language.

## 3. "23,607 recordings from 4,914 patients" — clarify EDF segments vs clinical studies
Keith reads "recordings" as clinical studies (~1/patient every few years). Our data: 23,607 = **EDF
recording segments** (a multi-day aEEG is split into several); ~**10,726 clinical studies** (~2.2/patient);
total hours (212,186 ≈ 43 h/patient) is consistent with ~one multi-day aEEG/patient.

**Fix (framing, authors' call):** define "recording = EDF segment" explicitly; report the distinct
clinical-study count separately. Touches abstract, Data Records, Table 2, Results (per-patient counts).
Same clarification in the bdsp.io listing.

## 4. Electrode montage overstated
Keith: extended electrodes (T1/T2/F11/F12, A1/A2) used *"only upon request — 75%+ don't have these,
but all have 2-channel EKG."* Fix Methods "Recording" montage list (line ~45) + `_channels`/listing text.

## 5. Annotation workflow — awaiting Neurotech
Keith **deleted** the annotation-methodology section ("this is the Natus format; Neurotech will get you
our correct annotations workflow"). Replace with Neurotech's Persyst-based description once received;
then update the manuscript Methods and the bdsp.io Methods.

---

## Mechanics (once values confirmed)
| Target | How |
|---|---|
| Manuscript `.docx`/`.pdf` | edit `manuscript-draft.md` → `md_to_docx.py` → `soffice --convert-to pdf` |
| Pipeline defaults | edit `build_bids.py` (Manufacturer/README/naming); commit |
| S3 `_eeg.json` Manufacturer + README | patch field across 23,607 JSONs, `rclone copy` back to `s3:.../Neurotech/` |
| bdsp.io listing | edit PublishedProject content fields via prod Django shell; refresh `bdsp_listing_draft.md` |
| Versioning | decide: correct **v1.0 in place** (likely no downloads yet) vs publish **v1.0.1** per BDSP convention |

## Decisions needed
1. Exact hardware + software names/versions (Lifelines vs EMS; Persyst version) — **from Neurotech**.
2. Rename `_Xltek.csv` annotation files, or leave the name and just fix the metadata? (rename = heavy)
3. Correct the published v1.0 in place, or issue v1.0.1?
4. Neurotech's correct annotation-workflow text (§5).
5. Journal target: Keith asked to try **Epilepsia** first (author decision).

---

## Investigation findings (evidence for Keith's three points)

### Hardware — why we said "Natus", and can we recover the truth per recording
- **Why we thought Natus: no evidence — it was hard-coded from the very first script.** `extract_inventory.py`
  line 2 opens *"Extract inventory … from Natus/Xltek NeuroWorks EEG dataset,"* and `build_bids.py:416`
  writes `"Manufacturer": "Natus/Xltek"` as a constant. We **never read the EDF equipment field**. The
  annotation files are `.lay` (a **Persyst** format), consistent with Keith's "Persyst detection."
- **Can we tell which equipment per recording?** Possibly — `extract_inventory.py:98` *did* capture the real
  EDF header `equipment` field into the (SSD, gitignored) inventory CSVs. If that field distinguishes
  Lifelines vs EMS, we can label per-recording. **But the published S3 EDFs have it scrubbed** (header
  recording-ID = `"Startdate DD-MMM-YYYY X X X"`), so it must be read from the **source EDFs / inventory on
  the SSD**. (Note: the de-id Supp Fig 2 says "Equipment — unchanged"; actually it was scrubbed — fix that too.)
- **Manuscript status:** corrected to "Lifelines or EMS ambulatory EEG systems (with Persyst spike/seizure
  detection)"; `.docx`/`.pdf` rebuilt. Pipeline default + published sidecars/README/listing still pending.

### "23,607 recordings" — Keith is right; these are EDF file fragments, not studies
- **Where the number came from:** `output/s3_recordings.csv` has one row per `.edf` file, and
  `build_bids.py` assigns **one BIDS `ses-N` per source `.edf` file**. So "23,607 recordings" = 23,607 EDF files.
- **Fragmentation is severe:** 3,709 of 23,607 files are **< 5 minutes** (one patient has **310** signal EDFs).
- **Regrouping (60-subject sample, 407 files) by recording date:** **6.8 EDF files/subject but only ~1
  recording session (median 1; 55/60 subjects = exactly one)** and **2.0 distinct recording days/subject**
  → **~6 EDF files : 1 session**. Extrapolated: **~1 EEG study per patient (~5,000 total), not 23,607.**
- **Independent corroboration:** 2.0 recording days/patient ≈ Keith's "**2.1 days per aEEG**"; total hours
  212,186 / 4,914 = **43 h/patient ≈ 1.8 days**. Everything matches Keith's model.
- **Proposed reframing (PENDING sign-off):** headline = "**~4,914 EEG studies from 4,914 patients** (≈ one
  multi-day ambulatory study per patient, ~2 recording days each), released as **23,607 EDF recording
  segments** (a continuous study is split into multiple EDF files) totaling 212,186 hours." Fix "recordings
  per patient median 3 (IQR 1-6)" → that is **EDF files** per patient, not studies. Same in the bdsp.io listing.

### "11% EMU" — no evidentiary basis; it was a duration label
- **There is no facility/setting field anywhere in the pipeline.** The only setting signal, `is_ambulatory`,
  is parsed from the tech-report **test-type text** (`build_csvs.py:106`), and **never encodes EMU/ICU**.
- The "11% = >24 h" bin is a pure **duration cut** that the manuscript *labeled* "ICU/EMU" by assumption.
  Given the recordings are multi-day **home ambulatory**, the >24 h studies are long aEEG, not inpatient.
- **Conclusion:** remove ICU/EMU everywhere (Table 1, Methods, Results, Limitations); describe as
  **ambulatory (incl. multi-day home) + routine outpatient (some routine inpatient bedside)**. Keep HEEDB's
  EMU/ICU description (that dataset, correct). **PENDING sign-off** (the ICU/EMU wording added for Chenxi's
  consistency note should be removed, not kept).
