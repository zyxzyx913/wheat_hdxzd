"""长势 V1 API 测试：验证四种算法均返回真实掩膜驱动指标。"""

from io import BytesIO
import json

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.main import create_app


def rgb_bytes():
    image = Image.new("RGB", (8, 6), (30, 70, 35))
    for x in range(4):
        for y in range(3):
            image.putpixel((x, y), (20, 180, 30))
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


@pytest.fixture
def api(tmp_path):
    settings = Settings(storage_root=tmp_path / "web")
    with TestClient(create_app(settings)) as client:
        yield client, settings


@pytest.mark.parametrize("algorithm", ["ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion"])
def test_all_algorithms_return_growth_v1_and_saved_json(api, algorithm):
    client, settings = api
    response = client.post("/api/image/analyze", data={"algorithm": algorithm}, files={"file": ("wheat.png", rgb_bytes(), "image/png")})
    assert response.status_code == 200, response.text
    result = response.json()
    growth = result["growth_analysis"]
    assert growth["version"] == "growth-analysis-v1"
    assert growth["algorithm"] == algorithm
    coverage = growth["metrics"]["vegetation_coverage"]
    assert coverage["vegetation_pixel_count"] == result["vegetation_pixel_count"]
    assert coverage["valid_pixel_count"] == result["total_valid_pixels"]
    assert coverage["fraction"] == result["vegetation_ratio"]
    assert result["growth_analysis_url"].endswith("/growth_analysis.json")
    directory = settings.storage_root / "analyses" / result["task_id"]
    saved = json.loads((directory / "growth_analysis.json").read_text(encoding="utf-8"))
    assert saved == growth
    served = client.get(result["growth_analysis_url"])
    assert served.status_code == 200
    assert served.json()["task_id"] == result["task_id"]


def test_growth_api_does_not_return_grade_or_future_prediction(api):
    result = api[0].post("/api/image/analyze", files={"file": ("wheat.png", rgb_bytes(), "image/png")}).json()
    assert not {"growth_grade", "growth_stage", "future_growth", "yield_prediction"} & result["growth_analysis"].keys()
