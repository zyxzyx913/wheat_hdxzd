# 小麦生育期近重复图片泄漏审计报告

## 1. 审计结论

本轮没有删除、覆盖或修改任何原始图片、标签、FoMo4Wheat 权重和历史实验结果。审计读取现有验证报告中的 514 条 aHash 候选记录，并将 hash 桶展开成 **565 个唯一 UID 对**进行逐对比较。

结论如下：

- 文件级精确重复组：**0 组**。
- 在更严格的 pHash、dHash 和缩放像素 RMSE 联合规则下，形成 **4 个高视觉相似候选组，共 11 张图片、7 条严格相似边**。
- 这 4 组是算法筛出的近重复候选，**不能仅凭图像自动认定为同一张图片或同一次拍摄**。联系表和缩略图已生成，均标记为人工复核必需。
- 原始随机划分中有 **1 个严格候选组跨越训练集和验证集**，因此原始 42.14% 结果存在图像级相似性泄漏风险；但目前没有地块、年份或拍摄批次字段，不能进一步确认是否为同一地块或相邻拍摄。
- 在不跨严格候选组的 5 折分层分组划分上重新训练轻量分类头后，SVM RBF 为 43.57% Accuracy、43.10% Macro-F1；Random Forest 为 45.00% Accuracy、44.88% Macro-F1。该变化来自新的分组划分和重新拟合分类头，不能直接解释为“去泄漏后性能提升”。

因此，当前模型仍不具备进入长势融合或面向普通用户做可靠生育期判断的证据条件。

## 2. 逐对检查方法

每个 UID 对记录在 `results/growth_stage_near_duplicate_audit/candidate_pairs.csv`，包括：

- 左右 UID；
- 两张图片的完整 SHA256；
- 原始 aHash 汉明距离；
- 重新计算的 pHash 汉明距离；
- dHash 汉明距离；
- 统一缩放到 64×64 RGB 后的像素 RMSE；
- 两张图的宽度和高度；
- 原训练/验证归属；
- 是否跨原始划分；
- 是否进入严格候选组；
- 复核状态。

严格候选规则为：

```text
pHash 汉明距离 ≤ 10
dHash 汉明距离 ≤ 24
64×64 RGB 像素 RMSE ≤ 0.12
```

这是用于降低漏掉明显近重复的保守筛选规则，不是人工真值，也不是“同一场景”的自动证明。

### 2.1 视觉复核观察

缩略图联系表：

![严格候选组缩略图](../results/growth_stage_near_duplicate_audit/contact_sheet_strict_groups.png)

4 个候选组的缩略图中可以看到部分共同的田间结构、白色标杆、作物条带和相似视角，存在相邻拍摄或同一场景的可能。部分图片的冠层颜色和成熟程度差异明显，说明它们不能直接称为“同一张图”。由于 CSV 没有拍摄日期、地块、相机或批次字段，无法确认这些图像之间的时间关系。

候选组清单：

| 组 | 图片数 | UID | 标签 | 原始划分 | 人工复核 |
|---|---:|---|---|---|---|
| near_group_01 | 4 | C3zKmLSh, P4qTHFf8, ao0UzCHi, nXwj7rWG | 2,4,4,4 | 全部 train | 必需 |
| near_group_02 | 3 | ZdtSjcpy, iATrC2kF, klZRBdVK | 7,6,1 | train + validation | 必需 |
| near_group_03 | 2 | EvXPGc6R, asAXSTgp | 4,3 | 全部 train | 必需 |
| near_group_04 | 2 | of1kWvQP, u1fINmRL | 4,4 | 全部 train | 必需 |

完整分组表见 `results/growth_stage_near_duplicate_audit/near_duplicate_groups.csv`。原始 514 条候选中，其余候选因 pHash、dHash 或像素差异较大，没有进入严格组，但仍保留在联系表中供人工抽查，未被删除。

## 3. 分组后的数据划分

使用严格候选组作为不可拆分 group，未进入候选组的图片作为单例 group。采用 `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=20261114)`，选择验证集规模和七类分布都最接近原协议的折：

- 训练集：560 张；
- 验证集：140 张；
- 七类验证样本仍为每类 20 张；
- 训练/验证严格候选组交集：0。

该划分是图像相似性约束下的可复现实验划分，但仍不是地块独立验证。缺少 `plot_uid`、年份、环境、拍摄批次和日期字段，因此无法保证同一地块或同一拍摄批次不跨集合。

## 4. 三个模型的真实分组评价

分类头使用现有 768 维缓存和原模型超参数重新拟合，FoMo4Wheat 主干没有重新训练。新分类器只保存到 `results/growth_stage_near_duplicate_audit/`，未覆盖生产模型或旧结果。

| 模型 | 分组验证 Accuracy | Macro-F1 | Weighted-F1 | 原验证 Accuracy | 差异 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 35.71% | 35.40% | 35.40% | 37.86% | -2.14 个百分点 |
| SVM RBF | 43.57% | 43.10% | 43.10% | 42.14% | +1.43 个百分点 |
| Random Forest | 45.00% | 44.88% | 44.88% | 32.86% | +12.14 个百分点 |

这些差异不能单独归因于近重复泄漏，因为本轮同时改变了训练/验证划分并重新拟合了分类头。当前证据只能说明：严格分组后没有出现所有模型同步大幅下降；不能据此证明原 42.14% 没有泄漏，也不能证明分组模型已经可靠。

### 4.1 分组验证每类 F1

阶段顺序为 1–7，名称沿用现有模型配置。

| 模型 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 29.17% | 32.56% | 66.67% | 35.90% | 28.57% | 21.62% | 33.33% |
| SVM RBF | 34.29% | 41.51% | 75.68% | 37.50% | 25.81% | 39.13% | 47.83% |
| Random Forest | 30.77% | 38.30% | 75.68% | 56.41% | 28.57% | 35.56% | 48.89% |

阶段 3 相对稳定，阶段 1、5、6 仍是主要薄弱类别。完整每类 Precision、Recall、F1 和三套 7×7 混淆矩阵见：

- `results/growth_stage_near_duplicate_audit/validation_report.json`
- `results/growth_stage_near_duplicate_audit/near_duplicate_groups.csv`
- `results/growth_stage_near_duplicate_audit/candidate_pairs.csv`

## 5. 原始划分与泄漏风险判断

原始 700 张子集的 UID 没有交集，但 UID 隔离不能排除近重复、同一地块或同一拍摄批次泄漏。严格视觉审计发现 1 个候选组跨 train/validation：`ZdtSjcpy, iATrC2kF, klZRBdVK`。这个组应在后续人工核验中确认是否为同一场景、连续拍摄或仅仅是相似的作物纹理。

因此，原始 42.14% 应标记为“UID 分层验证成绩”，而不能标记为“地块独立成绩”。近重复分组验证降低了已发现图像相似性的跨集合风险，但不能替代真正的地块/年份/环境独立验证。

## 6. 是否可以进入长势融合阶段

**暂不建议进入正式长势融合阶段。** 原因是：

1. SVM 分组 Macro-F1 只有 43.10%，仍不足以支撑稳定生育期条件校准；
2. 4 个严格候选组仍需人工确认，514 条候选尚未全部得到人工场景结论；
3. 没有地块、年份、环境和拍摄批次字段，无法完成真正的组级外部验证；
4. 当前七阶段标签来自 CGIAR 数据，尚未证明可迁移到中国品种和手机照片；
5. 生育期结果不应改变现有 V1.1 长势评分，长势融合必须等待真实长势标注和外部验证。

## 7. 下一步

1. 由数据提供方补充 plot、年份、环境、拍摄批次和日期字段，并将同一组元数据整体放入同一集合。
2. 对 4 个严格组和剩余高风险候选进行人工复核，记录“同一场景/相邻拍摄/仅纹理相似/无法判断”，不删除原图。
3. 在完整 10,695 条训练标签上建立分组特征缓存和冻结测试集；没有真实测试标签时继续禁止报告测试准确率。
4. 用中国小麦、手机照片和不同生育阶段建立外部验证集，再考虑生育期条件下的长势评分校准。

## 8. 新增文件

- `scripts/audit_growth_stage_near_duplicates.py`
- `results/growth_stage_near_duplicate_audit/candidate_pairs.csv`
- `results/growth_stage_near_duplicate_audit/near_duplicate_groups.csv`
- `results/growth_stage_near_duplicate_audit/contact_sheet_strict_groups.png`
- `results/growth_stage_near_duplicate_audit/grouped_logistic_regression.joblib`
- `results/growth_stage_near_duplicate_audit/grouped_svm_rbf.joblib`
- `results/growth_stage_near_duplicate_audit/grouped_random_forest.joblib`
- `results/growth_stage_near_duplicate_audit/validation_report.json`

所有数值均由现有图片、缓存和标签实际计算得到；没有使用官方测试集占位标签，也没有伪造模型成绩。
