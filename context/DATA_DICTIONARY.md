# C 题数据字典

来源：题面第 2–3 页、归档后附件 1–4、附件 5 五个空白模板。由 `src/data_audit.py` 复现。

| 原件 | 实际表及布局 | 数值单位 | 题定用途 |
| --- | --- | --- | --- |
| data/raw/2026C/附件1.xlsx | Sheet1；144 行，时间/电价/小区负载/光伏发电预测功率 | 元/kWh；kW；kW | Q1 全部输入，Q2/Q3 固定每日价格 |
| data/raw/2026C/附件2.xlsx | 小区负载、光伏发电实际功率；各 365 日×144 时段 | kW | Q2–Q4 历史观测与仿真真值 |
| data/raw/2026C/附件3.xlsx | Sheet1；1460 发布×24 预报，另有日期与预报时刻 | kW | 仅 Q3/Q4-3 的已发布预报 |
| data/raw/2026C/附件4.xlsx | Sheet1；365 日×144 时段 | 元/kWh | Q4 交付时段的真实结算价格 |

原始日期覆盖 2025-01-01 至 2025-12-31；Q2–Q4 正式评估 2025-02-01 至 12-31，共 334 日、48096 个时段。全部采用题目当地无时区日历，不套用美国 DST。

## 时间和功率语义

附件 1/2/4 实际只有 144 个标签：00:10、00:20、……、23:50、0:00+1。最后标签等于当天 24:00，不是第 145 个供电区间。内部采用 144 个左闭右开时段 [00:00,00:10)、……、[23:50,24:00)，储能采用 145 个状态端点。

题面仅称“功率”，未明确瞬时值还是区间平均值。**主建模假设**：标签 t 对应此前 10 分钟的平均功率；区间电量 = 功率/6。价格同样归属此前交付区间。原件没有被改写。`q1_instantaneous_sensitivity.csv` 为端点瞬时功率的独立解释：相邻端点线性积分，以周期条件补 P(00:00)=P(24:00)，电价仍按交付区间计。周期补边是敏感性假设，不是原始观测。

## 派生文件

| 文件/字段 | 类型、单位与含义 |
| --- | --- |
| q1.csv / interval_index | 整数 0–143；当日唯一时段 |
| q1.csv / start_minute,end_minute | 相对当天 0 点的分钟；0–1430、10–1440 |
| q1.csv / price | 元/kWh；当天固定交付价格 |
| q1.csv / load_kw,pv_kw | kW；主假设下区间平均功率 |
| q1.csv / load_kwh,pv_kwh | kWh；对应功率除以 6 |
| actuals.csv / date,interval_index | 日期+整数联合主键；52560 行 |
| actuals.csv / interval_start,interval_end | ISO 当地时间；相邻区间端点衔接 |
| actuals.csv / load_kw,pv_kw,price_variable,load_kwh,pv_kwh | 真实数据及物理单位同上；仅仿真环境持有未来记录 |
| actuals.csv / available_at | 保守的已完成区间数据可用时点，等于 interval_end；并非官方公布时间。实时控制若使用当前区间观测须另声明执行信息假设 |
| forecasts.csv / issue_time,available_at | ISO 当地时间；预报发布时刻及假定即时可用时刻，二者相同 |
| forecasts.csv / target_time | issue_time+lead_time 小时；保留跨年目标 |
| forecasts.csv / lead_time | 整数小时，1–24，绝非 0–23 |
| forecasts.csv / value | kW；对应整点预报，未擅自插值为 10 分钟 |
| forecasts.csv / source_row,source_column | Excel 1 基坐标，保留值级来源 |
| arrays.npz | 同内容的数值缓存；数组日期/发布顺序与 CSV 一致；不得给计划器传可任意索引的全年真值 |

附件 3 日期空白为同一日期的延续：按首次非空日期向下填充 1095 个日期标签；没有填补任何缺失功率。每个 (issue_time,lead_time) 保留唯一记录，不能按 target_time 去重。末次发布 2025-12-31 18:00，末目标为 2026-01-01 18:00，这些跨年预报真实存在，不能当成额外的 2025 年观测。预报 lead 0 未给出，后续重采样要明确因果边界。
