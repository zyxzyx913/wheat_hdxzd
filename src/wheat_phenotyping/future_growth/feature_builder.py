"""把当前分析记录整理成可用于时间序列建模的数值特征。"""
from __future__ import annotations

from collections.abc import Mapping
import math


FEATURE_VERSION = "future-growth-features-v1"


def build_feature_vector(record: Mapping[str, object]) -> dict[str, float]:
    """只读取当前记录中的已计算指标，不从未来字段补值。"""
    growth = record.get("growth_analysis") or {}
    metrics = growth.get("metrics") if isinstance(growth, Mapping) else {}
    metrics = metrics if isinstance(metrics, Mapping) else {}
    coverage = metrics.get("vegetation_coverage") or {}
    green = metrics.get("green_degree") or {}
    uniformity = metrics.get("distribution_uniformity") or {}
    quality = metrics.get("image_quality") or {}
    values = {
        "vegetation_coverage": coverage.get("fraction"),
        "greenness": green.get("mean_green_channel_ratio"),
        "uniformity_cv": uniformity.get("coefficient_of_variation"),
        "mean_brightness": quality.get("mean_brightness_ratio"),
        "vigor_score_rule": (growth.get("vigor_assessment") or {}).get("vigor_score") if isinstance(growth.get("vigor_assessment"), Mapping) else None,
    }
    output: dict[str, float] = {}
    for name, value in values.items():
        if value is None:
            continue
        number = float(value)
        if math.isfinite(number):
            output[name] = number
    return output
