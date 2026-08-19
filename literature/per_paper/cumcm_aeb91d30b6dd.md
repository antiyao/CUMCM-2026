# Paper: 波浪能装置输出功率最大化模型

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_aeb91d30b6dd`
- Year: 2022
- Problem: A（波浪能装置的设计）
- Award: 奖级未核验。只能确认本地文件的年份、题号与组委会官方展示代码 A022 一致，不能由展示状态推断奖项。
- Provenance tier: O（official display，官方展示匹配；本地 PDF 30 页与官方页图数量一致，奖级未知）
- Source file: `literature/raw_papers/2022/A022.pdf`
- Source URL: unknown
- Verification source: `https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2022qgdxssxjmjslwzs/221106/1820293.shtml`
- Pages: 30
- SHA-256: `165d00ec4d8064f126bd6800cd81dbf90b6b020d6c408daa21a2f50873958a96`
- Extraction method: OCR fallback（Tesseract 5.5.0，`chi_sim+eng`，250 DPI，PSM 3）+ manual visual review
- Extraction quality: 内嵌文本为 0；OCR 30/30 页均有文本，19908 个非空白字符，中位数 558 字符/页，无页级失败。OCR 可支持检索和正文阅读，但公式、上下标、希腊字母、单位与 MATLAB 代码均以渲染页为准。
- Page convention: 1-based physical PDF pages
- Visually checked pages: pp.1–30 全页渲染巡检；重点复核 pp.5–8（符号、平衡与两自由度方程）、pp.8–11（解析功率与两类优化图）、pp.11–16（转动惯量、耦合方程、结果表与双阻尼优化）、pp.16–19（频谱与稳定性图）、pp.21–30（支撑文件清单、公式引证和全部可见代码）；pp.6、8、16–19、23–30 另以高分辨率渲染核字。
- Unresolved extraction ambiguities: OCR 对 pp.11–13 的长惯量/转动方程和 pp.27、30 的长代码行断行明显；本报告只转写视觉上可确认的结构。图 17 的纵轴量级与正文结论存在源内异常，非 OCR 问题。
- Supplemental artifacts: 论文 p.21 列出 `result1-1.xlsx`、`result1-2.xlsx`、`result3.xlsx`、问题 4 数据表及 10 个 `.m` 文件；当前仓库未提供这些独立文件。PDF 附录只含代码截图/文本，未含结果工作簿和完整敏感性代码，故相关复现为 `not assessable` 或部分可审计。

## 1. Problem Archetype

本文是“机理动力学 + 数值仿真 + 参数优化”的混合问题，包含以下原型：

- **多自由度动力系统（multi-degree-of-freedom dynamical system）**：把浮子和振子的垂荡写成二自由度常微分方程（ODE），再把垂荡与纵摇写成八状态耦合系统。
- **受迫振动与稳态响应**：在线性阻尼情形使用复振幅求稳态解析解，以激励频率作为稳态响应频率。
- **非线性仿真**：相对速度幂次阻尼和垂荡—纵摇耦合没有闭式解时，用 MATLAB `ode45`。
- **有界参数优化**：对直线/旋转阻尼系数、非线性比例系数和幂指数作网格遍历，目标为稳态区间平均 PTO 输出功率。
- **模型适用域检查**：检查浮子浸没边界、稳态频率、小位移/小角假设，并改变激励力、力矩和弹簧刚度观察输出。

主要迁移价值不是某个具体最优阻尼值，而是“物理受力建模 → 可解析特例 → 数值互证 → 难例网格优化 → 假设适用域检查”的完整链条。证据边界是：所有验证都来自同一组方程和作者代码，没有独立实验或真实装置数据。

## 2. Problem Decomposition

论文按四问分解：

1. **仅垂荡、给定阻尼**：分别处理常量阻尼和 \(\eta |\Delta v|^{1/2}\) 型非线性阻尼，输出 40 个波浪周期内浮子/振子的位移和速度。
2. **仅垂荡、优化阻尼**：常量阻尼先推导稳态解析功率，再以 `ode45 + trapz` 数值积分互证；非线性阻尼则遍历比例系数 \(\eta\) 与幂指数 \(\alpha\)。
3. **垂荡与纵摇耦合**：先根据小量假设将整体纵摇与振子相对运动分层计算，引入以转轴为原点的平动非惯性系，输出垂荡/纵摇状态。
4. **双阻尼优化**：遍历直线阻尼 \(\eta_i\) 与旋转阻尼 \(\eta_j\)，在发现最优 \(\eta_j\) 位于上界后固定它，再细化 \(\eta_i\)。

显式管线为：

附件水动力参数与装置几何
→ 静水平衡/受力分析
→ 垂荡 ODE
→ 线性稳态解析解与数值积分互证
→ 非线性阻尼网格优化
→ 小量假设检查
→ 垂荡—纵摇近似耦合 ODE
→ 双阻尼网格优化
→ 频谱、边界与参数扰动检查。

该分解把可解析与不可解析部分分开，逻辑清楚；但问题三代码模拟到 400 s（约 109 个周期），而题目要求的 40 周期约为 146.5 s，正文没有说明延长仿真的目的与报告口径。

## 3. Data Processing

本文没有传统观测数据清洗；其“数据处理”主要是参数整理、稳态截取和数值输出后处理。

- **参数按工况切换**：代码对不同附件工况分别硬编码 \(\mu,\lambda_i,\lambda_j,f,L,\omega,J\) 等值。pp.22–30 可见至少三组工况；没有统一输入表或参数读取函数。
- **初始状态**：全部 ODE 以零位移、零速度开始；静水平衡通过 \(h_0\) 另行计算。
- **时间离散**：主程序普遍使用输出网格 `0:0.2:T`；`ode45` 内部仍为自适应步长，0.2 s 是请求的输出采样间隔，不是严格积分步长。
- **稳态窗口**：功率积分使用索引 1000:2000，对应约 199.8–399.8 s。`trapz(P)/1000` 等价于 \(0.2\,\mathrm{s}\times\mathrm{trapz}(P)/(200\,\mathrm{s})\)，因而在该固定网格上量纲与平均值缩放正确。
- **优化网格**：常量阻尼先粗看 \([0,10^5]\)；非线性附录代码展示 \(\alpha=0:0.05:1\)、\(\eta=30000:500:100000\)。最终 \(\alpha=0.370\) 不在该网格上，论文称反复缩小区间，但未给细化代码或完整网格历史。
- **结果抽样**：问题一/三只在 10、20、40、60、100 s 列表；主要动态形态由全时程图展示。

没有缺失值、异常值、尺度标准化或训练/测试划分。所有数值来自模型生成，不应称为独立数据验证。

## 4. Models Used

### 二自由度垂荡模型

**Purpose:** 计算浮子与振子的垂荡响应，并建立直线阻尼功率目标。

**Inputs:** 浮子/振子质量、附加质量、兴波阻尼、静水恢复、弹簧刚度、波浪激励 \(f\cos\omega t\)、PTO 阻尼。

**Outputs:** \(x_1,x_2,\dot x_1,\dot x_2\) 以及相对速度/位移。

**Why selected:** 论文明确把仅垂荡装置视为多自由度系统，并依据逐部件受力直接列牛顿方程（pp.3, 5–6）。

**Important assumptions:** 无黏无旋水体；忽略未给出的结构质量/摩擦；浮子不越出线性静水恢复适用区；附件水动力参数可直接代表该线性工况。

**Key equations or mathematical structure:** 常量阻尼时，

\[
\begin{cases}
(m_f+\mu)\ddot x_1+\eta_i(\dot x_1-\dot x_2)+\lambda_i\dot x_1+k(x_1-x_2)+\rho g\pi R_f^2x_1=f\cos\omega t,\\
m_z\ddot x_2+\eta_i(\dot x_2-\dot x_1)+k(x_2-x_1)=0.
\end{cases}
\]

非线性阻尼把 \(\eta_i\Delta v\) 替换为 \(\eta_i\Delta v|\Delta v|^{\alpha}\)；问题一第二小问 \(\alpha=0.5\)。

**Implementation notes:** `ode45` 输出网格 0.2 s。附录 `func1.m` 只展示了含 `sqrt(abs(delta_v))` 的非线性版本，因此问题一常量阻尼表无法由所示 `code1.m + func1.m` 原样复现。

### 线性稳态复振幅模型

**Purpose:** 为问题二常量阻尼求出可审计的最优阻尼和最大平均功率。

**Inputs:** 与二自由度模型相同的线性工况参数。

**Outputs:** 复振幅差 \(|x_1-x_2|\)、平均功率 \(\bar P\)、解析最优 \(\eta_{i,\mathrm{best}}\)。

**Why selected:** 论文利用线性受迫振动在稳态与激励同频，把微分方程转为 2×2 复数线性方程；这是常量阻尼特例可获得闭式基准的原因（pp.7–9, 21–22）。

**Important assumptions:** 已进入唯一稳定周期稳态；线性模型成立；只计算阻尼器耗散功率。

**Key equations or mathematical structure:** 令

\[
A=-\omega^2(m_f+\mu)+k+\rho g\pi R_f^2,\quad B=-\omega^2m_z+k,
\]
\[
C=AB-k^2,\quad D=\omega^2\lambda_i,\quad E=A+B-2k,
\]

则

\[
\bar P=\frac{1}{2}\frac{\omega^6m_z^2f^2\eta_i}
{(C-D\eta_i)^2+\omega^2(E\eta_i+B\lambda_i)^2},
\]

\[
\eta_{i,\mathrm{best}}=
\sqrt{\frac{C^2+\omega^2B^2\lambda_i^2}{D^2+\omega^2E^2}}.
\]

**Implementation notes:** 独立代入附录常量得到 \(37193.81188797\ \mathrm{N\,s/m}\) 和 \(229.33393984\ \mathrm W\)，与正文逐位一致。

### 非线性功率积分与网格搜索

**Purpose:** 在无闭式解时优化 \(\eta_i,\alpha\)，以及在耦合模型中优化 \(\eta_i,\eta_j\)。

**Inputs:** ODE 时程、阻尼参数网格与稳态窗口。

**Outputs:** 网格上的平均功率曲面和网格最佳点。

**Why selected:** 作者明确指出非线性阻尼和垂荡—纵摇模型难以获得解析解，并以线性特例的解析/数值接近作为使用数值积分的依据（pp.3, 10, 15）。

**Important assumptions:** 200–400 s 已稳态；离散网格足以定位峰值；目标面在细化区间内平滑；边界外不会出现更优的物理解。

**Key equations or mathematical structure:** 非线性直线阻尼

\[
P_i(t)=\eta_i|\Delta v|^{2+\alpha},
\]

双阻尼模型

\[
P(t)=\eta_i\dot x_{\mathrm{rel}}^2+\eta_j(\dot\theta_2-\dot\theta_1)^2,
\qquad \bar P=\frac1T\int P(t)\,dt.
\]

**Implementation notes:** 线性数值最优为 \(3.72\times10^4\ \mathrm{N\,s/m}\)、229.497276 W；非线性报告 \(\eta=9.75\times10^4\)、\(\alpha=0.370\)、230.12739 W；双阻尼报告 \(\eta_i=5.93\times10^4\)、\(\eta_j=10^5\)、322.128796 W。后两者的完整细化路径/数据表不可得。

### 垂荡—纵摇近似耦合模型

**Purpose:** 在浮子和振子同时垂荡、纵摇时计算八个状态，并为双阻尼优化提供正向模型。

**Inputs:** 几何质心距离、转动惯量、静水恢复力矩、纵摇附加惯量/阻尼、激励力矩、两类 PTO 阻尼。

**Outputs:** 浮子/振子的垂荡位移与速度、纵摇角位移与角速度。

**Why selected:** 直接分析转轴/中轴全部作用力所需信息不足，作者先检查相对垂荡与角位移为小量，再把整体纵摇和振子在平动非惯性系中的相对运动分开（pp.1, 3, 12–13）。

**Important assumptions:** 纵摇不显著改变垂荡；浮子与振子可先视为整体求纵摇；角位移小；相对垂荡位移小；未建模部件和摩擦可忽略。

**Key equations or mathematical structure:** 论文先由面积加权和平行轴定理计算 \(h_1,h_2,h_3,I_z,I_f\)，再形成整体角动量方程和振子相对角运动方程；完整式见 pp.12–13。代码状态向量为 \((x_1,\dot x_1,\theta_1,\dot\theta_1,x_{\rm rel},\dot x_{\rm rel},\theta_2,\dot\theta_2)\)。

**Implementation notes:** `func3.m/func4.m` 把重力、平动惯性、离心项、弹簧/阻尼力矩写入八状态 ODE。正文把表 4 的“振子绝对垂荡位移”与代码中的相对状态混用，符号口径需要谨慎。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 二自由度牛顿 ODE | selected | 仅垂荡响应 | 装置可视为多自由度线性/非线性受迫系统 | 受力结构与边界检查 | 无实验动力响应对照 | 结构可解释，但参数完全沿用附件且没有不确定性传播 |
| 稳态复振幅闭式解 | selected for constant damping | 常量阻尼优化基准 | 线性稳态与激励同频，可写解析响应 | 与数值积分功率相差约 0.0712% | 无独立软件/实验基准 | 是本文最强的公式—数值内部互证，但仍是同一模型证据 |
| `ode45 + trapz` | selected | 非线性和耦合模型的功率计算 | 闭式解困难；线性特例表明数值法接近解析法 | 线性特例 229.33394 W vs 229.49728 W | 步长收敛、容差和替代求解器比较未报告 | 选择理由合理，精度证据只覆盖一个线性工况 |
| 全有界网格遍历 | selected | 寻找阻尼参数最好点 | 参数维数低，可先全局后局部细化 | 功率曲面和局部峰值图 | 细化网格、计算误差、连续全局最优证明未报告 | 只能称网格最佳；\(\eta_j\) 位于上界，最优性边界尤其弱 |
| 完全耦合刚体/多体模型 | considered but not implemented | 垂荡—纵摇联合建模 | 转轴/中轴受力繁琐且信息未知 | not reported | 与简化模型的误差比较 | 合理降低复杂度，但缺少误差阶或适用域的定量验证 |
| 小量解耦 + 平动非惯性系 | selected | 八状态近似耦合 | 相对位移和角位移初算为小量 | 时程、角度上界和参数扰动图 | 对强波浪及完整耦合模型的对照 | 可迁移的建模折中；证据只支撑已扫描范围内的内部一致性 |

## 5. Model Pipeline

模型关系是“基线—互证—扩展—优化”：

1. 静水平衡给出浸没边界 \(h_0\)。
2. 二自由度 ODE 生成给定阻尼下的垂荡时程。
3. 常量阻尼分支同时走解析稳态和数值积分，得到内部基准。
4. 将数值法扩展到速度幂次阻尼，网格搜索 \((\eta,\alpha)\)。
5. 用前述时程判断相对运动为小量，构建垂荡—纵摇近似耦合系统。
6. 对耦合系统搜索 \((\eta_i,\eta_j)\)，再固定边界上的 \(\eta_j\) 细化 \(\eta_i\)。
7. 用浸没、频谱、小量和四类参数扰动回查模型适用域。

解析分支只校验“线性垂荡 + 常量阻尼”的积分实现，不能自动证明非线性阻尼、纵摇耦合或二维网格搜索正确。模型链也没有把水动力参数误差传递到最优阻尼区间。

## 6. Model Improvements

- **解析—数值双路**：比只给 `ode45` 输出更可审计。独立复算确认解析公式与数值常数一致；线性数值值比解析值高 0.0712%。
- **先检查小量再简化**：论文不是直接声称小角，而是给出相对位移、最大角度和扰动曲线。这个顺序优于无证据线性化，但比值定义和扫描网格没有完整报告。
- **全局粗网格再局部细化**：适合低维参数优化；问题四先观察 \(\eta_j\) 单调，再固定边界细化 \(\eta_i\)。不过边界解应触发扩大上界/物理约束讨论，论文没有做。
- **功率直接由耗散项积分**：避免从能量转换效率的不可得分母出发，目标清楚；但这最大化的是给定线性水动力模型内的阻尼耗散，不等于已验证的实物总转换效率。
- **平动非惯性参考系**：把振子相对浮子的运动写成可求解状态，减少未知转轴作用力；代价是耦合误差没有和更完整模型比较。

## 7. Parameter Estimation and Optimization

常量阻尼的解析最优由闭式公式直接计算；其余优化属于确定性网格搜索，不是统计估计。论文没有求解器容差、误差条或参数置信区间。结果应表述为给定硬编码附件参数、给定稳态窗口和网格下的最好点。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| \(m_f\) | 浮子质量 | kg | pp.22–30 code | 4866 | problem-provided | N/A - given | no | 各工况相同 |
| \(m_z\) | 振子质量 | kg | pp.22–30 code | 2433 | problem-provided | N/A - given | no | 各工况相同 |
| \(\rho\) | 海水密度 | kg/m³ | pp.22–30 code | 1025 | problem-provided | N/A - given | no | OCR 将变量名误作 `tho`，视觉代码为 `rho` |
| \(g\) | 重力加速度 | m/s² | pp.22–30 code | 9.8 | author-assumed | 常数近似 | no | 未讨论 9.8/9.81 差异 |
| \(R_f\) | 浮子半径 | m | pp.22–30 code | 1 | problem-provided | N/A - given | no | 用于静水恢复项 |
| \(k\) | 直线弹簧刚度 | N/m | pp.22–30 code | 80000 | problem-provided | N/A - given | yes | 图 18 扫描约 \(4\times10^4\)–\(8\times10^4\) |
| \(C_k\) | 扭转弹簧刚度 | N·m/rad | pp.25–30 code | 250000 | problem-provided | N/A - given | yes | 符号表写 N·m；图 17 扫描到 \(2.5\times10^5\) |
| \(\mu,\lambda_i,\lambda_j,f,L,\omega,J\) | 工况水动力/激励参数 | mixed | pp.22–30 code | 随附件工况改变 | problem-provided | 按题目附件表选取 | partial | 没有统一输入清单；示例见问题二 \(\mu=1165.992,\lambda_i=167.8395,f=4890,\omega=2.2143\) |
| \(\eta_i\)（问题二线性） | 直线阻尼最优值 | N·s/m | pp.8–10, 24 | 37193.8119 analytic；37200 grid | data-estimated | 闭式极值；数值网格互证 | partial | 数值/解析功率差约 0.0712% |
| \(\eta,\alpha\)（问题二非线性） | 阻尼比例与速度幂指数 | coefficient unit depends on \(\alpha\)；dimensionless | pp.10–11, 24–25 | \(\eta=9.75\times10^4,\alpha=0.370\) | data-estimated | 多轮二维网格细化 | no | 完整细化代码/网格未提供；\(\eta\) 的量纲随 \(\alpha\) 改变，论文未说明 |
| \(\eta_i,\eta_j\)（问题四） | 直线/旋转阻尼 | N·s/m；N·m·s/rad | pp.15–16, 27–30 | \(5.93\times10^4,10^5\) | data-estimated | 101×101 粗网格后局部一维网格 | no | \(\eta_j\) 为允许区间上界；符号表误写旋转阻尼单位为 N·s/m |
| \(\Delta t_{out}\) | ODE 输出采样间隔 | s | pp.22–30 code | 0.2 | algorithm hyperparameter | author setting | no | `ode45` 内部自适应步长，未报告 RelTol/AbsTol |
| 稳态积分窗口 | 平均功率后半段窗口 | s | pp.9–10, 23–30 | about 200–400 | author-assumed | 去除初始瞬态 | partial | 仅用频谱做一次稳态检查，没有比较不同窗口 |
| 网格步长 | 参数搜索分辨率 | mixed | pp.24, 28–29 code | 初始 \(\Delta\alpha=0.05,\Delta\eta=500\)；问题四粗网格 1000、局部 100 | algorithm hyperparameter | coarse-to-fine grid | no | 非线性最终细网格未报告 |
| 小角/小位移 | 解耦假设 | dimensionless/rad | pp.4, 13, 16–18 | 最大角约 6.88°/7.73°；相对位移比声称 0.09–0.10 | author-assumed | 由模型时程回查 | partial | 比值统计口径和完整数据不可得 |

## 8. Validation

本文最强证据是线性特例的解析—数值一致性，以及若干物理/内部 sanity check。它们不使用独立真实数据；所以没有 L5。参数扰动属于 L3，但只展示单条曲线，未给重复、误差、扫描表或结论阈值。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 常量阻尼解析公式与数值积分 | L2 - analytic/numeric consistency | theoretical / same model | 最优功率与阻尼差 | 1工况 | 229.33394 W @37193.81 vs 229.49728 W @37200；功率差约 0.0712% | none reported | 两路共享方程、参数和稳态假设 | 支持该线性工况下积分缩放与峰值位置大体一致，不验证物理模型 |
| 浮子不越出线性浸没区 | L2 - geometric boundary check | same sample | 最大位移 vs \(h_0\) | 4问题的模型输出 | 正文称均小于约 1.00 m | 极端波浪未覆盖 | 依赖同一仿真且未列全时程极值表 | 支持已模拟工况内未触碰所设几何边界 |
| 有限时间后与激励同频 | L2 - spectral sanity check | same sample | 主圆频率 | 1时程 | 0.0891×5π=1.399 rad/s，接近 1.4005 rad/s | none reported | 频率轴换算和窗函数未说明 | 支持问题一所选后半段近似周期稳态 |
| 小角/小位移近似 | L2 - magnitude check | same sample | 最大角、相对位移比 | 1组主要时程 | 6.88°、7.73°；比值声称 0.09–0.10 | 强激励下可能失效 | “小量”阈值与比值统计定义未给 | 只能支持作者工况下的近似量级，不能给误差上界 |
| 激励力/力矩变化下小量保持 | L3 - parameter sweep | same model | 相对位移/相对角位移曲线 | not reported | 图 15–16 在展示范围内单调且仍小 | 范围外未测 | 无网格、基线标记、误差或重复 | 支持展示范围内小量没有明显突变 |
| 弹簧/扭簧参数变化 | L3 - parameter sweep | same model | 平均 PTO 曲线 | not reported | 图 17–18 显示输出强烈变化；小扭簧刚度处称模型崩溃 | 图17量级/基线异常 | 原始表与 `code5.m` 不可得 | 只支持输出对刚度敏感；不支持笼统“鲁棒” |
| 问题四双阻尼最好点 | L1 - objective evaluation | same sample | 网格目标值 | 1 deterministic grid | 322.128796 W at (59300,100000) | 旋转阻尼最佳点位于上界 | 无边界外扫描、容差与数据表 | 只支持所给有界网格中的最好点 |

## 9. Sensitivity and Robustness

作者对四类输入做曲线扫描，但只报告图形和定性语句。严格说，其中激励力/力矩检查的是**近似假设稳定性**，刚度扫描检查的是**输出敏感性**；不能合并为“模型对大多数波浪均鲁棒”。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 波浪垂荡激励力 \(f\) | not marked | 图 15 约 0–2300 N | grid, spacing not reported | 振子相对浮子位移 | 约 0.008–0.055 m，近似线性增加 | no within plotted range | 只说明该扫描内相对位移仍较小；问题三代码基线 3640 N 不在图示范围内 |
| 纵摇激励力矩 \(L\) | 1690 or 2140 N·m in code, not marked in figure | 图 16 约 0–2500 N·m | grid, spacing not reported | 相对角位移 | 约 \(0.3\times10^{-3}\)–\(8.3\times10^{-3}\) rad，近似线性 | no within plotted range | 支持图示范围内小角，但不量化解耦误差 |
| 扭转弹簧刚度 \(C_k\) | 250000 N·m/rad | 图 17 约 0–250000 | grid, spacing not reported | PTO/W | 低刚度区出现约 \(1.5\times10^6\) W 尖峰，随后接近 0；正文称低于阈值时崩溃 | yes / model failure reported | 图形与问题四基线输出 322 W 难以协调；原始代码/表缺失，不能据此声称稳健 |
| 直线弹簧刚度 \(k\) | 80000 N/m | 图 18 约 40000–80000 N/m | grid, spacing not reported | PTO/W | 约 270 W 单调降至约 55 W | no qualitative feasibility change | 输出幅度变化约 80%，说明结果对 \(k\) 高度敏感，不是“输出稳定” |

在已审查范围内，未发现对 ODE 容差、输出步长、稳态窗口、网格分辨率、阻尼上界或水动力参数测量误差的正式敏感性实验；审查覆盖 pp.1–20 正文、pp.21–30 附录代码及当前可用补充材料清单，独立工作簿和 `code5.m/func5.m` 不可得。

## 10. Visualization Strategy

- **时程叠图**（图 1–2、7–11）：展示初始瞬态衰减、相位差和稳态振幅，是检查稳态与小量假设的直接证据。
- **一维/二维功率曲线**（图 3–6、12–13）：先用全局曲面定位区域，再用局部曲线报告峰值，适合低维优化结果展示。
- **频谱图**（图 14）：把“趋于稳态且与激励同频”的假设转为可检查对象，但坐标换算说明不足。
- **参数—输出曲线**（图 15–18）：把适用域与崩溃区显式画出；其中图 17 的异常量级反而暴露了需要复核的模型/代码问题。
- **结果表**（表 1–4）：给 5 个指定时刻的位移/速度/角度，便于核对；但没有列全时程极值、网格最优邻域或误差。

竞赛写作上值得复用“全局曲面 → 局部峰值 → 关键点数值”的顺序；必须同时标注网格分辨率和边界状态。

## 11. Writing Structure

正文结构为摘要—重述—分析—假设/符号—四问建模—检验/稳定性—优缺点—推广—附录。优点是每一问均从建模理由过渡到方程、图表和数值，附录还给出代码截图。主要写作问题有：

- 把“同一模型的解析/数值一致”写得接近普遍精度保证；
- 把多种不同含义的曲线统称“稳定性/鲁棒性”；
- 没有在最优 \(\eta_j\) 为边界值时主动收窄结论；
- 问题三的“相对位移状态”和“振子绝对位移”符号切换不够清晰；
- 附录代码看似完整，但含未定义变量、维数不匹配和缺失细化版本，读者容易高估可复现性。

## 12. Strengths

- 用受力方程而非算法堆叠建立主模型，变量、力项和优化目标之间关系可解释。
- 常量阻尼分支给出闭式最优并与数值积分对照；独立代数复算通过。
- 简化垂荡—纵摇前先检查小位移/小角，保留了近似的适用条件。
- 低维参数使用全局—局部网格，图形能直接显示峰值和边界。
- 附录公开了主要 MATLAB 代码结构，使公式—代码审计成为可能，并因此可定位实际复现缺口。

## 13. Weaknesses

- 所有“验证”均来自相同方程/参数，无真实装置、外部试验或留出工况；不能支持现实转换效率准确性。
- 参数不确定性没有传播到位移、功率或最优阻尼区间，且问题四旋转阻尼解卡在上界。
- 刚度扫描显示输出大幅变化甚至模型崩溃，与“鲁棒性好”的总括不一致。
- 附录代码不是可直接运行的完整复现包：问题一缺常量阻尼函数版本，问题二积分脚本引用未定义 `eta_i_best`，问题三引用未定义 `eta_i_index`，问题四局部绘图横坐标与结果向量长度不一致。
- 非线性最优 \(\alpha=0.370\) 需要未公开的细化网格；结果工作簿、问题 4 数据表和敏感性代码不可得。
- 旋转阻尼单位在符号表写为 N·s/m，和转动功率式所需的 N·m·s/rad 不一致；非线性比例系数的量纲随 \(\alpha\) 变化但未报告。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | pp.4–5 符号与 pp.22–30 硬编码参数；题目附件/结果工作簿当前不可得 | 无法核对全部水动力参数来源或重算表 1–4 |
| Code availability | partial | pp.21–30 含主要 `.m` 代码截图；独立源文件和 `code5.m/func5.m` 不可得 | 需人工转录，且缺细化/敏感性代码 |
| Dependency / environment information | partial | MATLAB、`ode45`、`trapz` 和信号分析器被点名 | MATLAB 版本、工具箱、RelTol/AbsTol 未报告 |
| Random seed | N/A - deterministic methods | ODE 与网格代码 pp.22–30 无随机步骤 | 不适用；若敏感性代码含随机过程则不可评估，因为文件缺失 |
| Hard-coded constants | extensive | pp.22–30 每个函数重复写入质量、刚度和工况参数 | 易发生工况错配；没有统一参数文件 |
| Formula-to-code consistency | partial with contradictions | 核对 pp.6, 8, 12–13 方程与 pp.22–30 代码 | 主力项基本对应；问题一只显示非线性函数，旋转单位错误，问题三输出变量口径不清 |
| Code-to-result consistency | not reproducible as printed | 核对 pp.9–16 结果与 pp.23–30 代码 | `eta_i_best`、`eta_i_index` 未定义；问题四 `plot` 21 点横轴对 151 点 PTO；非线性细化代码缺失 |
| Overall reproducibility | partially reproducible | 解析公式可完全复算；ODE/网格只能重建方法结构 | 缺附件/源代码/结果表，加上可见代码错误；不能原样重现全部论文数值 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 静水平衡高度 | \(h_0=0.99999\) m | \(3+0.8/3-7299/(1025\pi)=0.99998973\) m | pass | p.5 equation | 使用代码/几何给定值 |
| 常量阻尼解析最优 | \(\eta=37193.8119\), \(P=229.3339\) W | 由 p.8 公式与 p.24 常数得 37193.811888、229.33393984 | pass | pp.8–9 equation; p.24 code | 独立计算逐位吻合 |
| 解析/数值功率差 | “十分接近” | \((229.49727644-229.33393984)/229.33393984=0.07122\%\) | pass | pp.9–10 values | 支持该工况的内部数值一致性 |
| `trapz` 平均值缩放 | `trapz(pto)/1000` 表示 200 s 平均功率 | \(\Delta t/T=0.2/200=1/1000\) | pass | pp.23–30 code | 1001 个点的梯形积分缩放正确；起点索引约 199.8 s |
| 问题一 40 周期时长 | 代码运行到 180 s | \(40(2\pi/1.4005)=179.4555\) s | pass | p.22 code | 180 s 与 40 周期一致 |
| 问题三时域口径 | 题目/摘要称 40 周期；代码到 400 s | \(400/(2\pi/1.7152)=109.19\) 周期；40 周期约 146.5 s | concern | pp.1–2 paragraph; p.26 code | 延长仿真本身可用于稳态，但正文没有解释口径 |
| 旋转阻尼最优边界 | \(\eta_j=100000\) 为最优 | 等于允许区间上界 | concern | pp.15–16 figures 12–13 | 只能称有界网格最佳，不能判断更大值或物理约束下最优 |
| 非线性最优网格可复算性 | \(\alpha=0.370\) | 可见代码首轮 \(\alpha\) 步长 0.05，不含 0.370 | not assessable | pp.10–11 result; p.24 code | 作者称多轮细化，但细化版本未提供 |
| 问题三代码索引 | `PTO(:,eta_i_index)=...` | `eta_i_index` 在 `code3.m` 可见范围未定义 | fail | p.26 code line 50 | 原样运行到此行会报错或依赖污染工作区 |
| 问题四局部绘图维数 | 局部网格 151 个 PTO 值 | `50000:100:65000` 有 151 点，但 `plot(35000:100:37000,PTO)` 仅 21 个横坐标 | fail | pp.28–29 code lines 65–83 | `max(PTO)` 仍可算；图 13 横轴表明正确区间应为 5–6.5×10⁴ |
| 旋转阻尼单位 | 符号表给 \(\eta_j\) 为 N·s/m | \(P=\eta_j\Delta\omega^2\) 要求 \(\eta_j\) 为 N·m·s/rad（rad 视无量纲时为 N·m·s） | fail | p.5 symbol table; p.26/28 power code | 单位错误不一定改变数值代码，但破坏物理说明 |
| 刚度“稳定”表述 | 图 18 后称模型成立、输出正常 | PTO 约由 270 W 降至 55 W，变化约 80% | concern | p.19 figure 18 | 说明可计算，不等于输出对参数稳健 |
| 相对位移比 | 声称在 0.09–0.10 | 表 1 五个时刻的 \(|x_1-x_2|/|x_1|\) 约 0.005–0.110 | not assessable | pp.6, 17 table/paragraph | 论文可能使用振幅而非时点比值，但未定义统计口径且全时程数据不可得 |

## 14. Reusable Techniques

### 用可解析特例校验数值实现

**When useful:** 主问题含非线性/耦合 ODE，但存在一个线性或低维特例可闭式求解。

**Why useful:** 可快速发现积分缩放、符号、峰值位置和参数单位错误；本文解析常量与独立复算完全一致。

**Limitations:** 同一正向模型的内部互证不能验证物理假设，也不能把一个特例的误差界外推到所有非线性工况。

### 假设—量级—适用域闭环

**When useful:** 需要小角、小位移、线性化或弱耦合近似。

**Why useful:** 先用时程/几何估算量级，再做参数扫描，能把“拍脑袋假设”转为有范围的建模选择。

**Limitations:** 必须定义无量纲小参数和允许误差；只画输出曲线而不与完整模型比较，仍不能量化截断误差。

### 粗网格定位后局部细化

**When useful:** 决策变量 1–3 个、每次正向仿真可承受、目标可能非凸但边界明确。

**Why useful:** 全局曲面可见，结果易解释，避免启发式算法的随机性。

**Limitations:** 要保存每轮网格、分辨率和边界状态；最好点在边界时必须扩大范围或说明物理上界，不能直接写全局最优。

### 用耗散功率统一多阻尼目标

**When useful:** 机械系统的能量输出可由多个阻尼元件的瞬时耗散表示。

**Why useful:** 直线和旋转支路可在同一积分目标中相加，避免单位不清的“效率分数”。

**Limitations:** 每个阻尼系数的单位必须正确；机械耗散不自动等于可用电功率，还需发电机/转换损耗模型。

### 状态定义与参考系分层

**When useful:** 刚体整体运动与内部相对运动耦合，而完整约束反力难以求解。

**Why useful:** 以整体参考系写内部状态可减少未知力，降低方程维数。

**Limitations:** 必须清楚区分绝对位移和相对位移，并用完整模型、误差阶或实验检查忽略的耦合项。

## 15. Competition Takeaways

1. 先写清受力、状态、单位和边界，再选择 ODE 求解器；不要从 `ode45` 反推模型。
2. 为复杂数值模型保留一个能解析复算的特例，并报告相对误差而非只说“接近”。
3. `ode45` 的输出网格不等于内部步长；必须记录容差、稳态窗口和步长/窗口敏感性。
4. 网格最佳点落在边界时，立即扩大范围或给出物理上界，结论写“有界网格最好点”。
5. 小角/小位移假设要定义无量纲比值、阈值和扫描范围，不能只凭曲线视觉判断。
6. 公式、代码、结果三者逐项对照；交稿前至少做未定义变量、数组长度和工况参数的干净环境运行。
7. 输出功率曲线大幅变化或出现崩溃时，应报告敏感/失效区域，不能概括为“鲁棒性好”。
8. 支撑文件必须随论文完整保存；代码截图不足以替代可执行源文件、参数表和结果数据。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 论文建立垂荡二自由度 ODE，并对常量/速度幂阻尼分别求解 | explicit | 6 | §5.1.1 | equation (1), (2) | notation normalization | N/A | 公式符号经视觉核验 |
| 静水平衡给出 \(h_0=0.99999\) m | explicit | 5 | §5.1.1 | equation and paragraph | direct transcription | N/A | 独立计算见 Numerical Sanity Checks |
| 问题一常量阻尼与非线性阻尼的五时刻结果 | explicit | 6–7 | §5.1.2–5.1.3 | table 1, table 2 | direct transcription | N/A | 表格已视觉核验 |
| 常量阻尼稳态功率可写闭式并解析优化 | explicit | 8 | §5.2.1.1 | equations | notation normalization | N/A | 复振幅推导结构保留 |
| 解析最优为 37193.8119 N·s/m、229.3339 W | explicit | 9 | §5.2.1.1 | paragraph | direct transcription | N/A | 与 p.24 code 一致 |
| 独立代入解析式得到 37193.811888、229.33393984 | interpretation | 8–9 | §5.2.1.1 | equation | independent calculation | N/A | 使用 p.24 可见常数 |
| 数值网格给出 37200 N·s/m、229.497276 W | explicit | 10 | §5.2.1.2 | paragraph | direct transcription | N/A | 图 3–4 支持峰值位置 |
| 数值功率比解析功率高约 0.07122% | interpretation | 9–10 | §5.2.1 | paragraph values | independent calculation | N/A | 同模型内部一致性，不是外部验证 |
| 非线性阻尼报告 \(\eta=9.75\times10^4,\alpha=0.370,P=230.12739\) W | explicit | 11 | §5.2.2 | paragraph and figure 6 | direct transcription | N/A | 细化过程未公开 |
| 可见首轮 \(\alpha\) 网格不含 0.370 | criticism | 24 | appendix 7 | code lines 21–25 | independent calculation | N/A | 步长 0.05；作者称另有未展示版本 |
| 论文以小量假设和非惯性系简化垂荡—纵摇耦合 | explicit | 12–13 | §5.3.2 | equations, figure 9, paragraph | derived interpretation | N/A | 完整耦合对照未给 |
| 问题三最大角声称为 6.88°和 7.73° | explicit | 17 | §6.1.4 | paragraph | direct transcription | N/A | 作为小角量级证据 |
| 问题三代码运行 400 s，约为 109.19 个该工况周期 | criticism | 26 | appendix 9 | code lines 35–38 | independent calculation | N/A | 与“40 周期”叙述口径未解释 |
| 双阻尼网格最好点为 59300、100000 和 322.128796 W | explicit | 15–16 | §5.4 | figure 12–13 and paragraph | direct transcription | N/A | 旋转阻尼处于上界 |
| 上界解不能支持边界外全局最优 | criticism | 15–16 | §5.4 | figure 12 and paragraph | derived interpretation | N/A | 只否定更强结论，不否定有界网格值 |
| 频谱主圆频率 1.399 rad/s 接近激励 1.4005 rad/s | explicit | 16–17 | §6.1.2 | figure 14 and paragraph | direct transcription | N/A | 频率轴换算说明不足 |
| 激励力与力矩扰动维持小量 | explicit | 17–18 | §6.2.1–6.2.2 | figure 15, figure 16 | direct transcription | N/A | 只在图示范围内成立 |
| 图 18 显示 \(k\) 扫描时 PTO 约下降 80%，不宜称输出稳健 | criticism | 19 | §6.2.4 | figure 18 | independent calculation | N/A | 端点由图读取，近似值 |
| 图 17 出现百万瓦量级尖峰/崩溃，与问题四数百瓦基线难以协调 | criticism | 18 | §6.2.3 | figure 17 and paragraph | derived interpretation | N/A | 原始 `code5.m`/数据表不可得，不能定位原因 |
| 在已审查范围内未发现步长、ODE 容差、稳态窗口或阻尼边界敏感性 | criticism | 1–30 | full paper | none found | derived interpretation | 正文 pp.1–20、附录/代码 pp.21–30、当前可用补充材料清单均已审查 | 独立支撑文件不可得 |
| 附录列出结果工作簿、主/函数代码和敏感性代码 | explicit | 21 | appendix 1 | table, supporting-file list | direct transcription | N/A | 当前仓库仅有 PDF 内代码截图 |
| `func1.m` 只实现 \(\alpha=0.5\) 非线性阻尼，未展示问题一常量阻尼函数 | criticism | 22–23 | appendix 3–4 | code | derived interpretation | N/A | 固定阻尼结果不能由所示组合原样复现 |
| 问题二积分脚本使用未定义的 `eta_i_best` | criticism | 23 | appendix 5 | code line 6 | direct transcription | N/A | 可能依赖污染工作区，非独立脚本 |
| 问题三脚本使用未定义的 `eta_i_index` | criticism | 26 | appendix 9 | code line 50 | direct transcription | N/A | 原样运行到此行失败 |
| 问题四局部 `plot` 的 21 个横坐标与 151 个 PTO 值不匹配 | criticism | 28–29 | appendix 11 | code lines 65–83 | independent calculation | N/A | 图 13 的正确横轴应与 50000:100:65000 对齐 |
| 旋转阻尼符号表单位与转动功率式不一致 | criticism | 5, 26 | symbol table / appendix 9 | table and code | independent calculation | N/A | 应为 N·m·s/rad，而非 N·s/m |
| 当前证据最高为 L3 参数扰动，无独立真实验证 | criticism | 1–30 | full paper | none found | derived interpretation | 正文、检验、稳定性、附录代码和可用补充材料清单均审查 | 支撑工作簿/源代码不可得；不把同模型解析—数值互证当 L5 |
