# 公开小麦生育期预训练模型审计

审计日期：2026-11-14  
范围：只检查公开仓库、模型卡、权重说明和许可证；未下载大型权重、未训练、未修改麦视通代码/网页。

## 1. 最重要的结论

本轮没有找到一个同时满足以下条件的公开模型：

- 已训练好的小麦生育期分类头；
- 可直接下载的最终 checkpoint；
- 独立单张 RGB 图片推理入口；
- 明确的阶段标签定义；
- 可以直接在当前 Windows/Python 3.12 环境运行。

因此当前不能把任何公开项目直接接入 FastAPI 作为“单张图片生育期识别模型”，也不能伪造或用随机权重代替。

如果必须选一个研究优先级，推荐 **CGIAR Wheat Growth Stage Challenge 项目**，因为它的任务目标就是单张图片输出 1–7 生长阶段；但它当前仍不能作为已经可部署的预训练模型。它需要确认/取得最终任务 checkpoint，或使用其公开训练方案重新微调。

## 2. 项目比较

| 项目 | 任务匹配 | 完整分类权重 | 独立推理 | RGB 单图 | 当前判断 |
| --- | --- | --- | --- | --- | --- |
| CGIAR Wheat Growth Stage | 直接面向 1–7 阶段 | 未在仓库确认 | 主要是 Notebook/训练方案 | 是 | 最接近，但不能直接部署 |
| FoMo4Wheat | 有生育期 benchmark | 只有基础 backbone 权重 | 有 embedding/评估代码 | 是 | 需要分类头 |
| Wheat-KGCA | 8 类田间 RGB 阶段 | README 明确 checkpoints 外置 | 有训练/实验脚本 | 是 | checkpoint 不在仓库 |
| GSP-AI | 小麦生育期/开花相关 | 有 release 资产线索 | 依赖无人机/地块流程 | 不是普通单图手机模型 | 不适合当前入口 |
| SPROUT | 器官分割/计数为主 | 基础模型权重 | 有分割推理 | RGB | 不是阶段分类器 |

## 3. CGIAR Wheat Growth Stage Challenge

官方仓库描述的目标是：输入农户上传的小麦图像，输出 1–7 生长阶段，图像会自动裁剪为田间区域。[CGIAR 项目说明](https://github.com/Oraegbuayomide10/CGIAR-Wheat-Growth-Stage-Challenge-by-CGIAR-Platform-for-Big-Data-in-Agriculture)

其方法使用 ImageNet 预训练的 ResNet、VGG16_bn、DenseNet 等模型，并在竞赛数据集上 fine-tune；这说明它们是“预训练 backbone + 任务训练”，不是下载 backbone 后立即得到小麦阶段分类器。[CGIAR README](https://github.com/Oraegbuayomide10/CGIAR-Wheat-Growth-Stage-Challenge-by-CGIAR-Platform-for-Big-Data-in-Agriculture/blob/main/README.md)

另一个公开复现仓库使用 EfficientNet B2/B3 ensemble，报告 RMSE 0.4087，并说明模型先冻结编码器训练 70 epochs，再解冻训练 40 epochs；仓库文件列表仍主要是 Notebook、资源和 README，没有可核验的最终模型文件。[CGIAR 复现仓库](https://github.com/RsTaK/CGIAR-Wheat-Growth-Stage-Challenge-by-CGIAR)

审计结论：

- 完整权重：未确认。
- 独立图片推理：没有稳定的独立 CLI/API，主要依赖 Notebook 和配置。
- Windows/Python 3.12：未得到官方承诺；fastai/旧版深度学习依赖需要单独适配。
- 许可证：仓库 MIT，但数据集和标签来源仍需按 Zindi/CGIAR 条款单独核验。
- 公开成绩：有 RMSE 0.4087 的仓库声明，但不能当作麦视通手机图片的准确率。

它是本轮最接近目标的项目，但目前不是“可直接加载权重推理”的交付物。

## 4. FoMo4Wheat 生育期 benchmark

FoMo4Wheat 官方 benchmark 文档说明其生育期任务使用 WGSP 数据集：3,353 张 RGB 小麦冠层图像，来自中国、英国和美国，覆盖 6 个关键阶段：tillering、jointing、booting、anthesis、grain filling、maturity；训练 671 张，测试 2,682 张。[FoMo4Wheat 生育期 benchmark](https://huggingface.co/PheniX-Lab/FoMo4Wheat/blob/main/Benchmark/Classification-Wheat%20Growth%20Stage/readme.txt)

但 Hugging Face 目录该任务目前只有 `readme.txt`，没有可下载的生育期分类头或任务 checkpoint。[benchmark 文件列表](https://huggingface.co/PheniX-Lab/FoMo4Wheat/tree/main/Benchmark/Classification-Wheat%20Growth%20Stage)

麦视通已经接入 FoMo4Wheat ViT-B/14 基础权重并能提取 768 维特征，但这仍不是生育期分类器。要得到阶段输出，还需要：

1. 任务分类头；
2. 类别映射和标签定义；
3. 训练/验证/测试协议；
4. WGSP 数据或合法授权数据；
5. 中国手机照片域外验证。

结论：可作为未来轻量分类头的 backbone，不是当前可直接使用的完整模型。

## 5. Wheat-KGCA

Wheat-KGCA 是 8 类田间 RGB 生育期识别项目，包含农学规则、视觉模型、VLM 语义信息和 CAM 分析。其 README 明确指出 checkpoints 位于仓库外部，仅提供 checkpoint 目录说明；因此不能从仓库直接下载最终权重。[Wheat-KGCA README](https://github.com/zhanghaodong99/Wheat-KGCA/blob/main/wheat-kgca-main/README.md)

审计结论：

- 有完整研究代码和阶段定义方向；
- 没有仓库内可验证的完整 checkpoint；
- 依赖训练输出和较复杂的实验环境；
- 不能直接接入当前 FastAPI；
- 其 8 类标签也不能直接替换当前麦视通尚未确定的 Zadoks 映射。

## 6. GSP-AI 与 Zadoks 相关项目

GSP-AI 是中国/英国/美国三方田间试验相关的生育期预测项目，公开 release 中包含代码、测试数据和模型资产线索，但其流程围绕无人机数据、plot-level 采样和环境数据，并不是当前“用户上传一张普通 RGB 手机照片”的独立模型。[GSP-AI 仓库说明](https://github.com/The-Zhou-Lab/GSP-AI)、[GSP-AI release](https://github.com/The-Zhou-Lab/GSP-AI/releases)

Zadoks 体系本身是农学阶段编码标准，不是一个现成的视觉模型。Zadoks 是两位编码，第一位表示主生育阶段，第二位表示阶段细分；例如拔节、孕穗、抽穗、开花和籽粒发育都需要按可见器官和阶段定义标注。[Zadoks 阶段说明](https://extension.umn.edu/agriculture/crop-production/small-grains/spring-wheat-growth-and-development-guide)

因此：公开项目的“1–7 阶段”“6 阶段”“8 类阶段”和 Zadoks 代码不能直接混合，必须先建立标签映射表。

## 7. 其他相关项目

SPROUT 支持小麦器官分割和麦穗计数，有公开基础权重和推理代码，但任务不是生育期分类，不能当作阶段模型。[SPROUT](https://github.com/UTokyo-FieldPhenomics-Lab/SPROUT)

FoMo4Wheat 的基础权重可作为 embedding 提取器，但官方任务 benchmark 没有公开生育期分类头。本项目现有 768 维特征提取结果不能直接变成阶段预测。

## 8. 与麦视通的兼容性

当前最现实的 FastAPI 设计应是“模型状态接口”，而不是直接宣称已完成阶段识别：

```text
GET  /api/v1/growth-stage/models
GET  /api/v1/growth-stage/health
POST /api/v1/growth-stage/predict
```

只有在模型 checkpoint、标签映射、预处理和验证结果全部锁定后，`POST` 才能启用。响应至少记录：

- `model_id`
- `checkpoint_sha256`
- 标签体系（例如 CGIAR 1–7、WGSP 6 类或 Zadoks 映射）
- 预测类别和置信度
- 输入预处理版本
- 训练数据域
- “手机照片域外验证状态”

当前不能把 FoMo4Wheat embedding、EWS 分割掩膜或长势 V1 覆盖率直接解释为生育期类别。

## 9. 首选模型建议

**唯一首选：CGIAR Wheat Growth Stage Challenge 项目。**

原因：

1. 任务目标就是单张 RGB 图片的 1–7 生长阶段识别；
2. 输入形态与麦视通单图入口最接近；
3. 公开代码和训练流程相对容易理解；
4. 可作为后续阶段模型的研究基线。

但必须明确：**当前不能直接接入 FastAPI**。原因是没有在仓库中确认最终任务 checkpoint、稳定推理入口和完整部署配置。下一步应优先查找官方/竞赛平台是否仍能取得最终 checkpoint；如果无法取得，才评估使用其数据和 ImageNet/FoMo backbone 进行受控微调。

## 10. 最终结论

- 当前没有确认到可直接加载权重并在 Windows/Python 3.12 上运行的完整小麦生育期模型。
- FoMo4Wheat 只有基础 backbone 权重，不能冒充阶段分类器。
- Wheat-KGCA 有完整研究方向，但 checkpoint 外置。
- SPROUT 是器官分割/计数模型，不是阶段分类模型。
- CGIAR 项目最贴近业务目标，但目前仍缺少可核验的最终部署权重。
- 本轮没有训练、下载大型权重、修改项目或生成生育期预测结果。
