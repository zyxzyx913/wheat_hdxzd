"""天气驱动的未来情景分析。

天气来自 Open-Meteo 公开 Forecast API；本模块只做天气摘要和未校准的风险筛查，
不把筛查结果解释为经过中国田间验证的作物预测。
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
SOURCE = "https://open-meteo.com/en/docs"
GEOCODING_SOURCE = "https://open-meteo.com/en/docs/geocoding-api"


def geocode_location(location: str) -> dict[str, object]:
    """将用户输入的详细地点解析为 Open-Meteo 返回的首选坐标。"""
    query = (location or "").strip()
    if len(query) < 2 or len(query) > 120:
        raise ValueError("请填写至少包含省、市或县区的详细种植地址。")
    params = urlencode({"name": query, "count": 5, "language": "zh", "format": "json"})
    request = Request(f"{GEOCODING_URL}?{params}", headers={"User-Agent": "MaishitongResearch/5.0"})
    with urlopen(request, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("results") or []
    if not results:
        raise ValueError("没有找到该种植地址，请补充省、市、县区或乡镇名称。")
    item = results[0]
    return {
        "name": item.get("name"), "country": item.get("country"),
        "admin1": item.get("admin1"), "admin2": item.get("admin2"),
        "latitude": item.get("latitude"), "longitude": item.get("longitude"),
        "timezone": item.get("timezone"), "source": GEOCODING_SOURCE,
    }


def fetch_daily_weather(latitude: float, longitude: float, start_date: date, days: int = 15) -> dict[str, object]:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("经纬度范围无效")
    params = urlencode({
        "latitude": latitude, "longitude": longitude,
        "start_date": start_date.isoformat(),
        "forecast_days": min(max(days, 1), 16),
        "timezone": "auto",
        "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration,shortwave_radiation_sum",
    })
    request = Request(f"{OPEN_METEO_URL}?{params}", headers={"User-Agent": "MaishitongResearch/4.3"})
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    rows = []
    for index, observed in enumerate(dates):
        rows.append({key: (values[index] if index < len(values) else None) for key, values in daily.items() if key != "time"} | {"date": observed})
    return {"status": "succeeded", "weather_type": "forecast", "source": SOURCE, "fetched_at_utc": datetime.now(timezone.utc).isoformat(), "latitude": latitude, "longitude": longitude, "timezone": payload.get("timezone"), "forecast_days_requested": days, "forecast_days_returned": len(rows), "rows": rows}


def screen_weather_risks(weather: dict[str, object], horizon_days: int) -> dict[str, object]:
    """只输出未校准筛查标记；阈值不是农学诊断标准。"""
    rows = (weather.get("rows") or [])[:horizon_days]
    if not rows:
        return {"status": "unavailable", "flags": [], "threshold_status": "missing"}
    max_temp = max((float(row["temperature_2m_max"]) for row in rows if row.get("temperature_2m_max") is not None), default=None)
    min_temp = min((float(row["temperature_2m_min"]) for row in rows if row.get("temperature_2m_min") is not None), default=None)
    rainfall = sum(float(row["precipitation_sum"]) for row in rows if row.get("precipitation_sum") is not None)
    flags = []
    if max_temp is not None and max_temp >= 35: flags.append("高温筛查标记")
    if min_temp is not None and min_temp <= 0: flags.append("低温筛查标记")
    if rainfall < 5: flags.append("降水偏少筛查标记")
    if rainfall > 100: flags.append("降水偏多筛查标记")
    return {"status": "screening_only", "flags": flags, "threshold_status": "unvalidated_project_screening", "threshold_source": "项目筛查阈值，未作为农学诊断标准", "summary": {"max_temp_c": max_temp, "min_temp_c": min_temp, "precipitation_sum_mm": rainfall}}
