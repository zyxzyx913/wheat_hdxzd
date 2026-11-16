"""验证真正的 API 调用、掩膜一致性、文件保存和失败边界。

程序生成的小图仅是单元测试夹具，不代表真实小麦实验或分割精度。
"""

from dataclasses import replace
from io import BytesIO
import json

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.main import create_app
from wheat_phenotyping.app.inference import predict_visible_mask
from wheat_phenotyping.data import load_rgb_image


def image_bytes(fmt="PNG", color=(20, 180, 30), size=(3, 2)):
    """构建明确标识的测试夹具，不写入科研数据集。"""
    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format=fmt)
    return stream.getvalue()


@pytest.fixture
def setup_api(tmp_path):
    settings = Settings(storage_root=tmp_path / "web")
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, settings, app


def test_health_reports_real_configuration(setup_api):
    client, settings, _ = setup_api
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["algorithm"] == "ExG"
    assert response.json()["limits"]["max_file_bytes"] == settings.max_file_bytes


def test_missing_configuration_is_unavailable(tmp_path):
    settings = Settings(storage_root=tmp_path / "web", parameters_path=tmp_path / "missing.json")
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").status_code == 503
        response = client.post("/api/image/analyze", files={"file": ("x.png", image_bytes(), "image/png")})
        assert response.status_code == 503
        assert "original_url" not in response.json()


@pytest.mark.parametrize("fmt,suffix,mime", [("PNG", "png", "image/png"), ("JPEG", "jpg", "image/jpeg"), ("JPEG", "jpeg", "image/jpeg")])
def test_formats_return_real_masks_and_accessible_images(setup_api, fmt, suffix, mime):
    client, settings, _ = setup_api
    source = Image.new("RGB", (3, 2), (110, 80, 45))
    source.putpixel((1, 0), (20, 180, 30))
    data = BytesIO()
    source.save(data, format=fmt)
    raw = data.getvalue()
    response = client.post("/api/image/analyze", files={"file": (f"wheat.{suffix}", raw, mime)})
    assert response.status_code == 200, response.text
    result = response.json()
    saved = settings.storage_root / "analyses" / result["task_id"]
    assert (saved / f"uploaded_original.{ 'png' if fmt == 'PNG' else 'jpg'}").read_bytes() == raw
    record = json.loads((saved / "record.json").read_text(encoding="utf-8"))
    assert record["status"] == "succeeded"
    assert record["data_source"] == "user_upload"
    assert record["dataset_split"] == "not_assigned"
    for name in ("original_url", "mask_url", "overlay_url"):
        image_response = client.get(result[name])
        assert image_response.status_code == 200
        assert image_response.headers["content-type"] == "image/png"
        with Image.open(BytesIO(image_response.content)) as image:
            image.load()
            assert image.size == (3, 2)
    with Image.open(saved / "mask.png") as mask_image:
        pixels = mask_image.tobytes()
    rgb = load_rgb_image(saved / "original.png")
    expected, _ = predict_visible_mask(rgb, "ExG", parameters=result["parameters"])
    assert pixels == expected.pixels
    assert set(pixels) <= {0, 255}
    assert result["vegetation_pixel_count"] == pixels.count(255)
    assert result["total_valid_pixels"] == 6
    assert result["vegetation_ratio"] == pixels.count(255) / 6
    assert result["analysis_time_seconds"] >= result["segmentation_time_seconds"] >= 0
    assert result["algorithm"] == "ExG"
    assert not {"iou", "f1_score", "accuracy", "growth_grade"} & result.keys()


@pytest.mark.parametrize("filename,data,mime,status,code", [
    ("x.png", b"", "image/png", 400, "EMPTY_IMAGE"),
    ("x.png", b"not a photo", "image/png", 400, "INVALID_IMAGE"),
    ("x.exe", b"not a photo", "image/png", 415, "UNSUPPORTED_FORMAT"),
    ("x.jpg", image_bytes("PNG"), "image/jpeg", 415, "FORMAT_MISMATCH"),
    ("x.png", image_bytes("GIF"), "image/png", 415, "FORMAT_MISMATCH"),
    ("x.jpg", image_bytes("JPEG")[:70], "image/jpeg", 400, "INVALID_IMAGE"),
    ("x.png", image_bytes("PNG"), "text/plain", 415, "UNSUPPORTED_FORMAT"),
])
def test_invalid_inputs_never_return_success(setup_api, filename, data, mime, status, code):
    client, settings, _ = setup_api
    response = client.post("/api/image/analyze", files={"file": (filename, data, mime)})
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert "mask_url" not in response.json()
    assert not list((settings.storage_root / "analyses").iterdir())


def test_missing_file_is_clear_error(setup_api):
    response = setup_api[0].post("/api/image/analyze")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("change", [{"max_file_bytes": 16}, {"max_pixels": 1}, {"max_dimension": 1}])
def test_file_and_decoded_dimensions_are_bounded(tmp_path, change):
    settings = replace(Settings(storage_root=tmp_path / "web"), **change)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/image/analyze", files={"file": ("x.png", image_bytes(), "image/png")})
        assert response.status_code == 413


def test_body_limit_applies_without_content_length(tmp_path):
    settings = Settings(storage_root=tmp_path / "web", max_file_bytes=16)
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/image/analyze", content=iter([b"x" * 40_000, b"x" * 40_000]), headers={"Content-Type": "application/octet-stream"})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_empty_foreground_is_valid_zero_not_failure(setup_api):
    response = setup_api[0].post("/api/image/analyze", files={"file": ("dark.png", image_bytes(color=(0, 0, 0)), "image/png")})
    assert response.status_code == 200
    assert response.json()["vegetation_ratio"] == 0
    assert response.json()["vegetation_pixel_count"] == 0


def test_exif_orientation_and_transparency_are_explicit(setup_api):
    client, settings, _ = setup_api
    exif = Image.Exif()
    exif[274] = 6
    stream = BytesIO()
    Image.new("RGB", (2, 3), (20, 180, 30)).save(stream, format="JPEG", exif=exif)
    result = client.post("/api/image/analyze", files={"file": ("rotated.jpg", stream.getvalue(), "image/jpeg")}).json()
    assert (result["width"], result["height"]) == (3, 2)
    stream = BytesIO()
    Image.new("RGBA", (2, 2), (0, 255, 0, 0)).save(stream, format="PNG")
    result = client.post("/api/image/analyze", files={"file": ("transparent.png", stream.getvalue(), "image/png")}).json()
    assert result["vegetation_ratio"] == 0
    directory = settings.storage_root / "analyses" / result["task_id"]
    with Image.open(directory / "original.png") as original:
        assert original.getpixel((0, 0)) == (255, 255, 255)
    assert json.loads((directory / "record.json").read_text(encoding="utf-8"))["normalization"]["alpha_policy"] == "white_composite"


def test_animated_png_is_rejected(setup_api):
    stream = BytesIO()
    Image.new("RGB", (2, 2), "green").save(stream, format="PNG", save_all=True, append_images=[Image.new("RGB", (2, 2), "red")], duration=100)
    response = setup_api[0].post("/api/image/analyze", files={"file": ("animation.png", stream.getvalue(), "image/png")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "ANIMATED_IMAGE"


def test_extra_parameters_and_multiple_files_are_rejected(setup_api):
    client = setup_api[0]
    response = client.post("/api/image/analyze", files={"file": ("x.png", image_bytes(), "image/png")}, data={"exg_threshold": -510})
    assert response.status_code == 422
    response = client.post("/api/image/analyze", files=[("file", ("x.png", image_bytes(), "image/png")), ("file", ("y.png", image_bytes(), "image/png"))])
    assert response.status_code == 422


def test_same_names_have_unique_tasks_and_private_records(setup_api):
    client, settings, _ = setup_api
    ids = [client.post("/api/image/analyze", files={"file": ("../../wheat.png", image_bytes(), "image/png")}).json()["task_id"] for _ in range(2)]
    assert ids[0] != ids[1]
    assert all((settings.storage_root / "analyses" / task / "record.json").is_file() for task in ids)
    assert client.get(f"/media/{ids[0]}/record.json").status_code == 422
    assert client.get("/media/" + "0" * 32 + "/mask.png").status_code == 404


def test_busy_service_is_not_success(setup_api):
    client, _, app = setup_api
    app.state.analysis_gate.acquire()
    try:
        response = client.post("/api/image/analyze", files={"file": ("x.png", image_bytes(), "image/png")})
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SERVER_BUSY"
    finally:
        app.state.analysis_gate.release()


@pytest.mark.parametrize("error,expected", [(RuntimeError("algorithm failed"), 500), (OSError("disk full"), 503)])
def test_processing_failure_never_publishes_partial_results(setup_api, monkeypatch, error, expected):
    import backend.app.image_service as service
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(service, "predict_visible_mask", fail)
    client, settings, _ = setup_api
    response = client.post("/api/image/analyze", files={"file": ("x.png", image_bytes(), "image/png")})
    assert response.status_code == expected
    assert "original_url" not in response.json()
    assert not list((settings.storage_root / "analyses").iterdir())
    assert len(list((settings.storage_root / "failures").glob("*.json"))) == 1
