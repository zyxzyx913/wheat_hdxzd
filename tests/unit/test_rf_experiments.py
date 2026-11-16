"""随机森林实验表与五算法汇总测试。"""

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "combine_ews_test_summaries.py"
SPEC = importlib.util.spec_from_file_location("combine_ews_test_summaries", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FiveAlgorithmSummaryTest(unittest.TestCase):
    """确保只汇总同一测试样本集且输出可读取的 CSV/SVG。"""

    def test_combines_matching_test_summaries(self):
        fields = [
            "algorithm_name", "dataset_name", "dataset_version", "split", "sample_count",
            "successful_count", "failed_count", "double_empty_count", "macro_f1_score", "std_f1_score",
        ]
        baseline_rows = [self._row(fields, name) for name in ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion")]
        rf_rows = [self._row(fields, "RF-Color-Texture")]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline.csv"
            rf = root / "rf.csv"
            baseline_images = root / "baseline_images.csv"
            rf_images = root / "rf_images.csv"
            self._write(baseline, fields, baseline_rows)
            self._write(rf, fields, rf_rows)
            self._write_images(baseline_images, 4)
            self._write_images(rf_images, 1)
            csv_path, svg_path = MODULE.combine(baseline, rf, baseline_images, rf_images, root / "out")
            with csv_path.open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 5)
            self.assertIn("RF-Color-Texture", {row["algorithm_name"] for row in rows})
            self.assertIn("macro F1", svg_path.read_text(encoding="utf-8"))

    def test_rejects_different_test_sample_counts(self):
        fields = [
            "algorithm_name", "dataset_name", "dataset_version", "split", "sample_count",
            "successful_count", "failed_count", "double_empty_count", "macro_f1_score", "std_f1_score",
        ]
        baseline_rows = [self._row(fields, name) for name in ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion")]
        rf = self._row(fields, "RF-Color-Texture")
        rf["sample_count"] = "23"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, rf_path = root / "baseline.csv", root / "rf.csv"
            self._write(baseline, fields, baseline_rows)
            self._write(rf_path, fields, [rf])
            baseline_images, rf_images = root / "baseline_images.csv", root / "rf_images.csv"
            self._write_images(baseline_images, 4)
            self._write_images(rf_images, 1)
            with self.assertRaisesRegex(ValueError, "样本数"):
                MODULE.combine(baseline, rf_path, baseline_images, rf_images, root / "out")

    def test_rejects_different_sample_ids(self):
        fields = [
            "algorithm_name", "dataset_name", "dataset_version", "split", "sample_count",
            "successful_count", "failed_count", "double_empty_count", "macro_f1_score", "std_f1_score",
        ]
        baseline_rows = [self._row(fields, name) for name in ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion")]
        rf = self._row(fields, "RF-Color-Texture")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, rf_path = root / "baseline.csv", root / "rf.csv"
            self._write(baseline, fields, baseline_rows)
            self._write(rf_path, fields, [rf])
            baseline_images, rf_images = root / "baseline_images.csv", root / "rf_images.csv"
            self._write_images(baseline_images, 4)
            self._write_images(rf_images, 1, alternate=True)
            with self.assertRaisesRegex(ValueError, "完全相同"):
                MODULE.combine(baseline, rf_path, baseline_images, rf_images, root / "out")

    @staticmethod
    def _row(fields, algorithm):
        row = dict.fromkeys(fields, "")
        row.update({
            "algorithm_name": algorithm, "dataset_name": "EWS", "dataset_version": "2021-11-30",
            "split": "test", "sample_count": "24", "successful_count": "24",
            "failed_count": "0", "double_empty_count": "0", "macro_f1_score": "0.7", "std_f1_score": "0.1",
        })
        return row

    @staticmethod
    def _write(path, fields, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_images(path, repeats, alternate=False):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["sample_id"])
            writer.writeheader()
            for _ in range(repeats):
                for index in range(24):
                    writer.writerow({"sample_id": f"sample-{index + (1 if alternate else 0)}"})


if __name__ == "__main__":
    unittest.main()
