# Figures needing manual (artist) updates

Most figures are **regenerated automatically from committed data** by
`manuscript-materials/generate_tables_and_figures.py` and need no artist work. The
figures below are **hand-drawn schematics / illustrations** (BioRender-style) that our
code does not produce, so they must be updated by hand.

**Authoritative cohort numbers (use these everywhere):**
`4,914 patients · 23,607 EEG recordings · 212,186 hours · 10.2 TB · 2021–2025 · Natus/Xltek`

---

## ✅ Figure 1 — "Data pipeline from clinical recording to public release"
**File:** `figures/figure1_pipeline.png` · **Status: DONE (2026-07-03)** — replaced with a
corrected schematic showing the full A–Z cohort (4,914 / 23,607 / 212,186). Old small-cohort
version archived locally. The spec below is retained for reference only.

<details><summary>original fix spec (now applied)</summary>

This is a 5-stage horizontal flow diagram (rounded panels, one per stage, grey arrows
between them). The layout, icons, and colors are good and should be **kept as-is**. Only
the **numbers and a couple of labels are out of date** — they still show an early,
much smaller cohort. Update the text only:

| Panel | Currently shows (WRONG) | Change to (CORRECT) |
|---|---|---|
| **Stage 1 — EEG Recording** | `1,744 patients` | `4,914 patients` |
| **Stage 2 — Raw Export** | `8,410 EEG recordings` (large bold number) | `23,607 EEG recordings` |
| **Stage 2 — Raw Export** | `77,575 hours of data` | `212,186 hours of data` |

Everything else in Figure 1 is correct and should stay:
- Stage 1: "Clinical EEG recording", "2021–2025", "Natus/Xltek NeuroWorks".
- Stage 2: "+ .lay annotation files" (the raw Natus export format — keep).
- Stage 3 — De-identification: "Scrub EDF headers", "Shift dates ±365 days", "Replace names with [NAME]".
- Stage 4 — BIDS Conversion: "BIDS-EEG format", "sub-NeurotechN/ses-N/eeg/", file-type chips `.edf .json .tsv .csv`.
- Stage 5 — BDSP Release: "s3://bdsp-opendata-repository", "Accessible via Data Use Agreement (DUA)".

> Note: keep the bold styling on the Stage-2 headline number (it is the visual focal point).
> Double-check the three replaced numbers against the table above — they are the exact
> values reported throughout the manuscript abstract, Table 2, and every figure legend.

</details>

---

## ✅ Supplementary Figure 1 — "Example EEG traces" (normal background + interictal spike)
**File:** `figures/supp_figure1_eeg_example.png` · **Status: DONE (2026-07-03)** — created and
integrated. Reproducible from committed data (`figure_data/eeg_snippets.npz` via
`make_supp_figure1_eeg.py`): 18-channel longitudinal bipolar montage, two panels (normal
background + interictal spike marked at ~2.5 s), 100 µV / 1 s scale bar. Now embedded in the
docx. Optional polish only (match title font to the other figures). Spec retained below.

The manuscript references this figure and gives it a legend, but no image file exists.
It should show **real EEG waveform traces**, two side-by-side panels:

- **Left panel — "Normal background":** ~8 channels of a standard 10-20 **bipolar montage**
  (e.g., Fp1–F7, F7–T3, T3–T5, T5–O1 and the right-sided homologues), ~10 seconds,
  showing normal posterior-dominant background activity, no epileptiform discharges.
- **Right panel — "Interictal spike":** the same 8 channels, ~10 seconds, showing a clear
  interictal spike/sharp-wave. Overlay the actual technician annotation text
  **"NT-Bi-occipital S/W, right dominant"** at the moment of the event (small callout / vertical marker).
- **Scale bars:** a vertical bar labelled **100 µV** and a horizontal bar labelled **1 second**,
  placed once (e.g., lower-left of the left panel).
- Channel labels on the left; clean, publication-style (thin black traces on white, no grid clutter).

> **Recommended:** this figure is best **generated from a real de-identified recording** in
> the public S3 dataset rather than hand-drawn, so the traces are authentic and the spike is
> real. I can write a short script to pull one published recording
> (`s3://bdsp-opendata-repository/EEG/bids/Neurotech/…`), plot the two 10-second windows, and
> add the annotation + scale bars — just say the word and I'll produce it in-code (then it
> becomes reproducible like the other figures). If you'd rather your artist mock it up
> stylistically, the spec above is sufficient.

---

## 🟢 Supplementary Figure 2 — "De-identification of EDF header fields"
**File:** `figures/supp_figure2_deidentification.png` · **Status: OK — no numbers to fix**

A before→after table (red "Before (PHI)" column on the left, green "After" column on the
right, blue transformation pills in the middle) for six header fields: Patient Name → `[NAME]`,
Patient ID → `Neurotech-0042`, Recording Date shift, Birth Date shift, Technician → removed,
Equipment → unchanged. All examples are fictitious and the date-shift math is internally
consistent (+99-day example, drawn from ±365). **No content changes required.** Optional polish
only: match font/weight to Figure 1 for a uniform supplement, and (if desired) change the
example ID prefix to match the released style `sub-NeurotechN`. Safe to ship as-is.

---

## ✅ Code-generated figures — no artist work needed
Regenerated from committed de-identified data by `generate_tables_and_figures.py`:
- **Figure 2** — Dataset positioning (`figure2_dataset_positioning.png`)
- **Figure 3** — Patient characteristics (`figure3_patient_characteristics.png`)
- **Figure 4** — EEG findings (`figure4_eeg_findings.png`)
- **Supplementary Figure 3** — Comorbidities & anti-seizure medications (`supp_figure3_comorbidities_meds.png`)
- **Supplementary Figure 4** — Monitoring characteristics (`supp_figure4_monitoring.png`)

> `figure3_annotation_recording_summary.png` is a **legacy** figure with old small-cohort
> numbers; its content is now covered by Figure 2 (panels B and C). It has been moved to
> `archive/` and is not part of the manuscript.
