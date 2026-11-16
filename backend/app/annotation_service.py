"""科研标注任务库的本地 CSV 服务；记录采用追加写入，不覆盖其他标注者。"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
import threading
from uuid import uuid4

from fastapi import HTTPException
from wheat_phenotyping.growth_annotation import calculate_annotation_consistency

from .config import PROJECT_ROOT


ANNOTATION_ROOT = PROJECT_ROOT / "data" / "processed" / "growth_vigor"
TASKS_PATH = ANNOTATION_ROOT / "annotation_tasks.csv"
ANNOTATIONS_PATH = ANNOTATION_ROOT / "annotations.csv"
ADJUDICATED_PATH = ANNOTATION_ROOT / "adjudicated_labels.csv"
ACCESS_HEADER = "local-research"
LABELS = {"较好", "一般", "较弱", "无法判断"}
_lock = threading.Lock()


def require_access(request) -> None:
    if request.headers.get("X-Research-Access") != ACCESS_HEADER:
        raise HTTPException(status_code=403, detail="科研标注入口需要本地研究访问令牌。")


def load_tasks() -> list[dict[str, str]]:
    if not TASKS_PATH.is_file():
        raise HTTPException(status_code=503, detail="标注任务库尚未建立。")
    with TASKS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def task_map() -> dict[str, dict[str, str]]:
    return {row["anonymous_id"]: row for row in load_tasks()}


def load_annotations() -> list[dict[str, str]]:
    if not ANNOTATIONS_PATH.is_file():
        return []
    with ANNOTATIONS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def append_annotation(data: dict[str, object]) -> dict[str, object]:
    task_id = str(data["anonymous_id"])
    if task_id not in task_map():
        raise HTTPException(status_code=404, detail="找不到该匿名标注任务。")
    label = str(data["label"])
    if label not in LABELS:
        raise HTTPException(status_code=422, detail="标签必须是较好、一般、较弱或无法判断。")
    record = {
        "record_id": uuid4().hex,
        "anonymous_id": task_id,
        "annotator_id": str(data["annotator_id"]).strip(),
        "label": label,
        "growth_stage": str(data.get("growth_stage") or ""),
        "quality_flags": "|".join(data.get("quality_flags") or []),
        "rationale": str(data.get("rationale") or "").strip(),
        "annotated_at_utc": datetime.now(timezone.utc).isoformat(),
        "confidence": str(data.get("confidence") or ""),
        "review_round": str(data.get("review_round") or "1"),
    }
    with _lock:
        if any(item.get("anonymous_id") == task_id and item.get("annotator_id") == record["annotator_id"] and item.get("review_round") == record["review_round"] for item in load_annotations()):
            raise HTTPException(status_code=409, detail="该标注者已提交当前图片的这一轮记录；如需修订请增加复核轮次。")
        ANNOTATION_ROOT.mkdir(parents=True, exist_ok=True)
        exists = ANNOTATIONS_PATH.is_file()
        with ANNOTATIONS_PATH.open("a", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record))
            if not exists:
                writer.writeheader()
            writer.writerow(record)
    return record


def append_adjudication(data: dict[str, object]) -> dict[str, object]:
    """追加人工复核结果；不删除独立标注记录。"""
    task_id = str(data["anonymous_id"])
    if task_id not in task_map():
        raise HTTPException(status_code=404, detail="找不到该匿名标注任务。")
    final_label = str(data.get("final_label") or "")
    review_status = str(data.get("review_status") or "")
    if final_label and final_label not in LABELS:
        raise HTTPException(status_code=422, detail="最终标签必须是较好、一般、较弱或无法判断。")
    if review_status not in {"待复核", "已复核", "无法形成共识"}:
        raise HTTPException(status_code=422, detail="复核状态不合法。")
    record = {
        "anonymous_id": task_id, "final_label": final_label, "review_status": review_status,
        "reviewer_id": str(data["reviewer_id"]).strip(),
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "review_note": str(data.get("review_note") or "").strip(),
    }
    with _lock:
        ANNOTATION_ROOT.mkdir(parents=True, exist_ok=True)
        exists = ADJUDICATED_PATH.is_file()
        with ADJUDICATED_PATH.open("a", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(record))
            if not exists:
                writer.writeheader()
            writer.writerow(record)
    return record


def consistency() -> dict[str, object]:
    return calculate_annotation_consistency(load_annotations())
