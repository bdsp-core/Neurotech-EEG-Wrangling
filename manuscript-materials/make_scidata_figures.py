#!/usr/bin/env python3
"""Build the Scientific Data figure set (one file per figure, lower-case panel letters).

Outputs to manuscript-materials/scidata/figures/:
  Figure1.png            pipeline illustration (copied from figures/fig1.png)
  Figure2.png/.pdf       de-identification of EDF header fields (copied from supp_figure2_deidentification)
  Figure3.png/.pdf       data overview composite, panels a-f (regenerated from committed de-identified tables)
  Figure4.png/.pdf       example EEG traces, panels a/b (regenerated from figure_data/eeg_snippets.npz)

Run:  .venv/bin/python manuscript-materials/make_scidata_figures.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

MM = Path(__file__).resolve().parent
sys.path.insert(0, str(MM))
import generate_tables_and_figures as g  # noqa: E402  (sets the shared rcParams on import)
import make_supp_figure1_eeg as tr  # noqa: E402

OUT = MM / "scidata" / "figures"
OUT.mkdir(parents=True, exist_ok=True)


def letter(ax, s, x=-0.14, y=1.05):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=15, fontweight="bold", va="bottom", ha="left")


def figure3_overview(data: dict, demo: dict):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.6))
    s3_data = [r for r in data["s3_recordings"] if int(r.get("n_records", 0) or 0) > 0]

    # a: duration distribution
    ax = axes[0, 0]
    durs = [float(r["duration_hours"]) for r in s3_data if r.get("duration_hours")]
    ax.hist(durs, bins=np.logspace(-2, 2, 50), color=g.PALETTE[1], edgecolor="white", alpha=0.85)
    ax.set_xscale("log")
    ax.set_xlabel("EDF segment duration (hours)")
    ax.set_ylabel("Number of segments")
    ax.set_title("Segment duration", fontweight="bold")
    for v in (1, 24):
        ax.axvline(v, color="gray", linestyle="--", alpha=0.6)
    ytop = ax.get_ylim()[1]
    ax.text(0.3, ytop * 0.92, "<1 h", fontsize=9, color="gray")
    ax.text(3, ytop * 0.92, "1-24 h", fontsize=9, color="gray")
    ax.text(30, ytop * 0.92, ">24 h", fontsize=9, color="gray")
    letter(ax, "a")

    # b: annotation categories (top 10)
    ax = axes[0, 1]
    NAMES = {"clip": "Technologist clip", "spike": "Spike", "neurotech_comment": "Free-text observation (NT-)",
             "sharp_wave": "Sharp wave", "slowing": "Slowing", "activation": "Activation procedure",
             "generalized": "Generalized pattern", "spike_wave": "Spike-wave", "seizure": "Seizure",
             "pdr": "Posterior dominant rhythm", "artifact": "Artifact", "burst_suppression": "Burst-suppression"}
    ann = sorted((r for r in data.get("s3_annotations", []) if r["category"] != "other"),
                 key=lambda r: -int(r.get("count", 0)))[:10]
    labels = [NAMES.get(r["category"], r["category"].replace("_", " ").capitalize()) for r in ann]
    counts = [int(r["count"]) for r in ann]
    ax.barh(labels[::-1], counts[::-1], color=g.PALETTE[1])
    ax.set_xlabel("Number of annotations")
    ax.set_title("Annotation categories", fontweight="bold")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    letter(ax, "b", x=-0.55)

    # c: referral indications
    ax = axes[0, 2]
    diag = data.get("diagnosis_codes", [])
    groups = {"Epilepsy (G40)": "G40", "Convulsions (R56)": "R56", "Altered awareness (R40)": "R40",
              "Syncope (R55)": "R55", "Abnormal movements (R25)": "R25"}
    counts_c, labels_c = [], []
    for lab, prefix in groups.items():
        counts_c.append(sum(1 for r in diag if r.get("code", "").upper().startswith(prefix)))
        labels_c.append(lab)
    counts_c.append(len(diag) - sum(counts_c))
    labels_c.append("Other")
    ax.barh(labels_c[::-1], counts_c[::-1], color=g.PALETTE[1])
    ax.set_xlabel("Number of referral codes")
    ax.set_title("Referral indications (ICD-10)", fontweight="bold")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    letter(ax, "c", x=-0.48)

    # d: age distribution
    ax = axes[1, 0]
    ages = demo["ages"]
    ax.hist(ages, bins=np.arange(0, 105, 5), color=g.PALETTE[1], edgecolor="white", alpha=0.85)
    ax.set_xlabel("Age at first EEG (years)")
    ax.set_ylabel("Number of patients")
    ax.set_title(f"Age at first EEG (n = {len(ages):,})", fontweight="bold")
    ax.axvline(np.median(ages), color="red", linestyle="--", alpha=0.7, label=f"Median {np.median(ages):.0f} years")
    ax.legend(fontsize=9)
    letter(ax, "d")

    # e: PDR frequency
    ax = axes[1, 1]
    pdr_vals = [v for v in (g.pdr_hz(r.get("pdr_frequency_hz", "")) for r in data.get("eeg_background", [])) if v is not None]
    ax.hist(pdr_vals, bins=np.arange(3.5, 14.5, 1), color=g.PALETTE[1], edgecolor="white", alpha=0.85)
    ax.set_xlabel("Posterior dominant rhythm (Hz)")
    ax.set_ylabel("Number of studies")
    ax.set_title(f"Posterior dominant rhythm (n = {len(pdr_vals):,})", fontweight="bold")
    ax.axvspan(8, 13, alpha=0.08, color="green", label="8-13 Hz")
    ax.legend(fontsize=9)
    letter(ax, "e")

    # f: IED morphology x distribution heatmap
    ax = axes[1, 2]
    epi = data.get("eeg_epileptiform", [])
    morph_labels = ["Spike", "Sharp wave", "Spike-wave", "Polyspike"]
    dist_labels = ["Generalized", "Focal", "Multifocal", "Bilateral"]
    morph_cols = ["is_spike", "is_sharp_wave", "is_spike_wave", "is_polyspike"]
    dist_cols = ["is_generalized", "is_focal", "is_multifocal", "is_bilateral"]
    grid = np.zeros((len(morph_labels), len(dist_labels)))
    for r in epi:
        for mi, mc in enumerate(morph_cols):
            if r.get(mc) == "1":
                for di, dc in enumerate(dist_cols):
                    if r.get(dc) == "1":
                        grid[mi, di] += 1
    im = ax.imshow(grid, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(dist_labels)))
    ax.set_xticklabels(dist_labels, fontsize=9, rotation=30, ha="right")
    ax.set_yticks(range(len(morph_labels)))
    ax.set_yticklabels(morph_labels, fontsize=9)
    for i in range(len(morph_labels)):
        for j in range(len(dist_labels)):
            v = int(grid[i, j])
            if v > 0:
                ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=8,
                        color="white" if v > grid.max() * 0.6 else "black")
    ax.set_title("Epileptiform discharge morphology by distribution", fontweight="bold")
    for s in ax.spines.values():
        s.set_visible(True)
    plt.colorbar(im, ax=ax, shrink=0.8, label="Number of studies")
    letter(ax, "f", x=-0.30)

    fig.tight_layout(w_pad=2.5, h_pad=2.5)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"Figure3.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Figure3 saved;  panel n:", len(durs), sum(counts), len(diag), len(ages), len(pdr_vals), int(grid.sum()))


def figure4_traces():
    d = np.load(tr.NPZ, allow_pickle=True)
    sr = int(d["sr"])
    normal = tr.bipolar(d["normal_data"], [str(x) for x in d["normal_channels"]], sr)
    spike = tr.bipolar(d["spike_data"], [str(x) for x in d["spike_channels"]], sr)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 7.5), sharey=True)
    tr.plot_panel(ax1, normal, sr, "Normal background", mark_spike=False)
    tr.plot_panel(ax2, spike, sr, "Interictal spike", mark_spike=True)
    ax2.set_title("Interictal spike", fontweight="bold", pad=22)   # keep the spike arrow clear of the title
    x0 = spike.shape[1] / sr - 1.15
    y0 = -(spike.shape[0] - 0.4) * tr.SPACING
    ax2.plot([x0, x0 + 1.0], [y0, y0], color=tr.DARK, lw=1.5, clip_on=False)
    ax2.plot([x0, x0], [y0, y0 + 100], color=tr.DARK, lw=1.5, clip_on=False)
    ax2.text(x0 + 0.5, y0 - 0.12 * tr.SPACING, "1 s", ha="center", va="top", fontsize=8)
    ax2.text(x0 - 0.06, y0 + 50, "100 µV", ha="right", va="center", fontsize=8)
    letter(ax1, "a", x=-0.10, y=1.01)
    letter(ax2, "b", x=-0.03, y=1.01)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"Figure4.{ext}", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  Figure4 saved")


def main():
    shutil.copy(MM / "figures" / "fig1.png", OUT / "Figure1.png")
    for ext in ("png", "pdf"):
        src = MM / "figures" / f"supp_figure2_deidentification.{ext}"
        if src.exists():
            shutil.copy(src, OUT / f"Figure2.{ext}")
    print("  Figure1, Figure2 copied")
    data = g.load_all()
    demo = g.compute_demographics()
    figure3_overview(data, demo)
    figure4_traces()


if __name__ == "__main__":
    main()
