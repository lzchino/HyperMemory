from __future__ import annotations

"""Chunk enumeration for semantic indexing.

Constraint: semantic index must include **curated + distilled** content only.

Sources:
- MEMORY.md bullets (curated/distilled)
- Optionally staged curated items (memory/staging/MEMORY.pending.md) if enabled

We intentionally do NOT include raw daily logs unless they were distilled into MEMORY.md.
"""

import re
from dataclasses import dataclass
from pathlib import Path

BULLET_RE = re.compile(r"^\s*-\s*(.+?)\s*$")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    source: str
    source_key: str
    chunk_ix: int
    text: str


def iter_memory_md(workspace: Path) -> list[Chunk]:
    ws = workspace.resolve()
    p = ws / "MEMORY.md"
    if not p.exists():
        return []

    heading = "(root)"
    ix_by_heading: dict[str, int] = {}
    out: list[Chunk] = []

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
        out.append(Chunk(doc_id="MEMORY.md", source="memory", source_key=heading, chunk_ix=ix, text=text))

    return out


def iter_pending_curated(workspace: Path) -> list[Chunk]:
    ws = workspace.resolve()
    p = ws / "memory" / "staging" / "MEMORY.pending.md"
    if not p.exists():
        return []

    out: list[Chunk] = []
    ix = 0
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        bm = BULLET_RE.match(line)
        if not bm:
            continue
        text = bm.group(1).strip()
        if not text:
            continue
        out.append(Chunk(doc_id="memory/staging/MEMORY.pending.md", source="staging", source_key="pending", chunk_ix=ix, text=text))
        ix += 1

    return out


def iter_semantic_chunks(workspace: Path, include_pending: bool = False) -> list[Chunk]:
    chunks = []
    chunks.extend(iter_memory_md(workspace))
    if include_pending:
        chunks.extend(iter_pending_curated(workspace))
    return chunks
