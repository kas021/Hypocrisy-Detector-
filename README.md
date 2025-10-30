# Hypocrisy Detector

A single FastAPI application that records speech, transcribes audio locally, and surfaces likely
contradictions by comparing the latest statement against a curated corpus of transcripts, speeches,
and scraped sources.

## Quickstart

### Windows (Command Prompt)

```cmd
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m backend.config
.venv\Scripts\python -m scripts.ingest --srt samples/media/your_clip.srt --title "Sample"
.venv\Scripts\python -m scripts.run
```

### Linux or WSL

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m backend.config
python -m scripts.ingest --srt samples/media/your_clip.srt --title "Sample"
python -m scripts.run
```

After the server starts, open <http://127.0.0.1:7860>. A `/health` endpoint returns `{ "ok": true }`
for smoke tests.

## Core workflows

### Python CLIs

The repo ships PowerShell scripts for legacy users, but the Python entry points below are the primary
interfaces:

| Task | Command |
| ---- | ------- |
| Start the app with auto-setup | `python -m scripts.run` |
| Ingest SRT, VTT, or text files | `python -m scripts.ingest --srt <path>` or `--text <path>` |
| Run the scraper | `python -m scripts.scrape --providers govuk,whitehouse --limit 50 --out data/raw/scraped.sqlite` |
| Export the optional ONNX model | `python -m scripts.export_nli` |

All paths are relative to the repository root. No PowerShell execution policy tweaks are required.

### Voice recording and live detection

1. Click **Start recording** to capture microphone audio in the browser. MediaRecorder creates a WebM
   blob entirely on-device.
2. Stop the recording to POST the blob to `/api/transcribe`. If `faster-whisper` is installed it runs
   locally, writes a WebVTT transcript under `data/transcripts/`, ingests the segments, and fills the
   textarea with the detected speech.
3. Edit the text if needed, optionally ingest it into the corpus, then press **Run hypocrisy check**.
   The backend fetches candidate segments via sentence-transformer similarity, scores each with the
   DeBERTa cross-encoder, and returns ranked contradictions with score, evidence, source metadata,
   and links or timestamp hints.

### Use your own caption files or raw text

* Upload `.srt` or `.vtt` files from the UI, or run `python -m scripts.ingest --srt path/to/file.srt`.
* For plain text, run `python -m scripts.ingest --text path/to/file.txt` or click **Ingest typed text**
  in the UI. Each line becomes a segment stored in SQLite with embeddings.
* The database lives at `data/db/corpus.db`. Transcripts and uploads are under `data/transcripts/` and
  `data/uploads/` respectively.

### Scraping external sources

A lightweight scraper normalizes government feeds and YouTube channels into SQLite:

```bash
python -m backend.scraper.run --providers govuk,whitehouse --limit 10 --out data/raw/scraped.sqlite
python -m backend.ingest --from-scraped data/raw/scraped.sqlite
```

The UI also exposes **Run scraper** so you can fetch and optionally ingest fresh items from the
configured providers. Scraped rows live in `data/raw/scraped.sqlite` and can be ingested into the
main corpus with `--from-scraped`.

## Optional ONNX export

PyTorch is the default inference backend. If `backend/nli_onnx/model.onnx` exists and
`onnxruntime` imports successfully, the scorer switches to ONNX at runtime. Export the ONNX bundle
with `python -m scripts.export_nli`; missing files never crash the app because it falls back to the
Hugging Face model automatically.

## Testing

Run the minimal pytest suite:

```bash
pytest -q
```

The tests validate configuration paths, the NLIScorer interface (using a stub backend), subtitle
ingestion, and scraper storage upserts.

## Troubleshooting

- **Tokenizer cache issues** – Delete `data/` and rerun `python -m backend.config` followed by an
  ingestion command to recreate directories and warm caches.
- **ONNX backend unavailable** – If `NLI_BACKEND=onnx` is set but the ONNX file is missing or
  `onnxruntime` fails to import, the scorer logs a warning and defaults to PyTorch.
- **faster-whisper missing** – The transcription endpoint responds with a 400 containing installation
  instructions. Install `faster-whisper` to enable local speech-to-text.
- **yt-dlp optional** – The YouTube provider logs a warning and skips if `yt-dlp` is not installed.
  Install it if you want automated channel harvesting.

## Acceptance checklist

1. `python -m backend.config` prints resolved directories and creates `data/` subfolders.
2. `python -m scripts.ingest --srt samples/media/your_clip.srt --title "Sample"` ingests the bundled
   transcript and populates SQLite.
3. `python -m scripts.run` launches uvicorn on `127.0.0.1:7860` and `/health` returns `{ "ok": true }`.
4. Posting `audio/webm` to `/api/transcribe` returns transcript segments and updates the corpus.
5. Posting `{ "text": "The sky is not blue" }` to `/api/detect` yields contradictions scored above 0.5
   when the sample clip is ingested.
6. `python -m backend.scraper.run --providers govuk --limit 5 --out data/raw/scraped.sqlite` runs
   without error and writes rows for later ingestion.
=======
![Project Shield](https://user-gen-media-assets.s3.amazonaws.com/seedream_images/c32a1de6-545a-48db-a443-7cc25ca3454f.png)

---

**STATUS: UNDER ACTIVE DEVELOPMENT**

This project is an open-source, work-in-progress hypocrisy and contradiction detector for public statements, focused primarily on politics, journalism, and social transparency. It is not yet feature complete, and may have bugs or missing documentation. Your feedback and contributions are welcomed!

**Legal Disclaimer / Protection:**
- This repository is distributed "AS IS" WITHOUT WARRANTY of any kind. The creator accepts NO LIABILITY for use or misuse. 
- All functionality is provided for informational and educational purposes only. Use responsibly and ethically.
- No responsibility is taken for any consequences caused by use, reliance, or misinterpretation.
- The creator does not endorse or support any malicious activity.

**Purpose:**
- Help society by providing tools to analyze public statements and enable individuals to detect hypocrisy or lies using open data and the latest AI models. 
- Intended for non-commercial, educational, and research use only.

**Use at your own risk. The creator is NOT legally or personally responsible for any result.**

---

# Hypocrisy Detector
A local-first FastAPI app that records speech, transcribes audio on-device, and surfaces likely
contradictions by comparing the new statement against a curated transcript corpus.
## Quickstart (Windows-friendly)
```
powershell
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
|------|---------||
| Start the app | `python scripts/run.py` |

