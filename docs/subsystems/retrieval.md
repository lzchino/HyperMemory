# Subsystem: Retrieval

Retrieval is designed to be correct under production queries.

## Entry points
- `scripts/memory-retrieve.sh` — orchestrator
- `scripts/memory-search.sh` — SQLite FTS wrapper

## Layers
1) SQLite FTS (`memory/supermemory.sqlite`)
2) Local pgvector semantic search (`DATABASE_URL`)
3) BM25-ish fallback (`scripts/retrieval/bm25_search.py`)
4) Cloud curated fallback (`scripts/cloud/search_curated.py`) when enabled

## Fusion
- Reciprocal Rank Fusion (RRF) combines signals.

## Notes
- Exact lookups (IDs/ports/paths) should be solved by FTS/BM25.
- Semantic search should be used for broader context.
