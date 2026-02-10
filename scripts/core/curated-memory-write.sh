#!/usr/bin/env bash
set -euo pipefail

# curated-memory-write.sh — write a scored memory item.
#
# Convention:
#   - score 1..5
#   - always write to daily log
#   - if score >= threshold (default 3), also append to a staging file for curated memory
#
# Usage:
#   curated-memory-write.sh --workspace /path/to/ws --score 4 --text "Decision: ..." [--threshold 3]

WORKSPACE=""
SCORE=""
TEXT=""
THRESHOLD="${MEMORY_SCORE_THRESHOLD:-3}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace|--repo) WORKSPACE="$2"; shift 2 ;;
    --score) SCORE="$2"; shift 2 ;;
    --text) TEXT="$2"; shift 2 ;;
    --threshold) THRESHOLD="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$WORKSPACE" ]]; then
  WORKSPACE="${OPENCLAW_WORKSPACE:-$PWD}"
fi

if [[ -z "$SCORE" || -z "$TEXT" ]]; then
  echo "Usage: $0 --workspace <ws> --score 1..5 --text <text> [--threshold N]" >&2
  exit 2
fi

TODAY=$(date -u +%F)
mkdir -p "$WORKSPACE/memory" "$WORKSPACE/memory/staging"
DAILY="$WORKSPACE/memory/$TODAY.md"
STAGE="$WORKSPACE/memory/staging/MEMORY.pending.md"

# Normalize score
if ! [[ "$SCORE" =~ ^[1-5]$ ]]; then
  echo "Invalid --score (must be 1..5): $SCORE" >&2
  exit 2
fi

LINE="- [M${SCORE}] ${TEXT}"
printf '%s\n' "$LINE" >> "$DAILY"

echo "$DAILY"

if [[ "$SCORE" -ge "$THRESHOLD" ]]; then
  # Avoid duplicates in staging
  if ! grep -qF -- "$LINE" "$STAGE" 2>/dev/null; then
    printf '%s\n' "$LINE" >> "$STAGE"
  fi
  echo "$STAGE"
fi
