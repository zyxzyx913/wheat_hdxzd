"""多算法 HTTP 回归：验证输出一致性与错误隔离，不评价模拟图精度。"""

from io import BytesIO
import hashlib
import json

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings, SUPPORTED_ALGORITHMS
from backend.app.main import create_app
from wheat_phenotyping.app.inference import predict_visible_mask
from wheat_phenotyping.data import load_rgb_image


def photo_fixture():
    """颜色变化夹具仅用于 API 数据传递检查，不属于真实实验数据。"""
    stream = BytesIO()
    image = Image.new("RGB", (3, 2))
    image.putdata([(20, 180, 30), (150, 90, 40), (200, 220, 0), (30, 90, 80), (0, 0, 0), (240, 240, 240)])
    image.save(stream, format="PNG")
    return stream.getvalue()


@pytest.mark.parametrize("algorithm", SUPPORTED_ALGORITHMS)
def test_each_algorithm_matches_existing_predictor_and_saved_mask(tmp_path, algorithm):
    settings = Settings(storage_root=tmp_path / "web")
    raw = photo_fixture()
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/image/analyze", files={"file": ("fixture.png", raw, "image/png")}, data={"algorithm": algorithm})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["algorithm"] == algorithm
        assert result["input_sha256"] == hashlib.sha256(raw).hexdigest()
        directory = settings.storage_root / "analyses" / result["task_id"]
        expected, metadata = predict_visible_mask(load_rgb_image(directory / "original.png"), algorithm, parameters=result["parameters"])
        assert result["algorithm_metadata"] == metadata
        for field in ("original_url", "mask_url", "overlay_url"):
            asset = client.get(result[field])
            assert asset.status_code == 200
            with Image.open(BytesIO(asset.content)) as image:
                image.load()
                assert image.size == (3, 2)
                if field == "mask_url":
                    assert image.mode == "L"
                    pixels = image.tobytes()
                    assert pixels == expected.pixels
                    assert result["vegetation_pixel_count"] == pixels.count(255)
                    assert result["vegetation_ratio"] == pixels.count(255) / len(pixels)
        saved = json.loads((directory / "record.json").read_text(encoding="utf-8"))
        assert saved["algorithm"] == algorithm
        assert saved["algorithm_metadata"] == metadata
        frozen = json.loads(settings.calibration_path.read_text(encoding="utf-8"))[algorithm]
        assert result["parameters"] == frozen
        assert result["analysis_time_seconds"] >= result["segmentation_time_seconds"] >= 0
        if algorithm == "Otsu-ExG":
            assert type(result["algorithm_metadata"]["computed_exg_threshold"]) is int
        if algorithm == "HSV":
            assert result["parameters"]["saturation_min"] == 0.1


@pytest.mark.parametrize("algorithm", ["RF-Color-Texture", "unknown", "exg", ""])
def test_unsupported_algorithm_is_explicit_error(tmp_path, algorithm):
    with TestClient(create_app(Settings(storage_root=tmp_path / "web"))) as client:
        response = client.post("/api/image/analyze", files={"file": ("x.png", photo_fixture(), "image/png")}, data={"algorithm": algorithm})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "UNSUPPORTED_ALGORITHM"
        assert "mask_url" not in response.json()


def test_duplicate_algorithm_fields_are_rejected(tmp_path):
    with TestClient(create_app(Settings(storage_root=tmp_path / "web"))) as client:
        response = client.post("/api/image/analyze", files=[
            ("file", ("x.png", photo_fixture(), "image/png")),
            ("algorithm", (None, "ExG")), ("algorithm", (None, "HSV")),
        ])
        assert response.status_code == 422


def test_failed_algorithm_does_not_replace_or_block_other_results(tmp_path, monkeypatch):
    import backend.app.image_service as service
    original = service.predict_visible_mask
    def fail_hsv(rgb, method, **kwargs):
        if method == "HSV":
            raise RuntimeError("测试注入的 HSV 执行失败")
        return original(rgb, method, **kwargs)
    monkeypatch.setattr(service, "predict_visible_mask", fail_hsv)
    settings = Settings(storage_root=tmp_path / "web")
    with TestClient(create_app(settings)) as client:
        results = {}
        for algorithm in SUPPORTED_ALGORITHMS:
            response = client.post("/api/image/analyze", files={"file": ("x.png", photo_fixture(), "image/png")}, data={"algorithm": algorithm})
            if algorithm == "HSV":
                assert response.status_code == 500
                assert "HSV" in response.json()["error"]["message"]
                assert "mask_url" not in response.json()
            else:
                assert response.status_code == 200
                results[algorithm] = response.json()
        assert len({r["task_id"] for r in results.values()}) == 3
        assert len({r["input_sha256"] for r in results.values()}) == 1
        failure = next((settings.storage_root / "failures").glob("*.json"))
        assert json.loads(failure.read_text(encoding="utf-8"))["algorithm"] == "HSV"
        assert client.get(results["ExG"]["mask_url"]).status_code == 200


def test_invalid_hsv_profile_only_disables_hsv(tmp_path):
    original = Settings()
    config = json.loads(original.parameters_path.read_text(encoding="utf-8"))
    config["algorithm_parameters"]["HSV"]["value_min"] = 0.99
    parameters = tmp_path / "invalid-hsv.json"
    parameters.write_text(json.dumps(config), encoding="utf-8")
    settings = Settings(storage_root=tmp_path / "web", parameters_path=parameters)
    with TestClient(create_app(settings)) as client:
        health = client.get("/api/health").json()
        assert health["status"] == "degraded"
        assert "HSV" not in health["available_algorithms"]
        assert "ExG" in health["available_algorithms"]
        assert client.post("/api/image/analyze", files={"file": ("x.png", photo_fixture(), "image/png")} ).status_code == 200
        failure = client.post("/api/image/analyze", files={"file": ("x.png", photo_fixture(), "image/png")}, data={"algorithm": "HSV"})
        assert failure.status_code == 503
        assert failure.json()["error"]["code"] == "ALGORITHM_UNAVAILABLE"
