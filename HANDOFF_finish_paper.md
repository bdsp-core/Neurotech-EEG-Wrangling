# Handoff — finish the Neurotech EEG data-descriptor paper ✅ COMPLETED (2026-07-03)

> **STATUS: DONE.** Every task in this handoff has been completed. The conflicting/
> provisional numbers quoted below were the *starting state*; they have all been resolved.
> **Do not treat the numbers in this file as current** — the authoritative, reproduced
> values live in the manuscript, the committed de-identified tables, and
> `reproduce_manuscript_numbers.py`. See `REPRODUCIBILITY.md` for the full picture.

## Final resolutions (authoritative values)

| Item | Provisional (in early drafts / this handoff) | RESOLVED value (committed + reproduced) |
|---|---|---|
| Cohort | small pre-expansion cohort | **4,914 patients / 23,607 recordings / 212,186 hours / 10.2 TB** |
| Patients with clinical docs | 4,828 / 4,844 | **4,812 (98%)** |
| Age at first EEG | n=2,928 / 2,932 | **median 26.7 (IQR 13.4–48.2), n=2,915** |
| Sex | n=3,024 / 3,037 | **n=3,005 (1,374 M / 1,631 F)** |
| Referral ICD codes | 9,017 / 13,083 | **13,049 total** (G40 7,073·54% / R56 1,648·13% / R25 618·5% / Other 3,710·28%) |
| PDR extractable | 8,078 vs 5,333 "conflict" | **8,057** — ranges (e.g. "8-9") are valid extractions, counted at midpoint; median 9.0 Hz, 85% normal. Same rule in generator + reproduce gate. |
| Sub-documents | — | **40,529 across 11 document types** (confirmed against `output/`) |

## What was done
1. **Reproducibility closed.** `ehr_pipeline/build_deid_tables.py` now emits enriched,
   PHI-free tables (IED categorical flags, monitoring aggregates, comorbidities, meds,
   dates scrubbed, deterministic build). `manuscript-materials/generate_tables_and_figures.py`
   reads **only** committed de-identified tables — no `/Volumes` drive dependency.
   `reproduce_manuscript_numbers.py` reproduces every manuscript number from committed data;
   EEG/annotation numbers are additionally reproducible from public S3.
2. **Manuscript reconciled** to the reproduced values throughout (abstract, Table 2,
   Supp Tables 4/5, all figure legends). Consistency review: no cross-reference mismatches.
3. **Figures.** Fig 2/3/4 + Supp Fig 3/4 regenerate from committed data and were restyled
   (single-color ranked bars, unified quantile method, comorbidity de-duplication).
   Hand-made schematics that our code does not produce are specified for manual update in
   `manuscript-materials/FIGURES_FOR_ARTIST.md` (Figure 1 pipeline numbers; Supp Fig 1
   example EEG traces — **now generated, see below**; Supp Fig 2 de-id header is correct).
4. **PHI.** Committed `output/ehr_deid_tables/*.csv` audited: no names, no raw dates,
   structured columns / categorical flags / aggregates only. Raw `output/ehr/` stays gitignored.

## Known remaining (non-blocking, tracked in FIGURES_FOR_ARTIST.md)
- **Figure 1** (pipeline schematic) still shows old small-cohort numbers — artist to update.
- **Supplementary Figure 1** (example EEG traces) — ✅ **now created** (see update below).

---

## UPDATE — Supplementary Figure 1 (example EEG traces) created & pushed

Supp Fig 1 was the missing "example EEG traces" figure. It existed only as a *panel* inside
the archived `figure2_dataset_characteristics.png`; its generator and source data
(`eeg_snippets.npz`) were only in the local gitignored `archive/` — never pushed. And
`md_to_docx.py` was wiring Supp Fig 1 to `figure3_annotation_recording_summary.png`, a **stale
1,744-patient bar chart** (wrong image). Now fixed and on `main`:

- `manuscript-materials/figure_data/eeg_snippets.npz` — committed signal snippets (19 ch,
  256 Hz, 5 s; from an already-published de-identified recording) → figure is repo-reproducible.
- `manuscript-materials/make_supp_figure1_eeg.py` — standalone generator (rebuilds the bipolar
  montage, 1–30 Hz band-pass + 60 Hz notch, both panels + scale bar).
- `manuscript-materials/figures/supp_figure1_eeg_example.{png,pdf}` — rendered figure.
- `md_to_docx.py` — Supp Fig 1 now points at `supp_figure1_eeg_example.png`.

**Small follow-ups (fold into the figure styling you already did):**
- Match `supp_figure1_eeg_example`'s fonts/sizing to the unified figure style.
- `figure3_annotation_recording_summary.png` is now **orphaned** and **stale** (old cohort) —
  archive it (Figure 2B already covers annotation categories).
- Confirm the auto-marked spike (~2.5 s, largest synchronous deflection) is one you're happy to
  publish; adjust in the script if you prefer a different example.
- If Figure 1 is rebuilt after this, re-run `md_to_docx.py` so the `.docx` picks up Supp Fig 1.
