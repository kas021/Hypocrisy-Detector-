"""FastAPI frontend for the hypocrisy detector."""
from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path

from fastapi import (FastAPI, File, Form, HTTPException, Request, UploadFile)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from backend.config import REPO_ROOT, ensure_dirs
from backend.hypocrisy import HypocrisyDetector
from backend.ingest import (
    ingest_from_scraped_sqlite,
    ingest_subtitle,
    ingest_text_snippet,
)
from backend.nli import NLIScorer
from backend.transcribe import transcribe_audio
from backend.scraper.providers import PROVIDERS
from backend.scraper.run import run_scraper

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

    return {
        "segments": segments,
        "transcript": str(transcript_path.relative_to(REPO_ROOT)),
        "ingested": ingested,
    }


class TextIngestRequest(BaseModel):
    text: str
    title: str = Field(default="Ad-hoc statement")


@app.post("/api/ingest_text")
async def api_ingest_text(payload: TextIngestRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text body is required")
    count = ingest_text_snippet(text, payload.title or "Ad-hoc statement")
    if count == 0:
        raise HTTPException(status_code=400, detail="No statements found to ingest")
    return {"ingested": count}


@app.post("/api/ingest_srt")
async def api_ingest_srt(file: UploadFile = File(...), title: str = Form("Uploaded subtitle")):
    config = ensure_dirs()
    uploads_dir = REPO_ROOT / config["DATA_DIR"] / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "captions.srt").suffix or ".srt"
    temp_path = uploads_dir / f"{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(await file.read())
    try:
        count = ingest_subtitle(temp_path, source_title=title or temp_path.stem)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if count == 0:
        raise HTTPException(status_code=400, detail="Subtitle ingestion failed")
    return {"ingested": count, "path": str(temp_path.relative_to(REPO_ROOT))}


class DetectRequest(BaseModel):
    text: str
    top_k: int | None = Field(default=5, ge=1, le=20)


def _serialize_hit(hit):
    return {
        "score": hit.score,
        "corpus_text": hit.corpus_text,
        "source_type": hit.source_type,
        "source_title": hit.source_title,
        "url_or_path": hit.url_or_path,
        "ts_start": hit.ts_start,
        "ts_end": hit.ts_end,
        "extra": hit.extra or {},
    }


@app.post("/api/detect")
async def api_detect(payload: DetectRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Statement text is required")
    hits = detector.check(text, top_k=payload.top_k or 5)
    return {"statement": text, "hits": [_serialize_hit(hit) for hit in hits]}


@app.post("/api/hypocrisy")
async def api_hypocrisy(payload: DetectRequest):
    return await api_detect(payload)


class ScrapeRequest(BaseModel):
    providers: list[str] | None = None
    since: str | None = None
    limit: int | None = Field(default=None, ge=1)
    ingest: bool = False


@app.post("/api/scrape")
async def api_scrape(payload: ScrapeRequest):
    config = ensure_dirs()
    selected = payload.providers or list(PROVIDERS.keys())
    missing = [slug for slug in selected if slug not in PROVIDERS]
    if missing:
        raise HTTPException(status_code=400, detail=f"Unknown providers: {', '.join(missing)}")
    try:
        since = dt.datetime.fromisoformat(payload.since) if payload.since else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    provider_instances = [PROVIDERS[slug]() for slug in selected]
    out_path = REPO_ROOT / config["DATA_DIR"] / "raw" / "scraped.sqlite"
    summary = run_scraper(
        providers=provider_instances,
        since=since,
        limit=payload.limit,
        out_path=out_path,
    )
    ingested = 0
    if payload.ingest:
        ingested = ingest_from_scraped_sqlite(out_path)
    return {"summary": summary, "sqlite": str(out_path.relative_to(REPO_ROOT)), "ingested": ingested}
