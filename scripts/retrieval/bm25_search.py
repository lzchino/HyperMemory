#!/usr/bin/env python3
"""Pure-Python BM25-ish keyword search over a workspace.

No external deps. Intended as a portable fallback layer.

Outputs one line per hit:
  score\tpath\tsnippet
"""

from __future__ import annotations

import argparse
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z0-9_:\./-]{2,}")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


def iter_docs(repo: Path) -> list[tuple[str, str]]:
    docs: list[tuple[str, str]] = []

    mem = repo / "MEMORY.md"
    if mem.exists():
        docs.append((str(mem.relative_to(repo)), mem.read_text(encoding="utf-8", errors="replace")))

    mdir = repo / "memory"
    if mdir.exists():
        for p in sorted(mdir.glob("????-??-??.md")):
            docs.append((str(p.relative_to(repo)), p.read_text(encoding="utf-8", errors="replace")))

    return docs


def bm25_scores(query: str, docs: list[tuple[str, str]], k1: float = 1.2, b: float = 0.75) -> list[tuple[float, str, str]]:
    q_terms = tokenize(query)
    if not q_terms:
        return []

    # Build corpus stats
    doc_tokens: list[list[str]] = []
    doc_tf: list[Counter[str]] = []
    df: dict[str, int] = defaultdict(int)
    lengths: list[int] = []

    for _path, text in docs:
        toks = tokenize(text)
        doc_tokens.append(toks)
        tf = Counter(toks)
        doc_tf.append(tf)
        lengths.append(len(toks))
        for t in set(toks):
            df[t] += 1

    N = len(docs)
    if N == 0:
        return []
    avgdl = sum(lengths) / max(1, N)

    # idf
    def idf(t: str) -> float:
        n = df.get(t, 0)
        return math.log(1 + (N - n + 0.5) / (n + 0.5))

    scored: list[tuple[float, str, str]] = []
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

        # snippet: first matching line
        snippet = ""
        for line in text.splitlines():
            low = line.lower()
            if any(t in low for t in q_terms):
                snippet = line.strip()
                break
        if not snippet:
            snippet = " ".join(text.split())[:180]

        scored.append((score, path, snippet[:220]))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.environ.get("OPENCLAW_WORKSPACE", "."))
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    docs = iter_docs(repo)
    hits = bm25_scores(args.query, docs)[: args.limit]

    for score, path, snippet in hits:
        print(f"{score:.4f}\t{path}\t{snippet}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
