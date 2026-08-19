# Paper: 基于动态搜索的板凳龙运动状态及路线研究

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_bcfa3cb1ec01
- Year: 2024
- Problem: A
- Award: 全国大学生数学建模竞赛全国一等奖；官方获奖名单、团队信息与作者仓库来源已交叉核验
- Provenance tier: V; 作者仓库PDF与官方展示标题、队伍及官方一等奖信息匹配，但未做与官方页面图像的逐字节同一性核验
- Source file: literature/raw_papers/2024/A242_author_2024_A242_bench_dragon.pdf
- Source URL: https://raw.githubusercontent.com/cny123222/CUMCM-2024A-Bench-Dragon/main/OurPaper.pdf
- Verification source: https://www.mcm.edu.cn/upload_cn/node/733/4rFKQqyT96ee1e63dd8d2408e56df8b2ec172125.pdf
- Pages: 58
- SHA-256: 5f24d39c2723a1a6bb2c3f24892ebaa3eac7242711bc9fbeb163feb36f4e1d11
- Extraction method: mixed；原生文本层用于英文代码核对，macOS PDFKit逐页250 DPI渲染后用Tesseract 5.5.0 `chi_sim+eng`、PSM 3做OCR，并人工视觉复核
- Extraction quality: OCR usable with visual review；原PDF的Adobe-GB1中文字体映射使pypdf文本为乱码，Poppler/Ghostscript又丢失中文字形；PDFKit原生渲染后58/58页OCR成功，58/58页均超过30个非空白字符，中位数803字符/页，无页级错误；质量记录锚定原PDF SHA，原件未改动
- Page convention: 1-based physical PDF pages
- Visually checked pages: p.1摘要及五问结果；p.5–7阿基米德螺线、弧长积分、位置/速度递推；p.10–12碰撞区域、顶点—直线距离、动态搜索和表4；p.15–17螺距约束、PSO参数、图12–15；p.18–19双圆弧几何、切线角和半径关系；p.24–25问题四坐标/速度表及路线图；p.28–29三分搜索结果与图22–23；p.31支撑材料列表；p.33–34 `judge_col`/`min_dis`；p.39转向几何常数；p.53–55问题二硬编码时刻及问题三PSO入口；p.57–58三分搜索代码
- Unresolved extraction ambiguities: OCR会把“板凳龙”、上下标、希腊字母和部分公式符号误识；所有重要公式、表、图和关键代码页已回看PDFKit原生页图，代码判断以原生文本层与页图交叉为准；正文p.21个别孔距数字的OCR形态不稳定，代码和题给常量明确采用2.86m与1.65m
- Supplemental artifacts: PDF内嵌`dragon.py`、`dragon2.py`和问题1–5入口代码；文中列出的`result1.xlsx`、`result2.xlsx`、`result4.xlsx`及运行日志 referenced but unavailable，所示入口实际写出若干CSV文件

## 1. Problem Archetype

本文属于几何运动学、事件检测、约束路径设计和混合数值搜索的连续管线：

1. **约束运动学**：在阿基米德螺线上由龙头弧长反解极角，再按刚性孔距递推223节板凳的把手位置和速度。
2. **几何碰撞检测**：把板凳简化为平面矩形，用顶点到另一板中心线的距离与0.15m比较。
3. **边界可行性优化**：以螺距为一维决策，要求龙头进入半径4.5m调头空间前不碰撞。
4. **分段路径运动学**：把调头路线写成盘入螺线—大圆弧—小圆弧—盘出螺线四段，并跨段递推。
5. **极值搜索**：用粗网格定位速度峰，再在声称单峰的局部区间用三分搜索。

原型很适合比赛中的“连续轨迹→离散刚体链→首次事件→设计边界→局部极值”问题。但关键碰撞函数并非有限矩形的完备相交测试，问题三代码又把正文的全内圈约束缩成仅龙头板，导致最小螺距的可行性边界不能按论文代码确认。

## 2. Problem Decomposition

1. **盘入轨迹**：令极径 `r=dθ/(2π)`，以龙头速度1m/s对弧长方程积分，用二分法从时间反解龙头极角。
2. **刚体链递推**：龙头板两孔距2.86m，其余板两孔距1.65m；用余弦定理逐把手求后继极角，再对隐式方程求导得速度。
3. **首次碰撞**：作者先把候选范围缩到最内圈及外邻一圈，再以1s/变步长定位、二分细化首次阈值穿越。
4. **最小螺距**：外层逐步增加螺距，内层PSO在进入调头空间前的时间区间内最小化板间距离；首次满足距离大于0.15m即停止。
5. **调头几何**：给定螺距1.7m和4.5m空间，构造半径比2:1的两段相切圆弧；证明两弧总长由端点和切向条件固定。
6. **跨段状态**：根据把手所在四段路径分类，用同段解析递推或相邻段距离方程求位置，再对相应约束求导得速度。
7. **速度上限**：先令龙头1m/s，搜索全把手最大速度比；再用2m/s人员上限按比例缩放龙头速度。

## 3. Data Processing

- 本文没有外部观测数据集，主要“数据”是题给板凳尺寸、223节链、螺距、调头空间和计算生成的时间序列。
- 问题一在0–300s按1s输出；问题四在−100–100s按1s输出。位置与速度入口分别生成CSV，而非附录清单所写的单个XLSX。
- 连续极角通过二分搜索求根，默认区间误差`1e-8`；后继把手通过固定孔距隐式求根。
- 问题二正文声称1s粗搜后动态缩步并二分；公开入口仅对412–413s以0.1s打印碰撞状态，精确时刻在另一脚本中直接硬编码。
- 问题三正文声称从0.30m以0.01m逐级细化到六位小数；公开入口只运行`np.arange(0.45,0.46,0.001)`。
- PSO每个候选螺距使用40粒子、50迭代，未设随机种子，未保存重复运行或可行性置信度。
- 问题五先对候选时段以0.1s计算，再把14–15s交给容差`1e-8`的三分搜索。
- 在已审查范围内，未发现对二分区间括根失败、后继根唯一性、浮点阈值、公差传播、缺失输出文件或随机运行结果的自动QA；审查覆盖p.1–30正文、p.31–58全部代码及现有仓库补充物。

## 4. Models Used

### 阿基米德螺线刚体链运动学

**Purpose:** 生成盘入/盘出阶段全部把手的位置与速度。

**Inputs:** 螺距、龙头速度、初始极角、板数、两种孔距和时间。

**Outputs:** 224个把手的极角、二维坐标和速度。

**Why selected:** 题目给定等距螺线；极坐标能直接表达螺距，余弦定理能编码相邻把手固定距离。

**Important assumptions:** 板和把手为无变形刚体；板厚和把手直径对平面轨迹可忽略；后继极角根在指定区间唯一。

**Key equations or mathematical structure:** `r=dθ/(2π)`；弧长微分为`ds=(d/(2π))sqrt(1+θ²)dθ`；相邻把手满足两极坐标点距离等于2.86m或1.65m，隐式微分给角速度递推。

**Implementation notes:** `dragon.py`用二分法解龙头和后继极角；初始`θ0=32π`给`r0=8.8m`，与表2闭合。

### 顶点—中心线碰撞判定

**Purpose:** 检测盘入过程中板凳矩形是否相碰，并为螺距优化提供最小间距。

**Inputs:** 两块板的把手坐标、板宽0.3m、板端孔距0.275m和候选板索引。

**Outputs:** 碰撞布尔值和最小距离。

**Why selected:** 作者认为最内圈与外邻一圈相对角速度最大，且龙头更长，最可能首先碰撞；距离公式计算快。

**Important assumptions:** 首次碰撞必在该局部候选集；用内板两个外侧顶点到外板中心线的距离小于0.15m能代表矩形碰撞。

**Key equations or mathematical structure:** 式(5)–(7)构造内板两个外侧顶点，并计算其到外板把手连线的点线距离。

**Implementation notes:** 代码算的是到**无限直线**的距离，未检查垂足是否落在有限板段，也未使用两矩形所有分离轴、反向顶点或边—边相交。它可能在延长线附近误报，也不能构成完整矩形不相交证明。

### 外层螺距搜索与内层PSO

**Purpose:** 找到进入调头空间前满足安全间距的最小螺距。

**Inputs:** 候选螺距`d`、进入时间`to(d)`、距离函数和PSO超参数。

**Outputs:** 作者报告`dmin=0.450337m`。

**Why selected:** 作者称距离函数局部极小值多、峰值高，模拟退火易受能垒影响；选择PSO做全局时域搜索，外层再变步长。

**Important assumptions:** 单次PSO足以找到全时域最小距离；可行性随螺距单调；首次通过严格阈值的离散点可称最小值。

**Key equations or mathematical structure:** `min d`，约束`0.30<d<0.55`、龙头到达`r=4.5m`、到达前最小距离`>0.15m`。

**Implementation notes:** `Dragon.min_dis`仅检查龙头板与外一圈5块候选板，而正文式(7)写的是所有最内圈`i,j`；公开外层步长为0.001m，不能产生0.450337m；PSO无种子和多次重复。

### 两段相切圆弧的分段调头模型

**Purpose:** 在4.5m调头空间内连接盘入与中心对称盘出螺线，并递推全龙状态。

**Inputs:** 螺距1.7m、调头半径4.5m、两圆半径比2:1、龙头速度和链几何。

**Outputs:** −100–100s各把手位置/速度，以及后续速度峰函数。

**Why selected:** 题设限定两段相切圆弧及半径比；作者证明在这些条件下两弧总长固定，优化退化为几何求解。

**Important assumptions:** 轨迹拼接位置和切向连续；相邻把手至多跨越一个分段边界；刚体速度比例可由约束微分递推。

**Key equations or mathematical structure:** `θmin=2πr/d`，`α=atan(θmin)`，`R1=3/sin α`、`R2=3/(2sin α)`；四段曲线按时间切换。

**Implementation notes:** `dragon2.py`显式编码四种路径状态和同段/跨段递推；分段逻辑复杂，但论文未给自动连续性、孔距残差或跨段边界测试。

### 粗定位加三分搜索的速度极值模型

**Purpose:** 在所有时刻、所有把手中确定1m/s龙头基准下的最大速度放大系数。

**Inputs:** 分段运动模型、候选时间窗、三分搜索容差。

**Outputs:** `t≈14.47997148s`、最大把手速度`1.60479338m/s`和龙头上限`1.246266m/s`。

**Why selected:** 图23在14–15s内显示先增后减，满足三分搜索的局部单峰前提。

**Important assumptions:** 粗网格未漏掉其他窄峰；14–15s内目标确实单峰；速度对龙头速度线性缩放。

**Key equations or mathematical structure:** `M(t)=max_n v_n(t)`，先粗搜再在`[14,15]`三分；最终`v_head,max=2/max_t M(t)`。

**Implementation notes:** 三分实现与局部图一致，但“全局”时域由粗扫和物理判断缩小，未给完备上界或自适应区间证明。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 直角坐标直接递推 | rejected implicitly | 盘入运动学 | 等距螺线在极坐标更简洁 | not reported | 无复杂度或误差比较 | 极坐标选择合理 |
| 极坐标螺线+余弦定理 | selected | 盘入/盘出状态 | 直接表达螺距和固定孔距 | 表2–3与轨迹/极角图 | 无孔距残差分布和边界测试 | 数学结构合适，局部算术可核 |
| 全部板对有限矩形相交 | considered only | 碰撞检测 | 作者以局部首次碰撞假设降复杂度 | 图8–9同模型可视化 | 无全对检查作为基准 | 应作为离线验证基线 |
| 最内圈局部顶点—中心线距离 | selected | 碰撞检测 | 内圈相对角速度快、龙头更长 | 412.473838s图示与距离曲线 | 无有限线段/完整矩形测试 | 当前判据不完备，不能证明首次事件 |
| 模拟退火 | rejected | 时域最小间距 | 作者称多局部极小和高峰导致能垒问题 | 定性叙述 | 无同预算运行、参数或成功率 | 拒绝证据不足 |
| PSO | selected | 时域最小间距 | 作者称全局搜索能力强 | 一条收敛曲线及“多次实验”叙述 | 无种子、重复表、真值或算法对照 | 只能称单次best-found |
| 两段相切圆弧 | selected | 调头路径 | 题设限定且总长在条件下固定 | 几何证明 | 无其他可行轨迹族 | 在题设限定内合理，不是一般最短路结论 |
| 黄金分割/网格局部极值 | considered only | 速度峰定位 | not reported | not reported | 无函数调用数/误差比较 | 三分已足够，关键是全局区间而非局部算法 |
| 粗网格+三分搜索 | selected | 最大速度 | 局部函数呈单峰 | 图22–23 | 无全时域峰值上界与网格收敛 | 局部极值可信度高，全局性证据弱 |

## 5. Model Pipeline

主链为：

`题给几何 → 螺线弧长反解龙头极角 → 固定孔距递推全链位置 → 隐式微分递推速度 → 局部碰撞函数 → 首次事件/螺距可行性`。

问题四将单一螺线替换为四段路径：

`盘入螺线 → 大圆弧 → 小圆弧 → 中心对称盘出螺线 → 同段/跨段位置递推 → 同段/跨段速度递推 → 全把手最大速度 → 比例缩放龙头上限`。

关键断裂有三处：问题二正文的动态细化没有在公开入口实现；问题三正文对“所有最内圈板”的约束在代码中退化为仅龙头板；问题三六位螺距不可能由附录的0.001m入口直接产生。因而公式层管线完整，发布的可执行管线并不闭合。

## 6. Model Improvements

1. 用弧长积分和二分求根替代逐小步积分，直接把时间映射到螺线极角。
2. 先证明候选碰撞区域，再从全板对降到内外相邻圈，提高搜索速度。
3. 首次事件采用粗定位—细化，而不是全区间固定超小步长。
4. 螺距优化采用外层一维步长细化、内层时域启发式搜索的嵌套结构。
5. 调头阶段把复杂轨迹分成四段，并列出同段和跨段递推，保持问题一接口。
6. 最大速度先用线性比例转化，再以粗网格定位局部单峰，用三分搜索精化。

这些是有迁移价值的计算降维思路；但“更快”没有函数调用/时间表，“更准”没有误差表，碰撞降维还改变了判定问题本身。改进证据应与实现正确性分开评价。

## 7. Parameter Estimation and Optimization

盘入/调头模型的大多数物理量由题目给定；待估计量主要是首次碰撞时刻、最短螺距和速度峰。连续状态用二分求根，螺距采用离散外层搜索，最小间距用随机PSO，最大速度用局部三分搜索。论文没有报告优化运行时间、函数调用数、随机种子、重复成功率或最终最大约束残差。

严格约束写作`min distance>0.15m`。若可行边界恰为等式，开可行集上通常只有下确界而没有取得的最小值；“首次网格点通过”应表述为给定步长/随机运行下的最小可行候选，而非精确全局最小。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| `d` q1 | 盘入螺距 | m | p.5, p.31–32 code | 0.55 | problem-provided | N/A - given | partial | q2沿用 |
| `θ0` | 初始龙头极角 | rad | p.5, p.32 code | 32π | problem-provided | N/A - given | no | 对应第16圈、半径8.8m |
| `v0` | 龙头前把手基准速度 | m/s | p.5, p.32 code | 1 | problem-provided | N/A - given | yes | q5按比例缩放 |
| board count | 板凳数量 | boards | p.31 code | 223 | problem-provided | N/A - given | no | 代码产生224个把手 |
| board dimensions | 龙头/龙身长度、板宽 | m | p.31 code | 3.41, 2.20, 0.30 | problem-provided | N/A - given | no | 两孔距另由端部偏移推得 |
| hole offset/diameter | 孔离板端距离/孔径 | m | p.4, p.31 code | 0.275 / 0.055 | problem-provided | N/A - given | no | 孔径在运动学中被忽略 |
| handle spacing | 龙头板/其余板两孔距 | m | p.6, p.31–34 code | 2.86 / 1.65 | problem-provided | 板长减两端0.275m | no | 表2初始龙头—首节距离闭合 |
| collision threshold | 中心线安全半宽 | m | p.10–12, p.33–34 code | 0.15 | problem-provided | 板宽0.30m的一半 | partial | 并非完备矩形间距 |
| binary tolerance | 二分停止区间 | rad or s | p.38, p.50–51 code | `1e-8` | algorithm hyperparameter | fixed | no | 未报告残差或括根失败处理 |
| q2 coarse/fine step | 碰撞时间粗/展示步长 | s | p.12, p.53 code | 1 in prose; 0.1 in entry | algorithm hyperparameter | manual staged search | no | 公开入口不含二分 |
| `rmin` | 调头空间半径 | m | p.14, p.39 code | 4.5 | problem-provided | N/A - given | no | `arr_time`据此二分 |
| q3 pitch bounds | 螺距搜索边界 | m | p.14–15 | 0.30–0.55 | author-assumed | 板宽下界与q2可行上界 | partial | 下界未包含完整矩形可行性证明 |
| PSO population/iterations | 粒子数/最大迭代 | particles/iterations | p.16, p.54 code | 40 / 50 | algorithm hyperparameter | fixed | partial | 仅一条曲线；无重复统计 |
| PSO `w,c1,c2` | 惯性/个体/群体权重 | dimensionless | p.16, p.54 code | 0.8, 0.5, 0.5 | algorithm hyperparameter | fixed | no | 无调参依据 |
| q3 public pitch step | 公开入口外层步长 | m | p.55 code | 0.001 over `[0.45,0.46)` | algorithm hyperparameter | fixed grid | no | 不能输出0.450337 |
| `dmin` | 作者报告最短螺距 | m | p.16 | 0.450337 | data-estimated | staged search + PSO, exact run unavailable | partial | 只应视为reported best-found |
| q4 pitch/radius ratio | 调头螺距/空间/圆弧半径比 | mixed | p.18–19, p.39 code | 1.7m, 4.5m, 2:1 | problem-provided | geometry constraints | no | 决定两圆弧 |
| finite-difference step | q4速度复核时间差 | s | p.26 | 0.01 | algorithm hyperparameter | forward displacement comparison | no | 未给误差值 |
| q5 coarse window/step | 全局峰候选时段及粗步长 | s | p.27, p.56–57 code | `[13,16]∪[376,384]`; 0.1 | author-assumed | plots/physical judgment | partial | 代码公开的`main`只细搜14–15 |
| ternary tolerance | 局部峰搜索容差 | s | p.28, p.57 code | `1e-8` | algorithm hyperparameter | fixed | no | 只控制区间宽，不含模型误差 |
| `vhead,max` | 龙头允许最大速度 | m/s | p.28 | 1.246266 | data-estimated | `2/1.60479338` | no | 算术闭合 |

## 8. Validation

论文的验证以同一模型生成的轨迹图、距离曲线、PSO收敛曲线和位置差分—解析速度对照为主。最强的一项是问题四对速度采用另一种数值计算路径；但没有报告误差指标。碰撞图和最小间距图仍使用同一个不完备判据，不能独立验证首次碰撞。没有实物、外部模拟器、全板对有限矩形基线或解析合成小例。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| q1位置/速度递推 | L2 internal consistency | theoretical | 轨迹形态、速度趋势、固定孔距样例 | one reported run | 表2–3、图3–5形态合理 | 未展示全链孔距残差 | 图与表由同一代码产生 | 支持局部运动学闭合，不证明全时域无根切换 |
| q2碰撞时刻 | L1 same-model visualization | same sample | 图8接触、图9距离穿越0.15m | one trajectory | reported 412.473838s | 未做全矩形/全板对对照 | 相同局部点线判据重复验证自身 | 只能支持该判据下的作者时刻 |
| q3 PSO最小间距 | L1 optimization trace | same sample | `gbest`距离、50代收敛曲线 | one shown; others not quantified | reported slightly above0.15m | 随机重复与真值缺失 | 仅龙头局部距离且公开步长不符 | 只能记录单次best-found可行叙述 |
| q3螺距单调性 | L3 parameter sweep plot | same sample | 最小间距随螺距曲线 | not reported | 图15近似单调线性 | 无采样表、误差条或反例搜索 | 每点仍为随机PSO估计 | 定性支持局部变步长，不证明六位边界 |
| q4位置 | L1 same-model visualization | same sample | 把手是否沿四段轨迹 | selected snapshots | 图20视觉上沿路线 | 未给连续性/孔距残差 | 绘图来自同一坐标 | 仅视觉合理性 |
| q4速度 | L2 alternative numerical calculation | same sample | 0.01s位移差分 vs 解析速度 | not reported | 作者称差异较小 | 无MAE、最大误差、页表 | 时间步收敛未展示 | 支持方法交叉检查意图，不能量化精度 |
| q5局部峰 | L1 local shape check | same sample | 14–15s单峰图、峰值 | one curve | 14.47997148s, 1.60479338m/s | 窄峰/其他时段无严格排除 | 全局范围由粗扫缩小 | 局部三分搜索适用，全球最大仍是经验性结论 |
| 外部/实物验证 | not reported | external | geometry/event/speed | not reported | not reported | 无实物或独立引擎 | 全部证据来自论文模型 | 不构成L5验证 |

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 螺距 `d` | 0.450337m | plotted 0.30–0.55m | unspecified sweep + PSO | 到达前最小距离 | 图15呈近线性单调增加 | no in plotted trend | 支持局部单调，但点值/随机误差不可得 |
| PSO随机初始化 | pop40, iter50 | “多次实验” | not reported | 收敛值/迭代数 | 声称均稳定、前10代趋稳 | unclear | 无次数、种子、均值或最差值，不能评估误判概率 |
| 速度计算方法 | analytic recursion | 0.01s displacement difference | one alternate calculation | speed difference | 作者称差异较小 | no | 有交叉计算思路，但无误差量和步长收敛 |
| q5时间分辨率 | 0.1s coarse | 14–15s then `1e-8` ternary | grid + local search | max handle speed | 局部峰1.60479338 | no within local window | 细化局部充分，不证明粗网格未漏全局窄峰 |

在已审查范围内，未发现对碰撞候选圈数、有限矩形判据、PSO粒子数/迭代/权重、外层螺距步长、二分容差、浮点阈值、板长/宽误差或调头半径扰动的系统实验；审查覆盖p.1–30正文、p.31–58全部代码及现有补充物。

## 10. Visualization Strategy

- 图1和图7/10把运动学、事件搜索和嵌套优化画成流程图，适合作为五问之间的接口图。
- 图3–5分别展示螺线采样、速度随板号/时间变化和极角变化，帮助检查方向与趋势，但缺残差刻度。
- 图8把首次碰撞局部放大，图9画距离—时间阈值穿越；若换成有限矩形真实间距，它们会是很好的事件验证组合。
- 图12–13把PSO落点与收敛史并排，图15展示设计变量—安全间距关系；缺少重复误差带和数据表。
- 图17–20清楚展示四段调头路径和离散时刻姿态，适合解释跨段递推。
- 图22先给全时域概览、图23再放大14–15s峰值，符合“全局定位→局部精化”的视觉叙事；横轴范围和粗网格分辨率应明确标注。

## 11. Writing Structure

全文按五问顺序展开，每问基本采用“准备/模型建立/算法/结果/验证”的固定结构，附录给出核心Python代码。前一问的几何与递推函数被后问复用，问题五也先做比例转化再调用问题四，逻辑连接强于简单模型堆叠。

主要写作风险是把定性论证提升为“证明”：内圈相对角速度快并不自动排除其他板对先碰撞；一张PSO收敛图不等于全局最优或随机稳定；图像单调也不能支持六位小数边界。应把“准确”“全局”“最小”分别改成给定判据、给定运行和给定精度下的结果，并列出验证边界。

## 12. Strengths

1. 五问共享同一几何状态表示，模型接口连贯。
2. 螺线弧长反解、刚体孔距递推和隐式速度递推具有明确数学来源。
3. 把首次事件、设计边界和速度极值都拆成粗定位与细化，计算策略清晰。
4. 调头路径分段及同段/跨段分类较完整，能处理长刚体链跨边界。
5. 表2–6给出具体坐标/速度，附录公开28页代码，允许公式—实现审计。
6. 问题五的速度比例转化和全景图—局部图组合简洁有效。

## 13. Weaknesses

1. 碰撞函数用点到无限中心线距离代替有限矩形相交，只查单向两个顶点和少量候选板，判据不完备。
2. “首次碰撞只在最内圈与外邻圈”的论证是趋势性解释，没有全板对基准验证。
3. 问题三正文要求所有内圈板安全，`min_dis`代码只评估龙头板；优化约束被缩窄。
4. 问题二精确时刻在脚本中硬编码，问题三入口只有0.001m网格，均不能生成正文的六位结果。
5. PSO无随机种子、版本、重复统计或真值比较；模拟退火的淘汰仅有定性叙述。
6. 问题四差分验证无误差表，问题五全局区间无严格漏峰分析。
7. 输出清单写XLSX而入口写CSV，结果文件、环境和运行日志未随论文提供。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | 题给常量在p.4–5、p.14、p.18及代码中；result工作簿不可得 | 可重建输入常量，不能逐格比对全量作者输出 |
| Code availability | substantial but incomplete workflow | p.31–58内嵌`dragon.py`、`dragon2.py`及问题1–5入口 | 精确q2/q3搜索过程未编码在公开入口，结果文件缺失 |
| Dependency / environment information | partial | Python、NumPy、pandas、matplotlib、`sko.PSO`；Mac字体绝对路径 | 无Python/库版本、安装文件或平台说明 |
| Random seed | not reported | p.54–55 PSO入口已审查 | q3可行性和停止螺距不可精确重现 |
| Hard-coded constants | extensive | 223、2.86/1.65、0.15、PSO 40×50、时段、步长、`1e-8` | 配置与敏感性不足，入口依赖人工阶段切换 |
| Formula-to-code consistency | contradicted for q3 constraint | 对照p.14–16式(7)与p.34 `min_dis` | 正文全内圈最小值在代码中退化为仅龙头板 |
| Code-to-result consistency | partial/contradicted | 对照p.12、p.16、p.28结果与p.53–58入口 | q5算术/局部搜索闭合；q2硬编码，q3步长不能产生六位结果 |
| Overall reproducibility | partially reproducible | 58页正文、全部附录代码、OCR/原生文本与关键页图已审查 | 几何递推和q5局部算术可复核；精确q2/q3、随机运行、输出和完备碰撞验证不可复现 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 初始半径 | `d=0.55`, `θ0=32π`，龙头坐标(8.8,0) | `0.55×32π/(2π)=8.8m` | pass | p.5, p.7 table2 | 极坐标—表格闭合 |
| 龙头板孔距 | 表2初始龙头与第1节坐标 | 两坐标欧氏距离`2.860000085m` | pass | p.7 table2 | 与`3.41−2×0.275=2.86m`一致 |
| q1龙头速度 | 0–300s均1m/s | 表3六个时刻均1.000000 | pass | p.8 table3 | 题给约束保持 |
| q2碰撞位置半径 | 412.473838s龙头坐标(1.209931,1.942784) | 半径`2.288743m<4.5m` | pass | p.12 table4 | 说明0.55m螺距在进入空间后才报告碰撞，但不验证首次性 |
| 点线判据维数 | 距离阈值0.15m | 分子面积量纲m²除线长m得m | pass | p.11 equations | 量纲正确，几何对象仍不完备 |
| 有限板碰撞 | 点到中心线小于0.15m即碰撞 | 代码未限制垂足在线段内，也未查完整分离轴 | fail | p.11, p.33–34 code | 无限延长线可误报；单向顶点检查可漏报 |
| q2精确时刻来源 | 动态变步长+二分得到412.473838s | `problem2_1.py`仅412–413步长0.1；`problem2_2.py`直接写412.47383777 | fail | p.12, p.53 code | 发布代码不能生成精确时刻 |
| q3约束索引 | 所有最内圈`i,j`在到达前距离>0.15m | `min_dis`固定`i=0`只查龙头板及5个`j` | fail | p.14–15, p.34 code | 优化可行域被放宽 |
| q3六位螺距 | `dmin=0.450337m` | 公开调用步长0.001只测试0.450、0.451等 | fail | p.16, p.55 code | 正文所述逐级细化未发布 |
| q3边界裕量 | 0.450337m为最小且距离略大于0.15m | 图15边界约在0.45m；报告值仅高约0.000337m，即0.337mm | concern | p.16–17 figures12–15 | 小于模型/随机误差未量化；严格不等式可能只有下确界 |
| 调头最小极角 | `θmin≈5.294118π` | `2π×4.5/1.7=16.631961rad=5.29411765π` | pass | p.19, p.39 code | 舍入一致 |
| 切线角 | `α≈0.480885π` | `atan(16.631961)=1.510743rad=0.48088457π` | pass | p.19 | 舍入一致 |
| 两圆半径 | `R1:R2=2:1`且弦长为6m/3m | `R1=3/sinα=3.005418m`, `R2=1.502709m` | pass | p.18–19, p.39 code | 代码一致 |
| 调头圆弧时间尺度 | 速度1m/s，峰约14s | 两弧总长`2α(R1+R2)=13.621245m` | pass | p.18–20, p.28 | 解释峰出现在14.48s附近，但不是峰值证明 |
| q5速度缩放 | 基准最大1.60479338m/s，龙头上限1.246266m/s | `2/1.60479338=1.246266357m/s` | pass | p.28 | 算术闭合 |
| q5全局性 | 全过程最大值在14–15s | 局部图单峰；全时域仅粗扫/物理判断，无解析上界 | concern | p.27–29, p.56–58 code | 局部三分结果不自动等于全局结果 |
| 输出契约 | 附录列`result1/2/4.xlsx` | 入口写`result1_pos.csv`、`result1_vol.csv`、`result2_all.csv`、`result4_pos.csv`、`result4_vol.csv` | fail | p.31, p.52–56 code | 文件名和格式不一致 |

## 14. Reusable Techniques

### 弧长反解加刚体链递推

**When useful:** 领航点沿解析曲线匀速运动、后续节点保持固定距离的链式运动。

**Why useful:** 将高维动态系统化为一个标量根和顺序几何根，状态可解释。

**Limitations:** 必须验证根区间、唯一性、固定距离残差和累计误差；曲率突变处需单独处理。

### 事件粗定位—括区间—根细化

**When useful:** 首次碰撞、阈值穿越、约束激活等连续事件。

**Why useful:** 粗扫控制成本，细化提供时间精度。

**Limitations:** 事件函数须连续且括区间；若函数振荡或判据不完备，粗步长会漏首次事件。

### 有限矩形分离轴碰撞基线

**When useful:** 平面刚体板、车辆、杆件之间的安全距离/相交检测。

**Why useful:** 对凸矩形可用有限组投影轴给出完备相交判定，并可作为快速近似的校准真值。

**Limitations:** 全板对成本较高，应配合空间索引；不能用无限直线距离替代有限线段几何。

### 分段曲线上的跨段递推

**When useful:** 轨迹由直线、圆弧、样条或螺线拼接，长链同时覆盖多个分段。

**Why useful:** 每段保留最自然的参数化，并通过边界分类复用同一状态接口。

**Limitations:** 状态组合多；必须自动测位置/切向连续、固定距离和边界前后速度。

### 全景扫描加局部单峰搜索

**When useful:** 目标评估昂贵，但局部峰附近近似单峰。

**Why useful:** 将全局定位和局部精度分开，三分搜索实现简单。

**Limitations:** 粗扫需有分辨率收敛或Lipschitz上界，否则可能漏窄峰；局部单峰要用数据检验。

## 15. Competition Takeaways

1. 碰撞近似必须先用少量全板对有限矩形真值校准，再决定候选圈和邻板窗口。
2. 首次事件代码应完整保存“粗搜→括区间→二分”流程，结果脚本不能硬编码最终时刻。
3. 正文约束索引与代码循环逐项对照；“所有`i,j`”不能在实现中静默退化成`i=0`。
4. 随机优化报告种子、库版本、多次运行分布、最差可行性和确定性网格/局部精化交叉检查。
5. 严格不等式边界应报告安全裕量和数值容差，并区分最小值、下确界与网格最小可行候选。
6. 分段轨迹用自动测试检查每个拼接点的位置、切向、孔距和速度连续性。
7. 全局峰搜索先做网格收敛或上界分析，再在被验证的单峰区间用三分法。
8. 输出表由公开入口直接生成，文件名/格式与附件清单一致，并保留环境锁文件和运行日志。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 盘入模型以阿基米德螺线弧长反解龙头极角 | explicit | 5–7 | 5.1.1–5.1.2 | equations (1)–(4) | notation normalization | N/A for positive evidence | 公式页视觉核验 |
| 初始半径8.8m及龙头板孔距2.86m与表2闭合 | interpretation | 5–7 | 5.1 | equation, table2 | independent calculation | N/A for positive evidence | 两项误差均在舍入量级 |
| 问题二用内圈顶点到外圈板中心线距离判断碰撞 | explicit | 10–12 | 5.2.1–5.2.2 | equations (5)–(6), flowchart | direct transcription | N/A for positive evidence | 阈值0.15m |
| 发布的碰撞判据不是完备的有限矩形相交测试 | criticism | 11, 33–34 | 5.2.1, appendix | equations, `judge_col` | derived interpretation | p.10–13正文、p.33–34完整碰撞函数已审查 | 无限直线、单向两顶点、局部候选 |
| 论文报告首次碰撞时刻412.473838s | explicit | 12 | 5.2.2 | table4, paragraph | direct transcription | N/A for positive evidence | 作者结果 |
| q2公开入口不能推导六位碰撞时刻 | criticism | 53–54 | appendix | `problem2_1.py`, `problem2_2.py` | direct transcription | p.53–54两个完整入口已审查 | 0.1s打印与硬编码分离 |
| 问题三正文约束覆盖所有最内圈板与外邻圈板 | explicit | 14–15 | 5.3.1 | equation (7) | notation normalization | N/A for positive evidence | 时间范围为进入空间前 |
| 问题三代码把正文全内圈约束缩成仅龙头板 | criticism | 34, 54–55 | appendix | `min_dis`, `problem3.py` | direct transcription | p.34及p.54–55完整函数/入口已审查 | 固定使用`pos[0]`、`pos[1]` |
| 论文报告最短螺距0.450337m | explicit | 16 | 5.3.2 | paragraph | direct transcription | N/A for positive evidence | 作者称PSO+变步长 |
| 公开q3入口的0.001m网格不能产生0.450337m | criticism | 55 | appendix | `min_pitch(0.45,0.46,0.001)` | direct transcription | p.54–55完整问题三入口已审查 | 细化运行不可得 |
| PSO采用40粒子、50代、权重0.8/0.5/0.5 | explicit | 16, 54 | 5.3.2, appendix | paragraph, code | direct transcription | N/A for positive evidence | 无种子 |
| 图15给出最小间距随螺距近似单调线性趋势 | explicit | 17 | 5.3.3 | figure15, paragraph | direct transcription | N/A for positive evidence | 无数据表 |
| 调头路线由盘入螺线、两段相切圆弧和盘出螺线组成 | explicit | 18–23 | 5.4.1–5.4.2 | figures16–18, equations (8)–(14) | notation normalization | N/A for positive evidence | 关键几何页视觉核验 |
| 调头角度和圆半径的独立计算与正文/代码闭合 | interpretation | 19, 39 | 5.4.2, appendix | equations, constants | independent calculation | N/A for positive evidence | `θ=5.29411765π`, `R1:R2=2:1` |
| 问题四用0.01s位移差分与解析速度交叉检查 | explicit | 26 | 5.4.4 | paragraph | direct transcription | N/A for positive evidence | 未报数值误差 |
| q5在14–15s内用三分搜索得到局部最大把手速度 | explicit | 27–29, 57–58 | 5.5, appendix | figures22–23, `ternary_search` | direct transcription | N/A for positive evidence | 局部单峰图支持 |
| 龙头速度1.246266m/s由2除以1.60479338闭合 | interpretation | 28 | 5.5.2 | paragraph | independent calculation | N/A for positive evidence | 复算1.246266357 |
| q5的全局峰结论依赖粗网格和经验时段缩减 | criticism | 27–29, 56–58 | 5.5, appendix | figures, code | derived interpretation | p.27–29模型/图及p.56–58完整入口已审查 | 无全时域解析上界 |
| 附录清单的XLSX与入口实际CSV输出不一致 | criticism | 31, 52–56 | appendices A–B | file list, code | direct transcription | p.31清单与p.52–56全部输出语句已审查 | 结果文件不可得 |
| 在已审查范围内，未发现外部/实物验证和完整随机重复统计 | criticism | 1–58 | full paper and appendices | none found | derived interpretation | p.1–30正文、p.31–58全部代码及现有仓库补充物已审查 | 外部结果/运行日志不可得 |
| 论文整体为部分可复现 | criticism | 1–58 | full paper and appendices | none found | derived interpretation | 58页、OCR/原生文本、关键页图、全部公式/表图/代码及现有补充物已审查 | q1和q5局部可核；q2/q3流程与输出不闭合 |
