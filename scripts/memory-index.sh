#!/usr/bin/env bash
set -euo pipefail

# Build/update SQLite FTS index from memory/*.md + MEMORY.md
#
# Usage:
#   ./scripts/memory-index.sh [workspace]

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$ROOT}}"

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate" 2>/dev/null || true

python3 "$ROOT/scripts/supermemory_index.py" --repo "$WORKSPACE"
