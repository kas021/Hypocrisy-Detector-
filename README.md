
# Contradiction Finder (corrected build)

Local-only system that finds possible contradictions in a single speaker’s statements,
with timestamped receipts and auto-extracted video clips.

## Quick start

```bash
make install
make init-db

# Ingest one pair (repeat for each video+transcript)
make ingest VIDEO=/path/to/video.mp4 SUB=/path/to/transcript.srt SOURCE="YouTube" DATE="2024-03-15" TITLE="Interview Title"

# Precompute embeddings (desktop or Pi)
python tools/export_embeds.py

# Export NLI model on desktop (once), then copy backend/nli_onnx/ to the Pi
python tools/export_nli_to_onnx.py

# Run
make run
# open http://<pi-ip>:7860
```

## Notes

- Keep everything offline at runtime.
- Only show short, attributed quotes with timestamps.
- No speaker ID. Pure transcript alignment and NLI.
