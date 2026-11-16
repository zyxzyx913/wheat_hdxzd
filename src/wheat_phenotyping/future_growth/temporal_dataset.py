"""按地块和日期构造未来预测样本，并阻止跨地块泄漏。"""
from __future__ import annotations

from datetime import date, timedelta
from collections.abc import Iterable, Mapping

from .schemas import ForecastSample


def build_temporal_samples(records: Iterable[Mapping[str, object]], horizons=(7, 15, 30)) -> list[ForecastSample]:
    """将同一地块的观测按日期匹配未来目标，允许日期误差由调用方预先整理。"""
    rows = [row for row in records if row.get("plot_id") and row.get("capture_date")]
    grouped: dict[tuple[str, int], list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault((str(row["plot_id"]), int(row["year"])), []).append(row)
    samples: list[ForecastSample] = []
    for (plot_id, year), group in grouped.items():
        ordered = sorted(group, key=lambda row: row["capture_date"])
        for current in ordered:
            targets: dict[int, dict[str, float | str | None]] = {}
            current_date = current["capture_date"]
            for horizon in horizons:
                candidates = [row for row in ordered if row["capture_date"] >= current_date + timedelta(days=horizon)]
                if candidates:
                    future = candidates[0]
                    targets[horizon] = dict(future.get("target_values") or {})
            samples.append(ForecastSample(plot_id, year, current_date, dict(current.get("features") or {}), targets, str(current.get("source", "unknown"))))
    return samples


def validate_group_isolation(train: Iterable[Mapping[str, object]], test: Iterable[Mapping[str, object]]) -> None:
    """确保同一地块/年份不会同时出现在训练和测试集合。"""
    train_groups = {(str(row.get("plot_id")), int(row.get("year"))) for row in train if row.get("plot_id") is not None and row.get("year") is not None}
    test_groups = {(str(row.get("plot_id")), int(row.get("year"))) for row in test if row.get("plot_id") is not None and row.get("year") is not None}
    overlap = train_groups & test_groups
    if overlap:
        raise ValueError(f"训练集与测试集存在地块/年份重叠: {sorted(overlap)[:5]}")
