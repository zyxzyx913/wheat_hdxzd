"""冻结 FoMo4Wheat 特征上的生育期初步分类实验。

默认每类抽取固定数量作为今晚快速交付子集；不读取测试标签、不伪造测试成绩。
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import time

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC

from wheat_phenotyping.foundation_models.fomo4wheat import FoMo4WheatExtractor


SEED = 20261114
STAGES = tuple(range(1, 8))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    labels_path = root / "data/raw/growth_stage/CGIAR_Train_mirror.csv"
    image_dir = root / "data/processed/growth_stage/images"
    weight = root / "models/pretrained/fomo4wheat/FoMo4Wheat_base.pth"
    output = root / "results/growth_stage_initial"
    output.mkdir(parents=True, exist_ok=True)
    max_per_class = int(__import__("os").environ.get("FOMO_MAX_PER_CLASS", "100"))
    rows = list(csv.DictReader(labels_path.open(encoding="utf-8-sig")))
    by_stage = {stage: [row for row in rows if int(row["growth_stage"]) == stage] for stage in STAGES}
    rng = random.Random(SEED)
    selected = []
    for stage in STAGES:
        group = sorted(by_stage[stage], key=lambda row: row["UID"])
        if len(group) > max_per_class:
            group = rng.sample(group, max_per_class)
        selected.extend(group)
    selected.sort(key=lambda row: row["UID"])
    uids = np.asarray([row["UID"] for row in selected])
    y = np.asarray([int(row["growth_stage"]) for row in selected], dtype=np.int64)
    quality = np.asarray([int(row["label_quality"]) for row in selected], dtype=np.int64)
    image_paths = [image_dir / f"{uid}.jpeg" for uid in uids]
    missing = [str(path) for path in image_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"缺少训练图片 {missing[:5]}")

    extractor = FoMo4WheatExtractor(weight, device="cpu")
    features = np.empty((len(selected), 768), dtype=np.float32)
    timings = []
    started = time.perf_counter()
    for index, path in enumerate(image_paths):
        result = extractor.extract(path)
        features[index] = result.features
        timings.append(result.inference_seconds)
        if (index + 1) % 100 == 0 or index + 1 == len(image_paths):
            print(f"features {index + 1}/{len(image_paths)}", flush=True)
    extraction_seconds = time.perf_counter() - started
    feature_sha = hashlib.sha256(features.tobytes()).hexdigest()
    np.savez_compressed(output / "fomo_features_subset.npz", X=features, y=y, uids=uids, label_quality=quality)

    train_idx, val_idx = train_test_split(np.arange(len(y)), test_size=0.2, random_state=SEED, stratify=y)
    models = {
        "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED),
        "svm_rbf": SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=SEED),
        "random_forest": RandomForestClassifier(n_estimators=300, class_weight="balanced_subsample", random_state=SEED, n_jobs=-1),
    }
    metrics = {}
    fitted = {}
    for name, model in models.items():
        fit_started = time.perf_counter(); model.fit(features[train_idx], y[train_idx]); fit_seconds = time.perf_counter() - fit_started
        pred_started = time.perf_counter(); predictions = model.predict(features[val_idx]); predict_seconds = time.perf_counter() - pred_started
        report = classification_report(y[val_idx], predictions, labels=list(STAGES), output_dict=True, zero_division=0)
        metrics[name] = {
            "accuracy": float(accuracy_score(y[val_idx], predictions)),
            "macro_precision": float(precision_score(y[val_idx], predictions, labels=list(STAGES), average="macro", zero_division=0)),
            "macro_recall": float(recall_score(y[val_idx], predictions, labels=list(STAGES), average="macro", zero_division=0)),
            "macro_f1": float(f1_score(y[val_idx], predictions, labels=list(STAGES), average="macro", zero_division=0)),
            "weighted_f1": float(f1_score(y[val_idx], predictions, labels=list(STAGES), average="weighted", zero_division=0)),
            "fit_seconds": fit_seconds,
            "validation_predict_seconds": predict_seconds,
            "validation_predict_seconds_per_image": predict_seconds / len(val_idx),
            "per_class": {str(stage): {key: float(report[str(stage)][key]) for key in ("precision", "recall", "f1-score", "support")} for stage in STAGES},
            "confusion_matrix": confusion_matrix(y[val_idx], predictions, labels=list(STAGES)).tolist(),
        }
        train_predictions = model.predict(features[train_idx])
        train_report = classification_report(y[train_idx], train_predictions, labels=list(STAGES), output_dict=True, zero_division=0)
        metrics[name]["train"] = {
            "accuracy": float(accuracy_score(y[train_idx], train_predictions)),
            "macro_precision": float(precision_score(y[train_idx], train_predictions, labels=list(STAGES), average="macro", zero_division=0)),
            "macro_recall": float(recall_score(y[train_idx], train_predictions, labels=list(STAGES), average="macro", zero_division=0)),
            "macro_f1": float(f1_score(y[train_idx], train_predictions, labels=list(STAGES), average="macro", zero_division=0)),
            "weighted_f1": float(f1_score(y[train_idx], train_predictions, labels=list(STAGES), average="weighted", zero_division=0)),
            "per_class": {str(stage): {key: float(train_report[str(stage)][key]) for key in ("precision", "recall", "f1-score", "support")} for stage in STAGES},
        }
        joblib.dump(model, output / f"{name}.joblib", compress=3)
        fitted[name] = model

    best_name = max(metrics, key=lambda name: metrics[name]["macro_f1"])
    best = fitted[best_name]
    joblib.dump(best, output / "selected_model.joblib", compress=3)
    (output / "class_mapping.json").write_text(json.dumps({str(i): f"CGIAR stage {i}" for i in STAGES}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "validation_confusion_matrix.csv").write_text("true_stage," + ",".join(map(str, STAGES)) + "\n" + "\n".join(f"{stage}," + ",".join(map(str, metrics[best_name]["confusion_matrix"][i])) for i, stage in enumerate(STAGES)) + "\n", encoding="utf-8")
    train_predictions = best.predict(features[train_idx])
    train_report = classification_report(y[train_idx], train_predictions, labels=list(STAGES), output_dict=True, zero_division=0)
    with (output / "train_classification_report.csv").open("w", newline="", encoding="utf-8-sig") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=["stage", "precision", "recall", "f1-score", "support"])
        writer.writeheader()
        for stage in STAGES:
            writer.writerow({"stage": stage, **{key: train_report[str(stage)][key] for key in ("precision", "recall", "f1-score", "support")}})
    metadata = {
        "experiment_id": "growth-stage-fomo-subset-20261114",
        "status": "initial_subset_experiment",
        "seed": SEED,
        "max_per_class": max_per_class,
        "sample_count": len(selected),
        "train_count": len(train_idx),
        "validation_count": len(val_idx),
        "stage_counts": {str(stage): int((y == stage).sum()) for stage in STAGES},
        "label_quality_counts": {str(q): int((quality == q).sum()) for q in sorted(set(quality))},
        "feature_model": "FoMo4Wheat ViT-B/14 base frozen CLS token",
        "feature_dimension": 768,
        "feature_sha256": feature_sha,
        "preprocessing": "official_eval_resize256_centercrop224_imagenet_norm",
        "weight_path": str(weight.resolve()),
        "weight_sha256": extractor.weight_sha256,
        "device": "cpu",
        "extraction_seconds": extraction_seconds,
        "mean_image_feature_seconds": float(np.mean(timings)),
        "selected_model": best_name,
        "models": metrics,
        "test_evaluation": "not_run: SampleSubmission contains placeholder 0 and no ground-truth test labels",
        "split_limitation": "stratified UID split; no reliable plot/farmer grouping field was available in Train.csv, so field-level leakage cannot be excluded",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (output / "experiment_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"selected_model": best_name, "metrics": metrics, "metadata": str(output / 'experiment_metadata.json')}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
