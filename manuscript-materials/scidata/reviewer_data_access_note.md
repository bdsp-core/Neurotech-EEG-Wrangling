# Note to editors and reviewers: data access during peer review

**Manuscript:** Clinical scalp electroencephalography of 4,912 patients including multi-day ambulatory home recordings

**Dataset:** The Neurotech EEG Dataset, Brain Data Science Platform (BDSP), https://doi.org/10.60508/v99k-ek82 (https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/)

The dataset is distributed under **controlled access** because it contains patient-level health information (diagnoses, medications, EEG findings) with age and sex. Regular users register on bdsp.io, complete credentialing, and sign the data use agreement (https://bdsp.io/content/nf89816gtxbon11kbr9a/view-dua/1.0/), which prohibits re-identification and redistribution.

So that reviewers can inspect the data **immediately and without revealing their identity**, we have created a temporary reviewer account on BDSP that is already credentialed and has the data use agreement recorded:

- **Login page:** https://bdsp.io/login/
- **Username:** [INSERT USERNAME]
- **Password:** [INSERT PASSWORD]
- **Dataset page (after login):** https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/ — the Files section lists every file of the release (dataset-level files, the phenotype tables, and the per-subject BIDS directories with EDF recordings, sidecars, and annotation files) for direct download.
- **Bulk access (optional):** for the full 10.2 TB release, enter any AWS account ID under Account → Cloud settings while logged in as the reviewer account; access to `s3://bdsp-opendata-repository/EEG/bids/Neurotech/` is granted automatically, after which `aws s3 sync` works.

The account is shared by all reviewers and records no reviewer identity; it will be disabled after publication. The persistent record is the DOI above.
