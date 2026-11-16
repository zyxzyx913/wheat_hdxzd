"""生成带已知几何真值的小麦单株模拟 RGB 图像与三维点云。

本生成器用于软件流程开发和模拟数据实验，不代表真实小麦的外观或测量精度。
图像采用 PPM/PGM 格式，点云采用 CSV 格式，避免依赖专用相机或扫描仪。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class SimulationConfig:
    """单株模型与传感缺陷参数；长度单位为米。"""

    seed: int = 7
    leaf_count: int = 5
    plant_height_m: float = 0.35
    leaf_width_m: float = 0.018
    points_per_leaf: int = 500
    image_width: int = 512
    image_height: int = 512
    pixel_noise: int = 0
    point_noise_m: float = 0.0
    occlusion_fraction: float = 0.0
    missing_point_fraction: float = 0.0

    def validate(self) -> None:
        """检查参数范围，避免生成无效图像或点云。"""
        if self.leaf_count < 1 or self.points_per_leaf < 1:
            raise ValueError("leaf_count 和 points_per_leaf 必须大于 0")
        if self.plant_height_m <= 0 or self.leaf_width_m <= 0:
            raise ValueError("植株高度和叶宽必须大于 0")
        if self.image_width < 64 or self.image_height < 64:
            raise ValueError("图像宽高不能小于 64 像素")
        if not 0 <= self.pixel_noise <= 255:
            raise ValueError("pixel_noise 必须在 0 到 255 之间")
        if self.point_noise_m < 0:
            raise ValueError("point_noise_m 不能为负数")
        for name in ("occlusion_fraction", "missing_point_fraction"):
            if not 0 <= getattr(self, name) < 1:
                raise ValueError(f"{name} 必须在 0 到 1 之间")


def _leaf_center(t: float, angle: float, height: float) -> tuple[float, float, float]:
    """给出叶片中心线上的一点，t 从叶基 0 变化到叶尖 1。"""
    radial = 0.015 + 0.18 * t
    z = 0.015 + height * (0.25 * t + 0.75 * math.sin(t * math.pi / 2))
    return radial * math.cos(angle), radial * math.sin(angle), z


def _leaf_width(t: float, max_width: float) -> float:
    """叶片在基部和尖端收窄，中段较宽。"""
    return max_width * (0.08 + 0.92 * math.sin(math.pi * t) ** 0.7)


def _write_ppm(path: Path, width: int, height: int, pixels: bytearray) -> None:
    with path.open("wb") as stream:
        stream.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        stream.write(pixels)


def _write_pgm(path: Path, width: int, height: int, pixels: bytearray) -> None:
    with path.open("wb") as stream:
        stream.write(f"P5\n{width} {height}\n255\n".encode("ascii"))
        stream.write(pixels)


def generate_sample(output_dir: str | Path, config: SimulationConfig) -> dict:
    """生成一个模拟样本及其参数和真值标签，返回真值字典。"""
    config.validate()
    rng = random.Random(config.seed)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    width, height = config.image_width, config.image_height
    rgb = bytearray([245, 242, 232] * width * height)
    mask = bytearray(width * height)
    all_points: list[tuple[float, float, float, int]] = []
    leaves = []
    scale = min(width, height) * 0.39

    for leaf_id in range(config.leaf_count):
        angle = 2 * math.pi * leaf_id / config.leaf_count + 0.15
        leaf_height = config.plant_height_m * (0.65 + 0.30 * rng.random())
        centerline = []
        for step in range(101):
            t = step / 100
            x, y, z = _leaf_center(t, angle, leaf_height)
            centerline.append((x, y, z, t))
            # 正交俯视投影，中心点对应植株基部。
            px = int(width / 2 + x * scale / 0.22)
            py = int(height * 0.88 - z * scale / config.plant_height_m)
            radius = max(1, int(_leaf_width(t, config.leaf_width_m) * scale / 0.22 / 2))
            green = (42 + leaf_id * 5, 112 + leaf_id * 4, 35)
            for yy in range(max(0, py - radius), min(height, py + radius + 1)):
                for xx in range(max(0, px - radius), min(width, px + radius + 1)):
                    if (xx - px) ** 2 + (yy - py) ** 2 <= radius * radius:
                        idx = yy * width + xx
                        rgb[3 * idx:3 * idx + 3] = bytes(green)
                        mask[idx] = 255

        leaves.append({
            "leaf_id": leaf_id,
            "azimuth_rad": angle,
            "length_m": leaf_height,
            "max_width_m": config.leaf_width_m,
            "centerline_xyz_m": [[round(v, 6) for v in row[:3]] for row in centerline[::10]],
        })

        for _ in range(config.points_per_leaf):
            t = rng.random()
            x, y, z = _leaf_center(t, angle, leaf_height)
            lateral = (rng.random() - 0.5) * _leaf_width(t, config.leaf_width_m)
            # 叶片横向单位向量与方位角垂直。
            x += -math.sin(angle) * lateral
            y += math.cos(angle) * lateral
            x += rng.gauss(0, config.point_noise_m)
            y += rng.gauss(0, config.point_noise_m)
            z += rng.gauss(0, config.point_noise_m)
            all_points.append((x, y, z, leaf_id))

    # 矩形遮挡区域同时作用于 RGB 和分割真值掩膜。
    occlusion = None
    if config.occlusion_fraction > 0:
        occ_w = max(1, int(width * math.sqrt(config.occlusion_fraction)))
        occ_h = max(1, int(height * math.sqrt(config.occlusion_fraction)))
        x0 = rng.randrange(max(1, width - occ_w + 1))
        y0 = rng.randrange(max(1, height - occ_h + 1))
        for yy in range(y0, min(height, y0 + occ_h)):
            for xx in range(x0, min(width, x0 + occ_w)):
                idx = yy * width + xx
                rgb[3 * idx:3 * idx + 3] = bytes((110, 110, 110))
                mask[idx] = 0
        occlusion = {"x": x0, "y": y0, "width": occ_w, "height": occ_h}

    if config.pixel_noise:
        for i in range(len(rgb)):
            rgb[i] = max(0, min(255, rgb[i] + rng.randint(-config.pixel_noise, config.pixel_noise)))

    keep_count = int(len(all_points) * (1 - config.missing_point_fraction))
    rng.shuffle(all_points)
    all_points = all_points[:keep_count]
    points_path = out / "point_cloud.csv"
    with points_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["x_m", "y_m", "z_m", "leaf_id"])
        writer.writerows((f"{x:.6f}", f"{y:.6f}", f"{z:.6f}", leaf) for x, y, z, leaf in all_points)

    _write_ppm(out / "rgb.ppm", width, height, rgb)
    _write_pgm(out / "leaf_mask.pgm", width, height, mask)
    truth = {
        "data_source": "simulated",
        "sample_id": f"wheat_sim_seed_{config.seed}",
        "coordinate_frame": "plant_base_origin_xyz_m",
        "image_projection": "orthographic_xz",
        "units": "meter",
        "plant": {"leaf_count": config.leaf_count, "height_m": config.plant_height_m},
        "leaves": leaves,
        "point_count_before_missing": config.leaf_count * config.points_per_leaf,
        "point_count_after_missing": len(all_points),
        "occlusion_rectangle_px": occlusion,
        "files": {"rgb": "rgb.ppm", "leaf_mask": "leaf_mask.pgm", "point_cloud": "point_cloud.csv"},
    }
    (out / "ground_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "generation_parameters.json").write_text(
        json.dumps({"data_source": "simulated", **asdict(config)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return truth


def main(argv: Sequence[str] | None = None) -> None:
    """命令行入口，生成单个可复现模拟样本。"""
    parser = argparse.ArgumentParser(description="生成小麦单株模拟 RGB、点云及真值标签")
    parser.add_argument("--output", type=Path, required=True, help="样本输出目录")
    parser.add_argument("--seed", type=int, default=7, help="随机种子")
    parser.add_argument("--leaves", type=int, default=5, help="叶片数量")
    parser.add_argument("--height", type=float, default=0.35, help="株高（米）")
    parser.add_argument("--pixel-noise", type=int, default=0, help="RGB 通道噪声幅度")
    parser.add_argument("--point-noise", type=float, default=0.0, help="点云高斯噪声标准差（米）")
    parser.add_argument("--occlusion", type=float, default=0.0, help="图像遮挡比例，范围 [0,1)")
    parser.add_argument("--missing-points", type=float, default=0.0, help="点云缺失比例，范围 [0,1)")
    args = parser.parse_args(argv)
    cfg = SimulationConfig(
        seed=args.seed, leaf_count=args.leaves, plant_height_m=args.height,
        pixel_noise=args.pixel_noise, point_noise_m=args.point_noise,
        occlusion_fraction=args.occlusion, missing_point_fraction=args.missing_points,
    )
    generate_sample(args.output, cfg)


if __name__ == "__main__":
    main()
