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

## Open items — decide before clicking Submit

1. **Reviewer access to the data (blocking).** BDSP registration reveals the reviewer's identity to the data owner and involves credentialing, so the journal requires a sample of the data at an anonymous, instant-download URL. `scidata/make_review_sample.py` builds a package (top-level files + phenotype tables + complete BIDS folders for a set of subjects). Decide where to host it (e.g. a public-read object in a BDSP-controlled bucket, or an institutional file share) and paste the URL into `reviewer_data_access_note.md`, then export that note to PDF. Nothing has been made public by this session.
2. **Pediatric data under a consent waiver (policy risk).** The cohort includes children. Scientific Data's human-data policy says consent waivers "cannot be used to share data for children or vulnerable adults". The Ethics section states the IRB waiver transparently. Precedent exists for pediatric clinical datasets under IRB waivers in the journal, but the current checklist wording is strict. Recommended: email scientificdata@nature.com before or at submission describing the IRB-approved waiver, HIPAA Safe Harbor de-identification, and DUA-controlled access, and ask whether this is acceptable. If they decline, Epilepsia Open is the fallback and needs no reformatting of the earlier Epilepsia version.
3. **DUA must be public.** Provide the URL of the BDSP data use agreement text (or attach a copy as a Related Manuscript file) in checklist Q5.
4. **License field.** `dataset_description.json` on S3 says `"License": "CC BY-NC 4.0"`. The journal does not accept -NC licences for open data; for controlled-access data the DUA governs, but an editor may query the field. Consider changing it to describe the DUA (one-file re-upload).
5. **bdsp.io listing page still says Natus/Xltek and ICU/EMU.** Reviewers will read it. The corrected text is in `manuscript-materials/bdsp_listing_draft.md`; applying it needs the prod Django shell (host 35.92.7.76, port 22 unreachable from this machine on 2026-09-10). Fix before reviewers are invited.
6. **Published sidecars.** All 54,346 `*_eeg.json` sidecars still say `Natus/Xltek`. `patch_s3_manufacturer.py` is tested (dry run reads correctly) but every S3 write from Claude Code, even one file, is blocked by the auto-mode permission classifier. Run it from a terminal: see `scidata/s3_audit_2026-09-10/README.md`, Fix 2.
6b. **Published tree is incomplete (full S3 listing, 2026-09-10).** 107 sessions listed in the recordings table were never uploaded (7 signal-bearing, 53 h; bucket versioning confirms no deletion), 31 sessions have sidecars but no EDF, and 8 sessions lacked a sidecar. The 10 missing sidecars are regenerated and staged (`scidata/s3_audit_2026-09-10/staged/`, Fix 1, one rclone command). The 107 sessions need the Padlock_DT source drive and the linking table (Fix 3). Restore before reviewers are invited; the journal checks the repository from the second review round. The manuscript numbers describe the complete built release.
7. **Neurotech confirmations still outstanding.** Exact equipment names and Persyst version, and the annotation-workflow description (asked in `email_to_keith_corrections.md`). The text says "Lifelines or EMS ambulatory EEG systems with Persyst spike and seizure detection software" and can be tightened later.
8. **APC.** An article processing charge applies; check the current rate on the journal site and answer the APC questions in the system (waiver requests go there, not in the cover letter).
