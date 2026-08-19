# Paper: 基于混合效应模型的 NIPT 时点优化与胎儿异常判定

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_7af07fbe49ce
- Year: 2025
- Problem: C
- Award: 组委会官方展示已核验；具体奖项等级未核验
- Provenance tier: O*（入选时版本待核；本次确认本地 28 页覆盖官方主文 1–28 页，官方另有 29–122 页代码附录；按 O 的官方展示边界使用，不据此推断奖级）
- Source file: literature/raw_papers/2025/C023.pdf
- Source URL: unknown（Yao 提供的本地历史论文合集副本）
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025ctlw/251101/2022736.shtml
- Pages: 28（本地 PDF）；官方展示记录 122 张页图
- SHA-256: 19eba37bee16f7a8089abd5435073c24c9633987a08f044fb312490950681949
- Extraction method: Tesseract 5.5.0 `chi_sim+eng` OCR fallback（250 DPI，PSM 3）+ 原页视觉复核；因原件 pypdf Boolean 解析失败，使用 28 页 Ghostscript 临时兼容副本作渲染输入，100 DPI 下与原件 28/28 页逐像素一致
- Extraction quality: OCR 成功，28/28 页无 page error，27 页达到至少 30 个非空白字符；物理第 25 页主要是图，OCR 稀疏但视觉可读；公式、表格和代码不以 OCR 单独定案
- Page convention: 1-based physical PDF pages；本地物理页 1–8 对应官方页 1–8，9–27 对应官方页 10–28，本地物理页 28 对应官方页 9；“official pXX”专指官方展示页图
- Visually checked pages: 本地全部物理页 1–28；重点放大核对物理页 1–2、5–17、19–22、24–28 的公式、表 1–10、图 4–15 与代码入口；官方页 1–2、9、14–15、28–30、60–61、75、93–94、100–101、110、120–122
- Unresolved extraction ambiguities: 原件无法由 pypdf 解析但 Poppler/`pdfinfo` 可稳定读取；本地页序重排已映射；OCR 对上下标、希腊字母和代码标点有误识别，关键对象均回看页图；官方 snapshot 的 `list_item.extendjson` 有 122 页而 `article.list` 仅 100 页，末 22 页通过前者核验
- Supplemental artifacts: 官方展示页 29–122 提供 `q1.py`、`q2.py`、`q3.py`、`q4.py` 的代码页图；本地 PDF 仅在物理页 27 露出代码前三行；未取得可执行 `.py` 文件、`附件.xlsx`、运行日志或结果目录

## 1. Problem Archetype

这是一个“纵向统计建模 → 阈值达标概率 → 分组决策优化 → 多重检验判别”的混合原型：

- 男胎部分是重复测量的统计模型。响应为胎儿 Y 染色体浓度（文中记作 FF），核心解释变量为孕周（gestational age, GA）和身体质量指数（body mass index, BMI）。
- 问题二、三把 `Pr(FF >= 0.04)` 转化为最早达标时点，再用单调曲线和分段策略产生可执行的 BMI 分组。
- 女胎部分以男胎样本建立协变量校正后的经验零分布，对 13、18、21 号染色体信号做标准化、Benjamini–Hochberg（BH）校正和重复检测一致性聚合。

它同时涉及统计模型、优化、多重检验和临床决策。论文输出只能解释为基于给定数据的筛查/推荐规则；没有独立临床结局验证，不能解释为已验证的诊断工具。

## 2. Problem Decomposition

论文分四条任务链：

1. 对男胎 1082 条观测、267 名孕妇建立 logit(FF) 线性混合效应模型（linear mixed-effects model, LMM），加入 GA/BMI 二次项和孕妇随机截距、随机 GA 斜率。
2. 在 BMI 网格上求 `Pr(FF >= 4%) >= q` 的最早孕周，以单调回归平滑，再用动态规划/台阶化给出有限组推荐。
3. 加入年龄、怀孕次数、生产次数，重复“达标曲线 → 单调化 → 分段”过程并做误差缩放实验。
4. 对女胎按孕周层和染色体分层，以男胎回归残差构造零分布，计算标准化分数和 BH `q` 值，再按阈值与至少两次同号命中聚合为阴性、可疑、阳性。

主线衔接是清楚的，但正文的风险约束、协变量筛选、ChrX 质控和交叉验证并未全部进入官方代码。

## 3. Data Processing

男胎问题一报告有效观测 `N=1082`、孕妇 `267` 名，平均每人约 `4.05` 次测量；FF 均值/标准差为 `0.0772/0.0335`，GA 为 `16.85/4.08` 周，BMI 为 `32.29/2.97 kg/m²`。同一孕妇多次检测使普通独立回归假设不适用，这是选择 LMM 的合理动机。

正文把 `(0,1)` 内的 FF 做 logit 变换，并中心化 GA、BMI；二维热力图用于提示非线性。官方 `q2.py` 还会解析“周+天”、把百分数转为比例、删除 FF/GA/BMI 缺失及不在 `(0,1)` 的 FF。论文没有报告各清洗步骤删除了多少行、缺失机制或异常点对结果的影响。

问题四按 `Early <=14`、`Mid 14–22`、`Late >22` 分层；官方 `q4.py` 对男胎回归残差做 1% Winsorize，以中位数和 `1.4826*MAD` 估计位置尺度，21 号染色体可用 Student-t 零分布。代码在层内男胎少于 25 条时退回全部男胎样本，但正文没有说明这一跨层回退。代码也没有筛出经临床证实的“男胎阴性对照”，而是直接使用相应男胎表，零分布纯净性不可确认。

## 4. Models Used

### 二次项线性混合效应模型

**Purpose:** 描述 FF 随 GA、BMI 的群体趋势并处理孕妇内重复测量。

**Inputs:** logit(FF)、中心化 GA/BMI、孕妇 ID。

**Outputs:** 固定效应、随机截距/斜率、方差分量、FF 达标概率。

**Why selected:** 论文明确以重复测量相关性和热力图非线性为理由；表 2 与 GLM 比较 AIC、对数似然、R²、RMSE、MASE。

**Important assumptions:** 变换后残差正态；随机效应正态；二次均值结构充分；个体间独立；给定协变量后缺失/测量过程不会系统改变结论。

**Key equations or mathematical structure:** `logit(FF_ij)=β0+β1 GA_c+β2 GA_c²+β3 BMI_c+β4 BMI_c²+u_i+b_i GA_c+ε_ij`。

**Implementation notes:** 正文写 REML 目标，官方 `q2.py`/`q3.py` 实际调用 `MixedLM.fit(reml=False, method="lbfgs")`，即 ML。

### 达标概率、单调回归与 BMI 台阶化

**Purpose:** 求每个 BMI 的最早达标周并转换为少量临床分组。

**Inputs:** LMM 固定/随机效应方差、FF 阈值 0.04、保障水平 `q`、BMI/孕周网格、误差倍率 `κ`。

**Outputs:** `T*(BMI)`、单调曲线、分组边界与推荐孕周。

**Why selected:** 作者希望把连续统计预测变成“安全、及时、可执行”的分段策略。

**Important assumptions:** 推荐孕周随 BMI 单调不减；时间风险和技术失败风险可加；网格上结果可代表连续人群；误差仅通过方差倍率表达。

**Key equations or mathematical structure:** 最早 `Pr(FF>=0.04)>=q` 的时点；正文给出带硬保障率约束的分段风险最小化与 `DP[j,s]`。

**Implementation notes:** `q2.py` 默认 `guarantee-mode=typical`，概率只含残差方差，不含新孕妇随机效应；其台阶化代码用段内单调曲线中位数和失败/时间代价，没有实现正文式 (15) 的硬约束。

### 多因素扩展模型

**Purpose:** 加入年龄、怀孕次数、生产次数并调整推荐时点。

**Inputs:** 问题一变量加 AGE、G、P。

**Outputs:** 协变量条件下的达标曲线、BMI 分段和误差敏感性结果。

**Why selected:** 作者认为单一 BMI 无法表示个体差异。

**Important assumptions:** 额外协变量线性可加；作者给定的方向约束符合临床机制。

**Key equations or mathematical structure:** 扩展固定效应 LMM；正文式 (22) 为风险与偏移正则项的联合目标。

**Implementation notes:** 官方 `q3.py` 直接加入可识别的 AGE/G/P；未实现正文所称 Elastic-Net 筛选。其所谓 DP 最小化 `T*(BMI)` 的段内平方误差，不是式 (22) 的风险目标。

### 男胎经验零分布与女胎多重检验

**Purpose:** 校正 GA/BMI/测序质量后判定女胎 13/18/21 号染色体异常候选。

**Inputs:** 男/女胎 Z 值、GA、BMI、读段/比对/重复/GC/批次特征、受试者 ID。

**Outputs:** 层内标准化残差、p/q 值、样本级和受试者级三级标签。

**Why selected:** 作者希望控制协变量、厚尾和多重检验影响，并利用重复检测一致性降低偶然命中。

**Important assumptions:** 男胎数据可代表各常染色体零分布；线性协变量校正充分；层内残差分布可由正态或 t 分布描述；同一人的重复记录足以支持一致性规则。

**Key equations or mathematical structure:** 男胎 OLS 残差稳健标准化；双侧 p 值；层内 BH；`|z|`、`q` 与至少 `k=2` 次同号命中。

**Implementation notes:** 官方代码未使用 ChrX；阈值网格的“male pseudo-FPR”在拟合零分布的同一男胎样本上计算，且男胎规则不检查同号、女胎规则检查同号。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 随机截距+随机斜率+二次项 LMM | selected | FF 纵向关系 | 重复测量、个体异质性和非线性 | 表 2 AIC/LL/R²/RMSE/MASE；表 3 LR | GLM 的精确族/链接和参数数未说明；无独立预测比较 | 选择动机合理，但表 2 的 GLM R² 与 RMSE/FF 标准差不闭合 |
| GLM | rejected | 问题一基线 | 拟合指标较差 | 表 2 | 模型定义、是否同一响应尺度和诊断 not reported | 只能支持样本内比较，不能支持泛化优势 |
| PyMC 单调模型 | selected，失败时回退 | 平滑 `T*(BMI)` | 单调先验符合高 BMI 后移逻辑 | 正文置信带；代码 ADVI/NUTS | 未报告实际运行走 PyMC 还是回退 PAVA | 两路径可能给出不同结果，运行 provenance 缺失 |
| PAVA 等距回归 | fallback | 单调化 | PyMC 不可用时保证可运行 | 官方代码 | 与 PyMC 的同数据比较 not reported | 是合理工程回退，但不能与“贝叶斯置信带”混称 |
| 正态经验零分布 | selected for Chr13/18 | 女胎残差标准化 | 作者称这两条尾部较常规 | not reported | 拟合优度、尾部校准、外部阴性标签缺失 | 分布选择证据不足 |
| Student-t 经验零分布 | selected for Chr21 | 处理厚尾 | 作者称 Chr21 厚尾 | 代码可拟合自由度 | 无留出校准、无与正态的定量比较 | 可缓解厚尾，但同样本拟合与阈值选择会乐观 |

## 5. Model Pipeline

主干为：

`原始重复检测 → 清洗/变换 → LMM → FF 达标概率 → 单调最早时点曲线 → BMI 台阶化 → κ 敏感性`。

问题三在 LMM 固定效应加入 AGE/G/P；问题四另走：

`男胎层内回归校准 → 稳健残差零分布 → 女胎标准化 → 层内 BH → 样本阈值 → 受试者一致性聚合`。

正文结构把统计不确定性接到决策输出，这是优点；但代码默认“typical”概率只传播残差，分段又没有硬保障约束，统计模型到优化模型的接口没有完全按正文实现。问题四的网格选择也没有在同一运行中自动回填阈值后重算最终标签。

## 6. Model Improvements

- 相对普通回归，随机截距/斜率直接针对重复测量相关性；样本内拟合指标支持 LMM 更贴合现有数据，但没有受试者级留出验证。
- 二次项用于表示 GA/BMI 非线性；GA 与 BMI 二次项显著，但正文平均边际效应公式遗漏二次导数项。
- 对 `T*(BMI)` 加单调约束和上包络，减少局部反向波动；这是可执行性改进，不等于概率校准改进。
- 问题三加入 AGE/G/P，方向可解释；没有 Elastic-Net、显著性表或独立验证支撑“筛选后稳健”。
- 问题四加入稳健尺度、t 尾部、BH 和重复一致性；这些是合理防护层，但 male pseudo-FPR 与 female 决策规则不同，且没有临床真值，不能支持检出性能或临床适用性。

## 7. Parameter Estimation and Optimization

LMM 以 ML 代码拟合，固定效应包括 GA/BMI 一次与二次项，随机效应为孕妇截距和 GA 斜率。问题二在 GA `[10,28]` 和 BMI 步长 `0.1` 网格上求达标时点，默认 FF 阈值 `0.04`、`q=0.95`、五段、时间惩罚 `α=0.02`、`β=0.12`。PyMC 路径默认 ADVI 10000/12000 步及后验抽样，失败可退回 PAVA。

正文把问题二写成有硬保障率、单调和执行域约束的风险优化；代码实质是先构造 `T*(BMI)`，再以中位数候选时点和惩罚项分段。问题三代码以 L2 段内误差台阶化，不求正文式 (22)。因此正文的“全局风险最小”不能从附录实现推出。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| `N`, subjects | 男胎观测/孕妇数 | count | 物理 p5 表 1 | 1082 / 267 | data-estimated | 清洗后计数 | no | 删除量与缺失机制 not reported |
| `θ` | FF 临床达标阈值 | proportion | 物理 p9、正文式 (12) | 0.04 | problem-provided | 给定 | no | 论文称经验阈值；未传播阈值本身不确定性 |
| `q` | 达标概率保障水平 | dimensionless | 物理 p9–13 | 0.95；敏感性另用 0.98 | author-assumed | 固定阈值 | yes | 与问题四 BH `q` 值同符号但语义不同 |
| `K` | BMI 分段数 | count | 物理 p10–13 | 5 | author-assumed | 目标段数/惩罚二分搜索 | partial | 未比较执行成本与段数的稳定区间 |
| GA grid | 候选孕周 | week | 物理 p11；official p51–53 | 10–28，步长 0.1 | algorithm hyperparameter | 离散搜索+二分 | no | 正文时点约束又写 `[12,28]`，实现搜索从 10 开始 |
| BMI grid | 分段自变量网格 | kg/m² | 物理 p11；official p51–53 | 样本范围，步长 0.1 | algorithm hyperparameter | 等距离散 | no | 结果依赖端点和网格 |
| `κ` | 检测误差标准差倍率 | dimensionless | 物理 p13–17 | 0.75, 1.00, 1.25, 1.50 | author-assumed | 放缩残差方差 | yes | 默认 typical 模式不放缩/传播个体随机效应 |
| `α, β` | 时间风险斜率 | risk/week | 物理 p10；official p41、p63 | 0.02, 0.12（代码默认） | author-assumed | 硬编码 | no | q2 与 q3 的时间风险定义方向不一致 |
| `λ` | 分段数惩罚 | risk | 正文式 (14)，official p51–55 | 搜索区间默认 0–0.05 | algorithm hyperparameter | 二分到目标段数 | no | 固定 `K` 时正文称可取 0，代码仍以 λ 找 K |
| PyMC seed/draws | 单调曲线随机设置 | N/A | official p38–40、p51–53、p72–74、p82 | q2 seed 2025/draws 1500；q3 seed 42/draws 1000 | algorithm hyperparameter | ADVI 或 NUTS | no | 实际使用路径与收敛诊断 not reported |
| AGE/G/P coefficients | 年龄/孕次/产次偏效应 | week or logit-scale per unit | 物理 p15–17 | 推荐时点效应 -0.065/-0.057/+0.039 周/单位（作者报告） | data-estimated | 扩展 LMM 后解释 | partial | 未给系数标准误/显著性；年龄分层表方向冲突 |
| `z_thr` | 女胎标准化阈值 | dimensionless | 物理 p19–20 | 2.6（正文）；代码默认 3.0 | author-assumed | 男胎 pseudo-FPR 网格 | partial | typical CLI 只输出 best 表，不自动回填重算 |
| `q_thr` | BH 校正阈值 | dimensionless | 物理 p19–20 | 0.05 | author-assumed | 固定/网格 | partial | 层内 FDR 不等于整体临床 FPR |
| `k` | 同号重复命中数 | count | 物理 p19–20 | 2 | author-assumed | 网格候选 2/3 | partial | 男胎 pseudo-FPR 代码不检查同号，规则不一致 |
| Winsorize | 男胎残差截尾比例 | proportion per tail | 物理 p19；official p104、p115 | 0.01 | algorithm hyperparameter | 分位数截尾 | no | 对尾部检验影响未量化 |
| GA bins | 问题四孕周层 | week | 物理 p18–19；official p115 | `<=14`, `14–22`, `>22` | author-assumed | 固定分层 | no | 边界 14 同时属于前两段，代码按首个匹配归 Early |
| minimum bin n | 男胎层内最小样本量 | count | official p103–104、p121 | 25 | algorithm hyperparameter | 不足则回退全部男胎 | no | 跨层回退改变零分布但正文未披露 |

## 8. Validation

论文最强证据是现有样本内拟合、LR 结构比较和单因素误差扰动。表 2 报告 LMM `R²=0.8962, RMSE=0.0108`，表 3 报告随机斜率 `LR=109.44`、二次项 `LR=41.29`。这些支持现有样本内结构更贴合，但不是对新孕妇的预测验证。

摘要称有交叉验证，正文未给折数、受试者级划分、指标或结果，四份官方代码也没有交叉验证实现。问题四的 3 阳性、26 可疑、118 阴性只是模型输出分布；没有临床真值，不能计算灵敏度、特异度或真实检出率。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 问题一 LMM 拟合 | L1 — 样本内拟合 | same sample | R²/RMSE/MASE/AIC | 1 | 0.8962/0.0108/0.322/712.63 | GLM 表内 R² 不闭合 | 无受试者级留出；重复记录可能放大随机效应后的拟合优势 | 仅支持该样本上 LMM 拟合较好 |
| 随机斜率/二次项 | L2 — LR 结构检查 | same sample | LR/p | 1 | 109.44、41.29；p 很小 | 检验实现/自由度 not reported | ML/REML叙述不一致；无外部预测增益 | 支持保留结构，不支持临床泛化 |
| 问题二误差倍率 | L3 — 单因素扰动 | same sample | 平均推荐孕周/分段数 | 8 scenarios | 表 5/6 | `q=.95, κ=.75` 比基线更晚；硬保障率失效 | ADVI/分段共同变化，无重复误差条 | 说明输出对 κ 敏感，不能证明稳健 |
| 问题三误差倍率 | L3 — 单因素扰动 | same sample | 平均推荐孕周 | 4 scenarios | 20.20–23.71 周 | 三个相对变化均算术错误 | 未联合扰动协变量/阈值 | 只支持噪声增大时点后移的方向 |
| 问题四阈值网格 | L1 — 同样本 pseudo-FPR | same sample | male pseudo-FPR、女胎阳性数 | one grid | 作者选 `z=2.6,q=.05,k=2` | 男/女聚合规则不同 | 校准与评估复用男胎；女胎无真值；选择利用女胎阳性数 | 只能作内部阈值筛选 |
| 女胎三级结果 | L2 — 计数闭合 | same sample | 计数/比例 | 1 | 118/26/3，共147 | 无临床真值 | 不是诊断准确率或外部验证 | 仅说明规则如何分配本数据 |
| 摘要所称交叉验证 | not assessable | unknown | not reported | not reported | not reported | 协议、分组、指标、结果均不可见 | 正文 1–28 页和官方代码 29–122 页均未给实现 | 不可作为验证证据 |

## 9. Sensitivity and Robustness

论文实际改变了 `κ` 和问题二保障水平 `q`，属于 L3 扰动证据。问题二表 5/6 在 `q=.95` 下，`κ=0.75/1/1.25/1.5` 的平均推荐周为 `18.44/17.08/17.73/19.67`；低噪声反而比基线晚 1.36 周，和“噪声越大越晚”的无条件叙述不符。问题三表 8 的平均值随 κ 单调增加，但相对变化栏整体算错 1 周。

分组边界“稳定”的判断也受表 4 区间重叠和代码分段目标不一致限制。没有对 FF 阈值、时间风险斜率、段数、网格步长、PyMC/PAVA 路径、零分布族或 q4 分层边界做联合敏感性分析。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 问题二 `κ` at `q=.95` | 1.00 | 0.75–1.50 | four-point grid | 加权平均推荐周 | 18.44, 17.08, 17.73, 19.67 | unclear | 大噪声总体后移，但低噪声场景非单调，不能概括为全区间单调 |
| 问题二 `q` | 0.95 | 0.95 vs 0.98 | two levels × κ grid | 平均推荐周 | κ=1 时 17.08→18.62 | no for direction | 更高保障导致更晚，只有两个 q 水平 |
| 问题三 `κ` | 1.00 | 0.75–1.50 | four-point grid | 平均推荐周 | 20.20, 21.67, 23.17, 23.71 | no for direction | 方向单调；相对变化列错误，且无随机重复区间 |
| AGE/G/P 单位变化 | sample medians | 每项 +1 单位 | coefficient interpretation | 推荐周变化 | -0.065, -0.057, +0.039 周 | contradicted for AGE | 年龄分层表在相近 BMI 下显示年龄更大明显更晚；未隔离其他变量 |
| 女胎阈值网格 | z=2.6, q=.05, k=2 | z 2.6–3.2；q .03/.05/.08；k 2/3 | finite grid | 同样本 pseudo-FPR、阳性数 | 具体完整表未随论文提供 | unknown | 可见代码但无运行表；规则和数据独立性限制结论 |

## 10. Visualization Strategy

论文使用：GA–BMI–FF 热力图展示非线性；不同 BMI/孕周下的 LMM 群体平均曲线及 95% 区间；连续 `T*(BMI)` 与台阶策略对照；年龄分层表；女胎各染色体标签柱图、首次命中周箱图和 GA–`|z|` 散点；附录还展示交互网页。

这些图覆盖了“探索 → 拟合 → 决策 → 判别”链条。风险是部分图只展示模型生成结果，没有真实标签或预测误差；置信带来源也取决于实际是否运行 PyMC，运行日志缺失使区间 provenance 不完整。

## 11. Writing Structure

正文按四问逐步展开，每问大体采用“问题分析—数据/模型—求解—结果—敏感性/结论”，附录列数据、网页、异常个体和代码，阅读路径清晰。公式编号、表格和流程图使模型接口可定位。

主要写作问题是结论强于证据：把样本内 pseudo-FPR 写成“FPR 控制”，把无真值标签分配写成临床适用性，把有限网格/分段实现写成全局风险最小；表 5/6 重复、表 4 区间矛盾和表 8 算术错误也削弱可信度。

## 12. Strengths

- 正确认识重复测量结构，并把个体随机截距/斜率作为主模型，而不是把 1082 行当独立样本。
- 从统计关系继续构造阈值概率和可执行分段，模型链有明确决策出口。
- 女胎流程同时考虑协变量校正、稳健尺度、厚尾、BH 和重复一致性，防护层比单一 Z 阈值丰富。
- 官方展示保留 94 页代码附录，使公式—代码审计成为可能；代码提供部分随机种子、参数和 fallback。
- 进行了实际 `κ`/`q` 扰动，而非只写定性“稳健”。

## 13. Weaknesses

核心限制是独立验证缺失和正文—代码不一致：LMM 没有受试者级留出；女胎没有临床真值；男胎 pseudo-FPR 复用校准样本。正文 REML、硬保障约束、Elastic-Net、风险 DP、ChrX 门控、交叉验证未由官方代码完整实现。

数值上，GLM R² 与 RMSE/FF 标准差不可能同时成立；AME 漏掉二次项导数；表 4 分组重叠且四组平均保障率低于 0.95；表 8 相对变化三处错误；年龄结论方向与表 7 冲突。这些问题不否定 LMM/多重检验框架本身，但限制所有“最优、稳健、临床适用”表述。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | unavailable in repository | 正文引用 `附件.xlsx`；本地/官方展示未提供该文件 | 不能重跑清洗、拟合或核验结果表 |
| Code availability | partial | 官方页 29–122 展示 q1–q4 全部代码页图；无纯文本文件 | 可审计逻辑但转录执行成本高，OCR 不能替代源码 |
| Dependency / environment information | partial | imports 包含 pandas/numpy/scipy/statsmodels/sklearn/matplotlib/PyMC；无版本锁定 | PyMC/Pytensor/Aesara 与 fallback 会改变结果 |
| Random seed | partial | q2=2025；q3=42；q4 主体确定性 | 未说明正文结果采用 ADVI/NUTS/PAVA 哪一路及收敛状态 |
| Hard-coded constants | extensive | q/θ/K/κ/α/β、winsor、GA bins、min_n=25、阈值网格均在代码/正文 | 缺联合调参与敏感性，边界选择影响结果 |
| Formula-to-code consistency | contradicted in material parts | 对照正文式 (9)/(15)/(22)、ChrX 描述与 official p37/p42–44/p63–71/p94–122 | ML/REML、硬约束、q3风险目标、ChrX 门控不一致 |
| Code-to-result consistency | partial with contradictions | 官方代码全页抽查与表 4/5/7/8/9/10 | 无运行输出；表区间/相对变化错误；q4 grid best 不自动回填 |
| Overall reproducibility | partially reproducible | 已审查本地 28 页、官方 94 页代码附录和全部可用 metadata | 模型框架可重建，但缺输入、源码、环境和运行产物，且多处接口冲突 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 平均重复次数 | 1082 条、267 人、人均 4.05 | `1082/267=4.0524` | pass | 物理 p5 表 1 | 计数闭合 |
| LMM R² 与 RMSE | SD(FF)=0.0335，RMSE=.0108，R²=.8962 | `1-.0108²/.0335²=.8961` | pass | 物理 p5 表1、p7 表2 | 与常规定义近似闭合 |
| GLM R² 与 RMSE | SD=.0335，RMSE=.0113，R²=.0433 | `1-.0113²/.0335²≈.8862`，与 .0433 相差约 .843 | fail | 物理 p5 表1、p7 表2 | 同一响应/样本下不可同时成立 |
| AIC/LL 参数数 | LMM 712.63/-347.32；GLM 749.92/-367.96 | `k=(AIC+2LL)/2` 分别约 9 和 7 | pass | 物理 p7 表2 | 算术闭合；GLM 七参数定义未说明 |
| AME 导数 | 式 (10) 只用 `β1*FF*(1-FF)` | 二次预测器应为 `(β1+2β2 GA_c)*FF*(1-FF)` | fail | 物理 p8 式 (10) | 漏二次项，0.316百分点解释不可直接接受 |
| ML/REML | 正文式 (9) 称 REML | official p37/p67 均 `reml=False` | fail | 物理 p8 式(9)；official p37, p67 code | 实际为 ML；表2若比较固定效应用 ML 反而合理，但叙述错误 |
| BMI 分组互斥覆盖 | 表4称五组 | 第4组 `[42.8,46.8]` 与第5组 `[44.7,46.8]` 重叠，且第3至第4间缺 42.6–42.7 网格 | fail | 物理 p13 表4 | 不能作为有效分区直接执行 |
| 硬保障率 | `q=.95` 且式(15)要求组内最小概率至少 q | 表4平均保障率 .9103/.9244/.9264/.9243 已低于 .95 | fail | 物理 p11 式(15)、p13 表4 | 平均值低于阈值已足以否定最小值约束；代码也无硬约束 |
| 问题二风险列 | 组1保障 .9103、风险 .0897 | `1-.9103=.0897` | pass | 物理 p13 表4 | 组2–5风险另含时间项，口径未在表下注明 |
| 问题二 κ 单调性 | 论文称噪声越大推荐越晚 | q=.95 时 κ=.75 为18.44周，高于 κ=1 的17.08周 | concern | 物理 p13/14 表5/6 | 全区间单调结论不成立 |
| 问题三相对变化 | 基线21.67；表列 -.47/+.50/+1.04 | 实算20.20-21.67=-1.47；23.17-21.67=1.50；23.71-21.67=2.04 | fail | 物理 p17 表8 | 三个非基线场景均差 1.00 周 |
| 年龄方向 | 每增1岁推荐提前 .065 周 | 表7相近 BMI 约32附近：<25岁约10.6/12.8周，≥40岁22.5/23.2周 | contradicted | 物理 p17 表7及段落 | 分层表未控制其他协变量，至少不能声称方向一致 |
| q3风险函数 | 正文晚检惩罚随 t 增加 | q3 code 对 `t<28` 用 `(28-t)*α`，惩罚越早越大 | fail | 物理 p10 式(13)；official p63 code | 与正文方向相反；且分段选择实际最小化 L2 |
| 女胎总数与比例 | 118阴性、26可疑、3阳性；80.3/17.7/2.0% | 总和147；比例80.27/17.69/2.04% | pass | 物理 p20 结果段 | 仅计数闭合，不验证分类正确性 |
| q4 FPR规则一致性 | FPR<=1% 下选阈值 | 男胎 grid 只计命中数；女胎还要求同号；男胎又用于拟合零分布 | fail | official p103–114 code | pseudo-FPR 不是最终女胎规则的独立错误率 |
| ChrX质控 | 正文称加入 ChrX 门限 | q4 的列映射、回归和聚合只含 Z13/Z18/Z21 | fail | 物理 p19；official p94–122 code | 关键质控未进入所附实现 |

## 14. Reusable Techniques

### 受试者级纵向建模

**When useful:** 同一对象有多次测量，且关注群体趋势和个体差异。

**Why useful:** 随机截距/斜率比把所有行当独立样本更符合数据结构。

**Limitations:** 仍需受试者级划分验证、残差/随机效应诊断；边际效应必须包含所有非线性项。

### 阈值概率到单调决策曲线

**When useful:** 连续预测要转成“何时达标”的操作规则。

**Why useful:** 先求 `T*` 再单调化和台阶化，接口清楚且便于落地。

**Limitations:** 保障率约束必须真的进入求解器；要传播固定效应、随机效应、阈值和模型结构不确定性。

### 经验零分布+FDR+重复一致性

**When useful:** 无直接标签但有可信阴性校准组、多指标、多次测量。

**Why useful:** 比固定 Z 阈值更能处理协变量、厚尾和多重比较。

**Limitations:** 校准组必须独立且确认为阴性；阈值应在留出集评估；FDR、FPR、灵敏度不可混称。

### 公式—代码—结果三向核对

**When useful:** 论文附代码且模型链包含多个接口。

**Why useful:** 本文的 ML/REML、硬约束、风险方向、ChrX 和阈值回填问题只有对代码才能发现。

**Limitations:** 页图代码不是可执行源码；没有数据/日志时只能判接口，不可声称完整复现。

## 15. Competition Takeaways

1. 重复测量必须按受试者建模，并按受试者划分训练/验证，不能随机拆行。
2. 报告二次模型的边际效应时，把一次项和二次项导数全部写入公式并复算。
3. 将概率模型接优化前，做一张“正文约束—代码条件—结果表”对照表。
4. 分组输出先自动检查互斥、覆盖、顺序和每组最坏保障率，再排版进论文。
5. 灵敏度表的相对变化由脚本从基线自动计算，避免手填造成整列偏差。
6. 多重检验必须区分 FDR、样本内 pseudo-FPR 和外部临床错误率。
7. 附代码时同时保存数据字典、依赖版本、运行命令、随机种子和结果 hash。
8. 若官方版包含额外附录，先做页面身份映射；页数差不能单独作为版本无效证据。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 本地 28 页覆盖官方主文 1–28 页，官方第9页移到本地物理第28页 | interpretation | 1–28；official 1–28 | version review | figure/page image | independent calculation | N/A for positive evidence | 逐页归一化图像相关系数 0.99691–0.99859；身份充分一致 |
| 官方另有第29–122页代码附录 | explicit | official 29–122 | 附录E | code | direct transcription | N/A for positive evidence | snapshot `extendjson` 122页；`article.list` 仅100页是记录结构差异 |
| 男胎共有1082条观测、267名孕妇 | explicit | 5 | 4.2 | table 1 | direct transcription | N/A for positive evidence | 本地物理页 |
| 平均每人4.05次测量算术闭合 | interpretation | 5 | 4.2 | table 1 | independent calculation | N/A for positive evidence | 1082/267=4.0524 |
| LMM 使用随机截距、随机 GA 斜率及 GA/BMI 二次项 | explicit | 6–8 | 4.3–4.4 | equation (3)–(9) | notation normalization | N/A for positive evidence | 处理重复测量和非线性 |
| 表2报告 LMM 的 R²=.8962、RMSE=.0108 | explicit | 7 | 4.3.3 | table 2 | direct transcription | N/A for positive evidence | 样本内指标 |
| 表2 GLM 的 R²=.0433 与 RMSE=.0113、FF SD=.0335 不闭合 | criticism | 5,7 | 4.2/4.3.3 | table 1/table 2 | independent calculation | N/A for positive evidence | 常规 R²应约.886，不是.0433 |
| 正文 REML 与代码 ML 不一致 | criticism | 8；official 37,67 | 4.4/appendix code | equation (9)/code | derived interpretation | N/A for positive evidence | 两处 `reml=False` |
| 式(10)的 GA 平均边际效应遗漏二次项导数 | criticism | 8 | 4.4 | equation (10) | independent calculation | N/A for positive evidence | 应含 `2β2 GA_c` |
| 论文报告 GA 单调上升、BMI 倒U峰值约31–32 | explicit | 9,28 | 4.5–4.6 | paragraph/figure 5–6 | direct transcription | N/A for positive evidence | 物理28对应官方/印刷9 |
| 问题二以 FF>=.04 和 q=.95 定义最早达标时点 | explicit | 9–11 | 5.2–5.3 | equation (12)–(18) | notation normalization | N/A for positive evidence | 正文还写组内最坏保障约束 |
| 表4五个 BMI 区间不是互斥覆盖分区 | criticism | 13 | 5.5 | table 4 | independent calculation | N/A for positive evidence | 第4/5组重叠，42.6–42.7未覆盖 |
| 表4四组平均保障率低于 q=.95，硬约束不成立 | criticism | 11,13 | 5.3.3/5.5 | equation (15)/table 4 | independent calculation | N/A for positive evidence | 平均低于阈值即可否定最小值约束 |
| q2代码分段未实施正文的硬保障约束 | criticism | official 42–44 | q2.py | code | derived interpretation | N/A for positive evidence | 代价仅失败概率、时间项和λ |
| q2默认 typical 模式不含新孕妇随机效应方差 | explicit | official 37–38,52 | q2.py | code | direct transcription | N/A for positive evidence | `guarantee-mode` 默认 typical |
| q=.95时 κ=.75 比 κ=1 的推荐周更晚 | criticism | 13–14 | 5.6 | table 5/table 6 | independent calculation | N/A for positive evidence | 18.44 vs 17.08，和全区间单调叙述冲突 |
| 问题三加入 AGE/G/P 固定效应 | explicit | 15 | 6.2.1 | equation (21) | direct transcription | N/A for positive evidence | 正文称 Elastic-Net 筛选 |
| 在已审查范围内，未发现 Elastic-Net 筛选实现或显著性结果 | criticism | 1–28；official 29–122 | abstract/6.2/code appendices | none found | derived interpretation | 审查本地主文全部28页、参考文献/附录及官方q1–q4代码页29–122 | q3代码直接加入可识别 AGE/G/P |
| q3台阶化最小化段内L2，不是正文式(22)风险 | criticism | 15；official 69–71 | 6.2.2/q3.py | equation (22)/code | derived interpretation | N/A for positive evidence | 公式—代码目标不一致 |
| q3时间风险方向与正文相反 | criticism | 10；official 63 | 5.3.1/q3.py | equation (13)/code | direct transcription | N/A for positive evidence | 正文晚检增罚；代码早于28周越早罚越大 |
| 表8三个非基线相对变化均少算1周 | criticism | 17 | 6.5 | table 8 | independent calculation | N/A for positive evidence | 应为-1.47、+1.50、+2.04 |
| 年龄每增1岁提前.065周与表7分层输出方向冲突 | criticism | 17 | 6.4–6.5 | table 7/paragraph | derived interpretation | N/A for positive evidence | 表7未控制其他协变量，至少不能声称一致 |
| 问题四使用男胎校准、层内 BH 和至少两次同号聚合 | explicit | 18–20 | 7.1–7.4 | equation/paragraph | notation normalization | N/A for positive evidence | 13/18/21号染色体 |
| 女胎118阴性、26可疑、3阳性比例闭合 | interpretation | 20 | 7.5 | paragraph | independent calculation | N/A for positive evidence | 总数147；80.27/17.69/2.04% |
| 在已审查范围内，未发现女胎临床真值、独立测试集或可核查交叉验证协议 | criticism | 1–28；official 29–122 | abstract/validation/results/code | none found | derived interpretation | 审查本地主文1–28页、表1–10、参考文献/附录及官方四份代码页29–122 | 因而不能估计真实灵敏度/特异度 |
| male pseudo-FPR 复用男胎校准样本 | criticism | official 103–114 | q4.py | code | derived interpretation | N/A for positive evidence | 同样本拟合回归/零分布并评估阈值 |
| male pseudo-FPR 与女胎最终一致性规则不同 | criticism | official 107–114 | q4.py | code | direct transcription | N/A for positive evidence | 男胎只数命中，女胎还要求同号 |
| 在已审查范围内，未发现 ChrX 质控进入 q4 实现 | criticism | official 94–122 | q4.py | none found | derived interpretation | 审查q4全部官方代码页94–122的列映射、校准、阈值和聚合 | 正文物理p19明确声称 ChrX 门限 |
| q4 grid best 不会在同一运行自动回填并重算标签 | criticism | official 121–122 | q4.py | code | derived interpretation | N/A for positive evidence | 先按现有阈值产出结果，最后才写 best CSV |
| 官方代码可审计但缺附件、源码文件、环境锁和运行输出 | criticism | 24–28；official 29–122 | appendices | none found | derived interpretation | 审查本地附录A–E和官方完整代码页；核对仓库可用补充物 | 整体仅 partially reproducible |
