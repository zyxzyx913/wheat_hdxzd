"""科研标注 API 测试：数据路径使用临时清单，不触碰真实候选库。"""
import csv

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app import annotation_service
from backend.app.config import Settings
from backend.app.main import create_app


@pytest.fixture
def annotation_api(tmp_path, monkeypatch):
    root = tmp_path / "growth_vigor"
    root.mkdir()
    tasks = root / "annotation_tasks.csv"
    with tasks.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["anonymous_id", "dataset", "split", "source_image_id", "image_path", "width", "height", "pixel_count", "selection_stratum", "task_status", "created_at_utc"])
        writer.writeheader(); writer.writerow({"anonymous_id":"GV-test","dataset":"EWS","split":"test","source_image_id":"x","image_path":"data/raw/ews/test/images/missing.png","width":2,"height":2,"pixel_count":4,"selection_stratum":"test","task_status":"待标注","created_at_utc":"now"})
    annotations = root / "annotations.csv"
    annotations.write_text("record_id,anonymous_id,annotator_id,label,growth_stage,quality_flags,rationale,annotated_at_utc,confidence,review_round\n", encoding="utf-8-sig")
    adjudicated = root / "adjudicated_labels.csv"
    adjudicated.write_text("anonymous_id,final_label,review_status,reviewer_id,reviewed_at_utc,review_note\n", encoding="utf-8-sig")
    monkeypatch.setattr(annotation_service, "ANNOTATION_ROOT", root)
    monkeypatch.setattr(annotation_service, "TASKS_PATH", tasks)
    monkeypatch.setattr(annotation_service, "ANNOTATIONS_PATH", annotations)
    monkeypatch.setattr(annotation_service, "ADJUDICATED_PATH", adjudicated)
    with TestClient(create_app(Settings(storage_root=tmp_path / "web"))) as client:
        yield client


def test_annotation_requires_research_access(annotation_api):
    assert annotation_api.get("/api/research/annotation/tasks").status_code == 403


def test_annotation_append_consistency_and_adjudication(annotation_api):
    headers = {"X-Research-Access": "local-research"}
    for annotator, label in (("one", "较好"), ("two", "一般")):
        response = annotation_api.post("/api/research/annotation/records", headers=headers, json={"anonymous_id":"GV-test","annotator_id":annotator,"label":label})
        assert response.status_code == 200, response.text
    duplicate = annotation_api.post("/api/research/annotation/records", headers=headers, json={"anonymous_id":"GV-test","annotator_id":"one","label":"较好"})
    assert duplicate.status_code == 409
    status = annotation_api.get("/api/research/annotation/status", headers=headers).json()
    assert status["annotation_record_count"] == 2
    assert status["consistency"]["conflict_image_count"] == 1
    adjudication = annotation_api.post("/api/research/annotation/adjudications", headers=headers, json={"anonymous_id":"GV-test","final_label":"无法判断","review_status":"无法形成共识","reviewer_id":"reviewer_1","review_note":"两位标注意见不一致，保留为无法判断。"})
    assert adjudication.status_code == 200, adjudication.text
