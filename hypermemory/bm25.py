from __future__ import annotations

"""Pure-Python BM25-ish keyword search.

Designed to be deterministic and dependency-free.
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z0-9_:\./-]{2,}")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


def iter_docs(workspace: Path) -> list[tuple[str, str]]:
    ws = workspace.resolve()
    docs: list[tuple[str, str]] = []

    mem = ws / "MEMORY.md"
    if mem.exists():
        docs.append(("MEMORY.md", mem.read_text(encoding="utf-8", errors="replace")))

    mdir = ws / "memory"
    if mdir.exists():
        for p in sorted(mdir.glob("????-??-??.md")):
            docs.append((str(p.relative_to(ws)), p.read_text(encoding="utf-8", errors="replace")))

    return docs


@dataclass
class Bm25Hit:
    score: float
    path: str
    snippet: str


def search(workspace: Path, query: str, limit: int = 10, k1: float = 1.2, b: float = 0.75) -> list[Bm25Hit]:
    q_terms = tokenize(query)
    if not q_terms:
        return []

    docs = iter_docs(workspace)
    if not docs:
        return []

    doc_tf: list[Counter[str]] = []
    df: dict[str, int] = defaultdict(int)
    lengths: list[int] = []

    for _path, text in docs:
        toks = tokenize(text)
        tf = Counter(toks)
        doc_tf.append(tf)
        lengths.append(len(toks))
        for t in set(toks):
            df[t] += 1

    N = len(docs)
    avgdl = sum(lengths) / max(1, N)

    def idf(t: str) -> float:
        n = df.get(t, 0)
        return math.log(1 + (N - n + 0.5) / (n + 0.5))

    scored: list[Bm25Hit] = []
    for (path, text), tf, dl in zip(docs, doc_tf, lengths):
        score = 0.0
        for t in q_terms:
            f = tf.get(t, 0)
            if f == 0:
                continue
            denom = f + k1 * (1 - b + b * (dl / avgdl))
            score += idf(t) * (f * (k1 + 1) / denom)

        if score <= 0:
            continue

        snippet = ""
        for line in text.splitlines():
            low = line.lower()
            if any(t in low for t in q_terms):
                snippet = line.strip()
                break
        if not snippet:
            snippet = " ".join(text.split())[:180]

        scored.append(Bm25Hit(score=score, path=path, snippet=snippet[:220]))

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:limit]
