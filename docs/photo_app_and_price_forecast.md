# 图片入口与全国小麦价格预测基线

## 单图入口

在项目根目录运行：

```powershell
$env:PYTHONPATH = "src"
\.venv\Scripts\python.exe -m wheat_phenotyping.app.desktop
```

窗口支持 PNG、JPEG、BMP、TIFF 和 PPM。可选单张图或文件夹，可运行 ExG、HSV、Otsu-ExG、ExG-HSV Fusion、RF-Color-Texture 中的一种或全部。批量结果写入新建结果目录，包含逐图 CSV、运行摘要 JSON、PGM 掩膜和 PNG 叠加图；单图预览显示第一条成功结果。算法参数见 `configs/segmentation/desktop_frozen_defaults.json`，沿用项目已有验证集冻结参数。

RF 模型的标签语义为“活体植被 / 非活体或背景”，来自 EWS 公开数据；EWS 测试集表现不能代表用户手机图像表现。界面刻意不输出弱/中/旺等级、后续生长或产量预测，因为目前没有这些农学标签及连续地块观测。面积比例会受拍摄距离、视角、背景和光照影响。

## 全国平均价格目标

项目暂以“全国小麦周度平均收购价，元/吨”为目标概念。国家粮食和物资储备局公布全国主要粮食品种收购价格周报；周报页面适合作为来源目录，但图表/图片式周报需要先人工抄录或用可靠数据接口整理成结构化序列，并逐条保存原文来源。报告中的“收购价”须与市场批发价、最低收购价、企业报价区分。

官方目录：[国家粮食和物资储备局粮食价格/市场监测](https://sousuo.lswz.gov.cn/html/zmhd/lysj/lsjg.shtml)

导入价格表 CSV 要有三列：

```csv
date,price_yuan_per_ton,source
```

每行必须来自真实观察，日期按连续周记录。不得用本模板空表作为样本；不可自行插值补造缺失周。由于官方假期报告日期可能不等间隔，使用前应核实并在研究协议中定义时间频率，不能仅为了通过程序校验而改日期。

当有至少 10 个连续周的真实价格观测后，可运行：

```powershell
$env:PYTHONPATH = "src"
\.venv\Scripts\python.exe scripts\forecast_national_wheat_price.py path\to\prices.csv --horizon-weeks 4
```

脚本输出“末值保持”和“最近四周均值”两种透明基线、逐预测起点回测记录，以及 MAE、RMSE、MAPE、R² 汇总和数据截止日期/来源元数据。滚动回测只使用预测时点之前的数据；这些指标仍只是历史基线比较，不代表未来有效性。模型选择还需保留后续时间段作最终样本外检验，也不把田间单株照片直接映射成全国价格。

## 当前边界

图像分析和价格分析是两个独立实验链路。将来若研究图像长势与全国价格的关系，至少需要有明确的全国价格时间序列、同步的产量/供需/政策特征、严格时间切分和样本外回测。单幅田间图片不会决定全国平均价格。
