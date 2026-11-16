"""常见 RGB 图像和人工二值标注读取适配器。"""

from __future__ import annotations

from pathlib import Path

from wheat_phenotyping.evaluation.mask_io import read_binary_pgm
from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.rgb_preprocessing import RGBImage, read_ppm


def load_rgb_image(path: str | Path) -> RGBImage:
    """读取 PPM P3/P6、PNG、JPEG、BMP、TIFF 等格式为统一 RGBImage。

    PPM 使用项目自带读入器；其他格式由 Pillow 解码并应用 EXIF 方向信息。
    """
    source = Path(path)
    if source.suffix.lower() == ".ppm":
        return read_ppm(source)
    try:
        from PIL import Image, ImageOps
    except ImportError as error:
        raise RuntimeError("读取 PNG/JPEG/BMP/TIFF 需要安装 Pillow：python -m pip install -r requirements.txt") from error
    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            return RGBImage(image.width, image.height, image.tobytes())
    except Exception as error:
        raise ValueError(f"RGB 图像读取失败：{source}: {error}") from error


def load_binary_mask(path: str | Path) -> BinaryMask:
    """读取 PGM 或常见 PNG/TIFF 标注；拒绝灰度中间值和含糊的颜色编码。"""
    source = Path(path)
    if source.suffix.lower() == ".pgm":
        return read_binary_pgm(source)
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("读取 PNG/TIFF 标注需要安装 Pillow：python -m pip install -r requirements.txt") from error
    try:
        with Image.open(source) as opened:
            image = opened.copy()
        if image.mode in ("1", "L", "P", "I", "I;16", "I;16L", "I;16B"):
            values = [image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)]
            allowed = {0, 1, 255}
            if any(value not in allowed for value in values):
                raise ValueError("灰度/调色板标注只接受 0、1 或 255 二值")
            pixels = bytes(255 if value else 0 for value in values)
        elif image.mode in ("RGB", "RGBA"):
            rgb = image.convert("RGB")
            colors = set(rgb.getdata())
            if len(colors) > 2 or (len(colors) == 2 and (0, 0, 0) not in colors):
                raise ValueError("彩色标注必须仅含黑色背景和一种前景色；否则请转换为二值掩膜")
            pixels = bytes(
                0 if rgb.getpixel((x, y)) == (0, 0, 0) else 255
                for y in range(rgb.height) for x in range(rgb.width)
            )
        else:
            raise ValueError(f"不支持的标注图像模式：{image.mode}")
        return BinaryMask(image.width, image.height, pixels)
    except Exception as error:
        if isinstance(error, ValueError) and str(error).startswith(("灰度/调色板", "彩色标注", "不支持的标注")):
            raise
        raise ValueError(f"二值标注读取失败：{source}: {error}") from error


def load_sample_images(image_path: str | Path, mask_path: str | Path) -> tuple[RGBImage, BinaryMask]:
    """载入一对图像/标注并核对尺寸；不对标注进行缩放。"""
    image = load_rgb_image(image_path)
    mask = load_binary_mask(mask_path)
    if (image.width, image.height) != (mask.width, mask.height):
        raise ValueError(
            f"图像与人工掩膜尺寸不一致：图像 {image.width}x{image.height}，"
            f"掩膜 {mask.width}x{mask.height}；不会自动缩放人工标注"
        )
    return image, mask
