"""随机森林颜色与局部纹理特征测试。"""

import unittest

import numpy as np

from wheat_phenotyping.leaf_segmentation.rf_features import FEATURE_NAMES, extract_pixel_features
from wheat_phenotyping.rgb_preprocessing import RGBImage


class RandomForestFeatureTest(unittest.TestCase):
    """检查特征形状、数值范围和重复运行一致性。"""

    def test_extracts_finite_seven_channel_pixel_features(self):
        # 左列为绿色植被，右列为棕色背景，验证每像素输出七个特征。
        image = RGBImage(2, 2, bytes((30, 180, 40, 130, 90, 40) * 2))
        first = extract_pixel_features(image)
        second = extract_pixel_features(image)
        self.assertEqual(first.shape, (4, len(FEATURE_NAMES)))
        self.assertTrue(np.isfinite(first).all())
        np.testing.assert_array_equal(first, second)

    def test_rejects_invalid_rgb_buffer_through_image_type(self):
        with self.assertRaises(ValueError):
            RGBImage(2, 2, b"short")


if __name__ == "__main__":
    unittest.main()
