# Paper: 基于历史数据的蔬菜类商品定价与补货决策模型

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_55b6a27f3b5a
- Year: 2023
- Problem: C
- Award: 本地合集声称“优秀论文”，未获独立奖项核验，不作为奖级证据
- Provenance tier: L（Yao 提供的本地历史论文合集；文件名/目录标签不证明奖项）
- Source file: literature/raw_papers/2023/C235.pdf
- Source URL: unknown
- Verification source: unknown
- Pages: 73
- SHA-256: 84724f950dfe248bddef91071909dead68dd3717f17f580e8b9ea2e5e842a25b
- Extraction method: embedded text（pypdf 6.10.0）+ 全页 Poppler 渲染视觉复核；未使用 OCR
- Extraction quality: usable text layer，73/73 页均有足量文字、0 page error；公式版面、图表、代码缩进和支撑材料截图另以原页确认
- Page convention: 1-based physical PDF pages
- Visually checked pages: 全部物理页 1–73；重点放大核对 p4–18、24–35 的公式/表 1–11/图，p37–73 的 R/Python/Geatpy 代码及 p73 支撑材料列表
- Unresolved extraction ambiguities: 数学公式的变量名在文本层有部分缺失，均由页图恢复；附录代码存在换行/排版影响，但本文所列维度、索引、常数和函数调用均可在页图直接确认；未逐项重录 251 个单品的全部中间数据
- Supplemental artifacts: p73 截图列出 R/Python脚本、Excel 中间表和多个 notebook，但 PDF 无嵌入附件，仓库也未取得这些文件；当前仅有正文中的代码页，所列外部支撑材料均为 referenced but unavailable

## 1. Problem Archetype

论文是“零售时间序列分析 → 价格—需求建模 → 预测驱动定价补货 → 单品组合优化”的流水线：

- 描述/统计：K-S 检验、Pearson 相关、季节 ARIMA、周/月/年比例、聚类。
- 品类预测：带销售价格外生变量的 Prophet，拟合趋势、季节、节假日和价格项。
- 品类决策：以价格为变量，用预测需求和批发价构造利润目标，声称以模拟退火逐日求 7 天方案。
- 单品决策：把价格—销量线性关系接入带二进制选品和品类需求约束的二次优化，声称用遗传算法求解。
- 扩展建议：库存、跨日损耗、体积、保存时长、运输、封控、客流、时令、退货原因和产地。

该原型具有比赛迁移价值，但时间验证、因果价格效应、代码可执行性和约束一致性不足，结果只能视为样本内/启发式输出。

## 2. Problem Decomposition

1. 把交易流水按单品/品类和日、周、月、年聚合；用 IQR 规则替换异常销量，并用 0 补没有销售记录的日期。
2. 比较六品类分布、相关和 ARIMA 结构；筛出销量占比超过 1% 的 31 个单品并聚类。
3. 构造销量加权的品类售价/批发价指数和品类平均损耗率，拟合带价格外生项的 Prophet。
4. 从 Prophet 分解中提取价格—需求关联，以模拟退火搜索 2023-07-01 至 07-07 的品类价格和补货量。
5. 从近期可售记录筛单品，估计需求、批发价和线性价格关系，建立 27–33 个单品、最少 2.5 kg 和品类需求带约束的混合整数二次模型。
6. 提出多日库存动态规划需要补采的数据，但未实现该扩展。

论文的任务顺序合理；真正薄弱处集中在模型接口：去趋势代码没有去掉趋势、未来需求函数不能按附录执行、单品优化代码与正文变量/约束不一致。

## 3. Data Processing

问题一对每个单品按日汇总，以 `[Q1-1.5IQR,Q3+1.5IQR]` 标记异常，再用去异常后的全期均值替换。相关分析删除总销量后 25%（代码实际删除单品销量占比 `<=1%` 的单品），无销售记录日期补 0。上述规则会把真实节假日、断供或促销峰值平滑掉，也把“无记录”直接解释为零需求；阈值未做敏感性。

附录日相关代码没有按日期 join 六品类，而是直接取不同长度向量并对花菜补 1 个零、茄类补 35 个零后按行拼接，相关系数缺少日期对齐。月度代码同样依赖行顺序。论文称用 CURE 聚类，代码实际调用 `cluster::pam` 对相关矩阵做 k-medoids，方法不是 CURE。

问题二使用销量加权价格指数，但品类损耗率仅对单品做简单平均。问题三排除所有折扣销售和“利润后 10%”记录；R 代码只为第 2 个单品计算一次 10% 分位阈值，之后所有单品复用该绝对阈值，且第 1 个单品没有加入筛选结果。由此得到的“需求”既不是全体观察需求，也没有正确执行逐单品 10% 规则。

## 4. Models Used

### K-S、Pearson 与季节 ARIMA

**Purpose:** 描述品类销量分布、相关和时间结构。

**Inputs:** 日/月/周聚合销量。

**Outputs:** 15组K-S p值、相关矩阵、ARIMA结构/AIC。

**Why selected:** 作者希望从分布、关联和时间序列三个角度建立描述基线。

**Important assumptions:** 样本独立或检验近似有效；缺失补零正确；相关序列日期对齐；周序列连续。

**Key equations or mathematical structure:** 两样本 K-S、Pearson、`ARIMA(0,0,1)(0,1,1)[52]`。

**Implementation notes:** 日相关手工补零而非日期对齐；周 ARIMA 按存在记录的周生成 `ts(frequency=52)`，缺周时会压缩时间轴。

### Prophet + 价格外生回归

**Purpose:** 分离趋势/周度/年度/节假日，并表示销售价格对销量的关联。

**Inputs:** 品类日销量、销量加权售价、节假日。

**Outputs:** 样本内 `yhat`、成分、价格偏效应、未来批发价/需求。

**Why selected:** 作者认为 Prophet 比神经网络可解释、比 ARIMA 更适合非平稳/缺失数据。

**Important assumptions:** 同期价格可作为外生变量；加性分解充分；预测期结构稳定；价格影响局部线性。

**Key equations or mathematical structure:** `D_i(t)=g_i(t)+s_i(t)+h_i(t)+f(P_i(t))+ε`，价格项在局部线性。

**Implementation notes:** 代码的 `y_adjusted=yhat-yearly-weekly-holidays` 没有减去 trend，与式 (12) 不一致；未做滚动或时间留出验证。

### 品类利润与模拟退火

**Purpose:** 决定 7 天的品类价格与补货量。

**Inputs:** Prophet需求、预测批发价、平均折扣率/损耗率。

**Outputs:** 表 5–8 的价格、补货和加成率。

**Why selected:** Prophet 反复求值使解析优化困难，且作者只希望上一日价格附近的局部解。

**Important assumptions:** 所有进货当天售完；价格—需求关系仅在小邻域有效；逐日把预测值写回历史不会积累偏差。

**Key equations or mathematical structure:** 式 (13) 利润，式 (14) `Q_i=D_i`。

**Implementation notes:** 附录没有模拟退火循环；`mkt_demand` 添加布尔型 regressor、复用已拟合 Prophet，并在首个品类内 return，不能生成六品类逐日需求。

### 单品二次优化与启发式求解

**Purpose:** 在 61 个候选中选 27–33 个并给出数量、价格。

**Inputs:** 损耗率、批发价、线性价格—销量参数、品类需求。

**Outputs:** 表 9 的 33 个单品和 743 元利润。

**Why selected:** 混合整数二次结构变量多，作者选择启发式搜索。

**Important assumptions:** 当日售罄；折扣/低利润记录不是需求；各品类进货在需求的 60%–100%；线性价格关系可外推。

**Key equations or mathematical structure:** `z_i=(y_i-β_i0)/β_i1`，二进制选品、数量边界和分组需求约束。

**Implementation notes:** 代码写 `Dim=122`，变量类型/上下界却各有128项；`u/v`索引错误、`v`从未赋值，上界写成 `8*d`；算法模板是差分进化 `DE/best/1/L`，不是正文所称遗传算法。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| Prophet + price regressor | selected | 品类需求分解/预测 | 可解释、容忍非平稳和缺失、可纳入价格 | 表3样本内R²/MAE/RMSE与成分图 | 与LSTM/BP/ARIMA同一数据滚动比较；预测期误差 | R²仅.45–.55，不能称“预测较准确” |
| LSTM/BP | rejected conceptually | 需求预测候选 | 易过拟合、解释性弱 | not reported | 同预算实证基线 | 只有一般性理由，没有本数据比较 |
| ARIMA | considered then judged weak | 周销量基线 | ACF/PACF与三年周期少，单变量不足 | 一个模型AIC=1322.4及图 | 其他参数/naive/Prophet折外误差 | 能说明该ARIMA拟合受限，不能证明Prophet更强 |
| 模拟退火 | selected | 品类局部定价 | 只需上一日附近局部解、计算预算有限 | 结果表 | 代码、重复运行、基线、收敛与运行时 | 可作为搜索框架，当前结果不可复现 |
| CURE | selected in prose | 单品关系聚类 | 抗噪/离群 | 热力图三簇 | CURE参数/代码/稳定性 | 附录实际是PAM，论文方法名不成立 |
| 遗传算法 | selected in prose | 单品混合优化 | 变量/约束多 | 迭代图、743元方案 | 重复运行、可行率、MILP/MIQP基线 | 代码实际DE且结构错误，不能支持算法结论 |

## 5. Model Pipeline

品类链为：

`交易流水 → IQR替换/聚合 → 品类价格指数与销量 → Prophet分解 → 局部价格—销量线性化 → 批发价预测 → 模拟退火价格 → 预测需求=补货量`。

单品链为：

`近期可售筛选 → 6/7月需求估计 → 批发价与价格—销量系数 → 二进制选品/数量/需求约束 → 启发式搜索`。

接口问题包括：价格项仍混有 trend；模拟退火和多品类需求函数不可执行；正文说 61 个候选而优化代码用 58；需求筛选阈值跨单品误复用；正式需求上界未进入可用代码。

## 6. Model Improvements

- 从单一 ARIMA 转向可分解且带价格项的 Prophet，方向上更贴合“解释价格与需求”；但没有折外比较，改进只停留在结构层面。
- 用价格邻域 0.1 元内的中位数平滑噪声，使相关系数增大；重叠邻域产生高度相关的伪样本，不能视为独立证据或因果价格效应。
- 把品类预测下钻到单品二进制组合，加入陈列量和品类需求约束；两个独立的“至少5/6成立”变量允许不同品类分别违反上下界，未保证至少五个品类同时处于60%–100%。
- 问题四提出库存动态模型所需数据，但只是 proposed、未实现或验证。

## 7. Parameter Estimation and Optimization

Prophet 的周/年季节和中国节假日由库默认/作者开关配置，外生价格系数由样本内拟合。价格—需求偏效应在 0.1 元邻域取中位数后线性回归，未给标准误或时间划分。模拟退火的温度、步长、迭代数、接受率和随机种子没有在正文或代码中形成可执行记录。

单品模型声称最大进化 2000、突变概率 0.5、交叉概率 0.7；代码实际使用 DE 的缩放因子 `F=.5` 和交叉率 `.7`，种群 200。需求下限为 60%、上限100%，但打印代码用 `8*d` 且 `v=0`，实际上上界被关闭。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| IQR multiplier | 异常销量边界 | dimensionless | p4, p37 | 1.5 | algorithm hyperparameter | boxplot rule | no | 异常以全期均值替换 |
| low-volume filter | 单品相关筛选 | sales share | p4/p40 | 删除占比<=1%（叙述另称后25%） | author-assumed | hard threshold | no | 两种口径不一致 |
| missing-day value | 无销售记录日销量 | kg | p4,p7 | 0 | author-assumed | fixed fill | no | 缺货/未上架与零需求混同 |
| ARIMA seasonal period | 周销量年周期 | week | p9 | 52 | author-assumed | `auto.arima(seasonal=TRUE)` | no | 缺周未显式补齐 |
| Prophet seasonalities | 周度/年度 | day | p17–18,p46 | weekly/yearly on；daily off | algorithm hyperparameter | library configuration | no | Fourier阶数/prior scale not reported |
| price neighborhood | 中位数平滑窗口 | yuan/kg | p22–23 | ±0.1 | algorithm hyperparameter | overlapping local median | no | 会提高相关但无独立样本 |
| category loss rates | 品类平均损耗 | proportion | p17 table2 | 6.75%–11.16% | data-estimated | 单品损耗简单平均 | no | 未按销售量/采购量加权 |
| Prophet performance | 样本内拟合 | mixed | p18–19 table3 | R² .45–.55 | data-estimated | same-sample fit | no | 无时间留出 |
| SA neighborhood | 定价搜索邻域 | yuan/kg | p25 | small, exact range not reported | algorithm hyperparameter | author setting | no | 温度/迭代/seed not reported |
| candidate count | 单品候选 | count | p27/code p49 | 正文61；代码58 | data-estimated | 近期可售筛选/`df1.xlsx` | no | 输入不一致 |
| item count | 最终可售单品数 | count | p28 | 27–33 | problem-provided | binary count constraint | no | 结果33 |
| display minimum | 最小订购量 | kg/item | p28 | 2.5 | problem-provided | lower bound when selected | no | 表9最小2.5通过 |
| item maximum | 单品最大量 | kg/item | p28 | 50 | author-assumed | twice claimed max demand | no | 未检验50的合理性 |
| demand band | 品类满足区间 | proportion | p28 | 0.6–1.0 | author-assumed | at least5 lower + at least5 upper | no | 可由不同品类失败 |
| demand censoring | 删除低利润记录 | within-item quantile | p27/p54 | bottom10% | author-assumed | quantile filter | no | 代码阈值只算一次并跨单品复用 |
| wholesale window | 单品批发价 | yuan/kg | p27/p55 | 正文三年6–7月均值；代码2023-06-24至30均值 | data-estimated | conflicting windows | no | 直接影响利润/定价 |
| DE population/generations | 启发式规模 | count | p51 | 200 / 2000 | algorithm hyperparameter | fixed | no | 无seed/重复运行 |
| DE `F`, `XOVR` | 缩放因子/交叉率 | dimensionless | p51 | 0.5 / 0.7 | algorithm hyperparameter | fixed | no | 正文把F称突变概率 |

## 8. Validation

论文的验证主要是样本内拟合和结果算术/约束检查。Prophet 表 3 的 R² 为 .45–.55，MAE/RMSE 没有相对基准；代码虽导入 `cross_validation` 与 `performance_metrics`，未调用。7 天预测也没有 rolling-origin、留出最后窗口或朴素季节基线。

问题三提供迭代图、表 9 和品类满足度表 10。33 个商品、最小2.5kg、利润和基本算术可复算；但 308% 超过原上界、59%低于下界。打印代码维度/索引错误，不能把表10视为代码可行性验证。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 品类Prophet拟合 | L1 — in-sample fit | same sample | R²/MAE/RMSE | 1 per category | R² .45–.55 | 茄类/多品类拟合弱 | 无hold-out、无naive基线、量纲不同不宜横比MAE | 只支持中等样本内拟合 |
| 价格—需求线性项 | L1 — smoothed same-sample correlation | same sample | correlation/slope | 1 | r=-.565至-.966 | overlapping median windows | 内生价格、趋势未完全去除、无置信区间 | 只能称负相关，不是需求因果效应 |
| ARIMA结构 | L2 — diagnostic/AIC | same sample | AIC/ACF/PACF | 1 example | AIC1322.4，作者判拟合不好 | 无对比模型 | 支持该特定ARIMA受限 |
| 7天品类方案 | not assessable | unknown | forecast error/profit | not reported | 表仅给6天 | 第7天缺失；SA代码不可见 | 无真实销售回测 | 不能验证预测/利润 |
| 单品解算术 | L2 — result closure | same output | item count/profit/quantity | 1 | 33项，利润和743.3元 | 含3项负利润 | 只能检查表内闭合 | 支持表9内部算术 |
| 单品需求约束 | L2 — post-solution check | same output | category fill rate | 1 | 58.6%–307.5% | 两类越出60%–100% | 放松逻辑与代码均不保证原约束 | 不支持“较好满足需求” |
| 启发式稳定性 | not reported | unknown | repetitions/variance/gap | not reported | not reported | no repeated runs | 无seed、可行率、最优界 | 不能声称全局最优或稳定 |

## 9. Sensitivity and Robustness

在已审查范围内，未发现对异常阈值、1%筛选、价格窗口、Prophet超参数、需求带、50kg上界、候选窗口或启发式随机种子的实际扰动实验。图28是一次优化轨迹，不是敏感性或重复稳定性证据。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|

上述 scoped negative finding 覆盖正文 p1–36、全部代码 p37–73、附录图表和支撑材料列表；不可用的 notebook/Excel 无法评估。

## 10. Visualization Strategy

论文使用箱线图、预处理前后序列、相关矩阵/热力图、ACF/PACF、周/月/年比例图、Prophet 拟合/成分图、价格—需求散点及局部中位数线、模拟退火/启发式迭代图和结果表。

图形覆盖探索、模型和决策输出，结构完整。问题在于图21“拟合良好”的视觉叙述与 R² .45–.55 不匹配；图23/24的中位数平滑显著变直，却没有展示有效样本数或折外误差；迭代图没有可行性率、重复带和最优差距。

## 11. Writing Structure

正文前 36 页保持四问递进，后 37 页附代码和支撑材料列表。模型符号、目标和约束集中呈现，表5–10便于复核。

写作边界不足：相关被解释为替代/互补、年度低谷被直接归因疫情、样本内拟合被写成准确预测、启发式结果被写成“最大化利润”。表5–8标题为7月1–7日却只列1–6日，也没有解释缺行。

## 12. Strengths

- 从流水到单品/品类多尺度分析，数据管线覆盖面广。
- Prophet 成分与价格项形成“可解释预测→决策”接口，比赛叙事清楚。
- 主动承认 ARIMA、茄类价格拟合和部分品类关系不稳定，没有把所有模型都写成优秀。
- 单品方案给出完整名称、品类、数量、价格和利润，允许独立算术复核。
- p73 记录了作者侧支撑文件名/大小，便于识别哪些材料当前不可用。

## 13. Weaknesses

统计上缺少时间独立验证，价格效应存在同期内生性，相关关系不能推出替代/互补。异常均值替换、补零和低利润删样本都可能把真实供需结构改写。

实现上，Prophet需求函数、模拟退火和单品优化打印代码不能生成所述结果：未定义评价函数、错误 regressor、首品类 return、维度128/122冲突、u/v索引错误、DE/GA不一致、上界关闭。引用但不可得的 notebook 可能包含另一版本，因此当前结论是“在可用版本中不可复现”，不是断言作者从未实现。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable | 引用附件1–4及多个中间xlsx | 无法重跑清洗/拟合/优化 |
| Code availability | partial | p37–73页图文本可提取；p73列出外部脚本/notebook | 打印代码多处不可运行；外部版本not assessable |
| Dependency / environment information | unavailable | R/Python包名可见，无版本/环境 | Prophet/pandas/geatpy API依赖版本 |
| Random seed | partial | PAM seed=123 | Prophet/SA/DE无统一seed；无重复运行 |
| Hard-coded constants | extensive | 类别编码、手补零1/35、k=3、窗口、阈值、58项分段均硬编码 | 数据变化易破坏索引与维度 |
| Formula-to-code consistency | contradicted | 对照式(12)–(14)、p27–29与p47–51 | trend未去；SA缺失；61/58、需求上界1/8、GA/DE冲突 |
| Code-to-result consistency | not assessable / contradicted | 对照表5–10与p44–59代码 | code path不能完成六品类预测/可行优化；外部notebook不可用 |
| Overall reproducibility | not reproducible | 审查全部73页及PDF attachment状态 | 缺数据/环境/支撑文件，关键代码存在结构错误 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 7天表行数 | 表5–8称2023.7.1–7.7 | 四表均只列7.1–7.6，共6天 | fail | p25–26 tables5–8 | 第7天无解释 |
| 加成率 | 7.1水生根茎54.8%，花菜31.3% | 14.56/9.40-1=54.89%；11.58/8.82-1=31.29% | pass | p25–26 tables5,7,8 | 舍入闭合 |
| 单品数 | 可售27–33 | 表9共33项 | pass | p31 table9 | 命中上界 |
| 最小订购量 | 每项>=2.5kg | 表9最小2.5kg | pass | p31 table9 | 表内通过 |
| 单品利润合计 | 最大利润743元 | 33行利润合计743.3元 | pass | p30–31 table9 | 舍入闭合 |
| 需求满足率 | 表10六类59%–308% | 独立复算58.59%–307.53% | pass | p31–32 table10 | 表内算术闭合 |
| 原需求带 | 每品类60%–100% | 花叶58.6%<60%；水生307.5%>100% | fail | p28 constraints/p32 table10 | 两类违反原约束 |
| 放松逻辑 | 上下界各至少5/6成立 | 独立u/v允许不同品类分别失败 | concern | p28 equations | 不能保证同5类同时落入区间 |
| 损耗利润公式 | `w=sum(1-a)(z-c)y` | 采购成本应对完整y计，常见式为`z(1-a)y-cy` | concern | p27 objective | 当前少计`a*c*y`成本 |
| Prophet去因素 | 式12减trend/season/holiday | 代码只减yearly/weekly/holidays，保留trend | fail | p18 eq12/p47 code | 价格偏效应混入趋势 |
| Prophet代码评价 | 调用`evaluate_prophet_performance` | 全附录无定义 | fail | p46 code | 首次循环会NameError |
| 未来需求函数 | 应返回六品类需求 | 布尔regressor、重复fit同一model且首循环return | fail | p48–49 code | 不能支撑模拟退火 |
| CURE实现 | 正文称CURE | 代码调用`pam(...,k=3)` | fail | p15–16/p41 code | 实际为k-medoids |
| 单品候选数 | 正文61种 | Geatpy代码固定58 | fail | p27/p49–50 | 输入维度不一致 |
| 决策向量维度 | `Dim=58*2+6=122` | varTypes/lb/ub为58+58+6+6=128 | fail | p49–50 code | Problem初始化不一致 |
| u/v赋值 | 两组各6二进制 | 两个循环都写u，v保持0；索引又落在y区 | fail | p50 code | 上下需求约束失真 |
| 需求上界代码 | 正文1.0*d | 代码写8*d且乘v=0 | fail | p28/p50 code | 实际关闭上界 |
| 低利润10%筛选 | 每单品独立删后10% | mymin只在i=2计算，后续复用；首单品遗漏 | fail | p54/p58 code | 需求估计不符合正文 |
| 批发价窗口 | 正文三年6–7月均值 | R代码取2023-06-24至06-30均值 | fail | p27/p55,p59 code | 结果来源不清 |
| 求解算法 | 正文遗传算法、突变概率.5 | 代码`soea_DE_best_1_L`，F=.5 | fail | p30/p51 code | DE缩放因子不是突变概率 |

## 14. Reusable Techniques

### 多时间尺度零售 EDA

**When useful:** 日数据噪声大、周/月/年结构不同。

**Why useful:** 同时看日、周、月、年可区分短周期与季节结构。

**Limitations:** 所有品类必须按完整日历对齐；缺失、零销量、缺货要分开编码。

### 可解释时间序列接价格决策

**When useful:** 需要把趋势/季节剥离后研究价格关联。

**Why useful:** Prophet成分清楚，便于把预测接口给优化器。

**Limitations:** 价格通常内生；必须时间留出、滚动回测并完整去除非价格成分。

### 需求带与选品二进制约束

**When useful:** 货架SKU有限且需兼顾品类覆盖。

**Why useful:** 把数量、SKU数和品类服务水平同时形式化。

**Limitations:** 上下界放松应共享同一个“类别是否满足”变量；求解后逐项验约束。

### 表内自动闭合审计

**When useful:** 方案包含几十个SKU与多层汇总。

**Why useful:** 自动复算件数、利润和品类满足度可快速发现接口错误。

**Limitations:** 算术闭合不证明数据、模型或优化有效。

## 15. Competition Takeaways

1. 时间序列先建立完整日历，明确“零销售、缺货、未上架、缺失”四种状态。
2. 所有预测至少做最后窗口留出和 rolling-origin，并比较季节朴素基线。
3. 价格—销量只写相关效应，除非有价格实验、工具变量或可信因果设计。
4. 平滑前后同时报告样本数、折外误差和斜率区间，避免靠平滑制造高相关。
5. 预测到优化的每个接口建立单位、时间窗、变量含义和代码字段对照表。
6. 二进制放松约束使用共享状态变量，避免上下界由不同类别分别逃逸。
7. 启发式算法至少多seed重复，并报告可行率、均值/最好值和与确定性基线的gap。
8. 提交前从原始附件一键运行支撑代码，确保正文表格可由同一版本生成。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 异常销量用1.5IQR识别并以去异常均值替换 | explicit | 4–5 | 4.1 | paragraph/equation | direct transcription | N/A for positive evidence | 会平滑真实峰值 |
| 日销量相关代码以手工补零而非日期对齐 | criticism | 39 | appendix Q1 code | code | direct transcription | N/A for positive evidence | 花菜补1个零、茄类补35个零 |
| 15组日K-S均报告p<.001 | explicit | 6 | 4.3.1 | paragraph | direct transcription | N/A for positive evidence | 无多重校正/时序独立处理 |
| 月K-S中花菜/水生根茎p=.2106 | explicit | 6,42 | 4.3.1/code | paragraph/code | direct transcription | N/A for positive evidence | 仅不能拒绝同分布，不证明相同 |
| ARIMA(0,0,1)(0,1,1)[52] AIC=1322.4且作者判拟合不足 | explicit | 9–11 | 4.3.3 | equation/paragraph | direct transcription | N/A for positive evidence | 无对比AIC |
| 正相关被解释为互补、负相关为替代 | explicit | 15–16 | 4.7 | figure 20/paragraph | direct transcription | N/A for positive evidence | 相关也可能由共同季节/价格驱动 |
| 正文CURE与代码PAM不一致 | criticism | 15–16,41 | 4.7/code | paragraph/code | direct transcription | N/A for positive evidence | `pam(cor(...),k=3)`不是CURE |
| Prophet加入周/年季节、中国节假日和价格 | explicit | 17–18,46 | 5.3/code | equation (7)–(12)/code | notation normalization | N/A for positive evidence | daily seasonality关闭 |
| Prophet样本内R²仅.45–.55 | explicit | 18–19 | 5.4 | table3 | direct transcription | N/A for positive evidence | 与“拟合非常良好”表述有张力 |
| 在已审查范围内，未发现rolling-origin、时间留出或朴素预测基线 | criticism | 1–73 | forecasting/validation/code | none found | derived interpretation | 审查正文p1–36、Prophet代码p44–49及其导入的diagnostics | 不能证明7天预测泛化 |
| 价格局部0.1元中位数平滑后相关达到-.565至-.966 | explicit | 22–24 | 5.4 | table4/figure24 | direct transcription | N/A for positive evidence | 重叠窗口与同期价格内生限制解释 |
| 代码去季节项时保留trend | criticism | 18,47 | 5.3/code | equation (12)/code | direct transcription | N/A for positive evidence | `yhat-yearly-weekly-holidays` |
| 表5–8只覆盖7月1–6日 | criticism | 25–26 | 5.6 | tables5–8 | independent calculation | N/A for positive evidence | 标题称1–7日，缺第7日 |
| 问题二需求函数不能按附录返回六品类预测 | criticism | 48–49 | appendix Q2 code | code | derived interpretation | N/A for positive evidence | bool regressor、重复fit、首循环return |
| 在已审查范围内，未发现可执行的模拟退火循环或运行日志 | criticism | 1–73 | 5.5/appendix code | none found | derived interpretation | 审查正文模拟退火段、p44–51全部Python代码及p73支撑材料列表 | 外部notebook referenced but unavailable |
| 问题三需求排除折扣与低利润10%记录 | explicit | 27 | 6.2.1 | paragraph | direct transcription | N/A for positive evidence | 是作者筛选，不是观测真需求 |
| 低利润筛选代码跨单品复用一个阈值并遗漏首单品 | criticism | 54,58 | appendix Q3 R code | code | direct transcription | N/A for positive evidence | `mymin`只在i==2分支更新 |
| 正文候选61种而优化代码固定58种 | criticism | 27,49–50 | 6.2.1/code | paragraph/code | direct transcription | N/A for positive evidence | 来源接口不一致 |
| 单品利润目标少计损耗部分采购成本 | criticism | 27 | 6.2.2 | equation | independent calculation | N/A for positive evidence | 常见实物口径应为`z(1-a)y-cy` |
| 正文单品需求带为60%–100% | explicit | 28 | 6.2.3 | equation | direct transcription | N/A for positive evidence | 上下界各允许一类失败 |
| 表10水生根茎307.5%、花叶58.6%违反原需求带 | criticism | 31–32 | 6.3 | table10 | independent calculation | N/A for positive evidence | 表示上下界由不同类别逃逸 |
| Geatpy决策维度122与元数据128不一致 | criticism | 49–50 | appendix Q3 code | code | independent calculation | N/A for positive evidence | 58+58+6+6=128 |
| u/v索引错误且v从未赋值 | criticism | 50 | appendix Q3 code | code | direct transcription | N/A for positive evidence | 上界约束被0乘关闭 |
| 代码需求上限写8倍而非1倍 | criticism | 50 | appendix Q3 code | code | direct transcription | N/A for positive evidence | 与正文直接冲突 |
| 求解模板是DE而非遗传算法 | criticism | 30,51 | 6.3/code | paragraph/code | direct transcription | N/A for positive evidence | `soea_DE_best_1_L_templet` |
| 表9共33项、利润合计743.3元 | interpretation | 30–31 | 6.3 | table9 | independent calculation | N/A for positive evidence | 算术闭合但含3个负利润项 |
| 正文批发价窗与代码近期一周窗不一致 | criticism | 27,55,59 | 6.2.2/code | paragraph/code | direct transcription | N/A for positive evidence | 三年6–7月 vs 2023-06-24至30 |
| 问题四动态库存模型仅提出数据与方程 | explicit | 32–35 | 7.1–7.10 | equations (15)–(20) | direct transcription | N/A for positive evidence | proposed but not implemented |
| 在已审查范围内，未发现需求/价格/优化参数的实际敏感性实验 | criticism | 1–73 | sensitivity/results/code | none found | derived interpretation | 审查全部主文、结果表、迭代图、R/Python代码和p73支撑清单 | 外部支撑文件不可评估 |
| p73列出多个支撑文件但PDF与仓库均未含附件 | criticism | 73 | supplemental list | figure/table | derived interpretation | N/A for positive evidence | 不把不可得材料改写成“作者未实现” |
