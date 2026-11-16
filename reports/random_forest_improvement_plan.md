# 麦视通：随机森林分割改进检查与实验方案

检查日期：2026-11-14。项目：`D:\Desktop\wheat\source-code\wheat-phenotyping`。

本轮只检查源码、已有模型、数据和已有实验记录，新增本报告。没有训练模型、执行分割推理、开展新的精度实验、下载数据或修改网页。下文所有新增配置、特征和文件均为待实施方案，不代表已经实现或已经取得性能提升。

## 1. 检查结论

- 已有可复用的随机森林训练、验证、测试评价和 Python/Tkinter 推理代码；已有可加载的 7 维随机森林模型。
- 现有 RF 已经使用 RGB、ExG、局部灰度均值、标准差和梯度。因此“加入纹理”本身不是本项目全新的能力，必须通过明确的基线和消融实验说明改进点。
- FastAPI 和 Vue 目前只接入四种传统算法，尚无 RF 网页调用入口；Python 支持 RF 不等于网页已经支持 RF。
- EWS 实际为 train 142、validation 24、test 24，合计 190 组真实图像与人工标注。标签是活体植被与非活体材料/背景二分类，不包含叶片、茎秆、麦穗类别。
- 官方 test 集已有历史评价结果，不能再称为从未使用过的盲测集。后续严格冻结新方案，并如实披露既往测试暴露。
- 下一步应先实现独立、可配置、带特征版本校验的改进 RF 特征提取器及一致性测试，再进入训练。

## 2. 现有代码清单与实际接口

以下路径均相对项目根目录，函数名称来自实际源码。

| 文件 | 现有接口/职责 | 输入、输出及复用条件 |
| --- | --- | --- |
| `scripts/train_rf_segmenter.py` | `train_model(manifest, output_dir, *, seed=20261112, pixels_per_class_per_image=500, tree_count=100, max_depth=18, min_samples_leaf=2)` | 读取清单，仅用 train 抽样训练；输出 joblib 和训练元数据，返回元数据字典；非空输出目录拒绝覆盖。特征固定为现有 7 维，不能直接训练新特征组合。 |
| `src/wheat_phenotyping/leaf_segmentation/rf_features.py` | `FEATURE_NAMES`、`extract_pixel_features(image)` | `RGBImage` → 行优先的 `(H*W, 7)` 数组；逐像素颜色、局部统计、梯度；可作为旧模型的固定特征实现。 |
| `scripts/evaluate_rf_segmenter.py` | `_make_predictor(model_path)`、`run_experiment(manifest, model_path, split, output_dir, *, frozen_metadata=None, thresholds=...)` | 加载旧模型，整图提取 7 维特征，`predict_proba` 后阈值化；validation 选择阈值，test 要求冻结元数据；输出既有评价 CSV、JSON、图表。 |
| `src/wheat_phenotyping/app/inference.py` | `predict_visible_mask(rgb, method, *, model=None, parameters=None, probability_threshold=0.75)` | 返回 `(BinaryMask, metadata)`；RF 名称为 `RF-Color-Texture`，必须传入已加载的模型；正类概率列根据 `classes_` 中的标签 1 定位。 |
| 同上 | `run_image_batch(image_paths, methods, output_dir, *, model=None, model_path=None, algorithm_parameters=None, rf_probability_threshold=0.75, source_root=None, progress=None)` | 单图/批量无标注推理，支持加载 RF 模型，保存掩膜、叠加图、CSV、JSON；不是人工标注精度实验。 |
| `src/wheat_phenotyping/app/desktop.py` | 桌面程序的模型路径和算法选择 | 指向 `results/ews/rf_training/rf_color_texture.joblib`；桌面入口包含 RF。 |
| `src/wheat_phenotyping/data/image_io.py` | `load_rgb_image(path)`、`load_binary_mask(path)`、`load_sample_images(image_path, mask_path)` | 统一 RGB 和二值标注读取；配对尺寸不符时报错，不自动缩放标注。 |
| `src/wheat_phenotyping/leaf_segmentation/registry.py` | `DEFAULT_REGISTRY`、`SegmenterRegistry.run(name, image, parameters)` | 注册四种传统算法；RF 在统一推理函数中单独分支，尚未注册到此注册表。 |
| `src/wheat_phenotyping/evaluation/batch.py` | `evaluate_batch(...)`、`summarize_by_dataset(results)` | 统一逐图计算、运行时间、宏平均、总体混淆矩阵汇总、标准差和双空统计；适合复用评价标准。 |
| `src/wheat_phenotyping/evaluation/calibration.py` | `calibrate_candidates(...)` | 只允许 train/validation 选参，拒绝 test；目前选择指标限 IoU、Precision、Recall、F1。 |
| `src/wheat_phenotyping/evaluation/reporting.py` | 评价输出 | 复用 CSV/JSON/SVG 输出能力；目前没有本方案定义的覆盖率 MAE。 |
| `scripts/combine_ews_test_summaries.py` | 既有五算法结果汇总 | 已有历史汇总能力；新增 A–F 实验应另建输出目录，避免混入或覆盖历史结果。 |

### 2.1 当前 RF 的七个特征

顺序严格为：

1. `red`：R/255。
2. `green`：G/255。
3. `blue`：B/255。
4. `excess_green`：`clip(2g-r-b, -2, 2)/2`，其中 r/g/b 是归一化颜色；等价于原始字节值 `(2G-R-B)/510`，范围为 [-1, 1]。
5. `local_gray_mean_5x5`：灰度 `0.299r+0.587g+0.114b` 的 5×5 均值。
6. `local_gray_std_5x5`：同一窗口灰度标准差。
7. `gray_gradient_magnitude`：两个方向 Sobel 的幅值除以 8。

局部运算使用最近像素延拓 `mode="nearest"`。函数说明写“所有通道归一化至 0..1”，与 ExG 可为负值的实际实现不一致；本轮仅记录，保留算法原样。新特征 schema 应逐项写清公式、范围、顺序和 dtype。

### 2.2 输入与输出约定

- RGB 输入为 `RGBImage(width, height, pixels)`，像素缓冲区是 8 位 RGB，长度 `W*H*3`。通用读取器支持 PPM、PNG、JPEG、BMP、TIFF；常见格式由 Pillow 解码并处理 EXIF 方向。
- 输出为 `BinaryMask(width, height, pixels)`，内存中只使用 0/255，255 表示预测活体植被。尺寸与输入一致。
- RF 评价脚本和应用推理都按正类概率阈值生成掩膜。旧验证产物冻结值为 0.75；这是旧模型的历史选择，不能直接宣称是新 RF 的最优阈值。
- 旧评价脚本允许概率阈值闭区间 [0,1]，应用入口要求开区间 (0,1)。新适配器应统一约束并测试边界，旧实现本轮不改。
- 应用推理每 256 行分条带，保留上下各 2 行上下文；仅适配现有最大半径为 2 的特征。新 17×17 邻域需要至少 8 行上下文，不能套用原 halo=2。
- 原始 EWS PNG 标注具有特殊前景方向和中间灰度，不应直接送入通用二值读取器。研究使用清单已指向的规范化 PGM。

## 3. 现有模型文件核查

| 项目 | 本轮检查结果 |
| --- | --- |
| 模型 | `results/ews/rf_training/rf_color_texture.joblib` 存在，35,487,605 字节 |
| 训练记录 | `results/ews/rf_training/training_metadata.json` 存在 |
| 只读加载 | 使用项目 `.venv` 的 Python 以 `-B` 加载成功；没有调用 fit、predict 或 predict_proba |
| 实际对象 | `RandomForestClassifier`；`n_features_in_=7`；`classes_=[0,1]`；100 棵已拟合树 |
| SHA-256 | `61d388a4bd7809ddda3d668c5b19a39af6bd43b80d44eedca5bd756c85f14d85` |
| 训练时间记录 | `2026-11-12T09:10:27+00:00`，来自既有元数据 |
| 训练样本记录 | 142 张 train 图；每图每类至多 500 像素，无放回抽样；合计 142,000 像素，正负各 71,000 |
| 核心参数 | `n_estimators=100`、`max_depth=18`、`min_samples_leaf=2`、`max_features="sqrt"`、`class_weight="balanced_subsample"`、`bootstrap=True`、`random_state=20261112`、`n_jobs=-1` |
| 训练依赖记录 | scikit-learn 1.9.1、NumPy 2.5.4，来自既有训练元数据 |

源码的训练路径确实只筛选 train；元数据声明 validation/test 未用于训练。只读核查不能独立重建旧训练全过程，也不能把元数据声明等同于完整不可篡改审计证据。新实验需保存样本索引、数据和模型摘要。

旧模型只有七维，不能直接接收新八维或十七维特征。新旧模型必须保留不同模型标识和 schema，不覆盖旧 joblib。

## 4. FastAPI 与 Vue 接入情况

| 检查位置 | 实际情况 |
| --- | --- |
| `backend/app/config.py` | `SUPPORTED_ALGORITHMS` 只有 ExG、HSV、Otsu-ExG、ExG-HSV Fusion。 |
| `backend/app/schemas.py` | `AlgorithmName` 的 Literal 仅允许上述四项。 |
| `backend/app/main.py` | `/api/image/analyze` 接收该枚举的表单参数；没有 RF 请求入口。 |
| `backend/app/image_service.py` | `analyze_image(...)` 调用 `predict_visible_mask(rgb, algorithm, parameters=...)`，未加载/传入 RF 模型。 |
| `frontend/src/services/imageApi.js` | `segmentationAlgorithms` 只有四种传统算法，上传请求会校验名称。 |
| `frontend/src/components/ImageAnalysisWorkbench.vue` | 使用现有算法列表组织识别和对比，没有 RF 选择入口。 |

结论：RF 尚未接入 Web。后续完成科学实验与模型版本约定后，再另行接入；本轮不修改 API 或页面。

## 5. EWS 数据核查

### 5.1 本轮实读结果

读取全部清单条目、解码全部原图及原始掩膜，并按现有转换规则逐像素比较 PGM；没有运行模型。

| 划分 | 原始 RGB PNG | 原始人工 PNG | 清单条目 / 对应 PGM |
| --- | ---: | ---: | ---: |
| train | 142 | 142 | 142 |
| validation | 24 | 24 | 24 |
| test | 24 | 24 | 24 |
| 合计 | 190 | 190 | 190 |

- 原图和标注均为 350×350；190 对尺寸、文件名配对及转换像素比较全部通过，没有读取失败。
- 原始掩膜为 LA 模式 PNG，亮度通道合计出现 77 种值，最小 0、最大 255，含边缘中间灰度。
- 现有规则为原始亮度 `<128` → 活体植被 1，其余 → 背景 0。规范化文件是 PGM P5、maxval=1、磁盘字节为 0/1；内存读取后为 0/255。
- 全部 PGM 的原始载荷与该规则逐像素一致；未缩放、未插值。PNG 编码保留无损，但灰度边缘转换为两类属于标签量化，不能表述为“所有原始灰度值均无损保留”。原始 PNG 仍保留。
- 实际空人工掩膜 0 张，全前景人工掩膜 0 张。
- 跨划分原图文件 SHA-256 相同的情况为 0；这只能排除完全相同文件，不能排除相近时间/同地块图像的相关性。
- `manifest.csv` 的 `mask_path` 和 `reference_mask_path` 指向规范化 PGM；数据名均 EWS、版本均 `2021-11-30`、来源均 public、标注类型均 `manual_live_vs_non_live_vegetative_binary`。

### 5.2 标签、来源和历史质量记录

原论文将确定属于活体小麦植被的像素作为正类，土壤、石块、枯死植物等其余材料作为负类。因此研究目标为可见活体植被分割，不能据此宣称完成器官分类、长势等级诊断、产量预测或三维验证。[EWS 论文](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2021.774068/full)

来源保留：数据 DOI `10.3929/ethz-b-000512332`，论文 DOI `10.3389/fpls.2021.774068`。项目已有数据摘要记录许可证 CC BY-SA 4.0、官方归档文件名和 MD5 校验结果；本轮未重新下载归档、也未重做下载时校验。[官方数据记录](https://doi.org/10.3929/ethz-b-000512332)

已有 `dataset_summary.json`、`dataset_quality_report.csv`、`manifest.csv` 和 20 对可视化检查图。历史摘要记录 GitHub 镜像存在部分缺失/错误标注；当前清单使用官方归档对应的 PNG/PGM，不应换回镜像 JSON 重新生成标签。

### 5.3 分组独立性与需要披露的限制

- 190 个 `group_id` 都等于 `sample_id`。清单能防止同一图片 ID 跨划分，不能证明拍摄序列、地块或年份独立。
- 将文件名第一个字段视为待核实的分组线索，validation/test 共享两个前缀：`FPWW0180049`、`FPWW0180367`。该前缀的真实含义需结合官方元数据确认，不能直接断言已经发生泄漏，也不能声称完全地块独立。
- 按文件名日期字段统计，validation/test 各有 24 张标记为 2017；train 标记为 2017/2018/2019/2020 的数量为 4/56/68/14。这只是文件名解析结果，不等于已核实的采集元数据。
- train 中四个 2017 日期文件为 `FPWW0220032_RGB1_20171213_141430_6`、`FPWW0220078_RGB1_20171213_142438_6`、`FPWW0220193_RGB1_20171213_135732_6`、`FPWW0220356_RGB1_20171213_143142_6`。论文描述了年份留出设计，但不能据此直接将本地划分称为严格完整的年份留出；需要核对季节/元数据含义。[论文划分说明](https://www.frontiersin.org/journals/plant-science/articles/10.3389/fpls.2021.774068/full)
- 保留现有官方划分和标签版本，本轮不重新划分。后续可在 train 内依据核实后的组做内部交叉验证；不得把同一图片的像素随机分到训练与验证/测试。

## 6. 改进方法与研究假设

随机森林适合作为手工特征的像素级分类基线：输入逐像素特征向量，学习非线性类别边界，使用正类概率阈值输出掩膜。应记录树大小、随机种子和并行配置，控制训练与推理资源。[scikit-learn 随机森林接口](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)

研究假设是：多尺度邻域与局部纹理可能缓解单纯颜色阈值在阴影、强光、土壤近似色下的错误。能否改善必须由验证和最终测试证明，不预设提升幅度。

这些特征相互关联，并非统计独立。RF 仍逐像素分类，加入邻域统计不等于引入显式空间一致性约束；不能保证连通性，也不能生成器官类别。

### 6.1 建议特征 schema

| 特征块 | 建议维度 | 定义 |
| --- | ---: | --- |
| C：颜色 | 8 | `r,g,b,S*sin(h),S*cos(h),S,V,exg`。h 为 HSV 色相弧度，S/V 为 [0,1]，ExG 与旧七维公式一致。色相采用周期表示，S=0 时两个色相分量为 0。 |
| T：局部纹理 | 3 | 灰度 5×5 均值、5×5 标准差、Sobel 幅值/8；复用旧公式和最近像素延拓约定。 |
| S：空间邻域上下文 | 6 | 当前图像 r/g/b 的 9×9 均值各一项，以及 17×17 均值各一项；不读取人工标签。 |

建议基础 E 为 C（8 维），改进 F 为 C+T+S（17 维）。5/9/17 是待验证的初始工程配置，不是已知最优窗口。HSV 转换优先复用项目 `hsv.py::rgb_to_hsv` 的定义；如为性能编写向量化实现，必须用已有函数作一致性对照。

主实验不使用绝对 x/y 坐标，避免模型依赖固定拍摄布局；也不使用标签邻域、文件名中的类别暗示或测试集统计。主实验不叠加形态学后处理；若研究后处理，另列消融项并在验证阶段冻结。

### 6.2 推理与模型兼容

- 为每套特征保存 schema ID、有序名称、公式版本、范围、窗口、padding、dtype、最大有效邻域半径及源码摘要。
- 模型加载校验 schema 和 `n_features_in_`；即使维数相同但顺序/公式不同，也必须拒绝运行。
- 保留旧七维提取器及模型专用入口，不将旧模型自动升级成新特征模型。
- F 的最大初始半径为 8，条带需保留足够上下文后裁回中心；若存在串联滤波，按依赖链累计半径，不能仅取单个窗口半径。
- 整图与分块特征应在边界和条带接缝处一致；概率及掩膜差异需通过测试控制，不能容忍可见接缝。
- 输出仍为与输入同尺寸的 `BinaryMask` 0/255，统一接入现有评价器。不为对齐尺寸缩放人工标注。

## 7. 实验分组与公平比较

| 组 | 算法 | 特征/参数约定 | 当前状态 |
| --- | --- | --- | --- |
| A | ExG | 沿用验证集冻结参数 | 已有实现和历史结果 |
| B | HSV | 沿用验证集冻结参数 | 已有实现和历史结果 |
| C | Otsu-ExG | 每张图由 ExG 分布自动计算阈值 | 已有实现和历史结果 |
| D | ExG-HSV Fusion | 沿用冻结交集融合参数 | 已有实现和历史结果 |
| E | 基础 RF | C：8 维颜色特征 | 待实现、待训练 |
| F | 改进 RF | C+T+S：17 维 | 待实现、待训练 |

另列 H：旧 `RF-Color-Texture` 七维模型作为历史参照；不冒充颜色基础组 E，也不冒充新改进组 F。

A–D 的实际冻结来源是 `results/ews/validation_calibration/selected_parameters.json`；共享配置为 `configs/segmentation/desktop_frozen_defaults.json`，内容一致：

- A：`exg_threshold=20`，`min_component_area=0`。
- B：H 55–145 度、S 0.1–1、V 0.15–1。
- C：空参数字典，自动阈值应逐图记录。
- D：ExG 阈值 0、最小连通面积 0，与 H 55–145、S 0.1–1、V 0.05–1 的条件取交集。

上述是已有配置，不是本轮新编造的分类阈值。E/F 的概率阈值必须重新按预登记验证流程选择。

所有组使用同一清单、图像解码、标注版本、原始尺寸、最终测试 24 个 ID 和同一指标实现。Otsu 在单张测试输入图像上计算自动阈值属于算法推理，不是利用测试标签调参；禁止根据测试成绩挑选其输入特征或后处理规则。

### 7.1 消融实验

只在 train/validation 开发：RGB 三维 → RGB+HSV 七维 → C 八维（E），以及 C+T 十一维、C+S 十四维、C+T+S 十七维（F）。旧 H 另外标记。

比较特征贡献时，固定同一训练像素索引、随机种子、RF 参数和阈值选择规则；分别优化 E/F 时，给两组相同搜索预算，并与“固定模型参数的特征消融”分表报告，避免把更大的调参预算说成特征贡献。

## 8. 训练、验证与参数选择流程

所有候选范围都是预登记方案，不是实测最优值。本轮没有执行这些步骤。

1. 固定 train/validation 清单 ID、数据版本、标签规则和内容摘要。训练命令只能拟合 train；validation 只能用于选择；test 读取预测和分数的入口保持关闭。
2. 在 train 内按图、按类无放回抽样。建议主实验每图每类上限 500，保存实际像素索引与标签；E/F 使用相同索引。类别不足则全取，空类不伪造。不能把抽样出的像素再随机拆成 train/test。
3. 预登记主随机种子 `20261114`；旧实验种子 `20261112` 保留原记录。采样、RF 与附加随机过程的种子分别保存。版本、线程数、操作系统、CPU、运行时间均入日志。
4. 先以固定 RF 参数做特征消融：100 棵树、深度 18、最小叶样本 2、`max_features="sqrt"`、`bootstrap=True`、`class_weight="balanced_subsample"`。这是与历史设置接近的起点，不保证最优。
5. E/F 各用相同的 12 组 RF 网格：树数 {100,200} × 深度 {12,18,None} × 最小叶样本 {2,5}；其余固定。每个模型仅在 train 拟合，validation 全图预测，不能平衡抽样验证像素来计算最终验证指标。
6. 每个模型在 validation 比较阈值 {0.25,0.35,0.45,0.50,0.55,0.65,0.75}；可复用其验证概率图，避免为每个阈值重新训练。新模型不继承“0.75 最优”的结论。
7. 主选择标准：24 张验证图全部成功后，按现有非双空图宏平均 F1 最大选择；相同 F1 按预登记候选顺序决定。MAE、耗时作为报告的次级指标，不在看到结果后临时切换主指标。
8. 可预登记独立的敏感性实验：采样上限 {250,500,1000}；纹理窗口 {3,5,7}、上下文窗口对 {(5,9),(9,17)}。这些只在 train/validation 研究，全部尝试要记录。若用于选择最终配置，必须计入 E/F 的公开搜索预算，不能悄悄扩大搜索。
9. 主方案完成后，可在验证集以 `20261115`、`20261116` 检查随机性，完整报告，不挑最有利的种子替代预登记主种子。验证集多次使用可能过拟合，应限制迭代并公开完整搜索记录。
10. 主协议保持只用 142 张 train 拟合最终模型，不在主结果中偷偷合并 validation 重训。若未来设计 train+validation 重训，需另外规定不接触 test 的阈值确定方式和协议。

均衡抽样改变了训练类别比例，RF 的概率不应直接解释成真实世界校准概率。任何额外标准化、PCA 或概率校准若需要拟合，只能从 train 学习，然后原样应用到 validation/test。[数据泄漏与一致预处理说明](https://scikit-learn.org/stable/common_pitfalls.html)

## 9. 评价指标与时间口径

正类统一为活体植被。沿用现有混淆矩阵实现：

- IoU = TP/(TP+FP+FN)。
- Precision = TP/(TP+FP)。
- Recall = TP/(TP+FN)。
- F1 = 2TP/(2TP+FP+FN)。

特殊分母、双空图沿用现有评价器约定，不为了新算法改变。现有数据集汇总将双空图排除在四项分割宏平均之外，单独报告数量；全组无前景时 pooled 指标留空。标准差采用逐图总体标准差 `statistics.pstdev`，不是不同随机种子方差或置信区间。

### 9.1 本研究中 MAE 的明确含义

主 MAE 定义为逐图可见植被覆盖率误差，不是长势等级或物理高度误差：

`pred_fraction_i = (TP_i+FP_i)/N_i`

`true_fraction_i = (TP_i+FN_i)/N_i`

`coverage_MAE = mean(abs(pred_fraction_i-true_fraction_i))`

同时记录 `coverage_mae_fraction`（0–1）与 `coverage_mae_percentage_points`（前者乘 100，单位百分点）。有效空图亦可计算覆盖率误差，并单列空图数量；如提供非空子集 MAE，需要明确其分母。

覆盖率相同仍可能分错位置，因此 MAE 必须与 IoU/F1 同时报告。若另报像素二值 MAE `(FP+FN)/N`，使用不同字段 `pixel_binary_mae`，不与覆盖率 MAE 混称。现有评价器尚无上述 MAE 输出，拟以独立辅助模块扩展，不重定义已有四项指标。

### 9.2 时间与失败处理

- 主预测时间统一为 RGB 读取 + 特征提取 + 分类/阈值化；不包含人工标注读取、评价计算和文件写入。传统算法适配器遵循相同边界。
- 额外拆分 feature/predict 时间，模型冷加载、完整任务保存时间另外记录；旧应用批量耗时包含保存，不能直接与研究预测耗时比较。
- 训练元数据的旧 `training_seconds` 仅包围 `fit`，不等于读取、特征和保存的总时长。新协议分别记录 fit 与完整训练流水线时间。
- 所有组的逐图表必须保留同一组 ID、失败和错误原因。24 张中任意失败的候选不得成为最优候选；最终报告缺失结果不得静默按更容易的子集排名。
- 现有 `calibrate_candidates` 会记录失败数，但仍可能在剩余成功图上评选。新实验驱动层需增加“全部成功才可入选”门禁；本轮不改旧校准实现。
- 记录双空图数、成功/失败数、逐图值、宏平均、逐图标准差和 pooled 指标；需要不确定性估计时按图像或核实后的地块组重采样，不能把相关像素当独立样本。

## 10. 数据泄漏风险与测试冻结

### 10.1 已存在的测试暴露

本轮只读核查既有 CSV：`results/ews/test_evaluation/image_metrics.csv` 有四算法各 24 条 test 成功记录；`results/ews/rf_test_evaluation/image_metrics.csv` 有旧 RF 的 24 条 test 成功记录。还存在旧验证调参和五算法汇总目录。

这说明官方 test 已经使用过。不能宣称新方案拥有完全未知的独立测试集，也不能根据旧测试差错选择本次特征。后续的新结果应表述为“在既有 EWS 官方测试划分上，预先冻结配置后的最终比较”，并公开既往使用历史。更强的外部泛化证据需未来另行取得独立留出数据，本轮不下载。

### 10.2 拟实施的冻结机制

1. 为新研究建立唯一 `protocol_id`，默认命令只允许 train/validation。
2. 最终测试前生成锁定清单：全部 A–F 配置、特征 schema、模型及源码 SHA-256、训练抽样索引、清单/图像/标注摘要、选择过程、随机种子、依赖版本、线程配置、指标定义、失败和双空处理、计时范围。
3. 冻结记录保存真实时间，并将 A–D 历史参数与 E/F 新模型选择来源分开。未校验锁定摘要时拒绝 test。
4. 一次最终评价批次运行全部 A–F 相同的 24 张 test；预先声明的诊断/消融若要同时报告，也必须在锁定前列出，不能看完 test 后新增挑选。
5. 建立测试使用台账，同一协议不允许重复选参和重测。中断恢复仅补未完成的任务；若确定是软件缺陷，保留失败记录、修复差异和协议修订，不反复试到满意成绩。
6. 测试前不浏览新模型的测试预测图来改特征/阈值；最终评价之后的错误分析仅形成后续研究假设，不回头修改本次最终参数。
7. 所有新输出写入全新、拒绝覆盖的 `results/ews/rf_improvement/<protocol_id>/`，不复用 `rf_training`、`rf_test_evaluation` 或 `test_evaluation`。

现有评价器已有测试参数一致性检查，但冻结布尔值不能单独证明模型、数据和特征没有变更，也不能阻止多次运行测试脚本。新锁定摘要与台账是拟新增能力，不是当前已经具备的防护。

## 11. 预计新增文件及职责

以下仅列计划，本轮没有创建这些目录或代码。

| 预计路径 | 用途 |
| --- | --- |
| `src/wheat_phenotyping/leaf_segmentation/rf_improvement/schema.py` | 特征块、有序名称、版本、窗口和模型兼容契约。 |
| `src/wheat_phenotyping/leaf_segmentation/rf_improvement/features.py` | 独立提取 C/T/S，支持 8/11/14/17 维，避免改动旧七维模块。 |
| `src/wheat_phenotyping/leaf_segmentation/rf_improvement/sampling.py` | 只从 train 按图按类抽样，保存索引，供 E/F 共用。 |
| `src/wheat_phenotyping/leaf_segmentation/rf_improvement/model.py` | 模型与 schema/数据摘要的保存、加载、校验。 |
| `src/wheat_phenotyping/leaf_segmentation/rf_improvement/inference.py` | 整图/条带预测与可变 halo，统一 BinaryMask 输出；不直接接入网页。 |
| `src/wheat_phenotyping/evaluation/coverage_error.py` | 覆盖率 MAE 的独立计算，不改现有四项指标含义。 |
| `configs/rf_improvement/feature_profiles.json` | 特征组合和显式窗口参数。 |
| `configs/rf_improvement/experiment_plan.json` | A–F 协议、数据版本、选择指标、主种子、冻结规则。 |
| `configs/rf_improvement/search_space.json` | 有限搜索范围、候选顺序和预算。 |
| `scripts/train_rf_improvement.py` | 新 RF 的 train-only 训练命令。 |
| `scripts/validate_rf_improvement.py` | 验证比较、消融、候选成功门禁和锁定配置。 |
| `scripts/evaluate_rf_improvement.py` | 锁定后的单次最终测试、摘要校验和台账。 |
| `scripts/compare_rf_improvement.py` | 新研究逐图、汇总、消融、耗时 CSV/JSON/SVG；保留历史结果。 |
| `tests/unit/test_rf_improvement_features.py` | 公式、维数、顺序、数值范围、颜色周期、边缘和异常输入。 |
| `tests/unit/test_rf_improvement_sampling.py` | 划分隔离、共同抽样索引、种子复现及空类处理。 |
| `tests/unit/test_rf_improvement_inference.py` | 整图/分块一致性、模型 schema 不匹配拒绝、掩膜格式。 |
| `tests/unit/test_rf_improvement_protocol.py` | test 门禁、摘要变化拒绝、覆盖拒绝、失败候选不得入选。 |
| `tests/unit/test_coverage_error.py` | 手工可核算的覆盖率误差、单位、空图和无效输入。 |

将来每次实验至少保存：`experiment_config.json`、`dataset_snapshot.json`、`feature_schema.json`、训练抽样索引、训练元数据、模型摘要、验证候选 CSV、逐图评价 CSV、汇总 CSV、比较 SVG、真实运行日志及冻结记录。不存在的成绩字段留空或不生成，不能填入示例成绩。

## 12. 分阶段实施与验收

| 阶段 | 工作 | 进入下一步的标准 |
| --- | --- | --- |
| 1，下一步 | 实现独立特征 schema 与 C/T/S 提取器 | 8/11/14/17 维、公式/顺序/范围正确；灰色和色相周期、1×1/小图、尺寸/缓冲异常、最近边界、条带接缝有测试；旧七维实现和模型不变。 |
| 2 | train-only 抽样、模型契约和协议门禁 | train/validation/test 严格区分，抽样索引复现，跨图/组检查，模型特征不符立即报错，test 默认禁用。 |
| 3 | 训练 E/F 并开展有限验证与消融 | 全部配置/失败均记录，验证 24 图齐全，输出来自实算；不读取 test 预测/成绩选参；模型输出拒绝覆盖。 |
| 4 | 完成锁定，执行一次最终 A–F 比较 | 相同 24 图和标注版本、统一指标和时间口径，MAE 单位明确，保留空图/失败，历史目录不变。 |
| 5，后续单独安排 | RF 网页接入 | 科研模型版本明确后，另做 API/前端适配、错误处理和真实上传验证；不在本轮开展。 |

已有 RF 相关单元测试文件为 `test_rf_features.py`、`test_photo_app.py`、`test_rf_experiments.py`，分别覆盖七维特征/输入检查、应用推理/批量输出、汇总样本一致性等。它们尚不能代替新特征 schema、可变 halo 和协议门禁测试。

本轮只审阅这些测试代码，没有执行 pytest、构建前端或报告新的通过数量，也没有把测试夹具中的数值当真实实验成绩。

## 13. 本轮交付边界

仅新增本报告。只读模型加载成功、190 对数据逐像素检查通过，均属于已有产物检查，不是新模型训练或精度评价。现有算法、网页、价格/收益模块、EWS 原始数据与历史实验成绩保持原样。

完成前比对检查前后的保护快照：`src`、`scripts`、`configs`、`backend`、`frontend/src`、`results/ews` 的文件数与内容摘要一致；EWS 原始/处理数据目录的文件数、路径、大小和修改时间摘要一致。快照排除 `__pycache__`；本轮 Python 检查使用 `-B`。

下一步最应该实现的具体功能：**独立、可配置、带版本校验的 RF 改进特征提取器**。先固定 8/11/14/17 维契约，完成颜色公式和整图/条带一致性单元测试，确认旧七维模型兼容路径不受影响，再实施训练与验证流程。
