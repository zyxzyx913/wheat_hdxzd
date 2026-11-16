"""RGB 图像预处理模块的独立测试程序。"""

import tempfile
import unittest
from pathlib import Path

from wheat_phenotyping.rgb_preprocessing import RGBImage, preprocess_rgb, read_ppm, write_ppm


class RGBPreprocessingTest(unittest.TestCase):
    """检查 PPM 读写、尺寸变换和输入边界。"""

    def test_ppm_round_trip_and_resize(self):
        image = RGBImage(2, 1, bytes((10, 20, 30, 40, 50, 60)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.ppm"
            write_ppm(image, path)
            self.assertEqual(read_ppm(path), image)
        enlarged = preprocess_rgb(image, max_size=1)
        self.assertEqual((enlarged.width, enlarged.height), (1, 1))

    def test_rejects_invalid_image_buffer(self):
        with self.assertRaises(ValueError):
            RGBImage(2, 2, b"short")


if __name__ == "__main__":
    unittest.main()
