#!/usr/bin/env bash
set -euo pipefail

# memory-distill.sh — roll up tagged daily bullets into curated memory.
#
# Tag convention written by curated-memory-write.sh:
#   - [M3] / [M4] / [M5] are eligible for promotion.
#
# This script appends promoted lines into MEMORY.md under a dated heading.
# It is idempotent: it will not re-add exact duplicate lines.

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"
THRESHOLD="${2:-3}"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Workspace not found: $WORKSPACE" >&2
  exit 2
fi

TODAY=$(date -u +%F)
YDAY=$(date -u -d 'yesterday' +%F 2>/dev/null || true)

MEM="$WORKSPACE/MEMORY.md"
mkdir -p "$WORKSPACE/memory"

touch "$MEM"

append_unique() {
  local line="$1"
  if ! grep -qF -- "$line" "$MEM" 2>/dev/null; then
    printf '%s\n' "$line" >> "$MEM"
  fi
}

promote_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    # match bullets like: - [M3] text
    if echo "$line" | grep -qE '^\s*-\s*\[M[0-9]\]'; then
      score=$(echo "$line" | sed -n 's/^\s*-\s*\[M\([0-9]\)\].*$/\1/p')
      if [[ -n "$score" && "$score" -ge "$THRESHOLD" ]]; then
        append_unique "$line"
      fi
    fi
  done < "$f"
}

# Ensure a section marker exists
if ! grep -q '^## Curated$' "$MEM" 2>/dev/null; then
  printf '\n## Curated\n' >> "$MEM"
fi

# Append a run marker
printf '\n### distill %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$MEM"

promote_file "$WORKSPACE/memory/$TODAY.md"
if [[ -n "$YDAY" ]]; then
  promote_file "$WORKSPACE/memory/$YDAY.md"
fi

echo "$MEM"
