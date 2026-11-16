"""按植株/地块等 group 进行确定性训练、验证、测试划分。"""

from __future__ import annotations

import random
from collections import defaultdict

from .manifest import DatasetRecord, VALID_SPLITS, validate_records, with_split


def split_by_group(
    records: list[DatasetRecord],
    *,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
) -> list[DatasetRecord]:
    """在每个数据集版本内按 group 划分，固定 seed 可复现，禁止 group 泄漏。

    每个数据集版本需要至少三个独立 group，且三个比例都须大于零。
    组大小不等时实际样本比例可能偏离目标，调用方应检查输出统计。
    """
    ratios = {"train": train_ratio, "validation": validation_ratio, "test": test_ratio}
    if any(value <= 0 for value in ratios.values()) or abs(sum(ratios.values()) - 1.0) > 1e-8:
        raise ValueError("train/validation/test 比例必须均大于 0 且总和为 1")
    if not records:
        raise ValueError("不能划分空数据集")
    buckets: dict[tuple[str, str], dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for index, row in enumerate(records):
        if not row.group_id:
            raise ValueError(f"样本 {row.sample_id} 缺少 group_id，无法防止数据泄漏")
        buckets[(row.dataset_name, row.dataset_version)][row.group_id].append(index)
    rng = random.Random(seed)
    assignments: dict[int, str] = {}
    split_order = ("train", "validation", "test")
    for dataset_key, groups in sorted(buckets.items()):
        if len(groups) < 3:
            raise ValueError(f"数据集 {dataset_key} 只有 {len(groups)} 个 group，无法分为三组")
        shuffled_groups = list(groups.items())
        rng.shuffle(shuffled_groups)
        shuffled_groups.sort(key=lambda item: len(item[1]), reverse=True)
        counts = {name: 0 for name in split_order}
        for group_index, (_group_id, indices) in enumerate(shuffled_groups):
            if group_index < 3:
                target_split = split_order[group_index]
            else:
                # 按各集合当前样本量/目标比例的归一负载分配，避免所有余组都堆到 train。
                target_split = min(split_order, key=lambda name: (counts[name] / ratios[name], split_order.index(name)))
            counts[target_split] += len(indices)
            for index in indices:
                assignments[index] = target_split
    result = [with_split(record, assignments[index]) for index, record in enumerate(records)]
    # 拆分后的记录仍必须满足无 group 跨集合。
    validate_records(result, check_files=False)
    return result


def split_counts(records: list[DatasetRecord]) -> dict[str, int]:
    """返回每个集合的样本数。"""
    counts = {name: 0 for name in VALID_SPLITS}
    for row in records:
        if row.split not in VALID_SPLITS:
            raise ValueError(f"样本 {row.sample_id} 尚未设置有效划分")
        counts[row.split] += 1
    return counts
