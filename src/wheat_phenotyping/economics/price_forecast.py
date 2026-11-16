"""全国小麦周均收购价的透明基线预测工具，不内置虚构历史价格。"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class PricePoint:
    """单条官方/研究者整理的全国价格观测。"""

    date: date
    price_yuan_per_ton: float
    source: str


@dataclass(frozen=True)
class ForecastPoint:
    """一个未来周的朴素基线预测值。"""

    target_date: date
    forecast_yuan_per_ton: float
    model: str
    data_cutoff: date
    source: str


def load_price_csv(path: str | Path) -> list[PricePoint]:
    """读取 date,price_yuan_per_ton,source 格式，校验序列并按日期排序。"""
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"date", "price_yuan_per_ton", "source"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("价格 CSV 必须含 date,price_yuan_per_ton,source 三列")
        rows: list[PricePoint] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                observed = date.fromisoformat(row["date"].strip())
                value = float(row["price_yuan_per_ton"])
                provenance = row["source"].strip()
            except (ValueError, AttributeError, TypeError) as exc:
                raise ValueError(f"第 {row_number} 行日期或价格无效") from exc
            if not math.isfinite(value) or value <= 0 or not provenance:
                raise ValueError(f"第 {row_number} 行价格须为正数且来源不能为空")
            rows.append(PricePoint(observed, value, provenance))
    if len(rows) < 10:
        raise ValueError("预测并进行滚动回测至少需要 10 个真实连续周观测；当前数据不足")
    rows.sort(key=lambda point: point.date)
    if len({point.date for point in rows}) != len(rows):
        raise ValueError("价格序列存在重复日期")
    gaps = [(right.date - left.date).days for left, right in zip(rows, rows[1:])]
    if any(gap != 7 for gap in gaps):
        raise ValueError("周度价格日期必须严格每隔 7 天；请先核实缺周，不要自动补造")
    return rows


def forecast_naive(points: list[PricePoint], horizon_weeks: int = 4) -> list[ForecastPoint]:
    """生成末值保持与最近四周均值两种基线，以供透明比较。"""
    if len(points) < 4:
        raise ValueError("至少需要 4 个连续周观测")
    if not 1 <= horizon_weeks <= 4:
        raise ValueError("预测期限只支持 1 到 4 周")
    ordered = sorted(points, key=lambda point: point.date)
    if any(not math.isfinite(point.price_yuan_per_ton) or point.price_yuan_per_ton <= 0 or not point.source for point in ordered):
        raise ValueError("价格观测必须为有限正数且包含数据来源")
    if len({point.date for point in ordered}) != len(ordered):
        raise ValueError("价格序列存在重复日期")
    for left, right in zip(ordered, ordered[1:]):
        if (right.date - left.date).days != 7:
            raise ValueError("价格序列必须严格按周连续")
    last = ordered[-1]
    rolling_mean = sum(point.price_yuan_per_ton for point in ordered[-4:]) / 4
    provenance = "; ".join(sorted({point.source for point in ordered}))
    forecasts: list[ForecastPoint] = []
    for week in range(1, horizon_weeks + 1):
        target = last.date + timedelta(days=7 * week)
        forecasts.append(ForecastPoint(target, last.price_yuan_per_ton, "naive_last_value", last.date, provenance))
        forecasts.append(ForecastPoint(target, rolling_mean, "mean_last_4_weeks", last.date, provenance))
    return forecasts


def forecast_as_dicts(points: list[ForecastPoint]) -> list[dict[str, object]]:
    """将预测 dataclass 转换为便于 JSON/CSV 保存的字典。"""
    return [{**asdict(point), "target_date": point.target_date.isoformat(), "data_cutoff": point.data_cutoff.isoformat()} for point in points]


def rolling_origin_backtest(points: list[PricePoint], minimum_history: int = 8) -> tuple[list[dict[str, object]], dict[str, object]]:
    """按时间顺序评估一步预测基线，不让未来观测进入历史预测。"""
    ordered = sorted(points, key=lambda point: point.date)
    if any(not math.isfinite(point.price_yuan_per_ton) or point.price_yuan_per_ton <= 0 or not point.source for point in ordered):
        raise ValueError("价格观测必须为有限正数且包含数据来源")
    if len(ordered) < minimum_history + 2:
        raise ValueError(f"滚动回测至少需要 {minimum_history + 2} 条连续周度观测")
    if minimum_history < 4:
        raise ValueError("minimum_history 不得小于 4")
    for left, right in zip(ordered, ordered[1:]):
        if (right.date - left.date).days != 7:
            raise ValueError("滚动回测要求日期严格每周连续")

    rows: list[dict[str, object]] = []
    for target_index in range(minimum_history, len(ordered)):
        history = ordered[:target_index]
        target = ordered[target_index]
        prediction_map = {
            "naive_last_value": history[-1].price_yuan_per_ton,
            "mean_last_4_weeks": sum(item.price_yuan_per_ton for item in history[-4:]) / 4,
        }
        for model_name, prediction in prediction_map.items():
            rows.append({
                "data_cutoff": history[-1].date.isoformat(),
                "target_date": target.date.isoformat(),
                "actual_yuan_per_ton": target.price_yuan_per_ton,
                "forecast_yuan_per_ton": prediction,
                "error_yuan_per_ton": prediction - target.price_yuan_per_ton,
                "model": model_name,
                "source": "; ".join(sorted({item.source for item in history + [target]})),
            })

    summary: dict[str, object] = {
        "protocol": "expanding_window_one_step_ahead",
        "minimum_history_observations": minimum_history,
        "forecast_origins": len(ordered) - minimum_history,
        "results": {},
        "data_source": sorted({point.source for point in ordered}),
        "first_observation": ordered[0].date.isoformat(),
        "last_observation": ordered[-1].date.isoformat(),
    }
    for model_name in ("naive_last_value", "mean_last_4_weeks"):
        predictions = [row for row in rows if row["model"] == model_name]
        errors = [float(row["error_yuan_per_ton"]) for row in predictions]
        actuals = [float(row["actual_yuan_per_ton"]) for row in predictions]
        absolute_errors = [abs(error) for error in errors]
        squared_errors = [error * error for error in errors]
        mape_values = [abs(error) / actual for error, actual in zip(errors, actuals) if actual != 0]
        mean_actual = sum(actuals) / len(actuals)
        total_variation = sum((actual - mean_actual) ** 2 for actual in actuals)
        residual_sum = sum(squared_errors)
        summary["results"][model_name] = {
            "n": len(errors),
            "mae_yuan_per_ton": sum(absolute_errors) / len(errors),
            "rmse_yuan_per_ton": (sum(squared_errors) / len(errors)) ** 0.5,
            "mape": sum(mape_values) / len(mape_values) if mape_values else None,
            "r2": 1 - residual_sum / total_variation if total_variation else None,
        }
    return rows, summary
