from __future__ import annotations

"""Local pgvector semantic index/search for curated+distilled chunks.

This uses an external embeddings server (mf-embeddings compatible):
- GET /health
- POST /embed {"inputs": [..]}

Dependencies: psycopg + pgvector (kept in base package).
"""

import argparse
import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import psycopg
from pgvector.psycopg import register_vector
from pgvector import Vector

from .chunks import Chunk, iter_semantic_chunks


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_json(url: str, payload: dict | None = None, timeout: float = 30.0):
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def embed_texts(embed_base_url: str, texts: List[str]) -> List[List[float]]:
    return http_json(f"{embed_base_url.rstrip('/')}/embed", {"inputs": texts})


def embed_one(embed_base_url: str, text: str) -> Vector:
    v = http_json(f"{embed_base_url.rstrip('/')}/embed", {"inputs": [text]})
    return Vector(v[0])


@dataclass
class LocalVectorConfig:
    database_url: str
    embed_url: str
    model_id: str

    @staticmethod
    def from_env() -> "LocalVectorConfig":
        db = os.environ.get("DATABASE_URL")
        if not db:
            raise ValueError("DATABASE_URL missing")
        return LocalVectorConfig(
            database_url=db,
            embed_url=os.environ.get("MF_EMBED_URL", "http://127.0.0.1:8080"),
            model_id=os.environ.get("HYPERMEMORY_LOCAL_MODEL_ID", "local"),
        )


def ensure_schema(con: psycopg.Connection, dims: int) -> None:
    con.execute("CREATE EXTENSION IF NOT EXISTS vector")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS hm_local_embedding (
          id bigserial PRIMARY KEY,
          doc_id text NOT NULL,
          source text NOT NULL,
          source_key text NOT NULL,
          chunk_ix integer NOT NULL,
          content text NOT NULL,
          content_sha text NOT NULL,
          model_id text NOT NULL,
          dims int NOT NULL,
          embedding vector NOT NULL,
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(doc_id, source_key, chunk_ix, model_id)
        );
        """
    )


def index_workspace(workspace: Path, cfg: LocalVectorConfig, include_pending: bool = False, batch: int = 64) -> int:
    chunks = iter_semantic_chunks(workspace, include_pending=include_pending)
    if not chunks:
        return 0

    # determine dims
    dims = len(embed_texts(cfg.embed_url, ["dim-probe"])[0])

    with psycopg.connect(cfg.database_url) as con:
        register_vector(con)
        ensure_schema(con, dims)

        pushed = 0
        for i in range(0, len(chunks), batch):
            b = chunks[i : i + batch]
            vecs = embed_texts(cfg.embed_url, ["passage: " + c.text for c in b])
            for c, v in zip(b, vecs):
                con.execute(
                    """
                    INSERT INTO hm_local_embedding(doc_id, source, source_key, chunk_ix, content, content_sha, model_id, dims, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (doc_id, source_key, chunk_ix, model_id)
                    DO UPDATE SET
                      content=excluded.content,
                      content_sha=excluded.content_sha,
                      dims=excluded.dims,
                      embedding=excluded.embedding,
                      updated_at=now()
                    WHERE hm_local_embedding.content_sha <> excluded.content_sha;
                    """,
                    (c.doc_id, c.source, c.source_key, c.chunk_ix, c.text, sha256(c.text), cfg.model_id, dims, v),
                )
                pushed += 1
            con.commit()

    return pushed


def search_workspace(cfg: LocalVectorConfig, query: str, limit: int = 8) -> list[str]:
    qvec = embed_one(cfg.embed_url, "query: " + query)

    with psycopg.connect(cfg.database_url) as con:
        register_vector(con)
        cur = con.execute(
            """
            SELECT doc_id, source_key, chunk_ix, content, 1 - (embedding <=> %s) AS sim
            FROM hm_local_embedding
            WHERE model_id=%s
            ORDER BY embedding <=> %s
            LIMIT %s;
            """,
            (qvec, cfg.model_id, qvec, int(limit)),
        )
        rows = cur.fetchall()

    return [f"[{float(sim):.4f}] {r[0]}:{r[1]}#{r[2]} {r[3]}" for r in rows]
