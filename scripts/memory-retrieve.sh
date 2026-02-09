#!/usr/bin/env bash
set -euo pipefail

# HyperMemory retrieval orchestrator (public reference)
# Ordering: FTS (exact) -> pgvector+CUDA (semantic) -> optional BM25 fallback

MODE="${1:-}"
QUERY="${2:-}"

TRACE=false
HYBRID=true

shift 2 || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --trace) TRACE=true; shift ;;
    --no-hybrid) HYBRID=false; shift ;;
    --hybrid) HYBRID=true; shift ;;
    *) shift ;;
  esac
done

if [[ -z "$MODE" || -z "$QUERY" ]]; then
  echo "Usage: $0 <auto|targeted|broad> <query> [--no-hybrid] [--trace]" >&2
  exit 2
fi

if [[ "$MODE" == "auto" ]]; then
  if [[ ${#QUERY} -lt 40 ]]; then MODE=targeted; else MODE=broad; fi
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

say() { printf '%s\n' "$*"; }

say "== retrieve mode=$MODE query=$QUERY =="

# 1) FTS
if [[ -f "$ROOT/memory/supermemory.sqlite" ]]; then
  say "-- FTS (SQLite) --"
  "$ROOT/scripts/memory-search.sh" "$QUERY" | head -n 10 || true
else
  say "(skip) FTS DB missing; run ./scripts/memory-index.sh"
fi

# 2) pgvector+CUDA
if [[ -n "${DATABASE_URL:-}" ]]; then
  say "-- pgvector+CUDA --"
  python3 "$ROOT/scripts/hypermemory_cuda_vector_search.py" "$QUERY" --limit 5 || true
else
  say "(skip) pgvector: DATABASE_URL not set"
fi

# 3) Optional BM25 fallback (not included by default)
if $HYBRID; then
  :
fi
