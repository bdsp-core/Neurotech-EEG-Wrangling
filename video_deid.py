"""
Phase 5 video de-identification pipeline (Apple Silicon / MPS).

Per clip: extract a window around an event (audio stripped) -> per frame:
  1. YOLO11-seg  -> keep ONLY the largest person (patient); drop bystanders
  2. insightface -> swap every detected face to a synthetic donor identity
                    (consistent donor per subject via hash)
  3. composite the patient onto a neutral background (removes home/room/decor)
-> encode a de-identified mp4 (no audio). Timestamps live in filenames only
(no burned-in overlay observed), so nothing to OCR-mask here.

Usage:
  .venv/bin/python video_deid.py <clips_csv> <out_dir> [fps] [pre_s] [dur_s]
clips_csv columns: sub, folder, asf, offset_s
"""
import sys, os, glob, hashlib, subprocess, tempfile
import numpy as np, cv2, torch, insightface
from insightface.app import FaceAnalysis
from ultralytics import YOLO
import imageio_ffmpeg
import pandas as pd

DRIVE = "/Volumes/Padlock_DT"
DONORS = sorted(glob.glob("output/batch2_IZ/donor_faces/donor_*.jpg"))
FF = imageio_ffmpeg.get_ffmpeg_exe()
DEV = "mps" if torch.backends.mps.is_available() else "cpu"

_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_app.prepare(ctx_id=0, det_size=(640, 640))
_swap = insightface.model_zoo.get_model(
    os.path.expanduser("~/.insightface/models/inswapper_128.onnx"),
    providers=["CPUExecutionProvider"])
_seg = YOLO("yolo11m-seg.pt")

# preload donor embeddings
_donor_faces = []
for d in DONORS:
    fs = _app.get(cv2.imread(d))
    if fs:
        _donor_faces.append(fs[0])
print(f"loaded {len(_donor_faces)} donors, device={DEV}", flush=True)


def donor_for(sub):
    h = int(hashlib.md5(sub.encode()).hexdigest(), 16)
    return _donor_faces[h % len(_donor_faces)]


def deid_frame(frame, donor):
    # 1. face swap (all faces -> donor identity)
    out = frame
    for f in _app.get(frame):
        out = _swap.get(out, f, donor, paste_back=True)
    # 2. patient segmentation (largest person)
    r = _seg.predict(frame, device=DEV, classes=[0], retina_masks=True, verbose=False)[0]
    if r.masks is None:
        return np.full_like(frame, 128)          # nobody -> blank (never leak)
    m = r.masks.data.cpu().numpy()
    patient = (m[m.reshape(len(m), -1).sum(1).argmax()] > 0.5)
    bg = np.full_like(out, 128)
    return np.where(patient[..., None], out, bg).astype("uint8")


def process_clip(asf, offset_s, out_mp4, sub, fps=15, pre=10.0, dur=40.0, width=1280):
    start = max(0.0, offset_s - pre)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tmp = tf.name
    subprocess.run([FF, "-y", "-ss", f"{start}", "-i", asf, "-t", f"{dur}", "-an",
                    "-r", f"{fps}", "-vf", f"scale={width}:-2", "-loglevel", "error", tmp], check=True)
    cap = cv2.VideoCapture(tmp)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vw = cv2.VideoWriter(out_mp4, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    donor = donor_for(sub); n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        vw.write(deid_frame(frame, donor)); n += 1
    cap.release(); vw.release(); os.unlink(tmp)
    return n


def main():
    csv, out_dir = sys.argv[1], sys.argv[2]
    fps = int(sys.argv[3]) if len(sys.argv) > 3 else 15
    pre = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0
    dur = float(sys.argv[5]) if len(sys.argv) > 5 else 40.0
    os.makedirs(out_dir, exist_ok=True)
    clips = pd.read_csv(csv)
    for i, r in clips.iterrows():
        folder = [d for d in os.listdir(DRIVE) if d.startswith(str(r["folder"]).split(" 2")[0][:20])]
        asf = None
        for d in folder:
            p = os.path.join(DRIVE, d, r["asf"])
            if os.path.exists(p): asf = p; break
        if not asf:
            print(f"[{i+1}/{len(clips)}] {r.sub}: asf not found ({r.asf})", flush=True); continue
        sub = str(r["sub"])
        out = os.path.join(out_dir, f"{sub}_seizure_deid.mp4")
        try:
            n = process_clip(asf, float(r["offset_s"]), out, sub, fps=fps, pre=pre, dur=dur)
            print(f"[{i+1}/{len(clips)}] {sub}: {n} frames -> {os.path.basename(out)}", flush=True)
        except Exception as e:
            print(f"[{i+1}/{len(clips)}] {r.sub}: ERROR {e}", flush=True)


if __name__ == "__main__":
    main()
