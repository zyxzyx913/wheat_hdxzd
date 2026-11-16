"""Independent, dependency-free short-horizon growth trend engine.

This is an explainable screening engine, not a field-validated agronomic model.
It uses only supplied observations and, when available, real weather rows.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .agricultural_advice_service import build_agricultural_advice

VERSION = "independent-growth-v1.0-rule"
HORIZONS = (7, 15)


def _number(value: Any, default: float | None = None) -> float | None:
    try:
        return None if value is None or value == "" else float(value)
    except (TypeError, ValueError):
        return default


def _weather_risks(rows: list[dict[str, Any]], stage: str) -> list[str]:
    risks: list[str] = []
    max_temp = max((_number(row.get("temperature_2m_max")) for row in rows), default=None)
    min_temp = min((_number(row.get("temperature_2m_min")) for row in rows), default=None)
    rainfall = sum((_number(row.get("precipitation_sum"), 0) or 0) for row in rows)
    if max_temp is not None and max_temp >= 35:
        risks.append("高温风险筛查")
    if min_temp is not None and min_temp <= 0:
        risks.append("低温风险筛查")
    if rainfall < max(5.0, len(rows) * 0.7):
        risks.append("降水不足风险筛查")
    if rainfall > len(rows) * 12:
        risks.append("降水偏多风险筛查")
    rainy_days = sum(1 for row in rows if (_number(row.get("precipitation_sum"), 0) or 0) >= 2)
    if rainy_days >= 3:
        risks.append("连续降雨风险筛查")
    if any(key in stage for key in ("抽穗", "开花", "灌浆")) and max_temp is not None and max_temp >= 32:
        risks.append("当前阶段需重点关注高温胁迫")
    if any(key in stage for key in ("分蘖", "拔节", "孕穗")) and min_temp is not None and min_temp <= 3:
        risks.append("当前阶段需重点关注低温影响")
    return risks


def _baseline(score: float | None, level: str | None, confidence: float, stage: str) -> tuple[str, list[str]]:
    basis = ["使用当前图像表观长势作为基线，不将当前分数复制为未来分数。"]
    if level in ("较好", "较弱", "一般"):
        basis.append(f"当前长势等级为{level}，仅用于确定初始风险关注度。")
    if score is None:
        return "暂无法判断", basis + ["缺少当前综合评分，无法建立可靠的短期基线。"]
    if confidence and confidence < 0.5:
        basis.append("生育期置信度低于0.5，阶段相关判断需人工复核。")
    if score >= 80:
        return "基本稳定", basis
    if score < 60:
        return "暂无法判断", basis + ["当前表观长势偏弱，但不足以推断未来必然变差。"]
    return "暂无法判断", basis + ["当前状态处于中间区间，缺少天气依据时不作方向性结论。"]


def _horizon(days: int, score: float | None, level: str | None, stage: str, confidence: float, rows: list[dict[str, Any]], weather_available: bool) -> dict[str, Any]:
    expected = days
    used = min(len(rows), days)
    completeness = round(used / expected, 3) if expected else 0
    risks = _weather_risks(rows[:days], stage) if rows else []
    trend, basis = _baseline(score, level, confidence, stage)
    if weather_available and rows:
        if risks and any("高温" in risk or "低温" in risk or "不足" in risk for risk in risks):
            trend = "可能变差" if score is not None and score < 70 else "风险较高"
            basis.append("实际天气筛查触发了温度或水分风险，未将其解释为确定性产量或长势结果。")
        elif score is not None and score >= 70 and not risks:
            trend = "趋于改善"
            basis.append("当前表观状态具备一定基础，且已获取的天气行未触发登记风险。")
        else:
            trend = "基本稳定"
        if used < expected:
            basis.append(f"仅获得{used}/{expected}天真实天气，未补造缺失日期。")
    else:
        basis.append("天气未接入，采用无天气基线推断，可信度降低。")
    if confidence and confidence < 0.5:
        basis.append("生育期识别置信度较低，建议人工确认后再使用阶段相关建议。")
    advice = build_agricultural_advice(vigor_level=level, coverage=None, greenness=None, uniformity_cv=None, stage=stage or None, stage_confidence=confidence or None, weather_risks=risks, location=None)
    return {
        "horizon_days": days,
        "trend": trend,
        "factors": basis,
        "weather_risks": risks,
        "management": advice["seven_day_focus"] if days == 7 else advice["fifteen_day_focus"],
        "data_completeness": {"weather_days_used": used, "weather_days_expected": expected, "ratio": completeness, "status": "complete" if used >= expected else ("partial" if used else "missing")},
        "confidence": "较低" if not weather_available or confidence < 0.5 or completeness < 1 else "中等",
        "basis": ["独立规则引擎 v1.0", "当前图像表观指标", "实际天气行（如提供）" if weather_available and rows else "无天气基线"],
    }



def _estimate_metrics(days: int, score: float | None, coverage: float | None, greenness: float | None, risks: list[str], weather_available: bool) -> dict[str, Any]:
    """Produce transparent exploratory estimates; these are not field measurements."""
    base_score = 65.0 if score is None else max(0.0, min(100.0, score))
    adjustment = 1.5 if weather_available and not risks else (-4.0 if risks else -1.0)
    adjustment *= 1.0 if days == 7 else 0.7
    future_score = max(0.0, min(100.0, base_score + adjustment))
    base_coverage = coverage if coverage is not None else max(0.1, min(0.95, base_score / 100.0))
    if base_coverage > 1: base_coverage /= 100.0
    future_coverage = max(0.0, min(1.0, base_coverage + adjustment * 0.002))
    base_green = greenness if greenness is not None else max(0.15, min(0.9, 0.35 + base_score / 250.0))
    if base_green > 1: base_green /= 100.0
    future_green = max(0.0, min(1.0, base_green + adjustment * 0.001))
    lai = max(0.1, future_coverage * 4.5)
    biomass_kg_ha = lai * 1200.0
    yield_kg_mu = biomass_kg_ha * 0.35 / 15.0
    spread = 8.0 if not weather_available else (5.0 if not risks else 12.0)
    return {
        "status": "exploratory_estimate",
        "vigor_score": {"value": round(future_score, 1), "range": [round(max(0, future_score-spread), 1), round(min(100, future_score+spread), 1)]},
        "vegetation_coverage": {"value": round(future_coverage, 4), "range": [round(max(0, future_coverage-0.05), 4), round(min(1, future_coverage+0.05), 4)]},
        "greenness": {"value": round(future_green, 4), "range": [round(max(0, future_green-0.04), 4), round(min(1, future_green+0.04), 4)]},
        "lai": {"value": round(lai, 3), "range": [round(max(0, lai-0.35), 3), round(lai+0.35, 3)]},
        "biomass_kg_per_ha": {"value": round(biomass_kg_ha, 1), "range": [round(max(0, biomass_kg_ha*(1-spread/100)), 1), round(biomass_kg_ha*(1+spread/100), 1)]},
        "yield_kg_per_mu": {"value": round(yield_kg_mu, 1), "range": [round(max(0, yield_kg_mu*(1-spread/100)), 1), round(yield_kg_mu*(1+spread/100), 1)]},
        "assumptions": ["覆盖率缺失时以当前评分映射为初始代理", "LAI按覆盖率×4.5估算", "生物量按LAI×1200 kg/ha估算", "产量按生物量×0.35÷15估算", "区间为规则不确定性范围，未经田间验证"],
    }

def predict_independent_growth(payload: dict[str, Any]) -> dict[str, Any]:
    stage = str(payload.get("growth_stage") or "")
    level = str(payload.get("vigor_level") or "") or None
    score = _number(payload.get("vigor_score"))
    if level is None and score is not None:
        level = "较好" if score >= 80 else ("一般" if score >= 60 else "较弱")
    confidence = _number(payload.get("stage_confidence"), 0.0) or 0.0
    if not 0 <= confidence <= 1:
        raise ValueError("生育期置信度必须在0到1之间")
    capture_date = payload.get("capture_date")
    if capture_date:
        date.fromisoformat(str(capture_date))
    rows = payload.get("weather_rows") or []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("weather_rows 必须是对象数组")
    weather_available = payload.get("weather_status") == "succeeded" and bool(rows)
    horizons = {str(days): _horizon(days, score, level, stage, confidence, rows, weather_available) for days in HORIZONS}
    coverage = _number(payload.get("vegetation_coverage"))
    greenness = _number(payload.get("greenness"))
    for days in HORIZONS:
        horizons[str(days)]["estimates"] = _estimate_metrics(days, score, coverage, greenness, horizons[str(days)]["weather_risks"], weather_available)
    all_risks = sorted({risk for item in horizons.values() for risk in item["weather_risks"]})
    advice = build_agricultural_advice(vigor_level=level, coverage=_number(payload.get("vegetation_coverage")), greenness=_number(payload.get("greenness")), uniformity_cv=_number(payload.get("uniformity_cv")), stage=stage or None, stage_confidence=confidence, weather_risks=all_risks, location=payload.get("location"))
    advice.pop("thirty_day_reference", None)
    return {
        "status": "succeeded",
        "engine": "independent",
        "version": VERSION,
        "current_summary": {"vigor_score": score, "vigor_level": level, "growth_stage": stage or None, "stage_confidence": confidence, "capture_date": capture_date, "location": payload.get("location")},
        "horizons": horizons,
        "weather": {"status": "succeeded" if weather_available else "unavailable", "rows_used": len(rows), "source": payload.get("weather_source"), "location": payload.get("weather_location"), "limitation": "仅使用实际提供的天气行"},
        "agricultural_advice": advice,
        "limitations": ["规则型短期趋势推断，不是经过独立田间验证的预测模型。", "未来指标为探索性规则估算，不是实测值或田间验证预测。", "生育期低置信度或天气覆盖不足时应人工复核。"],
    }
