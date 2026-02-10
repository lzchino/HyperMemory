#!/usr/bin/env bash
set -euo pipefail

# Python-first wrapper (back-compat).
# Prefer: hypermemory retrieve

MODE="${1:-}"
QUERY="${2:-}"

if [[ -z "$MODE" || -z "$QUERY" ]]; then
  echo "Usage: $0 <auto|targeted|broad> <query>" >&2
  exit 2
fi

WORKSPACE="${OPENCLAW_WORKSPACE:-$PWD}"

# Run the in-repo module (works without pip install)
python3 -c 'from hypermemory.__main__ import main; import sys; sys.exit(main(sys.argv[1:]))' \
  --workspace "$WORKSPACE" retrieve "$MODE" "$QUERY"
