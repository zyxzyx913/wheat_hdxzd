"""只用官方 train 划分训练颜色与纹理随机森林分割器。"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier

from wheat_phenotyping.data import load_binary_mask, load_rgb_image, read_manifest
from wheat_phenotyping.leaf_segmentation.rf_features import FEATURE_NAMES, extract_pixel_features


def train_model(
    manifest: Path,
    output_dir: Path,
    *,
    seed: int = 20261112,
    pixels_per_class_per_image: int = 500,
    tree_count: int = 100,
    max_depth: int | None = 18,
    min_samples_leaf: int = 2,
) -> dict[str, object]:
    """分层抽取 train 像素并拟合模型；拒绝使用 validation/test 参与训练。"""
    if pixels_per_class_per_image < 1 or tree_count < 1 or min_samples_leaf < 1:
        raise ValueError("抽样量、树数和叶节点最小样本数必须为正整数")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"输出目录已有文件，拒绝覆盖：{output_dir}")
    records = read_manifest(manifest)
    training_records = [record for record in records if record.split == "train"]
    if not training_records:
        raise ValueError("清单中没有 train 样本")

    rng = np.random.default_rng(seed)
    sampled_features: list[np.ndarray] = []
    sampled_labels: list[np.ndarray] = []
    per_image_counts: dict[str, dict[str, int]] = {}
    for record in training_records:
        image = load_rgb_image(record.image_path)
        mask = load_binary_mask(record.reference_mask_path)
        if (image.width, image.height) != (mask.width, mask.height):
            raise ValueError(f"训练图像与标注尺寸不同：{record.sample_id}")
        features = extract_pixel_features(image)
        labels = np.frombuffer(mask.pixels, dtype=np.uint8) > 0
        class_indices = (np.flatnonzero(~labels), np.flatnonzero(labels))
        counts: dict[str, int] = {}
        for label_value, indices in enumerate(class_indices):
            amount = min(pixels_per_class_per_image, len(indices))
            if amount == 0:
                continue
            chosen = rng.choice(indices, size=amount, replace=False)
            sampled_features.append(features[chosen])
            sampled_labels.append(np.full(amount, label_value, dtype=np.uint8))
            counts["background" if label_value == 0 else "live_vegetation"] = int(amount)
        per_image_counts[record.sample_id] = counts

    x_train = np.concatenate(sampled_features, axis=0)
    y_train = np.concatenate(sampled_labels, axis=0)
    if set(np.unique(y_train)) != {0, 1}:
        raise ValueError("抽样训练数据没有同时包含背景与活体植被")

    model = RandomForestClassifier(
        n_estimators=tree_count,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=-1,
    )
    started = time.perf_counter()
    model.fit(x_train, y_train)
    training_seconds = time.perf_counter() - started

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "rf_color_texture.joblib"
    joblib.dump(model, model_path, compress=3)
    metadata = {
        "model_name": "RF-Color-Texture",
        "training_time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": "public EWS official train split only",
        "manifest": str(manifest.resolve()),
        "training_image_count": len(training_records),
        "validation_used_for_training": False,
        "test_used_for_training": False,
        "features": list(FEATURE_NAMES),
        "sampling": {
            "pixels_per_class_per_image_limit": pixels_per_class_per_image,
            "seed": seed,
            "sampled_total": int(len(y_train)),
            "sampled_background": int(np.sum(y_train == 0)),
            "sampled_live_vegetation": int(np.sum(y_train == 1)),
            "per_image_counts": per_image_counts,
        },
        "model_parameters": model.get_params(),
        "scikit_learn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "training_seconds": training_seconds,
        "model_file": model_path.name,
        "label_definition": "1=live vegetative material; 0=non-live/background",
    }
    (output_dir / "training_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="在 EWS train 划分训练像素级随机森林")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261112)
    parser.add_argument("--pixels-per-class-per-image", type=int, default=500)
    parser.add_argument("--trees", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=18)
    parser.add_argument("--min-samples-leaf", type=int, default=2)
    args = parser.parse_args()
    result = train_model(
        args.manifest, args.output_dir, seed=args.seed,
        pixels_per_class_per_image=args.pixels_per_class_per_image,
        tree_count=args.trees, max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
