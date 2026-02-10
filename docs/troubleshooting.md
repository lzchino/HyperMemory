# Troubleshooting

## SQLite search returns (none)
- Build the index:
  - `./scripts/memory-index.sh <workspace>`
- Ensure `OPENCLAW_WORKSPACE` is set when running retrieval/search.

## pgvector returns (none)
- Ensure Postgres is running and `DATABASE_URL` is set.
- Ensure embeddings server is running:
  - `curl http://127.0.0.1:8080/health`
- Rebuild vectors:
  - `python3 scripts/hypermemory_cuda_vector_index.py --repo <workspace>`

## Cloud push doesn’t write
- Ensure `HYPERMEMORY_CLOUD_DATABASE_URL` is set.
- Ensure staged curated items exist:
  - `memory/staging/MEMORY.pending.md`
- Run prepare step, inspect payload:
  - `python3 scripts/cloud/push_curated.py --workspace <ws>`
- Then commit:
  - `python3 scripts/cloud/push_curated.py --workspace <ws> --commit`
- If allowlist skips items, check:
  - `memory/cloud-redaction.jsonl`

## CI failures
- ShellCheck: ensure only shell scripts are scanned.
- pgvector service image tag: `pgvector/pgvector:pg16` is used.
