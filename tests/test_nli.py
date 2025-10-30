
import pytest
from pathlib import Path

@pytest.mark.skipif(not Path("backend/nli_onnx/model.onnx").exists(), reason="NLI ONNX not exported yet")
def test_nli_model_present():
    assert Path("backend/nli_onnx/model.onnx").exists()
