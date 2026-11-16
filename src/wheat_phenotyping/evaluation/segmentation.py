"""语义分割评价指标：IoU、Precision、Recall 和 F1-score。"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from wheat_phenotyping.leaf_segmentation import BinaryMask


@dataclass(frozen=True)
class SegmentationMetrics:
    """二值分割混淆计数和由计数计算的指标。"""

    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    iou: float
    precision: float
    recall: float
    f1_score: float

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def evaluate_binary_masks(prediction: BinaryMask, reference: BinaryMask) -> SegmentationMetrics:
    """比较预测和人工标注掩膜；空掩膜约定见文档。

    两张掩膜都为空时四项指标记为 1（完全一致）；仅分母为零时对应比率记为 0。
    尺寸不一致或掩膜类型无效时抛出 ValueError，不进行缩放或静默转换。
    """
    if not isinstance(prediction, BinaryMask) or not isinstance(reference, BinaryMask):
        raise ValueError("预测掩膜和参考掩膜必须是 BinaryMask")
    if (prediction.width, prediction.height) != (reference.width, reference.height):
        raise ValueError("预测掩膜和参考掩膜尺寸不一致；评价前请核对图像与标注")
    if any(value not in (0, 255) for value in prediction.pixels + reference.pixels):
        raise ValueError("掩膜标签无效：只接受 0 和 255")

    tp = fp = fn = tn = 0
    for predicted, actual in zip(prediction.pixels, reference.pixels):
        predicted_foreground = predicted == 255
        actual_foreground = actual == 255
        if predicted_foreground and actual_foreground:
            tp += 1
        elif predicted_foreground:
            fp += 1
        elif actual_foreground:
            fn += 1
        else:
            tn += 1
    union = tp + fp + fn
    if union == 0:
        # 双空掩膜表示前景预测和标注完全一致。
        iou = precision = recall = f1 = 1.0
    else:
        iou = tp / union
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
    return SegmentationMetrics(tp, fp, fn, tn, iou, precision, recall, f1)
