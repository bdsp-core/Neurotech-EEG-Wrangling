# Supplementary Material

## The Neurotech EEG Dataset: A Large Clinical Scalp EEG Corpus Dominated by Multi-Day Ambulatory Recordings

Morgan et al.

---

## Supplementary Tables

**Supplementary Table 1. Recording duration categories.** The majority of segments represent ambulatory or short-term monitoring.

| Category | Duration | N segments (%) | Likely clinical setting |
|---|---|---|---|
| Routine | < 1 hour | 8,545 (36%) | Outpatient EEG |
| Short monitoring | 1 - 24 hours | 12,572 (53%) | Ambulatory or short-term |
| Prolonged monitoring | > 24 hours | 2,490 (11%) | Multi-day ambulatory |

*Percentages computed over 23,607 EDF segments containing recoverable signal data.*

**Supplementary Table 2. Annotation categories.** Technician clips and spike markers are the most frequent categories.

| Category | Events | Description |
|---|---|---|
| Technician clips | 53,469 | Segments selected for physician review |
| Spike markers | 50,482 | Interictal epileptiform discharge detections |
| Neurotech free-text comments | 24,267 | Free-text EEG finding descriptions |
| Sharp waves | 21,330 | Sharp wave or sharp-slow-wave complexes |
| Slowing | 19,401 | Focal or diffuse slowing |
| Activation procedures | 15,746 | Eyes open/closed, photic, hyperventilation |
| Generalized patterns | 12,345 | Generalized discharges |
| Spike-wave | 10,439 | Spike-wave complexes |
| Seizure markers | 6,892 | Electrographic seizure events |
| Posterior dominant rhythm | 5,535 | PDR frequency notations |
| Artifact | 4,881 | Technical or physiological artifacts |
| Burst-suppression | 3,350 | Burst-suppression pattern |
| Focal | 1,928 | Focal patterns |
| Normal | 505 | "Normal" notations |
| Epileptiform | 164 | Other epileptiform |
| Periodic | 139 | Periodic discharges (LPDs/GPDs) |

*Categories are not mutually exclusive; a single annotation may contribute to multiple categories. Total annotation events: 226,486 across 14,517 segments with annotation files.*

**Supplementary Table 3. De-identification example.** Header field transformation and annotation scrubbing for a representative recording.

| Field | Original | De-identified |
|---|---|---|
| Patient identification | `12-34567 X 15-MAR-2023 Doe_Jane` | `X X X X` |
| Recording identification | `Startdate 15-MAR-2023 Record_stopped...` | `Startdate 22-JUN-2023 X X X` |
| Start date | `15.03.23` | `22.06.23` (shifted +99 days) |
| Start time | `14.32.08` | `14.32.08` (preserved) |
| Annotation text | `Patient event Jane had a blank stare` | `Patient event [NAME] had a blank stare` |
| Annotation timestamp | `2023-03-15T14:33:45` | `2023-06-22T14:33:45` (shifted) |

*Names and dates shown are fictitious. Actual date shifts are random per patient (uniform integer in [-365, +365] days) and applied consistently across all files for that patient.*

**Supplementary Table 4. Detailed EEG findings.** Breakdown of posterior dominant rhythm (PDR), interictal epileptiform discharges, slowing, seizures, and patient-reported events extracted from technologist scan reports (n=10,726 studies with extractable reports).

| Finding | Value | Notes |
|---|---|---|
| **Posterior dominant rhythm** | | |
|   PDR extractable | 8057 | of 10726 studies |
|   PDR frequency, median (IQR) | 9.0 (8.5-10.0) | Hz |
|   Normal range (8-13 Hz) | 6816 | (85%) |
|   Slow (<8 Hz) | 1146 | (14%) |
| Interictal epileptiform discharges | 6345 | of 10726 studies (59%) |
| **Morphology** | | |
|     Spike | 3342 |  |
|     Sharp wave | 1755 |  |
|     Spike-and-wave | 1669 |  |
|     Polyspike | 502 |  |
| **Distribution** | | |
|     Generalized | 1691 |  |
|     Focal | 1364 |  |
|     Multifocal | 277 |  |
|     Bilateral independent | 97 |  |
| **Laterality** | | |
|     Left / Right / Bilateral | 1770 / 1611 / 709 |  |
| **Region (temporal/frontal/central/parietal/occipital)** | 1940 / 1261 / 878 / 329 / 404 |  |
| Abnormal slowing | 4524 | of 10726 studies |
| Electrographic seizures | 2379 | of 10726 studies |
| Patient-reported events | 5119 |  |

*Morphology, distribution, laterality, and region were extracted from free-text descriptions using regex pattern matching. Categories are not mutually exclusive.*

**Supplementary Table 5. Hourly EEG monitoring data.** Summary of technician monitoring activity extracted from monitoring logs in technologist scan reports.

| Metric | Value |
|---|---|
| Studies with monitoring data | 6413 |
| Total logged hours | 296,948 |
| Hours recording active | 273,796 (92%) |
| Distinct days/study, median (IQR) | 3.0 (2.0-4.0) |
| Monitoring events | 173,096 |
|   EEG reviewed / General notes / Equipment failures | 134,875 / 37,704 / 517 |

*Each monitoring hour was documented individually by the assigned technician, including impedance, recording status, battery level, and free-text observations.*

---

## Supplementary Figures

**Supplementary Figure 1.** Example EEG traces from a representative recording in standard bipolar montage showing normal background activity (left) and an interictal spike (right). Channels from the standard 10-20 montage are displayed; scale bars indicate 100 microvolts and 1 second.

**Supplementary Figure 2.** De-identification of EDF header fields. Each row shows a header field before (containing protected health information) and after de-identification. Patient names are replaced with placeholders, identifiers are reassigned, dates are shifted by a consistent per-patient random offset, and technician and equipment identifiers are removed. All examples shown are fictitious.

**Supplementary Figure 3.** Comorbidities and anti-seizure medications. (A) Ten most frequent comorbidities extracted from clinical progress notes, excluding seizure-related diagnoses. (B) Ten most frequently prescribed anti-seizure medications. Levetiracetam is the most common, consistent with its status as a first-line agent.

**Supplementary Figure 4.** Monitoring characteristics. (A) Distribution of total monitoring duration across 6413 studies with hour-by-hour monitoring data. Peaks at 24 and 48 hours reflect standard ordered monitoring durations. (B) Recording activity by hour of day across all 296,948 documented monitoring hours. Light shading shows total hours logged; dark shading shows hours with active recording.
