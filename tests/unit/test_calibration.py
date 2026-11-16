"""参数校准模块的 split 限制、候选选择和参数快照测试。"""

import json
import tempfile
import unittest
from pathlib import Path

from wheat_phenotyping.evaluation import (
    EvaluationSample,
    calibrate_candidates,
    write_calibration_outputs,
)
from wheat_phenotyping.leaf_segmentation import BinaryMask


class CalibrationTest(unittest.TestCase):
    def _samples(self, root: Path):
        rows = []
        for sample_id, split, gt in (("v", "validation", bytes((255, 0))), ("t", "test", bytes((0, 255)))):
            image, mask = root / f"{sample_id}.ppm", root / f"{sample_id}.pgm"
            image.write_bytes(b"P6\n2 1\n255\n" + bytes(6))
            mask.write_bytes(b"P5\n2 1\n255\n" + gt)
            rows.append(EvaluationSample(sample_id, "test-set", "v1", split, image, mask))
        return rows

    def test_selects_candidate_on_validation_and_writes_freezable_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            samples = self._samples(root)

            def predictor(path, parameters):
                if path.stem == "t":
                    raise AssertionError("calibration must not read test images")
                if parameters["cutoff"] == 1:
                    return BinaryMask(2, 1, bytes((255, 0)))
                return BinaryMask(2, 1, bytes(2))

            result = calibrate_candidates(
                samples,
                {"ExG": predictor},
                {"ExG": [{"cutoff": 0}, {"cutoff": 1}]},
                selected_split="validation",
                selection_metric="f1_score",
            )
            self.assertEqual(result.selected_parameters["ExG"], {"cutoff": 1})
            self.assertEqual([row.score for row in result.candidate_scores], [0, 1])
            paths = write_calibration_outputs(result, root / "results")
            metadata = json.loads(paths["metadata"].read_text(encoding="utf-8"))
            self.assertEqual(metadata["split"], "validation")
            self.assertFalse(metadata["test_data_used_for_selection"])
            self.assertEqual(metadata["algorithms"]["ExG"], {"cutoff": 1})

    def test_rejects_test_split_and_double_empty_only_calibration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            samples = self._samples(root)
            predictor = lambda path, params: BinaryMask(2, 1, bytes(2))
            args = ({"ExG": predictor}, {"ExG": [{}]})
            with self.assertRaises(ValueError):
                calibrate_candidates(samples, *args, selected_split="test")
            samples[0].reference_mask_path.write_bytes(b"P5\n2 1\n255\n" + bytes(2))
            with self.assertRaises(ValueError):
                calibrate_candidates(samples[:1], *args, selected_split="validation")


if __name__ == "__main__":
    unittest.main()
