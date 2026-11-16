"""Web 工程限额与既有冻结参数的只读加载。"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_ALGORITHMS = ("ExG", "HSV", "Otsu-ExG", "ExG-HSV Fusion")


@dataclass(frozen=True)
class Settings:
    """限额属于软件容量保护，不是分割或农学判定阈值。"""

    storage_root: Path = PROJECT_ROOT / "var" / "web"
    parameters_path: Path = PROJECT_ROOT / "configs/segmentation/desktop_frozen_defaults.json"
    calibration_path: Path = PROJECT_ROOT / "results/ews/validation_calibration/selected_parameters.json"
    max_file_bytes: int = 10 * 1024 * 1024
    max_pixels: int = 4_000_000
    max_dimension: int = 4096

    @property
    def max_request_bytes(self) -> int:
        # 为 multipart 文件名、头部与分隔符保留少量空间。
        return self.max_file_bytes + 64 * 1024


def load_algorithm_profile(settings: Settings, algorithm: str) -> dict:
    """逐算法核对验证集冻结参数；某一配置失败不影响其他算法。"""
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise ValueError("不支持的网页分割算法")
    config_bytes = settings.parameters_path.read_bytes()
    calibration_bytes = settings.calibration_path.read_bytes()
    parameters = json.loads(config_bytes)["algorithm_parameters"][algorithm]
    if not isinstance(parameters, dict) or parameters != json.loads(calibration_bytes)[algorithm]:
        raise ValueError(f"{algorithm} 配置与原验证集冻结参数不一致")
    if algorithm == "ExG":
        if set(parameters) != {"exg_threshold", "min_component_area"}:
            raise ValueError("ExG 冻结参数字段不完整")
        if any(type(value) is not int for value in parameters.values()):
            raise ValueError("ExG 冻结参数必须为整数")
        if not -510 <= parameters["exg_threshold"] <= 510 or parameters["min_component_area"] < 0:
            raise ValueError("ExG 冻结参数范围无效")
    # HSV、Otsu 与 Fusion 的参数语义仍由原有算法校验，不在 Web 层复制实现。
    slug = algorithm.lower().replace(" ", "-")
    return {
        "parameters": parameters,
        "profile_id": f"ews-validation-{slug}-" + hashlib.sha256(calibration_bytes).hexdigest()[:12],
        "parameters_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "calibration_sha256": hashlib.sha256(calibration_bytes).hexdigest(),
        "parameter_source": "results/ews/validation_calibration/selected_parameters.json",
    }


def load_exg_profile(settings: Settings) -> dict:
    """保留原单算法调用接口，默认算法仍为 ExG。"""
    return load_algorithm_profile(settings, "ExG")
