<!--TITLEPAGE-->
# The Neurotech EEG Dataset: A Large Clinical Scalp EEG Corpus Dominated by Multi-Day Ambulatory Recordings

**Running title:** The Neurotech EEG Dataset

**Authors:** Keith Morgan^1^, Charles Pickering^1^, Matthew Goodwin^1^, Han Wu^2^, Manohar Ghanta^2^, Aditya Gupta^2^, Jin Jing^2^, ChenXi Sun^2^, Daniel Goldenholz^2^, M. Brandon Westover^2^

^1^ Neurotech, Waukesha, WI, USA
^2^ Department of Neurology, Beth Israel Deaconess Medical Center, Harvard Medical School, Boston, MA, USA

**Corresponding author:** M. Brandon Westover, MD, PhD; Department of Neurology, Beth Israel Deaconess Medical Center, Boston, MA, USA; bwestove@bidmc.harvard.edu

**Manuscript type:** Original research

**Word count (main text):** WORDCOUNT_PLACEHOLDER. **Abstract:** ~250 words. **Figures:** 4. **Tables:** 2. **References:** 12. **Supplementary items:** 4 figures, 5 tables.

**Keywords:** electroencephalography; ambulatory EEG; epilepsy; open dataset; machine learning; Brain Imaging Data Structure

<!--ENDTITLEPAGE-->

## Key Points

- The Neurotech EEG Dataset is a large de-identified clinical scalp EEG corpus distinguished by a high proportion of multi-day ambulatory recordings acquired in patients' homes.
- It comprises 4,914 patients and 23,607 signal-bearing EDF recording segments (212,186 hours), released in Brain Imaging Data Structure (BIDS)-EEG format with workflow-native technician annotations.
- De-identified patient-level clinical metadata (referral diagnoses, medications, and EEG findings) are provided for 98% of patients.
- The dataset is openly available through the Brain Data Science Platform under a data use agreement, supporting reproducible and artificial-intelligence-driven EEG research.

## Abstract

**Objective:** Large, clinically representative public electroencephalography (EEG) datasets are scarce, and existing corpora are dominated by in-hospital recordings, which limits the development and external validation of automated EEG analysis. We describe the Neurotech EEG Dataset, a large de-identified clinical scalp EEG corpus distinguished by a high proportion of multi-day ambulatory recordings acquired in patients' homes.

**Methods:** All clinical EEG performed by a single accredited ambulatory EEG service provider between 2021 and 2025 was included without selection. Recordings were acquired on Lifelines or EMS ambulatory equipment (256 Hz, International 10-20 montage) with Persyst-based technician annotation, converted to BIDS-EEG format, and de-identified in accordance with the Health Insurance Portability and Accountability Act (HIPAA) Safe Harbor standard (per-patient date shifting, header scrubbing, and automated free-text name removal). De-identified patient-level clinical metadata were extracted from scanned clinical records using an on-premises optical character recognition and large language model pipeline. All reported values are reproducible from the released data.

**Results:** The dataset comprises 4,914 patients and 23,607 signal-bearing EDF recording segments—corresponding to approximately one multi-day ambulatory study per patient (~2 recording days each)—totaling 212,186 hours of signal (10.2 TB). Recordings are accompanied by 226,486 technician-placed annotations, including 50,482 spike, 6,892 seizure, and 21,330 sharp-wave markers. Technologist reports were abnormal in 34% of studies, with interictal epileptiform discharges documented in 6,345 and electrographic seizures in 2,379; clinical metadata are provided for 98% of patients.

**Significance:** By releasing a large, workflow-native ambulatory EEG corpus with linked clinical metadata under a data use agreement, this resource enables reproducible, real-world development and validation of automated EEG analysis in an out-of-hospital context that is largely absent from existing datasets.

## 1. Introduction

Expert interpretation of the electroencephalogram (EEG) remains the cornerstone of epilepsy diagnosis,^1^ yet the global shortage of trained EEG readers creates a bottleneck affecting the approximately 50 million people living with epilepsy worldwide.^9^ Machine learning offers a path toward scalable automated interpretation,^2^ but the scarcity of large, clinically representative public datasets has constrained progress. Spike-detection algorithms trained on existing public datasets can achieve high accuracy on held-out test sets yet drop substantially when deployed on recordings from different clinical settings or hardware platforms—a persistent and well-documented generalization problem.^3-6,12^

Existing public EEG resources span a range of sizes and designs but share common limitations (Table 1). The CHB-MIT dataset provides 23 pediatric patients with seizure annotations;^3^ the Bonn dataset offers intracranial recordings from 5 patients;^4^ the Siena dataset contributes 14 patients with scalp EEG.^5^ The Temple University Hospital (TUH) EEG Corpus, at over 25,000 sessions, demonstrated that large-scale release of unselected clinical data could become the most widely used benchmark in the EEG artificial intelligence literature.^7^ The Harvard Electroencephalography Database (HEEDB) subsequently released a very large in-hospital clinical EEG resource on the same platform used here.^11^ However, publicly available clinical EEG remains insufficiently diverse across institutions, hardware platforms, clinical settings, and annotation practices—and, in particular, ambulatory EEG recorded outside the hospital is almost entirely absent.

Here we describe the Neurotech EEG Dataset—to our knowledge one of the largest public clinical EEG corpora from a single service provider—comprising 23,607 EDF recording segments from 4,914 patients totaling 212,186 recording hours. The dataset complements existing corpora in three ways: (1) a majority of ambulatory and multi-day recordings acquired in patients' homes, an out-of-hospital context largely missing from prior corpora; (2) ambulatory acquisition hardware (Lifelines/EMS) distinct from the clinical acquisition systems used elsewhere, enabling cross-platform algorithm validation; and (3) intact clinical-workflow annotations, including 50,482 technician-confirmed spike events and 6,892 seizure markers, that capture the noise, variability, and practical constraints under which automated systems must ultimately operate. Whereas HEEDB comprises routine, epilepsy monitoring unit, and intensive care unit recordings acquired in clinical facilities,^11^ the present corpus is far smaller overall but uniquely contributes a large volume of multi-day ambulatory EEG recorded in the home.

**Table 1. Comparison with existing clinical EEG datasets.**

| Dataset | Patients | Sessions | Hours | Hardware | Recording types | Annotation style |
|---|---|---|---|---|---|---|
| CHB-MIT^3^ | 23 | 23 | ~982 | Unknown | Inpatient | Expert seizure labels |
| Bonn^4^ | 5 | 5 | ~0.6 | Intracranial | Research | Segment-level labels |
| Siena^5^ | 14 | 14 | ~128 | Unknown | Inpatient | Expert seizure labels |
| TUH EEG Corpus^7^ | ~15,000 | ~25,000 | ~25,000 | Natus NicoletOne | Primarily inpatient | Clinical reports |
| Harvard EEG Database^11^ | ~109,000 | ~329,000 | ~3,300,000 | Mixed (4 sites) | Routine + EMU + ICU (in-hospital) | Clinical reports |
| **Neurotech (this work)** | **4,914** | **23,607** | **212,186** | **Lifelines / EMS** | **Routine + ambulatory (home)** | **Workflow-native** |

## 2. Materials and Methods

### 2.1 Patient population and clinical setting

The dataset comprises all clinical EEG recordings performed by Neurotech, LLC—an accredited EEG monitoring service provider—between 2021 and 2025. Rather than a single hospital or center, Neurotech performs ambulatory EEG in patients' homes together with some routine outpatient studies (and occasional routine inpatient bedside recordings), across geographically distributed sites in the United States, using a uniform hardware and technologist workflow. No inclusion or exclusion criteria were applied; this cohort represents the full clinical caseload.

### 2.2 EEG acquisition

All recordings were acquired using Lifelines or EMS ambulatory EEG systems, with Persyst spike and seizure detection. Electrodes were placed according to the standard International 10-20 system (Fp1, Fp2, F3, F4, C3, C4, P3, P4, O1, O2, F7, F8, T3, T4, T5, T6, Fz, Pz, Cz) together with a two-channel electrocardiogram; additional electrodes (e.g., A1, A2, T1, T2, F11, F12) were placed only on request and are absent from most recordings. Recordings span 22-30 channels (median 28); signals were sampled at 256 Hz and stored in European Data Format (EDF+C, continuous). Because the acquisition system exports each continuous recording as multiple EDF files, one clinical study is represented by several EDF segment files (see Results).

### 2.3 Annotations

EEG technicians placed annotations during routine clinical workflow using the Persyst spike/seizure-detection and clinical annotation workflow. Three annotation types are present: (1) event markers (@Spike, @Seizure), point-in-time markers likely including both automated detections and technician-confirmed events; (2) technician clips (@Clip), segments selected for physician review with descriptive labels; and (3) free-text observations (prefixed NT-), narrative clinical descriptions. Additional annotations document posterior dominant rhythm (PDR) frequency and activation procedures. These are single-reader clinical-workflow annotations rather than multi-expert research labels; inter-rater reliability was not assessed.

### 2.4 Clinical metadata extraction

Clinical documentation was available as scanned PDF packets for 4,812 of 4,914 patients (98%). Each packet contained a technologist scan report, hourly monitoring logs, referring-physician intake forms, and, in many cases, clinical progress notes. We developed a three-stage on-premises pipeline: (1) text extraction using pdftotext with optical character recognition via Tesseract for scanned pages (59% of documents); (2) document segmentation into sub-document types by regex landmark detection; and (3) structured field extraction using deterministic regex parsers for standardized sections and a locally hosted open-weight large language model (Qwen2.5, run on-device via Apple MLX) for narrative text. The pipeline runs entirely on-premises, so clinical text is processed without leaving the secure environment. It identified 40,529 sub-documents across 11 document types, extracting EEG findings, referral diagnoses (International Classification of Diseases, 10th Revision [ICD-10] codes), demographics, medications, and hour-by-hour monitoring data. Each patient was linked to their de-identified identifier through a four-tier name-matching procedure (exact, normalized, first-root, and Levenshtein edit distance ≤ 2), achieving 99.96% successful linkage; unmatched and low-confidence patients were excluded. Manual review of 30 randomly sampled records found zero hallucinated values, and cross-checking of medications and diagnosis codes against source text confirmed accurate extraction in 94% of cases (the remainder reflected minor OCR spelling differences, not extraction errors).

### 2.5 De-identification

De-identification was performed in compliance with HIPAA Safe Harbor standards. Patient name, identifier, date of birth, case number, and technician and equipment identifiers were removed from all EDF headers, and the local patient-identification field was replaced with `X X X X`. All recording dates were shifted by a random per-patient offset drawn uniformly from [-365, +365] days, with times of day preserved and the same offset applied consistently across all recordings and annotation timestamps for a given patient. A two-tier name scrubber replaced patient names in annotation free text with `[NAME]`, and dates embedded in annotation text were shifted by the same offset. A linking table mapping de-identified to original identifiers is maintained securely and is not published. De-identification was verified by automated audit of all output files: re-reading of every EDF header confirmed only `X X X X` in the patient field; all 226,486 annotation text entries were screened for residual names and dates; and de-identified clinical fields were screened for residual name, date, phone, and address patterns.

### 2.6 Data structure and reproducibility

The dataset was converted to BIDS-EEG format (version 1.7.0)^8,10^ with de-identified identifiers (`sub-NeurotechN`); each EDF segment constitutes a session (`ses-N`). For each session, the released files are the EEG recording (`*_eeg.edf`), recording metadata (`*_eeg.json`), a channels table (`*_channels.tsv`), technician annotations (`*_Xltek.csv`, when present), and session acquisition time (`*_scans.tsv`); dataset-level files include `dataset_description.json`, `participants.tsv/json`, and a README. Every quantitative value in this report is regenerable from the released de-identified data using the accompanying code (see Data Availability).

### 2.7 Ethics

This project was conducted under Institutional Review Board (IRB) protocol 2022P000417, with the Beth Israel Deaconess Medical Center IRB granting a waiver of consent, and under a Business Associate Agreement between Beth Israel Deaconess Medical Center and Neurotech. The IRB approved publication of the dataset in de-identified form with access restricted by a data use agreement prohibiting re-identification. The study complied with the Declaration of Helsinki.

## 3. Results

### 3.1 Cohort and dataset overview

The dataset comprises 4,914 patients. Among patients with available clinical documentation, the median age at first EEG was 26.7 years (interquartile range [IQR] 13.4-48.2; n=2,915), with a bimodal distribution reflecting both pediatric epilepsy referrals and adult-onset seizure disorders (Figure 3B); 46% were male and 54% female (n=3,005). Epilepsy diagnoses (ICD-10 G40.x) accounted for 54% of referral indications, followed by unspecified convulsions (13%) and abnormal movements (5%) (Figure 3A). Patient and study characteristics are summarized in Table 2.

**Table 2. Patient and study characteristics.** Clinical metadata were extracted for the 4,812 of 4,914 patients (98%) with available records. Age and sex were available for 2,915 and 3,005 patients, respectively. EEG recording statistics are from the full BIDS dataset.

| Characteristic | Value | Notes |
|---|---|---|
| **Patients** | | |
|   Unique patients | 4914 |  |
|   With clinical documentation | 4812 | (98%) |
|   Age at first EEG, median (IQR) | 26.7 (13.4-48.2) | n=2915 |
|   Male / Female | 1374 / 1631 | (46% / 54%) |
| **Referral indications (ICD-10)** |  | n=13049 codes |
|   Epilepsy (G40.x) | 7073 | (54%) |
|   Convulsions (R56.x) | 1648 | (13%) |
|   Abnormal movements (R25.x) | 618 | (5%) |
|   Other | 3710 | (28%) |
| **EEG recordings** | | |
|   Signal-bearing EDF segments | 23,607 |  |
|   Total recording hours | 212,186 |  |
|   Segment duration, median (IQR) | 3.0 (0.3-12.3) | hours |
|   EDF segments per patient, median (IQR) | 3.0 (1.0-6.0) |  |
|   Patients with multiple segments | 3570 | (73%) |
| **EEG findings (technologist reports)** |  | n=10726 studies |
|   Normal / Abnormal | 2506 / 3693 | (23% / 34%) |
|   With epileptiform discharges | 6345 |  |
|   With electrographic seizures | 2379 |  |

*IQR = interquartile range.*

### 3.2 Recording characteristics

The dataset totals 212,186 hours of signal across 23,607 signal-bearing EDF segments. Because each continuous recording is exported as multiple EDF files, the segment count substantially exceeds the number of distinct EEG studies: grouping segments by recording date indicates approximately one multi-day ambulatory study per patient (median one recording session per patient, spanning roughly two recording days), consistent with a total signal volume of ~43 hours per patient. By duration, 53% of segments fall in the 1-24 hour range consistent with ambulatory or short-term monitoring, 36% are under one hour, and 11% exceed 24 hours (multi-day ambulatory studies) (Figure 2A, Supplementary Table 1). In addition to the signal-bearing segments, the BIDS tree includes 30,819 header-only EDF stubs produced by the acquisition system at recording boundaries and aborted starts; these contain valid headers but no data records and should be filtered (e.g., on `n_records > 0`) for signal-level analysis. All readable files contained 22-30 channels at 256 Hz (median 28).

### 3.3 Annotation characteristics

Recordings are accompanied by 226,486 technician-placed annotations. Technician clips (53,469) and spike markers (50,482) are the most common categories, followed by free-text clinical observations, sharp waves (21,330), slowing (19,401), activation procedures (15,746), and seizure markers (6,892) (Supplementary Table 2, Figure 2B). Of the 23,607 signal-bearing segments, 14,517 (61%) have at least one annotation file, and nearly all patients have at least one annotated recording. Annotation density varies widely: the median annotated segment contains 8 annotations (IQR 3-21; 1.13 per hour, IQR 0.47-2.78).

### 3.4 EEG findings and clinical metadata

EEG findings extracted from technologist scan reports demonstrated a high yield of clinically significant abnormalities: 34% of studies were classified as abnormal, with interictal epileptiform discharges documented in 6,345 studies and electrographic seizures in 2,379 (Figure 4, Supplementary Table 4). The PDR frequency distribution peaked at 9-10 Hz (Figure 4A), consistent with expected physiological values and providing independent validation of the extraction pipeline. Epileptiform discharge morphology and distribution (Figure 4B) showed a predominance of generalized spike and spike-and-wave patterns. Comorbidities and anti-seizure medications extracted from clinical notes are summarized in Supplementary Figure 3, and hour-by-hour monitoring characteristics in Supplementary Figure 4 and Supplementary Table 5.

## 4. Discussion

The Neurotech EEG Dataset provides a large, unselected clinical EEG corpus whose defining feature is a high volume of multi-day ambulatory recordings acquired in patients' homes—an out-of-hospital context largely absent from existing public corpora. Three uses follow directly. First, for artificial-intelligence development, 226,486 workflow-native annotations across 14,517 annotated recordings (including 50,482 spike and 6,892 seizure events) supply pre-existing labels for spike- and seizure-detection tasks, while the ambulatory, home-based acquisition and distinct hardware enable external validation of algorithms trained on hospital data. Second, for clinical EEG research, the unselected cohort supports epidemiological study of EEG-finding prevalence and of annotation variability in real clinical workflow. Third, the multi-day recordings enable methodological work such as automated sleep staging and the study of interictal discharge rates across sleep-wake states. By preserving workflow-native annotations, the dataset captures the noise and variability under which automated systems must operate, helping bridge the gap between benchmark performance and real-world deployment.

### 4.1 Limitations

Several limitations should be noted. First, all recordings originate from a single service provider using one acquisition platform; although studies were acquired across many settings (predominantly patients' homes, with some outpatient clinic and occasional routine inpatient bedside studies) and geographically distributed sites, generalization to other providers and workflows requires caution. Second, annotations are clinical-workflow annotations placed by technicians during routine practice, not multi-expert research labels, and should not be treated as ground truth without independent validation—this is simultaneously a strength (it enables study of real-world labeling) and a limitation. Third, clinical metadata were extracted from scanned documentation using OCR, regex, and large language model extraction; coverage varies by field (e.g., age available for 59% and anti-seizure medication data for 32% of patients), and fields from handwritten forms are less accurate. Fourth, annotation completeness is heterogeneous (61% of segments have annotation files). Fifth, the BIDS tree includes 30,819 zero-record header stubs that must be filtered for signal-level analysis. Sixth, name-based linkage between extracted records and de-identified identifiers achieved 99.96% confident matches; the remainder were excluded from the clinical-metadata release.

### 4.2 Future directions

Future versions may add multi-expert re-annotation of a validation subset to establish inter-rater reliability, apply automated sleep staging to multi-day recordings, and develop a curated bank of teaching cases. We also hope to expand the clinical metadata as additional documentation becomes available and as the name-linkage procedure is refined.

## 5. Conclusions

The Neurotech EEG Dataset contributes a large, de-identified, ambulatory-dominant clinical EEG corpus with linked clinical metadata and workflow-native annotations, released openly under a data use agreement and fully reproducible from the released data. It fills a gap left by predominantly in-hospital corpora and provides a foundation for reproducible, real-world development and validation of automated EEG analysis.

## Author Contributions

M.B.W., D.M.G., K.M., and C.P. conceived and designed the study. K.M., C.P., and M.G. provided the clinical EEG data and domain expertise. H.W., M.G. (Ghanta), A.G., J.J., and C.S. developed the de-identification, conversion, and clinical-metadata-extraction pipelines and performed the analyses. M.B.W. and D.M.G. supervised the work. H.W. and M.B.W. drafted the manuscript. All authors critically revised the manuscript and approved the final version.

## Conflict of Interest Statement

M.B.W. is a co-founder of, scientific advisor and consultant to, and has personal equity interest in Beacon Biosignals. K.M., C.P., and M.G. are employees of Neurotech. D.M.G. has received speaker fees from Harvard Medical School, AAN, AES, ACNS, NNS, AI in Epilepsy and Neurology, Florida Epilepsy Alliance, and UT-Austin; has previously been a paid consultant for Neuro Event Labs, IDR, LivaNova, Health Advances, Duke University, Bloom Insights, and Wiley; and has received grants from NIH, ABPN, BIDMC, and the Lions Club. The remaining authors have no conflicts of interest. We confirm that we have read the Journal's position on issues involved in ethical publication and affirm that this report is consistent with those guidelines.

## Funding

M.B.W. receives research funding from the NIH (RF1AG064312, RF1NS120947, R01AG073410, R01HL161253, R01NS126282, R01AG073598, R01NS131347, R01NS130119). D.M.G. receives research funding from the NIH (K23NS124656, R21NS142800) and the ABPN.

## Data Availability Statement

The dataset is available through the Brain Data Science Platform (BDSP) at https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/ (DOI: https://doi.org/10.60508/v99k-ek82). Access is credentialed: users register on BDSP and sign a data use agreement prohibiting re-identification; the released data are de-identified. Analysis and conversion code, and scripts that regenerate every quantitative value in this report from the released data, are available at https://github.com/bdsp-core/Neurotech-EEG-Wrangling.

## References

1. Noachtar S, Rémi J. The role of EEG in epilepsy: a critical review. Epilepsy Behav. 2009;15:22-33.
2. Roy Y, Banville H, Albuquerque I, Gramfort A, Falk TH, Faubert J. Deep learning-based electroencephalography analysis: a systematic review. J Neural Eng. 2019;16:051001.
3. Shoeb A, Guttag J. Application of machine learning to epileptic seizure detection. In: Proceedings of the 27th International Conference on Machine Learning (ICML); 2010. p. 975-982.
4. Andrzejak RG, Lehnertz K, Mormann F, Rieke C, David P, Elger CE. Indications of nonlinear deterministic and finite-dimensional structures in time series of brain electrical activity. Phys Rev E. 2001;64:061907.
5. Detti P, Vatti G, Zabalo Manrique de Lara G. EEG synchronization analysis for seizure prediction: a study on data of noninvasive recordings. Processes. 2020;8:846.
6. Gemein LAW, Schirrmeister RT, Chrabąszcz P, Wilson D, Boedecker J, Schulze-Bonhage A, et al. Machine-learning-based diagnostics of EEG pathology. NeuroImage. 2020;220:117021.
7. Obeid I, Picone J. The Temple University Hospital EEG Data Corpus. Front Neurosci. 2016;10:196.
8. Pernet CR, Appelhoff S, Gorgolewski KJ, Flandin G, Phillips C, Delorme A, et al. EEG-BIDS, an extension to the brain imaging data structure for electroencephalography. Sci Data. 2019;6:103.
9. World Health Organization. Epilepsy: a public health imperative. Geneva: World Health Organization; 2019.
10. Gorgolewski KJ, Auer T, Calhoun VD, Craddock RC, Das S, Duff EP, et al. The brain imaging data structure, a format for organizing and describing outputs of neuroimaging experiments. Sci Data. 2016;3:160044.
11. Sun C, Jing J, Turley N, Alcott C, Kang WY, Cole AJ, et al. Harvard Electroencephalography Database: a comprehensive clinical electroencephalographic resource from four Boston hospitals. Epilepsia. 2025;66:3411-3425.
12. Xu L, Zhang W, Wang Y, Wang Q, Zhang W, Fang F, et al. Cross-dataset variability problem in EEG decoding with deep learning. Front Hum Neurosci. 2020;14:103.

---

## Figure Legends

**Figure 1.** Data pipeline from clinical recording to public release. 23,607 EDF recording segments from 4,914 patients (2021-2025) totaling 212,186 hours were de-identified through header scrubbing, per-patient date shifting (uniform random offset of ±365 days), and automated name replacement in free text, converted to BIDS-EEG format, and released through the Brain Data Science Platform via data use agreement.

**Figure 2.** Dataset positioning. (A) Distribution of EDF segment duration on a logarithmic scale (n = 23,607 signal-bearing EDFs). Dashed lines indicate approximate boundaries between routine (<1 hour), ambulatory/short-term (1-24 hours), and prolonged (>24 hours) recordings. (B) Annotation category breakdown (226,486 annotations; categories are not mutually exclusive). (C) Comparison of the Neurotech EEG Dataset with other clinical EEG datasets by number of patients and total recording hours (logarithmic scale); the Harvard EEG Database, on the same platform, is far larger overall but comprises in-hospital recordings only, whereas the present dataset uniquely contributes multi-day ambulatory/home recordings.

**Figure 3.** Patient characteristics. (A) Referral indications by ICD-10 category (n=13,049 diagnosis codes). Epilepsy (G40.x) is most common, followed by unspecified convulsions (R56.x). (B) Age distribution at first EEG (n=2,915 patients), showing a bimodal pattern with a pediatric peak (5-15 years) and a broad adult distribution; median age 27 years (dashed line).

**Figure 4.** EEG findings. (A) Posterior dominant rhythm (PDR) frequency from technologist reports (n=8,057 studies); the peak at 9-10 Hz and right-skewed distribution are consistent with normal values (green shading, 8-13 Hz). (B) Heatmap of interictal epileptiform discharge morphology by spatial distribution across 6,345 studies. (C) Seizure capture rate: 2,379 of 10,726 studies (22%) had electrographic seizures documented.

---

## Supporting Information

Supplementary Tables S1-S5 and Supplementary Figures S1-S4 are available online. (Supplementary content is carried over from the full data descriptor; see the project repository.)
