"""未来预测模块的可追溯数据结构；不包含任何虚构预测值。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ForecastSample:
    """一个地块在一个观测日期上的输入与未来目标。"""

    plot_id: str
    year: int
    capture_date: date
    features: dict[str, float]
    targets: dict[int, dict[str, float | str | None]] = field(default_factory=dict)
    source: str = "unknown"


@dataclass(frozen=True)
class ForecastOutput:
    """统一预测输出；不可用期限必须使用 None 而不是占位数字。"""

    status: str
    horizon_days: int
    prediction: dict[str, float | str | None] | None
    model_version: str | None
    reliability: str
    basis: list[str] = field(default_factory=list)
    uncertainty: dict[str, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
