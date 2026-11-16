"""解码、调用现有分割算法及保存单图结果，不重复实现算法。"""

from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import time
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from wheat_phenotyping.app.inference import predict_visible_mask
from wheat_phenotyping.data import load_rgb_image
from wheat_phenotyping.phenotyping import extract_visible_growth_features
from wheat_phenotyping.growth_analysis import analyze_growth

from .config import Settings
from .errors import AnalysisError
from .schemas import AnalysisResult


logger = logging.getLogger(__name__)
SUFFIX_FORMATS = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}
FORMAT_SUFFIX = {"JPEG": ".jpg", "PNG": ".png"}
SCOPE_WARNING = "仅分析画面可见植被区域，不识别叶、茎、穗；长势结果仅为未经过农学校准的表观规则初评，不提供农学诊断或未来预测。"


def validate_and_decode(data: bytes, filename: str, settings: Settings):
    """验证真实编码、完整性和尺寸，保持原始字节不变。"""
    suffix = Path(filename.replace("\\", "/")).suffix.lower()
    expected_format = SUFFIX_FORMATS.get(suffix)
    if expected_format is None:
        raise AnalysisError(415, "UNSUPPORTED_FORMAT", "仅支持 JPG、JPEG 或 PNG 图片。")
    if not data:
        raise AnalysisError(400, "EMPTY_IMAGE", "图片内容为空，请重新选择。")
    if len(data) > settings.max_file_bytes:
        raise AnalysisError(413, "FILE_TOO_LARGE", "图片超过 10 MiB，请选择较小图片。")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as opened:
                if opened.format not in FORMAT_SUFFIX or opened.format != expected_format:
                    raise AnalysisError(415, "FORMAT_MISMATCH", "图片真实格式与扩展名不一致，仅支持 JPG/PNG。")
                width, height = opened.size
                if width * height > settings.max_pixels or max(width, height) > settings.max_dimension:
                    raise AnalysisError(413, "IMAGE_TOO_LARGE", f"图片最多 {settings.max_pixels:,} 像素，最长边最多 {settings.max_dimension} 像素；不会自动缩图。")
                if getattr(opened, "n_frames", 1) != 1:
                    raise AnalysisError(415, "ANIMATED_IMAGE", "请选择静态单帧图片，不支持动画。")
                opened.verify()
            with Image.open(BytesIO(data)) as opened:
                orientation = opened.getexif().get(274, 1)
                oriented = ImageOps.exif_transpose(opened)
                oriented.load()
                transparent = "A" in oriented.getbands() or "transparency" in oriented.info
                if transparent:
                    # 透明像素以白底合成，避免隐藏 RGB 被误当作植被。
                    rgba = oriented.convert("RGBA")
                    canonical = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
                else:
                    canonical = oriented.convert("RGB")
                # 显示副本不保留 EXIF，防止浏览器再次旋转。
                canonical.info.clear()
                return canonical, {
                    "format": expected_format,
                    "uploaded_width": width,
                    "uploaded_height": height,
                    "exif_orientation": orientation,
                    "alpha_policy": "white_composite" if transparent else "not_applicable",
                    "coordinate_space": "exif_corrected_rgb_no_resizing",
                }
    except AnalysisError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise AnalysisError(413, "IMAGE_TOO_LARGE", "图片解码尺寸过大，请选择较小图片。") from error
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as error:
        raise AnalysisError(400, "INVALID_IMAGE", "图片损坏或无法完整读取，请重新导出为 JPG/PNG。") from error


def write_prediction_images(rgb, mask, directory: Path) -> None:
    """无标注预测区域叠加；绿色仅表示前景预测，不表示预测正确。"""
    mask_image = Image.frombytes("L", (mask.width, mask.height), mask.pixels)
    mask_image.save(directory / "mask.png", format="PNG")
    original = Image.frombytes("RGB", (rgb.width, rgb.height), rgb.pixels).convert("RGBA")
    tint = Image.new("RGBA", original.size, (30, 210, 80, 0))
    tint.putalpha(mask_image.point(lambda value: 105 if value else 0))
    # 沿用现有 app/inference.py 的预测区域叠加配色，不调用需要真值的误差叠加。
    Image.alpha_composite(original, tint).convert("RGB").save(directory / "overlay.png", format="PNG")


def analyze_image(data: bytes, filename: str, task_id: str, settings: Settings, profile: dict, algorithm: str = "ExG") -> AnalysisResult:
    """按明确选择独立运行一种算法，所有成功产物一起提交。"""
    started = time.perf_counter()
    created_at = datetime.now(timezone.utc).isoformat()
    staging = settings.storage_root / "staging" / task_id
    try:
        canonical, normalization = validate_and_decode(data, filename, settings)
        staging.mkdir(parents=True, exist_ok=False)
        (staging / ("uploaded_original" + FORMAT_SUFFIX[normalization["format"]])).write_bytes(data)
        canonical.save(staging / "original.png", format="PNG")
        # 复用已有图像读取器，统一输入必须是项目原生 RGBImage。
        rgb = load_rgb_image(staging / "original.png")
        prediction_started = time.perf_counter()
        mask, metadata = predict_visible_mask(rgb, algorithm, parameters=dict(profile["parameters"]))
        prediction_seconds = time.perf_counter() - prediction_started
        features = extract_visible_growth_features(rgb, mask)
        growth_analysis = analyze_growth(rgb, mask, task_id=task_id, algorithm=algorithm)
        vigor = growth_analysis["vigor_assessment"]
        growth_analysis_path = staging / "growth_analysis.json"
        growth_analysis_path.write_text(json.dumps(growth_analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        write_prediction_images(rgb, mask, staging)
        url_root = f"/media/{task_id}"
        notes = [SCOPE_WARNING]
        if features.green_pixel_count == 0:
            notes.append("本图未检出前景；不能据此判断小麦死亡或长势不良。")
        result = AnalysisResult(
            algorithm=algorithm, input_sha256=hashlib.sha256(data).hexdigest(),
            algorithm_metadata=metadata,
            task_id=task_id, original_url=f"{url_root}/original.png",
            mask_url=f"{url_root}/mask.png", overlay_url=f"{url_root}/overlay.png",
            width=rgb.width, height=rgb.height,
            vegetation_pixel_count=features.green_pixel_count,
            total_valid_pixels=rgb.width * rgb.height,
            vegetation_ratio=features.green_area_fraction,
            analysis_time_seconds=time.perf_counter() - started,
            segmentation_time_seconds=prediction_seconds,
            parameters=dict(profile["parameters"]), profile_id=profile["profile_id"],
            created_at_utc=created_at, warnings=notes,
            growth_analysis=growth_analysis,
            growth_analysis_url=f"{url_root}/growth_analysis.json",
            vigor_score=vigor["vigor_score"], vigor_level=vigor["vigor_level"],
            coverage_score=vigor["coverage_score"], greenness_score=vigor["greenness_score"],
            uniformity_score=vigor["uniformity_score"], reliability=vigor["reliability"],
            strengths=vigor["strengths"], improvement_suggestions=vigor["improvement_suggestions"],
            evaluation_version=vigor["evaluation_version"],
        )
        record = {
            **result.model_dump(mode="json"),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "input_sha256": hashlib.sha256(data).hexdigest(),
            "uploaded_filename": filename.replace("\\", "/").split("/")[-1][:200],
            "uploaded_size_bytes": len(data),
            "normalization": normalization,
            "algorithm_metadata": metadata,
            "parameter_provenance": profile,
            "data_source": "user_upload", "dataset_split": "not_assigned",
            "mask_encoding": {"background": 0, "live_vegetation": 255},
            "valid_pixel_policy": "all pixels of EXIF-corrected RGB; transparency composited on white",
            "timing_convention": "analysis: decode, segmentation, features and image saving; excludes upload/network and final record commit",
            "growth_analysis": growth_analysis,
            "growth_analysis_url": f"{url_root}/growth_analysis.json",
        }
        (staging / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        # 唯一任务目录整体原子提交，路由只读取已完成目录，失败不展示半成品。
        os.replace(staging, settings.storage_root / "analyses" / task_id)
        return result
    except Exception as error:
        failure = {
            "task_id": task_id, "status": "failed", "algorithm": algorithm,
            "created_at_utc": created_at,
            "error_code": error.code if isinstance(error, AnalysisError) else "ANALYSIS_FAILED",
        }
        try:
            (settings.storage_root / "failures" / f"{task_id}.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            logger.exception("无法保存失败记录 task_id=%s", task_id)
        if isinstance(error, AnalysisError):
            raise
        logger.exception("图像分析失败 task_id=%s", task_id)
        if isinstance(error, OSError):
            raise AnalysisError(503, "STORAGE_UNAVAILABLE", "暂时无法保存分析结果，请检查存储空间和目录权限。") from error
        raise AnalysisError(500, "ANALYSIS_FAILED", f"{algorithm} 分析未完成，请重试或记录任务 ID 联系维护人员。") from error
