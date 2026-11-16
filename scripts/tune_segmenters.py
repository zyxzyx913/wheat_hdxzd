"""仅在 train/validation 上比较候选参数，输出可冻结的最终参数。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wheat_phenotyping.data import load_rgb_image, read_manifest
from wheat_phenotyping.evaluation import EvaluationSample, calibrate_candidates, write_calibration_outputs
from wheat_phenotyping.leaf_segmentation import DEFAULT_REGISTRY

ALGORITHM_NAMES = {"ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion"}


def main() -> None:
    parser = argparse.ArgumentParser(description="小麦分割参数候选校准（禁止使用 test）")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True, help="JSON：每种算法对应候选参数对象列表")
    parser.add_argument("--split", choices=("train", "validation"), default="validation")
    parser.add_argument("--metric", choices=("iou", "precision", "recall", "f1_score"), default="f1_score")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    if not isinstance(candidates, dict) or set(candidates) != ALGORITHM_NAMES:
        raise ValueError(f"候选配置必须包含且只包含算法：{sorted(ALGORITHM_NAMES)}")
    if any(not isinstance(items, list) or any(not isinstance(item, dict) for item in items)
           for items in candidates.values()):
        raise ValueError("每种算法的候选值必须是 JSON 对象列表")
    predictors = {}
    for name in sorted(ALGORITHM_NAMES):
        def predictor(image_path: Path, parameters: dict[str, object], *, algorithm: str = name):
            return DEFAULT_REGISTRY.run(algorithm, load_rgb_image(image_path), parameters)
        predictors[name] = predictor
    records = read_manifest(args.manifest)
    samples = [EvaluationSample(
        row.sample_id, row.dataset_name, row.dataset_version, row.split,
        row.image_path, row.reference_mask_path, row.data_source, row.group_id,
    ) for row in records]
    calibrated = calibrate_candidates(
        samples,
        predictors,
        candidates,
        selected_split=args.split,
        selection_metric=args.metric,
    )
    outputs = write_calibration_outputs(calibrated, args.output_dir)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
