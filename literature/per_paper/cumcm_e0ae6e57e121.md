# Paper: “月上柳梢头，人约黄昏后”数学模型的建立

## Metadata

- Distillation schema: 1.1
- Paper ID: cumcm_e0ae6e57e121
- Year: 2015
- Problem: C
- Award: 组委会明确标为优秀论文；具体奖项等级未知
- Provenance tier: E; 官方展示页明确提供优秀论文，不能据此推断具体国奖等级
- Source file: literature/raw_papers/2015/C12001_moe_2015_1700971.pdf
- Source URL: https://dxs.moe.gov.cn/zx/json/2016/0725/1469413877397.pdf
- Verification source: https://dxs.moe.gov.cn/zx/a/hd_sxjm_sxjmlw_2015qgdxssxjmjslwzs/210621/1700971.shtml
- Pages: 25
- SHA-256: 2a439f4b3179ee38ed7370e47ea3a741bb25b4c94ea82a3a0a4a25d0ab0981ad
- Extraction method: embedded text (pypdf 6.10.0) + manual visual review
- Extraction quality: usable text layer；25/25页均超过30个非空白字符，中位数796字符/页；双栏/公式顺序在文本层局部倒置，关键公式、表、图和代码均回到原PDF核验
- Page convention: 1-based physical PDF pages
- Visually checked pages: p.1标题/摘要与城市次数；p.4柳树几何、60cm–70m和15.355°；p.5黄昏定义/城市经纬度；p.7–9太阳/月亮赤纬、时角式(1)–(15)；p.10月中天式(16)–(17)及表3外部验证；p.11表3尾部、历史日期与区间交集条件；p.12北京表4和六城市表5；p.14–15太阳/黄昏/月赤纬代码；p.18月亮时角与验证代码；p.19北京全年/求交代码；p.22城市代码与交集条件；p.23–25其余城市重复代码
- Unresolved extraction ambiguities: p.12表5下半部分跨页且图像字号较小，报告仅采用正文明确给出的城市总次数，不逐格转写全部时间；p.16–18月球黄经/黄纬系数长数组保持为代码证据，不重新排版以免引入转写错误
- Supplemental artifacts: PDF 内含8组（正文称13个）MATLAB程序及天文系数数组；2012《航海天文历》原页、百度资料、运行环境、实际 `.m` 文件和机器输出均为 referenced but unavailable

## 1. Problem Archetype

本文属于天文几何与离散事件检索：先用球面三角形从赤纬、纬度和高度求太阳/月亮地方时角，再构造太阳民用昏影区间和月亮15°–18°高度区间，最后在全年逐日搜索两区间至少重叠5分钟的日期。

方法链为“天文参数近似→时间窗→集合交”。太阳分支用外部天文历做24项比较，具有可审计性；月亮分支则用固定每日中天延迟，并把角度除以24.8127小时，存在量纲错误。区间交条件写成两个不等式的“或”，不能保证真实重叠5分钟，附录又出现 `asin/acos`、括号、`clc`和结果数组覆盖问题，因此最终日期/次数不具可复现保证。

## 2. Problem Decomposition

1. **场景定义**：用1.671m身高、20m柳树和“60cm至70m”距离定义月亮高度15°–18°；以太阳高度0°至-6°定义日没到民用昏影终。
2. **太阳时间窗**：由年内序号计算太阳赤纬，利用球面三角形求0°与-6°的时角，再以太阳中天12:00换成本地时间。
3. **月亮时间窗**：用积日、黄道倾角、黄经和黄纬谐波计算月亮赤纬；同样求15°/18°时角；以2016-01-01中天13.9667h和每日延迟48.7633min推全年中天。
4. **外部校验**：用2012年四个日期、10°/20°/40°N、太阳高度0°/-6°与航海天文历比较。
5. **事件搜索**：对2016年366日生成两个时间窗，按5分钟阈值求交，给北京及六城市日期/时段和次数。
6. **历史回推**：用同模型推算词中场景约为1035-02-20 18:52，并与作者1036年元夕回忆“去年”作叙事匹配。

## 3. Data Processing

- 年月日转换为积日和儒略世纪；月亮黄经/黄纬使用62+1项与45项谐波系数数组。
- 太阳赤纬用年内序号的三阶正余弦近似；2012验证程序循环365天，虽2012为闰年但验证日期不含12月31日。
- 时间先以十进制小时计算，再转成 `HH.MM` 伪十进制表示；区间长度用乘100并在≥60时减40修正。这种编码对跨午夜和超过一小时的差值不稳健。
- 北京及其他城市程序大量硬编码纬度和366元素时间数组；经度没有出现在可见的太阳/月亮时角核心公式中。
- 上海/成都、北京/乌鲁木齐被视为“近似同纬度”用于讨论经度，但表1纬差分别为3.83333°和4.60°，不是受控经度对照。
- 在已审查范围内，未发现对坐标来源、时区/标准时转换、夏令时、地平折射、月球视差或月面相位的数值校正；审查覆盖p.1–13正文和p.14–25全部代码，外部资料原页不可得。

## 4. Models Used

### 太阳赤纬—时角—民用昏影模型

**Purpose:** 求给定日期/纬度的日没和太阳高度-6°时刻。

**Inputs:** 年内序号N、纬度φ、太阳高度h。

**Outputs:** `δ_sun(N)`、地方时角t及0°至-6°时间窗。

**Why selected:** 太阳赤纬有周期近似，球面三角形能直接连接高度、赤纬、纬度和时角。

**Important assumptions:** 太阳每日中天为当地12:00；忽略经度、均时差、折射和海拔。

**Key equations or mathematical structure:** `sin h=sinφ sinδ+cosφ cosδ cos t`，`T=t/15+12`。

**Implementation notes:** 正文公式正确；附录5验证代码把角度换算因子放入 `acos` 参数且缺失分子括号，附录6还把-6°分支写成`asin`。

### 月亮谐波赤纬模型

**Purpose:** 从日期求月亮赤纬。

**Inputs:** 积日P、世纪积日TD/ET、黄道倾角ω、黄经λ、黄纬β。

**Outputs:** `δ_moon=arcsin(cosω sinβ+sinω cosβ sinλ)`。

**Why selected:** 作者直接采用天文资料的谐波展开，避免完整数值星历。

**Important assumptions:** 系数和历书时修正适用于研究日期；截断项误差可忽略。

**Key equations or mathematical structure:** 式(7)–(13)的积日与三组谐波级数。

**Implementation notes:** 代码与正文ET修正系数分别为3.17和3.14；没有用独立月亮赤纬数据校验。

### 固定延迟月亮中天与高度时间窗

**Purpose:** 求月亮经过15°–18°高度的时间。

**Inputs:** 2016-01-01中天13.9667h、每日延迟48.7633min、月亮时角t。

**Outputs:** 每日中天 `Z_t` 和高度窗端点。

**Why selected:** 作者用月日的平均延迟构造简单、可编程的全年模型。

**Important assumptions:** 每日中天延迟恒定；月球24h48.7633min绕行一周；无经度/时区修正。

**Key equations or mathematical structure:** `Z_t=13.9667+k×48.7633/60 (mod 24)`；正文式(17)写 `T=Z_t-t/24.8127`。

**Implementation notes:** t由`acos`得到且单位为度，24.8127单位为小时，二者不能直接相除；正确平均角速度约14.5087°/h，应除以14.5087而非24.8127。

### 时间窗交集判定

**Purpose:** 找出月亮15°–18°窗口和民用昏影窗口至少重叠5分钟的日期。

**Inputs:** `W=[a,b]`、`M=[c,d]`。

**Outputs:** 年内日期索引及交集时段。

**Why selected:** 题目最终事件天然是两个时间集合的交。

**Important assumptions:** 5分钟为“更好观赏效果”的最低重叠。

**Key equations or mathematical structure:** 文中用 `a+5≤d 或 c+5≤b`；代码用近似的HH.MM窗口比较。

**Implementation notes:** 正确条件应为 `max(a,c)+5≤min(b,d)`；“或”条件可让完全分离的区间通过。附录7 `C=[i]`每次覆盖而不累积日期。

### Model Decision Ledger

| Candidate model | Selected / rejected | Purpose | Author-stated reason | Comparison evidence | Missing comparison | Distiller assessment |
|---|---|---|---|---|---|---|
| 专业高精度天文模型 | rejected/mentioned | 星体位置 | 参数复杂、不便理解/编程 | 无同日期结果比较 | 无Meeus/星历软件基准 | 简化动机合理，但必须保留量纲和时区正确性 |
| 周期赤纬+球面三角形 | selected | 太阳/月亮高度时刻 | 思路清晰、可编程 | 太阳24项外部比较 | 月亮赤纬/高度无外部验证 | 太阳分支有证据，月亮分支未验证 |
| 固定48.7633min日延迟 | selected | 月亮中天 | 平均月日规律 | not reported | 无逐日天文历误差、无备选周期模型 | 过度简化且式(17)量纲错误 |
| 15°–18°高度窗 | selected | 定义“柳梢头” | 身高/树高/距离和舒适仰角 | 一次几何计算 | 距离单位矛盾、无阈值敏感性 | 是作者定义，不是客观唯一标准 |
| 民用昏影0°至-6° | selected | 定义“黄昏后” | 标准民用昏影定义 | 航海天文历比较 | 无折射/经度/时区说明 | 可解释标准，但实现与标准时边界不清 |
| 5分钟交集阈值 | selected | 事件判定 | 改善观赏效果 | not reported | 无其他阈值/体验依据 | 阈值透明，判定公式错误 |

## 5. Model Pipeline

`日期N → 太阳赤纬 → 0°/-6°时角 → 黄昏窗`；并行地，`年月日 → P/TD/ET → 月黄经/黄纬/赤纬 → 15°/18°时角 + 固定月中天 → 柳梢窗`；最后 `两窗求交≥5min → 城市年度日期/时间表`。

太阳分支公式、验证表和外部资料形成部分闭环。月亮分支从“24h48.7633min周期”到“角度/24.8127”的接口量纲错误；最终求交又使用错误逻辑和HH.MM算术。附录6/7不能可靠地产生表4/5，导致流水线在最关键的两个接口断裂。

## 6. Model Improvements

1. 将诗意场景拆成可计算的月高度窗和民用昏影窗。
2. 用高阶天文谐波计算月赤纬，比单纯正弦更细致。
3. 通过球面三角形统一太阳和月亮的高度—时角关系。
4. 用外部2012天文历对太阳分支做多日期、多纬度检验。
5. 扩展到七城市并讨论纬度覆盖。

这些改进未覆盖月亮核心：没有月中天/月高度外部检验，日延迟被当常数且量纲转换错误；城市扩展也没有形成经度受控实验。

## 7. Parameter Estimation and Optimization

本文无优化求解，参数来自题面、外部资料或作者设定。月亮谐波系数直接抄入代码；事件阈值未从数据估计。

### Parameter and Assumption Ledger

| Symbol / parameter | Meaning | Unit | Source | Value or range | Source type | Estimation or setting method | Sensitivity tested? | Notes |
|---|---|---|---|---|---|---|---|---|
| observer height | 观测者身高 | m | p.4 | 1.671 | literature-derived | 2015居民报告平均值 | no | 单一平均人 |
| tree height | 柳树高度 | m | p.4 | 20 | literature-derived | 百度文库/树种概括 | no | 城市/树龄差异忽略 |
| observer distance | 人—树距离 | mixed | p.4 | 60cm–70m | author-assumed | not reported | no | 60cm疑似单位错误；公式只用70m |
| moon altitude band | “月上柳梢头”高度 | degrees | p.4 | 15–18 | author-assumed | 几何+舒适角概括 | no | 几何计算本身用tan而非atan |
| twilight sun altitude | 民用昏影界 | degrees | p.5 | 0 to -6 | literature-derived | 标准定义 | no | 折射未讨论 |
| city coordinates | 城市中心经纬度 | degrees | p.5 table 1 | 7 city pairs | literature-derived | source not specified | no | 核心代码主要使用纬度 |
| solar declination constants | 周期近似系数 | degrees | p.7 equation (3) | fixed | literature-derived | referenced formula | no | 24项太阳验证只测时间输出 |
| lunar harmonic constants | λ/β/ω级数系数 | mixed | p.9、p.16–18 | 63/45/2 terms | literature-derived | astronomical formula transcription | no | 无系数版本/误差界 |
| lunar daily transit delay | 月中天每日推迟 | min/day | p.10 | 48.7633 | literature-derived | average lunar day | no | 实际逐日非恒定 |
| transit anchor | 2016-01-01月中天 | decimal hour | p.10 | 13.9667 | literature-derived | lookup | no | 来源原页不可得 |
| overlap threshold | 最短观赏交集 | minutes | p.1、p.11 | 5 | author-assumed | fixed | no | 实现公式错误 |

## 8. Validation

唯一有数值真值的验证是太阳0°/-6°时刻与2012航海天文历比较。它不验证月亮赤纬、中天、15°–18°窗口或最终事件交集。

### Validation Evidence Table

| Validation target | Evidence type | Data independence | Metric | Repetitions | Result | Failure case | Limitation | Justified conclusion boundary |
|---|---|---|---|---:|---|---|---|---|
| 太阳黄昏时刻 | L5 external almanac comparison | external | minute error | 24 cases | max abs16min；min0；独立复算MAE6.375min、RMSE8.101min、bias-4.625min | 2012-03/06高纬误差达16min | 仅4日期×3纬度×2高度，且附录验证代码与公式不一致 | 只支持太阳分支在该网格的分钟级量级 |
| 1035词境日期 | L2 historical narrative consistency | external/unknown | calendar/story match | 1 anecdote | 推算1035-02-20 18:52，与1036元夕回忆去年叙事称吻合 | 无独立天文时刻 | 历法转换、地点和月相证据未给 | 只能作叙事性一致性 |
| 北京2016事件 | not assessable | unknown | 日期/时间正确率 | 10 reported | 表4十个非空时间窗 | 附录交集逻辑/代码错误 | 无天文软件或实测逐日对照 | 不能确认10次正确 |
| 六城市事件 | not assessable | unknown | 城市次数 | 6 cities | 5/7/8/7或9/9/11 | 摘要/正文上海次数矛盾 | 无独立城市星历 | 不能支持纬度/经度规律 |

## 9. Sensitivity and Robustness

### Sensitivity / Robustness Table

| Parameter or perturbation | Baseline | Variation range | Sampling method | Output metric | Result | Conclusion changed? | Interpretation |
|---|---|---|---|---|---|---|---|
| 纬度/城市 | 7城市表1坐标 | 21.16667°–45.75°N | seven-city scenarios | 年事件次数 | 5,7,8,7/9,10,9,11（含北京；上海口径矛盾） | yes，非单调 | 不支持“纬度越高次数越多”的严格结论 |
| 日期/纬度太阳验证 | 4日期 | 10°/20°/40°N | 24 external grid cases | 分钟误差 | abs 0–16min | no，仍为分钟量级 | 只检验太阳分支 |

在已审查范围内，未发现对15°–18°高度、60cm/60m–70m距离、5分钟交集、48.7633分钟延迟、天文系数截断或时区/折射的实际扰动；审查覆盖p.1–13正文和p.14–25全部代码，外部资料原页不可得。

## 10. Visualization Strategy

- 图2/3把天体高度和柳树几何直观化，适合将文学描述转为角度；图3公式与几何函数不一致。
- 图4球面三角形支撑太阳/月亮共享公式，是模型核心图。
- 表2展示0°至-6°每一度对应时间，便于检查昏影时序。
- 表3把24个计算/资料时刻和误差逐列给出，是全文最强验证对象；应补MAE/RMSE和误差方向。
- 表4/5把事件日期和交集窗口直接交付；空白单元/摘要计数矛盾降低可读性。
- 附录打印长达数页的系数和366元素数组，但缺模块化函数/输入输出说明，审计成本高。

## 11. Writing Structure

报告从场景定义开始，依次建立太阳分支、月亮分支、检验、北京求解、城市扩展和评价，叙事顺序清楚。对关键概念、符号和假设均有专节。

主要问题是“简化”越过正确性边界：tan/atan混用、角度除小时、错误区间交、HH.MM算术和代码语法/函数错误；太阳验证被用来概括整个模型“精度较高”，但月亮和事件没有真值。摘要上海7次、正文9次也未统一。

## 12. Strengths

1. 把文学场景拆成两个可解释时间窗，问题形式化清楚。
2. 正确引入球面三角形核心关系，并对太阳分支做外部天文历比较。
3. 参数、城市坐标、日期结果和大部分代码公开，便于核查。
4. 24项验证表允许独立计算MAE、RMSE和偏差。
5. 七城市扩展揭示空间变量的重要性，即使作者的单调结论并不成立。

## 13. Weaknesses

1. 柳树几何用`tan`代替`atan`，且距离60cm–70m单位不合理。
2. 月亮时角（度）直接除以月日长度（小时），量纲错误，核心月亮时间窗失真。
3. 至少5分钟交集的逻辑条件错误，可能把不相交时间窗判为事件。
4. 附录6有`lc`、`asin`、括号等错误，附录7覆盖结果索引；代码无法可靠生成表4/5。
5. 只有太阳分支外部验证，最终事件次数、历史日期和城市规律均未独立验证。

### Reproduction Audit

| Audit item | Finding | Evidence / review scope | Reproducibility blocker or limitation |
|---|---|---|---|
| Data availability | partial | 天文系数数组和结果表嵌入PDF | 外部天文历原页、坐标来源和运行输出不可得 |
| Code availability | partial | p.14–25有8组大段MATLAB代码 | 正文称13程序；非模块化、长数组硬编码、驱动接口缺失 |
| Dependency / environment information | unavailable | 仅称MATLAB | 版本/工具箱未报告 |
| Random seed | N/A | 确定性计算 | 无随机过程 |
| Hard-coded constants | extensive | 经纬度、366数组、月中天锚、谐波系数、HH.MM阈值 | 难以维护和跨年/跨城复用 |
| Formula-to-code consistency | contradicted | 对照式(5),(9),(15),(17)与p.15、18–19代码 | ET 3.14/3.17、acos括号、asin/acos和量纲不一致 |
| Code-to-result consistency | contradicted | 对照附录6/7与表4/5 | 附录6不可可靠运行；`C=[i]`不能保存10个索引；上海7/9矛盾 |
| Overall reproducibility | not reproducible | 25页、全部公式/表图/代码和现有补充物已审查 | 核心月亮/交集公式与代码错误，外部输入/输出缺失 |

### Numerical Sanity Checks

| Check | Source claim | Independent check | Result | Source page / object | Notes |
|---|---|---|---|---|---|
| 柳树视角函数 | `tan((20-1.671)/70)×180/π=15.355°` | 正确几何应`atan(18.329/70)=14.673°` | fail | p.4 equation | 论文数值是tan而非反正切 |
| 距离范围 | 60cm–70m对应15°–18° | 60cm时角约87.°，若意为60m则约16.987° | fail | p.4 paragraph | 单位明显影响结论 |
| 太阳时角换算 | t=69.4829°对应16:37 | `12+69.4829/15=16.6322h≈16:37.9` | pass | p.8 table 2 | 舍去/四舍五入分钟略有差别 |
| 外部验证汇总 | 最大16min、最小0 | 24项MAE6.375、RMSE8.101、bias-4.625min | pass | p.10–11 table 3 | 仅太阳分支 |
| 月球平均角速度 | 24h48.7633min绕360° | 周期24.81272h，对应14.50869°/h | fail | p.10 equations (16)–(17) | 式(17)除24.8127，时间偏移仅正确值的58.47% |
| 5分钟交集 | `a+5≤d 或 c+5≤b` | 正确为`max(a,c)+5≤min(b,d)` | fail | p.11 equation/paragraph | 原条件可接受完全分离区间 |
| 北京次数 | 表4合计10 | 12个日期中10个有非空时间窗 | pass | p.12 table 4 | 不验证时窗正确性 |
| 上海次数 | 摘要7次 | p.12正文写9次 | fail | p.1 abstract vs p.12 section 6.2 | 批次结果口径冲突 |
| 纬度单调性 | 纬度越高次数越多 | 成都30.6667°为8次而上海34.5°为7/9；北京39.1667°10次而乌鲁木齐43.7667°9次 | fail | p.1, p.5 table1, p.12 paragraph | 自身城市结果非严格单调 |
| “同纬度”对照 | 上海/成都、北京/乌鲁木齐几乎同纬度 | 表1纬差3.83333°和4.60° | concern | p.5 table1; p.13 paragraph | 不能隔离经度效应 |
| ET修正系数 | 式(9)为3.14 | p.15代码使用3.17 | fail | p.9 equation (9); p.15 code | 公式—代码不一致 |
| 验证代码时角 | 应使用`acos((sin h-sinφsinδ)/(cosφcosδ))` | p.18把换算因子/括号位置写错 | fail | p.18 code | 表3来源无法由所列代码认证 |
| 北京全年昏影代码 | 0°/-6°均应acos | p.19 `t2=asin(...)`且开头`lc` | fail | p.19 code | 函数与语法错误 |
| 交集索引保存 | 应保存全部合格日 | p.22循环内`C=[i]`每次覆盖 | fail | p.22 code | 不能形成10项索引数组 |
| 2012全年循环 | 2012为闰年 | 附录1只循环1:365 | fail | p.14 code | 少一天；验证四日期未触及12月31日 |

## 14. Reusable Techniques

### 天体高度的球面三角形接口

**When useful:** 已知日期/赤纬/纬度，需要日出、昏影或高度阈值时刻时。

**Why useful:** 同一关系可服务太阳和月亮，并清楚暴露高度、纬度、赤纬。

**Limitations:** 要处理时角象限、无解区间、折射、视差、经度和标准时转换。

### 双时间窗事件检索

**When useful:** 场景由两个连续条件同时满足构成。

**Why useful:** 先各自求区间，再用`max(start)`和`min(end)`求交，逻辑透明。

**Limitations:** 不要用两个OR不等式代替交集长度；跨午夜需统一绝对分钟。

### 外部星历组件验证

**When useful:** 复杂天文管线包含多个可单独校验模块。

**Why useful:** 对赤纬、日没、月中天、月高度和最终交集分别验证，可定位误差来源。

**Limitations:** 太阳组件通过不能代表月亮/事件通过；每层都需独立真值。

### 全部时间转为连续分钟

**When useful:** 多城市、多时区、跨午夜的时间窗比较。

**Why useful:** 以某一日期起点的整数分钟计算交集，避免HH.MM和减40修正。

**Limitations:** 必须明确UTC、标准时、经度和日期滚动。

## 15. Competition Takeaways

1. 文学描述转参数时先做单位审计；60cm/60m和tan/atan会改变整个事件定义。
2. 每个式子写单位，角度除以角速度而不是除以周期。
3. 区间交统一使用`max(start)+threshold≤min(end)`，并写边界单元测试。
4. 天文时刻明确是当地太阳时、UTC还是法定标准时，经度/时区不能隐去。
5. 太阳、月亮、交集三层分别对外部星历验证，报告MAE、RMSE和偏差。
6. 城市规律要做受控比较或回归，不能从非单调七点直接声称纬度单调、经度无关。
7. 用绝对分钟/日期时间对象，不用17.35式HH.MM小数做加减。
8. 代码生成结果表并保留全部索引；提交前运行语法检查和公式—代码对照。

## 16. Traceability

| Claim | Claim type | Source page | Source section | Source object | Transformation | Review scope | Notes |
|---|---|---:|---|---|---|---|---|
| 作者定义月亮高度15°–18° | explicit | 4 | 3.2.1 | equation, paragraph | direct transcription | N/A for positive evidence | 来自身高/树高/距离和舒适角 |
| 几何应使用atan，70m结果14.673° | criticism | 4 | 3.2.1 | equation | independent calculation | p.4图3、文字与公式已视觉审查 | 原式用tan得到15.355° |
| 60cm距离与15°–18°不相容 | criticism | 4 | 3.2.1 | paragraph | independent calculation | p.4完整定义已审查 | 若意为60m则约16.987° |
| 黄昏定义为太阳高度0°至-6° | explicit | 5 | 3.2.2 | paragraph | direct transcription | N/A for positive evidence | 民用昏影 |
| 太阳/月亮共享球面三角形高度公式 | explicit | 8–9 | 5.1.2, 5.2.2 | equations (4),(14) | notation normalization | N/A for positive evidence | 正文公式结构正确 |
| 太阳验证24项误差abs 0–16min | explicit | 10–11 | 5.3 | table 3 | direct transcription | N/A for positive evidence | 外部航海天文历比较 |
| 24项MAE6.375、RMSE8.101、bias-4.625min | interpretation | 10–11 | 5.3 | table 3 | independent calculation | N/A for positive evidence | 太阳分支汇总 |
| 月亮中天每日延迟48.7633min | explicit | 10 | 5.2.3 | equation (16), paragraph | direct transcription | N/A for positive evidence | 固定平均假设 |
| 式(17)把度除以小时，量纲错误 | criticism | 10, 18 | 5.2.4；附录4 | equation, code | independent calculation | p.9–10时角单位、式(16)–(17)和p.18代码已审查 | 正确角速度约14.50869°/h |
| 至少5分钟交集条件使用OR | explicit | 11 | 6.1 | paragraph | direct transcription | N/A for positive evidence | `a+5≤d or c+5≤b` |
| OR条件不能保证区间重叠 | criticism | 11 | 6.1 | equation | derived interpretation | p.11区间定义和条件已审查 | 正确为max/min条件 |
| 北京表4有10个非空时段 | interpretation | 12 | 6.1 | table 4 | independent calculation | N/A for positive evidence | 表内计数通过 |
| 上海次数摘要7、正文9 | criticism | 1, 12 | 摘要；6.2 | paragraphs | direct transcription | p.1摘要、p.12正文/表5已审查 | 无法调和 |
| 纬度—次数结果并非严格单调 | criticism | 1, 5, 12 | 摘要；表1；6.2 | table, paragraphs | independent calculation | 七城市纬度与作者报告次数已交叉审查 | 至少成都/上海、北京/乌鲁木齐反例 |
| 经度效应没有受控比较 | criticism | 5, 13 | 3.2.3；7 | none found | derived interpretation | 表1和p.13空间结论、p.22–25城市代码已审查 | 所谓同纬度城市仍差3.83°/4.60° |
| ET修正正文3.14、代码3.17 | criticism | 9, 15 | 式(9)；附录3 | equation, code | direct transcription | p.9公式与p.15代码视觉核验 | 公式—代码不一致 |
| 附录6把-6°时角写成asin且有语法问题 | criticism | 19 | 附录6 | code | direct transcription | p.19完整相关代码已审查 | 不能认证表4 |
| 附录7 `C=[i]`覆盖而非累积索引 | criticism | 22 | 附录7 | code | derived interpretation | p.19–22完整求交代码已审查 | 最终只保留最后命中值 |
| 在已审查范围内，未发现月亮/最终事件的独立星历验证 | criticism | 1–25 | 全文/附录 | none found | derived interpretation | p.1–13正文、p.14–25全部代码已审查 | 外部资料原页不可得 |
| 论文整体不可复现 | criticism | 1–25 | 全文/附录 | none found | derived interpretation | 25页、全部公式/表图/代码和现有补充物已审查 | 核心量纲/交集/代码错误及外部输入缺失 |
