# CGIAR 生育期图片质量审计（V1 交付复核）

本文件是对已完成质量审计的命名补充，原始 ZIP、CSV 和已有 `manifest_verified.csv` 保留不变。

- 图片总数：14,253 张 JPEG
- 可正常解码：14,253 张
- 损坏图片：0 张
- RGB：14,251 张
- 灰度 L：2 张，进入 FoMo 前会统一转换 RGB
- 内容哈希重复组：0
- 训练标签：10,695 条
- 测试 UID：3,558 个
- 训练 UID 缺图：0
- 图片与标签 UID 缺失配对：0
- 训练/测试 UID 交集：0
- `SampleSubmission.csv` 的测试标签全部为占位 0，未用于测试准确率

当前轻量分类实验使用每类 100 张、共 700 张的可复现初步子集；图片和标签来自官方训练标签镜像，测试集保持冻结。

详细审计见 `reports/growth_stage_data_quality.md`，核验清单见 `data/processed/growth_stage/verified_manifest.csv`。
