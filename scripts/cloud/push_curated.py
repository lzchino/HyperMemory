#!/usr/bin/env python3
"""Push curated-only memory items to BYO Postgres (pgvector) Cloud L3.

Source of curated items: memory/staging/MEMORY.pending.md

Env:
  HYPERMEMORY_CLOUD_DATABASE_URL   (required)
  HYPERMEMORY_CLOUD_NAMESPACE      (optional, default: "default")
  HYPERMEMORY_CLOUD_SYNC_THRESHOLD (optional, default: 3)
  HYPERMEMORY_CLOUD_EMBED_URL      (optional, default: http://127.0.0.1:8080)
  HYPERMEMORY_CLOUD_MODEL_ID       (optional, default: "local")

This script is idempotent: uses content_sha (sha256) as stable key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import List

import psycopg
from pgvector.psycopg import register_vector

M_SCORE_RE = re.compile(r"^\s*-\s*\[M([1-5])\]\s+(.*)$")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_json(url: str, payload: dict | None = None, timeout: float = 30.0):
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def embed_texts(embed_base_url: str, texts: List[str]) -> List[List[float]]:
    return http_json(f"{embed_base_url.rstrip('/')}/embed", {"inputs": texts})


from scripts.cloud.redaction import redact as _redact, validate_allowlist


def parse_pending(path: Path, threshold: int) -> list[tuple[int, str]]:
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


def ensure_schema(con: psycopg.Connection) -> None:
    schema_sql = (Path(__file__).resolve().parent / "pgvector_schema.sql").read_text(encoding="utf-8")
    con.execute(schema_sql)
    con.commit()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=os.environ.get("OPENCLAW_WORKSPACE", "."))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", action="store_true", help="Actually push to cloud (otherwise writes a payload file)")
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()

    db_url = os.environ.get("HYPERMEMORY_CLOUD_DATABASE_URL")
    if not db_url:
        print("ERROR: HYPERMEMORY_CLOUD_DATABASE_URL missing", file=sys.stderr)
        return 2

    namespace = os.environ.get("HYPERMEMORY_CLOUD_NAMESPACE", "default")
    threshold = int(os.environ.get("HYPERMEMORY_CLOUD_SYNC_THRESHOLD", "3"))
    embed_url = os.environ.get("HYPERMEMORY_CLOUD_EMBED_URL", "http://127.0.0.1:8080")
    model_id = os.environ.get("HYPERMEMORY_CLOUD_MODEL_ID", "local")

    pending = ws / "memory" / "staging" / "MEMORY.pending.md"
    items = parse_pending(pending, threshold)
    if not items:
        print("No curated items to push.")
        return 0

    allowlist = os.environ.get("HYPERMEMORY_CLOUD_ALLOWLIST", "1") == "1"

    # redact + audit (never log raw secrets)
    redacted = []
    audit = []
    skipped = 0
    for score, text in items:
        rr = _redact(text)

        ok = True
        reasons: list[str] = []
        if allowlist:
            ok, reasons = validate_allowlist(rr.text)

        if not ok:
            skipped += 1
            audit.append({
                "score": score,
                "skipped": True,
                "skip_reasons": reasons,
                "redactions": rr.redaction_count,
                "rules": rr.matched_rules,
            })
            continue

        redacted.append((score, rr.text))
        audit.append({"score": score, "skipped": False, "redactions": rr.redaction_count, "rules": rr.matched_rules})

    if not redacted:
        print(f"No items eligible to push after allowlist/redaction (skipped={skipped}).")
        return 0

    texts = ["passage: " + t for _s, t in redacted]

    # embed
    vecs = embed_texts(embed_url, texts)
    if not vecs:
        print("ERROR: embedding server returned no vectors", file=sys.stderr)
        return 3
    dims = len(vecs[0])

    audit_dir = ws / "memory"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_log = audit_dir / "cloud-sync.jsonl"
    redaction_log = audit_dir / "cloud-redaction.jsonl"

    # Build a payload that can be reviewed before commit
    # Build payload from the non-skipped audit rows only
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
        "namespace": namespace,
        "threshold": threshold,
        "allowlist": allowlist,
        "model_id": model_id,
        "dims": dims,
        "count": len(payload_items),
        "skipped": skipped,
        "items": payload_items,
    }

    payload_path = ws / "memory" / "staging" / "cloud-push.payload.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.dry_run or not args.commit:
        print(
            f"Prepared payload at {payload_path} (count={len(redacted)}). "
            + ("DRY RUN." if args.dry_run else "Run again with --commit to push.")
        )
        # write a redaction audit summary
        with redaction_log.open("a", encoding="utf-8") as f:
            for a in audit:
                f.write(json.dumps({"action": "redaction", "namespace": namespace, **a}) + "\n")
        return 0

    with psycopg.connect(db_url) as con:
        register_vector(con)
        ensure_schema(con)

        pushed = 0
        # emit redaction audit first
        with redaction_log.open("a", encoding="utf-8") as f:
            for a in audit:
                f.write(json.dumps({"action": "redaction", "namespace": namespace, **a}) + "\n")

        for idx, ((score, text), vec) in enumerate(zip(redacted, vecs)):
            content_sha = payload["items"][idx]["content_sha"]
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
                (namespace, content_sha, text, score, json.dumps(meta)),
            )

            con.execute(
                """
                INSERT INTO hm_cloud_embedding(namespace, content_sha, model_id, dims, embedding)
                VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(namespace, content_sha, model_id)
                DO UPDATE SET dims=excluded.dims, embedding=excluded.embedding, updated_at=now();
                """,
                (namespace, content_sha, model_id, dims, vec),
            )

            pushed += 1
            audit_log.write_text("", encoding="utf-8") if False else None
            with audit_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"action": "push", "namespace": namespace, "sha": content_sha, "score": score}) + "\n")

        con.commit()

    print(f"Pushed {pushed} curated items to cloud namespace={namespace}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
