# 麦视通单图 ExG 网页闭环验收记录

日期：2026-11-14。根目录：`D:\Desktop\wheat\source-code\wheat-phenotyping`。

## 已交付行为

网页选择单张 JPG/JPEG/PNG → 本地预览 → POST 上传并分析 → 复用现有 ExG → 生成真实二值掩膜、预测叠加图与像素统计 → Vue 对照展示 → 按任务 ID 保存原图与记录。保留深色麦田背景、磨砂玻璃风格、共享布局和路由。

遵循本轮最新要求，只实现 `GET /api/health` 和接受 multipart 文件的 `POST /api/image/analyze`；此前方案的独立 upload/JSON analyze 两步接口未实现。记录采用每任务独立 JSON，本轮没有引入 SQLite、模型训练、其他算法服务或报告中心业务。

## 新增与修改文件

新增后端文件：

- `backend/__init__.py`、`backend/app/__init__.py`：独立服务包。
- `backend/app/config.py`：容量限制、既有 ExG 冻结配置加载与验证集参数一致性校验。
- `backend/app/errors.py`、`backend/app/schemas.py`：中文错误及结构化响应。
- `backend/app/image_service.py`：安全解码、原函数调用、指标和图片/记录保存。
- `backend/app/main.py`：FastAPI、health、analyze、受限图片访问、请求体限额及并发限制。
- `backend/tests/conftest.py`、`backend/tests/test_image_api.py`：独立临时目录的 API 测试。
- `backend/smoke_test.py`：对运行中 HTTP 服务的真实 EWS train 单图一致性检查。
- `backend/requirements.txt`、`backend/requirements-dev.txt`、`backend/constraints-research.txt`、`backend/requirements.lock.txt`：增量依赖、保护约束和实际版本锁。
- `backend/README.md`：启动、接口、存储及复现方法。

新增前端文件：

- `frontend/src/components/ImageAnalysisWorkbench.vue`：独立图片工作台，上传、三图预览、状态和真实指标。
- `frontend/src/services/imageApi.js`：原生 fetch、multipart、响应校验及错误提示。

修改文件：

- `frontend/src/views/ImageRecognition.vue`：该路由改为使用真实分析工作台；旧共享组件保留。
- `frontend/vite.config.js`：开发与预览的 `/api`、`/media` 代理。
- `frontend/src/main.js`：纠正“暂不调用 Python”的旧注释，不改变应用初始化逻辑。
- `.gitignore`：忽略 `var/web/` 上传与分析产物。

生成验收产物：`reports/web_exg_smoke_test.json`、`reports/web_exg_browser_check.json`、`reports/web_exg_browser.png` 以及本报告。前端生产文件由 `npm run build` 更新至 `frontend/dist/`。

## 实际运行结果

| 检查 | 实际结果 |
|---|---|
| Python | 使用项目 `.venv` 的 Python 3.12.10，64 位 |
| FastAPI | 0.162.7，已在 `127.0.0.1:8000` 实际启动，health 返回 200 |
| Uvicorn / multipart | 0.54.0 / 0.0.33，已安装 |
| 依赖一致性 | `python -m pip check` 返回 No broken requirements found；原研究图像包版本保持不变 |
| 新增 API 测试 | 25 passed，0 failed；一条 Starlette/httpx 弃用警告 |
| 原有 Python 单元测试 | collected 67；64 passed、3 skipped，另 4 subtests passed，0 failed |
| 前端构建 | 最终 `npm.cmd run build` 成功，1613 个模块转换；在预览裁切修复和断连提示修复后重新构建 |
| Vue 调接口 | 实际点击网页“开始分析”返回真实结果；通过 5173 代理加载三张 PNG |
| 浏览器检查 | 1280×720 默认视口无横向溢出，三张结果图已完整加载且等比例显示 |

三项原有 skip 是 fusion、phenotyping、registration 的原有占位测试，不表示这些科研功能已完成。原测试中的 RF 推理回归确实执行，但没有训练模型、没有修改模型或 EWS 成绩。

初次在受限执行环境运行 TestClient 未得到完成输出，已中止；随后在正常本机权限下重跑，以上 25 项结果来自该次实际成功运行。初次依赖下载被执行环境网络权限阻挡，正常权限下安装成功。均未通过修改 PATH、替换运行时或绕过测试来声称完成。

## 真实 EWS 单图验证

源样本：`FPWW0220011_RGB1_20180316_100219_6`，EWS 2021-11-30 官方 **train** 划分。

原图：`data/raw/ews/train/images/FPWW0220011_RGB1_20180316_100219_6.png`。

| 项目 | 实际结果 |
|---|---|
| 宽×高 | 350×350 |
| 总有效像素 | 122,500 |
| 植被前景像素 | 34,376 |
| API 植被比例 | 0.28062040816326533 |
| 网页显示 | 28.06% |
| 冒烟分析任务 | `f4b74e7a72e94e299253eb0ec809c3dd` |
| 最后一次浏览器分析任务 | `c07c109abe9c4b778eb101aa8dd9a40c` |
| 最后一次浏览器分析耗时 | 0.1198955001309514 秒，界面四舍五入为 0.120 秒；不作为性能基准承诺 |

对输出 PNG 的前景像素重新计数，与响应及 JSON 记录一致；与同图、同参数直接调用已有推理函数的掩膜逐像素一致。原图显示副本、掩膜、叠加图均通过 HTTP 读取和 Pillow 完整解码，尺寸一致。保存的上传原始字节与源图一致。未读取人工标注计算 IoU 等精度指标。

数据来源沿用本地 EWS 来源记录：论文 DOI `10.3389/fpls.2021.774068`，数据 DOI `10.3929/ethz-b-000512332`，CC BY-SA 4.0。本次是接口冒烟和软件一致性检查，不是新的模型精度实验；未使用测试集调参。

浏览器还实际验证：重新选择同一图片会清空旧掩膜和旧指标；停止自己启动的后端后，点击分析显示“服务没有正确响应”，无成功结果；恢复后端后重试成功。最终界面无错误提示，三张结果图自然尺寸均为 350×350，PNG 已加载。证据见 `web_exg_browser_check.json` 和 `web_exg_browser.png`。

## 保存位置与运行方式

最后一次浏览器结果目录：

`D:\Desktop\wheat\source-code\wheat-phenotyping\var\web\analyses\c07c109abe9c4b778eb101aa8dd9a40c\`

该目录有 `uploaded_original.png`（原始上传字节）、`original.png`（EXIF 方向统一显示副本）、`mask.png`、`overlay.png`、`record.json`。后续任务按新 UUID 独立保存，不覆盖已有结果。返回的 original_url 访问的是显示副本，原始上传字节另行保留。

后端启动：

```powershell
Set-Location -LiteralPath 'D:\Desktop\wheat\source-code\wheat-phenotyping'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端另开 PowerShell：

```powershell
Set-Location -LiteralPath 'D:\Desktop\wheat\source-code\wheat-phenotyping\frontend'
npm.cmd run dev
```

浏览器访问 `http://127.0.0.1:5173/#/image-recognition` → “选择图片” → 选择 JPG/PNG → “开始分析” → 查看三张图及实算指标。当前 5173 已有本项目开发服务器，本轮复用了该进程；不要重复启动或关闭不明进程。8000 后端在断连测试后已恢复。

图片限制：10 MiB、400 万像素、最长边 4096；界面和接口明确拒绝超限，不自动缩图。生产部署与多人服务不属于此次交付。

## 项目保护与功能边界

检查前后对比：`src` 35 个文件、`configs` 5 个文件、`results/ews` 118 个文件的内容 SHA-256 均一致；排除已有 Python 缓存。EWS 原始目录 770 个文件、处理目录 195 个文件的路径/大小/修改时间摘要均一致。本轮没有写入原始数据、标注、实验成绩或经济模块。

目前实际开放的是 ExG 可见植被/背景分割。空前景返回真实比例 0，不等于长势差；比例不是健康分数，也不能从单张照片得到经验证的生长阶段或未来预测。记录尚无前端历史列表、中断恢复或自动清理，失败的 staging 文件不会公开展示。
