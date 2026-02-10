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
    cfg = Config.from_env(args.workspace)
    script = Path(__file__).resolve().parent.parent / "scripts" / "memory-index.sh"
    return _run(["bash", str(script), str(cfg.workspace)])


def cmd_retrieve(args: argparse.Namespace) -> int:
    cfg = Config.from_env(args.workspace)
    script = Path(__file__).resolve().parent.parent / "scripts" / "memory-retrieve.sh"
    return _run(["bash", str(script), args.mode, args.query])


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
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
