# Paper: 反潜航空深弹命中概率的优化问题

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_f7e60ef24995
- Year: 2024
- Problem: D（D033）
- Award: 组委会官方展示匹配；具体奖项等级未核验
- Provenance tier: O: 年份、代码与官方展示匹配，官方展示不证明奖级
- Source file: literature/raw_papers/2024/D033.pdf
- Source URL: unknown（用户提供并与官方展示交叉匹配的本地副本）
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024dtlw/241104/1977965.shtml
- Pages: 55
- SHA-256: 5bb37151e8c6023ed47b2dd1e553d6fb6d93ebeee0ad1d28feb12dc57a366904
- Extraction method: OCR fallback；原PDF对pypdf报malformed Boolean，先用Ghostscript `pdfwrite`生成临时兼容副本供OCR helper计页，原件与副本均55页且72 DPI下55/55页逐像素一致；Tesseract 5.5.0 `chi_sim+eng`、250 DPI、PSM 3，质量记录重新锚定原PDF/SHA
- Extraction quality: OCR 55/55页成功，37,392个可见字符，中位数720字符/页，无page error；公式和p.24-55 MATLAB长代码均以原PDF视觉核验
- Page convention: 1-based physical PDF pages
- Visually checked pages: p.1-55全页缩略图；重点核验p.1-2题设/结论，p.4-14二维概率区域和定理，p.15-20截尾深度积分与数值最优，p.21-22九弹阵列，p.24-38单弹代码、p.39-55九弹积分/加权代码；p.1-2、4-5、8、10、12-15、18-22、24-25、28、35、38-39、54-55另以160 DPI核字
- Unresolved extraction ambiguities: OCR对积分上下限、`l/1`、`I/1`及代码变量有混淆；报告只转写经原页确认的结构。附录为代码截图而非源`.m`，未实际执行整份问题二/三程序
- Supplemental artifacts: PDF内含问题一和问题二五段函数、问题三九弹积分代码；没有独立`.m`、运行日志、积分收敛表或输出数组

## 1. Problem Archetype

本文是“定位误差概率建模—几何膨胀命中区域—截尾正态积分—连续参数搜索—多资源空间部署”的概率优化问题：

- 水平误差为各向同性二维正态，潜艇长方形与杀伤圆的Minkowski和构成圆角矩形命中域；
- 深度误差为左截尾正态，把水平命中条件按引爆深度分段后做三重积分；
- 单弹优化投点与引爆深度，多弹优化3×3阵列间距和共同引爆深度。

问题一的“看哪打哪”和航向无关结论建立在水平误差同方差、独立且零均值的特殊对称性上。问题三只优化九个命中域不重叠/相切的3×3方案，论文明确把重叠情形留待研究，因此0.3232不是完整可行域上的已证全局最大值。

## 2. Problem Decomposition

1. **无深度误差单弹**：按引爆深度相对潜艇上下表面和杀伤半径分5段，写出水平圆角矩形/矩形命中域概率；证明最优水平投点为(0,0)，引爆深度在潜艇上下表面之间。
2. **有深度误差单弹**：令实际中心深度`Z`服从下限120 m的截尾正态，把条件水平概率乘深度密度分段积分；先1 m粗网格，再0.01 m细网格求`d=157.56 m`。
3. **九弹阵列**：先限定各弹命中域不重叠，取最小间距`a=L+2R=140 m,b=W+2R=60 m`；利用正态对称性只算代表位置并按1/2/4倍加权，搜索共同深度得到157.50 m和0.3232。

问题二沿用问题一的水平最优结论是合理的，因为深度误差与水平误差独立。问题三将“互斥命中域概率相加”误写为“深弹相互独立”；共享同一潜艇位置的命中事件并不独立。

## 3. Data Processing

本文没有经验数据清洗。数值处理包括：

- 参数硬编码：`L=100,W=20,H=25,R=20,σ_xy=120,h0=150,σ_z=40,l=120`，单位均为m；
- 深度密度按`1/[1-Φ((l-h0)/σ_z)]`归一化；
- 水平圆角矩形分左圆帽、中矩形、右圆帽积分；
- 问题二侧向部分用`dx=dy=dz=0.5 m`黎曼和，深度`d`先1 m后0.01 m搜索；
- 问题三用`dx=dy=dz=1 m`，通过对称位置加权减少重复积分。

没有积分网格收敛、上限截断误差、浮点容差或替代积分器比较。输出到4位小数不能解释为4位有效精度。

## 4. Models Used

### 二维正态定位与圆角矩形命中域

**Purpose:** 计算固定深度条件下单弹水平命中概率并优化投点。

**Inputs:** 投点`t,s`、`L,W,R,σ`。

**Outputs:** `p(t,s)`及`p(0,0)=0.0837`。

**Why selected:** 触发/定深引信和杀伤球使潜艇中心可命中区域等于长方形与半径R圆的几何膨胀。

**Important assumptions:** X/Y独立同方差正态；潜艇静止；杀伤范围为球；定位均值无偏。

**Key equations or mathematical structure:** `f(x,y)=exp[-(x²+y²)/(2σ²)]/(2πσ²)`，对圆角矩形积分。

**Implementation notes:** 附录1把三块积分相加；独立一维数值积分复算为0.08373364。

### 水平投点最优与航向不变性

**Purpose:** 证明无需数值搜索`t,s,θ`。

**Inputs:** 各向同性零均值高斯和固定形状命中域。

**Outputs:** 最优`t=s=0`；概率与潜艇航向无关。

**Why selected:** 对称单峰密度下，固定长度积分区间居中取最大；旋转不改变各向同性密度。

**Important assumptions:** 两水平误差方差相等；若协方差非球形或有偏，结论不再自动成立。

**Key equations or mathematical structure:** 对积分区间平移求导，再逐轴居中。

**Implementation notes:** 正文给引理和累次积分证明，没有对非各向同性误差作敏感性。

### 截尾正态深度与分段三重积分

**Purpose:** 处理中心深度不确定并优化定深引信。

**Inputs:** `h0=150,σ_z=40,l=120,d`以及条件水平命中域。

**Outputs:** `P(A;d)`和`d*=157.56,P*=0.0586`。

**Why selected:** 深度方向独立，可对条件水平概率按截尾深度密度积分。

**Important assumptions:** 深度与水平独立；截尾正态正确；参数已知且无估计误差。

**Key equations or mathematical structure:** 五段`P(A|Z=z,d)`与`f_trunc(z)`的积分。

**Implementation notes:** 附录把五个d区间写成x2-x6函数；圆帽区域用固定0.5 m黎曼网格，未做网格收敛。

### 九弹3×3互斥阵列

**Purpose:** 最大化至少一弹命中概率。

**Inputs:** 九个投点、共同d；论文限制`a≥L+2R,b≥W+2R`。

**Outputs:** `a=140,b=60,d=157.50,P=0.3232`。

**Why selected:** 在命中域不重叠子空间中，离定位中心越近概率越高，故取最小允许间距和中心对称3×3阵列。

**Important assumptions:** 只考虑互斥命中域；爆炸互不影响；共同深度；不研究重叠覆盖的联合概率。

**Key equations or mathematical structure:** 互斥区域并概率`Σp_i`，代码利用中心/边/角的1/2/4对称权重。

**Implementation notes:** 正文称事件独立，但代码用概率求和；求和成立的理由是区域互斥而不是独立。1 m积分网格未验证。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 数值搜索水平投点 | rejected analytically | 单弹水平优化 | 对称高斯可证明(0,0)最优 | 引理/定理 | 非球形误差无比较 | 在给定特殊假设下合理 |
| 五段引爆深度模型 | selected | 双引信几何 | 引爆深度跨上下表面/半径时命中机制改变 | 几何图1-6 | 边界连续性数表未报 | 分段结构必要 |
| 截尾正态 | selected | 深度误差 | 题目给定下限与正态参数 | 归一公式 | 其他尾部模型未比较 | problem-provided |
| 解析三重积分 | not available | 问题二概率 | 表达式复杂 | not reported | 高精度自适应积分对照 | 作者改用黎曼和/积分函数 |
| 粗到细d网格 | selected | 引信优化 | 先定位峰区再精化 | 图17-18 | dx/dy/dz收敛未报 | d步长收敛不等于积分收敛 |
| 不重叠3×3阵列 | selected conditionally | 九弹部署 | 子空间内最近原点 | 位置单调推理 | 重叠/旋转/非矩形阵列未求 | 只是一类可行方案 |

## 5. Model Pipeline

问题一先把物理命中条件转成水平几何区域，再用高斯概率和对称性消去`t,s,θ`；问题二增加独立深度变量并分段积分；问题三复制单弹区域并用空间阵列合并。

接口风险有两点：固定0.5/1 m黎曼网格的误差没有传入最优值；问题三从“至少一弹命中”缩成“不重叠3×3阵列”，没有证明全局最优。

## 6. Model Improvements

- 从二维定位扩展到三维截尾深度，能表达实际深度下限；没有分布参数敏感性。
- 用解析对称性消去水平投点和航向，减少数值维数；只适用于各向同性误差。
- 对d用粗到细网格，提高峰位置分辨率；积分网格仍固定。
- 九弹代码利用对称权重减少重复积分；没有覆盖重叠阵列和其他packing。

## 7. Parameter Estimation and Optimization

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| L,W,H | 潜艇长宽高 | m | p.2/p.14 | 100,20,25 | problem-provided | N/A - given | no | 刚性长方体 |
| R | 杀伤半径 | m | p.2 | 20 | problem-provided | N/A - given | no | 球形范围 |
| σ_xy | 水平定位SD | m | p.2/p.24 | 120 | problem-provided | N/A - given | no | X/Y同方差 |
| h0 | 中心深度定位值 | m | p.19/p.24 | 150 | problem-provided | N/A - given | no | OCR易误读，原页确认 |
| σ_z | 深度定位SD | m | p.19/p.24 | 40 | problem-provided | N/A - given | no | 与水平独立 |
| l | 实际深度下限 | m | p.19/p.24 | 120 | problem-provided | N/A - given | no | 左截尾 |
| d problem1 | 最优深度区间 | m | p.14 | [137.5,162.5] | data-estimated | 几何定理 | no | 实为model-derived analytic result；当前schema无对应类别，故在Notes保留边界 |
| d problem2 | 单弹最优引爆深度 | m | p.19-20 | 157.56 | data-estimated | 1 m→0.01 m grid | partial | 数值模型输出 |
| d problem3 | 九弹最优共同深度 | m | p.22 | 157.50 | data-estimated | 1 m grid/code output | no | 小数精度超过积分网格证据 |
| a,b | 阵列间距 | m | p.20-22 | 140,60 | author-assumed | 非重叠最小边界 | no | 限定子空间边界解 |
| Δx,Δy,Δz q2 | 黎曼网格 | m | p.25-38 code | .5,.5,.5 | algorithm hyperparameter | fixed | no | 无收敛表 |
| Δx,Δy,Δz q3 | 九弹黎曼网格 | m | p.39-54 code | 1,1,1 | algorithm hyperparameter | fixed | no | 比单弹更粗 |

## 8. Validation

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 问题一概率 | L2 independent quadrature sanity check | theoretical | probability | 1 | 0.08373364≈0.0837 | none | 同一数学模型 | 支持附录二维积分算术 |
| 截尾密度 | L2 normalization check | theoretical | normalizing constant | 1 | `1-Φ(-.75)=.77337`, multiplier1.29304 | none | 不验证分布适用性 | 支持密度归一 |
| 水平投点最优 | L2 analytic symmetry proof | theoretical | derivative/sign | N/A | (0,0) | 非球形误差未覆盖 | 强依赖各向同性 | 支持给定假设下的最优 |
| d搜索 | L3 grid refinement | same model | peak d/P | 2 grids | coarse[87.5,180], fine[156,160]→157.56 | integral grid unchanged | 未报峰值对Δx/y/z敏感性 | 只支持当前积分离散下峰区 |
| 九弹结果 | L2 internal code result | same model | summed probability | 1 grid | .3232 | overlapping placements not tested | 仅互斥阵列子空间 | 不能称完整问题全局最优 |
| 外部验证 | not reported | unknown | not reported | not reported | not reported | not reported | 无真实投放/独立仿真 | 不支持现实命中率 |

## 9. Sensitivity and Robustness

唯一明确扰动是d搜索步长从1 m缩到0.01 m。作者没有改变水平/深度误差、杀伤半径、潜艇尺寸、截断下限、积分网格或阵列拓扑。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| d步长 | 1 m | .01 m in[156,160] | deterministic grid | argmax d/P | 157.56/.0586 | no | 精化峰位置，不验证积分误差 |

在已审查范围内，未发现分布参数、物理参数、积分网格或阵列几何的敏感性；审查覆盖p.1-23正文和p.24-55全部代码。

## 10. Visualization Strategy

图1-6展示五种深度情形，图7-16展示命中域包含关系和三维分段，图17-18展示粗细d曲线，图19展示3×3阵列。几何图对理解积分域很有效；数值图没有误差条、网格对照或相邻候选差值，无法确认峰值精度。

## 11. Writing Structure

正文按三问逐层扩展，问题一给定理证明，问题二给完整分段公式，问题三复用并扩展；附录代码很长但与公式对应。缺点是把互斥事件误称独立、问题三只完成限定情形却在摘要中表述为最大方案，且没有积分收敛/运行状态。

## 12. Strengths

- 把触发/定深引信条件转成可追溯的几何概率区域。
- 利用各向同性正态对称性解析证明水平投点和航向结论。
- 截尾正态归一和分段积分结构明确。
- 问题一0.0837可由独立一维积分高精度复算。
- 附录保留问题二/三大部分数值实现，便于审计。

## 13. Weaknesses

问题三没有覆盖重叠阵列或其他几何，不能视为全问题最优；事件“独立”的叙述与概率求和逻辑不符。问题二/三使用固定黎曼网格但不做收敛，输出小数精度过强；没有参数不确定性和外部物理验证。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | N/A - problem constants only | p.1-24参数 | 不依赖外部数据 |
| Code availability | partial | p.24-55 MATLAB截图 | 无`.m`，需转录；长代码重复且末尾有残留片段 |
| Dependency / environment information | not reported | MATLAB函数名，无版本 | 数值积分行为/性能不可锁定 |
| Random seed | N/A - deterministic integration | p.24-55 | 无随机模拟 |
| Hard-coded constants | extensive | 参数、d范围、黎曼步长、阵列 | 无敏感性 |
| Formula-to-code consistency | mostly consistent with wording issue | p.4-22 vs p.24-55 | 分段/归一/阵列加权对应；“独立”不对应求和理由 |
| Code-to-result consistency | partially assessable | 0.0837独立复算；问题二/三未执行 | 长代码截图/无收敛结果 |
| Overall reproducibility | partially reproducible | 审查55页、全部公式/代码 | 问题一可复算；问题二/三需转录且精度边界缺失 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 问题一最大概率 | p(0,0)=.0837 | 对圆角矩形一维积分得.0837336434 | pass | p.14 / p.24 code | 高精度闭合 |
| 截尾归一 | l=120,h0=150,σz=40 | denominator=.77337265,multiplier=1.2930377 | pass | p.19/p.24 | 公式正确 |
| 问题二搜索范围 | coarse[87.5,180],fine[156,160] | 157.56位于细区间 | pass | p.19-20 / p.35 code | OCR 137误读已由原页消歧 |
| 引爆深度相对位置 | d*=157.56,h0=150,H=25 | 位于上下表面137.5-162.5之间 | pass | p.1,p.14,p.19 | 几何一致 |
| 九弹间距 | a=L+2R,b=W+2R | 100+40=140；20+40=60 | pass | p.20-22 | 非重叠边界 |
| “事件独立”与求和 | 命中事件独立且总概率相加 | 独立并事件应`1-Π(1-p_i)`；相加只因命中域互斥 | fail | p.20-22 | 结论理由写错 |
| 同概率独立参考 | 单弹峰.0586、9弹 | 若九个同概率独立则`1-(1-.0586)^9=.4193`，非.3232 | concern | p.1 | 实际各弹p不同且事件共享位置；仅说明不能用独立解释 |
| 九弹概率上界 | 九弹总.3232 | ≤9×.0586=.5274，且<1 | pass | p.1 | 粗上界闭合 |
| 深度网格精度 | d=157.50报两位小数 | 问题三积分网格为1m且无收敛 | concern | p.22,p.39-54 | d搜索/积分步长口径不充分 |
| 问题三完整性 | 摘要称最大方案 | 正文明确重叠命中域“有待进一步研究” | fail (scope) | p.22 | 只能称限定子空间best-found |

## 14. Reusable Techniques

### 几何膨胀转概率积分

**When useful:** 目标有有限尺寸、攻击有作用半径、定位误差有密度。

**Why useful:** 把“是否命中”转成目标形状的Minkowski和，再积分。

**Limitations:** 复杂姿态/非球形作用域需重新构造几何。

### 对称性降维

**When useful:** 误差密度零均值、各向同性，命中域中心对称。

**Why useful:** 可解析消去投点/航向变量并减少阵列积分。

**Limitations:** 有偏、异方差或相关误差下必须重新优化。

### 截尾分布条件积分

**When useful:** 物理变量有硬下限/上限且测量近似正态。

**Why useful:** 保留边界条件并正确归一。

**Limitations:** 参数估计误差和尾部模型需要敏感性。

### 阵列对称权重

**When useful:** 规则阵列和中心对称密度使多个位置等价。

**Why useful:** 减少重复三重积分。

**Limitations:** 只适用于相同几何和互斥/正确并事件聚合。

## 15. Competition Takeaways

1. 先把有限目标与杀伤半径做几何膨胀，再对定位密度积分。
2. 对称性证明必须明确同方差、零均值和独立条件，避免过度推广。
3. 截尾正态先核归一常数，再写条件概率积分。
4. 粗细搜索同时检查目标参数步长和积分网格收敛，输出位数服从误差证据。
5. 多资源并事件区分“互斥”和“独立”：互斥求和，独立用乘积补集。
6. 限定阵列/不重叠子空间的解统一写best-found，不宣称全局最优。
7. 把分布、物理参数和阵列几何纳入敏感性，不只精化单一d。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 水平误差为独立同方差正态，深度误差独立截尾正态 | explicit | 2,14,19 | 题设/5.1/5.2 | paragraphs/equations | direct transcription | N/A for positive evidence | 最优性条件 |
| 五种引爆深度情形对应不同命中域 | explicit | 4-8 | 5.1.1 | figures1-6/equations2-10 | notation normalization | N/A for positive evidence | 几何主线 |
| 最优水平投点为(0,0)，航向无关 | explicit | 9-14 | theorem1-3 | equations11-17 | direct transcription | N/A for positive evidence | 依赖各向同性 |
| p(0,0)=.0837336434可独立复算 | interpretation | 14,24 | 5.1.2/appendix1 | equation/code | independent calculation | N/A for positive evidence | 与.0837一致 |
| 问题二截尾密度归一常数为1.2930377 | interpretation | 19,24 | 5.2.1/appendix | equation/code | independent calculation | N/A for positive evidence | l=120,h0=150,σ=40 |
| 问题二用1m粗搜和.01m细搜得到157.56/.0586 | explicit | 19-20,35 | 5.2.2/appendix2.5 | figures17-18/code | direct transcription | N/A for positive evidence | 原页消歧 |
| 在已审查范围内，未发现dx/dy/dz积分网格收敛 | criticism | 19-55 | 5.2-5.3/appendix | none found | derived interpretation | 审查正文数值求解、图17-18和p.24-55全部代码 | 仅d步长精化 |
| 九弹限定为命中域不重叠且取a=140,b=60 | explicit | 20-22 | 5.3 | figure19/paragraph | direct transcription | N/A for positive evidence | 条件子空间 |
| 九弹命中事件共享同一潜艇位置，不能称独立 | criticism | 20-22 | 5.3 | paragraph/equations | derived interpretation | N/A for positive evidence | 命中域互斥才允许概率相加 |
| 九弹代码按中心/边/角的对称倍数求和 | explicit | 39-54 | appendix3 | code | derived interpretation | N/A for positive evidence | 权重1/2/4 |
| 九弹报告d=157.50,P=.3232 | explicit | 1,22 | 摘要/5.3.2 | paragraph | direct transcription | N/A for positive evidence | 当前积分网格输出 |
| 正文明确重叠命中域情形未研究 | criticism | 22 | 5.3.2 | paragraph | direct transcription | N/A for positive evidence | 摘要的最大方案需限域 |
| 问题一引爆最优区间为137.5-162.5m | interpretation | 14 | 5.1.2 | paragraph | independent calculation | N/A for positive evidence | h0±H/2 |
| 157.56位于上下表面之间 | interpretation | 1,14,19 | 摘要/5.1/5.2 | numbers | independent calculation | N/A for positive evidence | 几何闭合 |
| 在已审查范围内，未发现σ、σz、R、尺寸或阵列的敏感性 | criticism | 1-55 | full paper | none found | derived interpretation | 审查23页正文和32页代码 | 只有d网格精化 |
| 在已审查范围内，未发现真实投放或独立模拟验证 | criticism | 1-55 | validation/evaluation | none found | derived interpretation | 审查全文、评价、参考文献和全部附录 | 仅同模型算术 |
| 论文仅部分可复现 | criticism | 1-55 | full paper/appendix | none found | derived interpretation | 55页及全部代码；无`.m`/运行输出 | 问题一可独立复算，问题二/三未完整执行 |
