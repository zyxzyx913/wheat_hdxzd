"""仅使用训练/验证划分的可复现分割参数候选比较。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from .batch import EvaluationSample, Predictor, evaluate_batch

VALID_SELECTION_METRICS = {"iou", "precision", "recall", "f1_score"}


@dataclass(frozen=True)
class CandidateScore:
    algorithm_name: str
    candidate_index: int
    parameters: Mapping[str, object]
    selection_metric: str
    score: float
    scored_image_count: int
    double_empty_count: int
    failed_count: int


@dataclass(frozen=True)
class CalibrationResult:
    selected_split: str
    selection_metric: str
    experiment_time_utc: str
    candidate_scores: tuple[CandidateScore, ...]
    selected_parameters: Mapping[str, Mapping[str, object]]
    datasets: tuple[tuple[str, str, str, int], ...]


def calibrate_candidates(
    samples: list[EvaluationSample],
    predictors: Mapping[str, Predictor],
    candidates: Mapping[str, list[Mapping[str, object]]],
    *,
    selected_split: str = "validation",
    selection_metric: str = "f1_score",
) -> CalibrationResult:
    """逐候选运行算法并按非双空图的平均指标选择参数。

    test split 一律拒绝。若输入清单同时含多种 split，仅处理 selected_split；
    参数不从测试样本读取或计算。相同分数按候选列表顺序选第一个。
    """
    if selected_split not in {"train", "validation"}:
        raise ValueError("参数选择只允许 train 或 validation，禁止使用 test")
    if selection_metric not in VALID_SELECTION_METRICS:
        raise ValueError(f"selection_metric 必须是 {sorted(VALID_SELECTION_METRICS)}")
    if not predictors or set(predictors) != set(candidates):
        raise ValueError("predictors 与 candidates 必须包含完全相同的算法名称")
    if any(not candidate_list for candidate_list in candidates.values()):
        raise ValueError("每个算法至少要提供一个候选参数配置")
    run_time = datetime.now(timezone.utc).isoformat(timespec="seconds")
    scores: list[CandidateScore] = []
    best: dict[str, CandidateScore] = {}
    for algorithm_name, predictor in predictors.items():
        for index, candidate in enumerate(candidates[algorithm_name]):
            results = evaluate_batch(
                samples,
                {algorithm_name: predictor},
                parameters={algorithm_name: candidate},
                selected_split=selected_split,
            )
            eligible = [row for row in results if row.status == "ok" and row.metrics and not row.is_double_empty]
            if not eligible:
                raise ValueError(f"算法 {algorithm_name} 的候选 {index} 没有可用于校准的非双空图")
            score = sum(getattr(row.metrics, selection_metric) for row in eligible if row.metrics) / len(eligible)
            row = CandidateScore(
                algorithm_name=algorithm_name,
                candidate_index=index,
                parameters=dict(candidate),
                selection_metric=selection_metric,
                score=score,
                scored_image_count=len(eligible),
                double_empty_count=sum(result.is_double_empty and result.status == "ok" for result in results),
                failed_count=sum(result.status != "ok" for result in results),
            )
            scores.append(row)
            if algorithm_name not in best or row.score > best[algorithm_name].score:
                best[algorithm_name] = row
    dataset_counts: dict[tuple[str, str, str], int] = {}
    for sample in samples:
        if sample.split == selected_split:
            key = (sample.dataset_name, sample.dataset_version, sample.data_source)
            dataset_counts[key] = dataset_counts.get(key, 0) + 1
    return CalibrationResult(
        selected_split=selected_split,
        selection_metric=selection_metric,
        experiment_time_utc=run_time,
        candidate_scores=tuple(scores),
        selected_parameters={name: dict(row.parameters) for name, row in best.items()},
        datasets=tuple(sorted((*key, count) for key, count in dataset_counts.items())),
    )


def write_calibration_outputs(result: CalibrationResult, output_dir: str | Path) -> dict[str, Path]:
    """保存候选分数 CSV、最终参数和测试集可读取的冻结元数据。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    candidate_csv = out / "candidate_scores.csv"
    parameters_json = out / "selected_parameters.json"
    metadata_json = out / "experiment_metadata.json"
    with candidate_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "algorithm_name", "candidate_index", "parameters_json", "selection_metric", "score",
            "scored_image_count", "double_empty_count", "failed_count", "selected",
        ])
        writer.writeheader()
        selected_indices = {}
        for algorithm in result.selected_parameters:
            selected_indices[algorithm] = min(
                (row for row in result.candidate_scores if row.algorithm_name == algorithm
                 and dict(row.parameters) == dict(result.selected_parameters[algorithm])),
                key=lambda row: row.candidate_index,
            ).candidate_index
        for row in result.candidate_scores:
            writer.writerow({
                "algorithm_name": row.algorithm_name,
                "candidate_index": row.candidate_index,
                "parameters_json": json.dumps(row.parameters, ensure_ascii=False, sort_keys=True),
                "selection_metric": row.selection_metric,
                "score": f"{row.score:.12g}",
                "scored_image_count": row.scored_image_count,
                "double_empty_count": row.double_empty_count,
                "failed_count": row.failed_count,
                "selected": row.candidate_index == selected_indices[row.algorithm_name],
            })
    parameters_json.write_text(json.dumps(result.selected_parameters, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    metadata = {
        "experiment_time_utc": result.experiment_time_utc,
        "split": result.selected_split,
        "selection_metric": result.selection_metric,
        "parameters_frozen": True,
        "algorithms": result.selected_parameters,
        "datasets": result.datasets,
        "candidate_count": len(result.candidate_scores),
        "double_empty_policy": "excluded from candidate means and counted separately",
        "test_data_used_for_selection": False,
        "files": [candidate_csv.name, parameters_json.name],
    }
    metadata_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"candidate_scores": candidate_csv, "selected_parameters": parameters_json, "metadata": metadata_json}
