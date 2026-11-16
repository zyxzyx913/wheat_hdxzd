"""规则型农事建议：只给出可追溯的观察重点，不给出剂量处方。"""
from __future__ import annotations


def build_agricultural_advice(*, vigor_level: str | None, coverage: float | None, greenness: float | None, uniformity_cv: float | None, stage: str | None, stage_confidence: float | None, weather_risks: list[str] | None, location: str | None) -> dict[str, object]:
    low_confidence = stage_confidence is not None and stage_confidence < 0.5
    stage_note = "生育期置信度较低，以下建议按图像表观状态提供，需人工确认。" if low_confidence else "建议按当前识别生育期复核田间情况。"
    strengths = []
    concerns = []
    if vigor_level: strengths.append(f"当前图像表观长势为{vigor_level}。")
    if coverage is not None and coverage < 0.2: concerns.append("可见植被覆盖偏低，建议复核缺苗、拍摄角度和群体均匀性。")
    if greenness is not None and greenness < 0.35: concerns.append("可见区域绿色程度偏低，建议结合叶片黄化和营养状况进行田间复核。")
    if uniformity_cv is not None and uniformity_cv > 0.8: concerns.append("图像空间分布不均，建议检查田间出苗和地块差异。")
    risks = weather_risks or []
    if risks: concerns.extend(risks)
    stage_focus = "结合当前生育期复核群体、水分和温度变化。"
    if stage and any(key in stage for key in ("分蘖", "营养生长")): stage_focus = "当前阶段重点观察苗情、群体均匀性和水肥管理效果。"
    elif stage and "拔节" in stage: stage_focus = "当前阶段重点观察温度变化、水分状态和倒伏风险。"
    elif stage and "孕穗" in stage: stage_focus = "当前阶段重点观察低温和群体生长状态。"
    elif stage and any(key in stage for key in ("抽穗", "开花")): stage_focus = "当前阶段重点观察高温、干热风和降水风险。"
    elif stage and any(key in stage for key in ("灌浆", "成熟")): stage_focus = "当前阶段重点观察高温、干旱和灌浆环境。"
    return {
        "status": "screening_advice",
        "summary": "".join(strengths) or "当前图像已完成分析，建议结合田间记录复核。",
        "current_concerns": concerns or ["暂未发现可由当前输入确认的突出风险。"],
        "seven_day_focus": [stage_focus, "根据未来天气筛查结果安排巡田，天气风险仅作提示。"],
        "fifteen_day_focus": ["持续观察生育期变化和群体状态，不把情景分析视为定量预测。"],
        "thirty_day_reference": ["当前没有经过验证的长期生长预测，建议作为气候风险参考。"],
        "risk_flags": risks,
        "basis": ["V1.1 图像表观指标", "当前生育期模型输出（如可用）", "天气筛查规则（未完成中国小麦田间校准）"],
        "limitations": [stage_note, "未提供土壤检测、施肥记录和当地农技参数，不给出肥料、农药或灌溉剂量。", f"地点：{location}" if location else "未提供地点，无法进行区域化农事解释。"],
    }
