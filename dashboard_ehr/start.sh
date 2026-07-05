#!/bin/bash
# Start the EHR extraction dashboard: HTTP server + optional ngrok tunnel.
#
# Usage:
#   ./dashboard_ehr/start.sh            # serve on http://localhost:8081
#   ./dashboard_ehr/start.sh --ngrok    # also open a public ngrok tunnel
#
# The HTTP server will stay in the foreground. Press Ctrl-C to stop both.
# ngrok (if started) is killed on exit.

set -euo pipefail

PORT="${PORT:-8081}"
DASHBOARD_DIR="$(cd "$(dirname "$0")" && pwd)"
WITH_NGROK=0
for arg in "$@"; do
  case "$arg" in
    --ngrok) WITH_NGROK=1 ;;
    --port=*) PORT="${arg#--port=}" ;;
    *) echo "Unknown arg: $arg" >&2; exit 1 ;;
  esac
done

cleanup() {
  if [[ -n "${NGROK_PID:-}" ]]; then
    kill "$NGROK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

cd "$DASHBOARD_DIR"

if [[ "$WITH_NGROK" -eq 1 ]]; then
  if ! command -v ngrok >/dev/null 2>&1; then
    echo "ngrok not found on PATH" >&2
    exit 1
  fi
  ngrok http "$PORT" --log=stdout > "$DASHBOARD_DIR/ngrok.log" 2>&1 &
  NGROK_PID=$!
  echo "ngrok pid=$NGROK_PID (logs: $DASHBOARD_DIR/ngrok.log)"
  # Wait for ngrok to establish, then print public URL from its local API
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if url=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c 'import sys,json;
ds=json.load(sys.stdin).get("tunnels",[])
print(next((t["public_url"] for t in ds if t.get("proto")=="https"), ""))' 2>/dev/null); then
      if [[ -n "$url" ]]; then
        echo ""
        echo "  Public:  $url"
        break
      fi
    fi
    sleep 1
  done
fi

echo "  Local:   http://localhost:$PORT"
echo ""
echo "Starting Python http.server on port $PORT (Ctrl-C to stop)..."
exec python3 -m http.server "$PORT" --bind 127.0.0.1
