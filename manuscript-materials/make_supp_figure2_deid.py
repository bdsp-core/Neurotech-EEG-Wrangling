#!/usr/bin/env python3
"""Supplementary Figure 2 — de-identification of EDF header fields (code-generated).

Before -> transformation -> after, for six header fields. Corrected facts: the
equipment example is a Lifelines device, and equipment identifiers are REMOVED
(they are scrubbed in the released files), not kept. All examples are fictitious.

Run:  .venv/bin/python manuscript-materials/make_supp_figure2_deid.py
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

FIG_DIR = Path(__file__).resolve().parent / "figures"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica"]})

# (field, before PHI value, transformation, after value)
ROWS = [
    ("Patient Name", '"Jane Doe"', "Replace", '"[NAME]"'),
    ("Patient ID", '"12-34567"', "Reassign", '"Neurotech-0042"'),
    ("Recording Date", '"15-MAR-2023"', "Shift (+99 days)", '"22-JUN-2023"'),
    ("Birth Date", '"04-JUL-1985"', "Shift (+99 days)", '"11-OCT-1985"'),
    ("Technician", '"J. Smith, R. EEG T."', "Remove", '"[removed]"'),
    ("Equipment", '"Lifelines ambulatory"', "Remove", '"[removed]"'),
]

RED_F, RED_E = "#fde8e8", "#e02424"
GRN_F, GRN_E = "#def7ec", "#0e9f6e"
BLU_F, BLU_E = "#e1effe", "#1c64f2"
DARK = "#1f2937"


def cell(ax, x, y, w, h, field, value, fill, edge):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.02",
                 linewidth=1.6, edgecolor=edge, facecolor=fill, mutation_aspect=0.35))
    ax.text(x + 0.015, y + h * 0.66, field + ":", ha="left", va="center",
            fontsize=11, fontweight="bold", color=DARK)
    ax.text(x + 0.015, y + h * 0.30, value, ha="left", va="center",
            fontsize=11, family="monospace", color=DARK)


def main():
    fig, ax = plt.subplots(figsize=(12.5, 7.6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    lx, lw = 0.02, 0.40      # before column
    rx, rw = 0.60, 0.38      # after column
    px = 0.50                # transformation pill center
    # headers
    ax.text(lx + lw / 2, 0.955, "Before De-identification (PHI)", ha="center", fontsize=13, fontweight="bold", color=DARK)
    ax.text(px, 0.955, "Transformation", ha="center", fontsize=13, fontweight="bold", color=DARK)
    ax.text(rx + rw / 2, 0.955, "After De-identification", ha="center", fontsize=13, fontweight="bold", color=DARK)

    n = len(ROWS); top = 0.90; row_h = 0.115; gap = 0.021
    for i, (field, before, transform, after) in enumerate(ROWS):
        y = top - i * (row_h + gap) - row_h
        cell(ax, lx, y, lw, row_h, field, before, RED_F, RED_E)
        cell(ax, rx, y, rw, row_h, field, after, GRN_F, GRN_E)
        cy = y + row_h / 2
        # arrow left-box -> pill -> right-box
        ax.add_patch(FancyArrowPatch((lx + lw + 0.005, cy), (px - 0.075, cy),
                     arrowstyle="-", linewidth=1.6, color="#4b5563"))
        ax.add_patch(FancyBboxPatch((px - 0.075, cy - 0.028), 0.15, 0.056,
                     boxstyle="round,pad=0.004,rounding_size=0.03",
                     linewidth=1.4, edgecolor=BLU_E, facecolor=BLU_F, mutation_aspect=0.5))
        ax.text(px, cy, transform, ha="center", va="center", fontsize=9.5, color=BLU_E, fontweight="bold")
        ax.add_patch(FancyArrowPatch((px + 0.075, cy), (rx - 0.005, cy),
                     arrowstyle="-|>", mutation_scale=16, linewidth=1.6, color="#4b5563"))

    ax.text(0.5, 0.02,
            "Recording and birth dates are shifted by the same random per-patient offset; times of day are preserved. "
            "All examples are fictitious.",
            ha="center", va="bottom", fontsize=9.5, style="italic", color="#4b5563")
    fig.tight_layout(pad=0.4)
    FIG_DIR.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG_DIR / f"supp_figure2_deidentification.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
        print("saved", FIG_DIR / f"supp_figure2_deidentification.{ext}")
    plt.close(fig)


if __name__ == "__main__":
    main()
