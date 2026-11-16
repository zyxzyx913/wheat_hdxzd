"""合并同一 EWS test 划分的四个传统基线与随机森林汇总。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from xml.sax.saxutils import escape


def combine(
    baseline_csv: Path,
    rf_csv: Path,
    baseline_images_csv: Path,
    rf_images_csv: Path,
    output_dir: Path,
) -> tuple[Path, Path]:
    """确认数据集/样本数一致后输出五算法汇总 CSV 与 F1 SVG。"""
    with baseline_csv.open("r", newline="", encoding="utf-8-sig") as stream:
        baseline = list(csv.DictReader(stream))
    with rf_csv.open("r", newline="", encoding="utf-8-sig") as stream:
        rf_rows = list(csv.DictReader(stream))
    with baseline_images_csv.open("r", newline="", encoding="utf-8-sig") as stream:
        baseline_images = list(csv.DictReader(stream))
    with rf_images_csv.open("r", newline="", encoding="utf-8-sig") as stream:
        rf_images = list(csv.DictReader(stream))
    if len(rf_rows) != 1:
        raise ValueError("随机森林汇总 CSV 必须恰好包含一个算法")
    combined = baseline + rf_rows
    required = {(row["dataset_name"], row["dataset_version"], row["split"], row["sample_count"], row["successful_count"]) for row in combined}
    if len(required) != 1 or any(row["split"] != "test" or row["failed_count"] != "0" for row in combined):
        raise ValueError("实验数据集、test 划分、样本数或成功状态不一致")
    if len({row["algorithm_name"] for row in combined}) != 5:
        raise ValueError("汇总必须有五种互不重复的算法")
    baseline_samples = {row["sample_id"] for row in baseline_images}
    rf_samples = {row["sample_id"] for row in rf_images}
    if len(baseline_images) != 4 * int(combined[0]["sample_count"]) or len(rf_images) != int(combined[0]["sample_count"]):
        raise ValueError("逐图评价记录数与算法数或汇总样本数不一致")
    if baseline_samples != rf_samples or len(rf_samples) != int(combined[0]["sample_count"]):
        raise ValueError("五种算法没有评价完全相同的 test 图像")
    if any(row["double_empty_count"] != combined[0]["double_empty_count"] for row in combined):
        raise ValueError("算法间双空图数量不同")

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "five_algorithm_test_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(combined[0]))
        writer.writeheader()
        writer.writerows(combined)

    svg_path = output_dir / "five_algorithm_macro_f1.svg"
    width, height = 1000, 560
    left, top, chart_w, chart_h = 90, 70, 850, 390
    colors = ("#3465A4", "#73A857", "#C47A28", "#8D63A8", "#279A91")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="500" y="34" text-anchor="middle" font-family="sans-serif" font-size="22">EWS test: macro F1 (mean ± SD)</text>',
    ]
    for tick in range(0, 11):
        value = tick / 10
        y = top + chart_h * (1 - value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#dddddd"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 5:.1f}" text-anchor="end" font-family="sans-serif" font-size="12">{value:.1f}</text>')
    bar_w, gap = 105, 55
    offset = left + 30
    for index, row in enumerate(combined):
        x = offset + index * (bar_w + gap)
        mean = float(row["macro_f1_score"])
        std = float(row["std_f1_score"])
        bar_h = mean * chart_h
        y = top + chart_h - bar_h
        color = colors[index % len(colors)]
        parts.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" fill="{color}"/>')
        mid_y = top + chart_h * (1 - mean)
        half_error = std * chart_h
        parts.append(f'<line x1="{x + bar_w / 2}" y1="{mid_y - half_error:.1f}" x2="{x + bar_w / 2}" y2="{mid_y + half_error:.1f}" stroke="#222" stroke-width="2"/>')
        parts.append(f'<line x1="{x + 35}" y1="{mid_y - half_error:.1f}" x2="{x + 70}" y2="{mid_y - half_error:.1f}" stroke="#222" stroke-width="2"/>')
        parts.append(f'<line x1="{x + 35}" y1="{mid_y + half_error:.1f}" x2="{x + 70}" y2="{mid_y + half_error:.1f}" stroke="#222" stroke-width="2"/>')
        parts.append(f'<text x="{x + bar_w / 2}" y="{y - 10:.1f}" text-anchor="middle" font-family="sans-serif" font-size="13">{mean:.3f}</text>')
        parts.append(f'<text x="{x + bar_w / 2}" y="{top + chart_h + 24}" text-anchor="middle" font-family="sans-serif" font-size="12">{escape(row["algorithm_name"])}</text>')
    parts.extend([
        f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#333"/>',
        '<text x="500" y="530" text-anchor="middle" font-family="sans-serif" font-size="13">24 张相同官方测试图；双空图已单独计数</text>',
        '</svg>',
    ])
    svg_path.write_text("\n".join(parts), encoding="utf-8")
    return csv_path, svg_path


def main() -> None:
    parser = argparse.ArgumentParser(description="生成五种 EWS 分割算法的 test 汇总")
    parser.add_argument("--baseline-summary", type=Path, required=True)
    parser.add_argument("--rf-summary", type=Path, required=True)
    parser.add_argument("--baseline-images", type=Path, required=True)
    parser.add_argument("--rf-images", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for path in combine(args.baseline_summary, args.rf_summary, args.baseline_images, args.rf_images, args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
