# pgvector semantic index

HyperMemory uses Postgres + pgvector as a semantic index.

## Schema (example)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS hypermemory_embedding (
  id bigserial PRIMARY KEY,
  source_type text NOT NULL,
  source_key text NOT NULL,
  chunk_ix integer NOT NULL,
  content text NOT NULL,
  content_sha text NOT NULL,
  embedding vector(384) NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(source_type, source_key, chunk_ix)
);

CREATE INDEX IF NOT EXISTS hypermemory_embedding_ivfflat
  ON hypermemory_embedding USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

## Query

Cosine distance operator (pgvector):

```sql
SELECT
  source_type, source_key, chunk_ix, content,
  1 - (embedding <=> $1) AS score
FROM hypermemory_embedding
ORDER BY embedding <=> $1
LIMIT 10;
```

## Notes
- If your embedding model changes dimensions, you need a new table or migration.
- `ivfflat` requires `ANALYZE` and enough rows to be effective.
