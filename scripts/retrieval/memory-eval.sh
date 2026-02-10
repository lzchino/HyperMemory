#!/usr/bin/env bash
set -euo pipefail

# Back-compat wrapper for older installs that call scripts/retrieval/memory-eval.sh
# Prefer the new location: scripts/memory-eval.sh

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "$ROOT/scripts/memory-eval.sh" "$@"
