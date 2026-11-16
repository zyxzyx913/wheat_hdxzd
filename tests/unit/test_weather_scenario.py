from backend.app.weather_scenario_service import screen_weather_risks


def test_weather_screening_is_explicitly_unvalidated():
    weather = {"rows": [{"temperature_2m_max": 36, "temperature_2m_min": 2, "precipitation_sum": 1}]}
    result = screen_weather_risks(weather, 7)
    assert result["status"] == "screening_only"
    assert result["threshold_status"] == "unvalidated_project_screening"
    assert "高温筛查标记" in result["flags"]


def test_empty_weather_is_unavailable():
    assert screen_weather_risks({"rows": []}, 7)["status"] == "unavailable"
