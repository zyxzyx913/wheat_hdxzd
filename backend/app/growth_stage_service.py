"""CGIAR 生育期轻量分类器的单图推理服务。

模型使用冻结的 FoMo4Wheat ViT-B/14 特征和已保存的轻量分类头；模型文件
不存在或加载失败时明确返回不可用，不生成随机概率。
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

import joblib
import numpy as np

from wheat_phenotyping.foundation_models.fomo4wheat import FoMo4WheatExtractor

from .config import PROJECT_ROOT, Settings
from .errors import AnalysisError
from .image_service import validate_and_decode


STAGE_NAMES = {
    1: "冠根期",
    2: "早期营养生长/分蘖期",
    3: "营养生长中期",
    4: "营养生长后期/孕穗期",
    5: "开花与生殖生长期/抽穗期",
    6: "花药开裂期",
    7: "灌浆与成熟期",
}
MODEL_DIR = PROJECT_ROOT / "results" / "growth_stage_initial"
WEIGHT_PATH = PROJECT_ROOT / "models" / "pretrained" / "fomo4wheat" / "FoMo4Wheat_base.pth"
_model_lock = threading.Lock()
_model = None
_extractor = None
_model_error: Exception | None = None


def _load_model():
    """按需加载模型，避免未启用时拖慢 FastAPI 启动。"""
    global _model, _extractor, _model_error
    if _model is not None and _extractor is not None:
        return _model, _extractor
    with _model_lock:
        if _model is not None and _extractor is not None:
            return _model, _extractor
        try:
            model_path = MODEL_DIR / "selected_model.joblib"
            if not model_path.is_file() or not WEIGHT_PATH.is_file():
                raise FileNotFoundError("分类器或 FoMo 权重文件不存在")
            # RTX 5060 当前独立环境的 CUDA wheel 不含 sm_120 内核，固定 CPU
            # 保证网页演示可用；以后更换兼容 wheel 时可通过环境变量切换。
            device = "cpu"
            _extractor = FoMo4WheatExtractor(WEIGHT_PATH, device=device)
            _model = joblib.load(model_path)
            if int(getattr(_model, "n_features_in_", 768)) != 768:
                raise ValueError("分类器特征维度不是 768")
            _model_error = None
            return _model, _extractor
        except Exception as error:  # noqa: BLE001 - 转换为明确的 API 错误
            _model_error = error
            raise AnalysisError(503, "GROWTH_STAGE_MODEL_UNAVAILABLE", "生育期模型暂未启用，无法生成分类结果。") from error


def model_status() -> dict[str, object]:
    """返回不执行推理的模型状态，用于健康信息和前端提示。"""
    return {
        "enabled": (MODEL_DIR / "selected_model.joblib").is_file() and WEIGHT_PATH.is_file() and _model_error is None,
        "model_version": "growth-stage-fomo-subset-20261114",
        "training_scope": "CGIAR 训练标签固定每类100张的分层初步实验",
        "limitations": ["验证集为 UID 分层切分，缺少可靠地块字段时无法排除地块泄漏", "模型来自 CGIAR 印度田间数据，未验证中国品种和手机域迁移"],
    }


def predict_growth_stage(data: bytes, filename: str, task_id: str, settings: Settings) -> dict[str, object]:
    """对一张 RGB 图像返回真实模型概率和分类结果。"""
    started = time.perf_counter()
    image, normalization = validate_and_decode(data, filename, settings)
    model, extractor = _load_model()
    result = extractor.extract_pil(image)
    features = result.features.reshape(1, -1)
    try:
        probabilities_array = model.predict_proba(features)[0]
        classes = [int(value) for value in model.classes_]
        probabilities = {STAGE_NAMES.get(stage, f"阶段{stage}"): float(probability) for stage, probability in zip(classes, probabilities_array)}
        predicted_stage = int(classes[int(np.argmax(probabilities_array))])
    except Exception as error:  # noqa: BLE001
        raise AnalysisError(500, "GROWTH_STAGE_INFERENCE_FAILED", "生育期模型推理失败，未生成结果。") from error
    elapsed = time.perf_counter() - started
    record = {
        "task_id": task_id,
        "status": "succeeded",
        "model_version": "growth-stage-fomo-subset-20261114",
        "predicted_stage": predicted_stage,
        "predicted_stage_name": STAGE_NAMES[predicted_stage],
        "probabilities": probabilities,
        "confidence": float(max(probabilities_array)),
        "inference_time_seconds": elapsed,
        "feature_extraction_time_seconds": result.inference_seconds,
        "width": image.width,
        "height": image.height,
        "device": result.device,
        "normalization": normalization,
        "label_source": "CGIAR Wheat Growth Stage Challenge train labels; subset experiment",
        "limitations": [
            "这是 CGIAR 数据上的初步七阶段分类模型，不等同于长势等级。",
            "未使用测试集标签进行评价；当前结果不能代表中国品种、地区或手机拍摄域的准确率。",
            "未来7/15/30天趋势预测模型尚未建立。",
        ],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    directory = settings.storage_root / "growth_stage" / task_id
    try:
        directory.mkdir(parents=True, exist_ok=False)
        image.save(directory / "original.png", format="PNG")
        (directory / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as error:
        raise AnalysisError(503, "STORAGE_UNAVAILABLE", "生育期分析结果无法保存。") from error
    return record
