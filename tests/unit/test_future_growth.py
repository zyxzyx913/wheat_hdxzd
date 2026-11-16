"""未来预测数据结构测试；不代表真实预测成绩。"""
from datetime import date

import pytest

from wheat_phenotyping.future_growth.feature_builder import build_feature_vector
from wheat_phenotyping.future_growth.temporal_dataset import build_temporal_samples, validate_group_isolation
from wheat_phenotyping.future_growth.validation import regression_metrics


def test_feature_builder_uses_only_finite_current_metrics():
    record = {"growth_analysis": {"metrics": {"vegetation_coverage": {"fraction": 0.5}, "green_degree": {"mean_green_channel_ratio": 0.7}, "distribution_uniformity": {"coefficient_of_variation": None}, "image_quality": {"mean_brightness_ratio": 0.4}}, "vigor_assessment": {"vigor_score": 55}}}
    assert build_feature_vector(record) == {"vegetation_coverage": 0.5, "greenness": 0.7, "mean_brightness": 0.4, "vigor_score_rule": 55.0}


def test_temporal_samples_match_future_observations_within_order():
    records = [
        {"plot_id": "p1", "year": 2024, "capture_date": date(2024, 1, 1), "features": {"x": 1}, "target_values": {"coverage": 0.2}},
        {"plot_id": "p1", "year": 2024, "capture_date": date(2024, 1, 9), "target_values": {"coverage": 0.3}},
    ]
    samples = build_temporal_samples(records, horizons=(7,))
    assert samples[0].targets[7]["coverage"] == 0.3


def test_group_isolation_rejects_overlap():
    with pytest.raises(ValueError, match="重叠"):
        validate_group_isolation([{"plot_id": "p1", "year": 2024}], [{"plot_id": "p1", "year": 2024}])


def test_regression_metrics_are_real():
    result = regression_metrics([1, 2, 3], [1, 3, 2])
    assert result["mae"] == pytest.approx(2 / 3)
    assert result["rmse"] == pytest.approx((2 / 3) ** 0.5)
