# FIP1 连续观测数据接入报告

## 执行结论

本轮已将 V4.1 数据源切换为 FIP1，并完成本地目录、字段清单和预测样本文件的准备，但当前环境无法通过 Hugging Face 读取 Parquet 元数据，因此没有下载图片、没有生成预测标签，也没有训练模型。

官方 FIP1 数据卡声明许可证为 CC-BY-4.0，并提供 `plot_uid`、`yearsite_uid`、`images`、`image_dates`、`inner_plot_images`、冠层覆盖率/株高/穗数/衰老时间序列、天气变量及官方分组数据。其数据卡还说明图像和表型是按地块组织的时间序列，适合后续按地块构建预测样本。[FIP1 数据卡](https://huggingface.co/datasets/mikeboss/FIP1)

FIP1 的研究论文描述了约 4,000 个小麦地块、跨多个年份的图像时间序列和表型测量，支持按地块做时序研究。[FIP1 论文](https://pmc.ncbi.nlm.nih.gov/articles/PMC12153353/)

## 本地环境检查

- FIP1 Parquet：未发现。
- FIP1 图片：未发现。
- Python `datasets`：未安装。
- Python `pyarrow`：未安装。
- `fsspec`：已存在，但单独使用无法读取 Hugging Face 数据集配置。
- 网络访问：当前代理 `127.0.0.1:7890` 连接被拒绝。

## 实际数据统计

| 项目 | 实际数量 |
|---|---:|
| 获取的 FIP1 地块 | 0 |
| 下载图片 | 0 |
| 连续观测地块 | 0 |
| 真实冠层覆盖率记录 | 0 |
| 真实植株高度记录 | 0 |
| 真实穗数记录 | 0 |
| 真实衰老记录 | 0 |
| 7 天样本 | 0 |
| 15 天样本 | 0 |
| 30 天样本 | 0 |

以上 0 表示本机本轮没有成功获取 Parquet 或图片，不代表 FIP1 官方数据集为空。

## 已建立目录和文件

- `data/raw/fip1/metadata/SOURCE_README.md`
- `data/raw/fip1/images/`
- `data/processed/future_growth/temporal_manifest.csv`
- `data/processed/future_growth/plot_statistics.csv`
- `data/processed/future_growth/forecast_samples_7d.csv`
- `data/processed/future_growth/forecast_samples_15d.csv`
- `data/processed/future_growth/forecast_samples_30d.csv`
- `data/processed/future_growth/split_manifest.csv`
- `data/processed/future_growth/dataset_audit.json`

CSV 文件目前只有字段表头，未写入任何伪造样本。`dataset_audit.json` 保存了数据源、许可、网络失败原因和零样本状态。

## 后续真实样本规则

数据进入后必须：

1. 按 `plot_uid + year` 分组。
2. 按 `image_dates` 排序，并保留真实图像路径。
3. 将 `canopy_cover_values`、`height_values`、`spike_count_values`、`senescence_values` 与各自日期独立匹配。
4. 对 7/15/30 天分别测试 ±1、±3、±5 天容差。
5. 真实测量表型和 RGB 计算指标分开记录；V1.1 只作为规则代理指标。
6. 训练、验证、测试按地块和年份隔离，同一连续序列不能跨集合。
7. 只有真实日期匹配成功的样本才能进入预测 CSV。

## 预测状态

本轮不能开始真实 7/15/30 天模型训练。现有 FastAPI 预测接口继续保持 `unavailable`，没有生成随机曲线、当前分数外推或模拟标签。

## 下一步

需要在可访问 Hugging Face 的环境中安装与项目 Python 版本兼容的 `datasets`、`pyarrow` 和 `huggingface_hub`，或将官方 Parquet 元数据文件放入 `data/raw/fip1/metadata/`。获得元数据后先筛选 100～300 个 `plot_uid + year`，再按日期构建非空预测样本和地块独立划分。

