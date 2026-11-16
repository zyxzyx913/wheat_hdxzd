# GSP-AI 官方模型结构与输出语义审计

## 1. 审计结论

当前 `GSP-AI_model.zip` 中的 SavedModel 可以用 TensorFlow 2.16.1 的 `tf.saved_model.load()` 读取，也可以对一个符合签名的 RGB 张量执行低层推理；但是它与官方 Notebook 描述的模型接口不一致：

- SavedModel 只有一个图像输入：`(None, 224, 350, 3)`；
- SavedModel 只有一个输出：`dense`，形状 `(None, 6)`；
- SavedModel 没有四维气象输入签名；
- SavedModel 没有 `FS` 花期输出签名；
- 官方 Notebook 使用的 `224×224×3` 图像和 `nor_rain` 到 `nor_solar` 气象输入无法直接传给当前签名；
- 官方 Notebook 的六阶段标签列表不能单独证明当前 SavedModel 的六维输出顺序；
- 模型包没有单独的标签映射、配置文件或花期预测头。

因此，当前模型只能称为“已加载的六输出 SavedModel”，不能安全称为已核验的 GSP-AI 生育期模型，也不能用于开花日期或未来 7/15/30 天预测。没有修改模型、没有训练新模型、没有把未知输出接入网页。

## 2. 模型包文件清单

解压后的模型目录只有：

```text
saved_model.pb
variables/variables.data-00000-of-00002
variables/variables.data-00001-of-00002
variables/variables.index
matrics.txt
```

没有发现：

- 第二个 SavedModel；
- 独立花期回归头；
- 标签映射 JSON/CSV；
- 模型配置 YAML/JSON；
- 气象归一化参数文件；
- 预测日期公式或单位说明。

`matrics.txt` 只包含数值数组，没有类别名称、输出字段说明或 `FS` 公式。

## 3. 官方 Notebook 对照

### 3.1 模型加载

官方 Notebook 使用：

```python
model_loaded = tf.keras.models.load_model(save_path)
```

当前 Keras 3.15.1 不支持直接用 `tf.keras.models.load_model()` 加载该旧 SavedModel；低层 `tf.saved_model.load()` 可以加载。

### 3.2 官方 Notebook 输入

Notebook 代码：

```python
img = skimage.transform.resize(img, (224, 224, 3))
data_info = df_new.loc[:, 'nor_rain':'nor_solar']
label, FS = model_loaded.predict([one_info, one_img])
```

它还读取 EXIF `Image DateTime`，再按日期匹配气象 Excel。

### 3.3 官方 Notebook 输出

Notebook 只将 `label` 的六个元素用于：

```text
Tillering, Jointing, B$H, Flowering, Filling, Ripening
```

并将第二个返回值命名为 `FS`，打印为 `FS_time`。Notebook 没有展示：

- FS 的计算公式；
- FS 的单位；
- FS 是日期、天数还是其他连续值；
- `label` 六个元素与 SavedModel 当前 `dense` 输出的正式映射文件。

因此不能把 `FS` 自动解释成开花日期，也不能把当前 `dense` 六维向量直接映射成六个阶段。

## 4. SavedModel 内部结构

审计文件：`results/gsp_ai_model_structure.json`

实际结构：

- ConcreteFunction：1 个，名称 `serving_default`；
- 图输入：`input_1`，`float32`，形状 `(None, 224, 350, 3)`；
- 图输出：`dense`，`float32`，形状 `(None, 6)`；
- Graph 操作数量：19；
- 变量数量：16；
- Trackable children：34 个；
- 计算图中存在一个 `StatefulPartitionedCall`，其输出为 `(None, 6)`；
- 没有第二个输出节点或花期回归节点。

变量名称显示该导出模型是一个卷积网络加六单元 Dense 输出头，包括 `conv2d` 到 `conv2d_6` 和 `dense`。这只能说明结构形态，不能据此推断六个 Dense 单元的农学标签语义。

## 5. 真实图片低层推理

使用真实 CGIAR 图片：

```text
data/processed/growth_stage/images/01AJUu7l.jpeg
```

按 SavedModel 签名将图像调整为 `224×350×3` 后执行：

- 输入：`(1, 224, 350, 3)`；
- CPU 推理时间：约 `0.1048` 秒；
- 输出：`dense` 六维浮点向量；
- 输出原始值已保存至 `results/gsp_ai_savedmodel_runtime_test.json`。

该结果只是签名级运行证明。它没有使用官方 Notebook 要求的气象输入，尺寸也与 Notebook 的 224×224 不同，且没有 `FS` 输出，所以没有被解释为生育期或开花日期结果。

## 6. 官方资源与版本关系

官方 Release V1.1 明确称 `GSP-AI_model.zip` 用于关键生育期识别和开花阶段预测，并同时发布 iPython 流程、环境因素表和测试数据。[官方 Release V1.1](https://github.com/The-Zhou-Lab/GSP-AI/releases/tag/V1.1)

本地 ZIP 与该 Release 的文件名一致，但当前 SavedModel 导出的 serving signature 与 Notebook 的双输入、双输出描述不一致。可能原因包括：

1. Release 中模型包和 Notebook 不是同一导出版本；
2. Notebook 使用的是训练时 Keras 对象，而 Release SavedModel 只导出了分类服务签名；
3. 花期头或预处理文件未包含在该 ZIP；
4. 发布包在转换/导出时丢失了第二输出。

这些是兼容性假设，不能作为已证实结论。当前审计只确认“文件实际是什么”。

## 7. 对项目能力的结论

### 当前 SavedModel 是什么？

一个可被 TensorFlow `tf.saved_model.load()` 加载的卷积网络 SavedModel，导出服务签名为单图像输入和六维 Dense 输出。具体任务语义未被当前文件充分记录。

### 六维输出代表什么？

当前模型文件没有正式标签映射。官方 Notebook列出六个阶段名称，但由于输入/输出签名不一致，不能证明当前 SavedModel 的六维顺序就是这六阶段。因此项目标记为未知，不接入生育期结果。

### FS 是什么？

官方 Notebook 将其作为模型第二返回值，但当前 SavedModel 没有第二输出。Notebook 没有公式、单位或参考定义。本项目不把 FS 解释为开花日期、距开花天数或任何长势指标。

### 是否缺少模型文件？

从当前 ZIP 看，缺少可见的独立花期头、标签映射、归一化参数和 FS 说明。是否存在未公开的其他 Release 资源，需要官方提供或用户获取后再核对；当前没有绕过权限查找。

### 官方 Notebook 是否能够完整运行？

在当前 Python 3.12 + Keras 3 环境中不能按原样完整运行：`tf.keras.models.load_model()` 不接受旧 SavedModel，且当前签名与 Notebook 的双输入/双输出不匹配。

### 能否用现有模型完成真实生育期预测？

不能安全完成。可以执行低层六输出推理，但输出语义未知，不应作为生育期预测。

### 能否预测开花日期？

不能。当前 SavedModel 没有 `FS` 输出，且没有可核验单位和公式。

### 还缺少什么？

- 与当前 SavedModel 完全对应的官方标签映射；
- `dense` 六维输出的任务定义；
- 花期回归头或正确版本模型；
- `FS` 的单位和计算公式；
- 与模型签名一致的官方预处理；
- 可复现的环境变量归一化表；
- 官方测试样本和期望输出。

## 8. 系统保护状态

- V1.1 长势评分未修改；
- 四种 RGB 分割算法未修改；
- FoMo4Wheat 未修改；
- CGIAR SVM 未修改；
- GSP-AI 原始 ZIP 和 SavedModel 未修改；
- 网页没有接入未知六维输出；
- 预测接口仍返回 `unavailable/unverified`。
