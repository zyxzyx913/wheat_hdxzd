"""ExG 指数直方图上的 Otsu 全局自动阈值分割。"""

from __future__ import annotations

from collections.abc import Mapping

from wheat_phenotyping.rgb_preprocessing import RGBImage

from .exg import BinaryMask


def exg_values(image: RGBImage) -> list[int]:
    """计算整数 Excess Green 指数 2G-R-B，理论范围 [-510, 510]。"""
    values = []
    for offset in range(0, len(image.pixels), 3):
        red, green, blue = image.pixels[offset:offset + 3]
        values.append(2 * green - red - blue)
    return values


def otsu_threshold(values: list[int]) -> int:
    """用 1021-bin 整数直方图最大化类间方差并返回实算 ExG 阈值。

    若特征图为常数，绿色正值统一标前景（阈值为 c-1），非正值统一标背景
    （阈值为 c）；该退化规则明确且可复现，避免均匀绿图被误判为空。
    多个阈值并列时选择最小阈值。
    """
    if not values:
        raise ValueError("Otsu 输入不能为空")
    if any(not -510 <= value <= 510 for value in values):
        raise ValueError("ExG 特征值必须位于 [-510, 510]")
    minimum, maximum = min(values), max(values)
    if minimum == maximum:
        return minimum - 1 if minimum > 0 else minimum

    histogram = [0] * 1021
    for value in values:
        histogram[value + 510] += 1
    total = len(values)
    total_sum = sum((index - 510) * count for index, count in enumerate(histogram))
    weight_background = 0
    sum_background = 0
    best_threshold = minimum
    best_variance = -1.0
    for index, count in enumerate(histogram[:-1]):
        weight_background += count
        sum_background += (index - 510) * count
        weight_foreground = total - weight_background
        if weight_background == 0 or weight_foreground == 0:
            continue
        mean_background = sum_background / weight_background
        mean_foreground = (total_sum - sum_background) / weight_foreground
        variance = weight_background * weight_foreground * (mean_background - mean_foreground) ** 2
        threshold = index - 510
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold


def segment_otsu_exg_with_threshold(
    image: RGBImage, parameters: Mapping[str, object] | None = None
) -> tuple[BinaryMask, int]:
    """用 Otsu 自动选择 ExG 阈值，同时返回掩膜和该图的实算阈值。

    参数映射目前可为空；不接受手动 threshold，避免误把固定阈值称作自动 Otsu。
    """
    if parameters and set(parameters) - {"method"}:
        raise ValueError("Otsu-ExG 不接受手动阈值参数；阈值由每张输入图像自动计算")
    if parameters and parameters.get("method", "exg_otsu") != "exg_otsu":
        raise ValueError("method 当前只支持 exg_otsu")
    values = exg_values(image)
    threshold = otsu_threshold(values)
    mask = BinaryMask(image.width, image.height, bytes(255 if value > threshold else 0 for value in values))
    return mask, threshold


def segment_otsu_exg(image: RGBImage, parameters: Mapping[str, object] | None = None) -> BinaryMask:
    """Otsu-ExG 标准接口，仅返回统一格式 BinaryMask。"""
    mask, _threshold = segment_otsu_exg_with_threshold(image, parameters)
    return mask
