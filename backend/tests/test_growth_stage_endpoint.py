"""生育期接口的真实产物契约测试。"""
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings
from backend.app.main import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    not (PROJECT_ROOT / "results/growth_stage_initial/selected_model.joblib").is_file(),
    reason="生育期初步分类器尚未生成",
)
def test_growth_stage_endpoint_returns_real_probabilities(tmp_path):
    image = next((PROJECT_ROOT / "data/processed/growth_stage/images").glob("*.jpeg"), None)
    if image is None:
        pytest.skip("CGIAR 图片尚未解压")
    settings = Settings(storage_root=tmp_path / "web")
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/growth-stage/predict", files={"file": (image.name, image.read_bytes(), "image/jpeg")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "succeeded"
    assert 1 <= result["predicted_stage"] <= 7
    assert abs(sum(result["probabilities"].values()) - 1.0) < 1e-6
    assert result["device"] == "cpu"
