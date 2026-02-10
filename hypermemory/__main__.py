from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from .config import Config


def _run(cmd: list[str]) -> int:
    p = subprocess.run(cmd)
    return int(p.returncode)


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = Config.from_env(args.workspace)
    m = cfg.workspace / "memory"
    out = {
        "workspace": str(cfg.workspace),
        "memory_dir": m.exists(),
        "memory_md": (cfg.workspace / "MEMORY.md").exists(),
        "sqlite_fts": (m / "supermemory.sqlite").exists(),
        "session_state": (m / "session-state.json").exists(),
        "message_buffer": (m / "last-messages.jsonl").exists(),
    }
    print(json.dumps(out, indent=2))
    critical_missing = not out["memory_dir"]
    return 1 if critical_missing else 0


def cmd_eval(args: argparse.Namespace) -> int:
    from .eval import run_eval

    cfg = Config.from_env(args.workspace)
    min_recall = int(os.environ.get("MIN_RECALL", "0"))
    res = run_eval(cfg, fast=args.fast, min_recall=min_recall)

    print("\n== summary ==")
    print(f"total={res.total} pass={res.passed} fail={res.failed} recall={res.recall_pct}%")
    print(f"pass_retrieve={res.pass_retrieve} pass_file={res.pass_file}")

    return 0


def cmd_index(args: argparse.Namespace) -> int:
    from .fts import build_index

    cfg = Config.from_env(args.workspace)
    res = build_index(cfg.workspace)
    print(str(res.db_path))
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    from .retrieval import retrieve

    cfg = Config.from_env(args.workspace)
    hits = retrieve(cfg.workspace, args.query, mode=args.mode, limit=10)
    for h in hits:
        print(f"[{h.layer}] {h.snippet}")
    return 0


def cmd_cloud(args: argparse.Namespace) -> int:
    from .cloud_pgvector import CloudConfig, commit_payload, init_schema, prepare_payload, pull_curated, search_curated

    cfg = Config.from_env(args.workspace)
    ccfg = CloudConfig.from_env()

    if args.action == "init":
        init_schema(ccfg)
        print("OK")
        return 0

    if args.action == "push":
        if args.commit:
            n = commit_payload(cfg.workspace, ccfg)
            print(f"pushed={n}")
            return 0
        p = prepare_payload(cfg.workspace, ccfg)
        print(str(p))
        return 0

    if args.action == "pull":
        p = pull_curated(cfg.workspace, ccfg, limit=args.limit)
        print(str(p))
        return 0

    if args.action == "search":
        for line in search_curated(ccfg, args.query, limit=args.limit):
            print(line)
        return 0

    raise SystemExit("unknown cloud action")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hypermemory")
    p.add_argument("--workspace", help="Workspace root (default: OPENCLAW_WORKSPACE or cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("doctor", help="Check workspace health")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("eval", help="Run eval harness")
    s.add_argument("--fast", action="store_true")
    s.set_defaults(func=cmd_eval)

    s = sub.add_parser("index", help="Build/update local indexes")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser("retrieve", help="Run retrieval")
    s.add_argument("mode", choices=["auto", "targeted", "broad"])
    s.add_argument("query")
    s.set_defaults(func=cmd_retrieve)

    s = sub.add_parser("cloud", help="Cloud L3 (BYO pgvector) commands")
    s.add_argument("action", choices=["init", "push", "pull", "search"])
    s.add_argument("--commit", action="store_true", help="For push: actually commit to cloud")
    s.add_argument("--limit", type=int, default=200)
    s.add_argument("--query", default="")
    s.set_defaults(func=cmd_cloud)

    return p


def main(argv: list[str] | None = None) -> int:
    # UX improvement: allow --workspace to appear anywhere (before or after subcommand)
    av = list(argv) if argv is not None else None
    if av is None:
        import sys

        av = sys.argv[1:]

    if "--workspace" in av:
        i = av.index("--workspace")
        if i > 0 and i + 1 < len(av):
            ws = av[i + 1]
            # remove pair
            del av[i : i + 2]
            # prepend
            av = ["--workspace", ws] + av

    args = build_parser().parse_args(av)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
