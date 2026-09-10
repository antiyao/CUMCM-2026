# Decision Log

## D001 — Historical-paper distillation workflow v1.1

**Decision:**\
Keep the existing 16-section per-paper structure. For future papers, add structured model-decision, parameter/assumption, validation, sensitivity/robustness, reproduction, numerical-sanity, and extended traceability blocks. Encode the workflow in the repository Skill `.agents/skills/cumcm-paper-distillation/`. Keep the five Batch 1 reports unchanged as the calibration set.

**Reason:**\
Batch 1 demonstrated sufficient mathematical depth and traceability, while revealing repeatable needs for explicit source/code checks, numerical reconciliation, evidence classification, and resumable metadata updates.

**Alternatives Considered:**\
Rewrite the five Batch 1 reports into a new structure; replace the 16-section schema; keep the workflow only as prose without a reusable Skill.

**Status:** Accepted

## D002 — Final historical-literature repository layer

**Decision:**\
Keep the Git-shareable `literature/` layer limited to a concise README, 32 validated per-paper reports, compact core/provenance/completion metadata, the detailed model matrix, and lightweight INDEX/QUICK_REFERENCE retrieval files. Keep raw PDFs, OCR, acquisition evidence, old batch audits, and corpus-maintenance scripts locally available but Git-ignored.

**Reason:**\
This preserves distilled knowledge and claim-level provenance while reducing the intended Git payload from hundreds of megabytes to a primarily text-based retrieval layer. The local archive retains original evidence for future re-audit without making it a normal repository dependency.

**Alternatives Considered:**\
Commit the full raw/extracted corpus; delete local source material; keep all acquisition and progress tables in the shared metadata directory; remove the detailed model matrix after creating the compact core table.

**Status:** Accepted

## D003 — Competition-time problem-solving Skill

**Decision:**\
Use a separate repository Skill for active CUMCM problem solving. It prioritizes the current official problem and data, then team context, then the cleaned historical retrieval layer. It retrieves about three to six reports when historical coverage is material, but uses at most two targeted auxiliary reports for known corpus gaps or narrow diagnostics. It compares end-to-end candidate pipelines, requires baselines and validation planning, and writes shared modeling state only after a direction is accepted or explicitly requested.

**Reason:**\
Historical papers improve method selection and auditing but are not templates. Independent forward tests showed that a softer weak-match rule still caused excessive retrieval in a causal-inference problem, so the hard two-report cap preserves first-principles reasoning where the corpus is weak.

**Alternatives Considered:**\
Merge competition solving into the paper-distillation Skill; scan all 32 reports for every problem; rank candidate models with a fixed weighted score; use historical award status as a model-selection signal.

**Status:** Accepted

## D004 — Paper workspace and Overleaf collaboration

**Decision:**\
Preserve the imported 2026 LaTeX template in `paper/template-original/`, keep the standalone active manuscript in `paper/overleaf/`, and save dated source/PDF snapshots in `paper/releases/`. Use SJTU Overleaf for collaborative manuscript editing and compilation. Keep code and generated results in the repository; coordinate manuscript and figure transfers through one integrator.

**Reason:**\
Yao approved organizing the template and creating the online paper project. A standalone paper directory can be uploaded and compiled without the entire modeling repository, while preserving the original template for reference.

**Alternatives Considered:**\
Keep the template at repository root; upload the full modeling repository; allow uncoordinated simultaneous local and online manuscript edits.

**Status:** Accepted

## D005 — C题真实建模工程与原件归档

**Decision:** 用户2026-09-10明确授权按根总指令v2执行审计、原件仅路径迁移、Q1真实求解并在数据充分时继续；当前代码/结果以本地仓库为准。采用HiGHS MILP、独立物理检查、同约束LP下界和可行基线，禁止把全知数据注入在线规划。

**Reason:** 题面/附件齐全，模型线性；MILP有可核验界，避免无必要启发式。已实读历史知识库，采用接口与证据审计，不再蒸馏。

**Status:** Accepted for implementation by explicit user request；解释性假设仍Under Review。

## D006 — 本轮论文与协作边界

**Decision:** 本轮按最新用户总指令使用本地LaTeX，不以Overleaf为前提；保留D004既有paper/overleaf与队友文件，不进行远端同步或覆盖。所有数值文本从真实结果生成，保留实际AI辅助记录，队员人工审核状态不得虚构。

**Status:** Accepted for this run by explicit user request。

## D007 — 年度主策略与样本比较边界

**Decision:** 导出固定采用预设q2_margin、q3_adjust_A、q4_2_margin、q4_3_adjust_A。B退款解释和greedy控制只作为对照，不按全年结果倒选并重命名主策略。Q3额外加入冻结零点预报的同机会重规划对照，分离终端/重优化与预报更新；观察到新预报当前利用方式不一定省费，如实保留。

**Reason:** 按题目主暂定口径形成可复现结果，同时保护在线评估不被全年事后选模污染。A/B与实时聚合观测依旧是Under Review解释。

**Status:** Implementation choice under the user-authorized master-prompt baseline; not a claim of globally optimal online strategy。

## D008 — Q2迭代与外部结果的比较口径

**Decision:** 用户明确授权审查外部工程并实际迭代。v1结果、原下载目录和Q1/Q3/Q4模型保留；新Q2候选在隔离目录导出。比较控制相同输入/初始状态/物理与账务口径，分别标记一月校准胜者和全年回溯最低；不将外部报告相对其自身A的9.06%改写为本地增益。

**Result:** bias_hourly_risk是已试候选中最低费用，但比已有greedy仅省0.055436%，周块描述区间跨0；紧急量减少24.3523%，未利用量增加。价格保留、动态选择、场景与执行一致SAA失败结果均保留。新策略不宣称全局最优或盲测获胜。

**Status:** Accepted for scoped experimentation by user request；部署选择/正式提交及题意歧义未因此获确认。ORACLE仅在候选完成后诊断，禁止回填线上策略。

## D009 — 第二问最终推荐的明确收敛

**Decision:** 针对用户“需要一个最终答案、是否费用越低越好”的要求，推荐bias_hourly_risk，费用13,868,005.116996元，统一复制到results/final_recommendation/result2.xlsx。当前附件、相同模型约束下，以已验证总费用最低为选择依据；原主方案与原greedy保留为对照。

**Boundary:** 明确排除使用未来真值的ORACLE和不同假设/结算下的费用。推荐是研究后的当前数据选择，不声称一月跨家族事前选中、外部盲测获胜或全局最优。正式提交语义仍受模板标签问题约束。

**Status:** Assistant final recommendation requested by user；没有执行部署或提交，旧数据及结果不覆盖。

## D010 — 当前论文线上项目与原样同步

**Decision:** 用户明确指定`https://latex.sjtu.edu.cn/project/6aa27f6bbd92933f73a5ac15`为本次上传目标，授权将当前本地`paper/overleaf/`工程原样同步。此授权更新D006针对先前轮次“不进行远端同步”的范围限制；不扁平化章节、不改写正文或样式。

**Result:** 23个工程文件已上传，sections/figures/tables结构保持；main.tex、XeLaTeX、TeX Live 2025在线生成4页。旧线上项目已复制备份到`6aa2f413bd92933f73a7e404`，本地源文件上传前后哈希不变；保留线上原有无关文件，未执行Git提交或推送。

**Status:** Accepted by explicit user request。

When recording a decision, use:

## D001 — Short title

**Decision:**\
What was decided.

**Reason:**\
Why this option was selected.

**Alternatives Considered:**\
Other approaches considered.

**Status:** Accepted / Rejected / Under Review
