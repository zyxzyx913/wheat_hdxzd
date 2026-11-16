# 麦视通 V4.2 PCSE/WOFOST 机理模型接入报告

## 结论

本轮完成了 PCSE/WOFOST 的独立接入边界设计、作物参数来源登记、天气字段校验、初始状态边界、情景配置和安全拒绝逻辑，但**没有成功运行 WOFOST 模拟**，因此没有启用未来 7/15/30 天结果。

原因是当前环境中 PCSE 尚未安装：独立 `.venv-pcse` 创建阶段 `ensurepip` 失败，随后网络代理也无法连接 PyPI。项目中没有可复用的 PCSE wheel、土壤文件、站点文件或真实天气输入。继续使用主环境或手写参数会破坏项目隔离和科研真实性，因此没有这样做。

## 官方兼容性和参数核查

PCSE PyPI 当前版本 6.0.13 声明 Python `>=3.9`，因此 Python 3.12 在版本声明上兼容。[PCSE PyPI](https://pypi.org/project/pcse/)

PCSE 文档要求作物、土壤、站点、天气和农事管理输入；官方 WOFOST 参数示例包含 `wheat / Winter_wheat_101`，但文档中的参数来源是 WOFOST 参数仓库，并且该品种是欧洲参考参数，不能直接声称适配中国小麦。[PCSE 参数文档](https://pcse.readthedocs.io/en/stable/code.html)

当前没有找到经过中国小麦产区验证的公开参数组合，也没有把欧洲参数数值复制进项目。WOFOST 模型本身适合作为作物生长模拟框架，但作物、土壤、站点和管理参数需要与目标区域核验。[PCSE 用户指南](https://pcse.readthedocs.io/en/stable/user_guide.html)

## 新增模块

- `src/wheat_phenotyping/future_growth/wofost_engine.py`
  - 可选 PCSE 执行器。
  - PCSE 未安装、参数缺失或输入未完成核验时明确拒绝运行。
- `src/wheat_phenotyping/future_growth/crop_parameters.py`
  - 登记官方欧洲冬小麦参考参数名称和来源。
  - 未验证参数不能用于正式预测。
- `src/wheat_phenotyping/future_growth/weather_service.py`
  - 校验日期、平均/最高/最低温度、降水和辐射字段。
- `src/wheat_phenotyping/future_growth/initial_state.py`
  - 保留图像指标和生育期信息。
  - 明确禁止把 RGB 覆盖率直接替换成 LAI。
- `src/wheat_phenotyping/future_growth/scenario.py`
  - 登记正常、偏干、偏湿、偏暖情景配置。
  - 当前只保存情景定义，没有生成天气或模拟结果。
- `src/wheat_phenotyping/future_growth/forecast_service.py`
  - 返回 `unverified` 状态，不生成虚假预测。
- `tests/unit/test_wofost_engine.py`
  - 覆盖参数拒绝、LAI 映射边界、天气字段和情景配置。

## 实际运行情况

| 项目 | 结果 |
|---|---|
| PCSE 独立环境 | 创建失败：ensurepip 返回错误 |
| PCSE 安装 | 未成功 |
| 小麦参数加载 | 未执行 |
| 土壤参数加载 | 未执行 |
| 站点参数加载 | 未执行 |
| 真实天气读取 | 未执行 |
| WOFOST 单地块模拟 | 未执行 |
| 7天模拟 | 不可用 |
| 15天模拟 | 不可用 |
| 30天模拟 | 不可用 |
| 情景模拟 | 仅登记配置，未运行 |
| 中国田间验证 | 未进行 |

## 测试结果

- 新增 WOFOST 边界测试：**4 passed**。
- 未来预测相关测试：**8 passed**。
- 全部 Python 单元测试：**154 passed，3 skipped，4 subtests passed**。
- 前端 `npm run build`：**通过**。

## 当前输入与模型边界

现有 RGB 分析可以提供植被覆盖率、绿色程度、空间均匀度和 V1.1 规则初评；CGIAR 模型可以提供生育期分类及置信度。但这些结果不能直接替换 WOFOST 的 LAI、TAGP、TWSO 或水分状态变量。必须通过连续观测和本地校准建立映射后，才能用于初始化或同化。

因此，当前系统没有输出任何 WOFOST LAI、生物量、开花日期或成熟日期数值，也没有把机理模型情景模拟包装成经过中国田间验证的预测。

## 下一步条件

1. 在可访问 PyPI 的环境中建立独立 `.venv-pcse`，安装并记录 PCSE 版本及依赖。
2. 获取官方 WOFOST 小麦参数文件、土壤参数和站点参数，并记录来源、区域和许可证。
3. 获取与用户麦田位置对应的真实历史天气和未来天气预报；不能使用电脑所在地代替地块位置。
4. 确定播种日期、品种、土壤和管理参数。
5. 先运行官方示例和欧洲参考参数，明确标记为跨区域探索性模拟。
6. 只有取得中国小麦连续观测后，才能评估 7/15/30 天 MAE、RMSE、R² 和参数敏感性，并决定是否启用网页预测。

