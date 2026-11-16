"""V2.0 一体化长势分析编排层。

复用既有图像分析、V1 指标、V1.1 规则和生育期服务，不重复实现分割算法。
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import time

from .config import Settings
from .errors import AnalysisError
from .growth_stage_service import predict_growth_stage
from .image_service import analyze_image


def analyze_growth_request(data: bytes, filename: str, task_id: str, settings: Settings, profile: dict, algorithm: str = "ExG", plot_id: str | None = None) -> dict[str, object]:
    """执行当前长势分析，并尽力附加已存在的生育期模型结果。"""
    started = time.perf_counter()
    result = analyze_image(data, filename, task_id, settings, profile, algorithm)
    growth = result.growth_analysis or {}
    vigor = growth.get("vigor_assessment", {})
    stage = None
    stage_status = "unavailable"
    try:
        stage = predict_growth_stage(data, filename, task_id, settings)
        stage_status = "succeeded"
    except AnalysisError as error:
        # 生育期模型是可选增强项，不能阻断已成功的当前长势分析。
        stage_status = error.code
    except Exception:
        stage_status = "GROWTH_STAGE_MODEL_UNAVAILABLE"

    record_path = settings.storage_root / "analyses" / task_id / "record.json"
    try:
        if record_path.is_file():
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["growth_stage"] = stage
            record["growth_stage_status"] = stage_status
            record["plot_id"] = plot_id
            record["v2_evaluation_version"] = vigor.get("evaluation_version", "growth-vigor-v1.1-rule")
            record["v2_completed_at_utc"] = datetime.now(timezone.utc).isoformat()
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        # 原始分析已成功；历史增强记录失败时不伪造成功状态。
        stage_status = "HISTORY_ENRICHMENT_FAILED"

    payload = result.model_dump(mode="json")
    payload.update({
        "analysis_id": task_id,
        "plot_id": plot_id,
        "vegetation_coverage": growth.get("metrics", {}).get("vegetation_coverage"),
        "vigor_score": vigor.get("vigor_score"),
        "vigor_level": vigor.get("vigor_level"),
        "coverage_score": vigor.get("coverage_score"),
        "greenness_score": vigor.get("greenness_score"),
        "uniformity_score": vigor.get("uniformity_score"),
        "reliability": vigor.get("reliability"),
        "strengths": vigor.get("strengths", []),
        "improvement_suggestions": vigor.get("improvement_suggestions", []),
        "growth_stage": stage,
        "growth_stage_status": stage_status,
        "model_version": stage.get("model_version") if stage else "rule-v1.1-only",
        "evaluation_version": vigor.get("evaluation_version", "growth-vigor-v1.1-rule"),
        "processing_time": time.perf_counter() - started,
    })
    return payload


def list_growth_history(settings: Settings) -> list[dict[str, object]]:
    """读取已完成分析的摘要，按完成时间倒序。"""
    root = settings.storage_root / "analyses"
    items: list[dict[str, object]] = []
    if not root.is_dir():
        return items
    for record_path in root.glob("*/record.json"):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            task_id = record.get("task_id")
            if not isinstance(task_id, str):
                continue
            items.append({
                "analysis_id": task_id,
                "task_id": task_id,
                "created_at_utc": record.get("created_at_utc"),
                "completed_at_utc": record.get("v2_completed_at_utc", record.get("completed_at_utc")),
                "algorithm": record.get("algorithm"),
                "original_url": record.get("original_url"),
                "vigor_score": record.get("vigor_score"),
                "vigor_level": record.get("vigor_level"),
                "vegetation_coverage": (record.get("growth_analysis") or {}).get("metrics", {}).get("vegetation_coverage"),
                "growth_stage": record.get("growth_stage"),
                "growth_stage_status": record.get("growth_stage_status", "not_run"),
                "reliability": record.get("reliability"),
                "width": record.get("width"),
                "height": record.get("height"),
                "evaluation_version": record.get("v2_evaluation_version", record.get("evaluation_version")),
                "plot_id": record.get("plot_id"),
            })
        except (OSError, ValueError, TypeError):
            continue
    return sorted(items, key=lambda item: str(item.get("completed_at_utc") or item.get("created_at_utc") or ""), reverse=True)


def get_growth_history(settings: Settings, analysis_id: str) -> dict[str, object]:
    if not analysis_id or any(character not in "0123456789abcdef" for character in analysis_id) or len(analysis_id) != 32:
        raise AnalysisError(404, "GROWTH_HISTORY_NOT_FOUND", "找不到该长势分析记录。")
    record_path = settings.storage_root / "analyses" / analysis_id / "record.json"
    if not record_path.is_file():
        raise AnalysisError(404, "GROWTH_HISTORY_NOT_FOUND", "找不到该长势分析记录。")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise AnalysisError(500, "GROWTH_HISTORY_INVALID", "历史分析记录无法读取。") from error
    growth = record.get("growth_analysis") or {}
    vigor = growth.get("vigor_assessment") or {}
    record.update({
        "analysis_id": analysis_id,
        "plot_id": record.get("plot_id"),
        "vegetation_coverage": growth.get("metrics", {}).get("vegetation_coverage"),
        "vigor_score": record.get("vigor_score", vigor.get("vigor_score")),
        "vigor_level": record.get("vigor_level", vigor.get("vigor_level")),
        "coverage_score": record.get("coverage_score", vigor.get("coverage_score")),
        "greenness_score": record.get("greenness_score", vigor.get("greenness_score")),
        "uniformity_score": record.get("uniformity_score", vigor.get("uniformity_score")),
        "reliability": record.get("reliability", vigor.get("reliability")),
        "strengths": record.get("strengths", vigor.get("strengths", [])),
        "improvement_suggestions": record.get("improvement_suggestions", vigor.get("improvement_suggestions", [])),
        "growth_stage": record.get("growth_stage"),
        "growth_stage_status": record.get("growth_stage_status", "not_run"),
        "model_version": record.get("model_version", "rule-v1.1-only"),
        "evaluation_version": record.get("v2_evaluation_version", "growth-vigor-v1.1-rule"),
        "processing_time": record.get("analysis_time_seconds"),
    })
    return record


def delete_growth_history(settings: Settings, analysis_id: str) -> dict[str, object]:
    """删除用户上传分析产物；只允许删除 Web 存储区内的任务目录。"""
    if not analysis_id or any(character not in "0123456789abcdef" for character in analysis_id) or len(analysis_id) != 32:
        raise AnalysisError(404, "GROWTH_HISTORY_NOT_FOUND", "找不到该长势分析记录。")
    analyses_root = (settings.storage_root / "analyses").resolve()
    directory = (analyses_root / analysis_id).resolve()
    if not directory.is_relative_to(analyses_root) or not (directory / "record.json").is_file():
        raise AnalysisError(404, "GROWTH_HISTORY_NOT_FOUND", "找不到该长势分析记录。")
    try:
        shutil.rmtree(directory)
        # 生育期增强结果与主分析共用任务 ID，随用户记录一并清理。
        stage_directory = (settings.storage_root / "growth_stage" / analysis_id).resolve()
        stage_root = (settings.storage_root / "growth_stage").resolve()
        if stage_directory.is_relative_to(stage_root) and stage_directory.is_dir():
            shutil.rmtree(stage_directory)
    except OSError as error:
        raise AnalysisError(503, "GROWTH_HISTORY_DELETE_FAILED", "历史分析记录删除失败，请检查存储权限。") from error
    return {"status": "deleted", "analysis_id": analysis_id}
