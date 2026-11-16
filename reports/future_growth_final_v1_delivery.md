# 麦视通未来生长趋势与风险分析 V1.0 收尾报告

## 功能冻结状态

- `weather_scenario_v1: completed`
- `quantitative_growth_forecast: not_validated`

本轮冻结天气驱动的风险筛查与情景分析模块，不再把它扩展为未经验证的定量长势预测。

## 已完成功能

1. 用户可上传图片并复用现有当前长势分析和生育期识别。
2. 用户可输入拍摄日期、种植地点、纬度和经度；不要求填写播种日期。
3. 当前生育期可作为初始化参考；低置信度仍提示人工复核。
4. 后端接入 Open-Meteo Forecast API，读取日均温、最高/最低温度、降水、日照和短波辐射。
5. 记录天气来源、时区、经纬度、返回条数和 UTC 获取时间。
6. 未来 7 天和 15 天可以在天气服务可访问时使用真实预报。
7. 未来 30 天如果接口只返回 15 天，会明确标记为不可用，不延长为真实预报。
8. 正常、偏干、偏湿情景均保留假设说明，不输出虚假作物数量指标。
9. 高温、低温、降水偏少、降水偏多只作为未校准筛查标记。

## 真实 HTTP 验证

本机使用河南周口附近坐标（纬度 34.75，经度 114.35）调用 Open-Meteo Forecast API，实际请求失败：

```text
WinError 10013：本机套接字访问被拒绝
```

因此本轮没有把模拟天气冒充真实天气，也没有声称完成真实 HTTP 成功验证。天气服务在浏览器/后端网络恢复后会执行真实请求；失败时返回 `weather.status=unavailable`。

接口设计已记录：

- `weather_type=forecast`
- `source=https://open-meteo.com/en/docs`
- `fetched_at_utc`
- `forecast_days_returned`
- `timezone`

Open-Meteo 官方文档说明其 daily 接口提供温度、降水、日照和短波辐射等变量。[官方文档](https://open-meteo.com/en/docs)

## 7/15/30 天范围

| 期限 | 当前行为 |
|---|---|
| 7 天 | 天气服务可访问且有足够日数据时，返回真实预报筛查 |
| 15 天 | 天气服务可访问且有足够日数据时，返回真实预报筛查 |
| 30 天 | 当前接口最多请求 16 天；不足 30 天时返回不可用，不伪装成长预报 |

本模块没有使用历史气候数据代替未来天气预报。

## 测试结果

- 全部 Python 单元测试：**157 passed，3 skipped，4 subtests passed**。
- 前端 `npm run build`：**通过**。
- 天气筛查测试：通过。
- 经纬度校验、缺失天气、低置信度初始化测试：通过。
- 真实 Open-Meteo HTTP：未通过，原因已记录为本机网络权限阻塞。
- 浏览器完整 HTTP 联调：未宣称通过，因同一网络阻塞存在。

## 输出边界

当前模块不会输出：

- 未来长势 0～100 分。
- 未来植被覆盖率。
- 未来 LAI。
- 未来生物量。
- 经过田间验证的产量或生育期变化。

当前结果只能称为天气风险筛查和情景推演，不是经过中国小麦田间验证的未来长势预测。阈值标记为 `unvalidated_project_screening`，需要未来农学专家和田间数据校准。

## 网页入口

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

浏览器入口：`http://127.0.0.1:5173/#/growth-analysis`

