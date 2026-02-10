from __future__ import annotations

"""Durable journal (WAL) + projections.

Operational intention: never lose user/agent messages; recover deterministically.

Design:
- Append-only JSONL journal: <workspace>/memory/journal.jsonl
- Projections (derived, rebuildable):
  - last-messages.jsonl (tail window)
  - daily file append (memory/YYYY-MM-DD.md)

Dependency-free (no sqlite/psycopg required).
"""

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class JournalEvent:
    ts_ms: int
    channel: str
    session_key: str
    role: str
    message: str


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mkdir_lock(lock_dir: Path, timeout_s: float = 5.0) -> None:
    start = time.time()
    while True:
        try:
            lock_dir.mkdir(parents=False, exist_ok=False)
            return
        except FileExistsError:
            if time.time() - start > timeout_s:
                raise TimeoutError(f"Lock timeout: {lock_dir}")
            time.sleep(0.05)


def _mkdir_unlock(lock_dir: Path) -> None:
    try:
        lock_dir.rmdir()
    except Exception:
        pass


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        if not line.endswith("\n"):
            f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def append_event(
    workspace: Path,
    message: str,
    role: str = "user",
    channel: str = "unknown",
    session_key: str = "",
    ts_ms: int | None = None,
    tail_limit: int = 200,
) -> JournalEvent:
    """Append to journal and update projections.

    Projections are best-effort; journal append is durable.
    """

    ws = workspace.resolve()
    mem = ws / "memory"
    mem.mkdir(parents=True, exist_ok=True)

    ev = JournalEvent(
        ts_ms=int(ts_ms if ts_ms is not None else _now_ms()),
        channel=str(channel or "unknown"),
        session_key=str(session_key or ""),
        role=str(role or "user"),
        message=str(message),
    )

    journal = mem / "journal.jsonl"
    lock_dir = mem / ".journal.lock"

    _mkdir_lock(lock_dir)
    try:
        _append_line(journal, json.dumps(ev.__dict__, ensure_ascii=False))

        # projection: last-messages.jsonl
        last = mem / "last-messages.jsonl"
        if last.exists():
            try:
                lines = last.read_text(encoding="utf-8", errors="replace").splitlines()
            except Exception:
                lines = []
            lines = lines[-(tail_limit - 1) :] if tail_limit > 1 else []
        else:
            lines = []
        lines.append(json.dumps(ev.__dict__, ensure_ascii=False))
        last.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # projection: daily file append
        day = time.strftime("%Y-%m-%d", time.gmtime(ev.ts_ms / 1000.0))
        daily = mem / f"{day}.md"
        _append_line(daily, f"- [{ev.role}@{ev.channel}] {ev.message}")

    finally:
        _mkdir_unlock(lock_dir)

    return ev
