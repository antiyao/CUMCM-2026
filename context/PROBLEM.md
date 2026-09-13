# Problem

## Competition

CUMCM 2026

## Problem Selection

C题《微网与外部电网电力调控策略》。

## Official Problem Statement

`docs/problem/2026C/C题.pdf`全部3页已提取并逐页视觉检查，全文在`docs/problem/2026C/problem.txt`。

## Questions

- Q1：已给负载、电价、光伏预测下的0点购电计划，无缺电，0/24点储电量相同。
- Q2：只用截至0点历史预测当天，普通计划收费、缺口紧急购电5倍价格。
- Q3：加入0/6/12/18发布的光伏预报和策略增减费用，回答额外预报/调整的价值。
- Q4：波动电价下重做Q2/Q3。Q2–4结果覆盖2025-02-01至12-31共334天，展示3/20、6/21、9/23、12/21。

## Provided Data

- 附件1–4：`data/raw/2026C/`，五份空模板：`templates/`。
- 附录1：额定12000kWh，运行1200–10800kWh，最大充放电5000kW，2025-01-01 00:00初始6000kWh，题称充放电效率90%。

## Notes

题面明示与解释假设分开，详见 ASSUMPTIONS.md、SETTLEMENT_SPEC.md。模板时间标签与当天144区间存在冲突，见 TEMPLATE_MAPPING.md。
