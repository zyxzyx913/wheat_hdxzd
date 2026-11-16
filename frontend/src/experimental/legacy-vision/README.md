# 外部 WheatVision 文件隔离审查

本目录只作为外部文件的隔离适配说明，不自动导入 `main.js`、路由或任何生产页面。

本次审查结论：`vision.js`、`style.css`、`analyze-page.js` 暂不复制进入本目录，也不接入麦视通生产页面。

原因：外部代码包含独立的 ExG/Otsu/颜色规则、五级 VGI、未经验证的生育期启发式、固定价格/亩产/收益估算和随机伪点云；`analyze-page.js` 还依赖当前目录不存在的 `common.js`、`pointcloud.js`、`report.js` 及一套未提供的静态 HTML DOM。接入会与现有 V1.1、FoMo 生育期接口、价格数据口径和 Vue 主题发生冲突。

可复用范围仅限于视觉布局参考和交互思路。实际分析必须继续调用现有 FastAPI 接口，不在浏览器端运行外部算法。
