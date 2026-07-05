#!/bin/bash
# Back up EMU video (per-patient tar, streamed) to Box. No local staging.
# Resumable: skips patients whose .tar already exists on Box.
#   ./video_backup.sh <patient_list_file> [workers]
#   ./video_backup.sh --one "<patient folder name>"
export PATH="$HOME/.local/bin:$PATH"
BOX="box:Brandon - PHI/Datasets/zz_neuroTech/video_backup"
DRIVE="/Volumes/Padlock_DT"
LOG="/Users/mbwest/Desktop/GithubRepos/neurotech_wrangling/output/batch2_IZ/video_backup.log"

backup_one(){
  local PAT="$1" D="$DRIVE/$1"
  [ -d "$D" ] || { echo "$(date -u +%H:%M:%S) MISS  $PAT" >>"$LOG"; return; }
  if [ -n "$(rclone lsf "$BOX/${PAT}.tar" 2>/dev/null)" ]; then
    echo "$(date -u +%H:%M:%S) SKIP  $PAT" >>"$LOG"; return
  fi
  if find "$D" -maxdepth 1 -type f \( -iname '*.asf' -o -iname '*.avi' -o -iname '*.mov' \
        -o -iname '*.wav' -o -iname '*.vinfo' \) -print0 \
      | tar --null -cf - -T - 2>/dev/null | rclone rcat "$BOX/${PAT}.tar" 2>>"$LOG"; then
    echo "$(date -u +%H:%M:%S) DONE  $PAT ($(rclone size --json "$BOX/${PAT}.tar" 2>/dev/null | grep -oE '\"bytes\":[0-9]+'))" >>"$LOG"
  else
    echo "$(date -u +%H:%M:%S) FAIL  $PAT" >>"$LOG"
  fi
}
export -f backup_one; export BOX DRIVE LOG

if [ "$1" = "--one" ]; then backup_one "$2"; exit 0; fi

LIST="$1"; WORKERS="${2:-3}"
total=$(wc -l < "$LIST" | tr -d ' ')
echo "$(date -u +%FT%TZ) START video backup: $total patients, $WORKERS workers" >>"$LOG"
tr '\n' '\0' < "$LIST" | xargs -0 -P "$WORKERS" -I{} bash "$0" --one "{}"
echo "$(date -u +%FT%TZ) ALL DONE" >>"$LOG"
