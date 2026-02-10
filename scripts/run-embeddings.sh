#!/usr/bin/env bash
set -euo pipefail

# Runs mf-embeddings on localhost:8080.
# CUDA is used automatically if torch detects it.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

export EMBED_MODEL_ID="${EMBED_MODEL_ID:-intfloat/e5-small-v2}"

# Device selection:
# - default: auto-detect (cuda -> mps -> cpu)
# - override by setting EMBED_DEVICE=cuda|mps|cpu
if [[ -z "${EMBED_DEVICE:-}" ]]; then
  EMBED_DEVICE=$(python3 -c 'import torch
if torch.cuda.is_available():
  print("cuda")
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
  print("mps")
else:
  print("cpu")
')
fi
export EMBED_DEVICE


# Expect server.py next to this script (public reference implementation)
python3 "$ROOT/scripts/server.py"
