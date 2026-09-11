#!/usr/bin/env python3
"""Format and consistency checks for the Scientific Data manuscript.

Checks the mandated Data Descriptor constraints against manuscript-scidata.md and,
when scratch output from reproduce_manuscript_numbers.py is supplied, that every
number the reproduction script prints appears in the manuscript text.

Run:  .venv/bin/python manuscript-materials/check_scidata.py [reproduce_output.txt]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MD = Path(__file__).resolve().parent / "manuscript-scidata.md"
t = MD.read_text()
ok = True


def report(cond: bool, msg: str):
    global ok
    print(("PASS " if cond else "FAIL ") + msg)
    ok &= cond


title = next(l[2:] for l in t.splitlines() if l.startswith("# "))
report(len(title) <= 110, f"title length {len(title)} <= 110")
report(":" not in title and "(" not in title, "title has no colon or parentheses")
report("Neurotech" not in title, "title has no dataset brand name")
report(not re.search(r"\b[A-Z]{2,}\b", title), "title has no acronyms")
report(not re.search(r"\b(novel|first|AI-ready|open)\b", title, re.I), "title has no advertising words")

abstract = t.split("## Abstract")[1].split("## Background")[0]
abstract = abstract.replace("---", "").strip()
n_abs = len(re.findall(r"\S+", abstract))
report(n_abs <= 170, f"abstract {n_abs} words <= 170")
report("http" not in abstract, "abstract has no URL")
report("**" not in abstract, "abstract has no sub-headings")

order = ["## Abstract", "## Background & Summary", "## Methods", "### Ethics", "## Data Records", "## Data Overview",
         "## Technical Validation", "## Usage Notes", "## Data Availability", "## Code Availability",
         "## Author Contributions", "## Competing Interests", "## Funding", "## References"]
pos = [t.find(h) for h in order]
report(all(p >= 0 for p in pos) and pos == sorted(pos), "mandated sections present and in order")
report(t.find("## Code Availability") < t.find("## References"), "Code Availability precedes References")

figs = sorted(set(int(n) for n in re.findall(r"\*\*Figure (\d+)\.\*\*", t)))
report(figs == [1, 2, 3, 4], f"figure legends {figs}")
for n in figs:
    first = min(m.start() for m in re.finditer(rf"Figure {n}\b", t))
    report(first < t.find("## Figure Legends"), f"Figure {n} is cited in the text before the legends")
tables = sorted(set(int(n) for n in re.findall(r"\*\*Table (\d+)\.", t)))
report(tables == [1, 2, 3], f"table captions {tables}")
report("Supplementary" not in t, "no supplementary material referenced")
report("^13^" in t.split("## Data Records")[1].split("## Data Overview")[0], "dataset data-citation cited in Data Records")
report("^13^" in t.split("## Data Availability")[1].split("## Code Availability")[0], "dataset data-citation cited in Data Availability")
refs = re.findall(r"^\d+\. ", t.split("## References")[1], re.M)
report(len(refs) == 13, f"{len(refs)} references")
cited = set(int(x) for grp in re.findall(r"\^([\d,\-]+)\^", t) for part in grp.split(",")
            for x in (range(int(part.split("-")[0]), int(part.split("-")[1]) + 1) if "-" in part else [int(part)]))
report(cited == set(range(1, 14)), f"every reference cited: {sorted(cited)}")
report(len(re.findall(r"\bNatus\b", t)) == 1 and "ICU" not in t.split("## Methods")[1].split("## Data Availability")[0],
       "no Natus/ICU wording outside the comparison table")
report("technician" not in t.lower(), "no 'technician' wording")
report("XXXX" not in t, "header placeholder kept as 'X X X X'")

if len(sys.argv) > 1 and Path(sys.argv[1]).exists():
    body = t.split("## References")[0]
    nums = set()
    for line in Path(sys.argv[1]).read_text().splitlines():
        for x in re.findall(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?![\w.])|(?<![\w.,])\d{4,}(?![\w.,])", line):
            nums.add(x)
    missing = sorted(n for n in nums if n not in body and n.replace(",", "") not in body)
    print(f"INFO reproduce script printed {len(nums)} large numbers; {len(missing)} not found in manuscript body: {missing[:40]}")

print("ALL PASS" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
