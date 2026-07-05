#!/usr/bin/env python3
from __future__ import annotations
"""
Generate all tables and figures for the Neurotech EEG Dataset paper.

Revised figure sequence (post-review):
  Fig 1: Pipeline diagram (existing, not generated here)
  Fig 2: Dataset positioning — duration distribution + annotation categories +
         dataset comparison (promoted from supplement)
  Fig 3: Patient characteristics — referral indications + age distribution
  Fig 4: EEG findings — PDR distribution + IED heatmap + seizure capture rate

Supplementary figures:
  Supp Fig 1: Example EEG traces (moved from old Fig 2B)
  Supp Fig 2: De-identification (existing)
  Supp Fig 3: Comorbidities and anti-seizure medications
  Supp Fig 4: Monitoring characteristics

Tables:
  Table 1: Comparison with existing datasets (renumbered from old Table 2)
  Table 2: Patient and study characteristics (renumbered from old Table 1)

Usage:
  python manuscript-materials/generate_tables_and_figures.py
"""

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
# All EHR inputs are the COMMITTED, de-identified aggregate tables (no PHI, no
# /Volumes drive). Every figure and table is regenerable by any reader from the
# repo. See ehr_pipeline/build_deid_tables.py and reproduce_manuscript_numbers.py.
EHR_DIR = ROOT / "output" / "ehr_deid_tables"
OUTPUT_DIR = ROOT / "output"
TABLE_DIR = ROOT / "manuscript-materials" / "tables"
FIG_DIR = ROOT / "manuscript-materials" / "figures"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
    # Tufte: drop the top/right frame lines (chartjunk) and the box around legends.
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
})
PALETTE = ["#7c3aed", "#2563eb", "#16a34a", "#f59e0b", "#dc2626",
           "#06b6d4", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"]


def load_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pdr_hz(s: str):
    """Parse a pdr_frequency_hz cell: single value or range ('8-9' -> midpoint 8.5).

    Ranges are legitimate PDR extractions and must be counted; returns None only when
    the cell is truly unparseable. Same rule as reproduce_manuscript_numbers._pdr_hz.
    """
    s = str(s).strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(s)
    except ValueError:
        return None


def median_iqr(values: list[float]) -> str:
    if not values:
        return "N/A"
    # Linear-interpolation quantiles (numpy default) — matches reproduce_manuscript_numbers.py.
    arr = np.asarray(values, dtype=float)
    med, q1, q3 = np.median(arr), np.percentile(arr, 25), np.percentile(arr, 75)
    return f"{med:.1f} ({q1:.1f}-{q3:.1f})"


def parse_date(s: str) -> datetime | None:
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def normalize_sex(s: str) -> str | None:
    s = s.lower().strip()
    if s in ("m", "male", "boy"): return "Male"
    if s in ("f", "female", "girl", "adult female"): return "Female"
    if s and s not in ("na", "n/a", "", "hol", "pemal", "f. hohe"): return "Other"
    return None


ASM_NAMES = {"levetiracetam","keppra","lamotrigine","lamictal","valproate","depakote",
             "clobazam","onfi","lacosamide","vimpat","diazepam","zonisamide",
             "topiramate","topamax","carbamazepine","tegretol","oxcarbazepine",
             "trileptal","phenytoin","dilantin","phenobarbital","gabapentin",
             "neurontin","brivaracetam","briviact","perampanel","fycompa",
             "ethosuximide","zarontin","cenobamate","xcopri","vigabatrin",
             "felbamate","eslicarbazepine","cannabidiol","epidiolex",
             "rufinamide","primidone","pregabalin","lyrica","clonazepam","klonopin"}

BRAND_MAP = {
    "keppra": "levetiracetam", "lamictal": "lamotrigine",
    "vimpat": "lacosamide", "onfi": "clobazam", "topamax": "topiramate",
    "tegretol": "carbamazepine", "trileptal": "oxcarbazepine",
    "dilantin": "phenytoin", "neurontin": "gabapentin",
    "briviact": "brivaracetam", "fycompa": "perampanel",
    "epidiolex": "cannabidiol", "klonopin": "clonazepam",
    "lyrica": "pregabalin", "zarontin": "ethosuximide", "xcopri": "cenobamate",
}


# ---------------------------------------------------------------------------

def load_all():
    # Committed de-identified tables (ehr_deid_tables). "conditions" is aliased to
    # the committed comorbidities.csv (already normalized names).
    data = {}
    names = ["studies", "eeg_background", "eeg_slowing", "eeg_epileptiform",
             "eeg_seizures", "technologist_impression", "medications",
             "diagnosis_codes", "patient_events", "monitoring_summary",
             "monitoring_hour_of_day", "monitoring_event_counts"]
    for name in names:
        p = EHR_DIR / f"{name}.csv"
        data[name] = load_csv(p) if p.exists() else []
    p = EHR_DIR / "comorbidities.csv"
    data["conditions"] = load_csv(p) if p.exists() else []
    p = OUTPUT_DIR / "s3_recordings.csv"
    data["s3_recordings"] = load_csv(p) if p.exists() else []
    p = OUTPUT_DIR / "s3_annotation_categories.csv"
    data["s3_annotations"] = load_csv(p) if p.exists() else []
    return data


def compute_demographics() -> dict:
    """Read age + sex from the committed, de-identified demographics.csv.

    demographics.csv holds one row per linked patient with derived integer age
    (years at first EEG) and sex — no raw dates, no PHI. Ages/sex counts here
    match reproduce_manuscript_numbers.py exactly.
    """
    rows = load_csv(EHR_DIR / "demographics.csv") if (EHR_DIR / "demographics.csv").exists() else []
    ages, sex_counts = [], Counter()
    n_with_dob = n_with_sex = 0
    for r in rows:
        a = r.get("age_years", "")
        if a not in ("", None):
            try:
                av = float(a)
                if 0 < av < 120:
                    ages.append(av)
                    n_with_dob += 1
            except ValueError:
                pass
        s = r.get("sex", "")
        if s in ("M", "F"):
            sex_counts["Male" if s == "M" else "Female"] += 1
            n_with_sex += 1
    # unique patients with any clinical documentation = union of bdsp_id across all tables
    docpats = set()
    for name in ["studies", "diagnosis_codes", "eeg_background", "eeg_epileptiform",
                 "eeg_seizures", "eeg_slowing", "technologist_impression",
                 "monitoring_summary", "comorbidities", "medications",
                 "patient_events", "demographics"]:
        p = EHR_DIR / f"{name}.csv"
        if p.exists():
            for r in load_csv(p):
                b = r.get("bdsp_id", "")
                if b and b != "nan":
                    docpats.add(b)
    return {
        "n_with_dob": n_with_dob, "n_with_sex": n_with_sex,
        "ages": ages, "sex_counts": sex_counts,
        "n_unique_patients_ehr": len(docpats),
    }


# ---------------------------------------------------------------------------
# Table 2: Patient and study characteristics (trimmed per review)
# ---------------------------------------------------------------------------

def generate_table2(data: dict, demo: dict):
    rows = []
    s3 = data["s3_recordings"]
    s3_data = [r for r in s3 if int(r.get("n_records", 0) or 0) > 0]
    n_patients = len(set(r["subject"] for r in s3))
    n_recs = len(s3_data)
    durations = [float(r["duration_hours"]) for r in s3_data if r.get("duration_hours")]
    total_hours = sum(durations)
    rpc = Counter(r["subject"] for r in s3_data)
    multi = sum(1 for v in rpc.values() if v > 1)

    rows.append(("Patients", "", ""))
    rows.append(("  Unique patients", str(n_patients), ""))
    rows.append(("  With clinical documentation", str(demo["n_unique_patients_ehr"]),
                 f"({demo['n_unique_patients_ehr']/n_patients*100:.0f}%)"))
    if demo["ages"]:
        rows.append(("  Age at first EEG, median (IQR)", median_iqr(demo["ages"]), f"n={len(demo['ages'])}"))
    sex = demo["sex_counts"]
    n_sex = sum(sex.values())
    for s in ["Male", "Female"]:
        n = sex.get(s, 0)
        rows.append((f"  {s}", str(n), f"({n/n_sex*100:.0f}%)" if n_sex else ""))

    # Referral indications (top-line only, per reviewer)
    diag = data.get("diagnosis_codes", [])
    rows.append(("", "", ""))
    rows.append(("Referral indications (ICD-10)", "", f"n={len(diag)} codes"))
    for label, prefix in [("Epilepsy (G40.x)", "G40"), ("Convulsions (R56.x)", "R56"),
                          ("Abnormal movements (R25.x)", "R25"), ("Other", None)]:
        if prefix:
            n = sum(1 for r in diag if r.get("code", "").upper().startswith(prefix))
        else:
            # "Other" = everything except the three categories shown in this table,
            # matching reproduce_manuscript_numbers.py.
            known = sum(1 for r in diag if any(r.get("code","").upper().startswith(p) for p in ["G40","R56","R25"]))
            n = len(diag) - known
        rows.append((f"  {label}", str(n), f"({n/len(diag)*100:.0f}%)" if diag else ""))

    # EEG recordings
    rows.append(("", "", ""))
    rows.append(("EEG recordings", "", ""))
    rows.append(("  Total recordings with signal data", f"{n_recs:,}", ""))
    rows.append(("  Total recording hours", f"{total_hours:,.0f}", ""))
    rows.append(("  Duration, median (IQR)", median_iqr(durations), "hours"))
    rows.append(("  Recordings per patient, median (IQR)",
                 median_iqr([float(x) for x in rpc.values()]), ""))
    rows.append(("  Patients with multiple recordings", str(multi), f"({multi/n_patients*100:.0f}%)"))

    # EEG findings (concise)
    imp = data.get("technologist_impression", [])
    n_imp = len(imp)
    n_normal = sum(1 for r in imp if r.get("classification") == "normal")
    n_abnormal = sum(1 for r in imp if r.get("classification") == "abnormal")
    rows.append(("", "", ""))
    rows.append(("EEG findings (tech reports)", "", f"n={n_imp} studies"))
    rows.append(("  Normal", str(n_normal), f"({n_normal/n_imp*100:.0f}%)" if n_imp else ""))
    rows.append(("  Abnormal", str(n_abnormal), f"({n_abnormal/n_imp*100:.0f}%)" if n_imp else ""))
    rows.append(("  With epileptiform discharges", str(len(data.get("eeg_epileptiform", []))), ""))
    rows.append(("  With seizures captured", str(len(data.get("eeg_seizures", []))), ""))

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TABLE_DIR / "table2_patient_characteristics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Characteristic", "Value", "Notes"])
        w.writerows(rows)
    print(f"  Table 2: {len(rows)} rows")
    return rows


# ---------------------------------------------------------------------------
# Figure 2: Dataset positioning (3 panels)
# ---------------------------------------------------------------------------

def generate_figure2(data: dict):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    s3_data = [r for r in data["s3_recordings"] if int(r.get("n_records", 0) or 0) > 0]

    # A: Duration distribution
    ax = axes[0]
    durs = [float(r["duration_hours"]) for r in s3_data if r.get("duration_hours")]
    ax.hist(durs, bins=np.logspace(-2, 2, 50), color=PALETTE[1], edgecolor="white", alpha=0.85)
    ax.set_xscale("log")
    ax.set_xlabel("Recording duration (hours)")
    ax.set_ylabel("Number of recordings")
    ax.set_title("A. Recording duration", fontweight="bold")
    ax.axvline(1, color="gray", linestyle="--", alpha=0.5)
    ax.axvline(24, color="gray", linestyle="--", alpha=0.5)
    ax.text(0.3, ax.get_ylim()[1]*0.9, "Routine", fontsize=8, color="gray")
    ax.text(3, ax.get_ylim()[1]*0.9, "Ambulatory", fontsize=8, color="gray")
    ax.text(30, ax.get_ylim()[1]*0.9, "Prolonged", fontsize=8, color="gray")

    # B: Annotation categories (promoted from supplement)
    ax = axes[1]
    ann = data.get("s3_annotations", [])
    if ann:
        # Sort by count, take top 10
        ann_sorted = sorted(ann, key=lambda r: -int(r.get("count", 0)))[:10]
        labels = [r["category"].replace("_", " ").title() for r in ann_sorted]
        counts = [int(r["count"]) for r in ann_sorted]
        ax.barh(labels[::-1], counts[::-1], color=PALETTE[1])
        ax.set_xlabel("Number of events")
        ax.set_title("B. Annotation categories\n(226,486 total events)", fontweight="bold")
    else:
        ax.text(0.5, 0.5, "No annotation data", ha="center", va="center", transform=ax.transAxes)

    # C: Dataset comparison (promoted from supplement)
    ax = axes[2]
    datasets = [
        ("CHB-MIT", 23, 982),
        ("Bonn", 5, 0.6),
        ("Siena", 14, 128),
        ("TUH EEG", 15000, 25000),
        ("Neurotech\n(this work)", len(set(r["subject"] for r in s3_data)), sum(float(r.get("duration_hours",0)) for r in s3_data)),
    ]
    x = np.arange(len(datasets))
    w = 0.35
    names = [d[0] for d in datasets]
    patients = [d[1] for d in datasets]
    hours = [d[2] for d in datasets]
    bars1 = ax.bar(x - w/2, patients, w, label="Patients", color=PALETTE[1], alpha=0.85)
    bars2 = ax.bar(x + w/2, hours, w, label="Hours", color=PALETTE[3], alpha=0.85)
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("Patients or recording-hours (log scale)")
    ax.set_title("C. Comparison with\npublic EEG datasets", fontweight="bold")
    ax.legend(fontsize=9)

    plt.tight_layout()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / "figure2_dataset_positioning.png")
    fig.savefig(FIG_DIR / "figure2_dataset_positioning.pdf")
    plt.close(fig)
    print("  Figure 2: saved")


# ---------------------------------------------------------------------------
# Figure 3: Patient characteristics (2 panels — clean per review)
# ---------------------------------------------------------------------------

def generate_figure3(data: dict, demo: dict):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # A: Referral indications
    ax = axes[0]
    diag = data.get("diagnosis_codes", [])
    groups = {"Epilepsy\n(G40.x)": "G40", "Convulsions\n(R56.x)": "R56",
              "Altered awareness\n(R40.x)": "R40", "Syncope (R55)": "R55",
              "Abn. movements\n(R25.x)": "R25"}
    counts_a, labels_a = [], []
    for label, prefix in groups.items():
        n = sum(1 for r in diag if r.get("code","").upper().startswith(prefix))
        counts_a.append(n)
        labels_a.append(label)
    n_other = len(diag) - sum(counts_a)
    counts_a.append(n_other)
    labels_a.append("Other")
    # Single color: on a ranked bar chart, color must not encode anything.
    ax.barh(labels_a[::-1], counts_a[::-1], color=PALETTE[1])
    ax.set_xlabel("Number of diagnoses")
    ax.set_title("A. Referral indications (ICD-10)", fontweight="bold")

    # B: Age distribution
    ax = axes[1]
    ages = demo["ages"]
    if ages:
        ax.hist(ages, bins=np.arange(0, 105, 5), color=PALETTE[1], edgecolor="white", alpha=0.85)
        ax.set_xlabel("Age at first EEG (years)")
        ax.set_ylabel("Number of patients")
        ax.set_title(f"B. Age distribution (n={len(ages)})", fontweight="bold")
        ax.axvline(np.median(ages), color="red", linestyle="--", alpha=0.7,
                   label=f"Median: {np.median(ages):.0f} years")
        ax.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "figure3_patient_characteristics.png")
    fig.savefig(FIG_DIR / "figure3_patient_characteristics.pdf")
    plt.close(fig)
    print("  Figure 3: saved")


# ---------------------------------------------------------------------------
# Figure 4: EEG findings (3 panels — PDR + IED heatmap + seizure rate)
# ---------------------------------------------------------------------------

def generate_figure4(data: dict):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # A: PDR frequency distribution (moved from old Fig 3D)
    ax = axes[0]
    pdr_vals = []
    for r in data.get("eeg_background", []):
        v = pdr_hz(r.get("pdr_frequency_hz", ""))
        if v is not None:
            pdr_vals.append(v)
    if pdr_vals:
        ax.hist(pdr_vals, bins=np.arange(3.5, 14.5, 1), color=PALETTE[1],
                edgecolor="white", alpha=0.85)
        ax.set_xlabel("Posterior dominant rhythm (Hz)")
        ax.set_ylabel("Number of studies")
        ax.set_title("A. PDR frequency", fontweight="bold")
        ax.axvspan(8, 13, alpha=0.08, color="green", label="Normal range")
        ax.legend(fontsize=9)

    # B: IED morphology × distribution heatmap
    ax = axes[1]
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
                ax.text(j, i, str(v), ha="center", va="center", fontsize=8,
                        color="white" if v > grid.max() * 0.6 else "black")
    ax.set_title("B. IED morphology by distribution", fontweight="bold")
    for s in ax.spines.values():          # a heatmap reads better fully framed
        s.set_visible(True)
    plt.colorbar(im, ax=ax, shrink=0.7, label="Count")

    # C: Seizure capture rate
    ax = axes[2]
    n_studies = len(data.get("studies", []))
    n_with_sz = len(data.get("eeg_seizures", []))
    n_without = n_studies - n_with_sz
    bars = ax.bar(["No seizures", "Seizures\ncaptured"], [n_without, n_with_sz],
                  color=[PALETTE[1], PALETTE[3]])
    ax.set_ylabel("Number of studies")
    ax.set_title("C. Seizure capture rate", fontweight="bold")
    for i, v in enumerate([n_without, n_with_sz]):
        ax.text(i, v + 20, f"{v}\n({v/n_studies*100:.0f}%)", ha="center", fontsize=9)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "figure4_eeg_findings.png")
    fig.savefig(FIG_DIR / "figure4_eeg_findings.pdf")
    plt.close(fig)
    print("  Figure 4: saved")


# ---------------------------------------------------------------------------
# Supplementary Figure 3: Comorbidities + ASMs (moved from old Fig 3 B,C)
# ---------------------------------------------------------------------------

def generate_supp_fig3(data: dict):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # A: Comorbidities
    ax = axes[0]
    cond = data.get("conditions", [])
    cond_c = Counter()
    COND_ALIASES = {
        "htn": "hypertension", "high blood pressure": "hypertension",
        "hld": "hyperlipidemia", "dyslipidemia": "hyperlipidemia",
        "dm": "diabetes", "diabetes mellitus": "diabetes", "t2dm": "diabetes",
        "gerd": "gastroesophageal reflux", "cad": "coronary artery disease",
    }
    for r in cond:
        c = r["condition_name"].lower().strip()
        if "seizure" in c or "epilepsy" in c: continue
        c = COND_ALIASES.get(c, c)
        cond_c[c] += 1
    top = cond_c.most_common(10)
    ax.barh([c.title() for c,_ in top][::-1], [n for _,n in top][::-1], color=PALETTE[1])
    ax.set_xlabel("Count")
    ax.set_title("A. Top 10 comorbidities", fontweight="bold")

    # B: ASMs
    ax = axes[1]
    meds = data.get("medications", [])
    asm_c = Counter()
    for r in meds:
        n = r.get("name", "").lower().strip()
        if not any(a in n for a in ASM_NAMES): continue
        base = re.match(r"([a-z]+)", n)
        generic = BRAND_MAP.get(base.group(1), base.group(1)) if base else n
        asm_c[generic] += 1
    top_asm = asm_c.most_common(10)
    ax.barh([m.title() for m,_ in top_asm][::-1], [n for _,n in top_asm][::-1], color=PALETTE[1])
    ax.set_xlabel("Count")
    ax.set_title("B. Top 10 anti-seizure medications", fontweight="bold")

    plt.tight_layout()
    fig.savefig(FIG_DIR / "supp_figure3_comorbidities_meds.png")
    fig.savefig(FIG_DIR / "supp_figure3_comorbidities_meds.pdf")
    plt.close(fig)
    print("  Supp Figure 3: saved")


# ---------------------------------------------------------------------------
# Supplementary Figure 4: Monitoring (moved from old Fig 7)
# ---------------------------------------------------------------------------

def generate_supp_fig4(data: dict):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # A: Duration histogram
    ax = axes[0]
    ms = data.get("monitoring_summary", [])
    hrs = [int(r.get("n_hours_total", 0) or 0) for r in ms]
    hrs = [h for h in hrs if h > 0]
    if hrs:
        ax.hist(hrs, bins=range(0, max(hrs)+5, 4), color=PALETTE[1], edgecolor="white", alpha=0.85)
        ax.set_xlabel("Monitoring duration (hours)")
        ax.set_ylabel("Number of studies")
        ax.set_title("A. Monitoring duration", fontweight="bold")

    # B: Hour-of-day (from committed 24-row aggregate)
    ax = axes[1]
    hod = data.get("monitoring_hour_of_day", [])
    hour_counts = {int(r["hour"]): int(r["n_logged"]) for r in hod}
    hour_on = {int(r["hour"]): int(r["n_recording_on"]) for r in hod}
    if hour_counts:
        hours = list(range(24))
        totals = [hour_counts.get(h, 0) for h in hours]
        on = [hour_on.get(h, 0) for h in hours]
        ax.bar(hours, totals, color=PALETTE[1], alpha=0.3, label="Total logged")
        ax.bar(hours, on, color=PALETTE[1], alpha=0.85, label="Recording active")
        ax.set_xlabel("Hour of day")
        ax.set_ylabel("Count")
        ax.set_title("B. Recording by hour of day", fontweight="bold")
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], fontsize=8)
        ax.legend(fontsize=9)

    plt.tight_layout()
    fig.savefig(FIG_DIR / "supp_figure4_monitoring.png")
    fig.savefig(FIG_DIR / "supp_figure4_monitoring.pdf")
    plt.close(fig)
    print("  Supp Figure 4: saved")


# ---------------------------------------------------------------------------
# Table generation for supplementary tables 4 and 5 (same as before)
# ---------------------------------------------------------------------------

def generate_supp_tables(data: dict):
    # Supp Table 4: EEG findings detail
    rows = []
    bg = data.get("eeg_background", [])
    epi = data.get("eeg_epileptiform", [])
    n_studies = len(data.get("studies", []))

    pdr_values = []
    for r in bg:
        v = pdr_hz(r.get("pdr_frequency_hz", ""))
        if v is not None:
            pdr_values.append(v)

    rows.append(("Posterior dominant rhythm", "", ""))
    rows.append(("  PDR extractable", str(len(pdr_values)), f"of {n_studies} studies"))
    if pdr_values:
        rows.append(("  PDR frequency, median (IQR)", median_iqr(pdr_values), "Hz"))
        normal = sum(1 for v in pdr_values if 8 <= v <= 13)
        slow = sum(1 for v in pdr_values if v < 8)
        rows.append(("  Normal range (8-13 Hz)", str(normal), f"({normal/len(pdr_values)*100:.0f}%)"))
        rows.append(("  Slow (<8 Hz)", str(slow), f"({slow/len(pdr_values)*100:.0f}%)"))

    rows.append(("", "", ""))
    rows.append(("Interictal epileptiform discharges", str(len(epi)),
                 f"of {n_studies} studies ({len(epi)/n_studies*100:.0f}%)"))

    for section_label, cols in [
        ("Morphology", [("Spike", "is_spike"), ("Sharp wave", "is_sharp_wave"),
                        ("Spike-and-wave", "is_spike_wave"), ("Polyspike", "is_polyspike")]),
        ("Distribution", [("Generalized", "is_generalized"), ("Focal", "is_focal"),
                          ("Multifocal", "is_multifocal"), ("Bilateral independent", "is_bilateral_independent")]),
        ("Laterality", [("Left", "is_left"), ("Right", "is_right"), ("Bilateral", "is_bilateral")]),
        ("Region", [("Temporal", "is_temporal"), ("Frontal", "is_frontal"), ("Central", "is_central"),
                    ("Parietal", "is_parietal"), ("Occipital", "is_occipital")]),
    ]:
        rows.append((f"  {section_label}", "", ""))
        for label, col in cols:
            n = sum(1 for r in epi if r.get(col) == "1")
            rows.append((f"    {label}", str(n), ""))

    rows.append(("", "", ""))
    rows.append(("Abnormal slowing", str(len(data.get("eeg_slowing", []))),
                 f"of {n_studies} studies"))
    rows.append(("Electrographic seizures", str(len(data.get("eeg_seizures", []))),
                 f"of {n_studies} studies"))
    pe = data.get("patient_events", [])
    n_ts = sum(1 for r in pe if r.get("has_timestamp") == "1")
    rows.append(("Patient-reported events", str(len(pe)), ""))
    rows.append(("  With timestamp", str(n_ts),
                 f"({n_ts/len(pe)*100:.0f}%)" if pe else ""))

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    with open(TABLE_DIR / "supp_table4_eeg_findings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Finding", "Value", "Notes"])
        w.writerows(rows)
    print(f"  Supp Table 4: {len(rows)} rows")

    # Supp Table 5: Monitoring (from committed aggregates)
    ms = data.get("monitoring_summary", [])
    hod = data.get("monitoring_hour_of_day", [])
    evc = data.get("monitoring_event_counts", [])
    n_logged = sum(int(r["n_logged"]) for r in hod)
    n_on = sum(int(r["n_recording_on"]) for r in hod)
    evt_types = {r["event_type"]: int(r["n"]) for r in evc}
    n_events = sum(evt_types.values())
    rows2 = []
    rows2.append(("Studies with monitoring data", str(len(ms)), ""))
    rows2.append(("Total logged hours", f"{n_logged:,}", ""))
    rows2.append(("Hours recording active", f"{n_on:,}", f"({n_on/n_logged*100:.0f}%)" if n_logged else ""))
    days = [int(r.get("n_distinct_days", 0) or 0) for r in ms]
    if days:
        rows2.append(("Distinct days/study, median (IQR)", median_iqr([float(v) for v in days]), ""))
    rows2.append(("Monitoring events", f"{n_events:,}", ""))
    rows2.append(("  EEG reviewed", f"{evt_types.get('eeg_reviewed',0):,}", ""))
    rows2.append(("  General notes", f"{evt_types.get('general_note',0):,}", ""))
    rows2.append(("  Equipment failures", str(evt_types.get("equipment_failure", 0)), ""))

    with open(TABLE_DIR / "supp_table5_monitoring.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Metric", "Value", "Notes"])
        w.writerows(rows2)
    print(f"  Supp Table 5: {len(rows2)} rows")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading data...")
    data = load_all()
    for name, rows in data.items():
        if rows:
            print(f"  {name}: {len(rows):,}")

    print("\nComputing demographics...")
    demo = compute_demographics()
    print(f"  Ages: {len(demo['ages'])}, Sex: {sum(demo['sex_counts'].values())}")

    print("\nGenerating tables...")
    generate_table2(data, demo)
    generate_supp_tables(data)

    print("\nGenerating main figures...")
    generate_figure2(data)
    generate_figure3(data, demo)
    generate_figure4(data)

    print("\nGenerating supplementary figures...")
    generate_supp_fig3(data)
    generate_supp_fig4(data)

    print("\nDone!")


if __name__ == "__main__":
    main()
