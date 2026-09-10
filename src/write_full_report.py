from pathlib import Path
import json

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'results/backtests/full-evaluation-v1'
LABELS={'q2_no_battery':'Q2无储能','q2_point':'Q2点预测','q2_margin':'Q2校准裕量',
        'q2_margin_greedy':'Q2裕量与贪心','q3_midnight':'Q3仅零点预报',
        'q3_frozen_update':'Q3冻结预报重规划','q3_battery_update':'Q3四预报仅电池',
        'q3_adjust_A':'Q3允许调整A','q3_selective_A':'Q3选择性调整A',
        'q3_adjust_B':'Q3允许调整B','q4_2_margin':'Q4-2因果价格',
        'q4_3_adjust_A':'Q4-3调整A','q4_3_adjust_B':'Q4-3调整B'}


def main():
    summary=json.loads((RUN/'summary.json').read_text())
    dest=ROOT/'paper/analysis'
    evaluation=ROOT/'results/evaluation'
    evaluation.mkdir(exist_ok=True)
    table=[]
    for k,label in LABELS.items():
        s=summary[k]
        assert s['days']==334 and s['intervals']==48096 and s['verification']['passed']
        table.append(dict(strategy=k,label=label,total_fee_yuan=s['total_fee'],emergency_kwh=s['emergency'],
                          terminal_soc_kwh=s['terminal_soc_kwh'],modifications=s['contract_modification_decisions']))
    pd.DataFrame(table).to_csv(evaluation/'strategy_comparison.csv',index=False)
    rows=['\\small\\begin{longtable}{lrrrr}\\toprule 策略 & 费用/万元 & 紧急电/MWh & 末储量/kWh & 修改次数\\\\\\midrule\\endfirsthead',
          '\\toprule 策略 & 费用/万元 & 紧急电/MWh & 末储量/kWh & 修改次数\\\\\\midrule\\endhead']
    for r in table:
        rows.append(f"{r['label']} & {r['total_fee_yuan']/1e4:.2f} & {r['emergency_kwh']/1000:.2f} & {r['terminal_soc_kwh']:.2f} & {r['modifications']}\\\\")
    rows.append('\\bottomrule\\end{longtable}')
    (dest/'annual_comparison.tex').write_text('\n'.join(rows)+'\n')
    pairs=[('q2_point','q2_margin'),('q3_frozen_update','q3_battery_update'),
           ('q3_battery_update','q3_adjust_A'),('q3_midnight','q3_adjust_A'),
           ('q3_adjust_A','q3_adjust_B')]
    paired=[]
    rng=np.random.default_rng(2026)
    for a,b in pairs:
        x=pd.read_csv(RUN/a/'daily.csv').set_index('date')
        y=pd.read_csv(RUN/b/'daily.csv').set_index('date')
        assert x.index.equals(y.index)
        delta=(x.total_fee-y.total_fee).to_numpy()
        means=[]
        for _ in range(2000):
            starts=rng.integers(0,len(delta)-6,size=48)
            sample=np.concatenate([delta[j:j+7] for j in starts])[:len(delta)]
            means.append(sample.mean())
        paired.append(dict(baseline=a,comparison=b,saving_total_yuan=float(delta.sum()),
             cheaper_days=int((delta>1e-7).sum()),dearer_days=int((delta < -1e-7).sum()),
             mean_daily_saving_yuan=float(delta.mean()),block7_resample_95_low=float(np.quantile(means,.025)),
             block7_resample_95_high=float(np.quantile(means,.975)),block_days=7,repeats=2000,seed=2026,
             caveat='Descriptive moving-block resampling on one seasonal year, not an out-of-year guarantee or causal information value'))
    pd.DataFrame(paired).to_csv(evaluation/'paired_comparisons.csv',index=False)
    display=[]
    for key in ['q2_margin','q3_adjust_A','q4_2_margin','q4_3_adjust_A']:
        frame=pd.read_csv(RUN/key/'intervals.csv.gz')
        for date in ['2025-03-20','2025-06-21','2025-09-23','2025-12-21']:
            day=frame.loc[frame.date==date].reset_index(drop=True)
            display.append(dict(strategy=key,date=date,planned_kwh=day.planned_grid.sum(),
                final_contract_kwh=day.contract_grid.sum(),emergency_kwh=day.emergency.sum(),
                total_fee_yuan=day.total_fee.sum(),initial_soc_kwh=day.soc_start.iloc[0],
                terminal_soc_kwh=day.soc_end.iloc[-1]))
    pd.DataFrame(display).to_csv(evaluation/'designated_days.csv',index=False)
    rows=['\\small\\begin{longtable}{llrrrr}\\toprule 策略 & 日期 & 原计划/kWh & 紧急电/kWh & 总费/元 & 末储量/kWh\\\\\\midrule\\endfirsthead',
          '\\toprule 策略 & 日期 & 原计划/kWh & 紧急电/kWh & 总费/元 & 末储量/kWh\\\\\\midrule\\endhead']
    for r in display:
        rows.append(f"{LABELS[r['strategy']]} & {r['date'][5:]} & {r['planned_kwh']:.1f} & {r['emergency_kwh']:.1f} & {r['total_fee_yuan']:.1f} & {r['terminal_soc_kwh']:.1f}\\\\")
    rows.append('\\bottomrule\\end{longtable}')
    (dest/'designated_days.tex').write_text('\n'.join(rows)+'\n')
    report=['# 四问首轮实际结果','',
        '当前统一运行：results/backtests/full-evaluation-v1；Q1另见results/q1/summary.json。阶段A–D基础策略已实际执行，阶段E为自动生成初稿，模板时间/解释和队员人工核验未最终确认。','',
        '| 策略 | 334天总费用/元 | 紧急电/kWh | 末储量/kWh | 修改决策次数 |','|---|---:|---:|---:|---:|']
    report += [f"| {r['label']} | {r['total_fee_yuan']:.2f} | {r['emergency_kwh']:.2f} | {r['terminal_soc_kwh']:.2f} | {r['modifications']} |" for r in table]
    report += ['', '## 结论边界', '',
        'Q1为暂定离散解释下的求解器认证最优；Q2–4为预先定义的预测/控制策略真实回测，非随机多阶段全局最优。日前信息与未来扰动检查通过；执行仍为区间内平均功率反馈近似。',
        'Q3新预报只更新电池未在本策略中带来节省。合同调整A较同四预报电池对照省钱，但较仅零点预报更贵。信息可被忽略，不能从这个策略比较推断信息本身负价值。A/B两种结算不可混算，B较低费用依赖退款解释。',
        '不同策略末SOC已列出；Q3相关策略末SOC一致，Q2末态差异需结合terminal_credit_sensitivity判断，禁止把免费起末能量差当收益。',
        'paired_comparisons.csv保存配对差及7日块再抽样描述区间，保留季节性/单年局限；全年结果未反向参与训练或主策略参数选择。',
        '', '## 下一阶段', '',
        '1. 根据官方澄清决定模板时间映射、90%效率、计量端口及A/B和多次调整价口径。',
        '2. 以过去验证窗口校准6/12/18预报的分提前期误差，改进当前整日裕量沿用；验证观测延迟/区间内波动和终端策略。',
        '3. 在相同结算和终端条件下补充价格已知条件对照、容量/功率/费率等扩展敏感性；不把未执行扩展写入结论。',
        '4. 队员审阅模型/源码/结果与AI披露后整合既有正式LaTeX工作区；不自动提交。']
    (ROOT/'context/FIRST_ROUND_REPORT.md').write_text('\n'.join(report)+'\n')
    evidence=ROOT/'paper/CLAIM_EVIDENCE_MAP.md'
    base=evidence.read_text().split('\n## Q2–4统一运行证据')[0]
    extra='\n## Q2–4统一运行证据\n\n'
    extra+='- 13策略334天费用、紧急量、末SOC：results/backtests/full-evaluation-v1/{strategy}/summary.json及intervals.csv.gz；独立结果results/audit/online_review_full.json。\n'
    extra+='- 预报/修改价值比较：results/evaluation/paired_comparisons.csv；相同信息/重优化对照及A/B边界见BACKTEST_REPORT。不是额外信息最优价值证明。\n'
    extra+='- 指定日汇总：results/evaluation/designated_days.csv，按源intervals聚合。\n'
    extra+='- 源码：run目录source_snapshot和provenance记录，与当前实现哈希核对；日期/预报泄漏测试见tests/test_online.py与独立在线审计。\n'
    evidence.write_text(base+extra)
    print('Generated 13-strategy tables, paired comparisons, designated days and first-round report')


if __name__=='__main__':main()
