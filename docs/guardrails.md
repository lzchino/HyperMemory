# Guardrails (Memory Fortress style)

The key difference between "I saved notes" and an actual memory system is enforcement.

## Pre-response evidence check
Before answering any question that depends on prior context (decisions, todos, IDs/ports/paths):
- check message buffer + session state + daily log presence
- if gaps detected → force retrieval

## Retrieval ordering (recommended)
1) **SQLite FTS/entity** — fastest, best for exact facts.
2) **pgvector+CUDA** — best for meaning/context.
3) Optional fallbacks — BM25 / ChromaDB only if needed.

## After meaningful work
Run a checkpoint:
- roll up tagged bullets from daily logs into curated memory
- rebuild derived indexes
- snapshot `MEMORY.md`

## Eval harness
Run periodic evaluations (regression checks) so retrieval doesn’t silently degrade.
