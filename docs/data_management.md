# 数据集管理和分组划分

## 清单字段

`data` 模块通过 CSV 索引公开、真实或模拟样本，不复制/伪造图像和标签。必要字段：

```csv
sample_id,dataset_name,dataset_version,group_id,split,image_path,reference_mask_path,data_source
plant001_view01,wheat_public_set,release-id,plant001,train,images/a.png,masks/a.png,public
```

- `sample_id` 在同一 dataset/version 内唯一。
- `group_id` 是防泄漏单位，如植株、地块、采集批次或视频序列。一个组只能落入一个 split。
- `split` 为 train / validation / test。创建划分前可留空。
- `data_source` 必须为 `public`、`real` 或 `simulated`。
- 数据集版本填写发布版本、DOI/commit 或用户记录的版本标签；项目不会猜测版本。
- 图像与人工二值掩膜尺寸须相同。不会自动缩放人工掩膜。

`load_rgb_image` 支持 PPM P3/P6、PNG、JPEG、BMP 和 TIFF；`load_binary_mask` 支持 PGM P2/P5 和 Pillow 可读的 PNG/TIFF 二值标注。灰度标签只接受 0、1 或 255；RGB 标注要求黑色背景且至多一种前景色。复杂类别调色板需先按数据集官方映射转换为二值叶片掩膜，并记录转换过程。

## 生成分组划分

1. 人工检查数据集来源许可和标签含义。
2. 制作完整 CSV 清单，`group_id` 必须反映相关样本的共同采集对象。
3. split 列可为空，运行：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
& .\.venv\Scripts\python.exe scripts\split_dataset.py `
  --manifest data\manifests\wheat_rgb_unassigned.csv `
  --output data\manifests\wheat_rgb_split.csv `
  --seed 42
```

程序在每个数据集版本内部按 group 划分，要求至少 3 个独立 group，比例在组样本数不等时仅近似。划分后检查 `group_id`，确认同组没有跨集合。数据极少时应人工制定分组方案并记录理由，不应为了得到比例而拆开同一植株/地块。

训练集/验证集用于参数选择和开发；测试集只在参数冻结后评价。若数据集已经发布官方分组，优先沿用官方方案，并通过清单校验其组边界。
