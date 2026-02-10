#!/usr/bin/env bash
set -euo pipefail

# pgvector-smoke.sh — minimal semantic layer smoke test
# Requires:
#   - DATABASE_URL set
#   - MF_EMBED_URL pointing to an embeddings server (fake ok)

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$ROOT/tests/fixture-workspace}}"

: "${DATABASE_URL:?DATABASE_URL is required}"

# Index curated+distilled semantic chunks into local pgvector
python3 -c "from hypermemory.pgvector_local import LocalVectorConfig, index_workspace; import pathlib; cfg=LocalVectorConfig.from_env(); print('indexed', index_workspace(pathlib.Path('$WORKSPACE'), cfg, include_pending=False, batch=16))"

# Query (smoke)
hypermemory --workspace "$WORKSPACE" vector search --query "vector-api.service" --limit 3
