"""导入并核验 ETH 官方 EWS 数据，保留源文件并生成可追溯清单。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import zipfile
import base64
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


EXPECTED_MD5 = "8e73182583c3f4faa84e48006688183d"
EXPECTED_SPLIT_COUNTS = {"train": 142, "validation": 24, "test": 24}
DATASET_VERSION = "2021-11-30"
SPLITS = tuple(EXPECTED_SPLIT_COUNTS)


def _open_archive(archive_path: Path) -> zipfile.ZipFile:
    """检查官方压缩包记录给出的校验和，拒绝处理来源不明的归档。"""
    checksum = hashlib.md5(archive_path.read_bytes()).hexdigest()
    if checksum != EXPECTED_MD5:
        raise ValueError(f"EWS 官方压缩包 MD5 不匹配：预期 {EXPECTED_MD5}，实际 {checksum}")
    return zipfile.ZipFile(archive_path)


def _pgm_p5(width: int, height: int, pixels: bytes) -> bytes:
    """生成最大像素值为 1 的 PGM P5；像素严格为背景 0 / 前景 1。"""
    if width < 1 or height < 1 or len(pixels) != width * height:
        raise ValueError("PGM 尺寸与像素数量不一致")
    if any(value not in (0, 1) for value in pixels):
        raise ValueError("PGM 标签只能包含 0 和 1")
    return f"P5\n{width} {height}\n1\n".encode("ascii") + pixels


def _read_official_mask(mask_bytes: bytes) -> tuple[Image.Image, bytes, dict[str, Any]]:
    """将官方 PNG 标签转为二值图；不缩放、不插值，也不改写源 PNG。

    官方 PNG 使用 LA 模式，其中 luminance 是反色标签：低值表示活体植被，
    高值表示非活体背景。用固定的 128 分界将 8-bit 灰度标签整理为两类。
    """
    with Image.open(io.BytesIO(mask_bytes)) as opened:
        source = opened.copy()
    if source.mode not in ("L", "LA"):
        raise ValueError(f"不支持的 EWS 掩膜模式：{source.mode}")
    luminance = source.getchannel("L")
    values = sorted(set(luminance.tobytes()))
    pixels = luminance.point(lambda value: 1 if value < 128 else 0).tobytes()
    if not pixels or not set(pixels).issubset({0, 1}):
        raise ValueError("官方掩膜二值化结果无效")
    details = {
        "source_mask_mode": source.mode,
        "source_mask_luminance_values": values,
        "foreground_rule": "luminance < 128 => live vegetative material (1); otherwise background (0)",
        "live_vegetation_pixels": pixels.count(1),
        "non_live_or_background_pixels": pixels.count(0),
    }
    return source, pixels, details


def _write_manifest(root: Path, records: list[dict[str, str]]) -> Path:
    """写入兼容现有评价器的清单，并补齐用户要求的 image_id/annotation_type。"""
    path = root / "manifest.csv"
    fields = (
        "sample_id", "image_id", "dataset_name", "dataset_version", "group_id", "split",
        "image_path", "mask_path", "reference_mask_path", "data_source", "annotation_type",
    )
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    return path


def _make_contact_sheet(root: Path, samples: list[dict[str, Any]], seed: int) -> Path:
    """固定随机种子抽样并制作原图/标注并排核验图。"""
    selected = random.Random(seed).sample(samples, min(20, len(samples)))
    tile_w, tile_h, label_h, gap = 150, 150, 40, 12
    cols = 4
    rows = (len(selected) + cols - 1) // cols
    card_w, card_h = tile_w * 2 + gap, tile_h + label_h
    sheet = Image.new("RGB", (cols * card_w, rows * card_h), "white")
    draw = ImageDraw.Draw(sheet)
    for index, item in enumerate(selected):
        col, row = index % cols, index // cols
        x, y = col * card_w, row * card_h
        with Image.open(item["image_file"]) as opened:
            image = opened.convert("RGB").resize((tile_w, tile_h), Image.Resampling.NEAREST)
        with Image.open(item["pgm_file"]) as opened:
            mask = opened.convert("L").point(lambda value: 255 if value else 0).convert("RGB")
            mask = mask.resize((tile_w, tile_h), Image.Resampling.NEAREST)
        sheet.paste(image, (x, y + label_h))
        sheet.paste(mask, (x + tile_w + gap, y + label_h))
        draw.text((x, y + 5), f"{item['split']} | {item['image_id']}", fill="black")
        draw.text((x, y + label_h - 15), "RGB", fill="black")
        draw.text((x + tile_w + gap, y + label_h - 15), "Mask (white = live)", fill="black")
    destination = root / "quality_visualizations" / "ews_20_pair_audit.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="PNG", optimize=False)
    return destination


def _inspect_github_repositories(
    staging: Path, official_names: dict[str, set[str]], processed_masks: Path
) -> tuple[dict[str, Any], dict[tuple[str, str], tuple[str, int | None]]]:
    """对照 GitHub Supervisely 原始归档，记录缺失、空标注和像素差异。"""
    output: dict[str, Any] = {}
    per_image: dict[tuple[str, str], tuple[str, int | None]] = {}
    repo_for_split = {
        "train": "EWS-Dataset-training-data-master",
        "validation": "EWS-Dataset-training-data-master",
        "test": "EWS-Dataset-test-data-master",
    }
    for split, repo in repo_for_split.items():
        directory = staging / repo / "project" / split
        if not directory.is_dir():
            output[split] = {"available": False}
            continue
        images = {path.name for path in (directory / "img").glob("*.png")}
        annotations = {path.name[:-5]: path for path in (directory / "ann").glob("*.png.json")}
        empty_annotations = 0
        exact_matches = 0
        mismatch_images: list[dict[str, Any]] = []
        for annotation in annotations.values():
            payload = json.loads(annotation.read_text(encoding="utf-8"))
            objects = payload.get("objects", [])
            empty_annotations += not objects
            image_name = annotation.name[:-5]
            if image_name not in official_names[split]:
                per_image[(split, image_name)] = ("github_image_not_in_official_split", None)
                continue
            official_path = processed_masks / split / f"{Path(image_name).stem}.pgm"
            with Image.open(official_path) as opened:
                official = opened.convert("L").tobytes()
            github = bytearray(350 * 350)
            for obj in objects:
                bitmap_bytes = zlib.decompress(base64.b64decode(obj["bitmap"]["data"]))
                with Image.open(io.BytesIO(bitmap_bytes)) as opened_bitmap:
                    bitmap = opened_bitmap.convert("L").point(lambda value: 255 if value else 0)
                origin_x, origin_y = obj["bitmap"]["origin"]
                if origin_x < 0 or origin_y < 0 or origin_x + bitmap.width > 350 or origin_y + bitmap.height > 350:
                    raise ValueError(f"Supervisely bitmap 超出图像边界：{split}/{image_name}")
                pixels = bitmap.tobytes()
                for row in range(bitmap.height):
                    start = (origin_y + row) * 350 + origin_x
                    for column, value in enumerate(pixels[row * bitmap.width:(row + 1) * bitmap.width]):
                        if value:
                            github[start + column] = 255
            xor_pixels = sum(left != right for left, right in zip(official, github))
            status = "exact_match" if xor_pixels == 0 else ("empty_github_annotation" if not objects else "pixel_mismatch")
            per_image[(split, image_name)] = (status, xor_pixels)
            if xor_pixels == 0:
                exact_matches += 1
            else:
                mismatch_images.append({"image_id": Path(image_name).stem, "status": status, "xor_pixels": xor_pixels})
        output[split] = {
            "available": True,
            "github_image_count": len(images),
            "github_annotation_json_count": len(annotations),
            "github_unpaired_images": sorted(images - set(annotations)),
            "github_unpaired_annotations": sorted(set(annotations) - images),
            "github_annotations_with_no_objects": empty_annotations,
            "github_annotation_exact_matches_to_official_mask": exact_matches,
            "github_annotation_nonmatching_images": mismatch_images,
            "official_images_missing_from_github_repo": sorted(official_names[split] - images),
            "github_images_not_in_official_split": sorted(images - official_names[split]),
        }
    for split in SPLITS:
        for image_name in official_names[split]:
            per_image.setdefault((split, image_name), ("not_in_github_repository", None))
    return output, per_image


def import_dataset(archive_path: Path, project_root: Path, *, sample_seed: int = 20261112) -> dict[str, Any]:
    """按 ETH 官方 train/validation/test 划分写入原始与处理数据。"""
    raw_root = project_root / "data" / "raw" / "ews"
    output_root = project_root / "data" / "processed" / "ews"
    staging = raw_root / "_staging"
    target_dirs = [raw_root / split for split in SPLITS]
    processed_masks = output_root / "masks_pgm"
    if any(path.exists() and any(path.iterdir()) for path in target_dirs):
        raise FileExistsError("data/raw/ews/train|validation|test 已有文件；为保护原始数据，本脚本拒绝覆盖")
    if processed_masks.exists() and any(processed_masks.rglob("*")):
        raise FileExistsError("data/processed/ews/masks_pgm 已有内容；为保护已有结果，本脚本拒绝覆盖")

    with _open_archive(archive_path) as archive:
        names = archive.namelist()
        official_names: dict[str, set[str]] = {split: set() for split in SPLITS}
        for name in names:
            parts = Path(name.replace("\\", "/")).parts
            if len(parts) != 3 or parts[0] != "EWS-Dataset" or parts[1] not in SPLITS:
                continue
            filename = parts[2]
            if filename.lower().endswith("_mask.png"):
                continue
            if filename.lower().endswith(".png"):
                official_names[parts[1]].add(filename)
        if {split: len(official_names[split]) for split in SPLITS} != EXPECTED_SPLIT_COUNTS:
            raise ValueError(f"官方划分数量与预期不符：{ {k: len(v) for k, v in official_names.items()} }")

        report_rows: list[dict[str, str]] = []
        manifest_rows: list[dict[str, str]] = []
        samples: list[dict[str, Any]] = []
        mode_counts: Counter[str] = Counter()
        raw_value_counts: Counter[str] = Counter()
        split_summaries: dict[str, Any] = {}
        total_live = total_pixels = 0
        empty_mask_count = 0

        for split in SPLITS:
            images_dir = raw_root / split / "images"
            masks_dir = raw_root / split / "masks"
            pgm_dir = processed_masks / split
            for directory in (images_dir, masks_dir, pgm_dir):
                directory.mkdir(parents=True, exist_ok=True)
            split_live = 0
            split_pixels = 0
            for image_name in sorted(official_names[split]):
                stem = Path(image_name).stem
                archive_base = f"EWS-Dataset/{split}/{image_name}"
                mask_name = f"{stem}_mask.png"
                archive_mask = f"EWS-Dataset/{split}/{mask_name}"
                if archive_base not in names or archive_mask not in names:
                    raise ValueError(f"官方文件缺失或未配对：{split}/{image_name}")

                image_bytes = archive.read(archive_base)
                mask_bytes = archive.read(archive_mask)
                with Image.open(io.BytesIO(image_bytes)) as opened_image:
                    image = opened_image.copy()
                source_mask, binary_pixels, details = _read_official_mask(mask_bytes)
                if image.mode not in ("RGB", "RGBA"):
                    raise ValueError(f"EWS 原图不是 RGB/RGBA：{split}/{image_name}: {image.mode}")
                if image.size != source_mask.size:
                    raise ValueError(f"图像/掩膜尺寸不一致：{split}/{image_name}")
                if image.size != (350, 350):
                    raise ValueError(f"EWS 图像尺寸不是官方 350x350：{split}/{image_name}: {image.size}")

                image_file = images_dir / image_name
                source_mask_file = masks_dir / mask_name
                pgm_file = pgm_dir / f"{stem}.pgm"
                # 源图与源掩膜逐字节复制；只在 processed 中生成二值派生掩膜。
                image_file.write_bytes(image_bytes)
                source_mask_file.write_bytes(mask_bytes)
                pgm_file.write_bytes(_pgm_p5(image.width, image.height, binary_pixels))

                image_rel = Path("../../raw/ews") / split / "images" / image_name
                mask_rel = Path("masks_pgm") / split / pgm_file.name
                sample_id = Path(image_name).stem
                record = {
                    "sample_id": sample_id,
                    "image_id": sample_id,
                    "dataset_name": "EWS",
                    "dataset_version": DATASET_VERSION,
                    "group_id": sample_id,
                    "split": split,
                    "image_path": image_rel.as_posix(),
                    "mask_path": mask_rel.as_posix(),
                    "reference_mask_path": mask_rel.as_posix(),
                    "data_source": "public",
                    "annotation_type": "manual_live_vs_non_live_vegetative_binary",
                }
                manifest_rows.append(record)
                live_pixels = details["live_vegetation_pixels"]
                empty_mask_count += live_pixels == 0
                pixel_count = image.width * image.height
                split_live += live_pixels
                split_pixels += pixel_count
                total_live += live_pixels
                total_pixels += pixel_count
                mode_counts.update([details["source_mask_mode"]])
                raw_value_counts.update(map(str, details["source_mask_luminance_values"]))
                report_rows.append({
                    "image_id": sample_id,
                    "split": split,
                    "dataset_name": "EWS",
                    "dataset_version": DATASET_VERSION,
                    "image_path": image_rel.as_posix(),
                    "original_mask_path": (Path("../../raw/ews") / split / "masks" / mask_name).as_posix(),
                    "mask_path": mask_rel.as_posix(),
                    "image_format": "PNG",
                    "original_mask_format": "PNG",
                    "image_width": str(image.width),
                    "image_height": str(image.height),
                    "mask_width": str(source_mask.width),
                    "mask_height": str(source_mask.height),
                    "source_mask_mode": details["source_mask_mode"],
                    "source_mask_luminance_values": json.dumps(details["source_mask_luminance_values"]),
                    "pgm_pixel_values": "0,1",
                    "foreground_label": "live vegetative material",
                    "background_label": "non-live vegetative material",
                    "live_vegetation_pixels": str(live_pixels),
                    "background_pixels": str(pixel_count - live_pixels),
                    "live_vegetation_ratio": f"{live_pixels / pixel_count:.8f}",
                    "pair_status": "matched; same 350x350 dimensions; no resizing",
                })
                samples.append({"split": split, "image_id": sample_id, "image_file": image_file, "pgm_file": pgm_file})
            split_summaries[split] = {
                "image_count": len(official_names[split]),
                "annotation_count": len(official_names[split]),
                "dimensions": {"width": 350, "height": 350},
                "live_vegetation_ratio_mean_pixel_weighted": split_live / split_pixels,
            }

    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = _write_manifest(output_root, manifest_rows)
    contact_sheet = _make_contact_sheet(output_root, samples, sample_seed)
    repository_checks, github_annotation_comparison = _inspect_github_repositories(
        staging, official_names, processed_masks,
    )
    for row in report_rows:
        split = row["split"]
        image_name = Path(row["image_path"]).name
        status, xor_pixels = github_annotation_comparison[(split, image_name)]
        row["github_annotation_comparison"] = status
        row["github_annotation_xor_pixels"] = "" if xor_pixels is None else str(xor_pixels)
    quality_csv = output_root / "dataset_quality_report.csv"
    quality_fields = list(report_rows[0])
    with quality_csv.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=quality_fields)
        writer.writeheader()
        writer.writerows(report_rows)

    summary = {
        "dataset_name": "Eschikon Wheat Segmentation (EWS)",
        "dataset_version": DATASET_VERSION,
        "dataset_type": "real public RGB images with manually annotated live/non-live vegetative material masks",
        "original_image_count": len(manifest_rows),
        "annotation_count": len(manifest_rows),
        "matched_image_annotation_pairs": len(manifest_rows),
        "unpaired_image_count": 0,
        "unpaired_annotation_count": 0,
        "empty_reference_mask_count": empty_mask_count,
        "splits": split_summaries,
        "image_formats": {"PNG": len(manifest_rows)},
        "original_mask_formats": {"PNG": len(manifest_rows)},
        "processed_mask_format": "PGM P5, maxval=1, values 0=background and 1=live vegetative material",
        "source_mask_modes": dict(mode_counts),
        "source_mask_luminance_values": sorted(int(value) for value in raw_value_counts),
        "mask_conversion": {
            "rule": "original PNG luminance < 128 becomes live vegetation 1; otherwise background 0",
            "source_grayscale_edge_values_quantized_to_two_classes": True,
            "resized": False,
            "interpolated": False,
            "lossy_compression": False,
            "original_png_preserved": True,
            "annotation_semantics": "vegetative active material is foreground; soil, rocks, dead plants, and other non-active material are background",
        },
        "live_vegetation_ratio_mean_pixel_weighted": total_live / total_pixels,
        "dataset_source": "https://doi.org/10.3929/ethz-b-000512332",
        "paper_doi": "10.3389/fpls.2021.774068",
        "license": "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
        "github_training_validation_repository": "https://github.com/supervisely-ecosystem/EWS-Dataset-training-data",
        "github_test_repository": "https://github.com/supervisely-ecosystem/EWS-Dataset-test-data",
        "github_original_model_repository_not_used_for_algorithm_implementation": "https://github.com/RadekZenkl/EWS",
        "official_archive_filename": archive_path.name,
        "official_archive_md5": EXPECTED_MD5,
        "official_archive_checksum_verified": True,
        "download_provenance": "../../raw/ews/_staging/download_provenance.json",
        "github_repository_comparison": repository_checks,
        "quality_artifacts": {
            "manifest": str(manifest_path.relative_to(project_root).as_posix()),
            "quality_report_csv": str(quality_csv.relative_to(project_root).as_posix()),
            "random_visual_audit_png": str(contact_sheet.relative_to(project_root).as_posix()),
            "visual_audit_sample_count": len(samples) if len(samples) < 20 else 20,
            "visual_audit_seed": sample_seed,
        },
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    summary_path = output_root / "dataset_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="导入和质量检查 ETH 官方 EWS 数据集")
    parser.add_argument("--archive", type=Path, required=True, help="ETH 官方 EWS-Dataset.zip")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--sample-seed", type=int, default=20261112)
    args = parser.parse_args()
    summary = import_dataset(args.archive, args.project_root.resolve(), sample_seed=args.sample_seed)
    print(json.dumps({
        "original_image_count": summary["original_image_count"],
        "annotation_count": summary["annotation_count"],
        "splits": summary["splits"],
        "quality_artifacts": summary["quality_artifacts"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
