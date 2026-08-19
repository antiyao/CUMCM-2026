# Paper: 基于梯度下降的决策树算法与非线性规划的信贷风险评估与信贷策略模型

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_22d8f1ad3373
- Year: 2020
- Problem: C（源文件名误写为 `2020D`，首页与题意均为 2020 C 中小微企业信贷决策）
- Award: 本地合集声称“优秀论文”，未获独立奖项核验，不作为奖级证据
- Provenance tier: L（Yao 提供的本地历史论文合集；来源目录标签不证明奖项）
- Source file: literature/raw_papers/2020/2020D：基于梯度下降的决策树算法与非线性规划的信贷风险评估与信贷策略模型.pdf
- Source URL: unknown
- Verification source: unknown（题号纠正来自首页内容与 `literature/acquisition/local_metadata_overrides.csv`，不是奖项核验）
- Pages: 77
- SHA-256: b338495c2b38026269c56cd83118037e8dbf3d9633f00acbc88795ca6b3bcc3c
- Extraction method: Tesseract 5.5.0 `chi_sim+eng` OCR fallback（250 DPI，PSM 3）+ 全页视觉复核
- Extraction quality: 原 PDF 为纯图像，embedded text 77/77 页为空；OCR 77/77 页无 page error，76 页达到至少 30 个非空白字符，物理页 77 仅含代码结尾；公式、长表和代码均回看原页
- Page convention: 1-based physical PDF pages
- Visually checked pages: 全部物理页 1–77；重点放大核对 p1–3、5–19、21–30 的公式/表/图，p31–58 的完整结果表，p58–77 的 Python/MATLAB 代码；特别核对 p11–12、19、27–28、59–64、67、71–77
- Unresolved extraction ambiguities: OCR 对变量上下标、百分号和代码标点存在误识别；本报告的关键公式、系数和代码错误以页图为准；附录长向量只核对与主要主张相关的索引、系数、约束和边界，未逐个重录全部 425 家企业数值
- Supplemental artifacts: p31–58 给出结果长表，p58–77 给出页图形式的 Python/MATLAB 代码；引用的附件 1/2、处理后 Excel、`loans.csv`、股票 CSV、可执行源码、运行日志与依赖环境均未随本地论文提供

## 1. Problem Archetype

论文属于“表格数据工程 → 监督分类 → 风险评分 → 非线性信贷配置 → 外部冲击情景调整”的混合原型：

- 信贷违约建模：用梯度提升决策树（Gradient Boosted Decision Trees，代码实际为 XGBoost）预测企业违约概率。
- 信用评级迁移：用四分类 XGBoost 为 302 家无信贷记录企业预测 A/B/C/D 评级，再把预测评级送入违约模型。
- 信贷优化：用客户流失率—利率三次多项式、违约损失和企业额度上限构造 `fmincon` 非线性规划。
- 突发事件：以 COVID-19 为情景，结合股票代理和 72 家企业发票同比变化，手工调整行业额度上限和利率。

这是高复用的“预测到优化”管线，但论文中分类验证口径不统一、下游没有传播评级/违约概率不确定性，且附录代码存在会改变结果或阻止运行的错误。

## 2. Problem Decomposition

1. 从 2017–2019 年进销项发票提取规模、利润、利润率、增长率、退货率和信誉评级等指标。
2. 以 123 家有信贷记录企业训练二分类 XGBoost，输出违约概率；与单棵决策树和 BP 神经网络比较。
3. 拟合 A/B/C 三种评级的客户流失率 `q=f(i)`，再优化贷款金额与利率。
4. 以 123 家企业训练四分类评级模型，为 302 家无记录企业产生评级，再重复违约预测和配置。
5. 通过股票与发票构造 COVID-19 行业影响等级，调整额度/利率，报告 1 亿元信贷总额下的方案与收益。

预测—优化的模块边界清楚；但问题二把 0.22 违约损失改成“只损失利息、本金可追回”，问题三又在优化后直接乘利率折扣，导致三问不是同一目标/风险定义下的可比方案。

## 3. Data Processing

论文删除作废发票，因信息少而不研究 2016、2020 全年数据，以 2017–2019 为主体。若某企业某年只覆盖部分月份，则用相邻完整年份相同月份占全年比例进行等比例补齐。该方法依赖跨年季节结构稳定；论文没有报告补齐企业数、补齐幅度、对结果的影响或仅用过去信息的时间约束。

特征包括企业规模、平均利润、平均年利润率、平均利润增长率、平均营业额增长率、负数发票/退货率和信誉评级。D 级企业在信贷配置中直接不放贷。问题三按行业和规模分类，并随机抽取 72/302 家做 2020 年 1–2 月同比分析，但抽样种子、抽样清单生成代码和代表性权重未报告；样本还不含餐饮业。

附录 MATLAB 代码提供发票导入、按月/年汇总和负数发票比例函数，但使用硬编码 Windows 路径；分母为 0 时的利润率/增长率保护也未见。ML 特征在全数据上形成后随机拆分，没有时间顺序验证。

## 4. Models Used

### XGBoost 违约概率模型

**Purpose:** 对 123 家企业做二分类并输出违约概率。

**Inputs:** 七项经营/信誉指标。

**Outputs:** 违约标签、概率和特征重要度。

**Why selected:** 作者认为单树易过拟合，Boosting、二阶泰勒展开和正则项可形成更强分类器。

**Important assumptions:** 标签与特征时间顺序正确；信誉评级不是目标泄漏；随机折叠可代表未来企业；概率已校准。

**Key equations or mathematical structure:** 加法树模型、XGBoost 二阶近似和分裂 Gain，见式 (7)–(27)。

**Implementation notes:** 代码 `max_depth=18, n_estimators=1000, learning_rate=.1`，以五折 AUC 早停选树数，随后在全部数据拟合并在同一训练集打印 Accuracy/AUC。

### XGBoost 信誉四分类模型

**Purpose:** 给 302 家无记录企业预测 A/B/C/D。

**Inputs:** 企业规模、利润、利润率、增长率、产品/服务质量等六项。

**Outputs:** 评级类别。

**Why selected:** 与问题一同为表格监督分类，作者复用梯度提升结构。

**Important assumptions:** 123 家训练样本足以覆盖四类；预测评级误差不会显著影响违约概率和配置。

**Key equations or mathematical structure:** 多分类 XGBoost，式 (41)–(45)。

**Implementation notes:** 附录代码定义 `params`，却调用未定义的 `param`；同时一个对象写 `num_class=5`、参数字典写 4。代码按页面无法运行，也没有评级准确率或混淆矩阵。

### 客户流失率三次多项式

**Purpose:** 把贷款利率映射为 A/B/C 客户流失率。

**Inputs:** 利率 `i`、信誉等级。

**Outputs:** `q=f(i)`。

**Why selected:** 二次拟合 Adjusted R² 已高，但作者依据高利率端斜率增大选择三次式。

**Important assumptions:** 历史流失关系可外推到优化利率；流失只由利率决定；多项式在 4%–15% 内保持概率范围。

**Key equations or mathematical structure:** `q=p1 i³+p2 i²+p3 i+p4`，表 5-3。

**Implementation notes:** 问题二代码把 A 级一次项从正文 `37.74` 写成 `27.74`，使 4%–15% 区间的 `q` 全为负；C 级常数也从 `-0.9846` 写成 `-0.9746`。

### 信贷配置非线性规划

**Purpose:** 在总额度、企业额度和利率边界下最大化预期收益并惩罚流失。

**Inputs:** 违约概率、客户价值、额度上限、流失率函数、违约损失率。

**Outputs:** 是否放贷、额度、利率、期望收益。

**Why selected:** 连续金额/利率与非线性流失函数适合一般非线性求解。

**Important assumptions:** 问题一违约损失率 0.22；问题二改为只损失利息；企业若期望收益非正即不放贷；局部解可代表“最优”。

**Key equations or mathematical structure:** 式 (29)–(40)、(46)–(63)；MATLAB `fmincon`。

**Implementation notes:** 没有梯度、退出标志、多起点或全局最优证据。问题二正文预算为不等式，代码用等式强制恰好 1 亿元。

### COVID-19 行业冲击情景

**Purpose:** 调整行业额度上限和利率。

**Inputs:** 代表股票、2020 年发票同比、手工行业影响等级、政策折扣。

**Outputs:** 调整后的 1 亿元贷款组合和 184.6552 万元期望收益。

**Why selected:** 作者希望同时表示市场风险、政策倾斜和社会效益。

**Important assumptions:** 上市公司股价代表中小微企业行业；72 家样本代表 302 家；手工比例量化合理。

**Key equations or mathematical structure:** 额度提升 20%–50%、利率优惠 10%–50%，式 (54)–(63)。

**Implementation notes:** 附录股票代码只抓取 `sh.600000` 在 2017-07-01 至 2017-12-31 的行情，不对应正文的 2020 年多行业股票；规划代码复用问题二目标，求解后再把部分利率乘 0.8/0.5，没有按式 (54) 重新优化。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| XGBoost/GBDT | selected | 违约预测 | 正则化与集成降低单树过拟合 | 96.75% accuracy；五折 AUC 早停代码 | hold-out confusion matrix、AUC值、校准、类不平衡指标 | 代码的96.75%是训练集 accuracy，不能证明泛化 |
| 单棵决策树 | rejected as weaker | 基线 | 作者称单树易过拟合 | 83.87% hold-out accuracy | 与XGBoost同一划分/特征的结果 | 基线代码单次75/25划分；比较口径不同 |
| BP神经网络 | rejected as weaker | 基线 | reported accuracy 59.3% | 单次代码 | 同数据/特征/划分证据 | 代码读另一个 `loans.csv` 且评估连续概率，比较不可接受 |
| 三次流失率多项式 | selected | `i→q` | 高利率端斜率增大，端点误差较小 | Adjusted R² .9972–.9977 | 留出误差、单调/概率约束、系数不确定性 | 样本内拟合高，但代码系数错误破坏概率语义 |
| 二次流失率多项式 | rejected | 简洁基线 | R²已>0.9但端点趋势不足 | 图5-4定性比较 | 同表数值和端点误差 not reported | 选择理由可理解，证据不足以量化改进 |
| `fmincon` | selected | 连续非线性配置 | MATLAB内置一般非线性规划 | 一组方案与目标值 | 多起点、solver status、KKT、全局/基线比较 | 只能称局部 best-found；问题二系数错误使解无效 |
| 股票+发票双层情景 | selected | COVID影响 | 宏观及时、微观贴近企业 | 股价表与72家同比表 | 融合权重、代表性检验、独立验证 | 最终分级主要手工决定，代码与正文数据窗不一致 |

## 5. Model Pipeline

`发票清洗/补齐 → 七项特征 → XGBoost违约概率 → 流失率曲线/额度上限 → fmincon`。

问题二在前端加 `XGBoost评级 → 预测评级作为违约特征`；问题三再加 `行业冲击标签 → 额度上限/利率后处理`。这条链使上游评级误差、概率校准误差和情景判断同时进入贷款决策，但论文只传递点估计，未传播任何不确定性。

问题一、二、三的损失口径还发生变化：0.22 本金损失 → 只损失利息 → 解后利率折扣。因而三问的收益差不只是政策情景差，也包含目标函数和实现变化。

## 6. Model Improvements

- 用 XGBoost 代替单树，确实加入树复杂度正则、行/列采样和五折早停；但深度 18 对 123 样本很大，只有树数被交叉验证。
- 以三次多项式改善高利率端拟合；代码系数抄错后该改进没有可靠进入问题二。
- 把客户流失成本和违约成本接入额度/利率联合选择，较单纯按评分排序更接近决策问题；但它是固定权重的单目标标量化，不是经过 Pareto 分析的多目标优化。
- 宏观/微观情景尝试加入外部冲击；最终代码仅做上限调整和解后折扣，未实现正文完整新目标。

## 7. Parameter Estimation and Optimization

风险模型的树数由五折 AUC 早停选取，其余 XGBoost 参数基本由作者设定。客户流失三次式由 MATLAB `cftool` 拟合。额度上限按规模设为个体 40、微型 60、小/中型 100 万元，客户价值为 1000/2000/5000/10000 元。问题一违约损失率 0.22 来自文献；问题二因可贷企业过少而直接改为“本金可追回、只损失利息”。

问题二代码的贷款和为等式 10000 万元；`fmincon` 初值取各变量上界（首项贷款改 20），没有多起点或停止信息。问题三先调整额度上限，调用相同问题二规划，再对两类行业利率乘 0.8/0.5；这个后处理改变目标和可贷条件后没有重新求解。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| analysis years | 主体发票年份 | year | p5 | 2017–2019 | author-assumed | 排除信息较少的2016/2020 | no | 补齐可用相邻完整年，包括未来年 |
| seven features | 违约模型特征 | mixed | p6–7 | 规模、利润、利润率、两类增长率、退货率、评级 | literature-derived | 文献筛选+数据构造 | no | 评级可能包含历史违约信息，时间顺序未证明 |
| XGB depth | 最大树深 | level | p60 code | 18 | algorithm hyperparameter | author setting | no | n=123下过深风险高 |
| XGB trees/learning rate | 初始树数/学习率 | count / dimensionless | p60 code | 1000 / 0.1 | algorithm hyperparameter | 五折AUC早停只调树数 | partial | 早停后树数未报告 |
| row/column sampling | XGB采样率 | dimensionless | p60 code | 0.8 / 0.8 | algorithm hyperparameter | author setting | no | seed=27 |
| default threshold | 违约分类阈值 | probability | p13 | 0.5 | author-assumed | fixed | no | 无成本敏感阈值或校准 |
| rating split | 评级模型训练/测试 | proportion | p62 code | 70/30 | algorithm hyperparameter | random_state=0 | no | 代码因 `param` 未定义不可运行 |
| `i` | 年贷款利率 | proportion/year | p12, p19 | 0.04–0.15 | problem-provided | box constraint | partial | 问题三解后折扣可降到2.45% |
| `A_j` | 企业贷款金额 | 万元 | p9–12 | 10至额度上限 | author-assumed | fmincon连续变量 | no | 实际业务取整未建模 |
| `d` | 年度总信贷额度 | 万元 | p19, code p75 | 10000 | problem-provided | 正文≤；代码问题二= | no | 约束类型不一致 |
| `0.22` | 问题一违约损失率 | fraction of principal | p10 | 0.22 | literature-derived | 文献取值 | no | 问题二因不可贷过多而放弃该口径 |
| problem-2 loss | 违约时损失 | 万元 | p19式(46) | 只损失利息 | author-assumed | 为使R<.5企业可贷而改设 | no | 不是数据估计，显著改变风险 |
| `M_j` | 客户流失价值 | 元 | p10表5-2 | 1000/2000/5000/10000 | author-assumed | 最大贷款收益的10%–25%近似 | no | 主观且无校准 |
| churn coefficients | A/B/C流失率三次式 | mixed | p11表5-3 | 三组系数 | data-estimated | cftool三次拟合 | no | 代码A一次项、C常数与表不一致 |
| COVID micro sample | 企业抽样数 | count | p20, p24 | 72/302 | author-assumed | reported random sample | no | seed、抽样清单生成和权重 not reported |
| COVID policy factors | 额度/利率调整 | percentage | p26表7-8 | 额度+20%–50%；利率-10%–50% | author-assumed | 手工情景 | no | 代码仅用额度×1.3和利率×.8/.5 |
| fmincon initialization | 初值 | model units | p72/p76 code | upper bounds；首贷款20 | algorithm hyperparameter | single start | no | 无exitflag/KKT/多起点 |

## 8. Validation

论文报告 XGBoost 训练精度 97.24%、预测准确率 96.75%，单树 83.87%、BP 59.3%。附录显示风险 XGBoost 在全部 123 条上拟合并在同一 `dtrain` 上打印 Accuracy/AUC；五折只用于 AUC 早停且没有报告折外指标。96.75% 又恰为 `119/123`，与训练集计数一致。

单树代码使用 sklearn 默认 75/25 划分，123 条会产生 31 条测试样本；`26/31=83.87%`。因此 96.75% 训练集准确率与 83.87% hold-out 准确率不是同一验证口径。BP 代码读取 `loans.csv`，而且把阈值后的 `tr` 丢置一旁，最终用连续预测 `r` 调 `accuracy_score`，按常见 sklearn 会报错。三算法比较不能作为改进证据。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 风险XGBoost拟合 | L1 — in-sample fit | same sample | Accuracy | 1 | 96.75%（119/123） | 类别不平衡/概率校准未评估 | 代码在训练数据预测；无混淆矩阵 | 仅说明训练样本拟合 |
| XGBoost树数选择 | L2 — five-fold early stopping | same sample folds | AUC | 5 folds | result not reported | 折层化和重复性 not reported | 只用于选树数，最终无折外汇总 | 不能量化泛化性能 |
| 单树基线 | L1 — one hold-out split | hold-out | Accuracy | 1 | 83.87%（与26/31一致） | split variability unknown | 与XGB评价集/特征不一致 | 仅是单次基线 |
| BP基线 | not assessable | unknown | reported Accuracy | 1 | 59.3% | 附录代码评估连续概率且数据为`loans.csv` | 不能确认同数据、同特征、同划分 | 不可用于算法优劣比较 |
| 流失率曲线 | L1 — in-sample fit | same sample | Adjusted R² | 1 per rating | .9972/.9977/.9977 | 代码系数不一致 | 无留出、无概率边界诊断 | 只支持拟合样本上的曲线贴合 |
| 问题二配置 | L2 — budget/result closure | same model output | 总额度/期望收益 | 1 | 1亿元/199.635万元 | 负流失率系数、等式预算 | 无solver status、无独立业务结果 | 仅为该实现的局部输出 |
| COVID情景 | L3 — one scenario perturbation | same firms + external proxies | 期望收益变化 | 1 | 199.635→184.6552万元，-7.50% | 股票代码窗口不符；解后折扣 | 不是重复压力测试 | 仅说明手工政策情景下输出变化 |

## 9. Sensitivity and Robustness

论文没有对 XGBoost深度/树数、分类阈值、0.22损失率、客户价值、三次式系数、利率边界或 fmincon 初值做局部/全局敏感性。COVID 是一次情景改写，不是对同一模型的稳健性验证；问题二甚至改变违约损失定义，不能把可贷企业增加理解为模型稳健。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 违约损失口径 | 本金损失率0.22 | 改为仅损失利息 | one assumption switch | 可贷范围/配置 | 作者称原口径使大部分企业不可贷，改后R<.5可贷 | yes | 是模型定义改变，不是稳健性实验 |
| COVID政策情景 | 问题二方案 | 额度上限×1.3；利率×.8/.5等 | one hand-built scenario | 总额/期望收益 | 1亿元不变；收益减少14.9798万元（7.50%） | no for total budget; yes for profit | 情景有数值输出，但代码后处理未重新优化 |

在已审查范围内，未发现对随机划分、72家抽样、损失率、客户价值、利率边界或求解初值的重复扰动；该缺口的审查范围记录在 Section 16。

## 10. Visualization Strategy

论文用流程图组织四个子模型；用柱图展示特征重要度、评级/规模计数和平均违约概率；用散点+拟合曲线说明利率—流失关系；用股票折线、行业表和完整贷款清单展示 COVID 情景结果。

可视化覆盖从 EDA 到决策输出，但多数图没有误差条、折外性能或概率校准图。股票图只显示精选代表，72 家发票表也没有抽样不确定性，容易把描述性代理写成行业因果影响。

## 11. Writing Structure

正文 30 页按“分析—假设—问题一/二/三—评价—参考文献”展开，随后 47 页附录给出完整结果表和代码，材料定位较好。问题二复用问题一、问题三再扩展情景，读者容易跟随。

主要问题是证据口径没有随结论同步：训练准确率写成预测有效性；不同数据/划分的算法准确率被直接比较；手工情景和局部 fmincon 输出被称“最优”；“多目标”实为固定标量目标。正文、表和代码的若干系数/约束/数据窗口冲突没有被披露。

## 12. Strengths

- 对发票级数据做了年/月聚合、缺失补齐、负数发票比例等实质性特征工程。
- 给出 XGBoost 二阶目标和较完整超参数代码，而非只列模型名称。
- 贷款模型同时显式写出违约、流失、额度、利率和客户价值，便于审计模型接口。
- 附录包含 425 家企业的评级/风险/配置长表以及 Python/MATLAB 代码，结果可追踪性好于只给摘要值的论文。
- COVID情景明确区分宏观股票代理和微观发票代理，并主动承认租赁/商务服务子行业结论冲突。

## 13. Weaknesses

分类验证存在严重不公平：XGBoost用训练集准确率，单树用hold-out，BP代码用另一个数据文件且不可按页运行。信用评级代码本身也因 `param` 未定义而失败；评级误差却直接传给违约和优化。

优化接口更严重：问题二流失率 A 级系数使概率为负，C级常数也抄错；正文预算≤，代码强制=；问题三求解后才改利率，没有重新优化。股票代码还抓取2017年单一股票而不是正文2020年多行业数据。故报告的方案不能视为已复现的最优信贷策略。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable | 正文/代码引用附件1、附件2、处理后Excel、`loans.csv`和股票CSV | 无法重跑特征、分类、情景和规划 |
| Code availability | partial | p58–77代码页图，非独立源码 | 可审计逻辑；需人工重录且多段不可运行 |
| Dependency / environment information | unavailable | sklearn/xgboost/keras/MATLAB函数名可见，无版本 | deprecated API与求解器版本会影响运行 |
| Random seed | partial | 风险XGB 27；评级代码0/1000；单树/BP 1 | 72家抽样无seed；无多次重复 |
| Hard-coded constants | extensive | 路径、企业索引、概率向量、M/E、政策类别和系数大量硬编码 | 数据—代码对应易错，迁移性差 |
| Formula-to-code consistency | contradicted | p11/p19/p27与p71/p74–77 | A/C流失率系数、预算不等/等式、问题三目标与后处理不一致 |
| Code-to-result consistency | contradicted / not assessable | p58–77对照表5-3、6-4、7-9 | 评级`param`未定义；BP评估错误；股票窗口错误；无运行日志 |
| Overall reproducibility | not reproducible | 审查全部77页、附录结果表和代码 | 缺数据/环境/源码且关键管线含运行和语义错误 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 302家规模计数 | 个体56、微型203、小型43 | 56+203+43=302 | pass | p17 figure 6-2 | 无中型企业 |
| 302家评级计数 | A16、B162、C97、D27 | 16+162+97+27=302 | pass | p17 figure 6-2 | 与D索引27个闭合 |
| 单树accuracy | 83.87% | 默认25%测试得到31条；26/31=83.87097% | pass | p59 code/p12 result | 单次hold-out |
| XGB accuracy | 96.75% | 119/123=96.74797%，且代码在全部dtrain上预测 | concern | p60 code/p12 result | 极可能是训练计数，不能与单树hold-out比较 |
| 相对提升 | 对DT/BP提升15.36%/63.15% | `(96.75-83.87)/83.87=15.357%`；对59.3为63.153% | pass | p1,p12 | 是相对百分比，不是百分点；比较设计仍无效 |
| A级流失率正文范围 | 表5-3系数在4%/15%给q=.0258/.9175 | 均在[0,1] | pass | p11 table 5-3 | 正文系数在区间端点可行 |
| 问题二A级流失率代码 | 一次项被写成27.74 | q(.04)=-.3742，q(.15)=-.5825 | fail | p74 code | “流失率”为负，目标把流失成本变收益 |
| C级流失率常数 | 表为-.9846，代码为-.9746 | 代码q整体高0.01 | fail | p11 table 5-3/p71,p74 code | 公式—代码不一致 |
| 问题二预算约束 | 正文 `sum A_j <= d` | `mycon2`返回 `ceq=sum A-10000` | fail | p19 eq(47)/p75 code | 代码强制用满1亿元 |
| 问题二损失口径 | 0.22使多数不可贷，遂改为只损失利息 | 式(46)为`A*i*(1-2R)` | concern | p19 eq(46) | 为得到可行方案而改变现实假设，无敏感性 |
| 期望收益变化 | 199.635→184.6552，减少14.98和7.50% | 差14.9798；相对7.5036% | pass | p1,p28 | 算术闭合 |
| 问题三利率边界 | 式(57)为4%–15% | 表7-9/附录有2.45%、2.57%等 | concern | p27–28 table 7-9/p58 | 来自解后50%折扣；需明确是基准还是实际利率 |
| 问题三重新优化 | 正文式(54)称新规划 | 代码先跑`myfun2`，后乘利率.8/.5，再仅重算fval | fail | p27 eq(54)/p76–77 code | 折扣后的方案不是新目标的fmincon解 |
| 股票数据窗口 | 正文称2020-01-20至2020-07、多行业 | 附录仅查询`sh.600000`, 2017-07-01至2017-12-31 | fail | p22–24/p58–59 code | 所附代码不能生成表7-3/图7-4 |
| 行业频率表口径 | 表7-7标题称“同比降低频率” | 工业2升14降给12.50%，实为上升频率 | concern | p25 table 7-7 | 列头写上升频率，标题/解释需区分 |
| 评级代码类别/变量 | 四分类 | 对象写`num_class=5`，字典写4，调用未定义`param` | fail | p61–62 code | 代码按页无法运行 |
| BP准确率代码 | 先阈值化`tr` | 最终调用`accuracy_score(y_test,r)`，r为连续概率 | fail | p62–64 code | 常见sklearn会报连续/离散目标类型错误 |
| 贷款最优性 | 报告“最佳/最优” | 仅单起点fmincon，无exitflag/KKT/多起点 | not assessable | p14–15,p72,p76 | 只能称一组局部求解输出 |

## 14. Reusable Techniques

### 发票到企业年度特征

**When useful:** 原始数据是大量交易记录、决策对象是企业。

**Why useful:** 先按企业—月份—年份聚合，再构造利润、增长、退货等特征，能把数据工程与模型输入对齐。

**Limitations:** 补齐必须只用决策时可见信息，并记录补齐率、零分母和异常值影响。

### 概率预测接资源配置

**When useful:** 分类风险需要转成额度/价格决策。

**Why useful:** 显式写出预期收益、风险损失、流失和预算，比只按评分排序更可执行。

**Limitations:** 先校准概率并传播不确定性；所有场景必须共享目标和约束才能比较。

### 同目标同划分模型比较

**When useful:** 选择树、Boosting、神经网络等预测器。

**Why useful:** 固定数据、特征、划分、调参预算与指标后，比较才可解释。

**Limitations:** 本文正是反例：训练accuracy、hold-out accuracy和不同数据BP不能直接排序。

### 情景政策映射

**When useful:** 突发事件需要进入贷款上限和定价。

**Why useful:** 把定性行业影响转成可审计的额度/利率参数。

**Limitations:** 映射要有数据依据、范围敏感性，并在改参后重新求解而非后处理。

## 15. Competition Takeaways

1. 预测模型比较必须共享同一数据、特征、折分、调参预算和折外指标。
2. 小样本分类除 accuracy 外至少报告混淆矩阵、AUC/PR-AUC和概率校准。
3. 每个下游概率函数都自动检查 `[0,1]`、单调性和正文—代码系数一致性。
4. 情景改变损失口径时同时给原口径结果和参数敏感性，不能只为“可贷”改假设。
5. 优化报告保存 objective、约束残差、exitflag、初值、多起点和边界命中情况。
6. 政策折扣进入目标后重新求解；解后乘系数不再是原优化问题的最优解。
7. 外部股票数据保存代码、代码列表、时间窗和静态快照，避免正文与脚本不一致。
8. 附录代码在提交前从空环境完整运行一次，清除未定义变量和错误评估对象。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 源文件名写D但正文是2020 C信贷题 | explicit | 1–3 | abstract/problem analysis | paragraph | direct transcription | N/A for positive evidence | acquisition override亦记录该纠正 |
| 主体使用2017–2019发票并按相邻完整年比例补齐 | explicit | 5 | 5.2 | paragraph | direct transcription | N/A for positive evidence | 2016/2020信息少而排除 |
| 违约模型使用七项经营/信誉特征 | explicit | 6–7 | 5.3.1–5.3.2 | paragraph/equation | notation normalization | N/A for positive evidence | 信誉评级重要度最高 |
| 风险模型是XGBoost而非普通“梯度下降决策树” | interpretation | 7–9,59–60 | 5.3.2/code | equation/code | derived interpretation | N/A for positive evidence | 附录直接导入XGBClassifier/xgb |
| XGB附录在全部训练数据上打印accuracy和AUC | criticism | 60 | 10.2.1(3) | code | direct transcription | N/A for positive evidence | `dtrain_predictions=alg.predict(dtrain[predictors])` |
| 96.75%恰等于119/123 | interpretation | 12,60 | 5.5.1/code | paragraph/code | independent calculation | N/A for positive evidence | 与训练集计数吻合 |
| 单树83.87%恰等于26/31 | interpretation | 12,59 | 5.5.1/code | paragraph/code | independent calculation | N/A for positive evidence | 默认25%测试集有31条 |
| 三模型准确率比较的评价集/数据不一致 | criticism | 59–64 | code appendix | code | derived interpretation | N/A for positive evidence | XGB训练集、DT hold-out、BP另读loans.csv |
| BP代码把连续概率r传入accuracy_score | criticism | 63–64 | 10.2.1(5) | code | direct transcription | N/A for positive evidence | 阈值结果tr未用于评估 |
| 信用评级代码调用未定义param且类别数5/4冲突 | criticism | 61–62 | 10.2.1(4) | code | direct transcription | N/A for positive evidence | 代码按页不可运行 |
| 302家评级计数A16/B162/C97/D27闭合 | interpretation | 17 | 6.3.1 | figure 6-2 | independent calculation | N/A for positive evidence | 总和302 |
| 问题一流失率用三次多项式 | explicit | 11 | 5.4.3 | table 5-3 | direct transcription | N/A for positive evidence | Adjusted R² .9972–.9977 |
| 问题二A级流失率代码在4%–15%为负 | criticism | 74 | 10.2.2(6) | code | independent calculation | N/A for positive evidence | 27.74导致q=-.3742至-.5825 |
| C级流失率常数正文/代码相差.01 | criticism | 11,71,74 | 5.4.3/code | table/code | direct transcription | N/A for positive evidence | -.9846 vs -.9746 |
| 问题一违约损失率为0.22 | explicit | 10 | 5.4.2.2 | paragraph/equation | direct transcription | N/A for positive evidence | 文献来源[9] |
| 问题二为扩大可贷范围改成只损失利息 | explicit | 19 | 6.3.3 | paragraph/equation (46) | direct transcription | N/A for positive evidence | 属作者假设，不是估计 |
| 问题二正文预算不等式与代码等式冲突 | criticism | 19,75 | 6.3.3/code | equation (47)/code | direct transcription | N/A for positive evidence | `ceq=sum A-10000` |
| 问题二总信贷1亿元、收益199.635万元 | explicit | 1,28 | abstract/7.6 comparison | paragraph | direct transcription | N/A for positive evidence | 无solver日志 |
| COVID方案收益184.6552万元，较前下降7.50% | explicit | 28 | 7.6 | paragraph | direct transcription | N/A for positive evidence | 独立复算7.5036% |
| 问题三代码在求解后才把利率乘.8/.5 | criticism | 76–77 | 10.2.2(7) | code | direct transcription | N/A for positive evidence | 未按新利率重新fmincon |
| 问题三最终利率出现低于4%的值 | criticism | 27–28,58 | 7.6/appendix table | table | direct transcription | N/A for positive evidence | 2.45%、2.57%等；来自后处理折扣 |
| 正文股票窗口为2020疫情、多行业 | explicit | 22–24 | 7.3.1 | table 7-2/table 7-3/figure 7-4 | direct transcription | N/A for positive evidence | 1–3支代表股/行业 |
| 股票附录代码只抓sh.600000的2017年下半年 | criticism | 58–59 | 10.2.1(1) | code | direct transcription | N/A for positive evidence | 不能生成正文股票表图 |
| 微观层随机抽取72家且不含餐饮业 | explicit | 24–25 | 7.3.2 | paragraph/table 7-5 | direct transcription | N/A for positive evidence | 样本代表性有限 |
| 在已审查范围内，未发现72家抽样种子、重复抽样或抽样不确定性 | criticism | 1–77 | methods/results/appendix code | none found | derived interpretation | 审查主文p1–30、结果附录p31–58和全部代码p58–77 | 不能把一次样本当稳健行业结论 |
| 表7-7百分比实际是营业额上升频率 | criticism | 25 | 7.3.2 | table 7-7 | independent calculation | N/A for positive evidence | 例如软件3升8降为27.27% |
| 在已审查范围内，未发现分类混淆矩阵、折外AUC值或概率校准 | criticism | 1–77 | validation/results/code | none found | derived interpretation | 审查正文所有模型/结果段、附录结果表与Python代码 | accuracy不足以证明风险概率有效 |
| 在已审查范围内，未发现fmincon退出标志、KKT、多起点或全局证据 | criticism | 1–77 | optimization/results/code | none found | derived interpretation | 审查式(29)–(63)、表5-6/6-4/7-9和MATLAB规划代码p70–77 | “最优”应限为单起点局部输出 |
| 附录提供结果长表和代码但关键输入/环境不可用 | criticism | 31–77 | appendices | none found | derived interpretation | 审查结果附录p31–58和代码p58–77；核对仓库可用补充物 | overall not reproducible |
