"""在 validation 校准随机森林概率阈值，或用冻结参数评价指定划分。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from wheat_phenotyping.data import load_binary_mask, load_rgb_image, read_manifest
from wheat_phenotyping.evaluation import (
    EvaluationSample,
    calibrate_candidates,
    evaluate_batch,
    write_calibration_outputs,
    write_evaluation_outputs,
)
from wheat_phenotyping.leaf_segmentation import BinaryMask
from wheat_phenotyping.leaf_segmentation.rf_features import extract_pixel_features


ALGORITHM_NAME = "RF-Color-Texture"


def _make_predictor(model_path: Path):
    """载入训练好的随机森林并构建统一批量评价器预测函数。"""
    model = joblib.load(model_path)

    def predict(image_path: Path, parameters: dict[str, object]) -> BinaryMask:
        threshold = float(parameters["probability_threshold"])
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("probability_threshold 必须位于 0..1")
        image = load_rgb_image(image_path)
        features = extract_pixel_features(image)
        positive_index = list(model.classes_).index(1)
        probability = model.predict_proba(features)[:, positive_index]
        pixels = np.where(probability >= threshold, 255, 0).astype(np.uint8).tobytes()
        return BinaryMask(image.width, image.height, pixels)

    return predict


def run_experiment(
    manifest: Path,
    model_path: Path,
    split: str,
    output_dir: Path,
    *,
    frozen_metadata: Path | None = None,
    thresholds: tuple[float, ...] = (0.25, 0.35, 0.45, 0.5, 0.55, 0.65, 0.75),
) -> dict[str, Path]:
    """在 validation 选择 F1 最优阈值，test 时强制读取冻结参数。"""
    if split not in {"train", "validation", "test"}:
        raise ValueError("split 必须是 train、validation 或 test")
    records = read_manifest(manifest)
    samples = [EvaluationSample(
        row.sample_id, row.dataset_name, row.dataset_version, row.split,
        row.image_path, row.reference_mask_path, row.data_source, row.group_id,
    ) for row in records]
    predictor = _make_predictor(model_path)
    if split == "validation":
        candidates = {ALGORITHM_NAME: [{"probability_threshold": value} for value in thresholds]}
        calibrated = calibrate_candidates(
            samples, {ALGORITHM_NAME: predictor}, candidates,
            selected_split="validation", selection_metric="f1_score",
        )
        outputs = write_calibration_outputs(calibrated, output_dir)
        metadata_path = outputs["metadata"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["model_file"] = str(model_path.resolve())
        metadata["candidate_thresholds"] = list(thresholds)
        metadata["validation_candidates_selected_by"] = "macro mean F1 excluding double-empty images"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        return outputs

    if split == "test" and frozen_metadata is None:
        raise ValueError("test 评价必须提供 validation 冻结元数据")
    frozen = None
    parameters: dict[str, dict[str, object]]
    if frozen_metadata:
        frozen_json = json.loads(frozen_metadata.read_text(encoding="utf-8"))
        frozen = frozen_json.get("algorithms")
        if not isinstance(frozen, dict) or ALGORITHM_NAME not in frozen:
            raise ValueError("冻结文件缺少 RF-Color-Texture 参数")
        parameters = {ALGORITHM_NAME: frozen[ALGORITHM_NAME]}
    else:
        parameters = {ALGORITHM_NAME: {"probability_threshold": 0.5}}

    results = evaluate_batch(
        samples, {ALGORITHM_NAME: predictor}, parameters=parameters,
        selected_split=split,
        parameters_frozen=(split == "test"),
        frozen_parameters=frozen,
        reference_loader=load_binary_mask,
    )
    outputs = write_evaluation_outputs(results, output_dir, parameters_frozen=(split == "test"))
    metadata_path = outputs["metadata_json"]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["model_file"] = str(model_path.resolve())
    metadata["validation_frozen_metadata"] = str(frozen_metadata.resolve()) if frozen_metadata else None
    metadata["test_data_used_for_parameter_selection"] = False if split == "test" else None
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="EWS 随机森林分割的 validation 校准和冻结评价")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--split", choices=("train", "validation", "test"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-metadata", type=Path, help="test 运行必须提供 validation 的 experiment_metadata.json")
    parser.add_argument(
        "--thresholds", default="0.25,0.35,0.45,0.5,0.55,0.65,0.75",
        help="仅 validation 用的概率阈值候选，以逗号分隔",
    )
    args = parser.parse_args()
    thresholds = tuple(float(value.strip()) for value in args.thresholds.split(",") if value.strip())
    outputs = run_experiment(
        args.manifest, args.model, args.split, args.output_dir,
        frozen_metadata=args.frozen_metadata,
        thresholds=thresholds,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
