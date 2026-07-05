#!/bin/bash
# Self-healing tunnel for the progress dashboard.
# - Uses --protocol http2 (TCP) instead of QUIC/UDP, which institutional
#   networks flap. Much more stable here.
# - Restarts cloudflared if the process dies OR the public URL is unreachable
#   for >5 min continuously (transient ~30-60s flaps are tolerated).
# - Writes the current public URL to dashboard_url.txt on every (re)start.
DIR="/Users/mbwest/Desktop/GithubRepos/neurotech_wrangling/output/batch2_IZ"
CF="$HOME/.local/bin/cloudflared"
PORT=8090
URLFILE="$DIR/dashboard_url.txt"
LOG="$DIR/tunnel_watchdog.log"

log(){ echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

start_tunnel(){
  pkill -f 'cloudflared tunnel' 2>/dev/null; sleep 2
  : > "$DIR/cloudflared.log"
  # QUIC (default) registers reliably here; http2 quick-tunnels fail to register.
  # --ha-connections 4: redundant edge connections so one flapping doesn't drop
  # the tunnel (single control-stream failures no longer cause user-visible outages).
  nohup "$CF" tunnel --url "http://localhost:$PORT" --ha-connections 4 --no-autoupdate \
      >> "$DIR/cloudflared.log" 2>&1 &
  log "started cloudflared (pid $!)"
  local url=""
  for _ in $(seq 1 30); do
    url=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$DIR/cloudflared.log" | tail -1)
    [ -n "$url" ] && break
    sleep 2
  done
  if [ -n "$url" ]; then echo "$url" > "$URLFILE"; log "URL: $url"
  else log "WARN: no URL captured after start"; fi
}

start_tunnel
fail_start=0
while true; do
  sleep 30
  if ! pgrep -f 'cloudflared tunnel' >/dev/null; then
    log "cloudflared process DEAD -> restarting"; start_tunnel; fail_start=0; continue
  fi
  url=$(cat "$URLFILE" 2>/dev/null)
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url/" 2>/dev/null)
  if [ "$code" = "200" ] || [ "$code" = "401" ]; then
    fail_start=0
  else
    now=$(date +%s); [ "$fail_start" -eq 0 ] && fail_start=$now
    down=$(( now - fail_start ))
    log "health check $code (down ${down}s)"
    if [ "$down" -ge 300 ]; then log "down >5min -> restarting"; start_tunnel; fail_start=0; fi
  fi
done
