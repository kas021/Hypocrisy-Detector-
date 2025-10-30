
# Contradiction Finder — Fixed Build

This package replaces the incomplete files and gives you a working baseline.

## Prereqs
- Windows 10/11
- Python 3.10.x (exactly — do not use 3.11)
- FFmpeg installed (winget or choco), optional for media clipping

## One-time setup (PowerShell)
```powershell
# From the project root (this folder)
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -r requirements.txt

# Optional: download the small embedding model for offline use
python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2').save('backend/embed_model')
print('✓ embed_model saved to backend/embed_model')
PY

# Optional: export a small NLI model to ONNX for speed (or skip to use PyTorch fallback)
python tools\export_nli_to_onnx.py
```

## Ingest your data
You need a transcript file per video (SRT, VTT, or JSONL with start_ms/end_ms/text).
```powershell
# Example paths — change these to real files you have
$VIDEO = 'E:\media\your_clip.mp4'
$SUB   = 'E:\media\your_clip.srt'

# Create the DB and ingest
python -m backend.ingest --db backend\db.sqlite3 --video "$VIDEO" --subtitle "$SUB" --source "Your Channel" --date "2024-03-15" --title "Interview" --url "https://example.com/clip"
```

## Precompute embeddings
```powershell
python tools\export_embeds.py
```

## Run the app
```powershell
uvicorn frontend.app:app --host 127.0.0.1 --port 7860 --reload
# Open http://127.0.0.1:7860
```

## Notes
- If you skip ONNX export, the NLI scorer falls back to a PyTorch model (`cross-encoder/nli-roberta-base`), which is compatible with the pinned tokenizers version.
- If you see CUDA warnings, it will run on CPU automatically.
- If you change requirements, stick to Python 3.10 to avoid toolchain mismatches.
