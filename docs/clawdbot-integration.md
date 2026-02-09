# Clawdbot integration (HyperMemory)

This page shows how to integrate HyperMemory into a Clawdbot deployment.

> Security note: do **not** publish your real `memory/` or `MEMORY.md` contents, or any `.env`/tokens.

## What HyperMemory expects

A Clawdbot agent workspace directory (example: `/home/luis/clawd`) containing:

- `memory/YYYY-MM-DD.md` — daily log (UTC)
- `MEMORY.md` — curated long-term memory

And scripts to:
- rebuild an SQLite FTS index for exact lookup
- index/query semantic memory via pgvector + local embeddings (CUDA)

## Recommended service layout

### 1) Workspace (source of truth)

```
/home/<user>/clawd/
  MEMORY.md
  memory/
    2026-02-09.md
    eval-queries.jsonl
    supermemory.sqlite
```

### 2) System-level retrieval orchestration

Option A (recommended): install the retrieval orchestrator as a system-level bundle, e.g.

- `/opt/hypermemory/scripts/retrieval/memory-retrieve.sh`

This script can be invoked from guardrails (pre-response checks) and can call into
workspace scripts.

### 3) Local embeddings service (CUDA)

Run `mf-embeddings` locally on loopback:
- `http://127.0.0.1:8080/health`
- `http://127.0.0.1:8080/embed`

Keep it bound to `127.0.0.1` unless you have a strong reason not to.

## Guardrails: enforce retrieval-before-answering

Clawdbot doesn’t (yet) intercept every user message via a hook event, so the practical
approach is to **inject an enforced protocol** into the agent bootstrap context.

### Hook idea: bootstrap protocol injection

Create a Clawdbot hook listening to `agent:bootstrap` that adds a virtual file like:

```
# HyperMemory Protocol — ENFORCED

When answering anything that depends on prior context (decisions, status, todos,
IDs/paths/ports, where something is, etc.), do NOT guess.

1) Evidence check:
   bash /opt/hypermemory/scripts/monitoring/pre-response-check.sh

2) If gaps detected, retrieve before answering:
   OPENCLAW_WORKSPACE=<workspace> bash /opt/hypermemory/scripts/retrieval/memory-retrieve.sh auto "<query>"

3) After meaningful work:
   <workspace>/scripts/memory_checkpoint.sh <workspace>
```

### Retrieval ordering (recommended)

Inside `memory-retrieve.sh`, prefer:
1) SQLite FTS/entity (fast exact)
2) pgvector + CUDA embeddings (fast semantic)
3) only then optional fallbacks (BM25/Chroma)

## Checkpointing

After meaningful work (or before reboot), run a checkpoint script that:
- rolls up tagged bullets from daily logs into `MEMORY.md`
- rebuilds `memory/supermemory.sqlite`
- optionally runs a small eval harness
- snapshots `MEMORY.md`

## Testing

- Exact retrieval: search for a known ID/port/path.
- Semantic retrieval: search for a concept without exact wording.
- Guardrail test: ask a memory-dependent question and verify retrieval happens before answering.

## Minimal benchmark

See `scripts/benchmark.sh` in this repo.
