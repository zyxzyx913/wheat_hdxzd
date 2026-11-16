"""读取人工标注 PGM 掩膜，严格检查二值标签和图像尺寸。"""

from __future__ import annotations

from pathlib import Path

from wheat_phenotyping.leaf_segmentation import BinaryMask


def _token(data: bytes, offset: int) -> tuple[bytes, int]:
    """读取 PGM 头字段并跳过空白和注释。"""
    while offset < len(data):
        if data[offset] in b" \t\r\n":
            offset += 1
        elif data[offset] == ord("#"):
            while offset < len(data) and data[offset] not in b"\r\n":
                offset += 1
        else:
            break
    start = offset
    while offset < len(data) and data[offset] not in b" \t\r\n#":
        offset += 1
    if start == offset:
        raise ValueError("PGM 文件头不完整")
    return data[start:offset], offset


def read_binary_pgm(path: str | Path) -> BinaryMask:
    """读取 PGM P2/P5；接受 0/最大值或 0/1 二值标签。"""
    data = Path(path).read_bytes()
    magic, pos = _token(data, 0)
    if magic not in (b"P2", b"P5"):
        raise ValueError("人工掩膜必须为 PGM P2 或 P5 格式")
    width_token, pos = _token(data, pos)
    height_token, pos = _token(data, pos)
    max_token, pos = _token(data, pos)
    width, height, max_value = int(width_token), int(height_token), int(max_token)
    if width < 1 or height < 1 or not 1 <= max_value <= 255:
        raise ValueError("PGM 宽高或最大像素值无效；仅支持 maxval <= 255")
    expected = width * height
    if magic == b"P5":
        if pos >= len(data) or data[pos] not in b" \t\r\n":
            raise ValueError("PGM 二进制数据缺少头部结束符")
        pos += 2 if data[pos:pos + 2] == b"\r\n" else 1
        values = data[pos:]
        if len(values) != expected:
            raise ValueError(f"PGM 像素数量错误：预期 {expected}，实际 {len(values)}")
        pixels = list(values)
    else:
        pixels = []
        while True:
            # PGM ASCII 文件允许像素数据后存在空白或注释。
            while pos < len(data):
                if data[pos] in b" \t\r\n":
                    pos += 1
                elif data[pos] == ord("#"):
                    while pos < len(data) and data[pos] not in b"\r\n":
                        pos += 1
                else:
                    break
            if pos >= len(data):
                break
            value, pos = _token(data, pos)
            pixels.append(int(value))
        if len(pixels) != expected:
            raise ValueError(f"PGM 像素数量错误：预期 {expected}，实际 {len(pixels)}")
    allowed = {0, max_value}
    # 部分标注工具将前景写作 1、背景写作 0，即使 maxval 声明为 255。
    if max_value != 1:
        allowed.add(1)
    if any(value not in allowed for value in pixels):
        raise ValueError("无效人工标签：掩膜必须只有背景 0 和前景 1 或 maxval")
    normalized = bytes(255 if value else 0 for value in pixels)
    return BinaryMask(width, height, normalized)
