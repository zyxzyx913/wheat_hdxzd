"""可解释的 ExG 与 HSV 交集融合分割。"""

from __future__ import annotations

from collections.abc import Mapping

from wheat_phenotyping.rgb_preprocessing import RGBImage

from .exg import BinaryMask, segment_leaves_exg
from .hsv import HSV_REQUIRED_PARAMETERS, segment_hsv


def segment_exg_hsv_fusion(image: RGBImage, parameters: Mapping[str, object]) -> BinaryMask:
    """仅当 ExG 超阈值且 HSV 同时落入植被范围时判为前景（逻辑 AND）。"""
    required = HSV_REQUIRED_PARAMETERS | {"exg_threshold"}
    missing = required - set(parameters)
    if missing:
        raise ValueError(f"缺少 ExG-HSV 融合参数：{sorted(missing)}")
    unknown = set(parameters) - required - {"min_component_area"}
    if unknown:
        raise ValueError(f"未知 ExG-HSV 融合参数：{sorted(unknown)}")
    exg_mask = segment_leaves_exg(
        image,
        exg_threshold=int(parameters["exg_threshold"]),
        min_component_area=int(parameters.get("min_component_area", 0)),
    )
    hsv_parameters = {key: parameters[key] for key in HSV_REQUIRED_PARAMETERS}
    hsv_mask = segment_hsv(image, hsv_parameters)
    fused = bytes(255 if left and right else 0 for left, right in zip(exg_mask.pixels, hsv_mask.pixels))
    return BinaryMask(image.width, image.height, fused)
