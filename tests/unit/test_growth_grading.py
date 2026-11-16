"""可见长势特征和分级规则模块的独立测试程序。"""

import unittest

from wheat_phenotyping.leaf_segmentation import segment_leaves_exg
from wheat_phenotyping.phenotyping import (
    GrowthGradeThresholds,
    classify_visible_growth,
    extract_visible_growth_features,
)
from wheat_phenotyping.rgb_preprocessing import RGBImage


class GrowthGradingTest(unittest.TestCase):
    """检查图像可见特征汇总、阈值分类和维度校验。"""

    def test_extracts_features_and_applies_supplied_thresholds(self):
        image = RGBImage(2, 1, bytes((20, 120, 20, 200, 200, 200)))
        mask = segment_leaves_exg(image, exg_threshold=20)
        features = extract_visible_growth_features(image, mask)
        result = classify_visible_growth(
            features,
            GrowthGradeThresholds(weak_max_green_fraction=0.2, moderate_max_green_fraction=0.6),
            data_source="simulated",
        )
        self.assertEqual(result.grade, "中势")
        self.assertEqual(result.data_source, "simulated")
        self.assertAlmostEqual(features.green_area_fraction, 0.5)

    def test_rejects_mismatched_mask_dimensions(self):
        image = RGBImage(2, 1, bytes((1, 2, 3, 4, 5, 6)))
        mask = segment_leaves_exg(RGBImage(1, 1, bytes((1, 2, 3))), exg_threshold=0)
        with self.assertRaises(ValueError):
            extract_visible_growth_features(image, mask)

    def test_requires_ordered_thresholds(self):
        with self.assertRaises(ValueError):
            GrowthGradeThresholds(0.6, 0.2)


if __name__ == "__main__":
    unittest.main()
