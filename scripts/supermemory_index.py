#!/usr/bin/env python3
"""Build a minimal SQLite FTS index for HyperMemory.

Indexes:
- MEMORY.md bullets (section heading as source_key)
- memory/YYYY-MM-DD.md bullets (date as source_key)

Output:
- memory/supermemory.sqlite

This is a public, simplified variant of the internal indexer.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

DAILY_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
BULLET_RE = re.compile(r"^\s*-\s*(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        PRAGMA journal_mode=WAL;
        DROP TABLE IF EXISTS entry;
        DROP TABLE IF EXISTS entry_fts;

        CREATE TABLE entry (
          id INTEGER PRIMARY KEY,
          source TEXT NOT NULL,
          source_key TEXT NOT NULL,
          chunk_ix INTEGER NOT NULL,
          text TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE entry_fts USING fts5(
          text,
          source UNINDEXED,
          source_key UNINDEXED,
          chunk_ix UNINDEXED,
          content='entry',
          content_rowid='id'
        );
        """
    )


def add_entry(con: sqlite3.Connection, source: str, source_key: str, chunk_ix: int, text: str) -> None:
    cur = con.execute(
        "INSERT INTO entry(source, source_key, chunk_ix, text) VALUES (?,?,?,?)",
        (source, source_key, chunk_ix, text),
    )
    rid = cur.lastrowid
    con.execute(
        "INSERT INTO entry_fts(rowid, text, source, source_key, chunk_ix) VALUES (?,?,?,?,?)",
        (rid, text, source, source_key, chunk_ix),
    )


def index_memory_md(repo: Path, con: sqlite3.Connection) -> None:
    p = repo / "MEMORY.md"
    if not p.exists():
        return

    heading = "(root)"
    ix_by_heading: dict[str, int] = {}

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
        add_entry(con, "memory", heading, ix, text)


def index_daily(repo: Path, con: sqlite3.Connection) -> None:
    mdir = repo / "memory"
    if not mdir.exists():
        return

    for f in sorted(mdir.glob("????-??-??.md")):
        if not DAILY_NAME_RE.match(f.name):
            continue
        day = f.stem
        ix = 0
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            bm = BULLET_RE.match(line)
            if not bm:
                continue
            text = bm.group(1).strip()
            if not text:
                continue
            add_entry(con, "daily", day, ix, text)
            ix += 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    db = repo / "memory" / "supermemory.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db))
    try:
        init_db(con)
        index_memory_md(repo, con)
        index_daily(repo, con)
        con.commit()
    finally:
        con.close()

    print(str(db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
