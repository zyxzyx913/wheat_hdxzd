# 小麦生育期智能识别 V1 交付报告

交付时间：2026-11-14

## 1. 数据质量

CGIAR 图片已经解压并完成质量核验：

- JPEG 图片：14,253 张
- 可解码：14,253 张
- 损坏：0 张
- RGB：14,251 张
- 灰度 L：2 张，模型预处理转换为 RGB
- 内容重复组：0
- 训练标签：10,695 条
- 测试图片 UID：3,558 个
- 训练 UID 缺图：0
- 训练/测试 UID 交集：0
- 测试提交文件标签：全部为占位 0，未计算测试准确率

核验清单：`data/processed/growth_stage/verified_manifest.csv`。

## 2. 模型和训练方法

使用冻结的 FoMo4Wheat ViT-B/14 base CLS 特征：

- 特征维度：768
- 预处理：官方 Resize 256、CenterCrop 224、ImageNet 归一化
- 特征设备：CPU
- GPU：RTX 5060 当前 CUDA wheel 未成功执行，未宣称 GPU 可用
- 特征缓存：`results/growth_stage_initial/fomo_features_subset.npz`

轻量分类器比较：

- Logistic Regression
- SVM RBF
- Random Forest

训练使用每个阶段 100 张、共 700 张的固定随机种子子集；560 张训练、140 张验证，按类别分层切分。当前训练 CSV 没有可靠地块/农户字段，因此不能声称完成地块独立验证。

按验证集 Macro-F1 选择 SVM RBF。测试集没有真实标签，未参与调参或准确率计算。

## 3. 真实评价成绩

| 模型 | Accuracy | Macro-F1 | Weighted-F1 |
|---|---:|---:|---:|
| Logistic Regression | 0.3786 | 0.3820 | 0.3820 |
| SVM RBF | **0.4214** | **0.4136** | 0.4136 |
| Random Forest | 0.3286 | 0.3234 | 0.3234 |

SVM RBF 各阶段验证 F1：

| 阶段 | Precision | Recall | F1 |
|---:|---:|---:|---:|
| 1 | 0.3125 | 0.2500 | 0.2778 |
| 2 | 0.2500 | 0.2000 | 0.2222 |
| 3 | 0.7391 | 0.8500 | 0.7907 |
| 4 | 0.5385 | 0.3500 | 0.4242 |
| 5 | 0.3000 | 0.3000 | 0.3000 |
| 6 | 0.3226 | 0.5000 | 0.3922 |
| 7 | 0.4762 | 0.5000 | 0.4878 |

这些是固定子集验证结果，不是完整 CGIAR 测试集成绩，也不是中国品种或手机照片准确率。

## 4. FastAPI 接口

已有接口：

```text
POST /api/growth-stage/predict
```

返回：

- 预测生育期
- 七阶段概率
- 最高概率
- 模型版本
- 特征提取和总推理耗时
- 设备
- 标签来源和适用范围限制

模型文件缺失、FoMo 加载失败或环境不兼容时返回明确的 503，不返回随机概率。

## 5. 网页接入

长势分析页已经同时展示：

- 当前长势综合分和等级
- 覆盖率、绿色程度、均匀度
- 图像可靠性、优势和改善建议
- 原图、掩膜、叠加图
- 当前生育期和七阶段概率

生育期与长势等级并列展示，不会把生育期直接解释成长势好坏。生育期模型使用当前 CGIAR 子集初步模型，并在页面保留适用范围提示。

## 6. 真实图片验证

已使用 EWS 真实 PNG 通过本机 FastAPI/Uvicorn 进行单图 HTTP 冒烟：

- `/api/growth/analyze` 返回 HTTP 200
- 生育期模型状态：`succeeded`
- 返回七阶段概率和阶段名称
- 同一响应包含长势 V1.1 结果
- 历史记录查询返回 HTTP 200

该验证是接口闭环测试，不是新的测试集精度实验。

## 7. 测试结果

- 全部 Python 单元测试和 FastAPI 测试：187 passed，3 skipped，4 warnings
- 生育期接口测试：通过
- V2.0 长势和历史接口测试：通过
- 异常图片测试：通过
- 前端 `npm run build`：通过

## 8. 未解决问题

1. 当前模型是每类 100 张的初步子集实验，尚未完成完整训练集特征缓存。
2. 缺少可靠地块/农户/拍摄批次字段，无法排除地块级泄漏。
3. `label_quality` 数值代码缺少完整来源字典，专家/农户分组只能保留数值代码。
4. 没有官方测试集真实标签，不能计算官方测试成绩。
5. 尚未验证中国品种、地区和手机图片域迁移。
6. 当前生育期识别不用于校准 V1.1 长势评分。
7. 未来 7/15/30 天生长预测模型尚未建立。

## 9. 启动方式

后端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
$env:TEMP="$PWD\.test-tmp"
$env:TMP=$env:TEMP
$env:PYTHONPATH="$PWD\.venv-fomo\Lib\site-packages;$PWD\.external\dinov2;$PWD\src"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm.cmd run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:5173/#/growth-analysis`，上传一张小麦图片即可同时查看当前长势初评和生育期识别结果。
