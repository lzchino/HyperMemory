# Configuration

HyperMemory uses environment variables for configuration.

## Workspace
- `OPENCLAW_WORKSPACE` — workspace root (defaults to current directory)

## Local semantic layer (pgvector)
- `DATABASE_URL` — Postgres connection URL for local pgvector
- `MF_EMBED_URL` — embeddings server base URL (default: `http://127.0.0.1:8080`)

## Embeddings server
- `EMBED_MODEL_ID` — sentence-transformers model id (default: `intfloat/e5-small-v2`)
- `EMBED_DEVICE` — `cuda|mps|cpu` (default: auto-detect)
- `EMBED_HOST` — default `127.0.0.1`
- `EMBED_PORT` — default `8080`

## Cloud L3 (BYO pgvector)
- `HYPERMEMORY_CLOUD_DATABASE_URL` — required for cloud
- `HYPERMEMORY_CLOUD_NAMESPACE` — namespace partition (default: `default`)
- `HYPERMEMORY_CLOUD_SYNC_THRESHOLD` — minimum score to sync (default: `3`)
- `HYPERMEMORY_CLOUD_EMBED_URL` — embeddings server URL used for cloud embeddings (default: `http://127.0.0.1:8080`)
- `HYPERMEMORY_CLOUD_MODEL_ID` — model id label stored in cloud (default: `local`)
- `HYPERMEMORY_CLOUD_FALLBACK` — if `1`, retrieval will include cloud curated fallback
- `HYPERMEMORY_CLOUD_ALLOWLIST` — if `1` (default), cloud push skips unsafe items

## Eval gating
- `MIN_RECALL` — if >0, `scripts/memory-eval.sh` fails if recall < MIN_RECALL
