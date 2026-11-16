# CGIAR 小麦生育期数据下载验证报告

检查日期：2026-11-14  
检查范围：只读检查 `data/raw/growth_stage/` 和 Windows 常见下载目录。未解压、未删除、未覆盖、未修改任何数据文件。

## 1. 文件下载情况

目标目录：`data/raw/growth_stage/`

| 文件 | 是否存在 | 实际大小 | 说明 |
| --- | --- | ---: | --- |
| `Images.zip` | 是 | 408,659,867 bytes（约 389.7 MiB） | 包含图片压缩包 |
| `SampleSubmission.csv` | 是 | 39,155 bytes | 测试 UID/提交模板 |
| `CGIAR_Train_mirror.csv` | 是 | 139,066 bytes | 之前保存的公开 GitHub 镜像标签文件 |

Windows 检查目录：

- `C:\Users\89885\Downloads`：未发现额外 CGIAR 文件；
- `C:\Users\89885\Desktop`：未发现额外 CGIAR 文件；
- `C:\Users\89885\Documents`：未发现额外 CGIAR 文件。

本次目标文件已经位于项目目标目录，不需要从 Windows 下载目录移动文件。

## 2. ZIP 完整性检查

使用 Python `zipfile` 只读取压缩包目录并执行 `testzip()` 校验，未解压任何文件。

结果：

- ZIP 可以正常打开；
- `testzip()` 返回空，没有发现损坏成员；
- ZIP 成员总数：14,254；
- 其中目录项：1 个（`Images/`）；
- 文件项：14,253 个；
- 图片扩展名全部为 `.jpeg`；
- 首批内部文件名形如 `Images/<UID>.jpeg`。

ZIP 文件可读且内部文件数量与官方数据页报告的 14,253 张图片一致。[官方 Zindi 数据页](https://zindi.africa/competitions/cgiar-wheat-growth-stage-challenge/data)

## 3. 图片 UID 与标签清单交叉检查

只读取 ZIP 内部文件名，没有读取图片内容。

| 检查项 | 结果 |
| --- | ---: |
| ZIP 内 JPEG UID 数量 | 14,253 |
| ZIP 内重复 UID | 0 |
| `CGIAR_Train_mirror.csv` 标签行数 | 10,695 |
| 标签 UID 在 ZIP 中 | 10,695 |
| 标签 UID 缺失 | 0 |
| `SampleSubmission.csv` 行数 | 3,558 |
| 测试 UID 在 ZIP 中 | 3,558 |
| 测试 UID 缺失 | 0 |
| 训练 UID 与测试 UID 重叠 | 0 |

这说明压缩包文件名、已有标签镜像和提交清单在 UID 层面可以完整对应。它不等于图片内容质量和标签语义已经验证通过。

## 4. SampleSubmission.csv 检查

实际读取结果：

- 字段：`UID,growth_stage`；
- 数据行：3,558；
- UID 空值：0；
- UID 重复：0；
- `growth_stage` 当前全部为提交模板占位值 `0`；
- 不能把这些 `0` 当作真实生育期标签。

该文件可正常读取，可作为测试 UID 清单使用；预测值尚未生成。

## 5. CGIAR_Train_mirror.csv 检查

已有镜像标签文件实际包含：

- 字段：`UID,growth_stage,label_quality`；
- 行数：10,695；
- UID 空值：0；
- UID 重复：0；
- `growth_stage` 为 1–7；
- `label_quality` 为 1 或 2；
- 标签 UID 全部在 Images.zip 中。

类别数量为：

| 阶段 | 数量 |
| ---: | ---: |
| 1 | 3,057 |
| 2 | 1,389 |
| 3 | 689 |
| 4 | 1,712 |
| 5 | 1,092 |
| 6 | 421 |
| 7 | 2,335 |

## 6. 当前尚未验证的内容

本轮没有解压图片，因此以下项目仍未完成：

- JPEG 图片实际宽度、高度和色彩模式；
- 图片是否能够被 Pillow 全部解码；
- 图片内容是否为空、损坏、过暗或重复；
- 图片与标签的视觉语义是否正确；
- 不同 UID 是否来自同一地块的相邻时间点；
- 数据集是否存在地块/农户级训练测试泄漏；
- 标签质量 1/2 的具体空间和时间分布。

官方背景说明数据来自印度 Punjab 和 Haryana 的两季 Rabi 田间观测，图片通过 WheatCam 采集并进行 ROI/隐私处理；这些信息不替代本地逐图质量检查。[官方数据背景](https://zindi.africa/competitions/cgiar-wheat-growth-stage-challenge/data)

## 7. 是否可以进入下一步

**可以进入下一步“受控解压和图片标签配对检查”，但不能把本报告视为数据质量验证完成。**

建议下一步：

1. 在新目录中解压，不覆盖 `Images.zip`；
2. 读取全部 JPEG 尺寸、模式、解码状态和 SHA-256；
3. 用 `manifest.csv` 建立 UID、标签、质量、图片路径和 split；
4. 对训练标签和测试 UID 分别统计质量与类别；
5. 检查相邻图片/同一地块泄漏风险；
6. 再决定是否训练冻结 FoMo4Wheat + 轻量分类头。

当前结论：**下载文件齐全，ZIP 完整可读，训练/测试 UID 均能对应图片；图片内容和标签质量仍需下一步解压后验证。**
