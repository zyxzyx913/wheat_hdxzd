"""生育期初步实验产物的可追溯性检查，不把产物当作准确率承诺。"""
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "results" / "growth_stage_initial"


def test_growth_stage_artifacts_have_frozen_feature_contract():
    metadata = json.loads((ARTIFACTS / "experiment_metadata.json").read_text(encoding="utf-8"))
    mapping = json.loads((ARTIFACTS / "class_mapping.json").read_text(encoding="utf-8-sig"))
    assert metadata["status"] == "initial_subset_experiment"
    assert metadata["feature_dimension"] == 768
    assert metadata["seed"] == 20261114
    assert metadata["sample_count"] == 700
    assert set(mapping) == {str(index) for index in range(1, 8)}
    assert metadata["selected_model"] in metadata["models"]


def test_growth_stage_feature_cache_is_finite_and_matches_metadata():
    metadata = json.loads((ARTIFACTS / "experiment_metadata.json").read_text(encoding="utf-8"))
    cached = np.load(ARTIFACTS / "fomo_features_subset.npz", allow_pickle=True)
    assert cached["X"].shape == (metadata["sample_count"], metadata["feature_dimension"])
    assert cached["y"].shape == (metadata["sample_count"],)
    assert np.isfinite(cached["X"]).all()
    assert set(np.unique(cached["y"])) == set(range(1, 8))
