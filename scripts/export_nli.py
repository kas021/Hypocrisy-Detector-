"""Optional helper to export the NLI model to ONNX."""
from __future__ import annotations

import sys
from pathlib import Path

from backend.config import get_config

MODEL_NAME = "cross-encoder/nli-deberta-v3-xsmall"
OUTPUT_DIR = Path("backend/nli_onnx")


def main() -> int:
    try:
        from optimum.exporters.onnx import main_export
    except Exception:  # pragma: no cover - optional dependency
        print("Install optimum[onnxruntime] to export ONNX models", file=sys.stderr)
        return 0

    config = get_config()
    model_name = config.get("HF_NLI_MODEL", MODEL_NAME)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    main_export(
        model_name_or_path=model_name,
        output=OUTPUT_DIR,
        task="text-classification",
    )
    print(f"Exported {model_name} to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
