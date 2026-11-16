# 麦视通 V4.0 未来小麦生长预测交付报告

## 结论

本轮完成了未来预测数据结构、时间序列匹配规则、地块/年份隔离校验、特征构建接口和真实指标计算模块，但 **尚未启用 7 天、15 天或 30 天预测模型**。原因是当前项目没有已下载并完成质量审计的连续地块数据，也没有可以作为未来长势真值的本地训练样本。为了遵守科研真实性要求，本轮没有训练模型、没有生成预测曲线，也没有修改现有预测接口的 `unavailable` 保护。

## 数据审计

WheatPheno 官方 Zenodo 记录显示，第一部分压缩包约 8.9 GB，包含多生育阶段图像和时间序列信息（[Zenodo 记录](https://zenodo.org/records/8115362)）。本轮没有下载该完整压缩包。

WheatPheno/FIP1 的公开数据卡明确包含 `plot_uid`、`images`、`image_dates`、`inner_plot_images`、多项表型值及日期、播种/收获日期和环境时间序列；FIP1 还提供按地块的训练、验证和多种测试划分（[FIP1 数据卡](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md)）。这些字段足以支持后续构建按地块、年份隔离的预测实验，但当前本地项目只有 FIP1/WheatPheno 的审计资料，没有可直接用于本轮训练的完整连续样本。

现有 EWS 是植被/背景分割数据，CGIAR 是七阶段分类数据，二者都没有同一地块连续观测的未来长势标签，因此没有被错误地用于未来回归训练。

## 本轮新增模块

- `src/wheat_phenotyping/future_growth/schemas.py`
  - 定义带地块、年份、日期、输入特征和未来目标的样本结构。
- `src/wheat_phenotyping/future_growth/feature_builder.py`
  - 从已有真实分析记录提取覆盖率、绿色程度、均匀度、亮度和 V1.1 规则分数。
  - 不从未来字段填补当前输入，不把 V1.1 分数当作农学真值。
- `src/wheat_phenotyping/future_growth/temporal_dataset.py`
  - 按 `plot_id + year` 分组并按日期排序。
  - 为 7/15/30 天任务寻找未来观测。
  - 拒绝训练集与测试集地块/年份重叠。
- `src/wheat_phenotyping/future_growth/model_registry.py`
  - 只有带验证报告的模型才允许标记为 enabled；当前登记状态为 `unverified`。
- `src/wheat_phenotyping/future_growth/validation.py`
  - 提供 MAE、RMSE、R² 的真实计算。
- `tests/unit/test_future_growth.py`
  - 覆盖特征提取、未来日期匹配、分组隔离和回归指标计算。

现有 `backend/app/growth_forecast_service.py` 未被解除保护：`GET /api/growth-forecast/status` 仍返回 `enabled=false`，`POST /api/growth-forecast/predict` 的 7/15/30 天结果仍为 `prediction=null`。

## 训练与验证状态

| 期限 | 模型 | 当前状态 | MAE/RMSE/R² | 是否启用 |
|---|---|---|---|---|
| 7 天 | 未训练 | 无连续样本审计结果 | 未计算 | 否 |
| 15 天 | 未训练 | 无连续样本审计结果 | 未计算 | 否 |
| 30 天 | 未训练 | 无连续样本审计结果 | 未计算 | 否 |

当前不能声称上传一张图片后已经实现未来长势预测。单张图片最多提供当前覆盖率、绿色程度、空间均匀度、图像可靠性、V1.1 表观规则初评和 CGIAR 七阶段分类结果；要预测未来变化，至少需要拍摄日期、稳定地块编号、同一地块历史观测，以及未来日期的真实表型测量。天气变量只有在与地块和日期正确匹配时才可使用。

## 测试

本轮新增测试使用程序构造的结构化夹具，不代表真实实验结果。应运行：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
\.venv\Scripts\python.exe -m pytest tests/unit/test_future_growth.py -q
```

已有 V3 验证结果仍保持：Python 单元测试 146 passed、3 skipped、4 subtests；前端 `npm run build` 已通过。新增模块没有修改 V1.1、EWS、CGIAR SVM、FoMo4Wheat、GSP-AI 原始权重或历史实验结果。

## 下一步实际开发顺序

1. 从官方 WheatPheno/FIP1 记录获取最小可用元数据和一小部分对齐图像，保留原始压缩包、许可证、版本和校验值。
2. 统计每个 `plot_uid + year` 的观测日期间隔，分别建立 7/15/30 天可用样本清单；缺失日期不得插值伪造标签。
3. 采用按地块/年份的 GroupKFold 或官方测试划分，先训练 Persistence 和历史相似轨迹基线，再比较 Random Forest、XGBoost、LightGBM 或 CatBoost。
4. 只有某一期限在独立验证中相对于基线有真实提升，并且有效样本量和覆盖率达到预设标准时，才将该期限登记为 enabled 并接入网页。
5. 中国手机照片需要单独的外部验证；瑞士平台数据不能直接证明对中国品种和手机拍摄域有效。

