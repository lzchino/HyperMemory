from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import List

import psycopg
from pgvector.psycopg import register_vector
from pgvector import Vector

from .redaction import redact as _redact, validate_allowlist

M_SCORE_RE = re.compile(r"^\s*-\s*\[M([1-5])\]\s+(.*)$")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_json(url: str, payload: dict | None = None, timeout: float = 30.0):
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def embed_texts(embed_base_url: str, texts: List[str]) -> List[List[float]]:
    return http_json(f"{embed_base_url.rstrip('/')}/embed", {"inputs": texts})


def embed_one(embed_base_url: str, text: str) -> Vector:
    v = http_json(f"{embed_base_url.rstrip('/')}/embed", {"inputs": [text]})
    return Vector(v[0])


SCHEMA_SQL = """\
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS hm_cloud_item (
  namespace text NOT NULL,
  content_sha text NOT NULL,
  content text NOT NULL,
  score int NOT NULL,
  source_meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(namespace, content_sha)
);

CREATE TABLE IF NOT EXISTS hm_cloud_embedding (
  namespace text NOT NULL,
  content_sha text NOT NULL,
  model_id text NOT NULL,
  dims int NOT NULL,
  embedding vector NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(namespace, content_sha, model_id)
);

CREATE INDEX IF NOT EXISTS hm_cloud_item_created_at_idx
  ON hm_cloud_item(namespace, created_at DESC);
"""


@dataclass
class CloudConfig:
    database_url: str
    namespace: str = "default"
    threshold: int = 3
    embed_url: str = "http://127.0.0.1:8080"
    model_id: str = "local"
    allowlist: bool = True

    @staticmethod
    def from_env() -> "CloudConfig":
        db_url = os.environ.get("HYPERMEMORY_CLOUD_DATABASE_URL")
        if not db_url:
            raise ValueError("HYPERMEMORY_CLOUD_DATABASE_URL missing")
        return CloudConfig(
            database_url=db_url,
            namespace=os.environ.get("HYPERMEMORY_CLOUD_NAMESPACE", "default"),
            threshold=int(os.environ.get("HYPERMEMORY_CLOUD_SYNC_THRESHOLD", "3")),
            embed_url=os.environ.get("HYPERMEMORY_CLOUD_EMBED_URL", "http://127.0.0.1:8080"),
            model_id=os.environ.get("HYPERMEMORY_CLOUD_MODEL_ID", "local"),
            allowlist=os.environ.get("HYPERMEMORY_CLOUD_ALLOWLIST", "1") == "1",
        )


def init_schema(cfg: CloudConfig) -> None:
    with psycopg.connect(cfg.database_url) as con:
        con.execute(SCHEMA_SQL)
        con.commit()


def _parse_pending(path: Path, threshold: int) -> list[tuple[int, str]]:
    if not path.exists():
        return []
    items: list[tuple[int, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = M_SCORE_RE.match(line)
        if not m:
            continue
        score = int(m.group(1))
        text = m.group(2).strip()
        if score >= threshold and text:
            items.append((score, text))
    return items


def prepare_payload(workspace: Path, cfg: CloudConfig) -> Path:
    ws = workspace.resolve()
    pending = ws / "memory" / "staging" / "MEMORY.pending.md"
    items = _parse_pending(pending, cfg.threshold)
    if not items:
        raise SystemExit("No curated items to push.")

    redacted: list[tuple[int, str]] = []
    audit: list[dict] = []
    skipped = 0

    for score, text in items:
        rr = _redact(text)
        ok = True
        reasons: list[str] = []
        if cfg.allowlist:
            ok, reasons = validate_allowlist(rr.text)
        if not ok:
            skipped += 1
            audit.append({"score": score, "skipped": True, "skip_reasons": reasons, "redactions": rr.redaction_count, "rules": rr.matched_rules})
            continue
        redacted.append((score, rr.text))
        audit.append({"score": score, "skipped": False, "redactions": rr.redaction_count, "rules": rr.matched_rules})

    if not redacted:
        raise SystemExit(f"No items eligible to push after allowlist/redaction (skipped={skipped}).")

    # embed to get dims and ensure embed server works
    vecs = embed_texts(cfg.embed_url, ["passage: " + t for _s, t in redacted])
    if not vecs:
        raise SystemExit("Embedding server returned no vectors")
    dims = len(vecs[0])

    payload_items = []
    audit_non_skipped = [a for a in audit if not a.get("skipped")]
    for (score, text), a in zip(redacted, audit_non_skipped):
        payload_items.append({
            "score": score,
            "content": text,
            "content_sha": sha256(text),
            "redactions": a.get("redactions", 0),
            "rules": a.get("rules", []),
        })

    payload = {
        "namespace": cfg.namespace,
        "threshold": cfg.threshold,
        "allowlist": cfg.allowlist,
        "model_id": cfg.model_id,
        "dims": dims,
        "count": len(payload_items),
        "skipped": skipped,
        "items": payload_items,
    }

    payload_path = ws / "memory" / "staging" / "cloud-push.payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # redaction audit logs (no raw secrets)
    redaction_log = ws / "memory" / "cloud-redaction.jsonl"
    redaction_log.parent.mkdir(parents=True, exist_ok=True)
    with redaction_log.open("a", encoding="utf-8") as f:
        for a in audit:
            f.write(json.dumps({"action": "redaction", "namespace": cfg.namespace, **a}) + "\n")

    return payload_path


def commit_payload(workspace: Path, cfg: CloudConfig) -> int:
    ws = workspace.resolve()
    payload_path = ws / "memory" / "staging" / "cloud-push.payload.json"
    if not payload_path.exists():
        payload_path = prepare_payload(ws, cfg)

    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if not items:
        return 0

    # embed again for embeddings (deterministic server)
    vecs = embed_texts(cfg.embed_url, ["passage: " + it["content"] for it in items])
    dims = int(payload.get("dims") or len(vecs[0]))

    init_schema(cfg)

    audit_log = ws / "memory" / "cloud-sync.jsonl"
    audit_log.parent.mkdir(parents=True, exist_ok=True)

    with psycopg.connect(cfg.database_url) as con:
        register_vector(con)
        pushed = 0
        for it, vec in zip(items, vecs):
            score = int(it["score"])
            content = str(it["content"])
            content_sha = str(it["content_sha"])
            meta = {
                "score": score,
                "workspace": str(ws),
                "source": "staging/MEMORY.pending.md",
                "payload_path": str(payload_path),
            }
            con.execute(
                """
                INSERT INTO hm_cloud_item(namespace, content_sha, content, score, source_meta)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(namespace, content_sha)
                DO UPDATE SET content=excluded.content, score=excluded.score, source_meta=excluded.source_meta;
                """,
                (cfg.namespace, content_sha, content, score, json.dumps(meta)),
            )
            con.execute(
                """
                INSERT INTO hm_cloud_embedding(namespace, content_sha, model_id, dims, embedding)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(namespace, content_sha, model_id)
                DO UPDATE SET dims=excluded.dims, embedding=excluded.embedding, updated_at=now();
                """,
                (cfg.namespace, content_sha, cfg.model_id, dims, vec),
            )
            pushed += 1
            with audit_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"action": "push", "namespace": cfg.namespace, "sha": content_sha, "score": score}) + "\n")

        con.commit()

    return pushed


def pull_curated(workspace: Path, cfg: CloudConfig, limit: int = 200) -> Path:
    ws = workspace.resolve()
    out_dir = ws / "memory" / "staging"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "MEMORY.cloud.md"

    with psycopg.connect(cfg.database_url) as con:
        cur = con.execute(
            """
            SELECT content_sha, score, content
            FROM hm_cloud_item
            WHERE namespace=%s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (cfg.namespace, int(limit)),
        )
        rows = cur.fetchall()

    existing = set()
    if out_file.exists():
        for line in out_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("- [sha="):
                existing.add(line.split(" ", 1)[0])

    with out_file.open("a", encoding="utf-8") as f:
        for sha, score, content in rows:
            key = f"- [sha={sha}]"
            if key in existing:
                continue
            f.write(f"- [sha={sha}] [M{int(score)}] {content}\n")

    return out_file


def search_curated(cfg: CloudConfig, query: str, limit: int = 8) -> list[str]:
    qvec = embed_one(cfg.embed_url, "query: " + query)

    with psycopg.connect(cfg.database_url) as con:
        register_vector(con)
        cur = con.execute(
            """
            SELECT e.content_sha, i.score, i.content,
                   1 - (e.embedding <=> %s) AS sim
            FROM hm_cloud_embedding e
            JOIN hm_cloud_item i
              ON i.namespace=e.namespace AND i.content_sha=e.content_sha
            WHERE e.namespace=%s AND e.model_id=%s
            ORDER BY e.embedding <=> %s
            LIMIT %s;
            """,
            (qvec, cfg.namespace, cfg.model_id, qvec, int(limit)),
        )
        rows = cur.fetchall()

    return [f"[{float(sim):.4f}] sha={sha} M{int(score)} {content}" for sha, score, content, sim in rows]
