#!/usr/bin/env python3
"""Tiny fake embedding server for CI.

Implements the mf-embeddings API:
- GET /health
- POST /embed {"inputs": [..]}

Returns deterministic unit-normalized vectors with small dims (default 16)
so pgvector indexing/search can be exercised without downloading models.
"""

from __future__ import annotations

import hashlib
import os
from typing import List, Union

from fastapi import FastAPI
from pydantic import BaseModel

DIMS = int(os.environ.get("FAKE_EMBED_DIMS", "16"))
HOST = os.environ.get("EMBED_HOST", "127.0.0.1")
PORT = int(os.environ.get("EMBED_PORT", "8080"))

app = FastAPI(title="fake-embeddings", version="0.1")


class EmbedRequest(BaseModel):
    inputs: Union[str, List[str]]


def embed_one(text: str) -> List[float]:
    # Deterministic pseudo-random vector from sha256.
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals = [(h[i % len(h)] / 255.0) for i in range(DIMS)]
    # normalize
    norm = sum(v * v for v in vals) ** 0.5 or 1.0
    return [v / norm for v in vals]


@app.get("/health")
def health():
    return {"ok": True, "model": "fake", "device": "cpu", "cuda": False, "dims": DIMS}


@app.post("/embed")
def embed(req: EmbedRequest):
    texts = req.inputs if isinstance(req.inputs, list) else [req.inputs]
    return [embed_one(t) for t in texts]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
