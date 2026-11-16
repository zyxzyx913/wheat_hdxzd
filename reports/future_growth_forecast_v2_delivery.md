# 未来小麦生长预测 V2.0 交付报告

## 1. 最终结论

本轮完成了 GSP-AI/WGSP 官方资源核查、免训练适配接口、天气输入字段预留、历史记录安全校验和网页展示，但**没有成功获取或运行 GSP-AI 官方权重**，因此没有把模型结果接入生产预测，也没有生成未来 7/15/30 天的虚假阶段或开花日期。

官方 Release 确实提供：

- `GSP-AI_model.zip`，约 9.4 MB；
- `iPython.zip` 推理流程；
- CN-UK-US 环境因素表；
- WGSP-CN 与 WGSP-Smartphone 分卷数据；
- 模型目标为关键生育期识别和开花期预测。[官方 Release V1.1](https://github.com/The-Zhou-Lab/GSP-AI/releases)

官方说明还指出，测试数据、人工花期数据和模型资源为学术使用；软件和算法采用 MIT 许可。当前项目不会把该资源直接包装成商业化预测能力。[官方仓库](https://github.com/The-Zhou-Lab/GSP-AI/blob/main/README.md)

## 2. 下载和运行结果

### 2.1 下载

本轮尝试通过官方 Release 直接获取：

```text
https://github.com/The-Zhou-Lab/GSP-AI/releases/download/V1.1/GSP-AI_model.zip
```

当前 Windows 沙箱的网络请求被本地代理端口拒绝，下载未完成。`models/pretrained/gsp_ai/` 中没有留下不完整压缩包，只有来源说明 README。没有绕过 GitHub 访问权限，也没有使用替代随机权重。

### 2.2 官方示例推理

由于模型包和 iPython 文件没有成功下载，本轮无法诚实声称完成官方示例推理、真实 GSP-AI 推理或官方输出字段复现。现有 CGIAR SVM 和 FoMo4Wheat 推理保持不变，不能替代 GSP-AI。

## 3. 模型能力边界

论文和官方仓库描述 GSP-AI 使用图像与气象因素预测关键生育期，并预测开花日期；公开论文报告了 70,410 张标注冠层图像和中国/英美试验数据。[论文页面](https://spj.science.org/doi/10.34133/plantphenomics.0255)

因此，本项目只会在模型包成功加载并复现官方示例后接入：

- 当前/下一关键生育阶段；
- 预计开花日期；
- 距离预计开花的天数；
- 模型原始置信度或不确定性（如果官方输出提供）。

以下功能当前不能声称已实现：

- 未来 7 天长势评分；
- 未来 15 天长势评分；
- 未来 30 天长势评分；
- 未来 7/15/30 天覆盖率、绿色程度或株高数值；
- 单张手机照片直接预测未来长势曲线。

开花日期预测不能替代长势评分，网页会将两者分开显示。

## 4. 新增 API

### 4.1 状态接口

```text
GET /api/growth-forecast/status
```

当前返回的关键状态：

```json
{
  "enabled": false,
  "status": "unverified",
  "available_horizons": [],
  "model_version": "gsp-ai-wgsp-adapter-unverified"
}
```

### 4.2 预测接口

```text
POST /api/growth-forecast/predict
```

支持输入：

- RGB 图片；
- 当前生育期；
- 拍摄日期；
- 可选纬度和经度；
- 可选历史分析编号 JSON 数组。

当前模型未启用时，返回结构化空结果：

- `current_stage` 可回显用户提供的阶段；
- `next_stage: null`；
- `predicted_flowering_date: null`；
- `days_to_flowering: null`；
- 7/15/30 天的 `prediction: null`；
- `weather.status: not_used`；
- `reliability: unavailable`。

接口会校验图片格式、图片内容、日期格式、经纬度范围和历史编号格式。

## 5. 历史数据和天气处理

现有网页历史记录没有可靠的 `plot_id`、生长季和地块元数据，不能把不同用户上传的图片拼成同一地块时间序列。当前接口只接受历史编号作为可追溯输入，不自动拼接记录。

天气字段已预留，但本轮没有接入在线天气服务，也不会使用当前电脑所在地代替小麦地块位置。只有用户提供地块位置且模型明确需要时，才会接入有来源、有日期的真实天气数据。

## 6. 网页接入

长势分析页面的“未来生长趋势”区域已更新：

- 显示模型状态；
- 支持填写拍摄日期；
- 支持检查未来预测接口；
- 7/15/30 天没有可用模型时显示“预测模型尚未验证”；
- 不绘制随机曲线；
- 不让未来预测改变 V1.1 当前长势评分。

## 7. 文件变更

新增：

- `reports/future_growth_forecast_v2_delivery.md`
- `models/pretrained/gsp_ai/README.md`
- `backend/app/growth_forecast_service.py`
- `frontend/src/services/forecastApi.js`
- `tests/unit/test_growth_forecast_service.py`

修改：

- `backend/app/main.py`
- `frontend/src/views/GrowthAnalysis.vue`

保留未修改：

- V1.1 权重和阈值；
- 四种分割算法；
- FoMo4Wheat 权重；
- CGIAR 七阶段 SVM；
- 历史分析记录；
- 全国小麦价格模块；
- EWS、CGIAR 原始数据和历史成绩。

## 8. 测试结果

- 新增免训练服务测试：**6 passed**；
- Python 单元测试：**146 passed，3 skipped，4 个子测试通过**；
- 后端文件编译检查：通过；
- 前端 `npm run build`：通过；
- 新接口路由注册检查：通过；
- 真实 GSP-AI 官方示例推理：**未完成**，原因是官方模型包无法下载；
- FastAPI HTTP 请求：当前运行环境此前存在 TestClient/Uvicorn 请求阶段无响应问题，未将未完成请求伪造为通过。

## 9. 启动方式

后端仍使用项目现有方式启动，并确保 `PYTHONPATH` 包含项目 `src`：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
$env:PYTHONPATH="$PWD\src;$PWD"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm run dev
```

浏览器访问：`http://127.0.0.1:5173`。

## 10. 下一步

1. 在本机普通 PowerShell 或浏览器中从官方 Release 下载 `GSP-AI_model.zip` 和 `iPython.zip`，记录 SHA256。
2. 建立独立 GSP-AI 环境，核对官方 TensorFlow/依赖版本，运行官方示例。
3. 用一张真实 CGIAR 或中国公开 RGB 图片复现阶段/开花输出。
4. 确认模型的气象字段、时间语义和输出置信度后，再实现 `predicted_flowering_date` 和阶段时间线。
5. 只有取得真实同一地块时间序列后，才考虑 7/15/30 天阶段变化预测；没有验证数据前继续显示“预测模型尚未验证”。

## 11. 本次实际模型包核验补充

本轮已在项目目录发现并核验手动下载文件：

- `models/pretrained/gsp_ai/GSP-AI_model.zip`
- `models/pretrained/gsp_ai/iPython.zip`
- `models/pretrained/gsp_ai/Data_S1_Environmental.factors.CN-UK-US.2018-2021.xlsx`

模型 ZIP：9,861,735 字节，MD5 `2174826623A55CE0B7CD27FE30445F6C`，SHA256 `42D4C03D53C715CC12249EAA10F2EC3ED60D42D750E1FB9B3ABFD52EF793D95B`。ZIP 共 6 个成员，包含 `saved_model.pb`、两个 TensorFlow 变量分片、索引文件和 `matrics.txt`，`ZipFile.testzip()` 返回无损坏成员。

推理 ZIP：6,170 字节，包含 `GSP_AI_model.ipynb`、图像采样和数据增强 Notebook，压缩校验通过。官方 Notebook 的实际推理调用为：

```text
model_loaded.predict([one_info, one_img])
```

其中 `one_img` 按官方代码缩放为 `224×224×3`，`one_info` 从拍摄日期匹配四个归一化环境字段 `nor_rain` 到 `nor_solar`；输出是六类阶段分数和一个 `FS` 数值。官方阶段名称是 Tillering、Jointing、B$H、Flowering、Filling、Ripening。该 `FS` 的单位和具体语义需要官方示例运行后再确认，当前不能擅自转换成日期。

独立 `.venv-gsp-ai` 已创建，但该环境未能初始化 pip；使用主环境的 pip 代理安装也因当前网络权限失败。当前运行时实际缺少：`tensorflow、pandas、scikit-image、exifread、openpyxl`。因此本轮没有成功加载 SavedModel，也没有完成官方示例或真实小麦图片推理。可复核详情见 `results/gsp_ai_inspection.json`。

接口状态现在会区分“官方 ZIP 已存在”和“运行依赖未满足”，仍返回 `enabled: false`、`available_horizons: []`，不会把模型包存在误报成模型可用。
