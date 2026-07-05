# Neurotech EHR Structured Data Schema Plan

Based on review of 600+ randomly sampled patient packets from the 2,469 successfully extracted.

## Corpus Summary

| Metric | Value |
|---|---|
| Source PDFs processed | 2,469 |
| Total pages | 41,926 |
| Total extracted text | 132.9M characters |
| Sub-documents identified | 5,264 |
| Sub-documents with structured fields | 4,156 |
| LLM extraction errors to retry | 603 |

---

## 1. Database Table Structure

### Table: `studies` (one row per EEG recording = one PDF packet)

This is the central table. Every packet represents one EEG study for one patient.

| Column | Type | Source | Notes |
|---|---|---|---|
| study_id | string PK | folder name | e.g., `Patient, Example-1762275026` |
| patient_name | string | tech_scan_report.patient_name | |
| dob | string | eeg_intake_form.dob | ~60% fill rate |
| sex | string | eeg_intake_form.sex | ~10% fill rate |
| insurance | string | eeg_intake_form.insurance | ~60% fill rate |
| insurance_type | enum | derived | medicare, medicaid, commercial, unknown |
| referring_physician | string | eeg_intake_form.referring_physician | ~60% fill rate |
| referring_phone | string | eeg_intake_form.referring_phone | |
| interpreting_physician | string | eeg_intake_form.interpreting_physician | |
| eeg_start_date | date | tech_scan_report.eeg_start_date | |
| eeg_start_time | time | tech_scan_report.eeg_start_time | |
| eeg_end_date | date | tech_scan_report.eeg_end_date | |
| eeg_end_time | time | tech_scan_report.eeg_end_time | |
| duration_hours | float | derived from dates/times or test_type | |
| duration_hours_ordered | int | eeg_intake_form.duration_hours_ordered | 24/48/72/96 |
| test_type_raw | string | tech_scan_report.test_type | original text |
| has_video | bool | parsed from test_type | |
| is_ambulatory | bool | parsed from test_type | |
| additional_electrodes | string[] | eeg_intake_form.additional_services | T1/T2, A1/A2, zygomatic |
| scanning_technologist | string | tech_scan_report | |
| n_patient_events | int | tech_scan_report | |
| n_patient_events_video | int | tech_scan_report | |
| n_tech_events | int | tech_scan_report | |
| automated_seizure_detections | int | tech_scan_report | |
| automated_spike_detections | int | tech_scan_report | |
| tech_comments | text | tech_scan_report | |
| source_pdf | string | filename | |

### Table: `diagnosis_codes` (many per study)

| Column | Type | Notes |
|---|---|---|
| study_id | FK | |
| code | string | ICD-10 code, e.g., G40.209 |
| code_normalized | string | Trimmed/validated to standard form |
| source | enum | `intake_form`, `clinical_note`, `eeg_order` |

**Top codes in the dataset:**
- R56.9 — Unspecified convulsions (64)
- G40.109 — Focal epilepsy, not intractable (62)
- G40.909 — Epilepsy, unspecified (28)
- G40.A09 — Absence epilepsy, not intractable (18)
- G40.209 — Focal epilepsy, not intractable (18)
- R40.4 — Transient alteration of awareness (16)
- G40.309 — Generalized epilepsy, not intractable (14)

---

### Table: `eeg_background` (one per study)

Captures the posterior dominant rhythm (PDR) and sleep architecture from the tech scan report.

| Column | Type | Enumeration / Notes |
|---|---|---|
| study_id | FK | |
| pdr_frequency_hz_low | float | lower bound; null if poorly formed |
| pdr_frequency_hz_high | float | upper bound (same as low if single value) |
| pdr_amplitude_uv_low | float | |
| pdr_amplitude_uv_high | float | |
| pdr_symmetry | enum | `symmetric`, `asymmetric` |
| pdr_reactivity | enum | `reactive`, `non_reactive`, `unknown` |
| pdr_poorly_formed | bool | |
| pdr_absent | bool | e.g., encephalopathic patients |
| posterior_slow_waves_of_youth | bool | pediatric finding |
| excess_beta | bool | often medication-related |
| sleep_recorded | bool | |
| sleep_stages_present | string[] | subset of `[N1, N2, N3, REM]` |
| sleep_architecture | enum | `normal`, `abnormal`, `absent`, `poorly_formed`, `fragmented` |
| sleep_symmetry | enum | `symmetric_synchronous`, `asymmetric`, `unknown` |
| vertex_waves_present | bool | |
| sleep_spindles_present | bool | |
| k_complexes_present | bool | |
| posts_present | bool | positive occipital sharp transients of sleep |
| raw_background_text | text | full free text for audit |
| raw_sleep_text | text | |

**PDR frequency distribution observed (n=22 non-bleeding):**
- 9 Hz: 27%, 10 Hz: 14%, 9-10 Hz: 18%, 8 Hz: 9%, 11 Hz: 9%, 7-8 Hz: 9%

---

### Table: `eeg_activations` (one per study)

| Column | Type | Enumeration / Notes |
|---|---|---|
| study_id | FK | |
| photic_performed | bool | |
| photic_reason_not_performed | string | "not ordered", "patient declined", "COVID precautions" |
| photic_driving_response | bool | |
| photic_driving_frequencies | string | e.g., "4-18 Hz" |
| photoparoxysmal_response | bool | rare but clinically critical |
| hv_performed | bool | |
| hv_duration_min | float | usually 3 minutes |
| hv_reason_not_performed | string | |
| hv_buildup | bool | normal buildup of slow activity |
| hv_abnormal_activation | bool | epileptiform triggered by HV |
| hv_response_description | text | |

---

### Table: `eeg_slowing` (potentially multiple per study — e.g., focal + diffuse)

| Column | Type | Enumeration / Notes |
|---|---|---|
| slowing_id | PK auto | |
| study_id | FK | |
| present | bool | |
| severity | enum | `rare`, `occasional`, `intermittent`, `frequent`, `semi_continuous`, `continuous` |
| severity_qualifier | string | "less than 50%", "50-75%", ">75%", "mild", "moderate" |
| frequency_band | enum | `theta`, `delta`, `theta_delta` |
| distribution | enum | `generalized`, `diffuse`, `focal`, `regional`, `lateralized`, `multifocal` |
| laterality | enum | `left`, `right`, `bilateral`, `bilateral_R_gt_L`, `bilateral_L_gt_R`, `midline` |
| region | string | `temporal`, `frontal`, `occipital`, `parietal`, `central`, `frontotemporal`, `hemispheric` |
| morphology | string[] | `irregular`, `rhythmic`, `semi_rhythmic`, `sharply_contoured`, `polymorphic` |
| special_pattern | enum | `FIRDA`, `TIRDA`, `OIRDA`, `GRDA`, `GPDs`, `triphasic`, `breach_rhythm` |
| state_dependency | enum | `wakefulness`, `sleep`, `both`, `throughout` |
| raw_description | text | |

**Observed distribution:** generalized (69), temporal (38), hemispheric (20), frontal (11), central (13)

---

### Table: `eeg_epileptiform` (potentially multiple per study)

| Column | Type | Enumeration / Notes |
|---|---|---|
| epileptiform_id | PK auto | |
| study_id | FK | |
| present | bool | |
| certainty | enum | `definite`, `probable`, `questionable` |
| frequency | enum | `rare`, `occasional`, `intermittent`, `frequent`, `abundant`, `semi_continuous`, `continuous` |
| morphology | string[] | from: `spike`, `sharp_wave`, `spike_and_wave`, `polyspike`, `polyspike_and_wave`, `sharp_and_wave`, `GPFA` |
| discharge_frequency_hz | float | e.g., 3.0 for absence-type spike-wave |
| run_duration_sec | float | "runs lasting up to 4-5 seconds" |
| amplitude_uv | string | e.g., "60-80 uV" |
| distribution | enum | `generalized`, `focal`, `multifocal`, `bilateral_independent`, `lateralized` |
| laterality | enum | `left`, `right`, `bilateral`, `bilateral_R_gt_L`, `bilateral_L_gt_R` |
| regions | string[] | subset of: `temporal`, `frontal`, `central`, `parietal`, `occipital`, `frontotemporal`, `centrotemporal`, `posterior_quadrant` |
| electrode_maxima | string[] | e.g., `["T4", "T6/O2"]`, `["F7", "T3"]` |
| state_dependency | enum | `wakefulness`, `sleep`, `both`, `predominantly_sleep`, `predominantly_wake` |
| csws_eses | bool | continuous spike-wave during sleep |
| breach_effect_noted | bool | (must distinguish from true epileptiform) |
| raw_description | text | |

**Observed morphology distribution:** spike (73), spike_and_wave (70), sharp_wave (61), polyspike (21)
**Observed regions:** temporal (60), frontal (34), frontotemporal (19), central (19), parietal (10), occipital (8)

---

### Table: `eeg_seizures` (one row per electrographic seizure detected by tech)

| Column | Type | Notes |
|---|---|---|
| seizure_id | PK auto | |
| study_id | FK | |
| seizure_number | int | within-study ordinal |
| event_date | date | from "10/20/2025@ 16:54:21" |
| event_time | time | precise to seconds when available |
| event_datetime | datetime | **CRITICAL:** exact timestamp for EEG signal linkage |
| onset_region | string | "right temporal", "left frontal", "generalized" |
| onset_laterality | enum | `left`, `right`, `bilateral`, `generalized` |
| onset_electrode | string | "T4", "F7" |
| spread_pattern | string | "secondary generalization", "spread to left temporal" |
| morphology | string | "spike wave discharge followed by electrodecrement" |
| frequency_hz | float | |
| duration_sec | float | |
| clinical_description | text | "loss of tone", "no clinical change" |
| subclinical | bool | no clinical correlate |
| video_captured | bool | |
| postictal_description | text | "post-ictal right temporal slowing" |
| linked_patient_event_id | FK→patient_events | link to corresponding patient-reported event, if any |
| raw_description | text | |

**107 studies had seizures** in the sample (600 studies examined).

**Timestamp availability:** Seizure timestamps come from two sources:
1. **Tech scan report event list:** "Seizure: 10/20/2025@ 16:54:21" — precise to the second, found in 97 events across 200-patient sample
2. **TrackIT monitoring notes:** "SeizureDetection: ..." with approximate hour
3. **Patient events:** "Patient Event #5 on 09/20/2025 at 10:38" — patient-reported, links to `patient_events` table

All three should be cross-referenced: an electrographic seizure at 16:54 might correspond to Patient Event #3 at 16:52 described as "arm stiffening".

---

### Table: `technologist_impression` (one per study)

| Column | Type | Notes |
|---|---|---|
| study_id | FK | |
| classification | enum | `normal`, `abnormal`, `questionably_abnormal` |
| abnormality_reasons | text[] | parsed from "due to..." clause |
| raw_text | text | |

**Distribution:** Normal 39%, Abnormal 60%, Questionable ~1%

---

### Table: `clinical_encounters` (one per progress note or H&P)

| Column | Type | Notes |
|---|---|---|
| encounter_id | PK auto | |
| study_id | FK | links to EEG study via same packet |
| encounter_type | enum | `progress_note`, `history_and_physical` |
| encounter_date | date | |
| provider_name | string | |
| provider_specialty | enum | see below |
| department | string | |
| chief_complaint | text | |
| chief_complaint_category | enum | `seizure`, `epilepsy`, `abnormal_movements`, `staring_episodes`, `syncope`, `headache`, `follow_up`, `new_consult`, `other` |
| reason_for_consultation | text | |
| hpi_summary | text | LLM-generated 1-3 sentence summary |
| neurological_exam | text | |
| assessment_plan | text | |
| follow_up | text | |
| raw_encounter_text | text | for audit/re-extraction |

**Provider specialties** (to be normalized):
- Neurology (103), Pediatric Neurology (60), Epilepsy (11), Child Neurology (9), Clinical Neurophysiology (2), Internal Medicine (1), Cardiology (1)

---

### Table: `conditions` (PMH entries, many per encounter)

| Column | Type | Notes |
|---|---|---|
| condition_id | PK auto | |
| encounter_id | FK | |
| study_id | FK | |
| condition_name | string | as stated |
| condition_normalized | string | mapped to standard terminology |
| category | enum | see below |
| is_epilepsy_related | bool | |
| icd10_code | string | if extractable |

**Categories:**
- `neurological` — seizures, epilepsy, developmental delay, autism, tics, neuropathy
- `psychiatric` — ADHD (19), anxiety (21), depression (14), mood disorder
- `cardiovascular` — hypertension (11), atrial fibrillation
- `respiratory` — asthma (15)
- `metabolic` — hypothyroidism (4), vitamin D deficiency (6), diabetes
- `dermatologic` — eczema (7)
- `developmental` — speech delay (7), learning disability (6), sensory processing disorder (6)
- `other`

**Top conditions:** seizures (30), epilepsy (27), anxiety (21), ADHD (19), asthma (15), depression (14), seizure disorder (12), hypertension (11), autism spectrum disorder (10), developmental delay (9)

---

### Table: `medications` (many per encounter)

| Column | Type | Notes |
|---|---|---|
| medication_id | PK auto | |
| encounter_id | FK | |
| study_id | FK | |
| name_as_stated | string | |
| name_generic | string | normalized |
| name_brand | string | |
| dose | string | e.g., "500 mg" |
| frequency | string | e.g., "BID", "twice daily" |
| route | string | oral, nasal, rectal |
| is_antiseizure_medication | bool | |
| is_rescue_medication | bool | e.g., diastat, nayzilam, valtoco |
| medication_class | enum | `ASM`, `benzodiazepine`, `stimulant`, `antidepressant`, `antipsychotic`, `analgesic`, `supplement`, `other` |

**Top ASMs observed:**
- levetiracetam/Keppra (86), lamotrigine/Lamictal (26), clobazam/Onfi (15), lacosamide/Vimpat (17), diazepam (14), zonisamide (6), topiramate (5), carbamazepine (5), brivaracetam (2), valproate/Depakote (2)

**Top non-ASMs:**
- midazolam/Nayzilam (12, rescue), melatonin (9), albuterol (10), sertraline (8), acetaminophen (11), aspirin (8), ibuprofen (8)

---

### Table: `imaging` (one per imaging report sub-document)

| Column | Type | Notes |
|---|---|---|
| imaging_id | PK auto | |
| study_id | FK | |
| modality | enum | `MRI`, `CT`, `PET`, `CTA`, `unknown` |
| anatomy | string | usually "brain" or "head" |
| study_date | date | |
| indication | text | |
| findings | text | |
| impression | text | |
| is_normal | bool | derived from impression |

**Modality distribution:** MRI (45), CT (16), unknown (7), EEG misclassified (6), PET (1), CTA (1)
**66 reports had extractable findings/impression.** Many more exist but were poorly extracted (known gap).

---

### Table: `monitoring_summary` (one per trackit log sub-document)

| Column | Type | Notes |
|---|---|---|
| study_id | FK | |
| n_eeg_reviewed_notes | int | |
| n_general_notes | int | |
| n_equipment_failures | int | 9% of studies had any |
| date_range_start | date | |
| date_range_end | date | |
| n_monitoring_days | int | |
| distinct_reviewers | string[] | |
| n_distinct_reviewers | int | mean 4.2 |
| n_hourly_rows | int | |
| n_hours_recording_on | int | hours where TrackIT was "Yes" |
| n_hours_recording_off | int | hours where TrackIT was "No" (data gaps) |

### Table: `monitoring_hours` (one row per hour of EEG monitoring — THE RICHEST TIME-SERIES DATA)

~4,100+ hourly rows per 100 patients. This table gives you a complete picture of every hour of every recording.

| Column | Type | Notes |
|---|---|---|
| hour_id | PK auto | |
| study_id | FK | |
| date | date | e.g., 08/25 |
| time_start | time | e.g., 3:00 PM |
| time_end | time | e.g., 4:00 PM |
| timezone | string | CST, CDT, EST, EDT |
| recording_on | bool | TrackIT column "Yes"/"No" |
| impedance_notes | string | "W NL", "PZ>30", "sev high", electrode-specific |
| video_files_present | bool | |
| patient_on_camera | bool | |
| battery_pct | int | TrackIT battery % column |
| reviewer_name | string | tech who reviewed this hour |
| review_timestamp | datetime | "04/25/2025 08:11 AM" |

### Table: `monitoring_events` (timestamped events from within the trackit log)

These are interspersed between the hourly rows and have rich clinical content with timestamps.

| Column | Type | Notes |
|---|---|---|
| event_id | PK auto | |
| study_id | FK | |
| hour_id | FK | links to the monitoring hour it appeared in |
| event_type | enum | `eeg_reviewed`, `general_note`, `equipment_failure`, `spike_detection`, `seizure_detection` |
| timestamp | datetime | derived from the associated hour row |
| reviewer_name | string | tech name from the event line |
| description | text | full text of the note |
| eeg_finding | text | for EEGReviewed events: "W NL", "GSW seen", "sharp waves right temporal", etc. |

**Volume:** 4,504 events across 100-patient sample → projects to ~110,000 events for the full 2,469 studies. These events include:
- **EEG reviewed** (3,527/4,504 = 78%): Tech reviewed the EEG for that hour and noted findings like "W NL" (within normal limits), "Stage II sleep", "sharp waves", "GSW seen", etc.
- **General notes** (968/4,504 = 21%): Troubleshooting, patient calls, caregiver contact, equipment notes
- **Equipment failures** (9/4,504 = 0.2%): Software crashes, battery issues

---

### Table: `lab_results` (one per lab sub-document)

| Column | Type | Notes |
|---|---|---|
| lab_id | PK auto | |
| study_id | FK | |
| panel_name | string | CMP, CBC, lipid panel, AED level, etc. |
| draw_date | date | |
| ordering_provider | string | |

### Table: `lab_result_items` (one per analyte)

| Column | Type | Notes |
|---|---|---|
| lab_id | FK | |
| analyte | string | BUN, valproate level, WBC, etc. |
| value | string | |
| units | string | |
| reference_range | string | |
| flag | enum | `normal`, `high`, `low`, `critical` |

---

### Table: `patient_events` (one per patient-reported or tech-documented event with timestamp)

97 seizure/clinical events with precise timestamps found in 200-patient sample → projects to ~1,200+ for the full corpus. These are **not** the same as the monitoring_events — they come from the tech scan report's event log section.

| Column | Type | Notes |
|---|---|---|
| event_id | PK auto | |
| study_id | FK | |
| event_number | int | sequential event # as documented (e.g., "Event #3") |
| event_date | date | extracted from "03/28/2026" in event text |
| event_time | time | extracted from "18:19" or "6:55 PM" in event text |
| event_datetime | datetime | combined; this is the PRIMARY timestamp field |
| event_type | enum | `seizure`, `aura`, `staring`, `behavioral`, `medication_admin`, `activity`, `sleep`, `unknown` |
| patient_description | text | quoted patient/family description, e.g., "Chill Event", "arm stiffening" |
| tech_description | text | technologist's objective description |
| video_captured | bool | |
| eeg_correlate | text | EEG findings at event time, if documented |
| duration_sec | float | |
| clinical_significance | enum | `electroclinical_seizure`, `subclinical`, `non_epileptic`, `uncertain`, `not_assessed` |

**Example events from the data:**
- `Event 1  10/16/2020 02:25  No description given`
- `Event 18 07/01/2020 @ 01:32 "arm stiffening"`
- `Event #2 on 05/25/2017 at 00:42 ~ no description provided`
- `Event 5  10/25 21:19 "muscle spasm in right upper leg"`
- `Event 1  5/17/2024 21:00 "Feeling short of breath and feeling of doom."`

**These timestamps are critical for linkage to the EEG signal data** — they tell you exactly when to look in the EDF recording for the clinical event, enabling correlation of patient-reported symptoms with EEG waveform patterns.

---

## 2. Known Issues to Fix Before Re-extraction

### Issue A: Tech scan report `seizures` field bleeding (CRITICAL)

**79% of tech_scan_report records** have a broken `seizures` field that captures the entire report text instead of just the seizure description. This causes:
- `background` null in 75% of records (data exists but is in `seizures`)
- `slowing` null when it shouldn't be
- Artificially inflated `seizures` field length (median 762 chars, max 8,544)

**Root cause:** The regex `\bSeizures?[:\s]*([\s\S]+?)(?:\n\s*TECHNOLOGIST|\Z)` is too greedy in the flattened pdftotext output where section headers aren't always on their own lines.

**Fix:** Need a two-pass approach:
1. First identify the report format (structured vs template)
2. Use format-specific delimiters. The "Seizure:" field is always last before "TECHNOLOGIST IMPRESSION" — but when the report repeats (same patient has 2+ EEG segments concatenated), the second instance's "Automated Seizure Detection:" gets grabbed.

### Issue B: Two tech scan report formats

**Format 1 (majority, template-based):**
> "The posterior dominant rhythm was characterized by symmetric and reactive 10 Hz activity with eyes closed."

**Format 2 (newer, structured):**  
> "Awake Background: 10 Hz; 60-75 uV; posterior head regions, symmetric, waxing and waning, reactive to eye opening and closure."
> "Vertex Wave: 90-100 uV, symmetric"
> "Sleep Spindles: 12-13 Hz; 15-20 uV; frontocentral, symmetric"

Format 2 is much more parseable. The extraction pipeline should detect which format and use a format-specific parser.

### Issue C: LLM extraction failures (603 total)

| Doc type | Errors | Total | Rate |
|---|---|---|---|
| clinical_progress_note | 429 | 1,589 | 27% |
| history_and_physical | 131 | 240 | 55% |
| eeg_intake_form | 30 | 2,701 | 1% |
| patient_event_log | 11 | 39 | 28% |
| imaging_report | 1 | 430 | 0.2% |

The dominant error is `Unterminated string` (206 occurrences) — the model's output was truncated. Fix: increase `max_output_tokens` and/or split long notes into smaller chunks.

### Issue D: 280 "unknown" sections

Breakdown of what they actually are:
- **90 blank pages** (<50 chars) — fax cover sheets, image-only pages. → Classify as `blank_page`, skip.
- **85 with content** — a mix of:
  - Faxed referral orders from children's hospitals (Aurora, CHW Neurology)
  - External clinical notes (Athena/Cortica EMR exports)
  - Neurotech patient satisfaction surveys
  - Fax confirmation pages
  
Recommendation: Add `fax_cover`, `external_referral`, `satisfaction_survey` doc types. Only `external_referral` has clinical value.

### Issue E: 6 EEG reports misclassified as `imaging_report`

The segment classifier matched "EEG" in the order text and assigned `imaging_report`. Fix: add a negative pattern excluding documents that mention "EEG" but not "MRI/CT/PET".

---

## 3. Extraction Strategy by Field Type

### Deterministic (regex) — no LLM cost

These fields have stereotyped, machine-readable text and should be extracted with regex:

- All `studies` table fields from tech_scan_report headers
- `eeg_background` PDR fields (from both format 1 and format 2)
- `eeg_activations` (photic/HV performed + response)
- `eeg_slowing` severity/distribution/laterality vocabulary
- `eeg_epileptiform` frequency/morphology/distribution vocabulary  
- `technologist_impression` classification (normal/abnormal)
- `monitoring_log` summary counts
- `eeg_order` accession/provider
- `diagnosis_codes` from intake forms (regex on `G40.xxx` / `R56.x` patterns)

### LLM-assisted — local on-device model (Qwen via MLX)

These fields require natural language understanding:

- `clinical_encounters` — HPI summary, assessment/plan (free-text clinical narrative)
- `conditions` — PMH parsing into discrete condition names
- `medications` — parsing dose/frequency from varied formats, generic/brand normalization
- `imaging` findings and impression (from varied external report formats)
- `eeg_intake_form` handwritten fields (OCR quality varies)
- `patient_events` descriptions

### Hybrid — regex first, LLM fallback

- `eeg_slowing.raw_description` → regex extracts severity/distribution, LLM resolves ambiguous cases
- `eeg_epileptiform.raw_description` → same pattern
- `eeg_seizures` — regex for count/duration, LLM for complex multi-seizure narratives
- `technologist_impression.abnormality_reasons` — regex splits "due to A and B", LLM for complex compound statements

---

## 4. Implementation Phases

### Phase 1: Fix the regex extractors
- Fix seizures field bleeding
- Detect report format (template vs structured)
- Parse PDR from both formats
- Parse sleep stages
- Parse epileptiform morphology/distribution
- Parse slowing severity/distribution
- Parse technologist impression classification

### Phase 2: Re-run Stage 3 with improved extractors
- Increase max_output_tokens for clinical notes
- Add retry logic for truncated JSON
- Re-process the 603 LLM failures
- Add new doc type classifiers (fax_cover, external_referral)

### Phase 3: Build the structured database
- Create CSV/Parquet files for each table
- Validate extracted fields against known vocabularies
- Flag outliers for manual review
- Generate summary statistics

### Phase 4: Quality assurance
- Random-sample 50 patients, compare fields.json ↔ raw.txt manually
- Check PDR frequency distribution against literature norms
- Verify seizure counts match automated_seizure_detections
- Cross-check medication names against drug database
