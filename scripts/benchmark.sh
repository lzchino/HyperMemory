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

/usr/bin/time -f 'FTS_INDEX_SECONDS %e' bash -lc 'OPENCLAW_WORKSPACE="'$WORKSPACE'" ./scripts/memory-index.sh "'$WORKSPACE'" >/dev/null || true'

if [[ -f memory/eval-queries.jsonl ]]; then
  /usr/bin/time -f 'FTS_EVAL_SECONDS %e' bash -lc 'OPENCLAW_WORKSPACE="'$WORKSPACE'" MIN_RECALL=0 ./scripts/memory-eval.sh "'$WORKSPACE'" --fast >/dev/null || true'
fi

# Retrieve stress (python-first)
/usr/bin/time -f 'RETRIEVE_STRESS_SECONDS %e' bash -lc '
set -euo pipefail
qs=("vector-api.service" "EADDRINUSE" "node-fishbowl" "RingCentral" ":8787")
n=300
for i in $(seq 1 $n); do
  q=${qs[$(( (i-1) % ${#qs[@]} ))]}
  python3 -c "from hypermemory.__main__ import main; import sys; sys.exit(main([\"--workspace\", \"'$WORKSPACE'\", \"retrieve\", \"auto\", q]))" >/dev/null

done
'

# Semantic checks (optional, python-first local pgvector)
if command -v curl >/dev/null 2>&1; then
  curl -s "${MF_EMBED_URL:-http://127.0.0.1:8080}/health" >/dev/null 2>&1 && say "embeddings: ok" || say "embeddings: not reachable"
fi

if [[ -n "${DATABASE_URL:-}" ]]; then
  /usr/bin/time -f 'LOCAL_VECTOR_INDEX_SECONDS %e' bash -lc 'python3 -c "from hypermemory.pgvector_local import LocalVectorConfig, index_workspace; import pathlib; cfg=LocalVectorConfig.from_env(); index_workspace(pathlib.Path(\"'$WORKSPACE'\"), cfg, include_pending=False, batch=64)" >/dev/null'
  /usr/bin/time -f 'LOCAL_VECTOR_SEARCH_STRESS_SECONDS %e' bash -lc '
set -euo pipefail
qs=("vector-api.service" "EADDRINUSE" "node-fishbowl" "RingCentral" ":8787")
n=100
for i in $(seq 1 $n); do
  q=${qs[$(( (i-1) % ${#qs[@]} ))]}
  python3 -c "from hypermemory.__main__ import main; import sys; sys.exit(main([\"--workspace\", \"'$WORKSPACE'\", \"vector\", \"search\", \"--query\", q, \"--limit\", \"5\"]))" >/dev/null
done
'
else
  say "(skip) local vector: DATABASE_URL not set"
fi

say "OK"
