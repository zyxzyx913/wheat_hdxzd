"""WOFOST 情景配置，只保存情景偏移，不制造天气观测。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherScenario:
    name: str
    temperature_offset_c: float = 0.0
    precipitation_multiplier: float = 1.0


SCENARIOS = (
    WeatherScenario("normal"),
    WeatherScenario("dry", precipitation_multiplier=0.7),
    WeatherScenario("wet", precipitation_multiplier=1.3),
    WeatherScenario("warm", temperature_offset_c=2.0),
)
