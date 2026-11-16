# 小麦长势初步分析 V1 交付报告

日期：2026-11-14  
项目：麦视通——小麦智能分析与预测系统  
范围：基于现有四种分割算法和真实分割掩膜，计算单幅图像的可见植被代理指标。本轮不训练长势等级、生育期或未来趋势模型。

## 1. 开发前检查结论

已复用的现有功能如下：

- `backend/app/image_service.py::validate_and_decode`：校验 JPG/JPEG/PNG、解码、EXIF 方向、透明背景和尺寸限制。
- `src/wheat_phenotyping/data/image_io.py::load_rgb_image`：将规范化原图读取为项目统一 `RGBImage`。
- `src/wheat_phenotyping/app/inference.py::predict_visible_mask`：统一调用 ExG、HSV、Otsu-ExG、ExG-HSV Fusion，不重复实现算法。
- `backend/app/image_service.py::write_prediction_images`：保存原图、实际生成的掩膜和叠加图。
- 既有 `extract_visible_growth_features` 仍保留，用于旧桌面/批量流程；V1 新模块独立计算覆盖率、绿色程度、空间均匀度和图像质量，不改变旧函数。
- `frontend/src/services/imageApi.js::analyzeImage`：长势页面复用现有上传和分析请求，不新增虚假接口。

## 2. 新增和修改文件

### 新增

- `src/wheat_phenotyping/growth_analysis/__init__.py`
- `src/wheat_phenotyping/growth_analysis/metrics.py`
- `tests/unit/test_growth_analysis.py`
- `backend/tests/test_growth_api.py`
- `reports/growth_analysis_v1_delivery.md`

### 修改

- `backend/app/schemas.py`：响应增加 `growth_analysis` 和 `growth_analysis_url` 字段。
- `backend/app/image_service.py`：在同一分析任务中复用 RGB 与实际掩膜，保存 `growth_analysis.json` 并返回 V1 指标。
- `backend/app/main.py`：允许通过受限媒体路由读取当前任务的 `growth_analysis.json`。
- `frontend/src/views/GrowthAnalysis.vue`：增加真实上传、算法选择、分析状态、原图/掩膜/叠加图和指标可视化。

未修改四种分割算法、EWS 数据、人工标注、旧模型、历史实验结果、价格模块或其他 Python 算法。

## 3. 指标定义

### 3.1 植被覆盖率

使用实际二值分割掩膜：

`coverage_fraction = foreground_pixels / valid_pixels`

同时输出 `fraction`、`percentage`、植被像素数和有效像素数。V1 的有效像素是 EXIF 校正后 RGB 图像的全部像素。该值只描述画面可见植被比例，不等同于长势等级、真实冠层覆盖度或田间生物量。

### 3.2 植被绿色程度

在掩膜前景区域计算：

`green_degree = mean(G / 255)`

输出 0–1 比例和百分比。结果明确标注为 RGB 绿色通道代理指标，不能解释为叶绿素含量、氮含量或生物量测量。

### 3.3 植被分布均匀度

默认把图像划分为 4×4 网格，逐格计算覆盖率，并输出：

- 网格覆盖率数组，可直接用于热力图。
- 覆盖率均值。
- 覆盖率总体标准差。
- 变异系数 `CV = std / mean`；均值为 0 时返回 `null`，不制造无限值。

这是二维图像空间分布指标，不代表田间真实植株密度或群体均匀度。

### 3.4 图像质量

输出图像宽高、灰度平均亮度、过暗像素比例、过曝像素比例、饱和像素比例和拉普拉斯方差清晰度参考值。

过暗、过曝提示采用显式质量阈值，并随结果保存。它们是图像质量风险提示，不是分类阈值，也不是农学阈值。清晰度指标用于相对质量参考，不能直接解释为相机 MTF 或田间观测精度。

## 4. 后端数据结构与存储

每个任务仍使用已有 32 位十六进制 `task_id`，示例结构为：

```json
{
  "status": "completed",
  "version": "growth-analysis-v1",
  "task_id": "...",
  "algorithm": "ExG",
  "metrics": {
    "vegetation_coverage": {},
    "green_degree": {},
    "distribution_uniformity": {},
    "image_quality": {}
  },
  "analysis_time_seconds": 0.0,
  "explanations": [],
  "limitations": []
}
```

分析目录现在同时保存：

- `uploaded_original.jpg/png`
- `original.png`
- `mask.png`
- `overlay.png`
- `growth_analysis.json`
- `record.json`

V1 结果通过 `/media/{task_id}/growth_analysis.json` 提供访问。分析失败仍沿用已有失败记录流程，不返回伪造成功结果。

## 5. Vue 页面功能

`GrowthAnalysis.vue` 已从静态等待页面改为真实图像工作台：

1. 选择 JPG/JPEG/PNG 图片并显示本地预览。
2. 选择 ExG、HSV、Otsu-ExG 或 ExG-HSV Fusion。
3. 调用现有 FastAPI 分析接口。
4. 显示加载、失败和成功状态。
5. 展示原图、分割掩膜和叠加图。
6. 展示覆盖率环形图、绿色程度、均匀度 CV、图像质量。
7. 根据真实网格覆盖率生成热力图。
8. 明确显示“长势等级模型待训练与验证”。
9. 明确区分绿色程度、覆盖率、均匀度和未来趋势的含义边界。

当前页面支持上传新图片；已有历史记录的列表选择接口尚未建立，因此没有伪造“已有记录”选项。后续可在记录列表 API 完成后接入选择历史任务。

## 6. 真实图像冒烟分析

使用现有 EWS train 图像：

`FPWW0220011_RGB1_20180316_100219_6.png`（350×350，真实公开 RGB 图像；本次仅做接口/流程冒烟，不计算新的 EWS 精度成绩）。使用四种算法分别生成真实掩膜并计算 V1 指标：

| 算法 | 可见植被覆盖率 | 绿色程度 | 均匀度 CV | 平均亮度 | 风险提示 |
| --- | ---: | ---: | ---: | ---: | --- |
| ExG | 28.0620% | 58.2014% | 0.4701 | 52.6977% | 无 |
| HSV | 27.0531% | 57.0073% | 0.4750 | 52.6977% | 无 |
| Otsu-ExG | 21.6947% | 59.1639% | 0.5250 | 52.6977% | 无 |
| ExG-HSV Fusion | 27.0531% | 57.0073% | 0.4750 | 52.6977% | 无 |

这些数值是该真实图像的实际计算结果，不是模拟数字，也不是准确率。不同算法的覆盖率差异只说明分割掩膜不同，不能直接说明哪个算法准确率更高。该冒烟分析未使用人工标注计算 IoU，也未修改历史 EWS 评价结果。

每种算法的任务目录位于临时冒烟目录 `.test-tmp/growth-v1-smoke/analyses/`，没有写入 EWS 原始数据或历史 `results/ews`。

## 7. 测试结果

### 指标测试

```text
tests/unit/test_growth_analysis.py
7 passed
```

覆盖尺寸一致性、RGB 通道顺序、空掩膜、过暗、过曝、网格配置、均匀度、无效掩膜和不生成等级结果。

### 全部 Python 单元测试

```text
126 passed, 3 skipped, 4 subtests passed in 5.49s
```

测试进程使用项目内 `.test-tmp` 作为 `TEMP/TMP`，避免 Windows 受限运行时系统临时目录权限问题。

### API 测试限制

新增 `backend/tests/test_growth_api.py` 覆盖四算法响应、JSON 保存、媒体访问和不返回长势等级。但当前 Codex Windows 沙箱的 FastAPI `TestClient` 在事件循环启动阶段卡住，直接绑定本地端口也被沙箱拒绝，因此本轮无法把 HTTP 测试结果报告为通过。

已完成的替代验证包括：

- 直接调用真实 `analyze_image()` 完成四种算法流程。
- 检查四种算法返回的覆盖率与掩膜前景像素一致。
- 检查 `growth_analysis.json` 保存内容与返回对象一致。
- `compileall` 检查后端和新增测试模块通过。

在普通 Windows 11 本机环境启动后端后，应执行：

```powershell
python -m pytest backend/tests/test_growth_api.py -v
```

## 8. 前端构建结果

已执行：

```powershell
npm run build
```

结果：Vite 成功转换 1618 个模块并完成生产构建，`GrowthAnalysis` 页面构建产物生成成功。

## 9. 当前功能边界

本版本可以从一张真实上传图片计算当前画面的可见植被指标，但还不能可靠完成：

- “好、一般、差”长势等级分类。
- 出苗期、分蘖期、拔节期等生育期识别。
- 连续时间序列生长趋势预测。
- 产量预测或市场价格预测。
- 叶片、茎秆、麦穗器官分类。
- 真实田间密度、叶绿素、株高和生物量测量。

这些功能需要带农学标签的纵向数据、标定信息或器官级标注，不能由 EWS 的活体植被/背景二分类标签直接推导。

## 10. 下一步长势等级模型数据要求

建议建立独立的真实数据协议，每个样本至少包含：

1. 原始 RGB 图像、拍摄日期、地块和拍摄条件。
2. 与图像严格配对的植被掩膜或质量审核记录。
3. 小麦生育期标签，按统一农学标准由专业人员确认。
4. 长势等级标签及其判定依据，不能由当前覆盖率阈值事后生成。
5. 同一地块的多日期纵向观测。
6. 产量实测、收获期水分、品种、播期、施肥和天气等辅助变量（若研究产量/价格）。
7. 明确的 train/validation/test 地块级划分，避免同一地块或同一时序泄漏。

在这些数据完成前，系统只显示“长势初步分析已完成”和真实图像代理指标，不生成未经验证的长势结论。
