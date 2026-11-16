"""V1.1 长势规则的真实图片稳定性审计。

只读取 EWS/CGIAR 图片和当前冻结算法参数，不修改原始数据、权重或历史结果。
CGIAR 的生育期标签仅用于分组观察，不被解释为长势标签。
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
import random
import json
import math

import numpy as np

from wheat_phenotyping.app.inference import predict_visible_mask
from wheat_phenotyping.data import load_rgb_image
from wheat_phenotyping.growth_analysis import analyze_growth
from backend.app.config import PROJECT_ROOT, SUPPORTED_ALGORITHMS, Settings, load_algorithm_profile


SEED = 20261114


def _corr(rows: list[dict], x_key: str, y_key: str) -> float | None:
    values = [(float(row[x_key]), float(row[y_key])) for row in rows if row.get(x_key) is not None and row.get(y_key) is not None]
    if len(values) < 2:
        return None
    x, y = np.asarray(values, dtype=float).T
    if np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _summary(rows: list[dict]) -> dict:
    result = {}
    for dataset in sorted({row["dataset"] for row in rows}):
        result[dataset] = {}
        for algorithm in SUPPORTED_ALGORITHMS:
            group = [row for row in rows if row["dataset"] == dataset and row["algorithm"] == algorithm]
            scores = np.asarray([row["vigor_score"] for row in group], dtype=float)
            valid_levels = [row["vigor_level"] for row in group if row["vigor_level"]]
            result[dataset][algorithm] = {
                "image_count": len(group),
                "mean_score": float(scores.mean()) if len(scores) else None,
                "std_score": float(scores.std()) if len(scores) else None,
                "min_score": float(scores.min()) if len(scores) else None,
                "max_score": float(scores.max()) if len(scores) else None,
                "level_counts": dict(Counter(valid_levels)),
                "rejection_count": sum(row["vigor_level"] is None for row in group),
                "rejection_rate": float(sum(row["vigor_level"] is None for row in group) / len(group)) if group else None,
                "reliability_counts": dict(Counter(row["reliability"] for row in group)),
            }
    return result


def _agreement(rows: list[dict]) -> dict:
    by_image = defaultdict(dict)
    for row in rows:
        by_image[(row["dataset"], row["image_id"])][row["algorithm"]] = row
    pairwise = {}
    complete = 0
    complete_total = 0
    for key, values in by_image.items():
        levels = [values[a]["vigor_level"] for a in SUPPORTED_ALGORITHMS]
        if all(level is not None for level in levels):
            complete_total += 1
            complete += len(set(levels)) == 1
        for i, left in enumerate(SUPPORTED_ALGORITHMS):
            for right in SUPPORTED_ALGORITHMS[i + 1:]:
                pair = f"{left} vs {right}"
                if values[left]["vigor_level"] is None or values[right]["vigor_level"] is None:
                    continue
                pairwise.setdefault(pair, []).append(values[left]["vigor_level"] == values[right]["vigor_level"])
    return {
        "all_four_level_agreement_rate": float(complete / complete_total) if complete_total else None,
        "all_four_comparable_images": complete_total,
        "all_four_agreement_count": complete,
        "pairwise_level_agreement": {key: float(np.mean(value)) for key, value in pairwise.items()},
    }


def main() -> None:
    root = PROJECT_ROOT
    output = root / "results" / "growth_vigor_audit_v1_1"
    output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    profiles = {algorithm: load_algorithm_profile(settings, algorithm) for algorithm in SUPPORTED_ALGORITHMS}
    samples: list[dict] = []

    ews_paths = sorted((root / "data/raw/ews/test/images").glob("*.png"))
    for path in ews_paths:
        samples.append({"dataset": "EWS", "split": "test_images_only", "image_id": path.stem, "image_path": path})

    labels = list(csv.DictReader((root / "data/raw/growth_stage/CGIAR_Train_mirror.csv").open(encoding="utf-8-sig")))
    randomizer = random.Random(SEED)
    for stage in range(1, 8):
        group = sorted([row for row in labels if int(row["growth_stage"]) == stage], key=lambda row: row["UID"])
        randomizer.shuffle(group)
        for row in group[:20]:
            path = root / "data/processed/growth_stage/images" / f"{row['UID']}.jpeg"
            samples.append({"dataset": "CGIAR", "split": "labelled_train_stage_audit", "image_id": row["UID"], "image_path": path, "growth_stage_label": int(row["growth_stage"]), "label_quality": int(row["label_quality"])})

    rows: list[dict] = []
    errors = []
    for sample in samples:
        try:
            image = load_rgb_image(sample["image_path"])
            for algorithm in SUPPORTED_ALGORITHMS:
                mask, _ = predict_visible_mask(image, algorithm, parameters=dict(profiles[algorithm]["parameters"]))
                analysis = analyze_growth(image, mask, task_id=sample["image_id"], algorithm=algorithm)
                metrics = analysis["metrics"]
                vigor = analysis["vigor_assessment"]
                row = {
                    "dataset": sample["dataset"], "split": sample["split"], "image_id": sample["image_id"], "algorithm": algorithm,
                    "width": image.width, "height": image.height, "pixel_count": image.width * image.height,
                    "growth_stage_label": sample.get("growth_stage_label"), "label_quality": sample.get("label_quality"),
                    "coverage_fraction": metrics["vegetation_coverage"]["fraction"], "green_degree": metrics["green_degree"]["mean_green_channel_ratio"],
                    "uniformity_cv": metrics["distribution_uniformity"]["coefficient_of_variation"], "coverage_score": vigor["coverage_score"],
                    "greenness_score": vigor["greenness_score"], "uniformity_score": vigor["uniformity_score"], "vigor_score": vigor["vigor_score"],
                    "vigor_level": vigor["vigor_level"], "reliability": vigor["reliability"], "reliability_score": vigor["reliability_score"],
                    "mean_brightness": metrics["image_quality"]["mean_brightness_ratio"], "sharpness": metrics["image_quality"]["sharpness_laplacian_variance"],
                    "risk_flags": "|".join(metrics["image_quality"]["risk_flags"]),
                }
                rows.append(row)
        except Exception as error:  # noqa: BLE001 - 记录异常，不中断其他样本
            errors.append({"dataset": sample["dataset"], "image_id": sample["image_id"], "error": repr(error)})

    fieldnames = list(rows[0]) if rows else []
    with (output / "per_image_algorithm_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader(); writer.writerows(rows)

    summary = _summary(rows)
    agreement = _agreement(rows)
    correlation = {
        "all_records": {key: _corr(rows, key, "vigor_score") for key in ("coverage_score", "greenness_score", "uniformity_score", "mean_brightness", "sharpness", "pixel_count")},
        "component_intercorrelation": {
            "coverage_vs_greenness": _corr(rows, "coverage_score", "greenness_score"),
            "coverage_vs_uniformity": _corr(rows, "coverage_score", "uniformity_score"),
            "greenness_vs_uniformity": _corr(rows, "greenness_score", "uniformity_score"),
        },
    }
    stage_summary = {}
    for stage in range(1, 8):
        stage_rows = [row for row in rows if row.get("growth_stage_label") == stage]
        stage_summary[str(stage)] = {algorithm: {"count": sum(row["algorithm"] == algorithm for row in stage_rows), "mean_score": float(np.mean([row["vigor_score"] for row in stage_rows if row["algorithm"] == algorithm])) if any(row["algorithm"] == algorithm for row in stage_rows) else None} for algorithm in SUPPORTED_ALGORITHMS}

    metadata = {
        "audit_id": "growth-vigor-v1.1-real-image-audit-20261114",
        "seed": SEED,
        "sample_counts": {"EWS": len(ews_paths), "CGIAR": sum(1 for sample in samples if sample["dataset"] == "CGIAR"), "total": len(samples)},
        "algorithm_parameters_source": "configs/segmentation/desktop_frozen_defaults.json + results/ews/validation_calibration/selected_parameters.json",
        "score_config": {"coverage_reference_fraction": 0.75, "uniformity_cv_max": 1.5, "coverage_weight": 0.45, "greenness_weight": 0.35, "uniformity_weight": 0.20, "good_threshold": 80.0, "average_threshold": 60.0},
        "summary": summary, "agreement": agreement, "correlation": correlation, "cgiar_stage_group_summary": stage_summary,
        "errors": errors, "record_count": len(rows),
        "truth_policy": "没有使用 EWS 掩膜或 CGIAR 生育期标签作为长势真值；仅审计图像指标、算法间稳定性和潜在分布偏差。",
    }
    (output / "audit_summary.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"samples": len(samples), "records": len(rows), "errors": len(errors), "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
