# Paper: 基于动态规划、统计分析、静态博弈的穿越沙漠游戏策略设计

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_f54b502c16d7`
- Year: 2020
- Problem: B（穿越沙漠）
- Award: 未核验。本地合集文件名/目录标签不能证明奖项；另有已隔离的两页赛题题面与本论文不是同一文献。
- Provenance tier: L（local collection only, award unverified）
- Source file: `literature/raw_papers/2020/2020B：基于动态规划、统计分析、静态博弈的穿越沙漠游戏策咯设计.pdf`
- Source URL: unknown
- Verification source: unknown
- Pages: 104
- SHA-256: `624e74483d26d8207761dc5225b67247aee6badce0115cbbcd84816e47186098`
- Extraction method: OCR fallback（Tesseract 5.5.0，`chi_sim+eng`，250 DPI，PSM 3）+ manual visual review
- Extraction quality: 内嵌文本为 0；OCR 104/104 页均有文本，101289 个非空白字符，中位数 959.5 字符/页，无页级失败。正文检索质量良好；公式、百分比、表格与 pp.30–104 代码的括号/下标以视觉渲染为准。
- Page convention: 1-based physical PDF pages
- Visually checked pages: pp.1–104 全页渲染巡检；重点高分辨率复核 pp.7–10（状态空间、转移和复杂度）、pp.15–20（1024 情景统计、Monte Carlo、天气等效、第四关结论）、pp.22–26（收益矩阵和混合策略）、pp.30–84（全部 C++ 动态规划/随机天气代码，重点 pp.52–57、61–67、73、78–80）、pp.84–104（全部 Python 仿真/策略代码，重点 pp.84–86、97–104）。
- Unresolved extraction ambiguities: pp.30–104 为代码截图，OCR 对 `l/1`、括号和长数组易混；本报告只引用经视觉确认的代码结构。第四关硬编码天气数组的逐项值不是中央结论，未将 OCR 结果当作精确数据；可确认其随机化方式是对单个固定数组做有限交换。
- Supplemental artifacts: p.29–30 列出 `Result.xlsx`、`代码.rar`、`图.rar`；当前仓库未提供这些独立附件。PDF 附录包含多份 C++/Python 代码截图，但没有可直接执行的源文件、原始输出、随机种子、编译环境或工作簿。

## 1. Problem Archetype

本文覆盖四个相互衔接的原型：

- **图上的有限时域动态规划（dynamic programming, DP）**：状态为日期、位置、水、食物，价值为可保留的最大现金；处理已知天气下的精确策略。
- **情景枚举与策略挖掘**：第三关枚举 \(2^{10}=1024\) 个晴朗/高温序列，对每个序列求完全信息最优解，再统计到达天数和初始购买量。
- **随机仿真与风险—收益评价**：把高温天行走概率作为策略参数，以失败率、成功条件下平均资金和失败记 0 的无条件平均资金比较方案。
- **非合作博弈**：第五关用双人单阶段收益矩阵选择纯/混合策略；第六关用局部 2×2 博弈矩阵给出行走、挖矿、村庄购买的局部均衡。

方法链的优点是由“确定性精确解”逐步扩展到随机和多人情形。关键边界是：第三/四关从完全信息最优解中提炼在线规则，存在幸存者偏差；第六关声称将多阶段博弈拆成逐日静态博弈，但日期间的库存与位置状态实际耦合，缺少适用条件证明。

## 2. Problem Decomposition

论文分为三问六关：

1. **问题一（第一、二关）**：天气全知、单人。先证明只需保留连接起点/终点/村庄/矿山的最短路子图，再对完整图和简化图分别做 DP，回溯最优购买、移动和挖矿策略。
2. **问题二（第三、四关）**：天气只逐日揭示、单人。第三关因只有晴朗/高温两类、10 天，枚举 1024 个完全信息天气序列并统计规律；把候选在线策略交给 10000 次/参数点 Monte Carlo。第四关用“天气等效”为购买量定标，再抽取 100 个天气序列做 DP、筛选前 20 个解，归纳路线。
3. **问题三（第五、六关）**：多人。第五关构造若干固定路线/购买策略的双人收益矩阵；第六关把 30 天视为多阶段博弈，再分别分析同地、同矿、同村时的局部 2×2 博弈。

显式管线为：

地图图化
→ 最短路功能子图
→ 确定天气 DP 精确解
→ 完整图/简化图结果核对
→ 全情景 DP 数据集
→ 到达日/购买量统计
→ 在线策略参数化
→ Monte Carlo 风险—收益评价
→ 第四关天气等效与抽样 DP
→ 多人收益矩阵与局部均衡。

论文没有建立一个统一的随机动态规划/马尔可夫决策过程来直接优化在线策略，而是以完全信息 DP 作为模式发现器，再手工收缩在线策略空间。

## 3. Data Processing

### 地图处理

- 把地区作为顶点、相邻关系作为无向边。
- 定义终点、村庄、矿山为“功能点”。作者证明每次移动应缩短到下一功能点的距离，据此仅保留起点/功能点及其最短路并集。
- 第一、二关同时运行完整图和简化图，正文称最高分和回溯策略一致。

### 状态离散与支配

- 所有状态变量均为整数箱/天/节点：\(s=(i,j,k,l)\)。
- 对同一 \((i,j,k,l)\) 只保留现金最多的路径，利用无后效性和最优子结构压缩重复搜索。
- 村庄购买的朴素四重扩展用现金支配提前 `break`，论文据此将局部购买更新降为二维量级；没有形式化证明该剪枝在所有迭代顺序下都安全，但完整/简化结果一致提供了有限 sanity check。

### 随机情景与统计

- 第三关只含晴朗/高温，代码以 10 位二进制枚举全部 1024 个序列。
- 从每个完全信息最优解提取到达天数和起点购买 \((w_i,f_i)\)，计算样本均值/标准差并观察二维峰。
- 论文没有把 1024 个序列按在线策略可用信息重新优化；这些是“预知未来”的 oracle 解，只用于模式发现。
- 第四关代码对一个硬编码 30 日天气数组做 0–29 次随机交换，保持天气计数不变；这不是按固定日概率独立采样，且 `srand(time(0))` 在函数内重置。

### Monte Carlo 评价

- 第三关对高温天行走概率 \(p=0,0.01,\ldots,1\) 每点运行 10000 次；首日天气决定初始购买量，之后逐日独立生成晴朗/高温。
- 失败率以百分数保存；成功平均资金只在成功样本上计算；无条件平均资金将失败收益置 0。
- 没有随机种子、置信区间、重复批次或方差报告。

## 4. Models Used

### 图动态规划模型

**Purpose:** 求天气完全已知时的全局最优现金和逐日策略，并为随机情形提供 oracle 样本。

**Inputs:** 图 \(G=(V,E)\)、天气序列、截止日、资金、负重、资源价格/重量/消耗、村庄/矿山位置和挖矿收益。

**Outputs:** \(\max_{i,k,l}dp(i,\mathrm{FinalPoint},k,l)\) 及前驱回溯路径。

**Why selected:** 作者明确识别出状态无后效性、重复子问题和最优子结构（pp.5–6）。

**Important assumptions:** 天气序列完全已知；资源箱数、天数和节点离散；同状态较多现金严格支配较少现金；玩家可在购买时精确调节整数箱数。

**Key equations or mathematical structure:** 状态

\[
s=(i,j,k,l),\qquad kw_w+lw_f\le W.
\]

价值 \(dp(i,j,k,l)\) 为该状态可拥有的最大现金。转移包括：

\[
dp(0,1,k,l)=M_0-kp_w-lp_f,
\]

村庄加购（双倍价格）、停留（1 倍消耗）、挖矿（3 倍消耗并加收入）、移动（2 倍消耗并换邻接点）；式 (1)–(5) 见 pp.7–8。

**Implementation notes:** C++ 使用稀疏邻接表、三角形资源数组和前驱状态表。论文估算复杂度 \(O(dpn^2)\)，代表性状态数约 \(2.3\times10^8\)。第一关报告 10470 元/24 天；第二关 12730 元/30 天。

### 全情景策略统计

**Purpose:** 从第三关所有完全信息最优策略中提取在线决策的候选结构。

**Inputs:** 1024 个二元天气序列及每个序列的 DP 最优路径。

**Outputs:** 到达天数分布、初始购买量均值/标准差和二维峰；候选路线/行走/购买规则。

**Why selected:** 10 天、两类天气使完全枚举可行；作者认为确定天气最优解包含随机天气优秀策略的共性（pp.3, 14）。

**Important assumptions:** 完全信息最优解中的频繁模式对在线策略有迁移价值；对“最优解”样本的选择偏差可由后续仿真补偿。

**Key equations or mathematical structure:** 到达日计数；购买量样本均值与无偏样本标准差；“优秀区间”用均值 ±1 标准差，同时又以二维分布的高购买量峰作为保守起点。

**Implementation notes:** 表 5 的计数为 576/320/112/16；表 6 均值水 38.4、食物 37.2，标准差 3.1/1.1。最终按首日晴朗/高温使用 42水44食物或54水54食物，并非直接采用均值 ± 标准差。

### Monte Carlo 在线策略评价

**Purpose:** 比较高温天移动概率和初始资源量对失败率与资金的影响。

**Inputs:** \(p\in[0,1]\)、首日条件购买、晴朗/高温各 0.5、三步最短路线。

**Outputs:** `LoseRate`、成功条件 `AvgIncome`、失败记 0 的 `Income`。

**Why selected:** 在线天气下无法直接使用完全信息 DP；仿真可对候选策略进行风险—收益比较（pp.14, 17）。

**Important assumptions:** 每日天气独立同分布；晴朗/高温概率固定 0.5；10000 次足以比较曲线；失败效用设为 0。

**Key equations or mathematical structure:**

\[
\mathrm{LoseRate}=\frac{n-n_1}{n},\quad
\mathrm{AvgIncome}=\frac{\sum_{i=1}^{n_1}m_i}{n_1},\quad
\mathrm{Income}=\frac{\sum_{i=1}^{n_1}m_i}{n}.
\]

**Implementation notes:** `simulation.py` 对 101 个 \(p\) 值各运行 10000 次。\(p=1\) 报告 Monte Carlo 9351，严格期望 9350；多/少买 5 箱作为资源扰动。

### 天气等效启发式

**Purpose:** 把第四关晴朗/沙暴折算为高温日，简化购买量设置。

**Inputs:** 三类天气的资源消耗、起点/村庄购买比例 7:3、停留/行走/挖矿净收益。

**Outputs:** “5 晴朗 + 1 沙暴约等于 6 高温”的等效规则。

**Why selected:** 直接在未知三类天气下设计购买/路线困难，作者希望用单一“等效高温日”给保守购买量（p.19）。

**Important assumptions:** 起点/村庄购买比例可固定为 7:3；三种行为净收益可线性相加；不同天气可按净收益做线性等效；路径与库存状态对边际价值无影响。

**Key equations or mathematical structure:**

\[
B_{i1}=-1.3(c_{fi}p_f+c_{wi}p_w),\quad B_{i2}=2B_{i1},\quad
B_{i3}=1000+3B_{i1},\quad B_i=\sum_{j=1}^3B_{ij},
\]

并令 \(xB_1+yB_3=(x+y)B_2\)。

**Implementation notes:** 正文给 \(x/y=0.214\approx1/5\)，但用附录第四关参数独立复算得到 \(x/y=0.1875=3/16\)（若 \(x\) 为晴朗数、\(y\) 为沙暴数），与正文不符。该折算也没有通过仿真对照。

### 静态收益矩阵与局部博弈

**Purpose:** 在玩家策略相互影响时寻找纯策略/混合策略均衡。

**Inputs:** 固定路线/购买策略的资源成本、失败惩罚，或同地/同矿/同村局部动作成本。

**Outputs:** 第五关纯策略 \(S_6\)；第六关局部行走/停留、挖矿、村庄购买概率。

**Why selected:** 多人同路、同矿、同村会改变消耗、收益和价格，单人最优不再可直接使用（pp.21–22）。

**Important assumptions:** 玩家理性、对称、非合作；收益矩阵已正确覆盖未来成本；局部均衡可逐日拼接；双方在递归近似中以 1/2 概率选下一动作。

**Key equations or mathematical structure:** 对 2×2 矩阵令两纯动作期望收益相等求混合概率；村庄双方停留的递归成本满足

\[
\frac14[(-135-x)+(-975)+(-1705)+(-3140)]=-x.
\]

**Implementation notes:** 行走矩阵给停留/行走概率 0.3/0.7；矿山“挖矿”严格支配停留；村庄给停留/购买 55.6%/44.4%。正文关于表 8 的一条最佳反应叙述写反，但两个非对称纯策略均衡和混合概率仍正确。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 搜索/暴力枚举策略树 | rejected in favor of DP | 确定天气全局策略 | 重复子问题、无后效性和最优子结构使搜索重复 | 状态压缩与复杂度推导 | 与通用最短路/MDP求解器的时间对照 | 选择正确；状态定义清晰，是全文最可靠部分 |
| 完整地图 DP | selected as baseline | 保留全部路径 | 不预先依赖最短路猜想 | 与简化图输出一致 | 原始输出工作簿不可得 | 提供 L2 内部检查，但单个两关结果不等同于一般证明 |
| 最短路功能子图 DP | selected | 降低节点数与计算量 | 证明多走路只增加消耗 | 完整/简化最高分和路线一致 | 更复杂含时边/多人干扰地图未比较 | 在本题规则下可迁移；应明确适用条件 |
| 直接随机动态规划/MDP | not implemented | 在线天气策略 | not reported | not reported | 与手工规则 + Monte Carlo 的最优性差距 | 这是最重要缺失基线；当前在线策略不具全局最优保证 |
| 全 1024 情景 DP + 统计 | selected | 第三关策略挖掘 | 状态规模小，可完全枚举 | 全情景覆盖与后续 Monte Carlo | 未做样本外策略选择/偏差校正 | 适合探索，但 oracle 选择造成幸存者偏差 |
| Monte Carlo | selected | 评价在线候选策略 | 比较期望资金与失败率 | p=1 严格期望互证、参数曲线 | 种子、置信区间、重复批次 | 用途合理；只能验证模拟规则内风险收益 |
| 天气等效 | selected | 第四关购买简化 | 将三类天气压成高温天便于复用 DP | not reported | 与原三天气模型的误差/决策一致性 | 算术有源内不一致，且线性等效忽略路径状态，证据弱 |
| 纯/混合静态博弈 | selected | 第五关固定策略选择 | 对称玩家收益可列矩阵 | 矩阵最佳反应与混合方程 | 更完整策略集、全局仿真 | 小矩阵可审计，但策略集由作者手选 |
| 逐日局部博弈拼接 | selected | 第六关多阶段近似 | 引用命题称阶段均衡可拼接 | 三个局部 2×2 算例 | 状态耦合条件、三人全局基线、仿真 | 库存/位置跨日耦合，引用条件未核验，不能声称子博弈完美均衡 |

## 5. Model Pipeline

1. 用图论证明删去非功能最短路之外的边。
2. 以 \((日,点,水,食物)\) 建 DP，现金作为价值，前驱表回溯策略。
3. 在第一、二关分别跑完整图和简化图，作为简图 sanity check。
4. 第三关把 1024 个天气序列逐一送入同一 DP，形成“天气—完全信息最优策略”数据集。
5. 从数据集统计路线、到达日、购买峰，手工形成参数化在线策略。
6. 用 Monte Carlo 扫描高温天移动概率和资源扰动，选择 \(p=1\) 的保守策略。
7. 第四关以天气等效设置资源，再对 100 个硬编码计数的随机排列求完全信息 DP，筛选高收益路线。
8. 第五/六关把候选策略成本写成小型收益矩阵，求纯/混合均衡。

DP 输出在后续既充当模式发现数据，也充当第四关“优秀解”筛选器；这不是独立验证。Monte Carlo 是更接近在线策略评价的分支，但第四关的完整仿真结果/代码—输出链未展示。

## 6. Model Improvements

- **图简化 + DP 双实现**：把结构证明转化为可运行的完整/简化双路检查，降低后续 1024 次求解成本。
- **三角形资源数组**：代码只为满足 \(3k+2l\le1200\) 的食物维度分配内存，并用 `short` 保存现金；比完整四维矩形显著节省空间。
- **购买状态支配剪枝**：遇到已存在更优现金的资源状态即截断一部分购买循环。该思路有价值，但论文没有给独立单元测试或形式化安全证明。
- **精确 oracle → 统计 → 在线仿真**：用确定性最优解缩小策略空间，再用失败率/期望评价；比直接凭直觉定策略更系统。
- **风险与条件收益分开**：同时画失败率、成功条件均值和无条件均值，避免只看幸存者的高分。
- **局部博弈矩阵**：把多人复杂相互作用拆成可手算 2×2 结构，便于给出规则；代价是全局状态耦合和三人互动没有覆盖。

## 7. Parameter Estimation and Optimization

DP 本身没有统计参数估计；它在有限离散状态空间上最大化现金。随机部分的关键概率、样本数、效用和策略集多为题目给定或作者设定。论文没有置信区间或超参数选择准则。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| \(M_0\) | 初始资金 | 元 | pp.30–104 code | 10000 | problem-provided | N/A - given | no | 各关相同 |
| \(W\) | 负重上限 | kg | pp.30–104 code | 1200 | problem-provided | N/A - given | no | 状态约束 \(3k+2l\le1200\) |
| \(p_w,p_f\) | 水/食物基础价 | 元/箱 | pp.13, 30–104 | 5, 10 | problem-provided | N/A - given | no | 村庄双倍、终点半价回收 |
| \(w_w,w_f\) | 水/食物箱重 | kg/箱 | pp.13, 30–104 | 3, 2 | problem-provided | N/A - given | no | 用于状态可行域 |
| \(c_w,c_f\) | 天气基础消耗 | 箱/日 | pp.30–104 code | 第一/二关水(5,8,10)、食(7,6,10)；第三/四关水(3,9,10)、食(4,9,10) | problem-provided | N/A - given | partial | 天气等效复算依赖此组值 |
| `BaseIncome` | 每日挖矿基础收益 | 元/日 | pp.30–104 code | 1000（第一/二/四）；200（第三） | problem-provided | N/A - given | no | 多人时收益按人数变化 |
| \(d,p\) | 截止日、节点数 | day / count | pp.7, 30–84 | 关卡特定；代表性 30日/64点 | problem-provided | N/A - given | no | 进入复杂度 \(O(dpn^2)\) |
| \(p_{hot}\) | 第三关高温日概率 | dimensionless | pp.17, 84–86 | 0.5 | author-assumed | fixed probability assumption | no | 日独立；未从数据估计 |
| \(p\) | 高温天移动概率 | dimensionless | pp.17–18, 84–86 | 0–1，步长 0.01；选择 1 | algorithm hyperparameter | grid sweep | yes | 每点 10000 次模拟 |
| 初始购买（第三关） | 首日晴/高温的水食 | box | pp.16–18, 84 | (42,44)/(54,54) | author-assumed | 1024 oracle 分布峰 + 手工平衡 | yes | ±5 箱扰动；不是统计估计量 |
| \(n\) | 每个 \(p\) 的 Monte Carlo 次数 | repetitions | p.85 code | 10000 | algorithm hyperparameter | author setting | no | 无重复批次/置信区间 |
| 失败效用 | 模拟失败时资金 | 元 | pp.17, 21–22 | Monte Carlo 为 0；净收益/博弈叙述为 -10000 | author-assumed | normalization | no | 不同章节效用零点不同，需避免直接横比 |
| 起点:村庄购买比 | 资源购买比例 | dimensionless | p.19 | 7:3 | author-assumed | 从第一关 8:2/7:3 近似统一 | no | 天气等效的核心主观量 |
| 沙暴概率（第四关） | 沙暴日概率 | dimensionless | p.19–20 | 10% | author-assumed | fixed | no | C++ 抽样代码是固定数组交换，并非按 10% iid 生成 |
| 第四关样本/筛选 | 天气样本数/保留数 | count | pp.20, 78–84 | 100 / top 20 | algorithm hyperparameter | author setting | no | 报告 93.41% 与 20 个一次性选择不闭合 |
| 局部继续概率 | 双方同停留后各动作概率 | dimensionless | pp.25–26 | 1/2 | author-assumed | symmetry approximation | no | 直接决定 585 和 1985 递归成本 |
| 混合概率 | 行走/村庄局部均衡 | dimensionless | pp.25–26 | 行走0.7/停留0.3；村庄停留0.556/购买0.444 | data-estimated | 2×2 无差异条件 | no | 对收益扰动未测 |
| Random seed | Python/C++ 随机种子 | N/A | pp.78–86, 101 | not reported / `srand(time(0))` | algorithm hyperparameter | not reported | no | Python无固定种子；C++函数内按秒重置 |

## 8. Validation

本文没有外部真实数据，因此无 L5。最强证据是可穷举场景、完整/简化同目标输出，以及 Monte Carlo 与可解析期望的内部互证。第四关和博弈分支的证据明显弱于第三关。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 简化图不损失第一/二关最优解 | L2 - same-objective implementation check | same sample | 最高现金/回溯路线 | 2关×2图版本 | 正文称完整图和简化图完全一致 | none reported | 原始输出和可执行代码包不可得 | 支持这两个关卡实例的等价，不单独证明所有地图 |
| 第三关天气场景覆盖 | L2 - exhaustive finite enumeration | synthetic-same-model | 1024/1024 序列、到达日计数闭合 | 1024 | 576+320+112+16=1024，百分比=100% | N/A | 每个解预知全序列，不是在线验证 | 支持 oracle 数据集内部完整性 |
| 第三关 \(p=1\) Monte Carlo | L2 - analytic/Monte Carlo consistency | synthetic-same-model | 期望终点资金 | 10000 | 仿真9351；严格9350 | none reported | 同一规则；种子和置信区间未给 | 支持 `simulation.py` 在该策略点的均值实现大体正确 |
| 高温移动概率选择 | L3 - grid perturbation | same model | 失败率、成功均值、无条件均值 | 101×10000 | \(p\) 增大时失败率降，\(p=1\) 无失败且无条件均值最高 | 低 \(p\) 失败率高 | 只在固定50/50 iid天气和手工购买量下 | 支持该模拟设定内选 \(p=1\) |
| 初始资源量 | L3 - ±5 box perturbation | same model | 失败率/无条件均值曲线 | 2 perturbations×101×10000 | 多5箱约9314，少5箱约7000；基线9350 | 少买导致失败 | 只改两个对称点，未给二维网格/误差 | 支持基线附近少买风险高，不证明全局购买最优 |
| 第四关路径一 | L1 - selected-sample frequency / same-sample objective | same sample | top解中路线频率、期望资金 | 100样本、保留20（按正文） | 报93.41%、失败<2.5%、期望10500 | not reported | 百分比不闭合；抽样分布/代码—输出缺失；oracle selection | 不能可靠支持具体概率，只能视为启发式候选 |
| 行走局部博弈 | L2 - payoff-matrix algebra | theoretical | 最佳反应/混合概率 | 1矩阵 | 两个非对称纯均衡；混合停留0.3 | 文本一条最佳反应写反 | 矩阵未来成本为近似 | 支持给定矩阵的均衡，不验证矩阵代表完整游戏 |
| 村庄局部博弈 | L2 - recursive-cost and payoff algebra | theoretical | 递归成本/混合概率 | 1矩阵 | \(x=1985\)，停留55.6% | none reported | 50/50延续假设主观，无状态验证 | 支持给定近似矩阵的代数结果 |
| 第六关逐日均衡拼接 | not assessable | unknown | 子博弈完美均衡条件 | not reported | 作者声称可逐日拼接 | state coupling not handled | 引用材料/适用前提未在论文内展开，三人模型未算 | 不能由现有证据证明全局或子博弈完美均衡 |

## 9. Sensitivity and Robustness

论文把“确定性算法”误当作“没有灵敏度问题”。算法在固定输入上确定，并不意味着结果对价格、天气概率、截止日、地图或负重不敏感。实际做出的敏感性主要集中在第三关策略参数。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 高温天移动概率 \(p\) | 1 | 0–1, step 0.01 | grid；每点10000 iid simulations | 失败率、成功条件资金、无条件资金 | \(p\downarrow\) 时失败急升，成功条件均值变化较小；\(p=1\) 最优 | no within tested grid | 清楚展示风险—幸存者收益权衡；只适用于50/50天气与固定购买规则 |
| 水/食物同时 +5 箱 | 基线首日条件购买 | +5 each | scenario rerun over full p grid | 同上 | \(p=1\) 约9314，低于基线9350 | no | 多买造成现金/回收损失，但影响较小 |
| 水/食物同时 -5 箱 | baseline | -5 each | scenario rerun over full p grid | 同上 | \(p=1\) 约7000且失败率显著上升 | yes for risk | 少买触发可行性边界；未探索非对称水/食物变化 |
| 预设“高温日需求” | \(n_{hot}=4,n_{sun}=3\) 的资源公式 | \(n_{hot}=3,4,5\)；\(n_{sun}=3\) | 100 simulations each, p=0.5 | death count / average money | 代码存在，结果未在正文报告 | unknown | 只能确认尝试，不能据不可得输出主张稳健 |

在已审查范围内，未发现对天气概率、沙暴概率、失败效用、负重、价格、截止日、地图边、DP剪枝、第四关样本数、收益矩阵或多人局部成本的正式敏感性实验；审查覆盖正文 pp.1–29、全部代码附录 pp.30–104 和当前可用补充材料清单。`Result.xlsx`/源代码包不可得。

## 10. Visualization Strategy

- **地图与路径叠图**（图 1–5、10）：把完整地图、功能点简化和回溯路径对应起来，直接支撑“结构先降维”。
- **逐日资源表**（图 2–3 内嵌表）：同时显示节点、现金、水、食物，使策略可执行；但表格字体很小，最好独立成表。
- **二维购买量峰图**（图 6）：展示 1024 个 oracle 解的多峰结构，提醒均值不是唯一代表；作者据此选保守高量峰。
- **双轴风险—收益曲线**（图 7–9）：蓝色失败率，红色成功条件均值，绿色无条件均值，能暴露幸存者偏差。应加 Monte Carlo 置信带和样本量标注。
- **2×2 收益矩阵**（表 7–10）：比纯文字更适合手查最佳反应与混合概率；表 8 也因此暴露正文最佳反应笔误。
- **附录代码全量展示**（pp.30–104）：透明度高，但 75 页截图不如可执行压缩包、版本说明和关键伪代码有效。

## 11. Writing Structure

正文 29 页，先统一游戏规则/假设/符号，再以 DP 作为主轴，随后处理随机和多人扩展；75 页附录给代码。写作上的突出优点是从状态定义到公式、伪代码、复杂度、结果表和策略规则形成闭环。

主要问题：

- “最优”在全文分别指 DP 全局最优、oracle 样本高频、Monte Carlo 无条件均值较高和博弈均衡，边界没有始终区分。
- 第四关 93.41%、2.5%、10500 缺可追溯表/公式；核心概率比第三关弱很多。
- “确定性算法不存在灵敏度”“博弈结果不会因微扰失效”是没有实验支持的强表述。
- 第六关标题为三人多阶段博弈，但所有明确矩阵都是两人；正文最终也承认没有三人全局最优解。
- 代码附录含多份复制改参数版本，缺目录化差异说明、干净运行日志和环境。

## 12. Strengths

- DP 状态、价值、约束和五类转移定义完整；不是只给代码结果。
- 在证明图简化后仍用完整/简化双实现核对，体现“理论降维 + 计算 sanity check”。
- 第三关穷举全部 1024 序列，计数闭合，并把策略发现与在线 Monte Carlo 评价分成两步。
- 风险评价同时保留失败率、成功条件收益和无条件收益，能识别只看幸存者的偏差。
- 第三关 Monte Carlo 均值有可独立严格计算的 9350 基准；独立复算支持正文。
- 收益矩阵使局部博弈结论可逐项审计；主要混合概率独立复算通过。

## 13. Weaknesses

- 第三/四关先从预知未来的 DP 最优解中筛模式；第四关还筛选高收益前 20，选择偏差没有定量修正。
- 第四关天气“随机生成”实际是对固定天气计数做有限交换，且函数内 `srand(time(0))`；不对应正文固定日概率假设，也没有种子。
- 第四关三项关键数值证据不闭合或不可追溯：20 个解不能直接产生 93.41%，失败<2.5% 无计算表，10500 无输出/区间。
- 天气等效的独立复算不支持正文 0.214，且线性净收益忽略路径/库存状态。
- 第六关把跨日状态耦合的动态博弈拆为独立局部矩阵，未核验引用命题的适用条件；也没有三人收益函数或全局仿真。
- 代码作为截图而非源文件提供；依赖、编译器、Python/C++版本、随机种子和运行日志缺失。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | 关卡参数、地图数组和天气数组嵌在 pp.30–104；`Result.xlsx` 不可得 | 可转录输入，但无法核对原始输出/完整逐日结果 |
| Code availability | partial | pp.30–104 展示 C++/Python 截图；`代码.rar` 不可得 | 需人工转录 75 页，截图换行/字体可能引入错误 |
| Dependency / environment information | unavailable | C++、Python、NumPy、Matplotlib、`windows.h` 可见 | 版本、编译器、OS和运行命令未报告；随机 C++ 版本偏 Windows |
| Random seed | not reported | Python `random`/NumPy 无 seed；p.80 `srand(time(0))` | 随机结果和 9351/10500 不可逐位重现 |
| Hard-coded constants | extensive | 各关复制代码并直接改节点、天气、消耗、文件名 | 易发生版本错配；没有统一配置或测试夹具 |
| Formula-to-code consistency | partial | 核对 pp.7–9 与 pp.30–84；pp.17 与 pp.84–86 | DP 五转移和第三关统计结构大体一致；天气等效未编码；第四关抽样与概率假设不一致 |
| Code-to-result consistency | partially assessable | 表5可由枚举计数结构检查；9350可独立计算；第四关输出不可得 | 10470/12730/93.41%/2.5%/10500 无可执行包和输出文件，不能完整复现 |
| Overall reproducibility | partially reproducible | 数学结构、参数和大部分代码逻辑可读；独立算术可复核多项 | 缺源文件/工作簿/环境/种子，且附录含可见缺陷；不能原样重跑全链 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 代表性状态空间 | \(|S|\approx2.3\times10^8\) | \(30\times64\times\tfrac12\times600\times400=230400000\) | pass | p.7 equation | 是连续三角形近似，离散边界差很小 |
| 第三关情景数/计数 | 1024，分为576/320/112/16 | 总和1024；比例56.25/31.25/10.9375/1.5625%，合计100% | pass | p.15 table 5 | 表格闭合 |
| \(p=1\) 严格期望 | 9350；模拟9351 | 枚举首日及后两日8种组合，终点回收后均值9350；单次SD约97.98，n=10000均值SE约0.98 | pass | pp.17–18, 84–85 | 模拟差1元约1.02 SE，合理 |
| 多/少买曲线方向 | +5约9314，-5约7000 | 多买提高前期支出且只半价回收；少买引入失败 | pass (qualitative) | p.18 figures 8–9 | 精确曲线因随机种子不可复现 |
| 天气等效比 | \(x/y=0.214\approx1/5\) | 用 p.19 方程及第四关 \((c_w,c_f)=(3,4),(9,9),(10,10)\)、价格5/10得 \(B=(571,-53,-170)\)，故 \(x/y=117/624=0.1875\) | fail | p.19 equation; p.73 parameters | 用第一关消耗也不产生0.214；正文未给另一参数源 |
| 5晴+1沙=6高温 | 由 \(x/y\approx1/5\) 推出 | 若 \(x\) 是晴朗、\(y\) 是沙暴，则 5:1 应为 \(x/y=5\)，与正文 \(1/5\) 变量方向还相反 | fail | p.19 paragraph/equation | 数值与叙述存在双重口径问题 |
| 第四关路线频率 | top20 中93.41%走路径一 | 20 个解各一次选择的比例只能以5%为步长；\(0.9341\times20=18.682\) | fail / denominator unknown | p.20 paragraph | 若分母不是20，论文未定义 |
| 行走矩阵混合概率 | 停留0.3、行走0.7 | 解 \(-585p-405(1-p)=-270p-540(1-p)\) 得 \(p=0.3\) | pass | p.25 table 8/equation | \(p\) 为对手停留概率 |
| 表8最佳反应文字 | “B行走时A最佳行走” | B行走列：A停留-405 > A行走-540 | fail (text only) | p.25 paragraph/table 8 | 之后列出的两个非对称纯均衡仍正确 |
| 矿山严格支配 | 双方都应挖矿 | 对B两列，A挖矿95>−135、595>−135 | pass | p.26 table 9 | 给定矩阵内成立 |
| 村庄递归成本 | \(x=1985\) | \(4x=135+x+975+1705+3140\Rightarrow x=1985\) | pass | p.26 equation | `停留-停留`收益为−2120 |
| 村庄混合概率 | 停留55.6%、购买44.4% | 无差异条件得 \(p=1435/2580=0.55620\) | pass | p.26 table 10 | 四舍五入一致 |
| 交流后平均成本 | 520 | \((465+575)/2=520\) | pass | p.24 paragraph | 使用S1/S3各一人 |
| 购买统计数组清零 | `memset(num_of_cases,0,sizeof(num_of_points))` | 只清 `sizeof(int)` 字节，而非整个二维数组 | concern | p.57 code | 数组有静态零初始化且 `init()` 只调用一次，当前运行可能未受影响；复用会出错 |
| 全情景完整图初始化 | 每个天气调用 `init(w)` | `init` 每次向 `world_map` 再次 `push_back`，邻接重复累积 | concern | pp.52–53 code | 不改变最大值但增加重复转移和运行量 |
| 第四关随机天气 | 固定概率下随机生成100种天气 | 代码对一个固定数组做0–29次随机交换，保持天气计数；`srand(time(0))` 每次重置 | fail (sampling design) | pp.78–81 code | 不是独立日概率抽样，也未充分均匀洗牌 |

## 14. Reusable Techniques

### 用支配状态构造资源—路径 DP

**When useful:** 有限时域、离散资源、图上移动，未来只依赖当前库存/位置/时间。

**Why useful:** 同状态只留最高现金，把指数策略树压为伪多项式状态表，并可保存前驱回溯可执行方案。

**Limitations:** 资源刻度决定复杂度；购买剪枝必须证明安全；随机在线信息需要扩展为随机 DP/MDP，而不是直接复用完全信息解。

### 结构证明后做原图/简图双跑

**When useful:** 能通过最短路、无支配边或功能节点压缩图。

**Why useful:** 证明提供一般理由，双实现提供实例级防错；后续大量情景计算可显著加速。

**Limitations:** 动态边成本、拥堵、多人交互或到达时奖励可能破坏静态最短路等价。

### 完全情景 oracle 用于模式发现

**When useful:** 不确定变量维数很小，可穷举全部情景，但在线最优模型较难。

**Why useful:** 可发现重复出现的路线、库存边界和到达时间，为在线策略降维。

**Limitations:** oracle 预知未来，不能直接当在线性能；必须用独立在线仿真/回测并量化选择偏差。

### 同时报告条件收益和失败率

**When useful:** 高收益方案可能只在幸存样本上表现好。

**Why useful:** `失败率 + 成功条件收益 + 无条件收益` 能清楚区分冒险策略和真正高期望策略。

**Limitations:** 失败效用必须由决策目标定义；应报告置信区间、风险厌恶指标或分位数，而不只均值。

### 用小型收益矩阵审计局部互动

**When useful:** 多人系统中某些碰撞事件只有两种动作，且即时成本可明确列出。

**Why useful:** 最佳反应、纯均衡、混合概率可手算，规则容易解释。

**Limitations:** 局部矩阵必须包含未来状态价值；跨期库存耦合时不能无条件把逐日均衡拼成全局均衡。

## 15. Competition Takeaways

1. 动态规划先写状态、价值、可行域、转移和终端价值，再写代码；明确“全知最优”还是“在线最优”。
2. 图简化既要证明，也要用原图/简图同目标双跑做实例核对。
3. 从 oracle 最优解挖策略时，单独标注未来信息泄漏和幸存者偏差；候选策略必须在在线信息约束下重新评价。
4. Monte Carlo 至少固定种子、报告重复数/置信区间，并确保采样器真的来自声明的概率分布。
5. 百分比必须和分母闭合；20 个样本不可能直接得到 93.41%。
6. 对天气等效、收益矩阵等手算模块做一遍独立算术复核，再把结果写进代码测试。
7. 确定性算法同样需要输入敏感性；“无随机”不等于“无灵敏度”。
8. 多阶段博弈若有库存/位置状态，局部均衡拼接前必须验证动态可行性和子博弈条件。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 状态为日期、位置、水、食物，价值为最大现金 | explicit | 6 | §4.3 | equation/paragraph | notation normalization | N/A | DP核心定义 |
| 状态空间约 \(2.3\times10^8\) | explicit | 7 | §4.4 | equation/paragraph | direct transcription | N/A | 独立复算通过 |
| 五类转移为起点买、村庄买、停留、挖矿、移动 | explicit | 7–9 | §4.5–4.6 | equations (1)–(5), algorithm 1 | notation normalization | N/A | 代码结构一致 |
| 复杂度声称为 \(O(dpn^2)\) | explicit | 10 | §4.7 | paragraph | direct transcription | N/A | 运行时间/硬件未给 |
| 第一关10470元/24天，第二关12730元/30天 | explicit | 11–12 | §5.1–5.2 | figures 2–3 and paragraphs | direct transcription | N/A | `Result.xlsx`不可得 |
| 完整图与简化图输出完全相同 | explicit | 13 | §5.3 | paragraph | direct transcription | N/A | 实例级内部检查 |
| 第三关枚举 \(2^{10}=1024\) 个天气序列 | explicit | 14 | §6.1 | paragraph | direct transcription | N/A | 仅晴朗/高温 |
| 到达日计数576/320/112/16闭合到1024 | interpretation | 15 | §6.1.2 | table 5 | independent calculation | N/A | 百分比合计100% |
| 第三关初始购买按首日天气取42/44或54/54 | explicit | 16–17 | §6.1.3–6.1.4 | table 6/paragraph | direct transcription | N/A | 由峰值再手工调整 |
| Monte Carlo 每个行走概率运行10000次 | explicit | 84–85 | appendix simulation.py | code | direct transcription | N/A | 正文未写n，代码补足 |
| \(p=1\) 模拟9351、严格期望9350且零失败 | explicit | 18 | §6.2 | paragraph/figure 7 | direct transcription | N/A | 独立期望复算通过 |
| 9350 严格期望可由8个三日天气组合得到 | interpretation | 17–18 | §6.2 | code/paragraph | independent calculation | N/A | 含终点半价回收 |
| ±5箱扰动分别约9314和7000 | explicit | 18 | §6.2 | figures 8–9/paragraph | direct transcription | N/A | 无随机误差条 |
| 天气等效给 \(x/y=0.214\approx1/5\) | explicit | 19 | §6.4 | equation/paragraph | direct transcription | N/A | 与独立复算冲突 |
| 用附录参数复算天气等效为0.1875 | criticism | 19, 73 | §6.4 / appendix | equation/code | independent calculation | N/A | 正文未给可产生0.214的参数 |
| 5晴+1沙的文字比例与所写 \(x/y\approx1/5\) 方向相反 | criticism | 19 | §6.4 | equation/paragraph | derived interpretation | N/A | x明确代表晴朗、y代表沙暴 |
| 第四关从100天气中筛前20后报告93.41%选路径一 | explicit | 20 | §6.5 | paragraph | direct transcription | N/A | 具体分母未另定义 |
| 20个单次路线选择不能产生93.41% | criticism | 20 | §6.5 | paragraph | independent calculation | N/A | 若另有加权分母，论文未报告 |
| 第四关失败率<2.5%、期望10500 | explicit | 20 | §6.5 | paragraph | direct transcription | N/A | 计算表/输出/区间不可得 |
| 在已审查范围内未发现2.5%与10500的可复核计算对象 | criticism | 1–104 | full paper | none found | derived interpretation | 正文pp.1–29、附录代码pp.30–104、可用补充材料清单均审查 | `Result.xlsx`/代码包不可得 |
| 第五关给S4/S6收益矩阵并选择S6纯策略 | explicit | 22–23 | §7.1.3–7.1.6 | table 7 | direct transcription | N/A | S6严格支配S4 |
| 允许交流时S1/S3平均成本520 | explicit | 24 | §7.1.7 | paragraph/equation | independent calculation | N/A | (465+575)/2 |
| 表8给两个非对称纯均衡和0.3/0.7混合概率 | explicit | 25 | §7.2.1 | table 8/equation | direct transcription | N/A | 代数复算通过 |
| 表8正文把B行走时A的最佳反应写成行走 | criticism | 25 | §7.2.1 | table/paragraph | independent calculation | N/A | 表中-405>-540，应为停留；均衡结论仍对 |
| 村庄递归得x=1985、停留/购买55.6%/44.4% | explicit | 26 | §7.2.3 | equation/table 10 | direct transcription | N/A | 独立复算通过 |
| 第六关标题为三人多阶段博弈，但明确矩阵均为两人 | criticism | 24–29 | §7.2–8.3.3 | paragraphs/tables | derived interpretation | N/A | p.29也承认未给三人完全最优解 |
| 逐日局部均衡拼接缺少跨日状态耦合条件验证 | criticism | 24–27 | §7.2 | cited proposition/paragraph | derived interpretation | N/A | 库存、位置、剩余天数直接影响下一阶段可行集 |
| “确定性算法不存在灵敏度问题”混淆确定性与输入敏感性 | criticism | 27 | §8.1 | paragraph | derived interpretation | N/A | 输入天气/价格/期限变化仍可改变最优策略 |
| 代码用固定数组交换生成第四关天气 | explicit | 78–80 | appendix random-weather DP | code | direct transcription | N/A | 保持天气计数，非iid抽样 |
| `srand(time(0))` 在洗牌函数内重置且只做0–29次交换 | criticism | 80 | appendix random-weather DP | code | derived interpretation | N/A | 随机性、均匀性和可复现性均受限 |
| `memset` 仅清 `sizeof(num_of_points)` 字节 | criticism | 57 | appendix buying-statistics DP | code | independent calculation | N/A | 当前静态初值可能掩盖缺陷 |
| 完全天气枚举版本反复向邻接表追加相同边 | criticism | 52–53 | appendix complete enumeration DP | code | derived interpretation | N/A | 结果不变但转移重复、性能恶化 |
| 在已审查范围内未发现外部真实验证或正式置信区间 | criticism | 1–104 | full paper | none found | derived interpretation | 正文、结果、灵敏度、全部附录代码与可用补充材料清单均审查 | 最高证据为L3同模型扰动 |
