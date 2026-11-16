# V5.1 全国小麦历史价格数据补全与审计报告

## 执行结论

本轮建立了官方周报索引采集脚本并实际运行，但当前 Windows 环境访问国家粮食和物资储备局目录时被本地代理/套接字权限拒绝，未能自动下载新增周报。没有把无法访问或无法 OCR 核验的记录写入主预测序列。

官方目录确实列出了“全国主要粮食品种收购价格周报”，当前页面可见 2026 年多周条目；周报详情页的价格主体以图片形式呈现，需要保存原始图片并 OCR/人工复核后才能录入。[官方市场监测目录](https://www.lswz.gov.cn/html/zmhd/lysj/lsjg-scjc.shtml)

## 当前真实数据

主序列仍保留 1 条真实记录：

| 日期 | 价格 | 单位 | 来源 | 核验状态 |
|---|---:|---|---|---|
| 2026-11-10 | 2417 | 元/吨 | 国家粮食和物资储备局官方周报 | source URL 已确认，非本轮 OCR |

本轮新增记录数：**0**。

数据范围：2026-11-10 至 2026-11-10。记录数不足以计算缺失周、连续周数或滚动回测。

## 自动采集脚本

新增：

[collect_official_wheat_prices.py](D:\Desktop\wheat\source-code\wheat-phenotyping\scripts\collect_official_wheat_prices.py)

脚本支持：

- 官方目录遍历入口。
- 周报链接识别。
- 失败记录写入清单。
- 断点续采的目录结构。
- 待人工复核状态。

本轮实际运行结果：

```text
official_index: failed
error: WinError 10013，当前代理/套接字访问被拒绝
verification_status: pending_manual_review
```

当前脚本没有绕过网站限制，也没有使用第三方或虚构数据。

通过官方搜索索引确认了可继续人工复核的历史入口，包括 2023-12-06 的国家发改委周报页面、2024 年周报目录和 2025 年周报目录。页面只暴露图片/附件入口，当前没有在本机成功下载价格图片，因此这些条目均保持 `pending_manual_review`，没有写入主序列。[2023-12-06 官方周报](https://www.ndrc.gov.cn/fgsj/tjsj/lslt/shichangjiance/202312/t20231218_1362699.html)、[2024 周报目录](https://www.lswz.gov.cn/html/zmhd/lysj/lsjg-scjc_5.shtml)、[2025 周报目录](https://lswz.gov.cn/html/zmhd/lysj/lsjg-scjc_3.shtml)

## 审计文件

- [price_data_audit.json](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_data_audit.json)
- [price_source_manifest.csv](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_source_manifest.csv)
- [price_observations_audit.csv](D:\Desktop\wheat\source-code\wheat-phenotyping\data\processed\economics\price_observations_audit.csv)

审计结果：

- 实际记录：1 条
- 新增记录：0 条
- 重复日期：0
- 缺失周：无法计算
- 待人工复核：1 条来源记录
- 主预测序列：不可用
- 30 天预测：未启用
- 收获期预测：未启用

## 回测状态

由于只有 1 条真实周度价格，Persistence、最近 4 周均值、移动平均、Holt/ETS 和 Random Forest 均未进行回测。没有 MAE、RMSE、MAPE、R² 成绩，也没有把当前价格复制成预测曲线。

## 下一步

在网络可访问官方目录的环境中运行：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
.\.venv\Scripts\python.exe scripts\collect_official_wheat_prices.py
```

下载的原始页面/图片应保存到 `data/raw/economics/official_weekly_reports/`，逐条 OCR 后人工复核小麦全国平均收购价、日期、单位和统计口径。至少积累 10～20 条连续周度记录后，才可以重新运行滚动回测并考虑启用 30 天预测。

