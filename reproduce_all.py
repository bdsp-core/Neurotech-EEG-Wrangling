#!/usr/bin/env python3
"""
Reproduce EVERYTHING in the manuscript with one command.

Regenerates every code-produced figure and table, rebuilds the Word document, and
reproduces every quantitative claim in the paper — all from committed, de-identified
repo data (public S3 dataset + committed aggregate CSVs). No PHI, no external drive.

Runs, in order:
  1. manuscript-materials/generate_tables_and_figures.py
        -> Figures 2, 3, 4 + Supplementary Figures 3, 4
        -> Table 2 + Supplementary Tables 4, 5
  2. manuscript-materials/make_supp_figure1_eeg.py
        -> Supplementary Figure 1 (example EEG traces, from figure_data/eeg_snippets.npz)
  3. manuscript-materials/md_to_docx.py
        -> rebuild Neurotech_EEG_Dataset_Draft.docx with all figures embedded
  4. reproduce_manuscript_numbers.py
        -> print every EEG / annotation / EHR number (each matches the manuscript)

NOT regenerable from code (hand-made schematics; static image assets committed to the repo):
  - Figure 1                 manuscript-materials/figures/figure1_pipeline.png
  - Supplementary Figure 2   manuscript-materials/figures/supp_figure2_deidentification.png

Usage:
  .venv/bin/python reproduce_all.py            # or: python reproduce_all.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
MM = ROOT / "manuscript-materials"

STEPS = [
    ("Regenerate tables + Figures 2/3/4 + Supp Figs 3/4", MM / "generate_tables_and_figures.py"),
    ("Regenerate Supp Fig 1 (example EEG traces)",         MM / "make_supp_figure1_eeg.py"),
    ("Rebuild the Word document (.docx)",                  MM / "md_to_docx.py"),
    ("Reproduce every manuscript number",                  ROOT / "reproduce_manuscript_numbers.py"),
]

HAND_MADE = [
    ("Figure 1", "manuscript-materials/figures/figure1_pipeline.png"),
    ("Supplementary Figure 2", "manuscript-materials/figures/supp_figure2_deidentification.png"),
]


def run(label: str, script: Path) -> None:
    rel = script.relative_to(ROOT)
    print(f"\n{'=' * 72}\n▶  {label}\n   {rel}\n{'=' * 72}", flush=True)
    result = subprocess.run([PY, str(script)], cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n✗  FAILED: {rel} (exit {result.returncode})")
        sys.exit(result.returncode)


def main() -> int:
    print("Reproducing all manuscript artifacts from committed, de-identified data...")
    for label, script in STEPS:
        run(label, script)
    print("\n" + "=" * 72)
    print("✅  Done. All code-generated figures + tables regenerated, docx rebuilt,")
    print("    and every manuscript number reproduced from committed data.")
    print("\n    Hand-made schematics (static assets, not code-generated):")
    for name, path in HAND_MADE:
        print(f"      - {name:24s} {path}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
