# mf-embeddings (local CUDA embedding service)

In the reference deployment, embeddings are generated locally on GPU via a small FastAPI server.

## API
- `GET /health` → `{ ok, model, device, cuda }`
- `POST /embed` with JSON `{ "inputs": "text" }` or `{ "inputs": ["...", "..."] }`
  - returns: `[[float, ...], ...]`

## Example server (FastAPI)

```py
import os
from typing import List, Union

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

MODEL_ID = os.environ.get("EMBED_MODEL_ID", "intfloat/e5-small-v2")
DEVICE = os.environ.get("EMBED_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

app = FastAPI(title="mf-embeddings", version="0.1")
model: SentenceTransformer | None = None

class EmbedRequest(BaseModel):
    inputs: Union[str, List[str]]

@app.on_event("startup")
def _load_model():
    global model
    model = SentenceTransformer(MODEL_ID, device=DEVICE)

@app.get("/health")
def health():
    return {"ok": True, "model": MODEL_ID, "device": DEVICE, "cuda": torch.cuda.is_available()}

@app.post("/embed")
def embed(req: EmbedRequest):
    assert model is not None
    texts = req.inputs if isinstance(req.inputs, list) else [req.inputs]
    emb = model.encode(texts, normalize_embeddings=True).tolist()
    return emb
```

## Running

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sentence-transformers torch

export EMBED_MODEL_ID=intfloat/e5-small-v2
export EMBED_DEVICE=cuda
uvicorn server:app --host 127.0.0.1 --port 8080
```

## Notes
- E5 models work best with prefixes:
  - queries: `"query: ..."`
  - passages: `"passage: ..."`
