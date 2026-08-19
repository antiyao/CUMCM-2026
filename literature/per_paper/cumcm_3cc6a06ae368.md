# Paper: 乙醇偶合制备 C4 烯烃的多元回归与神经网络模型

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_3cc6a06ae368`
- Year: 2021
- Problem: B050，B 题
- Award: 全国一等奖，已由参赛团队/作者与官方一等奖名单交叉核验；官方展示本身不作为奖级推断依据。
- Provenance tier: V; 湖南大学公开的赛后期刊增刊版为主版本，官方一等奖名单独立核验团队；组委会 59 页展示长稿作为伴随版本
- Source file: `literature/raw_papers/2021/B050_university_2021_B050_ethanol.pdf`
- Source URL: `https://math.hnu.edu.cn/__local/2/EC/E5/9D2A4553159C05438368574F2E0_62EFDFCC_20332D.pdf`
- Verification source: `https://www.mcm.edu.cn/upload_cn/node/626/n7nhofCn201ab6d8d92db35564daa7cca31853d6.pdf`
- Pages: 主版本 18 页，其中 p18 为空白；伴随长稿 `literature/raw_papers/2021/B050.pdf` 59 页
- SHA-256: `99292c324ce1c71ca859b6c0676f527b49fa93dd0f0441028ed828f04d0c3f09`
- Companion SHA-256: `a6eb652d52906b1bf8e5dc5272edb792f443adc3a3cc5ad9a59ae260c433ec5f`
- Extraction method: 主版本使用 embedded text；官方长稿为 59/59 无文本层图片 PDF，仅在 `tmp/` 以 `chi_sim+eng`、220 DPI、PSM 3 OCR 辅助全页审查，未建立第二份 corpus distillation
- Extraction quality: 主版本 17/18 页正文可读，控制字符来自数学排版和重复标题，关键公式、图表已视觉核验，故无需 OCR。长稿 OCR 可检索但代码标点和公式均以页图为准。
- Page convention: 1-based physical PDF pages；“伴随 pXX”表示 59 页官方展示长稿
- Visually checked pages: 主版本 p1、p4、p6、p9、p11、p13--16；伴随 p1、p21--22、p24、p41、p52--55、p59。伴随 p1--59 均经页级 OCR 全范围审查。
- Unresolved extraction ambiguities: 主版本中央证据可读。长稿代码只以页图存在，少数标点不适合自动转写；缺少输入 Excel、网络 `.mat`、Origin 工程和运行日志。
- Supplemental artifacts: 伴随 p27--59 给出部分 `sandian.m`、`tuxiang*.m`、`A12B1.m`、`main.m`、`pre_main.m`、`reglm.m`、`myNeuralNetworkFunction.m`、`real_sim.m`、`regress.m` 页面。清单中的附件1、`ml.csv`、`ml_x.mat`、`ml_xx.mat`、`ml_y.mat`、Origin/Word 文件均不可得。

## 1. Problem Archetype

本文属于“稀疏实验数据曲线拟合 + 高维回归特征工程 + 小样本神经网络响应面 + 实验设计”的混合原型：

1. 对 21 个催化剂组合分别拟合温度--转化率/选择性曲线。
2. 将催化剂拆成 5 个数值变量，加温度共 6 个自变量，对 114 条观测做逐步回归、非线性变换和交互项扩展。
3. 用 5 输入、5 隐藏神经元的 BP 网络预测 C4 烯烃收率，并在离散笛卡尔积中搜索最大预测值。
4. 用所谓“加权欧式距离”选择远离已有 114 个实验的设计点，再提出 5 次实验。

它展示了从解释模型到预测模型再到实验设计的完整框架，但存在小样本过拟合、共线性判据反向、错误线性化、随机行切分泄漏风险和实验设计目标错位。所有“最优”均是有限网格或边界处的模型预测，不是实验验证后的全局最优。

## 2. Problem Decomposition

- **问题一 A：** 每个催化剂组合分别比较线性/指数转化率模型和三/四次选择性多项式，并按曲线类型分类。
- **问题一 B：** 对 350°C 单次实验的时间序列拟合指数衰减，解释主/副反应进程。
- **问题二：** 比较 A12/B1 两种装料方式；构造 6 个自变量、2 个因变量；从线性逐步回归升级为变换、二次交互和 z-score 标准化。
- **问题三：** 删除可由质量推知的装料比，保留 5 个网络输入；70/15/15 随机行切分，Bayesian regularization 训练 5 隐藏神经元网络；枚举离散输入组合寻找全温度和 `T≤350°C` 的最大预测收率。
- **问题四：** 最大化到 114 个既有实验的带权平方距离，选取三个探索点；另复制问题三的两个预测最优点作拟议验证实验。

关键接口问题是：问题二的 PCA 叙述没有明确进入最终方程；问题四的距离目标不含神经网络预测收率，却被解释为“全局收率峰值”。

## 3. Data Processing

- 数据有 21 个催化剂组合、114 条实验观测；多数单组仅 5 个温度点。
- A5/A6 在 275°C 的轻微下降因文献机理与误差判断被“忽略”，没有给异常阈值或保留/删除对照。
- 仅凭 A12/B1 一个匹配组合的曲线相似，就合并两种装料方式；没有效应检验、等效界或统计功效。
- 六个基础变量扩展为 28 个候选预测项：线性项、平方/交互项和 `T^3`。114/28=4.07 个样本/候选项，随后逐步选择，没有嵌套验证。
- 回归变量做 z-score；实验设计变量另做 Min-Max 标准化。
- BP 网络按行随机拆为约 80/17/17。相同催化剂组合的不同温度点可同时落入训练和测试，测试 R 主要反映组内插值，未做催化剂组级留出。
- `real_sim.m` 活跃取值只枚举 `4×5×4×4×7=2240` 个组合；代码注释中还有被删去的质量取值，故并非所有原始边际取值的完整笛卡尔积。

## 4. Models Used

### 分组曲线拟合

**Purpose:** 描述每一催化剂组合的温度响应并分类。

**Inputs:** 每组约 5--7 个温度点与转化率/选择性。

**Outputs:** 线性或指数转化率曲线、三次选择性曲线和 5 类组合。

**Why selected:** explicit；作者根据散点形状和 B1/A10 的 R² 比较选择函数族。

**Important assumptions:** 每组曲线在观测区间内平滑，三次多项式足以描述峰值。

**Key equations or mathematical structure:** `y=ax+b`、`y=A exp(T/t)+y0`、三次多项式。

**Implementation notes:** A10 四次多项式以 5 点得到 R²=1 被正确识别为插值；但三次模型仍有 4 参数、在 5 点组仅 1 个残差自由度，R²高度乐观。

### 逐步回归、非线性变换和交互项

**Purpose:** 分析催化剂组成和温度对转化率、选择性的联合影响。

**Inputs:** 6 个基础变量与 114 条观测。

**Outputs:** 标准化转化率/选择性方程，调整 R²=0.934994/0.802786。

**Why selected:** explicit；初始线性模型调整 R²仅约0.79/0.68，作者逐步增加结构。

**Important assumptions:** 高斯--马尔可夫误差；逐步 p<0.05；R²≥0.8 即可接受。

**Key equations or mathematical structure:** `log(y1)`、`T^3`、所有 `x_i x_j (i≤j)`、z-score 标准化。

**Implementation notes:** 原指数模型含加性 `y0`，因此 `log(A exp(T/t)+y0)`并不对 T 线性；VIF 判据也被写反。附录同时试验 LASSO/PCA/PLS，但最终使用哪条路径缺少明确运行记录。

### PCA / 共线性诊断

**Purpose:** 降低 28 个候选项间的共线性。

**Inputs:** 标准化扩展矩阵。

**Outputs:** 主成分回归候选。

**Why selected:** explicit；作者认识到交互项造成信息重叠。

**Important assumptions:** 主成分能保留响应相关信息。

**Key equations or mathematical structure:** tolerance `1-R_i²`、VIF `1/(1-R_i²)`。

**Implementation notes:** 主文错误地认为 `R_i²≥0.8` 时可采用回归；此时 tolerance≤0.2、VIF≥5，恰是较强共线性。代码注释称删除不显著 PC2，随后仍使用全部 `[1:28]` 主成分。

### BP 神经网络响应面

**Purpose:** 预测收率并在输入组合中寻找最大值。

**Inputs:** Co/SiO2质量、HAP质量、Co负载量、乙醇浓度、温度。

**Outputs:** C4 烯烃收率及两个 best-found 组合。

**Why selected:** explicit；非线性规划被称结果误差大，作者选择具有非线性映射能力的 BP。

**Important assumptions:** 随机行测试能代表泛化；离散笛卡尔积中的组合化学可行；网络在边界附近可靠。

**Key equations or mathematical structure:** 5 隐藏神经元 `tansig`，线性输出，Bayesian regularization。

**Implementation notes:** 约 36 个参数、约 80 个训练行；训练 R=0.98815、测试 R=0.94222、全体 R=0.98397。无 seed/重复分布；`real_sim.m` 使用未在脚本内定义的 `net`，依赖缺失 `.mat` 工作区。

### 加权距离实验设计

**Purpose:** 选择远离已有实验的探索点并安排三次“峰前/峰值/峰后”实验。

**Inputs:** 5 个 Min-Max 变量和网络衍生权重 `[22.83,35.90,-4.44,-10.90,69.99]`。

**Outputs:** 500/500/0.01/0.9/450 附近的点及 400/400/400、500/500/450、600/600/500 三个实验。

**Why selected:** explicit；作者希望扩大设计空间并寻找未覆盖区域。

**Important assumptions:** 权重符号/大小可作为实验空间距离，最大距离点对应更高收率峰值。

**Key equations or mathematical structure:** 最大化 `sum_j sum_i w_i(x_i*-x_ji)^2`。

**Implementation notes:** 两个权重为负，目标不是欧氏距离平方；目标中没有预测收率，因此不能推出收率峰值。600 mg 与 500°C 还超出网络训练范围。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 线性转化率曲线 | selected for some groups / rejected for B1 | 温度响应 | 按散点形状 | B1 R²=0.90075 | hold-out、AIC、残差 | 只有约5点，模型选择不稳定 |
| 指数转化率曲线 | selected for some groups | 温度响应 | B1 R²=0.99959 | 与线性同样本比较 | offset-aware linearization、外推检查 | 样本内拟合强，后续取对数处理错误 |
| 四次选择性多项式 | rejected | 描述峰值 | 5点得到R²=1只是插值 | A10图6 | leave-one-out预测 | 拒绝理由正确 |
| 三次选择性多项式 | selected | 描述峰值 | 比四次更平滑 | A10 R²=0.98291 | 低阶/机理/样条基线 | 5点时残差df=1，仍高度过拟合 |
| 装料方式作为特征 | rejected | A/B组差异 | A12/B1曲线视觉接近 | 一对匹配组合图 | 等效检验、多组合重复 | 不足以得出“无显著影响” |
| 基础线性回归 | rejected | 多因素解释 | 调整R²=0.79/0.68低于作者0.8阈值 | 样本内R² | 外部预测指标 | R²阈值是作者选择，不是有效性证明 |
| 变换+交互逐步回归 | selected | 提高拟合 | 调整R²升至.935/.803 | 同样本拟合 | 嵌套选择、hold-out、残差/影响点 | 28候选项和逐步选择有过拟合/多重检验风险 |
| PCA/PLS/LASSO | considered / implementation role unclear | 共线性处理 | 减少信息重叠 | 代码存在 | 最终模型选择证据和主成分表 | 主文称PCA但最终方程更像逐步原变量回归 |
| 回归方程乘积 | rejected | 收率优化 | 作者称R²显然低于NN | 未计算 | 实际乘积预测与独立测试 | 两个R²不能推出乘积R²，拒绝论证无效 |
| 5神经元 Bayesian BP | selected | 收率预测 | 大量尝试后效果较好 | 单次随机测试R=.94222 | 其他神经元/基线、重复seed、组级CV | 有holdout但样本小、组泄漏风险高 |
| 加权距离最大化 | selected | 新实验探索 | 寻找远离现有实验的点 | none | 与最大预测方差、D-optimal、EI比较 | 不能被解释为收率全局最优 |

## 5. Model Pipeline

`114条实验 → 分组温度曲线 → 6基础变量 → 非线性/二次交互扩成28候选项 → 逐步回归与诊断 → 5输入BP网络 → 2240个离散组合枚举 → 两个边界best-found点 → 加权距离探索点 + 两个拟议验证点`。

管线的主要断点：

- 取对数线性化没有处理指数模型的加性常数。
- PCA/PLS/LASSO代码与最终主文方程缺少明确接口。
- 网络测试为随机行拆分，不是催化剂组级外推验证。
- 问题四的距离目标没有调用网络预测收率，却被写成收率峰值搜索。
- 五次实验只是设计，没有实际实验结果，不能作为前三问的已完成验证。

## 6. Model Improvements

1. **拒绝 5 点四次插值。** 识别 R²=1 并不等于泛化，是正确的模型复杂度警觉。
2. **从基础线性模型加入结构。** 将温度立方项、交互和标准化引入，改善样本内拟合。
3. **从解释回归切换到非线性预测。** BP 用于收率响应面，避免直接乘两个回归方程的接口误差。
4. **保留独立测试子集。** 网络至少报告测试 R，而不是只报训练拟合；但拆分单位应改为催化剂组。
5. **探索与验证混合设计。** 三个拓展点加两个预测点的意图合理；距离目标和外推边界需要重构。

## 7. Parameter Estimation and Optimization

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| sample size | 实验观测数 | rows | p14--15 | 114 | problem-provided | N/A - given | no | 21个催化剂组 |
| cubic degree | 选择性温度曲线次数 | degree | p4 | 3 | algorithm hyperparameter | visual/R² comparison to quartic | partial | 多数组5点，仅1残差df |
| stepwise threshold | 变量进入/剔除显著性 | probability | p10 | p<0.05 | algorithm hyperparameter | author setting | no | 未做多重选择修正 |
| candidate feature count | 线性/平方/交互/T³ | features | p11；伴随 p41 | 28 | algorithm hyperparameter | exhaustive expansion | no | 114/28=4.07 |
| acceptable R² | 回归接受阈值 | dimensionless | p11 | 0.8 | author-assumed | author criterion | no | 不能替代预测验证 |
| train/validation/test split | BP数据划分 | percent | p13 | 70/15/15 | algorithm hyperparameter | MATLAB random row split | no | seed未报；图只明确Train/Test/All R |
| hidden neurons | BP隐藏层大小 | neurons | p13 | 5 | algorithm hyperparameter | “大量尝试” | no | 未给候选、重复或选择曲线 |
| training method | BP优化 | N/A | p13 | Bayesian regularization | algorithm hyperparameter | author choice | no | 第493 epoch作为高温网络结果 |
| search grid | `real_sim.m`离散笛卡尔积 | combinations | 伴随 p54--55 | 2240 | algorithm hyperparameter | nested exhaustive loops | no | 省略部分注释中的质量取值 |
| low-temperature bound | 低温定义 | °C | p14 | `T≤350` | author-assumed | interpretation of wording | no | best-found命中350边界 |
| network optimum | 全范围预测best-found | % | p14 | 51.31 at 450°C | data-estimated | grid over trained network | no | 450为搜索上界 |
| low-T optimum | 低温预测best-found | % | p14 | 38.47 at 350°C | data-estimated | restricted grid | no | 350为约束上界 |
| distance weights | 实验设计变量权重 | dimensionless | p15 | 22.83,35.90,-4.44,-10.90,69.99 | data-estimated | described as neural-network weights | no | 负值使“距离平方”非度量 |
| proposed exploration bounds | 新实验质量/温度 | mg / °C | p15--16 | up to 600 mg, 500°C | author-assumed | boundary exploration | no | 超出网络训练 x1≤200 mg、T≤450°C |

## 8. Validation

网络有随机行测试集，这是本文最接近独立预测验证的证据；但约 17 条测试行与训练行共享催化剂组，不能评估新组合泛化。回归、分组曲线和所谓“问题三检验”主要是样本内 R²。五次实验从未执行。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| B1转化率函数族 | L1 - same-sample fit comparison | same sample | R² | 5点 | 线性.90075，指数.99959 | none reported | 仅5点、无holdout | 支持B1观测区间内指数拟合更贴合 |
| A10选择性函数族 | L2 - complexity sanity check | same sample | R²与参数数 | 5点 | cubic .98291，quartic 1 | quartic完全插值 | cubic也只有1残差df | 支持拒绝quartic，不充分证明cubic泛化 |
| A/B装料方式 | L2 - matched visual comparison | same sample | 三条响应曲线 | 1对组合 | A12/B1视觉接近 | none reported | 无统计检验/重复 | 只支持该一对条件相似 |
| 最终回归 | L1 - in-sample adjusted fit | same sample | adjusted R² | 1 | .934994/.802786 | 无holdout | 逐步选择同数据、28候选项 | 支持样本内解释，不支持外推 |
| BP收率网络 | L5 - random-row holdout | hold-out | Pearson R | 1 split，seed未报 | train .98815，test .94222，all .98397 | 低温网络另一次训练到边界解 | 测试约17行、催化剂组泄漏、无重复 | 支持同分布随机行插值相关性较高 |
| BP残差 | L1/L2 - histogram and training curves | same sample | MSE/gradient/error histogram | 1 run | epoch493稳定 | 极端残差可见但未量化 | MSE为原始百分比乘积尺度 | 只支持该次训练收敛 |
| 五次实验 | not assessable | unknown | 实验误差 | 0 | proposed but not implemented | N/A | 只有设计，无测量 | 不能称已验证前三问 |

在已审查主文 p1--17、伴随 p1--59 和全部可得支撑代码范围内，未发现重复随机划分、催化剂组级交叉验证、预测区间、外部实验结果、五次实验观测或实验设计敏感性。

## 9. Sensitivity and Robustness

论文没有实施参数敏感性或稳健性实验。作者只在误差分析中承认：隐藏神经元数、重复训练和实验设计权重变化会改变结果。这些是风险声明，不是扰动证据。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|

在已审查范围内，未发现对神经元数、随机 seed、训练/测试划分、温度/质量边界、回归项选择、负权重或输入噪声的实际扰动结果。审查范围为主版本 p1--17、伴随 p1--59；缺失 `.mat`、Excel 和运行日志。

## 10. Visualization Strategy

- 42 张分组散点/拟合图支撑函数族分类，代表图降低篇幅。
- A12/B1 三指标对比图用于装料方式讨论，但视觉相似不等于无显著效应。
- 回归系数误差条、调整历史和主成分/残差图展示模型诊断；正文没有量化残差异方差或影响点。
- BP performance、training state、error histogram 和 regression 图给出训练过程；测试 R 可从伴随 p22 直接读出。
- 五维实验设计没有画预测收率或不确定性，只给距离目标和五个点，难以验证“峰前/峰后”。

## 11. Writing Structure

论文按“分组曲线 → 时间规律 → 多因素回归 → BP优化 → 新实验设计”递进，期刊增刊版文字压缩、官方长稿保留代码和图，二者互补。

主要写作问题：

- 用高 R² 多次替代预测验证，并把 `R_i²≥0.8` 的共线性判据写反。
- 把拟议实验写成“能够验证”而非“若执行可验证”。
- 声称两个回归方程乘积的 R²“显然”低于0.98，没有数学依据。
- 把最大加权距离解释成收率全局峰值，目标函数与结论不对应。
- “全局最优”点和低温最优点均命中搜索边界，却未披露边界最优风险。

## 12. Strengths

1. 正确认识 5 点四次多项式 R²=1 是插值，不把它当泛化优势。
2. 清楚拆分催化剂组合变量，并同时考虑主效应、非线性和交互项。
3. 至少保留网络测试子集并报告测试 R，而非只有训练曲线。
4. 主文主动承认重复训练不稳定、权重不确定和回归仍可提升。
5. 官方长稿提供固定网络权重和预处理常数，便于公式--代码审计。
6. 实验设计同时包含探索点和预测点，研究意图合理，若重构目标可迁移。

## 13. Weaknesses

1. 每组约5点用三次多项式，残差自由度通常只有1；编辑按也明确指出次数偏高。
2. A/B装料方式只比较A12/B1一对，不能得出“无显著影响”。
3. 对 `A exp(T/t)+y0` 直接取log并宣称关于T线性，在 `y0≠0` 时错误。
4. 把 `R_i²≥0.8` 当可接受共线性；这实际意味着VIF≥5。
5. 114行上生成28候选项并逐步选择，无嵌套验证；标准化系数大小在存在交互时也不能简单等同单变量影响。
6. BP只有单次随机行切分，约36个参数对约80个训练行，且同催化剂组跨集合。
7. 两个最优点命中温度上界；`real_sim.m`还省略部分输入取值并依赖未定义`net`。
8. 加权距离含负权重且不含收率预测，不能发现收率峰；600mg/500°C严重外推。
9. `regress.m`只对前8/114行取log后就标准化并计算收率响应，问题四代码不可作为可靠实现。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable in repository | 主文引用附件1/2；伴随清单 | 不能重跑拟合、训练或实验设计 |
| Code availability | partial | 伴随 p27--59 页面代码 | Origin工程、`.mat`、输入表和若干脚本无代码 |
| Dependency / environment information | partial | MATLAB/Origin/Neural Net Fitting可识别 | 版本、toolbox版本、OS未报 |
| Random seed | not reported | 网络随机划分/初始化 | 测试R与最优值不可重复统计 |
| Hard-coded constants | extensive | 伴随 p37--59 | 114行映射、输入网格、权重、网络参数硬编码 |
| Formula-to-code consistency | mixed with material failures | 主文 p11,p15 vs伴随 p41,p54--59 | PCA使用不清、网格不完整、距离目标不等于收率、log 8行错误 |
| Code-to-result consistency | partially assessable | 固定网络函数及`real_sim` | `net`依赖缺失.mat；可见函数未被`real_sim`直接调用；无运行输出 |
| Overall reproducibility | partially reproducible | 主文+59页伴随全范围 | 固定网络可人工重建；原始训练、回归与实验设计结果不可完整复现 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 催化剂分类计数 | 5类覆盖21组合 | 4+1+13+1+2=21 | pass | p6 table1 | 分类数闭合 |
| A10模型自由度 | cubic R²=.98291优于quartic R²=1 | 5点cubic有4参数/1残差df；quartic 5参数/0残差df | concern | p4 figure6 | 拒绝quartic正确，cubic仍极弱 |
| 共线性判据 | `R_i²≥.8`可采用方程 | `VIF=1/(1-R_i²)≥5` | fail | p11 paragraph | 判据方向反了 |
| 指数线性化 | `y=Ae^(T/t)+y0`后`log(y)`线性 | 加性`y0`使log-sum-exp非线性 | fail | p11 eq.1 and paragraph | 应拟合offset或变换`log(y-y0)` |
| 样本/候选项 | 114行、28扩展项 | 114/28=4.07 | concern | p11 / companion p41 | 逐步选择过拟合风险高 |
| 网络规模 | 5输入5隐藏1输出 | 25输入权重+5隐藏偏置+5输出权重+1偏置=36；约80训练行=2.22行/参数 | concern | p13 / companion p52--53 | Bayesian正则化不能替代重复外部验证 |
| 网络测试R | 三组R接近1 | test R=.94222，低于train .98815；all .98397 | pass with limitation | companion p22 figure | 测试相关性高，但非组级独立 |
| 回归乘积R² | 两回归相乘的R²显然<.98 | 单个R²不能决定乘积预测R² | fail | p16 section3.1 | 必须实际复算 |
| 离散搜索规模 | 遍历所有组合 | 活跃代码4×5×4×4×7=2240，注释中有未用质量值 | concern | companion p54--55 | “所有取值”边界不清 |
| 全温度最优 | 51.31% at 450°C | 450为活跃温度网格最大值 | concern | p14 / companion p54 | 边界解，不证明内部峰值 |
| 低温最优 | 38.47% at 350°C | 350为约束上界 | concern | p14 | 边界解，需要350附近/以上验证 |
| 加权距离 | 目标为欧氏距离平方 | 权重含-4.44和-10.90，可能产生负“平方距离” | fail | p15 eq./Weight | 不是距离度量 |
| 实验设计目标 | 最大距离得到收率全局峰值 | 目标函数没有收率项或网络预测 | fail | p15 section2.5.2 | 只能选远离样本的边界点 |
| 外推尺度 | 建议600mg、500°C | 网络mapminmax中200mg/450°C映到1；600mg映到5.21，500°C映到1.5 | concern | p16 / companion p52--54 | 明显超出训练归一化范围[-1,1] |
| 问题四log循环 | 对选择性取log后回归收率 | 代码仅`for i=1:8`，其余106行未取log | fail | companion p59 code | 响应列混合尺度 |

## 14. Reusable Techniques

### 低阶模型与插值模型对照

**When useful:** 每组实验点极少，需要避免“完美拟合”诱惑。

**Why useful:** 明确展示四次多项式在5点上R²=1只是插值。

**Limitations:** 还需leave-one-out、机理约束或更低自由度模型。

### 分层特征工程

**When useful:** 综合实验条件可拆成质量、比例、浓度和温度。

**Why useful:** 主效应、非线性和交互的来源可解释。

**Limitations:** 扩展后必须用正则化/嵌套验证，并正确审计VIF。

### 解释回归与预测网络双轨

**When useful:** 既需因素解释，又需非线性响应面优化。

**Why useful:** 回归负责效应方向，网络负责预测，不强迫一个模型完成所有任务。

**Limitations:** 两条管线必须用共同外部测试比较，不能只比样本内R²。

### 催化剂组级验证

**When useful:** 同一组合在多个温度重复出现。

**Why useful:** 按组留出能测试对新催化剂组合的真正泛化，避免行级泄漏。

**Limitations:** 组数仅21，需要重复grouped CV并报告不确定性。

### 探索点加验证点的实验组合

**When useful:** 预算仅5次，既想拓展设计空间又要检验预测最优。

**Why useful:** 3+2结构兼顾探索与确认。

**Limitations:** 探索准则应使用非负距离/预测方差/期望改进，并受安全物理边界约束。

## 15. Competition Takeaways

1. 五点数据不要用三次曲线后仅凭R²分类；至少报告残差df和leave-one-out误差。
2. 写VIF时用 `R_i²` 越高共线性越强，检查不等号方向和阈值。
3. 含加性offset的指数模型不能直接对响应取log线性化。
4. 逐步回归和神经网络都要在催化剂组级交叉验证，避免同组温度点泄漏。
5. 优化前报告网格范围；最优点命中边界时写“边界best-found”，并扩域或补实验。
6. “欧式距离平方”权重必须非负；实验设计目标必须与预测收率或信息增益对应。
7. 新实验超出训练范围时，先做安全/机理审查和分阶段扩展，不直接外推到3倍质量。
8. 拟议实验不能写成已完成验证；结果回来后再更新Validation等级。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 主版本为湖南大学期刊增刊，官方长稿提供代码附录 | interpretation | 主1；伴随1,27--59 | metadata / appendix | paragraph / code | derived interpretation | N/A for positive evidence | 同题同作者同核心结果；主文作primary |
| B1指数拟合R²=.99959高于线性.90075 | explicit | 3--4 | 2.1.1 | figure5 / paragraph | direct transcription | N/A for positive evidence | 5点样本内 |
| A10四次拟合5点R²=1被作者识别为插值 | explicit | 4 | 2.1.1 | figure6 / paragraph | direct transcription | N/A for positive evidence | cubic仍仅1残差df |
| 21组分类计数闭合 | interpretation | 6 | table1 | table | independent calculation | N/A for positive evidence | 4+1+13+1+2=21 |
| A12/B1视觉相似被用来合并装料方式 | explicit | 9 | 2.3.1.1 | figures14--16 / paragraph | direct transcription | N/A for positive evidence | 仅一对，无显著性检验 |
| 回归基础假设包括正态同方差和无共线性 | explicit | 10 | 2.3.1.3 | paragraph | direct transcription | N/A for positive evidence | 后文又称出现强共线性 |
| 作者把R_i²≥.8当作可接受回归 | explicit | 11 | 2.3.1.5 | paragraph / formula | direct transcription | N/A for positive evidence | 与VIF定义同页 |
| `R_i²≥.8`意味着VIF≥5，判据方向错误 | criticism | 11 | 2.3.1.5 | formula / paragraph | independent calculation | p11完整共线性段 | 高R²代表强共线性 |
| 对含offset指数响应直接取log线性化 | criticism | 11 | 2.3.2 | equation1 / paragraph | derived interpretation | p11公式与紧随变换说明 | `y0≠0`时不线性 |
| 114条观测生成28个候选项 | explicit | 11；伴随41 | regression / code | equation / code | direct transcription | N/A for positive evidence | 比率4.07 |
| 最终回归调整R²为.934994/.802786 | explicit | 16 | 3.1 | paragraph | direct transcription | N/A for positive evidence | 样本内/逐步选择后 |
| 两个回归R²不能推出乘积收率R²低于.98 | criticism | 16 | 3.1 | paragraph | derived interpretation | p16完整比较段 | 必须实际计算乘积预测 |
| BP使用5输入、5隐藏神经元和Bayesian regularization | explicit | 13 | 2.4.1 | paragraph / network | direct transcription | N/A for positive evidence | 参数约36 |
| 网络随机行测试R=.94222 | explicit | 伴随22 | 5.4.1.3 | figure | direct transcription | N/A for positive evidence | train .98815, all .98397 |
| 在已审查范围内未发现seed或重复划分结果 | criticism | 主13--16；伴随20--22,52--55 | BP training | none found | derived interpretation | 两版本训练段与全部网络代码；`.mat`不可得 | 论文自承重复训练不稳定 |
| 全范围51.31%点位于450°C网格上界 | criticism | 14；伴随54 | 2.4.1.4 / real_sim | paragraph / code | independent calculation | p14结果与p54温度数组 | boundary best-found |
| 低温38.47%点位于350°C约束上界 | criticism | 14 | 2.4.2 | paragraph | derived interpretation | p14完整低温结果 | 不能证明内部最优 |
| real_sim活跃网格有2240组合且省略部分注释值 | criticism | 伴随54--55 | real_sim.m | code | independent calculation | p54--55完整循环与数组 | 4×5×4×4×7 |
| real_sim依赖未定义net及缺失.mat | criticism | 伴随52--55 | support list / code | code / none found | direct transcription | p52清单、p54--55脚本；工作区文件不可得 | 固定函数未被脚本直接调用 |
| 实验设计权重含两个负值 | explicit | 15；伴随24 | 2.5.2 | equation / paragraph | direct transcription | N/A for positive evidence | -4.44,-10.90 |
| 负权重使目标不是欧式距离平方 | criticism | 15 | 2.5.1--2.5.2 | equation / weight vector | derived interpretation | p15完整目标和权重 | 可产生负贡献 |
| 最大距离目标不含收率，不能定位收率峰 | criticism | 15 | 2.5 | equation / paragraph | derived interpretation | p14--16完整实验设计 | 目标--结论断裂 |
| 600mg/500°C超出网络训练范围 | criticism | 16；伴随52--54 | experiments / network preprocessing | paragraph / code | independent calculation | p16点位、p52输入offset/gain | 归一化映射为5.21和1.5 |
| 五次实验只是提出，未报告观测 | criticism | 14--16 | 2.5 / 3 | none found | derived interpretation | 主文全部验证/误差段、伴随p23--26；支撑材料不可得 | proposed but not implemented |
| 问题四代码只对前8行取log | criticism | 伴随59 | regress.m | code | direct transcription | p55--59完整代码 | 其余106行响应尺度不同 |
| 在已审查范围内未发现实际敏感性实验 | criticism | 主1--17；伴随1--59 | sensitivity | none found | derived interpretation | 两版本全文、所有可得代码 | 仅有误差风险陈述 |
| 原始训练不可复现，固定网络可部分重建 | criticism | 伴随27--59 | appendix | code / none found | derived interpretation | 全附录；Excel/.mat/Origin不可得 | overall partially reproducible |
