"""当前图像指标与 WOFOST 状态的边界；不把覆盖率直接当作 LAI。"""
from __future__ import annotations


def build_initial_state(*, image_metrics: dict[str, object], growth_stage: dict[str, object] | None) -> dict[str, object]:
    return {
        "image_metrics": image_metrics,
        "growth_stage": growth_stage,
        "lai": None,
        "tagp": None,
        "mapping_status": "unavailable",
        "limitations": ["RGB 覆盖率尚未经过本地校准，不能直接替换 WOFOST LAI。"],
    }
