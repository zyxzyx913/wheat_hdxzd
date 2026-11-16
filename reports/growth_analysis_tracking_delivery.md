# 麦视通小麦长势分析真实使用闭环交付报告

交付时间：2026-11-14

## 1. 当前闭环

当前用户流程为：上传 JPG/JPEG/PNG → 后端真实读取 → 运行选择的植被分割算法 → 计算 V1 指标 → 使用 V1.1 规则评分 → 保存原图/掩膜/叠加图/JSON → 前端展示当前植株分析 → 写入历史记录。

统一入口仍为 `POST /api/growth/analyze`，前端没有另起浏览器算法。评分继续使用 `growth-vigor-v1.1-rule`，没有修改 0.45/0.35/0.20 权重或 80/60 阈值。

## 2. 分析记录

每个成功的 V2.0 分析保存：

- 32 位唯一分析编号
- 原始图片、PNG 掩膜、PNG 叠加图
- 上传和完成时间
- 综合分和等级
- 覆盖率、绿色程度、均匀度
- 可靠性、优势、改善建议
- 算法、参数版本、评价规则版本
- V1 指标 JSON、模型阶段增强状态

产物写入 `var/web/analyses/<analysis_id>/`，不会写入 EWS、CGIAR、`results` 或 `models`。

## 3. 历史记录和报告中心

后端接口：

- `GET /api/growth/history`
- `GET /api/growth/history/{analysis_id}`
- `DELETE /api/growth/history/{analysis_id}`

前端变化：

- 长势分析页保留历史摘要和详情查看。
- “我的报告”页面改为真实历史报告中心。
- 可按完成时间倒序查看记录。
- 点击记录查看原图、叠加图、综合分、等级、覆盖率、分项评分、算法和评价规则。
- 删除操作必须经过浏览器确认。
- 删除只清理对应用户上传分析目录和同 ID 的阶段增强目录。

已有旧记录不会被补写虚假 V2.0 分数；缺少 V1.1 字段时显示为空，保持历史真实性。

## 4. 真实计算和异常处理

当前结果字段由 FastAPI 返回，前端只负责展示。低质量图片可能得到“暂不评级”，并显示质量原因；不会强行生成等级。无效图片、格式不匹配、过大文件、损坏图片会返回错误，不生成成功记录。

已有真实 EWS 图片的 V2.0 HTTP 冒烟已通过：接口返回 HTTP 200，生成综合分、等级、原图、掩膜、叠加图和历史记录。已有 CGIAR 图片也用于生育期模型和本地特征测试；CGIAR 生育期标签没有被当成长势真值。

## 5. 科研留存和边界

历史 JSON 保留原始算法参数、评价版本、质量指标和限制说明，可供后续专家标注、评分校准和趋势数据集构建。当前没有修改 V1.1 权重，没有生成专家标签，没有把生育期当成长势等级，也没有实现未来 7/15/30 天预测。

## 6. 测试结果

- 全部 Python 单元测试与 FastAPI 测试：**187 passed，3 skipped，4 warnings**。
- V2.0 分析、历史查询、异常输入和删除接口测试通过。
- 科研标注权限、重复提交保护、一致性统计测试通过。
- 前端 `npm run build`：通过。

## 7. 实际启动

后端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
$env:TEMP="$PWD\.test-tmp"
$env:TMP=$env:TEMP
$env:PYTHONPATH="$PWD\.venv-fomo\Lib\site-packages;$PWD\.external\dinov2;$PWD\src"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm.cmd run dev -- --host 127.0.0.1
```

长势分析：`http://127.0.0.1:5173/#/growth-analysis`

历史报告：`http://127.0.0.1:5173/#/reports`
