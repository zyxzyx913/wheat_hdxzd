# 小麦表型与全国价格研究原型

这是一个增量开发中的科研软件项目。当前已实现 EWS 公开数据集上的植被/背景分割研究，以及单图可见指标桌面演示；尚未实现经过农学验证的长势等级、未来长势预测或可信的市场价格预测模型。

## 环境与测试

Windows 11 / Python 3.12。项目虚拟环境已经建立时，可直接运行：

```powershell
\.venv\Scripts\python.exe -m pytest tests\unit -v
```

首次安装依赖：

```powershell
python -m venv .venv
\.venv\Scripts\python.exe -m pip install -r requirements.txt
\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 照片分析界面

```powershell
$env:PYTHONPATH = "src"
\.venv\Scripts\python.exe -m wheat_phenotyping.app.desktop
```

在窗口选择一张田间 RGB 图像或包含图像的文件夹，可单独运行某种算法或运行全部算法。支持 ExG、HSV、Otsu-ExG、ExG-HSV Fusion、RF-Color-Texture，并可选择是否递归读取子文件夹。界面显示原图、掩膜和绿色叠加预览；每张图输出 PGM 掩膜/PNG 叠加图，并写入逐图 `image_results.csv` 与 `run_summary.json`。传统算法参数读取 `configs/segmentation/desktop_frozen_defaults.json`，来源为既有验证集冻结参数。RF 使用 EWS 的活体植被/非活体背景标签训练；模型没有在用户手机图像上独立验证。结果仍是植被/背景分割与面积比例代理值，不是器官识别、长势等级、作物生物量或产量预测。

## 全国平均小麦价格

价格目标拟定义为全国小麦周度平均收购价（元/吨），与企业报价、批发价和最低收购价分开记录。先收集至少 10 周连续、带来源的实际价格序列，CSV 样式见 [价格预测与图片入口说明](docs/photo_app_and_price_forecast.md)。在目前数据不足时程序不会生成实验分数或虚构预测准确率。可运行两种透明基线和扩展窗口滚动回测：

```powershell
$env:PYTHONPATH = "src"
\.venv\Scripts\python.exe scripts\forecast_national_wheat_price.py data\national_wheat_weekly.csv --horizon-weeks 4
```

输出写入 `results/economics/latest/`，包含预测和数据来源/截止时间元数据。基线需先经滚动起点回测，不能当成已验证市场预测。

## 当前研究数据边界

- EWS 公开分割标注区分活体植被与非活体/背景，不含弱势、中势、旺势、产量或未来长势标签。
- 图像实验结果只对应对应数据集和拍摄条件，模拟数据与公开数据结果分别记录。
- 全国价格和田间单株图像为两个不同尺度的研究问题；价格预测应使用可靠全国序列和时间顺序样本外验证。
- 原始数据来源、许可和转换说明见 `data/processed/ews/README.md` 及 `docs/`。
