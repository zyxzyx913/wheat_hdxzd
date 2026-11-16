"""HSV 颜色阈值小麦叶片分割算法。"""

from __future__ import annotations

from collections.abc import Mapping

from wheat_phenotyping.rgb_preprocessing import RGBImage

from .exg import BinaryMask


HSV_REQUIRED_PARAMETERS = {
    "hue_min", "hue_max", "saturation_min", "saturation_max", "value_min", "value_max"
}


def rgb_to_hsv(red: int, green: int, blue: int) -> tuple[float, float, float]:
    """将 8 位 RGB 转换为 H∈[0,360)、S/V∈[0,1] 的 HSV。"""
    r, g, b = red / 255.0, green / 255.0, blue / 255.0
    maximum, minimum = max(r, g, b), min(r, g, b)
    delta = maximum - minimum
    if delta == 0:
        hue = 0.0
    elif maximum == r:
        hue = (60 * (((g - b) / delta) % 6)) % 360
    elif maximum == g:
        hue = 60 * ((b - r) / delta + 2)
    else:
        hue = 60 * ((r - g) / delta + 4)
    saturation = 0.0 if maximum == 0 else delta / maximum
    return hue, saturation, maximum


def segment_hsv(image: RGBImage, parameters: Mapping[str, object]) -> BinaryMask:
    """按显式 HSV 阈值分割；色相上下限可跨越 0 度。"""
    missing = HSV_REQUIRED_PARAMETERS - set(parameters)
    if missing:
        raise ValueError(f"缺少 HSV 参数：{sorted(missing)}")
    unknown = set(parameters) - HSV_REQUIRED_PARAMETERS
    if unknown:
        raise ValueError(f"未知 HSV 参数：{sorted(unknown)}")
    h_min, h_max = float(parameters["hue_min"]), float(parameters["hue_max"])
    s_min, s_max = float(parameters["saturation_min"]), float(parameters["saturation_max"])
    v_min, v_max = float(parameters["value_min"]), float(parameters["value_max"])
    if not (0 <= h_min < 360 and 0 <= h_max < 360):
        raise ValueError("hue_min/hue_max 必须在 [0, 360) 内")
    if not (0 <= s_min <= s_max <= 1 and 0 <= v_min <= v_max <= 1):
        raise ValueError("饱和度和明度范围必须满足 0 <= min <= max <= 1")

    output = bytearray(image.width * image.height)
    for index in range(image.width * image.height):
        offset = index * 3
        hue, saturation, value = rgb_to_hsv(*image.pixels[offset:offset + 3])
        hue_match = h_min <= hue <= h_max if h_min <= h_max else hue >= h_min or hue <= h_max
        if hue_match and s_min <= saturation <= s_max and v_min <= value <= v_max:
            output[index] = 255
    return BinaryMask(image.width, image.height, bytes(output))
