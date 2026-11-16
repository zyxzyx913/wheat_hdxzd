# CGIAR 小麦生育期数据质量报告

生成时间：2026-11-14（本地交付批次）

## 数据来源与文件

本次使用 `data/raw/growth_stage/Images.zip`、`CGIAR_Train_mirror.csv` 和 `SampleSubmission.csv`。原始 ZIP、CSV 未删除或覆盖；图片解压到 `data/processed/growth_stage/images/`。为保留既有清单，实际核验清单另存为 `data/processed/growth_stage/manifest_verified.csv`。

官方训练标签来源为 CGIAR Wheat Growth Stage Challenge 的训练镜像标签。阶段含义按官方比赛说明保留为 1 Crown Root、2 Early Vegetative/Tillering、3 Mid Vegetative、4 Late Vegetative/Booting、5 Flowering/Reproductive/Heading、6 Anthesis、7 Ripening/Maturity/Milking。标签是生育期类别，不是长势等级，也不是叶片、茎秆、麦穗器官标签。

## 全量图片审计

| 项目 | 实际结果 |
|---|---:|
| ZIP 内 JPEG 图片 | 14,253 |
| 可正常解码 | 14,253 |
| 损坏图片 | 0 |
| RGB 模式 | 14,251 |
| 灰度 L 模式 | 2 |
| 内容哈希重复组 | 0 |
| 训练标签行数 | 10,695 |
| 测试 UID | 3,558 |
| 训练 UID 缺图 | 0 |
| ZIP 图片无 UID 标签 | 0 |
| 训练/测试 UID 交集 | 0 |

2 张灰度图片会在 FoMo 输入预处理阶段转换为 RGB；没有进行尺寸插值或修改原始文件。图片尺寸并不完全一致，主要为宽 512 像素、不同高度，审计未发现解码尺寸异常。

## 标签分布

训练 CSV 的完整标签计数为：

| 阶段 | 数量 |
|---:|---:|
| 1 | 3,057 |
| 2 | 1,389 |
| 3 | 689 |
| 4 | 1,712 |
| 5 | 1,092 |
| 6 | 421 |
| 7 | 2,335 |

`label_quality` 数值为 1：7,839，数值为 2：2,856。当前镜像 CSV 只提供数字质量代码，没有提供“专家/农户”来源字典，因此报告不擅自把代码 1/2 命名为专家或农户；来源分组只能按原始数值代码追溯。

`SampleSubmission.csv` 有 3,558 行、UID 无重复，`growth_stage` 全部为占位值 0。它不是测试真值，未用于训练、调参或准确率计算。

## 划分和泄漏限制

官方镜像提供训练标签与测试 UID，但没有在当前 `CGIAR_Train_mirror.csv` 中发现可靠的地块、农户、拍摄批次分组字段。今晚初步实验从训练标签中每类固定抽取 100 张（共 700 张），再以 UID 分层随机切分 80%/20%（560/140）。因此本报告不能声称完成地块独立验证；相邻观察或同一地块泄漏风险仍需获得地块/农户元数据后再审计。

训练和测试 UID 本身没有交集；测试图片不参与训练和调参。由于没有测试标签，未生成任何测试集成绩。

## 质量结论

图片完整性和 UID 配对质量满足进行初步特征提取的条件。标签类别明显不平衡，阶段 6 最少；本轮子集通过每类等量采样避免了验证集被多数类主导，但这不是完整数据上的最终成绩。数据来自 CGIAR 竞赛的印度田间场景，尚未验证中国品种、地区和手机拍摄域迁移。

审计原始明细：`data/processed/growth_stage/data_quality_report.json`；核验清单：`data/processed/growth_stage/manifest_verified.csv`。
