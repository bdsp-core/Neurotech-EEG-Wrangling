"""
Fix the abnormality free-text fields (seizures/slowing/epileptiform) that bleed
past their section into following report sections or appended clinical notes.

Root cause: the tech-report `_extract_between` runs to end-of-document when its
section-ending markers don't appear (packets concatenate the tech report with
H&P / progress notes). We truncate each field at the first following
section/document header, with a high length backstop for pathological cases.

Usage:
  python ehr_pipeline/clean_findings.py --dry-run   # report, write nothing
  python ehr_pipeline/clean_findings.py             # patch *.fields.json in place
"""
import re, glob, json, sys
from pathlib import Path

SSD = Path("/Volumes/Extreme SSD/neurotech-data")
FIELDS = ("seizures", "slowing", "epileptiform_discharges")
CAP = 3000  # backstop; boundary markers do the real work

# Headers that mark the END of an abnormality free-text field (start of the next
# tech-report section OR an appended clinical document). Case-insensitive.
_BOUND = re.compile(
    r"(?i)(?:^|\s)(?:"
    r"HYPERVENTILATION|PHOTIC\s+STIMULATION|ACTIVATION\s+PROCEDURES?|"
    r"TECHNOLOGIST\s+IMPRESSION|SCANNING\s+TECHNOLOGIST|Technical\s+Description|"
    r"Technologist\s+Scan\s+Report|Brief\s+History|History\s+of\s+Present|"
    r"DIAGNOSTIC\s+TESTING|Seizure\s+Action\s+Plan|REASON\s+FOR\s+STUDY|"
    r"INDICATION\s*:|Patient\s+Name\s*:|Assessment\s+and\s+Plan|"
    r"CHIEF\s+COMPLAINT|Reviewed\s+with\s+(?:family|patient)"
    r")\b"
)


def clean_finding(s):
    if not s or not isinstance(s, str):
        return s
    m = _BOUND.search(s)
    if m and m.start() > 0:
        s = s[:m.start()]
    s = s.strip()
    if len(s) > CAP:
        s = s[:CAP].rstrip()
    return s


def main():
    dry = "--dry-run" in sys.argv
    files = glob.glob(str(SSD / "**" / "*.fields.json"), recursive=True)
    changed = 0
    before_max = after_max = 0
    for fp in files:
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        recs = data.get("section_records", []) if isinstance(data, dict) else []
        touched = False
        for r in recs:
            if not isinstance(r, dict):
                continue
            f = r.get("fields")
            if not isinstance(f, dict):
                continue
            for key in FIELDS:
                v = f.get(key)
                if isinstance(v, str) and v:
                    before_max = max(before_max, len(v))
                    nv = clean_finding(v)
                    if nv != v:
                        f[key] = nv
                        touched = True
                    after_max = max(after_max, len(nv) if isinstance(nv, str) else 0)
        if touched:
            changed += 1
            if not dry:
                json.dump(data, open(fp, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{'DRY-RUN ' if dry else ''}files scanned={len(files)} changed={changed} "
          f"| max field len before={before_max} after={after_max}")


if __name__ == "__main__":
    main()
