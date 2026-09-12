# Scientific Data submission — checklist and open items

Target: *Scientific Data*, Data Descriptor. Submit at https://www.nature.com/sdata/ → Submit manuscript.
Source of truth for the text: `manuscript-materials/manuscript-scidata.md` → `md_to_docx_scidata.py` → `scidata/Neurotech_EEG_Dataset_SciData.docx` (+ `.pdf`).
Figures: `make_scidata_figures.py` → `scidata/figures/Figure1..4.png` (+ `.pdf`).

## Files to upload

| Item | File | Submission-system slot |
|---|---|---|
| Main article, machine-readable | `scidata/Neurotech_EEG_Dataset_SciData.docx` | Article file (docx; no PDF for this slot) |
| Review PDF (figures embedded) | `scidata/Neurotech_EEG_Dataset_SciData.pdf` | Article file (optional; the docx already embeds figures) |
| Figures, one file each | `scidata/figures/Figure1.png` … `Figure4.png` | Figure files (panels merged; lower-case bold a, b… labels) |
| Human Data Checklist, signed | `manuscript-materials/Scientific_Data_Human_Data_Checklist.docx` (answers in `scidata/human_data_checklist_answers.md`) | Related Manuscript file |
| Reviewer data-access note | `scidata/reviewer_data_access_note.md` → PDF | Article file, appended to the **front** of the paper (the checklist asks for this for controlled-access data) |
| Cover letter | `scidata/cover_letter.md` | Cover letter box (must NOT contain data-access instructions) |
| Data Use Agreement copy | (obtain from bdsp.io) | Related Manuscript file, only if the DUA is not publicly linked |

Entered in the submission system rather than the file: author contributions, competing interests (answer "Yes" and paste the statement), funding, ethics. The file also carries them; keep both identical.

No supplementary information. All former supplementary figures and tables were folded into the main text or dropped (Data Descriptors may not carry summary statistics beyond a short Data Overview).

## Format compliance (verified by `check_scidata.py`)

- Title ≤ 110 characters, no colon, no dataset brand name, no acronyms.
- Abstract ≤ 170 words, unstructured, no URLs.
- Sections in mandated order: Abstract, Background & Summary, Methods (with Ethics sub-heading), Data Records, Data Overview, Technical Validation, Usage Notes, Data Availability, Code Availability, Author Contributions, Competing Interests, Funding, References.
- Data citation (ref. 13) reflects the DataCite record exactly (title and 8 creators as registered on bdsp.io).
- Nature reference style with DOIs; all 10 journal DOIs verified against Crossref on 2026-09-10.
- 4 figures (≤ 8 recommended), 3 tables (≤ 10), sans-serif figure fonts, lower-case panel letters.

## Open items — decide before clicking Submit (see README_SUBMISSION.md for the exact commands)

1. **Reviewer access to the data (blocking).** Temporary reviewer login on bdsp.io with pre-approved credentialing (README_SUBMISSION.md §3); credentials go into `reviewer_data_access_note.docx`, exported to PDF and uploaded as the first Article file.
2. **S3 release: DONE 2026-09-12.** Orphan sessions deleted (Brandon), `participants.tsv` uploaded (4,912 rows); `release_gate.py` verifies the live state.
3. **DUA: DONE.** The agreement is public at https://bdsp.io/content/nf89816gtxbon11kbr9a/view-dua/1.0/ and cited in the checklist and manuscript; no attachment.
5. **License field.** `dataset_description.json` on S3 says CC BY-NC 4.0; an editor may query the -NC tag.
6. **bdsp.io listing page** still shows Natus/Xltek, ICU wording and the July counts; corrected text in `manuscript-materials/bdsp_listing_draft.md` (prod shell needed). DataCite description: optional refresh.
7. **Neurotech confirmations still outstanding** (equipment names / Persyst version; annotation workflow). Text is worded to be correct without them.
8. **APC.** Answer the payment questions in the system.

## Done
- 2026-09-11: all 54,346 sidecars say `Lifelines/EMS`; 10 missing sidecars regenerated and uploaded.
- 2026-09-12: published-state numbers adopted (4,912 / 23,600 / 212,133 h / 225,957 annotations in 14,491 files); recordings table, annotation tables, Figure 1 artwork, Figure 3, Tables 2-3, legends, cover letter and listing draft updated; Human Data Checklist filled; package staged in ~/Downloads/SciData_submission_2026-09-12/.
