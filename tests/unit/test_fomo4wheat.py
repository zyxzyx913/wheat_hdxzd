"""FoMo 适配器单元测试；不下载权重、不运行深度模型。"""

from pathlib import Path
import tempfile

from PIL import Image
import numpy as np
import pytest

from wheat_phenotyping.foundation_models.fomo4wheat.extractor import (
    EXPECTED_FEATURE_DIMENSION, FoMo4WheatExtractor, official_preprocess,
)


def test_official_preprocess_is_rgb_224_float_tensor():
    tensor = official_preprocess(Image.new("RGBA", (350, 180), (20, 180, 30, 90)))
    assert tuple(tensor.shape) == (3, 224, 224)
    assert str(tensor.dtype) == "torch.float32"
    assert np.isfinite(tensor.numpy()).all()


def test_missing_weight_is_explicit():
    with pytest.raises(FileNotFoundError):
        FoMo4WheatExtractor("missing-fomo-base.pth")


def test_invalid_device_is_explicit(tmp_path):
    path = tmp_path / "weight.pth"
    path.write_bytes(b"not-a-weight")
    with pytest.raises(ValueError, match="SHA-256"):
        FoMo4WheatExtractor(path)


def test_contract_constants():
    assert EXPECTED_FEATURE_DIMENSION == 768
