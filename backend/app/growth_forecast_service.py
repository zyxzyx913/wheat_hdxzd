"""未来长势预测的免训练接入层。

本模块只允许调用已存在的、经过来源核验的预训练模型。当前项目尚未下载并
核验 GSP-AI/WGSP 推理包，因此默认返回明确的“尚未验证”状态，不生成曲线、
随机数或当前分数的外推值。
"""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import importlib.util
from typing import Any

from .config import PROJECT_ROOT, Settings
from .errors import AnalysisError
from .image_service import validate_and_decode
from .weather_scenario_service import fetch_daily_weather, screen_weather_risks
from .agricultural_advice_service import build_agricultural_advice


FORECAST_MODEL_ROOT = PROJECT_ROOT / "models" / "pretrained" / "gsp_ai"
FORECAST_MODEL_VERSION = "gsp-ai-wgsp-adapter-unverified"
OFFICIAL_SOURCE = "https://github.com/The-Zhou-Lab/GSP-AI/releases"


def _model_package_state() -> dict[str, object]:
    """只检查本地模型包，不下载或猜测模型文件。"""
    package_candidates = sorted(FORECAST_MODEL_ROOT.glob("GSP-AI_model*.zip"))
    extracted_markers = sorted(FORECAST_MODEL_ROOT.glob("**/saved_model.pb")) + sorted(FORECAST_MODEL_ROOT.glob("**/*model*.h5")) + sorted(FORECAST_MODEL_ROOT.glob("**/*model*.keras"))
    dependencies = {
        name: bool(importlib.util.find_spec(name))
        for name in ("tensorflow", "pandas", "skimage", "exifread", "openpyxl")
    }
    return {
        "installed": bool(extracted_markers),
        "official_package_present": bool(package_candidates),
        "dependencies": dependencies,
        "package_files": [str(path.relative_to(PROJECT_ROOT)) for path in package_candidates],
        "extracted_model_files": [str(path.relative_to(PROJECT_ROOT)) for path in extracted_markers],
    }


def forecast_model_status() -> dict[str, object]:
    """返回前端可展示的真实模型状态。"""
    local = _model_package_state()
    enabled = bool(local["installed"] and all(local["dependencies"].values()))
    reason = "官方模型和运行依赖已检测到，尚未完成本项目输入/输出复现。" if enabled else (
        "官方权重压缩包已存在，但独立运行依赖未满足：" + ", ".join(name for name, ok in local["dependencies"].items() if not ok)
        if local["official_package_present"] else "当前没有已下载的官方模型包。"
    )
    return {
        "enabled": False,
        "status": "unverified",
        "model_name": "GSP-AI/WGSP（官方模型适配预留）",
        "model_version": FORECAST_MODEL_VERSION,
        "local_model": local,
        "official_source": OFFICIAL_SOURCE,
        "supported_horizons": [7, 15],
        "available_horizons": [],
        "reason": reason,
        "limitations": [
            "GSP-AI/WGSP 的公开模型主要面向生育期和开花日期，不等同于未来7/15天连续长势指标预测。",
            "单张图片不足以构成同一地块时间序列；没有 plot_id 和生长季信息时不拼接历史记录。",
            "当前接口不会使用线性外推、随机数或当前长势分数冒充未来预测。",
        ],
    }


def _parse_history_ids(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise AnalysisError(400, "INVALID_HISTORY_IDS", "历史分析编号必须是 JSON 数组。") from error
    if not isinstance(parsed, list) or any(not isinstance(item, str) or len(item) > 64 for item in parsed):
        raise AnalysisError(400, "INVALID_HISTORY_IDS", "历史分析编号格式无效。")
    return parsed[:30]


def predict_future_growth(
    data: bytes,
    filename: str,
    settings: Settings,
    current_stage: str | None = None,
    capture_date: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    history_analysis_ids: str | None = None,
    location: str | None = None,
) -> dict[str, object]:
    """校验输入并返回未启用状态；模型可用前绝不生成虚假预测。"""
    image, _ = validate_and_decode(data, filename, settings)
    if capture_date:
        try:
            date.fromisoformat(capture_date)
        except ValueError as error:
            raise AnalysisError(400, "INVALID_CAPTURE_DATE", "拍摄日期必须使用 YYYY-MM-DD 格式。") from error
    if latitude is not None and not -90 <= latitude <= 90:
        raise AnalysisError(400, "INVALID_LOCATION", "纬度范围必须为 -90 到 90。")
    if longitude is not None and not -180 <= longitude <= 180:
        raise AnalysisError(400, "INVALID_LOCATION", "经度范围必须为 -180 到 180。")
    history_ids = _parse_history_ids(history_analysis_ids)
    if location is not None and len(location.strip()) > 80:
        raise AnalysisError(400, "INVALID_LOCATION", "种植地点文字不能超过 80 个字符。")
    status = forecast_model_status()
    weather = {"status": "not_requested", "source": None, "variables": []}
    scenario_analysis = {str(days): {"status": "unavailable", "reason": "需要有效经纬度和可访问的天气预报"} for days in (7, 15)}
    if latitude is not None and longitude is not None and capture_date:
        try:
            weather_payload = fetch_daily_weather(latitude, longitude, date.fromisoformat(capture_date), days=15)
            weather = {"status": weather_payload["status"], "weather_type": weather_payload["weather_type"], "source": weather_payload["source"], "fetched_at_utc": weather_payload["fetched_at_utc"], "latitude": latitude, "longitude": longitude, "timezone": weather_payload["timezone"], "forecast_days_returned": weather_payload["forecast_days_returned"], "rows": weather_payload["rows"], "variables": ["temperature_2m_mean", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "sunshine_duration", "shortwave_radiation_sum"]}
            scenario_analysis = {str(days): ({"status": "screening_only", "normal": screen_weather_risks(weather_payload, days), "dry": {"status": "scenario_definition", "assumption": "降水量相对正常预报减少；不代表真实天气", "description": "仅输出风险筛查，不输出定量作物指标"}, "wet": {"status": "scenario_definition", "assumption": "降水量相对正常预报增加；不代表真实天气", "description": "仅输出风险筛查，不输出定量作物指标"}} if len(weather_payload["rows"]) >= days else {"status": "unavailable", "reason": f"当前真实天气预报仅返回 {len(weather_payload['rows'])} 天，未延长为 {days} 天"}) for days in (7, 15)}
        except Exception as error:  # noqa: BLE001
            weather = {"status": "unavailable", "source": "https://open-meteo.com/en/docs", "variables": [], "error": str(error)}
    risk_flags = []
    for item in scenario_analysis.values():
        normal = item.get("normal") if isinstance(item, dict) else None
        if isinstance(normal, dict): risk_flags.extend(normal.get("flags") or [])
    advice = build_agricultural_advice(vigor_level=None, coverage=None, greenness=None, uniformity_cv=None, stage=current_stage, stage_confidence=None, weather_risks=sorted(set(risk_flags)), location=location)
    horizons = {
        str(days): {
            "horizon_days": days,
            "status": "unavailable",
            "prediction": None,
            "confidence": None,
            "uncertainty": None,
        }
        for days in (7, 15)
    }
    return {
        "status": "unavailable",
        "analysis_scope": "future_growth_forecast",
        "input": {
            "width": image.width,
            "height": image.height,
            "filename": filename,
            "current_stage": current_stage,
            "capture_date": capture_date,
            "latitude_provided": latitude is not None,
            "longitude_provided": longitude is not None,
            "location": location.strip() if location else None,
            "initialization_mode": "current_stage_without_sowing_date" if current_stage else "missing_current_stage",
            "history_analysis_ids": history_ids,
        },
        "horizons": horizons,
        "current_stage": current_stage,
        "next_stage": None,
        "predicted_flowering_date": None,
        "days_to_flowering": None,
        "model_name": status["model_name"],
        "model_version": status["model_version"],
        "prediction_basis": ["当前生育期作为初始化参考；未要求用户填写播种日期。"] if current_stage else [],
        "weather": weather,
        "scenario_analysis": scenario_analysis,
        "agricultural_advice": advice,
        "data_source": [status["official_source"]],
        "reliability": "unavailable",
        "message": "预测模型尚未验证，当前不生成未来7天或15天预测值。",
        "limitations": status["limitations"] + ["天气筛查仅在提供经纬度和拍摄日期且天气服务可访问时运行；风险阈值未完成中国小麦田间校准。"],
    }
