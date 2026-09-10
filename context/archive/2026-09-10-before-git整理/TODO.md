# TODO

## 2026 C 当前优先任务（2026-09-10）

- [x] 参考神秘卷3完成模型假设章节，将已有执行口径整理为6条短假设并核对代码一致性。
- [ ] 人工审阅6条模型假设；在模型评价中披露网损、自放电、老化、故障及外网购电容量未建模的边界。
- [x] 将现有论文工程原样上传用户指定SJTU项目6aa27f6bbd92933f73a5ac15，保留分章编译结构，备份旧线上项目并核验4页在线PDF。
- [x] 将1.1全部四条参考文献换为中国官方来源，核对原文、日期、页码及引文对应。
- [x] 在Canva完成仿神秘卷3视觉组织的图示版流程图，以小示意图替代文字框，核查思源宋体并交付可编辑设计、实际Canva矢量PDF和本地SVG源。
- [x] 压缩1.1背景和1.3图文，增加并核验两条权威来源，保留旧详细流程图版本。
- [x] 参考神秘卷3制作可编辑的总体流程SVG及draw.io源文件，加入“1.3 我们的工作”，提供LaTeX矢量PDF。
- [x] 按用户提供的LaTeX骨架调整章节、宏包、符号表与附录，清理过时占位文字并保留背景和引用。
- [x] 补写本地正式模板的问题背景，参考新增三篇论文的背景结构并核验两条权威来源。
- [x] 按题面补写“1.2 问题要求”，分列四问要求及共同输出范围。
- [ ] 队员审阅问题背景及问题要求，并在正式论文整合时汇总本轮AI辅助记录。
- [x] 审查并复现外部Q2优化工程，核对输入与本地基线差异，保留原下载文件及版本换解边界。
- [x] 完成小时保护、偏差修正、价格保留、动态选择、场景及执行一致SAA的Q2全期迭代；独立验证并隔离导出新候选。
- [x] 计算同起末状态的全期ORACLE物理下界，仅作不可实施诊断，未用于模型选择。
- [x] 给出唯一明确Q2最终推荐bias_hourly_risk及统一文件入口；原greedy保留为对照，不能将回溯推荐改写成一月事前选优。
- [ ] 若需宣称其他年份也稳定受益，另用未参与开发的数据验证；该泛化问题不作为否定当前附件总费用最低方案的额外条件。
- [x] 汇编面向评委的单份四问Markdown说明，覆盖答案、公式、求解、对照、指定日摘要、证据索引及待确认事项；关键数字与当前运行核对。
- [x] 读取实际总指令v2、根/相关AGENTS、本地技能与索引，保留队友未提交修改。
- [x] 迁移11份C题原件并保存映射/哈希，完整读取3页题面及9个工作簿。
- [x] 数据/单位/预报版本审计、四问拆解、交付矩阵、信息与结算规格。
- [x] Q1 MILP、无储能/规则基线、LP下界、物理检查及两种解释敏感性。
- [x] Q1模板导出/独立核验/基础图和可复现报告。
- [x] Q2季节朴素/回归历史选模，点预测/校准裕量，334天回测与未来扰动测试。
- [x] Q3 A/B账本、预报/修改价值消融，Q4因果价格回测，13策略统一最终版本重跑与独立审计。
- [x] 五Excel完整日历/数值/原结构核验、月度/四展示日结果；仍保留时间标签歧义。
- [x] Q1/Q2静态图、四问LaTeX初稿、AI使用详情PDF、真实结果主张映射。
- [x] 补齐4主策略×4指定日期的表1/2/3，16组共65个真实紧急事件及3个无事件日，编译无宽度溢出。
- [x] 23页初稿逐页视觉QA，首轮171文件支撑ZIP生成与逐文件哈希核验（10.57MB）。
- [ ] 官方模板时间与效率/端口/结算口径澄清，区间内反馈/延迟及逐issue/lead残差/终端敏感性。
- [ ] 初稿整合正式论文、完整源码附录和支撑包；队员最终人工核验及AI版本/人工修改记录补全。
- [ ] 可选扩展：价格已知条件对照、容量/功率/费率敏感性、情景/CVaR；交互HTML按实际需要再做。

## Priority

- [ ] Finish pre-competition collaboration setup.
- [ ] Test Git synchronization with all team members.
- [ ] Test shared Codex context workflow.
- [x] Teammate Codex onboarding and shared-context read test succeeded.
- [x] Archive the 2026 LaTeX template intact and prepare the standalone `paper/overleaf/` manuscript skeleton.
- [x] Compile and visually check the initial manuscript locally; package its source ZIP.
- [x] Create the SJTU Overleaf project and verify XeLaTeX / TeX Live 2025 compilation of `main.tex`.
- [ ] Add teammates and test chapter editing plus source/PDF download synchronization.

## Historical Literature

- [x] Acquire and audit the active 2015–2025 corpus.
- [x] Approve the 32-paper core selection.
- [x] Complete Batch 1 deep distillation for five papers.
- [x] Review the Batch 1 calibration audit and approve schema v1.1 changes.
- [x] Freeze workflow v1.1 and create the repository `cumcm-paper-distillation` Skill.
- [x] Start Batch 2 after explicit human approval.
- [x] Complete the 10 approved Batch 2 paper distillations and retain the batch audit in the local process archive.
- [x] Pass the Batch 2 pre-flight gate and start the explicitly authorized Batch 3.
- [x] Complete the 17 approved Batch 3 paper distillations and retain the batch audit in the local process archive.
- [x] Create a machine-readable completion report for all 32 selected papers.
- [x] Consolidate the final Git-shareable knowledge layer into compact metadata, INDEX, QUICK_REFERENCE, and 32 per-paper reports.
- [x] Keep raw PDFs, OCR, acquisition evidence, and process audits local-only through `.gitignore`.
- [x] Create the repository-scoped `cumcm-problem-solving` Skill with independent retrieval, audit, validation, and output references.
- [x] Pass structural validation, Tests A-E, and the filtered 2020 B historical holdout without modifying real competition context.
- [ ] Human-review the final literature structure, provenance table, retrieval layer, and B050 primary/companion boundary.
- [ ] Human-review the new competition-time Skill and its weak-coverage retrieval rule.
- [ ] Repair retired path references in `cumcm-paper-distillation` before any future historical distillation.
- [ ] Stage, commit, and push only after explicit approval.
- [ ] Build the final `COMPETITION_PLAYBOOK` only after the approved distillation batches.

## Competition Start

- [ ] Import official problem statement.
- [ ] Import provided data.
- [ ] Update PROBLEM.md.
- [ ] Perform initial problem analysis.
- [ ] Decide problem selection.

## Later

No tasks yet.
