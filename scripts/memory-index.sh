#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper. Prefer: hypermemory index
# Usage:
#   ./scripts/memory-index.sh [workspace]

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$ROOT}}"

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate" 2>/dev/null || true

python3 -c 'from hypermemory.__main__ import main; import sys; sys.exit(main(sys.argv[1:]))' \
  --workspace "$WORKSPACE" index
