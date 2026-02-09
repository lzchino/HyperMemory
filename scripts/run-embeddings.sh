#!/usr/bin/env bash
set -euo pipefail

# Runs mf-embeddings on localhost:8080.
# CUDA is used automatically if torch detects it.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

export EMBED_MODEL_ID="${EMBED_MODEL_ID:-intfloat/e5-small-v2}"
export EMBED_DEVICE="${EMBED_DEVICE:-cuda}"

# Expect server.py next to this script (public reference implementation)
python3 "$ROOT/scripts/server.py"
