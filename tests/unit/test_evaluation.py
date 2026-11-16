"""分割评价模块完整单元测试。"""

import csv
import tempfile
import unittest
from pathlib import Path

from wheat_phenotyping.evaluation import (
    EvaluationSample,
    evaluate_batch,
    evaluate_binary_masks,
    read_binary_pgm,
    summarize_by_dataset,
    write_evaluation_outputs,
)
from wheat_phenotyping.leaf_segmentation import BinaryMask


def write_pgm(path: Path, width: int, height: int, pixels: bytes) -> None:
    path.write_bytes(f"P5\n{width} {height}\n255\n".encode("ascii") + pixels)


class SegmentationMetricTest(unittest.TestCase):
    """使用手工可验证像素计数核对四项分割指标。"""

    def test_metrics_from_confusion_counts(self):
        predicted = BinaryMask(4, 1, bytes((255, 255, 0, 0)))
        reference = BinaryMask(4, 1, bytes((255, 0, 255, 0)))
        metrics = evaluate_binary_masks(predicted, reference)
        self.assertEqual((metrics.true_positive, metrics.false_positive, metrics.false_negative, metrics.true_negative), (1, 1, 1, 1))
        self.assertAlmostEqual(metrics.iou, 1 / 3)
        self.assertAlmostEqual(metrics.precision, 1 / 2)
        self.assertAlmostEqual(metrics.recall, 1 / 2)
        self.assertAlmostEqual(metrics.f1_score, 1 / 2)

    def test_empty_mask_conventions(self):
        empty = BinaryMask(2, 2, bytes(4))
        full = BinaryMask(2, 2, bytes((255,) * 4))
        self.assertEqual((evaluate_binary_masks(empty, empty).iou,
                          evaluate_binary_masks(empty, empty).precision,
                          evaluate_binary_masks(empty, empty).recall,
                          evaluate_binary_masks(empty, empty).f1_score), (1, 1, 1, 1))
        wrong = evaluate_binary_masks(empty, full)
        self.assertEqual((wrong.iou, wrong.precision, wrong.recall, wrong.f1_score), (0, 0, 0, 0))

    def test_rejects_different_sizes(self):
        with self.assertRaises(ValueError):
            evaluate_binary_masks(BinaryMask(1, 1, b"\0"), BinaryMask(2, 1, b"\0\0"))

    def test_reads_binary_and_ascii_pgm_and_rejects_invalid_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "binary.pgm"
            write_pgm(binary, 2, 1, bytes((0, 255)))
            self.assertEqual(read_binary_pgm(binary).pixels, bytes((0, 255)))
            ascii_mask = root / "ascii.pgm"
            ascii_mask.write_text("P2\n# label\n2 1\n1\n0 1\n", encoding="ascii")
            self.assertEqual(read_binary_pgm(ascii_mask).pixels, bytes((0, 255)))
            invalid = root / "invalid.pgm"
            invalid.write_text("P2\n2 1\n255\n0 127\n", encoding="ascii")
            with self.assertRaises(ValueError):
                read_binary_pgm(invalid)


class SegmentationBatchTest(unittest.TestCase):
    """验证批处理、固定数据划分、逐图计时和实验产物。"""

    def _samples(self, root: Path) -> list[EvaluationSample]:
        samples = []
        for name, split, size in (("a", "validation", (2, 1)), ("b", "validation", (3, 1)), ("c", "test", (2, 2))):
            image = root / f"{name}.ppm"
            mask = root / f"{name}.pgm"
            width, height = size
            image.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + bytes([100, 150, 50] * width * height))
            write_pgm(mask, width, height, bytes(255 if index % 2 == 0 else 0 for index in range(width * height)))
            samples.append(EvaluationSample(name, "dataset-A", "v1", split, image, mask, "public"))
        return samples

    def test_batch_processes_variable_sizes_and_summarizes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            samples = self._samples(root)

            def perfect(sample_path, parameters):
                sample = next(row for row in samples if row.image_path == sample_path)
                return read_binary_pgm(sample.reference_mask_path)

            def empty(sample_path, parameters):
                sample = next(row for row in samples if row.image_path == sample_path)
                reference = read_binary_pgm(sample.reference_mask_path)
                return BinaryMask(reference.width, reference.height, bytes(reference.width * reference.height))

            results = evaluate_batch(
                samples,
                {"perfect": perfect, "empty": empty},
                parameters={"perfect": {"mode": "copy"}, "empty": {"mode": "none"}},
                selected_split="validation",
            )
            self.assertEqual(len(results), 4)
            self.assertTrue(all(row.split == "validation" for row in results))
            self.assertTrue(all(row.runtime_seconds is not None and row.runtime_seconds >= 0
                                for row in results if row.status == "ok"))
            self.assertEqual(next(row for row in results if row.algorithm_name == "perfect" and row.sample_id == "a").metrics.iou, 1.0)
            summary = summarize_by_dataset(results)
            self.assertEqual(len(summary), 2)
            perfect_summary = next(row for row in summary if row["algorithm_name"] == "perfect")
            self.assertEqual(perfect_summary["successful_count"], 2)
            self.assertEqual(perfect_summary["macro_f1_score"], 1.0)
            outputs = write_evaluation_outputs(results, root / "results", parameters_frozen=True)
            for output in outputs.values():
                self.assertTrue(output.is_file())
            with outputs["image_csv"].open(encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            self.assertIn("experiment_time_utc", rows[0])
            self.assertIn("perfect", outputs["chart_svg"].read_text(encoding="utf-8"))

    def test_test_split_requires_frozen_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            samples = self._samples(Path(directory))
            predictor = lambda path, params: BinaryMask(2, 2, bytes((255, 0, 255, 0)))
            with self.assertRaises(ValueError):
                evaluate_batch(samples, {"noop": predictor},
                               parameters={"noop": {}}, selected_split="test")
            with self.assertRaises(ValueError):
                evaluate_batch(samples, {"noop": predictor}, parameters={"noop": {"threshold": 4}},
                               selected_split="test", parameters_frozen=True,
                               frozen_parameters={"noop": {"threshold": 3}})
            final = evaluate_batch(samples, {"noop": predictor}, parameters={"noop": {"threshold": 3}},
                                   selected_split="test", parameters_frozen=True,
                                   frozen_parameters={"noop": {"threshold": 3}})
            self.assertEqual(final[0].status, "ok")

    def test_invalid_reference_and_predictor_error_are_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = self._samples(root)[0]
            invalid = root / "invalid.pgm"
            invalid.write_text("P2\n2 1\n255\n0 123\n", encoding="ascii")
            bad_sample = EvaluationSample(sample.sample_id, sample.dataset_name, sample.dataset_version,
                                          sample.split, sample.image_path, invalid, sample.data_source)
            result = evaluate_batch([bad_sample], {"algo": lambda path, params: BinaryMask(1, 1, b"\0")},
                                    parameters={"algo": {}}, selected_split="validation")[0]
            self.assertEqual(result.status, "invalid_reference")
            self.assertIsNone(result.metrics)
            self.assertIn("无效人工标签", result.error)

            mismatch = evaluate_batch([sample], {"algo": lambda path, params: BinaryMask(1, 1, b"\0")},
                                      parameters={"algo": {}}, selected_split="validation")[0]
            self.assertEqual(mismatch.status, "error")
            self.assertIn("尺寸不一致", mismatch.error)

    def test_invalid_split_and_unmatched_split_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            samples = self._samples(Path(directory))
            with self.assertRaises(ValueError):
                evaluate_batch(samples, {"algo": lambda path, params: BinaryMask(1, 1, b"\0")},
                               parameters={"algo": {}}, selected_split="all")
            with self.assertRaises(ValueError):
                evaluate_batch(samples, {"algo": lambda path, params: BinaryMask(1, 1, b"\0")},
                               parameters={"algo": {}}, selected_split="train")

    def test_summary_counts_double_empty_and_excludes_from_macro(self):
        local_temp = Path.cwd() / ".test-tmp"
        local_temp.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=local_temp) as directory:
            root = Path(directory)
            samples = []
            for name, values in (("empty", bytes(2)), ("plant", bytes((255, 0)))):
                image, mask = root / f"{name}.ppm", root / f"{name}.pgm"
                image.write_bytes(b"P6\n2 1\n255\n" + bytes((10, 20, 30) * 2))
                write_pgm(mask, 2, 1, values)
                samples.append(EvaluationSample(name, "labels", "v2", "validation", image, mask))

            def empty_predictor(path, params):
                return BinaryMask(2, 1, bytes(2))

            rows = evaluate_batch(samples, {"empty-model": empty_predictor}, parameters={"empty-model": {}},
                                  selected_split="validation")
            summary = summarize_by_dataset(rows)[0]
            self.assertEqual(summary["double_empty_count"], 1)
            self.assertEqual(summary["nonempty_scored_count"], 1)
            self.assertEqual(summary["macro_f1_score"], 0.0)
            self.assertEqual(summary["std_f1_score"], 0.0)

    def test_all_double_empty_group_has_no_pooled_foreground_score(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image, mask = root / "empty.ppm", root / "empty.pgm"
            image.write_bytes(b"P6\n1 1\n255\n\x00\x00\x00")
            write_pgm(mask, 1, 1, b"\x00")
            sample = EvaluationSample("empty", "empty-set", "v1", "validation", image, mask)
            rows = evaluate_batch([sample], {"empty": lambda path, params: BinaryMask(1, 1, b"\x00")},
                                  parameters={"empty": {}}, selected_split="validation")
            summary = summarize_by_dataset(rows)[0]
            self.assertEqual(summary["double_empty_count"], 1)
            self.assertIsNone(summary["macro_iou"])
            self.assertIsNone(summary["pooled_iou"])


if __name__ == "__main__":
    unittest.main()
