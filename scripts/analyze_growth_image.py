"""对单张 PPM 小麦图像计算可见特征并按显式阈值输出等级。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from wheat_phenotyping.leaf_segmentation import segment_leaves_exg
from wheat_phenotyping.phenotyping import (
    GrowthGradeThresholds,
    classify_visible_growth,
    extract_visible_growth_features,
)
from wheat_phenotyping.rgb_preprocessing import preprocess_rgb, read_ppm


def main() -> None:
    """读取参数、运行基线链路并保存机器可读结果。"""
    parser = argparse.ArgumentParser(description="小麦图像可见长势特征与规则等级分析")
    parser.add_argument("image", type=Path, help="输入 PPM P3/P6 图像")
    parser.add_argument("--weak-max", type=float, required=True, help="弱势等级绿色面积比例上限")
    parser.add_argument("--moderate-max", type=float, required=True, help="中势等级绿色面积比例上限")
    parser.add_argument("--exg-threshold", type=int, default=20, help="ExG 分割阈值")
    parser.add_argument("--min-component-area", type=int, default=0, help="移除小连通域的像素面积阈值")
    parser.add_argument("--data-source", choices=("simulated", "public", "real"), required=True)
    parser.add_argument("--output", type=Path, help="结果 JSON 路径；缺省时输出到控制台")
    args = parser.parse_args()

    thresholds = GrowthGradeThresholds(args.weak_max, args.moderate_max)
    image = preprocess_rgb(read_ppm(args.image))
    mask = segment_leaves_exg(
        image,
        exg_threshold=args.exg_threshold,
        min_component_area=args.min_component_area,
    )
    features = extract_visible_growth_features(image, mask)
    result = classify_visible_growth(features, thresholds, data_source=args.data_source)
    payload = {
        "data_source": args.data_source,
        "image_path": str(args.image),
        "grade": result.grade,
        "interpretation": result.interpretation,
        "features": asdict(features),
        "classification": asdict(result),
        "segmentation": {
            "method": "ExG threshold",
            "exg_threshold": args.exg_threshold,
            "min_component_area": args.min_component_area,
        },
    }
    output = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
