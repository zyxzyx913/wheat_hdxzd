"""WOFOST 接口边界测试；没有运行真实作物模拟。"""
import pytest

from wheat_phenotyping.future_growth.crop_parameters import EUROPEAN_WINTER_WHEAT_REFERENCE, require_verified_crop_parameters
from wheat_phenotyping.future_growth.initial_state import build_initial_state
from wheat_phenotyping.future_growth.scenario import SCENARIOS
from wheat_phenotyping.future_growth.weather_service import validate_weather_rows


def test_unverified_crop_parameters_are_rejected():
    with pytest.raises(RuntimeError, match="未通过本地验证"):
        require_verified_crop_parameters(EUROPEAN_WINTER_WHEAT_REFERENCE)


def test_rgb_metrics_are_not_lai():
    state = build_initial_state(image_metrics={"vegetation_coverage": 0.5}, growth_stage=None)
    assert state["lai"] is None
    assert state["mapping_status"] == "unavailable"


def test_weather_fields_are_required():
    with pytest.raises(ValueError, match="缺少字段"):
        validate_weather_rows([{"date": "2026-01-01", "tavg_c": 2}])


def test_scenarios_are_explicit():
    assert {item.name for item in SCENARIOS} == {"normal", "dry", "wet", "warm"}
