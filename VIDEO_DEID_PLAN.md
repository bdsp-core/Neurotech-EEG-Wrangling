# Phase 5 — Video De-identification Plan (synthetic-face, semiology-preserving)

_Written 2026-06-30, revised after PI direction. Goal: turn the EMU `.asf` video-EEG on the final-batch drive into a **de-identified, semiology-preserving video derivative** (real face → synthetic face; background/bystanders removed; audio stripped) for release under the **credentialed-access + DUA** model used for the rest of the dataset. PI reviews samples before any upload. Optionally also publish quantitative pose/keypoint data._

---

## 0. Governance model (sets the whole bar)
This dataset is **not** an open/public release — it is **credentialed access via bdsp.io under a Data Use Agreement that prohibits re-identification**, under IRB protocol 2022P000417 (which already approved de-identified release gated by a DUA). That governance is the control.

**Implication (per PI):** we do **NOT** need motion-anonymization (PMR), adversarial re-identification testing, or a formal HIPAA Expert Determination for residual gait/motion cues. Those are requirements for *open* release; under credentialed access + DUA they're unnecessary. We focus on removing the obvious direct identifiers (face, audio, on-screen text, bystanders, room) and on **PI review before upload**.

---

## 1. What we publish
1. **De-identified video** (primary): the patient's body and movements preserved, **real face replaced by a synthetic face that preserves expression/orientation** (so seizure semiology — eye deviation, oral/peri-oral movements, facial emotion — survives). Background and any other people removed/blurred; audio stripped; burned-in timestamps masked and date-shifted.
2. **(Optional) Pose/keypoint time series** as a BIDS derivative (`derivatives/motion/`) for quantitative ML — cheap to add on top of the same person-tracking, and useful for movement analysis.

Both align to the EEG session clock with the patient's existing `shift_days`.

## 2. Why synthetic face (not skeleton-only, not eye-bars)
Verified clinical points:
- **Facial features carry localizing value** — eye deviation, oral/peri-oral movements, bilateral tonic facial contraction, and emotional expression (fear/mirth/disgust) help localize the epileptogenic zone.
- **Conventional eye-bar masking destroys** eye-deviation semiology; **pure skeleton discards all facial signal** and is noisy/occlusion-vulnerable.
- **Synthetic face-swap preserves semiology while removing identity** — validated on real EMU seizure clips (Mayo Clinic Proc Digital Health 2023, testing SimSwap / MobileFaceSwap / GHOST with objective facial-action + subjective semiology scoring). **GANonymization** is purpose-built to retain emotional expression and outperforms **DeepPrivacy2** (which does NOT guarantee face orientation/expression — so avoid DeepPrivacy2 for this use).

## 3. Recommended toolchain (open-source, on-prem)
Process on-premises / in a HIPAA-eligible environment; raw PHI-bearing video never leaves controlled storage.

| Stage | Recommended | Notes (verified) |
|---|---|---|
| Demux / audio | `ffmpeg -an` | strip `.wav`/embedded audio (voices, names) |
| Burned-in timestamp | OCR-detect → crop/mask region | dates are PHI; capture true time, date-shift to match EEG |
| Person + background | **SAM2** via **SAMannot** (MIT, local, sliding-window ~2.3–2.9 GiB VRAM, hours-long; +Kalman to survive occlusion) | segment the patient; blur/replace background; **remove/blur any other person** (caregivers, family) |
| **Face replacement** | **Face-swap (SimSwap / GHOST / MobileFaceSwap)** or **GANonymization** — semiology-preserving | the core de-id step; preserves expression/orientation. Detect+track face across frames (works under partial occlusion) |
| Fallback | where face can't be reliably swapped (severe occlusion/odd pose) → mask that region **and flag the clip for PI review** | off-the-shelf face/pose models can fail on seizing patients; never trust a frame silently |
| (Optional) keypoints | **ViTPose** (EMU-fine-tuned) → **MotionBERT** 3D / **SMPLer-X** / **4D-Humans** | off-the-shelf pose fails on seizing/occluded patients → fine-tune on EMU frames |

## 4. Pipeline architecture (per patient)
```
for each .asf/.avi hourly segment:
  1. ffmpeg demux, drop audio (-an); record true start time; date-shift with patient's shift_days
  2. OCR-detect + mask burned-in timestamp/overlay
  3. SAM2/SAMannot: segment patient; blur/replace background; remove/blur any OTHER people
  4. detect+track patient face → SYNTHETIC FACE SWAP (semiology-preserving)
  5. (optional) ViTPose→MotionBERT keypoints on the tracked patient
  6. re-render de-identified video (synthetic face, clean background, no audio, shifted timestamps)
  7. auto-QC: face swapped on every detected-face frame? any leak frames? bystanders gone? audio absent? timestamps shifted?
  8. >>> PI REVIEW GATE: Westover reviews sampled clips (esp. flagged ones) and confirms de-id sufficient <<<
package → released under credentialed access:
  derivatives/video/sub-Neurotech<N>/ses-<M>/   (de-identified video)
  derivatives/motion/sub-Neurotech<N>/ses-<M>/  (optional keypoints .tsv/.json)
```

## 5. Validation & QC
- **Automated**: confirm synthetic face on every frame with a detected face; flag any frame where face detection dropped while a person is present (potential leak); confirm audio removed, no second person, timestamps shifted.
- **PI human review** (the gate): sample clips across patients + all auto-flagged clips; PI signs off before upload. This replaces the open-release adversarial/Expert-Determination machinery.
- **Clinical fidelity spot-check**: confirm semiology (eye/face movements) is visibly preserved post-swap.

## 6. Governance checklist (credentialed model)
- **DUA** with explicit no-re-identification clause (already in place for the dataset) — extend to cover the video/motion derivatives.
- **IRB amendment** to add the de-identified video derivative to the approved release; confirm coverage under 2022P000417.
- **Destroy/retain originals** per IRB once derivative + PI sign-off complete.
- **On-prem processing**; never cloud-upload raw video.

## 7. Compute & sizing (the real cost)
Face-swap is **per-frame across thousands of recording hours** — this is the gating cost, much heavier than the EEG conversion.
- GPU: SAM2/SAMannot run on ≥6 GB; face-swap + pose want a **16–24 GB GPU** (e.g. AWS g5/g6, or a lab cluster), ideally HIPAA-eligible so raw video stays controlled.
- Plan for **batch processing + sampling decisions**: we likely can't (and may not need to) face-swap every hour of every multi-day recording — decide coverage (e.g. all routine + seizure-containing segments first) and log any caps explicitly.
- Throughput/cost estimate needed before committing — size against the per-patient video GB from the Phase-1 inventory's video manifest.

---

## 7b. Execution scope + progress (decided 2026-07-03)
- **Machine:** Apple **M5 Max, 128 GB** unified memory — runs SAM2/YOLO/face models on Metal (MPS). No external GPU needed; full-scale (all ~27,600 hrs) still infeasible, so scoped below.
- **Data reality:** EMU video is **ambulatory/home** (couch, home decor, family present) at 1920×1080/30fps — so the room, decor, and **bystanders are PHI too**. Approach confirmed: **segment patient → neutral background → drop other people → synthetic face**. (Validated: YOLO11-seg on MPS cleanly isolates the patient and removes the home + a bystander; face-swap step pending.)
- **Scope = seizure/event segments + controls:**
  - **Cases:** video windows overlapping `.lay` seizure/patient-event annotations → **2,976 events across 231 video patients** (~hundreds of unique segments).
  - **Controls (per PI, 2026-07-03):** random **non-seizure** segments, **matched in duration**, at **10× the number of case segments** (configurable; "equal or 10×" — chose 10× for detection-task class balance). Sampled from video-bearing patients' non-event periods.
  - Clip length bounded (e.g. event ±window / fixed minutes) to keep compute tractable; process at reduced fps if needed.
- **Pipeline validated so far:** person-seg + background-replace + bystander-removal (YOLO11-seg, MPS). Remaining: synthetic face-swap (insightface inswapper), event→.asf time mapping, control sampling, clip encode, BIDS `derivatives/video/` packaging, PI review gate before upload.

## 8. Sources (verified; 24 fetched, 25 claims adversarially checked)
Face/semiology: Mayo face-swap on EMU seizures `sciencedirect S2949761223000895`; GANonymization vs DeepPrivacy2 `dl.acm.org 10.1145/3641107`; DeepPrivacy2 `github.com/hukkelas/deep_privacy2`; eye-masking-destroys-semiology `S1525-5050(24)00116-1`, `S0920121124001682`.
Segmentation: SAMannot `arxiv 2507.07242`; SAM2+Kalman `PMC12252479`; USPTO face-region de-id under occlusion `patent 11,069,036`.
Pose (optional derivative): ViTPose `arxiv 2212.04246`; MotionBERT/SMPLer-X `arxiv 2309.08794`, `github.com/SMPLCap/SMPLer-X`; 4D-Humans `github.com/shubham-goel/4D-Humans`; EMU ViTPose+MotionBERT semiology `sciencedirect S1746809425013552`.
Governance (reference): HIPAA de-id `hipaajournal.com/de-identification-protected-health-information`; IRB/DUA `PMC12788357`.

## 9. Honesty note
The deep-research workflow's final *synthesis* step returned a malformed stub; this plan was rebuilt from the run's verified source set + recovered extract notes. 3 claims were refuted in verification (incl. an over-stated "100% sensitivity" skeleton seizure-detector result) and are not relied on. **Governance reframed per PI direction: credentialed-access + DUA model, so open-release anonymization steps (PMR / adversarial re-id / Expert Determination) are intentionally omitted.**
