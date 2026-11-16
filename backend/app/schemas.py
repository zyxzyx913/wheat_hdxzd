"""四种传统分割算法的统一单图响应，所有数值来自实际计算。"""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

AlgorithmName = Literal["ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion"]

class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    task_id: str
    status: Literal["succeeded"] = "succeeded"
    algorithm: AlgorithmName = "ExG"
    input_sha256: str
    original_url: str
    mask_url: str
    overlay_url: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    vegetation_pixel_count: int = Field(ge=0)
    total_valid_pixels: int = Field(gt=0)
    vegetation_ratio: float = Field(ge=0, le=1)
    analysis_time_seconds: float = Field(ge=0)
    segmentation_time_seconds: float = Field(ge=0)
    parameters: dict[str, int | float | str]
    algorithm_metadata: dict[str, object] = Field(default_factory=dict)
    profile_id: str
    created_at_utc: str
    warnings: list[str]
    # V1 仅返回可解释的图像代理指标，不包含长势等级或未来预测。
    growth_analysis: dict[str, object] | None = None
    growth_analysis_url: str | None = None
    # V1.1 规则初评；没有足够图像质量时等级可以为空。
    vigor_score: float | None = Field(default=None, ge=0, le=100)
    vigor_level: str | None = None
    coverage_score: float | None = Field(default=None, ge=0, le=100)
    greenness_score: float | None = Field(default=None, ge=0, le=100)
    uniformity_score: float | None = Field(default=None, ge=0, le=100)
    reliability: str | None = None
    strengths: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    evaluation_version: str | None = None


class GrowthStageResult(BaseModel):
    """冻结 FoMo 特征 + 轻量分类头的单图生育期响应。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    task_id: str
    status: Literal["succeeded"] = "succeeded"
    model_version: str
    predicted_stage: int = Field(ge=1, le=7)
    predicted_stage_name: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)
    inference_time_seconds: float = Field(ge=0)
    feature_extraction_time_seconds: float = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    device: str
    normalization: dict[str, object]
    label_source: str
    limitations: list[str]
    created_at_utc: str


class GrowthAnalyzeResult(BaseModel):
    """V2.0 当前长势一体化响应。"""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    analysis_id: str
    task_id: str
    plot_id: str | None = Field(default=None, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    status: Literal["succeeded"] = "succeeded"
    algorithm: AlgorithmName
    original_url: str
    mask_url: str
    overlay_url: str
    input_sha256: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    vegetation_pixel_count: int = Field(ge=0)
    total_valid_pixels: int = Field(gt=0)
    vegetation_ratio: float = Field(ge=0, le=1)
    analysis_time_seconds: float = Field(ge=0)
    segmentation_time_seconds: float = Field(ge=0)
    parameters: dict[str, int | float | str]
    algorithm_metadata: dict[str, object] = Field(default_factory=dict)
    profile_id: str
    created_at_utc: str
    growth_analysis_url: str | None = None
    vegetation_coverage: dict[str, object]
    vigor_score: float = Field(ge=0, le=100)
    vigor_level: str | None = None
    coverage_score: float = Field(ge=0, le=100)
    greenness_score: float = Field(ge=0, le=100)
    uniformity_score: float = Field(ge=0, le=100)
    reliability: str
    strengths: list[str]
    improvement_suggestions: list[str]
    growth_stage: dict[str, object] | None = None
    growth_stage_status: str
    model_version: str
    evaluation_version: str
    processing_time: float = Field(ge=0)
    growth_analysis: dict[str, object]
    warnings: list[str]


class AnnotationTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anonymous_id: str
    dataset: str
    split: str
    source_image_id: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    pixel_count: int = Field(gt=0)
    task_status: str


class AnnotationRecordInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anonymous_id: str
    annotator_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    label: Literal["较好", "一般", "较弱", "无法判断"]
    growth_stage: str | None = Field(default=None, max_length=80)
    quality_flags: list[str] = Field(default_factory=list, max_length=12)
    rationale: str = Field(default="", max_length=500)
    confidence: int | None = Field(default=None, ge=1, le=3)
    review_round: int = Field(default=1, ge=1)


class AnnotationRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    anonymous_id: str
    annotator_id: str
    label: str
    growth_stage: str
    quality_flags: str
    rationale: str
    annotated_at_utc: str
    confidence: str
    review_round: str


class AdjudicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anonymous_id: str
    final_label: Literal["较好", "一般", "较弱", "无法判断", ""] = ""
    review_status: Literal["待复核", "已复核", "无法形成共识"]
    reviewer_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    review_note: str = Field(default="", max_length=500)


class AdjudicationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anonymous_id: str
    final_label: str
    review_status: str
    reviewer_id: str
    reviewed_at_utc: str
    review_note: str
