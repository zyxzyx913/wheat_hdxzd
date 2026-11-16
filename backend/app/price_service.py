"""全国小麦价格服务：只使用可追溯观测，数据不足时明确不可用。"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from wheat_phenotyping.economics import load_price_csv, forecast_naive, rolling_origin_backtest, forecast_as_dicts

from .config import PROJECT_ROOT

PRICE_PATH = PROJECT_ROOT / "data/raw/economics/national_wheat_price.csv"
SOURCE_URL = "https://www.lswz.gov.cn/html/zmhd/lysj/lsjg-scjc.shtml"


def _load():
    if not PRICE_PATH.is_file():
        return []
    try:
        return load_price_csv(PRICE_PATH)
    except ValueError:
        # 允许历史数据少于十周时展示真实历史，但不允许预测。
        import csv
        rows = []
        with PRICE_PATH.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append((date.fromisoformat(row["date"]), float(row["price_yuan_per_ton"]), row["source"]))
        return rows


def price_status() -> dict[str, object]:
    points = _load()
    count = len(points)
    latest = max(points, key=lambda p: p.date) if points and hasattr(points[0], "date") else (max(points) if points else None)
    latest_date = latest.date if latest is not None and hasattr(latest, "date") else (latest[0] if latest else None)
    latest_price = latest.price_yuan_per_ton if latest is not None and hasattr(latest, "price_yuan_per_ton") else (latest[1] if latest else None)
    rows = price_history()["items"]
    prices = [float(row["price_yuan_per_ton"]) for row in rows]
    return {"dataset": "全国小麦平均收购价格", "source": SOURCE_URL, "count": count, "latest_date": latest_date.isoformat() if latest_date else None, "current_price_yuan_per_ton": latest_price, "highest_price_yuan_per_ton": max(prices) if prices else None, "lowest_price_yuan_per_ton": min(prices) if prices else None, "data_completeness": "unknown" if count < 2 else "calculated", "forecast_enabled": count >= 10, "status": "ready" if count >= 10 else "insufficient_history", "message": "真实历史序列不足 10 周，暂不生成价格预测。" if count < 10 else "可进行时间序列滚动验证。"}


def price_history() -> dict[str, object]:
    points = _load()
    rows = [{"date": p.date.isoformat(), "price_yuan_per_ton": p.price_yuan_per_ton, "source": p.source} if hasattr(p, "date") else {"date": p[0].isoformat(), "price_yuan_per_ton": p[1], "source": p[2]} for p in points]
    return {"dataset": "全国小麦平均收购价格", "unit": "元/吨", "source": SOURCE_URL, "items": rows, "latest_date": rows[-1]["date"] if rows else None, "coverage": {"count": len(rows), "first_date": rows[0]["date"] if rows else None, "last_date": rows[-1]["date"] if rows else None}}


def price_trend_summary() -> dict[str, object]:
    rows = price_history()["items"]
    prices = [float(row["price_yuan_per_ton"]) for row in rows]
    def change(window: int):
        return None if len(prices) <= window else prices[-1] - prices[-1 - window]
    return {"four_week_change_yuan_per_ton": change(4), "twelve_week_change_yuan_per_ton": change(12), "direction": "unavailable" if len(prices) < 5 else ("up" if change(4) > 0 else "down" if change(4) < 0 else "stable"), "status": "insufficient_history" if len(prices) < 5 else "available"}


def price_forecast(horizon_days: int = 30) -> dict[str, object]:
    points = _load()
    if len(points) < 10 or not hasattr(points[0], "date"):
        return {"status": "unavailable", "horizon_days": horizon_days, "model": None, "points": [], "backtest": None, "direction": "unavailable", "message": "真实周度历史不足 10 条，不能产生经过回测的价格预测。", "data_source": SOURCE_URL}
    _, summary = rolling_origin_backtest(points)
    forecasts = forecast_as_dicts(forecast_naive(points, horizon_weeks=4))
    return {"status": "succeeded", "horizon_days": horizon_days, "model": "baseline_comparison", "points": forecasts, "backtest": summary, "direction": price_trend_summary()["direction"], "harvest_scenarios": {"normal": "基于历史序列", "strong": "待验证", "weak": "待验证"}, "data_source": SOURCE_URL}


def profit_estimate(quantity_ton: float, price_yuan_per_ton: float, total_cost_yuan: float) -> dict[str, object]:
    if quantity_ton < 0 or price_yuan_per_ton < 0 or total_cost_yuan < 0:
        raise ValueError("数量、价格和成本不能为负数")
    revenue = quantity_ton * price_yuan_per_ton
    return {"quantity_ton": quantity_ton, "reference_price_yuan_per_ton": price_yuan_per_ton, "total_cost_yuan": total_cost_yuan, "estimated_revenue_yuan": revenue, "estimated_profit_yuan": revenue - total_cost_yuan, "price_is_reference_only": True}
