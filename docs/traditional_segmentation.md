# 传统 RGB 分割算法与对比实验

## 统一算法接口

四种算法通过 `wheat_phenotyping.leaf_segmentation.DEFAULT_REGISTRY` 注册。输入均为同一 `RGBImage`，输出 `AlgorithmPrediction`，其中掩膜为 `BinaryMask`（背景 0、前景 255）。批量评价器为每个算法传入参数字典，并输出同一人工标注上的逐图 IoU、Precision、Recall、F1 和耗时。输入图像当前支持 PPM P3/P6，参考掩膜支持二值 PGM P2/P5；图像尺寸不一致会记录为错误，不自动重采样。

## 算法原理与参数

1. **ExG**：计算 `ExG = 2G - R - B`，当 ExG 严格大于 `exg_threshold` 时判为前景。参数为 `exg_threshold`（必填）及可选 `min_component_area`（默认 0；最小连通域面积）。算法保留现有 ExG 函数。
2. **HSV**：RGB 转为 H∈[0,360)、S/V∈[0,1]，同时满足 H、S、V 范围则判前景。必须显式提供 `hue_min`、`hue_max`、`saturation_min`、`saturation_max`、`value_min`、`value_max`。Hue 下限大于上限时支持跨越 0 度的区间。代码不提供默认颜色阈值。
3. **Otsu-ExG**：先计算整数 ExG，再在固定 [-510,510] 的 1021 档直方图上最大化类间方差。前景定义为 `ExG > computed_threshold`；并列阈值取最小值。每张图的 `computed_exg_threshold` 记录在逐图 CSV 的 `algorithm_metadata_json` 和实验元数据中。不接受手工阈值。
4. **ExG-HSV Fusion**：使用可解释的逻辑交集：`(ExG > exg_threshold) AND (H、S、V 同时落在配置区间)`。这是偏保守的融合规则；参数为 ExG 阈值和 HSV 六个范围参数，可选 `min_component_area`。规则不会在代码中暗自调整。

Otsu 退化到常数 ExG 图时，正值常数全判为前景（阈值设为常数减 1），非正常数全判为背景（阈值等于常数）。此约定避免全绿常量图被 Otsu 分为全背景，也保证全黑图为空；这一行为会由测试固定。

## 参数 JSON

为避免把未经校准的数值误当成小麦通用标准，项目不附带具体阈值。复制 `configs/segmentation/four_algorithms.template.json` 后，用训练集/验证集实验确定并填写数值；模板中的 `null` 必须替换为实际参数，Otsu 无人工阈值：

```json
{
  "ExG": {"exg_threshold": null, "min_component_area": 0},
  "HSV": {
    "hue_min": null, "hue_max": null,
    "saturation_min": null, "saturation_max": null,
    "value_min": null, "value_max": null
  },
  "Otsu-ExG": {},
  "ExG-HSV Fusion": {
    "exg_threshold": null, "min_component_area": 0,
    "hue_min": null, "hue_max": null,
    "saturation_min": null, "saturation_max": null,
    "value_min": null, "value_max": null
  }
}
```

以上 JSON 是**结构模板而非推荐阈值**，必须替换 ExG/HSV 的 `null` 后才可用于实验。

## 运行四算法对比

数据清单列为 `sample_id,dataset_name,dataset_version,group_id,split,image_path,reference_mask_path,data_source`。每个样本只能属于 `train`、`validation`、`test` 之一；同一植株/地块/采集组使用相同 `group_id`，不能跨集合。图像和标注路径相对清单文件。四个算法在一次调用中共享同一划分、同一图像和同一标注。

```powershell
$python = 'C:\Users\89885\AppData\Local\Programs\Python\Python312\python.exe'
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& $python scripts\compare_segmenters.py `
  --manifest data\manifests\wheat_rgb.csv `
  --parameters configs\segmentation\four_algorithms.json `
  --split validation `
  --output-dir results\experiments\traditional_validation
```

验证集选定参数后，将结果目录中的 `experiment_metadata.json` 作为测试集冻结参数来源。程序逐项比对参数，不一致就拒绝运行：

```powershell
& $python scripts\compare_segmenters.py `
  --manifest data\manifests\wheat_rgb.csv `
  --parameters configs\segmentation\four_algorithms.json `
  --split test `
  --frozen-parameters results\experiments\traditional_validation\experiment_metadata.json `
  --output-dir results\experiments\traditional_test
```

## 输出与双空掩膜

- `image_metrics.csv`：每图、每算法的四项指标、耗时、状态、参数和 Otsu 实算阈值。
- `dataset_summary.csv`：各算法 macro 均值、总体标准差（`ddof=0`）、pooled 指标、有效数和失败数。
- `algorithm_comparison.svg`：由实际计算结果绘制的宏平均指标图。
- `experiment_metadata.json`：UTC 时间、划分、来源、数据集版本、完整参数、逐图自动阈值和评价约定。
- `algorithm_parameters.json`：本次实验参数快照。
- 使用 `--save-overlays` 时，还会输出逐图叠加图：TP 绿、FP 红、FN 蓝，背景区域保留原图。

双空（人工和预测掩膜都无前景）图像会在逐图 CSV 标记，并在汇总中计数。为避免空图抬高 macro 分数，macro 均值和标准差排除双空图；`pooled_*` 基于所有有效图的混淆计数，双空图不增加前景计数。若某算法/数据集的成功图全是双空图，macro、标准差和 pooled 前景指标均留空。双空图判定不改动 IoU 等单图评价定义。

## 参数候选校准

复制 `configs/segmentation/candidate_grid.template.json`，用训练集/验证集要比较的候选值替换 `null`（可给每个算法列出多个参数对象；Otsu-ExG 固定为 `[{}]`）。校准脚本仅接受 `train` 或 `validation`，按所选指标在非双空图上计算候选平均值，并输出候选 CSV、所选参数 JSON 和可供测试集核对的 `experiment_metadata.json`。不要将 `test` 样本用于候选定义、选择或排序。

```powershell
& $python scripts\tune_segmenters.py `
  --manifest data\manifests\wheat_rgb.csv `
  --candidates configs\segmentation\candidate_grid.json `
  --split validation `
  --metric f1_score `
  --output-dir results\experiments\calibration_validation
```

将输出的 `selected_parameters.json` 作为四算法比较的 `--parameters`，将同目录 `experiment_metadata.json` 作为 `--frozen-parameters` 进行 test 评价。候选参数由研究者依据训练/验证数据定义；项目没有宣称任何参数是通用最优值。

## 人工标注和划分

每张原始 RGB 图像准备同尺寸、逐像素对齐的二值 PGM 标注（背景 0、叶片前景 1 或 255）。人工标注应保存来源、标注者/流程和版本；不得由被比较算法生成后冒充人工真值。按植株、地块、采集批次或拍摄序列分组划分，防止相同植株或近重复图像跨训练/验证/测试集合。算法参数只在训练/验证集选择；test 使用验证实验元数据冻结参数。模拟样本需标 `data_source=simulated`，单独报告，不与公开或真实数据混称。

## 测试

```powershell
$env:TMP = (Join-Path (Get-Location) '.test-tmp')
$env:TEMP = $env:TMP
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& .\.venv\Scripts\python.exe -m pytest tests/unit -v
```
