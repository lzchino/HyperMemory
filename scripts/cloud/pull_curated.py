#!/usr/bin/env python3
"""Pull curated items from BYO Postgres Cloud L3 into local staging.

This does NOT modify MEMORY.md automatically.
It appends to memory/staging/MEMORY.cloud.md for review.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=os.environ.get("OPENCLAW_WORKSPACE", "."))
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    db_url = os.environ.get("HYPERMEMORY_CLOUD_DATABASE_URL")
    if not db_url:
        print("ERROR: HYPERMEMORY_CLOUD_DATABASE_URL missing", file=sys.stderr)
        return 2

    namespace = os.environ.get("HYPERMEMORY_CLOUD_NAMESPACE", "default")

    out_dir = ws / "memory" / "staging"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "MEMORY.cloud.md"

    with psycopg.connect(db_url) as con:
        cur = con.execute(
            """
            SELECT content_sha, score, content
            FROM hm_cloud_item
            WHERE namespace=%s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (namespace, args.limit),
        )
        rows = cur.fetchall()

    existing = set()
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("- [sha="):
                existing.add(line.split(" ", 1)[0])

    added = 0
    with out_file.open("a", encoding="utf-8") as f:
        for sha, score, content in rows:
            key = f"- [sha={sha}]"
            if key in existing:
                continue
            f.write(f"- [sha={sha}] [M{score}] {content}\n")
            added += 1

    print(f"Wrote {added} new items to {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
