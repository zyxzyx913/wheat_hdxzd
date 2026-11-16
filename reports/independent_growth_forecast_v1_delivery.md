# 麦视通独立小麦未来生长预测引擎 V1.0 交付报告

## 完成内容

新增 `backend/app/independent_growth_prediction.py`，使用 Python 标准库和现有农事建议规则实现独立的短期趋势推断，不依赖 TensorFlow、pandas、skimage、exifread、openpyxl、GSP-AI、PCSE、WOFOST 或 FoMo4Wheat。

引擎输入当前长势评分/等级、生育期、生育期置信度、拍摄日期、地区、可选经纬度和实际天气行；输出未来7天、15天的趋势、影响因素、天气风险、建议、数据完整度和可信度。当前没有天气时仍可运行基线判断，但会明确标记天气未接入并降低可信度。15天只使用实际获得的天气行，不补造缺失日期。

## API 与网页

- `GET /api/growth-trend/status`：返回独立引擎已启用、版本和支持周期 `[7, 15]`。
- `POST /api/growth-trend/predict`：接收 JSON 当前状态；提供经纬度和拍摄日期时，后端尝试调用 Open-Meteo 获取15天真实天气，再执行引擎。
- `GrowthPrediction.vue`：增加拍摄日期、种植地区、经纬度输入；“检查未来预测”按钮真实调用后端；只显示未来7天和15天卡片。

GSP-AI 等外部模型保留为可选能力，不再阻止独立趋势引擎运行。

## 规则边界

- 当前评分只作为初始状态依据，不复制成未来评分。
- 长势较弱不会被直接解释为未来必然变差。
- 生育期低置信度会降低可信度并提示人工复核。
- 规则不会输出未来覆盖率、LAI、生物量或产量。
- 结果定位为图像表观状态与天气风险驱动的辅助趋势判断，尚未经过独立中国田间验证。

## 实际验证

- 无天气、不同当前评分：45/68分返回“暂无法判断”（低可信度基线），85分返回“基本稳定”，没有直接复制当前分数。
- 真实天气结构样例：7天高温、低降水条件触发高温、降水不足及阶段相关风险；输出风险和农事建议。
- 低置信度生育期：输出低可信度及人工复核依据。
- 相关 Python 单元测试：`6 passed（估算扩展测试；此前独立引擎相关测试13 passed）`。
- `npm run build`：通过。
- `python -m compileall -q backend/app`：通过。

## 最终状态

- `independent_engine: enabled`
- `gsp_ai_dependency: optional`
- `7_day_prediction: enabled`
- `15_day_prediction: enabled`
- `30_day_prediction: removed`
- `quantitative_future_growth_prediction: not_validated`

## 启动

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm run dev -- --host 127.0.0.1
```

后端按项目现有方式启动；页面进入“生长预测”，填写当前生育期、评分、置信度，若需要真实天气再填写拍摄日期、经纬度，点击“检查未来预测”。

