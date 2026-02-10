from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .retrieval import retrieve


@dataclass
class EvalCase:
    query: str
    expected: str | None
    category: str
    min_hits: int


@dataclass
class EvalResult:
    total: int
    passed: int
    failed: int
    recall_pct: int
    pass_retrieve: int
    pass_file: int


def _iter_eval_cases(ws: Path) -> list[EvalCase]:
    p = ws / "memory" / "eval-queries.jsonl"
    if not p.exists():
        return []

    out: list[EvalCase] = []
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue

        q = d.get("query") or d.get("q")
        if not q:
            continue

        expected = d.get("expected")
        category = d.get("category") or "unknown"
        min_hits = int(d.get("minHits") or 1)

        out.append(EvalCase(query=str(q), expected=str(expected) if expected else None, category=str(category), min_hits=min_hits))

    return out


def _file_contains(ws: Path, needle: str) -> bool:
    targets = []
    mdir = ws / "memory"
    if mdir.exists():
        targets.extend(sorted(mdir.glob("*.md")))
    mem = ws / "MEMORY.md"
    if mem.exists():
        targets.append(mem)

    for t in targets:
        try:
            if needle in t.read_text(encoding="utf-8", errors="replace"):
                return True
        except Exception:
            continue
    return False


def run_eval(cfg: Config, fast: bool = False, min_recall: int = 0) -> EvalResult:
    ws = cfg.workspace
    cases = _iter_eval_cases(ws)

    total = 0
    passed = 0
    pass_retrieve = 0
    pass_file = 0

    for c in cases:
        total += 1

        found_file = False
        found_retrieve = False

        if c.expected:
            # expected mode
            if _file_contains(ws, c.expected):
                found_file = True

            if not fast and not found_file:
                hits = retrieve(ws, c.query, mode="auto", limit=10)
                blob = "\n".join(h.snippet for h in hits).lower()
                if c.expected.lower() in blob:
                    found_retrieve = True
        else:
            # minHits mode
            if _file_contains(ws, c.query[:80]):
                found_file = True

            if not fast:
                hits = retrieve(ws, c.query, mode="auto", limit=10)
                if len(hits) >= c.min_hits:
                    found_retrieve = True

        if found_retrieve:
            passed += 1
            pass_retrieve += 1
        elif found_file:
            passed += 1
            pass_file += 1

    failed = total - passed
    recall_pct = int((passed * 100) / total) if total else 0

    if min_recall and recall_pct < min_recall:
        raise SystemExit(f"FAIL: recall {recall_pct}% < MIN_RECALL={min_recall}%")

    return EvalResult(
        total=total,
        passed=passed,
        failed=failed,
        recall_pct=recall_pct,
        pass_retrieve=pass_retrieve,
        pass_file=pass_file,
    )
