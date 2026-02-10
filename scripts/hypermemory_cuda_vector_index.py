#!/usr/bin/env python3
"""LEGACY (deprecated): Hypermemory CUDA vector index (local embeddings) using Postgres + pgvector.

This script predates the python-first local pgvector implementation.

Prefer:
  hypermemory --workspace <ws> vector index
  hypermemory --workspace <ws> vector search --query "..." --limit N

This legacy script may be removed in a future release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import psycopg
from pgvector.psycopg import register_vector

DAILY_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
BULLET_RE = re.compile(r"^\s*-\s*(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")


@dataclass
class Chunk:
    source_type: str
    source_key: str
    chunk_ix: int
    text: str


def sha(text: str) -> str:
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


def infer_dims(embed_base_url: str) -> int:
    v = embed_texts(embed_base_url, ["dim-probe"])
    return len(v[0])


def iter_daily_files(memory_dir: Path, days: int) -> Iterable[Path]:
    files = sorted([p for p in memory_dir.glob("????-??-??.md") if DAILY_NAME_RE.match(p.name)])
    return files[-days:] if days > 0 else files


def chunks_from_memory_md(repo: Path) -> List[Chunk]:
    p = repo / "MEMORY.md"
    if not p.exists():
        return []

    heading = "(root)"
    ix_by_heading: dict[str, int] = {}
    out: List[Chunk] = []

    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = H2_RE.match(line)
        if m:
            heading = m.group(1).strip()
            continue
        bm = BULLET_RE.match(line)
        if not bm:
            continue
        text = bm.group(1).strip()
        if not text:
            continue
        ix = ix_by_heading.get(heading, 0)
        ix_by_heading[heading] = ix + 1
        out.append(Chunk("memory", heading, ix, text))

    return out


def chunks_from_daily(repo: Path, days: int) -> List[Chunk]:
    mdir = repo / "memory"
    if not mdir.exists():
        return []

    out: List[Chunk] = []
    for f in iter_daily_files(mdir, days=days):
        day = f.stem
        ix = 0
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            bm = BULLET_RE.match(line)
            if not bm:
                continue
            text = bm.group(1).strip()
            if not text:
                continue
            out.append(Chunk("daily", day, ix, text))
            ix += 1

    return out


def ensure_schema(con: psycopg.Connection, dims: int) -> None:
    con.execute("CREATE EXTENSION IF NOT EXISTS vector")
    con.execute(
        f"""
        CREATE TABLE IF NOT EXISTS hypermemory_embedding (
          id bigserial PRIMARY KEY,
          source_type text NOT NULL,
          source_key text NOT NULL,
          chunk_ix integer NOT NULL,
          content text NOT NULL,
          content_sha text NOT NULL,
          embedding vector({dims}) NOT NULL,
          updated_at timestamptz NOT NULL DEFAULT now(),
          UNIQUE(source_type, source_key, chunk_ix)
        );
        """
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--daily-days", type=int, default=14)
    ap.add_argument("--embed-url", default=os.environ.get("MF_EMBED_URL", "http://127.0.0.1:8080"))
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not args.db_url:
        print("ERROR: DATABASE_URL missing", file=sys.stderr)
        return 2

    dims = infer_dims(args.embed_url)
    health = http_json(f"{args.embed_url.rstrip('/')}/health")
    print(f"mf-embeddings: model={health.get('model')} device={health.get('device')} cuda={health.get('cuda')} dims={dims}")

    chunks = chunks_from_memory_md(repo) + chunks_from_daily(repo, days=args.daily_days)
    if not chunks:
        print("No chunks found.")
        return 0

    with psycopg.connect(args.db_url) as con:
        register_vector(con)
        ensure_schema(con, dims)

        for i in range(0, len(chunks), args.batch):
            batch = chunks[i : i + args.batch]
            texts = ["passage: " + ch.text for ch in batch]
            vecs = embed_texts(args.embed_url, texts)

            for ch, vec in zip(batch, vecs):
                con.execute(
                    """
                    INSERT INTO hypermemory_embedding(source_type, source_key, chunk_ix, content, content_sha, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (source_type, source_key, chunk_ix)
                    DO UPDATE SET
                      content=EXCLUDED.content,
                      content_sha=EXCLUDED.content_sha,
                      embedding=EXCLUDED.embedding,
                      updated_at=now()
                    WHERE hypermemory_embedding.content_sha <> EXCLUDED.content_sha;
                    """,
                    (ch.source_type, ch.source_key, ch.chunk_ix, ch.text, sha(ch.text), vec),
                )

            con.commit()
            print(f"indexed {min(i+args.batch, len(chunks))}/{len(chunks)}")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
