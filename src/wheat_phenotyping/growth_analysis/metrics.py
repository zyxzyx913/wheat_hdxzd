"""可解释的单幅图像长势代理指标。

这些指标描述画面中可见植被，不等同于叶绿素、植株密度、生育期或农学长势等级。
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np
from scipy.ndimage import laplace

from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.rgb_preprocessing import RGBImage
from .vigor import assess_vigor


@dataclass(frozen=True)
class GrowthAnalysisConfig:
    """V1 可追溯的图像质量与空间网格参数；不是长势分类阈值。"""

    grid_rows: int = 4
    grid_cols: int = 4
    dark_brightness_threshold: float = 0.20
    overexposed_brightness_threshold: float = 0.90
    saturated_pixel_threshold: float = 250 / 255

    def __post_init__(self) -> None:
        if type(self.grid_rows) is not int or type(self.grid_cols) is not int or self.grid_rows < 1 or self.grid_cols < 1:
            raise ValueError("均匀度网格行列必须为正整数")
        if not (0 <= self.dark_brightness_threshold < self.overexposed_brightness_threshold <= 1):
            raise ValueError("亮度风险阈值必须满足 0 <= 过暗阈值 < 过曝阈值 <= 1")
        if not (0 < self.saturated_pixel_threshold <= 1):
            raise ValueError("过曝像素阈值必须位于 (0,1]")


def _rgb_array(image: RGBImage) -> np.ndarray:
    return np.frombuffer(image.pixels, dtype=np.uint8).reshape(image.height, image.width, 3)


def _mask_array(mask: BinaryMask) -> np.ndarray:
    values = np.frombuffer(mask.pixels, dtype=np.uint8).reshape(mask.height, mask.width)
    if not np.isin(values, (0, 255)).all():
        raise ValueError("分割掩膜只能包含 0 或 255")
    return values == 255


def _grid_coverages(foreground: np.ndarray, rows: int, cols: int) -> list[float]:
    """按整数边界切分网格；边界像素只归属于一个区域。"""
    height, width = foreground.shape
    result: list[float] = []
    for row in range(rows):
        y0, y1 = row * height // rows, (row + 1) * height // rows
        for col in range(cols):
            x0, x1 = col * width // cols, (col + 1) * width // cols
            cell = foreground[y0:y1, x0:x1]
            result.append(float(cell.mean()) if cell.size else 0.0)
    return result


def analyze_growth(
    image: RGBImage,
    mask: BinaryMask,
    *,
    task_id: str | None = None,
    algorithm: str = "unspecified",
    config: GrowthAnalysisConfig = GrowthAnalysisConfig(),
) -> dict[str, object]:
    """计算真实掩膜驱动的长势代理指标并返回可 JSON 序列化字典。"""
    if not isinstance(config, GrowthAnalysisConfig):
        raise TypeError("config 必须为 GrowthAnalysisConfig")
    if (image.width, image.height) != (mask.width, mask.height):
        raise ValueError("RGB 图像和分割掩膜尺寸必须一致，不会自动缩放")
    started = time.perf_counter()
    rgb = _rgb_array(image)
    foreground = _mask_array(mask)
    total = int(foreground.size)
    green_pixels = int(foreground.sum())
    coverage_fraction = green_pixels / total

    # 绿色程度仅定义为植被区域 G 通道相对 8 位上限的均值，不解释为叶绿素含量。
    green_degree = float(rgb[..., 1][foreground].mean() / 255.0) if green_pixels else None
    cell_coverages = _grid_coverages(foreground, config.grid_rows, config.grid_cols)
    coverage_mean = float(np.mean(cell_coverages)) if cell_coverages else 0.0
    coverage_std = float(np.std(cell_coverages)) if cell_coverages else 0.0
    uniformity_cv = coverage_std / coverage_mean if coverage_mean > 0 else None

    rgb_float = rgb.astype(np.float32) / 255.0
    gray = 0.299 * rgb_float[..., 0] + 0.587 * rgb_float[..., 1] + 0.114 * rgb_float[..., 2]
    brightness = float(gray.mean())
    dark_fraction = float((gray < config.dark_brightness_threshold).mean())
    overexposed_fraction = float((gray >= config.overexposed_brightness_threshold).mean())
    saturated_fraction = float((rgb.max(axis=2) >= config.saturated_pixel_threshold * 255).mean())
    sharpness = float(np.var(laplace(gray, mode="nearest")))
    risks: list[str] = []
    if brightness < config.dark_brightness_threshold or dark_fraction >= 0.30:
        risks.append("画面可能偏暗，颜色分割结果可能受影响")
    if brightness >= config.overexposed_brightness_threshold or overexposed_fraction >= 0.30:
        risks.append("画面可能过曝，细节和颜色区分可能受影响")
    if not green_pixels:
        risks.append("当前掩膜没有前景像素，不能据此判断小麦死亡或长势不良")
    if sharpness < 0.0005:
        risks.append("画面清晰度参考值偏低，细节和分割结果可能受影响")

    elapsed = time.perf_counter() - started
    result = {
        "status": "completed",
        "version": "growth-analysis-v1",
        "task_id": task_id,
        "algorithm": algorithm,
        "metrics": {
            "vegetation_coverage": {
                "vegetation_pixel_count": green_pixels,
                "valid_pixel_count": total,
                "fraction": coverage_fraction,
                "percentage": coverage_fraction * 100,
                "definition": "分割掩膜前景像素 / 有效图像像素；仅表示画面可见植被覆盖，不等同于长势等级",
            },
            "green_degree": {
                "mean_green_channel_ratio": green_degree,
                "percentage": None if green_degree is None else green_degree * 100,
                "definition": "分割前景区域 G 通道 / 255 的均值；不是叶绿素含量测量",
            },
            "distribution_uniformity": {
                "grid_rows": config.grid_rows,
                "grid_cols": config.grid_cols,
                "cell_coverage_fractions": cell_coverages,
                "mean_coverage_fraction": coverage_mean,
                "std_coverage_fraction": coverage_std,
                "coefficient_of_variation": uniformity_cv,
                "definition": "网格覆盖率的空间离散程度；不是田间真实植株密度",
            },
            "image_quality": {
                "width": image.width,
                "height": image.height,
                "sharpness_laplacian_variance": sharpness,
                "mean_brightness_ratio": brightness,
                "mean_brightness_percentage": brightness * 100,
                "dark_pixel_fraction": dark_fraction,
                "overexposed_pixel_fraction": overexposed_fraction,
                "saturated_pixel_fraction": saturated_fraction,
                "risk_flags": risks,
                "thresholds": {
                    "dark_brightness_threshold": config.dark_brightness_threshold,
                    "overexposed_brightness_threshold": config.overexposed_brightness_threshold,
                    "saturated_pixel_threshold": config.saturated_pixel_threshold,
                },
            },
        },
        "analysis_time_seconds": elapsed,
        "explanations": [
            "本结果由当前 RGB 图像和实际分割掩膜计算；V1.1 等级是可解释规则初评。",
            "绿色程度是 RGB 颜色代理指标，不是叶绿素、氮含量或生物量测量。",
        ],
        "limitations": [
            "单幅二维图像不能可靠确定生育期或未来生长趋势。",
            "覆盖率和均匀度受拍摄角度、遮挡、光照、背景和分割算法影响。",
            "等级阈值尚未经过专家标签和多生育期数据校准，不等同于农学诊断。",
        ],
    }
    result["vigor_assessment"] = assess_vigor(result["metrics"])
    return result
