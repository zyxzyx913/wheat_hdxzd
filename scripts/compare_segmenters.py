"""用统一评价器比较 ExG、HSV、Otsu-ExG 和 ExG-HSV Fusion。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from wheat_phenotyping.evaluation import EvaluationSample, evaluate_batch, write_evaluation_outputs
from wheat_phenotyping.data import load_binary_mask, load_rgb_image, read_manifest
from wheat_phenotyping.leaf_segmentation import DEFAULT_REGISTRY
from wheat_phenotyping.rgb_preprocessing import RGBImage
from wheat_phenotyping.visualization import write_segmentation_overlay

ALGORITHM_NAMES = ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion")


def _load_manifest(path: Path) -> list[EvaluationSample]:
    return [EvaluationSample(
        row.sample_id, row.dataset_name, row.dataset_version, row.split,
        row.image_path, row.reference_mask_path, row.data_source, row.group_id,
    ) for row in read_manifest(path)]


def main() -> None:
    parser = argparse.ArgumentParser(description="四种传统 RGB 小麦分割算法统一对比")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--parameters", type=Path, required=True, help="四算法参数 JSON；阈值不得从测试集选择")
    parser.add_argument("--split", choices=("train", "validation", "test"), required=True)
    parser.add_argument("--frozen-parameters", type=Path, help="test 时必需：验证实验的 experiment_metadata.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--save-overlays", action="store_true", help="保存人工标注/预测差异叠加图")
    args = parser.parse_args()

    algorithm_parameters = json.loads(args.parameters.read_text(encoding="utf-8"))
    if not isinstance(algorithm_parameters, dict) or set(algorithm_parameters) != set(ALGORITHM_NAMES):
        raise ValueError(f"参数 JSON 必须恰好包含算法：{list(ALGORITHM_NAMES)}")
    if any(not isinstance(value, dict) for value in algorithm_parameters.values()):
        raise ValueError("每种算法的参数必须是 JSON 对象")
    # 先在内存单像素输入上做参数校验，避免整批图像因无效配置重复失败。
    probe = RGBImage(1, 1, bytes((0, 0, 0)))
    for name in ALGORITHM_NAMES:
        DEFAULT_REGISTRY.run(name, probe, algorithm_parameters[name])

    frozen_parameters = None
    if args.frozen_parameters:
        validation_metadata = json.loads(args.frozen_parameters.read_text(encoding="utf-8"))
        frozen_parameters = validation_metadata.get("algorithms")
        if not isinstance(frozen_parameters, dict):
            raise ValueError("冻结参数文件没有 algorithms 对象")
    if args.split == "test" and frozen_parameters is None:
        raise ValueError("test 运行必须提供 --frozen-parameters 指向验证集实验元数据")

    predictors = {}
    for algorithm_name in ALGORITHM_NAMES:
        def predictor(image_path: Path, params: dict[str, object], *, name: str = algorithm_name):
            image = load_rgb_image(image_path)
            return DEFAULT_REGISTRY.run(name, image, params)
        predictors[algorithm_name] = predictor

    overlay_dir = args.output_dir / "overlays"
    observer = None
    if args.save_overlays:
        overlay_dir.mkdir(parents=True, exist_ok=True)

        def observer(sample, algorithm_name, prediction, reference):
            safe_parts = [sample.dataset_name, sample.dataset_version, sample.sample_id, algorithm_name]
            filename = "__".join(re.sub(r"[^A-Za-z0-9_.-]+", "_", part) for part in safe_parts) + ".png"
            write_segmentation_overlay(
                load_rgb_image(sample.image_path), reference, prediction, overlay_dir / filename,
            )

    results = evaluate_batch(
        _load_manifest(args.manifest),
        predictors,
        parameters=algorithm_parameters,
        selected_split=args.split,
        parameters_frozen=frozen_parameters is not None,
        frozen_parameters=frozen_parameters,
        reference_loader=load_binary_mask,
        prediction_observer=observer,
    )
    outputs = write_evaluation_outputs(results, args.output_dir, parameters_frozen=frozen_parameters is not None)
    # 留存完整输入参数文件，包含算法名和运行者实际提供的参数，不附加人工成绩。
    (args.output_dir / "algorithm_parameters.json").write_text(
        json.dumps(algorithm_parameters, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"完成：样本-算法结果 {len(results)} 条；成功 {sum(row.status == 'ok' for row in results)} 条")


if __name__ == "__main__":
    main()
