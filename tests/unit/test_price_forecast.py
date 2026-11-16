"""全国小麦价格基线的数据校验和预测测试。"""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from wheat_phenotyping.economics import PricePoint, forecast_naive, load_price_csv, rolling_origin_backtest


class NationalPriceForecastTest(unittest.TestCase):
    def _series(self):
        start = date(2026, 1, 5)
        return [PricePoint(start + timedelta(days=7 * index), 2400 + index, "official_weekly_report") for index in range(10)]

    def test_outputs_two_baselines_for_each_future_week(self):
        results = forecast_naive(self._series(), horizon_weeks=2)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].forecast_yuan_per_ton, 2409)
        self.assertAlmostEqual(results[1].forecast_yuan_per_ton, 2407.5)
        self.assertEqual(results[0].target_date, date(2026, 3, 16))

    def test_rejects_gap_in_weekly_series(self):
        points = self._series()
        points[4] = PricePoint(points[4].date + timedelta(days=1), points[4].price_yuan_per_ton, points[4].source)
        with self.assertRaisesRegex(ValueError, "价格序列"):
            forecast_naive(points)

    def test_csv_requires_source_and_enough_actual_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prices.csv"
            path.write_text("date,price_yuan_per_ton,source\n2026-01-01,2400,official\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "至少需要 10"):
                load_price_csv(path)

    def test_loads_sorted_real_rows(self):
        points = self._series()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "prices.csv"
            lines = ["date,price_yuan_per_ton,source"]
            lines += [f"{point.date.isoformat()},{point.price_yuan_per_ton},{point.source}" for point in reversed(points)]
            path.write_text("\n".join(lines), encoding="utf-8")
            loaded = load_price_csv(path)
        self.assertEqual(loaded, points)

    def test_rolling_backtest_uses_only_prior_observations_and_reports_metrics(self):
        rows, summary = rolling_origin_backtest(self._series(), minimum_history=4)
        self.assertEqual(len(rows), 12)
        first_step = [row for row in rows if row["target_date"] == "2026-02-02"]
        self.assertEqual({row["data_cutoff"] for row in first_step}, {"2026-01-26"})
        self.assertEqual(summary["protocol"], "expanding_window_one_step_ahead")
        self.assertIn("mae_yuan_per_ton", summary["results"]["naive_last_value"])

    def test_rolling_backtest_rejects_short_series(self):
        with self.assertRaisesRegex(ValueError, "至少需要"):
            rolling_origin_backtest(self._series()[:9], minimum_history=8)

    def test_rejects_nonfinite_manual_observation(self):
        points = self._series()
        points[-1] = PricePoint(points[-1].date, float("nan"), points[-1].source)
        with self.assertRaisesRegex(ValueError, "有限正数"):
            forecast_naive(points)


if __name__ == "__main__":
    unittest.main()
