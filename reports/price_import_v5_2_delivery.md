# V5.2 官方小麦价格周报本地批量导入交付报告

## 实际完成情况

本轮已创建浏览器下载文件的本地导入目录，并完成批量识别工具和人工复核页面。由于当前 `inbox` 目录没有用户放入的官方 PDF/JPG/PNG 文件，实际导入文件数为 0，正式价格记录仍为 1 条。

目录：

- `data/raw/economics/official_reports/inbox/`
- `data/raw/economics/official_reports/processed/`
- `data/raw/economics/official_reports/rejected/`

## 新增工具

- [import_official_price_reports.py](D:\Desktop\wheat\source-code\wheat-phenotyping\scripts\import_official_price_reports.py)
  - 扫描 PDF、JPG、JPEG、PNG。
  - 计算文件哈希，避免重复导入。
  - OCR 可用时提取日期和“小麦 + 价格 + 单位”候选。
  - 元/斤候选按单位转换为元/吨，但仍必须人工确认。
  - 不确定结果统一标记 `pending_manual_review`。
- [merge_confirmed_price_records.py](D:\Desktop\wheat\source-code\wheat-phenotyping\scripts\merge_confirmed_price_records.py)
  - 只合并 `verification_status=confirmed` 的记录。
  - 自动拒绝重复日期和无效数值。
- [price_import_review.csv](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_import_review.csv)
- [price_import_review.html](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_import_review.html)

## OCR 依赖检查

当前主环境检查结果：

- Pillow：已安装。
- pytesseract：未安装。
- fitz/PyMuPDF：未安装。
- pdf2image：未安装。
- OpenCV：未安装。

因此当前工具可以扫描文件并生成待复核记录，但尚未自动 OCR PDF。没有为了 OCR 修改主环境依赖，也没有把 OCR 空结果当成价格数据。

## 当前数据统计

| 项目 | 数量 |
|---|---:|
| 导入文件 | 0 |
| OCR 成功识别 | 0 |
| 人工确认 | 0 |
| 正式价格记录 | 1 |
| 主序列最早日期 | 2026-11-10 |
| 主序列最新日期 | 2026-11-10 |
| 30 天预测 | 不可用 |
| 收获期预测 | 不可用 |

已有真实记录 2026-11-10、2417 元/吨保持不变。没有生成新价格，也没有重新运行没有数据支撑的回测。

## 使用方法

1. 用浏览器从国家粮食和物资储备局官方下载周报图片或 PDF。
2. 将文件放入 `data/raw/economics/official_reports/inbox/`。
3. 运行：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
.\.venv\Scripts\python.exe scripts\import_official_price_reports.py
```

4. 打开 `data/processed/economics/price_import_review.html` 检查日期、全国小麦平均收购价、单位和来源。
5. 人工确认后，把对应 CSV 行的 `verification_status` 改为 `confirmed`，再运行：

```powershell
.\.venv\Scripts\python.exe scripts\merge_confirmed_price_records.py
```

只有确认记录会进入 `data/raw/economics/national_wheat_price.csv`。

## 项目保护

本轮未修改图像识别、长势评分、生育期识别、FoMo4Wheat、GSP-AI 或 WOFOST/PCSE 模块；没有删除历史数据，也没有生成随机价格曲线。

