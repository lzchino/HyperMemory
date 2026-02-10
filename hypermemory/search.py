from __future__ import annotations

"""SQLite FTS search layer.

This is the Python equivalent of scripts/memory-search.sh.
"""

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SearchHit:
    source: str
    source_key: str
    chunk_ix: int
    snippet: str


def search_fts(workspace: Path, query: str, limit: int = 20) -> list[SearchHit]:
    ws = workspace.resolve()
    db = ws / "memory" / "supermemory.sqlite"
    if not db.exists():
        return []

    q = query.replace('"', '""')
    match = f'"{q}"'

    con = sqlite3.connect(str(db))
    try:
        rows = con.execute(
            """
            SELECT source, source_key, chunk_ix, substr(text,1,180)
            FROM entry_fts
            WHERE entry_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (match, int(limit)),
        ).fetchall()
        return [SearchHit(source=r[0], source_key=r[1], chunk_ix=int(r[2]), snippet=r[3]) for r in rows]
    finally:
        con.close()
