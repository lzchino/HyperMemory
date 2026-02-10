from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    import psycopg  # type: ignore
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore


@dataclass
class DoctorReport:
    workspace: str
    ok: bool
    checks: dict


def _exists(p: Path) -> bool:
    try:
        return p.exists()
    except Exception:
        return False


def run_doctor(workspace: Path) -> DoctorReport:
    ws = workspace.resolve()
    mem_dir = ws / "memory"

    checks: dict = {}
    checks["memory_dir"] = _exists(mem_dir)
    checks["memory_md"] = _exists(ws / "MEMORY.md")
    checks["daily_files"] = len(list(mem_dir.glob("????-??-??.md"))) if mem_dir.exists() else 0

    # SQLite FTS
    db = mem_dir / "supermemory.sqlite"
    checks["sqlite_fts"] = _exists(db)

    # Session / buffer
    checks["session_state"] = _exists(mem_dir / "session-state.json")
    checks["message_buffer"] = _exists(mem_dir / "last-messages.jsonl")
    checks["journal"] = _exists(mem_dir / "journal.jsonl")

    # Local pgvector
    db_url = os.environ.get("DATABASE_URL")
    checks["local_pgvector_enabled"] = bool(db_url)
    if db_url:
        if psycopg is None:
            checks["local_pgvector_connect"] = False
            checks["local_pgvector_error"] = "psycopg not installed"
        else:
            try:
                with psycopg.connect(db_url) as con:
                    con.execute("select 1")
                checks["local_pgvector_connect"] = True
            except Exception as e:
                checks["local_pgvector_connect"] = False
                checks["local_pgvector_error"] = str(e)[:200]

    # Cloud
    cloud_url = os.environ.get("HYPERMEMORY_CLOUD_DATABASE_URL")
    checks["cloud_enabled"] = bool(cloud_url)
    if cloud_url:
        if psycopg is None:
            checks["cloud_connect"] = False
            checks["cloud_error"] = "psycopg not installed"
        else:
            try:
                with psycopg.connect(cloud_url) as con:
                    con.execute("select 1")
                checks["cloud_connect"] = True
            except Exception as e:
                checks["cloud_connect"] = False
                checks["cloud_error"] = str(e)[:200]

    ok = bool(checks["memory_dir"]) and bool(checks["sqlite_fts"])
    return DoctorReport(workspace=str(ws), ok=ok, checks=checks)


def to_json(report: DoctorReport) -> str:
    return json.dumps({"workspace": report.workspace, "ok": report.ok, "checks": report.checks}, indent=2)
