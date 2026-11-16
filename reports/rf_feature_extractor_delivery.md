# RF 改进特征提取器交付报告

日期：2026-11-14  
范围：仅开发特征提取、特征版本契约、模型契约校验和单元测试。没有训练新模型、没有运行 EWS 推理/精度实验、没有修改网页、传统算法、原始数据或历史结果。

## 1. 开发前检查

检查确认旧实现位于：

- `src/wheat_phenotyping/leaf_segmentation/rf_features.py`：`FEATURE_NAMES` 固定七维，`extract_pixel_features(image)` 使用 RGB、ExG、5×5 灰度均值/标准差和 Sobel 梯度。
- `src/wheat_phenotyping/app/inference.py`：旧 `RF-Color-Texture` 分支调用该七维提取器，并以模型正类概率阈值生成 `BinaryMask`。
- `scripts/train_rf_segmenter.py`：训练时直接导入旧七维特征名和函数；只从 train 划分抽样。
- `scripts/evaluate_rf_segmenter.py`：旧模型推理使用同一七维特征顺序。
- `results/ews/rf_training/rf_color_texture.joblib`：已有 7 输入特征的 `RandomForestClassifier`，本轮未写入。

旧模型的特征顺序未改动：`red, green, blue, excess_green, local_gray_mean_5x5, local_gray_std_5x5, gray_gradient_magnitude`。新模块以旧函数为委托目标，测试中逐值比较，避免重写后产生隐蔽漂移。

## 2. 新增文件

### `src/wheat_phenotyping/leaf_segmentation/rf_improvement/schema.py`

新增不可变 `FeatureConfig` 和 `feature_schema()`：

- 旧版本：`rf-legacy-7-v1`，固定原七维、5×5 纹理和最近边界规则。
- 新版本：`rf-cts-v2`，支持颜色、纹理、空间三组分别启用/关闭。
- schema 保存版本号、名称顺序、维度、RGB 通道顺序、`float32`、行优先布局、最近像素延拓、窗口、最大邻域半径、公式和实现源码摘要。
- `schema_id` 由这些内容计算。改变排列、公式参数或实现摘要会产生不同 ID。

### `src/wheat_phenotyping/leaf_segmentation/rf_improvement/features.py`

新增向量化 `extract_features(image, config)` 和 `iter_feature_bands(...)`：

- 颜色组 8 维：R、G、B、饱和度加权的 `sin(H)`、`cos(H)`、S、V、ExG。
- 纹理组 3 维：配置窗口的灰度均值、灰度标准差、Sobel 梯度幅值。
- 空间组：每个窗口的局部 R/G/B 均值；默认 9×9 和 17×17，共 6 维。
- 使用当前 RGB 图像计算，不读取标签、文件名或测试集统计。
- 对色相采用周期表示；灰度像素的色相分量固定为 0。
- 使用 `scipy.ndimage` 向量化运算，边界使用 `nearest`。
- 输出连续的 C-order `float32` 矩阵，形状为 `(H*W, D)`；遇到 NaN/无穷值或形状错误立即报错。
- 条带接口按照 schema 的最大邻域半径增加 halo，再裁回中心，默认 17×17 时使用 8 行上下文；不会沿条带边界截断邻域。

### `src/wheat_phenotyping/leaf_segmentation/rf_improvement/model.py`

新增模型契约接口：

- `validate_model_features(model, config, metadata)`：同时检查 schema 全文、特征维度和可选的 `feature_names_in_`，不只检查维度。
- `load_feature_model(...)`：校验元数据、模型 SHA-256、实际维度后才加载模型。
- `build_model_metadata(...)`：为未来模型训练生成 sidecar 元数据；本轮没有训练或保存新模型。
- 旧模型元数据没有 schema 字段，因此只能在显式指定旧版本、已知 SHA-256 和允许历史元数据时加载。默认拒绝旧格式的静默兼容。

### `src/wheat_phenotyping/leaf_segmentation/rf_improvement/__init__.py`

集中导出上述接口；没有修改旧 `rf_features.py`、旧 RF 推理入口或传统算法注册表。

### `tests/unit/test_rf_improvement_features.py`

新增 55 个测试场景，覆盖旧特征逐值一致性、所有特征组组合、固定顺序和维度、HSV 与旧标量实现对照、色相周期、边界延拓、不同图像尺寸、整图/分块一致性、重复计算、无效配置、NaN/无穷值、schema 变化、模型维度/顺序/版本/摘要校验以及旧模型的显式兼容推理。

## 3. 特征组合维度

| 颜色 | 纹理 | 空间 | 维度 |
| --- | --- | ---: | ---: |
| 开 | 关 | 关 | 8 |
| 关 | 开 | 关 | 3 |
| 关 | 关 | 开（默认 9、17） | 6 |
| 开 | 开 | 关 | 11 |
| 开 | 关 | 开 | 14 |
| 关 | 开 | 开 | 9 |
| 开 | 开 | 开 | 17 |

其中 8 维颜色组对应实验计划中的基础 RF 组 E；17 维全组合对应改进 RF 组 F。它们目前只有特征提取和契约测试，尚未训练模型，不能报告准确率或优于旧模型的结论。

## 4. 旧版兼容性

旧版 7 维测试将新提取器输出与原 `extract_pixel_features()` 逐元素比较，所有测试通过。已有模型文件 `rf_color_texture.joblib` 仍可通过原有 `predict_visible_mask(..., "RF-Color-Texture", model=...)` 使用；新增加载器只在调用方明确选择旧版本并提供既知模型摘要时接受它。

本轮未修改旧模型文件。旧模型的 SHA-256 仍为：

`61d388a4bd7809ddda3d668c5b19a39af6bd43b80d44eedca5bd756c85f14d85`

## 5. 测试结果

### 新增测试

```text
python -B -m pytest tests/unit/test_rf_improvement_features.py -q
55 passed in 3.94s
```

### 全部现有 Python 单元测试

第一次直接运行时，受限 Windows 运行时将 `tempfile.TemporaryDirectory()` 指向不可写/不可清理的系统沙箱临时目录，出现 24 个 `PermissionError`；失败位置均为测试夹具文件创建或清理，不是特征计算断言。

在不改变任何源码逻辑的前提下，仅为测试进程设置：

```powershell
$env:TEMP = (Join-Path (Get-Location) '.test-tmp')
$env:TMP = $env:TEMP
python -B -m pytest tests/unit -q
```

重跑结果：

```text
119 passed, 3 skipped, 4 subtests passed in 5.56s
```

这里的 119 项包含新增 55 项；3 个 skipped 和 4 个 subtests 是现有测试套件报告的真实结果。本轮没有以任何模拟数据生成实验成绩。

## 6. 文件和数据保护核对

- 未修改 EWS 原始图片、人工标注、`manifest.csv`、数据质量报告或处理掩膜。
- 未修改 `results/ews` 中任何模型、评价 CSV、JSON 或 SVG。
- 未修改 Vue、FastAPI、四种传统算法和旧 RF 训练脚本。
- 源代码新增文件和单元测试是本轮唯一功能性变更；没有新增配置文件和模型产物。
- 原有项目保护快照显示 `scripts`、`configs`、`backend`、`frontend/src`、`results/ews`、`data/raw/ews`、`data/processed/ews` 均未发生内容或文件数变化；`src` 变化仅来自本轮新增 RF 改进包。

## 7. 下一步训练实验建议

下一步才进入训练和验证，建议顺序如下：

1. 新增 train-only 抽样器，保存每张训练图每类的实际像素索引；E/F 使用完全相同的抽样索引。
2. 用 `rf-cts-v2` schema 训练 8 维 E 和 17 维 F；旧 7 维 H 只作为历史参照，不覆盖旧模型。
3. 只在 validation 选择 RF 超参数和概率阈值，要求 24 张验证图全部成功；test 继续冻结。
4. 在训练前先执行计划中的颜色/纹理/空间消融，记录配置、随机种子、依赖版本、schema、模型摘要、运行时间和逐图指标。
5. 通过独立协议门禁后，才进行 A–F 的一次最终比较，并把覆盖率 MAE 与 IoU、Precision、Recall、F1 分开报告。

本轮交付的是可追溯的特征基础设施，不代表随机森林已经训练完成或效果已经改善。
