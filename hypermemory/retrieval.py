from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .fts import FtsHit, search as fts_search


@dataclass
class RetrievalHit:
    layer: str
    score: float
    snippet: str


_TARGETED_RX = re.compile(r"(?i)\b(gid|id\s+for|what\s+is\s+the|where\s+is|port|:([0-9]{2,5})|config|token|key|password|path)\b")


def detect_mode(query: str) -> str:
    if len(query) < 40:
        return "targeted"
    if _TARGETED_RX.search(query):
        return "targeted"
    return "broad"


def bm25_search(workspace: Path, query: str, limit: int = 10) -> list[RetrievalHit]:
    script = Path(__file__).resolve().parent.parent / "scripts" / "retrieval" / "bm25_search.py"
    if not script.exists():
        return []
    p = subprocess.run(
        ["python3", str(script), "--repo", str(workspace), query, "--limit", str(limit)],
        capture_output=True,
        text=True,
    )
    out = p.stdout.strip()
    if not out:
        return []
    hits: list[RetrievalHit] = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        score_s, path, snippet = parts
        try:
            score = float(score_s)
        except Exception:
            score = 0.0
        hits.append(RetrievalHit(layer=f"bm25:{path}", score=score, snippet=snippet))
    return hits


def retrieve(workspace: Path, query: str, mode: str = "auto", limit: int = 10) -> list[RetrievalHit]:
    ws = workspace.resolve()
    if mode == "auto":
        mode = detect_mode(query)

    # 1) FTS exact
    fts_hits: list[FtsHit] = fts_search(ws, query, limit=limit)

    # 2) Local vector (optional) - keep in shell for now
    # We intentionally do NOT index raw dailies semantically; only curated+distilled in future refactor.

    # 3) BM25 fallback
    bm25_hits = bm25_search(ws, query, limit=limit)

    # Basic fusion: prefer FTS first, then BM25
    fused: list[RetrievalHit] = []
    for h in fts_hits:
        fused.append(RetrievalHit(layer=f"fts:{h.source}:{h.source_key}#{h.chunk_ix}", score=1.0, snippet=h.text))
    fused.extend(bm25_hits)

    return fused[:limit]
