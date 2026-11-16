"""小麦叶片分割模块的独立测试程序。"""

import unittest

from wheat_phenotyping.leaf_segmentation import segment_leaves_exg
from wheat_phenotyping.rgb_preprocessing import RGBImage


class LeafSegmentationTest(unittest.TestCase):
    """验证 ExG 阈值判断和小连通域清理。"""

    def test_exg_separates_green_and_background(self):
        image = RGBImage(2, 1, bytes((20, 120, 20, 200, 200, 200)))
        mask = segment_leaves_exg(image, exg_threshold=20)
        self.assertEqual(mask.pixels, bytes((255, 0)))

    def test_removes_small_foreground_component(self):
        image = RGBImage(3, 1, bytes((10, 100, 10, 200, 200, 200, 10, 100, 10)))
        mask = segment_leaves_exg(image, exg_threshold=10, min_component_area=2)
        self.assertEqual(mask.pixels, bytes((0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
