#!/bin/bash
set -euo pipefail

RAW_DIR=~/ai-data-training/raw/incoming
STRUCT_DIR=~/ai-data-training/structured
MASTER_LOG=~/ai-data-training/logs/master.log
LOG_FILE=~/ai-data-training/logs/ingest_$(date +%Y%m%d_%H%M%S).log

mkdir -p "$STRUCT_DIR"/{json,csv,log,unknown}
touch "$MASTER_LOG"

for file in "$RAW_DIR"/*; do
  [ -f "$file" ] || continue
  fname=$(basename "$file")
  ext="${fname##*.}"
  checksum=$(sha256sum "$file" | awk '{print $1}')
  dest_dir="$STRUCT_DIR/unknown"

  case "$ext" in
    json) dest_dir="$STRUCT_DIR/json" ;;
    csv)  dest_dir="$STRUCT_DIR/csv" ;;
    log)  dest_dir="$STRUCT_DIR/log" ;;
  esac

  if grep -q "$checksum" "$MASTER_LOG" 2>/dev/null; then
    echo "$(date): DUPLICATE skipped -> $fname ($checksum)" | tee -a "$LOG_FILE" >> "$MASTER_LOG"
    continue
  fi

  cp "$file" "$dest_dir/$fname"
  echo "$(date): INGESTED $fname -> $dest_dir | sha256=$checksum" | tee -a "$LOG_FILE" >> "$MASTER_LOG"
done

echo "Done. Run log: $LOG_FILE"
echo "Master log: $MASTER_LOG"
