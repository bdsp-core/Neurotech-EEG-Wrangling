#!/bin/bash
# Incrementally sync the Neurotech EHR data from the SFTP server.
#
# Strategy: lftp mirror with --only-newer skips files we already have.
# This is safe to re-run — it won't re-download or overwrite existing files
# unless the remote version is newer.
#
# The SSH key is loaded into a fresh agent for the duration of this run,
# then unloaded. The passphrase is read from ~/.config/neurotech/passphrase
# if present, otherwise from the NEUROTECH_KEY_PASSPHRASE environment variable,
# or prompted interactively.
#
# Usage:
#   ./ehr_pipeline/sync_sftp.sh             # full sync (may take hours)
#   ./ehr_pipeline/sync_sftp.sh --dry-run   # report what would be transferred

set -euo pipefail

SSH_HOST="s-448066211e3243979.server.transfer.us-east-2.amazonaws.com"
SSH_USER="hwu"
SSH_KEY="/Users/mwestover/GithubRepos/Neutotech-key/hwu"
LOCAL_DIR="/Volumes/Extreme SSD/neurotech-data"
LOG_FILE="/tmp/sftp_sync_$(date +%Y%m%d_%H%M%S).log"

DRY_RUN=0
PARALLEL=8

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --parallel=*) PARALLEL="${arg#--parallel=}" ;;
        *) echo "Unknown arg: $arg" >&2; exit 1 ;;
    esac
done

# --- Load passphrase ---
PASSPHRASE="${NEUROTECH_KEY_PASSPHRASE:-}"
if [[ -z "$PASSPHRASE" && -f "$HOME/.config/neurotech/passphrase" ]]; then
    PASSPHRASE=$(cat "$HOME/.config/neurotech/passphrase")
fi
if [[ -z "$PASSPHRASE" ]]; then
    read -s -p "SSH key passphrase: " PASSPHRASE
    echo ""
fi

# --- Load key into a private ssh-agent (TTY-free via SSH_ASKPASS) ---
# Using SSH_ASKPASS instead of `expect` avoids the pty/timeout races that make
# expect unreliable in non-interactive shells. The passphrase is passed to the
# askpass helper via an env var, so it is never written to disk.
eval "$(ssh-agent -s)" >/dev/null
ASKPASS_SCRIPT=$(mktemp)
trap 'ssh-agent -k >/dev/null 2>&1 || true; rm -f "$ASKPASS_SCRIPT"' EXIT
printf '#!/bin/bash\nprintf "%%s\\n" "$NT_KEY_PASSPHRASE"\n' > "$ASKPASS_SCRIPT"
chmod 700 "$ASKPASS_SCRIPT"

NT_KEY_PASSPHRASE="$PASSPHRASE" SSH_ASKPASS="$ASKPASS_SCRIPT" SSH_ASKPASS_REQUIRE=force \
    ssh-add "$SSH_KEY" </dev/null >/dev/null 2>&1

if ! ssh-add -l >/dev/null 2>&1; then
    echo "ERROR: failed to load SSH key into agent" >&2
    exit 1
fi
echo "SSH key loaded into agent."

# --- lftp mirror ---
mkdir -p "$LOCAL_DIR"

LFTP_DRY_FLAG=""
[[ "$DRY_RUN" == "1" ]] && LFTP_DRY_FLAG="--dry-run"

echo "Starting lftp mirror to $LOCAL_DIR"
echo "Logging to $LOG_FILE"
echo "Parallel transfers: $PARALLEL"
echo ""

lftp -u "$SSH_USER," "sftp://$SSH_HOST" <<EOF | tee "$LOG_FILE"
set sftp:auto-confirm yes
set net:max-retries 5
set net:reconnect-interval-base 5
set xfer:log yes
set xfer:log-file $LOG_FILE
set mirror:parallel-transfer-count 1
# AWS Transfer Family doesn't permit mirroring "/" itself, but mirroring "."
# from inside the home directory works. Use "." as the source.
#
# Flags chosen to pull EVERYTHING:
#   --continue        resume any partial transfers
#   --only-newer      skip files we already have (size + timestamp match)
#   --no-perms        skip remote permissions we can't replicate
#   --parallel=N      N concurrent file transfers
#
# Notably NOT setting --no-empty-dirs (we want even empty dirs created in case
# Charles populates them later) and NOT excluding anything.
mirror $LFTP_DRY_FLAG --verbose --continue --only-newer --no-perms --parallel=$PARALLEL . $LOCAL_DIR
bye
EOF

echo ""
echo "Sync complete. Log: $LOG_FILE"

# --- Report ---
echo ""
echo "Local folder counts:"
ls "$LOCAL_DIR" | wc -l
echo "Total local PDFs:"
find "$LOCAL_DIR" -name "*.pdf" | wc -l
