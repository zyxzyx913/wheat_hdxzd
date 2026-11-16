# 麦视通小麦长势智能分析 V2.0 交付报告

交付时间：2026-11-14

## 1. 统一入口

新增统一接口：

```text
POST /api/growth/analyze
GET  /api/growth/history
GET  /api/growth/history/{analysis_id}
```

`POST /api/growth/analyze` 接收一张 JPG、JPEG 或 PNG 图片，可选保留四种分割算法选择，默认 ExG。接口按顺序复用现有实现：图片质量检查、RGB 读取、植被分割、V1 指标、V1.1 规则评分、建议生成，并尽力附加现有 FoMo 生育期模型结果。

生育期增强失败不会掩盖当前长势结果；响应中会记录 `growth_stage_status`。没有模型时不会生成随机阶段或随机概率。

## 2. 当前长势结果

统一响应包含：

- `vigor_score`
- `vigor_level`
- `coverage_score`
- `greenness_score`
- `uniformity_score`
- `vegetation_coverage`
- `reliability`
- `strengths`
- `improvement_suggestions`
- `growth_stage`
- `model_version`
- `evaluation_version`
- `processing_time`
- 原图、掩膜、叠加图 URL

评分仍使用历史 V1.1 规则：

```text
0.45 × 覆盖评分 + 0.35 × 绿色评分 + 0.20 × 均匀评分
```

等级阈值仍为 80/60，未修改历史权重或阈值。结果明确标记为 `growth-vigor-v1.1-rule`，属于规则初评，不是经过农学验证的 AI 诊断模型。

## 3. 真实 EWS HTTP 冒烟

使用现有 EWS 测试目录中的真实 PNG 进行本机 Uvicorn HTTP 联调：

- `POST /api/growth/analyze`：HTTP 200
- `GET /api/growth/history`：HTTP 200
- 图像尺寸：350×350
- 实际植被覆盖率：6.7282%
- 实际综合分：34.0126
- 规则等级：长势较弱
- 可靠性：较高
- 生育期模型：阶段 2“早期营养生长/分蘖期”
- 生育期模型版本：`growth-stage-fomo-subset-20261114`
- 统一处理耗时约 3.081 秒，包含 CPU FoMo 特征提取

以上仅是一次真实图片接口冒烟结果，不代表 EWS 上的长势准确率，也不代表中国品种或手机拍摄域表现。

## 4. 网页功能

长势分析页已升级为 V2.0 一体化入口：

- 点击选择或拖拽上传图片
- 原图预览和重新上传
- 自动执行统一长势分析
- 综合分环形图
- 长势较好/一般/较弱或暂不评级
- 覆盖、绿色、均匀三个分项评分
- 可靠性、优势、问题和改善建议
- 原图、掩膜、叠加图和分布热力图
- 生育期七阶段概率（模型可用时）
- 未来 7/15/30 天区域明确显示“预测模型待建立”
- 历史分析列表和完整记录查看

历史记录只追加保存，不覆盖已有分析。旧历史记录没有 V2.0 字段时会显示为空，不会被伪造补齐。

## 5. 科研标注管理

已有科研标注入口继续保留，路径为：

```text
/#/research-annotation
```

支持匿名图片、多个标注者、四种表观长势标签、生育期记录、图像质量问题、判断依据、标注时间、Cohen/Fleiss 一致性分析、人工复核和 CSV 导出。

候选样本库当前为 290 张，真实人工标注记录仍为 0。系统不会自动生成专家标签，也不会把 CGIAR 生育期或 EWS 二分类标签转换成长势真值。

## 6. 测试结果

- 全部 Python 单元测试与 FastAPI 测试：186 passed，3 skipped，4 warnings。
- V2.0 统一 API 测试：2 passed。
- 真实 EWS HTTP 联调：API 200，历史查询 200。
- 前端 `npm run build`：通过。

测试覆盖：

- 统一 API 真实计算字段
- 历史记录保存和读取
- 无效图片拒绝
- 旧四种算法接口兼容
- 长势 V1/V1.1 指标
- 生育期接口
- 标注权限、重复提交保护和一致性统计

## 7. 当前未实现功能

未来 7 天、15 天、30 天预测模型尚未建立，网页只显示“预测模型待建立”，没有随机曲线或线性外推。

当前生育期模型是 CGIAR 数据固定子集上的初步模型，虽然可以在环境和权重可用时返回七阶段概率，但尚未完成地块独立、跨年份环境和中国手机照片外部验证。生育期结果与长势等级严格分开。

当前长势等级也没有真实专家标签校准，不能报告长势分类准确率。

## 8. 启动方式

后端：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping
$env:TEMP="$PWD\.test-tmp"
$env:TMP=$env:TEMP
$env:PYTHONPATH="$PWD\.venv-fomo\Lib\site-packages;$PWD\.external\dinov2;$PWD\src"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

前端另开 PowerShell：

```powershell
cd D:\Desktop\wheat\source-code\wheat-phenotyping\frontend
npm.cmd run dev -- --host 127.0.0.1
```

浏览器打开 `http://127.0.0.1:5173/#/growth-analysis`，上传小麦图片即可查看当前长势分析。两个终端需要保持运行。

## 9. 下一步

优先使用现有候选库完成多标注者真实标注，获得一致性和人工复核结果；在地块/年份分组防泄漏的前提下，先校准 V1.1 评分，再比较规则基线与 FoMo 768 维轻量长势分类器。未来趋势预测应另行建立带时间间隔和未来实测表型标签的数据集。
