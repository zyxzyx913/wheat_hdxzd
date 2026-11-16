"""Compatibility entry point for the independent short-term growth engine."""
from __future__ import annotations

from .independent_growth_prediction import predict_independent_growth


def predict_growth_trend(payload: dict[str, object]) -> dict[str, object]:
    return predict_independent_growth(payload)
