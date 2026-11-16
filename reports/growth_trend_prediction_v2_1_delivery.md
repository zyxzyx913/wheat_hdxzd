# 麦视通未来生长预测 V2.1 交付报告

## 实际改动

- `backend/app/growth_trend_prediction_service.py`
  - 规则型趋势输出仅保留 `7` 和 `15` 两个周期。
  - 删除30天趋势与正常/偏干/偏湿情景输出。
  - 版本标记更新为 `growth-trend-v2.1-rule`。
  - 保留天气不可用时的有限状态判断，并明确提示无天气依据。
  - 保留生育期低置信度复核提示和不输出定量未来指标的限制。
- `backend/app/growth_forecast_service.py`
  - 现有未来预测适配层的支持周期收敛为7天、15天，避免继续暴露30天入口。
  - 天气风险接口和输入校验逻辑保留。
- `backend/app/main.py`
  - 生长趋势状态版本更新为 V2.1。
- `frontend/src/views/GrowthPrediction.vue`
  - 结果卡片仅渲染未来7天、15天。
  - 移除30天卡片、情景文字和相关展示。
  - 页面标题标记为 GROWTH TREND V2.1，双卡片布局保留深色驾驶舱样式。
- `tests/unit/test_growth_yield_v1.py`
  - 删除30天情景断言，增加只返回7/15周期和V2.1版本断言。

## 功能状态

- `7_day_growth_trend`: enabled
- `15_day_growth_trend`: enabled_with_weather_coverage_limits
- `30_day_growth_trend`: removed

7天和15天仍然是规则型趋势判断，不生成未来评分、覆盖率、LAI、生物量或产量。天气不可用时返回“暂无法判断”，并保留当前状态与限制说明。15天结果受实际天气接口返回天数限制，不会补造缺失天气。

## 测试结果

- 相关 Python 测试：`10 passed`。
- 前端 `npm run build`：通过。
- `python -m compileall -q backend/app`：通过。
- 全量 Python 测试：本次改动相关测试通过；全量执行在既有 FoMo4Wheat 测试处因环境缺少 `torchvision` 失败，未将该失败归因于本次V2.1修改。

## 启动方式

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:5173/`，进入“生长预测”页面即可使用7天和15天趋势判断。
