# GWFSS_v1.0 标注数据获取与检查报告

**检查日期：** 2026-11-12  
**项目：** `D:\Desktop\wheat\source-code\wheat-phenotyping`  
**任务范围：** 仅获取官方 1,096 张 labelled GWFSS 数据；不下载 52,078 张无标签图像、不训练模型、不改动 EWS 和既有实验结果。

## 执行结果

**下载未成功。** 已尝试从官方 Hugging Face 数据集文件直链下载 labelled 专用压缩包；普通环境无法解析主机名，获准的网络尝试仍在连接 `huggingface.co:443` 时超时。下载目录 `data/raw/gwfss/` 当前没有归档文件或部分下载文件，因此本轮没有解压、没有处理图像/掩膜，也没有进行数据质量统计。

官方仓库页面可确认 labelled split 为 1,096 条、许可元数据为 CC BY 4.0，且提供单独文件 `GWFSS_v1.0_labelled.zip`。Hugging Face 页面列出的远端文件大小约 611 MB，SHA-256 为 `b046d8bdb5edab77a50dd5aefbb5e08d6c512a721ed2e9f5482dc64de9aa6c82`。这些是**远端仓库元数据**，不是本地下载成功记录。[官方数据集卡](https://huggingface.co/datasets/GlobalWheat/GWFSS_v1.0/blob/main/README.md) [官方 labelled 压缩包文件页](https://huggingface.co/datasets/GlobalWheat/GWFSS_v1.0/blob/main/GWFSS_v1.0_labelled.zip)

## 官方信息核实

| 项目 | 官方资料可确认的信息 | 本地核实状态 |
|---|---|---|
| 数据集/版本 | Global Wheat Full Semantic Organ Segmentation，GWFSS_v1.0 | 官方名称已确认 |
| 标注数量 | Hugging Face `labelled` split 有 1,096 条记录 | 本地实际获取 0 张图像、0 张掩膜 |
| 类别语义 | background、leaves、stems、heads（穗） | 类别名称已从论文核实；原始掩膜实际编码未核实 |
| 文件结构 | 数据卡声明 feature 为 `image` 和 `mask`；仓库另有 labelled ZIP 文件 | ZIP 内部结构、扩展名及配对规则未检查 |
| 官方划分 | 数据卡只列 `labelled` split；未见 train/validation/test 官方划分 | 不进行随机切分 |
| 许可 | CC BY 4.0 | 使用时须依许可提供署名/来源、许可链接，并标明对数据所作的修改；具体使用仍应遵守数据卡及许可文本 |
| 论文 | Wang et al., *The Global Wheat Full Semantic Organ Segmentation (GWFSS) dataset*, DOI: 10.1016/j.plaphe.2025.100084 | 应在研究、报告和成果中引用 |

论文将 heads 定义为小麦穗并排除芒；leaves 为叶片叶身并包括叶舌；stems 包括叶鞘，穗下的 peduncle 不单独标注而计入 stem。论文还报告数据汇集自 11 家机构/高校，并包含生育阶段和成像设置相关描述。它确认的是**类别语义和数据集总体描述**，不能据此推断本地掩膜 PNG 的像素值或颜色编码。[GWFSS 论文全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC12710005/) [Global Wheat 项目页](https://www.global-wheat.com/gwfss.html)

### 标签编码状态

官方 Hugging Face README 只声明 `mask` 是图像特征，没有写出四个类别对应的像素值、调色板或内部标签 ID。本轮没有原始掩膜可读，因此像素编码必须保持为**未核实**，不能据常见语义分割惯例猜成 0/1/2/3。恢复下载后须逐张读取掩膜的调色板、像素唯一值及元数据，并与官方标注说明交叉确认后，才能建立类别映射。

## 下载失败原因与手动获取方法

本轮网络请求连接官方 Hugging Face 主机超时，未得到文件内容。没有证据表明官方文件损坏或链接失效；当前阻碍是本机执行环境无法建立 HTTPS 连接。

请手动获取**仅 labelled 的官方文件**：

1. 打开 [GWFSS_v1.0 文件列表](https://huggingface.co/datasets/GlobalWheat/GWFSS_v1.0/tree/main)。
2. 进入 `GWFSS_v1.0_labelled.zip` 文件页，使用 Hugging Face 页面上的下载按钮。不要下载 `unlabelled` 数据或 ETH 全量数据。
3. 将下载文件保存为：`D:\Desktop\wheat\source-code\wheat-phenotyping\data\raw\gwfss\GWFSS_v1.0_labelled.zip`。
4. 在项目 PowerShell 中核验文件完整性：

   ```powershell
   Get-FileHash .\data\raw\gwfss\GWFSS_v1.0_labelled.zip -Algorithm SHA256
   ```

   结果应与官方文件页公布的 SHA-256 一致：`b046d8bdb5edab77a50dd5aefbb5e08d6c512a721ed2e9f5482dc64de9aa6c82`。

5. 下载并核验后再继续解压至独立目录 `data/raw/gwfss/extracted/`；不要解压到 EWS 目录，也不要改写压缩包内的图像或掩膜。

## 数据质量检查状态

因下载失败，下面的项目均**未执行**，不以 0% 或“通过”代替：

| 检查项目 | 本地结果 |
|---|---|
| 实际下载归档大小 | 0 bytes；未取得归档 |
| RGB 图像数 / 掩膜数 | 0 / 0 个本地文件；不是数据集真实样本数 |
| RGB 与掩膜是否一一配对 | 未检查 |
| 图像和掩膜尺寸 | 未检查 |
| 实际像素编码、四类像素比例 | 未检查、未知 |
| 每类出现图像数 | 未检查 |
| 损坏文件、空掩膜、异常标签 | 未检查 |
| 机构、成像设置、生育阶段等逐样本元数据 | 论文描述了总体字段；本地压缩包是否含有对应文件尚未检查 |

本地清单 `data/processed/gwfss/dataset_manifest.csv` 目前只有字段头，没有样本记录；`dataset_summary.json` 将本地下载失败与无法执行的质量统计明确记为状态/空值。取得归档后应重新生成这些文件，不能把本报告中的 1,096 条官方记录数写成本地已获取数量。

## 数据划分与后续适用性

Hugging Face 数据卡当前只展示一个 `labelled` split，没有 train/validation/test 划分说明。即使图像有 1,096 张，也不应直接逐图随机拆分：同一机构、地块、采集批次、拍摄设置或近重复图像可能造成泄漏。建议先解析论文随数据提供的 subset 与 imaging-setup 元数据，按机构/地理位置/采集批次/拍摄设置分组，审查重复和相似图像；再制定分组的 train/validation/test 方案，并保存清单与随机种子。具体分组字段是否可用要待原始包检查后确定。

若官方掩膜确实为 RGB 图像逐像素对应的叶片、茎秆、麦穗和背景四类标注，则该 labelled 数据可用于后续器官语义分割研究。当前仍无法确认本地文件结构、类别数值编码、配对关系和标签质量，所以**尚不能进入训练阶段**。

## 当前遗留问题

1. 官方文件未能下载；需要手动浏览器下载后再继续。
2. 像素级类别编码尚未由原始掩膜核验，禁止猜测。
3. 具体归档内文件结构、逐样本元数据、图像-掩膜配对及质量问题均待检查。
4. 官方只列出 labelled split；防止机构/地块/拍摄条件泄漏的分组方案仍须结合解压后的元数据设计。
5. 论文中的语义类名不能替代本地掩膜值映射；在编码核验前不能直接训练四分类模型。

## 引用

Wang, X. et al. (2025). *The Global Wheat Full Semantic Organ Segmentation (GWFSS) dataset*. Plant Phenomics. https://doi.org/10.1016/j.plaphe.2025.100084. Dataset metadata license: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
