"""批量分割评价、数据划分约束与按数据集汇总。"""

from __future__ import annotations

import json
import statistics
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from wheat_phenotyping.leaf_segmentation import BinaryMask

from .mask_io import read_binary_pgm
from .segmentation import SegmentationMetrics, evaluate_binary_masks

Predictor = Callable[[Path, Mapping[str, object]], BinaryMask]
MaskLoader = Callable[[Path], BinaryMask]
PredictionObserver = Callable[["EvaluationSample", str, BinaryMask, BinaryMask], None]
VALID_SPLITS = {"train", "validation", "test"}


@dataclass(frozen=True)
class EvaluationSample:
    """数据清单中的一个样本；数据集版本和官方划分必须明确。"""

    sample_id: str
    dataset_name: str
    dataset_version: str
    split: str
    image_path: Path
    reference_mask_path: Path
    data_source: str = "public"
    group_id: str = ""


@dataclass(frozen=True)
class ImageEvaluation:
    """单张图像对一个算法的评价结果，失败样本保留错误状态。"""

    sample_id: str
    dataset_name: str
    dataset_version: str
    split: str
    data_source: str
    group_id: str
    image_path: str
    reference_mask_path: str
    algorithm_name: str
    parameters_json: str
    algorithm_metadata_json: str
    experiment_time_utc: str
    runtime_seconds: float | None
    status: str
    error: str
    is_double_empty: bool
    metrics: SegmentationMetrics | None


def evaluate_batch(
    samples: list[EvaluationSample],
    algorithms: Mapping[str, Predictor],
    *,
    parameters: Mapping[str, Mapping[str, object]],
    selected_split: str,
    parameters_frozen: bool = False,
    frozen_parameters: Mapping[str, Mapping[str, object]] | None = None,
    reference_loader: MaskLoader = read_binary_pgm,
    prediction_observer: PredictionObserver | None = None,
) -> list[ImageEvaluation]:
    """在单一固定数据划分上运行多个分割算法并逐图像计时。

    对 test 划分要求调用方显式声明参数已冻结；本函数不包含阈值搜索或调参逻辑。
    predictor 接收图像路径和参数字典，返回 BinaryMask；运行时间包含 predictor
    自身的图像读取与预测，不包含人工掩膜读取和指标计算。
    """
    if selected_split not in VALID_SPLITS:
        raise ValueError(f"selected_split 必须是 {sorted(VALID_SPLITS)} 之一")
    if selected_split == "test":
        if not parameters_frozen or frozen_parameters is None:
            raise ValueError("test 集必须提供验证集冻结参数并设置 parameters_frozen=True")
        if dict(frozen_parameters) != {name: dict(value) for name, value in parameters.items()}:
            raise ValueError("test 集参数与验证集冻结参数不一致；禁止在 test 集调参")
    if not algorithms:
        raise ValueError("至少需要注册一个分割算法")
    if set(parameters) != set(algorithms):
        raise ValueError("parameters 的算法名称必须与 algorithms 完全一致")
    if any(sample.split not in VALID_SPLITS for sample in samples):
        raise ValueError("数据清单包含无效划分；只允许 train、validation、test")
    selected = [sample for sample in samples if sample.split == selected_split]
    if not selected:
        raise ValueError(f"数据清单中没有 {selected_split} 划分样本")
    run_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results: list[ImageEvaluation] = []
    for sample in selected:
        # 每张参考掩膜只读取一次；无效标签对该样本的每个算法都记录为错误。
        reference: BinaryMask | None = None
        reference_error = ""
        try:
            reference = reference_loader(sample.reference_mask_path)
        except Exception as error:  # noqa: BLE001 - 批处理需记录单样本输入异常并继续
            reference_error = f"{type(error).__name__}: {error}"
        for algorithm_name, predictor in algorithms.items():
            params_json = json.dumps(parameters[algorithm_name], ensure_ascii=False, sort_keys=True)
            elapsed: float | None = None
            metrics: SegmentationMetrics | None = None
            prediction_mask: BinaryMask | None = None
            algorithm_metadata: Mapping[str, object] = {}
            status, error_message = "ok", ""
            if reference is None:
                status, error_message = "invalid_reference", reference_error
            else:
                started = time.perf_counter()
                try:
                    prediction = predictor(sample.image_path, parameters[algorithm_name])
                    elapsed = time.perf_counter() - started
                    # 统一注册表返回 AlgorithmPrediction；旧版预测器仍可直接返回 BinaryMask。
                    if hasattr(prediction, "mask") and hasattr(prediction, "metadata"):
                        algorithm_metadata = prediction.metadata
                        prediction = prediction.mask
                    prediction_mask = prediction
                    metrics = evaluate_binary_masks(prediction, reference)
                except Exception as error:  # noqa: BLE001 - 保留失败记录并继续批处理
                    elapsed = time.perf_counter() - started
                    status = "error"
                    error_message = f"{type(error).__name__}: {error}"
            if metrics is not None and prediction_observer is not None and prediction_mask is not None and reference is not None:
                try:
                    prediction_observer(sample, algorithm_name, prediction_mask, reference)
                except Exception as error:  # noqa: BLE001 - artifact failure must not erase valid metrics
                    algorithm_metadata = {
                        **algorithm_metadata,
                        "visualization_error": f"{type(error).__name__}: {error}",
                    }
            results.append(ImageEvaluation(
                sample_id=sample.sample_id,
                dataset_name=sample.dataset_name,
                dataset_version=sample.dataset_version,
                split=sample.split,
                data_source=sample.data_source,
                group_id=sample.group_id,
                image_path=str(sample.image_path),
                reference_mask_path=str(sample.reference_mask_path),
                algorithm_name=algorithm_name,
                parameters_json=params_json,
                algorithm_metadata_json=json.dumps(algorithm_metadata, ensure_ascii=False, sort_keys=True),
                experiment_time_utc=run_time,
                runtime_seconds=elapsed,
                status=status,
                error=error_message,
                is_double_empty=bool(metrics and metrics.true_positive + metrics.false_positive + metrics.false_negative == 0),
                metrics=metrics,
            ))
    return results


def summarize_by_dataset(results: list[ImageEvaluation]) -> list[dict[str, object]]:
    """按算法、数据集名称/版本和数据划分汇总宏平均与 pooled 指标。"""
    groups: dict[tuple[str, str, str, str], list[ImageEvaluation]] = defaultdict(list)
    for row in results:
        groups[(row.algorithm_name, row.dataset_name, row.dataset_version, row.split)].append(row)
    summaries: list[dict[str, object]] = []
    for (algorithm, dataset, version, split), rows in sorted(groups.items()):
        valid = [row for row in rows if row.status == "ok" and row.metrics is not None]
        double_empty = [row for row in valid if row.is_double_empty]
        scored = [row for row in valid if not row.is_double_empty]
        count = len(valid)
        total_pixels = sum(row.metrics.true_positive + row.metrics.false_positive + row.metrics.false_negative + row.metrics.true_negative for row in valid)  # type: ignore[union-attr]
        total_tp = sum(row.metrics.true_positive for row in valid if row.metrics)
        total_fp = sum(row.metrics.false_positive for row in valid if row.metrics)
        total_fn = sum(row.metrics.false_negative for row in valid if row.metrics)
        total_tn = sum(row.metrics.true_negative for row in valid if row.metrics)
        union = total_tp + total_fp + total_fn
        # 若整个分组都没有前景，pooled 前景指标无可评价对象，留空而不是记为 1。
        pooled_iou = total_tp / union if union else None
        pooled_precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else None
        pooled_recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else None
        pooled_f1 = 2 * total_tp / (2 * total_tp + total_fp + total_fn) if 2 * total_tp + total_fp + total_fn else None
        def macro(name: str) -> float | None:
            return statistics.mean(getattr(row.metrics, name) for row in scored if row.metrics) if scored else None

        def spread(name: str) -> float | None:
            values = [getattr(row.metrics, name) for row in scored if row.metrics]
            return statistics.pstdev(values) if values else None
        summaries.append({
            "algorithm_name": algorithm,
            "dataset_name": dataset,
            "dataset_version": version,
            "split": split,
            "sample_count": len(rows),
            "successful_count": count,
            "failed_count": len(rows) - count,
            "double_empty_count": len(double_empty),
            "nonempty_scored_count": len(scored),
            "total_pixels": total_pixels,
            "macro_iou": macro("iou"),
            "macro_precision": macro("precision"),
            "macro_recall": macro("recall"),
            "macro_f1_score": macro("f1_score"),
            "std_iou": spread("iou"),
            "std_precision": spread("precision"),
            "std_recall": spread("recall"),
            "std_f1_score": spread("f1_score"),
            "pooled_iou": pooled_iou,
            "pooled_precision": pooled_precision,
            "pooled_recall": pooled_recall,
            "pooled_f1_score": pooled_f1,
            "mean_runtime_seconds": sum(row.runtime_seconds or 0.0 for row in valid) / count if count else None,
            "experiment_time_utc": rows[0].experiment_time_utc,
            "parameters_json": rows[0].parameters_json,
        })
    return summaries
