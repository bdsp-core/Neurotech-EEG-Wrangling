# Scientific Data submission package — Neurotech EEG Dataset descriptor

Prepared 2026-09-12 from `NeuroTech-Wrangling/manuscript-materials/` (commit on `main`). Submit at
https://www.nature.com/sdata/ → "Submit manuscript" (Data Descriptor). The journal has no template; the
mandated headings are already in the article file.

## 1. Files in this folder and where each goes

| File | Submission slot | Notes |
|---|---|---|
| `Neurotech_EEG_Dataset_SciData.docx` | **Article file** (machine-readable copy; docx, not PDF) | Figures embedded at their legends; main text, tables, legends, references, end matter |
| `Neurotech_EEG_Dataset_SciData.pdf` | Article file (review copy) | Same content, for reviewers |
| `reviewer_data_access_note.docx` | **Article file, uploaded FIRST** so it sits in front of the paper | Fill the `[INSERT USERNAME]` / `[INSERT PASSWORD]` fields after §3, then export to PDF |
| `figures/Figure1.png` … `Figure4.png` | **Figure files**, one per figure | Panels merged, lower-case bold letters; PDFs of Figures 2-4 also included |
| `Human_Data_Checklist_FILLED.docx` | **Related Manuscript file** | Six boxes ticked and all answer boxes filled; **type the signature and date on the last page** before upload |
| `cover_letter.docx` / `.md` | Cover letter box | Contains no data-access instructions (journal rule) |

Fields entered in the submission system (copy from the article file, keep identical): Author Contributions,
Competing Interests (answer "Yes", paste the statement), Funding, Ethics (BIDMC IRB 2022P000417, waiver of consent).
APC: answer the payment questions in the system; waiver requests go there, not in the cover letter.

## 2. S3 release: done

Orphan sessions deleted and `participants.tsv` (4,912 rows) uploaded on 2026-09-12; all 54,346 sidecars say
`Lifelines/EMS`. `release_gate.py` verifies the live state and reports READY:

```bash
cd /Users/mwestover/GithubRepos/NeuroTech-Wrangling
.venv/bin/python manuscript-materials/scidata/release_gate.py --downloads ~/Downloads/SciData_submission_2026-09-12
```

## 3. Reviewer access (required for a controlled-access dataset): temporary reviewer login on BDSP

Reviewers must reach the data instantly and without revealing their identity. Decision: a **temporary reviewer
account on bdsp.io**, pre-credentialed with the DUA signed and the required training recorded, whose username and
password go into `reviewer_data_access_note.docx` (uploaded as the first Article file).

The provisioning script and the production connection steps are kept only in the private submission package
(`~/Downloads/SciData_submission_2026-09-12/README_SUBMISSION.md` §3), not in this public repository. The script
mirrors exactly what `PublishedProject.has_access()` checks: active + credentialed + DUA signature for this project +
accepted training for every training type the project requires. After running it: log in as the account in a private
window, confirm a file downloads from the dataset page with no further step, paste the credentials into
`reviewer_data_access_note.docx`, export to PDF, upload it in front of the article; disable the account after
publication.

Bulk access for reviewers who want the whole 10 TB: a logged-in credentialed user can enter a 12-digit AWS account
ID under Account → Cloud settings and the platform adds it to the S3 bucket policy automatically (no admin step),
after which `aws s3 sync s3://bdsp-opendata-repository/EEG/bids/Neurotech/ .` works. The note mentions this.

Fallback if step 1 shows no browser download for this S3-backed project: build the sample package
(`make_review_sample.py --zip`) and host it at an anonymous link (e.g. a Box shared link), and put that link in the
note instead of the login.

## 4. Open points

- **License field.** `dataset_description.json` on S3 says CC BY-NC 4.0; controlled access is governed by the DUA,
  but an editor may query the -NC tag.
- **bdsp.io listing page** still shows the old Natus/Xltek and ICU wording and the July counts; corrected text with
  the new numbers is in `manuscript-materials/bdsp_listing_draft.md` (apply via the prod Django shell, same host as
  §3). Fix before reviewers are invited. The DataCite record description also carries the old counts (optional).
- **Neurotech confirmations** (exact equipment names / Persyst version; annotation workflow) are still outstanding;
  the text is worded to be correct without them.

## 5. What changed on 2026-09-12 and why

A full listing of the S3 release found 107 sessions that were never uploaded in July (7 signal-bearing) and 31
sessions with sidecars but no EDF. The source drive is not available and Neurotech cannot re-export, so the
manuscript now describes the release as published: 4,912 patients, 23,600 signal-bearing segments, 212,133 h,
225,957 annotations in 14,491 annotation files. Annotation totals were recomputed from the published files with the
repository's own classifier (the earlier figures came from a line count and a non-committed classifier). Details:
`manuscript-materials/scidata/s3_audit_2026-09-10/README.md`. All numbers are regenerated by
`reproduce_manuscript_numbers.py` and gated by `release_gate.py`.
