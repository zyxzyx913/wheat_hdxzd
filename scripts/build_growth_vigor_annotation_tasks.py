"""构建不带长势标签的候选人工标注任务库。"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import random

from PIL import Image


SEED = 20261114
TARGET_EWS = 150
TARGET_CGIAR_PER_STAGE = 20
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "growth_vigor"


def anon_id(dataset: str, relative: str) -> str:
    return "GV-" + hashlib.sha256(f"{dataset}|{relative}".encode("utf-8")).hexdigest()[:16]


def ews_candidates() -> list[dict]:
    paths = []
    for split in ("train", "validation", "test"):
        paths.extend((ROOT / "data/raw/ews" / split / "images").glob("*.png"))
    # 用文件名中的地块前缀限制同一地块的重复图片；不修改原始图片。
    groups = {}
    for path in sorted(paths):
        plot = path.name.split("_RGB1_")[0]
        groups.setdefault(plot, []).append(path)
    rng = random.Random(SEED)
    selected = []
    for plot in sorted(groups):
        items = groups[plot]
        rng.shuffle(items)
        selected.extend(sorted(items))
    if len(selected) > TARGET_EWS:
        # 先保留每个地块一张，再轮询加入同地块的第二张，尽量减少相似图片集中。
        first_by_plot = {}
        remaining = []
        for path in selected:
            plot = path.name.split("_RGB1_")[0]
            if plot not in first_by_plot:
                first_by_plot[plot] = path
            else:
                remaining.append(path)
        selected = list(first_by_plot.values())
        rng.shuffle(remaining)
        selected.extend(remaining[: max(0, TARGET_EWS - len(selected))])
        selected = sorted(selected)
    records = []
    for path in selected:
        rel = path.relative_to(ROOT).as_posix()
        split = rel.split("/")[3]
        records.append({"dataset": "EWS", "split": split, "path": path, "selection_stratum": f"EWS_{split}"})
    return records


def cgiar_candidates() -> list[dict]:
    import csv as csv_module
    labels = list(csv_module.DictReader((ROOT / "data/raw/growth_stage/CGIAR_Train_mirror.csv").open(encoding="utf-8-sig")))
    rng = random.Random(SEED)
    records = []
    for stage in range(1, 8):
        group = sorted([row for row in labels if int(row["growth_stage"]) == stage], key=lambda row: row["UID"])
        rng.shuffle(group)
        for row in group[:TARGET_CGIAR_PER_STAGE]:
            path = ROOT / "data/processed/growth_stage/images" / f"{row['UID']}.jpeg"
            records.append({"dataset": "CGIAR", "split": "labelled_train", "path": path, "selection_stratum": f"CGIAR_stage_sampling_{stage}"})
    return records


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    records = ews_candidates() + cgiar_candidates()
    seen = set()
    tasks = []
    created = datetime.now(timezone.utc).isoformat()
    for record in records:
        path = record["path"]
        rel = path.relative_to(ROOT).as_posix()
        if not path.is_file() or rel in seen:
            continue
        seen.add(rel)
        with Image.open(path) as image:
            image.load()
            width, height = image.size
        tasks.append({
            "anonymous_id": anon_id(record["dataset"], rel),
            "dataset": record["dataset"], "split": record["split"],
            "source_image_id": path.stem, "image_path": rel,
            "width": width, "height": height, "pixel_count": width * height,
            "selection_stratum": record["selection_stratum"],
            "task_status": "待标注", "created_at_utc": created,
        })
    tasks.sort(key=lambda row: row["anonymous_id"])
    fields = ["anonymous_id", "dataset", "split", "source_image_id", "image_path", "width", "height", "pixel_count", "selection_stratum", "task_status", "created_at_utc"]
    with (OUT / "annotation_tasks.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(tasks)
    annotation_fields = ["record_id", "anonymous_id", "annotator_id", "label", "growth_stage", "quality_flags", "rationale", "annotated_at_utc", "confidence", "review_round"]
    annotation_path = OUT / "annotations.csv"
    if not annotation_path.exists():
        with annotation_path.open("w", newline="", encoding="utf-8-sig") as handle:
            csv.DictWriter(handle, fieldnames=annotation_fields).writeheader()
    adjudicated_path = OUT / "adjudicated_labels.csv"
    if not adjudicated_path.exists():
        fields_final = ["anonymous_id", "final_label", "review_status", "reviewer_id", "reviewed_at_utc", "review_note"]
        with adjudicated_path.open("w", newline="", encoding="utf-8-sig") as handle:
            csv.DictWriter(handle, fieldnames=fields_final).writeheader()
    quality_stats = {"dark_mean_brightness_lt_0.20": 0, "normal": 0, "overexposed_mean_brightness_ge_0.90": 0}
    for task in tasks:
        with Image.open(ROOT / task["image_path"]) as image:
            rgb = image.convert("RGB")
            pixels = list(rgb.getdata())
            brightness = sum(0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2] for pixel in pixels) / (255 * len(pixels))
        if brightness < 0.20:
            quality_stats["dark_mean_brightness_lt_0.20"] += 1
        elif brightness >= 0.90:
            quality_stats["overexposed_mean_brightness_ge_0.90"] += 1
        else:
            quality_stats["normal"] += 1
    summary = {
        "candidate_count": len(tasks),
        "dataset_counts": {dataset: sum(row["dataset"] == dataset for row in tasks) for dataset in ("EWS", "CGIAR")},
        "labels_assigned": 0,
        "selection_seed": SEED,
        "selection_policy": "EWS 控制同一地块重复；CGIAR 每个生育期抽取20张仅用于覆盖阶段分布；未写入长势标签。",
        "label_status": "候选样本库，尚无人工长势标签",
        "quality_strata_observed": quality_stats,
        "created_at_utc": created,
    }
    (OUT / "dataset_summary.json").write_text(__import__("json").dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
