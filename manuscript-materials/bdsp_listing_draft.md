# BDSP.io Dataset Listing Draft: Neurotech EEG Dataset

*This is the content to be entered into the bdsp.io content management system for the dataset listing page.*
*Numbers reflect the full A–Z cohort and are reproducible from the repository via `reproduce_manuscript_numbers.py`.*

---

## Title

Neurotech EEG Dataset

## Version

1.0

## Creators

Keith Morgan, Charles Pickering, Matthew Goodwin, Han Wu, Manohar Ghanta, Aditya Gupta, Daniel Goldenholz, M. Brandon Westover

## Topic Tags

eeg, epilepsy, clinical-eeg, bids, ambulatory-eeg, home-eeg, continuous-eeg, scalp-eeg, natus-xltek

## Access Level

Credentialed

---

## Abstract

The Neurotech EEG Dataset is a large clinical scalp EEG corpus comprising 23,607 EEG recordings from 4,914 patients acquired by a single EEG monitoring service provider between 2021 and 2025, totaling 212,186 hours of signal data (10.2 TB). A distinguishing feature is the large proportion of ambulatory recordings acquired in patients' homes, including multi-day studies — a real-world, out-of-hospital recording context largely absent from existing large clinical EEG corpora, which are predominantly hospital-based. Recordings span routine outpatient EEGs, ambulatory monitoring, and continuous inpatient/ICU EEG, all acquired with Natus/Xltek NeuroWorks hardware at 256 Hz using the standard International 10-20 montage. The dataset includes 226,486 technician-placed annotations — including 50,482 spike markers, 6,892 seizure markers, 21,330 sharp-wave annotations, activation-procedure documentation, and free-text clinical observations. De-identified patient-level clinical metadata (demographics, ICD-10 referral diagnoses, comorbidities, medications, EEG findings, and monitoring summaries) is included for the 4,812 patients with available clinical records. Data are released in BIDS-EEG format with HIPAA-compliant de-identification including per-patient date shifting and automated name scrubbing.

## Background

Electroencephalography (EEG) remains the cornerstone of epilepsy diagnosis and management, yet the global shortage of trained EEG readers limits access to expert interpretation. Machine learning offers a path toward scalable automated EEG interpretation, but progress has been constrained by the scarcity of large, clinically representative public datasets. The Neurotech EEG Dataset addresses this gap by providing a large, unselected clinical EEG corpus spanning the full spectrum of clinical EEG practice — from routine 20-minute outpatient recordings to multi-day continuous ICU monitoring — with a uniquely large volume of multi-day ambulatory EEG recorded in patients' homes.

This dataset complements the Harvard EEG Database (HEEDB; ~109,000 patients, ~329,000 recordings, ~3.3 million hours across four hospitals, on the same BDSP platform): whereas HEEDB comprises routine, EMU, and ICU recordings acquired in clinical facilities, the present corpus is far smaller overall but uniquely contributes out-of-hospital, in-home ambulatory EEG, Natus/Xltek hardware, and preserved workflow-native technician annotations that capture the variability of real-world clinical EEG practice.

## Methods

### Recording

All recordings were acquired using Natus/Xltek NeuroWorks EEG systems with standard International 10-20 electrode placement (25-29 channels; median 28, including ECG). Signals were sampled at 256 Hz and stored in EDF+C (continuous) format. Recording types include routine outpatient EEGs (<1 hour; 36%), ambulatory and short-term monitoring (1-24 hours; 53%), and prolonged continuous monitoring (>24 hours; 11%).

### Clinical metadata extraction

For the 4,812 of 4,914 patients (98%) with available scanned clinical documentation, a three-stage on-premises pipeline (text extraction with OCR, document segmentation, and structured field extraction using deterministic parsers plus a locally hosted open-weight LLM) produced structured, de-identified fields: demographics, ICD-10 referral diagnoses, comorbidities, medications, EEG findings (posterior dominant rhythm, epileptiform discharges, seizures, slowing, impression), and hour-by-hour monitoring summaries. All clinical text was processed on-device; no clinical text left the secure environment.

### De-identification

De-identification was performed in compliance with HIPAA Safe Harbor standards:
- Patient name, ID, date of birth, case number, and technician identifiers removed from EDF headers
- Recording dates shifted by a random per-patient offset (uniform in [-365, +365] days); times of day preserved
- Patient names in annotation free-text replaced with `[NAME]` via two-tier scrubbing
- Dates in annotation text detected and shifted by the same per-patient offset
- Clinical metadata released as structured, patient-level fields only (no free text, no dates; ages >89 top-coded to 90)

## Data Description

| Characteristic | Value |
|---|---|
| Unique patients | 4,914 |
| EEG recordings (with signal data) | 23,607 |
| Additional header-only stub files | 30,819 |
| Total EDF files | 54,426 |
| Total recording hours | 212,186 |
| Total dataset size | 10.2 TB (231,880 files) |
| Recording duration, median (IQR) | 3.0 (0.3 - 12.3) hours |
| Patients with multiple recordings | 3,570 (73%) |
| Recordings per patient, median (IQR) | 3 (1 - 6) |
| Recordings with ≥1 annotation file | 14,517 (61%) |
| Total annotation events | 226,486 |
| Spike markers | 50,482 |
| Seizure markers | 6,892 |
| Sharp wave annotations | 21,330 |
| Patients with clinical metadata | 4,812 (98%) |
| Referral ICD-10 codes (Epilepsy G40 / Convulsions R56) | 54% / 13% |
| Hardware | Natus/Xltek NeuroWorks |
| Sampling rate | 256 Hz |
| Channels | 25-29 (10-20 + ECG + auxiliary) |
| Date range | 2021-2025 |
| Format | BIDS-EEG v1.7.0 |

## Data Organization (BIDS)

```
Neurotech/
  dataset_description.json
  participants.tsv          # participant_id, age, sex
  participants.json
  README
  phenotype/                # de-identified patient-level clinical metadata
    demographics.tsv/.json
    diagnoses.tsv/.json      # full ICD-10 codes
    comorbidities.tsv/.json
    medications.tsv/.json
    eeg_findings.tsv/.json   # PDR, epileptiform/seizure/slowing flags, impression
    monitoring.tsv/.json
  sub-Neurotech1/
    ses-1/
      sub-Neurotech1_ses-1_scans.tsv
      eeg/
        sub-Neurotech1_ses-1_task-EEG_eeg.edf
        sub-Neurotech1_ses-1_task-EEG_eeg.json
        sub-Neurotech1_ses-1_task-EEG_channels.tsv
        sub-Neurotech1_ses-1_task-EEG_Xltek.csv
    ses-2/
      ...
  sub-Neurotech2/
    ...
```

## Usage Notes

### Recommended use cases
- AI/ML development: spike detection, seizure detection, EEG quality assessment
- Clinical EEG research: epidemiology of EEG findings, annotation variability, ambulatory/home EEG
- Methodological development: automated sleep staging and event detection on multi-day recordings

### Code
- BIDS conversion + de-identification + EHR extraction pipeline: https://github.com/bdsp-core/Neurotech-EEG-Wrangling

### Limitations
- Single service provider with one hardware platform
- Annotations are clinical workflow annotations, not multi-expert research labels
- Clinical metadata covers the 98% of patients with scanned records and is structured-field only (no free text)
- Header-only stub EDFs are included for session integrity; filter on `n_records > 0` for signal-level analysis

## Ethics & Governance

- IRB: Protocol 2022P000417 (BIDMC), waiver of consent granted, under BAA between BIDMC and Neurotech. Publication approved in de-identified form with access restricted by DUA prohibiting re-identification. Compliant with the Declaration of Helsinki.
- De-identification: HIPAA Safe Harbor compliant
- Data use agreement required for access

## Access Information

- **S3 path:** `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`
- **Access:** Credentialed (requires BDSP account and signed DUA)
- **License:** CC BY-NC 4.0 (Attribution–NonCommercial)

## Citation

[Data descriptor manuscript in preparation — update with full citation/DOI on publication.]

## Related Resources

- Harvard EEG Database: https://bdsp.io/content/harvard-eeg-db/
- BIDS-EEG specification: https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html
