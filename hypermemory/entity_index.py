from __future__ import annotations

"""Deterministic entity/fact index (SQLite).

Goal: answer targeted questions (ports, ids, paths, error codes, node names)
without relying on semantic embeddings.

Data sources (local-first):
- memory/journal.jsonl (WAL)
- MEMORY.md (curated/distilled)
- memory/staging/MEMORY.pending.md (optional)

This is a lightweight extractor + SQLite store.
"""

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .chunks import iter_semantic_chunks
from .journal import read_events

SERVICE_RE = re.compile(r"\b([a-zA-Z0-9][\w-]*\.service)\b")
PORT_RE = re.compile(r":([0-9]{2,5})\b")
ERROR_RE = re.compile(r"\b([A-Z]{3,}:?[A-Z0-9_]{3,})\b")
NODE_RE = re.compile(r"\bnode-[a-z0-9][a-z0-9-]*\b")
PATH_RE = re.compile(r"\b(/[^\s]+)\b")


@dataclass(frozen=True)
class EntityHit:
    entity: str
    attr: str
    value: str
    source: str
    score: float


def db_path(workspace: Path) -> Path:
    return workspace.resolve() / "memory" / "entity.sqlite"


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS hm_entity (
          entity TEXT NOT NULL,
          attr   TEXT NOT NULL,
          value  TEXT NOT NULL,
          source TEXT NOT NULL,
          ts_ms  INTEGER NOT NULL DEFAULT 0,
          raw    TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(entity, attr, value, source, ts_ms)
        );
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS hm_entity_entity ON hm_entity(entity)")
    con.execute("CREATE INDEX IF NOT EXISTS hm_entity_value ON hm_entity(value)")
    con.execute("CREATE INDEX IF NOT EXISTS hm_entity_attr  ON hm_entity(attr)")


def _emit(con: sqlite3.Connection, entity: str, attr: str, value: str, source: str, ts_ms: int, raw: str) -> None:
    con.execute(
        "INSERT OR IGNORE INTO hm_entity(entity, attr, value, source, ts_ms, raw) VALUES (?,?,?,?,?,?)",
        (entity, attr, value, source, int(ts_ms), raw),
    )


def extract_from_text(con: sqlite3.Connection, text: str, source: str, ts_ms: int = 0) -> int:
    n = 0

    # service + port
    services = SERVICE_RE.findall(text)
    ports = PORT_RE.findall(text)
    if services and ports:
        for s in services:
            for p in ports:
                _emit(con, s, "port", f":{p}", source, ts_ms, text)
                n += 1

    # node names
    for node in NODE_RE.findall(text):
        _emit(con, node, "type", "node", source, ts_ms, text)
        n += 1

    # error codes (EADDRINUSE etc)
    for err in ERROR_RE.findall(text):
        if err.startswith("HTTP"):
            continue
        if err in {"OK", "FAIL"}:
            continue
        if len(err) > 32:
            continue
        if err.isdigit():
            continue
        _emit(con, err, "type", "error", source, ts_ms, text)
        n += 1

    # paths
    for p in PATH_RE.findall(text):
        if len(p) < 2:
            continue
        _emit(con, p, "type", "path", source, ts_ms, text)
        n += 1

    return n


def build_entity_index(workspace: Path, include_pending: bool = False) -> dict:
    ws = workspace.resolve()
    dbp = db_path(ws)

    con = _connect(dbp)
    try:
        ensure_schema(con)

        con.execute("DELETE FROM hm_entity")

        total = 0
        # 1) WAL
        for ev in read_events(ws):
            total += extract_from_text(con, ev.message, source=f"journal:{ev.channel}", ts_ms=ev.ts_ms)

        # 2) curated/distilled (MEMORY bullets + optional pending)
        for c in iter_semantic_chunks(ws, include_pending=include_pending):
            total += extract_from_text(con, c.text, source=f"{c.doc_id}:{c.source_key}#{c.chunk_ix}", ts_ms=0)

        con.commit()

        rows = con.execute("SELECT COUNT(*) FROM hm_entity").fetchone()[0]
        return {"db": str(dbp), "rows": int(rows), "emitted": int(total)}
    finally:
        con.close()


def search_entities(workspace: Path, query: str, limit: int = 10) -> list[EntityHit]:
    ws = workspace.resolve()
    dbp = db_path(ws)
    if not dbp.exists():
        return []

    q = query.strip()
    if not q:
        return []

    # heuristic: if query includes a service token, bias to that entity
    service = None
    m = SERVICE_RE.search(q)
    if m:
        service = m.group(1)

    like = f"%{q}%"

    con = _connect(dbp)
    try:
        ensure_schema(con)
        if service:
            rows = con.execute(
                """
                SELECT entity, attr, value, source
                FROM hm_entity
                WHERE entity = ?
                ORDER BY ts_ms DESC
                LIMIT ?
                """,
                (service, int(limit)),
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT entity, attr, value, source
                FROM hm_entity
                WHERE entity LIKE ? OR value LIKE ? OR raw LIKE ?
                ORDER BY ts_ms DESC
                LIMIT ?
                """,
                (like, like, like, int(limit)),
            ).fetchall()

        out: list[EntityHit] = []
        for (entity, attr, value, source) in rows:
            score = 1.0
            if service and entity == service:
                score = 2.0
            out.append(EntityHit(entity=str(entity), attr=str(attr), value=str(value), source=str(source), score=float(score)))
        return out
    finally:
        con.close()
