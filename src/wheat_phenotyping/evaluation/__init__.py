"""独立的二值分割评价模块。"""

from .batch import EvaluationSample, ImageEvaluation, evaluate_batch, summarize_by_dataset
from .calibration import CalibrationResult, CandidateScore, calibrate_candidates, write_calibration_outputs
from .mask_io import read_binary_pgm
from .reporting import write_evaluation_outputs
from .segmentation import SegmentationMetrics, evaluate_binary_masks

__all__ = [
    "EvaluationSample",
    "ImageEvaluation",
    "CalibrationResult",
    "CandidateScore",
    "calibrate_candidates",
    "SegmentationMetrics",
    "evaluate_batch",
    "evaluate_binary_masks",
    "read_binary_pgm",
    "summarize_by_dataset",
    "write_evaluation_outputs",
    "write_calibration_outputs",
]

