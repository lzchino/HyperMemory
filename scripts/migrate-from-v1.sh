#!/usr/bin/env bash
set -euo pipefail

# migrate-from-v1.sh — helper to migrate a v1 workspace into HyperMemory.
#
# Non-destructive: does not delete or modify source files.
#
# Usage:
#   migrate-from-v1.sh --src /path/to/v1/workspace --dst /path/to/v2/workspace

SRC=""
DST=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --src) SRC="$2"; shift 2 ;;
    --dst) DST="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$SRC" || -z "$DST" ]]; then
  echo "Usage: $0 --src <v1> --dst <v2>" >&2
  exit 2
fi

mkdir -p "$DST/memory"

# Copy daily files + MEMORY.md if present
if [[ -d "$SRC/memory" ]]; then
  cp -n "$SRC/memory"/*.md "$DST/memory/" 2>/dev/null || true
fi
if [[ -f "$SRC/MEMORY.md" ]]; then
  cp -n "$SRC/MEMORY.md" "$DST/MEMORY.md" 2>/dev/null || true
fi

# Rebuild FTS index in destination
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/memory-index.sh" "$DST" >/dev/null 2>&1 || true

# Optional: build deterministic entity index
python3 -c "from hypermemory.entity_index import build_entity_index; from pathlib import Path; build_entity_index(Path('$DST'))" >/dev/null 2>&1 || true

echo "Migrated files into: $DST"
echo "Next: (optional) set DATABASE_URL + MF_EMBED_URL and run: hypermemory --workspace $DST vector index"