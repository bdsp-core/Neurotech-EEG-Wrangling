# The Neurotech EEG Dataset: A Large Clinical Scalp EEG Corpus for AI Development and Research

**Authors:** Keith Morgan^1^, Charles Pickering^1^, Matthew Goodwin^1^, Han Wu^2^, Manohar Ghanta^2^, Aditya Gupta^2^, Jin Jing^2^, ChenXi Sun^2^, Daniel Goldenholz^2^, M. Brandon Westover^2^

^1^ Neurotech, [City, State]
^2^ Department of Neurology, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA

**Corresponding author:** M. Brandon Westover, MD, PhD (bwestove@bidmc.harvard.edu)

---

## Abstract

We present the Neurotech EEG Dataset, a large clinical scalp electroencephalography (EEG) corpus comprising 23,607 EEG recordings from 4,914 patients acquired by a single EEG monitoring service provider across in-home and inpatient settings between 2021 and 2025, totaling 212,186 hours of signal data and 10.2 TB of storage. All recordings used the standard International 10-20 montage, spanning the full spectrum of clinical EEG practice: routine outpatient recordings (36%), ambulatory and short-term monitoring (53%), and prolonged continuous monitoring (11%). Recordings are accompanied by 226,486 technician-placed annotations including 50,482 spike markers, 6,892 seizure markers, 21,330 sharp wave annotations, and free-text clinical observations. We release the dataset in Brain Imaging Data Structure (BIDS) EEG format through the Brain Data Science Platform (BDSP) with de-identification compliant with the Health Insurance Portability and Accountability Act (HIPAA), including per-patient date shifting and automated name scrubbing of free-text annotations. By preserving workflow-native annotations, this resource enables researchers to train and validate EEG algorithms against the variability and noise of real clinical practice -- bridging the gap between benchmark performance and real-world deployment.

---

## Background & Summary

Expert interpretation of the electroencephalogram (EEG) remains the cornerstone of epilepsy diagnosis, yet the global shortage of trained EEG readers creates a bottleneck affecting the approximately 50 million people living with epilepsy worldwide^1^. Machine learning (ML) offers a path toward scalable automated interpretation^2^, but the scarcity of large, clinically representative public datasets has constrained progress. Spike detection algorithms trained on existing public datasets can achieve high accuracy on held-out test sets but can drop substantially when deployed on recordings from different clinical settings or hardware platforms -- a persistent and well-documented generalization problem^3-6^.

Existing public EEG resources span a range of sizes and designs but share common limitations (Table 1). The CHB-MIT dataset provides 23 pediatric patients with seizure annotations^3^; the Bonn dataset offers intracranial recordings from 5 patients^4^; the Siena dataset contributes 14 patients with scalp EEG^5^. The Temple University Hospital (TUH) EEG Corpus, at over 25,000 sessions, demonstrated that large-scale release of unselected clinical data could become the most widely used benchmark in the EEG artificial intelligence (AI) literature^7^. However, publicly available clinical EEG remains insufficiently diverse across institutions, hardware platforms, clinical settings, and annotation practices.

Here we release the Neurotech EEG Dataset -- to our knowledge, one of the largest public clinical EEG corpora from a single service provider -- comprising 23,607 EEG recordings from 4,914 patients totaling 212,186 recording hours. This dataset complements TUH by providing: (1) a majority of ambulatory and multi-day recordings (53% of recordings, compared with a predominantly inpatient corpus in TUH), (2) Natus/Xltek hardware enabling cross-platform algorithm validation, and (3) intact clinical workflow annotations including 50,482 technician-confirmed spike events and 6,892 seizure markers, enabling study of real-world annotation practices. We preserve these workflow-native annotations deliberately: while they lack the consistency of multi-expert research labels, they capture the noise, variability, and practical constraints under which automated systems must ultimately operate (Figure 1).

**Table 1. Comparison with existing public EEG datasets.**

| Dataset | Patients | Sessions | Hours | Hardware | Recording types | Annotation style |
|---|---|---|---|---|---|---|
| CHB-MIT^3^ | 23 | 23 | ~982 | Unknown | Inpatient | Expert seizure labels |
| Bonn^4^ | 5 | 5 | ~0.6 | Intracranial | Research | Segment-level labels |
| Siena^5^ | 14 | 14 | ~128 | Unknown | Inpatient | Expert seizure labels |
| TUH EEG Corpus^7^ | ~15,000 | ~25,000 | ~25,000 | Natus NicoletOne | Primarily inpatient | Clinical reports |
| **Neurotech (this work)** | **4,914** | **23,607** | **212,186** | **Natus/Xltek** | **Routine + ambulatory + ICU** | **Workflow-native** |

## Methods

### Patient population and clinical context

The dataset comprises all clinical EEG recordings performed by Neurotech, LLC -- an accredited EEG monitoring service provider -- between 2021 and 2025. Rather than a single hospital or center, Neurotech acquires recordings across diverse settings: in-home ambulatory studies performed in patients' homes, and continuous monitoring in partner hospital intensive care units (ICUs) and epilepsy monitoring units (EMUs) across the United States, using a uniform hardware and technologist workflow. No inclusion or exclusion criteria were applied; this cohort represents the full clinical caseload. Recording types span routine outpatient EEGs (typically <1 hour), ambulatory monitoring studies (1-24 hours), and prolonged continuous EEG monitoring in the intensive care unit (ICU; >24 hours). The 4,914 unique patients in the released dataset contributed 23,607 EEG recordings, with 73% of patients (3,570) having multiple recordings (median 3 per patient, interquartile range 1-6).

### Recording hardware and protocol

All recordings were acquired using Natus/Xltek NeuroWorks EEG systems. Electrodes were placed according to the standard International 10-20 system, with typical montages including 25-29 channels: Fp1, Fp2, F3, F4, C3, C4, P3, P4, O1, O2, F7, F8, T3, T4, T5, T6, Fz, Pz, Cz, A1, A2, T1, T2, F11, F12, and an electrocardiogram (ECG) channel. Recordings span 22-30 channels (median 28); 24% contain 29 channels including the EDF+ annotation signal. Signals were sampled at 256 Hz and stored in European Data Format (EDF+C, continuous).

### Annotation methodology

EEG technicians placed annotations during routine clinical workflow using the Natus/Xltek annotation system. Three annotation types are present:

1. **Event markers** (`@Spike`, `@Seizure`): point-in-time markers for detected events, likely including both Persyst automated detections and technician-confirmed events.
2. **Technician clips** (`@Clip`): segments of interest selected by the technician for physician review, typically accompanied by descriptive labels (e.g., "Awake", "Tech Event Type 1: Generalized Sharp Waves").
3. **Free-text observations** (prefixed `NT-`): narrative clinical descriptions such as "NT-Bi-occipital S/W, right dominant" or "NT-Right occipital S/W."

Additional annotations document posterior dominant rhythm frequency and activation procedures (eyes open/closed, photic stimulation, hyperventilation). These are single-reader clinical workflow annotations, not multi-expert research labels. Inter-rater reliability was not assessed. While this limits their use as gold-standard evaluation labels, it enables study of real-world annotation practices including human-AI collaboration in EEG reading -- a research direction impossible with curated labels alone.

### De-identification

We performed de-identification in compliance with HIPAA Safe Harbor standards, addressing three categories of protected health information (PHI):

**Header scrubbing.** We removed patient name, identifier, date of birth, case number, and technician identifiers from all EDF headers, replacing the local patient identification field with `X X X X`.

**Date shifting.** We shifted all recording dates by a random per-patient offset drawn uniformly from [-365, +365] days; times of day were preserved. The same offset was applied consistently across all recordings and annotation timestamps for a given patient.

**Free-text scrubbing.** We applied a two-tier name scrubber to annotation text: (1) each patient's own first and last name was matched and replaced with `[NAME]` regardless of word length, and (2) a broad dictionary of all first and last names in the dataset (4+ characters, excluding common medical terms) detected additional name occurrences. Dates embedded in annotation text were detected via pattern matching and shifted by the same per-patient offset. We verified de-identification by automated audit of all output files (see Technical Validation).

A linking table mapping de-identified identifiers to original identifiers is maintained securely and not published.

### Clinical metadata extraction

Clinical documentation was available as scanned PDF packets for 4,812 of 4,914 patients (98%), incrementally synced from a Neurotech-managed Amazon Web Services (AWS) Transfer Family Secure File Transfer Protocol (SFTP) endpoint. Each packet contained a Neurotech technologist scan report, hourly monitoring logs, referring physician intake forms, and in many cases clinical progress notes from the referring neurologist. We developed a three-stage extraction pipeline: (1) text extraction from PDFs using pdftotext with optical character recognition (OCR) via Tesseract for scanned pages (59% of documents required OCR), (2) document segmentation into sub-document types using regex-based landmark detection, and (3) structured field extraction using a combination of deterministic regex parsers for standardized report sections (technologist scan reports, hourly monitoring logs, EEG orders) and a locally hosted open-weight large language model (LLM; Qwen2.5, run on-device via Apple MLX) for narrative clinical text (clinical progress notes, intake forms, imaging reports). The extraction pipeline runs entirely on-premises with a local open-weight model, so clinical text can be processed without leaving the secure environment. The pipeline identified 40,529 sub-documents across 11 document types, extracting EEG findings (posterior dominant rhythm, epileptiform discharges, seizure descriptions), referral diagnoses (International Classification of Diseases, 10th Revision [ICD-10] codes), patient demographics, medication lists, and hour-by-hour EEG monitoring data with timestamps for clinically relevant events. Each EHR patient was linked to their corresponding BDSP de-identified identifier through a four-tier name-matching procedure (exact, normalized, first-root, and Levenshtein edit distance ≤ 2), achieving 99.96% successful linkage; unmatched and low-confidence patients were excluded from de-identified output. Manual review of 30 randomly sampled patient records found zero hallucinated values across all extracted fields, and cross-checking medication names and diagnosis codes against source text confirmed accurate extraction in 94% of cases (the remaining 6% reflected minor OCR-related spelling differences in the source text, not extraction errors). All extraction code is available in the project repository.

### Ethics

This project was conducted under Institutional Review Board (IRB) protocol number 2022P000417, with the BIDMC IRBs granting a waiver of consent, and under a Business Associate Agreement (BAA) between BIDMC and Neurotech. The IRB approved the publication of the dataset in a de-identified form with access restricted by a data usage agreement prohibiting attempts at re-identification. The study also complied with the Declaration of Helsinki.

### Data formatting

We converted the dataset to BIDS-EEG format (version 1.7.0)^8^ and assigned each patient a de-identified identifier (`sub-NeurotechN`). Each EDF recording segment constitutes a separate session (`ses-N`), numbered sequentially per patient. For each session, the following files are provided (Figure 1):

- `*_task-EEG_eeg.edf`: de-identified EEG recording
- `*_task-EEG_eeg.json`: recording metadata (sampling frequency, channel counts, duration)
- `*_task-EEG_channels.tsv`: channel names, types, units, and filter settings
- `*_task-EEG_Xltek.csv`: technician annotations with shifted timestamps (when present)
- `*_scans.tsv`: session-level acquisition time

Dataset-level files include `dataset_description.json`, `participants.tsv`, `participants.json`, and a `README`. The full BIDS dataset comprises 231,880 files totaling 10.2 TB of storage.

## Data Records

The dataset is hosted on the Brain Data Science Platform (BDSP) at `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`. Table 2 summarizes the dataset characteristics.

**Table 2. Patient and study characteristics.** Clinical metadata was extracted from technician scan reports and referring physician documentation for the subset of patients with available clinical records (n=4,812 of 4,914 patients, 98%). Age and sex were available for 2,915 and 3,005 patients respectively. Comorbidities and anti-seizure medications are summarized in Supplementary Figure 3. EEG findings are from technologist scan reports. EEG recording statistics are from the full BIDS dataset.

| Characteristic | Value | Notes |
|---|---|---|
| **Patients** | | |
|   Unique patients | 4914 |  |
|   With clinical documentation | 4812 | (98%) |
|   Age at first EEG, median (IQR) | 26.7 (13.4-48.2) | n=2915 |
|   Male | 1374 | (46%) |
|   Female | 1631 | (54%) |
|  |  |  |
| Referral indications (ICD-10) |  | n=13049 codes |
|   Epilepsy (G40.x) | 7073 | (54%) |
|   Convulsions (R56.x) | 1648 | (13%) |
|   Abnormal movements (R25.x) | 618 | (5%) |
|   Other | 3710 | (28%) |
|  |  |  |
| **EEG recordings** | | |
|   Total recordings with signal data | 23,607 |  |
|   Total recording hours | 212,186 |  |
|   Duration, median (IQR) | 3.0 (0.3-12.3) | hours |
|   Recordings per patient, median (IQR) | 3.0 (1.0-6.0) |  |
|   Patients with multiple recordings | 3570 | (73%) |
|  |  |  |
| EEG findings (tech reports) |  | n=10726 studies |
|   Normal | 2506 | (23%) |
|   Abnormal | 3693 | (34%) |
|   With epileptiform discharges | 6345 |  |
|   With seizures captured | 2379 |  |

*IQR = interquartile range; ASM = anti-seizure medication; EHR = electronic health record.*

The majority of recordings (53%) fall in the 1-24 hour range consistent with ambulatory or short-term monitoring, while 36% are routine outpatient EEGs under one hour and 11% are prolonged continuous monitoring studies exceeding 24 hours (Supplementary Table 1, Figure 2A). In addition to the 23,607 recordings containing signal data, the BIDS dataset includes 30,819 header-only EDF files originating from the Natus/Xltek source export. These zero-record stubs are produced by the acquisition system at recording-session boundaries and aborted-start events; they contain a valid EDF header with channel definitions but no data records. We release them alongside the full-signal recordings to preserve session-level integrity for users wishing to reconstruct complete clinical visits, but they should be filtered out (e.g., on `n_records > 0`) for any signal-level analysis.

Technician clips and spike markers are the most common annotation types, followed by free-text clinical observations and activation procedure documentation (Supplementary Table 2, Supplementary Figure 1).

The patient population spans the full age range from infancy to old age, with a median age of 27 years at first EEG (IQR 13-48) and a bimodal distribution reflecting both pediatric epilepsy referrals and adult-onset seizure disorders (Figure 3B). Epilepsy diagnoses (ICD-10 G40.x) account for 54% of referral indications, followed by unspecified convulsions (13%) and abnormal movements (5%) (Figure 3A). EEG findings extracted from technologist scan reports demonstrate a high yield of clinically significant abnormalities: 34% of studies were classified as abnormal, with interictal epileptiform discharges documented in 6,345 studies and electrographic seizures captured in 2,379 (Figure 4). The posterior dominant rhythm frequency distribution peaks at 9-10 Hz (Figure 4A), consistent with the expected physiological range and providing independent validation of the extraction pipeline. The morphology and spatial distribution of epileptiform discharges (Figure 4B) shows a predominance of generalized spike and spike-and-wave patterns, consistent with the high proportion of primary generalized epilepsy in the referral population.

## Technical Validation

### Data completeness and quality

All 23,607 EEG recordings were validated for EDF format compliance during BIDS conversion. Channel configuration is consistent across recordings, with all readable files containing 22-30 channels at 256 Hz (median: 28 channels). An additional 30,819 EDF files in the BIDS tree are zero-record header stubs from the Natus/Xltek source export (recording boundaries, interrupted sessions); they are documented in Data Records and should be filtered out for signal-level analyses. Signal quality metrics beyond format compliance (e.g., impedance values, artifact rates) are not reported; users should apply their own quality control procedures appropriate to their use case.

### Annotation completeness

Of the 23,607 EEG recordings, 14,517 (61%) have at least one technician annotation file. Across the patient population, nearly all subjects have at least one annotated recording. Annotation density varies widely: the median annotated recording contains 8 annotations (IQR 3-21), corresponding to 1.13 annotations per hour (IQR 0.47-2.78), with routine EEGs typically showing higher per-hour density and prolonged monitoring studies more total events (Figure 2B, Supplementary Figure 1).

### De-identification verification

We verified de-identification through automated audit of all output files at both the EEG signal and clinical metadata levels:

1. **EDF headers**: We re-read all de-identified EDF files and confirmed that the local patient identification field contained only `X X X X`, with no residual patient names, identifiers, or unshifted dates (Supplementary Figure 2).
2. **Annotation text**: We scanned all 226,486 annotation text entries from the source data for potential PHI. Pattern matching identified annotations containing embedded dates (all shifted in output) and annotations containing patient first or last names (all replaced with `[NAME]` in output). No medical record numbers, phone numbers, or other identifiers were detected in the released data.
3. **Clinical metadata**: De-identified EHR fields underwent automated PHI screening for residual `Last, First` name patterns, untranslated dates (post-shift), phone-number-like patterns, and street-address patterns. All extracted dates were shifted using each patient's BDSP-assigned offset (uniform random integer in ±365 days), the same offset applied to that patient's EEG recording dates and annotation timestamps, ensuring temporal alignment across modalities. Patients whose name match to the BDSP linking table fell below high or medium confidence (29 of 7,364 EHR folders) were excluded from the de-identified release.
4. **File structure**: Output file and directory names contain only de-identified subject identifiers (`sub-NeurotechN`) and session numbers.

Supplementary Table 3 illustrates the de-identification process for a representative recording.

## Usage Notes

### Recommended use cases

This dataset supports three primary research directions. (1) **AI/ML development**: 226,486 technician annotations across 14,517 annotated sessions provide pre-existing labels for spike and seizure detection tasks (50,482 spike events, 6,892 seizure events), while the mix of recording types (routine, ambulatory, ICU) enables training algorithms that generalize across clinical settings. (2) **Clinical EEG research**: the unselected cohort enables epidemiological studies of EEG finding prevalence and studies of annotation variability in clinical workflow. (3) **Methodological development**: automated sleep staging can be applied post-hoc to the multi-day recordings, enabling large-scale study of interictal epileptiform discharge (IED) rates across sleep-wake states.

### Limitations

The dataset has several important limitations. First, all recordings originate from a **single EEG service provider** using one hardware and acquisition platform; although studies were acquired across many settings (patients' homes, clinics, and hospital ICUs and epilepsy monitoring units) and geographically distributed sites, generalization to other providers, hardware platforms, and acquisition workflows requires caution. Second, annotations are **clinical workflow annotations** placed by technicians during routine practice, not multi-expert research labels; they should not be treated as gold-standard labels for algorithm evaluation without independent validation. This is both a strength and a limitation: while it enables study of real-world labeling practices, it means labels cannot be treated as ground truth. Third, clinical metadata (demographics, diagnoses, comorbidities, medications, and EEG interpretation reports) was extracted from scanned clinical documentation using a combination of OCR, regex parsing, and large language model (LLM) extraction. Coverage varies by field: age is available for 59% of patients, sex for 61%, referral diagnosis codes for 63%, and anti-seizure medication data for 32%. Fields extracted from handwritten forms have lower accuracy than those from typed clinical notes. Fourth, **annotation completeness is heterogeneous**: 61% of EEG recordings (14,517 of 23,607) have associated annotation files, with nearly all patients having at least one annotated recording. Fifth, the BIDS tree includes **30,819 zero-record header stubs** alongside the 23,607 EEG recordings (Natus/Xltek source artifact); users should filter on `n_records > 0` or file size when constructing analysis cohorts. Sixth, name-based linkage between extracted EHR data and BDSP de-identified subject IDs achieves 99.96% confident matches; the remaining 0.04% of EHR folders represent patients whose names exhibit substantial spelling variation between source systems and are excluded from the de-identified clinical metadata release.

### Future directions

Future versions of this dataset will add multi-expert re-annotation of a validation subset to establish inter-rater reliability, apply automated sleep staging to multi-day recordings, and develop a curated bank of teaching cases with an interactive web application for EEG education. We also plan to publish updates to the clinical metadata as additional patient documentation becomes available and as the name-linkage procedure is refined to capture more of the long tail of spelling variants.

### Data access

The dataset is available through BDSP at `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`. Access requires a data use agreement (DUA); registration details are available at https://bdsp.io. The dataset is formatted according to BIDS-EEG v1.7.0 and can be read using standard tools including MNE-Python, MNE-BIDS, pyedflib, and edfio.

### Code availability

Code for the BIDS conversion pipeline, de-identification procedures, and annotation extraction is available at https://github.com/bdsp-core/Neurotech-EEG-Wrangling. Every quantitative result in this manuscript can be regenerated from de-identified data via `reproduce_manuscript_numbers.py`; see `REPRODUCIBILITY.md`. EEG and annotation statistics are additionally reproducible directly from the public BIDS dataset (`compute_eeg_stats_from_s3.py`).

---

## Figure Legends

**Figure 1.** Data pipeline from clinical recording to public release. 23,607 EEG recordings from 4,914 patients (2021-2025) totaling 212,186 hours were de-identified through header scrubbing, per-patient date shifting (uniform random offset of +/- 365 days), and automated name replacement in free text, converted to BIDS-EEG format, and released through the Brain Data Science Platform (BDSP) via data use agreement.

**Figure 2.** Dataset positioning. (A) Distribution of EDF segment duration on a logarithmic scale (n = 23,607 EDFs with parseable signal data). Dashed lines indicate approximate boundaries between routine EEGs (<1 hour), ambulatory/short-term monitoring (1-24 hours), and prolonged continuous monitoring (>24 hours). (B) Annotation category breakdown: frequency of 226,486 annotation categories extracted from technician annotation files by keyword matching. Categories are not mutually exclusive. (C) Comparison of the Neurotech EEG Dataset with existing public EEG datasets by number of patients and total recording hours on a logarithmic scale.

**Figure 3.** Patient characteristics. (A) Distribution of referral indications by ICD-10 code category (n=13,049 diagnosis codes from intake forms). Epilepsy (G40.x) is the most common indication, followed by unspecified convulsions (R56.x). (B) Age distribution at first EEG (n=2,915 patients with available date of birth), showing a bimodal pattern with a pediatric peak (5-15 years) and a broad adult distribution. Median age 27 years (dashed line).

**Figure 4.** EEG findings. (A) Distribution of posterior dominant rhythm (PDR) frequency extracted from technologist scan reports (n=8,057 studies with extractable PDR). The peak at 9-10 Hz and right-skewed distribution are consistent with normal physiological values; the green shading indicates the normal adult range (8-13 Hz). (B) Heatmap of interictal epileptiform discharge (IED) morphology by spatial distribution across 6,345 studies with documented IEDs. Values represent the number of studies with each morphology-distribution combination. (C) Seizure capture rate: 2,379 of 10,726 studies (22%) had electrographic seizures documented by the scanning technologist.

---

## References

1. Noachtar, S. & Remi, J. The role of EEG in epilepsy: a critical review. *Epilepsy Behav.* 15, 22-33 (2009).
2. Westover, M.B. et al. Machine learning for electroencephalography: current status and future directions. *J. Clin. Neurophysiol.* (2023).
3. Shoeb, A. & Guttag, J. Application of machine learning to epileptic seizure detection. *Proc. ICML* (2010). [CHB-MIT]
4. Andrzejak, R.G. et al. Indications of nonlinear deterministic and finite-dimensional structures in time series of brain electrical activity. *Phys. Rev. E* 64, 061907 (2001). [Bonn dataset]
5. Detti, P. et al. EEG synchronization analysis for seizure prediction: a study on data of noninvasive recordings. *Processes* 8, 846 (2020). [Siena dataset]
6. Gemein, L.A.W. et al. Machine-learning-based diagnostics of EEG pathology. *NeuroImage* 220, 117021 (2020).
7. Obeid, I. & Picone, J. The Temple University Hospital EEG Data Corpus. *Front. Neurosci.* 10, 196 (2016).
8. Pernet, C.R. et al. EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. *Sci. Data* 6, 103 (2019).

---

## Conflicts of Interest

MBW is a co-founder, scientific advisor, consultant to, and has personal equity interest in Beacon Biosignals. KM, CP, and MG are employees of Neurotech. The other authors declare that they have no conflicts of interest.

## Funding

MBW receives research funding from the NIH (RF1AG064312, RF1NS120947, R01AG073410, R01HL161253, R01NS126282, R01AG073598, R01NS131347, R01NS130119, R01NS131347). DMG receives research funding from the NIH (K23NS124656).

---

---

## Supplementary Material

### Supplementary Tables

**Supplementary Table 1. Recording duration categories.** The majority of recordings represent ambulatory or short-term monitoring studies.

| Category | Duration | N segments (%) | Likely clinical setting |
|---|---|---|---|
| Routine | < 1 hour | 8,545 (36%) | Outpatient EEG |
| Short monitoring | 1 - 24 hours | 12,572 (53%) | Ambulatory or short-term |
| Prolonged monitoring | > 24 hours | 2,490 (11%) | Inpatient continuous EEG or multi-day ambulatory |

*Percentages computed over 23,607 EDF files containing recoverable signal data.*

**Supplementary Table 2. Annotation categories.** Technician clips and spike markers are the most frequent annotation categories.

| Category | Events | Description |
|---|---|---|
| Technician clips | 53,469 | Segments selected for physician review |
| Spike markers | 50,482 | Interictal epileptiform discharge detections |
| Neurotech free-text comments | 24,267 | Free-text EEG finding descriptions |
| Activation procedures | 15,746 | Eyes open/closed, photic, hyperventilation |
| Sharp waves | 21,330 | Sharp wave or sharp-slow-wave complexes |
| Slowing | 19,401 | Focal or diffuse slowing |
| Generalized patterns | 12,345 | Generalized discharges |
| Spike-wave | 10,439 | Spike-wave complexes |
| Seizure markers | 6,892 | Electrographic seizure events |
| Posterior dominant rhythm | 5,535 | PDR frequency notations |
| Artifact | 4,881 | Technical or physiological artifacts |
| Burst-suppression | 3,350 | Burst-suppression (ICU recordings) |
| Focal | 1,928 | Focal patterns |
| Normal | 505 | "Normal" notations |
| Epileptiform | 164 | Other epileptiform |
| Periodic | 139 | Periodic discharges (lateralized/generalized periodic discharges, LPDs/GPDs) |

*Annotation text was parsed into categories using keyword matching. Categories are not mutually exclusive; a single annotation may contribute to multiple categories. Total annotation events: 226,486 across 14,517 sessions with annotation files.*

**Supplementary Table 3. De-identification example.** Header field transformation and annotation scrubbing for a representative recording.

| Field | Original | De-identified |
|---|---|---|
| Patient identification | `12-34567 X 15-MAR-2023 Doe_Jane` | `X X X X` |
| Recording identification | `Startdate 15-MAR-2023 Record_stopped...` | `Startdate 22-JUN-2023 X X X` |
| Start date | `15.03.23` | `22.06.23` (shifted +99 days) |
| Start time | `14.32.08` | `14.32.08` (preserved) |
| Annotation text | `Patient event Jane had a blank stare` | `Patient event [NAME] had a blank stare` |
| Annotation timestamp | `2023-03-15T14:33:45` | `2023-06-22T14:33:45` (shifted) |

*Names and dates shown are fictitious examples. Actual date shifts are random per patient (uniform integer in [-365, +365] days) and applied consistently across all files for that patient.*

**Supplementary Table 4. Detailed EEG findings.** Breakdown of posterior dominant rhythm (PDR), interictal epileptiform discharges, slowing, seizures, and patient-reported events extracted from technologist scan reports (n=10,726 studies with extractable reports). All counts are regenerated from committed de-identified tables (`output/ehr_deid_tables/`) by `manuscript-materials/generate_tables_and_figures.py`; see `reproduce_manuscript_numbers.py`.

| Finding | Value | Notes |
|---|---|---|
| **Posterior dominant rhythm** | | |
|   PDR extractable | 8057 | of 10726 studies |
|   PDR frequency, median (IQR) | 9.0 (8.5-10.0) | Hz |
|   Normal range (8-13 Hz) | 6816 | (85%) |
|   Slow (<8 Hz) | 1146 | (14%) |
|  |  |  |
| Interictal epileptiform discharges | 6345 | of 10726 studies (59%) |
| **Morphology** | | |
|     Spike | 3351 |  |
|     Sharp wave | 1759 |  |
|     Spike-and-wave | 1671 |  |
|     Polyspike | 503 |  |
| **Distribution** | | |
|     Generalized | 1694 |  |
|     Focal | 1369 |  |
|     Multifocal | 277 |  |
|     Bilateral independent | 97 |  |
| **Laterality** | | |
|     Left | 1771 |  |
|     Right | 1616 |  |
|     Bilateral | 713 |  |
| **Region** | | |
|     Temporal | 1943 |  |
|     Frontal | 1265 |  |
|     Central | 880 |  |
|     Parietal | 330 |  |
|     Occipital | 405 |  |
|  |  |  |
| Abnormal slowing | 4524 | of 10726 studies |
| Electrographic seizures | 2379 | of 10726 studies |
| Patient-reported events | 5126 |  |
|   With timestamp | 5018 | (98%) |

*Morphology, distribution, laterality, and region were extracted from free-text descriptions using regex pattern matching. Categories are not mutually exclusive; a single description may contain multiple morphology or distribution terms.*

**Supplementary Table 5. Hourly EEG monitoring data.** Summary of technician monitoring activity extracted from TrackIT monitoring logs in technologist scan reports. All counts are regenerated from committed de-identified aggregates (`output/ehr_deid_tables/monitoring_summary.csv`, `monitoring_hour_of_day.csv`, `monitoring_event_counts.csv`) by `manuscript-materials/generate_tables_and_figures.py`.

| Metric | Value |
|---|---|
| Studies with monitoring data | 6413 |
| Total logged hours | 296,948 |
| Hours recording active | 273,796 (92%) |
| Distinct days/study, median (IQR) | 3.0 (2.0-4.0) |
| Monitoring events | 173,096 |
|   EEG reviewed | 134,875 |
|   General notes | 37,704 |
|   Equipment failures | 517 |

*Each monitoring hour was documented individually by the assigned EEG technician, including impedance readings, recording status, battery levels, and free-text observations. Hour-by-hour data enables reconstruction of the complete monitoring timeline for each study.*

### Supplementary Figure Legends

**Supplementary Figure 1.** Example EEG traces from a representative recording in standard bipolar montage showing normal background activity (left) and an interictal spike with technician annotation (right). Eight channels from the standard 10-20 montage are displayed; scale bars indicate 100 microvolts and 1 second. The annotation "NT-Bi-occipital S/W, right dominant" illustrates the free-text clinical observations preserved in the dataset.

**Supplementary Figure 2.** De-identification of EDF header fields. Each row shows a header field before (containing protected health information) and after de-identification. Patient names are replaced with placeholders, identifiers are reassigned, dates are shifted by a consistent per-patient random offset, and technician identifiers are removed. Equipment information is preserved. All examples shown are fictitious.

**Supplementary Figure 3.** Comorbidities and anti-seizure medications. (A) Ten most frequent comorbidities extracted from clinical progress notes, excluding seizure-related diagnoses. (B) Ten most frequently prescribed anti-seizure medications. Levetiracetam is the most common, consistent with its status as a first-line agent.

**Supplementary Figure 4.** Monitoring characteristics. (A) Distribution of total monitoring duration across 6413 studies with hour-by-hour monitoring data. Peaks at 24 and 48 hours reflect standard ordered monitoring durations. (B) Recording activity by hour of day across all 296,948 documented monitoring hours. Light shading shows total hours logged; dark shading shows hours with active recording. The slight reduction in active recording during daytime hours reflects battery replacements, electrode troubleshooting, and brief patient disconnections documented in the monitoring logs.
