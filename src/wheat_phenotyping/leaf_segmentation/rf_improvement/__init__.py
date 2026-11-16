"""独立 RF 特征接口；不替换旧模型或旧推理入口。"""

from .schema import FeatureConfig, feature_schema
from .features import extract_features, iter_feature_bands
from .model import build_model_metadata, load_feature_model, validate_model_features

__all__ = ["FeatureConfig", "feature_schema", "extract_features", "iter_feature_bands",
           "build_model_metadata", "load_feature_model", "validate_model_features"]
