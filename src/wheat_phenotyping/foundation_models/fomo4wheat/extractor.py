"""FoMo4Wheat ViT-B/14 特征提取适配器。

模型文件是官方发布的序列化 DINOv2 backbone，不包含长势/器官/产量任务头。
本模块只输出归一化前的 768 维 CLS token，不生成任何农学预测结果。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import time

import numpy as np
from PIL import Image, UnidentifiedImageError


OFFICIAL_MODEL_VERSION = "FoMo4Wheat ViT-B/14 base"
OFFICIAL_WEIGHT_URL = "https://huggingface.co/PheniX-Lab/FoMo4Wheat/resolve/main/weight/FoMo4Wheat_base.pth"
EXPECTED_FEATURE_DIMENSION = 768
EXPECTED_SHA256 = "5d996c01a8b99f58bf136d94abf65a54f86e3fd51572d1c1c121dbc7ade3dbcf"


@dataclass(frozen=True)
class FomoFeatureResult:
    """单张图片的可追溯 embedding 结果。"""

    features: np.ndarray
    feature_dimension: int
    model_version: str
    device: str
    inference_seconds: float
    image_width: int
    image_height: int
    preprocessing: str
    weight_sha256: str


def official_preprocess(image: Image.Image):
    """复用官方 DINOv2 分类评估预处理：Resize 256、CenterCrop 224、ImageNet 归一化。"""
    try:
        from torchvision import transforms
    except ImportError as error:
        raise RuntimeError("FoMo 独立环境缺少 torchvision") from error
    return transforms.Compose([
        transforms.Resize(256, interpolation=transforms.InterpolationMode.BICUBIC),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])(image.convert("RGB"))


def _load_image(path: str | Path) -> Image.Image:
    try:
        with Image.open(path) as opened:
            opened.load()
            return opened.convert("RGB")
    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError(f"RGB 图片读取失败：{path}") from error


def _device(device: str, torch):
    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError("device 必须是 auto、cpu 或 cuda")
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("请求 CUDA，但 torch.cuda.is_available() 为 False")
    return torch.device("cuda" if device == "auto" and torch.cuda.is_available() else device if device != "auto" else "cpu")


class FoMo4WheatExtractor:
    """加载官方序列化 backbone，并提取 CLS embedding。"""

    def __init__(self, weight_path: str | Path, *, device: str = "auto", verify_sha256: bool = True):
        try:
            import torch
        except ImportError as error:
            raise RuntimeError("当前环境未安装 PyTorch，请使用 .venv-fomo") from error
        self.torch = torch
        self.weight_path = Path(weight_path).resolve()
        if not self.weight_path.is_file():
            raise FileNotFoundError(f"FoMo 权重不存在：{self.weight_path}")
        self.weight_sha256 = hashlib.sha256(self.weight_path.read_bytes()).hexdigest()
        if verify_sha256 and self.weight_sha256 != EXPECTED_SHA256:
            raise ValueError(f"FoMo 权重 SHA-256 不匹配：{self.weight_sha256}")
        self.device = _device(device, torch)
        try:
            model = torch.load(self.weight_path, map_location="cpu", weights_only=False)
        except Exception as error:
            raise RuntimeError("FoMo 官方权重加载失败；请确认 dinov2 与官方权重版本匹配") from error
        if not hasattr(model, "forward_features") or getattr(model, "embed_dim", None) != EXPECTED_FEATURE_DIMENSION:
            raise ValueError("加载的权重不是预期 FoMo4Wheat ViT-B/14 backbone")
        self.model = model.to(self.device).eval()

    def extract(self, image_path: str | Path) -> FomoFeatureResult:
        """对一张 JPG/JPEG/PNG 进行确定性特征提取。"""
        image = _load_image(image_path)
        return self.extract_pil(image)

    def extract_pil(self, image: Image.Image) -> FomoFeatureResult:
        """对已经安全解码的 PIL 图像提取特征，供 Web API 避免临时文件。"""
        image = image.convert("RGB")
        tensor = official_preprocess(image).unsqueeze(0).to(self.device)
        started = time.perf_counter()
        try:
            with self.torch.inference_mode():
                output = self.model.forward_features(tensor)
                features = output["x_norm_clstoken"]
            array = features.detach().float().cpu().numpy()
        except Exception as error:
            raise RuntimeError(f"FoMo {self.device} 特征提取失败：{error}") from error
        elapsed = time.perf_counter() - started
        if array.shape != (1, EXPECTED_FEATURE_DIMENSION) or not np.isfinite(array).all():
            raise ValueError(f"FoMo 特征输出异常：shape={array.shape}")
        return FomoFeatureResult(
            features=array[0], feature_dimension=array.shape[1], model_version=OFFICIAL_MODEL_VERSION,
            device=str(self.device), inference_seconds=elapsed, image_width=image.width,
            image_height=image.height, preprocessing="official_eval_resize256_centercrop224_imagenet_norm",
            weight_sha256=self.weight_sha256,
        )
