"""PCSE/WOFOST 可选执行器；依赖和参数缺失时明确拒绝模拟。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WofostRunResult:
    status: str
    outputs: list[dict[str, Any]]
    model_version: str | None
    limitations: list[str]


def run_wofost(*, crop_parameters: Any, soil_parameters: Any, site_parameters: Any, weather: Any, agromanagement: Any) -> WofostRunResult:
    """仅在调用方提供真实参数、天气和 PCSE 时执行；当前默认不运行。"""
    try:
        import pcse  # type: ignore
    except ImportError as error:
        raise RuntimeError("PCSE 未安装，无法运行 WOFOST。") from error
    if any(value is None for value in (crop_parameters, soil_parameters, site_parameters, weather, agromanagement)):
        raise ValueError("WOFOST 需要作物、土壤、站点、天气和农事管理输入，禁止使用默认占位值。")
    raise RuntimeError("当前项目尚未完成参数来源核验和 PCSE 输入适配，未执行 WOFOST。")
