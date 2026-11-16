# V4.1 WheatPheno 完整下载、解压、审计与样本构建报告

## 执行结论

本轮已按要求检查磁盘、目标文件、官方下载地址和网络配置，并尝试从 Zenodo 官方地址下载 WheatPheno。磁盘 D: 剩余约 **500.06 GB**，满足至少 25GB 预留要求；目标 ZIP 原先不存在。

官方文件地址为：

`https://zenodo.org/records/8115362/files/WheatPheno_part_1.zip?download=1`

官方记录文件大小约 **8,881,621,279 bytes（约 8.9GB）**，MD5 为 `44ad918c0fd9c1915901bc6665a8e0be`。本轮下载失败，原因是当前系统代理 `127.0.0.1:7890` 连接被拒绝，直连 DNS 也不可用。没有得到可续传的有效 ZIP 文件，因此没有解压、没有修改原始数据，也没有计算虚假的 MD5。

## 下载与解压状态

| 项目 | 实际结果 |
|---|---|
| 完整 ZIP 下载 | 未成功 |
| 本地 ZIP | 不存在 |
| MD5 校验 | 未执行，因为没有完整文件 |
| ZIP 目录检查 | 未执行 |
| 解压文件数 | 0 |
| 图片质量审计 | 未执行 |
| 预测样本构建 | 未执行 |
| 真实数据可视化 | 未生成 |

没有因为下载失败而创建模拟图片、模拟标签或模拟统计图。

## 已生成的追踪文件

目录：`data/processed/future_growth/`

- `temporal_manifest.csv`
- `plot_statistics.csv`
- `forecast_samples_7d.csv`
- `forecast_samples_15d.csv`
- `forecast_samples_30d.csv`
- `data_source_manifest.csv`
- `split_manifest.csv`
- `dataset_audit.json`

这些 CSV 目前只包含字段表头，没有任何伪造样本。`dataset_audit.json` 记录了官方 URL、文件大小、MD5、下载错误和零样本状态。

## 数据字段和后续规则

公开元数据表明 WheatPheno/FIP1 类时序数据可能包含地块编号、图像日期、表型日期、图像路径、生育期、环境时间序列和官方划分，但本轮没有拿到 WheatPheno 压缩包内容，因此没有把这些字段当作本地已验证字段。

数据真正下载后，程序必须逐文件读取 README、元数据和原始字段；只有确认字段存在，才建立以下映射：

`plot_id, year, image_id, capture_date, image_path, growth_stage, variety, phenotype_date, phenotype_values, weather_features, data_source`

未来样本必须满足：

1. 锚点和目标来自同一地块、同一年份。
2. 目标日期使用真实拍摄/测量日期，分别按 ±1、±3、±5 天容差统计。
3. 目标间隔不能把任意相邻图片直接称为 7、15 或 30 天。
4. 真实测量表型与图像代理指标分开保存。
5. 训练、验证、测试按 `plot_id + year` 隔离。
6. 缺失值保持缺失，不能用未来数据、随机值或线性外推填补。

## 当前实际数量

| 项目 | 数量 |
|---|---:|
| 真实小麦图片 | 0 |
| 有效地块 | 0 |
| 连续观测地块 | 0 |
| 7天样本 | 0 |
| 15天样本 | 0 |
| 30天样本 | 0 |
| 真实表型标签 | 0 |
| 图像代理标签 | 0 |

这些 0 表示本地下载和解压没有完成，不代表官方数据集为空。

## 预测功能状态

7天、15天、30天均不具备训练和独立验证条件，现有 FastAPI 预测接口继续返回 `unavailable`。没有启用任何预测期限，也没有修改 V1.1、CGIAR SVM、FoMo4Wheat、GSP-AI 或历史实验结果。

## 下一步操作

需要在网络可访问 Zenodo 的环境中重新运行可续传下载，或由用户将官方 ZIP 放入：

`data/raw/wheatpheno/WheatPheno_part_1.zip`

放入后先校验文件大小和 MD5，只有校验通过才允许解压和审计。当前不应把下载失败报告为数据准备完成，也不应启用未来趋势预测。
