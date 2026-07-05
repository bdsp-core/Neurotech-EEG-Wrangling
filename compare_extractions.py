"""
Compare two de-identified extraction table sets (e.g. two extraction runs) on the
exact EHR numbers reported in the manuscript. Prints a side-by-side diff so we can see
whether the local model reproduces the released numbers (and whether anything needs
re-reconciling).

Usage:
  .venv/bin/python compare_extractions.py output/ehr_deid_tables_A output/ehr_deid_tables_B
"""
import re
import sys
import pandas as pd
from pathlib import Path


def _pdr_hz(s):
    s = str(s).strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(s)
    except ValueError:
        return None


def ehr_numbers(T: Path) -> dict:
    d = {}
    import glob
    docpats = set()
    for f in glob.glob(str(T / "*.csv")):
        c = pd.read_csv(f)
        if "bdsp_id" in c:
            docpats |= set(c.bdsp_id.dropna().astype(str))
    d["patients_with_docs"] = len({x for x in docpats if x and x != "nan"})
    dem = pd.read_csv(T / "demographics.csv")
    ages = pd.to_numeric(dem.age_years, errors="coerce").dropna()
    d["age_n"] = len(ages)
    d["age_median"] = round(ages.median(), 1)
    d["age_q1"], d["age_q3"] = round(ages.quantile(.25), 1), round(ages.quantile(.75), 1)
    sx = dem[dem.sex.isin(["M", "F"])].sex.value_counts()
    d["sex_n"] = int(sx.sum()); d["sex_M"] = int(sx.get("M", 0)); d["sex_F"] = int(sx.get("F", 0))
    d["studies"] = len(pd.read_csv(T / "studies.csv"))
    dc = pd.read_csv(T / "diagnosis_codes.csv", dtype=str).fillna("")
    code = dc["code"].astype(str).str.upper().str.strip()
    d["icd_total"] = len(dc)
    for lab, pat in [("G40", r"^G40"), ("R56", r"^R56"), ("R25", r"^R25")]:
        d[f"icd_{lab}"] = int(code.str.match(pat).sum())
    d["icd_other"] = d["icd_total"] - d["icd_G40"] - d["icd_R56"] - d["icd_R25"]
    for f, k in [("eeg_epileptiform.csv", "epileptiform"), ("eeg_seizures.csv", "seizures"),
                 ("eeg_slowing.csv", "slowing")]:
        d[k] = len(pd.read_csv(T / f)) if (T / f).exists() else 0
    imp = pd.read_csv(T / "technologist_impression.csv")
    cl = [c for c in imp.columns if "class" in c.lower()][0]
    vc = imp[cl].value_counts()
    d["impr_normal"] = int(vc.get("normal", 0)); d["impr_abnormal"] = int(vc.get("abnormal", 0))
    bg = pd.read_csv(T / "eeg_background.csv")
    fcol = [c for c in bg.columns if "freq" in c.lower()][0]
    f = pd.Series([_pdr_hz(x) for x in bg[fcol].dropna()]).dropna()
    d["pdr_n"] = len(f); d["pdr_median"] = round(f.median(), 1)
    d["pdr_normal"] = int(((f >= 8) & (f <= 13)).sum()); d["pdr_slow"] = int((f < 8).sum())
    d["monitoring"] = len(pd.read_csv(T / "monitoring_summary.csv"))
    for f, k in [("comorbidities.csv", "comorbidities"), ("medications.csv", "medications")]:
        d[k] = len(pd.read_csv(T / f)) if (T / f).exists() else 0
    return d


def main():
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    da, db = ehr_numbers(a), ehr_numbers(b)
    print(f"\n{'metric':28s} {'A: '+a.name:>24s} {'B: '+b.name:>24s}   delta")
    print("-" * 92)
    changed = 0
    for k in da:
        va, vb = da[k], db[k]
        same = va == vb
        if not same:
            changed += 1
        mark = "" if same else "  <-- CHANGED"
        print(f"{k:28s} {str(va):>24s} {str(vb):>24s}   {'' if same else str(vb-va) if isinstance(va,(int,float)) else '≠'}{mark}")
    print("-" * 92)
    print(f"{changed} of {len(da)} metrics differ between A and B.")
    if changed == 0:
        print("=> IDENTICAL: local extraction reproduces the released numbers exactly. No reconciliation needed.")


if __name__ == "__main__":
    main()
