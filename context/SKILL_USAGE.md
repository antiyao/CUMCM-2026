# 实际技能阅读与迁移（2026-09-10）

- .agents/skills/cumcm-problem-solving/SKILL.md：全文；retrieval-policy、validation-policy、output-contract全文；archetype-audits的接口、预测、确定性/随机优化、仿真及数值检查节。用于当前赛题。
- .agents/skills/cumcm-paper-distillation/SKILL.md：全文已读，确认是历史蒸馏维护流程。本轮不调用OCR/采集/批次蒸馏/全局playbook，不修历史路径，不改32篇知识库。
- 实际索引：literature/README.md、synthesis/QUICK_REFERENCE.md、synthesis/INDEX.md；core_papers.csv与completion.csv所选三篇记录。
- PDF skill用于题面3页文本和逐页图像复核；Spreadsheets skill用于原件结构审计、模板填值及视觉检查。
- 外部scientific-visualization、matplotlib仅接入这两项，来源/commit/许可证/脚本审查见EXTERNAL_SKILL_AUDIT.md。官方机制与AI规定另保存源证据。

| 报告 | 实际阅读范围 | 本题采用 | 不照搬 |
|---|---|---|---|
| C126，literature/per_paper/cumcm_3c2a8301acac.md | 5–6接口/改进、8验证、13–16弱点/复用/经验/相关追溯 | 时点/单位/版本接口；预测误差进入购电；公式—代码—结果闭合 | VAR(2)、均值抹零、同样本一致当独立验证；光伏夜零是物理现象 |
| C038，literature/per_paper/cumcm_919f31cf2944.md | 8验证、13–16弱点/复现/复用/经验/追溯 | 先MILP基线，硬约束残差；风险按方案总损失、正确尾部、相关残差 | DE-GA、软罚替代约束、未归一CVaR、优化输出反推现实相关 |
| 2020B穿越沙漠，literature/per_paper/cumcm_f54b502c16d7.md | 13弱点、14–16复用/经验/追溯 | 区分全知oracle与在线控制，跨日状态、终端价值、失败指标 | oracle当线上成绩、局部决策无条件拼为全局最优 |

前两篇元数据为官方展示但奖级未知，第三篇本地未核验奖项；不宣称一等奖。本库rolling-origin与端到端独立现实验证覆盖弱，本题按题目时序直接设计因果回测和泄漏测试。

Q1证书/物理复算是离散模型最优性/内部一致性，效率和采样解释实验是敏感性；不冒称现场验证。
