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
