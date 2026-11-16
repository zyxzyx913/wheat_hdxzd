# 麦视通单张图片多算法分割服务

本服务完成网页 JPG/JPEG/PNG 上传、四种传统算法推理、原图/掩膜/叠加图展示和真实可见植被比例计算。支持 ExG（默认）、HSV、Otsu-ExG、ExG-HSV Fusion，均通过 `wheat_phenotyping.app.inference.predict_visible_mask` 调用，不复制分割实现；参数只读复用原验证集冻结值。

## 启动

在两个独立 PowerShell 窗口运行，两个窗口均需保持打开。

后端：

```powershell
Set-Location -LiteralPath 'D:\Desktop\wheat\source-code\wheat-phenotyping'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
Set-Location -LiteralPath 'D:\Desktop\wheat\source-code\wheat-phenotyping\frontend'
npm.cmd run dev
```

访问 [图像识别工作台](http://127.0.0.1:5173/#/image-recognition)。选择图片，确认预览，选择方案并点击“开始分析”；或点击“四方案对比”顺序运行全部四种算法。完成后点击方案或四宫格卡片切换结果，用“叠加 / 掩膜”切换对比图类型。每种方案各自显示像素计数、真实植被占比和耗时。“重新选择图片”会清空该图的全部旧结果。面积比例的高低不代表分割准确率。

若提示 5173 或 8000 被占用，请先检查是否已有本项目服务在运行；已有服务正常时直接复用，不重复启动或强行结束未知进程。`Ctrl+C` 停止所在窗口的服务。

[健康检查](http://127.0.0.1:8000/api/health)，[接口文档](http://127.0.0.1:8000/docs)。仅监听本机，没有账号权限隔离，不作为公开网络部署方案。`npm run build` 的静态文件部署需要另外配置 `/api` 和 `/media` 同源转发；开发和 Vite preview 已有这两项代理。

## 环境

使用项目 `.venv` 的 Python 3.12.10。此次已经安装依赖并通过 `pip check`；根研究依赖未修改。重建同一 Windows 环境时，在项目根运行：

```powershell
& .\.venv\Scripts\python.exe -m pip install -r backend/requirements.lock.txt
```

`requirements.txt` 为运行依赖声明，`requirements-dev.txt` 含 API 测试依赖，`constraints-research.txt` 保护既有图像研究包版本。锁文件固定此次实际验证的依赖闭包，包含测试工具。

## 接口

- `GET /api/health`：真实服务状态、四算法名称、实际可用算法与容量限制；单项配置失效为 degraded，所有配置或存储不可用返回 503。
- `POST /api/image/analyze`：multipart/form-data，必填单张图片字段 `file`，可选 `algorithm`（省略默认 ExG）。只接受四种完整注册名；空值、未知算法、重复字段及阈值/模型路径等额外字段均拒绝。
- `GET /media/{task_id}/{asset}`：按允许列表提供 `original.png`、`mask.png`、`overlay.png`，不公开目录、原始上传字节或记录文件。

POST 成功返回任务 ID、实际算法、三张图 URL、宽高、`vegetation_pixel_count`、`total_valid_pixels`、`vegetation_ratio`、`analysis_time_seconds`、`segmentation_time_seconds`、实际参数与 profile，另有 `input_sha256` 与 `algorithm_metadata`。Otsu 的 metadata 含 `computed_exg_threshold`，融合算法含 `fusion_rule`。前景为 255、背景为 0，占比为实算前景像素数除以全图像素数，API 数值为 0–1，界面显示百分比。

前端只选择一次 File，四方案按钮将同一原始字节按算法顺序提交四次，每次独立执行和计时，保存不同 UUID。前端核对输入摘要及结果尺寸才纳入对比；单项失败明确标记，不填造结果，其余方案继续执行。切换已完成方案读取本图缓存；单独重跑只替换该方案，换图清空全部缓存。

工程限额为单张 10 MiB、最多 4,000,000 像素、最长边 4096 像素。校验后缀、实际编码、完整性和解码尺寸；拒绝空文件、损坏图片和动画，不自动缩图。后端单个推理槽繁忙时返回明确错误。

原始字节完整保留；方向校正后的 RGB 副本供算法和界面共用，透明 PNG 以白底合成并记入记录。`original_url` 指这个方向统一的无损 PNG 显示副本。所有处理像素都计入总有效像素数；原图、掩膜、叠加图采用同一坐标系。

## 结果保存

每个任务使用独立 UUID，目录为：

```text
var/web/analyses/<task_id>/
├─ uploaded_original.jpg 或 uploaded_original.png  # 上传原始字节
├─ original.png                                  # 方向统一的显示/推理副本
├─ mask.png                                      # 真实预测二值掩膜
├─ overlay.png                                   # 绿色预测区域叠加
└─ record.json                                   # 参数、来源摘要、时间、结果、处理说明
```

产物在 `var/web/staging/` 完整写好后，整体提交到分析目录。读图/算法/写图失败会记录到 `var/web/failures/`；中断或失败可能留下 staging 目录，但不会提供半成品 URL。尚未实现自动清理、历史记录列表或中断恢复，勿把磁盘记录保存理解为“我的报告”页面已经接通。

记录包含上传 SHA-256、冻结配置摘要与来源、分析时间、任务状态、处理策略。网页上传来源记录为 `user_upload`，不自动加入任何训练或测试清单。EWS 冒烟样本的公开数据来源与原划分另在验收报告中标明。

`analysis_time_seconds` 包括解码、分割、特征提取、图片保存，结束点在最终 JSON 记录提交前；不包括上传网络时间。`segmentation_time_seconds` 只包围已有推理函数调用。性能数值随机器和图片变化，不是准确率。

## 测试与复现

从项目根设置 PYTHONPATH 后运行：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& .\.venv\Scripts\python.exe -m pytest backend/tests -v
& .\.venv\Scripts\python.exe -m pytest tests/unit -v
# 后端运行时，使用原 EWS train 样本核验 HTTP 和结果文件；不计算精度。
& .\.venv\Scripts\python.exe -m backend.smoke_test
# 同一 EWS train 图片的四算法检查，不更新旧 EWS 实验成绩。
& .\.venv\Scripts\python.exe -m backend.smoke_multi_algorithm
```

冒烟默认写 `reports/web_exg_smoke_test.json`；`--report <路径>` 可另存一份记录。测试使用临时目录；单元测试中的程序生成小图只是软件夹具，不能当作真实小麦实验结果。

当前多算法验收详见 `reports/web_multi_algorithm_delivery.md`；上一轮 ExG 闭环记录仍保留在 `reports/web_exg_integration_delivery.md`。四算法冒烟默认写 `reports/web_multi_algorithm_smoke.json`。当前 TestClient 使用 httpx 会产生一条 Starlette 弃用警告，不影响本次测试通过；后续升级测试依赖时应一并处理，不在此轮扩展范围。

功能范围是可见植被/背景分割。没有人工真值的上传不输出 IoU、准确率；植被比例不等于器官识别、生物量或经农学验证的长势诊断。
