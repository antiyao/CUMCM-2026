"""Retrospective Q2 experiment. All forecasts consume historical prefixes only.
Candidate rules are frozen in PROTOCOL.md; January-only calibration of risk q.
No official result workbook is overwritten. Requires Python 3.10+, numpy/scipy.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from pathlib import Path
from datetime import date,timedelta
import numpy as np
from reference_dispatch import dispatch

ROOT=Path(__file__).resolve().parent
EC=ED=.9
LO,HI,CAP=1200.,10800.,5000./6

def forecast(load_hist: np.ndarray,pv_hist: np.ndarray,corrected: bool=False):
    n=len(load_hist)
    if n<7 or load_hist.shape!=pv_hist.shape:
        raise ValueError('At least 7 completed days required; histories must match.')
    lh=load_hist[-7].copy()
    vh=pv_hist[-7:].mean(axis=0)
    if corrected and n>=10:
        lr=[]; vr=[]
        for j in range(n-3,n):
            lr.append(load_hist[j]-load_hist[j-7])
            vr.append(pv_hist[j]-pv_hist[j-7:j].mean(axis=0))
        lh+=np.mean(lr,axis=0)
        vh+=np.mean(vr,axis=0)
    return np.maximum(lh,0)/6,np.maximum(vh,0)/6

def forecast_and_errors(load,pv,corrected):
    # All calls are prefix-restricted; each residual is observable after that day.
    preds=np.full((len(load),2,144),np.nan)
    residuals=np.full((len(load),144),np.nan)
    for d in range(7,len(load)):
        a,b=forecast(load[:d],pv[:d],corrected)
        preds[d,0]=a;preds[d,1]=b
        residuals[d]=(load[d]-pv[d])/6-(a-b)
    return preds,residuals

def safety(residual_hist: np.ndarray,q: float):
    if q==0:return np.zeros(144)
    z=residual_hist[-14:]
    z=z[np.isfinite(z).all(axis=1)]
    if not len(z):return np.zeros(144)
    # Hour-by-hour pool of prior completed days; no future day residuals.
    r=np.quantile(z.reshape(len(z),24,6).transpose(1,0,2).reshape(24,-1),q,axis=1)
    return np.repeat(np.maximum(r,0.),6)

def run(load,pv,p,preds,residuals,first,last,q,tag,save=True,verbose=True):
    E=6000.;rows=[];daily=[];plans=[];start=time.time()
    for d in range(first,last):
        lh,vh=preds[d]
        extra=safety(residuals[:d],q)
        plan=dispatch(lh+extra,vh,p,initial=E,terminal=6000.,integer_mode=True)
        g=plan['grid']; before_day=E
        ds=(date(2025,1,1)+timedelta(days=d)).isoformat()
        Hs=[];Cs=[];Ds=[];Ws=[]
        for t in range(144):
            L=float(load[d,t]/6);V=float(pv[d,t]/6);bef=E
            excess=float(g[t]+V-L)
            if excess>=0:
                C=min(excess,CAP,max(0.,(HI-E)/EC));D=H=0.;W=excess-C
            else:
                C=W=0.;D=min(-excess,CAP,max(0.,ED*(E-LO)));H=-excess-D
            E=bef+EC*C-D/ED
            balance=g[t]+V+D+H-L-C-W
            if abs(balance)>1e-6 or E<LO-1e-6 or E>HI+1e-6:
                raise AssertionError((ds,t,balance,E))
            Hs.append(H);Cs.append(C);Ds.append(D);Ws.append(W)
            if save:
                rows.append([ds,t,float(p[t]),float(g[t]),L,V,C,D,H,W,bef,E,
                             float(p[t]*g[t]),float(5*p[t]*H),float(lh[t]),float(vh[t]),float(extra[t]),
                             d-1,d-1])
        Hs=np.array(Hs)
        daily.append(dict(date=ds,initial_kwh=before_day,final_kwh=E,
                          planned_kwh=float(sum(g)),emergency_kwh=float(sum(Hs)),
                          planned_yuan=float(p@g),emergency_yuan=float(5*p@Hs),
                          total_yuan=float(p@g+5*p@Hs),unutilized_kwh=float(sum(Ws)),
                          charge_kwh=float(sum(Cs)),discharge_kwh=float(sum(Ds))))
        if verbose and ((d-first+1)%70==0 or d==last-1):
            print(tag,d-first+1,'days',round(time.time()-start,2),'sec',flush=True)
    result=dict(tag=tag,q=q,days=last-first,start=daily[0]['date'],end=daily[-1]['date'],
                initial_kwh=6000.,final_kwh=E,
                planned_yuan=sum(x['planned_yuan'] for x in daily),
                emergency_yuan=sum(x['emergency_yuan'] for x in daily),
                total_yuan=sum(x['total_yuan'] for x in daily),
                emergency_kwh=sum(x['emergency_kwh'] for x in daily),
                unutilized_kwh=sum(x['unutilized_kwh'] for x in daily),
                emergency_days=sum(x['emergency_kwh']>1e-6 for x in daily),
                seconds=time.time()-start)
    if save:
        dest=ROOT/'results'/tag;dest.mkdir(parents=True,exist_ok=True)
        with (dest/'trace.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['date','step','price','planned_grid_kwh','actual_load_kwh',
            'actual_pv_kwh','charge_kwh','discharge_kwh','emergency_kwh','unutilized_kwh',
            'energy_start_kwh','energy_end_kwh','planned_cost_yuan','emergency_cost_yuan',
            'forecast_load_kwh','forecast_pv_kwh','risk_buffer_kwh','forecast_last_day_index','residual_last_day_index'])
            w.writerows(rows)
        with (dest/'daily.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(daily[0]));w.writeheader();w.writerows(daily)
        (dest/'summary.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=ROOT/'data'/'inputs.npz')
    args=parser.parse_args()
    (ROOT/'results').mkdir(exist_ok=True)
    with np.load(args.input,allow_pickle=False) as z:
        L=z['load_kw'];V=z['pv_kw'];p=z['price']
    assert L.shape==V.shape==(365,144)
    frozen={
       'protocol_sha256':hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest(),
       'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
       'input_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
       'q_candidates':[0.,.65,.8,.9],
       'note':'Retrospective experiment after baseline year reviewed; not external blind test.'}
    (ROOT/'results'/'frozen_protocol.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    a,ea=forecast_and_errors(L,V,False);b,eb=forecast_and_errors(L,V,True)
    cal=[];select={}
    for name,pred,err in [('base',a,ea),('corrected',b,eb)]:
        choices=[]
        for q in [0.,.65,.8,.9]:
            r=run(L,V,p,pred,err,14,31,q,'cal_'+name+'_'+str(q),save=False,verbose=False)
            choices.append(r);cal.append(r)
            print('CAL',name,q,round(r['total_yuan'],2),round(r['seconds'],2),flush=True)
        select[name]=min(choices,key=lambda x:(round(x['total_yuan'],6),x['q']))['q']
    (ROOT/'results'/'january_calibration.json').write_text(json.dumps(cal,indent=2),encoding='utf-8')
    (ROOT/'results'/'selected_parameters.json').write_text(json.dumps(select,indent=2),encoding='utf-8')
    variants=[('A_baseline',a,ea,0.),('B_bias_corrected',b,eb,0.),
              ('C_risk_only',a,ea,select['base']),('D_bias_and_risk',b,eb,select['corrected'])]
    allres=[]
    for tag,pred,err,q in variants:
        r=run(L,V,p,pred,err,31,365,q,tag)
        allres.append(r)
        print('RESULT',json.dumps(r),flush=True)
    (ROOT/'results'/'comparison.json').write_text(json.dumps(allres,indent=2),encoding='utf-8')
    with (ROOT/'results'/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allres[0]));w.writeheader();w.writerows(allres)
    print('DONE',flush=True)

if __name__=='__main__':main()
