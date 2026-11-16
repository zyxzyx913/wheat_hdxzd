# 麦视通公开预训练小麦模型兼容性评估

检查日期：2026-11-14  
范围：只读检查本机环境和四个公开项目的仓库/README/模型卡。未安装依赖、未下载权重、未运行模型、未修改项目代码或网页。

## 1. 本机环境

| 项目 | 检查结果 |
| --- | --- |
| 操作系统 | Windows 11（根据项目开发环境） |
| Python | 3.12.10，路径 `C:\Users\89885\AppData\Local\Programs\Python\Python312\python.exe` |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU，显存约 8,151 MiB，驱动 592.01 |
| CUDA Toolkit | `nvcc` 不在 PATH，未确认本机 CUDA Toolkit |
| PyTorch | 当前 `.venv` 未安装 |
| torchvision | 未安装 |
| transformers | 未安装 |
| OpenCV | 未安装 |
| ultralytics | 未安装 |
| 当前项目依赖 | Pillow、NumPy、SciPy、scikit-learn、pytest；适合现有传统算法，不是深度学习环境 |

结论：硬件上可以尝试小型 RGB 模型，但当前环境不具备直接运行四个深度学习项目的依赖。RTX 5060 Laptop 约 8 GB 显存不适合 FoMo4Wheat Giant（约 1.1B 参数）或 SPROUT-L（361M 参数）直接进行高分辨率训练；推理仍需实测显存。Windows 兼容性也不能仅由“使用 Python”推断，必须按各项目环境文件单独验证。

## 2. 项目逐项审查

### 2.1 FoMo4Wheat

官方仓库称其为面向小麦图像的基础模型，支持图像分类、检测、计数和像素级分割等下游任务；仓库代码和权重采用 MIT License。[FoMo4Wheat 仓库](https://github.com/PheniX-Lab/FoMo4Wheat)

官方 README 的关键事实：

- 训练/评价环境基于 PyTorch 2.5.1，README 明确要求 Linux 和多项第三方依赖。
- 提供三个基础权重：ViT-B/14 约 86M、ViT-L/14 约 300M、ViT-G/14 约 1.1B 参数。
- 权重位于 Hugging Face；当前可见基础权重文件约 6.11 GB 级别。[FoMo4Wheat README](https://raw.githubusercontent.com/PheniX-Lab/FoMo4Wheat/main/README.md)
- README 的任务列表包含小麦生育期分类、疾病分类、麦穗检测、叶尖计数和小麦器官分割，但这描述的是 benchmark/下游任务，不等于基础权重本身已经包含可直接调用的任务头。
- 完整 ImAg4Wheat 数据集尚未在论文正式发表前完全公开，不能把预训练数据当作本地可用训练集。

兼容性判断：

- 源码：相对完整，包含模型、训练和评价目录。
- 预训练权重：有，下载地址有效，但体积大。
- 独立推理：可以提取 embedding/特征；要得到生育期等级、器官掩膜或计数，仍需对应任务头、任务 checkpoint 或微调配置。
- 输入：RGB 图像为主，适合当前图片入口作为特征提取器候选。
- Windows：README 偏向 Linux/Conda/多 GPU；Windows 原生未被官方承诺，可能需要 WSL2。
- FastAPI：可通过独立 Python 服务封装，但必须先固定预处理、输入尺寸、权重和任务头。

结论：**不是直接可用的长势预测模型，而是最有价值的 wheat-specific 特征骨干。**

### 2.2 SPROUT

SPROUT 是多作物扩散预训练视觉基础模型，公开说明支持器官分割、作物-杂草解析、单目深度和产量器官计数；代码、下游训练/推理脚本和 S/B/L 预训练 checkpoint 均公开。[SPROUT 仓库](https://github.com/UTokyo-FieldPhenomics-Lab/SPROUT)

官方 README 的关键事实：

- 预训练数据为 2.6M 开放田间图像。
- 任务覆盖 wheat organ segmentation 和 wheat spike counting。
- 提供 SPROUT-S 51M、SPROUT-B 112M、SPROUT-L 361M 权重，下载地址为 Google Drive。
- 提供 `segmentation_ms_inference.py`、`regression_inference.py` 等推理脚本。
- 分割数据要求 RGB 图像和同名 mask，训练图像要求方形；回归任务要求 `train.txt` 等图像-数值标注文件。
- README 要求参考 DODA 环境，训练脚本有硬编码超参数，任务类别数、权重和配置需要手动修改。
- 许可证为 Apache-2.0。[SPROUT README](https://raw.githubusercontent.com/UTokyo-FieldPhenomics-Lab/SPROUT/main/README.md)

兼容性判断：

- 源码和预训练权重：有。
- 独立推理：有脚本，但推理仍需要配置模型、权重、任务类别和输入数据目录。
- 是否零样本完成小麦器官识别：不能直接确认。基础 checkpoint 与任务输出头/任务微调 checkpoint 必须区分。
- 输入：支持普通 RGB 图像，但分割/回归的输入组织和尺寸有明确要求。
- Windows：未提供 Windows 原生安装承诺；DODA、扩散模型依赖和 CUDA 组合更适合 Linux/WSL2。
- FastAPI：可以封装，但模型冷启动、显存占用和同步推理时间需要单独处理。

结论：**最适合研究器官分割/麦穗计数方向，但不是当前单图长势等级的即插即用模型。**

### 2.3 CGIAR Wheat Growth Stage Challenge

该项目的目标与麦视通当前需求最接近：根据一张小麦图像输出 1–7 的生长阶段。仓库说明图像会先裁剪，并用 ResNet、VGG16_bn、DenseNet 等预训练架构组成 ensemble；这些基础模型在数据集上进行了 fine-tune。[CGIAR 项目](https://github.com/Oraegbuayomide10/CGIAR-Wheat-Growth-Stage-Challenge-by-CGIAR-Platform-for-Big-Data-in-Agriculture)

实际限制：

- 仓库主体是一个 Jupyter Notebook，历史记录显示源码规模小。
- “预训练模型”指 ImageNet 等 backbone 的初始化；项目说明的是 fine-tune 后的任务模型。
- 未在仓库说明中确认有可下载的最终 ensemble checkpoint、稳定版本的独立 inference CLI 或 FastAPI 入口。
- 需要其训练数据、标签定义和训练过程才能重建任务模型。
- 任务标签 1–7 的农学含义、跨地区泛化和中国手机照片适用性不能直接假定。
- Google Colab GPU 是其开发背景，不等于 Windows 本地直接可运行。

结论：**任务方向最匹配，但不能作为“已有可直接使用权重”的候选。** 它更适合作为长势等级数据/标签设计参考；若无最终 checkpoint，仍需训练或微调。

### 2.4 WheatPheno

WheatPheno 是 UAV/栅格数据的小麦表型工具箱，支持特征提取、模型训练、空间推理和本地 Streamlit 界面；源码 MIT，模型与示例数据 CC BY 4.0。[WheatPheno 仓库](https://github.com/chaoli-lgtm/WheatPheno)

官方说明的固定模型：

- 株高：基于 CHM PCT95，单位 cm。
- 地上生物量：Extra Trees，200 棵树，需要 72 个输入预测变量，单位 g m⁻²。
- 籽粒产量：Extra Trees，200 棵树，需要 72 个输入预测变量，单位 g m⁻²。
- 输入是 UAV/栅格派生特征、DSM/DTM、反射率等，不是普通手机 RGB 照片。
- 提供模型和元数据哈希，支持 `wheatpheno predict`；Python 3.12 和 Windows 虽可按 CLI 方式尝试，但上游栅格/摄影测量输入仍需准备。
- 官方报告的结果属于其 plot-level UAV 特征评估，不能直接解释为手机图片结果。

结论：**适合未来 UAV 产量/生物量研究，不适合当前单张 RGB 上传入口。**

## 3. 按任务分类

| 任务 | FoMo4Wheat | SPROUT | CGIAR Growth Stage | WheatPheno |
| --- | --- | --- | --- | --- |
| 当前长势/生育阶段 | 只有基础骨干；需任务头 | 不是现成阶段分类器 | 目标最匹配，但 checkpoint 未确认 | 不适合 |
| 叶片/茎秆/麦穗识别 | benchmark/下游方向；需任务模型 | 器官分割和麦穗计数方向最强；需确认任务权重 | 不支持器官分割 | 不支持手机器官分割 |
| 覆盖率/表型指标 | 可作为特征骨干，需适配头 | 可用于器官/分割后统计 | 只输出阶段，不能直接给覆盖率 | 可输出 UAV 特征，但非手机 RGB |
| 未来 7/15/30 天生长 | 不支持直接预测 | 不支持直接预测；需要时序模型 | 单图阶段分类，不是未来预测 | 非时序单图预测模型 |
| 最终产量 | 需产量回归头和数据 | 不是产量回归模型 | 不支持 | UAV 特征产量模型，不能直接用手机图 |

四个项目都不能被表述为“上传一张照片即可预测未来 7/15/30 天”。这类预测需要时间序列、地块/日期标签和经验证的未来目标。

## 4. 对当前麦视通的兼容性

当前项目的深度学习环境为空：PyTorch、torchvision、transformers、OpenCV、ultralytics 都未安装。当前 FastAPI 已有真实 RGB 上传和四种传统分割流程，但没有深度模型加载器、GPU worker、模型版本注册或任务 checkpoint 管理。

接入任何候选模型前都需要独立适配层：

```text
backend/app/model_registry/
├── manifest.json              # 模型名、权重 SHA-256、许可证、任务头、输入规范
├── fomo4wheat_adapter.py
├── sprout_adapter.py
├── cgiar_stage_adapter.py
└── wheatpheno_adapter.py
```

FastAPI 未来接口建议：

```text
GET  /api/v1/models
GET  /api/v1/models/{model_id}/health
POST /api/v1/models/{model_id}/predict
```

每个响应必须记录：模型 ID、权重哈希、输入预处理、任务头、输出标签定义、置信度/不确定性、许可证和适用域。模型推理应放到线程池或独立 worker，避免阻塞 FastAPI 事件循环。

Vue 页面只在模型清单中存在“已下载、已校验、已配置任务头、已完成本地冒烟测试”的模型后显示可用；否则显示“模型需准备/待验证”，不能显示虚构结果。

## 5. 四个项目的可用性分级

### 可以直接使用

**本轮没有确认任何一个项目可以在当前环境中直接运行。** 原因是本机没有 PyTorch，且 CGIAR 项目最终任务 checkpoint 未确认。

### 少量适配后可用

- **FoMo4Wheat Base**：下载权重、安装 PyTorch/项目依赖、实现输入预处理和 embedding 推理适配后，可以作为 wheat-specific 特征提取器。仍需任务头才能输出阶段/器官/产量。
- **SPROUT-S**：下载 checkpoint、安装 DODA/项目依赖、确认任务权重/类别配置后，可能适合作为分割/计数研究适配器。不是当前页面的即插即用长势模型。

### 不适合当前目标

- **CGIAR Growth Stage**：最接近长势阶段，但最终任务权重和独立部署入口不足，不能保证零训练使用。
- **WheatPheno**：输入依赖 UAV/DSM/反射率特征，无法直接接受普通手机 RGB 图片。

## 6. 推荐的唯一首选模型

**首选：FoMo4Wheat ViT-B/14 基础权重，作为麦视通的 wheat-specific RGB 特征提取器。**

原因：

1. 明确提供公开预训练权重和 MIT 许可证。
2. 目标就是小麦图像，和当前 RGB 入口最一致。
3. Base 规模约 86M，最接近 RTX 5060 Laptop 8 GB 显存的可行范围。
4. 可以先不改变现有 ExG/HSV/Otsu/Fusion 和长势 V1，仅增加离线 embedding 提取与模型登记。
5. 后续可以在已有 EWS、公开小麦阶段数据或中国手机数据上分别训练轻量任务头，保持基础模型与任务标签清晰分离。

重要限制：FoMo4Wheat Base **不是已经训练好的长势等级、未来生长预测或产量预测模型**。它只能作为特征骨干；任何阶段/器官/产量输出都需要对应任务头或微调，并必须重新验证。

## 7. 不选择其他三个作为首选的原因

- SPROUT 的器官分割能力更贴近叶/茎/穗研究，但其扩散模型、DODA 依赖、Google Drive 权重和任务配置带来更高集成复杂度；应作为第二个研究候选。
- CGIAR 项目直接面向阶段分类，但目前更像竞赛 notebook/训练方案，而不是带可验证最终 checkpoint 的部署包；不能把 ImageNet backbone 当成已完成的阶段模型。
- WheatPheno 的固定模型输入是 UAV/栅格特征，不是手机 RGB，接入当前单图 Web 入口会改变输入模态和研究问题。

## 8. 后续实施顺序

1. 只为 FoMo4Wheat Base 建立独立实验环境，不污染当前 `.venv`。
2. 下载并记录权重 SHA-256、许可证、来源和版本；先做本地单图 embedding 冒烟测试。
3. 建立 `model_registry` 和统一 RGB 预处理适配器。
4. 在不接入网页的情况下，验证同一输入重复推理一致性、CPU/GPU 输出差异和显存占用。
5. 选择一个有真实标签的下游任务头：优先生育期分类或器官分割，而不是未来生长预测。
6. 仅在独立验证集完成后，再接入 FastAPI；Vue 只显示真实可用状态。
7. SPROUT 作为后续器官分割候选；WheatPheno 仅在未来引入 UAV/DSM 时评估。

## 9. 本轮边界

本轮没有安装 PyTorch/CUDA、没有下载 FoMo4Wheat/SPROUT 权重、没有克隆四个项目、没有运行模型、没有修改麦视通代码或网页，也没有产生任何预测结果。
