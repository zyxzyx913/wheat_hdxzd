# 生育期分类模型评价报告

实验编号：`growth-stage-fomo-subset-20261114`

## 实验范围

本轮采用冻结的 FoMo4Wheat ViT-B/14 base CLS 特征（768 维），不更新视觉骨干。输入为 CGIAR 训练标签中每个阶段固定 100 张、共 700 张图片；随机种子为 20261114。按阶段分层切分训练集 560 张、验证集 140 张。由于当前训练 CSV 缺少可靠地块/农户分组字段，结果是 UID 分层初步实验，不能当作地块独立验证或完整数据集最终成绩。

官方测试集没有真实标签：`SampleSubmission.csv` 的 3,558 个 `growth_stage` 全为占位 0。因此没有计算、保存或展示测试准确率。

## 轻量分类器比较（验证集）

| 模型 | Accuracy | Macro Precision | Macro Recall | Macro F1 | Weighted F1 |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.3786 | 0.4024 | 0.3786 | 0.3820 | 0.3820 |
| SVM RBF | **0.4214** | **0.4198** | **0.4214** | **0.4136** | 0.4136 |
| Random Forest | 0.3286 | 0.3240 | 0.3286 | 0.3234 | 0.3234 |

训练集结果也已单独计算并保存在 `results/growth_stage_initial/experiment_metadata.json`：Logistic Regression Accuracy/Macro-F1 均为 1.0000，SVM RBF 为 0.7071/0.7049，Random Forest 为 1.0000/1.0000。训练与验证之间的落差说明子集模型存在明显泛化风险；选择 SVM 只依据验证集 Macro-F1，不依据训练集成绩。

选择规则是验证集 Macro-F1，当前选择 `svm_rbf`。这些数值均由真实验证预测计算，不能解释为中国小麦或手机照片上的准确率。

## 选择模型的各阶段指标

| 阶段 | Precision | Recall | F1 | Support |
|---:|---:|---:|---:|---:|
| 1 | 0.3125 | 0.2500 | 0.2778 | 20 |
| 2 | 0.2500 | 0.2000 | 0.2222 | 20 |
| 3 | 0.7391 | 0.8500 | 0.7907 | 20 |
| 4 | 0.5385 | 0.3500 | 0.4242 | 20 |
| 5 | 0.3000 | 0.3000 | 0.3000 | 20 |
| 6 | 0.3226 | 0.5000 | 0.3922 | 20 |
| 7 | 0.4762 | 0.5000 | 0.4878 | 20 |

质量代码分组（仅保留 CSV 数值代码，不命名为专家或农户）：

| label_quality | 验证数量 | Accuracy | Macro F1 |
|---:|---:|---:|---:|
| 1 | 96 | 0.2604 | 0.1786 |
| 2 | 44 | 0.7727 | 0.5402 |

分组差异说明标签来源/质量代码与视觉可分性可能存在关系，但由于官方代码含义字典未在本地 CSV 中提供，不能把它解释成专家和农户的真实对照结论。

## 混淆矩阵

七行七列顺序均为阶段 1 到 7；文件为 `results/growth_stage_initial/validation_confusion_matrix.csv`。阶段 3 的验证召回为 0.85，阶段 1、2、5 的召回较低，反映阶段相邻外观相似和子集规模限制。

## 推理和产物

FoMo CPU 特征提取总耗时约 43.805 秒，平均单图模型特征耗时约 0.0574 秒。RTX 5060 Laptop GPU 已检测到，但现有 `torch 2.5.1+cu121` 对该 GPU 报 `no kernel image is available`，本轮严格回退 CPU；没有把 GPU 失败伪装成成功。

产物：

- `results/growth_stage_initial/selected_model.joblib`：按 Macro-F1 选择的 SVM RBF。
- `results/growth_stage_initial/logistic_regression.joblib`、`svm_rbf.joblib`、`random_forest.joblib`。
- `results/growth_stage_initial/fomo_features_subset.npz`：700 张 768 维缓存。
- `results/growth_stage_initial/class_mapping.json`：阶段编号与中文显示名。
- `results/growth_stage_initial/validation_classification_report.csv`。
- `results/growth_stage_initial/train_classification_report.csv`。
- `results/growth_stage_initial/validation_confusion_matrix.csv`。
- `results/growth_stage_initial/label_quality_group_metrics.json`。
- `results/growth_stage_initial/experiment_metadata.json`：随机种子、样本量、权重哈希、预处理和模型指标。

## 结论边界

这是今晚用于网页演示的可追溯初步分类器，不能直接宣传为已经完成的中国小麦生育期识别，也不能把阶段识别结果直接当成长势好坏。下一步应获得地块/农户分组字段，完成按地块或年份环境的验证，并在完整训练数据上做冻结测试评估；同时收集中国手机图片进行域适配验证。
