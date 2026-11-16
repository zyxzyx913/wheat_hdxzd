# 麦视通 UI 风格恢复报告

## 本次修复

- 恢复 `GrowthPrediction.vue` 的深色智慧农业驾驶舱样式。
- 恢复 `YieldPrediction.vue` 的深色智慧农业驾驶舱样式。
- 使用现有 `growth-wheat-field-photo.jpg` 作为页面背景，增加暗化、轻微虚化和深绿遮罩。
- 输入框、数字框和下拉框统一为深绿色磨砂控件，移除浏览器默认白色外观。
- 预测按钮恢复嫩绿色强调样式、悬停反馈和禁用状态。
- 表单改为响应式网格：桌面端分栏，窄屏自动单列。
- 结果区恢复独立玻璃卡片、圆角边框、浅色文字和层次阴影。

## 保留内容

本轮未修改生长趋势规则、产量计算公式、天气接口、历史记录或任何后端逻辑，仅调整两个 Vue 页面样式。

## 验证结果

- `frontend/npm run build`：通过，Vite 成功构建。
- `python -m compileall -q backend/app`：通过。
- Python 单元测试：当前环境未安装 `pytest`，因此未能在本机执行 pytest；未将其标记为通过。
- 浏览器自动化验收：本轮未执行自动化浏览器截图，建议启动开发服务器后分别检查 1920×1080、1366×768 和手机宽度。

## 启动查看

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm run dev -- --host 127.0.0.1
```

浏览器打开 `http://127.0.0.1:5173/`，从“生长预测”和“产量预测”入口查看恢复后的页面。
