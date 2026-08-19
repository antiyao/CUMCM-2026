# Paper: 大型百货商场会员画像描述

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_07669cf86cb1
- Year: 2018
- Problem: C
- Award: 组委会官方展示；具体奖项等级未核验
- Provenance tier: O; PDF 来自全国大学生数学建模竞赛组委会官方展示入口，官方展示不证明奖级
- Source file: literature/raw_papers/2018/C101_moe_2018_1699825.pdf
- Source URL: https://dxs.moe.gov.cn/zx/json/2018/1101/1541055987930.pdf
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2018qgdxssxjmjslwzs_2018ctlw/240206/1699825.shtml
- Pages: 15
- SHA-256: 13e1a594e39920925b6b7db103fab8e2585148d38bc1b8163644fc71479c14ea
- Extraction method: embedded text (pypdf 6.10.0) + manual visual review
- Extraction quality: usable text layer；15/15页均超过30个非空白字符，中位数660字符/页，无替换字符；公式、表格、图和代码由原PDF渲染核验
- Page convention: 1-based physical PDF pages
- Visually checked pages: p.1摘要、四类人数和拟合式；p.4–5会员/非会员消费表与D指标；p.6图4-2、聚类人数/中心；p.7生命周期规则；p.8状态转移矩阵；p.9月度状态/激活率/销量表；p.10二次拟合与图4-3/4-4；p.11关联规则定义与122/120示例；p.13马尔科夫及FP-Growth代码；p.14支持度阈值/置信度代码；p.15输出代码
- Unresolved extraction ambiguities: p.1文本层打乱了二次拟合公式，已按p.10原页确认为 `y=-1.0×10^-10 x^2+9×10^-6 x-0.1875, R^2=0.7419`；表4-1/4-4中“单据数量480”与48751名聚类会员的统计粒度无法由缺失附件澄清
- Supplemental artifacts: PDF 内含马尔科夫和FP-Growth主函数代码；附录1–5.1数据、SPSS工程、`活跃状态矩阵.xlsx`、`fpgrowth建模数据.xlsx`、`fp_growth_py3`实现及输出工作簿均为 referenced but unavailable

## 1. Problem Archetype

本文属于零售交易数据工程与会员分析的组合型问题，串联五个原型：

1. SQL/Excel会员与非会员描述统计；
2. K-means会员价值分群；
3. 基于人工阈值的生命周期与活跃状态分类；
4. 二状态转移矩阵和月度激活率—销量回归；
5. FP-Growth购物篮关联规则。

其优势是“数据抽取→分群→状态→促销→商品组合”的业务链完整。主要证据边界是：不同模块使用48751、47210、13671等不同样本但缺少流转图；K-means未报告标准化/初始化稳定性；马尔科夫代码把不同会员序列首尾相连；促销月由高销量反推而非独立活动记录；关联规则未报告lift或样本外检验。

## 2. Problem Decomposition

1. **群体价值**：按单据号用 SQL Server 提取会员/非会员交易，计算数量、金额、平均商品价及日均/单据均值。
2. **购买力分层**：以消费金额、消费次数作二维特征，令 `D=类内平均距离/类间平均距离`，扫描 `K=2...15`并选K=4。
3. **生命周期/状态**：按最近消费间隔和消费次数制定引入、成长、成熟、休眠、流失五阶段，再把成长/成熟会员按月均次数区分活跃。
4. **月度转移与促销关系**：对2015–2016登记的13671人生成2017年12个月二元状态，计算转移矩阵；另以相邻月活跃占比之差定义“激活率”，和销量做相关/二次拟合。
5. **连带销售**：按会员消费编码形成购物篮，用FP-Growth找频繁项集，再计算单后件置信度并提出陈列/降价建议。

## 3. Data Processing

- 按会员/非会员和单据号从附件1/2抽取交易；具体 SQL 未收入PDF。
- 会员与非会员窗口分别为2016-01-01至2017-09-23和2017-01-01至2017-04-18；两组观察期和记录构成不同。
- K-means使用消费金额和消费次数；在已审查范围内，未发现对数变换、缩放、异常值处理或重复初始化说明，审查覆盖p.1–12正文与附录清单，SPSS工程不可得。
- 生命周期队列限定为2015-01-01至2018-01-03登记且能与消费明细关联的会员；聚类总数48751、生命周期总数47210，差1541人的过滤原因未报告。
- 月度状态队列进一步限定为2015–2016登记的13671人；每月有交易为2（活跃），无交易为1（非活跃）。
- 购物篮先按“会员卡号+消费时间+商品编码”去重，再按会员消费编码/消费时间组合交易。PDF代码没有排序语句，依赖外部工作簿已预排序。
- 频繁项集正文阈值为支持度计数50；代码传入 `minimum_support=49`，口径不一致。

## 4. Models Used

### K-means会员分群

**Purpose:** 以购买力将会员分为大众、黄金、铂金、钻石四类。

**Inputs:** 每位会员消费金额和消费次数。

**Outputs:** 四类标签、人数及二维中心点。

**Why selected:** 作者认为消费金额和次数能刻画购买力，并用类内/类间距离比D选择K。

**Important assumptions:** 欧氏距离在两维上可比；K=4的D最小且类别业务可解释。

**Key equations or mathematical structure:** `D=within-cluster mean distance / between-cluster mean distance`，取D较小的K。

**Implementation notes:** SPSS设置、随机初始化、迭代准则、缩放和逐会员标签文件均不可得；金额尺度远大于次数，未标准化时距离可能被金额支配。

### 生命周期规则分类

**Purpose:** 用最近消费间隔和频次给会员分阶段、分活跃状态。

**Inputs:** 注册时间、最后消费时间、累计次数、月均次数。

**Outputs:** 五阶段和活跃/非活跃标签。

**Why selected:** 题目未给阶段定义，作者用业务阈值建立可操作规则。

**Important assumptions:** 30天、90天和月均1次能跨会员稳定区分生命周期。

**Key equations or mathematical structure:** 规则树：0次消费→引入；最近≤30天且1–3次→成长；最近≤30天且≥4次→成熟；31–90天→休眠；>90天→流失。

**Implementation notes:** 未报告阈值敏感性、季节性校正或队列观察长度差异。

### 二状态转移矩阵

**Purpose:** 汇总2017年会员从活跃/非活跃到下一月状态的经验概率。

**Inputs:** 13671×12的1/2状态矩阵。

**Outputs:** `[[92.54%,7.46%],[63.39%,36.61%]]`。

**Why selected:** 作者希望以状态转移刻画非活跃会员激活。

**Important assumptions:** 状态转移齐次；一个月状态只依赖上月状态。

**Key equations or mathematical structure:** 对相邻状态对计数并按起始状态行归一化。

**Implementation notes:** 附录先把所有会员12月序列串成一个长向量再计相邻对，额外计入13670条“上一会员12月→下一会员1月”的伪转移；代码并未使用隐藏状态，正文的HMM“观测独立”假设不适用。

### 激活率—销量相关与二次回归

**Purpose:** 描述月度活跃占比变化与销售量关系。

**Inputs:** 2017年2–12月11个激活率和对应销量。

**Outputs:** Pearson相关约0.83；二次式 `y=-1.0×10^-10 x^2+9×10^-6 x-0.1875`，`R^2=0.7419`。

**Why selected:** 作者观察高销量月与活跃占比变化同向。

**Important assumptions:** 当月销量可代表促销强度；月度点独立；无季节/趋势/反向因果。

**Key equations or mathematical structure:** 激活率=`active_share_t-active_share_(t-1)`，再以销量为x做二次OLS。

**Implementation notes:** 文中称“线性拟合”但实际为一元二次回归；没有促销指示变量、p值、残差或时序控制。

### FP-Growth关联规则

**Purpose:** 发现可用于连带销售的商品组合。

**Inputs:** 去重后购物篮。

**Outputs:** 频繁项集、支持度计数/支持度、单后件规则置信度。

**Why selected:** 作者在模型评价中指出Apriori反复产生候选并扫描数据库，FP-Growth更适合大交易集。

**Important assumptions:** 支持度计数约50和置信度≥0.8具有业务意义；交易编码已正确排序和去重。

**Key equations or mathematical structure:** `confidence(X→Y)=support_count(X∪Y)/support_count(X)`。

**Implementation notes:** 只见主函数，外部 `fp_growth_py3`、输入和完整结果表缺失；未计算lift/leverage，无法排除高基频商品造成的伪“强规则”。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| K-means | selected | 会员购买力分群 | 消费金额和次数可形成相似会员组 | D(K)曲线，K=4最小 | 无层次/混合模型、稳定性、标准化对照 | 原型直观，但K与距离尺度证据不足 |
| 人工生命周期规则 | selected | 阶段/活跃分类 | 题目未定义标准，需自定义 | 阶段/状态人数闭合 | 无阈值学习、业务标签或敏感性 | 可解释基线，不是经验证分类器 |
| 马尔科夫转移 | selected | 月度状态变化 | 下一状态由当前状态描述 | 2×2经验矩阵 | 无非齐次/季节模型、留出预测 | 经验转移表可用；代码跨会员串接有偏 |
| 线性相关 | selected/claimed | 激活率与销量关系 | 相关系数0.83 | 11个月表可复算 | 无时间趋势、促销变量、显著性/CI | 只能表述同期相关，不能归因促销 |
| 二次回归 | selected | 拟合销量—激活率曲线 | not reported | R²=0.7419 | 无线性/常数/时序基线和外推检验 | n=11拟合可复算，证据仅样本内 |
| Apriori | rejected | 购物篮规则 | 候选组合多、数据库扫描/I/O大 | 概念性复杂度说明 | 无同数据运行时间/内存比较 | 选择FP-Growth动机合理 |
| FP-Growth | selected | 频繁项集 | 避免Apriori候选爆炸 | 一个122/120示例 | 无完整规则表、lift、留出期 | 代码透明度有限，促销因果未验证 |

## 5. Model Pipeline

`附件1/2/3 → SQL单据与会员关联 → Excel/SPSS特征表 → K-means分层 → 生命周期规则 → 2017月度状态矩阵 → 转移概率与激活率 → 月销量相关/二次回归 → 购物篮FP-Growth → 陈列与折价建议`。

模块覆盖全面，但队列接口没有闭合：48751名聚类会员、47210名生命周期会员和13671名转移会员之间的过滤表缺失；促销活动也没有作为独立输入，而是从销量高的月份反推。关联规则输出没有进入可量化的促销收益实验。

## 6. Model Improvements

1. 用D比值而非任意指定K，尝试为聚类数提供内部准则。
2. 将静态分群扩展为生命周期和月度状态，增加时间维度。
3. 从状态转移概率再构造月度“激活率”，并拟合销量关系。
4. 以FP-Growth替代Apriori候选生成，面向更大购物篮数据。

这些改进均停留在同样本分析；没有标准化、重采样、留出期或促销A/B实验来验证增益。马尔科夫实现还因跨会员边界计数削弱了时间扩展。

## 7. Parameter Estimation and Optimization

本文没有优化目标；主要参数由作者规则或软件设置决定。K通过D曲线选择，二次回归由11个月样本估计，转移概率由计数行归一化，关联阈值则由作者指定。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| `K` | 会员簇数 | clusters | p.5–6 式(1)/图4-2 | 4 | data-estimated | 最小化类内/类间平均距离比D | partial | 扫描2–15，但无数值表/重启稳定性 |
| amount/frequency | K-means两特征 | 元；次 | p.5–6 表4-6 | centers: (7607,4),(343245,81),(91325,28),(1302838,200) | data-estimated | SPSS K-means | no | 未报告缩放/变换 |
| lifecycle 30/90 | 最近消费间隔阈值 | days | p.7 | 30、90 | author-assumed | 业务规则 | no | 无阈值敏感性 |
| lifecycle count | 成长/成熟次数界 | purchases | p.7 | 1–3；≥4 | author-assumed | 业务规则 | no | 观察窗长度差异未校正 |
| active threshold | 月均消费次数 | times/month | p.7 | 1 | author-assumed | 业务规则 | no | 与“当月有消费即活跃”的问题四定义不同 |
| state encoding | 月度非活跃/活跃 | dimensionless | p.8 | 1 / 2 | author-assumed | 当月无/有消费 | no | 完全可观测，非隐藏状态 |
| transition cohort | 2015–2016登记会员数 | persons | p.8–9 | 13671 | problem-provided | 数据筛选 | no | 12个月每月人数均闭合 |
| activation rate | 活跃占比月差 | percentage points | p.9–10 | -3.30%至2.57% | data-estimated | 相邻月相减 | no | 与非活跃→活跃转移率7.46%同名异义 |
| quadratic coefficients | 销量—激活率二次系数 | mixed | p.10 | -1.0e-10, 9e-6, -0.1875 | data-estimated | 11点OLS | no | n=11、3参数、残差df=8 |
| support count | 频繁项集阈值 | baskets | p.1、p.11、p.14代码 | prose 50；code 49 | algorithm hyperparameter | 固定 | no | 代码/正文不一致 |
| confidence threshold | 推荐规则阈值 | dimensionless | p.1、p.11 | 0.8 | author-assumed | 固定 | no | 未结合lift和基频 |

## 8. Validation

论文提供内部计数、D曲线、月度拟合和单个关联规则示例；没有独立验证集、外部门店或实际促销实验。L1/L2证据可复算，但不支持因果或部署效果。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| K-means分群 | L1 internal clustering criterion | same sample | D ratio | one scan K=2...15 | K=4曲线最小 | K≥5大多接近0且K=10突增 | 无标准化、重启、轮廓或外部标签 | 仅支持作者D定义下的K=4 |
| 生命周期分类 | L2 count reconciliation | same sample | 类别人数和 | 1 table | 21298+1391+2230+3367+18924=47210 | 无标签正确率 | 人工规则定义即结果 | 只支持计数闭合 |
| 活跃分类 | L2 count reconciliation | same sample | 活跃/非活跃和 | 1 table | 45039+2171=47210 | 无行为结果对照 | 与问题四活跃定义不同 | 只支持表内闭合 |
| 月度状态 | L2 internal consistency | same sample | 每月总人数/占比 | 12 months | 每月均13671；占比复算一致 | 转移代码跨会员边界 | 无留出年 | 支持月度计数，不认证转移矩阵无偏 |
| 激活率—销量 | L1 in-sample fit | same sample | Pearson r；quadratic R² | 11 months | r=0.8340；R²≈0.7421复算 | 8月促销标签下激活率-0.15% | n小、时序/季节/促销混杂 | 仅支持2017同期相关 |
| 关联规则示例 | L2 arithmetic check | same sample | confidence | 1 rule | 120/122=98.36%≈98.4% | 无lift/基线概率 | 完整规则表不可得 | 支持该示例算术，不支持促销效果 |
| 促销干预效果 | not reported | external | 增量销售/利润 | not reported | not reported | 无A/B或前后对照 | 促销月由销量反推 | 不构成L5验证 |

## 9. Sensitivity and Robustness

在已审查范围内，未发现对K-means初始化/缩放、生命周期阈值、马尔科夫队列边界、回归月份删除、支持度或置信度阈值的实际扰动实验；审查覆盖p.1–12正文、p.13–15全部代码和可见附录清单，外部SPSS/Excel与完整规则表不可得。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|

## 10. Visualization Strategy

- E-R图先展示会员画像的数据实体关系，但正文没有字段字典或主外键审计。
- 表4-1至4-4集中比较会员/非会员极值、均值、中位数和归一化金额；统计粒度与观察窗差异应另加说明。
- 图4-2用K—D曲线选簇数，缺数值标签和误差条；K=10突增值得诊断。
- 表4-5/4-6把簇规模和中心并列，业务解释直观；应加比例和标准化中心。
- 表4-9至4-11给出转移矩阵、月状态和销量，使相关/回归可独立复算。
- 图4-3/4-4同时展示时间曲线和散点拟合；连接散点的折线会误导顺序关系，且没有残差图/置信带。

## 11. Writing Structure

五问按数据工程、分群、生命周期、状态促销、购物篮逐步推进，摘要为每问给出方法和结果，附录保留关键代码，竞赛叙事完整。

主要问题是术语和因果边界：7.46%的非活跃→活跃转移概率和月活跃占比差都称“激活率”；“线性拟合”实际是二次式；高销量月份被标成促销月后又用销量证明促销相关，存在循环定义；关联规则被写成可促进销量但没有实验。应明确描述统计、预测和因果干预的区别。

## 12. Strengths

1. 将数据库抽取、统计、聚类、状态模型和关联规则连接成完整业务分析管线。
2. K值、生命周期阈值、转移概率和关联阈值均显式给出，便于审计。
3. 月度状态/销量表充分，相关和二次回归可由公开表格复算。
4. 聚类、生命周期、活跃人数均提供明确计数，多个总数能闭合。
5. 附录公开代码，揭示了交易构篮和转移矩阵的实际实现。

## 13. Weaknesses

1. 会员/非会员观察窗和统计粒度不同，会员“480单据”与48751名聚类会员关系不明，强价值结论缺可比抽样设计。
2. K-means未标准化金额/次数，也无重复初始化、稳定性或外部标签验证。
3. 马尔科夫代码跨会员边界计入13670条伪转移；报告矩阵存在可观测实现偏差。
4. 促销月从高销量反推，相关/二次拟合只有11点且无时序控制，不能支持促销因果。
5. FP-Growth阈值正文50、代码49，且无lift、完整规则表或实际促销检验。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | p.4–11有汇总表；附录1–5.1仅列名 | 原始附件、逐会员标签和购物篮不可得 |
| Code availability | partial | p.13–15有转移/FP主函数 | SQL、K-means、生命周期、回归代码和FP库缺失 |
| Dependency / environment information | partial | SQL Server、Excel、SPSS、MATLAB、Python/pandas被命名 | 版本、SPSS设置和`fp_growth_py3`来源未报 |
| Random seed | not reported | K-means模块与附录已审查 | 聚类初始化不可精确复现 |
| Hard-coded constants | extensive | 30/90天、1次/月、49/50支持度、0.8置信度及Windows绝对路径 | 参数未做敏感性，路径不可移植 |
| Formula-to-code consistency | contradicted | 对照p.8转移定义、p.11支持度与p.13–14代码 | 跨会员伪转移；支持阈值49/50冲突 |
| Code-to-result consistency | partial/contradicted | r/R²可由p.9表复算；转移矩阵依赖缺失XLSX | 回归结果闭合，转移结果受串接偏差且原计数不可得 |
| Overall reproducibility | partially reproducible | 15页正文、全部表图/代码与仓库补充物已审查 | 月度拟合/计数可复算；核心聚类、转移、规则不可完整重跑 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 聚类人数 | 四类共48751 | 45678+348+2708+17=48751 | pass | p.6 表4-5 | 大众会员占93.70%，类别极不均衡 |
| 生命周期人数 | 五阶段共47210 | 21298+1391+2230+3367+18924=47210 | pass | p.7 表4-7 | 与聚类样本差1541，过滤原因未报 |
| 活跃人数 | 45039+2171=47210 | 复算一致 | pass | p.8 表4-8 | 活跃占4.60% |
| 每月队列闭合 | 各月总数13671 | 12个月非活跃+活跃均=13671 | pass | p.9 表4-10 | 固定队列 |
| 转移矩阵行和 | 每行概率应为100% | 92.54+7.46=100；63.39+36.61=100 | pass | p.8 表4-9 | 行和闭合不排除计数偏差 |
| 马尔科夫相邻对数量 | 13671人×12月应有13671×11条组内转移 | 正确150381；串平后计164051，额外13670（占代码计数8.33%） | fail | p.13 code | 每位会员Dec→下一会员Jan被误计 |
| 会员单据均额 | 1258934872/480=2622781 | 复算2622780.98 | pass | p.4–5 表4-1/4-4 | 统计粒度仍不明 |
| 非会员单据均额 | 4440518/2506=1772 | 复算1771.95 | pass | p.4–5 表4-2/4-4 | 四舍五入一致 |
| 日均金额 | 会员1995142、非会员41892 | 分别复算1995142.43、41891.68 | pass | p.5 表4-4 | 时间窗不同但各自算术闭合 |
| 激活率—销量相关 | r=0.83 | 用p.9二至十二月11点复算r=0.834049 | pass | p.9–10 table/paragraph | 同期相关，不是促销因果 |
| 二次拟合 | 系数约-1e-10、9e-6、-0.1875，R²=0.7419 | 复算-1.00747e-10、9.05162e-6、-0.187552，R²=0.742087 | pass | p.10 equation/figure | 舍入一致，残差df=8 |
| 8月促销叙述 | 促销月激活率较高 | 2017-8激活率为-0.15% | fail | p.9–10 表4-11/段落 | 与“一有促销激活率就高”矛盾 |
| 关联规则示例 | 120/122=98.4% | 复算98.3607% | pass | p.11 paragraph | 未给Y的基频/lift |
| 最小支持度 | 正文支持度计数≥50 | 代码`minimum_support=49` | fail | p.11 vs p.14 code | 边界项集集合可能不同 |

## 14. Reusable Techniques

### 数据工程到分析的队列台账

**When useful:** 多附件、多模块使用不同会员子样本时。

**Why useful:** 记录每步输入人数、过滤规则、时间窗和主键，可解释48751→47210→13671的变化。

**Limitations:** 只有总数闭合不够，还需唯一键、重复率和流失原因。

### 可解释生命周期规则

**When useful:** 缺少标签且业务需快速部署基线时。

**Why useful:** 30/90天和频次阈值易说明、易转SQL。

**Limitations:** 必须按队列年龄/季节校正并做阈值敏感性；规则标签不能当预测真值。

### 按会员分组的转移计数

**When useful:** 多实体的面板状态序列。

**Why useful:** 对每位会员内部相邻月计数再汇总，可避免跨实体伪转移。

**Limitations:** 不能直接flatten所有实体；还要处理缺月、队列进入/退出和时间非齐次性。

### 购物篮规则的业务审计

**When useful:** 设计陈列、组合券或交叉销售候选。

**Why useful:** 支持度、置信度、lift和增量实验能把频繁共购与业务价值分开。

**Limitations:** 高置信度可能只是后件高基频；最终建议需留出期或A/B测试。

## 15. Competition Takeaways

1. 多模块先画队列流转表，明确每一步人数、时间窗和过滤原因。
2. K-means前标准化/对数化金额与次数，并做多次初始化、轮廓系数和簇稳定性。
3. 面板转移必须按会员分组计数，禁止把所有序列直接串接。
4. “激活率”只保留一个定义；转移概率和活跃占比月差应分名。
5. 促销影响要有独立促销变量、时序/季节控制和留出期，相关不能改写为因果。
6. 二次拟合报告样本量、参数数、残差、置信区间和外推范围。
7. 关联规则同时报告support、confidence、lift和后件基频，并固定代码/正文阈值。
8. 随报告提供排序后的购物篮、SPSS设置、随机种子和可运行依赖。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 论文以SQL/Excel、K-means、生命周期规则、马尔科夫和FP-Growth串联五问 | explicit | 1–3 | 摘要；问题分析 | paragraphs | direct transcription | N/A for positive evidence | 方法链由摘要和各问对应 |
| K=4由D比值最小选择 | explicit | 5–6 | 4.2 | equation (1), figure 4-2 | direct transcription | N/A for positive evidence | 图和表视觉核验 |
| 四簇人数合计48751 | interpretation | 6 | 4.2 | table 4-5 | independent calculation | N/A for positive evidence | 45678+348+2708+17 |
| 金额和次数未报告标准化或重启稳定性 | criticism | 1–12 | K-means相关正文 | none found | derived interpretation | p.1摘要、p.2问题分析、p.5–6聚类、p.12评价已审查 | SPSS工程不可得 |
| 生命周期用30/90天和1–3/≥4次人工划分 | explicit | 7 | 4.3 | paragraph | direct transcription | N/A for positive evidence | 作者规则而非估计参数 |
| 五阶段人数与活跃人数分别闭合到47210 | interpretation | 7–8 | 4.3 | tables 4-7, 4-8 | independent calculation | N/A for positive evidence | 两表同队列 |
| 2017月度队列为13671人 | explicit | 8–9 | 4.4 | table 4-10 | direct transcription | N/A for positive evidence | 每月计数复算闭合 |
| 转移矩阵报告非活跃→活跃7.46% | explicit | 8 | 4.4 | table 4-9 | direct transcription | N/A for positive evidence | 与月差“激活率”不同 |
| 转移代码额外计13670条跨会员伪转移 | criticism | 13 | 附录4.2 | code | independent calculation | p.13完整MATLAB代码及p.8队列维数已审查 | 150381正确组内转移 vs 164051串平相邻对 |
| HMM观测独立假设不适用于完全观测二状态计数 | criticism | 3, 8, 13 | 模型假设；4.4；附录 | paragraphs, code | derived interpretation | p.3假设、p.8状态定义和p.13实现已审查 | 没有隐藏状态/发射模型 |
| 月激活率是相邻月活跃占比之差 | explicit | 9–10 | 4.4 | table 4-11, paragraph | direct transcription | N/A for positive evidence | 一月无前月差值 |
| r=0.834049和二次R²≈0.742087可由表复算 | interpretation | 9–10 | 4.4 | table 4-11, equation | independent calculation | N/A for positive evidence | 与作者0.83/0.7419一致 |
| 8月被列为促销月但激活率为-0.15% | criticism | 9–10 | 4.4 | table, paragraph | independent calculation | p.9完整月表与p.10解释已审查 | 反驳“一有促销激活率就高” |
| 促销月由销量高值反推，未发现独立活动记录 | criticism | 9–10 | 4.4 | none found | derived interpretation | p.9–10月表、图、模型解释已审查 | 附件中无可用促销日历 |
| 关联示例120/122=98.36% | interpretation | 11 | 4.5 | paragraph | independent calculation | N/A for positive evidence | 舍入为98.4% |
| 正文支持计数50而代码设置49 | criticism | 11, 14 | 4.5；附录5.2 | paragraph, code | direct transcription | p.11算法说明与p.14参数调用已审查 | 边界不一致 |
| 在已审查范围内，未发现lift、留出期或促销实验 | criticism | 1–15 | 全文/附录 | none found | derived interpretation | p.1–12正文和p.13–15全部代码已审查 | 外部规则结果表不可得 |
| 论文仅部分可复现 | criticism | 1–15 | 全文/附录 | none found | derived interpretation | 15页、所有图表/代码和现有补充物已审查 | 月度拟合可复算，核心数据/依赖缺失 |
