# Subsystem: Cloud (L3)

Cloud is optional and curated-only.

## Philosophy
- Cloud stores only curated items (score >= threshold)
- Cloud never replaces local source-of-truth files
- Cloud sync is redacted and allowlisted

## Files
- Curated feed: `memory/staging/MEMORY.pending.md`
- Payload (review): `memory/staging/cloud-push.payload.json`
- Pull output (review): `memory/staging/MEMORY.cloud.md`

## Scripts
- `scripts/cloud/pgvector_init.sh`
- `scripts/cloud/push_curated.py` (two-phase: prepare payload, then `--commit`)
- `scripts/cloud/pull_curated.py`
- `scripts/cloud/search_curated.py`

## Flags
- `HYPERMEMORY_CLOUD_FALLBACK=1` enables retrieval fallback.
