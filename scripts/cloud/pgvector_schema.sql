-- HyperMemory Cloud L3 schema (BYO Postgres + pgvector)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS hm_cloud_item (
  namespace text NOT NULL,
  content_sha text NOT NULL,
  content text NOT NULL,
  score int NOT NULL,
  source_meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(namespace, content_sha)
);

-- Embeddings are a derived index; can be rebuilt.
CREATE TABLE IF NOT EXISTS hm_cloud_embedding (
  namespace text NOT NULL,
  content_sha text NOT NULL,
  model_id text NOT NULL,
  dims int NOT NULL,
  embedding vector NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(namespace, content_sha, model_id)
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS hm_cloud_item_created_at_idx
  ON hm_cloud_item(namespace, created_at DESC);
