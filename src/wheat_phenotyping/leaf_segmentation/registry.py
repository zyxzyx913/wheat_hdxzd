"""传统分割算法统一注册和调用接口。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from wheat_phenotyping.rgb_preprocessing import RGBImage

from .exg import BinaryMask, segment_leaves_exg
from .fusion import segment_exg_hsv_fusion
from .hsv import HSV_REQUIRED_PARAMETERS, segment_hsv
from .otsu import segment_otsu_exg_with_threshold

Segmenter = Callable[[RGBImage, Mapping[str, object]], "AlgorithmPrediction"]


@dataclass(frozen=True)
class AlgorithmPrediction:
    """统一预测结果；metadata 保存逐图自动计算参数等信息。"""

    mask: BinaryMask
    metadata: Mapping[str, object]


class SegmenterRegistry:
    """以稳定名称注册算法，避免评价脚本复制分割逻辑。"""

    def __init__(self) -> None:
        self._algorithms: dict[str, Segmenter] = {}

    def register(self, name: str, algorithm: Segmenter) -> None:
        if not name or name.strip() != name:
            raise ValueError("算法名称不能为空或包含首尾空格")
        if name in self._algorithms:
            raise ValueError(f"算法已注册：{name}")
        self._algorithms[name] = algorithm

    def get(self, name: str) -> Segmenter:
        try:
            return self._algorithms[name]
        except KeyError as error:
            raise KeyError(f"未注册的分割算法：{name}") from error

    def names(self) -> tuple[str, ...]:
        return tuple(self._algorithms)

    def run(self, name: str, image: RGBImage, parameters: Mapping[str, object]) -> AlgorithmPrediction:
        return self.get(name)(image, parameters)


def _required(parameters: Mapping[str, object], required: set[str], name: str) -> None:
    missing = required - set(parameters)
    if missing:
        raise ValueError(f"{name} 缺少参数：{sorted(missing)}")


def _exg(image: RGBImage, parameters: Mapping[str, object]) -> AlgorithmPrediction:
    _required(parameters, {"exg_threshold"}, "ExG")
    unknown = set(parameters) - {"exg_threshold", "min_component_area"}
    if unknown:
        raise ValueError(f"ExG 存在未知参数：{sorted(unknown)}")
    mask = segment_leaves_exg(image, exg_threshold=int(parameters["exg_threshold"]),
                              min_component_area=int(parameters.get("min_component_area", 0)))
    return AlgorithmPrediction(mask, {})


def _hsv(image: RGBImage, parameters: Mapping[str, object]) -> AlgorithmPrediction:
    mask = segment_hsv(image, parameters)
    return AlgorithmPrediction(mask, {})


def _otsu(image: RGBImage, parameters: Mapping[str, object]) -> AlgorithmPrediction:
    mask, threshold = segment_otsu_exg_with_threshold(image, parameters)
    return AlgorithmPrediction(mask, {"computed_exg_threshold": threshold, "threshold_method": "otsu"})


def _fusion(image: RGBImage, parameters: Mapping[str, object]) -> AlgorithmPrediction:
    mask = segment_exg_hsv_fusion(image, parameters)
    return AlgorithmPrediction(mask, {"fusion_rule": "ExG threshold AND HSV range"})


def create_default_registry() -> SegmenterRegistry:
    """创建包含四种传统分割算法的默认注册表。"""
    registry = SegmenterRegistry()
    registry.register("ExG", _exg)
    registry.register("HSV", _hsv)
    registry.register("Otsu-ExG", _otsu)
    registry.register("ExG-HSV Fusion", _fusion)
    return registry


DEFAULT_REGISTRY = create_default_registry()
