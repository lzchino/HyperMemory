#!/usr/bin/env bash
set -euo pipefail

# HyperMemory installer (lean, reproducible)
# - creates .venv
# - installs python deps
# - prints next steps for Postgres+pgvector + CUDA

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

EMBED_ONLY=false
if [[ "${1:-}" == "--embeddings-only" ]]; then
  EMBED_ONLY=true
fi

python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"

pip install -U pip wheel >/dev/null
pip install -r "$ROOT/requirements.txt"

if ! $EMBED_ONLY; then
  cat <<'TXT'

Next steps:

1) Start Postgres+pgvector (recommended via docker):
   docker compose up -d

2) Set DATABASE_URL (example for docker-compose defaults):
   export DATABASE_URL='postgresql://hypermemory:hypermemory@127.0.0.1:5432/hypermemory'

3) Start mf-embeddings (CUDA optional):
   ./scripts/run-embeddings.sh

4) Run demo / benchmark:
   ./docs/demo.md
   ./scripts/benchmark.sh .

TXT
fi

echo "OK"
