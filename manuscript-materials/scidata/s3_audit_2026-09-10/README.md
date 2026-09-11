# Audit of the published S3 release — 2026-09-10

Full listing of `s3://bdsp-opendata-repository/EEG/bids/Neurotech/` (231,893 objects) compared with
`output/s3_recordings.csv` (54,426 EDF sessions; 23,607 signal-bearing).

| Item | On S3 | Expected | Gap |
|---|---|---|---|
| EDF files | 54,319 | 54,426 | **107 sessions absent entirely** (`missing_edf_paths.txt`); 7 are signal-bearing (53.2 h, 2.6 GB), 100 are header-only stubs; 88 subjects affected; subjects 1899 and 3295 have no directory on S3 |
| Signal-bearing EDFs | 23,600 | 23,607 | 7 |
| Recording hours | 212,133 | 212,186 | 53 |
| Subjects with a signal-bearing EDF | 4,882 | 4,882 | 0 |
| Sessions with sidecars but no EDF | 31 | 0 | not in the recordings table (subjects 1028, 934, 970 have only such sessions) |
| Sessions with an EDF but a missing sidecar | 9 | 0 | `missing_sidecar_paths.txt` (44 files in total with the 31 above) |
| `participants.tsv` rows | 4,915 | one per subject directory | matches the S3 subject directories today |
| `*_eeg.json` Manufacturer | "Natus/Xltek" | "Lifelines/EMS" | all 54,346 sidecars; fix with `patch_s3_manufacturer.py` |

The manuscript keeps the cohort numbers of the built release (4,914 subjects with EDF sessions, 23,607
signal-bearing segments, 212,186 h), which are reproducible from `output/s3_recordings.csv`; it no longer
claims a per-session completeness check of the published tree.

## Restore (run on the machine that holds the BIDS output, e.g. the SSD)

```bash
export NT_BIDS_ROOT=/path/to/bids_output/Neurotech
cd "$NT_BIDS_ROOT"
# 1. the 107 absent sessions (all files of each session directory)
sed -E 's#/(eeg/)?[^/]+$##' missing_edf_paths.txt | sort -u > sessions_to_restore.txt
rclone copy . s3:bdsp-opendata-repository/EEG/bids/Neurotech/ --files-from <(for s in $(cat sessions_to_restore.txt); do find "$s" -type f; done) --transfers 8 -P
# 2. the 44 missing sidecar/EDF files inside sessions that already exist on S3
rclone copy . s3:bdsp-opendata-repository/EEG/bids/Neurotech/ --files-from missing_sidecar_paths.txt -P
# 3. regenerate participants.tsv so it lists every subject directory (ehr_pipeline/build_bids_phenotype.py), re-upload
# 4. patch Manufacturer in all sidecars
python patch_s3_manufacturer.py --list <(rclone lsf -R --files-only --include '*_eeg.json' s3:bdsp-opendata-repository/EEG/bids/Neurotech/)
# 5. re-run this audit (rclone lsf -R --files-only ... | count by suffix) and update dataset_description/README if counts change
```
Never use `rclone sync` against the release root.
