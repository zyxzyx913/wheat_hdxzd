"""照片入口的算法调用回归测试。"""

import unittest
import csv
import json
from pathlib import Path
import tempfile

import joblib

from wheat_phenotyping.app.inference import ALGORITHM_NAMES, discover_images, predict_visible_mask, run_image_batch
from wheat_phenotyping.rgb_preprocessing import RGBImage, write_ppm


class PhotoAppInferenceTest(unittest.TestCase):
    def test_exg_inference_uses_common_mask_contract(self):
        image = RGBImage(2, 1, bytes((20, 200, 30, 150, 90, 40)))
        mask, metadata = predict_visible_mask(image, "ExG", parameters={"exg_threshold": 20, "min_component_area": 0})
        self.assertEqual((mask.width, mask.height), (2, 1))
        self.assertEqual(set(mask.pixels), {0, 255})
        self.assertEqual(metadata["algorithm"], "ExG")

    def test_all_four_traditional_algorithms_return_masks(self):
        image = RGBImage(2, 1, bytes((0, 255, 0, 100, 100, 200)))
        params = {
            "ExG": {"exg_threshold": 20, "min_component_area": 0},
            "HSV": {"hue_min": 55, "hue_max": 145, "saturation_min": 0.1, "saturation_max": 1.0, "value_min": 0.15, "value_max": 1.0},
            "Otsu-ExG": {},
            "ExG-HSV Fusion": {"exg_threshold": 0, "min_component_area": 0, "hue_min": 55, "hue_max": 145, "saturation_min": 0.1, "saturation_max": 1.0, "value_min": 0.05, "value_max": 1.0},
        }
        for name in ALGORITHM_NAMES[:4]:
            with self.subTest(algorithm=name):
                mask, metadata = predict_visible_mask(image, name, parameters=params[name])
                self.assertEqual((mask.width, mask.height), (2, 1))
                self.assertEqual(set(mask.pixels) - {0, 255}, set())
                self.assertEqual(metadata["algorithm"], name)

    def test_trained_model_accepts_uploaded_rgb_without_grade_output(self):
        root = Path(__file__).resolve().parents[2]
        model_path = root / "results" / "ews" / "rf_training" / "rf_color_texture.joblib"
        if not model_path.exists():
            self.skipTest("项目没有已训练的 EWS 随机森林模型")
        model = joblib.load(model_path)
        image = RGBImage(2, 2, bytes((20, 180, 40, 160, 100, 55, 30, 170, 35, 120, 80, 45)))
        mask, metadata = predict_visible_mask(image, "RF-Color-Texture", model=model)
        self.assertEqual((mask.width, mask.height), (2, 2))
        self.assertEqual(len(mask.pixels), 4)
        self.assertEqual(metadata["model_labels"], "1=live vegetation; 0=non-live/background")

    def test_discovers_single_and_folder_images_deterministically(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_ppm(RGBImage(1, 1, bytes((0, 255, 0))), root / "b.ppm")
            write_ppm(RGBImage(1, 1, bytes((0, 255, 0))), root / "a.ppm")
            self.assertEqual([path.name for path in discover_images(root)], ["a.ppm", "b.ppm"])
            self.assertEqual(discover_images(root / "b.ppm"), [root / "b.ppm"])

    def test_batch_saves_masks_overlays_and_per_image_status_without_stopping_on_bad_image(self):
        local_temp = Path.cwd() / ".test-tmp"
        local_temp.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local_temp) as folder:
            root = Path(folder)
            source, output = root / "input", root / "output"
            source.mkdir()
            write_ppm(RGBImage(2, 1, bytes((0, 255, 0, 100, 100, 200))), source / "good.ppm")
            (source / "bad.ppm").write_bytes(b"not a ppm")
            params = {
                "ExG": {"exg_threshold": 20, "min_component_area": 0},
                "HSV": {"hue_min": 55, "hue_max": 145, "saturation_min": 0.1, "saturation_max": 1.0, "value_min": 0.15, "value_max": 1.0},
                "Otsu-ExG": {},
                "ExG-HSV Fusion": {"exg_threshold": 0, "min_component_area": 0, "hue_min": 55, "hue_max": 145, "saturation_min": 0.1, "saturation_max": 1.0, "value_min": 0.05, "value_max": 1.0},
            }
            image_paths = discover_images(source)
            rows = run_image_batch(image_paths, list(ALGORITHM_NAMES[:4]), output,
                                   algorithm_parameters=params, source_root=source)
            self.assertEqual(len(rows), 8)
            self.assertEqual(sum(row["status"] == "ok" for row in rows), 4)
            self.assertTrue(all(Path(row["mask_path"]).exists() and Path(row["overlay_path"]).exists() for row in rows if row["status"] == "ok"))
            with (output / "image_results.csv").open(encoding="utf-8-sig", newline="") as stream:
                self.assertEqual(len(list(csv.DictReader(stream))), 8)
            summary = json.loads((output / "run_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["failed_count"], 4)


if __name__ == "__main__":
    unittest.main()
