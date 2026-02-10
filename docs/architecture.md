# Architecture

HyperMemory is a **local-first** memory system for Clawdbot/OpenClaw agents.

It is designed to prevent the most common production failures:
- guessing instead of retrieving
- losing state on compaction/restarts
- exact fact lookup failures (IDs, ports, paths)
- silent regressions (memory quality degrading over time)

## Storage layers

HyperMemory uses a layered model where **Markdown files remain the source of truth** and everything else is a derived index.

### L1 — Daily log (durable write-ahead)
- `memory/YYYY-MM-DD.md`
- Append-only event log.

### L2 — Curated memory
- `MEMORY.md`
- Distilled, long-term facts, preferences, decisions.

### L3 — Cloud (optional, curated-only)
- BYO Postgres + pgvector
- Stores only curated items (score >= threshold) from `memory/staging/MEMORY.pending.md`
- Intended for cross-agent durability and cross-machine recovery.

Docs: `docs/cloud/pgvector.md`

### L4 — Derived indexes (local)
1) **SQLite FTS (exact retrieval)**
   - DB: `memory/supermemory.sqlite`
   - Built from L1+L2
   - Best for IDs / ports / names

2) **Local semantic index (optional)**
   - Postgres + pgvector + embeddings server (`scripts/server.py`)
   - Used for semantic retrieval when configured

3) **BM25-ish keyword fallback**
   - Pure-python fallback search for portability

## Read path (retrieval)

Entry point: `scripts/memory-retrieve.sh`

Ordering:
1) SQLite FTS
2) Local pgvector (if `DATABASE_URL`)
3) BM25 fallback
4) Cloud curated fallback (only if enabled via `HYPERMEMORY_CLOUD_FALLBACK=1`)

Fusion:
- Results are combined using **Reciprocal Rank Fusion (RRF)**.

## Write path

### Raw notes
Write raw events to daily files (`memory/YYYY-MM-DD.md`).

### Curated writes
Curated items are written through:
- `scripts/core/curated-memory-write.sh`

Promoted curated items flow into:
- `memory/staging/MEMORY.pending.md`

### Checkpoint
A checkpoint distills + reindexes + runs eval:
- `scripts/checkpoint.sh`

## Guardrails

HyperMemory guardrails are the enforcement layer that prevents “answering without evidence”.

- Pre-response evidence check:
  - `scripts/monitoring/pre-response-check.sh`

- Suggested workflow:
  - `scripts/answer-with-guardrails.sh`

Docs: `docs/guardrails.md`

## Production invariants

HyperMemory is considered healthy when:
- daily + curated files exist and are readable
- SQLite FTS index is present and up to date
- retrieval produces evidence bundles (not guesses)
- eval suite meets thresholds in CI
- cloud sync (if enabled) is curated-only and redacted
