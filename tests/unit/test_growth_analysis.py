"""长势初步分析 V1 指标测试；所有图像均为程序生成夹具，不代表真实实验。"""

import numpy as np
import pytest

from wheat_phenotyping.growth_analysis import GrowthAnalysisConfig, VigorAssessmentConfig, analyze_growth, assess_vigor
from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.rgb_preprocessing import RGBImage


def pair(width=4, height=4, mask=None, pixel=(10, 100, 20)):
    image = RGBImage(width, height, bytes(pixel) * (width * height))
    values = mask or [0] * (width * height)
    return image, BinaryMask(width, height, bytes(values))


def test_coverage_green_degree_and_uniformity_are_real_values():
    mask = [255, 255, 0, 0, 255, 255, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    image, binary = pair(mask=mask, pixel=(10, 100, 20))
    result = analyze_growth(image, binary, task_id="task", algorithm="ExG", config=GrowthAnalysisConfig(grid_rows=2, grid_cols=2))
    metrics = result["metrics"]
    assert metrics["vegetation_coverage"]["vegetation_pixel_count"] == 4
    assert metrics["vegetation_coverage"]["percentage"] == 25.0
    assert metrics["green_degree"]["mean_green_channel_ratio"] == pytest.approx(100 / 255)
    assert metrics["distribution_uniformity"]["cell_coverage_fractions"] == [1, 0, 0, 0]
    assert metrics["distribution_uniformity"]["coefficient_of_variation"] == pytest.approx(np.sqrt(3))
    assert result["task_id"] == "task" and result["algorithm"] == "ExG"


def test_empty_mask_has_no_green_degree_and_no_fake_grade():
    image, mask = pair(pixel=(0, 0, 0))
    result = analyze_growth(image, mask)
    assert result["metrics"]["vegetation_coverage"]["percentage"] == 0
    assert result["metrics"]["green_degree"]["mean_green_channel_ratio"] is None
    assert result["metrics"]["distribution_uniformity"]["coefficient_of_variation"] is None
    assert any("不能据此判断" in item for item in result["metrics"]["image_quality"]["risk_flags"])
    assert not any(key in result for key in ("grade", "growth_grade", "stage", "prediction"))


def test_quality_metrics_detect_dark_and_overexposed_images():
    dark, mask = pair(pixel=(0, 0, 0))
    bright = RGBImage(4, 4, bytes((255, 255, 255)) * 16)
    dark_result = analyze_growth(dark, mask)
    bright_result = analyze_growth(bright, mask)
    assert dark_result["metrics"]["image_quality"]["mean_brightness_ratio"] == 0
    assert any("偏暗" in item for item in dark_result["metrics"]["image_quality"]["risk_flags"])
    assert bright_result["metrics"]["image_quality"]["mean_brightness_ratio"] == 1
    assert any("过曝" in item for item in bright_result["metrics"]["image_quality"]["risk_flags"])


def test_rgb_channel_order_is_green_channel_not_red_or_blue():
    image = RGBImage(2, 1, bytes((200, 10, 20, 20, 180, 30)))
    mask = BinaryMask(2, 1, bytes((255, 255)))
    result = analyze_growth(image, mask)
    assert result["metrics"]["green_degree"]["mean_green_channel_ratio"] == pytest.approx(95 / 255)


def test_size_mismatch_and_invalid_mask_are_rejected():
    image, _ = pair()
    with pytest.raises(ValueError, match="尺寸"):
        analyze_growth(image, BinaryMask(2, 2, bytes([0] * 4)))
    with pytest.raises(ValueError, match="0"):
        analyze_growth(image, BinaryMask(4, 4, bytes([2] * 16)))
    with pytest.raises(ValueError, match="网格"):
        analyze_growth(image, BinaryMask(4, 4, bytes([0] * 16)), config=GrowthAnalysisConfig(grid_rows=0))


@pytest.mark.parametrize("config", [GrowthAnalysisConfig(grid_rows=1, grid_cols=3), GrowthAnalysisConfig(grid_rows=5, grid_cols=2)])
def test_grid_configuration_covers_all_pixels(config):
    image, mask = pair(width=7, height=5, mask=[255] * 35)
    result = analyze_growth(image, mask, config=config)
    values = result["metrics"]["distribution_uniformity"]["cell_coverage_fractions"]
    assert len(values) == config.grid_rows * config.grid_cols
    assert values == [1.0] * len(values)


def test_vigor_rule_returns_traceable_scores_and_contributions():
    image, mask = pair(width=4, height=4, mask=[255] * 16, pixel=(20, 200, 30))
    result = analyze_growth(image, mask)
    vigor = result["vigor_assessment"]
    assert vigor["evaluation_version"] == "growth-vigor-v1.1-rule"
    assert vigor["vigor_level"] == "长势较好"
    assert 0 <= vigor["vigor_score"] <= 100
    assert abs(sum(vigor["scoring"]["contributions"].values()) - vigor["vigor_score"]) < 1e-9
    assert vigor["scoring"]["weights"] == {"coverage": 0.45, "greenness": 0.35, "uniformity": 0.2}


def test_vigor_rule_with_dark_image_withholds_grade():
    image, mask = pair(width=4, height=4, mask=[255] * 16, pixel=(5, 5, 5))
    vigor = analyze_growth(image, mask)["vigor_assessment"]
    assert vigor["vigor_level"] is None
    assert vigor["reliability"] == "较低"
    assert vigor["quality_blocking_reasons"]
    assert vigor["improvement_suggestions"]


def test_vigor_config_rejects_non_normalized_weights():
    with pytest.raises(ValueError, match="权重"):
        VigorAssessmentConfig(coverage_weight=0.5, greenness_weight=0.5, uniformity_weight=0.5)
