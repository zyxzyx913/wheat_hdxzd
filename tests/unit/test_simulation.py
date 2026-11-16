"""模拟数据生成模块的独立测试程序。"""

import json
import tempfile
import unittest
from pathlib import Path

from wheat_phenotyping.simulation import SimulationConfig, generate_sample


class SimulationGeneratorTest(unittest.TestCase):
    """验证生成文件、真值标签和参数边界。"""

    def test_generates_rgb_mask_point_cloud_and_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            truth = generate_sample(
                directory,
                SimulationConfig(seed=13, leaf_count=3, points_per_leaf=12),
            )
            sample_dir = Path(directory)
            for name in ("rgb.ppm", "leaf_mask.pgm", "point_cloud.csv", "ground_truth.json", "generation_parameters.json"):
                self.assertTrue((sample_dir / name).is_file(), name)
            self.assertEqual(truth["data_source"], "simulated")
            self.assertEqual(truth["plant"]["leaf_count"], 3)
            saved = json.loads((sample_dir / "ground_truth.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["point_count_after_missing"], 36)

    def test_rejects_invalid_missing_fraction(self):
        with self.assertRaises(ValueError):
            SimulationConfig(missing_point_fraction=1.0).validate()


if __name__ == "__main__":
    unittest.main()
