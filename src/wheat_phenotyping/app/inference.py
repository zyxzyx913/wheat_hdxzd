"""无标注单图/批量推理逻辑及结果文件保存。"""

from __future__ import annotations

import csv
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from wheat_phenotyping.data import load_rgb_image
from wheat_phenotyping.leaf_segmentation import BinaryMask, DEFAULT_REGISTRY
from wheat_phenotyping.leaf_segmentation.rf_features import extract_pixel_features
from wheat_phenotyping.phenotyping import extract_visible_growth_features


ALGORITHM_NAMES = ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion", "RF-Color-Texture")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".ppm"}


def predict_visible_mask(
    rgb,
    method: str,
    *,
    model=None,
    parameters: dict[str, object] | None = None,
    probability_threshold: float = 0.75,
) -> tuple[BinaryMask, dict[str, object]]:
    """以固定参数运行一个算法，返回二值掩膜和可追溯参数。"""
    if method not in ALGORITHM_NAMES:
        raise ValueError(f"不支持的算法：{method}")
    if method == "RF-Color-Texture":
        if model is None:
            raise ValueError("RF-Color-Texture 算法需要已加载模型")
        if not 0 < probability_threshold < 1:
            raise ValueError("RF 概率阈值必须在 0 与 1 之间")
        classes = list(model.classes_)
        if 1 not in classes:
            raise ValueError("随机森林模型缺少活体植被标签 1")
        foreground_column = classes.index(1)
        # 以带两行上下文的条带处理高分辨率照片，限制峰值内存。
        pixels = bytearray(rgb.width * rgb.height)
        band_height, halo = 256, 2
        for y_start in range(0, rgb.height, band_height):
            y_end = min(rgb.height, y_start + band_height)
            context_start, context_end = max(0, y_start - halo), min(rgb.height, y_end + halo)
            first, last = context_start * rgb.width * 3, context_end * rgb.width * 3
            band = type(rgb)(rgb.width, context_end - context_start, rgb.pixels[first:last])
            features = extract_pixel_features(band)
            probabilities = model.predict_proba(features)[:, foreground_column].reshape(band.height, band.width)
            local_start, local_end = y_start - context_start, y_end - context_start
            rows = np.where(probabilities[local_start:local_end] >= probability_threshold, 255, 0).astype(np.uint8)
            target_start, target_end = y_start * rgb.width, y_end * rgb.width
            pixels[target_start:target_end] = rows.tobytes()
        mask = BinaryMask(rgb.width, rgb.height, bytes(pixels))
        metadata = {"algorithm": method, "probability_threshold": probability_threshold,
                    "model_labels": "1=live vegetation; 0=non-live/background"}
        return mask, metadata

    configured = dict(parameters or {})
    prediction = DEFAULT_REGISTRY.run(method, rgb, configured)
    metadata = {"algorithm": method, "parameters": configured, **dict(prediction.metadata)}
    return prediction.mask, metadata


def discover_images(source: str | Path, *, recursive: bool = False) -> list[Path]:
    """接收单张图像或文件夹，按稳定顺序收集支持的图像。"""
    path = Path(source)
    if path.is_file():
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"不支持的图像扩展名：{path.suffix}")
        return [path]
    if not path.is_dir():
        raise FileNotFoundError(f"输入路径不存在：{path}")
    candidates = path.rglob("*") if recursive else path.iterdir()
    return sorted((candidate for candidate in candidates if candidate.is_file() and candidate.suffix.lower() in IMAGE_SUFFIXES), key=lambda p: str(p).lower())


def _safe_stem(image_path: Path, source_root: Path | None) -> str:
    """为同名文件生成稳定且不冲突的输出前缀。"""
    try:
        identity = str(image_path.resolve().relative_to(source_root.resolve())) if source_root else str(image_path.resolve())
    except ValueError:
        identity = str(image_path.resolve())
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]
    visible = "_".join(part for part in image_path.relative_to(source_root).with_suffix("").parts) if source_root and image_path.is_relative_to(source_root) else image_path.stem
    cleaned = "".join(character if character.isalnum() or character in "-_." else "_" for character in visible)
    return f"{cleaned[:100]}_{digest}"


def run_image_batch(
    image_paths: list[Path],
    methods: list[str],
    output_dir: str | Path,
    *,
    model=None,
    model_path: str | Path | None = None,
    algorithm_parameters: dict[str, dict[str, object]] | None = None,
    rf_probability_threshold: float = 0.75,
    source_root: str | Path | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> list[dict[str, object]]:
    """对一组图像运行所选算法，保存每张掩膜、叠加图、CSV 和 JSON。"""
    if not image_paths:
        raise ValueError("输入中没有支持的图像")
    if not methods or any(method not in ALGORITHM_NAMES for method in methods) or len(set(methods)) != len(methods):
        raise ValueError("算法列表为空、重复或含未知算法")
    params = algorithm_parameters or {}
    if any(method not in params for method in methods if method != "RF-Color-Texture"):
        raise ValueError("缺少传统算法冻结参数")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    root = Path(source_root) if source_root else None
    rows: list[dict[str, object]] = []
    loaded_model = model
    if "RF-Color-Texture" in methods and loaded_model is None:
        if model_path is None or not Path(model_path).is_file():
            raise FileNotFoundError("选择 RF 算法时需提供已训练的 EWS 模型文件")
        import joblib

        loaded_model = joblib.load(model_path)

    total = len(image_paths) * len(methods)
    done = 0
    for image_path in image_paths:
        base = _safe_stem(Path(image_path), root)
        for method in methods:
            done += 1
            started = time.perf_counter()
            row: dict[str, object] = {
                "image_path": str(Path(image_path).resolve()),
                "algorithm": method,
                "status": "error",
                "runtime_seconds": None,
                "width": None,
                "height": None,
                "green_area_fraction": None,
                "canopy_width_fraction": None,
                "canopy_height_fraction": None,
                "parameters_json": "",
                "algorithm_metadata_json": "",
                "mask_path": "",
                "overlay_path": "",
                "error": "",
                "data_scope": "live vegetation/background segmentation; not organ recognition or agronomic grading",
                "model_path": str(Path(model_path).resolve()) if method == "RF-Color-Texture" and model_path else "",
            }
            try:
                rgb = load_rgb_image(image_path)
                mask, metadata = predict_visible_mask(
                    rgb, method, model=loaded_model if method == "RF-Color-Texture" else None,
                    parameters=params.get(method), probability_threshold=rf_probability_threshold,
                )
                features = extract_visible_growth_features(rgb, mask)
                mask_path = out / f"{base}__{method.replace(' ', '_')}__mask.pgm"
                overlay_path = out / f"{base}__{method.replace(' ', '_')}__overlay.png"
                mask.save_pgm(str(mask_path))
                rgb_image = Image.frombytes("RGB", (rgb.width, rgb.height), rgb.pixels).convert("RGBA")
                tint = Image.new("RGBA", rgb_image.size, (30, 210, 80, 105))
                tint.putalpha(Image.frombytes("L", (mask.width, mask.height), mask.pixels).point(lambda value: 105 if value else 0))
                Image.alpha_composite(rgb_image, tint).convert("RGB").save(overlay_path, format="PNG")
                row.update({
                    "status": "ok", "runtime_seconds": time.perf_counter() - started,
                    "width": rgb.width, "height": rgb.height,
                    "green_area_fraction": features.green_area_fraction,
                    "canopy_width_fraction": features.canopy_width_fraction,
                    "canopy_height_fraction": features.canopy_height_fraction,
                    "parameters_json": json.dumps(params.get(method, {"probability_threshold": rf_probability_threshold}), ensure_ascii=False, sort_keys=True),
                    "algorithm_metadata_json": json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                    "mask_path": str(mask_path.resolve()), "overlay_path": str(overlay_path.resolve()),
                })
            except Exception as error:  # 单图失败要写入记录并继续处理后续图像
                row["runtime_seconds"] = time.perf_counter() - started
                row["error"] = f"{type(error).__name__}: {error}"
            rows.append(row)
            if progress:
                progress(done, total, f"{Path(image_path).name} · {method}")

    fields = list(rows[0])
    with (out / "image_results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "run_type": "unlabeled_image_inference",
        "methods": methods,
        "input_image_count": len(image_paths),
        "result_count": len(rows),
        "successful_count": sum(row["status"] == "ok" for row in rows),
        "failed_count": sum(row["status"] != "ok" for row in rows),
        "parameters": {method: params.get(method, {"probability_threshold": rf_probability_threshold}) for method in methods},
        "model_path": str(Path(model_path).resolve()) if model_path else None,
        "outputs": ["image_results.csv", "per-image PGM masks", "per-image PNG overlays"],
        "warning": "植被面积比例是图像可见性代理值；此流程不识别器官、不输出长势等级或未来生长预测。",
    }
    (out / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows
