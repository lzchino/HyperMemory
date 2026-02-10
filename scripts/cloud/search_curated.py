#!/usr/bin/env python3
"""Cloud L3 search (curated-only) using BYO Postgres + pgvector.

Env:
  HYPERMEMORY_CLOUD_DATABASE_URL (required)
  HYPERMEMORY_CLOUD_NAMESPACE (default: default)
  HYPERMEMORY_CLOUD_EMBED_URL (default: http://127.0.0.1:8080)
  HYPERMEMORY_CLOUD_MODEL_ID (default: local)

Outputs lines:
  [score] sha=<content_sha> M<score> <content>
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
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args()

    db_url = os.environ.get("HYPERMEMORY_CLOUD_DATABASE_URL")
    if not db_url:
        print("ERROR: HYPERMEMORY_CLOUD_DATABASE_URL missing", file=sys.stderr)
        return 2

    namespace = os.environ.get("HYPERMEMORY_CLOUD_NAMESPACE", "default")
    embed_url = os.environ.get("HYPERMEMORY_CLOUD_EMBED_URL", "http://127.0.0.1:8080")
    model_id = os.environ.get("HYPERMEMORY_CLOUD_MODEL_ID", "local")

    qvec = embed_one(embed_url, "query: " + args.query)

    with psycopg.connect(db_url) as con:
        register_vector(con)
        cur = con.execute(
            """
            SELECT e.content_sha, i.score, i.content,
                   1 - (e.embedding <=> %s) AS sim
            FROM hm_cloud_embedding e
            JOIN hm_cloud_item i
              ON i.namespace=e.namespace AND i.content_sha=e.content_sha
            WHERE e.namespace=%s AND e.model_id=%s
            ORDER BY e.embedding <=> %s
            LIMIT %s;
            """,
            (qvec, namespace, model_id, qvec, args.limit),
        )
        rows = cur.fetchall()

    for sha, score, content, sim in rows:
        print(f"[{float(sim):.4f}] sha={sha} M{int(score)} {content}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
