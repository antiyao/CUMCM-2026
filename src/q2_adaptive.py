import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

from q2_iteration import (Variant, prepare_forecasts, visible_packet, plan_packet,
                          execute_plan, save_variant)
from backtest import aggregate
from dispatch import Battery

ROOT=Path(__file__).resolve().parents[1]


def select_past_policy(history, cutoff, price, eta_charge, window_days=14):
    rows=[r for r in history if pd.Timestamp(r['available_at'])<=pd.Timestamp(cutoff)]
    last_dates=sorted({r['date'] for r in rows})[-window_days:]
    rows=[r for r in rows if r['date'] in last_dates]
    if not rows:
        raise ValueError('No completed shadow-policy validation days')
    costs={}
    for r in rows:
        adjusted=r['cost_yuan']-(r['end_soc']-r['start_soc'])*float(np.min(price))/eta_charge
        costs.setdefault(r['strategy'],[]).append(adjusted)
    assert len({len(v) for v in costs.values()})==1
    scores={k:float(np.mean(v)) for k,v in costs.items()}
    return min(scores,key=scores.get),scores,last_dates


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',required=True)
    ap.add_argument('--end-date',default='2025-12-31')
    args=ap.parse_args()
    out=ROOT/args.output;out.mkdir(parents=True,exist_ok=False)
    actuals=pd.read_csv(ROOT/'data/processed/2026C/actuals.csv',parse_dates=['interval_start','interval_end','available_at'])
    actuals=actuals.loc[actuals.date<=args.end_date].copy()
    price=pd.read_csv(ROOT/'data/processed/2026C/q1.csv').price.to_numpy()
    battery=Battery()
    variants=[Variant('legacy_margin_greedy',margin='legacy')]
    variants += [Variant(f'{prefix}hourly_q{q:g}',bias_days=bias,margin='hourly',quantile=q)
                 for prefix,bias in [('',0),('bias_',3)] for q in [0.,.65,.8,.9]]
    registry={v.name:v for v in variants}
    protocol=dict(candidates=[asdict(v) for v in variants],window_days=14,
                  criterion='past shadow cost minus known-price replacement value of SOC change',
                  selection_timing='before observing current date',
                  virtual_warmup='all shadow policies start 6000 on January 15; actual battery holds 6000 through January',
                  retrospective_development=True)
    (out/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    days,cache,metadata=prepare_forecasts(actuals,price)
    day_frames=[actuals.loc[actuals.date==d].copy() for d in days]
    states={v.name:6000. for v in variants}
    history=[]
    actual_state=6000.
    frames=[];decisions=[]
    begin=days.index('2025-01-15')
    for i in range(begin,len(days)):
        date=days[i]
        cutoff=pd.Timestamp(date)
        if date>='2025-02-01':
            chosen,scores,validation_dates=select_past_policy(history,cutoff,price,battery.eta_charge)
            variant=registry[chosen]
            packet=visible_packet(days,cache,metadata,i,variant)
            plan=plan_packet(packet,variant,actual_state,price,battery)
            decisions.append(dict(packet['metadata'],strategy='adaptive_selector',active_variant=asdict(variant),
                initial_soc=actual_state,solver=plan['solver'],decision_type='day_ahead',changed_contract=False,
                selection_scores_yuan=scores,selection_last_date=validation_dates[-1],
                selection_dates=validation_dates))
            frame,actual_state=execute_plan(day_frames[i],price,plan,actual_state,variant,battery)
            frames.append(frame)
        for variant in variants:
            packet=visible_packet(days,cache,metadata,i,variant)
            plan=plan_packet(packet,variant,states[variant.name],price,battery)
            before=states[variant.name]
            frame,states[variant.name]=execute_plan(day_frames[i],price,plan,before,variant,battery)
            history.append(dict(strategy=variant.name,date=date,available_at=str(cutoff+pd.Timedelta(days=1)),
                cost_yuan=float(frame.total_fee.sum()),start_soc=before,end_soc=states[variant.name]))
        if date>='2025-02-01' and (i-31)%30==0:
            print(json.dumps({'date':date,'selected':chosen,'state':actual_state}),flush=True)
    frame=pd.concat(frames,ignore_index=True)
    daily,monthly,summary=aggregate(frame,battery)
    summary['strategy']=dict(name='adaptive_selector',controller='greedy',battery=True,variable_price=False,
                             forecasts='none',adjustments='none',interpretation='A')
    summary['contract_modification_decisions']=0
    summary['selection_counts']=pd.Series([r['active_variant']['name'] for r in decisions]).value_counts().to_dict()
    save_variant(out,Variant('adaptive_selector'),(frame,daily,monthly,summary,decisions))
    pd.DataFrame(history).to_csv(out/'shadow_daily_scores.csv',index=False)
    (out/'summary.json').write_text(json.dumps({'adaptive_selector':summary},indent=2)+'\n')
    files=[Path(__file__),ROOT/'src/q2_iteration.py',ROOT/'src/dispatch.py',ROOT/'src/backtest.py',ROOT/'src/forecasting.py',
           ROOT/'data/processed/2026C/actuals.csv',ROOT/'data/processed/2026C/q1.csv']
    snapshot=out/'source_snapshot';snapshot.mkdir()
    for f in files:
        if f.suffix=='.py':shutil.copy2(f,snapshot/f.name)
    (out/'provenance.json').write_text(json.dumps(dict(run_id=out.name,created_utc=datetime.now(timezone.utc).isoformat(),
        actual_initial_soc=6000,actual_start='2025-02-01',actual_end=days[-1],seed=2026,
        real_time_observation='ideal within-interval average power feedback, same as v1',
        protocol=protocol,files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}),indent=2)+'\n')
    print(json.dumps({'total_fee':summary['total_fee'],'emergency':summary['emergency'],'selection_counts':summary['selection_counts']},indent=2))


if __name__=='__main__':main()
