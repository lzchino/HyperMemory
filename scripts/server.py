import os

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import List, Union

MODEL_ID = os.environ.get("EMBED_MODEL_ID", "intfloat/e5-small-v2")
DEVICE = os.environ.get("EMBED_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
HOST = os.environ.get("EMBED_HOST", "127.0.0.1")
PORT = int(os.environ.get("EMBED_PORT", "8080"))

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
