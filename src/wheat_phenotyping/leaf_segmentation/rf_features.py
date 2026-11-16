"""用于像素级植被识别的颜色与局部纹理特征。"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import sobel, uniform_filter

from wheat_phenotyping.rgb_preprocessing import RGBImage


FEATURE_NAMES = (
    "red", "green", "blue", "excess_green", "local_gray_mean_5x5",
    "local_gray_std_5x5", "gray_gradient_magnitude",
)


def extract_pixel_features(image: RGBImage) -> np.ndarray:
    """生成逐像素 RGB、ExG、局部亮度统计和梯度特征。

    所有通道归一化至 0..1。局部特征只用当前图像的 5x5 邻域，
    边缘采用最近像素延拓，确保输出尺寸与输入一致。
    """
    rgb = np.frombuffer(image.pixels, dtype=np.uint8).reshape(image.height, image.width, 3)
    color = rgb.astype(np.float32) / 255.0
    red, green, blue = color[:, :, 0], color[:, :, 1], color[:, :, 2]
    gray = 0.299 * red + 0.587 * green + 0.114 * blue
    exg = np.clip(2.0 * green - red - blue, -2.0, 2.0) / 2.0
    local_mean = uniform_filter(gray, size=5, mode="nearest")
    local_square_mean = uniform_filter(gray * gray, size=5, mode="nearest")
    local_std = np.sqrt(np.maximum(local_square_mean - local_mean * local_mean, 0.0))
    gradient = np.hypot(sobel(gray, axis=0, mode="nearest"), sobel(gray, axis=1, mode="nearest")) / 8.0
    return np.stack((red, green, blue, exg, local_mean, local_std, gradient), axis=-1).reshape(-1, len(FEATURE_NAMES))
