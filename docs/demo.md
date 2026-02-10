# Demo (60 seconds)

This is a quick manual demo you can run in a HyperMemory workspace.

## 1) Start Postgres+pgvector

If using docker compose:

```bash
docker compose up -d
```

Export `DATABASE_URL` (see `docker-compose.yml`).

## 2) Start the CUDA embedding server

```bash
./scripts/install.sh --embeddings-only
./scripts/run-embeddings.sh
curl -s http://127.0.0.1:8080/health
```

## 3) Create sample memory

```bash
mkdir -p memory
cp -a examples/workspace/memory/2026-02-09.md.example memory/2026-02-09.md
cp -a examples/workspace/MEMORY.md.example MEMORY.md
```

## 4) Build indexes

```bash
./scripts/memory-index.sh
# semantic (local pgvector, curated+distilled only)
# Requires: DATABASE_URL + MF_EMBED_URL
hypermemory --workspace . vector index
```

## 5) Retrieve

Exact (FTS):
```bash
./scripts/memory-search.sh "vector-api.service"
```

Semantic (CUDA+pgvector):
```bash
hypermemory --workspace . vector search --query "vector api service" --limit 5
```

Orchestrated:
```bash
./scripts/memory-retrieve.sh auto "vector api service"
```
