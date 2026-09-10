# 论文主张与证据

Q1当前运行：`q1-20260910T142542Z`。其他问题以实际BACKTEST_REPORT为准，不提前填量化结论。

| 主张 | 数据 | 代码 | 验证/边界 |
|---|---|---|---|
| Q1主费用/购电量 | results/q1/summary.json; milp_dispatch.csv | src/solve_q1.py | tests/test_dispatch.py; export_validation.json |
| 同模型离散最优 | summary.json中的status/gap/dual_bound及LP目标 | src/dispatch.py | LP下界+独立硬约束复算；非现场验证 |
| 较无储能节省26.8981% | summary.json两策略目标 | src/write_q1_report.py | 相同6000首末状态和物理参数 |
| 效率/采样解释敏感性 | summary.json sensitivity | src/solve_q1.py | 各方案独立守恒检查 |
| 官方模板时间歧义 | data/templates/2026C/result1.xlsx | src/export_q1.mjs | template_mapping.csv与原始标签逐格保留 |

## Q2–4统一运行证据

- 13策略334天费用、紧急量、末SOC：results/backtests/full-evaluation-v1/{strategy}/summary.json及intervals.csv.gz；独立结果results/audit/online_review_full.json。
- 预报/修改价值比较：results/evaluation/paired_comparisons.csv；相同信息/重优化对照及A/B边界见BACKTEST_REPORT。不是额外信息最优价值证明。
- 指定日汇总：results/evaluation/designated_days.csv，按源intervals聚合。
- 源码：run目录source_snapshot和provenance记录，与当前实现哈希核对；日期/预报泄漏测试见tests/test_online.py与独立在线审计。
