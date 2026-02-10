#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper. Prefer: hypermemory eval
# Usage:
#   scripts/memory-eval.sh [workspace] [--fast]

# If first arg starts with -, treat as no-workspace provided.
if [[ "${1:-}" == -* || -z "${1:-}" ]]; then
  WORKSPACE="${OPENCLAW_WORKSPACE:-$PWD}"
else
  WORKSPACE="$1"
  shift 1 || true
fi

ROOT_SELF="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT_SELF/.venv/bin/activate" 2>/dev/null || true

ARGS=("--workspace" "$WORKSPACE" "eval")
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fast) ARGS+=("--fast"); shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

python3 -c 'from hypermemory.__main__ import main; import sys; sys.exit(main(sys.argv[1:]))' "${ARGS[@]}"
