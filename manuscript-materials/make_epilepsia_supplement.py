#!/usr/bin/env python3
"""Render manuscript-epilepsia-supplement.md to a submission-shaped supplementary
Word document (double-spaced, line-numbered), embedding Supp Figures 1-4.
Reuses the Epilepsia renderer.

Run:  .venv/bin/python manuscript-materials/make_epilepsia_supplement.py
"""
import sys
from pathlib import Path
from docx import Document

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import md_to_docx_epilepsia as e

MD = BASE / "manuscript-epilepsia-supplement.md"
OUT = BASE / "Neurotech_EEG_Dataset_Epilepsia_Supplement.docx"


def main():
    doc = Document()
    e.set_double_spacing(doc)
    e.render_body(doc, MD.read_text())
    e.add_line_numbers(doc)
    doc.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
