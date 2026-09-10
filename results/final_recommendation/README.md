# 当前结果统一入口

本目录的五本工作簿是当前审阅入口，均为已核验来源的原字节副本。当前状态为可审阅结果，尚未确认可正式提交。

| 问题 | 当前方案 | 总购电费用/元 | 工作簿 |
|---|---|---:|---|
| Q1 | `milp` | 35,126.95 | [result1.xlsx](result1.xlsx) |
| Q2 | `bias_hourly_risk` | 13,868,005.12 | [result2.xlsx](result2.xlsx) |
| Q3 | `q3_adjust_A` | 14,395,641.96 | [result3.xlsx](result3.xlsx) |
| Q4-2 | `q4_2_margin` | 14,829,820.21 | [result4-2.xlsx](result4-2.xlsx) |
| Q4-3 | `q4_3_adjust_A` | 15,213,707.64 | [result4-3.xlsx](result4-3.xlsx) |

Q1为附件1的单日；其余四项均覆盖2025-02-01至2025-12-31，共334天、48096个10分钟区间。

## 版本与结论边界

- Q2使用最新`bias_hourly_risk`；旧`q2_margin`交付表已删除，14,056,248.25元的有效基线仍见`results/backtests/full-evaluation-v1/q2_margin/`。
- Q3/Q4仍为v1已验证方案，不代表全期最优。不能将新Q2与v1 Q3的费用差当作新增预报的价值；应使用v1内部同机会对照。
- Q2是当前已试可行策略的回溯推荐，不是1月事前跨家族盲测赢家；全知ORACLE不属于可实施策略。
- 五本均保持`submission_ready=false`。模板标签晚10分钟及现有暂定解释仍需审阅；整理文件不代表消歧完成。

## 核验与来源

`CURRENT_RESULTS.json`保存精确费用、范围、原始结果路径与哈希；`Q2_SELECTION.json`保留第二问选择依据。
在仓库根目录运行`.venv/bin/python src/catalog_results.py --check`，核验五本镜像、年度日汇总、已有验证状态与目录索引。
需创建缺少的镜像或重建索引时运行不带`--check`的命令；已有工作簿若与来源不一致会报错，不会覆盖。
完整物理与逐区间费用检查记录见各来源run的`independent_audit.json`、`summary.json`和导出验证文件。
