# GSP-AI 官方模型真实推理接入交付报告

## 1. 最终结论

官方 `GSP-AI_model.zip` 已成功获取、完整性校验并解压；官方 `iPython.zip` 和环境因素 Excel 也已核对。当前尚未完成官方模型真实推理，原因是独立环境缺少 TensorFlow 等运行依赖，且当前环境访问 PyPI 被系统代理拒绝。

因此，本轮没有把任何 GSP-AI 输出接入网页预测结果，也没有生成开花日期、阶段概率或未来 7/15/30 天数值。现有 `/api/growth-forecast/predict` 继续返回 `unavailable/unverified`，避免把“权重存在”误报成“模型可运行”。

## 2. 官方资源核验

官方 Release：<https://github.com/The-Zhou-Lab/GSP-AI/releases>

官方仓库：<https://github.com/The-Zhou-Lab/GSP-AI>

官方 Release V1.1 声明包含模型包、iPython 调用流程、环境因素表、WGSP-CN 和 Smartphone 数据；模型用于关键生育期识别和开花阶段预测。软件和算法为 MIT，测试数据、人工花期数据和模型资源标注为学术使用。

### 2.1 模型压缩包

文件：`models/pretrained/gsp_ai/GSP-AI_model.zip`

- 文件大小：9,861,735 字节；
- MD5：`2174826623A55CE0B7CD27FE30445F6C`；
- SHA256：`42D4C03D53C715CC12249EAA10F2EC3ED60D42D750E1FB9B3ABFD52EF793D95B`；
- ZIP 可读：是；
- `ZipFile.testzip()`：无损坏成员；
- 成员数量：6。

主要文件：

```text
GSP-AI_model/saved_model.pb
GSP-AI_model/variables/variables.data-00000-of-00002
GSP-AI_model/variables/variables.data-00001-of-00002
GSP-AI_model/variables/variables.index
GSP-AI_model/matrics.txt
```

解压目录：

```text
models/pretrained/gsp_ai/GSP-AI_model_extracted/GSP-AI_model/
```

### 2.2 官方推理代码

文件：`models/pretrained/gsp_ai/iPython.zip`

- 文件大小：6,170 字节；
- SHA256：`f7884efc20935bf571e7b5150debaa78c91df7b12564febeb0122374f38e0dce`；
- ZIP 可读：是；
- 成员：`GSP_AI_model.ipynb`、`1_sampling_images.ipynb`、`2_Data_aug.ipynb`。

官方 Notebook 的实际调用形式为：

```python
model_loaded = tf.keras.models.load_model(save_path)
label, flowering_value = model_loaded.predict([one_info, one_img])
```

官方代码中的输入处理：

- RGB 图像缩放到 `224×224×3`；
- 读取图片 EXIF 的 `Image DateTime`；
- 根据日期从环境 Excel 匹配四个归一化气象字段 `nor_rain` 到 `nor_solar`；
- 模型输入顺序为 `[environment_features, image]`。

官方 Notebook 中的阶段名称为：

```text
Tillering, Jointing, B$H, Flowering, Filling, Ripening
```

输出包含六类阶段分数和一个 `FS` 数值。`FS` 的单位、是否为距花期天数或其他定义必须通过官方示例和数据说明进一步确认，本项目没有擅自把它转换为日期。

## 3. 独立环境安装结果

已创建独立目录：

```text
.venv-gsp-ai
```

没有修改现有 `.venv` 或 `.venv-fomo`。

尝试安装：

```text
tensorflow-cpu
pandas
scikit-image
exifread
openpyxl
```

实际结果：

- `.venv-gsp-ai` 的 `ensurepip` 初始化失败；
- 使用现有 pip 对目标解释器安装时，PyPI 连接被系统代理拒绝；
- 当前运行时缺少：`tensorflow、pandas、skimage、exifread、openpyxl`；
- TensorFlow SavedModel 没有被加载。

完整检查结果保存在：

`results/gsp_ai_inspection.json`

## 4. 真实推理状态

### 官方示例推理

未完成。原因是 TensorFlow 和 Notebook 依赖未安装，不能把 ZIP 解压成功误认为模型推理成功。

### 真实小麦 RGB 图片推理

未完成。当前 EWS/CGIAR 图片没有在 GSP-AI 依赖完整的环境变量和模型运行时下执行，未生成阶段或花期结果。

### 输出字段核实

从官方 Notebook 静态代码可核实：

- 六阶段分数；
- `FS` 数值输出。

但没有通过实际运行核实具体数值范围、FS 单位、输出张量形状和模型签名，因此没有将这些字段写入真实预测记录。

## 5. 现有系统接入状态

已保留并增强模型状态检查：

```text
GET /api/growth-forecast/status
```

当前会区分：

- 官方 ZIP 是否存在；
- SavedModel 是否已解压；
- TensorFlow 等依赖是否存在；
- 模型是否真正启用。

当前状态为：

```text
official_package_present: true
saved_model_present: true
enabled: false
status: unverified
available_horizons: []
```

预测接口仍然不会返回伪造值：

```text
POST /api/growth-forecast/predict
```

返回的未来 7/15/30 天 `prediction`、`predicted_flowering_date` 和 `days_to_flowering` 保持为空，并明确说明模型未验证。

现有 V1.1、四种分割算法、FoMo4Wheat、CGIAR SVM 和价格模块没有被修改。

## 6. 测试结果

- ZIP 完整性测试：通过；
- 官方 Notebook ZIP 完整性测试：通过；
- SavedModel 文件结构检查：通过；
- 新增预测服务测试：**6 passed**；
- Python 单元测试：**146 passed，3 skipped，4 个子测试通过**；
- 后端文件编译：通过；
- `npm run build`：通过；
- 官方 GSP-AI 示例推理：**未通过/未执行**，依赖缺失；
- 真实小麦图片 GSP-AI 推理：**未执行**；
- HTTP 端到端推理：**未执行**，没有伪造测试通过记录。

## 7. 结论与下一步

本轮已经完成“官方权重获取和结构接入准备”，但没有完成“官方模型真实推理接入”。当前不能对外宣称：

- 已实现 GSP-AI 生育期识别；
- 已实现 GSP-AI 开花日期预测；
- 已实现未来 7/15/30 天阶段预测。

下一步必须在网络可用的普通 PowerShell 环境中完成：

1. 为 `.venv-gsp-ai` 安装与 TensorFlow SavedModel 兼容的 TensorFlow、pandas、scikit-image、ExifRead 和 openpyxl；
2. 运行官方 Notebook 的最小示例；
3. 用带 EXIF 日期的真实小麦图片和同日期气象行验证输出；
4. 记录模型实际输入签名、输出形状、FS 单位和推理时间；
5. 只有上述验证完成后，才接入 `predicted_flowering_date`、下一阶段和阶段时间线。
