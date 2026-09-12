# Scientific Data submission package — Neurotech EEG Dataset descriptor

Prepared 2026-09-12 from `NeuroTech-Wrangling/manuscript-materials/` (commit on `main`). Submit at
https://www.nature.com/sdata/ → "Submit manuscript" (Data Descriptor). The journal has no template; the
mandated headings are already in the article file.

## 1. Files in this folder and where each goes

| File | Submission slot | Notes |
|---|---|---|
| `Neurotech_EEG_Dataset_SciData.docx` | **Article file** (machine-readable copy; docx, not PDF) | Figures embedded at their legends; main text, tables, legends, references, end matter |
| `Neurotech_EEG_Dataset_SciData.pdf` | Article file (review copy) | Same content, for reviewers |
| `reviewer_data_access_note.docx` | **Article file, uploaded FIRST** so it sits in front of the paper | Fill the three `[INSERT …]` fields (sample URL, N subjects, size) after step 3 below, then export to PDF |
| `figures/Figure1.png` … `Figure4.png` | **Figure files**, one per figure | Panels merged, lower-case bold letters; PDFs of Figures 2-4 also included |
| `Human_Data_Checklist_FILLED.docx` | **Related Manuscript file** | Six boxes ticked and all answer boxes filled; **type the signature and date on the last page** before upload |
| `cover_letter.docx` / `.md` | Cover letter box | Contains no data-access instructions (journal rule) |

Fields entered in the submission system (copy from the article file, keep identical): Author Contributions,
Competing Interests (answer "Yes", paste the statement), Funding, Ethics (BIDMC IRB 2022P000417, waiver of consent).
APC: answer the payment questions in the system; waiver requests go there, not in the cover letter.

## 2. ONE remaining S3 command (Claude Code's safety classifier refuses deletes; credentials are fine)

The manuscript describes the release as it will be after this command. Run from the repo root on Brandon's Mac
(rclone remote `s3` is configured there). Idempotent.

```bash
cd /Users/mwestover/GithubRepos/NeuroTech-Wrangling
# remove the 32 sessions that have sidecars but no EDF (120 objects; versioned bucket, so reversible)
rclone delete s3:bdsp-opendata-repository/EEG/bids/Neurotech/ \
  --files-from manuscript-materials/scidata/s3_audit_2026-09-10/orphan_session_objects_to_delete.txt --no-traverse -v
# verify (participants.tsv was already uploaded with 4,912 rows on 2026-09-12)
rclone lsf -R s3:bdsp-opendata-repository/EEG/bids/Neurotech/sub-Neurotech934/ | wc -l                # 0
.venv/bin/python manuscript-materials/scidata/release_gate.py --downloads ~/Downloads/SciData_submission_2026-09-12
```

## 3. Reviewer access (required for a controlled-access dataset): temporary reviewer login on BDSP

Reviewers must reach the data instantly and without revealing their identity. Decision: provide a **temporary
reviewer account on bdsp.io** with pre-approved credentialing and the DUA accepted, whose username and password go
into `reviewer_data_access_note.docx` (uploaded as the first Article file). Steps for the BDSP admin (Brandon):

1. Register an account with a neutral address you control (e.g. a lab alias such as `eeg-reviewer@…`), using a
   non-identifying name such as "Scientific Data reviewer".
2. In the bdsp.io admin, mark that account's credentialing as approved and record the DUA as accepted, so the
   project's download options are immediately available to it.
3. Log in as that account once, open https://bdsp.io/content/nf89816gtxbon11kbr9a/1.0/, and confirm the file
   download works without any further request or approval step.
4. Paste the username, password, and the dataset URL into the `[INSERT …]` fields of the reviewer note, export it to
   PDF, and upload it in front of the article. Disable the account after publication.

Fallback if the platform cannot deliver instant downloads to that account: build the sample package
(`make_review_sample.py --zip`) and host it at an anonymous link (e.g. a Box shared link).

## 4. Open policy points (decisions, not tasks)

- **License field.** `dataset_description.json` on S3 says CC BY-NC 4.0; controlled access is governed by the DUA,
  but an editor may query the -NC tag.
- **bdsp.io listing page** still shows the old Natus/Xltek and ICU wording and the old counts; corrected text with
  the new numbers is in `manuscript-materials/bdsp_listing_draft.md` (needs the prod Django shell; host was
  unreachable from this machine). Fix before reviewers are invited. The DataCite record description also carries the
  old counts (optional refresh).
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
