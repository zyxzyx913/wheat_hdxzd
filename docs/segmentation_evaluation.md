# 分割评价模块使用说明

## 能力与限制

模块位于 `src/wheat_phenotyping/evaluation/`，可独立计算 IoU、Precision、Recall、F1-score，支持多图、多算法、逐图计时、按数据集版本和数据划分汇总，并输出 CSV、JSON 元数据和 SVG 对比图。核心仅使用 Python 标准库及项目内的 `BinaryMask`；人工标注掩膜目前支持 PGM P2/P5，图像 CLI 输入目前支持项目 RGB 读取器可读的 PPM P3/P6。

评价器不搜索参数。验证集用于选算法参数；最终 test 评价必须把验证集结果目录中的 `experiment_metadata.json` 作为冻结参数来源。程序会逐项比较算法参数，不一致时拒绝运行。每次调用只接受一个数据划分，避免把训练、验证、测试记录混在同一次指标汇总中。代码记录划分，但不能替代研究者对样本分组、标签来源及数据泄漏风险的核查。

尺寸不匹配不会自动缩放，而是为该图像/算法记录错误。无效标注也会记录 `invalid_reference` 并继续其余样本。双空掩膜的四项指标约定为 1；某指标分母为零时该指标为 0（双空掩膜例外）。数据集汇总同时给出逐图宏平均（macro）和按所有像素混淆计数计算的 pooled 指标。

## 数据清单格式

准备 UTF-8 CSV，必须包含下列列名。图像和掩膜路径可相对于清单文件填写。

```csv
sample_id,dataset_name,dataset_version,group_id,split,image_path,reference_mask_path,data_source
plot01_view01,public_wheat_example,1.0,plot01,train,images/plot01.ppm,masks/plot01.pgm,public
plot02_view01,public_wheat_example,1.0,plot02,validation,images/plot02.ppm,masks/plot02.pgm,public
plot03_view01,public_wheat_example,1.0,plot03,test,images/plot03.ppm,masks/plot03.pgm,public
```

上表仅展示格式，路径与样本均为示例，不代表项目已包含公开数据。标签必须是人工标注或有来源记录的参考掩膜。PGM 背景值为 0，前景可用 1 或 PGM 最大值（常见为 255）；灰度中间值会判定为无效标签。划分应按植株/地块/采集批次等适当分组，避免近重复图像跨集合。

## 命令行运行

在 Windows PowerShell 中从项目根目录执行：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python scripts\evaluate_segmentation.py `
  --manifest data\manifests\segmentation.csv `
  --split validation `
  --exg-threshold <验证集选定并记录的值> `
  --output-dir results\experiments\exg_validation
```

在完成验证集调参并冻结参数后，才可运行最终测试集：

```powershell
python scripts\evaluate_segmentation.py `
  --manifest data\manifests\segmentation.csv `
  --split test `
  --exg-threshold <验证集元数据中的原值> `
  --frozen-parameters results\experiments\exg_validation\experiment_metadata.json `
  --output-dir results\experiments\exg_test
```

占位符必须替换成实际参数，不能原样执行。当前 CLI 内置 ExG 适配器；其他算法无需修改评价核心，可在调用 `evaluate_batch` 时按相同接口注册：`predictor(image_path, parameters) -> BinaryMask`。每种算法参数都必须作为参数字典传入，以便记录。

## 输出文件

- `image_metrics.csv`：每个样本、每个算法一行，含参数 JSON、数据来源、数据集版本、划分、UTC 实验时间、运行时间、状态、错误和混淆计数/指标。
- `dataset_summary.csv`：按算法、数据集名称/版本和划分汇总成功/失败数、宏平均和 pooled 指标、平均运行时间。
- `algorithm_comparison.svg`：根据实际汇总值绘制四项宏平均指标对比图；没有成功记录时显示空图说明。
- `experiment_metadata.json`：记录算法参数、数据来源、版本、划分、时间、参数是否冻结和指标约定。

运行时间统计 predictor 调用本身；如果 predictor 在调用内部读取图像，读取时间包含在运行时间中。读取参考掩膜和计算指标的时间不计入算法运行时间。

## 单元测试

在项目根目录 PowerShell 中运行：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests\unit -p test_evaluation.py -v
```

测试仅使用临时构造的小型掩膜验证实现正确性，不构成任何真实数据实验结果。
