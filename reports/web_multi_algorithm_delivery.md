# 麦视通四种传统算法网页接入交付报告

日期：2026-11-14。项目根目录：`D:\Desktop\wheat\source-code\wheat-phenotyping`。以下文件路径相对此目录。

## 1. 已完成能力

网页同一张 JPG/JPEG/PNG 可分别运行 ExG、HSV、Otsu-ExG、ExG-HSV Fusion，默认仍为 ExG。保留原图、二值掩膜、叠加图、下载入口、真实植被占比、像素数和计时。新增四方案选择、四宫格结果、掩膜/叠加切换、面积比例条形对照；深色农业图片背景与玻璃面板保留。

实际算法仍是原来的 `src/wheat_phenotyping/app/inference.py` 中 `predict_visible_mask`，再调用原 `DEFAULT_REGISTRY`。未复制或修改任何分割算法，未训练模型。结果范围仍是活体植被/背景二分类，不能描述成器官识别、准确率或长势预测。

## 2. 新增与修改文件

### 新增代码

| 文件 | 作用 |
|---|---|
| `backend/tests/test_multi_algorithm.py` | 四算法输出、真实像素统计、冻结参数、小数参数保真、错误输入、失败隔离和单项配置不可用回归 |
| `backend/smoke_multi_algorithm.py` | 同一真实 EWS train 图像的四算法 HTTP 冒烟、原函数掩膜一致性与结果文件验证 |
| `frontend/src/components/AlgorithmComparison.vue` | 四宫格、真实状态/读数、图像类型切换和面积比例条形对照 |

### 修改文件

| 文件 | 变化 |
|---|---|
| `backend/app/config.py` | 新增四算法允许列表与逐算法冻结参数加载；保留 `load_exg_profile` 兼容入口 |
| `backend/app/schemas.py` | 四算法统一响应，允许 HSV 小数参数；新增输入 SHA-256 和逐算法元数据 |
| `backend/app/main.py` | 接收可选算法表单字段，默认 ExG；逐算法可用状态，错误隔离，保留上传限额和图片访问约束 |
| `backend/app/image_service.py` | 将选择的算法交给原推理函数，逐算法记录与保存真实结果、错误、参数、Otsu 自动阈值等元数据 |
| `frontend/src/services/imageApi.js` | 四算法选项、算法表单参数及响应校验，核对返回算法、像素计数、URL 与任务 ID |
| `frontend/src/components/ImageAnalysisWorkbench.vue` | 同图按算法独立缓存，选择/单项执行/四方案顺序执行、逐项状态、指标联动、同图摘要与尺寸校验 |
| `backend/README.md` | 更新当前接口、网页操作与多算法复现方法 |

### 新增验收证据

- `reports/web_multi_algorithm_smoke.json`：四算法真实 HTTP 返回值与一致性检查。
- `reports/web_multi_algorithm_tests.xml`：全部 Python 测试的 JUnit 记录。
- `reports/web_multi_algorithm_browser.json`：浏览器四种方案切换、图片加载和单项重跑隔离证据。
- `reports/web_multi_algorithm_browser.png`：真实网页全页截图。
- `reports/web_multi_algorithm_protection.json`：开发前后保护目录摘要核对。
- `reports/web_multi_algorithm_delivery.md`：本报告。

`npm run build` 更新 `frontend/dist/` 构建产物。没有修改路由、共享 App 布局、其他页面、Python 领域算法、EWS 文件或已有成绩。

## 3. 接口与数据真实性

`POST /api/image/analyze` 使用 multipart/form-data：

| 字段 | 含义 |
|---|---|
| `file` | 必填，一张 JPG/JPEG/PNG，原限额保留 |
| `algorithm` | 可选完整注册名：ExG、HSV、Otsu-ExG、ExG-HSV Fusion；省略时为 ExG |

显式空值、未知算法（包括 RF）、重复算法字段、额外阈值和多文件请求均拒绝，返回明确中文错误。不会偷偷回退到其他算法冒充所选结果。

每个请求只执行所选算法，通过统一结构返回实际算法名、参数、profile、任务 ID、三张图片 URL、输入摘要、宽高、像素数、面积比例、分析和推理耗时。Otsu 逐图记录 `computed_exg_threshold`，Fusion 记录 `fusion_rule`。

四算法配置只读来自 `configs/segmentation/desktop_frozen_defaults.json`，逐项对照 `results/ews/validation_calibration/selected_parameters.json`。没有新参数搜索，没有测试集调参。

四方案按钮使用同一浏览器 File，顺序向原分析 API 提交四次；每次独立执行、计时和保存。前端用 `input_sha256` 和宽高检查输入一致性，再按算法存储本图结果。不存在或失败的结果显示占位/错误，不显示示例数值；换图清空四组旧结果。单独重跑只替换对应结果。单项算法执行失败不阻止后续请求；单项配置失效不禁用其他可用算法。

植被占比严格为 `vegetation_pixel_count / total_valid_pixels`，不是 IoU、F1 或识别准确率。无人工真值的网页请求没有计算这些精度指标。图中条长来自真实面积比例，不用于评选“最准确算法”。

## 4. 同一真实 EWS 图像检查

样本：`FPWW0220011_RGB1_20180316_100219_6`，EWS `2021-11-30` 官方 **train** 划分。原始路径：

`data/raw/ews/train/images/FPWW0220011_RGB1_20180316_100219_6.png`

该图为 350×350，总有效像素 122,500。四次 HTTP 请求的输入摘要及方向统一后的 RGB 字节均一致。

以下数值来自本轮真实 HTTP 冒烟报告，耗时为该次实际运行值，并非稳定性能承诺：

| 算法 | 前景像素数 | 画面植被占比 | 分析耗时（秒，四舍五入） |
|---|---:|---:|---:|
| ExG | 34,376 | 28.0620% | 0.1110 |
| HSV | 33,140 | 27.0531% | 0.1746 |
| Otsu-ExG | 26,576 | 21.6947% | 0.1143 |
| ExG-HSV Fusion | 33,140 | 27.0531% | 0.2115 |

检查结果：

- 四种算法均 HTTP 200；12 张返回图片（每种三张）均能下载并完整解码，尺寸保持 350×350。
- 四份 PNG 掩膜仅有 0/255，前景重新计数与 API、JSON 记录的像素数/比例一致。
- 每种算法的掩膜与相同图像、相同参数直接调用已有 `predict_visible_mask` 的输出逐像素一致。
- 四组原始上传字节保持不变，各自 UUID 和保存目录独立。
- Otsu-ExG 本图实算 ExG 阈值为 **29**，不是人工填入阈值。
- 本图 HSV 与 Fusion 得到相同像素计数，这是真实输出，不据此推断算法在其他图片上等效。

**这是接口与软件一致性冒烟，不是新的模型精度实验。** 没有使用人工掩膜计算指标，没有改动原 EWS 验证/测试成绩。来源沿用原数据记录：论文 DOI `10.3389/fpls.2021.774068`；数据 DOI `10.3929/ethz-b-000512332`；CC BY-SA 4.0。

## 5. 测试与浏览器验收

使用项目 `.venv\Scripts\python.exe`（Python 3.12.10，64 位），实际执行：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& .\.venv\Scripts\python.exe -m pytest tests backend/tests -q -p no:cacheprovider --basetemp=.test-tmp/multi-full-suite --junitxml=reports/web_multi_algorithm_tests.xml
```

最终结果：**100 passed、3 skipped、0 failed，另 4 subtests passed**。其中原有研究测试为 64 通过、3 跳过；后端为 36 通过（原 25 项回归 + 本轮 11 项）。三项跳过是原融合、表型、配准的占位测试，不代表这些功能完成。另有一条 Starlette/httpx 已有弃用警告，不影响本次通过。

开发中曾发现显式空 algorithm 被框架当成默认 ExG，已经增加原始表单校验并重跑通过；没有通过更改预期来掩盖此问题。新增测试中的程序生成小图仅作为软件夹具，不作为真实小麦成绩。

`npm.cmd run build` 实际成功，1615 个模块转换。未新增前端运行依赖。当前后端健康检查为版本 0.2.0、状态 ok，四算法可用；5173 的代理也返回同样健康状态。

浏览器使用真实 EWS 图片实际验证了：

1. “四方案对比”顺序执行并呈现四组成功结果。
2. 逐项切换 ExG、HSV、Otsu-ExG、Fusion，主预览 URL 与侧栏读数分别关联各自任务，不混用结果。
3. 四宫格从叠加切换到掩膜，四张掩膜均已加载；点击卡片能联动当前方案。
4. 单独重跑 Otsu-ExG 只更新其 UUID，其他三组任务 ID 与图片保持不变。
5. 最终四宫格读数与磁盘掩膜再次核对一致，输入摘要相同，界面无错误提示；默认 1280×720 视口没有横向溢出。

浏览器另有一次独立重跑，耗时与表中 HTTP 冒烟值有所不同，均按各自真实结果显示，未人为统一耗时。具体浏览器任务、读数和截图见配套 JSON/PNG。

## 6. 网页操作与启动

当前服务已经启动，可访问：

[http://127.0.0.1:5173/#/image-recognition](http://127.0.0.1:5173/#/image-recognition)

操作：

1. 点击“选择图片”，选择一张 JPG/JPEG/PNG。
2. 单方案：点击左侧方案名，再点击“开始分析”。
3. 全部对比：点击“四方案对比”，等待各项依次完成。
4. 左侧方案或四宫格卡片可切换主预览和指标；“叠加 / 掩膜”切换四宫格图像类型。
5. 点击下载图标保存当前图片；“科研参数与记录”查看真实参数和 Otsu 实算阈值。
6. “重新选择图片”开始新图，旧图磁盘记录保留，界面旧结果清空。

重新启动时，两个独立 PowerShell 窗口分别运行：

```powershell
Set-Location -LiteralPath 'D:\Desktop\wheat\source-code\wheat-phenotyping'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
Set-Location -LiteralPath 'D:\Desktop\wheat\source-code\wheat-phenotyping\frontend'
npm.cmd run dev
```

已有服务运行时不要重复启动或终止未知进程。复现本轮 HTTP 检查：

```powershell
& .\.venv\Scripts\python.exe -m backend.smoke_multi_algorithm
```

每组产物仍保存于 `var/web/analyses/<task_id>/`，包含 `uploaded_original.png/jpg`、`original.png`、`mask.png`、`overlay.png` 和 `record.json`；具体目录在冒烟 JSON 内逐项记录。上传限额仍为 10 MiB、400 万像素、最长边 4096，不静默缩图。

## 7. 保护核对与边界

检查前后 `src`（35 文件）、`configs`（5 文件）、`results/ews`（118 文件）的内容 SHA-256 一致，排除 Python 缓存。EWS raw（770 文件）与 processed（195 文件）的路径、大小和修改时间摘要一致。详细值在 `web_multi_algorithm_protection.json`。

本轮没有修改算法原理、EWS 原图/标注/既有成绩、RF 模型、经济模块或路由，没有重新训练或测试集调参。旧分析目录和单算法记录继续保留。仍是本机研究原型，不包含器官识别、农学诊断、长势预测、多用户权限或全套报告中心业务。
