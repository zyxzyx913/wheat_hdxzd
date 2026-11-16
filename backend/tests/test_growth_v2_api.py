"""V2.0 一体化长势接口与历史记录测试。"""
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.main import create_app


def image_bytes():
    image = Image.new("RGB", (8, 8), (20, 180, 30))
    stream = BytesIO(); image.save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def api(tmp_path):
    with TestClient(create_app(Settings(storage_root=tmp_path / "web"))) as client:
        yield client


def test_growth_v2_analyze_returns_real_vigor_and_history(api):
    response = api.post("/api/growth/analyze", data={"algorithm": "ExG", "plot_id": "PLOT_A01"}, files={"file": ("wheat.png", image_bytes(), "image/png")})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["analysis_id"] == result["task_id"]
    assert result["plot_id"] == "PLOT_A01"
    assert 0 <= result["vigor_score"] <= 100
    assert result["evaluation_version"] == "growth-vigor-v1.1-rule"
    assert result["vegetation_coverage"]["fraction"] == result["growth_analysis"]["metrics"]["vegetation_coverage"]["fraction"]
    history = api.get("/api/growth/history")
    assert history.status_code == 200
    assert history.json()["items"][0]["analysis_id"] == result["analysis_id"]
    assert history.json()["items"][0]["plot_id"] == "PLOT_A01"
    detail = api.get(f"/api/growth/history/{result['analysis_id']}")
    assert detail.status_code == 200
    assert detail.json()["vigor_score"] == result["vigor_score"]
    assert detail.json()["plot_id"] == "PLOT_A01"


def test_growth_v2_rejects_invalid_input(api):
    response = api.post("/api/growth/analyze", files={"file": ("bad.png", b"not an image", "image/png")})
    assert response.status_code == 400
    assert "original_url" not in response.json()


def test_growth_v2_history_delete_removes_only_web_record(api):
    response = api.post("/api/growth/analyze", files={"file": ("wheat.png", image_bytes(), "image/png")})
    analysis_id = response.json()["analysis_id"]
    deleted = api.delete(f"/api/growth/history/{analysis_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
    assert api.get(f"/api/growth/history/{analysis_id}").status_code == 404
