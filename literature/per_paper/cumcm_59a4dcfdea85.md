# Paper: 基于成分数据的古代玻璃制品的成分分析与鉴别

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_59a4dcfdea85
- Year: 2022
- Problem: C
- Award: 组委会官方展示代码与年份匹配；具体奖项等级未核验
- Provenance tier: O; 本地 PDF 与 2022 C155 官方展示的年份、代码和 41 页页数匹配，但官方展示不证明奖级
- Source file: literature/raw_papers/2022/C155.pdf
- Source URL: unknown；acquisition 记录为用户提供的本地副本，无直接 PDF URL
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2022qgdxssxjmjslwzs/221106/1820281.shtml
- Pages: 41
- SHA-256: f0dd04d1887a0a3b0fc0aef306d0c005b8a7db768c6270023ede2b80e208e216
- Extraction method: OCR fallback；Tesseract 5.5.0，chi_sim+eng，250 DPI，PSM 3，并对关键公式、表图和附录代码直接视觉复核
- Extraction quality: 原嵌入文本为 poor_quality；OCR 41/41 页均达到至少30个非空白字符，中位数688字符/页，无页级失败；p.30–31以谱系图为主，p.32–41小字号代码需以原图为准
- Page convention: 1-based physical PDF pages
- Visually checked pages: p.1 标题/摘要；p.4–9 成分变换、卡方/Yates和描述统计；p.11–19 箱线图、Q聚类、式(9)–(12)、表9–20；p.20–28 R/Q聚类、扰动、未知样本、灰关联式(13)–(20)与表21–28；p.29 评价；p.30–31完整谱系图；p.32–41全部 MATLAB/Python 代码，其中p.34–35另以300 DPI核对索引
- Unresolved extraction ambiguities: 小字号代码的中文路径/函数依赖和少数注释不可可靠转写；关键循环索引、零值分支和回归列索引已视觉确认
- Supplemental artifacts: PDF 内附聚类/回归 MATLAB 片段及 log-ratio Python 片段；题目附件 Excel、SPSSPRO 工程、决策树/R-Q/灰关联完整代码、随机扰动记录和预测输出文件未随论文提供

## 1. Problem Archetype

本文是一个成分数据（compositional data）统计分析、分类与探索性关联的混合管线：

1. **成分数据预处理与列联表推断**：闭合到100%、中心化对数比（centered log-ratio, CLR）变换，分析风化与类型/颜色/纹饰关系。
2. **无监督状态构造 + 回归反推**：用Q型层次聚类把样品分成风化/未风化并进一步人为排序成四个“时段”，在四个聚类中心上拟合二次曲线，反推风化前组成。
3. **监督分类**：按风化状态拆分数据，以PbO阈值决策树区分高钾和铅钡玻璃。
4. **变量聚类 + 样本聚类**：先R型聚类14种成分、每组挑代表特征，再Q型聚类得到亚类。
5. **灰色关联分析**：轮流以每个成分作母序列，比较两类玻璃内部的成分曲线相似性。

其最有价值的认识是“百分比成分受闭合约束，不能直接照搬欧式统计”。但零值处理、统计检验、时序构造和验证设计没有达到这一认识要求的严谨程度。

## 2. Problem Decomposition

1. 删除总成分不在85%–105%的采样点15、17；把有效行重新闭合到100%，对成分作CLR，对颜色/类型/纹饰/风化作编码。
2. 对风化×类型做Pearson卡方；对风化×颜色和风化×纹饰声称做Yates校正；按类型/风化四组输出描述统计和箱线图。
3. 对高钾、铅钡数据各做两类Q聚类得到风化点；再分四类并手工赋予未风化→严重风化次序；对四个CLR中心拟合二次曲线并平移外推。
4. 对风化/未风化两组分别训练70/30决策树；随后在四组数据中先R型聚类成3个变量簇，再用代表变量做Q型亚类。
5. 用已训练PbO阈值给A1–A8分类，以Q聚类一致性作所谓“交叉检验”，再按离阈值距离讨论敏感性。
6. 对两类玻璃分别做灰色关联，比较以SiO2为母序列的表28和所有母序列的离散程度。

该链条存在循环：风化点及四级“时序”由化学组成聚类产生，回归和后续分类又以这些标签为依据；同源聚类一致性不能提供独立真值。

## 3. Data Processing

- **有效性筛选**：按题面要求，成分和介于85%–105%才有效；作者删除采样点15、17。
- **闭合**：式(1)将每一成分除以该行总和，使总和为1/100%。这是消除检测总量差异的必要步骤。
- **CLR**：正文式(2)为 `log(x_i/g(x))`，但文字误称 `alr`；附录D对非零元素计算几何均值，把原始0直接写成变换后的0。
- **缺失值**：颜色缺失的19、40、48、58在颜色分析中删除；化学成分空缺被填0。
- **分类变量编码**：纹饰A/B/C→0/1/2，类型→0/1，颜色→0–7，风化→0/1。编码只用于整理；名义变量不应据编码大小解释距离。
- **分组**：先按玻璃类型，再以原始未CLR数据做Ward层次聚类，构造风化/未风化与四级风化状态。
- **零值边界**：真正CLR要求正成分；将“未检测”直接作为0既不能取对数，也需要区分检测限零、结构零和缺失。论文未做乘法替换、pseudocount或零模式模型。

## 4. Models Used

### 成分闭合与CLR

**Purpose:** 消除百分比定和约束，进入对数比坐标。

**Inputs:** 14项非负化学成分。

**Outputs:** 总和100%的组成及CLR坐标。

**Why selected:** 作者明确认识到单形空间协方差和欧式统计解释不同。

**Important assumptions:** 所有0可原样保留；非零子组成的几何均值足以替代完整CLR。

**Key equations or mathematical structure:** `C_i/sum C_j` 与 `clr_i=ln(x_i/g(x))`。

**Implementation notes:** 附录D跳过0计算几何均值、再把0写为0；这不是标准零替换CLR，且变换后真正等于0的非零成分与原始0不可区分，附录C逆变换非双射。

### 列联表卡方检验

**Purpose:** 检验表面风化与类型、颜色、纹饰的关联。

**Inputs:** 2×2、2×8、2×3计数表。

**Outputs:** `chi-square,df,p`。

**Why selected:** 所有变量均为分类变量。

**Important assumptions:** 观测独立，期望计数条件满足；作者认为不满足时可对任意r×c表使用Yates。

**Key equations or mathematical structure:** Pearson `sum(O-E)^2/E`；作者式(5)把 `abs(O-E)` 减0.5后推广到r×c。

**Implementation notes:** Yates连续性校正通常限2×2；表6/7数值恰等于未校正Pearson统计量，未体现校正。

### Ward Q型聚类与四级风化“时序”

**Purpose:** 从无标签随机采样点识别风化点，并构造未/轻/中/重四阶段。

**Inputs:** 高钾18行、铅钡49行的14维原始成分。

**Outputs:** 两类/四类层次聚类及人工阶段标签。

**Why selected:** 同类离差平方和小、类间差异大；类型不同所以分开聚类。

**Important assumptions:** 化学距离可代表风化程度；四个簇存在可排序的单调时间；已知风化描述可给簇命名。

**Key equations or mathematical structure:** Ward离差平方和式(9)–(10)，欧氏/Minkowski-2距离。

**Implementation notes:** `k=2`后再把两个子簇各分2类；附录B手工重排簇次序。无轮廓系数、稳定性或外部年代。

### 四点二次回归与曲线平移预测

**Purpose:** 从风化点成分估算未风化组成。

**Inputs:** 四个阶段的CLR均值和待预测CLR值。

**Outputs:** 各成分的二次曲线、R²与闭合后的预测组成。

**Why selected:** 作者将四簇视为时序并用趋势曲线表达风化变化。

**Important assumptions:** 阶段等间距1–4；二次趋势可外推；低R²成分风化前后不变；对距离开平方能削弱异常值。

**Key equations or mathematical structure:** 每成分3参数二次式；把观测与阶段曲线的距离取平方根后平移到`t=1`，再用对数比逆变换闭合。

**Implementation notes:** 只有4个中心点，二次式残差自由度1；`sqrt(d)`规则无统计推导且可能遇到负被开方数；R²阈值未报告。

### PbO单阈值决策树

**Purpose:** 区分高钾与铅钡玻璃。

**Inputs:** 风化组或未风化组的化学成分。

**Outputs:** 未风化阈值8.495%、风化阈值6.155%。

**Why selected:** 类别已知，可做监督分类；树规则直接可解释。

**Important assumptions:** 单次70/30拆分可代表泛化；聚类生成的风化标签可靠。

**Key equations or mathematical structure:** ID3信息增益式(12)，最终树均只有PbO一个分裂。

**Implementation notes:** 训练/测试precision、recall、accuracy、F1均报1，但无样本数、混淆矩阵、随机种子或重复切分；聚类在全数据上先执行，存在预处理泄漏。

### R型变量聚类 + Q型亚类

**Purpose:** 每类玻璃选代表成分并划分亚类。

**Inputs:** 四个类型×风化组的14项成分。

**Outputs:** 每组3个变量簇、代表特征和样本亚类。

**Why selected:** 作者希望先去除高度相关特征，再聚类样本。

**Important assumptions:** `1-|r|`能表达变量距离；最短距离连接适合；每组固定3簇；星号代表变量可客观代表整簇。

**Key equations or mathematical structure:** Pearson相关式(13)，`d=1-|r|`，single linkage式(14)，随后Ward Q聚类。

**Implementation notes:** 高钾风化矩阵存在NaN，处理方式未报告；代表变量选择准则和“优于直接Q”的比较指标未给出。

### 灰色关联分析

**Purpose:** 比较同类玻璃中各化学成分曲线的相似度及两类型差异。

**Inputs:** 轮流选定的母序列、其余13个子序列。

**Outputs:** 关联系数和加权关联度。

**Why selected:** 作者认为小样本、非规律序列也可使用。

**Important assumptions:** 除均值尺度化合适；灰关联可解释为化学相关；权重已知。

**Key equations or mathematical structure:** 均值归一化、分辨系数`rho`、极差关联式(17)–(19)、加权和式(20)。

**Implementation notes:** `rho`仅称一般取0.5；权重值与来源均未报告；主要表只展示SiO2母序列。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 原始百分比欧式分析 | rejected | 成分统计 | 定和约束导致协方差/解释问题 | 文献性讨论 | 零值替代方案比较 | 转向对数比是正确方向 |
| CLR | selected | 成分坐标 | 打破定和限制并保持相对信息 | 预测闭合到100% | 标准零替换、ALR/ILR对比 | 实现把0原样保留，破坏理论性质 |
| Pearson卡方 | selected for 2×2 | 风化×类型 | 期望计数满足 | `chi2=6.88,p=.009` | 效应量和置信区间 | 该检验数值可复算 |
| Yates校正 | selected for 2×8/2×3 | 稀疏列联表 | 期望计数不足 | 表6/7 | Fisher-Freeman-Halton/Monte Carlo exact | 方法不适用，且表值其实是Pearson |
| 二次回归 | selected | 风化趋势 | 以四级时序拟合趋势 | 各成分R² | 线性/单调/留一阶段预测 | 四点三参数导致高R²证据弱 |
| 决策树 | selected | 玻璃分类 | 可解释监督分类 | 单次70/30指标全1 | 交叉验证、基线、混淆矩阵 | PbO规则直观，但泛化证据薄弱 |
| 梯度提升决策树 | considered only | 提升分类 | 问题分析称将进一步提高精度 | not reported | 实现、参数、结果 | proposed but not implemented |
| 直接Q聚类 | rejected | 亚类 | 相关变量可能影响样本聚类 | not reported | 同数据聚类质量对比 | R→Q有解释价值，但“更好”未被验证 |
| R后Q聚类 | selected | 特征选择+亚类 | 每簇选代表特征 | 图7、扰动表 | k选择、代表性准则、稳定性 | 结果可解释，证据仍依赖主观设定 |
| 灰色关联 | selected | 成分关联 | 小样本/不规则序列适用、计算量小 | 表28和图8–9 | Pearson/Spearman/partial correlation对比 | 是相似度描述，不应直接当化学机制 |

## 5. Model Pipeline

`原始成分 → 有效行筛选 → 闭合/非标准CLR → 描述统计/箱线图`。分类关系分支用列联表；预测分支用 `原始成分Q聚类 → 风化簇命名 → 四簇人工排序 → CLR中心 → 四点二次回归 → 曲线平移 → 逆变换`。

问题二/三分支为 `全数据风化聚类 → 风化/未风化拆分 → 单阈值树 → A1–A8分类 → 同源Q聚类一致性`。亚类分支为 `四组相关矩阵 → R聚类3簇 → 星号代表变量 → Q聚类 → 随机扰动`。问题四独立使用原始组内序列做灰关联。

接口风险集中在“聚类标签被当真值”：它同时定义风化阶段、训练分类器分层和验证预测，造成证据自洽但不独立。

## 6. Model Improvements

1. **先识别闭合数据几何**：相比直接相关/回归，加入闭合和CLR是结构性改进。
2. **按玻璃类型和风化状态分层**：避免把化学机制明显不同的样本完全混合。
3. **R→Q两级聚类**：先压缩相关特征再分样本，改善解释性；但论文未给直接Q基准。
4. **规则化未知样本分类**：两个PbO阈值易于复核和落地。
5. **加入扰动与异方法一致性**：尝试用特征扰动、树/聚类一致性和预测再聚类审查结果。

这些改进没有解决零值CLR、聚类标签循环、微小样本和缺少独立真值的问题；因此其证据级别需要逐项限定。

## 7. Parameter Estimation and Optimization

本文没有优化目标，关键“参数”主要由阈值、聚类数和经验规则设定。决策树阈值由一次训练集分裂估计；`k=2/4/3`分别用于风化点、阶段和变量簇；二次回归次数固定；灰关联权重未报告。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| valid sum range | 有效样品成分和 | % | p.4 | 85–105 | problem-provided | 题面规则 | no | 删除15、17 |
| closure total | 闭合总和 | % | p.4 式(1) | 100 | author-assumed | 行归一化 | no | 合理但会改变绝对总量 |
| chemical missing | 未检出成分处理 | % | p.5 | 0 | author-assumed | 空缺补0 | no | 与CLR正值前提冲突 |
| color missing rows | 缺颜色文物 | N/A | p.5 | 19、40、48、58 | data-estimated | 颜色分析删除 | no | 颜色表总样本54 |
| chi-square alpha | 显著性水平 | dimensionless | p.7–8 | 0.05 | author-assumed | 固定 | no | p=.084不能证明独立 |
| `k_weather` | 风化点聚类数 | 类 | p.12 | 2 | algorithm hyperparameter | author choice | no | 无聚类指标 |
| `k_stage` | 风化阶段数 | 类 | p.13 | 4 | algorithm hyperparameter | 两级二分聚类 | no | 无真实时间标尺 |
| polynomial degree | 每成分趋势次数 | degree | p.15 | 2 | algorithm hyperparameter | 四中心最小二乘 | no | 3参数、残差df=1 |
| R² cutoff | 预测/不变成分筛选阈值 | dimensionless | p.15–16 | not reported | author-assumed | “较高/较低” | no | 代码对不同类型硬编码跳过成分 |
| square-root distance | 曲线平移距离变换 | dimensionless | p.16 | `sqrt(d)` | author-assumed | 降低异常值影响 | no | d可负，缺统计依据 |
| train/test split | 决策树拆分 | dimensionless | p.18–19 | 70%/30% | algorithm hyperparameter | single split | no | 随机种子/分层未知 |
| PbO unweathered | 未风化分类阈值 | % | p.18–19 图4 | 8.495 | data-estimated | 决策树 | partial | A1–A8最小绝对边界8.495 |
| PbO weathered | 风化分类阈值 | % | p.19 图5 | 6.155 | data-estimated | 决策树 | partial | A1–A8最小绝对边界6.075 |
| `k_R` | R型变量簇数 | 类 | p.20–22 | 3 | algorithm hyperparameter | 固定 | no | 高钾风化有NaN |
| variable distance | R聚类距离 | dimensionless | p.21 式(14) | `1-|r|` | author-assumed | Pearson绝对相关 | no | 正负相关被视为同样相似 |
| perturbation `p` | 代表特征乘法扰动 | dimensionless | p.23–24 表25 | 0.05–0.20，逐特征不同 | data-estimated | 随机重赋值，次数未知 | yes | 正文误写0.10–0.20 |
| grey resolution `rho` | 分辨系数 | dimensionless | p.26 | 一般0.5；实际值未明确 | literature-derived | conventional | no | 结果对rho敏感性未给 |
| grey weights `w_k` | 关联度权重 | dimensionless | p.26 式(20) | not reported | author-assumed | not reported | no | 表28不可复算 |

## 8. Validation

论文有留出、扰动和异方法一致性，但均受小样本或同源预处理影响。特别是“聚类一致”只是 L2 内部证据，不能替代真实未风化组成或独立材质标签。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 风化×类型关联 | L1 full-sample hypothesis test | same sample | Pearson chi-square,p | 1 | 6.880,p=.009 | none reported | 无效应量/置信区间 | 支持该样本存在关联 |
| 风化×颜色/纹饰 | L1 full-sample hypothesis test | same sample | 被标为Yates的chi-square,p | 1 | 6.287/.507；4.957/.084 | 稀疏期望计数 | Yates不适用于2×8/2×3且数值未校正 | 不能证明独立，只能说未拒绝 |
| 四阶段二次回归 | L1 in-sample fit | same sample | R² | 1 per component | 0.2355–0.9998 | 多个成分低R² | 4点拟合3参数，df=1 | 仅描述人工簇中心，不支持预测泛化 |
| 风化前预测 | L2 reclustering consistency | same sample | 与已知未风化簇同类 | 1 | 声称全部预测点归入未风化类 | none reported | 无真实风化前真值，同一化学距离自证 | 支持内部相似性，不支持准确度 |
| 决策树玻璃类型 | L5 single hold-out classification | hold-out with preprocessing leakage | precision/recall/accuracy/F1 | 1 split | 训练/测试均1 | none reported | 约9–11测试点量级、无混淆矩阵；风化标签预聚类使用全数据 | 最多支持该次切分的PbO完全分离 |
| 亚类稳定性 | L3 random feature perturbation | same sample | 聚类标签是否变化 | not reported | 表25阈值0.05–0.20 | SiO2仅0.05 | 无随机次数/种子，不可能由有限抽样证明“任意值” | 支持有限扰动实验的局部稳定性 |
| A1–A8分类 | L2 cross-method consistency | same sample | 树与Q聚类标签一致 | 1 | A1/A6/A7高钾，其余铅钡 | none reported | Q聚类非独立标签，未见盲真值 | 支持两方法一致，不支持准确率 |
| A1–A8阈值裕量 | L2 deterministic margin check | same sample | PbO到阈值绝对距离 | 8 samples | 最小风化6.075个百分点；最小未风化8.495个百分点 | 仅PbO扰动 | 未传播测量误差/风化标签不确定性 | 支持单变量局部边界稳定 |
| 灰关联 | not reported | same sample | not reported | not reported | 仅描述值/离散度 | not reported | 无外部化学机制或替代相关指标 | 只能作探索性相似度 |

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 高钾未风化代表特征 | 原始SnO2/CuO/CaO | ±10%、±15%、±15% | random；次数未报 | Q亚类标签 | 声称不变 | no | 仅局部抽样证据 |
| 铅钡未风化代表特征 | 原始Na2O/CuO/SiO2 | ±20%、±20%、±5% | random；次数未报 | Q亚类标签 | 声称不变 | no | SiO2容许幅度最低0.05 |
| 高钾风化代表特征 | 原始SnO2/CuO/SO2 | 各±15% | random；次数未报 | Q亚类标签 | 声称不变 | no | 无联合扰动/重复统计 |
| 铅钡风化代表特征 | 原始Al2O3/CuO/SrO | ±15%、±10%、±15% | random；次数未报 | Q亚类标签 | 声称不变 | no | 无随机种子 |
| 未知风化样本PbO | 阈值6.155% | 样本值0–34.3% | deterministic margin | 树分类 | 最小裕量6.075个百分点 | no | 只检验给定8样本 |
| 未知未风化样本PbO | 阈值8.495% | 样本值0–39.58% | deterministic margin | 树分类 | 最小裕量8.495个百分点 | no | 0的乘法扰动永不改变 |

## 10. Visualization Strategy

- 图1把四个类型×风化组的CLR箱线图并排，适合展示组成分布差异；但“箱宽”不是样本波动的通用编码。
- 图2、图10及附录铅钡谱系图展示层次聚类结构，比只报簇标签更可审查。
- 表13–16把四阶段中心和每成分回归方程/R²放在一起，数学信息密度高。
- 图4–5把最终决策树简化为单个PbO阈值，是全文最清楚的规则图。
- 图6的四张相关矩阵揭示高钾风化组NaN块，但未说明处理；图7亚类树文字过小。
- 图8–9灰关联曲线显示两组离散差别，表28给精确值；图仅显示部分序列且权重缺失。

## 11. Writing Structure

论文按四问组织，每问先解释方法、再给公式/图表/结论，附录提供谱系图和部分代码。术语首次出现大多有定义，分类规则也被压缩成可执行阈值。

主要写作问题是把方法局限写成强结论：未拒绝原假设被写成“相互独立”，单次测试集全1被写成性能良好，四点高R²被写成风化作用证据，同源聚类被称“交叉检验”。此外`alr/clr`混用、“敏感性高”用于表示不敏感、表20/图5标题仍写“未风化类型”等，影响术语一致性。

## 12. Strengths

1. 明确识别成分数据闭合约束，并试图在对数比空间完成回归/逆变换。
2. 风化×类型列联表给出完整计数、统计量、自由度和p值，可独立复核。
3. 分类树最终退化为两个直观PbO阈值，便于解释和现场使用。
4. R型变量聚类和Q型样本聚类的串联具有条件化复用价值。
5. 作者主动加入扰动、再聚类和异方法一致性，验证意识强于只报聚类图的论文。

## 13. Weaknesses

1. 0值未做合规替代；附录把原始0和CLR恰为0混为一类，逆变换不是一一映射。
2. Yates方法及输出均错误，且“未拒绝”被升级为独立结论。
3. 四个聚类中心拟合二次曲线、人工排序为时序，再用同一距离聚类验证，存在严重循环与过拟合。
4. 决策树测试集很小，单次切分且风化预聚类泄漏；无交叉验证或外部样本。
5. R/Q与灰关联的关键参数、权重、随机次数和完整代码缺失；若干“优于/稳健”无比较证据。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable | 全文引用表单1–3；仅给部分汇总/预测表 | 原始附件未随PDF/仓库提供 |
| Code availability | partial | p.32–41含聚类、回归、CLR/逆变换片段 | 数据读取函数、决策树、R-Q、扰动、灰关联代码缺失 |
| Dependency / environment information | partial | MATLAB；Python numpy/openpyxl/sklearn import | 版本、SPSSPRO设置和函数依赖未给 |
| Random seed | not reported | 70/30拆分和随机扰动相关段落/附录均审查 | 指标全1与扰动范围不可精确复现 |
| Hard-coded constants | extensive | k=2/4/3、二次次数、手工簇重排、跳过成分索引、sqrt距离 | 选择依据/阈值不足 |
| Formula-to-code consistency | contradicted | 式(2)(11)、p.16预测法与附录B–D | 零值CLR/逆变换、人工簇顺序和平方根平移偏离标准定义 |
| Code-to-result consistency | not assessable | 对照表13–18与附录B | 缺输入和辅助函数；可见回归索引一致，但无法运行/复算 |
| Overall reproducibility | not reproducible | 全文p.1–29与全部附录p.30–41 | 原始数据和多数模型代码缺失，关键方法定义错误 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 风化×类型样本数 | 总计58 | `24+34=58`且列和`18+40=58` | pass | p.7 table 5 | 计数闭合 |
| 风化×类型Pearson统计量 | chi-square=6.880 | 由[[12,12],[6,28]]复算6.88039 | pass | p.7 table 5 | p≈.009一致 |
| 纹饰统计量 | 被称Yates=4.957 | 对[[11,0,13],[11,6,17]]复算Pearson=4.95654 | fail | p.8 table 7 | 数值是未校正Pearson |
| 颜色统计量 | 被称Yates=6.287 | 对2×8表复算Pearson=6.28714 | fail | p.7 table 6 | 数值是未校正Pearson |
| Yates适用维度 | 对2×8、2×3使用 | 标准连续性校正针对2×2 | fail | p.7 equation (5); tables 6–7 | 应考虑精确/Monte Carlo方法 |
| 颜色分析样本数 | 删除4个缺颜色后 | `24+30=54=58-4` | pass | p.5、p.7 table 6 | 数据删除闭合 |
| CLR零值 | 原始0在代码中保留为0 | 标准CLR要求正值；0不等于`ln(0/g)` | fail | p.5 equation (2); p.40 code | 需零替换/零模型 |
| CLR逆变换可逆性 | 声称恢复组成 | 变换后真实0与原始0都被逆代码当作缺失0 | fail | p.38–41 code | 映射非双射，虽能归一到1 |
| 变异系数 | 多项为负且“不分析” | `CV=sd/mean`在CLR负/近0均值下不适用 | concern | p.8–10 equation (6), table 8 | Na2O均值.013导致CV27.25 |
| 二次回归自由度 | 四阶段中心拟合二次式 | n=4、参数3，残差df=1 | concern | p.14–15 tables 13–16 | 高R²很容易出现 |
| 扰动范围总结 | 正文称[0.1,0.2] | 表25最小0.05、最大0.20 | fail | p.24 table 25/paragraph | 摘要同样漏掉0.05 |
| 未知样本边界裕量 | 声称远离阈值 | 风化最小`|12.23-6.155|=6.075`；未风化最小8.495 | pass | p.25 paragraph | 仅对PbO单变量成立 |
| SiO2灰关联离散度 | 高钾更集中、铅钡更分散 | 表28范围0.093 vs0.324；均值0.9608 vs0.9418 | pass | p.28 table 28 | 只验证SiO2母序列 |
| 灰关联加权 | 声称加权关联度 | 权重未列，无法复算0.893–0.991 | not assessable | p.26 equation (20), p.28 table 28 | 关键参数缺失 |

## 14. Reusable Techniques

### 成分数据闭合后进入对数比空间

**When useful:** 特征是百分比且总和受约束时。

**Why useful:** 避免伪相关和奇异协方差，保留相对比例信息。

**Limitations:** 先明确结构零/检测限零并采用可说明的零替代；高维时优先ILR，不能把0直接写成CLR的0。

### 风化分层后的可解释阈值分类

**When useful:** 一个成分已表现出强分离、样本小且需要规则可解释时。

**Why useful:** 单阈值树易复核、部署和做边界裕量分析。

**Limitations:** 分层必须在训练折内完成；用重复/嵌套交叉验证报告不确定性，并检查测量误差。

### R型变量聚类后做Q型样本聚类

**When useful:** 特征高度相关、样本聚类易受重复信息支配时。

**Why useful:** 每组挑代表变量可减少冗余并提升解释性。

**Limitations:** 报告k选择、代表性准则和与直接Q/PCA/ILR的定量比较；NaN相关需处理。

### 预测结果闭合审计

**When useful:** 回归输出必须仍是组成时。

**Why useful:** 逆对数比确保非负和总和1，是必要的输出约束。

**Limitations:** “总和100%”只是可行性，不是真实准确度；仍需留出真值、误差和不确定区间。

## 15. Competition Takeaways

1. 百分比成分先识别闭合几何；零值必须单独建模或替代，再做CLR/ILR。
2. 稀疏r×c列联表不要泛用Yates；使用精确或Monte Carlo检验，并报告Cramér's V。
3. “未拒绝H0”不等于证明独立，结论必须保留统计边界。
4. 四个簇中心拟合二次曲线只能作探索，不能以高R²当预测验证。
5. 所有聚类/特征选择应在训练折内完成，防止70/30测试泄漏。
6. 扰动实验报告分布、次数、种子、翻转率和最坏样本；表述范围要与表格一致。
7. 异方法一致性是L2内部证据，不叫交叉验证；优先寻找真实标签或留出样本。
8. 灰关联必须列出分辨系数和权重，并把结果称为形状相似度而非机制相关。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 论文标题和四问主方法 | explicit | 1 | 摘要 | paragraph | direct transcription | N/A | 首页视觉确认 |
| 删除采样点15、17并闭合到100% | explicit | 4 | 5.1.1–5.1.2 | equation (1); paragraph | direct transcription | N/A | 85%–105%规则 |
| 正文给出CLR公式但文字缩写为alr | criticism | 5 | 5.1.3 | equation (2); paragraph | direct transcription | N/A | 公式是CLR |
| 化学空缺填0，颜色缺失删除4行 | explicit | 5 | 5.1.5 | paragraph | direct transcription | N/A | 颜色样本54 |
| 原始0被代码直接保留为CLR值0 | criticism | 40–41 | 附录D | code | direct transcription | N/A | 不满足log正值前提 |
| 风化×类型Pearson为6.880、p=.009 | explicit | 6–7 | 5.2 | table 4–5 | direct transcription | N/A | 独立复算通过 |
| 表6/7标为Yates但数值分别等于未校正Pearson | criticism | 7–8 | 5.2 | table 6–7 | independent calculation | N/A | 2×8与2×3亦不适用标准Yates |
| p=.507/.084只能表示未拒绝，不能证明颜色/纹饰独立 | criticism | 8 | 5.2 | paragraph | derived interpretation | N/A | 论文错误写“拒绝备择” |
| 描述统计在CLR坐标上计算 | explicit | 8–10 | 5.3.1 | table 8 | direct transcription | N/A | CV出现负值/巨大值 |
| CLR负或近零均值下CV缺乏通常相对离散解释 | criticism | 8–10 | 5.3.1 | equation (6); table 8 | derived interpretation | N/A | 作者也称负CV无意义 |
| Q聚类把高钾/铅钡各分风化与未风化 | explicit | 11–13 | 5.4.1 | figure 2; table 9–10 | direct transcription | N/A | 使用原始未CLR数据 |
| 四级风化时序由聚类簇命名和手工重排产生 | explicit | 13、34 | 5.4.2、附录B | table 11–12; code | derived interpretation | N/A | 无外部年代标尺 |
| 每成分用四个阶段中心拟合二次曲线 | explicit | 14–15 | 5.4.3 | table 13–16 | direct transcription | N/A | 残差df=1 |
| 低R²被解释为成分不受风化影响 | explicit | 15–16 | 5.4.3 | paragraph | direct transcription | N/A | 该推断并非唯一解释 |
| 平方根距离平移用于预测未风化CLR | explicit | 16、36–37 | 5.4.3、附录B | figure 3; code | notation normalization | N/A | 规则缺统计推导 |
| 逆变换保证预测组成总和100% | explicit | 16–17 | 5.4.3 | equation (11); table 17–18 | direct transcription | N/A | 闭合不是准确性验证 |
| 预测点与已知未风化点再聚类同类 | explicit | 18 | 结果分析与验证 | paragraph | direct transcription | N/A | 同源内部一致性 |
| 决策树阈值为未风化8.495%、风化6.155% PbO | explicit | 18–20 | 6.1 | figure 4–5 | direct transcription | N/A | 图5标题误写未风化 |
| 决策树单次70/30训练和测试指标均为1 | explicit | 18–19 | 6.1.2 | table 19–20 | direct transcription | N/A | 样本数/混淆矩阵未报 |
| 全数据聚类先生成风化标签再拆分训练测试，存在泄漏 | criticism | 11–19 | 5.4.1、6.1.2 | figure 2; table 9–10; paragraph | derived interpretation | N/A | 测试样本参与预聚类 |
| R型聚类固定3类并挑星号代表特征 | explicit | 20–22 | 6.2.1 | table 21–24 | direct transcription | N/A | 高钾风化有NaN |
| 表25实际扰动范围为0.05–0.20 | explicit | 24 | 6.3.2 | table 25 | direct transcription | N/A | 正文/摘要称0.10–0.20 |
| 树与Q聚类对A1–A8给出相同类别 | explicit | 24–25 | 7.1 | table 26–27 | direct transcription | N/A | 非独立“交叉检验” |
| 未知样本PbO最小阈值裕量为6.075和8.495个百分点 | interpretation | 25 | 7.2.1 | paragraph | independent calculation | N/A | 局部单变量稳定性 |
| 灰关联以每个成分轮流作母序列 | explicit | 25–28 | 8.1 | equation (15)–(20); figure 8–9 | direct transcription | N/A | 需权重与rho |
| SiO2母序列表中高钾/铅钡关联度范围分别0.093/0.324 | interpretation | 28 | 8.1.2 | table 28 | independent calculation | N/A | 支持该母序列的集中/分散差异 |
| 在已审查范围内，未发现Yates适用的精确检验替代、效应量或置信区间 | criticism | 5–8 | 5.2 | none found | derived interpretation | 卡方前提、表2–7和结论段均审查 | 原始附件不可得 |
| 在已审查范围内，未发现二次回归的留一阶段/真实风化前验证 | criticism | 13–18 | 5.4.2–5.4.3 | none found | derived interpretation | 时序表、回归表、预测表、再聚类段及附录B均审查 | 只有同源再聚类 |
| 在已审查范围内，未发现决策树重复切分、交叉验证、混淆矩阵或随机种子 | criticism | 18–20 | 6.1 | none found | derived interpretation | 决策树方法、图4–5、表19–20均审查 | 梯度提升未实现 |
| 在已审查范围内，未发现扰动实验次数、随机种子和翻转率 | criticism | 23–24 | 6.3.2 | none found | derived interpretation | 敏感性方法段与表25均审查 | “任意取数均不变”不可验证 |
| 在已审查范围内，未发现灰关联权重数值/来源和外部机制验证 | criticism | 25–29 | 8.1及评价 | none found | derived interpretation | 灰关联全部公式、图8–9、表28、差异结论和评价均审查 | 附录无灰关联代码 |
