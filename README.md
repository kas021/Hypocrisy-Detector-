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
