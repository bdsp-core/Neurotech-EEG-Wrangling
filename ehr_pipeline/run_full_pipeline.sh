#!/bin/bash
# Post-sync re-run pipeline.
# Run this after sync_sftp.sh completes successfully.

set -uo pipefail
cd /Users/mwestover/GithubRepos/NeuroTech-Wrangling

echo "=== Stage 1: Extract text from new PDFs ==="
.venv/bin/python ehr_pipeline/extract_text.py --workers 6 --ocr-jobs 2

echo "=== Stage 2: Segment all packets ==="
.venv/bin/python ehr_pipeline/segment_documents.py

echo "=== Stage 3: Extract structured fields ==="
.venv/bin/python ehr_pipeline/extract_fields.py --concurrency 4

echo "=== Stage 4: Rebuild summary CSVs ==="
.venv/bin/python ehr_pipeline/build_csvs.py

echo "=== Stage 4.5: Extend linking table for EHR-only patients ==="
.venv/bin/python ehr_pipeline/extend_linking_table.py

echo "=== Stage 5: Update crosswalk (link to BDSP IDs) ==="
.venv/bin/python ehr_pipeline/build_crosswalk.py

echo "=== Stage 6: Re-run de-identification ==="
.venv/bin/python ehr_pipeline/deidentify_ehr.py

echo "=== Stage 6.6: Build committed de-identified aggregate tables ==="
# Produces output/ehr_deid_tables/*.csv — the ONLY EHR data committed to the repo
# and the single source of truth for every EHR number in the manuscript.
.venv/bin/python ehr_pipeline/build_deid_tables.py

echo "=== Stage 7: Regenerate paper tables and figures ==="
.venv/bin/python manuscript-materials/generate_tables_and_figures.py

echo "=== Stage 7.5: Fill manuscript placeholders ==="
.venv/bin/python manuscript-materials/fill_manuscript_placeholders.py

echo "=== Stage 8: Rebuild Word document ==="
.venv/bin/python manuscript-materials/md_to_docx.py

echo "=== ALL DONE ==="
