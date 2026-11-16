"""新旧 RF 特征数值与契约测试；仅使用程序构造的测试图，不训练模型。"""

from dataclasses import replace
from itertools import product
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile

import joblib
import numpy as np
import pytest

from wheat_phenotyping.rgb_preprocessing import RGBImage
from wheat_phenotyping.leaf_segmentation.hsv import rgb_to_hsv
from wheat_phenotyping.leaf_segmentation.rf_features import extract_pixel_features, FEATURE_NAMES
from wheat_phenotyping.leaf_segmentation.rf_improvement import (
    FeatureConfig, feature_schema, extract_features, iter_feature_bands,
    build_model_metadata, validate_model_features, load_feature_model,
)
from wheat_phenotyping.leaf_segmentation.rf_improvement.schema import LEGACY_VERSION


def image(width=11, height=19):
    """固定种子的 RGB 测试夹具，不是小麦实验数据。"""
    data = np.random.default_rng(7).integers(0, 256, (height, width, 3), dtype=np.uint8)
    return RGBImage(width, height, data.tobytes())


@pytest.mark.parametrize("width,height", [(1, 1), (1, 21), (23, 1), (2, 3), (11, 19), (37, 271)])
def test_legacy_exact_values_and_schema(width, height):
    rgb = image(width, height)
    config = FeatureConfig(version=LEGACY_VERSION)
    np.testing.assert_array_equal(extract_features(rgb, config), extract_pixel_features(rgb))
    schema = feature_schema(config)
    assert schema["names"] == list(FEATURE_NAMES)
    assert schema["dimension"] == 7 and schema["max_radius"] == 2


@pytest.mark.parametrize("color,texture,spatial", [c for c in product([False, True], repeat=3) if any(c)])
def test_combinations_fixed_order_and_dimensions(color, texture, spatial):
    config = FeatureConfig(color=color, texture=texture, spatial=spatial)
    rgb = image()
    full = extract_features(rgb)
    selected = extract_features(rgb, config)
    indices = ([*range(8)] if color else []) + ([8, 9, 10] if texture else []) + ([*range(11, 17)] if spatial else [])
    np.testing.assert_array_equal(selected, full[:, indices])
    assert selected.shape == (209, 8 * color + 3 * texture + 6 * spatial)
    assert selected.dtype == np.float32 and selected.flags.c_contiguous
    assert np.isfinite(selected).all()
    assert feature_schema(config)["names"] == [feature_schema()["names"][i] for i in indices]


def test_channel_order_exg_and_hsv_against_existing_scalar():
    colors = np.vstack([np.array([[255, 0, 0], [0, 255, 0], [0, 0, 255], [0, 0, 0],
                                [255, 255, 255], [120, 120, 120], [200, 200, 10], [200, 10, 200]], dtype=np.uint8),
                        np.random.default_rng(12).integers(0, 256, (200, 3), dtype=np.uint8)])
    actual = extract_features(RGBImage(len(colors), 1, colors.tobytes()), FeatureConfig(texture=False, spatial=False))
    expected = []
    for pixel in colors:
        r, g, b = [int(x) for x in pixel]
        h, s, v = rgb_to_hsv(r, g, b)
        expected.append([r/255, g/255, b/255, s*np.sin(np.deg2rad(h)), s*np.cos(np.deg2rad(h)), s, v, (2*g-r-b)/510])
    np.testing.assert_allclose(actual, expected, atol=6e-7, rtol=1e-5)
    np.testing.assert_array_equal(actual[3:6, 3:5], 0)
    assert actual[0, 7] == -0.5 and actual[1, 7] == 1.0


def test_hue_wraparound_is_continuous():
    rgb = RGBImage(2, 1, bytes([255, 0, 1, 255, 1, 0]))
    features = extract_features(rgb)
    assert np.linalg.norm(features[0, 3:5] - features[1, 3:5]) < 0.01


def test_texture_matches_old_formula_and_nearest_border_oracle():
    rgb = image(3, 2)
    result = extract_features(rgb)
    old = extract_pixel_features(rgb)
    np.testing.assert_array_equal(result[:, 8:11], old[:, 4:7])
    # 独立的边界算例：左上角取 nearest 延拓后的 3×3 RGB 均值。
    config = FeatureConfig(color=False, texture=False, spatial_windows=(3,))
    spatial = extract_features(rgb, config).reshape(2, 3, 3)
    source = np.frombuffer(rgb.pixels, np.uint8).reshape(2, 3, 3) / 255
    padded = np.pad(source, ((1, 1), (1, 1), (0, 0)), mode="edge")
    for y in range(2):
        for x in range(3):
            np.testing.assert_allclose(spatial[y, x], padded[y:y+3, x:x+3].mean(axis=(0, 1)), atol=1e-7)


@pytest.mark.parametrize("size", [(1, 1), (1, 5), (17, 1), (5, 9), (31, 277)])
@pytest.mark.parametrize("config", [FeatureConfig(), FeatureConfig(color=False),
                                      FeatureConfig(texture_window=7, spatial_windows=(5, 21)),
                                      FeatureConfig(version=LEGACY_VERSION)])
def test_deterministic_finite_and_band_consistency(size, config):
    rgb = image(*size)
    whole = extract_features(rgb, config)
    np.testing.assert_array_equal(whole, extract_features(rgb, config))
    bands = list(iter_feature_bands(rgb, config, band_height=3))
    assert bands[0][0] == 0 and bands[-1][1] == rgb.height
    np.testing.assert_array_equal(whole, np.concatenate([b[2] for b in bands]))
    assert np.isfinite(whole).all()


def test_constant_images_and_large_windows():
    for pixel in [(0, 0, 0), (255, 255, 255), (0, 255, 0)]:
        result = extract_features(RGBImage(1, 1, bytes(pixel)))
        assert np.isfinite(result).all()
        np.testing.assert_array_equal(result[:, 9:11], 0)
        np.testing.assert_array_equal(result[0, 11:14], result[0, :3])


@pytest.mark.parametrize("kwargs", [dict(version="unknown"), dict(color=1),
    dict(color=False, texture=False, spatial=False), dict(texture_window=0), dict(texture_window=4),
    dict(texture_window=True), dict(spatial_windows=()), dict(spatial_windows=(9, 9)),
    dict(spatial_windows=(17, 9)), dict(spatial_windows=(2,)), dict(spatial_windows=[9, 17]),
    dict(version=LEGACY_VERSION, spatial=False), dict(version=LEGACY_VERSION, texture_window=7)])
def test_invalid_configs(kwargs):
    with pytest.raises(ValueError):
        FeatureConfig(**kwargs)


def test_config_json_roundtrip_and_schema_identity():
    config = FeatureConfig(texture_window=7, spatial_windows=(5, 11))
    schema = feature_schema(config)
    assert FeatureConfig.from_dict(json.loads(json.dumps(schema))["config"]) == config
    assert feature_schema(config) == schema
    assert feature_schema(replace(config, texture_window=9))["schema_id"] != schema["schema_id"]
    assert schema["max_radius"] == 5
    assert schema["dtype"] == "float32" and schema["channel_order"] == "RGB" and schema["padding"] == "nearest"


def test_invalid_inputs_and_nonfinite_guard(monkeypatch):
    with pytest.raises(TypeError):
        extract_features(np.zeros((2, 2, 3)))
    with pytest.raises(ValueError):
        extract_features(RGBImage(1, 1, [np.nan, np.inf, 0]))
    with pytest.raises(ValueError):
        RGBImage(2, 3, b"bad")
    with pytest.raises(TypeError):
        extract_features(image(), {})
    with pytest.raises(ValueError):
        list(iter_feature_bands(image(), band_height=0))
    # 注入非有限计算结果，确认输出门禁不会静默放行。
    import wheat_phenotyping.leaf_segmentation.rf_improvement.features as module
    for invalid in [np.nan, np.inf]:
        with monkeypatch.context() as patch:
            patch.setattr(module, "uniform_filter", lambda array, **kw: np.full_like(array, invalid))
            with np.errstate(invalid="ignore"):
                with pytest.raises(ValueError, match="NaN"):
                    extract_features(image(), FeatureConfig(color=False, texture=False))


def test_model_contract_dimension_version_order_and_parameters():
    config = FeatureConfig()
    # 只模拟契约字段；不是训练产物，不输出任何实验分数。
    model = SimpleNamespace(n_features_in_=17)
    metadata = build_model_metadata(model, config, "a" * 64)
    validate_model_features(model, config, metadata)
    with pytest.raises(ValueError, match="维度"):
        validate_model_features(SimpleNamespace(n_features_in_=8), config, metadata)
    for field, value in [("version", LEGACY_VERSION), ("padding", "reflect"),
                         ("dtype", "float64"), ("names", list(reversed(metadata["feature_schema"]["names"])) )]:
        changed = json.loads(json.dumps(metadata))
        changed["feature_schema"][field] = value
        with pytest.raises(ValueError, match="schema"):
            validate_model_features(model, config, changed)
    with pytest.raises(ValueError, match="schema"):
        validate_model_features(model, replace(config, texture_window=7), metadata)
    with pytest.raises(ValueError, match="顺序"):
        validate_model_features(SimpleNamespace(n_features_in_=17, feature_names_in_=["wrong"]*17), config, metadata)


def test_loader_checks_metadata_hash_and_actual_dimension():
    import hashlib
    config = FeatureConfig()
    # 使用项目工作区临时目录，避免受限 Windows 运行时系统 Temp 的清理权限问题。
    local_tmp = Path(__file__).resolve().parents[2] / ".test-tmp"
    local_tmp.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rf_feature_contract_", dir=local_tmp) as folder:
        root = Path(folder)
        model_path, meta_path = root / "stub.joblib", root / "stub.json"
        joblib.dump(SimpleNamespace(n_features_in_=17), model_path)
        digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
        metadata = build_model_metadata(SimpleNamespace(n_features_in_=17), config, digest)
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        assert load_feature_model(model_path, meta_path, config).n_features_in_ == 17
        with pytest.raises(ValueError, match="schema"):
            load_feature_model(model_path, meta_path, replace(config, texture_window=7))
        with pytest.raises(ValueError, match="SHA-256"):
            load_feature_model(model_path, meta_path, config, expected_model_sha256="0"*64)
        joblib.dump(SimpleNamespace(n_features_in_=8), model_path)
        metadata["model_sha256"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        meta_path.write_text(json.dumps(metadata), encoding="utf-8")
        with pytest.raises(ValueError, match="维度"):
            load_feature_model(model_path, meta_path, config)


def test_existing_model_explicit_legacy_load_and_original_inference():
    from wheat_phenotyping.app.inference import predict_visible_mask
    root = Path(__file__).resolve().parents[2]
    model_path = root / "results/ews/rf_training/rf_color_texture.joblib"
    metadata_path = model_path.with_name("training_metadata.json")
    digest = "61d388a4bd7809ddda3d668c5b19a39af6bd43b80d44eedca5bd756c85f14d85"
    config = FeatureConfig(version=LEGACY_VERSION)
    with pytest.raises(ValueError, match="旧模型"):
        load_feature_model(model_path, metadata_path, config)
    with pytest.raises(ValueError, match="旧模型"):
        load_feature_model(model_path, metadata_path, FeatureConfig(), allow_legacy_metadata=True, expected_model_sha256=digest)
    model = load_feature_model(model_path, metadata_path, config, allow_legacy_metadata=True, expected_model_sha256=digest)
    rgb = image(5, 7)
    mask, _ = predict_visible_mask(rgb, "RF-Color-Texture", model=model)
    positive = model.predict_proba(extract_features(rgb, config))[:, list(model.classes_).index(1)]
    expected = np.where(positive >= 0.75, 255, 0).astype(np.uint8)
    np.testing.assert_array_equal(np.frombuffer(mask.pixels, np.uint8), expected)
