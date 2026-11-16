# GSP-AI 依赖与模型加载检查报告

## 1. 结论

本轮完成了官方 Notebook 的完整静态检查、模型 ZIP/推理 ZIP 完整性验证、Python 独立环境检查和一次官方 PyPI 安装尝试。

**SavedModel 尚未成功加载，官方示例尚未执行。** 原因是当前系统网络代理拒绝 PyPI 连接；独立环境中的 TensorFlow、pandas、scikit-image、ExifRead 和 openpyxl 均未安装。

没有修改主项目 `.venv`，没有修改 GSP-AI 原始权重，也没有伪造推理结果。

## 2. 独立环境状态

环境目录：

```text
D:\Desktop\wheat\source-code\wheat-phenotyping\.venv-gsp-ai
```

| 项目 | 实际结果 |
|---|---|
| Python | 3.12.10 |
| 架构 | Windows 11 AMD64，64 位 |
| pip | 25.0.1，已通过 ensurepip 初始化 |
| TensorFlow | 未安装 |
| pandas | 未安装 |
| scikit-image | 未安装 |
| ExifRead | 未安装 |
| openpyxl | 未安装 |

检查到的代理和 pip 配置没有输出认证令牌；当前环境变量中没有可用的 `HTTP_PROXY`、`HTTPS_PROXY`、`PIP_INDEX_URL` 或 `PIP_EXTRA_INDEX_URL` 值。使用官方 PyPI 地址安装时仍收到 WinError 10013 代理连接拒绝。

## 3. 官方 Notebook 静态检查

### 3.1 `1_sampling_images.ipynb`

导入：

```text
cv2
matplotlib.pyplot
os
skimage.io
skimage.transform
```

功能：对无人机原图做中心区域裁剪，不是模型推理。

### 3.2 `2_Data_aug.ipynb`

导入：

```text
os, random, shutil
cv2
skimage.io
skimage.io.imread
numpy
skimage.color
scipy.signal.convolve2d
```

代码还调用 `Image.open`，但 Notebook 中没有看到 `from PIL import Image`；这是官方增强 Notebook 的代码缺陷，不属于模型 SavedModel 本身。

### 3.3 `GSP_AI_model.ipynb`

导入：

```text
exifread
re
tensorflow
skimage.io
skimage.transform.resize
numpy
os
datetime
```

Notebook 还使用 `pd.read_excel`，但展示的代码片段没有 `import pandas as pd`；运行前需要在适配层显式补齐依赖，不修改官方原始 Notebook。

模型加载方式：

```python
model_loaded = tf.keras.models.load_model(save_path)
```

推理方式：

```python
label, FS = model_loaded.predict([one_info, one_img])
```

## 4. 官方输入与输出语义

### 图像输入

- 使用 `skimage.io.imread` 读取图片；
- 使用 `skimage.transform.resize(img, (224, 224, 3))`；
- Notebook 没有展示 ImageNet 均值方差归一化；不能自行添加未记录的归一化；
- 输入顺序为图像数组和环境表格数组，而不是单独 RGB 图片。

### 图像时间

官方函数读取 EXIF 的 `Image DateTime`：

```text
YYYY:MM:DD HH:MM:SS
```

然后只取年月日与环境 Excel 的 `datetime` 精确匹配。没有 EXIF 拍摄日期时，官方流程无法完成气象行匹配。

### 气象输入

Notebook 使用：

```text
nor_rain 到 nor_solar
```

共 4 个归一化环境字段。当前下载的 `Data_S1_Environmental.factors.CN-UK-US.2018-2021.xlsx` 首行实际字段是 `name、datetime、tempmax、tempmin、temp、precip、solarradiation、solarenergy ...`，没有 `nor_rain` 到 `nor_solar` 这四列。因此，这个 Excel 不能未经预处理直接作为 Notebook 的 `one_info` 输入。

### 模型输出

官方 Notebook 给出六个阶段名称：

```text
Tillering
Jointing
B$H
Flowering
Filling
Ripening
```

输出包括：

1. 六阶段分数向量；
2. `FS` 数值输出。

`FS` 的单位和具体定义没有在 Notebook 中明确说明。本轮没有将其擅自转换为日期，也没有把它解释成未来长势分数。

## 5. 权重和压缩包检查

模型压缩包：`models/pretrained/gsp_ai/GSP-AI_model.zip`

- ZIP 完整性：通过；
- 成员损坏检查：通过；
- SHA256：`42d4c03d53c715cc12249eaa10f2ec3ed60d42d750e1fb9b3abfd52ef793d95b`；
- SavedModel：已解压到 `models/pretrained/gsp_ai/GSP-AI_model_extracted/GSP-AI_model/`。

推理 Notebook：`models/pretrained/gsp_ai/official_inference/iPython/`

详细机器可读检查结果：

`results/gsp_ai_inspection.json`

## 6. 安装尝试

本轮只在 `.venv-gsp-ai` 中执行了一次现代 Python 3.12 兼容候选安装：

```text
tensorflow==2.16.1
tf-keras==2.16.0
pandas==2.2.3
scikit-image==0.24.0
exifread==3.0.0
openpyxl==3.1.5
numpy==1.26.4
scipy==1.14.1
```

安装因代理连接拒绝失败，没有升级系统级代理配置，也没有重复重试。

官方 README 中提到的 TensorFlow 2.2、scikit-image 0.17、NumPy 1.24.2、SciPy 1.9.1 等版本面向旧 Python 环境；其中 TensorFlow 2.2 不能直接作为 Python 3.12 运行时方案。现代候选版本只是后续兼容性尝试，尚未验证可以加载本 SavedModel。

在可联网的普通 PowerShell 中可以准备离线 wheel：

```powershell
\.venv-gsp-ai\Scripts\python.exe -m pip download `
  --index-url https://pypi.org/simple `
  --only-binary=:all: `
  --dest wheels `
  tensorflow==2.16.1 tf-keras==2.16.0 pandas==2.2.3 `
  scikit-image==0.24.0 exifread==3.0.0 openpyxl==3.1.5 `
  numpy==1.26.4 scipy==1.14.1
```

下载后再使用 `pip install --no-index --find-links wheels ...` 安装到 `.venv-gsp-ai`，不要修改主项目环境。

## 7. 模型加载和真实图片推理结果

- TensorFlow import：未执行成功，因为 TensorFlow 未安装；
- SavedModel 加载：未执行；
- 模型签名读取：未执行；
- 官方示例推理：未执行；
- 真实 EWS/CGIAR 图片推理：未执行；
- 六阶段输出：没有真实数值；
- `FS` 输出：没有真实数值；
- 真实推理耗时：没有记录。

因此，本轮不能声称完成 GSP-AI 官方模型真实推理，也不能把当前结果接入网页预测值。

## 8. 当前系统保护状态

`GET /api/growth-forecast/status` 会区分：

- 官方 ZIP 是否存在：存在；
- SavedModel 是否解压：存在；
- TensorFlow 等依赖是否满足：不满足；
- 模型是否启用：否。

`POST /api/growth-forecast/predict` 仍返回 `unavailable/unverified`，不会生成未来 7/15/30 天数据、开花日期或阶段概率。

## 9. 测试

- 新增预测服务测试：6 passed；
- Python 单元测试：146 passed，3 skipped，4 个子测试通过；
- Python 编译检查：通过；
- 前端 `npm run build`：通过；
- 官方模型真实推理：未执行，依赖安装失败；
- HTTP 端到端模型推理：未执行，没有伪造成功记录。

## 10. 下一步

1. 在普通 PowerShell 或可联网环境下载上述 wheels；
2. 安装 TensorFlow 2.16.1 + `tf-keras` 兼容组合；
3. 先用 `tf.saved_model.load` 检查 SavedModel 签名，再评估 `tf.keras.models.load_model` 是否兼容；
4. 准备带 EXIF 日期的真实小麦图片和已经按官方字段归一化的四维气象输入；
5. 运行官方 Notebook 等价推理并记录实际输出；
6. 只有模型输出、`FS` 单位和输入语义都确认后，才接入开花日期或阶段时间线。

## 11. wheelhouse 离线安装追加结果

用户提供的 `models/pretrained/gsp_ai/wheelhouse/` 共包含 60 个 Windows CPython 3.12 wheel。执行了用户指定的离线安装命令：

```powershell
\.venv-gsp-ai\Scripts\python.exe -m pip install --no-index --find-links=models/pretrained/gsp_ai/wheelhouse -r models/pretrained/gsp_ai/requirements-gsp-ai-python312.txt
```

安装成功，实际版本为：

```text
TensorFlow 2.16.1
tensorflow-intel 2.16.1
Keras 3.15.1
tf-keras 2.16.0
NumPy 1.26.4
Pandas 2.2.3
scikit-image 0.24.0
SciPy 1.14.1
Matplotlib 3.9.2
OpenCV 4.10.0.84
Pillow 11.0.0
ExifRead 3.0.0
openpyxl 3.1.5
```

导入检查通过，TensorFlow 仅检测到 CPU 设备，未安装或启用 CUDA。

## 12. SavedModel 签名和真实图片运行结果

使用 `.venv-gsp-ai` 执行 `tf.saved_model.load` 成功，签名为：

```text
serving_default
input_1: float32, shape=(None, 224, 350, 3)
output dense: float32, shape=(None, 6)
```

但是：

- `tf.keras.models.load_model()` 在 Keras 3.15.1 下不支持该旧 SavedModel 格式；
- SavedModel 签名只有一个图像输入，不包含官方 Notebook 所说的四维气象输入；
- SavedModel 输出只有六维 `dense`，不包含官方 Notebook 所说的 `FS` 花期输出；
- 签名输入宽度为 350，而 Notebook 静态代码使用 `(224,224,3)`，两者存在不一致。

使用项目现有 CGIAR 真实 RGB 图片 `data/processed/growth_stage/images/01AJUu7l.jpeg`，按签名要求缩放到 `224×350×3` 后直接调用 `serving_default`，运行成功：

```text
inference_time_seconds: 0.10480579920113087
raw_dense_output:
[1.2038751e-05, 5.2710129e-07, 5.0121196e-07,
 3.1006891e-08, 1.9976056e-13, 9.9998701e-01]
```

这个数值只是**签名级 SavedModel 直接推理结果**，使用了与官方 Notebook 不一致的输入尺寸，也没有气象输入和 `FS` 输出。因此本项目不会把它显示为已经验证的生育期或开花日期结果。

详细原始记录：

`results/gsp_ai_savedmodel_runtime_test.json`

当前正确结论是：

- 依赖安装：成功；
- TensorFlow 导入：成功；
- SavedModel 低层加载：成功；
- SavedModel 签名级真实图片调用：成功；
- 官方 Notebook 语义一致的阶段+花期推理：未完成；
- 可用于麦视通开花日期预测：未验证，接口继续保持 `unavailable/unverified`。
