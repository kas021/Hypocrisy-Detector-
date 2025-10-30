
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np

# Optional ONNX runtime acceleration
_ORT_OK = True
try:
    import onnxruntime as ort
except Exception:
    _ORT_OK = False
    ort = None

from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

LABELS = ["contradiction", "neutral", "entailment"]

class NLIScorer:
    """
    If backend/nli_onnx exists with model.onnx and tokenizer files, use ONNX.
    Otherwise fall back to a PyTorch Transformers pipeline (roberta-base MNLI).
    """
    def __init__(self, onnx_dir: str = "backend/nli_onnx", hf_model: str = "cross-encoder/nli-roberta-base"):
        self.onnx_dir = Path(onnx_dir)
        self.use_onnx = _ORT_OK and self._onnx_available()
        if self.use_onnx:
            self.session = ort.InferenceSession(str(self.onnx_dir/"model.onnx"), providers=["CPUExecutionProvider"])
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.onnx_dir))
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(hf_model)
            self.pipe = pipeline("text-classification", model=hf_model, tokenizer=self.tokenizer, return_all_scores=True)

    def _onnx_available(self) -> bool:
        return (self.onnx_dir/"model.onnx").exists() and (self.onnx_dir/"tokenizer.json").exists()

    def score(self, claim: str, texts: List[str]) -> List[Dict]:
        if not texts:
            return []
        if self.use_onnx:
            return self._score_onnx(claim, texts)
        else:
            return self._score_pipeline(claim, texts)

    def _score_pipeline(self, claim: str, texts: List[str]) -> List[Dict]:
        pairs = [(claim, t) for t in texts]
        outs = self.pipe(pairs, truncation=True)
        results = []
        for scores in outs:
            # scores is list of dicts with 'label' and 'score'
            by_label = {d["label"].lower(): float(d["score"]) for d in scores}
            # Map to fixed order
            vec = [by_label.get(k, 0.0) for k in ["CONTRADICTION".lower(), "NEUTRAL".lower(), "ENTAILMENT".lower()]]
            label = LABELS[int(np.argmax(vec))]
            results.append({"probs": vec, "label": label})
        return results

    def _score_onnx(self, claim: str, texts: List[str]) -> List[Dict]:
        # Tokenize batch
        pairs = [(claim, t) for t in texts]
        enc = self.tokenizer([a for a,b in pairs], [b for a,b in pairs], padding=True, truncation=True, return_tensors="np")
        ort_inputs = {k: v for k, v in enc.items()}
        logits = self.session.run(None, ort_inputs)[0]  # (N, 3)
        # softmax
        e = np.exp(logits - logits.max(axis=1, keepdims=True))
        probs = e / e.sum(axis=1, keepdims=True)
        results = []
        for p in probs:
            label = LABELS[int(np.argmax(p))]
            results.append({"probs": p.tolist(), "label": label})
        return results
