# 颜色与纹理随机森林分割实验

此基线使用项目自行实现的像素特征提取流程和 scikit-learn 随机森林，不调用论文或其他项目的训练代码。标签目标沿用 EWS 的活体植被/非活体背景二分类。

## 输入特征

每个像素使用 7 个特征：归一化 RGB、ExG、5×5 灰度均值、5×5 灰度标准差、灰度 Sobel 梯度幅值。局部窗口边缘使用最近像素延拓。

## 数据和参数边界

- 只从官方 train 划分训练；每张图每类最多均匀随机抽 500 像素，随机种子为 20261112。
- 随机森林固定 100 棵树、最大深度 18、叶节点最少 2 个样本、平衡子样本类别权重。
- 只在 validation 选择输出概率阈值，目标为排除双空图后的宏平均 F1。阈值候选和两轮验证结果分别记录于 `results/ews/rf_validation/` 与 `results/ews/rf_validation_refined/`。
- test 必须读取 validation 的冻结元数据；评价脚本会核对冻结参数。

## 运行

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\train_rf_segmenter.py --manifest data\processed\ews\manifest.csv --output-dir results\ews\rf_training
.\.venv\Scripts\python.exe scripts\evaluate_rf_segmenter.py --manifest data\processed\ews\manifest.csv --model results\ews\rf_training\rf_color_texture.joblib --split validation --output-dir results\ews\rf_validation_refined --thresholds 0.75,0.8,0.85,0.9,0.95
.\.venv\Scripts\python.exe scripts\evaluate_rf_segmenter.py --manifest data\processed\ews\manifest.csv --model results\ews\rf_training\rf_color_texture.joblib --split test --frozen-metadata results\ews\rf_validation_refined\experiment_metadata.json --output-dir results\ews\rf_test_evaluation
.\.venv\Scripts\python.exe scripts\combine_ews_test_summaries.py --baseline-summary results\ews\test_evaluation\dataset_summary.csv --rf-summary results\ews\rf_test_evaluation\dataset_summary.csv --baseline-images results\ews\test_evaluation\image_metrics.csv --rf-images results\ews\rf_test_evaluation\image_metrics.csv --output-dir results\ews\five_algorithm_comparison
```

## 解释限制

每图抽样训练能控制内存并平衡类别，但不会利用全部像素。当前实验只在单一 EWS 官方划分上训练、验证和测试；模型泛化结论需要额外公开数据集或新采集数据验证。RF 是植被/背景分割基线，不构成器官识别或长势分级验证。
