"""从有来源记录的全国周度价格 CSV 生成朴素预测与元数据。"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from wheat_phenotyping.economics.price_forecast import (
    forecast_as_dicts,
    forecast_naive,
    load_price_csv,
    rolling_origin_backtest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="全国小麦平均收购价透明基线预测")
    parser.add_argument("csv", type=Path, help="真实、连续周度序列 CSV")
    parser.add_argument("--horizon-weeks", type=int, default=4, choices=range(1, 5))
    parser.add_argument("--output-dir", type=Path, default=Path("results/economics/latest"))
    args = parser.parse_args()
    observations = load_price_csv(args.csv)
    forecasts = forecast_as_dicts(forecast_naive(observations, args.horizon_weeks))
    backtest_rows, backtest_summary = rolling_origin_backtest(observations)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "forecasts.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(forecasts[0]))
        writer.writeheader()
        writer.writerows(forecasts)
    with (args.output_dir / "rolling_backtest.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(backtest_rows[0]))
        writer.writeheader()
        writer.writerows(backtest_rows)
    (args.output_dir / "rolling_backtest_summary.json").write_text(
        json.dumps(backtest_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "target": "全国小麦周度平均收购价",
        "unit": "CNY/ton",
        "data_source": sorted({point.source for point in observations}),
        "observation_count": len(observations),
        "first_observation": observations[0].date.isoformat(),
        "last_observation": observations[-1].date.isoformat(),
        "data_cutoff": observations[-1].date.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "horizon_weeks": args.horizon_weeks,
        "models": ["naive_last_value", "mean_last_4_weeks"],
        "validation_status": "baseline only; rolling-origin metrics are descriptive and require a future holdout period for model selection",
        "input_file": str(args.csv.resolve()),
    }
    (args.output_dir / "experiment_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 {len(forecasts)} 条基线预测和 {len(backtest_rows)} 条滚动回测记录。仅为基线结果，不代表市场预测有效性。输出目录：{args.output_dir}")


if __name__ == "__main__":
    main()
