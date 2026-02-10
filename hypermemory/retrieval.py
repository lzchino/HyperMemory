from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from .bm25 import search as bm25_search
from .fts import FtsHit, search as fts_search


@dataclass
class RetrievalHit:
    layer: str
    score: float
    snippet: str
    why: str


_TARGETED_RX = re.compile(r"(?i)\b(gid|id\s+for|what\s+is\s+the|where\s+is|port|:([0-9]{2,5})|config|token|key|password|path)\b")


def detect_mode(query: str) -> str:
    if len(query) < 40:
        return "targeted"
    if _TARGETED_RX.search(query):
        return "targeted"
    return "broad"


def bm25_layer(workspace: Path, query: str, limit: int = 10) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, h in enumerate(bm25_search(workspace, query, limit=limit), 1):
        out.append((f"bm25:{h.path}#{i}", h.snippet))
    return out


def fts_layer(workspace: Path, query: str, limit: int = 20) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for i, h in enumerate(fts_search(workspace, query, limit=limit), 1):
        out.append((f"fts:{h.source}:{h.source_key}#{h.chunk_ix}", h.text))
    return out


def vec_layer(query: str, limit: int = 8) -> list[tuple[str, str]]:
    """Local pgvector semantic layer.

    Only indexes curated+distilled chunks (hm_local_embedding).
    Enabled when DATABASE_URL is set.
    """

    if not os.environ.get("DATABASE_URL"):
        return []

    from .pgvector_local import LocalVectorConfig, search_workspace

    cfg = LocalVectorConfig.from_env()
    lines = search_workspace(cfg, query, limit=limit)
    out: list[tuple[str, str]] = []
    for i, line in enumerate(lines, 1):
        out.append((f"vec:{i}", line))
    return out


def cloud_layer(query: str, limit: int = 8) -> list[tuple[str, str]]:
    if os.environ.get("HYPERMEMORY_CLOUD_FALLBACK", "0") != "1":
        return []
    if not os.environ.get("HYPERMEMORY_CLOUD_DATABASE_URL"):
        return []

    from .cloud_pgvector import CloudConfig, search_curated

    cfg = CloudConfig.from_env()
    lines = search_curated(cfg, query, limit=limit)
    out: list[tuple[str, str]] = []
    for i, line in enumerate(lines, 1):
        out.append((f"cloud:{i}", line))
    return out


def rrf_score(ranks: dict[str, int], k: float = 60.0) -> float:
    return sum(1.0 / (k + float(r)) for r in ranks.values())


def entity_layer(workspace: Path, query: str, limit: int = 8) -> list[tuple[str, str]]:
    """Entity index layer.

    If the index is missing, return a single low-signal hint so operators know
    what to do (but don't crash retrieval).
    """

    from .entity_index import db_path, search_entities

    if not db_path(workspace).exists():
        return [("entity:missing", "(hint) run: hypermemory entity index")]

    hits = search_entities(workspace, query, limit=limit)
    out: list[tuple[str, str]] = []
    for i, h in enumerate(hits, 1):
        out.append((f"entity:{i}", f"{h.entity} {h.attr}={h.value}"))
    return out


def retrieve(workspace: Path, query: str, mode: str = "auto", limit: int = 10) -> list[RetrievalHit]:
    ws = workspace.resolve()
    if mode == "auto":
        mode = detect_mode(query)

    # Local-first layers
    ent = entity_layer(ws, query, limit=8) if mode == "targeted" else []
    fts = fts_layer(ws, query, limit=20)
    bm25 = bm25_layer(ws, query, limit=10)
    vec = vec_layer(query, limit=8)
    cloud = cloud_layer(query, limit=8)

    items: dict[str, dict] = {}

    def add(layer: str, rank: int, key: str, snippet: str):
        it = items.get(key)
        if not it:
            it = {"snippet": snippet, "ranks": {}}
            items[key] = it
        it["ranks"][layer] = min(rank, it["ranks"].get(layer, 10**9))
        if snippet and (not it["snippet"] or len(snippet) > len(it["snippet"])):
            it["snippet"] = snippet

    for r, (key, snip) in enumerate(ent, 1):
        add("entity", r, key, snip)
    for r, (key, snip) in enumerate(fts, 1):
        add("fts", r, key, snip)
    for r, (key, snip) in enumerate(bm25, 1):
        add("bm25", r, key, snip)
    for r, (key, snip) in enumerate(vec, 1):
        add("vec", r, key, snip)
    for r, (key, snip) in enumerate(cloud, 1):
        add("cloud", r, key, snip)

    scored: list[RetrievalHit] = []
    for key, it in items.items():
        ranks = it["ranks"]
        score = rrf_score(ranks)
        why = " ".join(f"{k}:{v}" for k, v in sorted(ranks.items()))
        scored.append(RetrievalHit(layer=key, score=score, snippet=str(it["snippet"]), why=why))

    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:limit]
