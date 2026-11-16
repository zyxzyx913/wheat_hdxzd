# 小麦表型智能分析 Web 系统改造方案

**检查日期：** 2026-11-13  
**项目路径：** `D:\Desktop\wheat\source-code\wheat-phenotyping`  
**本轮范围：** 只读检查并制定方案；未修改代码、数据、实验结果或依赖，未安装环境、训练模型或下载数据。本轮只新增本报告。

## 1. 当前项目技术结构

项目目前是 Python 3.12 的 `src` 布局研究原型，没有前后端 Web 工程目录。

| 部分 | 现状 |
|---|---|
| Python 包 | `src/wheat_phenotyping/`，包含 data、rgb_preprocessing、leaf_segmentation、phenotyping、evaluation、visualization、simulation、pointcloud_preprocessing、registration、fusion、economics、app 等包 |
| 传统图像分割 | ExG、HSV、Otsu-ExG、ExG-HSV Fusion 四算法均通过注册器统一调用；另有 RF-Color-Texture 随机森林分割器 |
| 桌面入口 | `wheat_phenotyping.app.desktop`，Python Tkinter 窗口，使用 Pillow、NumPy 与已保存的 scikit-learn 模型 |
| 命令行工具 | 数据导入、模型训练、参数校准、分割评价、图片分析、价格基线等脚本位于 `scripts/` |
| 数据 | EWS 原始/处理数据位于 `data/raw/ews/`、`data/processed/ews/`；GWFSS 目录只有此前下载失败状态文件，未有可用图像/掩膜 |
| 实验结果 | EWS 多次实验在 `results/ews/` 下分别保存逐图 CSV、数据集汇总、SVG、算法参数和元数据；已有结果不应被 Web 实验覆盖 |
| 文档与测试 | 根目录有 README、架构说明、方法文档与 `tests/unit/` 测试 |
| 包工程配置 | 有 `requirements.txt` 和 `requirements-dev.txt`；目前没有 `pyproject.toml`、FastAPI 服务目录或 Vue 工程配置 |

### 当前桌面软件入口

启动入口为 `python -m wheat_phenotyping.app.desktop`。界面基于 Tkinter 和 Pillow，支持本地选取单张 PPM/PNG/JPEG/BMP/TIFF 图像，运行 RF-Color-Texture 或 ExG，展示原图、掩膜和叠加图，导出 JSON 与 PGM 掩膜。它是本机桌面程序，不是浏览器服务；四种传统分割算法当前通过 Python 注册器/命令行实验入口运行，未全部接入桌面菜单。

## 2. 可复用的现有代码

Web 后端应以适配层调用现有包，避免复制算法实现或重写已有科研代码。

| Web 能力 | 建议复用模块 | 说明/边界 |
|---|---|---|
| 图像解码与 RGB 规范 | `data/image_io.py`、`rgb_preprocessing/` | 支持常用 RGB 图像格式，读取统一转 `RGBImage`；保留原图尺寸 |
| 四种可解释基线分割 | `leaf_segmentation/registry.py`、`exg.py`、`hsv.py`、`otsu.py`、`fusion.py` | 原注册器和算法原样调用，Web 表单提供可审计参数 |
| EWS 随机森林推理 | `leaf_segmentation/rf_features.py` 与 `results/ews/rf_training/rf_color_texture.joblib` | 标签是活体植被/非活体背景，不是器官识别；限制为隔离的模型加载适配器，不更改训练产物 |
| 可见表型指标 | `phenotyping/growth_grading.py` 的 `extract_visible_growth_features` | 绿色面积、外接框比例、掩膜内颜色等只代表画面可见代理量 |
| 图像/掩膜可视化 | `visualization/segmentation_overlay.py` | 可生成预测与参考标签差异叠加；用户分析可另显示原图/预测掩膜 |
| 科研评价与元数据 | `evaluation/batch.py`、`evaluation/reporting.py`、`evaluation/segmentation.py` | 面向有人工标签的数据集评估；不应把普通上传分析伪装成有 ground truth 的评价 |
| 清单与来源校验 | `data/manifest.py`、`data/split.py` | 保留来源、版本、分组和拆分追踪 |
| 价格实验现状 | `economics/price_forecast.py` | 只提供读入 CSV 的朴素基线与回测，当前无真实价格序列；按既有决定暂缓此模块开发，Web 页面仅展示规划/未启用状态 |

不要让 API endpoint 自己实现阈值算法；建议 `api -> service adapter -> wheat_phenotyping` 调用路径，服务层负责输入校验、计时、错误转换和产物写入。

## 3. 当前开发环境检查

| 环境 | 检查结果 |
|---|---|
| Python | 项目 `.venv` 中 Python 3.12.10 可用 |
| Node.js | 当前命令环境中的 `node` 可运行，版本 24.22.1；路径指向 Codex 自带运行时，不等于已配置完整的常规前端开发环境 |
| npm / npx | `npm` 命令不可用；`npx` 未发现 |
| Vue 3 / Vite | 没有 `package.json`、Vue/Vite 配置、`frontend/` 目录或安装记录，不能认为已安装 |
| FastAPI / Uvicorn | 项目虚拟环境均未安装 |
| PyTorch | 项目虚拟环境未安装，当前没有 PyTorch 推理代码 |
| SQLite | 未发现 `sqlite3` 命令行工具；Python 标准库 `sqlite3` 可用于初期数据库，不需先安装独立数据库服务 |
| Pillow / NumPy / SciPy / scikit-learn | 项目虚拟环境已有，现有图像链路可用 |

前端开始前应在用户可维护的 Windows 开发环境中安装正式 Node.js LTS（含 npm），再创建 Vue 3/Vite 项目。不要使用 Codex 私有运行时路径作为项目部署依赖。FastAPI/Uvicorn 应安装到项目 `.venv`，建议先独立新增 Web 依赖清单或分组，避免无意改变当前研究环境；PyTorch 放到后续模型阶段，根据实际硬件/CPU 与 CUDA 需求再评估。

## 4. 是否适合直接增加 Web 前后端

**适合增量增加，不建议重构现有 Python 包。** 算法、图像类型、评价和文件格式已有模块化接口；Tkinter 入口本身也可以保留，两种入口共享同一 Python 领域代码。建议新增 `backend/` 与 `frontend/`，让后端通过服务层适配现有 `src/wheat_phenotyping/`。

Web 第一阶段只能作为单机/局域网研究原型：支持图片上传、分割预览、可见指标、参数与运行记录。当前没有器官级 GWFSS 标签数据、经农学验证的长势标签、未来生长标签或完整产量数据，不能把“生长状态”“产量预测”“价格预测”页面展示为已经实现并验证的模型。页面应显示真实功能状态、数据来源和适用边界。

### 推荐前后端通信

- Vue 页面通过 JSON REST API 请求 FastAPI，统一加 `/api/v1/` 前缀。
- 图片通过 `multipart/form-data` 上传到后端；附算法名和经过 schema 校验的参数。
- 分割响应返回 `analysis_id`、指标与元数据；图像/掩膜/叠加图用独立只读文件 API 按 ID 获取，不将大图片编码塞进 JSON。
- 小图像的首版可同步计算；后续长任务改为 `POST -> job_id`、`GET /jobs/{job_id}` 轮询状态，必要时引入任务队列。不要在 FastAPI async event loop 中直接运行耗时 CPU 分割。
- CORS 首期只允许本机 Vite 地址；生产/演示时尽量由同一入口反向代理 `/api`，减少跨域和部署配置。
- SQLite 保存用户分析任务、算法名/参数、数据/模型版本、运行时间、状态、结果路径和表型数值。上传原图及 PNG/PGM 结果保存在受控文件目录，数据库只存相对路径与 SHA-256；不把二进制图像直接塞入 SQLite。
- 上传端校验文件扩展名、MIME、实际可解码格式、像素尺寸和大小；生成服务端文件名，不信任用户路径；失败任务写状态和错误，不覆盖原文件。

建议首批 API：

| 方法与路径 | 用途 |
|---|---|
| `GET /api/v1/health` | 服务存活和版本信息 |
| `POST /api/v1/analyses` | 上传一张图片并发起选定算法分析 |
| `GET /api/v1/analyses/{id}` | 查询状态、参数、指标和数据来源说明 |
| `GET /api/v1/analyses/{id}/artifacts/{name}` | 获取原图预览、掩膜或叠加图 |
| `GET /api/v1/analyses` | 分页查看历史记录 |
| `GET /api/v1/reports/{id}` | 获取研究评价报告；仅对有标注实验提供指标 |

## 5. 推荐网页目录结构

先建立精简可启动的框架，按页面需要逐步新增文件，不要一次性铺开空模块。

```text
wheat-phenotyping/
├── src/wheat_phenotyping/            # 现有算法/领域包，保持原样
├── scripts/                          # 现有科研命令行工具，保持原样
├── tests/                             # 现有测试；后续增加 API/服务测试
├── backend/                           # 新增 FastAPI 适配服务
│   ├── app/
│   │   ├── main.py                   # FastAPI 创建、CORS、中间件、路由装配
│   │   ├── api/v1/                   # health、analyses、reports 路由
│   │   ├── schemas/                  # 请求和响应 Pydantic 模型
│   │   ├── services/                 # 复用现有算法的用例适配层
│   │   ├── db/                       # SQLite 初始化、模型/Repository
│   │   └── core/                     # 配置、路径、日志、上传限制
│   └── tests/                        # API、上传、服务与数据库测试
├── frontend/                          # 新增 Vue 3 + Vite
│   ├── index.html
│   ├── src/
│   │   ├── main.js                   # Vue 启动
│   │   ├── App.vue                   # 主应用外壳
│   │   ├── router/                   # 页面路由
│   │   ├── api/                      # FastAPI 请求客户端
│   │   ├── layouts/                  # 全站导航与内容布局
│   │   ├── views/                    # 各业务页面
│   │   ├── components/               # 上传区、图像结果、状态卡片
│   │   └── assets/                   # 样式、图标
│   └── package.json                  # Vue/Vite/组件库依赖与脚本
├── data/                             # 现有数据不移动；Web 上传数据另设本地目录
├── results/                          # 历史 EWS 结果不覆盖；Web 分析另建命名空间
└── reports/web_system_development_plan.md
```

### 页面规划

| 页面 | 第一版建议展示/功能 | 当前限制与后续条件 |
|---|---|---|
| 系统首页 | 项目定位、最近分析记录、数据来源与算法版本、页面功能状态 | 统计卡片必须由真实数据库数据计算，空数据要如实展示 |
| 小麦图像识别 | 图片上传、选择 ExG/HSV/Otsu-ExG/融合/RF、参数设置、原图/掩膜/叠加图、可见面积数值、导出 | 不标注为器官识别；RF 的 EWS 类别是活体植被/背景，且新相机图像泛化未验证 |
| 小麦表型分析 | 展示绿色面积比例、冠层外接框比例、颜色特征等定义/单位/算法来源 | 目前来自单张 2D 图片的代理指标；不等于株高、生物量或真实叶面积 |
| 生长状态分析 | 页面可先做同地块多时间点的历史观测录入/可视化，并显示“预测功能未验证” | 长势等级需要农学标注；未来生长趋势需要同地块连续观测。无数据前不输出分级结论 |
| 产量与价格预测 | 本阶段显示数据需求、模型状态和研究计划，价格部分注明已暂停 | 没有株级产量标签/全国价格历史与关联验证；本页面不发起价格预测，也不沿用基线产生虚假产品结论 |
| 科研分析报告 | 汇总分析输入、算法参数、运行时间、数据来源/版本、图像结果；有人工标注的实验才展示 IoU/F1 等 | 区分用户单图分析与公开数据实验；每份报告可复现且有实验 ID |

## 6. 分阶段开发任务

### 阶段 0：前端/后端环境准备

确认并安装正式 Node.js LTS/npm；在项目虚拟环境加入 FastAPI、Uvicorn、Pydantic（如当前版本链已含则锁定兼容范围）；建立 Vue/Vite 前端清单。记录 Python、Node、npm 版本和安装方式，不安装 PyTorch。

### 阶段 1：最小 Web 框架

创建 `backend/app/main.py` 和 health route；创建 Vue/Vite 外壳、路由与系统首页；配置本地 `/api` 代理及最小 CORS；首页向后端 health API 读取运行状态。验证前后端可分别启动、浏览器能访问首页和 API、错误状态可见。此阶段不接训练或新模型。

### 阶段 2：图像分析垂直切片

建立上传 API schema 与页面，调用现有 `load_rgb_image`、四传统算法 registry 和现有 RF 模型推理适配器；保存 mask/preview artifact，显示参数、方法、执行时间与醒目的 EWS 类别语义说明。先对算法函数/服务层作测试，再做浏览器端到端验证。

### 阶段 3：任务记录与科研可追溯

引入 SQLite schema 与迁移/初始化机制；保存用户上传记录、文件哈希、算法参数、模型/数据版本、状态、指标、错误和 artifact 路径。Web 产物写入独立 `results/web/` 或配置目录，严禁覆盖 `results/ews/`。

### 阶段 4：表型分析与科研报告

展示已实现可见指标和分割结果；加入单位、算法来源、图像尺寸、局限性、下载报告。把含人工真值的 EWS 基准实验与用户上传无标签结果分开。

### 阶段 5：器官分割与长势研究

待 GWFSS 标注数据真实获取并核对 mask 编码后，建立独立四类标签映射和训练/验证/测试分组；模型另存、另评估。长势与未来预测须先有可追踪植株/地块和人工农学标签。PyTorch 只在数据规范与任务定义完成后引入。

### 阶段 6：演示部署与稳定性

建立 Windows 一键启动或容器化方案、静态前端服务、数据库备份/迁移、日志、上传清理和访问控制；用清洁环境复现安装、运行和报告导出。

## 7. 第一阶段网页框架的具体实施步骤

本轮只做方案，实施获确认后建议分小步进行：

1. 在系统 PATH 中核实 Node.js LTS 和 npm；确认版本并用 npm 创建 Vue 3 + Vite 空壳。前端先只添加 `index.html`、`src/main.js`、`src/App.vue`、一个 router、一个 home view、基础 CSS 与 `package.json`。
2. 在现有 `.venv` 安装 FastAPI/Uvicorn/Pydantic，不更改当前 `src/wheat_phenotyping/` 包依赖或算法；新增 `backend/app/main.py`、`backend/app/api/v1/health.py` 和对应测试。
3. 后端提供 `GET /api/v1/health`，返回服务名、API 版本和状态，不暴露本机磁盘路径或敏感配置。
4. Vite 开发服务器将 `/api` 代理到 FastAPI；Vue 首页请求 health 接口，展示“后端在线/不可用”和版本号。
5. 确认项目已有的桌面 Tkinter 启动方式仍可使用；不搬迁、不重命名、不替换既有 EWS 文件和结果。
6. 在干净终端分别启动前后端，验证首页、health API、前端对 API 断开时的提示；保存启动说明和依赖版本。
7. 阶段验收后再开始图像上传垂直切片，不在框架阶段一次创建全部业务页面文件。

## 风险与实施原则

- 同一算法仅保留一份 Python 实现；Web 通过 service adapter 调用，桌面程序继续使用原包。
- 上传图片是不可信输入；限制体积/分辨率并安全生成输出路径，防止路径遍历、压缩炸弹或覆盖研究数据。
- 本地 SQLite 适合单机竞赛演示和低并发科研原型；多人并发/部署到服务器时再评估 PostgreSQL 与对象存储。
- 不将项目内保存的实验指标预填成首页实时成绩；每个结果应能追溯到原实验文件或 Web analysis ID。
- “生长状态”“产量与价格预测”先做状态诚实的研究页面；在标签/数据及样本外验证完成前不产生决策性结论。
