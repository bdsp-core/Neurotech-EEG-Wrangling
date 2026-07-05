# Neurotech EEG Data Wrangling Plan

## Goal

Convert ~1,960 patient EEG folders from a Natus/Xltek NeuroWorks export (on external drive `Padlock_DT`) into a de-identified, BIDS-compliant EEG dataset and publish to:

```
s3://bdsp-opendata-repository/EEG/bids/Neurotech/
```

---

## 1. Source Data Inventory

| Item | Value |
|------|-------|
| Location | `/Volumes/Padlock_DT` |
| Patient folders | ~1,960 |
| EDF files | 5,975 (~3 per patient) |
| `.lay` annotation files | 884 unique (1,924 including backups) |
| `.xml` Persyst metadata | 3,866 |
| `.ems` study files | 136 |
| `.vinfo` video info | 14,498 |
| EDF format | EDF+C (continuous), 256 Hz, ~27-28 channels |
| Channel set | Standard 10-20 + ECG + Digi + EDF Annotations |
| Typical EDF size | ~400-850 MB per file |
| Estimated total | Hundreds of GB to ~1 TB+ |

### Source File Types and Their Role

| File | Contains | Use in Pipeline |
|------|----------|-----------------|
| `.edf` | Raw EEG signals + embedded annotations | **Primary data** — copy with de-identified header |
| `.lay` | Human annotations (INI format) | **Clinical annotations** — spikes, seizures, clips, free-text |
| `.mg2` + `.mg2.*.raw/.ar` | Persyst quantitative EEG trends | Skip (can be re-derived) |
| `.mg2.xml` | Persyst baseline statistics | Skip |
| `.mg2.ntf.xml` | File identification metadata | Skip |
| `.ems` | Binary study file (patient demographics, amplifier config) | Extract demographics if possible |
| `.vinfo` | Video reference info | Skip |
| `_m/` directories | Montage display configurations | Skip |

### Annotation Sources

1. **`.lay` files** (primary) — INI-style `[Comments]` section with `timestamp,duration,_,_,text`:
   - `@Spike` — machine or human spike markers
   - `@Clip: Awake` — technician state markers
   - `@Seizure` — seizure markers (if present)
   - Free text: `"NT-Bi-occipital S/W, right dominant."`, `"8 Hz PDR"`, `"Eyes Closed"`
   - Available for ~45% of patients

2. **EDF+ embedded annotations** — system markers (e.g. `"Serial number : 0000"`, `"YYY marker"`)
   - Mostly non-clinical; some may contain useful events

---

## 2. Target BIDS Structure

Based on the existing BDSP format at `s3://bdsp-opendata-repository/EEG/bids/S0001/`:

```
Neurotech/
├── dataset_description.json
├── participants.tsv
├── participants.json
├── README
├── sub-Neurotech1/
│   ├── ses-1/
│   │   ├── sub-Neurotech1_ses-1_scans.tsv
│   │   └── eeg/
│   │       ├── sub-Neurotech1_ses-1_task-EEG_eeg.edf
│   │       ├── sub-Neurotech1_ses-1_task-EEG_eeg.json
│   │       ├── sub-Neurotech1_ses-1_task-EEG_channels.tsv
│   │       └── sub-Neurotech1_ses-1_task-EEG_Xltek.csv     (if .lay annotations exist)
│   ├── ses-2/
│   │   └── ...
│   └── ...
├── sub-Neurotech2/
│   └── ...
└── ...
```

### Naming Conventions

- **Subjects**: `sub-Neurotech1`, `sub-Neurotech2`, ... `sub-Neurotech1960`
- **Sessions**: `ses-1`, `ses-2`, ... (one per EDF recording, numbered chronologically)
- **Task label**: `task-EEG` (routine EEG; could also use `task-cEEG` if continuous monitoring)
- **Files per session**:
  - `*_task-EEG_eeg.edf` — de-identified EEG data
  - `*_task-EEG_eeg.json` — recording metadata sidecar
  - `*_task-EEG_channels.tsv` — channel descriptions
  - `*_task-EEG_Xltek.csv` — Xltek/Natus annotations (from `.lay` files)
  - `*_scans.tsv` — session-level scan index (at session level, not inside eeg/)

### File Schemas

**`_eeg.json`** (per session):
```json
{
    "TaskName": "EEG",
    "Manufacturer": "Natus/Xltek",
    "PowerLineFrequency": 60,
    "SamplingFrequency": 256.0,
    "SoftwareFilters": "n/a",
    "RecordingDuration": 32148.5,
    "RecordingType": "continuous",
    "EEGReference": "n/a",
    "EEGGround": "n/a",
    "EEGPlacementScheme": "10-20",
    "EEGChannelCount": 25,
    "EOGChannelCount": 0,
    "ECGChannelCount": 1,
    "EMGChannelCount": 0,
    "MiscChannelCount": 1,
    "TriggerChannelCount": 0
}
```

**`_channels.tsv`** (per session):
```
name    type    units   low_cutoff  high_cutoff description sampling_frequency  status  status_description
Fp1     EEG     uV      0.0         128.0       ElectroEncephaloGram    256.0   good    n/a
Fp2     EEG     uV      0.0         128.0       ElectroEncephaloGram    256.0   good    n/a
...
ECG2    ECG     uV      0.0         128.0       ElectroCardioGram       256.0   good    n/a
Digi    MISC    uV      0.0         128.0       Digital input           256.0   good    n/a
```

**`_Xltek.csv`** (per session, if annotations exist):
```
Text,CreationTime
"@Clip: Awake",2025-10-24T10:55:58.000000
"Eyes Closed",2025-10-24T10:56:00.000000
"@Spike",2025-10-24T10:57:11.000000
"NT-Bi-occipital S/W, right dominant.",2025-10-24T10:57:11.000000
```

**`_scans.tsv`** (per session):
```
filename    acq_time
eeg/sub-Neurotech1_ses-1_task-EEG_eeg.edf  2025-10-24T10:54:47.000000Z
```

**`participants.tsv`** (dataset-level):
```
participant_id  age sex
sub-Neurotech1  n/a n/a
sub-Neurotech2  n/a n/a
```

**`dataset_description.json`** (dataset-level):
```json
{
    "Name": "Neurotech EEG Dataset",
    "BIDSVersion": "1.7.0",
    "DatasetType": "raw",
    "License": "TBD",
    "Authors": ["TBD"],
    "InstitutionName": "Neurotech"
}
```

---

## 3. De-identification Plan

### 3.1 Linking Table (kept locally, NEVER published)

File: `output/linking_table.csv` — one row per patient

| Column | Description |
|--------|-------------|
| `BDSPPatientID` | `Neurotech-1`, `Neurotech-2`, ... |
| `original_folder` | Original folder name (e.g. `Patient, Example 25-06077 EMS`) |
| `last_name` | Patient last name |
| `first_name` | Patient first name |
| `case_id` | Original case ID (e.g. `25-06077`) |
| `DOB_unshifted` | Date of birth (from EDF header, if available) |
| `DOB_shifted` | Date of birth + shift |
| `sex` | Sex (from EDF header, if available) |
| `ethnicity` | Ethnicity (if available — likely n/a) |
| `race` | Race (if available — likely n/a) |
| `shift_days` | Random integer in [-365, +365] applied to all dates |
| `recording_date_unshifted` | Original recording start date |
| `recording_date_shifted` | Shifted recording start date |
| `n_sessions` | Number of EDF files for this patient |

### 3.2 Date Shifting

- Generate one random integer per patient: `shift_days = random.randint(-365, 365)`
- Apply to ALL dates for that patient: recording dates, birth dates, annotation timestamps
- **Times are NOT shifted** — only the date component changes
- Store both `_unshifted` and `_shifted` versions in the linking table

### 3.3 EDF Header De-identification

The EDF header contains PHI in these fixed-position fields:

| Bytes | Field | PHI | Action |
|-------|-------|-----|--------|
| 8-87 | Local patient identification | Name, sex, birthdate, patient code | Replace with `X X X X` |
| 88-167 | Local recording identification | Start date, technician, equipment | Replace with `Startdate {shifted_date} X X X` |
| 168-175 | Start date (dd.mm.yy) | Recording date | Replace with shifted date |
| 176-183 | Start time (hh.mm.ss) | Recording time | **Preserve** (time is not PHI) |

**Approach**: Use the `edfio` library with `lazy_load_data=True` to avoid loading multi-GB signal data into memory. Alternatively, do direct binary header manipulation (the header is a fixed-size structure at known byte offsets).

### 3.4 EDF+ Annotation Channel De-identification

EDF+ files have an "EDF Annotations" signal channel that may contain:
- Recording start timestamps (with dates)
- Free-text annotations with dates

These must also be scrubbed or date-shifted. The `edfio` library handles this when using `anonymize()`.

### 3.5 `.lay` File Annotation De-identification

The `.lay` annotations use timestamps in seconds relative to recording start. These are already de-identified (no absolute dates/times). However, when converting to `_Xltek.csv` format with absolute timestamps, we must use the **shifted** recording start date + time.

### 3.6 What Gets Removed

- Patient name (from EDF header + folder name)
- Patient ID / case number
- Date of birth
- Recording date (replaced with shifted date)
- Technician name
- Hospital/equipment identifiers
- Any PHI in annotation free-text (need to scan for names, MRNs)

### 3.7 What Gets Preserved

- EEG signal data (unchanged)
- Channel labels and configuration
- Sampling rate
- Recording time of day (hh:mm:ss)
- Relative annotation timestamps
- Annotation clinical content (spike descriptions, seizure markers, etc.)
- Sex (as a demographic variable in participants.tsv)

---

## 4. Pipeline Steps

### Step 1: Run Inventory Extraction (DONE / IN PROGRESS)

Script: `extract_inventory.py`
- Reads all EDF headers and `.lay` files
- Produces `recordings.csv`, `annotations.csv`, `patients.csv`
- Used to validate data before conversion

### Step 2: Generate Linking Table & Subject Assignments

Script: `generate_linking_table.py`

1. Read `patients.csv` from Step 1
2. Assign `BDSPPatientID` = `Neurotech-{N}` sequentially (sorted by case_id or folder name)
3. For each patient:
   - Extract DOB, sex from EDF header (if available)
   - Generate `shift_days = random.randint(-365, 365)`
   - Compute shifted dates
4. Handle **duplicate patients** (same person, multiple folders):
   - Some patients appear in multiple folders (e.g. "Patient, Example 22-05711 EMS" and "Patient, Example 23-06942 EMS")
   - These should get the **same** `BDSPPatientID` and **same** `shift_days`
   - Match on exact name (last, first) — flag ambiguous matches for manual review
5. Save `output/linking_table.csv`

### Step 3: Build BIDS Directory Structure Locally

Script: `build_bids.py`

For each patient:
1. Create `sub-Neurotech{N}/`
2. For each EDF file (sorted chronologically → `ses-1`, `ses-2`, ...):
   a. Create `ses-{M}/eeg/`
   b. **Copy & de-identify EDF** → `sub-Neurotech{N}_ses-{M}_task-EEG_eeg.edf`
      - Use `edfio` with `lazy_load_data=True` to read
      - Clear patient identification fields
      - Apply date shift to recording date
      - Write de-identified copy
   c. **Generate `_eeg.json`** sidecar from EDF header metadata
   d. **Generate `_channels.tsv`** from EDF channel labels
   e. **Convert `.lay` → `_Xltek.csv`** if annotations exist
      - Convert relative timestamps to absolute shifted timestamps
      - Format: `Text,CreationTime`
   f. **Generate `_scans.tsv`** with shifted acquisition time

3. Generate dataset-level files:
   - `dataset_description.json`
   - `participants.tsv` (with BDSPPatientID, age, sex)
   - `participants.json` (column descriptions)
   - `README`

### Step 4: Validate BIDS Compliance

- Run [bids-validator](https://bids-standard.github.io/bids-validator/) on the local BIDS directory
- Check file naming, required sidecars, JSON schema compliance
- Spot-check a sample of de-identified EDFs to confirm PHI removal

### Step 5: Upload to S3

```bash
aws s3 sync ./bids_output/Neurotech/ s3://bdsp-opendata-repository/EEG/bids/Neurotech/ \
    --storage-class STANDARD
```

- Use `aws s3 sync` for resumable uploads
- Consider `--only-show-errors` for cleaner output on large uploads
- Verify upload: `aws s3 ls --recursive --summarize s3://bdsp-opendata-repository/EEG/bids/Neurotech/`

---

## 5. Handling Multi-Segment Recordings

Many patients have multiple EDF files per recording session (e.g. `2_0_1D...`, `2_0_2D...`, etc.). The naming convention appears to be:

```
{device}_{session}_{segment}D{timestamp}.edf
```

**Options:**
- **Option A (recommended)**: Treat each EDF file as a separate session (`ses-1`, `ses-2`, ...)
  - Simple, matches how existing BDSP data is structured
  - Each session is self-contained
- **Option B**: Group segments into sessions using the session number from the filename
  - Would require `run-1`, `run-2` BIDS entities within a session
  - More complex, but preserves the original session structure

**Decision**: Use Option A for consistency with existing BDSP data.

---

## 6. Handling Duplicate Patients

Some patients appear in multiple folders with different case IDs (different recording dates/visits):

```
Patient, Example 22-05711 EMS
Patient, Example 23-06942 EMS
```

These represent different visits for the same patient and should:
- Share the same `BDSPPatientID` (e.g. `Neurotech-42`)
- Share the same `shift_days`
- Get sequential session numbers across all visits

**Matching strategy**:
1. Exact match on `(last_name, first_name)` → same patient
2. Flag cases where names match but other identifiers conflict → manual review
3. Log all matches in the linking table

---

## 7. Channel Type Classification

The Neurotech data has ~27 channels. We need to classify them for `_channels.tsv`:

| Channel | BIDS Type | Description |
|---------|-----------|-------------|
| Fp1, Fp2, F3, F4, C3, C4, P3, P4, O1, O2, F7, F8, T3, T4, T5, T6, Fz, Pz, Cz, A1, A2, T1, T2, F11, F12 | EEG | Standard 10-20 electrodes |
| ECG2 | ECG | Electrocardiogram |
| Digi | MISC | Digital input channel |
| EDF Annotations | n/a | Not listed in channels.tsv (BIDS convention) |

---

## 8. Estimated Timeline & Resources

| Step | Estimated Duration | Notes |
|------|-------------------|-------|
| Step 1: Inventory | ~20 min | Running now |
| Step 2: Linking table | ~5 min | Quick script |
| Step 3: BIDS conversion | **8-24 hours** | Bottleneck: reading/writing ~6,000 large EDF files from external USB |
| Step 4: Validation | ~30 min | bids-validator |
| Step 5: S3 upload | **Hours to days** | Depends on upload bandwidth; ~500 GB+ of data |

### Storage Requirements
- Local BIDS output: ~same size as source data (EDF files are copied, not compressed)
- Ensure sufficient local disk space before starting Step 3
- Alternative: stream directly to S3 (more complex, but avoids local storage needs)

---

## 9. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| External drive disconnects mid-process | Build pipeline to be resumable (skip already-processed files) |
| PHI leakage in annotation free-text | Scan all annotation text for patterns matching names, MRNs, dates |
| Insufficient local disk space | Process in batches, or stream to S3 |
| Duplicate patient matching errors | Conservative matching + manual review log |
| EDF files with unusual formats | Error handling + error log for manual review |
| Large file memory issues | Use `edfio` lazy loading, never load full signal data |

---

## 10. Files Produced by This Pipeline

### Published to S3 (de-identified)
- `Neurotech/` BIDS directory with all subjects/sessions
- `dataset_description.json`, `participants.tsv`, `README`

### Kept Locally (NOT published)
- `output/linking_table.csv` — maps BDSPPatientID ↔ real identity + date shifts
- `output/recordings.csv` — full inventory with original metadata
- `output/annotations.csv` — all annotations with original timestamps
- `output/patients.csv` — patient summary
- `output/errors.csv` — any processing errors
- `output/phi_scan_results.csv` — results of PHI scanning in annotation text
