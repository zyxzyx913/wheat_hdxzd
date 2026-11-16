from backend.app.agricultural_advice_service import build_agricultural_advice


def test_advice_is_non_prescriptive_and_confidence_aware():
    result = build_agricultural_advice(vigor_level="长势一般", coverage=0.1, greenness=0.2, uniformity_cv=1.0, stage="拔节期", stage_confidence=0.3, weather_risks=["高温筛查标记"], location="河南")
    assert result["status"] == "screening_advice"
    assert any("置信度较低" in item for item in result["limitations"])
    assert any("高温" in item for item in result["risk_flags"])
    assert any("剂量" in item for item in result["limitations"])
