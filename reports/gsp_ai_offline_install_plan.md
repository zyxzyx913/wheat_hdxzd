# GSP-AI 离线依赖安装与模型加载计划

## 1. 当前结论

本轮没有修改系统全局代理、没有修改主项目 `.venv`、没有修改 GSP-AI 权重，也没有重复执行 ZIP 检查。

独立环境的 pip 已成功初始化，但依赖仍未安装。当前网络存在两层阻断：

1. Windows Internet Settings 开启了代理，地址为 `127.0.0.1:7890`；
2. 在当前命令临时清空代理、设置 `NO_PROXY=*` 后，访问 `https://pypi.org/simple` 仍出现 DNS `getaddrinfo failed`。

因此当前机器无法在线解析 PyPI，不能继续重复安装。

## 2. 环境检查

| 项目 | 结果 |
|---|---|
| Python | 3.12.10 |
| 解释器 | `.venv-gsp-ai\Scripts\python.exe` |
| OS | Windows 11 AMD64 |
| 位数 | 64 位 |
| pip | 25.0.1 |
| pip.ini | 未发现用户、站点或全局 pip.ini |
| 环境变量代理 | 未发现 HTTP_PROXY/HTTPS_PROXY/ALL_PROXY/PIP_INDEX_URL |
| Windows 用户代理 | 已启用，`127.0.0.1:7890` |
| SavedModel | 文件已准备，未加载 |

未输出代理密码、认证令牌或其他敏感内容。

## 3. 只读代理诊断

执行了：

```powershell
pip config debug
pip config list
```

未发现 pip 配置中的代理或镜像项。

检查 Windows Internet Settings 得到：

```text
ProxyEnable = 1
ProxyServer = 127.0.0.1:7890
AutoConfigURL = empty
```

本轮没有执行 `Set-ItemProperty`、注册表修改、PATH 修改或系统代理关闭操作。

## 4. 官方 Notebook 依赖清单

从官方 `iPython.zip` 实际代码提取到：

### 模型 Notebook

```text
tensorflow
skimage
numpy
exifread
pandas（代码调用 pd.read_excel，但 Notebook 片段未显式 import pandas）
openpyxl（Excel 引擎）
```

### 采样 Notebook

```text
cv2
matplotlib
skimage.io
skimage.transform
```

### 增强 Notebook

```text
cv2
skimage
numpy
scipy
matplotlib
Pillow（代码调用 Image.open，但片段未显式导入）
```

官方 README 给出的旧版本包括 TensorFlow 2.2、scikit-image 0.17、Matplotlib 3.7.1、Pandas 2.0.1、NumPy 1.24.2、SciPy 1.9.1。TensorFlow 2.2 不能直接作为 Python 3.12 方案，因此本项目生成了现代兼容候选清单：

`models/pretrained/gsp_ai/requirements-gsp-ai-python312.txt`

## 5. Python 3.12 候选版本

```text
tensorflow==2.16.1
tf-keras==2.16.0
numpy==1.26.4
pandas==2.2.3
scipy==1.14.1
scikit-image==0.24.0
matplotlib==3.9.2
opencv-python==4.10.0.84
Pillow==11.0.0
ExifRead==3.0.0
openpyxl==3.1.5
```

这些是 Python 3.12 的候选版本，不是已经验证成功的组合。TensorFlow 2.16 的 Keras 3 SavedModel 兼容性仍需通过 `tf.saved_model.load` 和官方模型签名测试确认。

## 6. 离线 wheel 下载方案

在一台能够访问官方 PyPI 的普通 PowerShell 中执行：

```powershell
$project = 'D:\Desktop\wheat\source-code\wheat-phenotyping'
$wheelDir = Join-Path $env:TEMP 'gsp-ai-wheels'
New-Item -ItemType Directory -Force $wheelDir | Out-Null

& "$project\.venv-gsp-ai\Scripts\python.exe" -m pip download `
  --index-url https://pypi.org/simple `
  --only-binary=:all: `
  --dest $wheelDir `
  -r "$project\models\pretrained\gsp_ai\requirements-gsp-ai-python312.txt"

Get-ChildItem $wheelDir | Select-Object Name,Length
Get-FileHash $wheelDir\* -Algorithm SHA256
```

`pip download` 会解析并下载传递依赖，不需要手工猜测每个依赖包。wheel 统一保存在系统临时目录，不写入项目源码目录。

将 wheel 目录复制到目标电脑后，在项目目录执行：

```powershell
$wheelDir = 'D:\Temp\gsp-ai-wheels'
$project = 'D:\Desktop\wheat\source-code\wheat-phenotyping'
& "$project\.venv-gsp-ai\Scripts\python.exe" -m pip install `
  --no-index --find-links $wheelDir `
  -r "$project\models\pretrained\gsp_ai\requirements-gsp-ai-python312.txt"
```

不应使用 `--trusted-host` 绕过证书或访问控制，也不应修改系统全局代理。

## 7. 安装后的验证顺序

```powershell
& "$project\.venv-gsp-ai\Scripts\python.exe" -c "import tensorflow as tf; print(tf.__version__)"
& "$project\.venv-gsp-ai\Scripts\python.exe" -c "import pandas, skimage, exifread, openpyxl; print('imports-ok')"
```

然后检查 SavedModel：

```python
import tensorflow as tf
path = r"models/pretrained/gsp_ai/GSP-AI_model_extracted/GSP-AI_model"
loaded = tf.saved_model.load(path)
print(list(loaded.signatures))
for name, fn in loaded.signatures.items():
    print(name, fn.structured_input_signature, fn.structured_outputs)
```

只有签名和输入 dtype/shape 明确后，才考虑适配官方 `model.predict([one_info, one_img])` 调用；不能直接修改模型结构或重训。

## 8. 当前模型加载状态

- 官方权重压缩包：存在；
- SavedModel 文件：存在；
- TensorFlow：未安装；
- SavedModel 加载：未执行；
- 输入签名：未读取；
- 真实图片推理：未执行；
- 未来预测接口：保持 `unavailable/unverified`。

## 9. 保护范围

本轮没有修改：

- 主项目 `.venv`；
- V1.1 长势评价；
- FoMo4Wheat；
- CGIAR SVM；
- GSP-AI 原始 ZIP/SavedModel；
- EWS、CGIAR 数据和历史实验结果。
