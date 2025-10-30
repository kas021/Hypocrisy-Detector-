"""Natural language inference scoring helpers."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

try:  # pragma: no cover - optional dependency for tests
    import numpy as np
except Exception:  # pragma: no cover - fallback for environments without numpy
    np = None  # type: ignore

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .config import REPO_ROOT, ensure_dirs, get_config


LOGGER = logging.getLogger(__name__)


@dataclass
class _PytorchBackend:
    tokenizer: AutoTokenizer
    model: AutoModelForSequenceClassification

    def score(self, pairs: Sequence[Tuple[str, str]]):
        inputs = self.tokenizer(
            [premise for premise, _ in pairs],
            [hypothesis for _, hypothesis in pairs],
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=-1)
        contradiction_idx = 0 if probs.shape[-1] == 1 else 0
        # huggingface cross-encoders typically use [contradiction, neutral, entailment]
        if probs.shape[-1] >= 3:
            contradiction_idx = 0
        elif probs.shape[-1] == 2:
            # binary classification - assume index 0 is contradiction
            contradiction_idx = 0
        return probs[:, contradiction_idx].cpu().numpy().tolist()


@dataclass
class _OnnxBackend:
    session: "onnxruntime.InferenceSession"
    tokenizer: AutoTokenizer

    def score(self, pairs: Sequence[Tuple[str, str]]):
        inputs = self.tokenizer(
            [premise for premise, _ in pairs],
            [hypothesis for _, hypothesis in pairs],
            padding=True,
            truncation=True,
            return_tensors="np",
        )
        ort_inputs = {k: v for k, v in inputs.items()}
        outputs = self.session.run(None, ort_inputs)
        logits = outputs[0]
        exp = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
        probs = exp / exp.sum(axis=-1, keepdims=True)
        contradiction_idx = 0
        if probs.shape[-1] >= 3:
            contradiction_idx = 0
        elif probs.shape[-1] == 2:
            contradiction_idx = 0
        return probs[:, contradiction_idx].tolist()


class NLIScorer:
    """Score hypothesis/premise pairs using PyTorch or ONNX."""

    def __init__(self, model_name: str | None = None) -> None:
        config = get_config()
        ensure_dirs()
        self.model_name = model_name or config.get(
            "HF_NLI_MODEL", "cross-encoder/nli-deberta-v3-xsmall"
        )
        self.backend_preference = os.environ.get(
            "NLI_BACKEND", config.get("NLI_BACKEND", "hf")
        ).lower()
        self.backend = self._load_backend()

    def _load_tokenizer(self) -> AutoTokenizer:
        last_exc: Exception | None = None
        for kwargs in (
            {"use_fast": True},
            {"use_fast": True, "force_download": True},
            {"use_fast": False},
        ):
            try:
                LOGGER.debug("Loading tokenizer with args %s", kwargs)
                tokenizer = AutoTokenizer.from_pretrained(self.model_name, **kwargs)
                return tokenizer
            except Exception as exc:  # pragma: no cover - best-effort logging
                last_exc = exc
                LOGGER.warning("Tokenizer load failed (%s): %s", kwargs, exc)
        raise RuntimeError(f"Unable to load tokenizer for {self.model_name}: {last_exc}")

    def _load_backend(self):
        preference = self.backend_preference
        if preference == "onnx":
            backend = self._load_onnx_backend()
            if backend is not None:
                return backend
            LOGGER.warning("Falling back to Hugging Face backend for NLI")
        return self._load_hf_backend()

    def _load_onnx_backend(self):
        onnx_path = REPO_ROOT / "backend" / "nli_onnx" / "model.onnx"
        if np is None:
            LOGGER.warning("NumPy is required for ONNX inference; falling back to Hugging Face backend")
            return None
        if not onnx_path.exists():
            LOGGER.warning("Requested ONNX backend but model not found at %s", onnx_path)
            return None
        try:
            import onnxruntime as ort  # type: ignore

            LOGGER.info("Loading NLI model from ONNX: %s", onnx_path)
            sess = ort.InferenceSession(str(onnx_path))
            tokenizer = self._load_tokenizer()
            return _OnnxBackend(session=sess, tokenizer=tokenizer)
        except ImportError:
            LOGGER.warning("onnxruntime not available - falling back to Hugging Face backend")
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to load ONNX backend: %s", exc)
        return None

    def _load_hf_backend(self):
        LOGGER.info("Loading NLI model with PyTorch: %s", self.model_name)
        tokenizer = self._load_tokenizer()

        model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        model.eval()
        return _PytorchBackend(tokenizer=tokenizer, model=model)

    def score(self, premise: str, hypothesis: str) -> float:
        result = self.score_batch([(premise, hypothesis)])
        return result[0]

    def score_batch(self, pairs: Iterable[Tuple[str, str]]) -> List[float]:
        pair_list = list(pairs)
        if not pair_list:
            return []
        return self.backend.score(pair_list)


__all__ = ["NLIScorer"]
