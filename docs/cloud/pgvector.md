# Cloud L3 (BYO Postgres + pgvector)

HyperMemory supports an optional cloud layer for **curated-only** durability and cross-agent sync.

## Philosophy
- Local files remain source of truth
- Cloud is a derived index / backup for curated items
- Default policy: **curated-only** (score >= 3)

## Configure

Set these env vars:

- `HYPERMEMORY_CLOUD_DATABASE_URL` (required)
- `HYPERMEMORY_CLOUD_NAMESPACE` (optional; default `default`)
- `HYPERMEMORY_CLOUD_SYNC_THRESHOLD` (optional; default `3`)
- `HYPERMEMORY_CLOUD_EMBED_URL` (optional; default `http://127.0.0.1:8080`)

## Initialize schema

```bash
./scripts/cloud/pgvector_init.sh
```

## Push curated (staging-only)

Curated feed:
- `memory/staging/MEMORY.pending.md`

```bash
./scripts/cloud/push_curated.sh /path/to/workspace
```

## Pull curated (review-only)

```bash
./scripts/cloud/pull_curated.sh /path/to/workspace
```

This writes to `memory/staging/MEMORY.cloud.md`.
