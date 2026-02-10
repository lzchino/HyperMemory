#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"

python3 "$ROOT/scripts/cloud/pull_curated.py" --workspace "$WORKSPACE" "${@:2}"
