"""保存逐图像 CSV、数据集汇总 CSV、运行元数据和 SVG 对比图。"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

from .batch import ImageEvaluation, summarize_by_dataset


def write_image_csv(results: list[ImageEvaluation], path: str | Path) -> None:
    """写出逐图像结果；失败记录保留，未计算的指标留空。"""
    fields = [
        "sample_id", "dataset_name", "dataset_version", "group_id", "split", "data_source",
        "image_path", "reference_mask_path", "algorithm_name", "parameters_json",
        "algorithm_metadata_json", "experiment_time_utc", "runtime_seconds", "status", "error",
        "is_double_empty",
        "true_positive", "false_positive", "false_negative", "true_negative",
        "iou", "precision", "recall", "f1_score",
    ]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            row = {key: getattr(result, key) for key in fields if hasattr(result, key)}
            row["runtime_seconds"] = "" if result.runtime_seconds is None else f"{result.runtime_seconds:.9f}"
            if result.metrics:
                row.update(result.metrics.to_dict())
            else:
                row.update({key: "" for key in fields if key in {
                    "true_positive", "false_positive", "false_negative", "true_negative",
                    "iou", "precision", "recall", "f1_score",
                }})
            writer.writerow(row)


def write_summary_csv(results: list[ImageEvaluation], path: str | Path) -> list[dict[str, object]]:
    """写出按算法、数据集版本和划分的宏平均及 pooled 汇总。"""
    summaries = summarize_by_dataset(results)
    fields = [
        "algorithm_name", "dataset_name", "dataset_version", "split", "sample_count",
        "successful_count", "failed_count", "double_empty_count", "nonempty_scored_count",
        "total_pixels", "macro_iou", "macro_precision", "macro_recall", "macro_f1_score",
        "std_iou", "std_precision", "std_recall", "std_f1_score",
        "pooled_iou", "pooled_precision", "pooled_recall",
        "pooled_f1_score", "mean_runtime_seconds", "experiment_time_utc", "parameters_json",
    ]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    return summaries


def write_comparison_svg(summaries: list[dict[str, object]], path: str | Path) -> None:
    """根据汇总中的真实计算值生成 IoU/Precision/Recall/F1 分组柱状 SVG。"""
    metric_names = [
        ("macro_iou", "Macro IoU"),
        ("macro_precision", "Macro Precision"),
        ("macro_recall", "Macro Recall"),
        ("macro_f1_score", "Macro F1-score"),
    ]
    algorithms = sorted({str(row["algorithm_name"]) for row in summaries})
    groups = sorted({(str(row["dataset_name"]), str(row["dataset_version"]), str(row["split"])) for row in summaries})
    lookup = {(str(row["algorithm_name"]), str(row["dataset_name"]), str(row["dataset_version"]), str(row["split"])): row for row in summaries}
    colors = ["#2878B5", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2", "#EDC948", "#FF9DA7"]
    width = max(900, 190 * max(1, len(groups)))
    panel_h, top, bottom = 190, 45, 35
    height = top + panel_h * len(metric_names) + bottom
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    out.append('<rect width="100%" height="100%" fill="white"/>')
    out.append('<text x="24" y="26" font-family="sans-serif" font-size="17" font-weight="bold">Segmentation algorithm comparison (macro metrics)</text>')
    if not summaries:
        out.append(f'<text x="24" y="70" font-family="sans-serif" font-size="14">No evaluation rows available.</text></svg>')
        Path(path).write_text("\n".join(out), encoding="utf-8")
        return
    legend_x = 24
    for index, name in enumerate(algorithms):
        x = legend_x + index * 175
        out.append(f'<rect x="{x}" y="34" width="13" height="13" fill="{colors[index % len(colors)]}"/>')
        out.append(f'<text x="{x + 19}" y="45" font-family="sans-serif" font-size="12">{html.escape(name)}</text>')
    chart_top = top + 20
    plot_left, plot_right = 70, width - 25
    plot_w = plot_right - plot_left
    cluster_w = plot_w / max(1, len(groups))
    bar_w = min(34, cluster_w / max(1, len(algorithms)) * 0.72)
    for panel, (metric, label) in enumerate(metric_names):
        y0 = chart_top + panel * panel_h
        plot_top, plot_bottom = y0 + 20, y0 + panel_h - 38
        plot_h = plot_bottom - plot_top
        out.append(f'<text x="18" y="{plot_top + 9}" font-family="sans-serif" font-size="12">{label}</text>')
        for tick in range(5):
            value = tick / 4
            y = plot_bottom - value * plot_h
            out.append(f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_right}" y2="{y:.1f}" stroke="#dddddd"/>')
            out.append(f'<text x="{plot_left - 28}" y="{y + 4:.1f}" font-family="sans-serif" font-size="10">{value:.2f}</text>')
        for group_index, group in enumerate(groups):
            group_label = " / ".join(group)
            center = plot_left + cluster_w * (group_index + 0.5)
            for algo_index, algorithm in enumerate(algorithms):
                row = lookup.get((algorithm, *group))
                value = row.get(metric) if row else None
                if not isinstance(value, (int, float)):
                    continue
                value = max(0.0, min(1.0, float(value)))
                x = center + (algo_index - (len(algorithms) - 1) / 2) * bar_w - bar_w / 2
                bar_h = value * plot_h
                out.append(f'<rect x="{x:.1f}" y="{plot_bottom - bar_h:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{colors[algo_index % len(colors)]}"/>')
            out.append(f'<text x="{center:.1f}" y="{plot_bottom + 15}" text-anchor="middle" font-family="sans-serif" font-size="10">{html.escape(group_label)}</text>')
    out.append("</svg>")
    Path(path).write_text("\n".join(out), encoding="utf-8")


def write_evaluation_outputs(
    results: list[ImageEvaluation], output_dir: str | Path, *, parameters_frozen: bool
) -> dict[str, Path]:
    """保存全部评价产物并记录划分、算法参数、版本和运行时间。"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    image_csv, summary_csv = out / "image_metrics.csv", out / "dataset_summary.csv"
    chart_svg, metadata_json = out / "algorithm_comparison.svg", out / "experiment_metadata.json"
    write_image_csv(results, image_csv)
    summaries = write_summary_csv(results, summary_csv)
    write_comparison_svg(summaries, chart_svg)
    metadata = {
        "experiment_time_utc": results[0].experiment_time_utc if results else None,
        "splits_evaluated": sorted({row.split for row in results}),
        "parameters_frozen": parameters_frozen,
        "algorithms": {
            name: json.loads(next(row.parameters_json for row in results if row.algorithm_name == name))
            for name in sorted({row.algorithm_name for row in results})
        },
        "per_image_algorithm_metadata": {
            "::".join((row.dataset_name, row.dataset_version, row.split, row.sample_id, row.algorithm_name)): json.loads(row.algorithm_metadata_json)
            for row in results if row.algorithm_metadata_json != "{}"
        },
        "datasets": sorted({
            (row.dataset_name, row.dataset_version, row.data_source) for row in results
        }),
        "row_count": len(results),
        "metric_convention": "Both masks empty => all four metrics 1; zero denominator otherwise => 0.",
        "macro_convention": "Double-empty images are counted and excluded from macro means/std to avoid inflating scores.",
        "runtime_convention": "Predictor call only, including image loading performed inside predictor.",
        "files": [image_csv.name, summary_csv.name, chart_svg.name],
    }
    metadata_json.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"image_csv": image_csv, "summary_csv": summary_csv, "chart_svg": chart_svg, "metadata_json": metadata_json}
