"""使用 CSV 数据清单运行可复现的分割评价；当前内置 ExG 基线适配器。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from wheat_phenotyping.data import load_binary_mask, load_rgb_image, read_manifest
from wheat_phenotyping.evaluation import EvaluationSample, evaluate_batch, write_evaluation_outputs
from wheat_phenotyping.leaf_segmentation import segment_leaves_exg


def _read_manifest(path: Path) -> list[EvaluationSample]:
    return [EvaluationSample(
        row.sample_id, row.dataset_name, row.dataset_version, row.split,
        row.image_path, row.reference_mask_path, row.data_source, row.group_id,
    ) for row in read_manifest(path)]


def main() -> None:
    parser = argparse.ArgumentParser(description="小麦叶片分割批量评价（人工 PGM 掩膜）")
    parser.add_argument("--manifest", type=Path, required=True, help="含训练/验证/测试划分的 CSV 清单")
    parser.add_argument("--split", choices=("train", "validation", "test"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exg-threshold", type=int, required=True, help="冻结的 ExG 参数，不提供未经校准默认值")
    parser.add_argument("--min-component-area", type=int, default=0)
    parser.add_argument("--frozen-parameters", type=Path, help="验证集实验元数据 JSON；test 必填并用于核对参数")
    args = parser.parse_args()
    params = {"exg_threshold": args.exg_threshold, "min_component_area": args.min_component_area}
    frozen_parameters = None
    if args.frozen_parameters:
        frozen_meta = json.loads(args.frozen_parameters.read_text(encoding="utf-8"))
        frozen_parameters = frozen_meta.get("algorithms")
        if not isinstance(frozen_parameters, dict):
            raise ValueError("冻结参数文件缺少 algorithms 字段")

    def predict_exg(image_path: Path, parameters: dict[str, object]):
        image = load_rgb_image(image_path)
        return segment_leaves_exg(
            image,
            exg_threshold=int(parameters["exg_threshold"]),
            min_component_area=int(parameters["min_component_area"]),
        )

    samples = _read_manifest(args.manifest)
    results = evaluate_batch(
        samples,
        {"ExG": predict_exg},
        parameters={"ExG": params},
        selected_split=args.split,
        parameters_frozen=frozen_parameters is not None,
        frozen_parameters=frozen_parameters,
        reference_loader=load_binary_mask,
    )
    paths = write_evaluation_outputs(results, args.output_dir, parameters_frozen=frozen_parameters is not None)
    for name, path in paths.items():
        print(f"{name}: {path}")
    print(f"逐图像结果数：{len(results)}；成功：{sum(row.status == 'ok' for row in results)}")


if __name__ == "__main__":
    main()
