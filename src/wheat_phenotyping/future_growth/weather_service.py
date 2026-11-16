"""天气输入校验；不把电脑所在地或随机值当作麦田天气。"""
from __future__ import annotations

from datetime import date
from collections.abc import Mapping


REQUIRED_FIELDS = ("date", "tavg_c", "tmin_c", "tmax_c", "precip_mm", "radiation_mj_m2")


def validate_weather_rows(rows: list[Mapping[str, object]]) -> list[dict[str, object]]:
    validated = []
    for row in rows:
        missing = [name for name in REQUIRED_FIELDS if row.get(name) is None]
        if missing:
            raise ValueError(f"天气记录缺少字段: {', '.join(missing)}")
        date.fromisoformat(str(row["date"]))
        validated.append(dict(row))
    return validated
