# Paper: 基于价格弹性的蔬菜类商品自动定价与补货决策

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_38406b5bc61c
- Year: 2023
- Problem: C
- Award: 官方展示匹配；具体奖项等级未核验
- Provenance tier: O; 本地 PDF 的年份和题号与官方展示匹配，页数也与官方页面图像记录一致；官方展示不证明全国一等奖或其他具体奖级
- Source file: literature/raw_papers/2023/C228.pdf
- Source URL: unknown（用户提供的本地副本）
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2023qgdxssxjmjslwzs_2023ctlw/231104/1865128.shtml
- Pages: 70
- SHA-256: fb3f16b5294a6ea14781d3a824756af39a2700a2333d0df56c31ee3351188b10
- Extraction method: mixed；嵌入文本用于结构对照，中文主证据采用 Tesseract 5.5.0 chi_sim+eng OCR（250 DPI，PSM 3）和 Ghostscript 10.05.1 正确渲染后的人工视觉复核
- Extraction quality: 嵌入文本 70/70 页有字符，但因 Adobe-GB1 字体映射产生高控制字符比例，状态 poor_quality；默认 Poppler 又因缺 Adobe-GB1 CMap 而把中文渲染为空，第一次 OCR 不可用。改用临时 Ghostscript 渲染兼容层重跑后，OCR 70/70 页成功，62,239 个可见字符，中位数 878 字符/页，无页级错误
- Page convention: 1-based physical PDF pages
- Visually checked pages: 1、5-7、10、15-33、39、46、48、51-52、56-61、64-67；核验标题/摘要、清洗阈值、时间序列图、偏相关与 FP-Growth、双对数回归表、LSTM 参数/指标、价格修正式、PSO 目标和解、VIKOR/NSGA-II 公式、鲁棒性图、结果表及公式—代码矛盾
- Unresolved extraction ambiguities: 代码附录为排版图像，少量 OCR 标点不可靠；所有本报告引用的关键代码行均回看 Ghostscript 渲染页。中心公式、表格和结论均可读，未留下阻断性歧义
- Supplemental artifacts: p.31 列出 13 个 Python 文件、6 个 SPSSPRO 输出文件及 XLSX 支撑材料；PDF 内仅提供部分代码清单和部分结果表，实际源文件、原始附件、支撑 DOCX/XLSX 未随本地论文提供

## 1. Problem Archetype

本文是“高维零售数据处理 → 描述与关联分析 → 需求弹性回归 → 时间序列预测 → 连续/混合多目标优化”的复合管线，主要原型为：

1. **零售交易数据工程**：自然连接四个附件，处理时间、分类变量、日/周/月/年聚合、异常利润率和滞销单品。
2. **时间序列与市场篮子描述**：ACF、时间序列分解、销量长尾、偏相关和 FP-Growth。
3. **统计需求模型**：双对数需求函数同时放入六类价格与总销售额，估计需求价格/交叉/支出弹性。
4. **机器学习预测**：LSTM 预测六类未来七天批发价和销量。
5. **连续决策优化**：把预测量经价格函数修正后，用 GBest-PSO 搜索品类加成率与进货量。
6. **多准则筛选和混合多目标优化**：VIKOR 从 45 个候选筛到 40 个，再用混合编码 NSGA-II 在利润和需求覆盖之间求 Pareto 解。

最有迁移价值的是模型接口设计；最主要的风险也位于接口：回归“弹性”、LSTM 输出、价格修正函数和优化器代码并未保持同一数学口径。

## 2. Problem Decomposition

论文按四问组织：

1. 先清洗、聚合数据，再从年/周/日、品类/单品、销量/交易次数三个颗粒度描述销售规律，并研究品类偏相关与单品日共现。
2. 用双对数回归估计品类销量—价格关系；用 LSTM 预测七天销量和批发价；把价格修正后的销量放入利润函数，逐日用 PSO 求六类加成率和进货量。
3. 从过去一周 48 个可售单品中删除周销量低于 2.5 kg 的 3 个，再用销量/订单数 VIKOR 删除后 5 个，得到 40 个候选；用 NSGA-II 同时最大化利润和需求覆盖。
4. 从竞争者价格、消费者预期/价格敏感度和居民收入/消费水平提出额外数据建议。

正文的顺序清楚，但“问题二按日独立”“问题三把需求度当作第二目标”等关键决策没有用留出数据或基线实验验证。

## 3. Data Processing

### 整合与聚合

- 附件 1/4 描述单品、分类和损耗，附件 2/3 描述销售和批发价；作者以单品编码作自然连接。
- 销售日期/时间转为时间序列，销售类型与是否打折作 one-hot 编码。
- 销量按日/周/月/年、单品/品类聚合；售价、进价和加成率按销量加权平均。

### 供应时间分类

- 规则 1：三年中至少一年可供天数大于 300，判为常年性。
- 规则 2：每年最大可供天数小于 15，判为时令性。
- 规则 3：四季都可供，且各季三年可供天数大于 20，修正为常年性。
- 规则 4：各季三年可供天数均小于 20，修正为时令性。
- 代码说明原始计数为常年 30、季节 151、时令 70；再从季节类转出 46 和 12 后，应剩 93，不是正文写的 90。图 1 的 30%/37%/33%反而与 76/93/82 共 251 个吻合。

### 清洗

- Fisher 表使用 \(\begin{bmatrix}457&4\\830680&47362\end{bmatrix}\)，检验折扣与退货的关联。
- 利润率先按 3σ，再删除加成率大于 2 的记录，共报告删除 16,430 条。
- 删除 5 个完全无销量单品；正文称删除“销售天数小于 10、销量占比小于 3‰、无年周期”的 48 个。
- 附录代码的销量占比阈值实际为 0.00003，即 0.03‰，与正文 3‰ 相差 100 倍。

这些删除规则直接决定后续 198 个单品范围，却没有阈值敏感性、删除前后预测对照或训练集内拟合的隔离处理。

## 4. Models Used

### ACF 与时间序列分解

**Purpose:** 识别总销量和品类/单品销量的年、周、日周期及长期趋势。

**Inputs:** 按月、日、小时聚合的销量。

**Outputs:** ACF 峰值、趋势/季节/残差图和生活经验解释。

**Why selected:** 作者认为外部生活、工作、气候因素会造成周期。

**Important assumptions:** 聚合后序列可代表稳定周期；异常事件不会破坏周期解释。

**Key equations or mathematical structure:** \(p_k=\operatorname{Cov}(X_t,X_{t-k})/\operatorname{Var}(X_t)\)；正文介绍乘法分解，部分附录代码使用 additive seasonal_decompose。

**Implementation notes:** 年周期以 12 个月峰值、周周期以 7 天峰值、日内周期以 13 个有销量小时峰值解释。

### 偏相关与 FP-Growth

**Purpose:** 控制总销量后研究品类共变，并挖掘单品关联。

**Inputs:** 六品类日销量；每日出现的单品集合。

**Outputs:** 偏相关矩阵、频繁项集和关联规则。

**Why selected:** 偏相关用于剔除市场总量影响；FP-Growth 被认为比 Apriori 更适合大数据。

**Important assumptions:** 总销量足以控制共同时间/市场因素；“某日出现”可代表有效交易事务。

**Key equations or mathematical structure:** 偏相关假设检验；FP 树与支持度/置信度。

**Implementation notes:** 表 2 规则支持度 0.833-0.843、置信度 0.996，但事务是“每日可售/出现”，不是顾客购物篮。

### 双对数需求模型

**Purpose:** 对六品类销量的自身价格、交叉价格和总支出弹性进行估计。

**Inputs:** 六品类平均售价 \(P_k\)、六品类销量 \(Q_i\)、总销售额 \(x=\sum_i Q_iP_i\)。

**Outputs:** 六个回归方程的价格/支出系数和显著性。

**Why selected:** 作者称双对数需求函数可直接估计弹性。

**Important assumptions:** 同期价格与销量的方向可由 OLS 识别；总销售额作为支出变量外生；残差满足 OLS 要求。

**Key equations or mathematical structure:** \(\ln Q_i=\alpha_i+\sum_k e_{ik}\ln P_k+e_i\ln x+\epsilon_i\)。

**Implementation notes:** 表 3 的自身价格对角系数为 -0.186、-0.076、-0.221、-0.168、-0.430、-0.381；作者报告 F 检验 p=0.000、VIF<10，但未给样本数、残差、标准误或 VIF 明细。

### LSTM 预测

**Purpose:** 预测六品类未来七天批发价和销量。

**Inputs:** 每品类单变量历史序列，look-back 30。

**Outputs:** 七维预测、训练样本上的 R²/MSE/RMSE/MAE。

**Why selected:** 作者称 ARIMA、岭回归、灰色预测效果较差，LSTM 更能捕捉周期与趋势。

**Important assumptions:** 全历史拟合能代表未来；单变量历史足够；七个 Dense 输出对应七天。

**Key equations or mathematical structure:** 单层 6 单元 LSTM 接 Dense(7)，MSE + Adam。

**Implementation notes:** 表 4 写 400 epochs；附录 p.52 为 50。代码把 train_size 设为 len(data)+1，实际无留出集；训练目标是单个下一时点标量，却由 Dense(7) 同时拟合，七个输出没有对应七个不同预测步的监督标签。

### 价格修正与利润模型

**Purpose:** 让价格决策反馈到 LSTM 预测销量，并计算损耗/折扣后的利润。

**Inputs:** LSTM 销量/批发价、售价、品类损耗率、折扣率。

**Outputs:** 修正销量和利润。

**Why selected:** 作者希望把需求价格弹性显式接入优化。

**Important assumptions:** 同日销量相互独立；价格是唯一影响当日需求的决策变量；损耗品按固定折扣售出。

**Key equations or mathematical structure:** 正文式 (7) 为 \(\ln Q=\ln Q_{\text{pred}}+E_p\ln(P/P_{\text{pred}})\)；利润见式 (11)-(14)。

**Implementation notes:** PSO 代码没有实现式 (7)，而是用 \(Q=aP+bQ_{\text{LSTM}}+c\) 的线性函数；表 7 所称“弹性”是带单位斜率，且与表 3 的无量纲自身价格弹性不一致。

### GBest-PSO

**Purpose:** 逐日优化六品类加成率和进货量。

**Inputs:** 修正销量函数、六品类成本/损耗/折扣和变量上下界。

**Outputs:** 七天的加成率、进货量和目标利润。

**Why selected:** 连续非线性决策；作者希望通过先验粒子加快收敛。

**Important assumptions:** 罚函数足以代替 \(Q_i\le B_i\) 硬约束；变量上下界包含合理最优解。

**Key equations or mathematical structure:** \(f=-(M-T)+F\)，缺货罚 \(F=20(Q_i-B_i)\)。

**Implementation notes:** 1000 粒子、12 维、300 次迭代，\(c_1=c_2=0.5,w=0.6\)，30% 先验混合粒子；没有随机种子或重复运行。

### VIKOR

**Purpose:** 用最近一周销量和销售次数排序 45 个候选，留下前 40。

**Inputs:** 标准化销量与订单数。

**Outputs:** 群体效用 \(S_i\)、个体遗憾 \(R_i\)、折中指标 \(D_i\)。

**Why selected:** 作者强调同时考虑总体效用和最大遗憾。

**Important assumptions:** 两指标足以代表需求；等权和 \(v=0.5\) 合理。

**Key equations or mathematical structure:** 正文给出标准 VIKOR 归一化、\(S_i,R_i,D_i\)。

**Implementation notes:** 代码等权求 \(S=F_1+F_2\)、\(R=\max(F_1,F_2)\)，但折中指标括号写法与正文标准公式不一致。

### NSGA-II 混合优化

**Purpose:** 在 40 个候选中选 27-33 个，并同时优化利润和需求覆盖。

**Inputs:** 40 个二元选择、40 个加成率、40 个补货量，合计 120 维。

**Outputs:** Pareto 前沿、选定组合和定价/补货方案。

**Why selected:** 决策变量混合离散/连续，目标有利润和需求覆盖两个。

**Important assumptions:** 统一 10% 损耗、0.8 折扣和 0.5 价格反应权重可近似所有单品；单次 Pareto 解可选出“最优”。

**Key equations or mathematical structure:** \(f_1=M-T\)，\(f_2=\sum z_jD_j/\sum D_j\)，数量 27-33，最小陈列 2.5 kg。

**Implementation notes:** 正文称 400 次迭代，代码 MAXGEN=300、NIND=100、seed=1；最小陈列 CV 在代码中被注释掉。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| ACF + 时间序列分解 | selected | 周期/趋势描述 | 多时间颗粒适合识别生活规律 | ACF 峰值与分解图相互印证 | 无滚动稳定性、异常期前后比较 | 适合作描述证据，不等于预测验证 |
| FP-Growth vs Apriori | selected / Apriori rejected | 单品关联 | FP-Growth 更适合大规模数据 | 给出高支持度/置信度规则 | 无实际运行时间、阈值敏感性和购物篮定义比较 | 日共现会把长期可售品种制造成高支持度，业务解释需收窄 |
| 双对数需求函数 | selected | 估计价格弹性 | 系数可直接解释为弹性 | OLS 显著性和 VIF 总结 | 无基线、残差、内生性处理 | 形式可解释，但总销售额含因变量，不能作因果弹性 |
| ARIMA / 岭回归 / 灰色预测 | rejected | 七天预测 | 作者称效果较差 | not reported | 模型指标、参数、切分均缺失 | 不足以证明 LSTM 优越 |
| LSTM | selected | 七天成本/销量预测 | 捕捉长期依赖、周期与趋势 | 训练样本 R²/MSE/RMSE/MAE | 无 hold-out、滚动回测、重复训练 | 报告指标只能证明样本内拟合 |
| GBest-PSO | selected | 连续利润优化 | 非线性连续变量；先验初始化加快收敛 | 与历史图中“通常利润”定性比较 | 无标准 PSO/其他求解器、重复运行、最优性差距 | 输出受上下界驱动，且一个报告方案违反硬约束 |
| VIKOR | selected | 需求排序 | 兼顾群体效用与个体遗憾 | 得到前 40 | 无权重/参数敏感性或其他排序法 | 适合预筛选，但代码公式需先修正 |
| NSGA-II | selected | 混合双目标优化 | 混合编码、非支配排序和存档 | 单次 Pareto 前沿 | 无不同种子、基线、HV/spacing 报告值或选点规则 | 可生成候选前沿，不能支持“唯一最优” |

## 5. Model Pipeline

\[
\text{四附件}
\rightarrow \text{连接/聚合/清洗}
\rightarrow
\begin{cases}
\text{ACF/分解/偏相关/FP-Growth}\\
\text{双对数需求回归}
\end{cases}
\rightarrow \text{LSTM 七天预测}
\rightarrow \text{价格修正}
\]

然后分为两条决策链：

- 品类层：价格修正 + 损耗/折扣利润 → GBest-PSO → 七天六品类方案。
- 单品层：近一周可售 48 → 2.5 kg 过滤 45 → VIKOR 前 40 → 加权均值预测 → NSGA-II → 7 月 1 日 33 个单品方案。

接口审计显示：正文双对数弹性没有直接进入 PSO；问题三又用统一 0.5 价格权重替代品类/单品弹性，预测不确定性也没有传播进优化。

## 6. Model Improvements

1. **统计预测 → LSTM**：作者称经典模型效果差，转向非线性序列模型；但没有保留基线结果。
2. **LSTM → 加价格外生修正**：意识到纯时间序列预测无法响应定价，这是正确的接口方向；实现却从对数弹性变成线性回归。
3. **标准 PSO → 先验初始化 + 罚函数**：30% 粒子围绕经验初值，70% 随机；缺货约束转罚项。
4. **直接全单品优化 → 业务过滤 + VIKOR 降维**：48→45→40，降低 120 维混合优化难度。
5. **传统 GA → BG/RI 混合编码 NSGA-II + 全局存档**：适应二元/连续混合变量并保留 Pareto 多样性。

作者没有给标准 PSO/NSGA-II 与改进版在相同目标和随机种子下的收敛曲线、运行时间或解质量比较，因此只能确认实现修改，不能量化改进收益。

## 7. Parameter Estimation and Optimization

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| history window | 原始销售期 | date | p.2 | 2020-07-01 to 2023-06-30 | problem-provided | N/A - given | no | 约 3 年 |
| annual-day threshold | 常年单品规则 | day/year | p.5 | >300 in any year | author-assumed | rule | no | 规则 1 |
| seasonal-day threshold | 时令单品规则 | day/year | p.5 | <15 annual maximum | author-assumed | rule | no | 规则 2 |
| four-season threshold | 分类修正规则 | day/season across 3 years | p.5 | >20 or <20 | author-assumed | rule | no | 规则 3/4 |
| markup outlier cutoff | 加成率异常阈值 | dimensionless | p.7 | >2 plus 3σ | author-assumed | deletion rule | no | 删除 16,430 条 |
| dead-stock days | 低频单品阈值 | day | p.7 | <10 | author-assumed | deletion rule | no | 与销量占比联合 |
| dead-stock share | 低销量占比阈值 | ratio | p.7 vs p.43 code | 3‰ in text; 0.03‰ in code | algorithm hyperparameter | hard-coded | no | 100× contradiction |
| \(k\) | 损耗品折扣率 | dimensionless | p.18 Eq. (5) | 0.7 | data-estimated | 打折/不打折售价比加权平均 | no | 品类 PSO 使用 |
| \(L_i\) | 六品类损耗率 | fraction | p.64 code | 0.1283, 0.1551, 0.1365, 0.0668, 0.0924, 0.0945 | data-estimated | 单品损耗率加权平均 | no | 代码硬编码 |
| Double-log coefficients | 价格/支出弹性 | dimensionless | p.17 Table 3 | 7 predictors per response | data-estimated | stated OLS | no | 样本数、标准误未报告 |
| look_back | LSTM 输入窗口 | day | p.52 code | 30 | algorithm hyperparameter | hard-coded | no | 单变量 |
| LSTM units / outputs | 隐层单元/输出单元 | count | pp.19,52 | 6 / 7 | algorithm hyperparameter | hard-coded | no | 七输出没有七步标签 |
| epochs | LSTM 训练轮数 | count | p.19 vs p.52 | 400 text / 50 code | algorithm hyperparameter | not reconciled | no | 明确矛盾 |
| batch / optimizer | LSTM 训练设置 | count / N/A | p.19 | 1 / Adam | algorithm hyperparameter | hard-coded | no | 无 seed |
| Table 7 slopes | 所谓品类“弹性” | kg per yuan in code | pp.20,65 | -1.92,-0.26,-0.07,-0.029,-0.51,-0.03 | data-estimated | not reported | no | 非无量纲弹性，与表 3 不一致 |
| PSO population / iterations | 粒子数/迭代 | count | pp.64,67 | 1000 / 300 | algorithm hyperparameter | hard-coded | no | 七天各跑一次，不是重复验证 |
| PSO \(c_1,c_2,w\) | 学习与惯性参数 | dimensionless | p.66 | 0.5,0.5,0.6 | algorithm hyperparameter | hard-coded | no | 无收敛敏感性 |
| prior share | 人工先验粒子比例 | fraction | pp.22,64 | 0.30 | algorithm hyperparameter | 0.8 random draw + 0.2 empirical point | no | 正文措辞“人为设定”不完全准确 |
| stockout penalty | \(Q>B\) 罚系数 | currency per kg | pp.22,66 | 20 | author-assumed | hard-coded | no | 没有保证硬可行 |
| markup bounds | 六类加成率范围 | dimensionless | p.64 code | lower 0.3/0.2/0.2/0.3/0.3/0.3; upper 1.2/0.98/0.8/0.9/1.2/1.0 | algorithm hyperparameter | historical information | no | 7/1 有 5/6 落在上界 |
| VIKOR \(v\) | 群体/遗憾权衡 | dimensionless | p.60 code | 0.5 | author-assumed | hard-coded | no | 两指标等权 |
| candidate count | 问题三候选数 | item count | pp.24-25 | 48→45→40 | data-estimated | 周可售、2.5 kg、VIKOR 后 5 | no | 最终选择 33 |
| item count | 问题三进货单品数 | item count | problem / Eq. (18) | 27-33 | problem-provided | constraint | no | code只保留此 CV |
| minimum display | 最小陈列量 | kg/item | problem / Eq. (19) | 2.5 | problem-provided | constraint | no | 公式错误，代码 CV 被注释 |
| NSGA population / generations | 种群/代数 | count | pp.27,58-59 | 100 / 400 text, 300 code | algorithm hyperparameter | hard-coded | no | seed=1, trapped count=20 |
| q3 loss / discount | 单品统一损耗/折扣 | fraction | p.56 code | 0.1 / 0.8 | author-assumed | hard-coded | no | 忽略 p.61 已载入的单品损耗 |
| q3 price weight | 统一价格反应权重 | dimensionless | p.57 code | 0.5 | author-assumed | hard-coded | no | 未使用表 7 或单品拟合 |

## 8. Validation

论文主要提供样本内拟合、内部一致性和单一扰动。没有留出期、滚动回测或外部真实销售验证。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 时间周期描述 | L2 — ACF/decomposition consistency | same sample | ACF peak and visual cycle | 3 scales | 12 months, 7 days, 13 active hours | COVID/holiday spikes not separately modeled | 同一序列、无滚动稳定性 | 支持所审阅历史中的周期描述 |
| 折扣与退货 | L1 — Fisher exact test | same sample | p-value | 1 | \(4.2921\times10^{-7}\) | causal direction unknown | 观察性关联、样本巨大 | 支持关联，不支持折扣导致退货下降 |
| 双对数回归 | L1 — in-sample OLS | same sample | F p-value; VIF | 6 regressions | p reported 0.000; VIF<10 | residual behavior not reported | 总销售额含因变量；无标准误表/样本量 | 支持样本内相关，不支持因果弹性 |
| LSTM 成本预测 | L1 — training fit | same sample | R²/MSE/RMSE/MAE | 6 categories | R² 0.62-0.96, mean 0.835 | 食用菌 R²=0.62 | 全数据训练、只用第一个输出算指标 | 只支持训练拟合 |
| LSTM 销量预测 | L1 — training fit | same sample | R²/MSE/RMSE/MAE | 6 categories | R² 0.75-0.86, mean 0.8183 | none reported | 无留出、Dense(7) 目标错误 | 只支持训练拟合 |
| 价格修正函数 | L1 — stated improved fit | same sample | not reported | not reported | “拟合效果较优” | coefficients conflict with Double-log | 无指标、无切分、单位不一致 | 不能确认弹性修正可靠 |
| PSO 七日利润 | L2 — same-history range comparison | same sample | optimized profit vs visually inferred 1000-1500 | 7 daily runs | 1745.22-1810.02, mean 1785.84 | 7/1 方案违反 \(Q\le B\) | 基线非同日同输入求解；无重复种子 | 只说明优化器输出高于作者选定历史区间 |
| NSGA-II | L2 — internal Pareto output | same sample | \(f_1,f_2\), Pareto plot | 1 seeded run | \(f_2=0.9667\); reported \(f_1=16686\) | \(f_1\) 与图轴数量级冲突 | 陈列约束未实现、选点规则缺失 | 只支持生成一组候选组合 |
| LSTM 扰动 | L3 — input noise perturbation | same sample | output range | about 18 plotted trials | 3.1589-3.9382 | “<5%”复算失败 | 扰动标准差、基线、seed 未报告 | 支持输出会随扰动变化，不支持 5% 稳健性 |

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 辣椒成本输入正态扰动 | not reported | “微小”，方差/标准差 not reported | normal random noise, about 18 plotted trials | LSTM output min/max | 3.1589-3.9382 | unclear | 全范围相对中点约 21.96%，与正文“5%以内”矛盾；没有可复现扰动设置 |

在已审查范围内，未发现预测窗口、LSTM 随机初始化、价格弹性、清洗阈值、PSO 变量界/罚系数、VIKOR 权重或 NSGA-II 不同种子的敏感性分析。审查覆盖 pp.1-30 全部正文与鲁棒性、pp.31-70 附录/代码；外部支撑文件不可用。

## 10. Visualization Strategy

- 年/月/日总销量、六品类销量、供应类型和长尾累计图将多颗粒数据结构直观化。
- ACF 与时间序列分解并排展示，能让周期峰值和周期形态相互对照。
- 偏相关热图和 FP-Growth 表适合表达类别/单品关系，但文本把负相关误称“互补”，图不能替代经济学识别。
- 图 17 把 LSTM 训练拟合画成实际—预测叠线，却没有时间留出分界或未来七日真实值。
- 图 18 用历史利润折线作 PSO 结果背景；缺少同日基线、置信区间和利润分解。
- 图 19 给 Pareto 前沿，但未标被选点或选点规则，且正文 \(f_1\) 与横轴不一致。
- 图 20 给扰动输出范围，但不显示扰动幅度、基准输出和相对误差，导致“5%”无法由图支持。

## 11. Writing Structure

论文按“数据工程 → 描述规律 → 回归与预测 → 连续优化 → 混合多目标优化 → 数据建议 → 鲁棒性 → 40 页附录”推进，结构完整。优点是每问都有流程图，附录也覆盖主要代码。主要写作问题是：

- 多次把生活经验、同源图形或训练拟合称为“验证准确性”；
- 方法名称与实际实现不同，如对数弹性变线性斜率、硬约束变罚函数；
- 正文参数与代码不一致（LSTM 400/50、NSGA 400/300）；
- 关键结论出现源内矛盾（季节单品 90/93、辣椒 7/7 预测 4.06/102.2766、\(f_1\) 数量级）。

## 12. Strengths

1. 以自然连接、时间处理和多颗粒聚合开场，说明复杂附件如何进入后续模型。
2. 将“价格—销量”接口显式放在预测和优化之间，方向上优于把销量预测直接当固定需求。
3. 问题二/三分别识别连续与混合决策结构，选择 PSO 与混合编码 NSGA-II，问题分解有针对性。
4. 对商品数量上限造成的需求不能完全满足进行双目标建模，而非只最大化利润。
5. 附录保留了大量实现细节，足以发现训练切分、边界解、公式—代码和结果表问题。
6. 提出竞争价格、消费者预期和收入数据，正确指出仅用内部历史价格的外推边界。

## 13. Weaknesses

1. **时序验证缺失。** LSTM 使用全部数据训练，指标是训练拟合；七维输出没有七步监督标签。
2. **弹性接口不一致。** 表 3 是无量纲对数系数，表 7/PSO 是线性价格斜率；公式 (7) 未进入代码。
3. **内生性/泄漏。** 总销售额 \(x=\sum Q_iP_i\) 包含被解释销量，同期 OLS 不能直接作因果支出弹性。
4. **约束未被执行。** PSO 用软罚替代 \(Q\le B\)，表 9 已出现缺货；NSGA 最小陈列 CV 被注释。
5. **边界解主导。** 7 月 1 日六类加成率有五个等于代码上界，未做边界/界值敏感性。
6. **问题三统一硬编码。** 所有单品损耗 10%、折扣 0.8、价格权重 0.5，未使用已加载的单品损耗或拟合弹性。
7. **验证语言过强。** 正态扰动范围复算约 22%，并非 5%；历史利润背景也不是同日基线。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable in repository | pp.2,31 列出四附件和支撑表；仓库只有 PDF | 无法重跑连接、清洗、回归、LSTM 和优化 |
| Code availability | partial | pp.39-70 提供排版后的代码清单 | tool 模块、全部源文件、SPSSPRO 输出和中间 CSV/XLSX 不可用 |
| Dependency / environment information | not reported | pandas/numpy/scipy/sklearn/statsmodels/keras/pyswarms/geatpy/fuzzywuzzy 等 | 无版本、Python、TensorFlow 后端信息 |
| Random seed | partial | NSGA-II seed=1；LSTM、PSO、扰动无 seed | 主要预测和 PSO 结果不可确定复现 |
| Hard-coded constants | extensive | pp.52,56-59,64-66 | 清洗阈值、统一损耗/折扣、价格权重、罚系数、变量界均无审计 |
| Formula-to-code consistency | contradicted in several central links | 对照 pp.17-27 公式与 pp.48,51-52,56-60,64-67 代码 | OLS 约束、弹性函数、最小陈列和损耗参数不一致 |
| Code-to-result consistency | partial with contradictions | 对照 pp.19,27,32,38-39 与代码 | 400/50、400/300、辣椒 4.06/102.2766、\(f_1\) 数量级冲突 |
| Overall reproducibility | not reproducible | 70 页全文与仓库文件已审阅 | 缺数据/源文件/环境，且中心公式—代码矛盾尚未消解 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 分类计数闭合 | 初始季节 151，转出 46 与 12，剩 90 | 151-46-12=93 | Fail | pp.5-6 paragraphs/figure 1 | 76/93/82 对应 30.28%/37.05%/32.67%，与图 30/37/33%一致 |
| Fisher 方向 | 折扣时退货概率更低 | 4/47366=0.00845%；457/831137=0.05498% | Pass | p.6 figure 2; p.46 code | 只验证关联方向，不验证因果 |
| 清洗占比阈值 | 正文销量占比小于 3‰ | 代码 threshold=0.00003=0.03‰ | Fail | p.7 paragraph; p.43 code | 相差 100 倍 |
| LSTM 成本平均 R² | 摘要称平均 R² 超过 0.8 | 六值均值 0.835 | Pass | p.19 table 5 | 但全为训练拟合 |
| LSTM 销量平均 R² | 摘要称平均 R² 超过 0.8 | 六值均值 0.8183 | Pass | p.19 table 6 | 但全为训练拟合 |
| RMSE/MSE 关系 | 花叶销量 MSE 1129.01, RMSE 33.60 | \(33.60^2=1128.96\) | Pass | p.19 table 6 | 舍入一致 |
| LSTM epochs | 表 4 为 400 | 代码 model.fit epochs=50 | Fail | p.19 table 4; p.52 code | 未说明使用哪个生成结果 |
| 7/7 辣椒销量 | 附录 C 为 4.06 | PSO 输入代码为 102.2766 | Fail | p.32 table; p.64 code | 4.06 实为同日食用菌进价量级，疑似粘贴错误 |
| 7/1 库存约束 | 模型要求 \(Q_i\le B_i\) | 花菜修正销量 24.14 > 进货量 23.37，短缺 0.77 kg（3.19%） | Fail | p.23 table 9 | 罚函数没有保证硬可行 |
| 7/1 加成率边界 | 输出为最优内部解 | 1.20/0.98/0.80/0.88/1.20/1.00；其中 5/6 等于代码上界 | Concern | p.23 table 9; p.64 bounds | 需要界值敏感性 |
| 七日利润均值 | 表 21 七值 | 独立平均 1785.8401 | Pass | p.39 table 21 | 基线 1000-1500 不是同日计算 |
| 问题三式 (19) | \(2.5\le z_jB_j\le Q_j\) 且允许 \(z_j=0\) | 若 \(z_j=0\)，左式变 2.5≤0，不可能 | Fail | p.25 Eq. (19) | 与 27-33 个选择约束冲突 |
| 最终单品数 | 附录 D 给全部方案 | p.32 七项 + p.33 二十六项 =33 | Pass | pp.32-33 appendix D | 在允许的 27-33 上界 |
| NSGA 代数 | 正文 400 次 | 代码 MAXGEN=300 | Fail | p.27 paragraph; p.58 code | seed=1 |
| NSGA 利润尺度 | 正文 \(f_1=16686\) | Pareto 图横轴约 1525-1715 | Fail | p.27 figure 19 | 至少差约 10 倍，无法确认选点值 |
| 扰动幅度 | 输出 3.16-3.93 且“5%以内” | 精确范围 3.1589155-3.93817；range/midpoint=21.96% | Fail | pp.29-30 figure 20 | 扰动输入尺度未报告 |

## 14. Reusable Techniques

### 多颗粒零售数据聚合

**When useful:** 交易级数据需要同时服务描述、预测和优化。

**Why useful:** 日/周/月/年与单品/品类双维度聚合能把不同模型需要的接口统一起来。

**Limitations:** 聚合必须在训练/验证切分之后拟合，且不能用销量加权价格制造同期内生性而不说明。

### 弹性—预测—优化接口

**When useful:** 决策价格会反过来改变需求，不能把预测需求视为固定。

**Why useful:** 先预测基准需求，再通过价格响应函数更新需求，最后优化利润。

**Limitations:** 响应函数单位和回归系数必须一致；需要留出期估计和不确定性传播。

### 预筛选后做混合多目标优化

**When useful:** 候选单品多、决策含二元选择和连续数量。

**Why useful:** 业务过滤和 VIKOR 可减少维度，NSGA-II 保留利润—覆盖权衡。

**Limitations:** 预筛选可能排除互补组合；权重、阈值和筛选稳定性必须测试。

### 先验初始化的群体智能

**When useful:** 有历史可行方案且搜索空间大。

**Why useful:** 将一部分初始种群放在经验区域，可减少早期无效搜索。

**Limitations:** 应与全随机多种子比较，报告收敛速度和解质量；先验比例本身也需敏感性。

### 源内公式—代码—结果三向校验

**When useful:** 论文提供长代码附录和结果表。

**Why useful:** 能发现无留出、参数冲突、被注释约束、边界解和粘贴错误。

**Limitations:** 缺数据时只能审计结构和算术，不能替代端到端运行。

## 15. Competition Takeaways

1. 时间序列必须按时间留出或滚动回测；训练 R² 不得写成未来预测准确率。
2. 多步预测要构造对应每个 horizon 的标签，不能用一个下一步标签训练 Dense(7) 后直接称七天预测。
3. 价格弹性是无量纲比率；若实现使用线性价格斜率，必须改名并保持单位一致。
4. 总销售额含被解释销量时存在同期内生性，至少做滞后、工具变量或明确仅作相关模型。
5. 罚函数不能自动替代硬约束；交付前逐行检查 \(Q\le B\)、陈列量和选品数量。
6. 对 PSO/GA 报告多种子、基线、边界命中率和约束违反量，不把单次最好值写成全局最优。
7. 清洗阈值、损耗率、折扣率和 VIKOR 权重都应进敏感性表，并确保正文与代码数值一致。
8. Pareto 前沿必须说明选点规则，并核对正文数值与坐标轴数量级。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 论文构建数据分析—弹性—LSTM—PSO—VIKOR—NSGA-II 管线 | explicit | 1 | 摘要 | paragraph | direct transcription | N/A | 方法链来自作者 |
| 官方展示匹配但奖级未知 | explicit | unknown | acquisition metadata | paragraph | direct transcription | N/A | 官方展示不等于一等奖 |
| 默认 Poppler 因 Adobe-GB1 丢失中文，需 Ghostscript 渲染后 OCR | criticism | 1-70 | extraction QA | none found | derived interpretation | 默认 Poppler 70 页、首次 OCR、Ghostscript 重渲染和第二次 OCR 均检查 | 最终 OCR 70/70 可用，无中心 blocker |
| 数据按附件连接并按多颗粒聚合 | explicit | 4-5 | 5.1 | flowchart, equations (1)-(3) | direct transcription | N/A | 售价/成本按销量加权 |
| 分类最终季节性应为 93 而非 90 | criticism | 5-6,39 | 5.2 与附录 I | paragraphs and code | independent calculation | N/A | 151-46-12=93；百分比也支持 93 |
| Fisher 表显示折扣组退货率更低 | interpretation | 6,46 | 5.2(c) 与附录 L | figure 2 and code | independent calculation | N/A | 0.00845% vs 0.05498%，不作因果解释 |
| 正文与代码低销量阈值相差 100 倍 | criticism | 7,43 | 5.4 与附录 J | paragraph and code | independent calculation | N/A | 3‰ vs 0.00003 |
| ACF 年/周/日峰值用于周期解释 | explicit | 9-11 | 6.2 | figures 5-8 and paragraphs | direct transcription | N/A | 同源描述证据 |
| 负偏相关被作者解释成“挤占”后又称“互补品” | criticism | 15-16 | 6.4.3 | figure 15 and paragraph | derived interpretation | N/A | 术语内部矛盾，且数量相关不能识别替代/互补 |
| FP-Growth 高支持度来自每日出现项集 | explicit | 15-16,34-35 | 6.4.2-3 | table 2, appendix rules | derived interpretation | N/A | 不是顾客订单篮子 |
| 双对数模型包含六类价格和总销售额 | explicit | 17 | 7.1 | equation (4), table 3 | notation normalization | N/A | 总销售额含 \(Q_i\) |
| 总销售额作为同期解释量带来内生/机械相关风险 | criticism | 17 | 7.1 | equation (4) | derived interpretation | N/A | 无工具变量或滞后处理 |
| 附录回归代码额外强制七个系数和为 1 | criticism | 48 | 附录 M | code | direct transcription | N/A | 正文 OLS 未报告该约束 |
| LSTM 表 4 写 400 epochs、代码写 50 | criticism | 19,52 | 7.2.3 与附录 O | table 4 and code | direct transcription | N/A | 无法确认结果版本 |
| LSTM 使用全部数据且指标为训练拟合 | criticism | 51-52 | 附录 O | code | derived interpretation | N/A | train_size=len+1，无 test |
| Dense(7) 用单步标量标签训练 | criticism | 52 | 附录 O | code | derived interpretation | N/A | 七输出没有七 horizon 标签 |
| 表 5/6 平均训练 R² 分别为 0.835/0.8183 | interpretation | 19 | 7.2.3 | table 5 and table 6 | independent calculation | N/A | 不升级为预测验证 |
| 表 7“弹性”与表 3 对角弹性不一致 | criticism | 17,20,65 | 7.1/7.3.1 与附录 T | tables 3/7 and code | derived interpretation | N/A | 代码用有量纲线性斜率 |
| PSO 用 30% 先验混合粒子、1000 粒子、300 迭代 | explicit | 22,64,66-67 | 7.3.3 与附录 T | paragraph and code | direct transcription | N/A | 无 seed |
| 7/1 花菜修正销量大于进货量 | criticism | 23 | 7.4 | table 9 | independent calculation | N/A | 24.14>23.37，违反式 (10) |
| 7/1 五个加成率命中上界 | criticism | 23,64 | table 9 / bounds | table and code | independent calculation | N/A | 需要边界敏感性 |
| 问题三 48→45→40 候选 | explicit | 24-25 | 8.1 | paragraphs | direct transcription | N/A | 两级预筛选 |
| 式 (19) 与二元选择逻辑矛盾 | criticism | 25 | 8.2.1 | equation (19) | independent calculation | N/A | z=0 时 2.5≤0 不可能 |
| NSGA 代码注释掉最小陈列 CV | criticism | 58 | 附录 Q | code | direct transcription | N/A | 只保留 27-33 数量 CV |
| 问题三统一使用 10% 损耗、0.8 折扣、0.5 价格权重 | explicit | 56-57 | 附录 Q | code | direct transcription | N/A | 与单品损耗数据接口断裂 |
| 问题三最终选择 33 个单品 | interpretation | 32-33 | 附录 D | table | independent calculation | N/A | 位于允许上界 |
| NSGA 正文 400 代、代码 300 代 | criticism | 27,58 | 8.3 与附录 Q | paragraph and code | direct transcription | N/A | seed=1 |
| \(f_1=16686\) 与 Pareto 横轴约 1525-1715 冲突 | criticism | 27 | 8.3 | figure 19 and equation | independent calculation | N/A | 数量级不闭合 |
| 附录 C 的 7/7 辣椒 4.06 与代码 102.2766 冲突 | criticism | 32,64 | appendix C/T | table and code | independent calculation | N/A | 影响第七天方案输入 |
| LSTM 扰动范围不支持“5%以内” | criticism | 29-30 | 模型鲁棒性检验 | figure 20 and paragraph | independent calculation | N/A | range/midpoint=21.96% |
| 在已审查范围内未发现时序留出或滚动回测 | criticism | 1-70 | 正文、结果、附录 | none found | derived interpretation | pp.1-30 正文、pp.31-70 结果和代码均审阅；外部支撑文件不可用 | 训练图不算留出验证 |
| 在已审查范围内未发现 PSO 多种子或边界敏感性 | criticism | 20-23,64-67 | PSO 模型与代码 | none found | derived interpretation | PSO 正文、表 8-9、完整附录 T 已审阅 | 单次每日报告不算重复 |
| 在已审查范围内未发现关键清洗/弹性/VIKOR/损耗参数敏感性 | criticism | 1-70 | 参数、鲁棒性、附录 | none found | derived interpretation | pp.5-7、17-30 及相关代码 pp.39-67 均审阅 | 唯一扰动是 LSTM 输入噪声 |
| 端到端复现不可行 | criticism | 31-70 | 附录 | code | derived interpretation | 支撑材料表、全部代码页和仓库可用文件已审阅 | 缺数据、源代码、tool 模块、环境与一致版本 |
