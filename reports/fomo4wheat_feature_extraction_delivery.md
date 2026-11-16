# FoMo4Wheat ViT-B/14 特征提取交付报告

日期：2026-11-14。范围：建立独立环境、下载官方 Base 权重、完成单张 EWS RGB 图片特征提取；未训练、未接入网页、未修改现有算法或长势 V1。

## 官方实现核对

已克隆官方参考源码到 `.external/FoMo4Wheat/`，并克隆其 DINOv2 依赖到 `.external/dinov2/`。官方配置要求 Python 3.11、PyTorch 2.5.1、CUDA 12.1 和 torchvision；本机无 Python 3.11/Conda，因此使用独立 Python 3.12 环境验证。[官方配置](https://raw.githubusercontent.com/PheniX-Lab/FoMo4Wheat/main/conda.yaml)

官方 ViT-B/14 定义为 patch size 14、embed dimension 768、12 层、12 heads。官方分类评估预处理为 Resize 256、CenterCrop 224、ToTensor、ImageNet mean/std 归一化；本适配器复用了这一确定性预处理。[官方 README](https://raw.githubusercontent.com/PheniX-Lab/FoMo4Wheat/main/README.md)

## 独立环境

新增 `.venv-fomo`，未修改现有 `.venv`。实际安装：Python 3.12.10；torch 2.5.1+cu121；torchvision 0.20.1+cu121；dinov2 0.0.1；omegaconf 2.4.0；torchmetrics 1.9.0；fvcore 0.1.5.post20221221；iopath 0.1.10；numpy 2.5.4；Pillow 13.0.0。

## 权重

文件：`models/pretrained/fomo4wheat/FoMo4Wheat_base.pth`。官方地址：`https://huggingface.co/PheniX-Lab/FoMo4Wheat/resolve/main/weight/FoMo4Wheat_base.pth`。文件大小：346,484,753 bytes。SHA-256：`5d996c01a8b99f58bf136d94abf65a54f86e3fd51572d1c1c121dbc7ade3dbcf`。官方 ETag：`"428a4bdffa46ecf0f9a262df5539a2411d7a1f3d33e0d42950c052450e10c98f"`。

权重实际加载为官方序列化 `DinoVisionTransformer` 对象，不是随机初始化权重，也不是本项目训练结果。

## 新增文件

- `src/wheat_phenotyping/foundation_models/__init__.py`
- `src/wheat_phenotyping/foundation_models/fomo4wheat/__init__.py`
- `src/wheat_phenotyping/foundation_models/fomo4wheat/extractor.py`
- `tests/unit/test_fomo4wheat.py`
- `models/pretrained/fomo4wheat/FoMo4Wheat_base.pth`
- `.venv-fomo/`、`.external/FoMo4Wheat/`、`.external/dinov2/`

适配器支持 JPG/JPEG/PNG、CPU/CUDA/auto，检查权重 SHA-256、模型维度、输出 shape、NaN/无穷值和图片异常，并返回特征、维度、模型版本、设备、原图尺寸、预处理标识、权重摘要和耗时。

## 真实 EWS 图片验证

图片：`data/raw/ews/train/images/FPWW0220011_RGB1_20180316_100219_6.png`。

CPU 结果：模型 `FoMo4Wheat ViT-B/14 base`；设备 `cpu`；特征维度 `768`；有限值检查 `true`；推理耗时 `0.1410769001` 秒；最小值 `-3.6236775`；最大值 `3.7743268`；均值 `0.00145998`。

相同图片重复运行结果完全一致：`same=true`，embedding SHA-256 为 `aef1ac63cab446f3c2ad794ce112361728b50b96db37b5546a8c49eb2ef48533`。该摘要只用于重复性核对，不代表准确率或预测成绩。

## CUDA/GPU 结果

PyTorch 检测到 RTX 5060 Laptop GPU、CUDA runtime 12.1，`torch.cuda.is_available()` 为 True。但实际 GPU 推理失败：`CUDA error: no kernel image is available for execution on the device`。原因是当前 PyTorch wheel 支持列表不包含 RTX 5060 的 `sm_120`。因此 CUDA 可见，但 GPU FoMo 推理未成功；CPU 推理成功。没有把 CUDA 可见性误报为 GPU 成功，也没有使用随机权重替代。

## 测试

FoMo 独立测试：`4 passed in 9.30s`。覆盖官方预处理 shape/dtype、权重缺失错误、契约常量和输入检查。完整真实模型验证使用上面的 EWS 图片完成。

## 功能边界与下一步

当前交付只实现“单张 RGB 图片 → 768 维小麦视觉 embedding”，不输出长势等级、生育期、器官类别、未来 7/15/30 天趋势、产量或价格。FoMo Base 是基础视觉骨干，不包含这些任务头。

接入长势 V1 的下一步应是：固定 embedding schema 和权重哈希，选择一个有真实标签的生育期或器官任务，在训练集训练轻量任务头、验证集选参、测试集冻结；验证完成后再注册到 FastAPI/Vue。现有 ExG、HSV、Otsu、Fusion 和长势 V1 保持不变。
