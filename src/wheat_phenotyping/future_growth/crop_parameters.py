"""WOFOST 作物参数登记；不在本项目内复制或编造参数数值。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CropParameterSpec:
    crop: str
    variety: str
    source: str
    region: str
    verified: bool = False


EUROPEAN_WINTER_WHEAT_REFERENCE = CropParameterSpec(
    crop="wheat",
    variety="Winter_wheat_101",
    source="https://github.com/ajwdewit/WOFOST_crop_parameters",
    region="Europe reference; not validated for China",
    verified=False,
)


def require_verified_crop_parameters(spec: CropParameterSpec) -> None:
    if not spec.verified:
        raise RuntimeError(f"作物参数 {spec.variety} 仅为{spec.region}，未通过本地验证，禁止用于正式预测。")
