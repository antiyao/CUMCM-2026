# Paper: 系泊系统的设计（题目名称；论文首页标题栏未填写）

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_fc7ed54151ab
- Year: 2016
- Problem: A（系泊系统的设计）
- Award: 组委会官方展示论文；具体奖项等级未核验，不能由展示状态推断奖级
- Provenance tier: O: 官方展示 PDF 直接下载；年份、代码 A28、44 页和 SHA-256 均有采集记录，奖级未知
- Source file: literature/raw_papers/2016/A28_moe_2016_1699719.pdf
- Source URL: https://dxs.moe.gov.cn/zx/json/2016/1128/1480298680384.pdf
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2016qgdxssxjmjslwzs/220809/1699719.shtml
- Pages: 44
- SHA-256: b7aa78f24f98ff96856422d9306013df8d8a2e992f4ff9bd8e0db0831a4fad20
- Extraction method: embedded text（pypdf 6.10.0）+ manual visual review；未使用 OCR
- Extraction quality: `success / usable_text_layer`；43/44 页至少有 30 个非空白字符，共 27,240 个可见字符，中位数 629 字符/页。公式符号和旧编码 MATLAB 注释不能只依赖文本层，均回看渲染页
- Page convention: 1-based physical PDF pages
- Visually checked pages: 1-44 全页缩略图；重点核验 p.5-10 受力递推/几何/沉底修正，p.11-16 步长、表 5.4.2/5.4.4、权重、表 6.3.1/6.3.3，p.17-23 三维水流模型、式 (7-2-1)-(7-2-18)、表 7.3.1/7.3.2，p.24-44 全部附录代码；p.5-44 另以高分辨率渲染核字
- Unresolved extraction ambiguities: 论文首页只显示“论文标题”，摘要问题二的页码/表号和结果范围保留 `XXX/XX` 或空白，这是源文缺失而非抽取失败；MATLAB 中文注释乱码，但本报告引用的变量、循环、公式和数值均可从原页确认
- Supplemental artifacts: p.24-44 内嵌 9 组 MATLAB 程序/函数；未提供独立 `.m` 文件、运行日志、结果数组或环境版本

## 1. Problem Archetype

本文是“静力机理递推 + 条件模型切换 + 多目标约束优化 + 网格搜索”的系泊系统设计论文，包含：

- 二维静力平衡：逐构件递推拉力、力方向和构件倾角；
- 接触状态切换：锚链悬浮时用逐环递推，提前触底时改用临界起链条件；
- 多目标优化：同时压低钢桶倾角、浮标吃水深度和游动半径；
- 三维扩展：把风力和水流力投影到两个平面，重建空间状态；
- 离散/连续混合搜索：选择链型、链环数和重物球质量。

可迁移价值在于先利用递推结构把高维状态压缩为一个吃水深度搜索，再把系统状态嵌入设计优化。核心证据风险在于问题三的附录实现没有忠实使用所选链长和水流力模型，且所谓“熵权”和“变步长”均未在可见求解代码中实现。

## 2. Problem Decomposition

1. **问题一**：给定 II 型 22.05 m 锚链、1200 kg 重物球和 18 m 水深，分别求 12/24 m·s⁻¹ 风速下的构件角度、锚链形状、吃水和游动区域；对 12 m·s⁻¹ 的锚链触底另建修正模型。
2. **问题二**：先求 36 m·s⁻¹ 的未优化状态，再以重物球质量为决策，满足钢桶≤5°、锚点切线≤16°，并最小化钢桶角、吃水和游动半径。
3. **问题三**：加入 16-20 m 水深、最大 1.5 m·s⁻¹ 水流和风/流方向；选择链型、链环数、重物质量，用三维投影状态模型搜索方案并列出四个环境情景。

模型链为：题目参数 → 浮标/钢管/钢桶/链环隔离受力 → 拉力与角度递推 → 竖直投影闭合 → 触底条件切换 → 状态输出 → 加权目标和约束 → 网格搜索。问题三正文的三维结构完整，但附录代码的链长变量、当前深度和链环水流力接口出现断裂。

## 3. Data Processing

本文没有观测数据清洗；数据处理主要是参数转换与搜索离散化：

- 由 22.05/0.105 得 II 型锚链 210 环；代码取单环质量 0.735 kg、等效密度 6450 kg·m⁻³。
- 重物球和锚链材料密度分别按 7800、6450 kg·m⁻³，用质量换体积后计算浮力。
- 问题一吃水深度用 0.0001 m 网格；问题二/三主优化用 0.01 m 网格，并允许竖直闭合残差至 0.2 m。
- 问题二质量搜索为 1800-4100 kg、步长 1 kg；问题三主代码为 5 种链长、链环数 100:20:280、质量 2000:50:4500。
- 水流剖面按 `v(z)=v_max z²/H²`，构件水流力按投影面积积分；链环拟作等体积圆柱。

没有参数不确定区间、测量误差或单位转换审计。正文“变步长”仅描述粗搜后局部细搜，可见问题三代码只展示单层固定网格，未保存粗细网格历史。

## 4. Models Used

### 二维逐构件静力递推

**Purpose:** 给定风速、吃水和配置，计算浮标—钢管—钢桶—锚链的平衡状态。

**Inputs:** 几何、质量/密度、风速、重物质量、链环数量/长度、海水深度。

**Outputs:** 各连接拉力与方向、构件倾角、吃水 `h`、游动半径 `r` 和锚点切线角。

**Why selected:** 铰接构件按自上而下受力递推，可把大量状态变量写成 `h` 的函数，避免同时解整个非线性方程组。

**Important assumptions:** 浮标不倾斜；构件刚性且静止；风向水平；链环用统一质量/密度；不考虑波浪和动态响应。

**Key equations or mathematical structure:** 浮标满足浮力、重力、风力与首节拉力平衡；每根杆/链环满足水平—竖直合力和下端力矩平衡；几何闭合为 `h+Σl_i cosθ_i=H`，半径为 `r=Σl_i sinθ_i`。

**Implementation notes:** p.25-26 以 `h=0:0.0001:2` 搜索最小 `|H_calc-18|`；24 m·s⁻¹ 代码可读，12 m·s⁻¹ 使用触底函数。

### 锚链提前触底修正

**Purpose:** 处理小风速下部分链环躺在海床、原悬浮递推失效的情形。

**Inputs:** 第一个离床链环位置、上部递推力、链环重浮力差。

**Outputs:** 离床段角度和长度、沉底链环数、修正后的半径。

**Why selected:** 12 m·s⁻¹ 解出现锚链触底；作者用首个将被提起链环的临界力矩与整体竖直受力切换模型。

**Important assumptions:** 沉底链环完全拉直；临界链环与海床夹角为 0；海床摩擦只通过临界条件间接处理。

**Key equations or mathematical structure:** p.9-10 式 (5-3-1)-(5-3-5) 给临界力矩和离床段竖直受力约束。

**Implementation notes:** `tuodir` 在 `h=0.6:0.0001:0.72` 内搜索并在角度接近水平时停止递推。

### 加权多目标质量优化

**Purpose:** 在 36 m·s⁻¹ 下选择重物球质量，使三目标小且满足角度约束。

**Inputs:** 质量 `m_q`、状态模型、钢桶≤5°、锚点切线≤16°。

**Outputs:** 作者报告可行质量 2200-4100 kg、最佳 2894 kg，及 `h=1.16 m, r=18.2831 m, θ=2.9954°`。

**Why selected:** 题目要求同时控制三项互相权衡的状态指标。

**Important assumptions:** 三目标可线性加权；固定比例尺能表达偏好；搜索上界足够大。

**Key equations or mathematical structure:** `U=Aθ_6+B h+C r`，正文称 `A=11.46,B=1.5,C=0.05` 来自熵权。

**Implementation notes:** p.31 直接硬编码 `a=36/pi,b=1.5,c=1/20`；附录熵权函数从未被调用。这三个量更像把 5°、约 2/3 m、20 m 归一到相近尺度的单位换算，不是归一化熵权。

### 三维投影与水流力模型

**Purpose:** 同时考虑水流、风向、水深和空间方向。

**Inputs:** `H,v_water,v_wind,α0` 及配置变量。

**Outputs:** 两投影面的力和角度、空间构件姿态、设计目标。

**Why selected:** 两个投影面可以重建构件方向，比直接写三维力矩方程更易递推。

**Important assumptions:** 水流 `v(z)=v_max z²/H²`；风和水流在代码中固定同向 `α0=0`；链环可等效为同体积圆柱；静态刚体。

**Key equations or mathematical structure:** p.17 式 (7-2-1)-(7-2-4) 给抛物速度和 `v²` 水流力积分，p.18-22 式 (7-2-5)-(7-2-18) 给两个投影面递推和三维目标。

**Implementation notes:** 正文包含链环水流力，但 `tuodir2` 和主优化代码把 `Fshui4(i)=0`；主代码还有 `H`/`gdH` 与 `lm`/`Lm` 不一致。

### 链型—长度—配重网格优化

**Purpose:** 对 16/20 m 水深和最大风/流选择链型、环数、重物质量。

**Inputs:** 五种链环长度/质量、`n=100:20:280`、`m_q=2000:50:4500`。

**Outputs:** 16 m 方案 `(V型,140环,3000 kg)`；20 m 方案 `(V型,180环,2950 kg)`。

**Why selected:** 决策混合离散/连续且状态函数非线性，作者认为先粗后细搜索能兼顾时间与精度。

**Important assumptions:** 枚举范围覆盖全局好解；固定网格足以区分相近方案；0.2 m 闭合容差可接受。

**Key equations or mathematical structure:** 与问题二相同的三目标与角度约束，外层枚举链型/环数/质量。

**Implementation notes:** 可见代码没有第二阶段细化；链长在外层赋给小写 `lm`，几何闭合和半径却使用大写 `Lm`，触底函数又固定 `Lm=0.105`。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 同时求解全部非线性状态 | rejected | 系统平衡求解 | 方程多且难直接定解 | 未给求解器基准 | Newton/SQP 初值、收敛与失败率未报告 | 利用递推降为单变量是合理的结构简化 |
| 吃水单变量网格搜索 | selected | 二维状态求解 | 解空间小、可直接循环 | 步长缩小检查 q=0.38×10⁻³ | 残差分布、解析特殊情形未报告 | 可解释，但 q 的定义不能替代状态误差上界 |
| 悬浮链模型 | selected conditionally | 大风状态 | 全链离床时递推成立 | 24/36 m·s⁻¹ 图形 | 接触判定裕量未报告 | 必须与触底模型明确切换 |
| 触底修正模型 | selected conditionally | 小风状态 | 12 m·s⁻¹ 链环落床 | 59 环沉底的状态输出 | 摩擦、松弛链形和海床反力验证未报告 | 是必要修正，但简化较强 |
| 熵权线性加权 | selected in prose | 三目标合成 | 声称较客观、利用变异度 | 只给 A/B/C | 原始目标样本矩阵和熵值未报告 | 代码未调用熵权函数，不能接受“熵权”来源 |
| 二维平面递推 | selected | 无水流或同平面受力 | 旋转对称、状态相同 | 12/24/36 m·s⁻¹ 输出 | 3D 对照未报告 | 对问题一/二条件合理 |
| 双投影三维递推 | selected | 风流不同方向 | 避免直接三维受力表达 | 仅 `α0=0` 的代码/图 | 非同向场景未实现 | 正文扩展合理，代码没有验证一般角度 |
| 变步长搜索 | selected in prose | 大解空间优化 | 粗搜定位、细搜精化 | 未给粗细结果对比 | 第二阶段代码、运行时间、全局性未报告 | 附录只证明固定网格枚举 |

## 5. Model Pipeline

问题一先完成二维正向状态模型，并用是否触底决定调用模型 I 或 II；问题二把正向模型嵌入质量枚举和加权目标；问题三再把正向模型扩展到两个投影面，外层枚举链型、环数和质量。该“正向状态 → 可行性 → 设计优化”接口是正确的竞赛结构。

但问题三实现有四个断点：选中的 `lm` 没有进入 `H/r`，两处钢管水流深度使用未定义 `H`，链环水流力被置零，环境情景代码固定 20 m 配置而正文说在 16 m 下测试。因此问题三结果不能由可见代码可靠复现。

## 6. Model Improvements

- **触底切换**：从全悬浮递推升级为接触状态模型，解决 12 m·s⁻¹ 的物理不适用；证据只限静态图与几何输出。
- **单变量降维**：把所有角度递推为吃水的函数，避免高维联立求解；未与通用非线性求解器比较。
- **从二维到三维双投影**：扩展水流和方向；但代码只用风流同向，无法证明一般角度实现。
- **粗网格思想**：为大解空间提出粗到细；附录未展示细化步骤，不能把运行效率提升视为已验证。

## 7. Parameter Estimation and Optimization

本文没有统计估计；多数参数由题目、参考文献或作者设定。优化是确定性枚举，目标最小化三项线性加权状态。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| ρ | 海水密度 | kg/m³ | p.2 problem | 1025 | problem-provided | N/A - given | no | 全文固定 |
| g | 重力加速度 | m/s² | p.25 code | 9.8 | author-assumed | fixed | no | 未说明舍入影响 |
| H | 水深 | m | p.2 problem | 18；16-20 | problem-provided | N/A - given | partial | 只报 16/18/20 情形 |
| v_wind | 海面风速 | m/s | p.2 problem | 12, 24, 36 | problem-provided | N/A - given | yes | 离散场景，不是连续响应 |
| v_water | 最大水速 | m/s | p.2 problem | up to 1.5 | problem-provided | N/A - given | partial | 表 7.3.2 用 0.5,1,1.5 |
| α0 | 风流方向夹角 | rad | p.21 model; p.35/38 code | code fixes 0 | author-assumed | fixed | no | 正文列为环境变量但未扫角度 |
| n_II, L_II | II 型链环数/长度 | count, m | p.2,4 | 210, 0.105 | problem-provided | 22.05/0.105 | no | 质量代码取 0.735 kg/环 |
| ρ_chain | 链环等效密度 | kg/m³ | p.8 ref. [1], code | 6450 | literature-derived | referenced / fixed | no | 来源没有页码 |
| ρ_ball | 重物球密度 | kg/m³ | p.11 assumption/code | 7800 | author-assumed | 普通铸铁 | no | 问题二材料固定 |
| Δh fine | 问题一吃水网格 | m | p.25,27 code | 0.0001 | algorithm hyperparameter | fixed grid | yes | 文本称缩小 50 倍检查 |
| Δh coarse | 问题二/三吃水网格 | m | p.29,35,38 code | 0.01 | algorithm hyperparameter | fixed grid | no | 可接受闭合残差另设 0.2 m |
| m_q problem 2 | 问题二质量扫描 | kg | p.29-32 code | 1800-4100, step 1 | algorithm hyperparameter | exhaustive enumeration | yes | 上界为代码边界 |
| A,B,C | 三目标系数 | mixed inverse units | p.14; p.31/41 code | 36/π, 1.5, 1/20 | author-assumed | hard-coded scaling | no | 和为 13.009，不是归一熵权；熵权函数未调用 |
| L types | 五种链环长度 | m | p.38 code | 0.078,0.105,0.12,0.15,0.18 | problem-provided | N/A - table values | no | 主优化未正确传入 `Lm` |
| n problem 3 | 链环数网格 | count | p.38 code | 100:20:280 | algorithm hyperparameter | enumeration | no | 无局部步长细化 |
| m_q problem 3 | 重物质量网格 | kg | p.38 code | 2000:50:4500 | algorithm hyperparameter | enumeration | no | 无局部步长细化 |
| ε_H | 竖直闭合容差 | m | p.41 code | 0.2 | algorithm hyperparameter | feasibility filter | no | 相对报告三位小数较宽 |

## 8. Validation

验证证据以内部几何闭合、步长检查、同一模型的参数扫描和简单算术为主。没有实验、外部仿真或独立测量；问题三代码缺陷进一步限制其场景证据。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 吃水搜索步长 | L3 step-size perturbation | theoretical | q 定义值 | 1 comparison | q=0.38×10⁻³ | 未给两次状态向量/残差 | q 公式除以 50，物理含义不清 | 只支持作者所用目标在该次细化下变化小 |
| 几何闭合 | L2 internal consistency | same model | `|H_calc-H|` | every grid point | 选择最小残差 | 问题二/三允许至 0.2 m | 未列最终残差 | 只能说明代码有闭合筛选 |
| 半径—面积 | L2 arithmetic sanity check | theoretical | πr² | 3 reported cases | 681.011≈681；997.889≈997.89；1121.0923≈1121.092 | none in checked cases | 不验证力学状态 | 三个面积值表内闭合 |
| 重物质量响应 | L3 parameter sweep | same model | h,r,θ6 | one grid | h/r 小变，θ6 随质量明显下降 | 高质量端仍是搜索边界 | 无约束裕量和残差表 | 支持局部单调趋势，不支持区间外结论 |
| 环境情景 | L3 scenario perturbation | same model | θ6,h,r | 4 cases | 表 7.3.2 给四组状态 | 代码用 20 m 配置，正文称 16 m | 风流方向固定、无不确定分布 | 仅作为模型情景输出，不能称现实鲁棒性 |
| 问题三设计可行性 | L2 reported constraint check | same model | θ6≤5° | 2 designs | 4.593°、4.959° | 20 m 仅余 0.041° | 未报告锚点角和闭合残差 | 只确认表内钢桶角满足约束 |
| 外部物理验证 | not reported | unknown | not reported | not reported | not reported | not reported | 无实验或独立软件对照 | 不支持现实部署精度 |

## 9. Sensitivity and Robustness

论文包含质量扫描和四个环境情景，但未对链长变量错误、闭合容差、目标比例尺、风流夹角、刚体假设或水流力公式作敏感性。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 吃水搜索步长 | original step | 1/50 original | two grids | author-defined q | 0.38×10⁻³ | unclear | 未给状态误差，证据只限目标变化 |
| 重物球质量 | 约 2894 kg | 2200-4100 kg | 1 kg grid | θ6,h,r | θ6 明显下降，h/r 小幅变化 | no within plotted range | 不覆盖 4100 kg 以上，所谓可行上界是搜索边界 |
| 风速/水速组合 | 36/1.5 | wind 12-36; current 0.5-1.5 | four scenarios | θ6,h,r | θ6 2.543°-4.259°；h 1.288-1.300 m；r 16.053-18.795 m | no for θ6≤5° | 文本/代码深度配置冲突，结论需保留 |

## 10. Visualization Strategy

受力图与投影图承担模型定义，锚链二维/三维曲线承担状态解释，质量—目标曲线承担敏感性。图形顺序与模型链基本一致。问题一图号出现 5.4.3/5.4.5 跳号，摘要还保留 `XXX/XX`；问题三曲线没有同时标出锚点角、闭合残差和约束裕量，因此不能作为完整可行性证书。

## 11. Writing Structure

正文按“假设—符号—问题分析—逐问建模—评价—附录”组织，机理推导占主体，附录代码覆盖所有问题。优点是每个模型都有受力图、递推式和几何闭合；不足是摘要未清稿、权重来源和代码不一致、变步长细化缺失、问题三正文与代码使用不同方案深度。

## 12. Strengths

- 利用构件递推把高维静力状态降为吃水深度的一维搜索，结构清楚。
- 显式识别锚链接触状态并切换模型，而不是强行使用全悬浮公式。
- 正向状态、约束和设计变量接口明确，适合形成“机理—优化”竞赛模板。
- 报告质量扫描和环境场景，并在附录提供大部分 MATLAB 逻辑，便于主动审计。
- 半径—面积和沉底环数等简单结果可独立闭合。

## 13. Weaknesses

问题三代码是主要短板：外层所选链长没有进入几何，部分水流深度变量未定义，链环水流力置零，情景代码还使用与正文不同的 20 m 方案。问题二的三个系数并非可复核的熵权，可行质量上限就是搜索上限。所有证据来自同一静态刚体模型，未传播材料、风流、海床或波浪不确定性。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | mostly embedded constants | p.2 题面参数、p.24-44 代码硬编码 | 不依赖外部数据表，但引用密度来源细节不足 |
| Code availability | partial | p.24-44 九组 MATLAB 文本 | 需人工转录；问题三脚本含未定义/大小写变量 |
| Dependency / environment information | not reported | p.1-44 | MATLAB 版本、工具箱和运行方式未知 |
| Random seed | N/A - deterministic grids | p.24-44 | 无随机算法 |
| Hard-coded constants | extensive | 网格、容差、比例尺、密度、风流同向 | 来源/敏感性不足 |
| Formula-to-code consistency | contradicted in problem 3 | p.17-22 vs p.35-44 | 链环水流力、`lm/Lm`、`H/gdH` 和 α0 接口不一致 |
| Code-to-result consistency | partial for problems 1-2; contradicted/not assessable for problem 3 | 表 5.4.2/5.4.4/6.3.3、表 7.3.1/7.3.2 与附录 | 问题三可见脚本不能在干净工作区生成报告方案 |
| Overall reproducibility | partially reproducible | 全 44 页、全部附录代码和现有仓库文件 | 问题一/二可手工转录检查；问题三需修代码且无保存输出 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| II 型链环数 | 22.05 m 对应 210 环 | 22.05/0.105=210 | pass | p.2,4 | 尺度闭合 |
| 12 m/s 沉底数 | 从第 152 环触底，共 59 环 | 210-151=59 | pass | p.12 paragraph | 编号口径闭合 |
| 12 m/s 游动面积 | r=14.7232 m, area=681 m² | πr²=681.0113 m² | pass | p.12 table/paragraph | 舍入一致 |
| 24 m/s 游动面积 | r=17.8224 m, area=997.89 m² | πr²=997.8890 m² | pass | p.12 paragraph | 舍入一致 |
| 36 m/s 未优化面积 | r=18.8906 m, area=1121.092 m² | πr²=1121.0923 m² | pass | p.15 paragraph | 舍入一致 |
| 36 m/s 未优化约束 | 锚点角 21.397° | 21.397°>16° | pass | p.15 paragraph | 正确识别需要优化 |
| “熵权”闭合 | A=11.46,B=1.5,C=0.05 | 和为13.01而非1；代码为36/π、1.5、1/20且不调用熵权函数 | fail | p.14; p.31-33 code | 更像量纲比例尺，来源声明不成立 |
| 问题二质量上界 | 可行范围至4100 kg | 枚举只到4100，端点可行不能证明其上无可行值 | concern | p.16 table 6.3.3; p.29 code | 应扩大区间或说明设计上限 |
| 问题三链长传递 | 外层遍历 `lm=mlcd(l)` | 后续 H/r 使用 `Lm`；触底函数固定 `Lm=0.105` | fail | p.38,40-41; p.35 code | V 型 0.18 m 方案无法由此链路确认 |
| 问题三水深变量 | 钢管流力都按 gdH | p.39 第二、三项使用此前未定义的 `H` | fail | p.39 code | 干净工作区首轮会失败或受旧变量污染 |
| 链环水流力 | 正文按等体积圆柱计算 | 代码逐环强制 `Fshui4(i)=0` | fail | p.21; p.37,40 code | 公式—代码直接冲突 |
| 16 m 情景口径 | 表 7.3.2 称在16 m改变环境 | 附录 9 固定 `gdH=20,mq=2950,n=180,Lm=0.18` | fail | p.23; p.42 code | 实际对应20 m设计 |
| 变步长实现 | 先粗搜再局部细搜 | 可见代码只有固定 `l,n,mq,h` 网格 | not assessable | p.23; p.38-41 code | 未提供第二阶段代码/结果 |
| 20 m 钢桶角裕量 | θ6=4.959°≤5° | 裕量仅0.041° | concern | p.23 table 7.3.1 | 未做参数/数值误差传播 |
| 竖直闭合精度 | 报告 h 到0.001 m | 问题三可接受 `|H_calc-H|≤0.2 m` | concern | p.23 table; p.41 code | 报告小数位不代表状态精度 |

## 14. Reusable Techniques

### 递推降维的静力系统求解

**When useful:** 串联系统的下游状态可由上游力和一个边界变量递推。

**Why useful:** 把高维联立方程压为一维闭合残差，易于调试和可视化。

**Limitations:** 必须控制三角函数分支、接触状态、累积误差和闭合容差。

### 接触状态的条件模型切换

**When useful:** 绳链可能悬浮、部分着地或松弛。

**Why useful:** 防止在物理适用域外继续使用同一递推式。

**Limitations:** 接触摩擦、海床反力和松弛形态需单独建模并验证切换阈值。

### 正向机理嵌入设计优化

**When useful:** 每个设计配置可由快速正向模型计算状态和约束。

**Why useful:** 决策变量、目标和可行性边界透明，适合网格/启发式比较。

**Limitations:** 必须记录求解器状态、约束残差和参数真正进入正向模型的证据。

### 先粗后细的分层搜索

**When useful:** 离散组合少、连续变量范围大且目标较平滑。

**Why useful:** 可降低全细网格成本。

**Limitations:** 粗网格可能漏掉窄可行域；必须保存细化范围、步长、边界扩展和运行时间。

## 15. Competition Takeaways

1. 先画受力图并建立逐构件递推，再用几何闭合求唯一边界变量。
2. 对悬浮/触底等物理状态设置显式切换条件，并分别验证。
3. 多目标合成前先无量纲化；若称熵权，必须保留原矩阵、熵值、归一权重和代码调用。
4. 每个决策变量做“赋值—传入正向模型—进入目标/约束”的接口测试，尤其检查大小写和默认值。
5. 网格上界命中时扩大范围；边界解只写“当前范围最好”，不写全局最优。
6. 输出方案必须附锚点角、钢桶角、闭合残差和约束裕量，不能只给形状图。
7. 场景分析固定同一个设计和水深口径，再改变单一环境变量；记录代码参数表。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 首页标题栏只写“论文标题”，正文处理2016 A系泊系统题 | explicit | 1-2 | title/abstract/problem | paragraph | direct transcription | N/A | 报告标题使用题目名称并注明边界 |
| 二维模型递推浮标、钢管、钢桶和锚链的力与角度 | explicit | 5-9 | 5.2 | equations (5-2-1)-(5-2-19) | notation normalization | N/A | 公式经高分辨率原页核验 |
| 几何闭合为竖直投影等于水深，半径为水平投影和 | explicit | 8-9 | 5.2.2 | equations (5-2-17)-(5-2-19) | notation normalization | N/A | 正向模型接口 |
| 12 m/s 需用锚链触底修正 | explicit | 9-12 | 5.3-5.4.3 | equations (5-3-1)-(5-3-5); table 5.4.2 | direct transcription | N/A | 报告59环沉底 |
| 12/24 m/s 构件角和吃水见表5.4.2/5.4.4 | explicit | 12 | 5.4.3 | tables 5.4.2, 5.4.4 | direct transcription | N/A | 视觉核表 |
| 三个半径—面积值独立复算闭合 | interpretation | 12,15 | 5.4.3,6.3.2 | paragraphs | independent calculation | N/A | πr² |
| 36 m/s 未优化锚点角21.397°超过16° | explicit | 15 | 6.3.2 | paragraph | direct transcription | N/A | 正确触发优化需求 |
| 问题二目标为θ6、h、r的线性加权 | explicit | 13-15 | 6.2-6.3 | equation (6-2-3); objective | notation normalization | N/A | 三目标单位不同 |
| 正文称A/B/C来自熵权 | explicit | 14 | 6.3.1 | paragraph | direct transcription | N/A | 值为11.46/1.5/0.05 |
| 求解代码硬编码比例尺且未调用熵权函数 | criticism | 31-33 | appendix 3-4 | code | direct transcription | N/A | 权重和13.009，来源声明不成立 |
| 问题二报告可行质量2200-4100 kg、最佳2894 kg | explicit | 16 | 6.3.3 | table 6.3.3 | direct transcription | N/A | 4100是搜索上界 |
| 质量扫描显示θ6明显下降而h/r小变 | explicit | 16 | sensitivity | figures 6.3.4-6.3.5 | direct transcription | N/A | 同模型L3证据 |
| 三维模型使用抛物水速和两个投影面 | explicit | 17-22 | 7.2 | equations (7-2-1)-(7-2-18) | notation normalization | N/A | 正文方法结构 |
| 链环被等效为同体积圆柱以计算水流投影 | explicit | 21 | 7.2.2(iv) | equation/paragraph | direct transcription | N/A | 形状近似 |
| 问题三报告16/20 m均选V型，配置见表7.3.1 | explicit | 23 | 7.3.2 | table 7.3.1 | direct transcription | N/A | 仅钢桶角可直接核约束 |
| 20 m方案钢桶角距5°上限仅0.041° | criticism | 23 | 7.3.2 | table 7.3.1 | independent calculation | N/A | 无误差传播 |
| 外层赋值lm但H/r使用Lm，触底函数又固定0.105 | criticism | 35,38,40-41 | appendix 7-8 | code | direct transcription | N/A | 选定V型链长无法确认进入状态 |
| 问题三钢管水流数组含未定义H | criticism | 39 | appendix 8 | code | direct transcription | N/A | 首轮或干净工作区不可运行 |
| 链环水流力在代码中被置零 | criticism | 37,40 | appendix 7-8 | code | direct transcription | N/A | 与p.21正文冲突 |
| 表7.3.2称16 m场景，附录9固定20 m配置 | criticism | 23,42 | 7.3.2/appendix 9 | table and code | direct transcription | N/A | 场景口径冲突 |
| 正文提出变步长，附录只展示固定网格 | criticism | 23,38-41 | 7.3.1/appendix 8 | paragraph and code | derived interpretation | N/A | 未展示局部细化 |
| 问题三接受0.2 m闭合残差却报告三位小数状态 | criticism | 23,41 | 7.3.2/appendix 8 | table and code | independent calculation | N/A | 输出精度与可行容差不匹配 |
| 在已审查范围内，未发现实验、外部求解器或真实部署验证 | criticism | 1-44 | full paper | none found | derived interpretation | 审查p.1-24正文、全部图表、p.24-44附录代码和现有仓库材料 | 所有证据来自同一静态模型 |
| 在已审查范围内，未发现风流夹角、目标比例尺、链长接口或闭合容差的敏感性 | criticism | 1-44 | model/sensitivity/appendix | none found | derived interpretation | 审查问题二/三模型、灵敏度图、表7.3.2及全部代码 | 只发现质量和四个环境情景 |
| 问题一/二代码可部分转录，问题三不能按可见脚本端到端复现 | criticism | 24-44 | appendix | code | derived interpretation | N/A | 总体partially reproducible |
