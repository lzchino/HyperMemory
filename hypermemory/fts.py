from __future__ import annotations

"""SQLite FTS indexer (deterministic, derived index).

This is the Python-first equivalent of scripts/supermemory_index.py.

Source of truth:
- <workspace>/MEMORY.md
- <workspace>/memory/YYYY-MM-DD.md

Output:
- <workspace>/memory/supermemory.sqlite

Design goals:
- deterministic
- incremental (skip unchanged docs)
- safe migration from older schemas
"""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DAILY_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
BULLET_RE = re.compile(r"^\s*-\s*(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")


def _stamp_ms() -> int:
    import time

    return int(time.time() * 1000)


def _fingerprint_for_path(p: Path) -> str:
    st = p.stat()
    return f"{p.name}:{st.st_mtime_ns}:{st.st_size}"


def _init_db(con: sqlite3.Connection, full_rebuild: bool = False) -> None:
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


def _delete_doc_entries(con: sqlite3.Connection, doc_id: str) -> None:
    cur = con.execute("SELECT id FROM entry WHERE doc_id=?", (doc_id,))
    ids = [int(x[0]) for x in cur.fetchall()]
    for rid in ids:
        con.execute(
            "INSERT INTO entry_fts(entry_fts, rowid, text, source, source_key, chunk_ix) VALUES('delete', ?, '', '', '', '')",
            (rid,),
        )
    con.execute("DELETE FROM entry WHERE doc_id=?", (doc_id,))


def _upsert_entry(con: sqlite3.Connection, doc_id: str, source: str, source_key: str, chunk_ix: int, text: str) -> None:
    cur = con.execute(
        "SELECT id, text FROM entry WHERE source=? AND source_key=? AND chunk_ix=?",
        (source, source_key, chunk_ix),
    )
    row = cur.fetchone()
    if row:
        rid, old_text = int(row[0]), str(row[1])
        if old_text != text:
            con.execute("UPDATE entry SET doc_id=?, text=? WHERE id=?", (doc_id, text, rid))
            con.execute(
                "INSERT INTO entry_fts(entry_fts, rowid, text, source, source_key, chunk_ix) VALUES('delete', ?, '', '', '', '')",
                (rid,),
            )
            con.execute(
                "INSERT INTO entry_fts(rowid, text, source, source_key, chunk_ix) VALUES (?,?,?,?,?)",
                (rid, text, source, source_key, chunk_ix),
            )
        return

    cur2 = con.execute(
        "INSERT INTO entry(doc_id, source, source_key, chunk_ix, text) VALUES (?,?,?,?,?)",
        (doc_id, source, source_key, chunk_ix, text),
    )
    rid2 = cur2.lastrowid
    con.execute(
        "INSERT INTO entry_fts(rowid, text, source, source_key, chunk_ix) VALUES (?,?,?,?,?)",
        (rid2, text, source, source_key, chunk_ix),
    )


@dataclass
class BuildResult:
    db_path: Path
    full_rebuild: bool
    docs_indexed: int


def build_index(workspace: Path, force: bool = False, full_rebuild: bool = False) -> BuildResult:
    ws = workspace.resolve()
    db = ws / "memory" / "supermemory.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db))
    docs_indexed = 0

    try:
        # auto-migrate older schemas
        if not full_rebuild:
            try:
                cols = [r[1] for r in con.execute("PRAGMA table_info(entry)").fetchall()]
                if cols and "doc_id" not in cols:
                    full_rebuild = True
            except Exception:
                pass

        _init_db(con, full_rebuild=full_rebuild)

        # MEMORY.md
        mem = ws / "MEMORY.md"
        if mem.exists():
            doc_id = "MEMORY.md"
            fp = _fingerprint_for_path(mem)
            cur = con.execute("SELECT fingerprint FROM doc_state WHERE doc_id=?", (doc_id,))
            r = cur.fetchone()
            if force or not (r and str(r[0]) == fp):
                _delete_doc_entries(con, doc_id)
                heading = "(root)"
                ix_by_heading: dict[str, int] = {}
                for line in mem.read_text(encoding="utf-8", errors="replace").splitlines():
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
                    _upsert_entry(con, doc_id, "memory", heading, ix, text)

                con.execute(
                    "INSERT INTO doc_state(doc_id, fingerprint, updated_at) VALUES (?,?,?) ON CONFLICT(doc_id) DO UPDATE SET fingerprint=excluded.fingerprint, updated_at=excluded.updated_at",
                    (doc_id, fp, _stamp_ms()),
                )
                docs_indexed += 1

        # daily files
        mdir = ws / "memory"
        seen_doc_ids: set[str] = set()
        if mdir.exists():
            for f in sorted(mdir.glob("????-??-??.md")):
                if not DAILY_NAME_RE.match(f.name):
                    continue
                doc_id = f"memory/{f.name}"
                seen_doc_ids.add(doc_id)
                fp = _fingerprint_for_path(f)
                cur = con.execute("SELECT fingerprint FROM doc_state WHERE doc_id=?", (doc_id,))
                r = cur.fetchone()
                if not (force or not (r and str(r[0]) == fp)):
                    continue

                _delete_doc_entries(con, doc_id)

                day = f.stem
                ix = 0
                for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                    bm = BULLET_RE.match(line)
                    if not bm:
                        continue
                    text = bm.group(1).strip()
                    if not text:
                        continue
                    _upsert_entry(con, doc_id, "daily", day, ix, text)
                    ix += 1

                con.execute(
                    "INSERT INTO doc_state(doc_id, fingerprint, updated_at) VALUES (?,?,?) ON CONFLICT(doc_id) DO UPDATE SET fingerprint=excluded.fingerprint, updated_at=excluded.updated_at",
                    (doc_id, fp, _stamp_ms()),
                )
                docs_indexed += 1

            # clean up removed daily docs
            cur = con.execute("SELECT doc_id FROM doc_state WHERE doc_id LIKE 'memory/%'")
            for (doc_id,) in cur.fetchall():
                if str(doc_id) not in seen_doc_ids:
                    _delete_doc_entries(con, str(doc_id))
                    con.execute("DELETE FROM doc_state WHERE doc_id=?", (str(doc_id),))

        con.commit()
    finally:
        con.close()

    return BuildResult(db_path=db, full_rebuild=full_rebuild, docs_indexed=docs_indexed)
