# BDSP.io Dataset Listing Draft: Neurotech EEG Dataset

*This is the content to be entered into the bdsp.io content management system for the dataset listing page.*

---

## Title

Neurotech EEG Dataset

## Version

1.0

## Creators

Keith Morgan, Charles Pickering, Matthew Goodwin, Han Wu, Manohar Ghanta, Aditya Gupta, Daniel Goldenholz, M. Brandon Westover

## Topic Tags

eeg, epilepsy, clinical-eeg, bids, ambulatory-eeg, continuous-eeg, scalp-eeg, natus-xltek

## Access Level

Credentialed

---

## Abstract

The Neurotech EEG Dataset is a large clinical scalp EEG corpus comprising 8,410 EEG recordings from 1,744 patients collected at a single center between 2021 and 2025, totaling 77,575 hours of signal data (3.95 TB). Recordings span routine outpatient EEGs, ambulatory monitoring, and continuous inpatient/ICU EEG, all acquired with Natus/Xltek NeuroWorks hardware at 256 Hz using the standard International 10-20 montage. The dataset includes 83,714 technician-placed annotations including spike markers, seizure markers, activation procedure documentation, and free-text clinical observations. Data are released in BIDS-EEG format with HIPAA-compliant de-identification including per-patient date shifting and automated name scrubbing.

## Background

Electroencephalography (EEG) remains the cornerstone of epilepsy diagnosis and management, yet the global shortage of trained EEG readers limits access to expert interpretation. Machine learning offers a path toward scalable automated EEG interpretation, but progress has been constrained by the scarcity of large, clinically representative public datasets. The Neurotech EEG Dataset addresses this gap by providing a large, unselected clinical EEG corpus spanning the full spectrum of clinical EEG practice — from routine 20-minute outpatient recordings to multi-day continuous ICU monitoring.

This dataset complements the Harvard EEG Database by adding data from a different clinical site with Natus/Xltek hardware (vs. Natus NicoletOne), a higher proportion of ambulatory recordings, and preserved workflow-native technician annotations that capture the variability of real-world clinical EEG practice.

## Methods

### Recording

All recordings were acquired using Natus/Xltek NeuroWorks EEG systems with standard International 10-20 electrode placement (25-29 channels including ECG). Signals were sampled at 256 Hz and stored in EDF+C (continuous) format. Recording types include routine outpatient EEGs (<1 hour; 34%), ambulatory and short-term monitoring (1-24 hours; 55%), and prolonged continuous monitoring (>24 hours; 11%).

### De-identification

De-identification was performed in compliance with HIPAA Safe Harbor standards:
- Patient name, ID, date of birth, case number, and technician identifiers removed from EDF headers
- Recording dates shifted by a random per-patient offset (uniform in [-365, +365] days); times of day preserved
- Patient names in annotation free-text replaced with [NAME] via two-tier scrubbing
- Dates in annotation text detected and shifted by the same per-patient offset

## Data Description

| Characteristic | Value |
|---|---|
| Unique patients | 1,744 |
| EEG recordings (with signal data) | 8,410 |
| Additional header-only stub files | 10,397 |
| EDF files with signal data | 8,410 |
| Total recording hours | 77,575 |
| Total dataset size | 3.95 TB (80,382 files) |
| Recording duration, median (IQR) | 3.35 (0.43 - 12.72) hours |
| Patients with multiple sessions | 1,320 (76%) |
| Sessions per patient, median (IQR) | 4 (2 - 9) |
| Sessions with annotation files | 5,065 (27% of sessions; 99.9% of patients) |
| Total annotation events | 83,714 |
| Spike markers | 19,705 |
| Seizure markers | 2,757 |
| Sharp wave annotations | 8,027 |
| Hardware | Natus/Xltek NeuroWorks |
| Sampling rate | 256 Hz |
| Channels | 25-29 (10-20 + ECG + auxiliary) |
| Date range | 2021-2025 |
| Format | BIDS-EEG v1.7.0 |

## Data Organization (BIDS)

```
Neurotech/
  dataset_description.json
  participants.tsv
  README
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
- Clinical EEG research: epidemiology of EEG findings, annotation variability
- Methodological development: automated sleep staging on multi-day recordings

### Code
- BIDS conversion pipeline: https://github.com/bdsp-core/Neurotech-EEG-Wrangling

### Limitations
- Single center with one hardware platform
- Annotations are clinical workflow annotations, not multi-expert research labels
- No clinical metadata (diagnosis, medications, demographics) in current release
- 55% of EDF files are header-only stubs (filter on n_records > 0)

## Ethics & Governance

- IRB: Protocol 2022P000417 (BIDMC), waiver of consent granted, under BAA between BIDMC and Neurotech. Publication approved in de-identified form with access restricted by DUA prohibiting re-identification. Compliant with the Declaration of Helsinki.
- De-identification: HIPAA Safe Harbor compliant
- Data use agreement required for access

## Access Information

- **S3 path:** `s3://bdsp-opendata-repository/EEG/bids/Neurotech/`
- **Access:** Credentialed (requires BDSP account and signed DUA)
- **License:** [TBD]

## Citation

[TBD -- manuscript in preparation]

## Related Resources

- Harvard EEG Database: https://bdsp.io/content/harvard-eeg-db/
- BIDS-EEG specification: https://bids-specification.readthedocs.io/en/stable/modality-specific-files/electroencephalography.html
