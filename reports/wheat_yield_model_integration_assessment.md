# wheatmedel.py 与麦视通产量预测模块兼容性评估

检查日期：2026-11-14  
检查范围：只读检查附件 `C:\Users\89885\Documents\xwechat_files\wxid_mb2elaeaadnu22_f8f7\msg\file\2026-11\wheatmedel.py` 和项目 `D:\Desktop\wheat\source-code\wheat-phenotyping`。本轮未执行该脚本、未导入并运行模型、未训练、未下载 FIP1 或气象数据、未修改任何代码/数据/网页/实验结果。

## 1. 结论摘要

`wheatmedel.py` 是一个独立的 FIP1 产量回归研究脚本，不是当前麦视通的可插拔模型。它可以作为“科研产量预测原型”的参考，但不能直接接入当前网页的单张照片入口。

主要原因：

1. 当前项目没有 FIP1 数据、Parquet、图像缓存或该脚本生成的模型/结果文件。
2. 脚本把 FIP 图像 URL、`yearsite_uid`、播种/抽穗日期、瑞士固定坐标气象数据和 `yield_value` 组合为输入；麦视通当前上传接口只接收一张 RGB 图片和四种分割算法。
3. 产量目标单位由 `yield_si_unit` 原样读取，但脚本没有校验、转换或拒绝混合单位。
4. 所谓“两时相”是“抽穗前约 8 天 + 最新收获前图像”，不是适合手机早期预测的固定早期观测方案；最新收获前图像会带来严重的预测时点问题。
5. 脚本读取 train 和 validation Parquet 后合并，再按 `yearsite_uid` 做留一环境验证；它没有沿用官方 validation/test split，也没有在代码中证明地块/年份/图像序列不重叠。
6. 训练对象是 ExtraTreesRegressor 和 HistGradientBoostingRegressor 的离线实验，不保存可供 FastAPI 加载的模型、特征 schema、预处理版本或推理契约。

建议：**先保持长势分析 V1 独立完成，再把产量预测作为单独的科研数据管线接入。** 只有当数据、单位、特征时间窗和中国场景验证协议完成后，才把它接到网页；不要在当前单图上传页面上直接显示产量数值。

## 2. 本地数据检查

### 2.1 项目目录

在当前项目中检查了以下位置：

```text
data/fip1
data/FIP1
data/raw/fip1
data/raw/FIP1
data/processed/fip1
data/processed/FIP1
fip_full
fip_validation
```

以上路径均不存在，项目内没有 FIP1 Parquet。当前 `data` 中已有的是 EWS 相关数据和其他既有项目数据；没有发现可直接供 `wheatmedel.py` 使用的 FIP1 训练/验证文件。

### 2.2 附件脚本旁的数据

附件所在目录只发现 `wheatmedel.py` 和其他用户文件，没有：

- `fip_full/train-*.parquet`
- `fip_validation/validation-*.parquet`
- `fip_temporal/images`
- `fip_multisite/images`
- `fip_temporal_results.json`
- `fip_weather_era5.json`

因此本机当前不能回答以下“实际文件统计”：非空 `yield_value` 小区数、`yield_si_unit` 的实际取值频数、脚本最终可用样本数、下载失败数、实际 `yearsite_uid` 数量和模型训练结果。没有执行 `read_rows()` 或 `main()` 来补这些数字，因为那会进入数据处理/网络/模型流程，违反本轮只读兼容性检查边界。

### 2.3 FIP1 公开数据的外部核对

FIP1 官方数据卡公开描述了 4,058 行 plot-year 数据、六个数据采集年份（2016–2019、2021–2022；2015 和 2020 因测量季不完整被排除），超过 4,000 个小麦小区和超过 153,000 张对齐图像；数据包含产量、冠层覆盖、株高、穗数、衰老、抽穗日期、最终株高和蛋白质等性状。[FIP1 官方数据卡](https://huggingface.co/datasets/mikeboss/FIP1)  

官方文件划分还包括 train 2,930 行、validation 380 行，以及 test_plot、test_genotype、test_environment、test_genotype_environment 等留出集；Parquet 文件本身在公开仓库中可见，但本轮未下载。[FIP1 README 与 split 元数据](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)  

“试验环境数量”需要先明确口径：FIP1 资料同时出现年份、lot、year-site 和 MET year-location 概念。脚本使用 `yearsite_uid` 作为分组键，实际环境数应由本地 Parquet 的唯一值计算；不能把公开资料中的六年、两个小麦 lot、六个环境或八个 MET year-location 直接互换。因此本报告不填一个未经本地核验的环境数量。

“标注小区数量”也必须区分总 plot-year 行与有非空产量、有有效图像且满足两时相选择的小区。官方 4,058 行不是脚本最终 `n_labeled_plots`，后者需要读取文件后按代码过滤才能得到。

## 3. wheatmedel.py 代码审查

### 3.1 数据路径和样本筛选

关键代码：

- `ROOT = Path(__file__).resolve().parent`
- `DATA = ROOT / "fip_full"`
- `VALIDATION = ROOT / "fip_validation"`
- `read_rows()` 读取 `train-*.parquet` 和 `validation-*.parquet`。
- 只保留 `yield_value is not None` 且存在 `inner_plot_images` 的行。
- 按 `yearsite_uid` 组织行，每个环境最多随机抽取 `PER_SITE=1000` 条，种子为 `SEED=42`。

问题：

1. 没有检查两个目录中的文件是否真的是官方 train/validation、是否重复、是否同一 plot 出现在两个 split。
2. 没有保存筛选前后的样本清单、排除原因和抽样索引到独立协议文件。
3. `PER_SITE=1000` 是硬编码抽样上限，不是由数据规模或统计功效推导出的参数。
4. `yearsite_uid` 的分组粒度可能比地块、基因型或图像序列更粗/更细；代码没有检查同一 plot、同一基因型、同一图像 URL 是否跨组重复。
5. `yield_value`、日期、图像数组长度和 URL 是否一一对应均未做完整质量检查。

### 3.2 RGB 图像特征

`rgb_features(path)` 的实际特征包括：

- Pillow 转 RGB，缩略图最长边不超过 320 像素。
- R、G、B 各 20 bin 直方图，共 60 维。
- 三个 ExG/绿色判定比例：`exg > 0.03`、`exg > 0.12` 和 `(g > 1.04r) & (g > 1.02b)`。
- R、G、B、ExG 各自的均值、标准差、10%、50%、90% 分位数，共 20 维。
- 8×8 粗空间网格中 ExG>0.05 的比例，共 64 维。

单张图像共 147 维。两张图像拼接后再加入：

- 两个时相各自的 147 维特征：294 维。
- 后期减早期的差分特征：147 维。
- 每个时相距离播种和抽穗的天数、抽穗-播种间隔、播种日序：6 维。

因此视觉/物候输入 `X_visual` 为 447 维。代码没有使用当前麦视通的 ExG 掩膜、HSV 掩膜、RF 特征 schema 或 V1 覆盖率指标；它是一套独立的全图统计特征方案。可复用的思想是颜色统计、ExG比例、粗空间统计和时相差分，不能直接复用为当前 Web 的推理函数。

风险：

- `Image.thumbnail((320, 320))` 保留宽高比，但没有记录原始尺寸、缩放比例或拍摄裁剪信息。
- 直方图和空间网格依赖 FIP 的固定相机/对齐 inner plot 图像；手机照片的构图、距离、背景和视角不同。
- ExG 阈值写在函数内部，不能按研究协议配置、冻结和追溯。
- 只使用全图统计，不利用当前已经生成的植被掩膜；土壤、行间背景、遮挡和天空会进入同一统计量。
- 没有检查图片色彩空间、曝光、模糊或透明通道处理策略。

### 3.3 时相特征与时间选择

`select_frame_indices(row)` 的逻辑是：

1. 收集有日期且有 URL 的图像。
2. 有抽穗日期时选择抽穗前约 8 天最近图像；没有抽穗日期时选择播种到收获时间跨度约 78% 处的图像。
3. 再加入 `pairs[-1]`，即最新可用图像，代码注释称为 latest pre-harvest。
4. 最终只保留两张。

这不是“早期产量预测”的可靠时间设计：

- 最新 pre-harvest 图像接近收获，可能携带强烈的后期产量代理信息；如果产品声称播种后早期预测，会发生预测时点泄漏或使用场景不一致。
- 有抽穗日期时，第一张是抽穗前 8 天，不是苗期/分蘖期；没有抽穗日期时，约 78% 生育进程也偏晚。
- 两张图可能时间间隔很小，变化特征不代表稳定生长轨迹；也可能因缺测而时间间隔很大，代码没有记录或限制间隔。
- 选择会依赖抽穗/收获日期，这些信息在手机单图上传时通常不可得。

未来应先定义产品时点，例如“抽穗前 21 天预测收获产量”，只使用该时点及更早观测；固定允许的观测窗口，保存每张图的拍摄日期与距预测时点的天数，并在地块级分组后评估。

### 3.4 气象特征

`load_weather()` 调用 Open-Meteo ERA5 历史接口，硬编码：

```text
latitude=47.449
longitude=8.682
start_date=2015-09-01
end_date=2022-07-31
timezone=Europe/Zurich
models=era5
```

`weather_features()` 对播种到照片日期以及照片前 30 天聚合：平均/积温式温度、降水、短波辐射、ET0、高温日数等，共 10 维；两张图的天气特征再拼接差分，天气输入为 30 维，最终 `X_fused` 为 477 维。

必须修改的地方：

- 不能把瑞士坐标用于中国地块；应优先读取样本的 `latitude/longitude`，或明确使用中国站点/再分析网格。
- 对每个样本记录气象源、坐标、时间区间、时区、缺失率和 API 版本。
- 不应把温度、降水、辐射和 ET0 的单位、缺测处理隐含在函数里。
- 中国项目需要考虑冬小麦区域、播期、越冬和灌溉差异，不能直接迁移瑞士累计窗口。
- 气象 API 请求和缓存必须与模型训练解耦；Web 在线推理不能因为一次天气 API 访问失败而产生无来源预测。

### 3.5 ExtraTrees 与 HistGradientBoosting

ExtraTrees 部分：

- 对 `visual_only` 和 `visual_plus_weather` 两套输入分别训练。
- 外层每次留出一个 `yearsite_uid` 环境。
- 内层对训练环境再做留一环境比较。
- 只搜索 `min_samples_leaf ∈ {3,5}` 和 `max_features ∈ {"sqrt",1.0}`。
- 内层选择 RMSE 最小配置后，外层训练 300 棵树，`random_state=42`、`n_jobs=-1`。

HistGradientBoosting 部分：

- 只使用 `X_fused`。
- 搜索 `max_leaf_nodes ∈ {7,15,31}`。
- 固定 `max_iter=180`、`learning_rate=0.05`、`l2_regularization=5.0`、`min_samples_leaf=20`、`early_stopping=False`、`random_state=42`。
- 同样按 `yearsite_uid` 外层留出，内层用 RMSE 选叶节点数。

可复用：模型类型、树模型适合混合手工特征、嵌套环境留出验证思路。不能直接复用：训练命令、数据路径、天气函数、时相选择和结果文件，因为它们没有项目化 schema、配置冻结和模型 artifact 契约。

### 3.6 评价和产物

`score()` 输出 MAE、RMSE、R²；每个外层环境输出 fold 结果，并保存：

- `fip_train_features.npz`
- `fip_temporal_results.json`

问题：

- 没有保存每个样本的预测值、样本日期、模型配置和数据版本清单。
- 没有置信区间、预测区间、不确定性或按环境的误差分布图。
- R² 在小环境 fold、跨环境分布变化明显时可能不稳定，不能单独作为模型可用性依据。
- MAE/RMSE 的单位直接继承 `yield_value`；如果单位混合，指标不可解释。
- 没有和简单均值、历史均值、按环境均值等基线建立一致的预注册比较表。
- `fip_train_features.npz` 名称暗示 train，但实际输入已经包含脚本读取的 validation Parquet 行，命名和数据角色不一致。

## 4. 训练/验证划分风险

脚本的“留出 year-site”比随机像素划分更合理，但仍有以下风险：

1. 它把官方 train 和 validation 文件一起读入，然后只按 `yearsite_uid` 重划；官方 validation 的独立角色没有保留。
2. 没有检查官方 validation 与 train 是否共享 plot、genotype、image URL 或同一时间序列。
3. 没有预先锁定最终测试协议，也没有防止多次查看外层 fold 后调整特征。
4. `yearsite_uid` 是否足以代表地块环境没有通过清单核验；应同时检查 `plot_uid`、lot、genotype 和日期序列。
5. 同一地块的多时相图像被作为同一行的特征，这是正确方向；但必须确保同一地块不会在其它行或 split 重复出现。
6. 最终训练模型没有保存 `feature_names`、特征维度、时相规则、天气源、单位转换和源码 commit/hash，无法可靠复现。

建议新协议：地块级分组，优先使用官方 test_environment/test_genotype_environment 做最终外部验证；如果研究“早期预测”，按时间截止点冻结输入，而不是只按环境留出。

## 5. yield_value 单位和目标定义

脚本选择 `yield_value`，把 `yield_si_unit` 原样存入 `unit`，但没有：

- 枚举允许单位；
- 检查是否全体一致；
- 把 kg、t/ha、g/plot 等转换到统一目标；
- 检查 `yield_value` 是否为 adjusted yield；
- 检查 plot 面积、收获行数和估产口径。

因此当前不能把它的 MAE/RMSE 直接解释为“吨/公顷误差”。FIP1 公开论文资料中，产量存在调整后的 t/ha 口径，但本地脚本仍必须以 Parquet 中 `yield_si_unit`、trait 名称和来源字段实际核验为准。[FIP1 论文与产量口径](https://pmc.ncbi.nlm.nih.gov/articles/PMC12153353/)

集成前必须建立统一目标：例如 `yield_t_per_ha`，保存原始值、原始单位、转换公式、plot 面积/收获行数依据和转换版本；混合单位、空单位或目标含义不明确的记录应拒绝训练。

## 6. 手机照片迁移评估

当前不能直接迁移到手机照片。原因不是 ExtraTrees 或 HistGradientBoosting 本身，而是输入域不一致：

- FIP 使用固定相机平台和对齐的 inner plot crop；官方资料说明图像是按 plot 采集的时序数据。[FIP1 数据结构说明](https://huggingface.co/datasets/mikeboss/FIP1/blob/main/README.md?code=true)
- 手机图像可能包含天空、行间土壤、多人/设备遮挡、不同视角、分辨率、焦距、曝光、白平衡和背景。
- 当前脚本没有裁剪/地块定位/尺度标定/相机域适配，也没有手机数据验证。
- 当前脚本要求两张带日期的图像、播种/抽穗日期和天气特征；网页上传一张图片不能提供这些输入。

建议的迁移方式：

1. 先把手机图像经过当前真实分割流程，得到植被掩膜和 V1 覆盖率/绿色程度/均匀度。
2. 建立手机拍摄协议：固定距离、视角、标尺/地面参考、时间和地块 ID。
3. 重新设计手机可获得的时相特征，先做单时相基线，再做多时相模型。
4. 使用中国地块级产量实测作为目标，做跨地块/跨季节验证。
5. 在未完成域适配和样本外验证前，网页只展示“产量研究模块待启用”，不显示 FIP 模型数值。

## 7. 中国小麦数据可用性

### 当前项目内

当前项目没有中国小麦产量图像数据，也没有可与用户手机照片配对的中国地块实测产量数据。因此目前不能声称已有中国训练/验证集。

### 可作为后续候选的数据方向

- **FIP1**：适合做方法学与多时相产量研究，但主要是瑞士固定平台冬小麦，不能直接代表中国生产场景。[FIP1 官方数据卡](https://huggingface.co/datasets/mikeboss/FIP1)
- **Wheat breeding phenotyping and yield dataset**：公开描述包含中国田间试验的冠层高度、冠层体积、LAI、多光谱植被指数、天气和产量（kg），更适合做中国场景的表型-产量辅助数据核查；当前资料没有证明它提供与手机 RGB 图像配对的数据，因此不能直接替代图像产量集。[Zenodo 数据集](https://zenodo.org/records/14322630)
- **WGSW173**：北京采集、105 个小麦品种、3,777 张图像，含可见光等多传感器和图像级表型标签，但定位是表型分类，不是带收获产量的田间回归集。[OPIA WGSW173](https://ngdc.cncb.ac.cn/opia/dataset/datasets?dataId=48)
- **CUWT**：中国江苏与英国田间手机双视角图像和穗部性状，适合手机域和器官/品种表型研究，但公开说明的目标是品种分类与穗部性状，不是当前脚本所需的 plot-level 收获产量回归。[China-UK Wheat Traits](https://zenodo.org/records/20056636)
- **中国长期产量/农艺数据**：可用于区域或历史产量趋势研究，但没有与单张 RGB 图像逐地块配对，不能直接用于手机图像产量预测。[中国作物产量与农艺数据说明](https://pmc.ncbi.nlm.nih.gov/articles/PMC13578210/)

结论：目前存在可作为补充的中国小麦公开资源，但没有一项已被当前项目核实为“手机 RGB + 同地块实测产量 + 多时相 + 气象”的直接替代数据集。需要先做许可证、字段、空间尺度、目标单位和图像配对核验。

## 8. 独立产量预测模块的集成设计

### 8.1 建议目录

不把附件脚本直接复制到现有入口，建议新建：

```text
src/wheat_phenotyping/yield_prediction/
├── schema.py              # 样本、单位、时相和特征版本
├── image_features.py      # 手机/FIP 各自可追溯的特征适配器
├── phenology.py           # 日期与预测截止时点处理
├── weather.py             # 坐标、气象源、单位和缺失策略
├── model.py               # ExtraTrees/HistGB 模型加载与 schema 校验
├── inference.py           # 已冻结模型的推理，不负责训练
└── storage.py             # 模型元数据、预测记录和 provenance
```

训练和实验脚本另放：

```text
scripts/yield_prediction/
├── inspect_fip1.py
├── prepare_dataset.py
├── train_extratrees.py
├── train_hist_gradient_boosting.py
├── validate_grouped.py
└── evaluate_frozen_test.py
```

### 8.2 建议 FastAPI 接口

第一版不要把产量预测挂到当前“单张图立即返回”接口，建议独立版本：

```text
GET  /api/v1/yield/health
POST /api/v1/yield/analyses
GET  /api/v1/yield/analyses/{analysis_id}
GET  /api/v1/yield/models
```

`POST /api/v1/yield/analyses` 的输入至少应包含：

- 一组属于同一地块的 RGB 图像，而不是单张任意照片；
- 每张图的采集日期/时间；
- 地块或观测 ID；
- 播种日期；
- 预测截止日期；
- 位置或已确认的气象特征来源；
- 明确的模型版本和数据域。

如果只有一张图片，接口应返回“输入不足，产量模型需要多时相/地块信息”，不能运行 FIP 模型后显示数字。

响应应包含：

- `analysis_id`、`model_id`、`feature_schema_id`；
- 输入图像哈希、时间窗、气象来源和目标单位；
- 预测值及单位；
- 适用范围和域提示；
- 是否为研究验证结果或用户推理；
- 不确定性/预测区间（模型具备后）；
- 明确的“非中国验证/非农事决策结论”提示。

### 8.3 Vue 展示方式

产量页面可以先做真实状态页面：

- 输入图像时间线和地块信息；
- 数据完整性检查；
- 模型/域/单位信息；
- “需要至少 N 个时相”提示；
- 预测模块待启用状态。

完成中国验证后再显示预测卡片、区间、模型来源和验证环境。不要把 FIP 瑞士模型结果放入当前单图长势页面，也不要把预测值与市场价格直接连成经济结论。

## 9. 可直接复用与必须修改

### 可以直接复用的思想/局部代码

- RGB 直方图、ExG 比例、分位数和粗空间统计的特征设计思路。
- 多时相“每时相特征 + 后期减早期差分”的数组组织方式。
- ExtraTreesRegressor 和 HistGradientBoostingRegressor 作为可解释的树模型基线。
- 按 `yearsite_uid` 做外层留一环境、内层选择参数的验证思想。
- MAE、RMSE、R² 的基本计算形式。

### 不能直接复用，必须修改

- `ROOT/DATA/VALIDATION` 路径和运行时网络下载逻辑。
- 两张图像选择规则。
- 瑞士固定坐标和 Open-Meteo 查询。
- `yield_value` 原样作为目标的做法。
- 把 train 与 validation 合并后再验证的流程。
- 无模型 artifact/schema 的保存方式。
- 直接把 FIP 固定相机特征当成手机照片特征。
- 直接把 `fip_temporal_results.json` 当作 FastAPI 可加载模型。

## 10. 应在长势分析 V1 之前还是之后集成

**之后集成。**

顺序建议：

1. 完成并稳定当前长势分析 V1：单图上传、四算法实际掩膜、覆盖率/绿色程度/空间均匀度/质量指标。
2. 增加分析记录列表、地块 ID、拍摄日期和多次观测存储；这是产量模型输入的基础。
3. 独立检查和整理 FIP1，不下载进 EWS 目录，不混合真实数据域。
4. 先在 FIP1 上建立 train/validation/test 冻结协议和单位审计，复现实验但不把结果宣称为中国成绩。
5. 再建立中国手机/田间图像与实测产量配对集，做域外验证。
6. 最后把冻结的独立产量模型接入 FastAPI 和 Vue。

如果在长势 V1 之前集成，会把“单幅可见植被指标”“多时相产量预测”和“市场价格预测”混成一个未经验证的输入链，难以解释和审计。

## 11. 当前缺失清单

- FIP1 train/validation/test Parquet。
- FIP1 图像或可访问的完整图像缓存。
- FIP1 的字段 schema、产量非空计数和单位频数的本地审计结果。
- 可复现的 FIP1 数据快照、样本 ID、分组和数据版本。
- 单位统一和 adjusted yield 定义。
- 中国地块级 RGB/手机图像与实测产量配对数据。
- 中国区域、品种、播期、管理和气象元数据。
- 早期预测的统一截止时点和最少时相协议。
- 模型保存、schema 校验、预测区间和冻结测试流程。
- FastAPI 产量分析 API 及 Vue 多时相输入界面。

本报告没有填入 FIP1 本地样本数、训练成绩或预测成绩，因为这些数据/结果目前不存在且本轮禁止下载和运行。
