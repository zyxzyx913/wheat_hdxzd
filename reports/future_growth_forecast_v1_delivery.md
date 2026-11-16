# 未来小麦长势预测 V1（免训练模型接入版）交付报告

## 1. 交付结论

本轮完成了免训练预测适配层、FastAPI 接口、网页状态展示和真实性保护，但**没有生成未来 7/15/30 天预测数值**。原因是目前没有找到同时满足以下条件的可直接使用模型：

- 已公开权重；
- 官方独立推理代码；
- 输入为当前单张 RGB 图片或明确的可用多时相输入；
- 明确输出未来 7、15、30 天连续小麦长势指标；
- 可在当前 Python 3.12/Windows 11 环境中复现；
- 许可允许当前科研项目使用。

因此，接口和网页现在会显示“预测模型尚未验证”，不会生成随机曲线、当前分数外推值或未经验证的未来结果。

## 2. 公开预训练模型核查

### 2.1 GSP-AI/WGSP

官方仓库和 Release 提供模型包、iPython 调用文件、中国/英美环境数据、WGSP-CN 和 WGSP-Smartphone 数据。论文描述该模型使用无人机/手机图像和气象因素进行关键生育期识别与开花日期预测，并报告了生育期和开花日期结果。[官方仓库](https://github.com/The-Zhou-Lab/GSP-AI)、[官方 Release V1.1](https://github.com/The-Zhou-Lab/GSP-AI/releases)、[论文页面](https://spj.science.org/doi/10.34133/plantphenomics.0255)

核查结论：

- 有公开权重和推理流程：是；
- 目标：生育期/开花日期，不是直接 7/15/30 天连续长势；
- 输入：图像 + 气象/试验上下文，不能只依赖当前单图；
- Windows/Python 3.12：官方 README 使用较旧 TensorFlow 2.2 等依赖，当前环境尚未验证；
- 许可：软件 MIT，但 Release 明确测试数据、人工花期数据和模型资源为学术使用；
- 本轮状态：**未下载权重、未接入推理**。不能把它宣传为已完成的未来长势预测模型。

### 2.2 WheatPheno

WheatPheno 是中国南京农业大学数据资源，固定 RGB 相机对同一批小区连续观测，两年、小时级采集、约 32 万张质量图像和五个阶段。[PhenoNet 官方说明](https://phenonet.org/wheatpheno)、[Zenodo 数据记录](https://zenodo.org/records/8115362)

核查结论：

- 它是时间序列数据集，不是现成未来预测模型；
- 当前公开页面未给出可直接调用的 7/15/30 天预训练预测权重；
- 可用于后续构造同一小区的阶段/时间到阶段任务；
- Zenodo 页面没有明确显示可直接复用的商业许可，需下载后核对 README 和条款；
- 本轮没有下载 8.9 GB 数据包。

### 2.3 其他公开项目

CGIAR 生育期项目、FoMo4Wheat 和其他公开仓库主要提供生育期分类、特征提取或需要微调的模型，不提供已经验证的未来 7/15/30 天长势输出。本轮没有把“生育期分类器”误当作“未来长势预测器”。

## 3. 新增接口

### 3.1 模型状态

```text
GET /api/growth-forecast/status
```

当前真实返回：

- `enabled: false`
- `status: unverified`
- `available_horizons: []`
- `model_version: gsp-ai-wgsp-adapter-unverified`
- 官方来源：GSP-AI Release

### 3.2 未来预测入口

```text
POST /api/growth-forecast/predict
```

支持接收：

- JPG/JPEG/PNG 图片；
- 当前生育期；
- 拍摄日期；
- 可选经纬度；
- 可选历史分析编号数组。

当前模型不可用时，接口仍会真实校验图片、日期、位置和历史编号，然后返回：

- 7 天：`prediction: null`；
- 15 天：`prediction: null`；
- 30 天：`prediction: null`；
- `reliability: unavailable`；
- 明确的模型未验证原因和限制。

接口不会读取不同用户的历史图片拼成地块时间序列。现有历史记录没有可靠 `plot_id`、生长季和地块元数据，因此不会用于未来预测。

## 4. 网页改造

长势分析页面新增“未来生长趋势”面板：

- 可填写拍摄日期；
- 可检查当前预测模型状态；
- 显示 7/15/30 天预测状态；
- 模型不可用时显示“预测模型尚未验证”；
- 不显示随机曲线或示例数值；
- 当前长势评价与未来趋势预测保持分离。

已有 V1.1 长势评分、CGIAR 生育期识别、历史记录和全国小麦价格模块未被改写。

## 5. 新增文件与修改文件

新增：

- `backend/app/growth_forecast_service.py`
- `frontend/src/services/forecastApi.js`
- `models/pretrained/gsp_ai/README.md`
- `tests/unit/test_growth_forecast_service.py`
- `reports/future_growth_forecast_v1_delivery.md`

修改：

- `backend/app/main.py`：增加预测状态和预测入口；
- `frontend/src/views/GrowthAnalysis.vue`：增加未来趋势状态面板；

没有修改：

- ExG、HSV、Otsu-ExG、ExG-HSV Fusion；
- V1.1 权重和阈值；
- FoMo4Wheat 权重；
- CGIAR 模型文件；
- EWS、CGIAR 原始数据和历史实验结果；
- 价格模块和经济收益模块。

## 6. 测试结果

- 新增免训练服务测试：**6 passed**；
- Python 单元测试：**146 passed，3 skipped，4 个子测试通过**；
- Python 文件编译检查：通过；
- `npm run build`：通过；
- 当前运行环境的 FastAPI TestClient/真实 Uvicorn 请求此前存在请求阶段无响应问题，因此没有伪造 HTTP 接口通过记录。本轮已完成服务函数级输入校验和状态验证。

## 7. 当前真实能力

| 功能 | 状态 |
|---|---|
| 当前图片长势 V1.1 规则初评 | 已有，可运行 |
| 当前图片七阶段识别 | 已有，模型为 CGIAR 初步实验版本 |
| 未来 7 天真实预测 | 未实现，接口预留 |
| 未来 15 天真实预测 | 未实现，接口预留 |
| 未来 30 天真实预测 | 未实现，接口预留 |
| 天气辅助情景分析 | 未接入 |
| 同一地块历史序列预测 | 未实现，缺少可靠地块元数据 |
| 产量/价格未来预测 | 本轮未接入 |

## 8. 下一步推荐

1. 先下载并审计 WheatPheno 小规模样本，确认 `plot_id、camera_id、日期、阶段标签` 和许可。
2. 独立环境下载 GSP-AI Release，复现官方阶段/花期推理，不修改当前 `.venv`。
3. 先实现“未来阶段/到下一阶段天数”任务，再讨论 7/15/30 天连续表型目标。
4. 只有取得同一小区的真实未来标签后，才允许把预测结果接入网页；在此之前继续显示“预测模型尚未验证”。
