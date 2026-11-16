"""对现有七阶段初步分类实验做冻结验证审计，不训练新模型、不读取测试占位标签。"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import time

import joblib
import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split


SEED = 20261114
STAGES = list(range(1, 8))
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "growth_stage_validation_v1_1"


def ahash(path: Path) -> int:
    with Image.open(path) as image:
        gray = image.convert("L").resize((8, 8), Image.Resampling.BILINEAR)
        values = np.asarray(gray, dtype=np.float32)
    mean = float(values.mean())
    bits = 0
    for value in values.ravel():
        bits = (bits << 1) | int(value >= mean)
    return bits


def ece(y_true: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    confidence = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1) + 1
    correct = predictions == y_true
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for index in range(bins):
        selected = (confidence >= edges[index]) & ((confidence < edges[index + 1]) if index < bins - 1 else (confidence <= edges[index + 1]))
        if selected.any():
            total += float(selected.mean()) * abs(float(confidence[selected].mean()) - float(correct[selected].mean()))
    return total


def model_metrics(model, X, y, indices):
    started = time.perf_counter()
    predictions = model.predict(X[indices])
    predict_seconds = time.perf_counter() - started
    report = classification_report(y[indices], predictions, labels=STAGES, output_dict=True, zero_division=0)
    probabilities = model.predict_proba(X[indices])
    cm = confusion_matrix(y[indices], predictions, labels=STAGES)
    off_diag = []
    for row in range(len(STAGES)):
        for col in range(len(STAGES)):
            if row != col and cm[row, col] > 0:
                off_diag.append({"true_stage": STAGES[row], "predicted_stage": STAGES[col], "count": int(cm[row, col])})
    off_diag.sort(key=lambda item: item["count"], reverse=True)
    return {
        "accuracy": float(accuracy_score(y[indices], predictions)),
        "macro_precision": float(precision_score(y[indices], predictions, labels=STAGES, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y[indices], predictions, labels=STAGES, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y[indices], predictions, labels=STAGES, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y[indices], predictions, labels=STAGES, average="weighted", zero_division=0)),
        "per_class": {str(stage): {key: float(report[str(stage)][key]) for key in ("precision", "recall", "f1-score", "support")} for stage in STAGES},
        "confusion_matrix": cm.tolist(),
        "top_confusion_pairs": off_diag[:10],
        "predict_seconds": predict_seconds,
        "predict_seconds_per_image": predict_seconds / len(indices),
        "ece_10_bins": ece(y[indices], probabilities),
        "confidence_mean": float(probabilities.max(axis=1).mean()),
        "confidence_p10": float(np.quantile(probabilities.max(axis=1), 0.10)),
        "confidence_p90": float(np.quantile(probabilities.max(axis=1), 0.90)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    artifact = ROOT / "results/growth_stage_initial"
    cached = np.load(artifact / "fomo_features_subset.npz", allow_pickle=True)
    X, y, uids, quality = cached["X"], cached["y"].astype(int), cached["uids"].astype(str), cached["label_quality"].astype(int)
    train_indices, validation_indices = train_test_split(np.arange(len(y)), test_size=0.2, random_state=SEED, stratify=y)
    labels = {row["UID"]: row for row in csv.DictReader((ROOT / "data/raw/growth_stage/CGIAR_Train_mirror.csv").open(encoding="utf-8-sig"))}
    image_dir = ROOT / "data/processed/growth_stage/images"
    missing = [uid for uid in uids if uid not in labels or not (image_dir / f"{uid}.jpeg").is_file()]
    exact_hashes = {}
    perceptual = {}
    for uid in uids:
        path = image_dir / f"{uid}.jpeg"
        exact_hashes.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(uid)
        perceptual.setdefault(ahash(path), []).append(uid)
    near_pairs = []
    hashes = list(perceptual)
    for left_index, left in enumerate(hashes):
        for right in hashes[left_index + 1:]:
            if (left ^ right).bit_count() <= 4:
                near_pairs.append({"hamming_distance": (left ^ right).bit_count(), "left_uids": perceptual[left], "right_uids": perceptual[right]})
    train_uids, validation_uids = set(uids[train_indices]), set(uids[validation_indices])

    models = {}
    for name in ("logistic_regression", "svm_rbf", "random_forest"):
        model = joblib.load(artifact / f"{name}.joblib")
        group_metrics = {}
        for code in sorted(set(quality.tolist())):
            group_indices = validation_indices[quality[validation_indices] == code]
            if len(group_indices):
                group_metrics[str(code)] = model_metrics(model, X, y, group_indices)
        models[name] = {"train": model_metrics(model, X, y, train_indices), "validation": model_metrics(model, X, y, validation_indices), "validation_by_label_quality": group_metrics}

    metadata = json.loads((artifact / "experiment_metadata.json").read_text(encoding="utf-8"))
    cache_hash = hashlib.sha256(X.astype(np.float32).tobytes()).hexdigest()
    report = {
        "validation_id": "growth-stage-validation-v1.1-20261114",
        "seed": SEED,
        "sample_count": len(y),
        "train_count": len(train_indices),
        "validation_count": len(validation_indices),
        "train_validation_uid_overlap": len(train_uids & validation_uids),
        "train_uids": sorted(train_uids),
        "validation_uids": sorted(validation_uids),
        "missing_image_or_label_count": len(missing),
        "exact_duplicate_groups": [values for values in exact_hashes.values() if len(values) > 1],
        "perceptual_near_duplicate_pairs_hamming_le_4": near_pairs,
        "available_group_fields": ["UID", "growth_stage", "label_quality"],
        "group_aware_validation": "not_possible: CGIAR_Train_mirror.csv has no plot, farmer, capture_batch, date or environment field",
        "label_quality_counts": {str(code): int((quality == code).sum()) for code in sorted(set(quality.tolist()))},
        "label_quality_meaning": "CSV numeric quality codes retained; no official expert/farmer mapping was available, so names are not inferred",
        "stage_counts": {str(stage): int((y == stage).sum()) for stage in STAGES},
        "cache_feature_shape": list(X.shape),
        "cache_feature_sha256": cache_hash,
        "metadata_feature_sha256": metadata.get("feature_sha256"),
        "models": models,
        "test_evaluation": "not_run: SampleSubmission growth_stage values are placeholder 0",
        "calibration_note": "probabilities are raw classifier predict_proba outputs; no temperature/isotonic calibration was fitted",
    }
    (OUT / "validation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "validation_confusion_matrices.json").write_text(json.dumps({name: value["validation"]["confusion_matrix"] for name, value in models.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "uid_overlap": report["train_validation_uid_overlap"], "exact_duplicate_groups": len(report["exact_duplicate_groups"]), "near_pairs": len(near_pairs)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
