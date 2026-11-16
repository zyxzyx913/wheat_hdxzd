"""基于可见 RGB 特征和显式阈值的小麦长势等级规则基线。

此方法仅输出图像可见性代理指标；没有经验证的农学等级标准时，不提供默认阈值。
"""

from __future__ import annotations

from dataclasses import dataclass

from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.rgb_preprocessing import RGBImage


@dataclass(frozen=True)
class VisibleGrowthFeatures:
    """从单幅 RGB 图像提取的可见特征，不等同于完整植株生物量。"""

    image_width: int
    image_height: int
    green_pixel_count: int
    green_area_fraction: float
    canopy_height_fraction: float
    canopy_width_fraction: float
    mean_rgb_in_mask: tuple[float, float, float] | None
    mean_exg_in_mask: float | None


@dataclass(frozen=True)
class GrowthGradeThresholds:
    """通过带等级标签的参考数据确定的绿色面积比例分界值。"""

    weak_max_green_fraction: float
    moderate_max_green_fraction: float

    def __post_init__(self) -> None:
        weak, moderate = self.weak_max_green_fraction, self.moderate_max_green_fraction
        if not (0 <= weak < moderate <= 1):
            raise ValueError("阈值须满足 0 <= 弱势上限 < 中势上限 <= 1")


@dataclass(frozen=True)
class GrowthGradeResult:
    """规则分类结果及其判定依据。"""

    grade: str
    feature_name: str
    feature_value: float
    thresholds: GrowthGradeThresholds
    data_source: str = "unspecified"
    interpretation: str = "基于图像可见绿色面积比例的规则结果，未经农学标准验证。"


def extract_visible_growth_features(image: RGBImage, mask: BinaryMask) -> VisibleGrowthFeatures:
    """汇总掩膜面积、外接框比例、掩膜内均值颜色和 ExG。"""
    if (image.width, image.height) != (mask.width, mask.height):
        raise ValueError("图像和叶片掩膜的宽高必须一致")
    indices = [index for index, value in enumerate(mask.pixels) if value == 255]
    green_count = len(indices)
    if not indices:
        return VisibleGrowthFeatures(image.width, image.height, 0, 0.0, 0.0, 0.0, None, None)
    xs = [index % image.width for index in indices]
    ys = [index // image.width for index in indices]
    totals = [0, 0, 0]
    exg_total = 0
    for index in indices:
        offset = index * 3
        red, green, blue = image.pixels[offset:offset + 3]
        totals[0] += red
        totals[1] += green
        totals[2] += blue
        exg_total += 2 * green - red - blue
    return VisibleGrowthFeatures(
        image_width=image.width,
        image_height=image.height,
        green_pixel_count=green_count,
        green_area_fraction=green_count / (image.width * image.height),
        canopy_height_fraction=(max(ys) - min(ys) + 1) / image.height,
        canopy_width_fraction=(max(xs) - min(xs) + 1) / image.width,
        mean_rgb_in_mask=tuple(value / green_count for value in totals),
        mean_exg_in_mask=exg_total / green_count,
    )


def classify_visible_growth(
    features: VisibleGrowthFeatures,
    thresholds: GrowthGradeThresholds,
    *,
    data_source: str = "unspecified",
) -> GrowthGradeResult:
    """按绿色面积比例分为弱势、中势、旺势三个可配置等级。"""
    value = features.green_area_fraction
    if value <= thresholds.weak_max_green_fraction:
        grade = "弱势"
    elif value <= thresholds.moderate_max_green_fraction:
        grade = "中势"
    else:
        grade = "旺势"
    return GrowthGradeResult(
        grade=grade,
        feature_name="green_area_fraction",
        feature_value=value,
        thresholds=thresholds,
        data_source=data_source,
    )
