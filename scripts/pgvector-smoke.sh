#!/usr/bin/env bash
set -euo pipefail

# pgvector-smoke.sh — minimal semantic layer smoke test
# Requires:
#   - DATABASE_URL set
#   - MF_EMBED_URL pointing to an embeddings server (fake ok)

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$ROOT/tests/fixture-workspace}}"

: "${DATABASE_URL:?DATABASE_URL is required}"

# Index a small workspace
python3 "$ROOT/scripts/hypermemory_cuda_vector_index.py" --repo "$WORKSPACE" --daily-days 30 --batch 16

# Query
python3 "$ROOT/scripts/hypermemory_cuda_vector_search.py" "vector-api.service" --limit 3
