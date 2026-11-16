"""向量化颜色、纹理与邻域特征；仅依赖当前 RGB 图像。"""

import numpy as np
from scipy.ndimage import sobel, uniform_filter

from wheat_phenotyping.rgb_preprocessing import RGBImage
from ..rf_features import extract_pixel_features
from .schema import FeatureConfig, LEGACY_VERSION, feature_schema


def _check_image(image):
    # RGBImage 原类型未限制 pixels 为 bytes，此处增加显式类型检查。
    if not isinstance(image, RGBImage):
        raise TypeError("输入必须为 RGBImage，不能传入 BGR/浮点数组")
    if (type(image.width) is not int or type(image.height) is not int
            or image.width < 1 or image.height < 1 or not isinstance(image.pixels, bytes)
            or len(image.pixels) != image.width * image.height * 3):
        raise ValueError("RGB 尺寸或 uint8 bytes 缓冲区无效")


def extract_features(image: RGBImage, config: FeatureConfig = FeatureConfig()) -> np.ndarray:
    """返回连续 float32 特征矩阵；旧版直接委托原函数，保证逐值一致。"""
    _check_image(image)
    schema = feature_schema(config)
    if config.version == LEGACY_VERSION:
        result = extract_pixel_features(image)
    else:
        rgb = np.frombuffer(image.pixels, np.uint8).reshape(image.height, image.width, 3).astype(np.float32) / 255.0
        r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        channels = []
        if config.color:
            # 最大通道并列时依照旧 rgb_to_hsv 的 R、G、B 优先顺序。
            value = rgb.max(axis=2)
            delta = value - rgb.min(axis=2)
            saturation = np.divide(delta, value, out=np.zeros_like(value), where=value != 0)
            hue = np.zeros_like(value)
            active = delta > 0
            red = active & (value == r)
            green = active & ~red & (value == g)
            blue = active & ~red & ~green
            hue[red] = ((g[red] - b[red]) / delta[red]) % 6
            hue[green] = (b[green] - r[green]) / delta[green] + 2
            hue[blue] = (r[blue] - g[blue]) / delta[blue] + 4
            radians = hue * (np.pi / 3)
            channels += [r, g, b, saturation * np.sin(radians), saturation * np.cos(radians),
                         saturation, value, (2 * g - r - b) / 2]
        if config.texture:
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            mean = uniform_filter(gray, size=config.texture_window, mode="nearest")
            variance = uniform_filter(gray * gray, size=config.texture_window, mode="nearest") - mean * mean
            channels += [mean, np.sqrt(np.maximum(variance, 0)),
                         np.hypot(sobel(gray, axis=0, mode="nearest"), sobel(gray, axis=1, mode="nearest")) / 8]
        if config.spatial:
            for window in config.spatial_windows:
                # 不沿通道维滤波，防止混淆 RGB。
                local = uniform_filter(rgb, size=(window, window, 1), mode="nearest")
                channels += [local[..., i] for i in range(3)]
        result = np.stack(channels, axis=-1).reshape(-1, schema["dimension"])
    result = np.ascontiguousarray(result, dtype=np.float32)
    if result.shape != (image.width * image.height, schema["dimension"]) or not np.isfinite(result).all():
        raise ValueError("特征形状异常或含 NaN/无穷值")
    return result


def iter_feature_bands(image: RGBImage, config: FeatureConfig = FeatureConfig(), *, band_height: int = 256):
    """逐条带返回 (起始行, 结束行, 中心特征矩阵)，避免截断邻域。"""
    _check_image(image)
    if type(band_height) is not int or band_height < 1:
        raise ValueError("band_height 必须为正整数")
    halo = feature_schema(config)["max_radius"]
    for start in range(0, image.height, band_height):
        end = min(start + band_height, image.height)
        top, bottom = max(0, start - halo), min(image.height, end + halo)
        band = RGBImage(image.width, bottom - top, image.pixels[top * image.width * 3:bottom * image.width * 3])
        features = extract_features(band, config).reshape(band.height, image.width, -1)
        yield start, end, features[start - top:end - top].reshape((end - start) * image.width, -1).copy()
