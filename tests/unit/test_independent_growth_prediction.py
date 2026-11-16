from backend.app.independent_growth_prediction import predict_independent_growth


def test_independent_engine_returns_two_horizons_without_optional_models():
    result = predict_independent_growth({'vigor_score': 82, 'vigor_level': '较好', 'growth_stage': '拔节期', 'stage_confidence': 0.9, 'weather_status': 'unavailable'})
    assert result['status'] == 'succeeded'
    assert set(result['horizons']) == {'7', '15'}
    assert result['horizons']['7']['trend'] == '基本稳定'
    assert result['horizons']['7']['data_completeness']['status'] == 'missing'
    assert result['horizons']['7']['estimates']['status'] == 'exploratory_estimate'
    assert result['horizons']['7']['estimates']['vigor_score']['value'] != 82


def test_weather_changes_risk_and_advice():
    rows = [{'temperature_2m_max': 37, 'temperature_2m_min': 4, 'precipitation_sum': 0} for _ in range(7)]
    result = predict_independent_growth({'vigor_score': 55, 'vigor_level': '较弱', 'growth_stage': '抽穗开花期', 'stage_confidence': 0.8, 'weather_status': 'succeeded', 'weather_rows': rows})
    assert result['horizons']['7']['trend'] in {'可能变差', '风险较高'}
    assert result['horizons']['7']['weather_risks']
    assert result['agricultural_advice']['risk_flags']


def test_low_confidence_is_reported():
    result = predict_independent_growth({'vigor_score': 72, 'growth_stage': '拔节期', 'stage_confidence': 0.3, 'weather_status': 'unavailable'})
    assert result['horizons']['15']['confidence'] == '较低'
    assert any('置信度' in item for item in result['horizons']['15']['factors'])
