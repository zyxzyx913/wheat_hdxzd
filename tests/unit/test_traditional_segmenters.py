"""四种传统 RGB 分割算法和统一注册接口的单元测试。"""

import tempfile
import unittest
from pathlib import Path

from wheat_phenotyping.evaluation import EvaluationSample, evaluate_batch, read_binary_pgm
from wheat_phenotyping.leaf_segmentation import (
    DEFAULT_REGISTRY,
    BinaryMask,
    SegmenterRegistry,
    create_default_registry,
    otsu_threshold,
    segment_exg_hsv_fusion,
    segment_hsv,
    segment_leaves_exg,
    segment_otsu_exg,
    segment_otsu_exg_with_threshold,
)
from wheat_phenotyping.rgb_preprocessing import RGBImage


def hsv_parameters() -> dict[str, float]:
    return {
        "hue_min": 60.0, "hue_max": 180.0,
        "saturation_min": 0.2, "saturation_max": 1.0,
        "value_min": 0.1, "value_max": 1.0,
    }


class TraditionalSegmenterTest(unittest.TestCase):
    """覆盖典型颜色、边界图像和算法参数校验。"""

    def test_hsv_green_and_different_background_colors(self):
        image = RGBImage(4, 1, bytes((0, 255, 0, 180, 120, 20, 20, 30, 180, 245, 245, 245)))
        mask = segment_hsv(image, hsv_parameters())
        self.assertEqual(mask.pixels, bytes((255, 0, 0, 0)))

    def test_hsv_accepts_hue_range_wrapping_zero(self):
        image = RGBImage(2, 1, bytes((255, 0, 0, 0, 255, 0)))
        params = {"hue_min": 300, "hue_max": 30, "saturation_min": .9,
                  "saturation_max": 1, "value_min": .9, "value_max": 1}
        self.assertEqual(segment_hsv(image, params).pixels, bytes((255, 0)))

    def test_hsv_requires_explicit_valid_parameters(self):
        image = RGBImage(1, 1, bytes((0, 255, 0)))
        with self.assertRaises(ValueError):
            segment_hsv(image, {})
        params = hsv_parameters()
        params["value_min"] = 1.2
        with self.assertRaises(ValueError):
            segment_hsv(image, params)

    def test_otsu_exg_bimodal_and_records_computed_threshold(self):
        image = RGBImage(4, 1, bytes((100, 100, 200, 100, 100, 200, 20, 180, 20, 20, 180, 20)))
        prediction, threshold = segment_otsu_exg_with_threshold(image)
        self.assertIsInstance(segment_otsu_exg(image), BinaryMask)
        self.assertLess(threshold, 320)
        self.assertGreaterEqual(threshold, -100)
        self.assertEqual(prediction.pixels, bytes((0, 0, 255, 255)))

    def test_otsu_constant_images_have_documented_deterministic_output(self):
        green = RGBImage(3, 2, bytes((0, 255, 0) * 6))
        dark = RGBImage(3, 2, bytes(18))
        green_mask, green_threshold = segment_otsu_exg_with_threshold(green)
        dark_mask, dark_threshold = segment_otsu_exg_with_threshold(dark)
        self.assertEqual(green_mask.pixels, bytes((255,) * 6))
        self.assertEqual(green_threshold, 509)
        self.assertEqual(dark_mask.pixels, bytes(6))
        self.assertEqual(dark_threshold, 0)
        with self.assertRaises(ValueError):
            otsu_threshold([])

    def test_fusion_uses_exg_and_hsv_intersection(self):
        # 第一像素为绿色；第二像素有正 ExG，但色相不在配置区间。
        image = RGBImage(2, 1, bytes((0, 255, 0, 200, 220, 0)))
        hsv_params = hsv_parameters()
        hsv_params["hue_min"] = 75.0
        params = {"exg_threshold": 20, **hsv_params}
        fused = segment_exg_hsv_fusion(image, params)
        self.assertEqual(fused.pixels, bytes((255, 0)))
        with self.assertRaises(ValueError):
            segment_exg_hsv_fusion(image, {"exg_threshold": 20})

    def test_empty_and_single_pixel_images(self):
        black = RGBImage(1, 1, bytes((0, 0, 0)))
        self.assertEqual(segment_leaves_exg(black, exg_threshold=1).pixels, b"\0")
        self.assertEqual(segment_hsv(black, hsv_parameters()).pixels, b"\0")
        self.assertEqual(segment_exg_hsv_fusion(black, {"exg_threshold": 1, **hsv_parameters()}).pixels, b"\0")

    def test_image_size_validation_and_all_green_hsv(self):
        with self.assertRaises(ValueError):
            RGBImage(2, 2, bytes((0, 255, 0)))
        image = RGBImage(2, 2, bytes((0, 255, 0) * 4))
        self.assertEqual(segment_hsv(image, hsv_parameters()).pixels, bytes((255,) * 4))


class SegmenterRegistryTest(unittest.TestCase):
    """检查算法注册、参数映射和四算法统一调用。"""

    def test_default_registry_contains_four_algorithms(self):
        self.assertEqual(DEFAULT_REGISTRY.names(), ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion"))
        registry = create_default_registry()
        with self.assertRaises(KeyError):
            registry.get("missing")
        with self.assertRaises(ValueError):
            registry.register("ExG", lambda image, params: None)
        with self.assertRaises(ValueError):
            SegmenterRegistry().register(" padded ", lambda image, params: None)

    def test_all_algorithms_return_common_mask_and_otsu_metadata(self):
        image = RGBImage(2, 1, bytes((0, 255, 0, 100, 100, 200)))
        parameters = {
            "ExG": {"exg_threshold": 20},
            "HSV": hsv_parameters(),
            "Otsu-ExG": {},
            "ExG-HSV Fusion": {"exg_threshold": 20, **hsv_parameters()},
        }
        registry = create_default_registry()
        outputs = {name: registry.run(name, image, params) for name, params in parameters.items()}
        self.assertTrue(all(isinstance(output.mask, BinaryMask) for output in outputs.values()))
        self.assertIn("computed_exg_threshold", outputs["Otsu-ExG"].metadata)
        self.assertEqual(outputs["ExG-HSV Fusion"].metadata["fusion_rule"], "ExG threshold AND HSV range")

    def test_four_algorithms_run_through_same_evaluator_and_reference(self):
        local_temp = Path.cwd() / ".test-tmp"
        local_temp.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local_temp) as directory:
            root = Path(directory)
            image_path, mask_path = root / "sample.ppm", root / "sample.pgm"
            image_path.write_bytes(b"P6\n2 1\n255\n" + bytes((0, 255, 0, 100, 100, 200)))
            mask_path.write_bytes(b"P5\n2 1\n255\n" + bytes((255, 0)))
            sample = EvaluationSample("sample-1", "unit", "v1", "validation", image_path, mask_path, "simulated")

            def predictor(image_file, params):
                # 通过统一 registry 调用；各算法读取同一份输入图像。
                from wheat_phenotyping.rgb_preprocessing import read_ppm
                return DEFAULT_REGISTRY.run(params["algorithm"], read_ppm(image_file), params["parameters"])

            names_and_params = {
                "ExG": {"algorithm": "ExG", "parameters": {"exg_threshold": 20}},
                "HSV": {"algorithm": "HSV", "parameters": hsv_parameters()},
                "Otsu-ExG": {"algorithm": "Otsu-ExG", "parameters": {}},
                "ExG-HSV Fusion": {"algorithm": "ExG-HSV Fusion", "parameters": {"exg_threshold": 20, **hsv_parameters()}},
            }
            results = evaluate_batch([sample], {name: predictor for name in names_and_params},
                                     parameters=names_and_params, selected_split="validation")
            self.assertEqual(len(results), 4)
            self.assertTrue(all(row.status == "ok" for row in results))
            otsu_row = next(row for row in results if row.algorithm_name == "Otsu-ExG")
            self.assertIn("computed_exg_threshold", otsu_row.algorithm_metadata_json)
            self.assertTrue(all(row.reference_mask_path == str(mask_path) for row in results))


if __name__ == "__main__":
    unittest.main()
