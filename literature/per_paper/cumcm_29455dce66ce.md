# Paper: 多情形下无人机烟幕遮蔽策略的建模与优化研究

## Metadata

- Distillation schema: 1.1
- Paper ID: `cumcm_29455dce66ce`
- Year: 2025
- Problem: A196，A 题
- Award: 奖级未核验。文件名和本地合集标签不作为奖项证据；只能确认 A196 在组委会官方展示中存在。
- Provenance tier: O*; 本地 34 页正文与官方展示第 1--34 页在首页、摘要、代表性中页和末页抽查中一致；官方第 35--98 页另附 MATLAB 代码页，本地 PDF 不含该附录。官方展示状态不等于一等奖，且本地版本仍缺官方代码附录，故保留 O* 伴随版本边界。
- Source file: `literature/raw_papers/2025/A196.pdf`
- Source URL: unknown；本地来源为用户提供合集
- Verification source: `https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2025qgdxssxjmjslwzs_2025atlw/251101/2022729.shtml`
- Pages: 本地 PDF 34 页；官方展示 98 页，其中第 35--98 页为额外 MATLAB 代码附录
- SHA-256: `c2c656954b60381a0eb9f923cbe8bd7b0fab5a9c2fe9527b02451787a8d0ed0a`
- Extraction method: 本地 PDF 为 `chi_sim+eng` Tesseract 5.5.0 OCR fallback，250 DPI、PSM 3；官方代码附录以官方页图 OCR 辅助并直接视觉核验关键页
- Extraction quality: 本地嵌入文本 34/34 页为空；OCR 34/34 页成功、无页级错误，质量为 `ocr_usable_with_visual_review`。公式、表格、代码标点与上下标均以原页为准。官方代码附录是页图而非可执行 `.m` 文件，OCR 仅用于定位和全附录审查。
- Page convention: 1-based physical PDF pages；“官方 pXX”专指官方 98 页展示中的物理页
- Visually checked pages: 本地 p1--2、p7、p9、p14、p16、p18、p20、p23--24、p27--29、p32、p34；官方 p1--2、p17、p34、p39、p46、p49、p54、p59、p66、p76、p88、p90--92、p97--98。官方 p35--98 代码页均经页级 OCR 全范围审查。
- Unresolved extraction ambiguities: OCR 对一般正文中少量汉字和复杂下标有误识别；本报告引用的关键约束、参数、表值、代码分支和公式均已回看原页。官方附录只有代码图片，未逐字符转写为可运行源文件。
- Supplemental artifacts: 本地 p34 列出 `first`、`second_greed_solve`、`second2_pso`、`third`、`fourth_DE`、`fourth_grid`、`fifth`、`IntervalInter`、`IntervalUnion`、`isOverwhelm`、`result1.xlsx`、`result2.xlsx`、`result3.xlsx` 与使用说明。官方 p35--98 展示上述 MATLAB 代码，但仓库中没有原始 `.m`、三个结果工作簿或使用说明；这些缺失产物为 `not assessable`。

## 1. Problem Archetype

本文属于“确定性运动学正向模型 + 空间几何遮蔽判定 + 黑箱优化 + 多实体调度”的混合原型：

1. 以导弹、无人机、烟幕弹和云团的三维运动方程构成正向模型。
2. 将“导弹到圆柱目标任一点的线段与烟幕球相交”写成布尔遮蔽判定，并以布尔函数的时间积分作为目标。
3. 对单机单弹采用多起点变步长坐标搜索，对单机多弹和多机单弹采用差分进化（Differential Evolution, DE）或几何降维后的网格搜索。
4. 对多机多弹多导弹情形，正文提出任务分配整数线性规划（Integer Linear Programming, ILP）后再分解优化；官方代码却实现了另一条最近导弹启发式路径。

其可迁移价值主要在于把复杂时空可见性条件封装为可复用的几何判定器，再由不同优化器调用。结论边界是：求得的是给定理想化物理模型、离散边界和有限搜索预算下的 best-found 策略，不是经证明的全局最优或真实作战有效性。

## 2. Problem Decomposition

- 问题一：固定 FY1、M1、投放与起爆参数，计算单云团有效遮蔽区间；先建运动方程，再做线段--球相交判定、圆柱边界离散和二分搜索。
- 问题二：把航向角、速度、投放时间和起爆延迟作为四维决策变量，最大化单弹遮蔽时长；以 PSO 作同一模拟器下的算法对照。
- 问题三：扩展到同一无人机三枚烟幕弹，用区间并集评价总遮蔽时长，用 DE 搜索八维变量。
- 问题四：三架无人机各一弹。正文先用“云团与导弹在预测时刻重合”构造近似解，再局部网格微调；另用 12 维 DE 对照。
- 问题五：正文把最多 45 维问题写成“任务分配 ILP → 每枚导弹独立优化 → 三个时间集合求交”。官方 `fifth.m` 实际执行“每架无人机分配给平面距离最近的导弹 → 每机固定三弹、相隔 1 秒 → 四参数网格搜索 → 直接累加各弹时长”，与正文接口不一致。

前四问大体共享同一个正向判定器，问题五在任务分配、目标聚合和求解器处发生实质性断裂。

## 3. Data Processing

本文没有经验数据清洗、缺失值或异常值处理。主要“数据处理”是几何离散与区间运算：

- 将半径 7 m、高 10 m 的圆柱目标上下底面圆周均匀离散；正文以每个圆周 300 点为基准。
- 用线段参数方程与半径 10 m 球体的二次判别式逐点判断遮蔽。
- 对单弹返回一个起止区间；多弹通过 `IntervalUnion` 合并、通过 `IntervalInter` 对不同采样点取交。
- 官方不同模块的离散密度并不一致：`fourth_grid.m` 使用 `2*50` 个点，`fifth.m` 使用 `2*300` 个点；正文的 n 敏感性只覆盖问题一，不能自动证明其他模块的离散稳定性。
- 结果工作簿 `result1.xlsx`、`result2.xlsx`、`result3.xlsx` 未提供，无法核对完整决策变量和中间区间。

## 4. Models Used

### 三维运动学模型

**Purpose:** 生成导弹、无人机、投放后烟幕弹和起爆后云团中心的时空位置。

**Inputs:** 初始位置、导弹速度 300 m/s、无人机航向与速度、投放时间、起爆延迟、重力加速度、云团下沉速度。

**Outputs:** 各对象位置向量及烟幕有效时间窗口。

**Why selected:** explicit；题目对象做匀速直线、抛体和匀速下沉，运动方程是几何判定的直接输入。

**Important assumptions:** 质点、无风和空气阻力、无人机瞬时转向、云团瞬时成为固定半径球且 20 s 内不扩散。

**Key equations or mathematical structure:** 无人机为水平匀速；烟幕弹为带初始水平速度的抛体；起爆后球心仅以 3 m/s 竖直下沉。

**Implementation notes:** 官方代码把初始位置和速度直接硬编码；不同模块重复实现同一正向模型。

### 线段--球相交与布尔遮蔽模型

**Purpose:** 判断给定时刻导弹到目标采样点的视线是否被烟幕球截断。

**Inputs:** 导弹位置、云团中心、圆柱采样点、球半径 10 m。

**Outputs:** 每个采样点的相交布尔值，以及全点均被遮蔽时的 `Bool(t)`。

**Why selected:** explicit；把三维遮蔽转成一元二次方程根是否落在线段参数区间 `[0,1]`。

**Important assumptions:** 有限采样代表连续圆柱边界；所有采样视线都相交才算完整遮蔽。

**Key equations or mathematical structure:** `a s^2+b s+c=0`，判别式 `Delta=b^2-4ac`；至少一个根在 `[0,1]`，或线段完全位于球内，则该视线相交。

**Implementation notes:** 官方 `isOverwhelm` 的不同副本对“导弹位于烟幕球内”有的强制返回 false、有的把该分支注释掉，口径不统一。

### 多起点变步长坐标搜索与 PSO

**Purpose:** 求解问题二四维黑箱优化。

**Inputs:** 航向、速度、投放时间、起爆延迟及几何模拟器。

**Outputs:** best-found 投放策略和遮蔽时长。

**Why selected:** explicit；目标没有解析梯度，作者希望兼顾全局采样和局部搜索。

**Important assumptions:** 有限随机起点与步长递减足以找到高质量解。

**Key equations or mathematical structure:** 多起点坐标正负方向试探；无改进时缩小步长。PSO 以同一目标作对照。

**Implementation notes:** 官方代码使用四轮、每轮 2000 个随机起点；PSO 为 600 粒子、1000 次迭代。无随机种子或重复运行分布。

### DE 与区间集合目标

**Purpose:** 问题三的八维单机三弹、问题四的 12 维三机单弹优化。

**Inputs:** 方向、速度、三组投放/延迟变量及逐点区间并交结果。

**Outputs:** 最大总有效遮蔽时间和策略。

**Why selected:** explicit；高维、非线性、无梯度。

**Important assumptions:** 给定种群、迭代数、变异因子和交叉率足以探索可行域。

**Key equations or mathematical structure:** DE/rand/1 型变异 `V=X_r1+F(X_r2-X_r3)`、二项交叉、约束优先选择和精英保留。

**Implementation notes:** 问题三正文与官方 p54 均为 `N=100, G=500, F=0.5, CR=0.9`；问题四官方 p66 为种群 800、最多 300 代、`F=0.5, CR=0.9`。

### 预测拦截点与局部网格

**Purpose:** 将问题四的 12 维直接优化拆为每架无人机一个四维局部问题。

**Inputs:** 令云团/烟幕弹与 M1 在候选时刻重合得到的初值，以及局部角度、速度、投放时间、延迟网格。

**Outputs:** 三架无人机的三个有效区间及其并集长度。

**Why selected:** explicit；作者声称物理降维可以减少全局进化开销。

**Important assumptions:** 越早的可行拦截时刻越优；重合点附近包含高质量解；固定局部搜索域足够。

**Key equations or mathematical structure:** 由 z 轴解自由落体比例 `s`，由 xy 距离解所需速度，再在邻域全网格搜索。

**Implementation notes:** 每机网格为 51 个角度 × 50 个速度 × 80 个投放时间 × 80 个延迟，共 16,320,000 个候选；三机共 48,960,000 个候选，论文未给运行时间或等预算比较。

### 正文任务分配 ILP 与官方 `fifth.m`

**Purpose:** 为问题五分配无人机/烟幕弹到三枚导弹并求联合遮蔽。

**Inputs:** 正文的理论窗口 `c_ij`、整数弹数 `y_ij`；或代码中的无人机到导弹航迹平面距离。

**Outputs:** 正文期望给出任务分配矩阵与三导弹联合遮蔽时间；代码给出最近导弹和各弹单独时长总和。

**Why selected:** 正文称用层次分解降低最多 45 维组合优化；代码没有实现该 ILP。

**Important assumptions:** 正文假设 `c_ij y_ij` 可加；代码假设最近导弹就是分配对象且每架无人机固定投三弹。

**Key equations or mathematical structure:** 正文式 (10.9) 为整数线性目标；代码是逐无人机最近邻选择与四维网格。

**Implementation notes:** 式 (10.9) 的求和索引与“每机至多三弹、每弹至少一机”文字相反；`fifth.m` 也未调用分支定界或遗传算法，最终 `all_time` 直接累加 15 个单弹时长。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 点目标近似 | rejected | 遮蔽判定 | 真实目标是圆柱，不应只检查中心 | 无定量对照 | 点目标近似的误差 | 拒绝理由合理，但连续圆柱仍被有限采样替代 |
| 圆柱全表面离散 | rejected | 空间判定 | 计算量大；作者用凸性/外轮廓论证只查上下圆周 | n=100--1000 的问题一敏感性 | 对其他场景和内部点的直接对照 | 几何降维有价值，证明与适用范围仍需更严格表述 |
| 梯度下降 | rejected | 问题二优化 | 目标由布尔仿真给出，无解析梯度 | not reported | 平滑替代目标、无梯度基线 | 拒绝传统梯度合理，但不等于所选算法全局可靠 |
| 多起点变步长搜索 | selected | 问题二 | 全局随机起点加局部坐标搜索 | PSO 目标 4.587772 s，对本文 4.587300 s | 等计算预算、重复随机种子、运行时间 | 只支持两个 best-found 值接近，不支持“准确性很高” |
| DE | selected | 问题三/问题四对照 | 适合高维非线性无梯度优化 | 问题四 DE 为 11.645260 s，网格法为 11.125936 s | 重复运行、置信区间、公平预算 | DE 给出更高目标，说明网格法至少存在约 4.46% best-found gap，而非真值误差 |
| 预测拦截点 + 局部网格 | selected | 问题四降维 | 利用物理结构缩小搜索空间 | 与 DE 单次结果比较 | 运行时间、候选数公平比较、搜索域敏感性 | 可迁移的物理初始化，但“效率显著优势”未被数据支持 |
| 任务分配 ILP + 分支定界 | selected in prose / not implemented in available code | 问题五分配 | 先分配再优化以降维 | not assessable | 分配矩阵、求解状态、结果工作簿 | 正文约束索引错误；官方代码走最近邻，不可把 21.0770 s 归因于该 ILP |
| 改进遗传算法 | claimed / not found in available code | 问题五连续参数优化 | 高维组合问题需分层和 GA | none found | GA 编码、适应度、参数、迭代输出 | 在已审查官方 p35--98 代码范围内未发现问题五 GA 实现 |

## 5. Model Pipeline

共享流水线是：

`问题参数 → 运动学位置 → 线段--球相交 → 目标圆柱离散全点判定 → 单云团有效区间 → 区间并/交 → 优化器 → 表格结果`。

- 问题一建立判定器和二分边界搜索。
- 问题二把判定器作为四维黑箱目标，另用 PSO 对照。
- 问题三在逐目标点层面先合并三云团区间，再对所有目标点取交。
- 问题四先做物理初始化和局部网格，再用 12 维 DE 对照。
- 问题五正文计划把 ILP 输出送入三个导弹子问题，并对三个时间集合取交；官方代码没有实现这个接口，而是直接最近邻分配并累加单弹时长。

因此前四问的接口较清楚，问题五不能按正文所述闭合。

## 6. Model Improvements

1. **从点目标升级为圆柱目标。** 避免只遮中心却露出轮廓的明显几何错误；代价是需要边界采样并承担离散误差。
2. **用布尔时间积分统一目标。** 单弹、多弹和多机都可复用相同的遮蔽判定；布尔目标不光滑，优化成本较高。
3. **用区间集合运算代替固定时间步积分。** 官方 `IntervalUnion` / `IntervalInter` 把多云团覆盖与多目标点全覆盖关系明确分开。
4. **问题四先物理降维再局部搜索。** 将“云团靠近导弹--目标视线”转成预测重合点初值；但局部域和最早时刻假设缺敏感性。
5. **跨算法复算。** 问题二用 PSO、问题四用 DE；这种做法能发现局部算法的 best-found gap，但不是独立真实验证。
6. **问题五分层思想。** “任务分配 → 连续策略”本身适合大规模混合优化；本稿的公式和代码没有一致实现，不能复用其具体结果。

## 7. Parameter Estimation and Optimization

本文几乎没有从数据估计参数；大多数为题给物理值、作者理想化假设和算法超参数。随机优化均未报告随机种子或重复运行。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| `v_m` | 导弹速度 | m/s | p6 | 300 | problem-provided | N/A - given | no | 方向指向原点 |
| `v_fy` | 无人机水平速度 | m/s | p17 | `[70,140]` | problem-provided | N/A - given | no | 问题二两个解均接近上界，但未扩域或做边界分析 |
| `r_c` | 烟幕球半径 | m | p4、p9 | 10 | problem-provided | N/A - given | no | 固定 20 s，不扩散 |
| `T_cloud` | 云团有效寿命 | s | p4、p9 | 20 | problem-provided | N/A - given | no | 部分诊断代码未显式限制起爆后 20 s |
| `v_sink` | 云团下沉速度 | m/s | p4、p7 | 3 | problem-provided | N/A - given | no | 仅竖直下沉 |
| `R,H` | 真目标圆柱半径、高度 | m | p9 | 7, 10 | problem-provided | N/A - given | no | 圆柱中心平移至 `(0,200)` |
| `g` | 重力加速度大小 | m/s² | p7、官方代码 | 9.8 | author-assumed | 常数设置 | no | 量纲与抛体式一致 |
| 环境假设 | 无风、无阻力、瞬时成球、半径不变 | N/A | p4、p33 | fixed assumptions | author-assumed | 理想化 | no | 论文自己承认推广时需补风和扩散 |
| `n` | 每个圆周离散点数 | points/circle | p14、p16 | 300；比较 100/200/300/500/1000 | algorithm hyperparameter | 正多边形面积误差与结果收敛 | yes | 只验证问题一；其他代码模块采样数不同 |
| `epsilon` | 二分时间精度 | s | p14--16、官方代码 | 正文 `1e-5`；代码多处 `1e-7`/`1e-8` | algorithm hyperparameter | author setting | partial | 公式、代码容差不一致，未报告对目标的影响 |
| 随机起点数 | 问题二多起点搜索 | starts | 官方 p42--43 | 4 轮 × 2000 | algorithm hyperparameter | uniform random starts | no | 无 `rng` 种子、无重复分布 |
| PSO 设置 | 粒子数、迭代数、惯性权重 | N/A | 官方 p44--46 | 600；1000；`w=0.9`, damp `0.996` | algorithm hyperparameter | author setting | no | 与坐标搜索没有等预算比较 |
| `N,G,F,CR` | 问题三 DE | N/A | p23、官方 p54 | 100, 500, 0.5, 0.9 | algorithm hyperparameter | author setting | no | 无收敛曲线或重复种子结果 |
| 问题四 DE 设置 | 种群、代数、`F`,`CR` | N/A | 官方 p66 | 800, 300, 0.5, 0.9 | algorithm hyperparameter | author setting | no | 注释掉的 warm-start 行未执行，主初始化为随机 |
| 局部网格 | 角度、速度、投放、延迟网格 | rad / points / s | p28、官方 p88 | `theta0±0.2` 步长 0.008；50×80×80 | algorithm hyperparameter | exhaustive local grid | no | 搜索域宽度和分辨率未做敏感性 |
| `c_ij` 代理值 | 无人机 j 对导弹 i 的理论窗口 | s | p32 | `max(0,20-T_fly,ij)` | author-assumed | 固定 140 m/s 与参考点构造 | no | 与真实圆柱遮蔽、区间重叠和多弹边际收益不一致 |

## 8. Validation

本文最可靠的验证是问题一离散点数收敛；两次“不同算法验证”只在同一正向模型、同一目标函数和同一题给场景上比较单次 best-found 值。它们不是独立真实数据验证，也没有相同计算预算、重复种子或误差条。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 问题一圆周离散 | L3 - n 网格扰动 | same sample | 有效时长 | 5 个 n 值 | n≥300 时六位小数均为 1.391643 s | none reported | 只覆盖固定问题一场景 | 支持该场景下 n=300 的数值稳定，不支持所有后续场景 |
| 正多边形逼近圆 | L2 - 独立算术 | theoretical | 面积相对误差 | 5 个 n 值 | 表 2 五个数均与公式复算一致 | N/A | 面积误差不等于遮蔽时长误差 | 支持表 2 算术 |
| 问题二求解器 | L2 - PSO 同目标复算 | same sample | best-found 时长相对差 | 单次，种子未报 | 4.587300 vs 4.587772 s，相差约 0.01029% | 无失败场景 | 同一模拟器、不同预算、无真值 | 支持两个单次 best-found 值接近 |
| 问题三区间结果 | L2 - 表内一致性审计 | same sample | 起止差与总时长 | 3 行 | headline 6.93586 与时长列和 6.93585 接近 | 起止区间与时长列严重不闭合 | 缺 `result1.xlsx` | 不能确认问题三时间区间或 6.93586 s 的语义 |
| 问题四局部网格 | L2 - 表内区间闭合 | same sample | 三段时长之和 | 3 行 | 三行起止差闭合，总和 11.12595 s 与报告差 1.4e-5 s | none reported | 仅内部算术 | 支持表 6 的加和口径 |
| 问题四求解器 | L2 - DE 同目标复算 | same sample | best-found 时长相对差 | 单次，种子未报 | 11.645260 vs 11.125936 s，以 DE 为分母差 4.4595% | DE 给出更高目标 | 非真值、预算不等、无重复 | 说明局部网格有可见 best-found gap，不证明其“误差仅 4.46%” |
| 问题五结果 | L2 - 公式/代码/结果一致性审计 | same sample | 目标与实现接口 | 1 条结果 | 论文报 21.0770 s | ILP、GA、三导弹交集均未在官方代码实现 | 工作簿缺失 | 21.0770 s 的生成链不可确认 |

在已审查的本地 p1--34、官方代码 p35--98 和可得补充材料范围内，未发现合成真值恢复（L4）、外部真实场景验证（L5）、风场/扩散数据对照或独立现场测量。缺失的三个结果工作簿使部分中间结果为 `not assessable`。

## 9. Sensitivity and Robustness

论文只对问题一的圆周离散点数做了明确敏感性实验。算法间单次比较不等同于参数敏感性；正文对风、扩散、半径、寿命、速度误差、初始位置、随机种子、DE/PSO 超参数和问题四局部搜索域均未给扰动实验。

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 每圆周离散点数 n | 300 | 100, 200, 300, 500, 1000 | five-point grid | 问题一有效时长 | 1.391646, 1.391644, 1.391643, 1.391643, 1.391643 s | no for n≥300 | 只证明固定场景的离散收敛；不能外推到采样数不同的其他模块 |

在已审查范围内，未发现联合不确定性传播、随机算法重复运行、物理参数扰动或问题五任务分配稳健性分析。审查范围包括正文 p1--34、官方 MATLAB 代码页 p35--98；`result1/2/3.xlsx` 不可得。

## 10. Visualization Strategy

- 图 2 用关系图展示五问由单机单弹逐步扩展到多机多弹多目标。
- 图 3 展示三维初始几何，帮助产生“迎弹方向”和空间分配直觉。
- 图 4--8 用线段--球相交、导弹视角轮廓和二维截面支撑几何降维。
- 图 9--11 把二分搜索和 DE 流程图化，适合作为比赛论文算法说明模板。
- 图 12 用初始空间分布启发任务分配，但图形直觉后来被直接转成最近邻代码，缺少与正文 ILP 的一致性说明。
- 结果主要用表 3--6 表达收敛、算法比较和策略坐标；问题三表 5 的列间矛盾说明可视化表格仍需自动算术校验。

## 11. Writing Structure

论文按“问题重述 → 分析 → 假设/符号 → 统一模型准备 → 五问递进 → 评价推广 → 附录目录”组织。前四问重复使用统一符号和判定器，叙事链清楚；每次复杂度升级都说明变量维数、约束与求解器选择。

主要写作问题是：

- 把同模型下算法对照称为“准确性和可靠性很高”或“独立验证”，结论越过证据边界。
- 问题二汇总约束、问题三结果表和问题五公式/代码存在未被正文承认的矛盾。
- 问题五先宣称改进遗传算法，随后正文只给分层框架，官方代码又实现最近邻加网格，方法名称与可审计实现脱节。
- 结论和缺点只讨论理想化与行文篇幅，没有披露上述数值与接口问题。

## 12. Strengths

1. 正向物理模型、几何判定和优化变量之间的接口在前四问较明确。
2. 没有把圆柱目标粗暴降为中心点，而是讨论视线、凸性与边界采样。
3. 问题一给出实际 n 扰动，并可由独立算术复核正多边形误差和时长收敛。
4. 区间并/交把“任一云团遮住某点”与“所有目标点均被遮住”区分清楚，适合复用。
5. 问题四的物理初始化展示了如何用机理降低黑箱搜索维度。
6. 官方附录展示 64 页 MATLAB 代码，使公式--代码审计成为可能；这比只给流程图更有证据价值。

## 13. Weaknesses

1. “单弹有效区间必为一个连续区间”的证明依赖“连续且单调就只进出一次”，没有给出覆盖判定量的全局单调性；二分法因此带有未充分证明的结构假设。
2. p18 式 (7.8) 写 `t_b ≥ t_d+1`，但问题二最优起爆延迟只有 0.0497 s，直接违反该汇总约束；代码也没有执行 1 s 的单弹延迟下限。
3. p24 表 5 的两行起止差分别是 4.62001 s、4.07793 s，却给出 2.55600 s、4.37985 s；正文又把第二行贡献写成 4.07793 s。缺工作簿时无法判定哪一列正确。
4. 问题四的 DE 值比局部网格高 0.519324 s。4.46% 是两个 best-found 值的相对差，不是相对于真值的误差。
5. p32 式 (10.9) 的两个求和索引与文字约束相反；若按公式直读，不能表达“每机至多三弹、每枚导弹至少一机”，且非负 `c_ij` 下会鼓励无约束地增加 `y_ij`。
6. 官方 `fifth.m` 没有实现 ILP、分支定界、改进 GA 或三导弹时间集合交集；它按最近导弹分配每架无人机、固定三弹并直接累加各弹时长，无法支撑正文 21.0770 s 的联合遮蔽解释。
7. 官方代码不同 `isOverwhelm` 副本对“导弹在烟幕球内”的处理不一致；p39 强制 false，p98 将该分支注释掉。
8. 随机优化无种子、重复运行、收敛分布或公平预算；物理不确定性也没有进入下游优化。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | 正文与代码给出主要初始坐标和题给常数；p34 引用三个结果工作簿但仓库不可得 | 无法核对完整解向量、中间区间和问题五结果 |
| Code availability | partial | 官方 p35--98 展示 MATLAB 代码图片；本地 PDF 只有支撑目录截图 | 页图不可直接执行，需人工转写且易引入标点错误 |
| Dependency / environment information | not reported | 全文、官方代码附录和可得补充材料 | MATLAB 版本、工具箱、并行环境未记录 |
| Random seed | not reported | 多起点、PSO、DE 初始化代码和正文 | 无法重现单次 best-found 值或评估随机波动 |
| Hard-coded constants | extensive | 官方 p35--98 | 初始坐标、65 s 上界、采样点、种群与网格均硬编码；模块间采样数不同 |
| Formula-to-code consistency | mixed with material contradictions | p18/p24/p32 与官方 p35--98 | 问题二约束、问题五 ILP/GA/交集未一致实现；`isOverwhelm` 副本口径不同 |
| Code-to-result consistency | partially checkable | 表 2--6、官方代码；工作簿不可得 | 表 5 不闭合；表 6 可闭合；21.0770 s 生成链不可确认 |
| Overall reproducibility | partially reproducible | 本地全文 34 页 + 官方代码页 35--98 全范围审查 | 前四问部分结构可按页图重建；缺 `.m`/xlsx/环境/种子，问题五公式--代码断裂 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 抛体与下沉量纲 | `0.5 g Delta t^2`、`3(t-t_b)` | 分别为 m/s²×s² 与 m/s×s | pass | p7 eq. 5.6--5.8 | 仅量纲通过，不验证环境假设 |
| 正 n 边形面积误差 | n=100/200/300/500/1000 对应表 2 | `100[1-n sin(2pi/n)/(2pi)]` 得 0.065784/0.016449/0.007311/0.002632/0.000658% | pass | p14 table 2 | 与报告四舍五入一致 |
| n 收敛 | n≥300 均为 1.391643 s | 表 3 直接比较 | pass | p16 table 3 | 固定场景内部收敛 |
| 问题二约束可行性 | 式 (7.8) 要求 `t_b≥t_d+1`；结果延迟 0.0497 s | 0.0497 < 1，违反 0.9503 s | fail | p18 eq. 7.8；p19--20 result/table 4 | 正文前一段只要求起爆晚于投放，汇总式与结果冲突 |
| 问题二算法相对差 | 4.587300 vs 4.587772 s，称 0.01% | `(4.587772-4.587300)/4.587772=0.010288%` | pass | p20 table 4 | 算术通过；不是预测准确率 |
| 问题三表 5 起止差 | 行 1/2 有效时长为 2.55600/4.37985 s | 起止差为 4.62001/4.07793 s；正文写第二行为 4.07793 s | fail | p24 table 5 and paragraph | 时长列和 6.93585 s 与 headline 6.93586 s 仅差 1e-5，但区间列不支持该总值 |
| 问题四表 6 区间 | 三段时长 4.52271/3.89455/2.70869 s | 三个起止差逐行相等；和为 11.12595 s | pass | p28 table 6 | 与 11.125936 s 差 1.4e-5 s，可由显示精度解释 |
| 问题四算法差 | 11.125936 vs 11.645260 s，称 4.46% | 以 DE 值为分母为 4.45953% | pass | p29 paragraph | 数值口径通过；“误差”解释不成立 |
| 局部网格规模 | 角度步长 0.008、速度 50 点、两时间各 80 点 | 每机 `51×50×80×80=16,320,000`，三机 48,960,000 候选 | concern | p28 algorithm；官方 p88 code | 未报告运行时间；不能仅凭降维声称效率显著 |
| 问题五 ILP 索引 | 文字称每机≤3、每导弹≥1 | 正确索引应分别对 i 求和约束每机、对 j 求和覆盖每导弹；式 (10.9) 反向 | fail | p32 eq. 10.9 | 公式不能表达文字约束 |
| 问题五目标实现 | 正文对三导弹遮蔽集合取交并报 21.0770 s | 官方 `fifth.m` p91 将 15 个单弹 `longest_t` 直接求和 | fail | p33 paragraph；官方 p90--92 code | 不能将代码总和解释为三导弹同时遮蔽时长 |
| 导弹进入烟幕球 | 正文称线段完全在球内也算遮蔽 | p39 代码在 `norm(smoke-missile)<10` 时强制 false；p98 同分支被注释 | concern | p9 paragraph；官方 p39/p98 code | 模块间语义不一致 |

## 14. Reusable Techniques

### 几何判定器与优化器解耦

**When useful:** 决策变量通过仿真产生空间轨迹，目标由可见性、碰撞或覆盖布尔条件定义。

**Why useful:** 同一可信正向判定器可供坐标搜索、PSO、DE 和网格算法复用。

**Limitations:** 必须锁定判定器版本；本稿多个 `isOverwhelm` 副本语义不一致就是典型风险。

### 先证明/审计几何降维，再离散边界

**When useful:** 连续目标集合是凸集或可由极点/边界生成。

**Why useful:** 可显著减少每次目标函数调用的采样量。

**Limitations:** 需要严格说明凸包、视角和边界条件；应对不同场景重复离散收敛检查。

### 区间并集与交集表达多源覆盖

**When useful:** 多个资源各自产生若干有效时间段，目标是覆盖并集或同时满足多个对象。

**Why useful:** 比固定时间步计数更精确，且能明确区分“任一资源有效”和“所有对象有效”。

**Limitations:** 起止区间生成器必须可靠；若错误假设单区间，集合运算仍会继承错误。

### 机理初值加局部优化

**When useful:** 高维黑箱问题存在明确几何或物理近似解。

**Why useful:** 把全局搜索缩到结构合理的邻域，并便于解释策略。

**Limitations:** 要对邻域宽度、边界和多初值做敏感性；还应与等预算全局方法比较。

### 任务分配与连续控制分层

**When useful:** 同时含离散资源指派和连续轨迹/时序参数。

**Why useful:** 可将混合整数高维问题拆成主问题和可并行子问题。

**Limitations:** 主问题代理目标必须与子问题真实边际收益一致，且代码必须真正消费分配矩阵；本稿问题五没有达到这一条件。

## 15. Competition Takeaways

1. 先固定并单测一个几何判定器，再让所有优化算法调用同一实现，避免复制函数产生语义漂移。
2. 对离散边界至少做一个场景外的采样收敛复核，不要把问题一的 n 敏感性直接外推到全部问题。
3. 把“算法 best-found 差”写成求解器一致性证据，不写成相对真值误差或准确率。
4. 每张结果表自动复算 `end-start`、区间并集和总和；表 5 这类矛盾应在交稿前由脚本拦截。
5. 汇总模型中的每条约束必须用最终解重新验算，尤其检查 1 秒间隔、速度上界和烟幕寿命。
6. 混合优化要做公式--代码接口表：分配变量、子问题输入和总目标聚合必须逐项对应。
7. 随机算法报告种子、重复次数、运行时间、目标分布和相同预算，才可比较“稳定”和“高效”。
8. 附录尽量提交可执行源文件和结果表，而非代码截图；同时记录环境和依赖版本。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 本地 34 页与官方主文一致，官方另有 35--98 页代码附录 | interpretation | 本地 1,2,17,34；官方 1,2,17,34,49,98 | version review | paragraph / code | derived interpretation | N/A for positive evidence | p49 为 `get_last_time` 代码中段，p98 为 `isOverwhelm` 结尾；保留 O* |
| 导弹、无人机、烟幕弹和云团使用匀速/抛体/下沉方程 | explicit | 6--7 | 5.1 | equations 5.1--5.8 | notation normalization | N/A for positive evidence | g 和速度单位按原页 |
| 遮蔽由线段--球二次方程和圆柱全点条件定义 | explicit | 8--10 | 5.2 | equations 5.11--5.23 | notation normalization | N/A for positive evidence | 关键公式经视觉核验 |
| 作者声称单弹有效时间必为单一连续区间 | explicit | 12 | 6.2.1 | paragraph | direct transcription | N/A for positive evidence | 作为二分法前提 |
| 连续运动不足以单独证明遮蔽判定只进入/退出一次 | criticism | 12 | 6.2.1 | paragraph | derived interpretation | p12 的完整论证与官方 `get_last_time` 搜索代码 p35--53 | 未给覆盖判定量单调性证明 |
| 正 n 边形面积误差表算术正确 | interpretation | 14 | 6.2.3 | table 2 | independent calculation | N/A for positive evidence | 五个 n 值均复算通过 |
| n≥300 时问题一结果在六位小数稳定 | explicit | 16 | 6.4.1 | table 3 | direct transcription | N/A for positive evidence | L3，固定场景 |
| 问题二选择多起点变步长搜索因为目标无解析梯度 | explicit | 18--19 | 7.2.1 | paragraph / algorithm | direct transcription | N/A for positive evidence | 全局最优措辞不由有限起点保证 |
| 式 (7.8) 的 1 秒延迟约束被报告解违反 | criticism | 18--20 | 7.1.4--7.3 | equation 7.8 / table 4 | independent calculation | p18 汇总约束、p19 结果、p20 表 4、官方相关代码 p35--50 | 0.0497 < 1 |
| 问题二两算法目标差约 0.01029% | interpretation | 20 | 7.3 | table 4 | independent calculation | N/A for positive evidence | 只表示单次 best-found 接近 |
| 问题三 DE 参数为 N=100、G=500、F=0.5、CR=0.9 | explicit | 23；官方 54 | 8.2.1 / `third.m` | paragraph / code | direct transcription | N/A for positive evidence | 正文和代码一致 |
| 问题三表 5 的区间和时长不闭合 | criticism | 24 | 8.2.2 | table 5 / paragraph | independent calculation | p24 全表与相邻解释；`result1.xlsx` 不可得 | 两行起止差与时长列均不一致 |
| 问题四由预测重合点构造初值再局部网格微调 | explicit | 26--28 | 9.2.1 | equations 9.6--9.11 / algorithm | notation normalization | N/A for positive evidence | 物理初始化属于近似 |
| 问题四表 6 三段时长可由起止时刻复算 | interpretation | 28 | 9.2.2 | table 6 | independent calculation | N/A for positive evidence | 总和与正文差 1.4e-5 s |
| 问题四 DE 结果比网格法高 0.519324 s，文中 4.46% 算术成立 | interpretation | 29 | 9.3 | paragraph | independent calculation | N/A for positive evidence | 不是相对真值误差 |
| 问题四局部网格三机至多评估 48,960,000 个候选 | interpretation | 28；官方 88 | 9.2.1 / `fourth_grid.m` | algorithm / code | independent calculation | N/A for positive evidence | 51×50×80×80×3 |
| 在已审查范围内未发现运行时间或公平预算比较 | criticism | 18--29；官方 35--89 | 问题二--四求解 | none found | derived interpretation | 正文 p18--29、官方代码 p35--89；无可得运行日志 | “效率显著”缺运行证据 |
| 问题五正文目标要求三枚导弹均被遮蔽 | explicit | 29--31 | 10.1.2--10.1.4 | equations 10.2--10.7 | direct transcription | N/A for positive evidence | 最终应对应三个时间集合交集 |
| 式 (10.9) 求和索引与文字约束相反 | criticism | 32 | 10.2.1 | equation 10.9 / paragraph | derived interpretation | p32 的变量定义、文字与完整公式 | 不能表达每机≤3、每导弹≥1 |
| 正文称问题五用 ILP 分支定界、分层与改进 GA | explicit | 31--33 | 10.2 | paragraph / equation | direct transcription | N/A for positive evidence | 报告总时长 21.0770 s |
| 官方 `fifth.m` 实际按最近导弹分配并固定三弹 | criticism | 官方 90--92 | `fifth.m` | code | derived interpretation | 官方 p90--92 完整主循环和 grid_search；p35--98 全附录搜索 | 未见 ILP、分支定界或 GA 调用 |
| 官方 `fifth.m` 直接累加单弹时长而非三导弹时间交集 | criticism | 官方 91 | `fifth.m` | code | direct transcription | 官方 p90--92；与正文 p29--33 对照 | `all_time += longest_t1+longest_t2+longest_t3` |
| 21.0770 s 的正文生成链不可确认 | criticism | 33；官方 90--92 | 10.2.3 / `fifth.m` | paragraph / code | derived interpretation | 正文 p29--33、官方 p90--92；`result3.xlsx` 不可得 | 目标聚合口径冲突 |
| `isOverwhelm` 对导弹进入烟幕球的处理在模块间不一致 | criticism | 官方 39,98 | support code | code | direct transcription | 官方 p35--98 中各函数副本 | p39 强制 false；p98 注释该分支 |
| 在已审查范围内未发现随机种子或重复运行分布 | criticism | 18--29；官方 35--89 | optimization | none found | derived interpretation | 正文所有随机优化段、官方多起点/PSO/DE 代码；无可得运行日志 | 不等于算法没有随机性 |
| 在已审查范围内未发现物理参数联合敏感性或外部真实验证 | criticism | 1--34；官方 35--98 | validation / evaluation | none found | derived interpretation | 本地全文、官方完整代码附录；三个结果工作簿不可得 | 仅 n 敏感性和同模型算法对照 |
| 官方代码附录存在，但原始 `.m` 和结果工作簿不可得 | explicit | 34；官方 35--98 | appendix | figure / code | direct transcription | N/A for positive evidence | 代码页可审计但不可直接运行 |
