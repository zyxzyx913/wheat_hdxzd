# 小麦图像识别模块现状审查

**首次检查日期：** 2026-11-12  
**最近进展更新：** 2026-11-13  
**项目：** `D:\Desktop\wheat\source-code\wheat-phenotyping`  
**检查范围：** RGB 图像读取、分割算法、图像入口、批量处理、器官识别、数据集和测试  
**首次检查约束：** 2026-11-12 检查仅新增本报告；2026-11-13 按后续开发指示扩展了图像桌面推理入口，没有训练模型、下载数据或改动价格预测/经济收益模块。

## 检查结论摘要

EWS 的四种传统植被/背景分割算法已有统一注册接口和共同评价器；仓库保存的 EWS 测试集记录显示四种算法各处理 24 张图像，96 条记录全部成功，样本集合相同。2026-11-13 又将四种算法及 RF 接入桌面入口，支持单图或文件夹推理并导出逐图结果、PGM 掩膜和 PNG 叠加图。当前任务仍是**活体植被与非活体/背景二分类**，没有叶片、茎秆、麦穗器官分类分割。项目内没有找到 GWFSS 数据文件或目录。

## 1. 现有实现检查

### 算法与接口

四种算法由 `src/wheat_phenotyping/leaf_segmentation/registry.py` 注册，统一接收 `RGBImage` 和参数映射，返回 `AlgorithmPrediction`，其 `mask` 为前景 255、背景 0 的二值 `BinaryMask`。

| 算法 | 实现 | 当前方法 |
|---|---|---|
| ExG | `leaf_segmentation/exg.py` | 对 `2G-R-B` 使用显式阈值，可选移除小连通域 |
| HSV | `leaf_segmentation/hsv.py` | 按调用方传入的 H/S/V 范围判定绿色区域 |
| Otsu-ExG | `leaf_segmentation/otsu.py` | 对 ExG 整数直方图逐图计算 Otsu 阈值，并记录实算值 |
| ExG-HSV Fusion | `leaf_segmentation/fusion.py` | ExG 与 HSV 均通过才标记前景（逻辑 AND） |

四算法有统一注册名、参数校验以及对同一 RGB 输入产生标准掩膜的接口。测试代码还覆盖四种算法共享同一参考掩膜、经同一批量评价器运行。

### 图像读取、单图入口和可视化

- `data/image_io.py` 的 `load_rgb_image` 支持 PPM、PNG、JPEG、BMP、TIFF；对带 EXIF 方向的图像进行方向校正并转为 RGB。读取评价掩膜时检查二值像素，图像和掩膜尺寸不一致时拒绝自动缩放。
- 已有 Windows Tk 桌面入口 `python -m wheat_phenotyping.app.desktop`，使用本地文件选择框导入单张图片或文件夹；支持 ExG、HSV、Otsu-ExG、ExG-HSV Fusion、RF-Color-Texture，可选递归子文件夹。结果逐图写出 CSV/JSON、PGM 掩膜和 PNG 绿色叠加图，并在界面显示运行状态和首个成功预览。这是本地桌面导入，不是网页上传服务。
- `visualization/segmentation_overlay.py` 可将 TP/FP/FN 区域叠加到 RGB 图像并保存 PNG；评价流程可选保存与人工标注比较的叠加图。
- 旧命令行入口 `scripts/analyze_growth_image.py` 仅支持 PPM P3/P6、ExG 分割，并要求调用者明确输入弱/中等级面积阈值。这些阈值不是经 EWS 验证的农学等级界限。

### 批量处理

已实现两类批处理：`scripts/compare_segmenters.py` 对带人工掩膜的 manifest 做分割评价；桌面端 `app/inference.py` 对未标注图片目录推理，逐图记录成功/失败、参数、耗时、面积比例，并保存预测掩膜与叠加图。桌面批处理当前同步执行，没有中断/暂停队列，也尚未对超大目录做性能评估。

### 器官分类分割

没有发现叶片、茎秆、麦穗彼此区分的图像分割标签或算法。虽然部分模块以 `leaf_segmentation` 命名，EWS 人工掩膜的标签语义实际是“活体植被 / 非活体或背景”。它不能区分叶片、茎秆或麦穗，也不能作为器官识别结果描述。模拟程序包含叶片几何生成和 `leaf_id` 点云标签，但这属于程序生成的模拟样本，不是 EWS 真实图像器官标签。

### 数据集与当前实验记录

- EWS 已存在于 `data/raw/ews/` 和 `data/processed/ews/`。本地摘要记录 190 张 RGB 图像与 190 份标注；官方划分为 train 142、validation 24、test 24，图像尺寸均为 350 × 350。
- 处理后的掩膜是从原始 PNG 派生的二值 PGM：0 为背景、1 为活体植被。原 PNG 保留；灰度边缘值按记录的亮度阈值二值化，因此 PGM 是量化后的派生标注。
- 在 `data/raw/public/`、`data/raw/real/`、`data/raw/ews/` 和项目代码/文档目录中检查名称，未发现 GWFSS 数据集文件或目录。**本轮未下载 GWFSS。**
- 已有 EWS 四算法测试集实验产物位于 `results/ews/test_evaluation/`。`experiment_metadata.json` 记录参数已冻结、仅评估 test split；`image_metrics.csv` 有 96 行：ExG、HSV、Otsu-ExG、ExG-HSV Fusion 各 24 行，各算法 status 均为 `ok`，均对应相同 24 个 sample_id。双空掩膜数为 0。此结论来自现有实验记录的逐行核查，并非本轮重新训练或重新调参。

## 2. 测试情况

2026-11-12 首次检查时使用项目虚拟环境 Python 3.12.10 运行图像读取、分割、评价、可视化和桌面入口相关测试：34 passed。2026-11-13 更新桌面端后重新运行全套单元测试：

```powershell
$env:PYTHONPATH = "src"
$env:TEMP = (Join-Path (Get-Location) ".test-tmp")
$env:TMP = $env:TEMP
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider `
  tests\unit\test_leaf_segmentation.py `
  tests\unit\test_traditional_segmenters.py `
  tests\unit\test_data.py `
  tests\unit\test_evaluation.py `
  tests\unit\test_visualization.py `
  tests\unit\test_photo_app.py -q
```

**最新结果：64 passed，3 skipped，0 failed，另 4 个 subtests passed。** 本轮还将一个 EWS 训练划分图像输入桌面批处理链路，五种算法均成功并生成预期结果文件。自动化测试和该软件烟雾检查不等同于用户自有田间照片验证。已保存 EWS 测试评价 CSV 仍为 96/96 条成功，四传统算法样本集合完全一致。

## A. 已经完成的功能

- EWS 公开数据集已导入，保留官方 train/validation/test 划分和原始 PNG 标注，并生成数据清单、数据摘要与质量报告。
- ExG、HSV、Otsu-ExG、ExG-HSV Fusion 已实现并接入统一注册接口；四算法已有共同人工掩膜上的批量评价产物。
- RGB 图像读取支持 PPM、PNG、JPEG、BMP、TIFF；有掩膜尺寸校验、二值标签校验、实验指标和参数记录。
- 已有本地桌面单图/文件夹推理入口，支持四种传统算法和 RF，显示分割预览并导出逐图 CSV/JSON、PGM 掩膜和 PNG 叠加图。
- 已有分割掩膜叠加可视化以及 34 项通过的相关自动化测试。

## B. 尚未完成的功能

- 叶片、茎秆、麦穗的器官级分类分割及对应有标注数据。
- 经过农学等级标签校准的长势分类，以及基于同一地块连续观测的未来长势预测。
- 对用户手机/相机拍摄图像的独立外部验证；当前 RF 模型基于 EWS 场景训练，不能据现有 EWS 测试成绩推断新拍摄条件下的泛化效果。
- 桌面端算法结果目前逐条显示，尚无多算法并排视觉比较、任务暂停/取消或大目录性能优化。
- GWFSS 数据集：当前本地项目未发现；按本轮要求没有下载。

## C. 当前最严重的三个问题

1. **标签任务与最终目标不匹配。** EWS 只有活体植被/非活体背景标签，没有器官类别或农学长势等级，现有分割不能回答“叶、茎、穗分别是什么”或可靠判断长势等级。
2. **对新拍摄图像的适用性未经验证。** 当前模型和结果来自单一 EWS 数据集，只有 24 张官方测试图；拍摄设备、距离、光照、背景变化可能导致分布偏移。当前单图面积比例只是画面内植被可见比例代理值。
3. **用户场景验证仍缺失。** 桌面端现在支持五种算法和文件夹批量推理，但尚未用独立手机/田间图像及人工标注验证新场景下的分割质量，界面面积比不能直接解释成农学长势。

## D. 下一步最值得做的一个任务

**建立独立的手机/田间图像外部验证集。** 目前软件入口已支持单图和批量推理，最关键的不确定性转为：EWS 训练的模型和传统阈值算法能否适用于用户实际拍摄的小麦图像。

## E. 完成该任务的具体步骤

1. 明确相机/手机拍摄协议：拍摄距离、视角、光照、背景、地块/植株 ID、拍摄日期及生育期；取得可用于研究的授权。
2. 为独立拍摄图像制作活体植被/非活体像素标注，记录标注规则与复核过程；不要伪装成叶、茎、穗器官标注。
3. 按地块、植株或拍摄序列分组，避免相邻帧泄漏；以验证组冻结算法配置，测试组只用于一次最终评价。
4. 用桌面批量入口生成预测，按算法报告 IoU、Precision、Recall、F1、运行时间和失败数，并保存数据来源、参数、图像分组和评价产物。
5. 比较 EWS 内部测试结果与外部测试结果；若外部表现不足，再使用训练/验证数据研究改进，保留独立外部测试集不参与调参。

---

**审查结论：** 当前已具备 RGB 植被/背景分割研究原型和单图演示入口；尚不是器官识别或农学长势评估成品。
