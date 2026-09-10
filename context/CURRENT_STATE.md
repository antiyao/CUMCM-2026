# 当前状态

更新日期：2026-09-10。当前执行 C 题《微网与外部电网电力调控策略》；题面和附件齐全，已完成基础建模、真实数据回测及 Q2 迭代，正在逐节编写正式论文。

## 当前结果与使用入口

Q2–Q4 评价范围为 2025-02-01 至 2025-12-31，共 334 天、每策略 48096 个 10 分钟区间。以下费用均采用当前暂定物理与结算解释，不能与不同解释下的结果混排。

| 问题 | 当前方案 | 购电费用 / 元 | 结果入口与边界 |
|---|---|---:|---|
| Q1 | MILP 日前调度 | 35,126.948589 | results/final_recommendation/result1.xlsx；日初日末均 6000 kWh，HiGHS optimal、gap=0，LP 下界一致，仅在当前离散解释下认证最优。 |
| Q2 | 最终推荐 bias_hourly_risk | 13,868,005.116996 | results/final_recommendation/result2.xlsx；当前数据研究比较后的推荐，非一月事前选中家族、独立盲测获胜或全局最优。 |
| Q3 | q3_adjust_A | 14,395,641.957396 | results/final_recommendation/result3.xlsx；主 A 结算，是既有合同调整方案，并非已测 Q3 方案中费用最低。 |
| Q4-2 | q4_2_margin | 14,829,820.206964 | results/final_recommendation/result4-2.xlsx；未来价未知，历史预测价规划、实际价结算。 |
| Q4-3 | q4_3_adjust_A | 15,213,707.644630 | results/final_recommendation/result4-3.xlsx；未来价未知及主 A 结算，尚未完成全部 Q4 消融。 |

- Q2 推荐采用历史预测、最近 3 日偏差修正、过去 14 日同小时 0.8 分位保护和贪心储能执行；普通计划费 13,500,745.611521 元，紧急费 367,259.505475 元，紧急电量 60,360.941416 kWh。来源与哈希在 results/final_recommendation/Q2_SELECTION.json，解释见 paper/analysis/第二问最终答案.md。
- Q2 比原有 greedy 少 7,692.100026 元（0.055436%），紧急电量减少 24.3523%，但未利用电量增加；142 天更省、192 天更贵，周块描述区间跨 0，不宣称跨年稳定提升。一月跨家族评分胜者仍是 price_reserve；0.8 参数的一月校准不等于事前选中了最终家族。
- **当前五本工作簿统一使用 results/final_recommendation/。**首轮 Q2（14,056,248.251414 元）及 greedy 的数学有效日汇总和审计证据仅用于历史比较，不作当前交付入口。Q1/Q3/Q4 未因 Q2 迭代改模或重选。
- Q3 当前直接使用新预报、只更新电池的方式更贵；允许 A 口径合同调整挽回部分费用，但仍贵于仅零点预报。该结果揭示当前策略的不足，不能推断额外信息本身具有负价值。A/B 退款解释不可混算。
- Q2 完美信息 ORACLE 下界 12,230,448.060614 元仅在候选结束后作诊断，采用相同起末状态，不能作为可实施策略或回填调参。执行一致 SAA 等未胜出的实验保留；达到迭代上限的结果仅称 best-found。

## 已有证据与交付状态

- 11 份原件路径和 SHA-256 见 context/FILE_RELOCATION_MANIFEST.csv；原始数据未改。数据审计 15/15 项通过，包含 365 日实际数据和 1460 次预报。
- 首轮统一运行在 results/backtests/full-evaluation-v1/，13 个策略的母线平衡、SOC、合同事件和真实价格费用均经独立重算；Q2 新迭代及验证在 results/q2_iteration/。现有核验记录含 Q1 导出 23 项、年度工作簿各 36 项检查，以及 Q2 新候选 7 幅视觉 QA。本快照不将历史核验记录冒充本轮重新运行。
- Q1 效率和功率语义敏感性与主结果分开；Q1/Q2 图形、16 组指定日表、四问说明及主张证据映射均已保存。入口为 paper/analysis/C题四问答案与建模审理说明.md、paper/analysis/第二问迭代评估.md、paper/CLAIM_EVIDENCE_MAP.md。
- 首轮 23 页自动生成建模初稿及 171 文件支撑包位于 paper/releases/2026C-first-round/，是研究材料，尚未整合为正式提交稿。首轮报告中的 Q2 数值需按上方最终推荐理解其版本。

## 正式论文与协作

- 活跃论文为 paper/overleaf/，主文件 main.tex，保持 sections/、figures/、tables/ 分章结构。**目前已完成问题背景、四问问题要求、图示流程图和 6 条模型假设；摘要、符号、四问模型与结果、评价及附录仍待写，不是完整论文。**
- 1.1 保持短篇背景，四条引用全部为中国官方文件/报告。写作参考为根目录 05-CUMCM2025C-神秘卷3.pdf；参考组织方式，模型和数值以本题证据为准。
- Canva 已实际保存图示版设计 [DAHU0aqVVig](https://www.canva.com/design/DAHU0aqVVig/mjgvOiLyeP096QiViStfFg/edit)，8 个主题 SVG 配短标签，中文为思源宋体常规体。实际 Canva 第 4 版 PDF 字体已嵌入、无位图，并接入 1.3；本地可编辑 SVG 源仍为 STSong，不能冒称 Canva 原生 SVG 导出。文件、生成器和核验见 figures/overview/canva/README.md、交付核验.json。
- 当前 [SJTU 项目](https://latex.sjtu.edu.cn/project/6aa27f6bbd92933f73a5ac15) 已同步 23 个工程文件，后续模型假设也已单章同步。最近一次记录核验为 main.tex、XeLaTeX / TeX Live 2025 本地及在线编译 4 页成功；源工程上传记录和哈希在 paper/releases/2026-09-10-overleaf-sync/。旧线上工程备份为 6aa2f413bd92933f73a7e404；当前本地 PDF 看 paper/overleaf/build/main.pdf 编译输出。

## 仍需确认的解释与研究边界

context/ASSUMPTIONS.md A001–A006 均为 **Under Review**；用户授权按披露假设推进，不代表官方消歧或队员最终核验：

- 10 分钟平均功率/交付价语义；充、放单程效率均 0.9、交流侧 5000 kW 限额与内部 SOC 计量。
- Q2–Q4 一月储能停用、二月起状态连续；区间平均功率代表值下的理想化区间内反馈，未验证采样、通信和执行延迟，不能称为严格区间起点真实观测控制。
- Q3 主 A 为原费不退、减购另付 0.5p、增购付 1.5p；相对最近合同累计、只修改未交付区间。Q4 未来价未知和预报即时可见也属于暂定信息解释。
- 所有官方输出模板存在 10 分钟标签错位，当前按 ordinal 映射并保留表头。工作簿数值已核验，但仍为 submission_ready=false，不能标为最终无歧义可提交。
- 年度策略及其算法是已实现并验证的可行方案，未证明随机在线全局最优；逐 issue/lead 预报校准、严格观测延迟、终端与更多参数敏感性仍待补。算法和解释的最终选用仍需队员审阅。

## 本次整理与历史资料

- 本轮按用户授权整理为Git快照；源码、输入、当前五本结果、轻量研究汇总和论文一并纳入。实际发布状态以Git分支及GitHub提交记录为准。无效/过期交付副本删除清单见results/final_recommendation/REMOVED_DELIVERABLES.json。
- 整理前的完整 CURRENT_STATE.md 和 TODO.md 原样保存在 context/archive/2026-09-10-before-git整理/，包含赛前准备、各轮写作和运行历史。
- 历史知识层已完成 32/32 篇核心论文蒸馏，入口为 literature/synthesis/INDEX.md、literature/synthesis/QUICK_REFERENCE.md 及 literature/metadata/completion.csv；两个独立建模/蒸馏 Skill 和已审查绘图 Skill 保留。原 PDF/OCR/过程档案继续遵守既有本地归档范围；本次不重做历史审计，B050 版本边界及旧 Skill 路径维护见上述归档。
