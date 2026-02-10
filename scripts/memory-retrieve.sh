#!/usr/bin/env bash
set -euo pipefail

# HyperMemory retrieval orchestrator (public reference)
#
# Retrieval ordering + fusion:
#   1) SQLite FTS (exact)
#   2) pgvector (semantic) when available
#   3) BM25-ish keyword fallback
#
# Results are fused with Reciprocal Rank Fusion (RRF) for better recall.

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

WORKSPACE="${OPENCLAW_WORKSPACE:-$ROOT}"
DB="$WORKSPACE/memory/supermemory.sqlite"

export FTS_OUT=""
export VEC_OUT=""
export BM25_OUT=""

# --- collect FTS ---
if [[ -f "$DB" ]]; then
  FTS_OUT=$("$ROOT/scripts/memory-search.sh" "$QUERY" 2>/dev/null | head -n 20 || true)
  export FTS_OUT
fi

# --- collect vector (pgvector) ---
if [[ -n "${DATABASE_URL:-}" ]]; then
  VEC_OUT=$(python3 "$ROOT/scripts/hypermemory_cuda_vector_search.py" "$QUERY" --limit 10 2>/dev/null || true)
  export VEC_OUT
fi

# --- collect BM25-ish ---
if $HYBRID; then
  if [[ -f "$ROOT/scripts/retrieval/bm25_search.py" ]]; then
    BM25_OUT=$(python3 "$ROOT/scripts/retrieval/bm25_search.py" --repo "$WORKSPACE" "$QUERY" --limit 10 2>/dev/null || true)
    export BM25_OUT
  fi
fi

# --- optional cloud fallback (curated-only) ---
# Enabled only when explicitly requested.
CLOUD_OUT=""
if [[ "${HYPERMEMORY_CLOUD_FALLBACK:-0}" = "1" ]]; then
  if [[ -n "${HYPERMEMORY_CLOUD_DATABASE_URL:-}" ]]; then
    CLOUD_OUT=$(HYPERMEMORY_CLOUD_DATABASE_URL="$HYPERMEMORY_CLOUD_DATABASE_URL" \
      HYPERMEMORY_CLOUD_NAMESPACE="${HYPERMEMORY_CLOUD_NAMESPACE:-default}" \
      HYPERMEMORY_CLOUD_EMBED_URL="${HYPERMEMORY_CLOUD_EMBED_URL:-http://127.0.0.1:8080}" \
      HYPERMEMORY_CLOUD_MODEL_ID="${HYPERMEMORY_CLOUD_MODEL_ID:-local}" \
      python3 "$ROOT/scripts/cloud/search_curated.py" "$QUERY" --limit 8 2>/dev/null || true)
    export CLOUD_OUT
  fi
fi

# --- RRF fuse + print ---
python3 - "$MODE" "$QUERY" <<'PY'
import os,sys

mode=sys.argv[1]
query=sys.argv[2]
fts=os.environ.get('FTS_OUT','')
vec=os.environ.get('VEC_OUT','')
bm25=os.environ.get('BM25_OUT','')
cloud=os.environ.get('CLOUD_OUT','')

k=60.0
items = {}

def add(layer, rank, key, snippet):
    it=items.get(key)
    if not it:
        it={'snippet':snippet,'ranks':{}}
        items[key]=it
    it['ranks'][layer]=min(rank, it['ranks'].get(layer, 10**9))
    if snippet and (not it['snippet'] or len(snippet)>len(it['snippet'])):
        it['snippet']=snippet

# FTS: source | source_key | chunk_ix | text
for i,line in enumerate([l for l in fts.splitlines() if l.strip()]):
    parts=[p.strip() for p in line.split('|',3)]
    if len(parts)<4: continue
    src, sk, ix, text = parts[0], parts[1], parts[2], parts[3]
    key=f"fts:{src}:{sk}#{ix}"
    add('fts', i+1, key, text)

# Vector: [sim] daily:DATE#ix ...
for i,line in enumerate([l for l in vec.splitlines() if l.strip()]):
    if not line.startswith('['):
        continue
    rest=line.split(']',1)[1].strip() if ']' in line else line
    token=rest.split(' ',1)[0]
    key=f"vec:{token}"
    add('vec', i+1, key, rest)

# BM25: score\tpath\tsnippet
for i,line in enumerate([l for l in bm25.splitlines() if l.strip()]):
    parts=line.split('\t',2)
    if len(parts)<3: continue
    _score, path, snippet = parts
    key=f"bm25:{path}#{i}"
    add('bm25', i+1, key, snippet)

# Cloud curated: [sim] sha=... M3 content
for i,line in enumerate([l for l in cloud.splitlines() if l.strip()]):
    if not line.startswith('['):
        continue
    rest=line.split(']',1)[1].strip() if ']' in line else line
    key=f"cloud:{i}"
    add('cloud', i+1, key, rest)

scored=[]
for key,it in items.items():
    score=0.0
    for layer, r in it['ranks'].items():
        score += 1.0/(k + float(r))
    scored.append((score,key,it))

scored.sort(key=lambda x: x[0], reverse=True)

print("-- FUSED TOP --")
for score,key,it in scored[:10]:
    ranks=' '.join([f"{l}:{it['ranks'][l]}" for l in sorted(it['ranks'])])
    print(f"[{score:.4f}] {ranks} {it['snippet'][:220]}")

print("")
print("-- RAW FTS --")
print(fts or "(none)")
print("")
print("-- RAW VECTOR --")
print(vec or "(none)")
print("")
print("-- RAW BM25 --")
print(bm25 or "(none)")
print("")
print("-- RAW CLOUD --")
print(cloud or "(none)")
PY
