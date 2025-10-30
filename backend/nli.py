"""Natural language inference scoring helpers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np
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
        self.backend = self._load_backend()

    def _load_backend(self):
        onnx_path = REPO_ROOT / "backend" / "nli_onnx" / "model.onnx"
        if onnx_path.exists():
            try:
                import onnxruntime as ort  # type: ignore

                LOGGER.info("Loading NLI model from ONNX: %s", onnx_path)
                sess = ort.InferenceSession(str(onnx_path))
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name, use_fast=False
                )
                return _OnnxBackend(session=sess, tokenizer=tokenizer)
            except ImportError:
                LOGGER.warning(
                    "onnxruntime not available - falling back to PyTorch backend"
                )
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.warning("Failed to load ONNX backend: %s", exc)
        LOGGER.info("Loading NLI model with PyTorch: %s", self.model_name)
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, use_fast=False)
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
