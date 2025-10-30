"""Speech-to-text helpers using faster-whisper if available."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Dict, List

from fastapi import HTTPException

from .config import REPO_ROOT, ensure_dirs

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from faster_whisper import WhisperModel  # type: ignore

    _FAST_WHISPER_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    WhisperModel = None  # type: ignore
    _FAST_WHISPER_AVAILABLE = False


class TranscriptionDependencyError(RuntimeError):
    pass


def _format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def _write_vtt(segments: List[Dict[str, float | str]], transcript_path: Path) -> None:
    with transcript_path.open("w", encoding="utf-8") as handle:
        handle.write("WEBVTT\n\n")
        for index, segment in enumerate(segments, start=1):
            start = _format_timestamp(float(segment["start"]))
            end = _format_timestamp(float(segment["end"]))
            text = str(segment["text"]).strip()
            handle.write(f"{index}\n{start} --> {end}\n{text}\n\n")


def transcribe_audio(path: str) -> List[Dict[str, float | str]]:
    """Transcribe a local audio file and store a WebVTT transcript."""
    ensure_dirs()
    audio_path = Path(path)
    if not audio_path.exists():
        raise HTTPException(status_code=400, detail="Audio file not found")

    if not _FAST_WHISPER_AVAILABLE:
        msg = "faster-whisper not installed. pip install faster-whisper"
        print(msg, file=sys.stderr)
        raise HTTPException(status_code=400, detail=msg)

    model = WhisperModel("base", device="cpu")
    segments_iter, _ = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)

    segments: List[Dict[str, float | str]] = []
    for segment in segments_iter:
        segments.append(
            {
                "text": segment.text.strip(),
                "start": float(segment.start),
                "end": float(segment.end),
            }
        )

    config = ensure_dirs()
    data_dir = REPO_ROOT / config["DATA_DIR"]
    transcripts_dir = data_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = transcripts_dir / f"{audio_path.stem}.vtt"
    _write_vtt(segments, transcript_path)
    LOGGER.info("Saved transcript to %s", transcript_path)
    return segments


__all__ = ["transcribe_audio", "TranscriptionDependencyError"]
