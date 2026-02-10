#!/usr/bin/env python3
"""LEGACY (deprecated): Hypermemory CUDA vector search (local embeddings) using Postgres + pgvector.

Prefer:
  hypermemory --workspace <ws> vector search --query "..." --limit N

This legacy script may be removed in a future release.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

import psycopg
from pgvector.psycopg import register_vector
from pgvector import Vector


def http_json(url: str, payload: dict | None = None, timeout: float = 30.0):
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def embed_one(embed_base_url: str, text: str) -> Vector:
    v = http_json(f"{embed_base_url.rstrip('/')}/embed", {"inputs": [text]})
    return Vector(v[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--embed-url", default=os.environ.get("MF_EMBED_URL", "http://127.0.0.1:8080"))
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    if not args.db_url:
        print("ERROR: DATABASE_URL missing", file=sys.stderr)
        return 2

    qvec = embed_one(args.embed_url, "query: " + args.query)

    with psycopg.connect(args.db_url) as con:
        register_vector(con)
        cur = con.execute(
            """
            SELECT source_type, source_key, chunk_ix, content,
                   1 - (embedding <=> %s) AS score
            FROM hypermemory_embedding
            ORDER BY embedding <=> %s
            LIMIT %s;
            """,
            (qvec, qvec, args.limit),
        )
        rows = cur.fetchall()

    for r in rows:
        print(f"[{float(r[4]):.4f}] {r[0]}:{r[1]}#{r[2]} {r[3]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
