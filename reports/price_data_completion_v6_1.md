# V6.1 全国小麦历史价格数据补全与预测启用准备报告

## 实际结果

本轮检查并完善了本地导入和人工复核流程，但 `inbox` 目录目前没有用户放入新的官方 PDF、图片或 CSV 文件，因此实际新增正式价格记录为 **0 条**。

主序列仍为 1 条真实记录：

```text
2026-11-10, 2417 元/吨
```

没有虚构价格、插值数据或稀疏连续序列。

## 已完善功能

- `import_official_price_reports.py` 现在支持 CSV、PDF、JPG、JPEG、PNG。
- CSV 导入记录也必须进入 `pending_manual_review`，不会直接进入正式序列。
- PDF/图片 OCR 结果继续保留待复核状态。
- 保留原始文件到 `official_reports/processed/`。
- 导入记录保留日期、价格、来源文件、来源 URL、发布日期、OCR 状态和复核说明。
- `merge_confirmed_price_records.py` 仍只合并 `verification_status=confirmed` 的记录。
- 新增 `price_import_stats.json` 和 `price_history_completion_v6_1.json`。

## 数据统计

| 项目 | 数量 |
|---|---:|
| inbox 文件 | 0 |
| 复核队列记录 | 0 |
| 人工确认记录 | 0 |
| 新增正式价格记录 | 0 |
| 正式价格记录总数 | 1 |
| 最早日期 | 2026-11-10 |
| 最新日期 | 2026-11-10 |
| 重复日期 | 0 |
| 异常价格 | 0 |
| 缺失周 | 无法从单条记录计算 |
| 连续周度片段 | 1 条单点片段 |

## 预测启用状态

由于仍没有至少 10 条连续真实周度数据：

- Persistence：未运行有效回测。
- 最近 4 周均值：未运行有效回测。
- 移动平均：未运行有效回测。
- Holt/ETS：未运行有效回测。
- 30 天方向预测：不可用。
- 2027 年收获期预测：不可用。

没有生成 MAE、RMSE、MAPE 或 R²，也没有将当前价格复制成预测结果。

## 文件

- [price_import_review.csv](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_import_review.csv)
- [price_import_review.html](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_import_review.html)
- [price_import_stats.json](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_import_stats.json)
- [price_history_completion_v6_1.json](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_history_completion_v6_1.json)

## 使用流程

1. 将官方周报 PDF/JPG/PNG 或人工整理 CSV 放入 `data/raw/economics/official_reports/inbox/`。
2. 运行 `scripts/import_official_price_reports.py`。
3. 打开 `data/processed/economics/price_import_review.html`。
4. 人工核对全国小麦平均收购价、日期、单位和来源。
5. 将确认行标记为 `confirmed`。
6. 运行 `scripts/merge_confirmed_price_records.py`。
7. 重新运行价格回测。

本轮没有修改图像识别、长势、生育期、天气农事建议、WOFOST/PCSE 和历史实验结果，也没有修改现有价格页面设计。

