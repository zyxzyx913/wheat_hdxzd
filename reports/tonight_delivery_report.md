# 麦视通今晚快速交付报告

交付批次：2026-11-14
项目：基于 CGIAR 生育期标签的冻结 FoMo4Wheat 特征 + 轻量分类头演示闭环

## 已实际完成

1. 将原始 `Images.zip` 解压到 `data/processed/growth_stage/images/`，原始 ZIP、CSV 保留。
2. 完成 14,253 张 JPEG 的全量解码、模式、尺寸、内容重复和 UID 配对审计：全部可读、0 张损坏、0 个内容重复组；训练 10,695 个 UID 与测试 3,558 个 UID 无交集。
3. 创建 `manifest_verified.csv`，保留训练标签和 `label_quality` 数值来源。
4. 在冻结 FoMo4Wheat ViT-B/14 768 维特征上，按每类 100 张、共 700 张完成可复现的初步实验。视觉骨干未训练，特征缓存已保存。
5. 比较 Logistic Regression、SVM RBF、Random Forest，按验证集 Macro-F1 选择 SVM RBF。
6. 保存分类器、类别映射、特征缓存、实验元数据、分类报告、混淆矩阵和质量代码分组指标。
7. 新增 `POST /api/growth-stage/predict`：上传一张 JPG/JPEG/PNG 后，真实执行 FoMo 特征和分类头，返回阶段、7 类概率、置信度、模型版本、设备和推理时间；模型缺失或加载失败时返回不可用错误，不返回随机概率。
8. 在现有长势分析页面增加“识别生育期”按钮、阶段结果卡和七阶段概率条，同时保留长势分析 V1 的真实分割指标。生育期识别不被解释为长势好坏。

## 真实验证结果

本次初步验证集（140 张、每类 20 张）结果：

- SVM RBF：Accuracy 0.4214，Macro Precision 0.4198，Macro Recall 0.4214，Macro-F1 0.4136，Weighted-F1 0.4136。
- Logistic Regression：Macro-F1 0.3820。
- Random Forest：Macro-F1 0.3234。

各阶段指标与混淆矩阵见 `reports/growth_stage_model_evaluation.md`。这些是分层子集的真实验证结果，不是完整数据集成绩，也不是中国小麦或手机照片准确率。

训练集结果已另存：Logistic Regression 和 Random Forest 的训练 Macro-F1 为 1.0000，SVM RBF 为 0.7049；训练/验证落差提示当前 700 张子集存在过拟合和泛化风险。

## 测试集处理

`SampleSubmission.csv` 有 3,558 个测试 UID，但 `growth_stage` 全部为占位 0，未计算测试 Accuracy、Precision、Recall、F1，也未将占位值当成真值。没有任何测试集调参。

## FastAPI 与网页状态

代码路径：

- `backend/app/growth_stage_service.py`
- `backend/app/main.py`
- `backend/app/schemas.py`
- `src/wheat_phenotyping/foundation_models/fomo4wheat/extractor.py`（新增安全的 PIL 输入入口）
- `frontend/src/services/imageApi.js`
- `frontend/src/views/GrowthAnalysis.vue`

已完成本机真实 HTTP 冒烟：用 Uvicorn 启动后，`GET /api/health` 返回 200，使用解压后的 CGIAR JPEG 调用 `POST /api/growth-stage/predict` 返回 200；模型返回阶段 2（早期营养生长/分蘖期）、七类概率、置信度约 0.2284、CPU 推理，原图尺寸 512×200。记录写入 `var/web/growth_stage/<task_id>/`。这不是测试集成绩。

前端 `npm run build` 已通过（Vite 7.3.8，生产构建成功）。合并运行 `tests/unit` 与 `backend/tests`：174 passed、3 skipped、4 subtests passed；新增生育期接口测试包含真实 CGIAR JPEG 和七类概率校验。FastAPI 本机 Uvicorn HTTP 冒烟也已通过。

## 今晚演示方式

1. 后端（PowerShell，项目根目录）：

```powershell
$env:TEMP = "$PWD\.test-tmp"
$env:TMP = $env:TEMP
$env:PYTHONPATH = "$PWD\.venv-fomo\Lib\site-packages;$PWD\.external\dinov2;$PWD\src"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

2. 前端：

```powershell
cd frontend
npm run dev
```

3. 浏览器打开 `http://127.0.0.1:5173`，进入“长势分析”，选择一张 CGIAR JPEG 或自己的 JPG/PNG，点击“开始分析”查看真实分割和 V1 指标，再点击“识别生育期”查看阶段和概率。

若后端启动受到 Windows 沙箱端口限制，在普通 PowerShell 中执行上述命令；不要把浏览器页面显示的“等待数据接入”当作模型结果。

## 仍不能使用的功能

- 没有测试真值，因此不能提供官方测试集成绩。
- 没有可靠地块/农户分组字段，尚未完成地块独立或年份/环境独立验证。
- 模型只在 CGIAR 印度田间数据的固定子集上做初步验证，尚未证明适用于中国品种、地区和手机照片。
- 未来 7/15/30 天生长趋势、长势等级、产量预测和价格预测本轮没有生成任何数值。
- RTX 5060 当前 CUDA wheel 报 `no kernel image is available`，本轮生育期推理固定 CPU；没有把 GPU 失败伪装成成功。

## 下一阶段最重要的三项工作

1. 获取地块/农户/年份环境分组元数据，完成按地块冻结的验证与真实测试评价。
2. 使用完整训练标签缓存 FoMo 特征，比较完整数据上的分类头和类别不平衡处理，并保留独立中国手机图像外部验证集。
3. 在有时间序列表型标签后，单独建立未来 7/15/30 天预测任务；不要把当前单图阶段分类器直接当成长势或未来预测模型。
