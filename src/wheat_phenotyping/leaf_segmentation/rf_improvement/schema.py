"""特征契约：顺序、公式、参数和实现摘要共同决定版本身份。"""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

from ..rf_features import FEATURE_NAMES

LEGACY_VERSION = "rf-legacy-7-v1"
CURRENT_VERSION = "rf-cts-v2"


@dataclass(frozen=True)
class FeatureConfig:
    """不可变配置；v1 只允许原始七维，不接受重配参数。"""

    version: str = CURRENT_VERSION
    color: bool = True
    texture: bool = True
    spatial: bool = True
    texture_window: int = 5
    spatial_windows: tuple[int, ...] = (9, 17)

    def __post_init__(self):
        if self.version not in (LEGACY_VERSION, CURRENT_VERSION):
            raise ValueError("未知特征版本")
        if any(type(v) is not bool for v in (self.color, self.texture, self.spatial)):
            raise ValueError("特征组开关必须为 bool")
        if not any((self.color, self.texture, self.spatial)):
            raise ValueError("至少启用一个特征组")
        if type(self.texture_window) is not int or self.texture_window < 1 or self.texture_window % 2 != 1:
            raise ValueError("纹理窗口必须为正奇数")
        if (type(self.spatial_windows) is not tuple or not self.spatial_windows
                or any(type(w) is not int or w < 1 or w % 2 != 1 for w in self.spatial_windows)
                or tuple(sorted(set(self.spatial_windows))) != self.spatial_windows):
            raise ValueError("空间窗口必须为非空、递增且不重复的正奇数 tuple")
        if self.version == LEGACY_VERSION and (
            not all((self.color, self.texture, self.spatial))
            or self.texture_window != 5 or self.spatial_windows != (9, 17)
        ):
            raise ValueError("旧版七维配置固定，不能切换特征或窗口")

    @classmethod
    def from_dict(cls, data: dict):
        """恢复 JSON 配置，保留严格的字段校验。"""
        values = dict(data)
        if isinstance(values.get("spatial_windows"), list):
            values["spatial_windows"] = tuple(values["spatial_windows"])
        return cls(**values)


def feature_schema(config: FeatureConfig = FeatureConfig()) -> dict:
    """返回独立字典；schema_id 覆盖排列、公式、窗口和实现内容。"""
    if not isinstance(config, FeatureConfig):
        raise TypeError("config 必须为 FeatureConfig")
    legacy = config.version == LEGACY_VERSION
    if legacy:
        names = list(FEATURE_NAMES)
        formulas = {"legacy": "delegated unchanged to rf_features.extract_pixel_features"}
        radius = 2
        sources = [Path(__file__).parent.parent / "rf_features.py"]
    else:
        names = []
        if config.color:
            names += ["red", "green", "blue", "hue_sin_saturation", "hue_cos_saturation",
                      "saturation", "value", "excess_green"]
        if config.texture:
            names += [f"local_gray_mean_{config.texture_window}x{config.texture_window}",
                      f"local_gray_std_{config.texture_window}x{config.texture_window}", "gray_gradient_magnitude"]
        if config.spatial:
            names += [f"local_{c}_mean_{w}x{w}" for w in config.spatial_windows for c in ("red", "green", "blue")]
        formulas = {"rgb": "uint8 RGB / 255", "hsv": "S*sin(H radians), S*cos(H radians), S, V; H periodic; S=0 implies hue components=0",
                    "exg": "(2*g-r-b)/2, range [-1,1]", "gray": "0.299*r+0.587*g+0.114*b",
                    "texture": "mean(gray), sqrt(max(mean(gray*gray)-mean(gray)**2,0)), hypot(sobel_y,sobel_x)/8",
                    "spatial": "independent per-channel RGB means at configured windows"}
        radius = max([0] + ([max(config.texture_window // 2, 1)] if config.texture else [])
                     + ([max(config.spatial_windows) // 2] if config.spatial else []))
        sources = [Path(__file__).with_name("features.py"), Path(__file__)]
    body = {"version": config.version, "names": names, "dimension": len(names),
            "config": json.loads(json.dumps(asdict(config))), "channel_order": "RGB",
            "dtype": "float32", "layout": "row-major (H*W,D)", "padding": "nearest",
            "max_radius": radius, "formulas": formulas,
            "implementation_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in sources)).hexdigest()}
    body["schema_id"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body
