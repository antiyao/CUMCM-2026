# 核验与复现

## 先核验当前交付

```bash
python3 src/catalog_results.py --check
```

该命令只用Python标准库，核对五本工作簿与对应已验证源的字节、年度日汇总与summary费用、Q2选择记录、覆盖范围及当前索引。不会重跑优化，也不会修改结果。

科学计算环境使用Python 3.12和`configs/requirements-lock.txt`：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r configs/requirements-lock.txt
.venv/bin/python -m pytest tests -q
```

当前已安装环境为Python 3.12.14；依赖锁记录本次实际使用版本。原始竞赛输入在`data/raw/2026C/`，空模板在`data/templates/2026C/`，精确派生输入在`data/processed/2026C/`。

## 重算策略

Q1：`src/solve_q1.py`固定写入`results/q1/`，需要复算时在独立克隆或工作副本中运行。它会生成真实调度、独立物理验证和最优性证书；运行日期、时间、Git状态等元数据可能改变，比较数值而非整个summary文件哈希。

```bash
.venv/bin/python src/solve_q1.py
```

Q2最新推荐由下列迭代生成，包含多个候选，耗时长于基础测试。输出目录必须不存在：

```bash
.venv/bin/python src/q2_iteration.py --policy --output results/q2_iteration/reproduce_policy
```

Q3/Q4当前方案：

```bash
.venv/bin/python src/backtest.py --strategies q3_adjust_A,q4_2_margin,q4_3_adjust_A --end-date 2025-12-31 --output results/backtests/reproduce_q3_q4
```

完整v1的13项策略及同机会消融命令见`context/BACKTEST_REPORT.md`，Q2情景/自适应实验见`context/Q2_ITERATION_PLAN.md`与`paper/analysis/第二问迭代评估.md`。复算使用新输出目录，不覆盖历史验证记录。

Git保留参数、输入/源码指纹、源码快照、日/月汇总和验证JSON；体积较大的`intervals.csv.gz`、预测缓存、逐单元格NDJSON及临时视觉截图留在本地。高级逐区间审计和重新导出Excel前，需要先重跑相应策略得到轨迹。

## Excel与论文

已有五本当前工作簿可直接读取，不依赖Codex工具。重新导出Excel需Codex bundled Node和`@oai/artifact-tool`，以及`BUNDLED_PYTHON`所指向的bundled Python；运行时不随仓库分发。按依赖加载工具的真实位置重新建立`results/audit/artifact_runtime/node_modules`链接，或调整运行环境。不要把本机依赖目录提交。

年度导出必须明确策略来源，并使用新的目标目录与审计目录。例如复算完成后：

```bash
node src/export_annual.mjs --q2 results/q2_iteration/reproduce_policy/bias_hourly_risk --q3 results/backtests/reproduce_q3_q4/q3_adjust_A --q4-2 results/backtests/reproduce_q3_q4/q4_2_margin --q4-3 results/backtests/reproduce_q3_q4/q4_3_adjust_A --output-dir results/reproduced_workbooks --report-dir results/reproduced_export_audit
```

不要用历史`q2_margin`替换当前推荐。`src/package_first_round.py`是历史v1打包器，旧Q2交付表删除后会明确拒绝生成缺少工作簿的包；它不是当前结果发布入口。

正式论文：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -cd -outdir=build paper/overleaf/main.tex
```

图示文件已提供矢量SVG/PDF。重绘Canva图示源需bundled Python的reportlab；本地STSong字体来自macOS字体集合，不在仓库分发。Canva中的已保存设计另采用思源宋体；导出与本地源的差别见`figures/overview/canva/README.md`。当前环境的验证不等于所有平台已完成全流程测试。

## 解释边界

Q2当前推荐是对这份数据的回溯选择，不能改写为一月跨家族盲测胜者。Q3/Q4仍使用v1方案，不与新Q2直接作信息价值归因。模板时间标签、效率/端口、反馈、合同退款与未来价格可见性仍以`context/ASSUMPTIONS.md`和`SETTLEMENT_SPEC.md`的暂定解释为条件。
