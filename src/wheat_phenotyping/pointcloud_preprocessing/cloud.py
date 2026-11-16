"""点云数据结构、CSV 读写和体素网格下采样基线。"""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PointCloud:
    """点云坐标采用米制 XYZ；labels 可选，缺失标签以 None 表示。"""

    points: tuple[tuple[float, float, float], ...]
    labels: tuple[int | None, ...] | None = None

    def __post_init__(self) -> None:
        if self.labels is not None and len(self.labels) != len(self.points):
            raise ValueError("点标签数量必须与点数一致")
        for point in self.points:
            if len(point) != 3 or not all(math.isfinite(value) for value in point):
                raise ValueError("点坐标必须由三个有限数值组成")

    def __len__(self) -> int:
        return len(self.points)


def read_point_cloud_csv(path: str | Path) -> PointCloud:
    """读取包含 x_m/y_m/z_m 列的 CSV；可选读取 leaf_id 标签列。"""
    points: list[tuple[float, float, float]] = []
    labels: list[int | None] = []
    has_label = False
    with Path(path).open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"x_m", "y_m", "z_m"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("点云 CSV 必须包含 x_m、y_m、z_m 列")
        has_label = "leaf_id" in reader.fieldnames
        for line_number, row in enumerate(reader, start=2):
            try:
                point = (float(row["x_m"]), float(row["y_m"]), float(row["z_m"]))
                if not all(math.isfinite(value) for value in point):
                    continue
                label_value = row.get("leaf_id") if has_label else None
                label = int(label_value) if label_value not in (None, "") else None
            except (TypeError, ValueError) as error:
                # 无效行跳过；错误内容和行号保留，避免静默误读格式错误。
                raise ValueError(f"第 {line_number} 行点云数据无效") from error
            points.append(point)
            labels.append(label)
    return PointCloud(tuple(points), tuple(labels) if has_label else None)


def write_point_cloud_csv(cloud: PointCloud, path: str | Path) -> None:
    """将点云写入米制 XYZ CSV，可选写入叶片标签。"""
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        columns = ["x_m", "y_m", "z_m"] + (["leaf_id"] if cloud.labels is not None else [])
        writer = csv.writer(stream)
        writer.writerow(columns)
        for index, point in enumerate(cloud.points):
            row: list[object] = [f"{value:.8f}" for value in point]
            if cloud.labels is not None:
                row.append("" if cloud.labels[index] is None else cloud.labels[index])
            writer.writerow(row)


def voxel_downsample(cloud: PointCloud, voxel_size_m: float) -> PointCloud:
    """按立方体体素聚合点坐标质心，标签使用体素内多数票。"""
    if not math.isfinite(voxel_size_m) or voxel_size_m <= 0:
        raise ValueError("voxel_size_m 必须是大于 0 的有限数值")
    sums: dict[tuple[int, int, int], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
    label_counts: dict[tuple[int, int, int], Counter[int]] = defaultdict(Counter)
    for index, point in enumerate(cloud.points):
        key = tuple(math.floor(value / voxel_size_m) for value in point)
        accumulator = sums[key]
        for axis, value in enumerate(point):
            accumulator[axis] += value
        accumulator[3] += 1
        if cloud.labels is not None and cloud.labels[index] is not None:
            label_counts[key][cloud.labels[index]] += 1
    keys = sorted(sums)
    reduced = tuple(
        tuple(sums[key][axis] / sums[key][3] for axis in range(3))
        for key in keys
    )
    if cloud.labels is None:
        return PointCloud(reduced)
    reduced_labels = tuple(
        min(label_counts[key], key=lambda label: (-label_counts[key][label], label))
        if label_counts[key] else None
        for key in keys
    )
    return PointCloud(reduced, reduced_labels)
