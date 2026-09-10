from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'results/q2_iteration/policy_annual_v4'
NAMES={'legacy_point_reference':'原点预测＋参考控制','legacy_margin_reference':'原主方案：动态裕量＋参考控制',
       'legacy_margin_greedy':'已有对照：动态裕量＋贪心','point_greedy':'无裕量＋贪心',
       'bias_only_greedy':'仅3日偏差修正＋贪心','hourly_risk':'固定小时保护（1月选分位）',
       'bias_hourly_risk':'偏差＋小时保护（1月选分位）','price_reserve':'价格条件下保留部分SOC',
       'scenario':'历史日块场景＋全知补救代理','adaptive_selector':'过去14日费用选择保护策略',
       'policy_saa':'与贪心执行一致的历史样本费用优化'}


def table(header,rows):
    return '\n'.join(['| '+' | '.join(header)+' |','|'+'|'.join(['---']*len(header))+'|']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])


def main():
    summary=json.loads((RUN/'summary.json').read_text())
    sources={k:RUN/k for k in summary}
    extras={'scenario':ROOT/'results/q2_iteration/annual_final_v3',
            'adaptive_selector':ROOT/'results/q2_iteration/adaptive_annual_v3'}
    for name,path in extras.items():
        summary[name]=json.loads((path/'summary.json').read_text())[name]
        sources[name]=path/name
    ordering=list(NAMES)
    old=summary['legacy_margin_greedy']['total_fee']
    selected=json.loads((RUN/'selected_parameters.json').read_text())
    rows=[]
    for k in ordering:
        s=summary[k]
        rows.append(dict(strategy=k,name=NAMES[k],total_fee=s['total_fee'],ordinary_fee=s['original_fee'],
                         emergency_fee=s['emergency_fee'],emergency_kwh=s['emergency'],unused_kwh=s['unused'],
                         initial_soc=s['initial_soc_kwh'],terminal_soc=s['terminal_soc_kwh'],
                         saving_vs_old_greedy=old-s['total_fee'],source=str(sources[k].relative_to(ROOT))))
    out=ROOT/'results/q2_iteration/evaluation_v4';out.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out/'comparison.csv',index=False)
    best=min(rows,key=lambda x:x['total_fee'])
    paired=[];rng=np.random.default_rng(2026)
    base_daily=pd.read_csv(sources['legacy_margin_greedy']/'daily.csv').set_index('date')
    for k in ordering:
        daily=pd.read_csv(sources[k]/'daily.csv').set_index('date')
        delta=base_daily.total_fee-daily.total_fee
        n=len(delta);starts=rng.integers(0,n-6,size=(2000,(n+6)//7))
        indices=(starts[:,:,None]+np.arange(7)).reshape(2000,-1)[:,:n]
        boot=delta.to_numpy()[indices].sum(axis=1)
        paired.append(dict(strategy=k,saving_yuan=float(delta.sum()),cheaper_days=int((delta>1e-6).sum()),
            dearer_days=int((delta < -1e-6).sum()),block7_total_low=float(np.quantile(boot,.025)),
            block7_total_high=float(np.quantile(boot,.975)),repetitions=2000,seed=2026))
    pd.DataFrame(paired).to_csv(out/'paired_comparisons.csv',index=False)
    best_pair=next(r for r in paired if r['strategy']==best['strategy'])
    primary='policy_saa'
    primary_daily=pd.read_csv(sources[primary]/'daily.csv').set_index('date')
    monthly=pd.DataFrame({'old_greedy_yuan':base_daily.total_fee,'policy_saa_yuan':primary_daily.total_fee})
    monthly=monthly.groupby(monthly.index.str[:7]).sum();monthly['saving_yuan']=monthly.old_greedy_yuan-monthly.policy_saa_yuan
    monthly.to_csv(out/'monthly_policy_vs_old.csv')
    best_daily=pd.read_csv(sources[best['strategy']]/'daily.csv').set_index('date')
    best_monthly=pd.DataFrame({'old_greedy_yuan':base_daily.total_fee,'best_candidate_yuan':best_daily.total_fee})
    best_monthly=best_monthly.groupby(best_monthly.index.str[:7]).sum()
    best_monthly['saving_yuan']=best_monthly.old_greedy_yuan-best_monthly.best_candidate_yuan
    best_monthly.to_csv(out/'monthly_best_vs_old.csv')
    diagnostics=[]
    for line in (sources[primary]/'decisions.jsonl').read_text().splitlines():
        d=json.loads(line);s=d['solver']
        diagnostics.append(dict(date=d['cutoff'][:10],status=s['status'],iterations=s['iterations'],
            objective=s['objective'],initial_objective=s['initial_objective'],
            in_sample_improvement=s['in_sample_improvement_yuan'],runtime=s['runtime_seconds'],
            initial_retained=s['initial_grid_retained'],latest_residual=s['latest_residual_available_at']))
    diag=pd.DataFrame(diagnostics);diag.to_csv(out/'policy_solver_diagnostics.csv',index=False)
    assert (diag.objective<=diag.initial_objective+1e-6).all()
    d=summary[primary]
    text=['# 第二问迭代审查与实测结果','',
          '范围：固定原始附件、10分钟计量、单程效率0.9、储能容量/功率、计划全额收费、5倍紧急价格、1月待机6000及2月后状态连续。仅研究第二问，不读附件3，不修改日内合同。已看过全期历史结果，本轮属于因果实现下的回溯开发，不是未见数据上的盲测。','',
          '## 1. 上传方案有无问题','',
          '配套源码、输入和4条48096行轨迹已独立核验；输入与本地逐项一致，预测/修正/小时保护只用历史，物理和账务检查通过。主要问题不是发现造假或费用漏计，而是比较基线不同、1月参数的季节泛化不足，以及跨求解器版本的等价最优解换解。',
          '外部基线采用负载7日前同期、PV过去7日均值和greedy；本地原基线用昨日/上周/Ridge按历史误差选模并采用参考SOC控制。其8.55%/9.06%只相对它自己的15,252,429.00元成立，不能视作本地新增收益。外部D为13,869,999.38元，只比本地已有greedy对照低约5,697.84元。完整审查与原样重跑见context/Q2_EXTERNAL_REVIEW.md。','',
          '## 2. 本轮实际比较','',
          table(['策略','334天总费/元','紧急费/元','紧急电/kWh','末储量/kWh','较已有greedy节省/元'],
                [[r['name'],f"{r['total_fee']:,.2f}",f"{r['emergency_fee']:,.2f}",f"{r['emergency_kwh']:,.2f}",f"{r['terminal_soc']:,.2f}",f"{r['saving_vs_old_greedy']:,.2f}"] for r in rows]),
          '',f"本轮回溯费用最低行是**{best['name']}，{best['total_fee']:,.2f}元**。这不是全局最优或外部泛化证明。按1月15—31日回放选出的家族仍是`{selected['deployment_family']}`；不能把全年最便宜的候选包装成一月份已经独立选中的部署赢家。",'',
          '小时保护与价格条件留电的一月表现未稳定推广到全年；过去14日费用选择也未自动胜过旧策略。3/5场景的预知补救代理与真实greedy不一致，场景方案失败结果保留。没有继续按全年最优值调整这些候选。','',
          '## 3. 当前最低费用候选及代价','',
          f"{best['name']}相对已有greedy只节省{best['saving_vs_old_greedy']:,.2f}元（{100*best['saving_vs_old_greedy']/old:.6f}%）。其14日同小时0.8分位数按一月选择，但不是跨家族的一月胜出者；本文件将其标为回溯研究候选，不倒填成已获独立验证的部署决策。",
          '与已有greedy相比，普通计划费增加120,614.80元，紧急费减少128,306.90元；净节省7,692.10元。紧急电从79,792.19降至60,360.94kWh（减少24.3523%），紧急事件211→184，日费用95%尾均值71,786.24→68,592.38元。未利用总量增加200,362.85kWh，约7.4%；不能将所有未利用量称为弃光。',
          '本地净负载预测MAE由272.834341 kW升至291.109245 kW，因此不能把该候选描述成预测更准。它通过偏差/保护/储能执行的组合改变费用和风险，经济指标与平均预测误差不是同一目标。',
          '末储量由6,038.53变为6,136.73kWh，新候选并没有靠额外消耗期末电池省钱。两者末能量替代价值修正差约40.51元，与7,692.10元分开列示，不虚构售电收入，也不等于严格相同终态实验。','',
          f"该候选{best_pair['cheaper_days']}天更便宜、{best_pair['dearer_days']}天更贵。7日移动块再抽样的全期节省95%描述区间为[{best_pair['block7_total_low']:,.2f}, {best_pair['block7_total_high']:,.2f}]元，跨过0。因此现有证据不足以说费用优势稳定或显著；不建议仅凭0.055%的回溯费用差直接淘汰已有greedy基线。它更适合作为本样本紧急用电风险较低、但浪费更多电量的备选。",'',
          '## 4. 与实际执行一致的优化策略：已试但未胜出','',
          '日前合同q跨所有历史误差日共享。取当前历史预测净负载，加上最近14或28个已完成的样本外完整误差日；每一场景按与实际完全相同的greedy逐步充放、饱和和紧急补缺，不让控制器预先看到该场景未来。两个历史窗仅用1月回放选择，之后冻结，残差窗口随日期向前更新。',
          '目标为：普通合同费 + 历史样本平均的实际greedy紧急费 + 平均终端短缺估值。终端系数固定为已知最低电价/充电效率，短缺是max(6000−末SOC,0)；估值仅用于规划，不进入真实收费账本。与旧模型相比，除优化执行费用外还改变了终端处理，这是一套策略改变，不能把改善全归于预测精度。',
          '初值是已有动态裕量方案的计划。对greedy分段状态递推计算反向梯度，L-BFGS-B至多50次迭代，只约束合同非负；始终保留初值，对样本目标不改善或物理不通过的候选不采用。非光滑优化仅称best-found，不输出全局最优证书。',
          f"本轮policy_saa总费**{d['total_fee']:,.2f}元**，普通费{d['original_fee']:,.2f}元、紧急费{d['emergency_fee']:,.2f}元；紧急电{d['emergency']:,.2f}kWh、未利用总电量{d['unused']:,.2f}kWh，末SOC{d['terminal_soc_kwh']:,.2f}kWh。",'',
          '## 5. 最低费用候选的月度结果与不利日期','',
          table(['月份','已有greedy/元','偏差＋小时保护/元','节省/元'],[[i,f'{r.old_greedy_yuan:,.2f}',f'{r.best_candidate_yuan:,.2f}',f'{r.saving_yuan:,.2f}'] for i,r in best_monthly.iterrows()]),
          '', '正数为节省，负数为变贵。配对日差与7日移动块2000次再抽样见evaluation_v4/paired_comparisons.csv；这是单个季节性年份上的描述区间，不是未来收益保证。', '',
          '## 6. 验证与限制','',
          '所有来源/执行源码均按运行目录保存快照和SHA。既有v1三个基线在同一runner中精确复现；原附件、下载目录和旧五本Excel未覆盖。',
          '新测试覆盖未来数据不改过去预测/裕量/计划、未来shadow结果不参与当日选择、SAA梯度有限差分、执行器逐步一致、历史标签拒绝、初值保留及物理边界。每条实际轨迹均需独立重算输入、母线/SOC、功率、互斥、紧急只补缺和逐行费用。独立审计结果另存run目录，不以优化器success代替它。',
          f"SAA求解状态计数：{diag.status.value_counts().to_dict()}；保留初值天数{int(diag.initial_retained.sum())}。达到50步上限的可行最好点不是已证最优。",
          '实时执行仍采用区间内恒定平均功率反馈，不认证秒级跟踪。不同策略最终储电量、终端价值差与未利用量均如实列出，没有新增售电收入。时标、效率与模板标签仍为此前公开的暂定解释。', '',
          '## 7. 完美信息下界：只用于诊断', '',
          '另外单次求解334天连续LP，所有未来负载/PV仅在该明确标为ORACLE的隔离计算中可见；初始6000、终态固定为新候选6136.72869169657kWh，同效率/功率/容量/普通价，无跨日重置。HiGHS状态0、物理复算通过，认证费用下界为12,230,448.060614元。',
          '新候选比该下界高1,637,557.056382元。但差额混合了完美信息价值、有限视野和策略近似，不能当成现有信息下承诺能节省的金额。此下界是在候选全部完成之后才计算，未用于预测、参数选择或回填正式合同；其调度不能作为第二问可实施答案。证据：results/q2_iteration/oracle_bound_v4/summary.json。','',
          '## 8. 复现与交付','',
          '主迭代：results/q2_iteration/policy_annual_v4；场景对照：annual_final_v3；动态选择对照：adaptive_annual_v3。各子目录包含intervals.csv.gz、daily/monthly、summary与decisions，均为真实执行。',
          '命令：`.venv/bin/python src/q2_iteration.py --policy --output results/q2_iteration/new_policy_run`；动态选择用`src/q2_adaptive.py --output ...`。输出须新建目录，不能覆盖历史run。',
          '新Q2候选已在results/q2_iteration/review_candidate_v4/submission/result2.xlsx隔离导出，36项独立导出检查及7幅目视QA通过；184个紧急事件，费用对账差0。旧五本及旧导出报告哈希均未改变，仍保留模板时间标签歧义与submission_ready=false。',
          'policy_annual_v4、annual_final_v3、adaptive_annual_v3均有独立审计PASS；最后SAA逐日样本目标、实际greedy轨迹与未来扰动已另行核验。测试共50项通过；不把这些检查当成外部盲测或年度最优性证明。']
    dest=ROOT/'paper/analysis/第二问迭代评估.md';dest.write_text('\n'.join(text)+'\n')
    (out/'provenance.json').write_text(json.dumps(dict(source_runs=[str(RUN.relative_to(ROOT))]+[str(p.relative_to(ROOT)) for p in extras.values()],
            report=str(dest.relative_to(ROOT)),report_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
            best_observed=best['strategy'],january_selected_family=selected['deployment_family']),indent=2)+'\n')
    print(json.dumps({'best_observed':best['strategy'],'policy_cost':d['total_fee'],'january_family':selected['deployment_family']},ensure_ascii=False))


if __name__=='__main__':main()
