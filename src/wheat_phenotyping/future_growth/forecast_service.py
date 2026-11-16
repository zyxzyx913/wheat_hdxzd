"""机理模型预测编排层；没有真实参数和天气时保持不可用。"""
from __future__ import annotations

from .model_registry import UNVERIFIED_SPEC


def forecast_status() -> dict[str, object]:
    return {"enabled": False, "status": "unverified", "model": "PCSE/WOFOST", "model_version": UNVERIFIED_SPEC.version, "available_horizons": [], "message": "PCSE、作物/土壤/站点参数和真实天气输入尚未完成核验。"}
