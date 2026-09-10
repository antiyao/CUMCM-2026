from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    summary=json.loads((ROOT/'results/q1/summary.json').read_text())
    s=summary['strategies']
    dest=ROOT/'paper/analysis'
    dest.mkdir(parents=True,exist_ok=True)
    f=lambda v:f'{v:,.4f}'
    no=s['no_storage']['solver']['objective']
    best=s['milp']['solver']['objective']
    macros={'RunID':summary['run_id'],'QOneCost':f(best),'NoStorageCost':f(no),
            'RuleCost':f(s['simple_rule']['solver']['objective']),
            'QOneGrid':f(s['milp']['grid_kwh']),'Saving':f(100*(no-best)/no),
            'TotalLoad':f(summary['total_load_kwh']),'TotalPV':f(summary['total_pv_kwh']),
            'ChargeTotal':f(s['milp']['charge_kwh']),'DischargeTotal':f(s['milp']['discharge_kwh']),
            'EfficiencyCost':f(summary['sensitivity'][0]['cost_yuan']),
            'PointCost':f(summary['sensitivity'][1]['cost_yuan'])}
    (dest/'q1_numbers.tex').write_text('\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in macros.items())+'\n')
    t1=pd.read_csv(ROOT/'results/q1/table1.csv')
    t2=pd.read_csv(ROOT/'results/q1/table2.csv')
    rows=['\\small\\begin{tabular}{lrlrlr}\\toprule 时间段 & 购电量 & 时间段 & 购电量 & 时间段 & 购电量\\\\\\midrule']
    records=list(t1.itertuples())
    for group in [records[:3],records[3:]]:
        cells=[]
        for r in group:
            h,m=divmod(r.start_minute,60)
            cells.extend([f'{h:02.0f}:{m:02.0f}--{h:02.0f}:{m+10:02.0f}',f'{r.grid_kwh:.4f}'])
        rows.append(' & '.join(cells)+'\\\\')
    rows.append('\\midrule\\multicolumn{2}{c}{全天购电量/kWh} & '+f(s['milp']['grid_kwh'])+' & \\multicolumn{2}{c}{全天购电费/元} & '+f(best)+'\\\\')
    rows.append('\\bottomrule\\end{tabular}')
    (dest/'q1_table1.tex').write_text('\n'.join(rows)+'\n')
    rows=['\\small\\begin{tabular}{lrrlrr}\\toprule 时间段 & 充电量 & 放电量 & 时间段 & 充电量 & 放电量\\\\\\midrule']
    records=list(t2.itertuples())
    for i in range(0,6,2):
        cells=[]
        for r in records[i:i+2]:
            cells.extend([f'{r.start_hour:.0f}:00--{r.end_hour:.0f}:00',f'{r.charge_kwh:.4f}',f'{r.discharge_kwh:.4f}'])
        rows.append(' & '.join(cells)+'\\\\')
    rows.append('\\midrule\\multicolumn{2}{c}{0:00储电量} & 6000 & \\multicolumn{2}{c}{24:00储电量} & 6000\\\\')
    rows.append('\\bottomrule\\end{tabular}')
    (dest/'q1_table2.tex').write_text('\n'.join(rows)+'\n')
    claims=[
        ('Q1主费用/购电量','results/q1/summary.json; milp_dispatch.csv','src/solve_q1.py','tests/test_dispatch.py; export_validation.json'),
        ('同模型离散最优','summary.json中的status/gap/dual_bound及LP目标','src/dispatch.py','LP下界+独立硬约束复算；非现场验证'),
        ('较无储能节省26.8981%','summary.json两策略目标','src/write_q1_report.py','相同6000首末状态和物理参数'),
        ('效率/采样解释敏感性','summary.json sensitivity','src/solve_q1.py','各方案独立守恒检查'),
        ('官方模板时间歧义','data/templates/2026C/result1.xlsx','src/export_q1.mjs','template_mapping.csv与原始标签逐格保留')]
    out=['# 论文主张与证据','',f'Q1当前运行：`{summary["run_id"]}`。其他问题以实际BACKTEST_REPORT为准，不提前填量化结论。','',
         '| 主张 | 数据 | 代码 | 验证/边界 |','|---|---|---|---|']
    out += ['| '+' | '.join(row)+' |' for row in claims]
    (ROOT/'paper/CLAIM_EVIDENCE_MAP.md').write_text('\n'.join(out)+'\n')
    print('Generated Q1 LaTeX values, tables and evidence map from current run')


if __name__=='__main__':
    main()
