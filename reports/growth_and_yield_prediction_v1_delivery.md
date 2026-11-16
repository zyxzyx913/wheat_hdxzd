# V8.0 初级生长趋势预测与小麦产量估算交付报告

## 最终状态

- `growth_trend_prediction_v1: enabled_with_rule_based_limits`
- `yield_estimation_v1: enabled_with_user_supplied_yield_scenarios`
- `quantitative_biomass_prediction: not_implemented`
- `field_validated_yield_prediction: not_validated`

## 生长趋势预测 V1.0

新增 `backend/app/growth_trend_prediction_service.py` 和接口：

- `GET /api/growth-trend/status`
- `POST /api/growth-trend/predict`

当前输入包括当前生育期、置信度、长势评分、天气状态和天气风险。输出：

- 未来 7 天趋势判断。
- 未来 15 天趋势判断。
- 未来 30 天正常/偏干/偏湿情景。
- 主要影响因素。
- 管理重点。
- 规则版本和限制。

规则边界：

- 天气不可用时返回“暂无法判断”。
- 生育期置信度低于 0.5 时降低可信度并提示复核。
- 当前长势等级不会直接外推为未来等级。
- 不输出未来评分、覆盖率、LAI 或生物量。
- 30 天仅为条件性情景判断。

## 产量估算 V1.0

新增 `backend/app/yield_estimation_service.py` 和接口：

- `POST /api/yield-estimation/calculate`

用户输入面积、低位/正常/高位亩产、销售价格和每亩成本，系统计算：

```text
总产量（吨）= 面积（亩）× 亩产（kg/亩）÷ 1000
销售收入 = 总产量 × 价格（元/吨）
总成本 = 面积 × 每亩成本
预计利润 = 销售收入 − 总成本
亩均利润 = 预计利润 ÷ 面积
```

产量情景完全来自用户输入，没有使用长势等级修正系数，也不冒充田间产量预测模型。

## 前端变化

- `GrowthPrediction.vue` 已变为可操作的趋势规则页面。
- `YieldPrediction.vue` 已变为可操作的产量情景计算页面。
- 生长预测页面支持生育期、评分、置信度、天气状态和风险输入。
- 产量预测页面支持三档亩产和收益对比卡片。

## 测试结果

- 全部 Python 单元测试：**161 passed，3 skipped，4 subtests passed**。
- 新增趋势与产量测试：**3 passed**。
- 单位换算和利润计算测试：通过。
- 非法亩产顺序测试：通过。
- 前端 `npm run build`：**通过**。

## 示例计算

输入：10 亩、正常亩产 450 kg/亩、销售价格 2000 元/吨、每亩成本 500 元。

- 正常总产量：4.5 吨。
- 销售收入：9000 元。
- 总成本：5000 元。
- 预计利润：4000 元。

该示例只验证单位换算和公式，不代表真实田间产量或市场预测结果。

## 限制

1. 生长趋势是规则型趋势判断，不是未来生物量模型。
2. 产量估算依赖用户提供的亩产情景。
3. 没有字段独立、品种独立和年份独立的产量验证。
4. 当前没有自动识别真实亩产或最终产量的模型。

