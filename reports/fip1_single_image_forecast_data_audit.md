# FIP1 单张图像未来 7/15/30 天预测可行性审计

审计日期：2026-11-14  
项目：`D:\Desktop\wheat\source-code\wheat-phenotyping`  
范围：只读检查官方数据卡、README、论文公开结构和本地项目目录。没有下载完整数据、没有解压图片、没有训练模型、没有修改现有长势 V1、EWS 或网页。

## 1. 先给出明确结论

FIP1 **在数据结构上支持构造“同一 plot 的当前图像 → 未来表型测量”样本**，因为官方说明每行对应某一年某个 plot，包含图像序列、图像日期、表型值序列和表型日期序列；但本地项目没有 FIP1 Parquet，因此本轮不能诚实地给出 7、15、30 天的可用训练样本数。

本轮可核实的是：

- 当前项目中 FIP1 文件数为 0，FIP1 Parquet 数为 0。
- 官方公开数据卡显示 4,058 行、超过 4,000 个小麦 plot、六个数据采集年份、超过 153,000 张对齐图像，许可证 CC-BY。[官方数据卡](https://huggingface.co/datasets/mikeboss/FIP1)
- 官方公开 split 包含 train、validation、test_plot、test_genotype、test_environment、test_genotype_environment；README 元数据显示 train 2,930 行、validation 380 行及多种测试集。[官方 README](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)
- 官方结构明确包含 `plot_uid`、`yearsite_uid`、`images`、`image_dates`、`inner_plot_images`、`trait_value(s)`、`trait_date(s)`、播种日期、收获日期和环境变量序列。[官方结构说明](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)
- 数据卡列出的生长/产量性状包括 canopy cover、plant height、wheat head count、senescence、heading date、final plant height、grain yield 和 protein content。[官方数据卡](https://huggingface.co/datasets/mikeboss/FIP1)

因此，“7 天多少、15 天多少、30 天多少”当前的真实答案是：**项目本地 0 条可审计样本；FIP1 官方总数不能由公开摘要直接分解成这些窗口，必须读取 Parquet 的日期数组后计算。** 报告不填估计值。

## 2. 本地检查结果

在项目中检查了：

```text
data/fip1
data/FIP1
data/raw/fip1
data/raw/FIP1
data/processed/fip1
data/processed/FIP1
fip_full
fip_validation
```

全部不存在，没有发现：

- train/validation Parquet；
- FIP1 原始图像或 `inner_plot_images` 缓存；
- FIP1 元数据快照；
- 7/15/30 天样本清单；
- FIP1 模型或评价结果。

本轮没有通过 Hugging Face 下载文件来补齐统计，符合“只获取公开结构和少量元数据、不下载完整数据”的要求。

## 3. 官方字段核对

| 用户关注字段 | 官方结构核对 | 备注 |
| --- | --- | --- |
| `plot_uid` | 存在 | 每行是某一年某 plot 的记录 |
| `yearsite_uid` | 存在 | 可作为年份-环境分组线索，不能直接代替地块 ID |
| `images` | 存在 | 原始图像路径序列 |
| `inner_plot_images` | 存在 | 对齐后的 plot 内图像序列，更适合作为 plot 级输入 |
| `image_dates` / image times | 存在 | 日期和时间序列，需与图像数组按索引配对 |
| `trait_value(s)` / `trait_date(s)` | 存在 | 官方 README 使用复数泛称；实际字段还应按具体性状 schema 读取 |
| canopy cover | 存在 | `canopy_cover_values` 与对应 dates/元数据字段 |
| plant height | 存在 | `height_values` 与对应 dates/元数据字段 |
| wheat head counts | 存在 | 官方数据卡称 wheat head count；schema 中对应 spike/head count 字段，需以当前 Parquet schema 定名 |
| senescence | 存在 | `senescence_values` 与 dates/元数据字段 |
| heading date | 存在 | 单值/日期及 trait 元数据 |
| final height | 存在 | final height 字段及日期/元数据 |
| grain yield | 存在 | `yield_value`/yield 相关字段及单位元数据 |
| sowing date | 存在 | 每个 plot-year 记录 |
| harvest date | 存在 | 每个 plot-year 记录 |
| weather variables | 存在 | 以 `_value(s)`、`_date(s)`、`_time(s)` 形式提供环境变量 |

官方 README 说明 `images` 是原图，`inner_plot_images` 是对齐的 plot 内裁剪图；缺失时间序列日期不会人为补齐。这个缺失语义对 7/15/30 天窗口计算非常关键。[字段和缺失说明](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)

## 4. 单图未来指标样本如何构造

### 4.1 样本定义

每个样本应固定为：

```text
plot_uid = p
当前图像日期 = t0
输入图像 = inner_plot_images[p][i0]
预测目标 = 同一 plot_uid、同一 plot-year 记录中未来日期的表型值
```

对于某一指标 `y` 和窗口 `h`，目标匹配规则建议：

1. 在同一 `plot_uid` 记录内，读取该指标的 `trait_dates` 和 `trait_values`。
2. 只保留 `t1 > t0` 的未来测量。
3. 选择最接近 `t0+h` 的测量日期。
4. 只有 `abs((t1-t0)-h) <= tolerance_h` 才生成样本。
5. 保存真实 `t0`、`t1`、实际间隔天数、目标值、目标字段、时间误差和选择理由。
6. 同一 `plot_uid` 的相邻日期不能跨 train/validation/test 随机拆开。

建议初始日期误差规则不是拍脑袋固定：先统计每个窗口的实际间隔分布，再预注册：

- 7 天：建议候选容差 ±2 天；
- 15 天：建议候选容差 ±3 天；
- 30 天：建议候选容差 ±5 天。

这只是待审计的候选方案，不是当前已验证规则。若某窗口用更宽容差才能凑够样本，必须单独报告实际间隔分布，不能把 12 天或 21 天样本称为严格 15 天/30 天预测。

### 4.2 图像和表型能否正确匹配

结构上可以匹配，但必须通过以下检查后才允许建样本：

- `len(inner_plot_images) == len(image_dates)` 或明确记录无法配对项；
- 图像 URL 非空且日期可解析；
- 目标 trait 的 value/date 数组长度一致；
- 目标日期属于同一 `plot_uid` 和同一年度记录；
- 目标日期确实晚于当前图像日期；
- 不把 `heading_date`、`harvest_date` 这种单一事件日期误当作连续测量值；
- 不用跨 plot、跨年份或跨环境的最近日期进行补配；
- 记录图像和标签缺失原因。

本轮未读取 Parquet，所以没有声称这些检查已经通过。

## 5. 7、15、30 天样本可行性

### 当前可报告数量

| 目标窗口 | 本地可审计样本 | FIP1 官方公开摘要是否直接给出数量 | 当前结论 |
| --- | ---: | --- | --- |
| 7 天 | 0 | 否 | 需读取 plot 级图像/trait 日期后统计 |
| 15 天 | 0 | 否 | 需读取 plot 级图像/trait 日期后统计 |
| 30 天 | 0 | 否 | 需读取 plot 级图像/trait 日期后统计 |

FIP1 官方说明图像最多每周约三次采集，且 canopy cover、height、head count、senescence覆盖生长季，因此从设计上 7/15/30 天样本有可行性；但实际数量取决于每个指标的测量日期、缺失率、日期容差和 plot 的连续观测长度。[FIP1 采集说明](https://huggingface.co/datasets/mikeboss/FIP1)

不能用“153,000 张图像”除以 7/15/30 推出样本数，因为：

- 图像和表型测量日期不是同一个序列；
- 不同 trait 的测量频率不同；
- 同一 plot 的图片数量不同；
- 缺失日期不自动补值；
- train/validation/test 还需要按地块分组。

### 不同生长阶段样本

官方数据有播种、抽穗和收获日期，可用 `days_since_sowing`、`days_to_heading`、`days_to_harvest` 划分阶段。但当前没有本地 Parquet，因此不能报告苗期、分蘖/拔节、孕穗、灌浆、成熟等阶段的样本数量。阶段边界也不能直接用固定日数代替，需要依据抽穗日期、品种和地区定义。

## 6. 最适合先预测的指标

建议优先级：

1. **Canopy cover / 冠层覆盖率**：与图像外观最直接，观测频次较适合做 7/15/30 天变化；可先预测未来覆盖率或覆盖率变化量。
2. **植株高度**：有明确物理含义，但 FIP 的测量方式跨年份包含 TLS/无人机，需先统一单位和测量方法。
3. **Senescence**：有生物学意义，但标签主观性、阶段性和缺失需审计。
4. **Wheat head count**：更适合孕穗/抽穗后，不能强行覆盖全生育期。

单张图像先预测“未来冠层覆盖率”比直接预测最终产量更合适。V1 目标可以是：

```text
输入：t0 的 RGB 图像 + 可选图像日期/播种日期
输出：t0+7、t0+15、t0+30 的冠层覆盖率，或相对当前覆盖率的变化量
```

但模型必须通过 FIP1 实际日期审计后才能确定哪些 horizon 有足够样本。

## 7. 是否能预测最终产量

FIP1 数据集定位上支持基于图像时序和辅助变量研究产量预测；官方数据卡明确把 image-based phenomic prediction 作为用途，并包含 grain yield。[FIP1 研究用途](https://huggingface.co/datasets/mikeboss/FIP1)

但这不意味着“单张当前照片即可可靠预测最终产量”：

- 产量是收获期综合结果，受品种、环境、管理和天气影响；
- 需要统一 `yield_value` 与 `yield_si_unit`，确认是否 adjusted yield；
- 必须按 plot、年份、环境和 genotype 做泄漏审计；
- FIP 固定平台图像与手机图像存在显著域差异；
- 需要报告预测区间和样本外验证，而非只报告一个 R²。

因此本轮结论是：**FIP1 可作为最终产量研究数据源，但不支持直接把单张手机照片产量预测功能上线。**

## 8. 数据划分与泄漏检查方案

优先保留官方 train、validation 及测试 split。新增审计必须检查：

1. `plot_uid` 是否只出现在一个 split；
2. `yearsite_uid`、lot、genotype 是否跨 split；
3. 同一 plot 的相邻日期图像是否跨 split；
4. 同一图像 URL 或同一图像文件名是否跨 split；
5. trait 的未来标签是否来自同一 split 的 plot；
6. 如果使用未来 7/15/30 天窗口，当前图像和未来标签必须保持同一 plot/year；
7. 任何标准化、缺失填补、特征选择只能在 train 拟合；
8. test_environment 和 test_genotype_environment 只能最终一次评价，不能用来选窗口/容差。

严禁把同一 plot 的相邻图像随机拆成独立训练和测试样本。否则模型可能记住地块、相机背景和品种，而不是学习可迁移的未来生长关系。

## 9. 许可、大小和图像下载说明

- 数据卡标注许可证为 **CC-BY**。[许可与数据卡](https://huggingface.co/datasets/mikeboss/FIP1)
- 当前公开仓库页面显示总文件大小约 170 GB；README 的数据文件统计还显示下载大小约 1.38 GB、数据集展开大小约 5.02 GB，具体口径不同，不能把二者混为“本地下载后大小”。[README 文件统计](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)
- 官方说明 Hugging Face 仓库包含对齐的 inner plot images，但原始图像路径指向 `/data/image`，需要从 ETH Research Collection 另行获取。[数据下载说明](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)
- 本轮没有下载或解压任何 FIP1 文件。

无需下载全部图像即可进行第一阶段元数据审计：优先只取得 Parquet schema、split 文件名和每行的 plot/date/trait 日期字段；如果远程服务支持 range/metadata 读取，先读取 footer/统计信息。若必须完整获取 Parquet，先只下载 train/validation 的元数据切片或小批次，不进入模型训练。

## 10. 对麦视通单图预测的适配结论

### 能做的第一版

在 FIP1 元数据验证后，可以先做一个研究原型：

- 当前图像经过现有 ExG/HSV/Otsu/Fusion 分割；
- 计算当前覆盖率、绿色程度、空间均匀度；
- 将当前覆盖率作为输入之一；
- 结合图像日期/播种日期（若用户提供）；
- 预测未来 7/15/30 天冠层覆盖率或变化量；
- 页面明确显示预测 horizon、实际日期误差、训练数据域和“研究原型”状态。

### 不能直接做的版本

- 只上传任意手机照片、没有日期，直接预测 30 天后数值；
- 把 FIP 瑞士固定相机模型当作中国手机照片模型；
- 把覆盖率预测称为长势等级或产量；
- 用同一 plot 的相邻日期随机划分得到“高准确率”；
- 在没有足够日期匹配样本时强行训练 7/15/30 天三套模型。

## 11. 下一步应下载哪些数据

不建议现在下载完整 170 GB 图像。下一步应分层获取：

1. FIP1 README/schema 和 Parquet footer 元数据；
2. train、validation、test split 中的 `plot_uid`、`yearsite_uid`、日期字段、trait 字段、单位字段；
3. 只下载少量 plot 的 `inner_plot_images`，验证图像 URL、日期和图片内容对应关系；
4. 先统计每个 trait 的非空比例、日期间隔和 7/15/30 天可匹配数；
5. 通过审计后，再按官方 split 和地块分组下载所需图像；
6. 最后才下载用于最终实验的完整图像，并保存版本、哈希和许可证记录。

建议新增但本轮未创建的审计程序：

```text
scripts/audit_fip1_forecast_windows.py
reports/fip1_window_summary.csv
reports/fip1_split_leakage_report.csv
reports/fip1_trait_date_quality.json
```

## 12. 最终回答

1. **FIP1 能否支持单张图片预测未来生长指标？** 结构上可以构造 plot 内的单图未来指标样本，但当前还没有完成日期匹配审计；不能直接上线。
2. **7/15/30 天分别多少样本？** 当前项目本地均为 0 条可审计样本；官方摘要没有给出窗口分解数，必须读取 Parquet 日期字段后真实统计。
3. **最适合先预测什么？** 冠层覆盖率或覆盖率变化量，其次是植株高度；先不直接预测产量。
4. **是否能预测最终产量？** FIP1 作为研究数据源可以支持产量研究，但单张手机照片直接预测最终产量目前不具备验证条件。
5. **是否适合中国手机照片直接使用？** 不适合直接使用。需要中国地块数据、手机拍摄协议、域适配和跨地块/跨季节验证。
6. **下一步下载什么？** 先下载/读取 Parquet 元数据和少量 plot 的对齐图像，统计窗口样本和泄漏，再决定是否下载完整图像。
7. **如何建立真正的单图输入模型？** 先固定预测截止时点和日期容差；按 plot-year 构造 `t0 → t0+h` 样本；以地块/环境分组冻结 train/validation/test；先预测冠层覆盖率；最后再用中国手机图像和实测标签做域外验证。

本轮没有训练、没有预测、没有下载完整数据，也没有修改麦视通现有代码。
