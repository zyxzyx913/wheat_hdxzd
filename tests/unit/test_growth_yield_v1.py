import pytest
from backend.app.growth_trend_prediction_service import predict_growth_trend
from backend.app.yield_estimation_service import calculate_yield_estimation


def test_growth_trend_without_weather_is_unavailable():
    result = predict_growth_trend({'growth_stage': '拔节期', 'stage_confidence': 0.4, 'weather_status': 'unavailable'})
    assert result['horizons']['7']['trend'] == '暂无法判断'
    assert set(result['horizons']) == {'7', '15'}
    assert result['version'] == 'independent-growth-v1.0-rule'


def test_yield_unit_conversion_and_profit():
    result = calculate_yield_estimation({'area_mu': 10, 'low_yield_kg_per_mu': 300, 'normal_yield_kg_per_mu': 450, 'high_yield_kg_per_mu': 600, 'price_yuan_per_ton': 2000, 'cost_yuan_per_mu': 500})
    assert result['scenarios']['normal']['total_yield_ton'] == pytest.approx(4.5)
    assert result['scenarios']['normal']['revenue_yuan'] == pytest.approx(9000)
    assert result['scenarios']['normal']['profit_yuan'] == pytest.approx(4000)


def test_yield_rejects_invalid_order():
    with pytest.raises(ValueError):
        calculate_yield_estimation({'area_mu': 1, 'low_yield_kg_per_mu': 500, 'normal_yield_kg_per_mu': 400, 'high_yield_kg_per_mu': 600, 'price_yuan_per_ton': 2000, 'cost_yuan_per_mu': 500})
