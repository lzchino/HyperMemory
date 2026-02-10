#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper.

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"

python3 "$ROOT/scripts/cloud/push_curated.py" --workspace "$WORKSPACE" "${@:2}"
