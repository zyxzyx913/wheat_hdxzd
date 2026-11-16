# 外部 vision.js / style.css / analyze-page.js 安全集成审查

审查时间：2026-11-14

## 1. 文件和项目保护

三个外部文件均存在于用户提供的微信文件目录：

| 文件 | 大小 | SHA-256 | 处理 |
|---|---:|---|---|
| vision.js | 22,982 bytes | `9E19C212FA71E790A872125702B0C1F996ADC861C1EECDC90F5D6D587E90D417` | 仅读审查 |
| style.css | 35,712 bytes | `FBCCBA0B1EF3A8095E8EEEC5238700ABF2B23BE02C06C8D61F3E484B878D7643` | 仅读审查 |
| analyze-page.js | 14,322 bytes | `216ACB1914444B6AB9D78F356F4CA5AD87708951F1923E23F17DE65477C1AC10` | 仅读审查 |

当前项目没有 Git 元数据，`git status` 返回“not a git repository”。因此已将可能涉及的现有前端文件复制到：

`var/audit_backup/external_legacy_20261114/`

本轮没有覆盖 `src`、`data`、`results`、`models`，没有修改 V1.1 权重和阈值，没有修改四种分割算法、FoMo 权重、价格研究代码或历史实验结果。

## 2. vision.js 审查

### 可识别的功能

- `analyzeCanopy`：浏览器端 ROI、颜色校正、ExG、Otsu 阈值、黄化规则、8×8 网格、纹理、图像质量和 VGI。
- `inferStage`：基于覆盖率、黄化率、纹理和 ExG 的启发式生育期判断。
- `renderMask`：把外部掩膜渲染为 RGBA 图层。
- `buildPseudoCloud`：从二维掩膜和亮度生成“单目伪点云”。
- `estimatePrice`：由 VGI、生育期和固定价格参数推导亩产、单价和收益区间。

### 不可复用部分

1. 它重新实现了 ExG/Otsu/HSV 相关颜色处理，不能替代现有四种注册算法，也没有调用 `/api/image/analyze` 或 `/api/growth/analyze`。
2. VGI 使用五级 `Ⅰ～Ⅴ` 和 85/72/58/44 阈值，与现有 `growth-vigor-v1.1-rule` 的三等级 80/60 阈值冲突。
3. 生育期是浏览器规则推断，不是现有 FoMo4Wheat/CGIAR 七分类模型结果。
4. `PRICE_CONFIG.basePrice = 2.44`、等级溢价、阶段亩产基数和收益公式均是写死规则，没有使用项目真实周度价格字段 `date,price_yuan_per_ton,source`，禁止接入市场页面。
5. `buildPseudoCloud` 使用多处 `Math.random()`，重复运行不能得到相同点云，不能用于科研结果或真实三维验证。

### 可保留思路

可以参考它的“图像预览、掩膜叠加、指标卡片和质量提示”的交互思路；实际数据必须由现有 FastAPI 返回。

## 3. analyze-page.js 审查

### 依赖和运行条件

文件导入：

- `./common.js`
- `./vision.js`
- `./pointcloud.js`
- `./report.js`

在外部文件目录中，`common.js`、`pointcloud.js`、`report.js` 和对应 `analyze.html`/`index.html` 均不存在，因此不能独立运行。当前 Vue 项目也没有 Three.js 依赖，不能直接承载 `createCloudViewer`。

脚本直接通过 `document.getElementById` 获取 45 个固定 ID，并在模块加载时立即注册事件。缺少任何一个 ID 都会在 `addEventListener` 处抛错。它不是 Vue 组件，也不是可直接挂载的纯计算模块。

### DOM 和副作用

- 使用 `document.getElementById`、`querySelector`、`querySelectorAll`、`innerHTML` 和全局 `document.addEventListener`。
- 依赖固定 Canvas、上传 input、ROI、价格输入、生育期选择和测报卡弹层 DOM。
- 没有 `window.onload`，但默认脚本执行时 DOM 已完整存在；在 Vue 生命周期中直接执行会造成时序问题。
- 图片 `URL.createObjectURL` 在 `Image.onload/onerror` 中释放，属于较好的局部处理；`createImageBitmap` 路径没有显式调用 `ImageBitmap.close()`，长时间多图操作可能累积资源。
- 文件限制为 MIME `image/*` 且 30MB，没有严格限制为 JPG/PNG，没有对真实编码和像素上限做服务端同等校验；SVG 等 `image/*` 文件应拒绝。
- `innerHTML` 用于等级、价格和动态提示。当前值大多来自内部规则，但若以后接入 API 或用户字段会形成 XSS 风险，应全部改成 `textContent`/Vue 模板。

## 4. style.css 审查

该文件是整页全局 CSS，包含 `:root`、`*`、`html`、`body`、`body::before/after`、`img`、`button`、`input`、`nav`、`.card`、`.panel`、`.price-grid` 等大量通用选择器，并使用浅蓝白主题（例如 `#f4f9fd`、`#ffffff`、`#fbfdff`）。

直接导入会覆盖麦视通现有深森林绿、深色麦田背景、玻璃面板、按钮、导航和表单样式，也会与现有 `styles.css`、`dark-cockpit.css`、`glass-theme.css` 产生级联冲突。当前没有安全的“复制后直接导入”路径。

若将来只借鉴视觉，应把选择器全部包在 `.legacy-vision` 命名空间内，并移除 `:root`、全局 `body`、`*`、全局 `button/input/img` 和价格卡片规则；本轮没有执行这类接入。

## 5. 价格、产量和科研口径风险

外部代码直接把单张图片的 VGI 和启发式生育期映射成亩产、单价、亩产值和价格区间。这违反当前项目的真实数据要求：单张图片不能推导全国价格、最终产量或收益，且没有连续真实价格、产量和回测结果。

现有市场页面继续显示“等待数据接入”，没有接入外部价格卡片。外部文件中的示例价格和产量不会进入项目。

## 6. 运行检查

- `vision.js` `node --check`：通过，仅表示 JavaScript 语法可解析。
- `analyze-page.js` `node --check`：通过，仅表示 JavaScript 语法可解析。
- 外部页面实际运行：未执行；依赖文件和 HTML 缺失，不能伪造成功。
- 现有项目 `npm run build`：通过。
- 现有 Python/FastAPI 测试：既有结果保持通过；本轮没有因外部文件修改生产代码。

## 7. 集成结论

### 可复用

- 图片上传区的交互布局思路。
- 原图/掩膜/叠加图对照的展示思路。
- 指标条和质量提示的视觉组织方式。

### 不可复用

- 浏览器端 ExG/Otsu/颜色分割实现。
- 五级 VGI、固定等级阈值和固定权重。
- 启发式生育期判断。
- 固定价格、亩产和收益估算。
- 随机伪点云。
- 依赖缺失的静态 DOM 控制器。
- 未命名空间的全局 CSS。

### 当前处理

三个文件保持在外部目录，未复制到生产 `src`，未加入 `main.js`、路由或 `GrowthAnalysis.vue`。项目内只新增了隔离说明：

`frontend/src/experimental/legacy-vision/README.md`

该说明明确记录了不接入的原因。现有分析继续使用：

- `POST /api/image/analyze`
- `POST /api/growth/analyze`
- `POST /api/growth-stage/predict`
- `GET /api/growth/history`
- `GET /api/growth/history/{analysis_id}`

如果未来要演示外部视觉稿，建议先提供完整 `common.js`、`pointcloud.js`、`report.js` 和 HTML，并把算法和价格部分完全替换成现有 API 适配器；在此之前不得进入生产页面。
