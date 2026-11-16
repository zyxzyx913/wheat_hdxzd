"""人工标注和预测掩膜错误区域叠加可视化。"""

from __future__ import annotations

from pathlib import Path

from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.rgb_preprocessing import RGBImage


def create_segmentation_overlay(
    image: RGBImage,
    reference: BinaryMask,
    prediction: BinaryMask,
    *,
    alpha: float = 0.45,
) -> RGBImage:
    """生成叠加图：TP 绿色、FP 红色、FN 蓝色、TN 保留原图。"""
    if not 0 <= alpha <= 1:
        raise ValueError("alpha 必须在 [0,1] 范围内")
    if (image.width, image.height) != (reference.width, reference.height) or (
        prediction.width, prediction.height
    ) != (reference.width, reference.height):
        raise ValueError("原图、人工标注和预测掩膜尺寸必须完全一致")
    colors = {
        "tp": (0, 220, 0),
        "fp": (255, 40, 40),
        "fn": (40, 100, 255),
    }
    output = bytearray(image.pixels)
    for index, (actual, predicted) in enumerate(zip(reference.pixels, prediction.pixels)):
        if actual == 255 and predicted == 255:
            color = colors["tp"]
        elif predicted == 255:
            color = colors["fp"]
        elif actual == 255:
            color = colors["fn"]
        else:
            continue
        offset = index * 3
        for channel in range(3):
            output[offset + channel] = round(
                (1 - alpha) * image.pixels[offset + channel] + alpha * color[channel]
            )
    return RGBImage(image.width, image.height, bytes(output))


def write_segmentation_overlay(
    image: RGBImage,
    reference: BinaryMask,
    prediction: BinaryMask,
    path: str | Path,
    *,
    alpha: float = 0.45,
) -> Path:
    """保存带错误区域颜色编码的 PNG 叠加图。"""
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("保存 PNG 叠加图需要 Pillow") from error
    overlay = create_segmentation_overlay(image, reference, prediction, alpha=alpha)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.frombytes("RGB", (overlay.width, overlay.height), overlay.pixels).save(destination, format="PNG")
    return destination
