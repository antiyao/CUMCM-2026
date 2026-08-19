# Paper: 基于优化算法的农作物最优种植模型

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_dafa80747f5e
- Year: 2024
- Problem: C
- Award: 组委会官方展示代码与年份匹配；具体奖项等级未核验
- Provenance tier: O; 本地 PDF 的 2024 C063 代码、49 页页数与官方展示记录匹配，官方展示不证明奖级
- Source file: literature/raw_papers/2024/C063.pdf
- Source URL: unknown；acquisition 记录为用户提供并与官方展示交叉匹配的本地副本
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2024qgdxssxjmjslwzs_2024ctlw/241104/1977958.shtml
- Pages: 49
- SHA-256: 138a32f817443e055e5f87b6fa317905aaac2d24f6e554b59782559511e8e34d
- Extraction method: OCR fallback；原 PDF 对 pypdf 6.10.0 报 `PdfReadError: Could not read Boolean object`，故使用 Ghostscript `pdfwrite` 临时兼容副本供仓库 OCR helper 计页；原件与副本均为49页，100 DPI 下49/49页 Poppler 渲染逐像素一致；随后以 Tesseract 5.5.0 `chi_sim+eng`、250 DPI、PSM 3 OCR，质量记录重新锚定原 PDF 路径与 SHA-256
- Extraction quality: OCR 49/49 页均超过30个非空白字符，中位数639字符/页，无页级失败；公式、表格、图和附录代码均以原 PDF 渲染核验，OCR只用于检索
- Page convention: 1-based physical PDF pages
- Visually checked pages: p.1 标题/摘要与三问结果；p.13 式(5-6)–(5-15)目标和地类约束；p.15 式(5-25)–(5-28)集中度/最小面积；p.18 图17–18灵敏度；p.27风险决策、16状态与maximin；p.28–29正态假设及11状态表；p.34式(7-4)与问题三结果表；p.36–38 MATLAB评估代码、LINGO集合与目标；p.41 LINGO输出/年度利润；p.47附录收益表
- Unresolved extraction ambiguities: p.16–17、p.23–25、p.33–34的大括号模型在扫描件中排版密集，报告仅转写经视觉确认的目标/约束结构；p.42–46外部统计年鉴截图字号过小且与主模型参数接口未说明，不据此提取具体数值
- Supplemental artifacts: PDF 内含 MATLAB/LINGO 代码片段和若干数据表；题目附件、`CM2024C_TTO1.xlsx`、`CM2024C_result1_1.xlsx`、`CM2024C_result2_11.xlsx`、随机数工作簿及实际运行日志均为 referenced but unavailable

## 1. Problem Archetype

本文是多期、多地块、多季次的混合离散—连续农业规划，并叠加场景模拟与风险决策：

1. **确定性种植优化**：在54个地块、41种作物、两季、2024–2030年上最大化利润，分别处理超产浪费和半价出售。
2. **随机场景/鲁棒决策**：对销量、亩产、成本和价格设区间分布，生成状态并以期望或最坏收益选方案。
3. **替代、互补与相关性扩展**：以作者定义的替代/互补系数和线性销量关系修正问题二。

结构覆盖题目三问，但正文在“11个典型候选方案”“16个状态方案”和代码实际读取的7个方案之间不一致；LINGO附录还把年份集合声明为 `Y1..Y3` 却访问到第8期，并在优化目标中错误地加回第二季成本。因此报告利润只能作为作者声称的输出，不能视为已复现的可行最优值。

## 2. Problem Decomposition

1. **数据基线**：把2023年种植产量作为未来预期销售量；价格区间取中点；计算作者声称的2023年总收益5926348.25元。
2. **问题一**：定义第一/第二季面积和0-1种植标志，加入地块适宜性、面积、重茬、三年豆类、集中度和单块最小面积约束；用 LINGO Global Solver 求两种超产处置。
3. **问题二参数化**：按题定区间描述小麦/玉米销量、其他销量、亩产、成本、蔬菜/食用菌价格；另提出自然灾害和市场风险变量。
4. **风险决策**：生成1000个均匀随机状态，使用若干候选种植方案形成收益矩阵，并讨论最大期望、乐观和悲观/maximin准则。
5. **问题三**：以亩利润/成本差定义替代策略，以作物高度或豆类改土定义互补策略，再提出销量对价格和成本的线性关系，比较四种组合情形。
6. **附录实现**：MATLAB生成随机数并评估固定方案，LINGO代码求基础规划；输入/输出工作簿未提供。

## 3. Data Processing

- 54个耕地单元由34块露天地/水浇地、16个普通大棚、4个智慧大棚组成；作物编号1–41。
- 附件2中的价格区间取上下限算术平均，未传播价格区间不确定性到问题一。
- 2023年逐地块面积、亩产、成本和价格被转换为54×41的第一/第二季矩阵；不可种组合填0。
- 2023年各作物当季总产量直接作为预期销售量基线，未建立独立需求数据。
- 问题二按四维随机向量生成状态；MATLAB实际仅使用小麦/玉米销量、其他作物销量、亩产、食用菌价格四列，成本和蔬菜价格按固定5%增长。
- 问题三声称分析销量、价格、成本相关性，但正文只给通用线性式和经济学方向，未给样本、回归系数、拟合指标或估计输出。
- 在已审查范围内，未发现对附件缺失值、重复地块—作物记录、价格区间异常、单位一致性或随机状态相关结构的正式清洗审计；审查覆盖p.1–35正文、p.35–41代码和p.42–49附录表，外部工作簿不可得。

## 4. Models Used

### 多期种植利润规划

**Purpose:** 在作物适宜性、轮作和管理约束下分配七年种植面积。

**Inputs:** 地块面积、亩产、成本、价格、预期销售量、地类/季次规则。

**Outputs:** 第一/第二季面积 `x,y`、二元标志 `F,G`、年度及七年利润。

**Why selected:** 作者指出多数约束为线性，`min/max`目标适合由 LINGO 全局求解器处理。

**Important assumptions:** 每作物每季最多5个地块；单块面积占比至少25%；以2023产量代表需求；未售部分浪费或五折销售。

**Key equations or mathematical structure:** 式(5-6)–(5-10)以 `min(total,pre)` 和 `max(total-pre,0)`构造分段收入；式(5-11)–(5-28)表达面积、地类、重茬、豆类、集中度和最小面积。

**Implementation notes:** LINGO附录并非可运行的七年实现：`Years/Y1..Y3/`与 `X7=X(...,8)`矛盾；优化目标把成本写成 `X*C-Y*CC` 后整体相减，等价于加回第二季成本，而年度 `Prof` 又正确减去 `X*C+Y*CC`。

### Monte Carlo 状态评估与悲观/maximin决策

**Purpose:** 在销量、亩产、成本和价格不确定时选择下界较高的方案。

**Inputs:** 四维均匀/正态状态、候选种植方案、同一利润计算器。

**Outputs:** 状态×方案收益矩阵及期望、乐观或最坏准则下的方案。

**Why selected:** 作者希望避免只在单一预测状态最优，强调粮食安全下的抗风险能力。

**Important assumptions:** 给定边界足以描述不确定性；1000状态代表未来；极端状态可由分布边界或3σ裁剪处理。

**Key equations or mathematical structure:** 对每个方案 `n` 计算 `min_m W_mn`，再取 `max_n min_m W_mn`；另讨论平均收益最大化。

**Implementation notes:** 正文/摘要分别出现11、16个候选方案；MATLAB仅载入7个工作表并完成 `1000×7=7000` 次方案—状态评估，且未设随机种子。

### 替代—互补—销量相关扩展

**Purpose:** 回答问题三对作物替代/互补及销量—价格—成本相关性的要求。

**Inputs:** 亩利润、成本、作物高度、豆类改土概念、价格和成本。

**Outputs:** 替代策略1/2、互补策略1/2、预测销量模型1/2及四种利润。

**Why selected:** 作者认为同类地块上的近似亩利润/成本可表达经济替代，空间/生态差异可表达互补。

**Important assumptions:** 近似利润或成本即替代；高度差或豆类种植即互补；销量可由价格和成本线性解释。

**Key equations or mathematical structure:** p.30–32定义距离/归一化系数、产量修正 `D=d(1+H)` 及 `Y=beta0+beta1 X1+beta2 X2+beta3 X3+epsilon`。

**Implementation notes:** 阈值、系数、回归样本和估计值均未报告；附录没有问题三实现，四种情形无法重算。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 线性/混合规划 + LINGO | selected | 问题一面积配置 | 多数约束和目标关系近似线性，LINGO表达接近数学式 | 报告两种处置利润 | 无可行性残差、求解状态、最优界或独立求解器 | 模型原型合适；附录代码错误使结果不可认证 |
| 均匀分布 | selected | 问题二主状态生成 | 题目只给上下界，作者据此等概率抽样 | 1000状态声称；MATLAB有生成器 | 无分布拟合、相关性、种子和抽样误差 | 是透明的假设，不是数据估计 |
| 正态分布 | considered only | 概率加权状态 | 作者用3σ原则忽略小概率尾部 | 无完整结果表 | 均值/标准差定义、截断后归一化和实现均缺 | 只停留在概念，不能视为已实现 |
| 最大期望准则 | selected/claimed | 风险方案选择 | 最大化平均利润 | p.27报告70131049.92元 | 候选数与对应方案、方差/置信区间缺失 | MATLAB可评估均值，但输入工作簿不可得 |
| 乐观准则 | considered only | 风险偏好比较 | 取方案的最大可能收益 | not reported | 无结果 | 仅定义，无比较证据 |
| 悲观准则/maximin | selected/claimed | 鲁棒方案 | 粮食安全要求不利条件下仍有较大收益 | p.27文字与摘要6374万元 | 收益矩阵、选中列、最坏状态均缺 | 可称有限场景maximin，不能称全域鲁棒最优 |
| 替代/互补四组合 | selected | 问题三扩展 | 分别表示经济替代、空间/生态互补 | p.34四情形利润 | 系数、阈值、代码和同约束可行性均缺 | 结果是未复现情景比较，不是机制验证 |

## 5. Model Pipeline

`附件1/2 → 价格中点与2023需求基线 → 54×41×季次矩阵 → 确定性规划 → 两种超产处置`。

问题二理论管线为 `题定区间 → 11/16个典型状态各求一方案 → 1000随机环境 → 收益矩阵 → 期望/乐观/maximin选择`。附录实际管线则是 `7个外部Excel方案 → 1000×4随机矩阵 → 逐年更新参数 → 1000×7总利润`，与正文候选规模不闭合。

问题三管线为 `亩利润/成本/作物特征 → 替代与互补系数 → 销量线性关系 → 修正同一规划 → 四情形利润`，但中间系数、预测模型和代码均缺失，无法核查是否真正进入目标和约束。

## 6. Model Improvements

1. 从单一确定参数扩展到销量、亩产、成本和价格不确定性，并把方案在多状态下重新评价。
2. 从平均收益扩展到有限状态 maximin，概念上可约束最坏场景表现。
3. 以集中度和单块最小面积把管理可执行性显式化，并对阈值做有限扫描。
4. 在问题三尝试把替代、互补和经济变量相关性回写到决策模型。

这些升级的逻辑顺序清楚，但证据没有闭合：随机候选数前后矛盾，3σ正态方案未落地，问题三系数没有估计，附录优化目标和年份集合还存在结构性错误。

## 7. Parameter Estimation and Optimization

作者使用 LINGO 20.0 Global Solver，并把变量上限设为1000000，但没有报告求解状态、gap、运行时间或初始化。随机状态由 MATLAB `unifrnd` 生成，无种子。面积占比扫描只展示0.25、0.30、0.40、0.50四点，地块数只比较 `Num+1` 与 `2(Num+1)`。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| `i,j,t` | 地块、作物、年份索引 | N/A | p.4–5 | 54、41、2024–2030 | problem-provided | 题面/附件 | no | 代码另含2023基期，理论应8个时间点 |
| `p_j` | 销售单价 | 元/斤 | p.5 表1 | 价格区间中点 | author-assumed | 上下限算术平均 | no | 区间不确定性在问题一被压成点值 |
| `pre_j` | 预期销售量基线 | 斤/季 | p.6 式(5-1) | 2023实际产量 | author-assumed | 以产代需 | partial | 问题二再施加区间变化 |
| `m_j` | 每作物每季最大地块数 | 个 | p.15 式(5-25)–(5-26) | 5 | author-assumed | 由2023除羊肚菌外均少于5概括 | yes | 图18只比较两个离散水平 |
| `alpha` | 单块最小种植面积占比 | dimensionless | p.15 式(5-27)–(5-28) | 0.25 | author-assumed | 四点扫描后选最高利润点 | yes | 无更细网格或管理依据 |
| wheat/corn growth | 小麦玉米销量年增长 | dimensionless/year | p.20–21 | 5%–10% | problem-provided | 均匀或正态假设 | yes | 典型状态表取5%、7.5%、10% |
| other-sales change | 其他作物销量变化 | dimensionless | p.21 | -5%–5% | problem-provided | 均匀或正态假设 | yes | MATLAB每年相对基线一次变化，不复利 |
| yield change | 亩产变化 | dimensionless | p.21、p.24、p.35 | -10%–10% | problem-provided | MATLAB均匀抽样 | yes | p.21式(6-14)视觉/OCR显示±5%，与题面和代码±10%矛盾 |
| cost growth | 种植成本年增长 | dimensionless/year | p.21 式(6-16) | 5% | problem-provided | 固定复利 | partial | 未单独给敏感性数表 |
| vegetable price growth | 蔬菜价格年增长 | dimensionless/year | p.21、p.36代码 | 5% | problem-provided | 固定复利 | partial | 情景表未单列 |
| mushroom decline | 食用菌价格年变化 | dimensionless/year | p.21–22、p.35代码 | -5%至-1%；羊肚菌-5% | problem-provided | 均匀抽样/固定复利 | yes | p.22式(6-22)写成±5%，代码为-5%至-1% |
| random states `K` | Monte Carlo环境数 | 个 | p.1、p.26、p.35代码 | 1000 | algorithm hyperparameter | 固定 | no | 无种子/收敛诊断 |
| candidate plans | 风险决策候选数 | 个 | p.1、p.27、p.35–37 | 11 / 16 / 7 | algorithm hyperparameter | 典型状态求解后导入 | no | 三处互相矛盾；代码为7 |
| normal cutoff | 正态尾部裁剪 | standard deviations | p.28 | ±3σ | author-assumed | 3σ规则 | no | 分布记号把第二参数写成3σ，定义不规范 |
| `q,v,r,s` | 灾害/市场发生概率与等级 | mixed | p.22 式(6-24)–(6-25) | not reported | author-assumed | 概念设定 | no | 未进入可见代码或结果表 |
| solver upper bound | LINGO变量上限 | mixed | p.18、p.27 | 1000000 | algorithm hyperparameter | 手动设置 | no | 未按变量单位分开设置 |
| `L,H`及阈值 | 替代/互补系数 | mixed | p.30–32 | not reported | author-assumed | 利润/成本距离、高度/豆类概念 | no | 阈值和归一化定义缺失 |
| `beta0...beta3` | 销量线性模型系数 | mixed | p.32 式(7-2) | not reported | data-estimated | 声称相关分析，实际估计未报告 | no | 无样本、拟合和误差 |

## 8. Validation

证据主要是同一模型的情景输出和有限参数扫描，属于 L1–L3；没有独立农业年份、基准策略、可行性证书或重复求解。附录错误还削弱了内部一致性证据。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 问题一两种处置 | L2 情境算术对比 | same sample | 七年利润 | 2 scenarios | 4530万元与6469万元 | 无可行性残差/solver gap | 同一附件和模型 | 只支持作者报告的处置情境差异 |
| 最小面积占比 | L3 单参数网格 | same sample | 七年利润 | 4 levels visible | 0.25在四点中最高，约4530万元 | 未测0.25以下和细网格 | 与地块数固定值混杂 | 只支持所绘四点中的best-found |
| 地块数量上限 | L3 两情境比较 | same sample | 七年利润 | 2 levels | `2(Num2023+1)`高于`Num2023+1` | 仅两点 | 取值定义/作物异质性未展开 | 不能证明全域最优阈值 |
| 11个典型状态 | L3 边界/OAT情境 | same sample | 七年利润 | 11 states | 5669.96–7122.81万元 | 候选状态不等于联合分布验证 | 只展示参数角点/均值 | 支持局部方向比较 |
| 1000随机环境 | L3 Monte Carlo情境 | synthetic-same-model | 方案总利润 | 1000 states claimed | 摘要报告maximin约6374万元；p.27另报均值最优70131049.92元 | 候选数7/11/16矛盾，无矩阵/种子 | 同一模型生成和评价，输入方案不可得 | 不能确认鲁棒最优或抽样稳定性 |
| 问题三四组合 | L2 模型变体结果 | same sample | 七年利润 | 4 scenarios | 5988.62–6524.48万元 | 系数、实现和可行性缺失 | 不能隔离三个改动各自作用 | 仅记录作者输出 |
| 外部农业表现 | not reported | external | 实际利润、产量或履约 | not reported | not reported | 无2024真实结果/留出年份 | 仅题目附件 | 不构成L5验证 |

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 超产处置 | 滞销浪费 | 半价出售 | two scenarios | 七年利润 | 4530→6469万元，增1939万元/42.80% | yes | 题目情境比较，非稳健性证明 |
| 单块面积占比 | 固定地块数 | 0.25、0.30、0.40、0.50 | small grid | 七年利润 | 0.25为绘图最高点 | unclear | 下边界获优，应继续向0.25以下扩域 |
| 每作物地块数 | 面积占比0.25 | `Num+1`与`2(Num+1)` | two levels | 七年利润 | 后者较高 | unclear | 仅两点且没有管理成本 |
| 小麦/玉米及其他销量 | 平均状态 | 题定边界/OAT | 11 typical scenarios | 七年利润 | 6464.40 vs 6305.27万元，差159.13万元 | no | 局部情景方向成立，未传播联合相关性 |
| 亩产 | 0 | -10%至10% | boundary scenarios | 七年利润 | 5813.74–6962.86万元 | no | 单因素边界，无概率/重复 |
| 食用菌价格 | -3% | -5%至-1% | boundary scenarios | 七年利润 | 6310.07–6400.44万元 | no | 差90.37万元，仅一类价格 |
| 四维不确定性 | 平均状态 | 1000个均匀样本 | Monte Carlo claimed | 七年收益矩阵 | 选中方案约6374万元（摘要） | unclear | 候选数、矩阵、种子和最坏状态未提供 |
| 替代/互补/销量模型 | 问题2 6024.45万元 | 4组合 | factorial-like scenarios | 七年利润 | -35.83至+500.03万元 | yes for some | 多组件同时改变，不能归因单一机制 |

## 10. Visualization Strategy

- 图1–4展示季节产量和地类作物结构，帮助识别作物—地类可行组合。
- 图5–12逐地类对比亩成本和亩收入，为替代分析提供经济直觉，但多图重复且缺误差范围。
- 图17–18直接画出集中度参数与利润，适合作为局部参数选择证据；只有4点和2点，不能支持全局最优措辞。
- 图19–20展示年利润与年种植数量，却没有给年度数值表或约束违反量。
- p.28–29的11状态表比纯文字更可审计；问题三结果表则缺系数和方案细节。
- 附录表保留部分输入/收益，但外部 Excel 仍是核心接口，图表不能替代可运行数据包。

## 11. Writing Structure

全文按“数据描述—问题一确定性模型—问题二随机/风险扩展—问题三相关性扩展—附录代码”递进，主线清楚。问题一约束按地类、重茬、豆类、集中度逐项写出，便于核查。

主要写作风险是同一概念多套口径并存：候选方案为11/16/7，问题二利润为6374/7013.10/6024.45万元，均匀、正态、乐观、期望、悲观准则没有逐一对应结果；“鲁棒优化”也只是有限场景 maximin。正文应增加一张“状态生成—候选方案—选择准则—输出利润”对照表，并给公式—代码一致性检查。

## 12. Strengths

1. 用 `min/max` 分段收入同时表达滞销和折价处置，经济含义清楚。
2. 把地类、季次、重茬、豆类轮作、集中度和最小面积都显式列为约束，覆盖题目主要规则。
3. 从确定性基线到随机状态再到替代/互补的递进符合三问结构。
4. 报告了多组具体利润和参数扫描，允许独立算术复核。
5. 附录公开 MATLAB/LINGO 片段，使年份集合、成本符号和候选数矛盾可被发现。

## 13. Weaknesses

1. LINGO代码年份集合仅3期却访问第8期，优化目标还把第二季成本加回；附录不能执行或不能优化正文目标。
2. 7、11、16个候选方案口径矛盾，1000状态收益矩阵和选中方案均未提供。
3. maximin只覆盖作者抽样的有限状态，不能推出全不确定域鲁棒性。
4. 问题三的替代/互补阈值、回归系数、数据和代码缺失，四情形利润不可重算。
5. 没有solver gap、方案可行性残差、随机重复、基准策略或外部年度验证。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | p.42–49有统计截图/收益表；全文引用附件与多个Excel | 核心附件和矩阵工作簿不可得 |
| Code availability | partial | p.35–41含MATLAB/LINGO片段 | 不是完整工程；问题三代码缺失 |
| Dependency / environment information | partial | 报告 LINGO 20.0；MATLAB版本/工具箱未报 | `unifrnd/xlsread`环境不可锁定 |
| Random seed | not reported | p.35–37全部随机代码已审查 | 1000状态不可精确重现 |
| Hard-coded constants | extensive | p.18、p.27、p.35–41：0.25、5、1000、1000000及本地绝对路径 | 参数与路径不可移植 |
| Formula-to-code consistency | contradicted | 对照p.13–18、p.20–34公式与p.35–41代码 | 年份集合、第二季成本、亩产/菌价区间和候选数不一致 |
| Code-to-result consistency | contradicted | 对照摘要/p.27/p.34利润与MATLAB 7方案接口 | 6374/7013.10/6024.45万元缺准则映射，外部结果表不可得 |
| Overall reproducibility | not reproducible | 审查49页正文、附录表、全部可见代码及现有仓库附件 | 缺输入/输出，代码结构性错误，问题三未实现 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 两种超产处置利润差 | 4530 vs 6469万元 | 差1939万元，相对4530增42.80% | pass | p.1 摘要 | 数值闭合，不证明方案可行 |
| 销量情景影响 | 降低约160万元 | 6464.40-6305.27=159.13万元 | pass | p.28–29 表 | 对应两个销量边界情景 |
| 食用菌价格影响 | 变化约90万元 | 6400.44-6310.07=90.37万元 | pass | p.28–29 表 | 文本“变化率达到峰值”含糊 |
| 两类销量交叉情景 | 总利润变化85.5万元 | 6416.14-6329.70=86.44万元 | fail | p.29 表/段落 | 相差0.94万元，非四舍五入口径 |
| 问题三情形1增益 | 6024.45→6524.48万元 | 增500.03万元，8.30% | pass | p.34 表 | 同表算术闭合 |
| 正态3σ尾部 | ±3σ外小于0.3% | 标准正态双侧概率约0.26998% | pass | p.28 段落 | 但分布参数记号不规范 |
| 候选方案规模 | 摘要11组，正文16组 | MATLAB `FangAn=cell(1,7)`且循环`j=1:7` | fail | p.1、p.27、p.35–37 code | 实际代码为7方案×1000状态=7000次评价 |
| LINGO年份维数 | 需覆盖2023基期+2024–2030 | 集合仅`Years/Y1..Y3/`，后文访问`X(...,8)` | fail | p.37、p.41 code | 索引越界，代码不可运行 |
| 第二季成本符号 | 利润=收入-两季成本 | 目标为`-sum(X*C-Y*CC)`，等价于`-X*C+Y*CC` | fail | p.38 code | p.41 `Prof`才使用`X*C+Y*CC` |
| 亩产随机范围 | 题定±10% | p.21式(6-14)写均匀±5%，p.35代码用±10% | fail | p.21 equation; p.35 code | 公式—代码矛盾 |
| 食用菌降价范围 | 年降1%–5% | p.22式(6-22)写±5%，代码用-5%至-1% | fail | p.22 equation; p.35 code | 代码更接近题意 |
| 问题二利润口径 | 摘要6374万元 | p.27为70131049.92元=7013.104992万元；p.34基线6024.45万元 | concern | p.1、p.27、p.34 | 可能对应不同准则，但论文未映射 |
| 面积占比最优 | 0.25最优 | 可见扫描点仅0.25、0.30、0.40、0.50，最优在最小边界 | concern | p.18 图17 | 应向0.25以下扩域并检查管理可行性 |

## 14. Reusable Techniques

### 分段销售收入

**When useful:** 产量超过需求后存在滞销、折价或处理成本时。

**Why useful:** `min(production,demand)` 与 `max(production-demand,0)` 可把两段收入写在一个目标中。

**Limitations:** 需求必须按作物/季次正确聚合；两季成本与销售量不能漏项或符号错误。

### 候选方案—状态矩阵

**When useful:** 精确随机规划过大，但能先生成少量可行候选方案时。

**Why useful:** 同一批状态下比较期望、分位数与最坏收益，决策准则透明且易审计。

**Limitations:** 必须固定候选数、状态数、种子和概率权重；有限样本maximin不等于全域鲁棒最优。

### 约束阈值扫描

**When useful:** “不宜太分散/面积不宜太小”等定性要求需转为数值约束时。

**Why useful:** 把管理偏好和利润权衡显式化。

**Limitations:** 至少要扩域、细化网格并报告可行性；边界最优不能直接宣布最终最优。

### 公式—代码—结果三向核对

**When useful:** 使用多期索引、两季变量和外部工作簿的优化报告。

**Why useful:** 可快速发现年份维数、成本符号、候选数量和输出口径断裂。

**Limitations:** 需要提供可执行源码、输入和结果文件；扫描代码只能支持审计，不能自动复现。

## 15. Competition Takeaways

1. 先建立可运行的确定性基线，并输出每类约束的最大违反量和solver gap。
2. 分段收入中逐项核对第一/第二季销售与成本符号，避免目标和报告利润不一致。
3. 用一张表固定“候选方案数、状态数、分布、准则、选中方案和利润”，不允许11/16/7并存。
4. 有限样本 `max-min` 只能称场景集上的maximin；报告样本外压力测试和抽样稳定性。
5. 随机模拟要保存种子、状态矩阵和收益矩阵，至少做多次独立抽样。
6. 定性管理阈值若最优命中边界，应扩域并加入管理成本，而非直接定为最优。
7. 替代/互补和销量相关性要给数据、系数、显著性/不确定性及代码，不能只靠经济学叙述。
8. 提交前做索引维数和公式—代码单元测试；`Y1..Y3`访问第8期应在运行前被拦截。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 论文建立54地块、41作物、两季、多年利润规划 | explicit | 5, 12–17 | 5.1 | equations (5-3)–(5-30) | notation normalization | N/A for positive evidence | OCR后以p.13、15原页核验目标/约束 |
| 超产浪费与五折出售分别报告4530、6469万元 | explicit | 1 | 摘要 | paragraph | direct transcription | N/A for positive evidence | 作者报告值 |
| 2023年总收益为5926348.25元 | explicit | 5 | 5.1.1 | paragraph | direct transcription | N/A for positive evidence | 附录完整工作簿不可得，未整表复算 |
| 每作物最多5地块、单块最小占比25% | explicit | 15, 18 | 5.1.2–5.3.1 | equations (5-25)–(5-28), figure 17 | direct transcription | N/A for positive evidence | 5来自作者对2023分布概括；0.25来自四点扫描 |
| 0.25只是在可见四个扫描点中的best-found | criticism | 18 | 5.3.1 | figure 17 | derived interpretation | p.18图17及说明已审查 | 最优命中扫描下边界 |
| 问题二对四类因素生成1000随机环境 | explicit | 1, 26, 35 | 摘要；6.5；附录 | paragraph, code | direct transcription | N/A for positive evidence | MATLAB `K=1000` |
| 正文讨论期望、乐观和悲观三准则 | explicit | 23, 25 | 6.4 | paragraph | direct transcription | N/A for positive evidence | 只有部分结果可见 |
| 悲观准则是有限场景上的`max_n min_m W_mn` | interpretation | 25, 27 | 6.4–6.5 | equation, paragraph | notation normalization | N/A for positive evidence | 不能外推到连续不确定域 |
| 正常3σ外双侧概率约0.26998% | interpretation | 28 | 6.5 | paragraph | independent calculation | N/A for positive evidence | 标准正态复算通过，原分布记号仍含糊 |
| 11个典型状态利润为5669.96–7122.81万元 | explicit | 28–29 | 6.6 | table | direct transcription | N/A for positive evidence | 表格视觉核验 |
| 销量情景差159.13万元、菌价情景差90.37万元 | interpretation | 28–29 | 6.6 | table | independent calculation | N/A for positive evidence | 支持作者约160/90万元的量级 |
| 交叉销量情景差86.44万元而非85.5万元 | criticism | 29 | 6.6 | table, paragraph | independent calculation | p.28–29完整11状态表和随后解释已审查 | 数值不闭合 |
| 问题三用替代/互补和销量线性关系修正规划 | explicit | 29–34 | 7.1–7.4 | equations, paragraphs | direct transcription | N/A for positive evidence | 系数未报告 |
| 问题三情形1比基线高500.03万元/8.30% | interpretation | 34 | 7.5 | table | independent calculation | N/A for positive evidence | 6524.48-6024.45 |
| 在已审查范围内，未发现问题三系数估计、阈值或实现代码 | criticism | 29–41 | 7；附录代码 | none found | derived interpretation | p.29–34问题三正文、p.35–41全部代码已审查 | 外部工作簿不可得 |
| MATLAB只载入7个候选方案 | explicit | 35–37 | 附录9.1 | code | direct transcription | N/A for positive evidence | `cell(1,7)`、`for j=1:7` |
| 7方案与摘要11组、正文16组矛盾 | criticism | 1, 27, 35–37 | 摘要；6.5；附录 | paragraph, code | derived interpretation | p.1、p.27、p.35–37已交叉审查 | 候选规模不能调和 |
| LINGO年份集合只有Y1..Y3却访问第8期 | criticism | 37, 41 | 附录9.1 | code | direct transcription | p.37–41全部LINGO代码已审查 | 结构性索引错误 |
| LINGO优化目标错误加回第二季成本 | criticism | 38, 41 | 附录9.1 | code | derived interpretation | p.38目标与p.41年度Prof逐符号视觉核验 | `-(X*C-Y*CC)`与`-(X*C+Y*CC)`冲突 |
| 亩产范围在公式±5%与代码±10%之间矛盾 | criticism | 21, 35 | 6.2.2；附录 | equation, code | derived interpretation | p.20–24参数公式与p.35生成器已审查 | 代码更接近题面±10% |
| 食用菌价格在公式±5%与代码-5%至-1%之间矛盾 | criticism | 22, 35 | 6.2.4；附录 | equation, code | derived interpretation | p.21–24公式与p.35生成器已审查 | 代码更接近题面 |
| 问题二利润出现6374、7013.104992、6024.45万元三种口径 | criticism | 1, 27, 34 | 摘要；6.5；7.5 | paragraph, table | independent calculation | p.1、p.27、p.34已审查 | 可能对应不同准则，但未建立映射 |
| 在已审查范围内，未发现solver gap、可行性残差或重复随机运行 | criticism | 1–41 | 全文与代码 | none found | derived interpretation | p.1–35正文与p.35–41全部代码已审查 | 输入/结果工作簿不可得 |
| 论文整体不可复现 | criticism | 1–49 | 全文/附录 | none found | derived interpretation | 49页正文、图表、附录代码和仓库现有补充物已审查 | 缺输入/输出且代码有结构性错误 |
