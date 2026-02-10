# Migration (v1 -> HyperMemory)

This repo supports a simple, non-destructive migration path.

## Quick migrate

```bash
./scripts/migrate-from-v1.sh --src /path/to/v1/workspace --dst /path/to/new/workspace
```

What it does:
- copies `memory/YYYY-MM-DD.md` files
- copies `MEMORY.md` if present
- rebuilds the SQLite FTS index in the destination

## pgvector data

If your v1 used a vector DB, re-embed and rebuild vectors in the new stack.
This repo treats vectors as a derived index.
