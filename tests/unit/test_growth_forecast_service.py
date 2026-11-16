"""未来预测免训练接入层测试；不允许产生伪造预测值。"""

from io import BytesIO

from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.errors import AnalysisError
from backend.app.growth_forecast_service import forecast_model_status, predict_future_growth


def png_bytes() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (8, 8), (20, 180, 30)).save(stream, format="PNG")
    return stream.getvalue()


def test_forecast_status_is_explicitly_unverified(tmp_path):
    status = forecast_model_status()
    assert status["enabled"] is False
    assert status["status"] == "unverified"
    assert status["available_horizons"] == []


def test_forecast_never_generates_placeholder_values(tmp_path):
    result = predict_future_growth(
        png_bytes(), "wheat.png", Settings(storage_root=tmp_path / "web"),
        current_stage="营养生长中期", capture_date="2026-11-14",
    )
    assert result["status"] == "unavailable"
    assert result["reliability"] == "unavailable"
    assert all(item["prediction"] is None for item in result["horizons"].values())
    assert all(item["confidence"] is None for item in result["horizons"].values())
    assert result["input"]["initialization_mode"] == "current_stage_without_sowing_date"
    assert result["prediction_basis"]


def test_forecast_accepts_optional_location_without_sowing_date(tmp_path):
    result = predict_future_growth(
        png_bytes(), "wheat.png", Settings(storage_root=tmp_path / "web"),
        current_stage="拔节期", capture_date="2026-11-14", location="河南周口",
    )
    assert result["input"]["location"] == "河南周口"
    assert result["input"]["initialization_mode"] == "current_stage_without_sowing_date"


@pytest.mark.parametrize("capture_date", ["2026/11/14", "not-a-date"])
def test_forecast_rejects_invalid_capture_date(tmp_path, capture_date):
    with pytest.raises(AnalysisError) as error:
        predict_future_growth(png_bytes(), "wheat.png", Settings(storage_root=tmp_path / "web"), capture_date=capture_date)
    assert error.value.code == "INVALID_CAPTURE_DATE"


def test_forecast_rejects_invalid_location(tmp_path):
    with pytest.raises(AnalysisError) as error:
        predict_future_growth(png_bytes(), "wheat.png", Settings(storage_root=tmp_path / "web"), latitude=100)
    assert error.value.code == "INVALID_LOCATION"


def test_forecast_rejects_malformed_history_ids(tmp_path):
    with pytest.raises(AnalysisError) as error:
        predict_future_growth(png_bytes(), "wheat.png", Settings(storage_root=tmp_path / "web"), history_analysis_ids="not-json")
    assert error.value.code == "INVALID_HISTORY_IDS"
