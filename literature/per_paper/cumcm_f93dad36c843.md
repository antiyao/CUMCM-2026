# Paper: 生产过程中的决策优化设计

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_f93dad36c843`
- Year: 2024
- Problem: B（生产过程中的决策问题）
- Award: 奖级未核验。人工版本审查确认本地 36 页与组委会官方展示前 36 页内容一致，官方第 37 页为空白；展示状态仍不能证明具体奖级。
- Provenance tier: O（official display content matched after version review；award level not inferred）
- Source file: `literature/raw_papers/2024/B159.pdf`
- Source URL: unknown
- Verification source: `https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024btlw/241104/1977943.shtml`
- Pages: 36
- SHA-256: `bced3c19c5b9b5ecca93c1f000075eb11e7308c214a013726c30782d9ec45112`
- Extraction method: OCR fallback（Tesseract 5.5.0，`chi_sim+eng`，250 DPI，PSM 3）+ manual visual review。原 PDF 可被 `pdfinfo/pdftoppm` 读取，但 pypdf 因 malformed Boolean object 失败；仅为 OCR 计页兼容，临时用 Ghostscript `pdfwrite` 重写副本，未改动源 PDF。
- Extraction quality: OCR 36/36 页均有文本，37145 个非空白字符，中位数 938 字符/页，无页级失败。原/临时兼容副本均为 36 页，全部 36 页经 `pdftoppm` 100 DPI 渲染逐像素完全一致；OCR quality JSON 已锚回原始路径和原始 SHA-256，并记录临时副本哈希。
- Page convention: 1-based physical PDF pages
- Visually checked pages: pp.1–36 全页原始 PDF 渲染巡检；重点复核 pp.4–7（检验假设、拒绝域、功效与样本量）、pp.8–13（16方案、几何分布成本、利润表）、pp.14–18（状态—决策模型、成本收益、递归）、pp.18–22（Beta 后验、三重积分、决策表、灵敏度图）、pp.25–36（全部 R/Python 代码，特别 pp.25、28–30、33–36）。
- Unresolved extraction ambiguities: OCR 对 pp.11–12 长公式和 pp.25–36 代码长行易错，所有源内矛盾均以视觉页确认。版本审查已确认本地 pp.1/18/36 与官方同页一致，官方 p.37 为空白；版本身份歧义已解除。
- Supplemental artifacts: p.24 列出 `问题一代码.R`、`问题二代码.R`、`问题三代码.py`、问题四两份代码及灵敏度代码；当前仓库没有独立源文件。PDF 附录只有代码截图，且问题三截图缺少可运行所需的初始化/主调用。

## 1. Problem Archetype

本文是“统计抽样 + 随机成本核算 + 多阶段生产决策 + Bayesian 不确定性传播”的混合论文：

- **单侧比例假设检验**：在标称次品率 10% 下设计拒收/接收规则，并以功效—检测成本加权目标选样本量。
- **精确期望成本/利润枚举**：对两个零件直接装配的 16 种检测/拆解决策，利用几何分布计算得到一件合格成品的期望成本。
- **状态—决策/动态规划**：把 8 零件→3 半成品→1 成品的多工序流程写成检测、装配、拆解的递归决策。
- **Bayesian 后验积分**：以 Beta(1,1) 先验和名义次品率构造 Beta 后验，三重积分计算问题二的期望利润，并尝试修改问题三的缺陷概率。
- **超参数敏感性**：单独变化 Beta 先验的 \(\alpha\) 或 \(\beta\)。

数学层面最扎实的是问题二的 16 个解析期望式与逐表比较。问题一的最优样本量高度依赖作者权重，且正态近似在 \(n=43\) 时未满足一项精确二项显著性约束。问题三正文描述随机动态规划，但附录代码是确定性阈值搜索且不可运行，故 56.7/54.2 元是本篇最严重的复现边界。

## 2. Problem Decomposition

1. **问题一：来料抽样**
   - 情形 (1)：\(H_0:p\le0.1\) vs \(H_1:p>0.1\)，显著性 0.05。
   - 情形 (2)：\(H_0:p>0.1\) vs \(H_1:p\le0.1\)，显著性 0.10。
   - 用正态近似写拒绝域与功效函数，再以检测成本减加权平均功效选择 \(n\)。
2. **问题二：两零件—成品流程**
   - 四个二元决策：检测零件1、检测零件2、检测成品、拆解不合格成品，共16种。
   - 分“拆解/不拆解”推导生产一件合格品的期望成本，带入6种题设参数，选期望利润最大者。
3. **问题三：多工序流程**
   - 定义零件/半成品/成品的检测、质量和拆解状态。
   - 定义采购/检测/装配/拆解成本及销售/回收收益。
   - 声称用记忆化动态规划寻找最大期望利润路径。
4. **问题四：次品率不确定**
   - 用 Beta 共轭后验替换固定次品率。
   - 对问题二做三维后验积分；对问题三先模拟后验预测缺陷，再声称重跑 DP。
   - 改变 \(\alpha,\beta\) 做灵敏度图。

论文的接口逻辑是“问题一给样本量 → 问题四形成后验 → 重算问题二/三”。但实际代码中问题四固定 `n=100`，未使用问题一得到的 43；也没有实际观测缺陷数 \(k\)，而以 \(k=np_0\) 代替，接口没有闭合。

## 3. Data Processing

本文没有外部真实数据清洗；所有输入是题设成本/次品率和作者生成的伪后验参数。

- **二元质量编码**：样本 \(X_i\in\{0,1\}\)，零件/半成品/成品质量状态也用 0/1。
- **决策编码**：问题二把四个 yes/no 决策映射到 001–016；问题三把检测/拆解状态组成状态元组。
- **名义率转“样本”**：问题四设 \(k=np_0\)，用 Beta\((1+np_0,1+n-np_0)\)。这不是实际抽样数据；当 \(np_0\) 非整数时更不可能对应观察计数。
- **数值积分**：R `cubature::adaptIntegrate` 在 \([0,1]^3\) 上积分16个利润函数与三个独立 Beta 密度。
- **Monte Carlo 辅助**：Python 从一个 Beta 分布抽 10000 个缺陷率，再条件 Bernoulli 生成零件/半成品/成品缺陷；只计算三个边际均值，未把结果传入附录中的 DP 主调用。
- **可视化后判断“影响小”**：只画一个固定决策的 \(\alpha/\beta\) 曲线，不重新比较 16 个策略，也不记录是否发生决策翻转。

没有实际供应商抽样结果、观测 \(k\)、外部生产批次或留出验证数据。

## 4. Models Used

### 单侧比例正态近似检验

**Purpose:** 在名义次品率 \(p_0=0.1\) 下给出批次接收/拒收规则。

**Inputs:** 样本量 \(n\)、样本次品比例 \(\bar X\)、显著性 \(\alpha\)。

**Outputs:** 两个情形的拒绝域与功效 \(K(n,p)\)。

**Why selected:** 作者认为样本量较大，可用样本比例的渐近正态性（pp.5–6）。

**Important assumptions:** 简单随机抽样；样本独立同分布 Bernoulli；正态近似在最终 \(n\) 与尾概率处足够准确。

**Key equations or mathematical structure:** 在 \(p_0=0.1\) 边界，

\[
Z=\frac{\sqrt n(\bar X-0.1)}{0.3}\approx N(0,1).
\]

情形(1)拒绝若

\[
\bar X>0.1+\frac{0.3u_{0.95}}{\sqrt n};
\]

情形(2)拒绝 \(H_0:p>0.1\)（即接收批次）若

\[
\bar X<0.1+\frac{0.3u_{0.1}}{\sqrt n}.
\]

**Implementation notes:** R 附录只实现情形(1)功效积分和 \(n=1\ldots1000\) 枚举；没有情形(2)独立代码，也没有输出整数次品数阈值。

### 功效—成本加权样本量选择

**Purpose:** 在检测数量和检验功效之间取折中。

**Inputs:** 单件检测成本 \(c\)、权重 \(w_1,w_2\)、功效函数、备择空间先验。

**Outputs:** \(n^*=43\)。

**Why selected:** 作者明确把样本量选择解释为成本与第二类错误之间的权衡（pp.5–7）。

**Important assumptions:** 备择参数服从 Uniform(0,1)；平均功效足以代表所有实际偏离；\(w_1=0.001,w_2=0.999\) 代表企业偏好；检测成本被归一为1。

**Key equations or mathematical structure:**

\[
q(n)=\int_{\Theta_1} f(p)K(n,p)\,dp,\qquad
g(n)=w_1cn-w_2q(n).
\]

代码枚举并**最小化** \(g(n)\)。

**Implementation notes:** 独立复算确认给定代码目标的 `argmin=43`。正文表1却写“最大化决策函数 \(g(n)\)”，与代码/成本含义矛盾。轻微改变 \(w_1\) 会显著改变 \(n\)：0.0005→68、0.001→43、0.002→27、0.005→15。

### 16策略解析期望利润

**Purpose:** 对问题二6种参数情形选择检测/拆解组合。

**Inputs:** 零件/装配次品率、采购/检测/装配/拆解/调换成本、售价。

**Outputs:** 16×6 期望利润表和每列最大策略。

**Why selected:** 仅4个二元决策，完整枚举可行；作者希望避免仿真误差（pp.3, 8）。

**Important assumptions:** 各零件与装配缺陷独立；检测无误；重复生产次数服从几何分布；不合格退换/拆解规则固定；回收零件可再次使用且不损耗。

**Key equations or mathematical structure:** 若检测零件 \(i\)，取得一个可用零件的次数 \(\xi_i\sim G(1-p_i)\)，\(E\xi_i=1/(1-p_i)\)。不检测时一次进入下一流程。成品成功次数也用几何分布。对拆解策略按首次缺陷来源分类后求全成本期望。

**Implementation notes:** 表4与表5的每列最大值闭合：18.84、12.00、16.47、14.75、14.96、21.68。R 附录把16个利润式直接硬编码，并未包含自动公式生成/单元测试。

### 状态—决策动态规划

**Purpose:** 处理8零件、3半成品、1成品的检测、装配和拆解决策。

**Inputs:** 各节点质量/检测状态、题设成本、次品率和动作集合。

**Outputs:** 声称的最优路径、56.7元期望利润。

**Why selected:** 解析枚举随工序/零件数量迅速膨胀，作者选择可记忆化的多阶段结构（pp.3, 14, 17）。

**Important assumptions:** 检测结果可正确更新质量；未检节点按 Bernoulli 次品率转移；最优子结构成立；回收价值等于部分采购/检测/装配成本；递归深度足够。

**Key equations or mathematical structure:**

\[
V(S_t)=\max_{a_t}\{R(S_t,a_t)-C(a_t)+E[V(S_{t+1})]\}.
\]

正文状态包含12个节点的检测/质量/拆解信息；成本包括采购、检测、两级装配与拆解，收益包括销售和回收。

**Implementation notes:** 附录 Python 与上述模型不一致且不可运行：所有 `defect_rate=0.1`，检测时用 `>=0.1` 确定为次品；没有 Bernoulli 分支/期望；8零件被一次 `all()` 当作一个半成品；成品合格直接复制半成品标志；未计采购成本、成品装配成本和调换损失；`parts` 被原地修改却不在 memo key；深度截断20；`initial_state` 与主求值 `max_profit=dynamic_programming(...)` 未定义/未调用。故56.7不能由所示代码复现。

### Beta 后验与利润积分

**Purpose:** 把问题四的次品率不确定性纳入问题二/三。

**Inputs:** Uniform prior Beta(1,1)、作者设定 \(n=100\)、名义率 \(p_0\)。

**Outputs:** Beta\((1+np_0,1+n-np_0)\)，16×6后验平均利润表；问题三54.2元。

**Why selected:** Beta 是 Bernoulli/Binomial 的共轭先验，可解析更新并数值积分（pp.18–19）。

**Important assumptions:** 用 \(k=np_0\) 可代表抽样结果；不同节点次品率相互独立；三个问题二次品率各自服从独立 Beta；名义率可作为后验 mode。

**Key equations or mathematical structure:**

\[
p\mid k\sim\mathrm{Beta}(1+k,1+n-k),\qquad k=np_0,
\]

\[
E[h(p_1,p_2,p_3)]
=\int_0^1\!\int_0^1\!\int_0^1h(p_1,p_2,p_3)\prod_{i=1}^3\phi_i(p_i)\,dp_1dp_2dp_3.
\]

**Implementation notes:** R `params_list` 固定 `n=100`，完全没有观测 \(k\)。例如 \(p_0=0.1\) 产生 Beta(11,91)，mode=0.1但均值=0.107843。表7/8最大值闭合；情况6最优 row012=20.36 仅比 row016=20.34 高0.02，决策对数值/先验并不“高稳定”。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 精确二项单侧检验 | not reported | 来料接收阈值 | not reported | not reported | 与正态近似的实际size/样本量对照 | 最终n=43并不很大；精确复算发现情形(1) size=6.07%>5%，应优先精确法 |
| 正态近似比例检验 | selected | 两种信度下接收/拒收 | 作者称n较大，可用渐近正态 | 理论推导 | 连续性修正、精确binomial对照 | 推导清楚，但尾概率控制未兑现 |
| 固定错误概率约束下最小n | not reported | 直接满足题意 | not reported | not reported | 功效目标点/OC曲线 | 论文改为主观加权平均功效，n依赖权重而非明确质量约束 |
| 功效—成本加权目标 | selected | 选择n | 平衡检测费与第二类错误 | R枚举n=1..1000 | 权重敏感性、企业成本标定 | 给定权重可复算，但不是唯一“最佳样本量” |
| 16策略解析枚举 | selected | 两零件流程 | 状态少，可严格求期望 | 16×6全表 | 仿真/递推交叉检查 | 是问题二合适且可审计的选择 |
| 直接解析枚举用于8零件流程 | rejected | 问题三 | 方案数太多、难推广 | not reported | 小实例对照 | 转向DP理由合理 |
| 随机动态规划 | selected in prose | 多工序检测/拆解 | 多阶段、重叠子问题和最优子结构 | 仅最终56.7 | 基线、状态计数、代码一致性、模拟验证 | 正文结构合理，但代码未实现，结果不可接受为已复现 |
| 固定次品率点估计 | selected in problem 2/3 | 基准决策 | 题设给定 | 后验版本决策对照 | 参数误差区间 | 作为基线合理 |
| Beta(1,1)后验积分 | selected | 问题四不确定性 | 共轭、无偏先验 | 表7与点估计表比较 | 实际观测数据、先验预测检验、其他先验 | 使用伪计数np0而非数据，只是围绕名义率平滑，不是真实更新 |

## 5. Model Pipeline

1. 把抽样比例写成正态近似单侧检验。
2. 将功效在备择空间积分，与检测数量线性加权，枚举得到 \(n=43\)。
3. 问题二按拆解与否分支，推导16个期望利润式并逐情形取最大。
4. 问题三把解析公式扩展为状态—决策递归，声称记忆化求56.7。
5. 问题四以 Beta(1,1)+伪计数 \(np_0\) 形成后验；三重积分重算问题二。
6. 对问题三只计算后验预测的边际缺陷概率，声称替换固定概率后得到54.2。
7. 对一个非最优策略分别改变 \(\alpha\) 或 \(\beta\)，据图宣称先验影响小。

三个接口断裂：问题一得到43而问题四代码用100；问题四没有实际抽样 \(k\)；问题三/四 Python 未把 posterior simulation 接到可运行 DP。

## 6. Model Improvements

- **小流程先做解析全枚举**：避免不必要的启发式算法，并保留每个成本项的解释。
- **从解析枚举升级到状态—决策框架**：在概念上能推广到更多工序/零件，且能表达检测后信息更新和回收决策。
- **用后验积分而非只代入后验点估计**：问题二 R 代码确实对三维利润函数积分，能反映非线性期望与 \(h(Ep)\) 的差别。
- **检查先验超参数**：至少意识到 Beta(1,1) 是主观选择；但实际只检查一个非最优策略，且 \(\alpha\) 变化不小。
- **记忆化搜索**：正文提出缓存状态价值；附录虽有 `memo`，但状态外的 `parts` 被原地改变，缓存键不充分，未实现可靠改进。

## 7. Parameter Estimation and Optimization

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| \(p_0\) | 标称次品率 | dimensionless | pp.2, 5 | 0.10 | problem-provided | N/A - given | no | 来料检验边界 |
| \(\alpha_1\) | 情形(1)显著性 | dimensionless | p.5 | 0.05 | problem-provided | confidence requirement | no | 精确binomial size复算为0.06067 |
| \(\alpha_2\) | 情形(2)显著性 | dimensionless | p.6 | 0.10 | problem-provided | confidence requirement | no | 精确binomial size复算0.06226 |
| \(w_1,w_2\) | 检测成本/平均功效权重 | dimensionless | p.7, p.25 code | 0.001, 0.999 | author-assumed | illustrative preference | no | 对n极敏感，未由企业成本标定 |
| \(c\) | 单件抽检成本归一系数 | normalized cost/sample | p.7; p.25 code | code等效为1 | author-assumed | normalization | no | 未给实际货币成本 |
| \(n^*\) | 问题一样本量 | count | p.7, p.25 | 43 | data-estimated | 枚举最小化加权目标 | partial | 只实现情形(1)；两情形是否共用未解释 |
| 整数拒绝阈值 | 情形(1)/情形(2)缺陷数阈值 | count | pp.5–6 formula | not reported | algorithm hyperparameter | should derive from continuous threshold | no | n=43时独立得情形1拒绝k≥8；情形2接收k≤1 |
| \(p_1,p_2,p_3\) | 零件1/2/装配次品率 | dimensionless | table4 code/题设 | six-case values | problem-provided | N/A - given | no | 问题二解析输入 |
| \(a_i,b_i,v,e,s,P\) | 采购/检测/装配/调换/拆解/售价 | 元/件 | pp.9–13, code | six-case values | problem-provided | N/A - given | no | 进入16个利润式 |
| 所有问题三未检次品率 | dimensionless | pp.14,17 | 0.1 | author-assumed | uniform node rate | no | 题设节点实际成本不同，统一率简化 |
| recursion depth | Python递归截断 | actions | p.29 code | 20 | algorithm hyperparameter | author setting | no | 正文只说“预设深度”，未说明20的充分性 |
| \(\alpha_0,\beta_0\) | Beta先验超参数 | dimensionless | pp.18,21 | baseline(1,1) | author-assumed | uniform prior | yes | 单独1..10扫描 |
| \(n_B\) | 问题四伪后验样本量 | count | p.33/p.34 code | 100 | author-assumed | hard-coded | no | 与问题一43不一致 |
| \(k\) | 后验“缺陷数” | count | pp.18–19, p.33 | \(np_0\) | author-assumed | expected count, not observed | no | 没有真实抽样；可为非整数 |
| trials | posterior predictive simulation | repetitions | p.34 code | 10000 | algorithm hyperparameter | author setting | no | 无seed/置信区间；只求边际均值 |

## 8. Validation

本文没有真实批次、外部生产数据、合成真值恢复或留出验证。问题二的主要证据是解析公式内部闭合；问题一和问题四可做理论/算术检查。问题三只有自报结果，且代码矛盾，因此不能视为已验证。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 问题一样本量目标 | L2 - independent objective recalculation | theoretical | argmin over n=1..1000 | 1 grid | 独立复算n=43 | 权重变化时大幅改变 | 只验证代码目标，不验证目标合理或检验size | 支持给定w/正态功效下的argmin |
| 情形(1)显著性控制 | L2 - exact binomial size check | theoretical | \(P_{0.1}(K\ge8)\) | exact | 0.06067 > 0.05 | nominal boundary | 正态近似无连续性修正 | 不能声称5% size得到控制 |
| 情形(2)显著性控制 | L2 - exact binomial size check | theoretical | \(P_{0.1}(K\le1)\) | exact | 0.06226 < 0.10 | none at boundary | 仅检查边界p=.1 | 支持边界size不超10% |
| 问题二每列最优策略 | L2 - exhaustive table reconciliation | same model | 16×6列最大值 | 96 evaluations | 表4/5最大值与策略一致 | none reported | 公式与R代码硬编码，缺独立实现 | 支持给定解析式/参数下的表内最大 |
| 问题三DP | not assessable | unknown | 期望利润/路径 | not reported | 自报56.7 | code cannot execute/model mismatch | 缺随机分支、主调用、基线、输出 | 现有证据不能支持56.7或“最优” |
| 问题四问题二后验积分 | L2 - exhaustive table reconciliation | same model | 16×6列最大值 | 96 integrals | 表7/8最大值闭合，情况6翻转 | case6 margin only 0.02 | 无观测数据；积分误差未报告 | 支持伪后验设定下表内比较 |
| 问题四问题三 | not assessable | unknown | 期望利润/路径 | not reported | 自报54.2 | code only computes marginal probabilities | 未展示把边际概率传入可运行DP | 不能支持54.2或稳定路径 |
| 先验超参数 | L3 - one-at-a-time prior perturbation | same model | one strategy expected profit | 10+10 points | α增大时约17.62→13.22；β增大约17.62→18.11 | α effect substantial | 检查的是非最优decision002，未重选16策略 | 只支持该函数的单因素曲线，不支持整体决策稳健 |

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| Beta prior \(\alpha_0\) | 1 (\(\beta_0=1\)) | 1–10 integer grid | one-at-a-time analytic integration | `h_func` expected profit | 独立解析复算17.622→13.222，下降约24.97% | not assessed | 影响并不“小”；代码函数对应decision002，不是情况1最优decision004 |
| Beta prior \(\beta_0\) | 1 (\(\alpha_0=1\)) | 1–10 integer grid | one-at-a-time analytic integration | same `h_func` | 17.622→18.111，上升约2.78% | not assessed | β影响较小，但只对单一非最优策略 |

在已审查范围内，未发现对问题一权重/检测成本、正态近似、问题二次品率/成本、问题三递归深度/状态编码、问题四伪样本量、积分容差或 posterior predictive trial 数的正式敏感性实验；审查覆盖正文 pp.1–23、附录 pp.24–36 及当前可用补充材料清单。独立权重复算显示 \(w_1\) 从0.0005到0.005时 \(n^*\) 从68降到15。

## 10. Visualization Strategy

- **生产流程图**（图1）：把8零件—3半成品—成品层级呈现清楚，是问题三状态设计的必要前置。
- **方案编码表**（表2）：四个二元决策映射到001–016，便于公式/代码/结果跨页索引。
- **完整利润矩阵 + 高亮最大值**（表4、7）：比只报最优策略更透明；问题四还用绿色标出与问题二不同的决策。
- **最终策略表**（表5、6、8、9）：把检测/拆解动作转为可执行清单。
- **先验曲线**（图2–3）：一维扫描直观，但缺具体数值、相对变化、策略翻转标记和多策略包络；图2实际变化约25%，与文字结论不符。
- **代码截图**（pp.25–36）：提高了可审计性，也暴露严重实现问题；但不能替代源文件、运行日志和测试。

## 11. Writing Structure

论文按四问逐级扩展：假设检验 → 小型解析决策 → 多阶段DP → Bayesian 不确定性。问题二从一个代表性拆解情形推到16个公式，再列全表，组织清晰。

主要写作/证据问题：

- 把作者示例权重产生的43写成“最佳样本量”，没有给企业成本口径和权重敏感性。
- 表1写“最大化 \(g(n)\)”而代码/公式需要最小化。
- 问题三正文数学结构远比附录实现完整，未进行公式—代码—结果一致性说明。
- 问题四称“通过抽样检测得到”，实际无观测样本，只用 \(np_0\) 伪计数。
- 先验敏感性文字称影响小，图2和独立复算显示 \(\alpha\) 影响接近25%；且代码不是最优策略。
- O*版本边界和官方/本地页数差异未在论文自身可解决，报告需持续保留。

## 12. Strengths

- 问题二完整枚举16个策略，推导、代码函数和结果表有统一编号，容易审计。
- 正确识别几何分布可计算重复采购/装配至合格的期望次数。
- 问题三正文尝试明确状态、动作、成本、收益和 Bellman 递归，而非只给“用DP”。
- 问题四对非线性利润做后验积分，而不是简单把名义率替换为一个点。
- 完整表格揭示情况6 Bayesian后决策翻转且margin仅0.02，为稳健性审计提供了材料。

## 13. Weaknesses

- 问题一没有使用精确二项检验；情形(1)实际size约6.07%，不满足5%要求。
- 样本量目标的权重/成本高度主观且未敏感性分析；两个情形是否应共用43也未说明。
- 问题三代码未实现正文的随机状态转移，缺多个成本项、分组逻辑和主调用，56.7不可复现。
- 问题四没有真实观测数据；Beta后验用预期计数 \(np_0\) 生成，且问题一/四样本量43/100不一致。
- 单次 Bernoulli 的 Beta 混合最终只由后验均值决定；论文又近似回 \(p_0\)，对问题三“传播不确定性”几乎退化为点概率。
- 敏感性代码检查非最优策略，且 \(\alpha\) 影响明显；没有重选策略或检查情况6的0.02 margin。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | 题设参数硬编码于pp.25–36；无实际抽样k或生产数据 | 问题二表可重建；Bayesian“数据”不可核验 |
| Code availability | partial | 6份代码仅以截图给出；独立 `.R/.py` 不可得 | 需人工转录；问题三缺初始化/主调用 |
| Dependency / environment information | partial | R `cubature`, `openxlsx`; Python NumPy/SciPy | 版本、解释器、容差、运行命令未报告 |
| Random seed | not reported | p.34 posterior predictive uses NumPy RNG | 10000次边际结果不可逐位复现 |
| Hard-coded constants | extensive | 16个利润函数、6个参数列表、n=100、率/成本全部硬编码 | 公式变更易与表/代码失配 |
| Formula-to-code consistency | contradicted for problem 3; partial otherwise | 核对pp.4–22与pp.25–36 | 问题1 min/max文字冲突；问题2大体一致；问题3随机DP未实现；问题4只部分连接 |
| Code-to-result consistency | partial / not assessable | n=43和两张16×6表可核；56.7/54.2不可核 | 问题三代码无法运行，问题四问题三代码未调用DP |
| Overall reproducibility | partially reproducible | 问题1目标与问题2/4积分可重建 | 多工序核心结果和灵敏度结论存在阻断性代码问题 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 样本量argmin | \(n=43\) | 重写p.25目标并枚举1..1000，最小值在43 | pass | pp.7,25 equation/code | 仅验证给定w与情形1 |
| 决策函数方向 | 表1“最大化g(n)” | g=成本−效果，p.25使用`min/which.min` | fail (text) | pp.7,25 table/code | 应为最小化 |
| 情形1整数阈值/size | 正态近似控制5% | n=43阈值7.5358件→拒绝k≥8；精确Bin(43,.1)尾概率0.060669 | fail | p.5 rejection region | 无连续性修正 |
| 情形2整数阈值/size | 控制10% | n=43阈值1.7789件→接收k≤1；精确概率0.062257 | pass | p.6 rejection region | 边界p=.1 |
| 权重敏感性 | 权重为示例0.001/0.999 | w1=.0005/.001/.002/.005对应n=68/43/27/15 | concern | pp.7,25 objective | 论文自己承认主观但未量化 |
| 问题二列最大值 | 表5六个终值 | 逐列核表4：18.84/12/16.47/14.75/14.96/21.68 | pass | p.13 tables 4–5 | 高亮与终表一致 |
| 伪后验均值 | p0=.1,n=100 | Beta(11,91) mode=.1，mean=11/102=.107843 | concern | pp.18–19,33–34 | 无实际k；后验预测不等于p0 |
| 问题四列最大值 | 表8六个终值 | 表7逐列最大闭合；case6 row01220.36>row01620.34 | pass / concern | pp.19–20 tables 7–8 | case6 margin仅0.02，稳定性弱 |
| α先验敏感性 | “影响不大” | 按p.35函数精确期望17.622→13.222，降24.97% | fail (interpretation) | pp.21–22 figures; p.35 code | 并非小影响 |
| β先验敏感性 | “影响不大” | 同函数17.622→18.111，升2.78% | pass (bounded) | pp.21–22 figures; pp.35–36 code | 只对单一策略 |
| 灵敏度对象 | 称情况1最优策略 | p.35 `h_func`在α=β=1给17.62，对应表7 decision002；case1最优decision004=18.18 | fail | pp.20–22 tables/paragraph; p.35 code | 没有检查最优策略 |
| 检测后质量代码 | 随机Bernoulli(p=.1) | p.29用`defect_rate >= 0.1`；8个率均0.1，故全部判次品 | fail | pp.17,28–29 prose/code | 与状态转移模型直接矛盾 |
| 问题三成本覆盖 | 正文含采购、检测、两级装配、拆解、调换 | p.29–30代码不扣采购/成品装配/调换，且回收用采购成本作收益 | fail | pp.15–17 vs pp.29–30 | 无法产生正文目标 |
| 问题三可执行性 | 自报56.7 | 附录未定义`initial_state`/`max_profit`主调用；状态外parts被原地修改 | fail | pp.28–30 code | 原样不能运行/缓存键无效 |
| 问题四问题三接口 | 自报54.2 | p.34仅输出三类边际概率，未调用问题三DP | not assessable | pp.21,34 code | 关键接口缺失 |
| OCR兼容副本等价 | 临时重写仅为解析兼容 | 36/36页100DPI RGB渲染逐像素相同 | pass | extraction QA | 源PDF未改；报告哈希锚定原件 |

## 14. Reusable Techniques

### 小决策空间的解析全枚举

**When useful:** 二元决策不超过4–6个，成本结构可解析。

**Why useful:** 可保留全部备选、利润差和边界策略，避免启发式“最好解”。

**Limitations:** 公式硬编码易错；应由统一函数生成并用仿真/单元测试交叉核对。

### 用几何分布核算“直到合格”的重复成本

**When useful:** 每次生产独立同分布，失败后流程同分布重启。

**Why useful:** \(E[N]=1/q\) 可把采购、检测、装配、退换成本直接转为单件合格品期望。

**Limitations:** 回收零件、状态依赖质量或重复使用会破坏简单重启结构，需要 Markov/renewal 状态模型。

### 后验积分重算非线性决策值

**When useful:** 已有真实抽样 \((n,k)\)，利润对次品率非线性。

**Why useful:** \(E[h(p)]\) 比 \(h(Ep)\) 保留更多不确定性，能发现小利润margin下的决策翻转。

**Limitations:** 必须使用真实k并报告先验/后验；伪计数np0不是数据；多节点共享不确定性时要保留相关性。

### Bellman状态—决策建模模板

**When useful:** 多工序、检测后信息更新、回收/拆解可循环。

**Why useful:** 把检测、质量、拆解状态与未来价值统一在 \(R-C+EV\) 中。

**Limitations:** 实现必须真正分支随机结果，状态键要包含所有可变信息，并有终止性/小实例验证；本文代码未达到此标准。

### 精确检验优先于渐近检验

**When useful:** Bernoulli比例、n仅几十、尾概率决定接收/拒收。

**Why useful:** 直接控制实际size，并给整数缺陷数阈值，避免连续正态阈值落在错误尾概率。

**Limitations:** 离散性使名义α未必恰好达到；可用随机化检验或选择保守阈值。

## 15. Competition Takeaways

1. 比例抽检先给精确二项整数阈值和实际size，再考虑正态近似是否足够。
2. “成本—功效”权重必须有企业货币解释，并报告权重变化下样本量，不把示例权重写成唯一最优。
3. 小决策空间保留全表及利润margin；margin仅0.02时必须做积分误差/参数稳健性。
4. Bayesian 更新必须使用真实 \(k\)，不能用 \(np_0\) 伪造观测；明确 posterior mode、mean 和 predictive 的区别。
5. 动态规划正文、状态转移代码和结果必须用小实例逐项对照；确定性阈值不能冒充Bernoulli期望。
6. 记忆化键必须覆盖所有被修改对象；避免状态外可变全局数据和深度依赖价值。
7. 灵敏度必须检查真正的最优策略并记录是否翻转，不能只画一个非最优公式后概括整体稳健。
8. 支撑代码交付可执行源文件、依赖和运行日志；截图只适合审阅，不足以复现。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 问题一建立两组相反单侧假设 | explicit | 5–6 | §5.1–5.2 | equations/paragraphs | notation normalization | N/A | p0=.1，α=.05/.1 |
| 正态近似拒绝域与功效函数 | explicit | 5–7 | §5.1–5.3 | equations | notation normalization | N/A | 公式视觉核验 |
| 权重0.001/0.999时报告n=43 | explicit | 7 | §5.3 | paragraph | direct transcription | N/A | R代码仅情形1 |
| 给定代码目标独立枚举的argmin为43 | interpretation | 25 | appendix 1 | code | independent calculation | N/A | n=1..1000 |
| 表1写最大化g而代码最小化 | criticism | 7,25 | §5.4 / appendix 1 | table/code | direct transcription | N/A | 成本−功效也应最小化 |
| 情形1精确size为0.060669，超过0.05 | criticism | 5 | §5.1 | rejection equation | independent calculation | N/A | n=43,k≥8 |
| 情形2精确size为0.062257，不超过0.10 | interpretation | 6 | §5.2 | rejection equation | independent calculation | N/A | n=43,k≤1 |
| n对权重高度敏感 | criticism | 7,25 | §5.3 / appendix 1 | objective/code | independent calculation | N/A | w1=.0005/.001/.002/.005→68/43/27/15 |
| 问题二枚举16种检测/拆解决策 | explicit | 8 | §6 | table 2 | direct transcription | N/A | 四个二元变量 |
| 几何分布用于重复生产至合格 | explicit | 9–11 | §6.1–6.2 | equations | notation normalization | N/A | 独立假设为关键边界 |
| 16个利润公式列于表3 | explicit | 11–12 | §6.3 | table 3 | direct transcription | N/A | 附录R硬编码 |
| 问题二六列最优终值闭合 | interpretation | 13 | §6.4 | tables 4–5 | independent calculation | N/A | 逐列max复核 |
| 问题三正文定义12节点状态和Bellman目标 | explicit | 14–18 | §7.1–7.5 | equations/paragraphs | notation normalization | N/A | 描述随机质量状态 |
| 问题三自报全检测/缺陷拆解与56.7元 | explicit | 18 | §7.5.4 | table 6/paragraph | direct transcription | N/A | 无独立输出 |
| p.29检测代码把rate>=.1确定为次品 | criticism | 28–29 | appendix 3 | code | direct transcription | N/A | 8个rate均.1，因此全为次品 |
| 问题三代码未实现3个半成品分组与随机装配缺陷 | criticism | 29 | appendix 3 | code | derived interpretation | N/A | `all(parts)`和布尔复制 |
| 问题三代码遗漏多项正文成本 | criticism | 15–17,29–30 | §7.2–7.4 / appendix 3 | equations/code | derived interpretation | N/A | 无采购、成品装配、调换成本 |
| 问题三代码缺initial_state和max_profit主调用 | criticism | 28–30 | appendix 3 | code | direct transcription | N/A | 原样不可运行 |
| 状态外parts原地修改使memo key不充分 | criticism | 29–30 | appendix 3 | code | derived interpretation | N/A | 缓存只用state.items() |
| 在已审查范围内无法复现56.7 | criticism | 1–36 | full paper | none found | derived interpretation | 正文、附录、全部可用代码和补充材料清单均审查 | 独立源文件/输出不可得 |
| 问题四使用Beta(1,1)共轭后验 | explicit | 18–19 | §8.1–8.2 | equations | notation normalization | N/A | 理论形式正确 |
| 实际代码以k=np0和n=100构造后验 | explicit | 33–34 | appendix 4–5 | code | direct transcription | N/A | 没有观测数据 |
| p0=.1伪后验Beta(11,91)均值0.107843 | criticism | 18–19,33–34 | §8.1 / appendix | equation/code | independent calculation | N/A | mode=.1不等于mean |
| 问题四问题二表仅情况6翻转 | explicit | 20 | §8.2 | tables 7–8/paragraph | direct transcription | N/A | row012与row016差0.02 |
| 问题四问题三自报54.2 | explicit | 21 | §8.3 | table 9/paragraph | direct transcription | N/A | 代码接口缺失 |
| 附录5只模拟并输出三类边际概率 | criticism | 34 | appendix 5 | code | direct transcription | N/A | 未调用问题三DP |
| 在已审查范围内无法复现54.2 | criticism | 1–36 | full paper | none found | derived interpretation | 正文pp.1–23、附录pp.24–36及可用支撑清单均审查 | 源py/输出不可得 |
| α/β先验扫描范围各为1..10 | explicit | 21–22,35–36 | §9 / appendix 6 | figures/code | direct transcription | N/A | 单因素扫描 |
| α扫描利润约下降24.97% | criticism | 22,35 | §9.1 / appendix 6 | figure/code | independent calculation | N/A | 与“影响不大”矛盾 |
| 灵敏度代码对应decision002而非情况1最优004 | criticism | 19–22,35 | §8.2–9 / appendix 6 | tables/code | independent calculation | N/A | baseline17.62对表7 row002 |
| 没有外部真实验证、实际抽样k或预测区间 | criticism | 1–36 | full paper | none found | derived interpretation | 主文、验证/灵敏度、附录代码和可用补充材料均审查 | 最高为L3同模型先验扰动 |
| OCR临时兼容副本与原件36页渲染完全一致 | interpretation | 1–36 | extraction QA | figure/page renders | independent calculation | N/A | 100DPI逐像素；源hash仍为bced...45112 |
| 本地36页与官方展示前36页内容一致，官方第37页为空白 | interpretation | 1,18,36 | version review | figure/page renders | independent calculation | N/A | 检查首页、摘要、代表中页、末页和官方空白尾页；provenance由O*更新为O，奖级仍未知 |
