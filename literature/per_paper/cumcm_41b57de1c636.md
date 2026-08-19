# Paper: 基于小波变换和背包模型的小浪底水库最优监测方案研究

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_41b57de1c636
- Year: 2023
- Problem: E（本地及官方展示代码 E176）
- Award: 组委会官方展示匹配，具体奖级未独立核验；不由文件名或展示状态推断奖级
- Provenance tier: O: 年份、题号、页数与官方展示记录匹配，奖级未知
- Source file: literature/raw_papers/2023/E176.pdf
- Source URL: unknown
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2023qgdxssxjmjslwzs_2023etlw/231104/1865138.shtml
- Pages: 56
- SHA-256: 1b0fbd065535cb56dfdcc4daa0f8331eef29dafd9ab99119bf769514df0e278e
- Extraction method: embedded text（pypdf 6.10.0）+ manual visual review；未使用 OCR
- Extraction quality: `poor_quality / needs_review`，原因是控制字符比例 0.007029；56/56 页均有文本，正文总体可读（43,677 个可见字符，中位数 725 字符/页），公式、图表和代码另以渲染页核验
- Page convention: 1-based physical PDF pages
- Visually checked pages: 1-56 全文缩略图；重点核验 p.6-8 回归式与表 2-4、p.12 M-K/Fisher、p.15-17 R/S 与 Fourier、p.18-19 0-1 模型及表 11、p.20-21 图 38-41 与 GM(1,1)、p.23-24/26/28/31-32/45-49/53/55-56 附录代码
- Unresolved extraction ambiguities: 正文关键式、表和结论已由渲染页消歧；附录长代码存在 PDF 换行造成的语句断行，但本文所列关键变量、循环范围和公式均在原页可辨
- Supplemental artifacts: p.23-56 内嵌 Python、MATLAB、LINGO 代码；代码引用的 Excel/MAT 数据、`y2023.txt`、自定义模块和软件环境未作为独立文件提供，因而不可直接运行

## 1. Problem Archetype

本文是一个混合型水文数据建模任务，包含：

- 统计回归与弹性解释：用双对数回归分别描述含沙量与水位、水流量的关系；
- 水文时间序列描述：用季节指数、正弦拟合、Mann-Kendall（M-K）检验、Fisher 有序聚类和小波变换描述季节、周期和突变；
- 预测：用重标极差分析（Rescaled Range Analysis, R/S）判断持续性，用 Fourier 级数预测未来 24 个月；
- 离散决策：把监测月份选择写成最小基数的 0-1 覆盖模型；
- 河道断面计算与外推：用梯形面积近似计算河底高程/流量，并用 GM(1,1) 外推 10 年。

高价值部分在于“描述—检测—预测—监测决策”的完整接口；主要风险也集中在接口处：时间单位、日/月聚合、预测参数化和代码实现并不完全一致。

## 2. Problem Decomposition

论文按四问串联：

1. 清洗 2016-2021 年数据，研究含沙量与时间、水位、水流量的关系，并估算年度水流量、排沙量；
2. 将数据聚合为 72 个月序列，分别描述统计特征、季节性、周期性和突变性；
3. 用 R/S 判断趋势方向，用 2018-2020 年拟合 Fourier 级数、2021 年留出检验，再预测 2022-2023 年；依据相邻月变化量建立 0-1 监测选择模型；
4. 从断面测点计算河底高程、水通量和沙通量，比较“调水调沙”时点，并用 4 个年增量拟合 GM(1,1)。

该分解覆盖了题目要求，但数据聚合代码把每月固定为 30 天，与正文“一年 365 天”的设定冲突，使四问共享的数据底座存在系统性偏差。

## 3. Data Processing

论文称先补齐日期，再对缺失值作填补并剔除离群点。这里存在三层证据边界：

- 摘要 p.1 写“采用平均值填补”，p.3 §5.0 写“用邻近值代替”，两者口径不同；附录展示的格式转换代码只复制工作表，未展示具体填补规则。
- p.4 的离群点由自定义 `liqundian3` 识别，附录给出 `k1=1.5, k2=3`，但未给函数定义；另一些正弦拟合直接删除最大 3 个或 7 个含沙量值，属于作者设定的单侧截尾，未评估对回归与周期结论的影响。
- MATLAB 多处使用 `for k=1:30`，形成 `30×12×6=2160` 个日单元；这会忽略每月第 31 天，并使 2 月第 29/30 日的空集合处理不明。Python 年度汇总代码也只累加 `G2:G361` / `H2:H361` 共 360 行。

附录还显示：日汇总最后一日把 `water_level_sum` 而非 `flow_sum` 用于径流量；月汇总对日径流量取平均而非月内求和；部分含沙量缺失被先记为 0 再按固定 5 点平均。这些实现会改变水沙通量及其后续检验输入。

## 4. Models Used

### 双对数一元回归

**Purpose:** 估计含沙量相对水位、流量的弹性。

**Inputs:** 日尺度含沙量、水位或水流量；离群点剔除后的同一样本。

**Outputs:** 回归系数、95% 置信区间、R²、F 检验和残差图。

**Why selected:** 论文先观察散点图；因水位与流量高度相关，拒绝同时进入二元回归，分别建立两个双对数模型。

**Important assumptions:** 误差独立、同方差、正态；对数变量为正；剔除规则不会扭曲关系。

**Key equations or mathematical structure:** `ln y = β0 + β1 ln x + ε`。水位模型 `β1=36.31, R²=0.5797`；流量模型 `β1=1.06, R²=0.8013`。

**Implementation notes:** MATLAB `regress(log(y),[ones(n,1),log(x)],0.05)`；残差标准化使用 `sqrt(stats(4))`。未提供完整输入数据和 `liqundian3`。

### 周期、突变与多尺度分析

**Purpose:** 描述 72 个月水沙通量的季节、周期和变点。

**Inputs:** 月尺度水通量、沙通量。

**Outputs:** 月份指数、12 月正弦拟合、M-K 的 UF/UB 曲线、Fisher 两类分割、小波等值线和方差图。

**Why selected:** M-K 用于非参数趋势/突变识别；Fisher 用于独立的有序分割；小波用于局部时频尺度。

**Important assumptions:** 月序列可由 30 日固定聚合代表；正弦周期固定为 12；小波图的尺度峰可解释为实际周期。

**Key equations or mathematical structure:** `p(t)=22.76 sin(2πt/12-2.44)+34.54`；沙通量类似。M-K 临界线取 ±1.96。

**Implementation notes:** M-K 代码未处理 ties；Fisher 代码固定 `m=2`，没有展示类别数选择过程；小波仅给出 MATLAB App 操作和系数平方求和。

### R/S 与 Fourier 预测

**Purpose:** 判断持续/反持续特征，并预测 2022-2023 年水沙通量。

**Inputs:** R/S 使用 24、48 或 72 个月片段；Fourier 使用 2018-2020 年 36 点训练、2021 年 12 点检验。

**Outputs:** Hurst 指数；10 阶 Fourier 系数；拟合 RMSE、留出 RMSE；未来 24 点预测。

**Why selected:** 论文以 R/S 表征长期记忆，以 12 月周期为理由选 Fourier 逼近。

**Important assumptions:** 周期和波形跨年稳定；高阶谐波可识别；预测值可直接用于小波和监测决策。

**Key equations or mathematical structure:** 10 阶 12 月周期 Fourier 展开，共常数项及 20 个正余弦系数；RMSE 见式 (17)。

**Implementation notes:** 附录 R/S 代码对原始 `n` 与 `R/S` 做 `polyfit`，并未对 `ln(n)` 与 `ln(R/S)` 回归；`m=size(x); p=m/n` 也不是可执行的标量分段数。Fourier 设计矩阵 36×21 的数值秩仅 12，系数不唯一。

### 0-1 最小监测模型

**Purpose:** 在保留至少历史平均动态信息量的前提下，最少选择监测月份。

**Inputs:** 预测序列相邻月绝对差 `y_{t+1}=|x_{t+1}-x_t|`，并令 `y1=y2`；阈值 `ȳ=10.8` 亿 m³。

**Outputs:** 12 个二元选择变量；2022、2023 年均仅 5 月不监测。

**Why selected:** 论文把变化量视作信息价值，把监测次数视作成本，形成最小基数覆盖问题。

**Important assumptions:** 水、沙通量变化趋势相同，因此只优化水通量；相邻差绝对值足以衡量信息；两年预测严格重复。

**Key equations or mathematical structure:** `min Σz_t`, s.t. `(1/12)Σz_t y_t ≥ ȳ`, `z_t∈{0,1}`。

**Implementation notes:** LINGO 代码与式 (22) 一致。独立算术确认表 11 的 11 次监测为该单约束模型的最小基数解。

### 断面梯形积分与 GM(1,1)

**Purpose:** 估计河底高程、水沙通量，并外推无调水调沙时的 10 年河底高程。

**Inputs:** 断面起点距、水深、流速、含沙量；4 个跨年河底高程增量。

**Outputs:** 图 38-40 的断面指标；表 14 的 10 年预测，末值 64.79 m。

**Why selected:** 梯形面积近似适合离散断面测点；论文因增量序列只有 4 点而选择小样本 GM(1,1)。

**Important assumptions:** 测点间线性变化；4 点增量足以支持 10 年指数型外推；平移 `z0=1` 不改变有效动力结构。

**Key equations or mathematical structure:** `S=ΣΔx_i·(y_{i-1}+y_i)/2`, `h=S/a`；对 `u_t=z_t+1` 建 GM(1,1) 再平移还原。

**Implementation notes:** PDF 未给 GM(1,1) MATLAB 代码、拟合参数或后验检验；Python 断面代码有缺失值置零、末行遗漏和越界风险。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 水位+流量二元回归 | rejected | 同时解释含沙量 | 两自变量高度相关 | 散点图定性显示相关 | VIF、条件数、岭回归或偏回归比较未报告 | 拒绝共线二元 OLS 有合理动机，但未量化共线性 |
| 两个双对数一元回归 | selected | 弹性估计 | 散点关系与经济/弹性解释 | R²、F、区间、残差图 | 独立测试、非线性基线未报告 | 解释清楚，但样本处理和聚合代码限制可信度 |
| M-K + Fisher | selected | 趋势与变点交叉检查 | 非参数趋势与有序分割互补 | 水通量都指向 t=27 | 沙通量结论不一致；类别数敏感性未报告 | 只能作为同一序列的内部一致性检查 |
| 小波变换 | selected | 局部周期/突变 | 需要时频局域化 | 给出尺度图与小波方差峰 | 母小波、边界处理、显著性和尺度换算未报告 | 可视化有用，数值结论不可完整复算 |
| R/S | selected | 趋势持续性判断 | 非参数、可表征长期记忆 | 24/48/72 月 H 值和定性后验比较 | 正确 log-log 实现、置信区间、短样本偏差校正未报告 | 附录实现与方法定义冲突，H 值不可由现有代码验证 |
| 10 阶 Fourier | selected | 月度预测 | 水沙序列具有周期性 | 36 点拟合、12 点留出 RMSE | 低阶 Fourier、季节朴素、ARIMA 等基线未报告 | 月采样下高阶列混叠，21 个系数不可识别 |
| GM(1,1) | selected | 4 点增量的 10 年外推 | 样本只有 4 点 | 仅给拟合/预测序列表 | 级比检验、残差、后验差、替代趋势模型未报告 | 长期外推远超数据长度，且独立级比检查不通过 |

## 5. Model Pipeline

主线为：原始日内观测 → 日/月/年聚合 → 回归与描述统计 → M-K/Fisher/小波 → R/S/Fourier → 0-1 监测选择。第四问另走断面数据 → 梯形积分 → 年增量 → GM(1,1)。

接口上存在三个关键断点：

1. 正文以 365 日定义周期，附录却固定 30 日/月；
2. R/S 的趋势判断没有形成可验证的数值预测，而 Fourier 的不确定性也未传入监测优化；
3. 0-1 模型只对单一确定预测序列求解，预测误差和突变点误差均未进入约束。

## 6. Model Improvements

- 用 Fisher 对 M-K 变点作交叉检查，避免只依赖单一图形；但两法使用同一序列，不是独立数据验证，且沙通量给出 t=27 与 t=30 的冲突。
- 用小波补充固定周期正弦模型，可观察局部尺度变化；但缺少母小波、显著性和边界效应设置。
- 对 Fourier 留出 2021 年作时间顺序检验，优于只报拟合误差；但模型阶数在查看全数据后是否确定未说明，且 21 列设计矩阵秩仅 12。
- 将监测选择转化为确定性 0-1 模型，使目标和约束明确；但“平均信息量”阈值是作者定义，未做阈值或预测误差敏感性。

## 7. Parameter Estimation and Optimization

回归系数由最小二乘估计；正弦与 Fourier 系数由 `lsqcurvefit` 估计；M-K、Fisher、R/S 和小波参数主要由作者固定；监测模型由 LINGO 求二元最优解；GM(1,1) 参数和求解代码未报告。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| α | 回归与 M-K 显著性水平 | dimensionless | p.6-7, p.11 | 0.05 | author-assumed | 固定 | no | M-K 临界值据此取 ±1.96 |
| k1, k2 | `liqundian3` 离群阈值 | unknown | p.29-32 code | 1.5, 3 | algorithm hyperparameter | 固定 | no | 函数定义未提供 |
| 删除点数 | 正弦拟合前单侧删除最大值个数 | count | p.33-35 code | 3；7 | author-assumed | 手工删除 | no | 未说明统计准则 |
| T_day | 含沙量日周期 | day | p.5 eqs. (1)-(3) | 365 | author-assumed | 固定周期 | no | 与 30 日/月代码冲突 |
| T_month | 水沙通量周期 | month | p.10 eqs. (12)-(14) | 12 | data-estimated | 时序图后固定 | no | 正文一处误称 t 为“日” |
| β1(level) | 水位弹性 | dimensionless | p.6 table 2 | 36.31 [34.97, 37.64] | data-estimated | OLS | no | 同一样本拟合 |
| β1(flow) | 流量弹性 | dimensionless | p.7 table 3 | 1.06 [1.03, 1.08] | data-estimated | OLS | no | 同一样本拟合 |
| m | Fisher 分类数 | count | p.41 code | 2 | algorithm hyperparameter | 固定 | no | 未报告类别数选择 |
| H | Hurst 指数 | dimensionless | p.15 table 8 | 0.2029-0.3317 | data-estimated | 论文称 log-log R/S；代码不一致 | no | 现有代码不可验证 |
| K | Fourier 阶数 | count | p.15-16, p.48 | 10（21 系数） | algorithm hyperparameter | 固定 | no | 36×21 设计矩阵秩 12 |
| n_train / n_test | Fourier 训练/留出长度 | month | p.16, p.48 | 36 / 12 | author-assumed | 按时间切分 | partial | 仅一个留出年 |
| ȳ | 最低月均动态信息量 | 亿 m³ | p.18 eq. (21), p.49 | 10.8 | data-estimated | 2018-2021 年变化量均值 | no | 计算细节未给 |
| z_t | 月份监测决策 | binary | p.18 eqs. (19)-(22) | 0 or 1 | problem-provided | LINGO 精确求解 | no | 单约束最小基数模型 |
| z0 | GM 正值平移量 | 河底高程增量同单位 | p.21 eq. (23) | 1 | author-assumed | 固定平移 | no | 平移敏感性未检验 |
| n_GM | GM 输入点数 | count | p.21 tables 12-13 | 4 | data-estimated | 跨年高程差 | no | 用于 10 年外推 |
| days_per_month | 月聚合固定天数 | day | p.28, p.35-48 code | 30 | author-assumed | 硬编码循环 | no | 与实际月长和 365 日假设冲突 |

## 8. Validation

论文提供了样本内诊断、同数据方法交叉、一个真实时间留出年和优化内部算术检查。最强的独立数据证据是 2021 年 Fourier 留出检验，但仅一个季节周期，且上游聚合及模型可识别性有问题。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 双对数回归 | L1 in-sample fit | same sample | R²、F p 值、系数区间 | 2 models | R²=0.5797/0.8013；p<0.05 | 流量模型仍有个别离群残差 | 删除点与聚合规则未纳入不确定性 | 仅支持处理后样本内相关与弹性估计 |
| 回归残差 | L1 residual diagnostic | same sample | 直方图、标准化残差图 | 2 models | 作者称近似正态、同方差 | 无正式检验统计量 | 图形来自同一拟合样本 | 不能推出独立预测性能 |
| M-K 与 Fisher 变点 | L2 internal cross-method consistency | same sample | 变点月份 | 2 series | 水通量均指向 t=27 | 沙通量 M-K 写 t=27，Fisher 写 t=30，却称一致 | 同数据、参数未敏感性检查 | 只支持水通量变点的内部一致性 |
| R/S 趋势判断 | L5 chronological qualitative check | hold-out | 无正式指标 | 1 split | 2016-2017 的反持续判断被称与 2018-2021 相符 | 未定义“相符”的方向/误差 | R/S 代码未做 log-log 回归且函数维度有误 | 不能验证报告的 H 或预测能力 |
| Fourier 预测 | L5 chronological hold-out | hold-out | RMSE | 1 split | 水 0.3205；沙 24.6572 | 沙通量误差远大于其 0.17 亿吨月均量级 | 单一年份；系数不可识别；误差单位未解释 | 水序列存在季节复现；不能支持“水沙均预测精度较高” |
| 0-1 监测解 | L2 objective/constraint sanity check | theoretical | 目标值、约束余量 | 1 deterministic instance | 11 次；选中平均 10.8831≥10.8 | 去掉第二小差值后 10.6776<10.8 | 输入来自单一确定预测，无现实监测验证 | 表 11 解对式 (22) 是可行且最小基数 |
| GM(1,1) 10 年外推 | not reported | unknown | not reported | not reported | 末值 64.79 m | 未报告拟合误差、后验差或外部检验 | 4 点训练、10 年外推、级比不合格 | 只能视为模型情景输出，不是已验证预测 |

## 9. Sensitivity and Robustness

在已审查范围内，未发现对离群阈值、Fourier 阶数、M-K/Fisher 参数、小波设置、监测阈值、预测误差、GM 平移量或断面缺失值处理的正式敏感性实验。审查覆盖 p.1-22 正文、p.23-56 全部附录代码及 PDF 内可用支撑材料；外部输入文件不可用。论文 p.2 虽写“还需要进行敏感性分析和稳健性分析”，正文和附录未给对应结果。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|

在已审查范围内未发现可填入该表的实际扰动实验；因此不把方法并列、拟合图或单次留出检验改写为敏感性证据。

## 10. Visualization Strategy

论文使用了四类图：

- 时序图、月份/季度指数柱图用于先识别季节结构；
- 散点、残差直方图与残差-预测图用于回归诊断；
- M-K 双曲线、Fisher 分类曲线、小波等值线与方差曲线用于趋势、变点和尺度展示；
- 预测对比、断面指标折线/柱图用于结果表达。

布局能让模型链易读，但部分图号/图注错误：p.13 引用“图 2/图 4”而实际应为图 26/28；p.20 两幅不同指标都标为“图 40 日均水通量”。图形应与可复核表格或指标绑定，不能用“看起来相符”替代验证。

## 11. Writing Structure

摘要按四问报告模型和结论，正文依次给问题分析、假设、建模、结果、评价，附录收录大量代码，整体竞赛结构完整。优点是公式、表格、图和代码通常能形成对应关系；不足是跨章节口径未统一：缺失填补方法、河底高程效果、时间单位、变点位置和百分比结论存在矛盾，正文自评也没有暴露这些问题。

## 12. Strengths

- 从统计描述到监测决策形成完整流程，接口定义大多可定位到公式。
- 回归模型明确避免将高度共线的水位和流量同时放入普通二元 OLS。
- Fourier 使用时间顺序留出一年，而不是只报训练拟合。
- 0-1 监测模型目标、约束和实现一致，独立算术可核验其最小基数解。
- 附录提供了大量代码，使公式—代码审计成为可能。

## 13. Weaknesses

主要弱点不是方法数量不足，而是数据口径和实现一致性不足：固定 30 日/月、年度汇总代码错误、R/S 实现错误、高阶 Fourier 不可识别，以及多个百分比与变点结论矛盾。预测误差没有进入监测决策，GM(1,1) 用 4 点作 10 年外推且无验证。因输入数据和自定义模块缺失，现有附录无法端到端复现。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable in repository | p.23-56 引用多个 Excel/MAT/TXT 文件；仓库仅有 PDF | 无法重算表格和图 |
| Code availability | partial | p.23-56 内嵌 Python/MATLAB/LINGO；部分自定义模块未给 | 代码需人工转录且模块不完整 |
| Dependency / environment information | not reported | p.23-56 仅给软件名，无版本/包清单 | 旧 API 与求解器行为不可锁定 |
| Random seed | not reported | p.1-56；所列模型基本确定性 | 对当前确定性主链影响有限，但无统一运行记录 |
| Hard-coded constants | extensive | 30 日/月、3/7 点删除、10 阶 Fourier、m=2、10.8、z0=1 | 多数未做敏感性 |
| Formula-to-code consistency | contradicted in material parts | p.15 与 p.46-47 R/S；p.16 与 p.48 Fourier；p.3-5 与 p.28-39 日历 | R/S 不做 log-log；日历 365/360 冲突；Fourier `a0/2` 与代码常数项冲突 |
| Code-to-result consistency | contradicted / not assessable | p.24-32, p.45-56 与表 4、8-14 | 年排沙累加器不逐年清零、末日径流变量错误；缺输入无法确认实际运行版本 |
| Overall reproducibility | not reproducible | 审查正文、全附录代码和仓库可用文件 | 缺输入/模块/环境，且关键代码有执行或逻辑错误 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 月份占比闭合 | 水、沙 12 个月占比 | 两行分别求和均为 100.00% | pass | p.9 table 6 | 仅验证表内闭合 |
| 年均值闭合 | 年均水量 324.73、沙量 1.99 | 六年值均值 324.73、1.9867 | pass | p.8 table 4 | 表头沙量单位误写“吨”，正文为亿吨 |
| 监测最优性 | 仅 5 月不监测 | 12 差值和 132.0049；去掉最小值后平均 10.8831≥10.8，去掉次小值后 10.6776<10.8 | pass | p.19 table 11, eq. (22) | 对给定单约束实例成立 |
| 水通量下降比例 | 9.46 降至 5.49，下降 72% | `(9.46-5.49)/9.46=41.97%`；72.31% 使用了后值作分母 | fail | p.20 fig. 39 / paragraph | 日期还是跨年点，并非同年调沙前后 |
| 2022 水通量上升 | 上升 6.4% | 图 39 的 4.23→5.76 为 36.17%；6.39% 对应另一图的 12.67→13.48 | concern | p.20 figs. 39-40 | 文字引用对象混淆 |
| 沙通量下降比例 | 0.3547→0.244，下降 45.4% | 以前值为分母为 31.21%；45.37% 使用后值为分母 | fail | p.20 right fig. 40 | 图注还误标为水通量 |
| M-K/Fisher 一致性 | 两法结论一致 | 沙通量 M-K 写 t=27，Fisher 写 t=30 | fail | p.11-12 figs. 22, 24 | 水通量 t=27 一致 |
| 日历维度 | 一年按 365 日 | MATLAB 为 30×12=360 日；Python 只取 360 行 | fail | p.3 §5.0; p.24, p.28, p.35 code | 会影响全部聚合结果 |
| Fourier 可识别性 | 36 点估计 10 阶、21 系数 | 按附录构建设计矩阵得到 shape 36×21、rank 12、condition≈1.10×10^15 | fail | p.16 table 9; p.48 code | 月度 12 周期导致高次谐波混叠，系数不唯一 |
| Fourier 常数项 | 式 (16) 使用 `a0/2`，表 9 `a0=33.07` | 附录代码直接用 `p(1)`；若按正文则截距 16.535 | fail | p.16 eq. (16), table 9; p.48 code | 公式—代码参数化冲突 |
| R/S 实现 | H 是 `ln(R/S)` 对 `ln(n)` 斜率 | 代码对原始 `n,R/S` 做 `polyfit`，且 `m=size(x); p=m/n` 非标量 | fail | p.14-15; p.46-47 code | 报告 H 不可由所附代码重现 |
| 年排沙循环 | 表 4 给逐年排沙量 | `d9=0` 位于年份循环外，`d10(i)=d9/10^8` 为累计量 | fail | p.32 code | 与“逐年”定义不一致 |
| 最后一日径流 | 日径流=日均流量×86400 | 最后一组代码使用 `water_level_sum×86400` | fail | p.26 code | 变量维度也不一致 |
| GM 级比 | 4 点平移后建立 GM(1,1) | `u=[1.05,0.69,1.15,1.03]`，级比 `[1.522,0.600,1.117]`；n=4 的常用可容区间约 `[0.670,1.492]`，前两项越界 | concern | p.21 tables 13-14, eqs. (23)-(24) | 论文未报告级比检验；10 年外推不稳 |

## 14. Reusable Techniques

### 时间序列“检测—预测—决策”接口

**When useful:** 题目同时要求规律识别、未来预测和资源配置。

**Why useful:** 能把描述性模型的输出转成明确决策变量和约束。

**Limitations:** 必须把预测误差、时间切分和数据聚合口径传到决策层；不能只把点预测当真值。

### 同数据异方法变点交叉检查

**When useful:** 单一变点方法对假设或噪声敏感时。

**Why useful:** M-K 与有序分割关注不同结构，结果一致可作为内部一致性证据。

**Limitations:** 不是独立验证；必须先核对变点索引、时间单位和参数，并报告不一致结果。

### 最小基数覆盖式监测设计

**When useful:** 每个候选时点有可加的信息价值，目标是用最少测次达到信息阈值。

**Why useful:** 模型简单、可解释、容易验证可行性和边界解。

**Limitations:** 信息价值若不是可加的、存在连续变化或漏测风险时，需要鲁棒/机会约束或最大间隔约束。

### 公式—代码—结果三向审计

**When useful:** 论文附有实现代码且模型链较长。

**Why useful:** 可发现仅看正文无法发现的固定 30 日、累加器未清零、变量误用和谐波混叠。

**Limitations:** 缺输入数据时只能验证结构和简单算术，不能声称完整复现。

## 15. Competition Takeaways

1. 日/月/年聚合先写一个统一函数，并用实际日历检查行数闭合，禁止同时出现 365 日和 30×12 日。
2. 缺失填补与离群剔除必须给唯一规则、删除数和消融结果，摘要、正文、代码保持一致。
3. 季节 Fourier 阶数要结合采样频率和设计矩阵秩选择；先比较季节朴素与低阶基线。
4. 时间序列验证至少保留未来区间，并报告与变量量级可比较的 MAE/RMSE；不要只写“图形拟合较好”。
5. 多方法交叉验证前先统一数据、索引和目标；出现 t=27/t=30 时应报告冲突而非宣称一致。
6. 优化前把预测不确定性传入情景或鲁棒约束，并对信息阈值做敏感性。
7. 每个百分比固定基准分母并附一行算式；图号、图注和正文引用必须逐项核对。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 摘要写均值填补，§5.0 写邻近值替代 | criticism | 1, 3 | 摘要；5.0 数据整理 | paragraph | direct transcription | N/A | 源内口径冲突 |
| 水位、流量弹性分别为 36.31 与 1.06 | explicit | 6-7 | 5.1.2 | tables 2-3; equations (7), (9) | notation normalization | N/A | 处理后样本内 OLS |
| 六年年均水流量 324.73 亿 m³、排沙量约 1.99 亿吨 | explicit | 8 | 5.1.3 | table 4 | direct transcription | N/A | 表头排沙量单位排版有误 |
| 水、沙月份占比表各自闭合为 100% | interpretation | 9 | 5.2.2.1 | table 6 | independent calculation | N/A | 逐项求和 |
| 水通量 M-K 与 Fisher 都定位 t=27 | explicit | 11-12 | 5.2.4 | figures 21, 23; paragraphs | direct transcription | N/A | 同一序列内部一致性 |
| 沙通量 M-K 为 t=27、Fisher 为 t=30，却被称为一致 | criticism | 11-12 | 5.2.4 | figures 22, 24; paragraphs | direct transcription | N/A | 明确源内矛盾 |
| 小波给出约 20 月主周期、水通量约 55 月次周期 | explicit | 13-14 | 5.2.5 | figures 25-28 | direct transcription | N/A | 小波设置未报告 |
| 表 8 报告 H=0.2029-0.3317 并判为反持续 | explicit | 15 | 5.3.1 | table 8 | direct transcription | N/A | H<0.5 |
| R/S 附录未做 log-log 回归且分段数变量非标量 | criticism | 46-47 | Appendix 2.3.1 | code | independent calculation | N/A | 公式—代码冲突 |
| Fourier 用 2018-2020 训练、2021 留出，报告水/沙 RMSE 0.3205/24.6572 | explicit | 16-17 | 5.3.2.2 | table 10; paragraph | direct transcription | N/A | 单一留出年 |
| 10 阶 Fourier 设计矩阵 36×21 但秩为 12 | criticism | 16, 48 | 5.3.2.2; Appendix 2.3.2 | equation (16); code | independent calculation | N/A | 月度 12 周期谐波混叠 |
| 式 (16) 的 a0/2 与代码直接使用 p(1) 不一致 | criticism | 16, 48 | 5.3.2.2; Appendix 2.3.2 | equation (16); table 9; code | independent calculation | N/A | a0=33.07 时差一倍 |
| 监测模型是最小基数二元覆盖模型 | explicit | 18 | 5.3.3.2 | equations (18)-(22) | notation normalization | N/A | 相邻绝对差为信息量 |
| 表 11 的 11 次监测是给定实例最小基数解 | interpretation | 19 | 5.3.3.2 | table 11; equation (22) | independent calculation | N/A | 选中平均 10.8831，阈值 10.8 |
| 正文称河底高程调沙成效显著，摘要却称成效不佳 | criticism | 1, 20 | 摘要；5.4.1 | paragraphs; figure 38 | direct transcription | N/A | 结论方向冲突 |
| 9.46→5.49 的标准降幅为 41.97%，不是 72% | criticism | 20 | 5.4.2 | figure 39; paragraph | independent calculation | N/A | 72.31% 使用后值作分母 |
| 6.4% 对应 12.67→13.48，不对应图 39 的 4.23→5.76 | criticism | 20 | 5.4.2 | figures 39-40 | independent calculation | N/A | 图文引用混淆 |
| 0.3547→0.244 的标准降幅为 31.21%，不是 45.4% | criticism | 20 | 5.4.3 | right figure 40; paragraph | independent calculation | N/A | 45.37% 使用后值作分母 |
| GM(1,1) 用 4 个增量点预测 10 年，末值 64.79 m | explicit | 21 | 5.4.4 | tables 13-14; figure 41 | direct transcription | N/A | 无验证指标 |
| 平移序列的两个级比落在常用可容区间外 | criticism | 21 | 5.4.4 | table 13; equation (23) | independent calculation | N/A | 1.522、0.600 越界 |
| 正文 365 日与附录 30×12 日冲突 | criticism | 3, 28, 35-48 | 5.0; Appendix | paragraph; code | independent calculation | N/A | 上游系统性偏差 |
| Python 最后一日径流误用水位变量 | criticism | 26 | Appendix 2.0 | code | direct transcription | N/A | 量纲错误 |
| 年排沙量累加器 d9 未在年份循环内清零 | criticism | 32 | Appendix 2.1.2 | code | direct transcription | N/A | 逐年与累计口径冲突 |
| 在已审查范围内，未发现正式敏感性或稳健性实验 | criticism | 1-56 | 全文与附录 | none found | derived interpretation | 审查 p.1-22 正文、p.23-56 附录代码、全部表图和 PDF 内支撑材料列表 | 外部输入文件不可用 |
| 在已审查范围内，未发现依赖版本、完整运行环境或随机种子记录 | criticism | 1-56 | 全文与附录 | none found | derived interpretation | 审查 p.1-22 正文、p.23-56 附录代码及支撑材料列表 | 主链基本确定性，但环境仍影响复现 |
| 附录引用的 Excel/MAT/TXT 和自定义模块不可用于本次审计 | criticism | 23-56 | Appendix | code; support-material list | direct transcription | N/A | 缺少独立文件，标记 not assessable |
