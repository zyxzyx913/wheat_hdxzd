"""审计 CGIAR 生育期子集的感知近重复风险并进行分组验证。

本脚本只读取原始图片、现有 768 维缓存和已保存分类器配置，不删除或修改
原始图片、标签、FoMo4Wheat 权重和历史实验结果。新模型与结果全部写入独立目录。
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.fftpack import dct
from sklearn.base import clone
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedGroupKFold


SEED = 20261114
STAGES = list(range(1, 8))
ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "data/processed/growth_stage/images"
SOURCE_REPORT = ROOT / "results/growth_stage_validation_v1_1/validation_report.json"
ARTIFACT_DIR = ROOT / "results/growth_stage_initial"
OUT = ROOT / "results/growth_stage_near_duplicate_audit"

# 这是一个保守的图像级候选规则，不等同于人工确认的“同一张图”。
# pHash、dHash 同时约束全局结构与局部边缘，RMSE 限制缩放后的像素差异。
PHASH_MAX = 10
DHASH_MAX = 24
RMSE_MAX = 0.12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phash(path: Path) -> int:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float32)
    coefficients = dct(dct(gray, axis=0, norm="ortho"), axis=1, norm="ortho")[:8, :8]
    values = coefficients.ravel()[1:]
    median = float(np.median(values))
    result = 0
    for value in values:
        result = (result << 1) | int(value >= median)
    return result


def dhash(path: Path) -> int:
    with Image.open(path) as image:
        gray = np.asarray(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS), dtype=np.float32)
    result = 0
    for row in gray:
        for left, right in zip(row[:-1], row[1:]):
            result = (result << 1) | int(left > right)
    return result


def resized_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB").resize((64, 64), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0


def image_info(path: Path) -> dict[str, object]:
    with Image.open(path) as image:
        return {"width": image.width, "height": image.height, "mode": image.mode}


def expanded_candidate_pairs(report: dict[str, object]) -> list[dict[str, object]]:
    """将 hash 桶中的 UID 列表展开为唯一 UID 对。"""
    unique: dict[tuple[str, str], dict[str, object]] = {}
    for candidate in report["perceptual_near_duplicate_pairs_hamming_le_4"]:
        for left in candidate["left_uids"]:
            for right in candidate["right_uids"]:
                if left == right:
                    continue
                pair = tuple(sorted((str(left), str(right))))
                unique[pair] = {
                    "left_uid": pair[0],
                    "right_uid": pair[1],
                    "original_ahash_distance": int(candidate["hamming_distance"]),
                }
    return list(unique.values())


def connected_components(edges: list[tuple[str, str]]) -> list[list[str]]:
    parent: dict[str, str] = {}

    def find(value: str) -> str:
        parent.setdefault(value, value)
        if parent[value] != value:
            parent[value] = find(parent[value])
        return parent[value]

    for left, right in edges:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left
    groups: dict[str, set[str]] = defaultdict(set)
    for value in parent:
        groups[find(value)].add(value)
    return sorted((sorted(values) for values in groups.values() if len(values) > 1), key=lambda values: (-len(values), values))


def classifier_metrics(model, x: np.ndarray, y: np.ndarray, indices: np.ndarray) -> dict[str, object]:
    prediction = model.predict(x[indices])
    report = classification_report(y[indices], prediction, labels=STAGES, output_dict=True, zero_division=0)
    matrix = confusion_matrix(y[indices], prediction, labels=STAGES)
    return {
        "sample_count": int(len(indices)),
        "accuracy": float(accuracy_score(y[indices], prediction)),
        "macro_precision": float(precision_score(y[indices], prediction, labels=STAGES, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y[indices], prediction, labels=STAGES, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(y[indices], prediction, labels=STAGES, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y[indices], prediction, labels=STAGES, average="weighted", zero_division=0)),
        "per_class": {str(stage): {key: float(report[str(stage)][key]) for key in ("precision", "recall", "f1-score", "support")} for stage in STAGES},
        "confusion_matrix": matrix.tolist(),
    }


def write_contact_sheet(groups: list[list[str]], pair_rows: list[dict[str, object]]) -> None:
    """生成严格候选组缩略图，供人工复核，不改变原始图片。"""
    if not groups:
        return
    font = ImageFont.load_default()
    width, thumb_height, row_height = 230, 130, 165
    sheet = Image.new("RGB", (width * 4, row_height * len(groups)), (20, 30, 25))
    draw = ImageDraw.Draw(sheet)
    for row_index, group in enumerate(groups):
        y = row_index * row_height
        for column, uid in enumerate(group[:4]):
            path = IMAGE_DIR / f"{uid}.jpeg"
            with Image.open(path) as image:
                thumb = image.convert("RGB")
                thumb.thumbnail((width - 10, thumb_height))
            sheet.paste(thumb, (column * width + 5, y + 4))
            draw.text((column * width + 5, y + thumb_height + 8), uid, fill=(240, 245, 235), font=font)
        draw.text((5, y + row_height - 18), f"group_{row_index + 1:02d} ({len(group)} images)", fill=(170, 225, 155), font=font)
    sheet.save(OUT / "contact_sheet_strict_groups.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    report = json.loads(SOURCE_REPORT.read_text(encoding="utf-8"))
    cache = np.load(ARTIFACT_DIR / "fomo_features_subset.npz", allow_pickle=True)
    x = cache["X"].astype(np.float32)
    y = cache["y"].astype(int)
    uids = cache["uids"].astype(str)
    uid_index = {uid: index for index, uid in enumerate(uids)}
    original_train = set(report["train_uids"])
    original_validation = set(report["validation_uids"])
    original_split = {uid: "train" if uid in original_train else "validation" for uid in uids}

    image_cache: dict[str, dict[str, object]] = {}
    for uid in uids:
        path = IMAGE_DIR / f"{uid}.jpeg"
        image_cache[uid] = {
            "sha256": sha256(path),
            "phash": phash(path),
            "dhash": dhash(path),
            "pixels": resized_rgb(path),
            **image_info(path),
        }

    pair_rows: list[dict[str, object]] = []
    strict_edges: list[tuple[str, str]] = []
    for candidate in expanded_candidate_pairs(report):
        left, right = candidate["left_uid"], candidate["right_uid"]
        left_info, right_info = image_cache[left], image_cache[right]
        pixel_rmse = float(np.sqrt(np.mean((left_info["pixels"] - right_info["pixels"]) ** 2)))
        phash_distance = int((int(left_info["phash"]) ^ int(right_info["phash"])).bit_count())
        dhash_distance = int((int(left_info["dhash"]) ^ int(right_info["dhash"])).bit_count())
        strict = phash_distance <= PHASH_MAX and dhash_distance <= DHASH_MAX and pixel_rmse <= RMSE_MAX
        if strict:
            strict_edges.append((left, right))
        pair_rows.append({
            "left_uid": left,
            "right_uid": right,
            "left_sha256": left_info["sha256"],
            "right_sha256": right_info["sha256"],
            "original_ahash_distance": candidate["original_ahash_distance"],
            "phash_distance": phash_distance,
            "dhash_distance": dhash_distance,
            "pixel_rmse_64x64": round(pixel_rmse, 8),
            "left_width": left_info["width"],
            "left_height": left_info["height"],
            "right_width": right_info["width"],
            "right_height": right_info["height"],
            "left_original_split": original_split[left],
            "right_original_split": original_split[right],
            "crossed_original_split": original_split[left] != original_split[right],
            "strict_visual_candidate": strict,
            "review_status": "algorithmic_candidate_manual_review_required" if strict else "aHash_candidate_not_confirmed",
        })

    groups = connected_components(strict_edges)
    group_id: dict[str, str] = {}
    for index, group in enumerate(groups, start=1):
        for uid in group:
            group_id[uid] = f"near_group_{index:02d}"
    for uid in uids:
        group_id.setdefault(uid, f"singleton_{uid}")
    for row in pair_rows:
        row["strict_group_id"] = group_id[row["left_uid"]] if row["left_uid"] in group_id else ""

    # 用严格候选组作为 group，所有未命中的图像保持单例组。
    groups_array = np.array([group_id[uid] for uid in uids])
    split_generator = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    folds = []
    for fold_index, (train_indices, validation_indices) in enumerate(split_generator.split(np.zeros(len(y)), y, groups_array)):
        counts = np.bincount(y[validation_indices], minlength=8)[1:]
        score = abs(len(validation_indices) - 140) + int(np.abs(counts - 20).sum())
        folds.append((score, fold_index, train_indices, validation_indices, counts))
    _, chosen_fold, train_indices, validation_indices, validation_counts = min(folds, key=lambda item: (item[0], item[1]))

    grouped_models: dict[str, dict[str, object]] = {}
    for name in ("logistic_regression", "svm_rbf", "random_forest"):
        original = joblib.load(ARTIFACT_DIR / f"{name}.joblib")
        grouped_model = clone(original)
        grouped_model.fit(x[train_indices], y[train_indices])
        grouped_models[name] = {
            "train": classifier_metrics(grouped_model, x, y, train_indices),
            "validation": classifier_metrics(grouped_model, x, y, validation_indices),
            "parameters": grouped_model.get_params(),
        }
        joblib.dump(grouped_model, OUT / f"grouped_{name}.joblib")

    with (OUT / "candidate_pairs.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = list(pair_rows[0]) + ["left_label", "right_label", "left_group_id", "right_group_id"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in pair_rows:
            left, right = row["left_uid"], row["right_uid"]
            row.update({"left_label": int(y[uid_index[left]]), "right_label": int(y[uid_index[right]]), "left_group_id": group_id[left], "right_group_id": group_id[right]})
            writer.writerow(row)

    group_rows = []
    for index, group in enumerate(groups, start=1):
        group_rows.append({
            "strict_group_id": f"near_group_{index:02d}",
            "member_count": len(group),
            "uids": "|".join(group),
            "labels": "|".join(str(int(y[uid_index[uid]])) for uid in group),
            "original_splits": "|".join(sorted({original_split[uid] for uid in group})),
            "grouped_splits": "|".join(sorted({"train" if index in set(train_indices) else "validation" for index in [uid_index[uid] for uid in group]})),
            "manual_confirmation": "required",
        })
    with (OUT / "near_duplicate_groups.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = list(group_rows[0]) if group_rows else ["strict_group_id", "member_count", "uids", "labels", "original_splits", "grouped_splits", "manual_confirmation"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(group_rows)

    write_contact_sheet(groups, pair_rows)
    cross_group_count = sum(len({original_split[uid] for uid in group}) > 1 for group in groups)
    summary = {
        "audit_id": "growth-stage-near-duplicate-audit-v1-20261114",
        "seed": SEED,
        "source_candidate_records": len(report["perceptual_near_duplicate_pairs_hamming_le_4"]),
        "expanded_unique_uid_pairs": len(pair_rows),
        "exact_duplicate_groups": len(report["exact_duplicate_groups"]),
        "strict_visual_candidate_groups": len(groups),
        "strict_visual_candidate_images": int(sum(len(group) for group in groups)),
        "strict_visual_candidate_edges": len(strict_edges),
        "strict_thresholds": {"phash_hamming_max": PHASH_MAX, "dhash_hamming_max": DHASH_MAX, "pixel_rmse_max": RMSE_MAX},
        "strict_groups_are_confirmed_duplicates": False,
        "manual_confirmation_required": True,
        "cross_original_train_validation_strict_groups": cross_group_count,
        "original_split": {"train": len(original_train), "validation": len(original_validation)},
        "grouped_split": {"train": int(len(train_indices)), "validation": int(len(validation_indices))},
        "grouped_validation_stage_counts": {str(stage): int(validation_counts[stage - 1]) for stage in STAGES},
        "chosen_stratified_group_fold": int(chosen_fold),
        "group_aware_validation_limitation": "近重复分组只能降低图像级相似性泄漏，不能替代缺少地块、年份、环境和拍摄批次字段的真正地块独立验证。",
        "models": grouped_models,
        "old_svm_validation": {"accuracy": 0.42142857142857143, "macro_f1": 0.41355740563641535, "weighted_f1": 0.41355740563641535},
        "artifacts": ["candidate_pairs.csv", "near_duplicate_groups.csv", "contact_sheet_strict_groups.png", "validation_report.json"],
    }
    (OUT / "validation_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "candidate_records": len(report["perceptual_near_duplicate_pairs_hamming_le_4"]), "expanded_pairs": len(pair_rows), "groups": len(groups), "cross_original_groups": cross_group_count, "grouped_split": summary["grouped_split"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
