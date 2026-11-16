"""仅提供模型契约校验和读取；不包含训练或推理实现。"""

import hashlib
import json
from pathlib import Path
import re

import joblib

from .schema import FeatureConfig, LEGACY_VERSION, feature_schema


def validate_model_features(model, config: FeatureConfig, metadata: dict) -> None:
    """版本、顺序、参数及实现摘要均须一致，不能只检查维数。"""
    expected = feature_schema(config)
    if metadata.get("feature_schema") != expected:
        raise ValueError("模型特征版本/schema 不匹配（名称、顺序、参数或实现摘要不同）")
    if getattr(model, "n_features_in_", None) != expected["dimension"]:
        raise ValueError("模型特征维度不匹配")
    if hasattr(model, "feature_names_in_") and list(model.feature_names_in_) != expected["names"]:
        raise ValueError("模型特征名称或顺序不匹配")


def build_model_metadata(model, config: FeatureConfig, model_sha256: str) -> dict:
    """供未来保存模型时生成 sidecar，不写文件、不训练模型。"""
    if not isinstance(model_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", model_sha256) is None:
        raise ValueError("需要模型文件的 SHA-256")
    metadata = {"feature_schema": feature_schema(config), "model_sha256": model_sha256}
    validate_model_features(model, config, metadata)
    return metadata


def load_feature_model(model_path, metadata_path, config: FeatureConfig, *,
                       allow_legacy_metadata: bool = False, expected_model_sha256: str | None = None):
    """读取可信本地模型；新格式校验 SHA，历史格式需显式授权和已知 SHA。

    joblib 只能读取可信产物；摘要用于绑定文件，不能把不可信 pickle 变安全。
    旧元数据没有特征版本，故只允许明确指定旧版、校验历史名称和调用方给定摘要。
    """
    metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8-sig"))
    expected = feature_schema(config)
    historical = "feature_schema" not in metadata
    if historical:
        if (not allow_legacy_metadata or config.version != LEGACY_VERSION
                or metadata.get("model_name") != "RF-Color-Texture"
                or metadata.get("features") != expected["names"]
                or expected_model_sha256 is None):
            raise ValueError("旧模型缺少版本契约，必须显式指定旧版、已知摘要和匹配的训练特征顺序")
        bound = {"feature_schema": expected, "model_sha256": expected_model_sha256}
    else:
        bound = metadata
    if bound.get("feature_schema") != expected:
        raise ValueError("模型特征版本/schema 不匹配")
    digest = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    if bound.get("model_sha256") != digest or (expected_model_sha256 is not None and expected_model_sha256 != digest):
        raise ValueError("模型文件 SHA-256 不匹配")
    model = joblib.load(model_path)
    validate_model_features(model, config, bound)
    return model
