#!/usr/bin/env bash
set -euo pipefail

# HyperMemory benchmark runner (Clawdbot-friendly)
#
# Runs a basic suite and prints timings.
# Safe: does not require publishing any memory content.

WORKSPACE="${1:-${OPENCLAW_WORKSPACE:-$PWD}}"

if [[ ! -d "$WORKSPACE" ]]; then
  echo "Workspace not found: $WORKSPACE" >&2
  exit 2
fi

cd "$WORKSPACE"

QS=("vector-api.service" "EADDRINUSE" "node-fishbowl" "RingCentral" ":8787")

say() { printf '%s\n' "$*"; }

say "== HyperMemory benchmark =="
say "workspace: $WORKSPACE"

if [[ -f scripts/hypermemory/supermemory_index.py ]]; then
  /usr/bin/time -f 'FTS_INDEX_SECONDS %e' python3 scripts/hypermemory/supermemory_index.py --repo "$WORKSPACE" >/dev/null
fi

if [[ -f scripts/hypermemory/supermemory_eval.py && -f memory/eval-queries.jsonl ]]; then
  /usr/bin/time -f 'FTS_EVAL_SECONDS %e' python3 scripts/hypermemory/supermemory_eval.py --repo "$WORKSPACE" --file memory/eval-queries.jsonl >/dev/null
fi

# FTS stress
if [[ -f scripts/hypermemory/supermemory_retrieve.py ]]; then
  /usr/bin/time -f 'FTS_RETRIEVE_STRESS_SECONDS %e' bash -lc '
set -euo pipefail
qs=("vector-api.service" "EADDRINUSE" "node-fishbowl" "RingCentral" ":8787")
n=500
for i in $(seq 1 $n); do
  q=${qs[$(( (i-1) % ${#qs[@]} ))]}
  python3 scripts/hypermemory/supermemory_retrieve.py --repo "'$WORKSPACE'" auto "$q" >/dev/null
done
'
fi

# CUDA semantic checks (optional)
if command -v curl >/dev/null 2>&1; then
  curl -s http://127.0.0.1:8080/health >/dev/null 2>&1 && say "mf-embeddings: ok" || say "mf-embeddings: not reachable"
fi

if [[ -f scripts/hypermemory/hypermemory_cuda_vector_index.py ]]; then
  if [[ -n "${DATABASE_URL:-}" ]]; then
    /usr/bin/time -f 'CUDA_VECTOR_INDEX_SECONDS %e' python3 scripts/hypermemory/hypermemory_cuda_vector_index.py --repo "$WORKSPACE" --daily-days 14 --batch 64 >/dev/null || true
  else
    say "(skip) CUDA vector index: DATABASE_URL not set"
  fi
fi

if [[ -f scripts/hypermemory/hypermemory_cuda_vector_search.py ]]; then
  if [[ -n "${DATABASE_URL:-}" ]]; then
    /usr/bin/time -f 'CUDA_VECTOR_SEARCH_STRESS_SECONDS %e' bash -lc '
set -euo pipefail
qs=("vector-api.service" "EADDRINUSE" "node-fishbowl" "RingCentral" ":8787")
n=100
for i in $(seq 1 $n); do
  q=${qs[$(( (i-1) % ${#qs[@]} ))]}
  python3 scripts/hypermemory/hypermemory_cuda_vector_search.py "$q" --limit 5 >/dev/null
done
'
  else
    say "(skip) CUDA vector search: DATABASE_URL not set"
  fi
fi

say "OK"
