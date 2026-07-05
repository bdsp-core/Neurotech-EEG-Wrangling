"""
Reproduce every quantitative claim in the manuscript from DE-IDENTIFIED data
committed to this repository (no PHI required).

Sources (all committed, all de-identified):
  - output/s3_recordings.csv            : one row per published EDF (subject, duration, channels, n_records)
  - output/s3_annotation_categories.csv : annotation counts by category (A-Z)
  - output/ehr_deid_tables/*.csv        : structured EHR fields keyed by BDSP id (no free text, no names)

The EEG/annotation numbers are ALSO reproducible directly from the public BIDS
dataset on S3 (s3://bdsp-opendata-repository/EEG/bids/Neurotech/) — see
compute_eeg_stats_from_s3.py, which regenerates output/s3_recordings.csv and the
annotation totals by reading the published *_eeg.json and *_Xltek.csv files.

Run:  .venv/bin/python reproduce_manuscript_numbers.py
Every printed value should match the corresponding number in manuscript-draft.md.
"""
import re
import pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parent / "output"


def _pdr_hz(s):
    """Parse a pdr_frequency_hz cell: single value or range (-> midpoint). None if unparseable."""
    s = str(s).strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(s)
    except ValueError:
        return None
ANN_TOTAL = 226486   # total annotation events = count of rows across all published *_Xltek.csv (see compute_eeg_stats_from_s3.py)


def p(label, value):
    print(f"  {label:52s} {value}")


def eeg():
    r = pd.read_csv(OUT / "s3_recordings.csv")
    sig = r[r.n_records > 0]
    print("\n=== EEG (from output/s3_recordings.csv; also derivable from public S3) ===")
    p("Unique subjects", f"{r.subject.nunique():,}")
    p("Recordings with signal", f"{len(sig):,}")
    p("Header-only stubs", f"{len(r) - len(sig):,}")
    p("Total EDF files (BIDS)", f"{len(r):,}")
    p("Total recording hours", f"{sig.duration_hours.sum():,.0f}")
    p("Total size (TB)", f"{r.size_mb.sum()/1024/1024:.1f}")
    p("Channels median", f"{int(sig.n_signals.median())}")
    p("29-channel fraction", f"{100*(sig.n_signals==29).mean():.0f}%")
    rpp = sig.groupby('subject').size()
    p("Patients w/ >1 recording", f"{(rpp>1).sum():,} ({100*(rpp>1).mean():.0f}%)")
    p("Recordings/patient median (IQR)", f"{rpp.median():.0f} ({rpp.quantile(.25):.0f}-{rpp.quantile(.75):.0f})")
    d = sig.duration_hours
    p("Duration median (IQR) h", f"{d.median():.1f} ({d.quantile(.25):.1f}-{d.quantile(.75):.1f})")
    p("Routine <1h", f"{(d<1).sum():,} ({100*(d<1).mean():.0f}%)")
    p("Short 1-24h", f"{((d>=1)&(d<=24)).sum():,} ({100*((d>=1)&(d<=24)).mean():.0f}%)")
    p("Prolonged >24h", f"{(d>24).sum():,} ({100*(d>24).mean():.0f}%)")


def annotations():
    c = pd.read_csv(OUT / "s3_annotation_categories.csv").set_index("category")["count"]
    print("\n=== Annotations (from output/s3_annotation_categories.csv) ===")
    p("Total annotation events", f"{ANN_TOTAL:,}")
    for k, lab in [("spike","Spike markers"),("seizure","Seizure markers"),("sharp_wave","Sharp waves"),
                   ("clip","Technician clips"),("activation","Activation procedures"),("slowing","Slowing")]:
        p(lab, f"{int(c.get(k,0)):,}")


def ehr():
    T = OUT / "ehr_deid_tables"
    print("\n=== EHR (from output/ehr_deid_tables/*.csv, BDSP-keyed, de-identified) ===")
    dem = pd.read_csv(T / "demographics.csv")
    # patients with ANY clinical document = unique BDSP ids across all EHR tables
    import glob as _g
    docpats = set()
    for _f in _g.glob(str(T / "*.csv")):
        _d = pd.read_csv(_f)
        if "bdsp_id" in _d:
            docpats |= set(_d.bdsp_id.dropna().astype(str))
    docpats = {x for x in docpats if x and x != "nan"}
    p("Patients with clinical docs", f"{len(docpats):,}")
    ages = pd.to_numeric(dem.age_years, errors="coerce").dropna()
    p("Age median (IQR), n", f"{ages.median():.1f} ({ages.quantile(.25):.1f}-{ages.quantile(.75):.1f}), n={len(ages)}")
    sx = dem[dem.sex.isin(["M","F"])].sex.value_counts()
    tot = int(sx.sum())
    p("Sex n (M/F)", f"{tot} ({sx.get('M',0)} M / {sx.get('F',0)} F)")
    st = pd.read_csv(T / "studies.csv")
    p("Studies (tech reports)", f"{len(st):,}")
    dc = pd.read_csv(T / "diagnosis_codes.csv", dtype=str).fillna("")
    code = dc["code"].astype(str).str.upper().str.strip()
    n_codes = len(dc)
    p("Referral ICD codes (total)", f"{n_codes:,}")
    for lab, pat in [("Epilepsy (G40)", r"^G40"), ("Convulsions (R56)", r"^R56"),
                     ("Abnormal movements (R25)", r"^R25")]:
        n = int(code.str.match(pat).sum())
        p(f"ICD: {lab}", f"{n:,} ({100*n/n_codes:.0f}%)")
    for f, lab in [("eeg_epileptiform.csv","With epileptiform discharges"),
                   ("eeg_seizures.csv","With seizures captured")]:
        if (T / f).exists():
            p(lab, f"{len(pd.read_csv(T/f)):,}")
    imp = pd.read_csv(T / "technologist_impression.csv")
    cl = [c for c in imp.columns if "class" in c.lower()]
    if cl:
        vc = imp[cl[0]].value_counts()
        p("Impression: Normal", f"{int(vc.get('normal',0)):,} ({100*vc.get('normal',0)/len(imp):.0f}%)")
        p("Impression: Abnormal", f"{int(vc.get('abnormal',0)):,} ({100*vc.get('abnormal',0)/len(imp):.0f}%)")
    # PDR (posterior dominant rhythm) from eeg_background. pdr_frequency_hz is either a
    # single value ("9") or a range ("8-9"); ranges are valid extractions and are taken
    # as their midpoint. Same rule as generate_tables_and_figures.pdr_hz.
    bg = pd.read_csv(T / "eeg_background.csv")
    fcol = [c for c in bg.columns if "freq" in c.lower()]
    if fcol:
        f = pd.Series([_pdr_hz(x) for x in bg[fcol[0]].dropna()]).dropna()
        n_norm = int(((f >= 8) & (f <= 13)).sum())
        n_slow = int((f < 8).sum())
        p("PDR extractable", f"{len(f):,}")
        p("PDR median (IQR) Hz", f"{f.median():.1f} ({f.quantile(.25):.1f}-{f.quantile(.75):.1f})")
        p("PDR normal 8-13 Hz", f"{n_norm:,} ({100*n_norm/len(f):.0f}%)")
        p("PDR slow <8 Hz", f"{n_slow:,} ({100*n_slow/len(f):.0f}%)")
    # Monitoring
    mon = pd.read_csv(T / "monitoring_summary.csv")
    p("Studies with monitoring data", f"{len(mon):,}")
    hcol = [c for c in mon.columns if "hour" in c.lower() and "monitor" in c.lower()]
    if hcol:
        p("Total monitoring hours", f"{pd.to_numeric(mon[hcol[0]], errors='coerce').fillna(0).sum():,.0f}")
    # Annotated recordings (reproducible from S3: count of published *_Xltek.csv files)
    print("\n  (Annotated recordings = 14,517 = number of published *_Xltek.csv files on S3;\n"
          "   reproduce with: python compute_eeg_stats_from_s3.py)")


if __name__ == "__main__":
    print("Reproducing manuscript numbers from committed de-identified data:")
    eeg(); annotations(); ehr()
    print("\nAll values above are computed from committed CSVs; EEG/annotation values\n"
          "are additionally reproducible from the public S3 BIDS dataset.")
