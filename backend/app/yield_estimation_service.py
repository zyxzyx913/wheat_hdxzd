"""用户输入亩产情景的透明产量与利润估算。"""
from __future__ import annotations


def calculate_yield_estimation(payload: dict[str, object]) -> dict[str, object]:
    area = float(payload.get("area_mu", 0)); low = float(payload.get("low_yield_kg_per_mu", 0)); normal = float(payload.get("normal_yield_kg_per_mu", 0)); high = float(payload.get("high_yield_kg_per_mu", 0)); price = float(payload.get("price_yuan_per_ton", 0)); cost = float(payload.get("cost_yuan_per_mu", 0))
    if area <= 0 or min(low, normal, high, price, cost) < 0 or not (low <= normal <= high): raise ValueError("面积、产量、价格和成本输入无效，且需满足低位≤正常≤高位")
    scenarios = {}
    for name, yield_kg in (("low", low), ("normal", normal), ("high", high)):
        tons = area * yield_kg / 1000
        revenue = tons * price
        total_cost = area * cost
        scenarios[name] = {"yield_kg_per_mu": yield_kg, "total_yield_ton": tons, "revenue_yuan": revenue, "total_cost_yuan": total_cost, "profit_yuan": revenue - total_cost, "profit_per_mu_yuan": (revenue - total_cost) / area}
    return {"status": "succeeded", "version": "yield-estimation-v1-user-scenarios", "inputs": {"area_mu": area, "price_yuan_per_ton": price, "cost_yuan_per_mu": cost}, "scenarios": scenarios, "limitations": ["亩产情景由用户输入，不是模型预测", "未使用长势等级修正产量", "结果不等同于实测产量或最终成交收益"]}
