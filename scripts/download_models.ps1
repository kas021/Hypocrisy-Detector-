# Optional: download the embedding model locally for offline use
    .\.venv\Scripts\Activate.ps1
    python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2').save('backend/embed_model')
print('✓ embed_model saved to backend/embed_model')
PY