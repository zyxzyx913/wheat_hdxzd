"""数据集 CSV 清单读取、校验和写出。"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from pathlib import Path

VALID_SPLITS = {"train", "validation", "test"}
VALID_SOURCES = {"public", "real", "simulated"}
MANIFEST_FIELDS = (
    "sample_id", "dataset_name", "dataset_version", "group_id", "split",
    "image_path", "reference_mask_path", "data_source",
)


@dataclass(frozen=True)
class DatasetRecord:
    """一个具有数据来源、分组标识和可选人工掩膜的数据样本。"""

    sample_id: str
    dataset_name: str
    dataset_version: str
    group_id: str
    split: str
    image_path: Path
    reference_mask_path: Path
    data_source: str

    def to_dict(self, root: Path | None = None) -> dict[str, str]:
        """转成清单 CSV 行；路径可相对 root 序列化。"""
        def path_text(path: Path) -> str:
            if root is not None:
                try:
                    return path.relative_to(root).as_posix()
                except ValueError:
                    pass
            return str(path)
        return {
            "sample_id": self.sample_id,
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "group_id": self.group_id,
            "split": self.split,
            "image_path": path_text(self.image_path),
            "reference_mask_path": path_text(self.reference_mask_path),
            "data_source": self.data_source,
        }


def validate_records(
    records: list[DatasetRecord], *, check_files: bool = True, allow_unassigned: bool = False
) -> None:
    """检查必填元数据、样本重复、文件存在性和 group 泄漏。"""
    if not records:
        raise ValueError("数据清单没有样本记录")
    seen_samples: set[tuple[str, str, str]] = set()
    group_splits: dict[tuple[str, str, str], set[str]] = {}
    for index, record in enumerate(records, start=1):
        required = (record.sample_id, record.dataset_name, record.dataset_version, record.group_id)
        if any(not value or not value.strip() for value in required):
            raise ValueError(f"第 {index} 条记录缺少样本、数据集、版本或 group_id")
        if record.split not in VALID_SPLITS and not (allow_unassigned and record.split == "unassigned"):
            raise ValueError(f"样本 {record.sample_id} 划分无效：{record.split}")
        if record.data_source not in VALID_SOURCES:
            raise ValueError(f"样本 {record.sample_id} 来源无效：{record.data_source}")
        sample_key = (record.dataset_name, record.dataset_version, record.sample_id)
        if sample_key in seen_samples:
            raise ValueError(f"样本 ID 重复：{sample_key}")
        seen_samples.add(sample_key)
        group_key = (record.dataset_name, record.dataset_version, record.group_id)
        group_splits.setdefault(group_key, set()).add(record.split)
        if check_files:
            if not record.image_path.is_file():
                raise ValueError(f"图像文件不存在：{record.image_path}")
            if not record.reference_mask_path.is_file():
                raise ValueError(f"人工标注掩膜不存在：{record.reference_mask_path}")
    leaked = {key: splits for key, splits in group_splits.items() if len(splits) > 1}
    if leaked:
        key, splits = next(iter(leaked.items()))
        raise ValueError(f"同一 group 跨数据划分：{key} -> {sorted(splits)}")


def read_manifest(path: str | Path, *, require_split: bool = True, check_files: bool = True) -> list[DatasetRecord]:
    """读取 UTF-8 CSV；image/mask 路径相对 CSV 文件所在目录解析。"""
    source = Path(path).resolve()
    required = {"sample_id", "dataset_name", "dataset_version", "group_id", "image_path", "reference_mask_path", "data_source"}
    if require_split:
        required.add("split")
    records = []
    with source.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"清单必须包含列：{sorted(required)}")
        for line_number, row in enumerate(reader, start=2):
            missing = [name for name in required if not row.get(name, "").strip()]
            if missing:
                raise ValueError(f"清单第 {line_number} 行缺少字段：{missing}")
            split = row.get("split", "").strip() or "unassigned"
            records.append(DatasetRecord(
                sample_id=row["sample_id"].strip(),
                dataset_name=row["dataset_name"].strip(),
                dataset_version=row["dataset_version"].strip(),
                group_id=row["group_id"].strip(),
                split=split,
                image_path=(source.parent / row["image_path"].strip()).resolve(),
                reference_mask_path=(source.parent / row["reference_mask_path"].strip()).resolve(),
                data_source=row["data_source"].strip(),
            ))
    if require_split or check_files:
        validate_records(records, check_files=check_files, allow_unassigned=not require_split)
    return records


def write_manifest(records: list[DatasetRecord], path: str | Path, *, relative_to: str | Path | None = None) -> None:
    """保存数据清单 CSV，绝不生成或修改图像及标注。"""
    validate_records(records, check_files=False, allow_unassigned=bool(records) and all(row.split == "unassigned" for row in records))
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    root = Path(relative_to).resolve() if relative_to else None
    with destination.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(record.to_dict(root) for record in records)


def with_split(record: DatasetRecord, split: str) -> DatasetRecord:
    """返回仅划分字段不同的新记录。"""
    if split not in VALID_SPLITS:
        raise ValueError(f"无效数据划分：{split}")
    return replace(record, split=split)
