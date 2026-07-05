#!/usr/bin/env python3
"""
Supplementary Figure 1 — example EEG traces (bipolar montage).

Normal background (left) and an interictal spike (right), from a representative
de-identified recording already published in the BIDS dataset on S3.

Reproducible from the repo: reads the committed signal snippets in
  manuscript-materials/figure_data/eeg_snippets.npz
(19 monopolar 10-20 channels, 256 Hz, 5 s windows), rebuilds the standard
double-banana bipolar montage, band-passes 1-30 Hz + 60 Hz notch, and renders
the figure. No EDF / external drive required.

Run:  .venv/bin/python manuscript-materials/make_supp_figure1_eeg.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch

BASE = Path(__file__).resolve().parent
NPZ = BASE / "figure_data" / "eeg_snippets.npz"
FIG_DIR = BASE / "figures"

TRACE_COLOR = "#1a1a80"
ORANGE = "#d97706"
DARK = "#1f2937"
GRAY = "#6b7280"

# Mirror the unified figure style used by generate_tables_and_figures.py so this
# supplement matches the main figures' fonts and sizing exactly.
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
    "text.color": DARK,
    "axes.edgecolor": GRAY,
})

# Standard longitudinal bipolar (double-banana) montage
BIPOLAR = [
    "Fp1-F7", "F7-T3", "T3-T5", "T5-O1",       # left temporal
    "Fp2-F8", "F8-T4", "T4-T6", "T6-O2",       # right temporal
    "Fp1-F3", "F3-C3", "C3-P3", "P3-O1",       # left parasagittal
    "Fp2-F4", "F4-C4", "C4-P4", "P4-O2",       # right parasagittal
    "Fz-Cz", "Cz-Pz",                           # midline
]
SPACING = 150.0  # uV between traces


def bipolar(mono: np.ndarray, names: list[str], sr: int) -> np.ndarray:
    idx = {n: i for i, n in enumerate(names)}
    rows = []
    for pair in BIPOLAR:
        a, b = pair.split("-")
        rows.append(mono[idx[a]].astype(float) - mono[idx[b]].astype(float))
    data = np.asarray(rows)
    # band-pass 1-30 Hz then 60 Hz notch
    nyq = sr / 2.0
    bb, ab = butter(4, [1.0 / nyq, 30.0 / nyq], btype="band")
    data = filtfilt(bb, ab, data, axis=-1)
    bn, an = iirnotch(60.0, 30, sr)
    data = filtfilt(bn, an, data, axis=-1)
    return data


def plot_panel(ax, data: np.ndarray, sr: int, title: str, mark_spike: bool):
    n_ch, n_samp = data.shape
    t = np.arange(n_samp) / sr
    for i in range(n_ch):
        ax.plot(t, (data[i] - data[i].mean()) - i * SPACING,
                color=TRACE_COLOR, linewidth=0.5, zorder=2)
    ax.set_yticks([-i * SPACING for i in range(n_ch)])
    ax.set_yticklabels(BIPOLAR, fontsize=8, color=DARK)
    ax.set_xlim(0, t[-1])
    ax.set_ylim(-(n_ch - 0.5) * SPACING, 0.7 * SPACING)
    ax.set_title(title, fontweight="bold", pad=6)   # size from rcParams (axes.titlesize=12)
    ax.set_xlabel("Time (s)")                        # size from rcParams (axes.labelsize=11)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False)
    if mark_spike:
        # mark the point of largest synchronous deflection
        ts = t[np.argmax(np.abs(data - data.mean(axis=1, keepdims=True)).sum(0))]
        ax.axvline(ts, color=ORANGE, lw=0.6, ls=":", alpha=0.6, zorder=1)
        ax.annotate("", xy=(ts, 0.55 * SPACING), xytext=(ts, 0.55 * SPACING + 90),
                    arrowprops=dict(arrowstyle="-|>", color=ORANGE, lw=2), zorder=5)


def main() -> int:
    d = np.load(NPZ, allow_pickle=True)
    sr = int(d["sr"])
    normal = bipolar(d["normal_data"], [str(x) for x in d["normal_channels"]], sr)
    spike = bipolar(d["spike_data"], [str(x) for x in d["spike_channels"]], sr)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 7.5), sharey=True)
    plot_panel(ax1, normal, sr, "Normal background", mark_spike=False)
    plot_panel(ax2, spike, sr, "Interictal spike", mark_spike=True)

    # scale bar (100 uV, 1 s) at lower-right of the spike panel
    x0 = spike.shape[1] / sr - 1.15
    y0 = -(spike.shape[0] - 0.4) * SPACING
    ax2.plot([x0, x0 + 1.0], [y0, y0], color=DARK, lw=1.5, clip_on=False)
    ax2.plot([x0, x0], [y0, y0 + 100], color=DARK, lw=1.5, clip_on=False)
    ax2.text(x0 + 0.5, y0 - 0.12 * SPACING, "1 s", ha="center", va="top", fontsize=8)
    ax2.text(x0 - 0.06, y0 + 50, "100 µV", ha="right", va="center", fontsize=8)

    fig.suptitle("Example EEG traces (longitudinal bipolar montage)",
                 fontsize=13, fontweight="bold", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    FIG_DIR.mkdir(exist_ok=True)
    for ext in ("png", "pdf"):
        out = FIG_DIR / f"supp_figure1_eeg_example.{ext}"
        fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"  saved {out}")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
