"""Run the FastAPI frontend with sensible defaults."""
from __future__ import annotations

import uvicorn


def main() -> None:
    host = "127.0.0.1"
    port = 7860
    uvicorn.run("frontend.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
