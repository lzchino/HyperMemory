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
if [[ -f "$ROOT/scripts/supermemory_index.py" ]]; then
  python3 "$ROOT/scripts/supermemory_index.py" --repo "$WORKSPACE" >/dev/null || true
fi

# 3) Optional eval
if [[ -x "$ROOT/scripts/memory-eval.sh" && -f "$WORKSPACE/memory/eval-queries.jsonl" ]]; then
  "$ROOT/scripts/memory-eval.sh" "$WORKSPACE" --fast || true
fi

say "OK"
