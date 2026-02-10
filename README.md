# HyperMemory

**HyperMemory = durable markdown memory (Supermemory) + Memory Fortress guardrails + local CUDA-accelerated semantic search.**

This repo is a cleaned-up, public-friendly writeup + install guide for the system we built on a real Clawdbot deployment.

## Why this exists

LLM assistants fail in predictable ways:
- they *guess* when they should retrieve evidence
- they forget decisions after compaction/restarts
- semantic retrieval is slow/remote (network-bound) or brittle

HyperMemory solves that by combining:

1) **Durable source-of-truth files**
- `memory/YYYY-MM-DD.md` (UTC daily log)
- `MEMORY.md` (curated long-term)

2) **Fast exact retrieval (SQLite FTS)**
- builds `memory/supermemory.sqlite`
- best for IDs / ports / paths / exact terms

3) **Fast semantic retrieval (pgvector + CUDA embeddings)**
- local embedding service (FastAPI + sentence-transformers) running on CUDA
- vectors stored in Postgres (pgvector)
- local-first: avoids OpenAI embeddings latency

4) **Memory Fortress-style guardrails**
- pre-response evidence check (`./scripts/monitoring/pre-response-check.sh`)
- retrieval-before-answering when gaps are detected
- periodic checkpoint (`./scripts/checkpoint.sh`) + eval harness

## Architecture (high level)

```
User message
   |
   v
Pre-response check (guardrails)
   |
   +--> if gaps -> retrieval pipeline
           |
           +--> SQLite FTS/entity (fast exact)
           +--> pgvector+CUDA (fast semantic)
           +--> optional legacy fallbacks (BM25/Chroma)
   |
   v
Assistant responds with evidence
   |
   v
Checkpoint -> rollup tagged items -> rebuild indexes
```

## Quickstart (full distro)

## Docs

- Architecture: `docs/architecture.md`
- Getting started: `docs/getting-started.md`
- Configuration: `docs/configuration.md`
- Troubleshooting: `docs/troubleshooting.md`
- Guardrails: `docs/guardrails.md`
- Cloud L3: `docs/cloud/pgvector.md`
- Subsystems:
  - `docs/subsystems/core.md`
  - `docs/subsystems/retrieval.md`
  - `docs/subsystems/monitoring.md`
  - `docs/subsystems/maintenance.md`
  - `docs/subsystems/cloud.md`
- Protocols:
  - `docs/protocols/guardrails.md`
  - `docs/protocols/cloud-sync.md`


### Prereqs
- Ubuntu 24.04+ (or similar)
- Python 3.10+
- Docker (recommended for Postgres+pgvector)
- NVIDIA GPU + CUDA (optional)
- Apple Silicon (MPS) supported
- CPU fallback supported (slower)

### 1) Clone

```bash
git clone https://github.com/lzchino/HyperMemory.git
cd HyperMemory
```

### 2) Install Python deps

```bash
# full install (includes sentence-transformers)
./scripts/install.sh

# lightweight (no sentence-transformers; good for CI + FTS/entity + pgvector with fake embeddings)
./scripts/install.sh --embeddings-only
```

### 3) Start Postgres+pgvector

```bash
docker compose up -d
export DATABASE_URL='postgresql://hypermemory:hypermemory@127.0.0.1:5432/hypermemory'
```

### 4) Start the local embeddings server

```bash
./scripts/run-embeddings.sh
curl -s http://127.0.0.1:8080/health
```

### 5) Create a workspace (example)

```bash
mkdir -p memory
cp -a examples/workspace/memory/2026-02-09.md.example memory/2026-02-09.md
cp -a examples/workspace/MEMORY.md.example MEMORY.md
```

### 6) Index + retrieve

```bash
./scripts/memory-index.sh
./scripts/memory-retrieve.sh auto "vector api service"

# semantic (local pgvector, curated+distilled only)
# Requires: DATABASE_URL + MF_EMBED_URL
hypermemory --workspace . vector index
hypermemory --workspace . vector search --query "vector api service" --limit 5
```

### 7) Benchmark

```bash
./scripts/benchmark.sh .
```

More: `docs/demo.md`

## Benchmarks (from a real deployment)

Example results (your numbers will vary):
- FTS index rebuild: ~1s
- FTS retrieval: ~30ms/call
- CUDA vector index (14 days + curated memory): ~30–40s
- CUDA vector search: ~180ms/search
- Orchestrator (FTS → CUDA → fallback): ~250ms/call

## Security / redactions

This repo intentionally does **not** include:
- `MEMORY.md` content
- `memory/` daily logs
- any `.env` or tokens
- any phone numbers / internal IPs

## License
MIT
