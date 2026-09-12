# Human Data Submission Checklist — answers to enter in `Scientific_Data_Human_Data_Checklist.docx`

Form: `manuscript-materials/Scientific_Data_Human_Data_Checklist.docx` (downloaded 2026-09-10 from nature.com/documents/sdata-sensitive-data-checklist.docx). Tick the boxes below, fill the text boxes, type a signature and date, and upload as a "Related Manuscript file".

## Q1 — How consent was obtained
Tick: **"Patients were not informed or did not provide consent for data sharing … but a third party has agreed this may be waived, and I have explained this in the Methods section of the paper."**

Note for the editors (put in the Q2 box or the cover email): the cohort spans all ages, including children. The BIDMC IRB granted a waiver of informed consent for this retrospective use of clinical data and approved release in de-identified form (HIPAA Safe Harbor) under a data use agreement. The journal's guidance says waivers should not be used for minors; we ask the editorial office to confirm acceptability (see SUBMISSION_CHECKLIST.md item 2).

## Q2 — Ethics approval
Tick: **Institutional ethics board or IRB.**
Box: "Beth Israel Deaconess Medical Center (BIDMC) Institutional Review Board, protocol 2022P000417. The IRB granted a waiver of informed consent and approved publication of the dataset in de-identified form with access restricted by a data use agreement prohibiting re-identification. Both details are stated in Methods → Ethics. A Business Associate Agreement between BIDMC and Neurotech governs the data transfer."

## Q3 — Category of data sharing
Tick: **Controlled access.** The DUA (BDSP data use agreement) is signed by every user; the access route and the reason for the restriction are described in Data Records and Usage Notes → Access procedure.

## Q4 — What the data contain
- Direct identifiers: **none.** Names, identifiers, dates of birth, case numbers, technologist and equipment identifiers were removed from EDF headers; names in annotation free text replaced with `[NAME]`; all dates shifted by a per-patient random offset.
- Tick **"Contains 3 or more indirect identifiers"**: age at first EEG (top-coded at 90), sex, date-shifted recording dates and times of day, and geographic scope (United States, single provider).
- Tick **"Contains sensitive or protected fields"**: health data — ICD-10 referral diagnoses, comorbid conditions, medications, technologist-reported EEG findings, and the EEG recordings themselves.

## Q5 — Where the DUA can be found
"The BDSP Credentialed Health Data Use Agreement is publicly viewable at https://bdsp.io/content/nf89816gtxbon11kbr9a/view-dua/1.0/ (license: https://bdsp.io/content/nf89816gtxbon11kbr9a/view-license/1.0/) and is presented to every user during registration." No attachment needed.

## Q6 — Practical controls and reviewer access
Tick: **"Manual application or registration process via the repository (beyond basic email validation)."**
Text: "Users register on bdsp.io with name, institution, and email, complete BDSP credentialing, and sign the data use agreement; access credentials for direct download are then issued. This is described in Usage Notes → Access procedure. For peer review, a representative sample of the release (top-level files, all phenotype tables, and complete BIDS directories for a set of subjects) is available for anonymous, immediate download at the URL given in the reviewer data-access note appended to the front of the article file."

## Q7 — Declaration
"I certify that all the above information is complete and correct." Typed signature: M. Brandon Westover. Date: [submission date].
