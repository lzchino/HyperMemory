#!/usr/bin/env bash
set -euo pipefail

# checkpoint.sh — distill + reindex + optional eval.

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Workspace not found: $WORKSPACE" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

say() { printf '%s\n' "$*"; }

say "== checkpoint =="
say "workspace: $WORKSPACE"

# 1) Distill (curate)
if [[ -x "$ROOT/scripts/maintenance/memory-distill.sh" ]]; then
  "$ROOT/scripts/maintenance/memory-distill.sh" "$WORKSPACE" 3 >/dev/null || true
fi

# 2) Rebuild SQLite FTS index
if [[ -x "$ROOT/scripts/memory-index.sh" ]]; then
  "$ROOT/scripts/memory-index.sh" "$WORKSPACE" >/dev/null || true
fi

# 2b) Rebuild deterministic entity index (optional but recommended)
python3 -c "from hypermemory.entity_index import build_entity_index; from pathlib import Path; build_entity_index(Path('$WORKSPACE'))" >/dev/null 2>&1 || true

# 3) Optional eval
if [[ -x "$ROOT/scripts/memory-eval.sh" && -f "$WORKSPACE/memory/eval-queries.jsonl" ]]; then
  "$ROOT/scripts/memory-eval.sh" "$WORKSPACE" --fast || true
fi

say "OK"
