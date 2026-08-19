# Paper: “拍照赚钱”的任务定价

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_5df317cebc0a`
- Year: 2017
- Problem: B
- Award: 奖级未核验。文件名含“国家一等奖”且来源合集标为优秀论文，但文件名和合集标签均不构成独立奖项证据。
- Provenance tier: L; 仅本地用户提供合集，未找到可独立核验的官方展示或奖项记录
- Source file: `literature/raw_papers/2017/2017国赛国家一等奖B题优秀论文5.pdf`
- Source URL: unknown
- Verification source: unknown
- Pages: 45
- SHA-256: `1a32ed2ef9b843f48aac54d7d8adccb748c0574398a0a79f7faea8c04e91f2eb`
- Extraction method: embedded text；公式、回归表、灵敏度图和 MATLAB 代码页直接视觉核验
- Extraction quality: `success / usable_text_layer`；45/45 页有可用文本。数学公式在文本层多有空缺，因此关键系数、约束和代码以渲染页为准。
- Page convention: 1-based physical PDF pages
- Visually checked pages: p1、p9--11、p14--17、p19、p22--25、p29--30、p33--35、p39--40、p42、p44--45
- Unresolved extraction ambiguities: 主文未给附录输入表和辅助函数；部分图只提供曲线而无原始数值。公式本身已视觉核验，无中央页面不可读。
- Supplemental artifacts: 论文引用 `data1.xls`、`data2.xlsx`、`data3.xls`、`data_group.xlsx`、`data4_ans.xlsx`、`data4_group.xlsx` 及多个辅助函数，但仓库中均不可得。p29--45 仅含部分主脚本截图/文本，不含 `dis_matrix_O2P`、`dis_around`、`amount`、`LOF`、`predict`、`fun1`、`pre_price`、`pre_percent`、`geodistance` 等实现。

## 1. Problem Archetype

本文属于“空间特征工程 + 回归定价 + 多目标优化 + 空间打包 + 行为仿真”的众包平台决策原型：

- 用会员限额、最近用户平均距离和 Local Outlier Factor（LOF）构造任务价格特征。
- 用成功/失败任务的两个价格曲面给出价格上下界，再以总价格和平均成功率形成两个约束优化问题。
- 用自适应半径对任务分组，降低低成功率任务的单独暴露并修改路途价格。
- 对新项目生成价格与模型成功率，再用 100 次行为仿真作内部一致性比较。

它覆盖了从历史数据到部署决策的完整链条，但最终成功率仍是同一历史样本上的低拟合度多项式，打包与优化代码又与正文方法名称不一致。因此结果应理解为一套启发式定价方案，而不是经外部检验的因果或预测模型。

## 2. Problem Decomposition

1. **定价规律。** 修正一个经纬度疑点，删除 12 名偏远会员和 3 个任务；构造 1 km 内限额和、最近 5 人平均距离与 LOF，分别做单因素非线性回归。
2. **未完成原因。** 按完成标签分组拟合价格曲线，把失败组价格曲线较低解释为定价未充分考虑相应因素。
3. **新价格。** 用 LOF 与三个人--任务特征的加权和拟合成功/失败价格曲面；用二元完成标签的多项式 OLS 构造“成功率”；在价格曲面区间内优化总价或成功率。
4. **任务打包。** 用成功率决定任务半径，以局部密度和到更高密度点距离排序，将高/低成功率近邻最多四个一组，再按路程缩短折价。
5. **新项目与仿真。** 将上述模型应用到 2066 个新任务，生成打包与价格，随后模拟用户申请和按剩余额度分配任务。

主要接口风险是：单因素回归的 70/30 检验没有延续到最终成功率模型；正文“改进 DBSCAN + GA”与附录“改进 DPCA + 确定性循环”不一致；代码中打包中心、概率公式和输出范围存在断裂。

## 3. Data Processing

- 原始任务表读入 835 行，删除任务 297、298、303 后保留 832 行。
- 会员 B1175 的经纬度被作者判断为颠倒并交换；另删除 12 名远离任务区域的会员。没有坐标来源核验或删除前后性能比较。
- 地理距离由未提供的 `geodistance` / `dis_matrix_O2P` 转换；正文称由球面距离转直线距离，但具体公式和单位不可审计。
- 所谓“随机 70%/30%”在 `Q1_2.m` 中实际按行号末位固定切分：训练 583 行、测试 249 行，分别占 70.07%/29.93%；没有 `randperm` 或随机种子。
- `Q1_2.m` 删除了 12 行 `address_user`，却没有同步删除 `user_limit`，使会员坐标剩 1865 行而限额仍为 1877 行；后续 `amount(user_limit,D,1000)` 的对齐或可执行性取决于不可得辅助函数。
- 特征均值归一化后以 AHP 权重加总。最终成功率回归在全部 832 条清洗样本上拟合，没有独立验证集。
- 打包代码把任务按纬度排序后连接，未求解最短路径；且首次计算“中心”时实际只取组内最后一个任务点坐标。

## 4. Models Used

### 单因素非线性价格回归

**Purpose:** 检查 1 km 限额和、最近 5 人平均距离、LOF 与任务价格的关联。

**Inputs:** 清洗后的任务价格、会员/任务坐标、会员限额。

**Outputs:** 三条价格曲线及训练/测试均方残差。

**Why selected:** explicit；作者根据散点形状选择有理函数、平方根加线性项和 `log(L)+L` 形式。

**Important assumptions:** 固定的空间半径、最近人数和 LOF 邻居数能代表局部供需；单变量曲线可分离解释。

**Key equations or mathematical structure:** 限额和为二次分式；平均距离为 `q1 sqrt(d)+q2 d+q3`；LOF 为 `q1 log(L)+q2 L+q3`。

**Implementation notes:** 固定行号切分而非随机；LOF 测试与训练残差代码均漏掉拟合式的 `c*L` 项，验证的不是图 18/式 (9) 的完整模型。

### 完成/失败价格曲面与成功率 OLS

**Purpose:** 构造合理价格区间和每个任务的预计成功率。

**Inputs:** LOF、用户--任务综合因子、归一化价格、二元完成标签。

**Outputs:** 成功曲面 `P_S`、失败曲面 `P_F`、多项式成功率。

**Why selected:** explicit；作者用两个标签组的价格曲面之间区域作为可调价区间。

**Important assumptions:** 分组价格曲面可以定义因果可执行区间；二元完成标签可以用无约束 OLS 多项式表示概率。

**Key equations or mathematical structure:** 成功曲面含 x、y 的三次项，失败曲面含二次项和交互项；成功率式 (23) 的 `R²=0.2602`。

**Implementation notes:** 成功曲面绘图字符串把最后 `y^3` 写成第二个 `y^2`；式 (23) 的系数与 Q3/Q4 代码硬编码多项式不一致。OLS 输出还需手工裁剪到 `[0,1]`，不具备天然概率校准。

### 约束多目标定价

**Purpose:** 在原总价/成功率约束下分别提高成功率或降低总价，并用商家价格 90 构造期望利润。

**Inputs:** 合理价格上下界、成功率多项式、原总价 57707.5、原平均成功率 62.5%。

**Outputs:** 约 56000 总价下保持 62.5%，或 57707.5 总价下给出 68.4%；利润代理最优点 56908。

**Why selected:** explicit；平台同时关心成本和完成率。

**Important assumptions:** 商家每任务支付 90；模型成功率可作为真实执行概率；价格下降会使成功率上升的正文方向假设。

**Key equations or mathematical structure:** 两个单目标约束问题和 `W=sum_i (Q_i-Q'_i)R_i`。

**Implementation notes:** 正文称用遗传算法取局部最优，附录 `Q2_2.m` 实际调用 `fmincon`；初值是 835 维而清洗后上下界为 832 维，且没有保存返回值。

### 自适应半径任务分组

**Purpose:** 将预计低成功率任务与邻近高成功率任务最多四个一组。

**Inputs:** 预计成功率、任务间距离、任务半径 `R_i`、阈值 0.4。

**Outputs:** 原项目 62 个任务组成 25 组；新项目 123 个包。

**Why selected:** 正文称 DBSCAN 可发现非凸簇并过滤噪声，优于 K-means/层次聚类。

**Important assumptions:** 成功率越高半径越小或越大所形成的邻接规则能提高低成功率任务；每包不超过四个。

**Key equations or mathematical structure:** `lambda_i=2.06 exp(5S_i)+4.17`，`R_i=lambda_i t`；用户可达半径为信誉/预订系数乘最近 5 个任务平均距离。

**Implementation notes:** 附录脚本明确标为“改进 DPCA”，按局部密度和到更高密度点的距离排序；未实现标准 DBSCAN 的 `eps/MinPts` 密度可达扩张，也没有遗传算法。

### 打包定价与行为仿真

**Purpose:** 以固定任务价值加缩短后的路途费用定价，并评估新项目方案。

**Inputs:** 组内预计价格、选定用户到任务距离、组内路径、五因素申请权重、会员限额。

**Outputs:** 打包价格、模型成功率、100 次模拟成功率。

**Why selected:** explicit；把任务申请和限额分配过程显式化。

**Important assumptions:** 固定价值占 30%、路途费用占 70%；任务难度服从均值 0.9、方差 0.05 的正态分布；交通便利为 1/0.2 的 80%/20% 二点分布。

**Key equations or mathematical structure:** 五个启发式权重经乘加组合并截断到 `[0,1]`；每用户--任务做 Bernoulli 抽样，申请者按剩余额度比例排序。

**Implementation notes:** 模拟使用与定价模型同源的人为概率规则，不是独立现实验证；无随机种子，只有 100 次，最大二项标准误约 0.05。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 原始任务间距离 | considered only | 表示空间离群 | LOF 能更好表示局部密度 | not reported | 与 kNN 距离、核密度等基线 | 选择可解释，但未做特征消融 |
| LOF | selected | 任务--任务空间特征 | 能识别局部离群点 | 单因素散点和回归 | k 的训练内选择、公平基线 | k=3 后又由鲁棒性段建议 k≥5，设置未闭合 |
| 线性/其他回归 | considered only | 单因素价格拟合 | 根据散点形状选择非线性函数 | R²和残差表 | 同一测试集上的候选比较、模型选择规则 | 曲线是手工挑选；测试代码还漏掉 LOF 线性项 |
| Logistic / calibrated classifier | not reported | 二元成功率 | not reported | not reported | 分类基线、AUC/Brier/calibration | 用 OLS 多项式拟合 0/1 且 R²仅 0.2602，不宜称可靠概率 |
| AHP | selected | 三个人--任务特征权重 | 文献和经验 | 权重和为 1 | 判断矩阵、一致性比率、权重敏感性 | 权重来源不可复核 |
| 遗传算法 | claimed in prose / not found in code | 定价和打包求解 | 近似全局/处理复杂搜索 | 50 个结果点和曲线 | 编码、种群、适应度、迭代、种子 | 可得代码分别是 `fmincon` 和确定性 DPCA 循环 |
| K-means / 层次聚类 | rejected | 空间打包 | 只适合凸样本集 | not reported | 同成功率目标下的聚类比较 | 对层次聚类的概括过强；没有定量基线 |
| 改进 DBSCAN | selected in prose / not implemented as named | 空间打包 | 任意形状、可滤噪 | 模型成功率提高 2.3% | 实际完成数据、与不打包/标准 DBSCAN 对照 | 附录实现更接近密度峰值分组，方法身份不一致 |
| 行为仿真 | selected | 方案可靠性 | 模拟用户申请与限额分配 | 100 次内部模拟 | 真实新项目结果、外部校准 | 只能检查自设规则内的行为，不是现实有效性 |

## 5. Model Pipeline

`原任务/会员表 → 坐标修正与删除 → 空间距离 → 1 km 限额/人数、最近 5 人距离、LOF → 单因素回归 → 完成/失败价格曲面 + 二元成功率 OLS → 定价约束优化 → 自适应半径分组 → 路程折价 → 新项目价格/成功率 → 100 次行为仿真`。

关键断点：

- 单因素 hold-out 只验证各自价格曲线，没有验证最终多因素成功率模型。
- “合理价格区间”由结果标签分组后的曲面产生，再用于同样本优化，存在结果导向和泄漏边界。
- `Q2_2.m` 的维度不一致阻断正文遗传算法结果复现。
- 打包脚本与正文算法身份不同，且组中心和概率计算代码有缺陷。
- 仿真成功率由同一套人为权重产生，不能反证定价成功率的现实正确性。

## 6. Model Improvements

1. **把空间供需拆成三类可解释特征。** 比仅按区域均价更容易诊断任务定价，但各特征高度相关，未检验共线性。
2. **用成功/失败价格曲面构造任务级区间。** 给优化器提供显式上下界；标签分组并不能证明区间有因果可执行含义。
3. **用成功率驱动可变半径。** 目标是让低成功率任务搭载高成功率近邻，比纯空间聚类更贴近运营目标。
4. **把打包价格拆为固定价值与路途费用。** 结构便于解释和修改，但 30%/70% 是硬编码，路径又只按纬度排序。
5. **加入用户申请和限额竞争模拟。** 比只输出回归概率多了一层资源分配机制；由于概率模型本身未经外部校准，证据仍为内部模拟。

## 7. Parameter Estimation and Optimization

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| 70/30 split | 单因素回归训练/测试 | rows | p9--11；code p29 | 583 / 249 | algorithm hyperparameter | 行号末位固定切分 | no | 正文称随机，代码不是随机 |
| `r` | 统计周边用户/限额半径 | km | p9、p24 | 1 | author-assumed | subjective | yes | p24 图 40 显示此处波动大，作者建议 2--3 km |
| nearest-user count | 平均距离人数 | persons | p10、p24 | 5 | author-assumed | subjective | yes | 图 39 称从 4 起稳定 |
| LOF `k` | 近邻数 | neighbors | p8、p24--25 | 3 | algorithm hyperparameter | author setting | yes | p25 又称 k>5 才基本稳定，未回改基线 |
| `beta1,beta2,beta3` | 人--任务三特征权重 | dimensionless | p16 | 0.2131, 0.3036, 0.4833 | author-assumed | AHP based on literature/experience | no | 和为 1；判断矩阵与 CR 未报 |
| `alpha,beta` | 信誉/预订时间修正 | dimensionless | p15 table 5 | 0.80--0.99 / 0.90--0.99 | author-assumed | five-level lookup | no | 阈值为经验设定 |
| price bounds | 失败/成功曲面间价格 | currency/task | p15--16 | task-specific | data-estimated | separate OLS surfaces | no | 同样本标签分组，曲面 R²为0.8523/0.7780 |
| merchant price `Q_i` | 商家支付平台价格 | currency/task | p17 | 90 | author-assumed | scenario assumption | yes | 对利润高度敏感，作者承认需专家值 |
| max package size | 每包最多任务数 | tasks | p18 | 4 | author-assumed | practical limit | no | 未与用户行为数据校准 |
| `theta_normal` | 任务半径基准 | distance | code p35 | 500 | algorithm hyperparameter | author setting | no | 结合成功率指数变换 |
| success threshold | 高/低成功率分组阈值 | probability | code p35 | 0.4 | algorithm hyperparameter | author setting | no | 与 LOF 的 k 符号重名，正文未清楚区分 |
| fixed/travel shares | 打包固定价值/路途费用 | dimensionless | code p39 | 0.3 / 0.7 | author-assumed | hard-coded | no | 无拟合过程输出或置信区间 |
| difficulty random term | 任务难度 | dimensionless | p22 eq.36 | Normal(mean 0.9, variance 0.05) | author-assumed | synthetic draw | no | 正态分布无界，可能超出合理权重范围 |
| traffic random term | 交通便利 | dimensionless | p22 eq.37 | 1 with 0.8; 0.2 with 0.2 | author-assumed | Bernoulli scenario | no | 无现实频率依据 |
| simulation repetitions | 用户行为模拟次数 | runs | p23 | 100 | algorithm hyperparameter | author setting | no | 无 seed；单任务 MC SE 最大约0.05 |
| coefficient perturbation | 三个单因素回归系数 | percent | p25--26 | -5%, -2.5%, 0, +2.5%, +5% | algorithm hyperparameter | five-point grid | yes | 文称基于95% CI，但未列CI数值，图例是统一百分比 |

## 8. Validation

单因素回归使用独立行子集，形式上具有 hold-out；但切分是确定的，LOF 验证代码又漏项。最终成功率模型、优化收益和打包提升均在同一历史样本或其模型输出上评估。行为仿真不使用真实新项目完成标签。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 限额和价格曲线 | L5 - deterministic hold-out | hold-out | train/test MSE shift | 1 split | 17.3006 vs 16.4646；表称4.83% | signed code result为-4.832% | 固定行号切分、绝对值口径未说明 | 支持该切分下误差量级接近 |
| 平均距离价格曲线 | L5 - deterministic hold-out | hold-out | train/test MSE shift | 1 split | 14.6306 vs 15.4912，+5.882% | 极端距离段趋势反常 | 后半段被作者主动弃用，无预注册范围 | 支持保留区间内的有限拟合 |
| LOF价格曲线 | L5 label with invalid implementation | hold-out | train/test MSE shift | 1 split | 表称6.57% | 复算绝对变化6.165%；验证代码漏 `c*L` | 测试的不是式(9)完整模型 | 不能据表4验证式(9) |
| 完成/失败价格曲面 | L1 - in-sample fit | same sample | R² | 1 | 0.7780 / 0.8523 | 绘图代码重复 y² 项 | 标签分组同样本，无外部验证 | 支持样本内曲面描述，不支持因果价格区间 |
| 最终成功率模型 | L1 - in-sample OLS | same sample | R² | 1 | 0.2602 | 无概率校准、代码系数不一致 | 二元响应、无 hold-out | 仅支持很弱的样本内线性投影 |
| 定价优化 | L2 - model-internal comparison | same sample | 总价/模型成功率 | 50 个输出点，生成方式不完整 | 约降价2.9%或相对提高9.4% | 可得 `fmincon` 代码维数不一致 | 结果完全依赖低拟合度成功率模型 | 只能称模型内方案差异 |
| 打包 | L2 - model-derived before/after | same sample | 模型成功率变化 | not reported | 最高+7.2%，平均+2.3% | 无真实执行结果 | 算法身份和代码路径不一致 | 只支持内部评分改变 |
| 新项目模拟 | L2 - synthetic behavior simulation | synthetic-mismatched | 模型率与模拟率差 | 100 | 示例绝对差≤0.19 | 0.29 vs0.10相对差65.5% | 同源人为概率、无真实标签、无CI | 只支持自设模拟中绝对差未超过20个百分点的示例 |

在已审查的 p1--45、全部附录代码和可得补充材料范围内，未发现新项目真实执行结果、预注册外部测试、概率校准曲线、重复训练切分或对最终成功率模型的独立验证。输入工作簿与辅助函数不可得。

## 9. Sensitivity and Robustness

论文确实主动改变若干主观参数，但多为一维曲线且缺原始输出表。最重要的反面结果是：1 km 半径位于波动较大的区域，k=3 又低于作者自己认为稳定的 k≥5；因此不能概括为“模型整体鲁棒”。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 最近用户人数 | 5 | 1--10 | integer grid | 定价波动比例 | 从4人起接近稳定 | no after 4 | 支持5人选择，未验证下游优化 |
| 周边覆盖半径 | 1 km | 图示约0.5--10 | grid / plotted points | 定价波动比例 | 半径增大时曲线总体下降；1 km附近变化较大 | unclear | 正文先写“半径越高定价越高”又写“半径越大定价越低”；图支持后者 |
| 商家每任务价格 | 90 | 85--100 | grid | 系统利润 | 近线性增加 | yes for profit optimum | 作者承认这是高敏感参数 |
| LOF近邻 k | 3 | 1--20 | integer grid | LOF值 | k>5后接近1并稳定 | yes | 基线3不在作者识别的稳定区，应重新拟合而非只宣称鲁棒 |
| 单因素回归系数 | fitted | ±2.5%, ±5% | five-point OAT | 整条价格曲线 | 因素1负向更敏感；因素2/3部分方向明显变化 | partial | 未给标量输出或结论保持率，不能推出整体优化稳健 |

## 10. Visualization Strategy

- 图 3--10 用空间气泡、用户覆盖与交互流程形成特征假设。
- 图 12--20 把 LOF、单因素曲线、hold-out 点和区域价格热力图并列展示。
- 图 21--29 对完成/失败组分别画曲线和曲面，直观但容易诱发事后因果解释。
- 图 30 用总价--成功率前沿比较两种模型内优化目标。
- 图 31--38 展示分组、路程等效、打包前后评分和新项目空间结果。
- 图 39--45 是参数扰动曲线，能暴露不稳定区域；论文结论没有充分吸收这些负面结果。

## 11. Writing Structure

论文按四问推进，先从机理猜想构造特征，再进入回归、优化、分组、定价和仿真，叙事完整。附录给出 17 页 MATLAB 主脚本，使实现审计成为可能。

写作上的主要问题是术语和证据边界：

- 将固定行号切分写成“随机抽取”。
- 将结果标签分组曲线差异写成任务失败“主要原因”，没有控制混杂或因果设计。
- 把 OLS 二元响应输出称成功率，却没有校准且 R²仅0.2602。
- 把 DPCA 风格代码称改进 DBSCAN，把 `fmincon`/确定性循环称遗传算法。
- 把绝对概率差20个百分点写成“20%以内”，没有说明相对误差可达65.5%。
- 鲁棒性段展示基线不稳定，却仍在优点中概括“鲁棒性强”。

## 12. Strengths

1. 从用户--任务与任务--任务两个层面组织特征，业务含义清楚。
2. 单因素部分保留了一个未用于拟合的行子集，而不是只报告样本内 R²。
3. 主动检查最近人数、覆盖半径、商家价格、LOF k 和回归系数扰动。
4. 打包模型明确限制每包最多四个，并把固定价值和出行成本分开。
5. 仿真把用户申请、额度竞争和任务分配写成顺序步骤，便于后续重构。
6. 附录代码足够揭示数据删除、特征归一化、权重和核心实现风险。

## 13. Weaknesses

1. 数据删除和 B1175 坐标交换由目测决定，没有源数据核验或删除敏感性。
2. 单因素验证并非随机切分；LOF 验证漏掉 `c*L`，表 4 的6.57%也与21.5751/20.2449不闭合。
3. 用完成标签分组拟合价格后再解释“失败原因”存在循环推断，不能建立定价不足的因果结论。
4. 最终成功率模型是无界 OLS 多项式，R²仅0.2602，正文还写出“降价提高成功率”的方向，与平台酬金机制相反。
5. 正文遗传算法、DBSCAN 与可得 `fmincon`、DPCA 风格代码不一致。
6. `Q2_2.m` 的 835 维初值与清洗后 832 维边界不匹配；输入、辅助函数和返回结果也缺失。
7. 打包定价把“中心”计算为组内最后一个任务点，并按纬度排序代替路线优化；Q4 又对负成功率多项式取绝对值，而 Q3 不取。
8. 仿真是同源规则的内部生成，100 次模拟不足以证明真实实施可靠；报告的20%实际是绝对百分点口径。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable | p2 references three attachments；repo无输入表 | 无法重算任何回归、优化、分组或模拟 |
| Code availability | partial | p29--45 主脚本 | 关键辅助函数缺失；只提供论文内代码而非源文件 |
| Dependency / environment information | not reported | p29--45 | MATLAB版本、Curve Fitting/Optimization工具箱未报 |
| Random seed | not reported | 所谓随机split、GA、难度/交通抽样、100次模拟 | 70/30实际无随机；仿真不可重复 |
| Hard-coded constants | extensive | p29--45 | 删除索引、权重、归一化均值、阈值、输出范围均硬编码 |
| Formula-to-code consistency | materially inconsistent | p9--25 vs p29--45 | LOF漏项、成功曲面y次方、成功率系数、GA/DBSCAN身份不一致 |
| Code-to-result consistency | not assessable with visible failures | p17--23、p29--45 | 835/832维度错、会员限额未同步删除、组中心错误、输出范围固定 |
| Overall reproducibility | not reproducible | 全文45页、完整可得代码与补充材料范围 | 缺数据/函数/环境且主脚本存在阻断性错误 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 70/30样本数 | 随机70%训练、30%测试 | 固定索引给583/249，共832，即70.07%/29.93% | concern | p9--11；code p29 | 比例近似正确，但不是随机 |
| 限额回归MSE偏移 | 17.3006→16.4646，表称4.83% | `(test-train)/train=-4.8322%` | concern | p10 table 2；code p30 | 绝对变化为4.83%，代码输出带负号 |
| 距离回归MSE偏移 | 14.6306→15.4912，5.88% | +5.8822% | pass | p10 table 3 | 算术通过 |
| LOF回归MSE偏移 | 21.5751→20.2449，6.57% | signed -6.1654%，绝对6.1654% | fail | p11 table 4 | 6.57%不由表值产生；代码还漏线性项 |
| AHP权重和 | 0.2131,0.3036,0.4833 | 和为1.0000 | pass | p16 paragraph | 不验证权重合理性 |
| 最终成功率拟合 | R²=0.2602 | 仅约26%样本方差由OLS线性投影解释 | concern | p17 eq.23 | 无hold-out或概率校准 |
| 总价下降 | 57707.5→约56000，称2.9% | 下降2.9589% | pass | p17 paragraph | “约56000”限制精度 |
| 成功率提高 | 62.5%→68.4%，称提高9.4% | 相对提高9.44%；绝对+5.9个百分点 | pass | p17 paragraph | 必须区分相对与百分点 |
| 新项目任务计数 | 1689独立、48四包、35三包、40二包，共2066 | 包数48+35+40=123；原任务1689+192+105+80=2066 | pass | p23 paragraph | 计数闭合 |
| 模拟差异口径 | 模型率与模拟率差在20%内 | 0.29 vs0.10绝对差0.19，但相对差65.52% | concern | p23 table 8 | 只在“20个百分点”口径下成立 |
| 会员特征对齐 | 删除12名偏远会员后计算限额和 | `address_user`删12行，`user_limit`未删，1865 vs1877 | fail | code p29 | `amount`输入可能错位或维数不合 |
| 定价优化维数 | 清洗后任务优化 | `x0=ones(835,1)`，价格上下界按832个任务生成 | fail | code p34 | `fmincon`维度不一致 |
| 打包中心 | 以组内平均经纬度为中心 | p39/p44首次用 `mean(address_order(a{i}(w),:))`，w为循环末值 | fail | p19 paragraph；code p39/p44 | 实际是最后一个任务点，不是组均值 |
| 算法身份 | 改进DBSCAN并用GA求解 | 代码标题“改进DPCA”，实现局部密度排序；无GA调用 | fail | p18--19；code p34--38 | 方法名称与实现不一致 |
| 成功率代码口径 | 同一回归用于原/新项目 | Q3直接多项式并裁剪；Q4先取`abs`再裁剪 | fail | code p40/p45 | 负预测在Q4被翻为正概率 |

## 14. Reusable Techniques

### 特征假设--单因素审计--联合模型

**When useful:** 平台数据含空间供需、资源容量和任务聚集度。

**Why useful:** 先用单因素图和 hold-out 排除明显不合适的特征，再进入联合模型。

**Limitations:** 特征选择、函数选择和最终模型必须使用分离的数据流程，避免同一测试集反复调参。

### LOF 作为任务稀疏度特征

**When useful:** 任务分布不均、全局密度无法表示局部稀疏。

**Why useful:** LOF 可把局部邻域相对密度压缩成任务级标量。

**Limitations:** 应验证 k、坐标尺度和边界效应；不能把 LOF 当作因果价格因素。

### 价格--成功率双目标前沿

**When useful:** 平台同时关心支付成本和任务完成率。

**Why useful:** 分别固定预算/完成率能给决策者可解释的折中方案。

**Limitations:** 成功率模型必须经过校准和外部验证；优化应报告可行性和同预算基线。

### 低成功率任务与高成功率邻居打包

**When useful:** 空间邻近任务可一次执行且存在冷热任务不均。

**Why useful:** 打包目标直接面向弱任务，而非纯粹最小化空间距离。

**Limitations:** 要用标准算法名称、明确定义簇生成规则，并用真实执行实验验证捆绑效应。

### 申请--分配离散事件模拟

**When useful:** 用户申请具有概率性，任务分配受信誉、优先时间和剩余额度影响。

**Why useful:** 能把回归得分传播到实际资源竞争过程。

**Limitations:** 概率必须由行为数据校准；需报告seed、重复次数、置信区间和现实回测。

## 15. Competition Takeaways

1. 训练/测试切分必须由代码和文字共同记录；固定尾数切分不要写成随机抽样。
2. 每个验证公式必须调用与训练完全相同的特征项，尤其检查遗漏线性项和归一化。
3. 二元成功率优先用 Logistic/树模型并报告 AUC、Brier、校准与 hold-out，不用低 R² 的无界 OLS 直接优化。
4. 把“算法名称--正文公式--代码入口--输出文件”做一张接口表，防止 DBSCAN/DPCA、GA/fmincon 混用。
5. 数据删行后立即断言所有会员字段长度一致；优化前断言初值和上下界维数一致。
6. 打包中心和路径用可复算函数实现，不在循环变量残留值上取 `mean`，也不以纬度排序冒充路线优化。
7. 模拟验证要区分绝对百分点与相对误差，并给二项置信区间及真实部署回测。
8. 敏感性发现基线位于不稳定区时，应重新估计并重跑全部下游结果，而不是仍宣称整体鲁棒。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 论文以限额、最近用户距离和LOF构造价格特征 | explicit | 1,4--11 | 5.1 | paragraphs / equations 7--9 | direct transcription | N/A for positive evidence | 三类空间供需特征 |
| B1175经纬度被交换，另删除12名会员和3个任务 | explicit | 9；29--34 | 5.1.2 / appendix | paragraph / code | direct transcription | N/A for positive evidence | 无外部坐标核验 |
| 所谓随机70/30实际为固定行号末位切分 | criticism | 9--11；29 | validation / Q1_2.m | code | independent calculation | 正文p9--11与附录Q1_2全部split代码 | 583/249，无随机调用 |
| Q1_2删除会员坐标但未同步删除限额 | criticism | 29--30 | Q1_2.m | code | direct transcription | p29--30完整Q1_2可得代码；amount辅助函数不可得 | 1865 vs1877 |
| 限额和/距离回归MSE变化可由表值复算 | interpretation | 10 | 5.1.2 | tables 2--3 | independent calculation | N/A for positive evidence | -4.832%和+5.882% |
| LOF验证代码漏掉拟合式的线性项 | criticism | 9,11；30 | eq.9 / Q1_2.m | equation / code | direct transcription | 式9、图18、p30训练测试残差代码 | `c*L`只用于绘图，不用于MSE |
| 表4的6.57%与MSE表值不闭合 | criticism | 11 | table 4 | table | independent calculation | p11全表 | 绝对变化为6.165% |
| 由完成/失败曲线差异推断失败原因是循环证据 | criticism | 12--13 | 5.1.3 | figures 21--26 / paragraphs | derived interpretation | p12--13全部三因素比较 | 无混杂控制或干预 |
| AHP权重为0.2131/0.3036/0.4833且和为1 | explicit | 16 | 5.2.1 | paragraph | independent calculation | N/A for positive evidence | 判断矩阵和CR未报 |
| 正文称降价导致执行率上升 | explicit | 15 | fig.27 explanation | paragraph | direct transcription | N/A for positive evidence | 与平台奖励机制方向相反，需实证确认 |
| 最终成功率多项式样本内R²为0.2602 | explicit | 17 | eq.23 | equation / paragraph | direct transcription | N/A for positive evidence | 无hold-out与校准 |
| 成功率公式与Q3/Q4硬编码系数不一致 | criticism | 17；40,45 | eq.23 / Q3_2 / Q4_1 | equation / code | direct transcription | 主文p17与附录p40,p45逐项比较 | 多个价格项和交互项数量级不同 |
| 成功价格曲面绘图代码重复y²而非y³ | criticism | 16；33 | eq.21 / Q2_1.m | equation / code | direct transcription | p16公式与p33设计矩阵/ezsurf字符串 | 图29可能未画出回归式本身 |
| 模型内优化称总价降2.9%或相对成功率升9.4% | explicit | 17 | 5.2.2 | paragraph / figure 30 | direct transcription | N/A for positive evidence | 复算2.9589%和9.44% |
| 正文称GA，附录Q2实际调用fmincon | criticism | 17；34 | 5.2.2 / Q2_2.m | paragraph / code | direct transcription | 正文求解段与全部可得Q2代码；无其他GA文件 | 算法身份不一致 |
| Q2初值835维而清洗后任务为832 | criticism | 29,34 | Q1_2 / Q2_2 | code | independent calculation | p29删除3任务、p34初值和边界调用 | 阻断性维数错误 |
| 正文打包称改进DBSCAN并用GA | explicit | 18--19 | 5.3.1 | paragraph | direct transcription | N/A for positive evidence | 最高+7.2%、平均+2.3%为模型分数 |
| 附录打包代码标为改进DPCA且无GA | criticism | 34--38 | Q3_1/Q3_2 | code | derived interpretation | p34--38完整分组代码 | 用局部密度和更高密度点距离排序 |
| 打包首次中心计算实际取最后一个任务点 | criticism | 19；39,44 | 5.3.2 / Q3_2/Q4_1 | paragraph / code | direct transcription | p19中心定义与p39,p44代码 | `mean`输入为单个`a{i}(w)` |
| 打包路径按纬度排序而非路线优化 | criticism | 20；39,44 | 5.3.2 / code | equation / code | direct transcription | p20距离定义与p39,p44 | 路途费用代理可能偏差大 |
| 新项目123个包和2066原任务计数闭合 | interpretation | 23 | 5.5.3 | paragraph | independent calculation | N/A for positive evidence | 48+35+40=123；1689+377=2066 |
| 模拟使用100次且无随机种子 | explicit | 22--23 | 5.5 | equations / algorithm | direct transcription | N/A for positive evidence | 难度正态、交通二点分布均为作者假设 |
| 0.29与0.10仅在绝对20个百分点口径内 | criticism | 23 | table 8 | table | independent calculation | p23完整示例表 | 相对差65.52% |
| 覆盖半径段落方向表述自相矛盾 | criticism | 24 | 6.1 | figure 40 / paragraph | direct transcription | p24图40和完整解释段 | 图示总体支持半径增大定价下降 |
| baseline k=3低于作者识别的k≥5稳定区 | criticism | 24--25 | 6.1 | figure 42 / paragraph | derived interpretation | p24--25完整k讨论 | 下游结果未用稳定k重跑 |
| Q3与Q4对负成功率的处理不一致 | criticism | 40,45 | Q3_2 / Q4_1 | code | direct transcription | p40和p45同一多项式实现 | Q4额外取abs后再裁剪 |
| 在已审查范围内未发现最终成功率外部验证 | criticism | 1--45 | validation / appendix | none found | derived interpretation | 全文、全部代码附录；输入表和辅助函数不可得 | 单因素hold-out不等于最终模型验证 |
| 可得代码与材料不足以复现结果 | criticism | 28--45 | appendix | none found | derived interpretation | 附录数据表和所有主脚本；输入/辅助函数/环境均不可得 | overall not reproducible |
