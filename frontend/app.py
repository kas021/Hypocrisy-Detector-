
import os
from pathlib import Path
from typing import Dict, Any, List

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.index import EmbeddingRetriever
from backend.nli import NLIScorer

DB = "backend/db.sqlite3"

app = FastAPI(title="Contradiction Finder (Fixed)")

# Static files
static_dir = Path("frontend/static")
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

nli = NLIScorer("backend/nli_onnx")
retriever = EmbeddingRetriever(db_path=DB)

@app.get("/", response_class=HTMLResponse)
def home():
    return (Path("frontend/static/index.html").read_text(encoding="utf-8"))

@app.get("/api/search")
def api_search(claim: str = Query(...), top_k: int = 10) -> Dict[str, Any]:
    items = retriever.search(claim, top_k=top_k)
    texts = [it["text"] for it in items]
    nli_out = nli.score(claim, texts)
    for it, sc in zip(items, nli_out):
        it["nli"] = sc
    return {"claim": claim, "results": items}
