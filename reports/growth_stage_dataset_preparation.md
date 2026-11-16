# CGIAR 小麦生育期数据准备报告

审计日期：2026-11-14  
项目：`D:\Desktop\wheat\source-code\wheat-phenotyping`  
范围：只准备标签元数据和数据清单，不训练模型，不修改 FoMo4Wheat、分割算法、长势 V1 或网页。

## 1. 数据来源和下载结果

官方数据页面是已结束的 Zindi 竞赛：

`https://zindi.africa/competitions/cgiar-wheat-growth-stage-challenge/data`

官方页面确认提供：

- `Train.csv`：图像 UID、生育期标签、标签质量；
- `Images.zip`：UID 对应的 JPEG 图片；
- `SampleSubmission.csv`：测试集 UID。

官方页面报告 Images 文件夹共有 14,253 张图片，图片格式为 `[UID].jpeg`，数据包约 389.7 MB；但当前页面没有暴露无需登录的直接下载 URL。[官方 Zindi 数据页](https://zindi.africa/competitions/cgiar-wheat-growth-stage-challenge/data)

本轮没有下载图片包，也没有绕过 Zindi 登录或权限。为了完成小型标签审计，下载了公开 GitHub 镜像中的小型 `Train.csv`：

```text
data/raw/growth_stage/CGIAR_Train_mirror.csv
```

来源：

`https://raw.githubusercontent.com/conaldes20/CGIAR-Wheat-Growth-Stage-Challenge/master/Train.csv`

该镜像文件 SHA-256：

```text
f740d4e5980c62f0cb3323beb62f8057814d67b70e85985125209142cba628d8
```

重要限制：镜像标签文件与官方原始文件尚未做逐字节对比，不能把镜像完整性当作官方发布证明；本地没有图片字节。

## 2. 标签和类别统计

镜像 `Train.csv` 实际包含 10,695 行标签，字段为：

```text
UID,growth_stage,label_quality
```

类别定义来自官方数据页：

| 标签 | 官方描述 | 常用名称 | 样本数 |
| ---: | --- | --- | ---: |
| 1 | Crown Root | 冠根始发期 | 3,057 |
| 2 | Early Vegetative Phase | 早期营养生长期/分蘖期 | 1,389 |
| 3 | Mid Vegetative Phase | 中期营养生长期 | 689 |
| 4 | Late Vegetative Phase / Booting | 后期营养生长期/孕穗期 | 1,712 |
| 5 | Flowering and Reproductive Phase / Heading | 开花与生殖阶段/抽穗期 | 1,092 |
| 6 | Anthesis | 开花期 | 421 |
| 7 | Ripening and Maturity Phase / Milking | 成熟过程/乳熟期 | 2,335 |

标签计数合计 10,695，与公开研究对所有七类图片给出的分布一致；官方页面总图片数 14,253，说明并非所有图片都有训练标签。[公开数据说明](https://lanfrica.com/en/record/cgiar-wheat-growth-stage-challenge)、[数据研究说明](https://pmc.ncbi.nlm.nih.gov/articles/PMC13045506/)

标签质量统计：

- `label_quality=2`：2,856 条，专家确认；
- `label_quality=1`：7,839 条，农户报告，可靠性可能较低。

这不是简单的 1–7 均衡分类集。类别 6 只有 421 条，类别 3 有 689 条，存在明显不平衡；训练阶段应按标签质量和类别分布制定方案，不应直接把所有标签视为同等可靠。

## 3. 已生成的数据清单

新增：

- `data/processed/growth_stage/manifest.csv`
- `data/processed/growth_stage/dataset_summary.json`

`manifest.csv` 字段包括：

```text
uid
label
label_quality
image_path
image_exists
split
source_file
```

当前所有图片行的 `image_exists=false`，因为本轮没有下载 `Images.zip`。`split` 暂记为 `official_labeled_train`，表示官方标签文件中的训练标签，不表示本地已经拥有完整图片训练集。

## 4. 图片和数据质量检查

当前可确认：

- 官方图片格式为 JPEG；
- 官方图像由 WheatCam Android 应用采集，来自印度 Punjab 和 Haryana 的两季 Rabi 小麦观测；
- 采集过程中要求重复图片尽量保持相同观察位置和视角；
- 官方进行了 ROI 裁剪、隐私屏蔽、模糊/异常图片筛除和非植被区域处理；
- 图片是地面 RGB 图像，不是 EWS 的 350×350 图像，也不是 FIP 固定相机图像。[官方数据背景](https://zindi.africa/competitions/cgiar-wheat-growth-stage-challenge/data)

本地尚未完成的检查：

- JPEG 实际宽高、色彩模式、损坏数量；
- 图片 UID 与标签 UID 的逐个配对；
- 训练图片是否完整覆盖 10,695 个 UID；
- 官方测试图片数量及其 UID；
- 重复图片内容哈希；
- 真实地块/农户/时间序列泄漏。

这些检查必须等官方图片包和 `SampleSubmission.csv` 可合法取得后进行。

## 5. 数据划分和泄漏风险

官方页面提供带标签的 `Train.csv` 和测试 UID 的 `SampleSubmission.csv`，但本地没有后者，也没有图片包。因此当前不能生成真正的 train/test 图像清单。

泄漏风险：

1. 官方背景说明同一农户会在生长季重复拍摄同一田块；相邻日期图片可能来自同一地块。
2. `Train.csv` 只有 UID、标签和质量字段，没有可直接用于地块分组的 plot/farmer ID。
3. 仅凭随机拆分 UID，可能把同一地块相邻日期图片分到训练和验证，造成过高成绩。
4. 测试集图片有可靠标签，但训练标签质量混合；不能把全部训练标签视为同一可靠等级。
5. 需要从图片 UID、竞赛元数据或官方说明中核实是否可以恢复农户/地块/季节分组；如果无法恢复，必须明确写作“按 UID 划分，无法排除地块级泄漏”。

下一步训练前必须建立：

- 按地块/农户/季节的 group split；
- 训练、验证、测试图片内容哈希审计；
- 标签质量分层统计；
- 不使用测试标签调参；
- 相邻日期不得随机拆分为独立样本。

## 6. FoMo4Wheat 对接方案

现有 FoMo 模块可以提取 768 维 embedding，但它没有生育期分类头。建议后续新增独立分类头，不修改 FoMo backbone：

```text
RGB 图片
  → 官方 FoMo4Wheat ViT-B/14 预处理
  → 冻结 768 维 embedding
  → 轻量分类头
  → CGIAR 1–7 阶段概率
```

建议分类头：

- 第一基线：Linear(768, 7)；
- 第二基线：Linear → LayerNorm → Dropout → Linear(7)；
- 训练时只允许使用训练集；
- 验证集用于类别权重、阈值和早停；
- 测试集冻结；
- 记录 FoMo 权重 SHA-256、预处理版本、标签映射和分类头 hash。

由于 CGIAR 的标签是 1–7 竞赛阶段，不是完整 Zadoks 代码，不能直接把 1–7 自动宣称为 Zadoks 10、21、31、49、59、65、75 等。需要另建标签映射文档并由农学人员审核。

## 7. 是否适合训练轻量分类头

**适合做研究性轻量分类头，暂不适合直接训练和上线。**

适合原因：

- 有 10,695 条带标签记录；
- 输入是 RGB，与现有图片入口一致；
- 已有冻结 FoMo 768 维特征；
- 标签质量字段可用于可靠性分析；
- 七类阶段定义清晰，能先做粗粒度阶段识别。

主要限制：

- 目前没有图片字节，不能检查实际输入；
- 类别明显不平衡；
- 训练标签中农户标签占多数；
- 同一地块重复观测带来泄漏风险；
- 数据来自印度北部，不等于中国小麦手机照片域；
- 官方页面不提供现成任务 checkpoint。

## 8. 下一步数据获取建议

优先顺序：

1. 通过已授权的 Zindi 账号获取官方 `Train.csv`、`Images.zip` 和 `SampleSubmission.csv`；
2. 下载后保留原始压缩包、来源页面、下载时间、SHA-256；
3. 解压到 `data/raw/growth_stage/images/`，不覆盖当前镜像 CSV；
4. 用 UID 与图片文件名逐个配对；
5. 生成真实 `image_exists`、尺寸、格式和文件哈希质量报告；
6. 评估是否能恢复重复地块/时间序列分组；
7. 只在完成分组审计后建立 train/validation/test 清单。

本轮不建议绕过 Zindi 权限下载图片，也不建议把第三方镜像图片当成官方数据。

## 9. 当前交付结论

- 标签元数据审计已完成：10,695 条已标注记录。
- 7 类定义和类别数量已获得；标签质量为 2,856 条专家、7,839 条农户。
- 图片没有下载，实际图片数量和分辨率尚未核验。
- 官方训练/测试文件结构已确认，但本地没有完整 split 文件。
- 已生成 `manifest.csv` 和 `dataset_summary.json`，明确标记图片缺失。
- FoMo 768 维冻结特征接口已经具备后续分类头对接条件，但本轮不训练。

下一步应先完成官方授权图片下载与 UID 配对质量审计，再训练冻结 FoMo + 轻量分类头。当前不能生成生育期分类结果或准确率。
