"""FastAPI frontend for the hypocrisy detector."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from backend.config import REPO_ROOT, ensure_dirs
from backend.hypocrisy import HypocrisyDetector
from backend.ingest import ingest_subtitle
from backend.nli import NLIScorer
from backend.transcribe import transcribe_audio

app = FastAPI(title="Hypocrisy Detector")

ensure_dirs()
templates = Jinja2Templates(directory=str(REPO_ROOT / "frontend" / "templates"))

scorer = NLIScorer()
detector = HypocrisyDetector(scorer)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    config = ensure_dirs()
    uploads_dir = REPO_ROOT / config["DATA_DIR"] / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    temp_path = uploads_dir / f"{uuid.uuid4().hex}{suffix}"
    content = await file.read()
    temp_path.write_bytes(content)

    try:
        segments = transcribe_audio(str(temp_path))
    except HTTPException as exc:
        raise exc

    transcripts_dir = REPO_ROOT / config["DATA_DIR"] / "transcripts"
    transcript_path = transcripts_dir / f"{temp_path.stem}.vtt"

    try:
        ingested = ingest_subtitle(
            transcript_path, source_title=file.filename or temp_path.stem
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if ingested == 0:
        raise HTTPException(status_code=400, detail="Transcript ingestion failed")

    return {"segments": segments, "transcript": str(transcript_path.relative_to(REPO_ROOT))}


class HypocrisyRequest(BaseModel):
    text: str


@app.post("/api/hypocrisy")
async def api_hypocrisy(payload: HypocrisyRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Statement text is required")

    hits = detector.check(text)
    return {
        "statement": text,
        "hits": [
            {
                "score": hit.score,
                "corpus_text": hit.corpus_text,
                "source_type": hit.source_type,
                "source_title": hit.source_title,
                "url_or_path": hit.url_or_path,
                "ts_start": hit.ts_start,
                "ts_end": hit.ts_end,
            }
            for hit in hits
        ],
    }
