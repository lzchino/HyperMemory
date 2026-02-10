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


def init_db(con: sqlite3.Connection, full_rebuild: bool = False) -> None:
    """Initialize schema.

    If full_rebuild=True, drops and recreates tables.
    Otherwise creates tables if missing.
    """

    con.execute("PRAGMA journal_mode=WAL;")

    if full_rebuild:
        con.executescript(
            """
            DROP TABLE IF EXISTS entry;
            DROP TABLE IF EXISTS entry_fts;
            DROP TABLE IF EXISTS doc_state;
            """
        )

    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS doc_state (
          doc_id TEXT PRIMARY KEY,
          fingerprint TEXT NOT NULL,
          updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS entry (
          id INTEGER PRIMARY KEY,
          doc_id TEXT NOT NULL,
          source TEXT NOT NULL,
          source_key TEXT NOT NULL,
          chunk_ix INTEGER NOT NULL,
          text TEXT NOT NULL,
          UNIQUE(source, source_key, chunk_ix)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(
          text,
          source UNINDEXED,
          source_key UNINDEXED,
          chunk_ix UNINDEXED,
          content='entry',
          content_rowid='id'
        );
        """
    )


def upsert_entry(con: sqlite3.Connection, doc_id: str, source: str, source_key: str, chunk_ix: int, text: str) -> None:
    """Upsert an entry and keep FTS in sync."""

    # Try update first
    cur = con.execute(
        "SELECT id, text FROM entry WHERE source=? AND source_key=? AND chunk_ix=?",
        (source, source_key, chunk_ix),
    )
    row = cur.fetchone()
    if row:
        rid, old_text = int(row[0]), str(row[1])
        if old_text != text:
            con.execute(
                "UPDATE entry SET doc_id=?, text=? WHERE id=?",
                (doc_id, text, rid),
            )
            con.execute(
                "INSERT INTO entry_fts(entry_fts, rowid, text, source, source_key, chunk_ix) VALUES('delete', ?, '', '', '', '')",
                (rid,),
            )
            con.execute(
                "INSERT INTO entry_fts(rowid, text, source, source_key, chunk_ix) VALUES (?,?,?,?,?)",
                (rid, text, source, source_key, chunk_ix),
            )
        return

    # Insert new
    cur2 = con.execute(
        "INSERT INTO entry(doc_id, source, source_key, chunk_ix, text) VALUES (?,?,?,?,?)",
        (doc_id, source, source_key, chunk_ix, text),
    )
    rid2 = cur2.lastrowid
    con.execute(
        "INSERT INTO entry_fts(rowid, text, source, source_key, chunk_ix) VALUES (?,?,?,?,?)",
        (rid2, text, source, source_key, chunk_ix),
    )



def _fingerprint_for_path(p: Path) -> str:
    st = p.stat()
    return f"{p.name}:{st.st_mtime_ns}:{st.st_size}"


def index_memory_md(repo: Path, con: sqlite3.Connection, force: bool = False) -> None:
    p = repo / "MEMORY.md"
    if not p.exists():
        return

    doc_id = "MEMORY.md"
    fp = _fingerprint_for_path(p)
    if not force:
        cur = con.execute("SELECT fingerprint FROM doc_state WHERE doc_id=?", (doc_id,))
        r = cur.fetchone()
        if r and str(r[0]) == fp:
            return

    # remove old entries for this doc
    cur = con.execute("SELECT id FROM entry WHERE doc_id=?", (doc_id,))
    ids = [int(x[0]) for x in cur.fetchall()]
    for rid in ids:
        con.execute(
            "INSERT INTO entry_fts(entry_fts, rowid, text, source, source_key, chunk_ix) VALUES('delete', ?, '', '', '', '')",
            (rid,),
        )
    con.execute("DELETE FROM entry WHERE doc_id=?", (doc_id,))

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
        upsert_entry(con, doc_id, "memory", heading, ix, text)

    con.execute(
        "INSERT INTO doc_state(doc_id, fingerprint, updated_at) VALUES (?,?,?) ON CONFLICT(doc_id) DO UPDATE SET fingerprint=excluded.fingerprint, updated_at=excluded.updated_at",
        (doc_id, fp, int(stamp_ms())),
    )


def stamp_ms() -> int:
    import time

    return int(time.time() * 1000)


def index_daily(repo: Path, con: sqlite3.Connection, force: bool = False) -> None:
    mdir = repo / "memory"
    if not mdir.exists():
        return

    seen_doc_ids: set[str] = set()

    for f in sorted(mdir.glob("????-??-??.md")):
        if not DAILY_NAME_RE.match(f.name):
            continue
        doc_id = f"memory/{f.name}"
        seen_doc_ids.add(doc_id)
        fp = _fingerprint_for_path(f)

        if not force:
            cur = con.execute("SELECT fingerprint FROM doc_state WHERE doc_id=?", (doc_id,))
            r = cur.fetchone()
            if r and str(r[0]) == fp:
                continue

        # remove old entries for this doc
        cur = con.execute("SELECT id FROM entry WHERE doc_id=?", (doc_id,))
        ids = [int(x[0]) for x in cur.fetchall()]
        for rid in ids:
            con.execute(
                "INSERT INTO entry_fts(entry_fts, rowid, text, source, source_key, chunk_ix) VALUES('delete', ?, '', '', '', '')",
                (rid,),
            )
        con.execute("DELETE FROM entry WHERE doc_id=?", (doc_id,))

        day = f.stem
        ix = 0
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            bm = BULLET_RE.match(line)
            if not bm:
                continue
            text = bm.group(1).strip()
            if not text:
                continue
            upsert_entry(con, doc_id, "daily", day, ix, text)
            ix += 1

        con.execute(
            "INSERT INTO doc_state(doc_id, fingerprint, updated_at) VALUES (?,?,?) ON CONFLICT(doc_id) DO UPDATE SET fingerprint=excluded.fingerprint, updated_at=excluded.updated_at",
            (doc_id, fp, int(stamp_ms())),
        )

    # delete doc_state rows for removed daily files
    cur = con.execute("SELECT doc_id FROM doc_state WHERE doc_id LIKE 'memory/%'")
    for (doc_id,) in cur.fetchall():
        if str(doc_id) not in seen_doc_ids:
            # delete entries and state
            cur2 = con.execute("SELECT id FROM entry WHERE doc_id=?", (doc_id,))
            ids = [int(x[0]) for x in cur2.fetchall()]
            for rid in ids:
                con.execute(
                    "INSERT INTO entry_fts(entry_fts, rowid, text, source, source_key, chunk_ix) VALUES('delete', ?, '', '', '', '')",
                    (rid,),
                )
            con.execute("DELETE FROM entry WHERE doc_id=?", (doc_id,))
            con.execute("DELETE FROM doc_state WHERE doc_id=?", (doc_id,))



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--force", action="store_true", help="Reindex docs even if unchanged")
    ap.add_argument("--full-rebuild", action="store_true", help="Drop and recreate tables")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    db = repo / "memory" / "supermemory.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db))
    try:
        # Auto-migrate from older schema by forcing a full rebuild if needed.
        if not args.full_rebuild:
            try:
                cols = [r[1] for r in con.execute("PRAGMA table_info(entry)").fetchall()]
                if cols and "doc_id" not in cols:
                    args.full_rebuild = True
            except Exception:
                pass

        init_db(con, full_rebuild=args.full_rebuild)
        index_memory_md(repo, con, force=args.force)
        index_daily(repo, con, force=args.force)
        con.commit()
    finally:
        con.close()

    print(str(db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
