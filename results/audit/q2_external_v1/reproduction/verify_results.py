"""Independent Q2 trace audit; does not call optimizer or simulation code.
Reconstructs input-based forecasts and hourly risk quantiles from source snapshot.
"""
from pathlib import Path
from datetime import datetime,date,timedelta
import csv,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent

def audit(name):
    z=np.load(ROOT/'data'/'inputs.npz',allow_pickle=False)
    L=z['load_kw']/6;V=z['pv_kw']/6;p=z['price']
    corrected=name in ['B_bias_corrected','D_bias_and_risk']
    q=json.loads((ROOT/'results'/name/'summary.json').read_text())['q']
    # Independent forecast construction, written separately from planner.
    pl=np.full_like(L,np.nan);pv=np.full_like(V,np.nan)
    for d in range(7,365):
        a=L[d-7].copy();b=sum(V[d-i] for i in range(1,8))/7
        if corrected and d>=10:
            a+=sum(L[k]-L[k-7] for k in range(d-3,d))/3
            b+=sum(V[k]-sum(V[k-i] for i in range(1,8))/7 for k in range(d-3,d))/3
        pl[d]=np.maximum(a,0);pv[d]=np.maximum(b,0)
    er=L-V-pl+pv
    expected_margin=np.zeros_like(L)
    if q:
        for d in range(31,365):
            for h in range(24):
                vals=er[max(7,d-14):d,h*6:h*6+6].ravel()
                expected_margin[d,h*6:h*6+6]=max(0.,float(np.quantile(vals,q)))
    daily={};E=6000.;worst=dict(balance=0.,storage=0.,source=0.,forecast=0.,margin=0.,billing=0.)
    planned=emergency=Htotal=Wtotal=0.;rows=0;minE=E;maxE=E;emsteps=0;target_dates={}
    with (ROOT/'results'/name/'trace.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            ds=row['date'];d=(date.fromisoformat(ds)-date(2025,1,1)).days;t=int(row['step'])
            assert d==31+rows//144 and t==rows%144
            r={k:float(v) for k,v in row.items() if k!='date'}
            g=r['planned_grid_kwh'];l=r['actual_load_kwh'];v=r['actual_pv_kwh']
            c=r['charge_kwh'];di=r['discharge_kwh'];h=r['emergency_kwh'];w=r['unutilized_kwh']
            assert min(g,c,di,h,w)>-1e-6 and c<=5000/6+1e-6 and di<=5000/6+1e-6
            assert not (c>1e-6 and di>1e-6)
            assert not (c>1e-6 and h>1e-6)
            assert abs(E-r['energy_start_kwh'])<1e-6
            E+=.9*c-di/.9
            assert 1200-1e-6<=E<=10800+1e-6
            minE=min(minE,E);maxE=max(maxE,E)
            errs=dict(balance=abs(g+v+di+h-l-c-w),storage=abs(E-r['energy_end_kwh']),
                      source=max(abs(l-L[d,t]),abs(v-V[d,t]),abs(r['price']-p[t])),
                      forecast=max(abs(r['forecast_load_kwh']-pl[d,t]),abs(r['forecast_pv_kwh']-pv[d,t])),
                      margin=abs(r['risk_buffer_kwh']-expected_margin[d,t]),
                      billing=max(abs(r['planned_cost_yuan']-p[t]*g),abs(r['emergency_cost_yuan']-5*p[t]*h)))
            for k,x in errs.items():worst[k]=max(worst[k],x);assert x<1e-6,(k,ds,t,x)
            assert int(r['forecast_last_day_index'])==d-1
            assert int(r['residual_last_day_index'])==d-1
            planned+=p[t]*g;emergency+=5*p[t]*h;Htotal+=h;Wtotal+=w;emsteps+=h>1e-6;rows+=1
            if ds not in daily:daily[ds]={'planned_yuan':0.,'emergency_yuan':0.,'emergency_kwh':0.,'start_kwh':r['energy_start_kwh']}
            daily[ds]['planned_yuan']+=p[t]*g;daily[ds]['emergency_yuan']+=5*p[t]*h;daily[ds]['emergency_kwh']+=h;daily[ds]['end_kwh']=E
    assert rows==334*144
    summary=json.loads((ROOT/'results'/name/'summary.json').read_text())
    for key,value in [('planned_yuan',planned),('emergency_yuan',emergency),('total_yuan',planned+emergency),('final_kwh',E),('emergency_kwh',Htotal)]:
        assert abs(summary[key]-value)<1e-5,(key,summary[key],value)
    neterr=(L-V-pl+pv)[31:]*6
    mae=float(abs(neterr).mean());wape=float(abs(neterr).sum()/abs((L-V)[31:]*6).sum())
    month=[]
    for m in range(2,13):
        data=[r for s,r in daily.items() if int(s[5:7])==m]
        month.append(dict(month=m,planned_yuan=sum(x['planned_yuan'] for x in data),emergency_yuan=sum(x['emergency_yuan'] for x in data),
                          total_yuan=sum(x['planned_yuan']+x['emergency_yuan'] for x in data),emergency_kwh=sum(x['emergency_kwh'] for x in data)))
    for s in ['2025-03-20','2025-06-21','2025-09-23','2025-12-21']:target_dates[s]=daily[s]
    res=dict(tag=name,passed=True,rows=rows,planned_yuan=planned,emergency_yuan=emergency,total_yuan=planned+emergency,
             emergency_kwh=Htotal,unutilized_kwh=Wtotal,emergency_fee_share=emergency/(planned+emergency),
             final_kwh=E,min_kwh=minE,max_kwh=maxE,emergency_steps=int(emsteps),
             max_errors=worst,net_load_mae_kw=mae,net_load_wape=wape,monthly=month,specified_dates=target_dates,
             causality='independent prefix-only forecast and residual reconstruction matches every saved decision input; midnight plan execution inspected in source')
    (ROOT/'results'/name/'independent_audit.json').write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
    return res

def main():
    result=[audit(n) for n in ['A_baseline','B_bias_corrected','C_risk_only','D_bias_and_risk']]
    base=result[0]
    for r in result:
        r['saving_yuan']=base['total_yuan']-r['total_yuan']
        r['saving_fraction']=r['saving_yuan']/base['total_yuan']
    (ROOT/'results'/'independent_audit_all.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps([{k:r[k] for k in ['tag','passed','total_yuan','saving_yuan','saving_fraction','emergency_fee_share','final_kwh','net_load_mae_kw','net_load_wape']} for r in result],indent=2))
if __name__=='__main__':main()
