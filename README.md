# CUMCM 2026 · 微网与外部电网电力调控策略

当前工作分为已核验的计算结果与正在编写的正式论文。结果统一从 [`results/final_recommendation/`](results/final_recommendation/) 读取；精确数值、来源与哈希见 [`CURRENT_RESULTS.json`](results/final_recommendation/CURRENT_RESULTS.json)。

## 当前结果

| 问题 | 当前方案 | 总购电费用/元 | 文件 |
|---|---|---:|---|
| Q1 | `milp` | 35,126.95 | [result1.xlsx](results/final_recommendation/result1.xlsx) |
| Q2 | `bias_hourly_risk` | 13,868,005.12 | [result2.xlsx](results/final_recommendation/result2.xlsx) |
| Q3 | `q3_adjust_A` | 14,395,641.96 | [result3.xlsx](results/final_recommendation/result3.xlsx) |
| Q4-2 | `q4_2_margin` | 14,829,820.21 | [result4-2.xlsx](results/final_recommendation/result4-2.xlsx) |
| Q4-3 | `q4_3_adjust_A` | 15,213,707.64 | [result4-3.xlsx](results/final_recommendation/result4-3.xlsx) |

Q1为附件1给定单日；其余结果覆盖2025-02-01至12-31，共334天。Q1在当前离散假设下有求解器最优证书；Q2是已试可行策略中费用最低的回溯推荐，Q3/Q4为当前已验证方案，均不宣称年度全局最优。

**五本文件均未标记为可正式提交。** 原模板时间标签晚10分钟，效率、端口、日内反馈、退款及价格信息等解释仍需队员审阅，见 [`ASSUMPTIONS.md`](context/ASSUMPTIONS.md) 与 [`TEMPLATE_MAPPING.md`](context/TEMPLATE_MAPPING.md)。

## 阅读入口

- [当前状态与待办](context/CURRENT_STATE.md)：当前结论、已完成内容和仍未解决的问题。
- [第二问最终答案](paper/analysis/第二问最终答案.md)：最新Q2方法、费用构成和选择依据。
- [第二问迭代评估](paper/analysis/第二问迭代评估.md)：候选对照、失败实验与不可实施ORACLE下界。
- [首轮v1方法与对照记录](paper/analysis/C题四问答案与建模审理说明.md)：Q1/Q3/Q4方法以及v1内部消融；该历史记录中的Q2不是当前推荐。
- [正式论文源文件](paper/overleaf/main.tex)：分章LaTeX，目前完成问题背景、四问要求、图示流程和6条假设，其余章节待写。
- [SJTU在线项目](https://latex.sjtu.edu.cn/project/6aa27f6bbd92933f73a5ac15)：已同步的正式稿，最近核验为XeLaTeX/TeX Live 2025、4页。
- [Canva图示稿](https://www.canva.com/design/DAHU0aqVVig/mjgvOiLyeP096QiViStfFg/edit)：可编辑图示，矢量源和核验在 `figures/overview/canva/`。

## 版本规则

- `results/final_recommendation/` 是五项当前结果的唯一入口。
- `full-evaluation-v1` 与 `results/evaluation/` 为正确的首轮基线、消融与汇总；不能将新Q2和旧Q3的费用差直接解释为预报价值。
- 含未解析引用的旧 `paper/overleaf/main.pdf`、旧Q2交付表、未整合新Q2的整篇初稿PDF及旧首轮ZIP已删除。删除清单见 [`REMOVED_DELIVERABLES.json`](results/final_recommendation/REMOVED_DELIVERABLES.json)。
- 原始竞赛附件只读。第三方参考论文、环境链接、逐区间大轨迹、全单元格扫描、临时截图和重复发布ZIP不提交Git；保留必要源码、输入、日/月汇总、参数和验证证据。

## 核验与复现

```bash
python3 src/catalog_results.py --check
.venv/bin/python -m pytest tests -q
latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd -outdir=build paper/overleaf/main.tex
```

本次数值核验覆盖Q1的144区间、四项年度结果各48096区间、日汇总与费用账本、五本工作簿哈希；50项测试通过。整理只复制已有核验结果，没有新优化或改写数值。完整复现与工具依赖见 [`docs/REPRODUCE.md`](docs/REPRODUCE.md)。

AI参与与人工审核状态据实记录在论文分析目录及共享context中；编译或测试通过不代替题意消歧和队员最终审阅。
