"""分割错误区域叠加可视化测试。"""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.rgb_preprocessing import RGBImage
from wheat_phenotyping.visualization import create_segmentation_overlay, write_segmentation_overlay


class SegmentationOverlayTest(unittest.TestCase):
    def test_true_positive_false_positive_false_negative_and_true_negative_colors(self):
        image = RGBImage(4, 1, bytes((10, 10, 10) * 4))
        reference = BinaryMask(4, 1, bytes((255, 0, 255, 0)))
        prediction = BinaryMask(4, 1, bytes((255, 255, 0, 0)))
        result = create_segmentation_overlay(image, reference, prediction, alpha=1.0)
        self.assertEqual(result.pixels, bytes((0, 220, 0, 255, 40, 40, 40, 100, 255, 10, 10, 10)))

    def test_rejects_bad_alpha_and_mismatched_dimensions(self):
        image = RGBImage(1, 1, bytes((1, 2, 3)))
        mask = BinaryMask(1, 1, b"\0")
        with self.assertRaises(ValueError):
            create_segmentation_overlay(image, mask, mask, alpha=2)
        with self.assertRaises(ValueError):
            create_segmentation_overlay(image, BinaryMask(2, 1, b"\0\0"), mask)

    def test_writes_png_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = write_segmentation_overlay(
                RGBImage(1, 1, bytes((30, 40, 50))),
                BinaryMask(1, 1, b"\xff"),
                BinaryMask(1, 1, b"\xff"),
                Path(directory) / "overlay.png",
                alpha=1,
            )
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.getpixel((0, 0)), (0, 220, 0))


if __name__ == "__main__":
    unittest.main()
