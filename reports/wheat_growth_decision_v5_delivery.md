# 麦视通 V5.0 智能生长诊断与未来农事决策交付报告

## 完成状态

- `current_growth_diagnosis: completed`
- `growth_stage_recognition: completed_with_confidence_limits`
- `weather_scenario_analysis: completed_if_http_verified`
- `agricultural_recommendations: completed_with_rule_sources`
- `quantitative_future_growth_prediction: not_validated`

## 本轮完成

1. 新增 `backend/app/agricultural_advice_service.py`，根据当前阶段、图像指标和天气筛查生成非处方农事建议。
2. 将农事建议接入 `/api/growth-forecast/predict` 响应中的 `agricultural_advice` 字段。
3. 长势页面增加智能农事建议区域，展示当前关注、未来 7/15/30 天重点和限制说明。
4. 保留 V1.1、四种分割算法、CGIAR 阶段模型、历史报告和天气情景接口。
5. 不修改图像算法、V1.1 权重、CGIAR、FoMo4Wheat、GSP-AI、WOFOST/PCSE 和价格模块。

## 农事建议规则

建议仅基于：

- V1.1 图像表观指标。
- 当前生育期及其置信度。
- 天气筛查标记。

阶段重点按以下方式表达：分蘖/营养生长期关注苗情和群体均匀性，拔节期关注温度、水分和倒伏风险，孕穗期关注低温和群体生长，抽穗/开花期关注高温和降水风险，灌浆/成熟期关注高温、干旱和灌浆环境。当前建议属于项目规则筛查，尚未完成中国小麦田间和农技专家校准。

不提供肥料、农药或灌溉剂量；缺少土壤检测、施肥记录和当地农技参数时，不生成处方性建议。

## 天气接口验证

Open-Meteo 真实 HTTP 请求已实际尝试，但当前 Windows 运行环境返回 `WinError 10013`，套接字访问被拒绝。因此本轮没有把模拟天气或静态天气当作真实结果。天气服务失败时返回 `weather.status=unavailable`，网页显示明确错误状态。

天气字段设计包括：日均温、最高温、最低温、降水、日照、短波辐射、时区、来源和 UTC 获取时间。[Open-Meteo 官方文档](https://open-meteo.com/en/docs)

## 预测范围

- 7 天：天气服务可访问时，使用真实返回的逐日预报进行风险筛查。
- 15 天：天气服务可访问且返回足够日期时进行风险筛查。
- 30 天：如果接口只返回 15/16 天，剩余日期明确不可用，不延长短期预报。
- 未来长势分数、覆盖率、LAI、生物量和产量预测：未验证，不输出。

## 测试结果

- 全部 Python 单元测试：**158 passed，3 skipped，4 subtests passed**。
- 农事建议规则测试：通过。
- 低置信度阶段测试：通过。
- 天气失败状态测试：通过。
- 前端 `npm run build`：**通过**。
- 真实 Open-Meteo HTTP：失败，原因是本机网络权限 `WinError 10013`。
- 浏览器完整 HTTP 联调：未宣称通过，受同一网络限制影响。

## 网页入口

```text
http://127.0.0.1:5173/#/growth-analysis
```

启动后端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

启动前端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm run dev
```

## 最终限制

当前系统可以完成当前小麦图像诊断、阶段识别、天气风险筛查和规则型农事建议；它仍不是经过中国田间数据验证的未来生长定量预测系统。GSP-AI、WOFOST/PCSE 和未来长势模型继续保持未验证状态。

