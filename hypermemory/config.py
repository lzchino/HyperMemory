from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    workspace: Path

    @staticmethod
    def from_env(workspace: str | None = None) -> "Config":
        ws = workspace or os.environ.get("OPENCLAW_WORKSPACE") or os.getcwd()
        return Config(workspace=Path(ws).resolve())
