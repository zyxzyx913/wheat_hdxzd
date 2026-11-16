"""多标注者长势标签一致性计算，不生成或修改任何标签。"""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Iterable


LABELS = ("较好", "一般", "较弱", "无法判断")


def _cohen_kappa(left: list[str], right: list[str]) -> float | None:
    if not left or len(left) != len(right):
        return None
    observed = sum(a == b for a, b in zip(left, right)) / len(left)
    left_counts, right_counts = Counter(left), Counter(right)
    expected = sum((left_counts[label] / len(left)) * (right_counts[label] / len(right)) for label in LABELS)
    if expected == 1:
        return 1.0 if observed == 1 else 0.0
    return (observed - expected) / (1 - expected)


def _fleiss_kappa(item_labels: list[list[str]]) -> float | None:
    usable = [labels for labels in item_labels if len(labels) >= 2]
    if not usable:
        return None
    n = len(usable[0])
    if any(len(labels) != n for labels in usable):
        # Fleiss 公式要求每个项目的标注数相同；不等数时返回不可用，避免误算。
        return None
    counts = [[labels.count(category) for category in LABELS] for labels in usable]
    p_items = [(sum(value * value for value in row) - n) / (n * (n - 1)) for row in counts]
    p_bar = sum(p_items) / len(p_items)
    total = len(usable) * n
    p_categories = [sum(row[index] for row in counts) / total for index in range(len(LABELS))]
    p_expected = sum(value * value for value in p_categories)
    if p_expected == 1:
        return 1.0 if p_bar == 1 else 0.0
    return (p_bar - p_expected) / (1 - p_expected)


def calculate_annotation_consistency(rows: Iterable[dict]) -> dict[str, object]:
    """计算独立标注的一致性；不做多数投票、不生成最终标签。"""
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    record_count = 0
    for row in rows:
        label = str(row.get("label", ""))
        annotator = str(row.get("annotator_id", ""))
        if label in LABELS and row.get("anonymous_id") and annotator:
            grouped[str(row["anonymous_id"])][annotator] = label
            record_count += 1
    comparable = [values for values in grouped.values() if len(values) >= 2]
    annotator_ids = sorted({annotator for values in grouped.values() for annotator in values})
    pair_kappas = []
    for left_annotator, right_annotator in combinations(annotator_ids, 2):
        pairs = [(values[left_annotator], values[right_annotator]) for values in comparable if left_annotator in values and right_annotator in values]
        if pairs:
            pair_kappas.append(_cohen_kappa([pair[0] for pair in pairs], [pair[1] for pair in pairs]))
    cohen = None
    if len(annotator_ids) == 2:
        cohen = pair_kappas[0] if pair_kappas else None
    item_labels = [list(values.values()) for values in comparable]
    conflict_count = sum(len(set(values.values())) > 1 for values in comparable)
    status = "ready" if comparable else "waiting_for_multiple_annotators" if record_count else "insufficient_annotations"
    observation_pair_count = sum(1 for values in comparable for _ in combinations(sorted(values), 2))
    return {
        "status": status,
        "annotation_record_count": record_count,
        "annotated_image_count": len(grouped),
        "annotator_count": len(annotator_ids),
        "annotator_ids": annotator_ids,
        "comparable_image_count": len(comparable),
        "conflict_image_count": conflict_count,
        # 保留旧字段语义：可比较的图片-标注者配对数量；κ本身仍按标注者对计算。
        "cohen_kappa_pair_count": observation_pair_count,
        "cohen_kappa_mean": sum(value for value in pair_kappas if value is not None) / len(pair_kappas) if pair_kappas else None,
        "cohen_kappa": cohen,
        "pairwise_cohen_kappa_mean": sum(value for value in pair_kappas if value is not None) / len([value for value in pair_kappas if value is not None]) if any(value is not None for value in pair_kappas) else None,
        "fleiss_kappa": _fleiss_kappa(item_labels),
        "label_counts": dict(Counter(label for values in grouped.values() for label in values.values())),
        "note": "一致性指标只描述标注者意见，不自动产生 adjudicated_labels.csv。",
    }
