"""预测实验的基础指标计算，不负责生成或修改实验标签。"""
from __future__ import annotations

import math
from collections.abc import Iterable


def regression_metrics(actual: Iterable[float], predicted: Iterable[float]) -> dict[str, float]:
    y = [float(value) for value in actual]
    p = [float(value) for value in predicted]
    if len(y) != len(p) or not y:
        raise ValueError("真实值和预测值必须非空且长度一致")
    errors = [a - b for a, b in zip(y, p)]
    mae = sum(abs(value) for value in errors) / len(errors)
    rmse = math.sqrt(sum(value * value for value in errors) / len(errors))
    mean = sum(y) / len(y)
    total = sum((value - mean) ** 2 for value in y)
    r2 = 1.0 - sum(value * value for value in errors) / total if total else float("nan")
    return {"mae": mae, "rmse": rmse, "r2": r2}
