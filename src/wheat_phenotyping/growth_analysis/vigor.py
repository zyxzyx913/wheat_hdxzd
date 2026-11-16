"""可解释的表观长势初评规则。

这里的分数是图像代理指标的规则组合，不是深度学习模型，也不是经过农学试验
校准的长势标准。所有阈值和权重都显式保存，便于后续专家标签校准。
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class VigorAssessmentConfig:
    """V1.1 演示规则的可配置参数。"""

    coverage_reference_fraction: float = 0.75
    uniformity_cv_max: float = 1.5
    coverage_weight: float = 0.45
    greenness_weight: float = 0.35
    uniformity_weight: float = 0.20
    good_threshold: float = 80.0
    average_threshold: float = 60.0

    def __post_init__(self) -> None:
        if self.coverage_reference_fraction <= 0 or self.uniformity_cv_max <= 0:
            raise ValueError("覆盖率参考值和均匀度上限必须为正数")
        weights = (self.coverage_weight, self.greenness_weight, self.uniformity_weight)
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("长势评分权重必须为非负数且总和为 1")
        if not (0 <= self.average_threshold < self.good_threshold <= 100):
            raise ValueError("长势等级阈值必须满足 0 <= 一般阈值 < 较好阈值 <= 100")


def _clip_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _level(score: float) -> str:
    if score >= 80:
        return "长势较好"
    if score >= 60:
        return "长势一般"
    return "长势较弱"


def assess_vigor(metrics: dict[str, Any], *, config: VigorAssessmentConfig = VigorAssessmentConfig()) -> dict[str, Any]:
    """从 V1 指标计算 V1.1 表观长势初评。"""
    if not isinstance(config, VigorAssessmentConfig):
        raise TypeError("config 必须为 VigorAssessmentConfig")
    coverage = metrics["vegetation_coverage"]
    green = metrics["green_degree"]
    uniformity = metrics["distribution_uniformity"]
    quality = metrics["image_quality"]

    coverage_fraction = float(coverage["fraction"])
    green_ratio = green["mean_green_channel_ratio"]
    cv = uniformity["coefficient_of_variation"]
    coverage_score = _clip_score(coverage_fraction / config.coverage_reference_fraction * 100)
    greenness_score = 0.0 if green_ratio is None else _clip_score(float(green_ratio) * 100)
    uniformity_score = 0.0 if cv is None else _clip_score((1.0 - float(cv) / config.uniformity_cv_max) * 100)
    contributions = {
        "coverage": coverage_score * config.coverage_weight,
        "greenness": greenness_score * config.greenness_weight,
        "uniformity": uniformity_score * config.uniformity_weight,
    }
    score = _clip_score(sum(contributions.values()))

    risks = list(quality.get("risk_flags", []))
    no_foreground = int(coverage.get("vegetation_pixel_count", 0)) == 0
    blocking_reasons = []
    if no_foreground:
        blocking_reasons.append("没有检测到可见植被前景")
    if any("偏暗" in risk for risk in risks):
        blocking_reasons.append("画面偏暗")
    if any("过曝" in risk for risk in risks):
        blocking_reasons.append("画面过曝")
    # 模糊会降低可靠性，但单独出现时保留分数，避免把质量参考误当成作物长势。
    reliability_score = max(0.0, 1.0 - 0.35 * len(blocking_reasons) - 0.20 * sum("模糊" in risk for risk in risks))
    if blocking_reasons:
        reliability = "较低"
    elif risks:
        reliability = "中等"
    else:
        reliability = "较高"
    level = None if blocking_reasons else _level(score)

    strengths = []
    suggestions = []
    component_scores = {
        "coverage_score": coverage_score,
        "greenness_score": greenness_score,
        "uniformity_score": uniformity_score,
    }
    labels = {"coverage_score": "植被覆盖", "greenness_score": "绿色程度", "uniformity_score": "空间均匀度"}
    for key, label in labels.items():
        if component_scores[key] >= 70:
            strengths.append(f"{label}表现较好")
        elif component_scores[key] < 60:
            suggestions.append(f"{label}偏低，建议结合更稳定的光照和拍摄角度复查")
    if not strengths and not blocking_reasons:
        strengths.append("当前图像未显示出明显的单项优势")
    if blocking_reasons:
        suggestions = ["请在光照均匀、对焦清晰且植株完整可见的条件下重新拍摄"]
    if not suggestions and not blocking_reasons:
        suggestions.append("当前图像代理指标未发现需要优先复查的项目")

    return {
        "status": "completed" if level else "insufficient_quality",
        "evaluation_version": "growth-vigor-v1.1-rule",
        "vigor_score": score,
        "vigor_level": level,
        "coverage_score": coverage_score,
        "greenness_score": greenness_score,
        "uniformity_score": uniformity_score,
        "reliability": reliability,
        "reliability_score": reliability_score,
        "strengths": strengths,
        "improvement_suggestions": suggestions,
        "quality_blocking_reasons": blocking_reasons,
        "scoring": {
            "formula": "score = 0.45×coverage_score + 0.35×greenness_score + 0.20×uniformity_score",
            "weights": {
                "coverage": config.coverage_weight,
                "greenness": config.greenness_weight,
                "uniformity": config.uniformity_weight,
            },
            "normalized_scores": component_scores,
            "contributions": contributions,
            "thresholds": {
                "coverage_reference_fraction": config.coverage_reference_fraction,
                "uniformity_cv_max": config.uniformity_cv_max,
                "good": config.good_threshold,
                "average": config.average_threshold,
                "weak": 0.0,
            },
            "config": asdict(config),
        },
        "interpretation": "图像表观长势初评；尚未进行生育期校正和专家标签校准，不等同于农学诊断。",
    }
