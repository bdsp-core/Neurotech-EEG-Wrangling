# Note to editors and reviewers: data access during peer review

**Manuscript:** Clinical scalp electroencephalography of 4,912 patients including multi-day ambulatory home recordings

**Dataset:** The Neurotech EEG Dataset, Brain Data Science Platform, https://doi.org/10.60508/v99k-ek82 (https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/)

The dataset is distributed under **controlled access** because it contains patient-level health information (diagnoses, medications, EEG findings) with age and sex. Users register on bdsp.io, complete credentialing, and sign a data use agreement that prohibits re-identification and redistribution; access is then granted to the full 10.2 TB BIDS release.

Because that process records the user's identity and is not instantaneous, we provide a **representative sample for anonymous, immediate download** so that reviewers can inspect the data without revealing their identity:

- **Download:** [INSERT ANONYMOUS DOWNLOAD URL OF THE SAMPLE ZIP]
- **Contents:** the complete top-level files of the release (`dataset_description.json`, `README`, `participants.tsv`, `participants.json`, the full `phenotype/` directory with all six tables and their data dictionaries) and the complete BIDS directories of [INSERT N] subjects chosen to span routine, ambulatory, and multi-day studies, including every EDF recording, JSON sidecar, channels table, annotation file, and scans table for those subjects. The sample is a verbatim subset of the published release.
- **Size:** approximately [INSERT SIZE] GB as a single zip archive.

The sample link is temporary and will be withdrawn after publication; the persistent record is the DOI above.
