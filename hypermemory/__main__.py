from __future__ import annotations

import argparse
import json
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
    cfg = Config.from_env(args.workspace)
    script = Path(__file__).resolve().parent.parent / "scripts" / "memory-eval.sh"
    cmd = ["bash", str(script), str(cfg.workspace)]
    if args.fast:
        cmd.append("--fast")
    return _run(cmd)


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
