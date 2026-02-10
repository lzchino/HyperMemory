# Getting Started

This guide installs HyperMemory as a local-first memory system.

## Prerequisites
- Linux/macOS
- Python 3.10+
- `sqlite3` CLI
- (optional) Docker for Postgres+pgvector

## 1) Clone

```bash
git clone https://github.com/lzchino/HyperMemory.git
cd HyperMemory
```

## 2) Install

```bash
./scripts/install.sh
```

## 3) Create memory files

Create:
- `memory/YYYY-MM-DD.md`
- `MEMORY.md`

HyperMemory will index these.

## 4) Build SQLite FTS index

```bash
./scripts/memory-index.sh /path/to/workspace
# or (python-first):
hypermemory --workspace /path/to/workspace index
```

## 5) Retrieve

```bash
OPENCLAW_WORKSPACE=/path/to/workspace ./scripts/memory-retrieve.sh auto "vector-api.service"
# or:
hypermemory --workspace /path/to/workspace retrieve auto "vector-api.service"
```

## 6) Guardrails workflow

Run evidence checks before memory-dependent answers:

```bash
./scripts/monitoring/pre-response-check.sh /path/to/workspace
./scripts/answer-with-guardrails.sh /path/to/workspace "what port is vector-api.service on?"
```

## Optional: semantic retrieval (local pgvector)

1) Start Postgres+pgvector (example via docker-compose):

```bash
docker compose up -d
export DATABASE_URL='postgresql://hypermemory:hypermemory@127.0.0.1:5432/hypermemory'
```

2) Start embeddings server:

```bash
./scripts/run-embeddings.sh
```

3) Index vectors:

```bash
python3 scripts/hypermemory_cuda_vector_index.py --repo /path/to/workspace --daily-days 14
```

## Optional: Cloud L3 (curated-only)

See `docs/cloud/pgvector.md`.
