# Windows guide

The Python CLIs shipped with the project keep everything PowerShell-free. The steps below assume a
Command Prompt session opened at the repository root.

## One-time setup

```cmd
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

Optional extras:

- `pip install faster-whisper` enables the `/api/transcribe` endpoint for microphone recordings.
- `pip install optimum[onnxruntime]` lets you run `python -m scripts.export_nli` to build the ONNX
  inference bundle.

## Check configuration and ingest the sample

```cmd
.venv\Scripts\python -m backend.config
.venv\Scripts\python -m scripts.ingest --srt samples\media\your_clip.srt --title "Sample"
```

`python -m backend.config` creates the `data/` hierarchy (db, transcripts, uploads, raw). The ingest
command loads the bundled transcript so the detector returns results immediately.

## Run the app

```cmd
.venv\Scripts\python -m scripts.run
```

This command ensures dependencies are installed, prints the resolved paths, and launches uvicorn on
`http://127.0.0.1:7860`. Visit the page to record speech, upload captions, or paste text, then click
**Run hypocrisy check** to see ranked contradictions.

## Optional scrape flow

```cmd
.venv\Scripts\python -m scripts.scrape --providers govuk,whitehouse --limit 25 --out data\raw\scraped.sqlite
.venv\Scripts\python -m backend.ingest --from-scraped data\raw\scraped.sqlite
```

The UI also exposes a **Run scraper** button that triggers the same providers. Scraped rows are stored
under `data/raw/` and can be ingested into the main corpus for contradiction detection.
