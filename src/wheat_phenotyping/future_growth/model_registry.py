"""未来预测模型登记表；只有验证通过的模型才能被标记为 enabled。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastModelSpec:
    name: str
    version: str
    horizons: tuple[int, ...]
    enabled: bool = False
    validation_report: str | None = None
    training_source: str | None = None


UNVERIFIED_SPEC = ForecastModelSpec(
    name="future-growth-pending-validation",
    version="unverified",
    horizons=(),
    enabled=False,
    validation_report=None,
    training_source=None,
)
