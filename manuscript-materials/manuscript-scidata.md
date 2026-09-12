# Clinical scalp electroencephalography of 4,912 patients including multi-day ambulatory home recordings

**Authors:** Keith Morgan^1^, Charles Pickering^1^, Matthew Goodwin^1^, Han Wu^2^, Manohar Ghanta^2^, Aditya Gupta^2^, Jin Jing^2^, ChenXi Sun^2^, Daniel Goldenholz^2^, M. Brandon Westover^2^

^1^ Neurotech, Waukesha, Wisconsin, USA
^2^ Department of Neurology, Beth Israel Deaconess Medical Center and Harvard Medical School, Boston, Massachusetts, USA

**Corresponding author:** M. Brandon Westover (bwestove@bidmc.harvard.edu)

---

## Abstract

Large, clinically representative public electroencephalography (EEG) datasets are scarce and consist mainly of in-hospital recordings. We describe a de-identified clinical scalp EEG dataset comprising all studies performed by a single ambulatory EEG service provider in the United States from 2021 to 2025: 4,912 patients and 23,600 EDF recording segments totaling 212,133 hours (10.2 TB). Most are multi-day ambulatory recordings acquired in patients' homes; the remainder are routine outpatient studies. Recordings were acquired on Lifelines or EMS ambulatory systems at 256 Hz with the International 10-20 montage, and carry 225,957 technologist annotations placed during routine clinical workflow, including spike, seizure, and free-text markers. De-identified patient-level clinical metadata from scanned clinical records (age, sex, referral diagnoses, comorbidities, medications, and reported EEG findings) are provided for 98% of patients. The dataset is organized in Brain Imaging Data Structure (BIDS) format and distributed through the Brain Data Science Platform under a data use agreement. It supports development and validation of automated EEG analysis and studies of clinical annotation practice in out-of-hospital settings.

---

## Background & Summary

Expert interpretation of the electroencephalogram (EEG) remains the cornerstone of epilepsy diagnosis^1^, yet the global shortage of trained EEG readers creates a bottleneck affecting the approximately 50 million people living with epilepsy worldwide^9^. Machine learning offers a path toward scalable automated interpretation^2^, but progress depends on large, clinically representative datasets. Spike and seizure detection algorithms trained on existing public datasets can achieve high accuracy on held-out test sets yet perform substantially worse when applied to recordings from different clinical settings or hardware platforms, a persistent and well-documented generalization problem^3-6,12^.

Existing public EEG resources span a range of sizes and designs (Table 1). The CHB-MIT dataset provides 23 pediatric patients with seizure annotations^3^; the Bonn dataset offers intracranial recordings from 5 patients^4^; the Siena dataset contributes 14 patients with scalp EEG^5^. The Temple University Hospital (TUH) EEG Corpus, with over 25,000 sessions, showed that large-scale release of unselected clinical data can serve as a widely used benchmark^7^. The Harvard Electroencephalography Database (HEEDB) provides approximately 109,000 patients and 3.3 million recording hours from four hospitals^11^. These corpora are predominantly hospital-based, and publicly available clinical EEG remains limited in its coverage of acquisition hardware, clinical settings, and annotation practices.

Here we describe the Neurotech EEG Dataset^13^, which comprises all clinical EEG studies performed by a single accredited ambulatory EEG service provider between 2021 and 2025: 23,600 EDF recording segments from 4,912 patients totaling 212,133 recording hours. Three characteristics distinguish it from existing resources. First, most recordings are ambulatory or multi-day studies acquired in patients' homes, an out-of-hospital context largely absent from existing corpora; HEEDB, hosted on the same platform, comprises routine, epilepsy monitoring unit, and intensive care unit recordings acquired in clinical facilities. Second, the recordings were acquired on ambulatory hardware (Lifelines or EMS systems) that differs from the acquisition systems represented in existing corpora, which may be useful for cross-platform evaluation. Third, the clinical workflow annotations are released intact, including 51,546 spike markers and 6,956 seizure markers placed or confirmed by EEG technologists, together with free-text observations. These workflow-native annotations lack the consistency of multi-expert research labels, but they document the conditions under which automated systems must operate in practice (Figure 1). De-identified patient-level clinical metadata extracted from scanned clinical documentation accompany the recordings.

**Table 1. Comparison with existing public clinical EEG datasets.** Values for other datasets are approximate and taken from their published descriptions.

| Dataset | Patients | Sessions | Hours | Hardware | Recording setting | Annotation style |
|---|---|---|---|---|---|---|
| CHB-MIT^3^ | 23 | 23 | ~982 | Not stated | Inpatient | Expert seizure labels |
| Bonn^4^ | 5 | 5 | ~0.6 | Intracranial | Research | Segment-level labels |
| Siena^5^ | 14 | 14 | ~128 | Not stated | Inpatient | Expert seizure labels |
| TUH EEG Corpus^7^ | ~15,000 | ~25,000 | ~25,000 | Natus NicoletOne | Primarily inpatient | Clinical reports |
| Harvard EEG Database^11^ | ~109,000 | ~329,000 | ~3,300,000 | Mixed (4 sites) | Routine, EMU, ICU (in-hospital) | Clinical reports |
| **This dataset**^13^ | **4,912** | **23,600 EDF segments** | **212,133** | **Lifelines / EMS** | **Ambulatory (home) and routine outpatient** | **Workflow-native technologist annotations** |

## Methods

### Patient population and clinical context

The dataset comprises all clinical EEG recordings performed by Neurotech, LLC, an accredited EEG monitoring service provider, between 2021 and 2025. Rather than a single hospital or center, Neurotech performs ambulatory EEG in patients' homes together with some routine outpatient studies (and occasional routine inpatient bedside recordings), across geographically distributed sites in the United States, using a uniform hardware and technologist workflow. No inclusion or exclusion criteria were applied; the cohort represents the full clinical caseload. Recording types span routine outpatient EEGs (typically under 1 hour), ambulatory monitoring studies (1 to 24 hours), and prolonged multi-day ambulatory monitoring (over 24 hours). Because the acquisition system exports each continuous recording as multiple EDF files, the 4,912 patients contributed 23,600 EDF recording segments containing signal data (median 3 segments per patient, interquartile range 1 to 6; 73% of patients have more than one segment). Grouping segments by recording date indicates that they correspond to far fewer distinct EEG studies, approximately one multi-day ambulatory study per patient (median one recording session per patient, spanning roughly two recording days), so the segment count should not be read as a count of separate EEG studies.

### Recording hardware and protocol

All recordings were acquired using Lifelines or EMS ambulatory EEG systems with Persyst spike and seizure detection software. Electrodes were placed according to the International 10-20 system (Fp1, Fp2, F3, F4, C3, C4, P3, P4, O1, O2, F7, F8, T3, T4, T5, T6, Fz, Pz, Cz) together with a two-channel electrocardiogram (ECG). Additional electrodes (for example A1, A2, T1, T2, F11, F12) were placed only on request and are absent from most recordings. Recordings span 22 to 30 channels (median 28); 24% contain 29 channels including the EDF+ annotation signal. Signals were sampled at 256 Hz and stored in European Data Format (EDF+C, continuous).

### Annotation methodology

EEG technologists placed annotations during routine clinical workflow using the Persyst spike and seizure detection and clinical annotation workflow. Three annotation types are present:

1. **Event markers** (`@Spike`, `@Seizure`): point-in-time markers for detected events, including both automated detections and technologist-confirmed events.
2. **Technologist clips** (`@Clip`): segments of interest selected by the technologist for physician review, typically accompanied by descriptive labels (for example "Awake" or "Tech Event Type 1: Generalized Sharp Waves").
3. **Free-text observations** (prefixed `NT-`): narrative clinical descriptions such as "NT-Bi-occipital S/W, right dominant" or "NT-Right occipital S/W."

Additional annotations document posterior dominant rhythm (PDR) frequency and activation procedures (eyes open and closed, photic stimulation, hyperventilation). These are single-reader clinical workflow annotations, not multi-expert research labels, and inter-rater reliability was not assessed. They should therefore not be treated as gold-standard evaluation labels without independent validation, but they permit study of real-world annotation practice.

### De-identification

We performed de-identification in compliance with the Health Insurance Portability and Accountability Act (HIPAA) Safe Harbor standard, addressing three categories of protected health information (PHI) (Figure 2).

**Header scrubbing.** We removed patient name, identifier, date of birth, case number, and technologist and equipment identifiers from all EDF headers, replacing the local patient identification field with `X X X X` and the recording identification field with `Startdate DD-MMM-YYYY X X X` (shifted date).

**Date shifting.** We shifted all recording dates by a random per-patient integer offset drawn uniformly from -365 to +365 days; times of day were preserved. The same offset was applied consistently across all recordings, annotation timestamps, and clinical metadata for a given patient, so that temporal relationships within a patient are preserved.

**Free-text scrubbing.** We applied a two-tier name scrubber to annotation text: (1) each patient's own first and last name was matched and replaced with `[NAME]` regardless of word length, and (2) a broad dictionary of all first and last names in the dataset (4 or more characters, excluding common medical terms) detected additional name occurrences. Dates embedded in annotation text were detected by pattern matching and shifted by the same per-patient offset. We verified de-identification by automated audit of all output files (see Technical Validation).

A linking table mapping de-identified identifiers to original identifiers is maintained securely by the study team and is not published.

### Clinical metadata extraction

Clinical documentation was available as scanned PDF packets for 4,812 of 4,912 patients (98%), incrementally synced from a Neurotech-managed Amazon Web Services Transfer Family Secure File Transfer Protocol endpoint. Each packet contained a Neurotech technologist scan report, hourly monitoring logs, referring physician intake forms, and in many cases clinical progress notes from the referring neurologist. We developed a three-stage extraction pipeline: (1) text extraction from PDFs using pdftotext, with optical character recognition (OCR) via Tesseract for scanned pages (59% of documents required OCR); (2) document segmentation into sub-document types using regex-based landmark detection; and (3) structured field extraction using deterministic regex parsers for standardized report sections (technologist scan reports, hourly monitoring logs, EEG orders) and a locally hosted open-weight large language model (Qwen2.5, run on-device via Apple MLX) for narrative clinical text (clinical progress notes, intake forms, imaging reports). The pipeline runs entirely on-premises, so clinical text never leaves the secure environment. It identified 40,529 sub-documents across 11 document types and extracted EEG findings (posterior dominant rhythm, epileptiform discharges, seizure descriptions), referral diagnoses (International Classification of Diseases, 10th Revision, ICD-10, codes), patient demographics, medication lists, and hour-by-hour EEG monitoring data. Each clinical record was linked to its de-identified subject identifier through a four-tier name-matching procedure (exact, normalized, first-root, and Levenshtein edit distance of 2 or less), achieving 99.96% successful linkage; unmatched and low-confidence patients were excluded from the de-identified output. Manual review of 30 randomly sampled patient records found no hallucinated values across all extracted fields, and cross-checking medication names and diagnosis codes against source text confirmed accurate extraction in 94% of cases (the remaining 6% reflected minor OCR-related spelling differences in the source text rather than extraction errors). Only patient-level structured fields are released; no dates, names, or free text from the clinical records are included.

### Data formatting

We converted the dataset to BIDS-EEG format (version 1.7.0)^8,10^ and assigned each patient a de-identified identifier (`sub-NeurotechN`). Each EDF recording segment constitutes a separate session (`ses-N`), numbered sequentially per patient. For each session the release includes the de-identified EDF recording, a JSON sidecar with recording metadata, a channels table, a technologist annotation file (when annotations exist), and a session-level scans table (Figure 1). Dataset-level files include `dataset_description.json`, `participants.tsv`, `participants.json`, a `README`, and a `phenotype/` directory holding the patient-level clinical metadata tables. The files and their fields are defined in Data Records.

### Ethics

This project was conducted under Beth Israel Deaconess Medical Center (BIDMC) Institutional Review Board (IRB) protocol 2022P000417 and under a Business Associate Agreement between BIDMC and Neurotech. The IRB granted a waiver of informed consent for this retrospective use of clinical data and approved publication of the dataset in de-identified form with access restricted by a data use agreement prohibiting attempts at re-identification. The study complied with the Declaration of Helsinki.

## Data Records

The dataset^13^ is hosted on the Brain Data Science Platform (BDSP) at https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/ (DOI 10.60508/v99k-ek82) and stored at `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`. Access is controlled: users register on BDSP, complete credentialing, and sign a data use agreement, after which the full dataset can be downloaded (see Usage Notes). The release follows BIDS-EEG version 1.7.0 and comprises approximately 231,800 files totaling 10.2 TB. Table 2 defines every file type and field.

**Directory layout.** Dataset-level files sit at the root of the release. Each patient has a directory `sub-NeurotechN/` containing one session directory `ses-M/` per EDF recording segment; each session directory holds a scans table and an `eeg/` subdirectory with the recording, its sidecars, and the annotation file:

- `dataset_description.json`, `README`, `participants.tsv`, `participants.json`
- `phenotype/` with six patient-level tables, each as a `.tsv` with a `.json` data dictionary
- `sub-NeurotechN/ses-M/sub-NeurotechN_ses-M_scans.tsv`
- `sub-NeurotechN/ses-M/eeg/sub-NeurotechN_ses-M_task-EEG_eeg.edf`
- `sub-NeurotechN/ses-M/eeg/sub-NeurotechN_ses-M_task-EEG_eeg.json`
- `sub-NeurotechN/ses-M/eeg/sub-NeurotechN_ses-M_task-EEG_channels.tsv`
- `sub-NeurotechN/ses-M/eeg/sub-NeurotechN_ses-M_task-EEG_Xltek.csv` (present for 14,491 sessions)

**Signal-bearing segments and header-only stubs.** Of the EDF files in the release, 23,600 contain signal data. A further 30,719 EDF files are header-only stubs produced by the acquisition system at recording-session boundaries and aborted-start events; they contain a valid EDF header with channel definitions but no data records. They are released alongside the signal-bearing files, with their own session directories and sidecars, to preserve session-level integrity for users wishing to reconstruct complete clinical visits. For any signal-level analysis they should be excluded, for example by filtering on the number of data records in the EDF header or on `RecordingDuration` in the JSON sidecar.

**Annotation file.** The annotation file name retains the `_Xltek` suffix assigned by the conversion pipeline; the annotations themselves originate from the Persyst-based clinical workflow described in Methods. Each row holds the annotation text and its absolute, date-shifted timestamp. Event markers are prefixed with `@` (for example `@Spike`, `@Seizure`, `@Clip: Awake`), free-text technologist observations are prefixed with `NT-`, and remaining rows are workflow labels such as `Eyes Closed` or `Photic Stimulation`. Category counts reported in this paper were derived from these strings by keyword matching using code in the project repository.

**Clinical metadata.** The `phenotype/` tables contain de-identified, patient-level structured fields extracted from technologist scan reports and intake forms as described in Methods. Rows are keyed by `participant_id`; patients without clinical documentation are absent. `participants.tsv` carries age and sex for the patients for whom they could be extracted and `n/a` otherwise. Ages above 89 years are top-coded to 90.

**Table 2. Files and fields in the released dataset.** One row per file type. Row counts for the phenotype tables are data rows excluding the header.

| File | Rows or count | Fields | Definition |
|---|---|---|---|
| `dataset_description.json` | 1 | Name, BIDSVersion, DatasetType, License, Authors | BIDS dataset-level metadata |
| `participants.tsv` / `.json` | 1 per subject directory | participant_id, age, sex | One row per subject directory in the release. `age`: age at first EEG in years (top-coded at 90; `n/a` if unavailable). `sex`: M, F, or n/a |
| `phenotype/demographics.tsv` | 2,692 | participant_id, age, sex | Patients with extractable demographics |
| `phenotype/diagnoses.tsv` | 10,290 | participant_id, icd10_code | One row per unique patient and ICD-10 referral or diagnosis code |
| `phenotype/comorbidities.tsv` | 22,671 | participant_id, condition | One row per unique patient and comorbid condition (normalized text) |
| `phenotype/medications.tsv` | 21,417 | participant_id, medication | One row per unique patient and medication (normalized name) |
| `phenotype/eeg_findings.tsv` | 4,409 | participant_id, ever_abnormal, any_epileptiform, any_seizure, any_slowing, median_pdr_hz | Patient-level flags (0 or 1) aggregated over the patient's technologist reports; median posterior dominant rhythm in Hz |
| `phenotype/monitoring.tsv` | 4,105 | participant_id, total_monitoring_hours, monitoring_days | Aggregates of the hour-by-hour monitoring logs |
| `*_scans.tsv` | 54,319 sessions | filename, acq_time | Relative path of the EDF file and its date-shifted acquisition start (ISO 8601) |
| `*_task-EEG_eeg.edf` | 23,600 with signal; 30,719 header-only | EDF+C | De-identified recording; header patient field `X X X X` |
| `*_task-EEG_eeg.json` | 1 per session | TaskName, Manufacturer, PowerLineFrequency, SamplingFrequency, SoftwareFilters, RecordingDuration, RecordingType, EEGReference, EEGGround, EEGPlacementScheme, EEGChannelCount, EOGChannelCount, ECGChannelCount, EMGChannelCount, MiscChannelCount, TriggerChannelCount | BIDS EEG sidecar. `RecordingDuration` in seconds (0 for header-only stubs); `PowerLineFrequency` 60 Hz; `EEGPlacementScheme` 10-20 |
| `*_task-EEG_channels.tsv` | 1 per session | name, type, units, low_cutoff, high_cutoff, description, sampling_frequency, status, status_description | One row per channel. `type`: EEG, ECG, or MISC. `units`: uV. Cutoffs in Hz. `status` is `good` for all channels (no per-channel quality assessment was performed) |
| `*_task-EEG_Xltek.csv` | 14,491 sessions | Text, CreationTime | One row per annotation. `Text`: annotation string as entered in the clinical workflow (names scrubbed). `CreationTime`: date-shifted absolute timestamp (ISO 8601) |

## Data Overview

Table 3 and Figure 3 summarize the contents of the release. Of the 23,600 signal-bearing EDF segments, 36% are under one hour, 53% are between 1 and 24 hours, and 11% exceed 24 hours (Figure 3a); the segments correspond to approximately one multi-day ambulatory study per patient. Technologist clips (53,280) and spike markers (51,546) are the most frequent annotation categories, followed by free-text observations, sharp waves (21,290), slowing (19,364), activation procedures (11,688), and seizure markers (6,956) (Figure 3b); 14,491 segments (61%) carry at least one annotation, with a median of 8 annotations per annotated segment (interquartile range 3 to 19). Epilepsy (ICD-10 G40) accounts for 54% of referral codes, followed by convulsions (R56, 13%) and abnormal movements (R25, 5%) (Figure 3c). Age at first EEG spans infancy to old age with a median of 27 years and a bimodal distribution reflecting pediatric and adult referrals (Figure 3d). Among 10,726 technologist reports, 34% were read as abnormal, interictal epileptiform discharges were documented in 6,345 and electrographic seizures in 2,379; the posterior dominant rhythm frequency peaks at 9 to 10 Hz (Figure 3e), and generalized spike and spike-and-wave patterns are the most common epileptiform morphologies (Figure 3f). Every value in this section is regenerated from the released data by the code described in Code Availability.

**Table 3. Patient and study characteristics.** Clinical metadata were extracted from technologist scan reports and referring physician documentation for the patients with available clinical records (4,812 of 4,912). Age and sex were extractable for 2,915 and 3,005 patients respectively. EEG findings are from technologist scan reports (10,726 studies). Recording statistics are from the full BIDS release. IQR, interquartile range.

| Characteristic | Value | Notes |
|---|---|---|
| **Patients** | | |
|   Unique patients | 4,912 |  |
|   With clinical documentation | 4,812 | (98%) |
|   Age at first EEG, median (IQR) | 26.7 (13.4 to 48.2) | n = 2,915 |
|   Male | 1,374 | (46%) |
|   Female | 1,631 | (54%) |
| **Referral indications (ICD-10)** |  | n = 13,049 codes recorded across intake documents |
|   Epilepsy (G40.x) | 7,073 | (54%) |
|   Convulsions (R56.x) | 1,648 | (13%) |
|   Abnormal movements (R25.x) | 618 | (5%) |
|   Other | 3,710 | (28%) |
| **EEG recordings** | | |
|   EDF segments with signal data | 23,600 |  |
|   Total recording hours | 212,133 |  |
|   Segment duration, median (IQR) | 3.0 (0.3 to 12.3) | hours |
|   Segments per patient, median (IQR) | 3.0 (1.0 to 6.0) |  |
|   Patients with multiple segments | 3,570 | (73%) |
|   Segments with annotation files | 14,491 | (61%) |
|   Annotations, total | 225,957 |  |
| **EEG findings (technologist reports)** |  | n = 10,726 studies |
|   Normal | 2,506 | (23%) |
|   Abnormal | 3,693 | (34%) |
|   With epileptiform discharges | 6,345 |  |
|   With seizures captured | 2,379 | (22%) |

## Technical Validation

### Data completeness and format compliance

All 23,600 signal-bearing EEG recordings were validated for EDF format compliance during BIDS conversion, and every session directory was generated with its sidecar, channels table, and scans table by the same conversion script. Channel configuration is consistent across recordings, with all signal-bearing files containing 22 to 30 channels at 256 Hz (median 28 channels). The 30,719 header-only stubs were verified to contain zero data records and are documented in Data Records. Signal quality metrics beyond format compliance (for example impedance values or artifact rates) are not reported; users should apply quality control appropriate to their use case. Figure 4 shows representative traces from one released recording, illustrating normal background activity and an interictal spike with its accompanying technologist annotation.

### Annotation completeness

Of the 23,600 signal-bearing recordings, 14,491 (61%) have at least one technologist annotation file, and nearly all patients have at least one annotated recording. Annotation density varies widely: the median annotated recording contains 8 annotations (interquartile range 3 to 19), corresponding to 1.08 annotations per hour (interquartile range 0.46 to 2.90), with routine EEGs typically showing higher per-hour density and prolonged studies more total events (Figure 3b).

### De-identification verification

We verified de-identification through automated audit of all output files at both the EEG signal and clinical metadata levels:

1. **EDF headers**: we re-read all de-identified EDF files and confirmed that the local patient identification field contained only `X X X X` and the recording identification field only the shifted start date, with no residual patient names, identifiers, technologist or equipment identifiers, or unshifted dates (Figure 2).
2. **Annotation text**: we scanned all 225,957 annotation text entries from the source data for potential PHI. Pattern matching identified annotations containing embedded dates (all shifted in the output) and annotations containing patient first or last names (all replaced with `[NAME]` in the output). No medical record numbers, phone numbers, or other identifiers were detected in the released data.
3. **Clinical metadata**: de-identified fields underwent automated screening for residual `Last, First` name patterns, untranslated dates, phone-number-like patterns, and street-address patterns. All extracted dates were shifted using each patient's assigned offset, the same offset applied to that patient's EEG recording dates and annotation timestamps; only date-free patient-level aggregates are released. Patients whose name match to the linking table fell below high or medium confidence (29 of 7,364 clinical record folders) were excluded from the release.
4. **File structure**: output file and directory names contain only de-identified subject identifiers (`sub-NeurotechN`) and session numbers.

### Clinical metadata extraction accuracy

Manual review of 30 randomly sampled patient records compared every extracted field against the source documents and found no fabricated values. Cross-checking medication names and diagnosis codes against the source text confirmed accurate extraction in 94% of cases, with the remainder attributable to OCR-related spelling variation in the source. The distribution of extracted posterior dominant rhythm frequencies peaks at 9 to 10 Hz with 85% of values in the 8 to 13 Hz range (Figure 3e), consistent with the expected physiological distribution and providing an independent check on the extraction pipeline.

## Usage Notes

### Access procedure

The dataset is distributed under controlled access because it contains patient-level health information (diagnoses, medications, EEG findings) together with age and sex, which under the applicable regulations requires safeguards against re-identification. Users register at https://bdsp.io with their name, institution, and email address, complete BDSP credentialing, and sign the BDSP data use agreement, which prohibits attempts at re-identification and redistribution of the data. Credentialed users then receive access credentials for direct download from the storage location given in Data Records. The text of the data use agreement is publicly viewable at https://bdsp.io/content/nf89816gtxbon11kbr9a/view-dua/1.0/ and the dataset license at https://bdsp.io/content/nf89816gtxbon11kbr9a/view-license/1.0/.

### Reading the data

The release conforms to BIDS-EEG and can be read with standard tools including MNE-Python, MNE-BIDS, pyedflib, and edfio. Because each EDF segment is a separate BIDS session, users reconstructing complete clinical studies should group sessions by patient and by the date-shifted acquisition time in `scans.tsv`; segments from the same study share the same date-shift offset, so their relative timing is preserved. Header-only stubs (zero data records; `RecordingDuration` of 0 in the sidecar) should be excluded from signal-level analyses. Annotation timestamps in `CreationTime` are absolute, date-shifted times on the same clock as the EDF start time, so the offset of an annotation within a recording is the difference between `CreationTime` and the EDF start time. The `Manufacturer` field of the JSON sidecars identifies the acquisition hardware as Lifelines or EMS ambulatory equipment; per-recording attribution to one of the two systems is not available in the release.

### Intended uses and limitations

The annotations provide pre-existing labels for spike and seizure detection (51,546 spike markers and 6,956 seizure markers across 14,491 annotated segments), and the mix of routine and multi-day home recordings supports evaluation of algorithms across recording settings. The unselected cohort and linked clinical metadata support studies of EEG finding prevalence and of annotation practice in clinical workflow. Users should note the following limitations. First, all recordings originate from a single service provider using one hardware and acquisition workflow; although studies were acquired in many settings and geographically distributed sites, generalization to other providers and platforms requires caution. Second, annotations are clinical workflow annotations placed by technologists during routine practice, not multi-expert research labels, and may include unconfirmed automated detections; they should not be treated as ground truth without independent validation. Third, clinical metadata were extracted from scanned documentation with OCR, regex parsing, and a large language model, and coverage varies by field: age is available for 59% of patients, sex for 61%, referral diagnosis codes for 63%, and anti-seizure medication data for 32%; fields extracted from handwritten forms have lower accuracy than those from typed notes. Fourth, annotation coverage is heterogeneous: 61% of signal-bearing segments have annotation files. Fifth, the release contains 30,719 header-only stubs alongside the 23,600 signal-bearing recordings, as described above. Sixth, name-based linkage between clinical records and de-identified subject identifiers excluded 0.04% of clinical record folders whose names differed substantially between source systems.

## Data Availability

The Neurotech EEG Dataset^13^ is available through the Brain Data Science Platform at https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/ (DOI 10.60508/v99k-ek82) and is stored at `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`. Access is controlled: users register on BDSP, complete credentialing, and sign a data use agreement prohibiting re-identification, after which the complete BIDS release (EEG recordings, sidecars, annotation files, participants table, and phenotype tables, as defined in Data Records and Table 2) can be downloaded. The released data are de-identified; the linking table is not shared.

## Code Availability

All code used to build, de-identify, and validate the release is available at https://github.com/bdsp-core/Neurotech-EEG-Wrangling. The repository contains the BIDS conversion and de-identification pipeline (`build_bids.py`), the de-identification audit, the clinical metadata extraction pipeline (`ehr_pipeline/`, including the on-premises OCR and large language model extraction and the phenotype table builder), and the annotation category keyword mapping. Every quantitative value in this paper is regenerated from de-identified data by `reproduce_manuscript_numbers.py`, as documented in `REPRODUCIBILITY.md`; the EEG and annotation statistics can additionally be recomputed directly from the released BIDS dataset with `compute_eeg_stats_from_s3.py`. The pipeline is written in Python 3 and uses pyedflib for EDF handling, pdftotext and Tesseract for text extraction, and Qwen2.5 via Apple MLX for narrative text extraction.

## Author Contributions

M.B.W., D.M.G., K.M., and C.P. conceived and designed the study. K.M., C.P., and M.G. provided the clinical EEG data and domain expertise. H.W., M.G. (Ghanta), A.G., J.J., and C.S. developed the de-identification, conversion, and clinical-metadata-extraction pipelines and performed the analyses. M.B.W. and D.M.G. supervised the work. H.W. and M.B.W. drafted the manuscript. All authors critically revised the manuscript and approved the final version.

## Competing Interests

M.B.W. is a co-founder of, scientific advisor and consultant to, and has personal equity interest in Beacon Biosignals. K.M., C.P., and M.G. are employees of Neurotech; K.M. also has personal equity interest in Neurotech. D.M.G. has received speaker fees from Harvard Medical School, AAN, AES, ACNS, NNS, AI in Epilepsy and Neurology, Florida Epilepsy Alliance, and UT-Austin; has previously been a paid consultant for Neuro Event Labs, IDR, LivaNova, Health Advances, Duke University, Bloom Insights, and Wiley; and has received grants from NIH, ABPN, BIDMC, and the Lions Club. The remaining authors declare no competing interests.

## Funding

M.B.W. receives research funding from the National Institutes of Health (RF1AG064312, RF1NS120947, R01AG073410, R01HL161253, R01NS126282, R01AG073598, R01NS131347, R01NS130119). D.M.G. receives research funding from the National Institutes of Health (K23NS124656, R21NS142800) and the American Board of Psychiatry and Neurology.

---

## Figure Legends

**Figure 1.** Data pipeline from clinical recording to public release. Clinical EEG from 4,912 patients recorded between 2021 and 2025 on Lifelines or EMS ambulatory equipment with Persyst detection was exported as 23,600 signal-bearing EDF recording segments (212,133 hours) with annotation files, de-identified through header scrubbing, per-patient date shifting (uniform random offset of up to 365 days in either direction), and automated name replacement in free text, converted to BIDS-EEG format, and released through the Brain Data Science Platform under a data use agreement.

**Figure 2.** De-identification of EDF header fields. Each row shows a header field before de-identification (containing protected health information) and after. Patient names are replaced with placeholders, identifiers are reassigned, dates are shifted by a consistent per-patient random offset, and technologist and equipment identifiers are removed. All examples shown are fictitious.

**Figure 3.** Overview of the released data. (a) Distribution of EDF segment duration on a logarithmic scale (n = 23,600 signal-bearing segments); dashed lines mark 1 hour and 24 hours. (b) Most frequent annotation categories among the 225,957 annotations, derived from annotation text by keyword matching; categories are not mutually exclusive and the residual uncategorized remainder is omitted. (c) Referral indications by ICD-10 code group (n = 13,049 codes from intake documents). (d) Age at first EEG (n = 2,915 patients with extractable date of birth); the dashed line marks the median. (e) Posterior dominant rhythm frequency extracted from technologist reports (n = 8,057 studies); shading marks the 8 to 13 Hz range. (f) Interictal epileptiform discharge morphology by spatial distribution across 6,345 studies with documented discharges; cell values are numbers of studies and a study may contribute to several cells.

**Figure 4.** Example EEG traces from one released recording, shown in a longitudinal bipolar (double-banana) montage after 1 to 30 Hz band-pass and 60 Hz notch filtering. (a) Normal background activity. (b) An interictal spike (arrow) with the accompanying technologist annotation "NT-Bi-occipital S/W, right dominant", illustrating the free-text observations preserved in the dataset. Scale bars: 100 microvolts and 1 second.

---

## References

1. Noachtar, S. & Rémi, J. The role of EEG in epilepsy: a critical review. *Epilepsy Behav.* **15**, 22-33 (2009). https://doi.org/10.1016/j.yebeh.2009.02.035
2. Roy, Y. et al. Deep learning-based electroencephalography analysis: a systematic review. *J. Neural Eng.* **16**, 051001 (2019). https://doi.org/10.1088/1741-2552/ab260c
3. Shoeb, A. & Guttag, J. Application of machine learning to epileptic seizure detection. In *Proceedings of the 27th International Conference on Machine Learning (ICML 2010)* 975-982 (Omnipress, 2010).
4. Andrzejak, R. G. et al. Indications of nonlinear deterministic and finite-dimensional structures in time series of brain electrical activity: dependence on recording region and brain state. *Phys. Rev. E* **64**, 061907 (2001). https://doi.org/10.1103/PhysRevE.64.061907
5. Detti, P., Vatti, G. & Zabalo Manrique de Lara, G. EEG synchronization analysis for seizure prediction: a study on data of noninvasive recordings. *Processes* **8**, 846 (2020). https://doi.org/10.3390/pr8070846
6. Gemein, L. A. W. et al. Machine-learning-based diagnostics of EEG pathology. *NeuroImage* **220**, 117021 (2020). https://doi.org/10.1016/j.neuroimage.2020.117021
7. Obeid, I. & Picone, J. The Temple University Hospital EEG Data Corpus. *Front. Neurosci.* **10**, 196 (2016). https://doi.org/10.3389/fnins.2016.00196
8. Pernet, C. R. et al. EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. *Sci. Data* **6**, 103 (2019). https://doi.org/10.1038/s41597-019-0104-8
9. World Health Organization. *Epilepsy: A Public Health Imperative* (World Health Organization, 2019). https://www.who.int/publications/i/item/epilepsy-a-public-health-imperative
10. Gorgolewski, K. J. et al. The brain imaging data structure, a format for organizing and describing outputs of neuroimaging experiments. *Sci. Data* **3**, 160044 (2016). https://doi.org/10.1038/sdata.2016.44
11. Sun, C. et al. Harvard Electroencephalography Database: a comprehensive clinical electroencephalographic resource from four Boston hospitals. *Epilepsia* **66**, 3411-3425 (2025). https://doi.org/10.1111/epi.18487
12. Xu, L. et al. Cross-dataset variability problem in EEG decoding with deep learning. *Front. Hum. Neurosci.* **14**, 103 (2020). https://doi.org/10.3389/fnhum.2020.00103
13. Morgan, K. et al. The Neurotech EEG Dataset. *Brain Data Science Platform* https://doi.org/10.60508/v99k-ek82 (2026).
