#!/usr/bin/env python3
"""Figure 1 — data pipeline schematic, generated in code (reproducible).

Five-stage horizontal flow: EEG recording -> raw export -> de-identification ->
BIDS conversion -> BDSP release. Numbers/labels reflect the corrected facts
(Lifelines/EMS + Persyst; 23,607 EDF recording segments). Replaces the hand-made
BioRender version so it stays correct and code-controlled.

Run:  .venv/bin/python manuscript-materials/make_figure1_pipeline.py
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG_DIR = Path(__file__).resolve().parent / "figures"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica"]})

# (title, headline, body-lines, fill, edge)
STAGES = [
    ("Stage 1:\nEEG Recording", None,
     ["Clinical EEG recording", "4,914 patients", "2021–2025",
      "Lifelines / EMS", "ambulatory equipment", "(Persyst detection)"],
     "#eff6ff", "#2563eb"),
    ("Stage 2:\nRaw Export", "23,607\nEDF recording\nsegments",
     ["212,186 hours of signal", "(≈ one multi-day study", "per patient)",
      "+ .lay annotation files"],
     "#ecfdf5", "#059669"),
    ("Stage 3:\nDe-identification", None,
     ["• Scrub EDF headers", "• Shift dates ±365 days",
      "• Replace names with", "   [NAME]"],
     "#fff7ed", "#ea580c"),
    ("Stage 4:\nBIDS Conversion", None,
     ["BIDS-EEG format", "sub-NeurotechN/", "  ses-N/eeg/", "", ".edf  .json  .tsv  .csv"],
     "#f5f3ff", "#7c3aed"),
    ("Stage 5:\nBDSP Release", None,
     ["s3://bdsp-opendata-", "  repository", "", "Accessible via a", "Data Use Agreement", "(DUA)"],
     "#f3f4f6", "#4b5563"),
]


def main():
    n = len(STAGES)
    fig, ax = plt.subplots(figsize=(16, 4.6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    bw, x0, gap = 0.163, 0.012, 0.0
    span = (1 - 2 * x0)
    step = span / n
    box_bottom, box_h = 0.06, 0.62
    centers = []
    for i, (title, headline, body, fill, edge) in enumerate(STAGES):
        cx = x0 + step * (i + 0.5)
        centers.append(cx)
        left = cx - bw / 2
        ax.add_patch(FancyBboxPatch((left, box_bottom), bw, box_h,
                     boxstyle="round,pad=0.006,rounding_size=0.02",
                     linewidth=2, edgecolor=edge, facecolor=fill, mutation_aspect=0.4))
        # stage title (bold) above the box
        ax.text(cx, 0.94, title, ha="center", va="top", fontsize=13, fontweight="bold", color=edge)
        # body
        y = box_bottom + box_h - 0.06
        if headline:
            ax.text(cx, y, headline, ha="center", va="top", fontsize=15, fontweight="bold", color=edge)
            y -= 0.20
        for line in body:
            ax.text(cx, y, line, ha="center", va="top", fontsize=10.5, color="#1f2937")
            y -= 0.062
    # arrows between boxes
    for i in range(n - 1):
        x_from = centers[i] + bw / 2 + 0.003
        x_to = centers[i + 1] - bw / 2 - 0.003
        ax.add_patch(FancyArrowPatch((x_from, box_bottom + box_h / 2),
                     (x_to, box_bottom + box_h / 2), arrowstyle="-|>",
                     mutation_scale=22, linewidth=2.2, color="#374151"))
    fig.tight_layout(pad=0.4)
    FIG_DIR.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"figure1_pipeline.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
        print("saved", FIG_DIR / f"figure1_pipeline.{ext}")
    plt.close(fig)


if __name__ == "__main__":
    main()
