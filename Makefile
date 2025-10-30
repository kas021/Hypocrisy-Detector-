
.PHONY: install init-db ingest run test deploy-to-pi

install:
\tpip install -r requirements.txt

init-db:
\tpython -c "from backend.ingest import init_db; init_db('backend/db.sqlite3')"

# Usage: make ingest VIDEO=video.mp4 SUB=transcript.srt SOURCE="YouTube" DATE="2024-01-01" TITLE="Interview"
ingest:
\tpython -m backend.ingest --db backend/db.sqlite3 --video $(VIDEO) --subtitle $(SUB) --source "$(SOURCE)" --date "$(DATE)" --title "$(TITLE)" --url "$(URL)"

run:
\tuvicorn frontend.app:app --host 0.0.0.0 --port 7860

test:
\tpytest -q

deploy-to-pi:
\trsync -avz backend/db.sqlite3 $(PI_HOST):~/contradiction-finder/backend/
\trsync -avz backend/nli_onnx/ $(PI_HOST):~/contradiction-finder/backend/nli_onnx/
\trsync -avz clips/ $(PI_HOST):~/contradiction-finder/clips/
