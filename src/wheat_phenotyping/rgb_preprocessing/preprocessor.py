"""轻量级 RGB 图像读入与预处理，支持 PPM P3/P6 格式。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RGBImage:
    """行优先 RGB 图像；pixels 为每通道 0 到 255 的字节数据。"""

    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1 or len(self.pixels) != self.width * self.height * 3:
            raise ValueError("RGB 图像的尺寸与像素数据长度不匹配")


def _read_token(data: bytes, offset: int) -> tuple[bytes, int]:
    """读取 PPM 头部字段，并跳过空格和注释。"""
    size = len(data)
    while offset < size:
        if data[offset] in b" \t\r\n":
            offset += 1
        elif data[offset] == ord("#"):
            while offset < size and data[offset] not in b"\r\n":
                offset += 1
        else:
            break
    start = offset
    while offset < size and data[offset] not in b" \t\r\n#":
        offset += 1
    if start == offset:
        raise ValueError("PPM 文件头不完整")
    return data[start:offset], offset


def read_ppm(path: str | Path) -> RGBImage:
    """读取 PPM P3/P6 图像并将像素值映射到 0 至 255。"""
    data = Path(path).read_bytes()
    magic, pos = _read_token(data, 0)
    if magic not in (b"P3", b"P6"):
        raise ValueError("仅支持 PPM P3/P6 格式")
    width_token, pos = _read_token(data, pos)
    height_token, pos = _read_token(data, pos)
    max_token, pos = _read_token(data, pos)
    width, height, max_value = int(width_token), int(height_token), int(max_token)
    if width < 1 or height < 1 or not 1 <= max_value <= 255:
        raise ValueError("PPM 尺寸或最大像素值无效；当前只支持 maxval <= 255")

    if magic == b"P6":
        # P6 像素数据紧跟 maxval 后的一个空白分隔符。
        if pos >= len(data) or data[pos] not in b" \t\r\n":
            raise ValueError("PPM 二进制数据缺少头部结束符")
        if data[pos:pos + 2] == b"\r\n":
            pos += 2
        else:
            pos += 1
        raw = data[pos:]
        expected = width * height * 3
        if len(raw) != expected:
            raise ValueError(f"PPM 像素数据长度错误：预期 {expected}，实际 {len(raw)}")
        if max_value != 255:
            pixels = bytes(round(value * 255 / max_value) for value in raw)
        else:
            pixels = raw
    else:
        values = []
        while pos < len(data):
            token, pos = _read_token(data, pos)
            values.append(int(token))
        expected = width * height * 3
        if len(values) != expected or any(v < 0 or v > max_value for v in values):
            raise ValueError("PPM ASCII 像素数量或像素值无效")
        pixels = bytes(round(value * 255 / max_value) for value in values)
    return RGBImage(width, height, pixels)


def preprocess_rgb(
    image: RGBImage,
    *,
    max_size: int | None = None,
    normalize_brightness: bool = False,
    target_mean: float = 127.0,
) -> RGBImage:
    """以最近邻插值缩小图像，可选用全图均值进行亮度归一化。

    最近邻缩放便于保持模拟标签与像素坐标的可追溯性；若需高质量重采样，
    后续可在模块接口不变的前提下扩展插值策略。
    """
    if max_size is not None and max_size < 1:
        raise ValueError("max_size 必须大于 0")
    width, height, pixels = image.width, image.height, image.pixels
    if max_size is not None and max(width, height) > max_size:
        ratio = max_size / max(width, height)
        new_width = max(1, round(width * ratio))
        new_height = max(1, round(height * ratio))
        resized = bytearray(new_width * new_height * 3)
        for y in range(new_height):
            source_y = min(height - 1, int(y / ratio))
            for x in range(new_width):
                source_x = min(width - 1, int(x / ratio))
                source = (source_y * width + source_x) * 3
                target = (y * new_width + x) * 3
                resized[target:target + 3] = pixels[source:source + 3]
        width, height, pixels = new_width, new_height, bytes(resized)

    if normalize_brightness:
        if not 0 < target_mean <= 255:
            raise ValueError("target_mean 必须在 (0, 255] 范围内")
        mean = sum(pixels) / len(pixels)
        if mean > 0:
            gain = target_mean / mean
            pixels = bytes(max(0, min(255, round(value * gain))) for value in pixels)
    return RGBImage(width, height, pixels)


def write_ppm(image: RGBImage, path: str | Path) -> None:
    """将 RGB 图像写为 PPM P6。"""
    Path(path).write_bytes(f"P6\n{image.width} {image.height}\n255\n".encode("ascii") + image.pixels)
