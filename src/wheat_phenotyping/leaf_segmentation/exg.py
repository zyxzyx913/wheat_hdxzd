"""基于 Excess Green（ExG）颜色指数的叶片分割基线。"""

from __future__ import annotations

from dataclasses import dataclass

from wheat_phenotyping.rgb_preprocessing import RGBImage


@dataclass(frozen=True)
class BinaryMask:
    """二值掩膜，前景值为 255，背景值为 0。"""

    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        if self.width < 1 or self.height < 1 or len(self.pixels) != self.width * self.height:
            raise ValueError("掩膜尺寸与像素数据长度不匹配")
        if any(value not in (0, 255) for value in self.pixels):
            raise ValueError("二值掩膜的像素值只能是 0 或 255")

    def save_pgm(self, path: str) -> None:
        """将掩膜保存为标准 PGM P5 文件。"""
        with open(path, "wb") as stream:
            stream.write(f"P5\n{self.width} {self.height}\n255\n".encode("ascii"))
            stream.write(self.pixels)


def _remove_small_components(mask: bytearray, width: int, height: int, min_area: int) -> None:
    """使用四邻域连通域标记，原地移除小于阈值的前景区域。"""
    if min_area <= 1:
        return
    visited = bytearray(width * height)
    for start, value in enumerate(mask):
        if value == 0 or visited[start]:
            continue
        stack = [start]
        visited[start] = 1
        component = []
        while stack:
            index = stack.pop()
            component.append(index)
            x, y = index % width, index // width
            for neighbor in (index - 1 if x else -1, index + 1 if x + 1 < width else -1,
                             index - width if y else -1, index + width if y + 1 < height else -1):
                if neighbor >= 0 and mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = 1
                    stack.append(neighbor)
        if len(component) < min_area:
            for index in component:
                mask[index] = 0


def segment_leaves_exg(
    image: RGBImage,
    *,
    exg_threshold: int = 20,
    min_component_area: int = 0,
) -> BinaryMask:
    """按 ExG=2G-R-B 阈值分割绿色叶片区域。

    当 ExG 大于阈值时标为前景。该颜色规则容易解释，但在复杂光照、
    绿色背景或叶片遮挡场景下可能失效；这些局限应在实验记录中注明。
    """
    if not -510 <= exg_threshold <= 510:
        raise ValueError("exg_threshold 必须在 -510 到 510 之间")
    if min_component_area < 0:
        raise ValueError("min_component_area 不能为负数")
    mask = bytearray(image.width * image.height)
    for pixel in range(image.width * image.height):
        offset = pixel * 3
        red, green, blue = image.pixels[offset:offset + 3]
        if 2 * green - red - blue > exg_threshold:
            mask[pixel] = 255
    _remove_small_components(mask, image.width, image.height, min_component_area)
    return BinaryMask(image.width, image.height, bytes(mask))
