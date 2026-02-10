#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper. Prefer: hypermemory search

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="${OPENCLAW_WORKSPACE:-$ROOT}"
QUERY="${1:-}"

if [[ -z "$QUERY" ]]; then
  echo "Usage: $0 <query>" >&2
  exit 2
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate" 2>/dev/null || true

python3 -c 'from hypermemory.__main__ import main; import sys; sys.exit(main(sys.argv[1:]))' \
  --workspace "$WORKSPACE" search "$QUERY"
