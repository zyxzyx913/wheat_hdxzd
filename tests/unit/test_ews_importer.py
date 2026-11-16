"""EWS 原始标签解释和 PGM 转换测试。"""

import importlib.util
import io
import unittest
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMPORTER_PATH = PROJECT_ROOT / "scripts" / "import_ews_dataset.py"
SPEC = importlib.util.spec_from_file_location("import_ews_dataset", IMPORTER_PATH)
assert SPEC is not None and SPEC.loader is not None
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


class EWSMaskConversionTest(unittest.TestCase):
    """确认官方 LA 掩膜的反色规则和 PGM 二值格式。"""

    def test_converts_inverted_luminance_without_resizing(self):
        # 低灰度按官方反色编码映射为活体前景 1，高灰度映射为背景 0。
        original = Image.new("LA", (4, 1))
        original.putdata([(0, 255), (127, 255), (128, 255), (255, 255)])
        buffer = io.BytesIO()
        original.save(buffer, format="PNG")

        source, pixels, details = IMPORTER._read_official_mask(buffer.getvalue())

        self.assertEqual(source.size, (4, 1))
        self.assertEqual(source.mode, "LA")
        self.assertEqual(pixels, bytes((1, 1, 0, 0)))
        self.assertEqual(details["live_vegetation_pixels"], 2)
        self.assertEqual(details["non_live_or_background_pixels"], 2)

    def test_writes_p5_with_background_zero_and_foreground_one(self):
        pgm = IMPORTER._pgm_p5(2, 2, bytes((0, 1, 1, 0)))
        header, pixels = pgm.split(b"\n", 3)[:3], pgm.split(b"\n", 3)[3]
        self.assertEqual(header, [b"P5", b"2 2", b"1"])
        self.assertEqual(pixels, bytes((0, 1, 1, 0)))

    def test_rejects_nonbinary_pgm_pixels(self):
        with self.assertRaisesRegex(ValueError, "只能包含 0 和 1"):
            IMPORTER._pgm_p5(1, 1, bytes((255,)))

    def test_rejects_unexpected_source_mask_mode(self):
        buffer = io.BytesIO()
        Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
        with self.assertRaisesRegex(ValueError, "不支持的 EWS 掩膜模式"):
            IMPORTER._read_official_mask(buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
