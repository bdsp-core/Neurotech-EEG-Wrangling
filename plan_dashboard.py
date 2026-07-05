"""
Plan progress dashboard for the Neurotech final-batch wrangling.

Serves a phone-friendly, auto-refreshing page showing:
  - MASTER_PLAN phase checklist + statuses
  - LIVE inventory progress (folders done / total, %, rate, ETA)
  - Non-PHI aggregates from the latest checkpoint (recordings, EEG hours/GB,
    video files/GB, clinical annotations)

PHI SAFETY: this page emits ONLY aggregate numbers. It never outputs folder
names, patient names, case IDs, or any row content — safe to expose via tunnel.

Run:  .venv/bin/python plan_dashboard.py [PORT]
"""
import sys
import os
import re
import base64
import html
from datetime import datetime, timezone
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Basic-auth credentials from env (set before launch). If unset, no auth.
AUTH_USER = os.environ.get("NT_DASH_USER", "")
AUTH_PASS = os.environ.get("NT_DASH_PASS", "")
_EXPECTED = ("Basic " + base64.b64encode(f"{AUTH_USER}:{AUTH_PASS}".encode()).decode()) \
    if AUTH_PASS else None

REPO = Path(__file__).resolve().parent
INV = REPO / "output" / "batch2_IZ"
TOTAL_FOLDERS = 3652
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8090

PHASES = [
    ("0", "Environment setup", "done", "Repo, venv, drive confirmed (H–Z, 3,652 folders, 19 TB)"),
    ("1", "Inventory final batch", "done", "3,652 folders, 0 errors; 137,882 EEG hrs; video manifest"),
    ("2", "Reconcile + linking table", "done", "3,182 patients; 2,824 pre-assigned IDs, 357 new (4965–5321)"),
    ("3", "De-identify + BIDS + S3 upload", "done", "3,171 new subjects, 6.64 TB, 54k EDFs — verified, no gaps"),
    ("4", "Validate + finalize dataset files", "done", "A–Z participants.tsv fixed (4,915); structural audit passed"),
    ("5", "Video → synthetic-face de-id", "plan-ready", "VIDEO_DEID_PLAN.md; PI review gate; needs GPU"),
    ("6", "Finish EHR pipeline", "pending", "Clear known bugs, re-link to A–Z IDs"),
    ("7", "Finalize manuscript", "pending", "Full A–Z numbers, add video modality, regen tables/figures"),
    ("8", "Confirm completeness w/ Neurotech", "done", "Charles confirmed final batch; email drafted for record"),
]
BIDS_TOTAL_FOLDERS = 3632  # folders with EDFs in the batch-2 linking table
BADGE = {"done": "#1f9d55", "running": "#2563eb", "plan-ready": "#7c3aed",
         "pending": "#6b7280"}


def count_lines(p):
    try:
        with open(p) as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def parse_runlog():
    """Return (done_n, rate_per_min, eta_min) from run.log's last progress line. No PHI."""
    log = INV / "run.log"
    last = None
    try:
        for line in open(log):
            if re.search(r"\[\d+/\d+\]", line):
                last = line
    except OSError:
        return None
    if not last:
        return None
    m = re.search(r"\[(\d+)/(\d+)\].*?~([\d.]+)min left, ([\d.]+) fld/min", last)
    if m:
        return {"n": int(m.group(1)), "eta_min": float(m.group(3)), "rate": float(m.group(4))}
    m2 = re.search(r"\[(\d+)/(\d+)\]", last)
    return {"n": int(m2.group(1)), "eta_min": None, "rate": None} if m2 else None


def bids_progress():
    """Phase-3 progress = original serial run + 4 parallel workers. Aggregated. No PHI."""
    import json, glob
    out = {"folders": 0, "gb": 0.0, "edfs_up": 0, "workers": 0}
    # folders completed: original serial run + each worker's progress file
    pf = INV / "bids_progress.tsv"
    if pf.exists():
        out["folders"] += max(0, count_lines(pf) - 1)
    for wp in glob.glob(str(INV / "workers" / "w*" / "bids_progress.tsv")):
        out["folders"] += max(0, count_lines(wp) - 1)
    # bytes/EDFs: original dashboard/progress.json (frozen) + each worker's dash json
    jsons = [REPO / "dashboard" / "progress.json"] + \
            [p for p in glob.glob(str(INV / "workers" / "w*" / "dash" / "progress.json"))]
    for p in jsons:
        try:
            d = json.loads(open(p).read())
            out["gb"] += d.get("bytes_uploaded", 0) / 1073741824
            out["edfs_up"] += d.get("edfs_uploaded", 0)
        except Exception:
            pass
    out["workers"] = len(glob.glob(str(INV / "workers" / "w*" / "dash" / "progress.json")))
    return out


def aggregates():
    """Non-PHI sums from the latest checkpoint CSVs. Uses pandas if available."""
    out = {}
    try:
        import pandas as pd
        rp = INV / "recordings.csv"
        if rp.exists():
            r = pd.read_csv(rp, usecols=lambda c: c in
                            ("edf_size_mb", "duration_hours", "n_data_records"))
            out["recordings"] = len(r)
            if "duration_hours" in r:
                out["eeg_hours"] = float(r["duration_hours"].fillna(0).sum())
            if "edf_size_mb" in r:
                out["eeg_gb"] = float(r["edf_size_mb"].fillna(0).sum()) / 1024
        pp = INV / "patients.csv"
        if pp.exists():
            p = pd.read_csv(pp, usecols=lambda c: c in
                            ("video_files", "video_gb", "n_lay_annotations", "edf_gb"))
            out["patients"] = len(p)
            for col, key in (("video_files", "video_files"), ("video_gb", "video_gb"),
                             ("n_lay_annotations", "lay_anns")):
                if col in p:
                    out[key] = float(p[col].fillna(0).sum())
    except Exception as e:
        out["_err"] = str(e)
    return out


def render():
    done_n = count_lines(INV / "done.txt")
    rl = parse_runlog()
    if rl and rl["n"] > done_n:
        done_n = rl["n"]
    pct = 100 * done_n / TOTAL_FOLDERS if TOTAL_FOLDERS else 0
    agg = aggregates()
    inv_running = (REPO / "output/batch2_IZ/run.log").exists() and done_n < TOTAL_FOLDERS

    rate = rl.get("rate") if rl else None
    eta = rl.get("eta_min") if rl else None
    eta_txt = (f"{eta/60:.1f} h" if eta and eta >= 90 else f"{eta:.0f} min") if eta else "—"
    rate_txt = f"{rate:.1f} folders/min" if rate else "—"

    bp = bids_progress()
    bpct = 100 * bp["folders"] / BIDS_TOTAL_FOLDERS if BIDS_TOTAL_FOLDERS else 0
    rows = []
    for num, name, status, detail in PHASES:
        st = status
        extra = ""
        if num == "1":
            extra = f"<div class='sub'>{TOTAL_FOLDERS:,} folders inventoried · 0 errors</div>"
        if num == "3":
            extra = f"<div class='bar'><div class='fill' style='width:{bpct:.1f}%'></div></div>" \
                    f"<div class='sub'>{bp['folders']:,} / {BIDS_TOTAL_FOLDERS:,} folders converted+uploaded " \
                    f"({bpct:.1f}%) · {bp['gb']:.0f} GB on S3 · {bp['edfs_up']:,} EDFs · {bp['workers']} parallel workers</div>"
        rows.append(f"""
        <div class="phase">
          <div class="ph-head">
            <span class="badge" style="background:{BADGE.get(st,'#6b7280')}">{html.escape(st)}</span>
            <span class="ph-name"><b>{num}.</b> {html.escape(name)}</span>
          </div>
          <div class="ph-detail">{html.escape(detail)}</div>
          {extra}
        </div>""")

    def stat(label, val):
        return f"<div class='stat'><div class='v'>{val}</div><div class='l'>{label}</div></div>"
    cards = ""
    if agg:
        cards = "<div class='stats'>" + "".join([
            stat("folders done", f"{done_n:,}"),
            stat("recordings", f"{agg.get('recordings',0):,}"),
            stat("EEG hours", f"{agg.get('eeg_hours',0):,.0f}"),
            stat("EEG TB", f"{agg.get('eeg_gb',0)/1024:,.2f}"),
            stat("video files", f"{int(agg.get('video_files',0)):,}"),
            stat("video GB", f"{agg.get('video_gb',0):,.0f}"),
            stat("clin. annotations", f"{int(agg.get('lay_anns',0)):,}"),
        ]) + "</div><div class='note'>Aggregates as of last checkpoint (every 200 folders); folder count is live.</div>"

    now = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    inv_dot = "🟢 running" if inv_running else ("✅ complete" if done_n >= TOTAL_FOLDERS else "⏸ stopped")
    return f"""<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="20">
<title>Neurotech wrangling — progress</title>
<style>
  body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0b1020;color:#e5e7eb}}
  .wrap{{max-width:760px;margin:0 auto;padding:18px}}
  h1{{font-size:20px;margin:6px 0}}
  .meta{{color:#9ca3af;font-size:13px;margin-bottom:14px}}
  .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));gap:10px;margin:12px 0}}
  .stat{{background:#151b30;border:1px solid #232a45;border-radius:12px;padding:12px;text-align:center}}
  .stat .v{{font-size:20px;font-weight:700;color:#fff}}
  .stat .l{{font-size:11px;color:#9ca3af;margin-top:4px}}
  .note{{font-size:11px;color:#6b7280;margin:-4px 0 16px}}
  .phase{{background:#121829;border:1px solid #222a44;border-radius:12px;padding:12px 14px;margin:10px 0}}
  .ph-head{{display:flex;align-items:center;gap:10px}}
  .ph-name{{font-size:15px}}
  .ph-detail{{color:#9ca3af;font-size:12px;margin:6px 0 0 2px}}
  .badge{{color:#fff;font-size:11px;padding:3px 9px;border-radius:999px;white-space:nowrap}}
  .bar{{height:9px;background:#232a45;border-radius:999px;overflow:hidden;margin:10px 0 4px}}
  .fill{{height:100%;background:linear-gradient(90deg,#2563eb,#7c3aed)}}
  .sub{{font-size:12px;color:#cbd5e1}}
</style></head><body><div class="wrap">
  <h1>🧠 Neurotech EEG — final batch</h1>
  <div class="meta">Inventory: {inv_dot} · updated {html.escape(now)} · auto-refresh 20s</div>
  {cards}
  {''.join(rows)}
  <div class="note" style="margin-top:18px">Aggregate, de-identified metrics only — no patient information on this page.</div>
</div></body></html>"""


class H(BaseHTTPRequestHandler):
    def _auth_ok(self):
        if _EXPECTED is None:
            return True
        return self.headers.get("Authorization", "") == _EXPECTED

    def do_GET(self):
        if not self._auth_ok():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Neurotech progress"')
            self.end_headers()
            self.wfile.write(b"Authentication required")
            return
        if self.path not in ("/", "/index.html"):
            self.send_response(404); self.end_headers(); return
        body = render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"dashboard on http://0.0.0.0:{PORT}  (LAN: http://10.110.128.60:{PORT})", flush=True)
    srv.serve_forever()
