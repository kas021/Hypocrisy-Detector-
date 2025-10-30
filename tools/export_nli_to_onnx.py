
"""
Export a small NLI model to ONNX and save tokenizer + config into backend/nli_onnx.
Uses 'cross-encoder/nli-roberta-base' which is compatible with tokenizers==0.15.2.
"""
from pathlib import Path
import onnx
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

OUT_DIR = Path("backend/nli_onnx")
HF_MODEL = "cross-encoder/nli-roberta-base"

def export_nli_model():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(HF_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(HF_MODEL)
    model.eval()

    # Dummy inputs
    ins = tokenizer("A", "B", return_tensors="pt")
    with torch.no_grad():
        torch.onnx.export(
            model,
            (ins["input_ids"], ins.get("attention_mask", None), ins.get("token_type_ids", None)),
            str(OUT_DIR / "model.onnx"),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "seq"},
                "attention_mask": {0: "batch", 1: "seq"},
                "token_type_ids": {0: "batch", 1: "seq"},
                "logits": {0: "batch"},
            },
            opset_version=17,
        )

    # Save tokenizer + config into same folder for offline use
    tokenizer.save_pretrained(OUT_DIR)
    model.config.save_pretrained(OUT_DIR)

    # Basic sanity
    onnx_model = onnx.load(str(OUT_DIR / "model.onnx"))
    onnx.checker.check_model(onnx_model)
    print("✓ Exported ONNX to", OUT_DIR)

if __name__ == "__main__":
    export_nli_model()
