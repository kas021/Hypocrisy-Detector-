# Hypocrisy Detector

A local-first FastAPI app that records speech, transcribes audio on-device, and surfaces likely
contradictions by comparing the new statement against a curated transcript corpus.

## Quickstart (Windows-friendly)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python scripts/ingest.py  # loads the bundled sample transcript
uvicorn frontend.app:app --host 127.0.0.1 --port 7860
```

Then visit <http://127.0.0.1:7860>. The `/health` route returns `{ "ok": true }` for CI smoke tests.

### Python alternatives to PowerShell helpers

The repository ships PowerShell scripts for backwards compatibility, but the primary entry points
are the Python wrappers under `scripts/`:

| Task | Command |
|------|---------|
| Start the app | `python scripts/run.py` |
| Ingest subtitles | `python scripts/ingest.py --subtitle samples/media/your_clip.srt` |
| Export NLI model to ONNX (optional) | `python scripts/export_nli.py` |

## Using your own transcripts

1. Place SRT or VTT files inside `samples/media/` (or another folder inside the repo).
2. Run `python scripts/ingest.py --subtitle relative/path/to/your_file.srt`.
3. The SQLite database and embeddings live under `data/db/` with transcripts under `data/transcripts/`.

Each ingestion splits subtitles into atomic statements, stores them in SQLite, and writes
sentence-transformer embeddings for quick retrieval.

## Voice recording + live hypocrisy check

The single-page frontend uses Tailwind (CDN) and htmx. Click **Start recording** to capture audio via
MediaRecorder. Once you stop, the browser posts a WebM blob to `/api/transcribe`, which runs the
local `faster-whisper` speech-to-text pipeline (if installed) and ingests the resulting transcript.
The textarea automatically fills with the latest transcription so you can run the hypocrisy check.

Press **Run hypocrisy check** to call `/api/hypocrisy`. The backend retrieves likely matches using
embeddings, scores each with the DeBERTa NLI model, and returns ranked contradictions with scores,
source metadata, and optional jump-to timestamps.

## Optional ONNX export

PyTorch is the default inference path. If `backend/nli_onnx/model.onnx` exists and `onnxruntime`
imports successfully, the app will switch to the ONNX runtime automatically. Use `python scripts/export_nli.py`
to generate the ONNX bundle (requires `optimum[onnxruntime]`). Missing files never crash the app—the
backend falls back to PyTorch.

## Extras

`faster-whisper` is optional. Install it with `pip install faster-whisper` to enable transcription.
Without it, the `/api/transcribe` endpoint returns a friendly 400 with installation instructions.

## Troubleshooting

- **Tokenizer model downloads are slow** – Pre-download models by running `python -m backend.config`
to materialize directories, then `python scripts/ingest.py` while online to populate caches.
- **ONNX files missing** – The backend logs a warning and uses PyTorch automatically. Run
  `python scripts/export_nli.py` once to generate ONNX weights if you prefer them.
- **faster-whisper not installed** – The transcription endpoint will respond with a 400 instructing you
to install the package. Add it to your environment when you want local speech-to-text.
- **Database reset** – Delete the `data/` folder to start clean. Directories are recreated automatically
  when you run `python -m backend.config` or start the app.

## Acceptance checks

1. `python -m backend.config` prints the resolved configuration and creates data folders.
2. `python backend/ingest.py --subtitle samples/media/your_clip.srt` ingests the bundled sample.
3. `uvicorn frontend.app:app --host 127.0.0.1 --port 7860` serves the UI and `/health` returns `{ "ok": true }`.
4. Posting `audio/webm` blobs to `/api/transcribe` stores transcripts and updates the database.
5. Sending `{ "text": "The sky is not blue" }` to `/api/hypocrisy` returns ranked contradictions.
