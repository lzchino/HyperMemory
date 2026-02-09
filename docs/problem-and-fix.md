# Problem → Fix (HyperMemory)

## The problem
We started with a robust *concept* ("write to durable files") but ran into the real-world failure modes:

1) **Compaction amnesia**
- Older chat context gets compacted.
- If decisions/todos aren't written to disk, they're effectively lost.

2) **Brittle retrieval**
- Semantic retrieval that depends on external services (network latency, API keys, rate limits).
- Keyword search that misses context when you don't remember the exact string.

3) **Operational footguns**
- File permissions can silently break indexing.
- Multiple entrypoints drift (scripts vs skills vs system installs).

## The fix (HyperMemory)
HyperMemory combines the best of both worlds:

### Supermemory layer (durable + exact)
- Markdown is source of truth:
  - `memory/YYYY-MM-DD.md`
  - `MEMORY.md`
- SQLite FTS index:
  - `memory/supermemory.sqlite`

### Memory Fortress layer (reliability guardrails)
- Enforced protocol:
  - pre-response evidence check
  - retrieval-before-answering if gaps
  - checkpoint after meaningful work
  - eval harness to detect regressions

### CUDA semantic layer (fast local meaning search)
- Local `mf-embeddings` service generates embeddings on GPU.
- Postgres + pgvector stores and searches those embeddings.
- Retrieval ordering for best latency + correctness:
  1) SQLite FTS/entity
  2) pgvector + CUDA
  3) legacy fallbacks only if needed

## Key operational lesson
If you want this to be "a system" and not "a prompt":
- pin the workflow to files/scripts
- add benchmarks/evals
- prevent permission drift
- make retrieval local-first
