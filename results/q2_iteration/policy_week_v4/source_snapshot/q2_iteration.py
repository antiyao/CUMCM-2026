import argparse
from dataclasses import dataclass, asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import pandas as pd

from backtest import aggregate, checked_optimization, RealtimeController
from dispatch import Battery
from forecasting import ForecastProvider, historical_snapshot

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Variant:
    name: str
    bias_days: int = 0
    margin: str = 'none'
    quantile: float = 0.8
    controller: str = 'greedy'
    reserve_alpha: float = 0.0
    scenario_count: int = 0
    policy_history: int = 0


def prepare_forecasts(actuals, price):
    days = sorted(actuals.date.unique())
    n = len(days)
    cache = {k: np.full((n, 144), np.nan) for k in
             ['load', 'pv', 'legacy_margin', 'load_error', 'pv_error',
              'bias_load', 'bias_pv', 'bias_load_error', 'bias_pv_error']}
    metadata = [None] * n
    provider = ForecastProvider()
    for i, date in enumerate(days):
        if i == 0:
            continue
        cutoff = pd.Timestamp(date)
        history = historical_snapshot(actuals, cutoff)
        history['price_variable'] = price[history.interval_index.to_numpy()]
        bundle = provider.predict(history, cutoff)
        cache['load'][i], cache['pv'][i], cache['legacy_margin'][i] = bundle.load, bundle.pv, bundle.margin
        begin = max(1, i-3)
        for target in ['load', 'pv']:
            available = cache[target+'_error'][begin:i]
            correction = np.mean(available, axis=0) if len(available) else np.zeros(144)
            cache['bias_'+target][i] = np.maximum(cache[target][i]+correction, 0)
        metadata[i] = dict(bundle.metadata, bias_error_dates=list(days[begin:i]))
        completed = actuals.loc[actuals.date == date].copy()
        completed['price_variable'] = price
        for target in ['load', 'pv']:
            truth = completed[target+'_kwh'].to_numpy()
            cache[target+'_error'][i] = truth-cache[target][i]
            cache['bias_'+target+'_error'][i] = truth-cache['bias_'+target][i]
        provider.observe_completed_day(bundle, completed, price)
    return days, cache, metadata


def visible_packet(days, cache, metadata, index, variant):
    if index < 1:
        raise ValueError('No preceding complete day')
    if variant.bias_days not in (0, 3):
        raise ValueError('Only the preregistered zero/three-day bias versions are implemented')
    prefix = 'bias_' if variant.bias_days else ''
    window = variant.policy_history or (28 if variant.scenario_count or variant.margin == 'legacy' else 14)
    start = max(1, index-window)
    residual = cache[prefix+'load_error'][start:index]-cache[prefix+'pv_error'][start:index]
    available = pd.to_datetime(days[start:index])+pd.Timedelta(days=1)
    cutoff = pd.Timestamp(days[index])
    assert (available <= cutoff).all() and np.isfinite(residual).all()
    margin = np.zeros(144)
    if variant.margin == 'legacy':
        margin = cache['legacy_margin'][index].copy()
    elif variant.margin == 'hourly' and variant.quantile > 0 and len(residual):
        groups = residual.reshape(len(residual), 24, 6).transpose(1, 0, 2).reshape(24, -1)
        margin = np.repeat(np.maximum(np.quantile(groups, variant.quantile, axis=1), 0), 6)
    return dict(date=days[index], cutoff=cutoff, load=cache[prefix+'load'][index].copy(),
                pv=cache[prefix+'pv'][index].copy(), margin=margin,
                residual_days=residual.copy(), residual_available_at=available,
                metadata=dict(metadata[index], residual_first_date=days[start],
                              residual_last_date=days[index-1],
                              residual_days=len(residual), bias_corrected=bool(variant.bias_days),
                              margin_type=variant.margin,
                              margin_quantile=(metadata[index].get('margin_quantile') if variant.margin == 'legacy' else variant.quantile),
                              configured_quantile=variant.quantile,
                              attachment3_used=False))


def plan_packet(packet, variant, state, price, battery):
    if variant.policy_history:
        from q2_policy_saa import plan_greedy_saa
        initial = checked_optimization(packet['load']+packet['margin'], packet['pv'], price, state, battery)
        result = plan_greedy_saa(packet['load'],packet['pv'],price,packet['residual_days'],
            cutoff=packet['cutoff'],residual_available_at=packet['residual_available_at'],
            initial=state,battery=battery,initial_grid=initial['grid'],max_history_days=variant.policy_history)
        result['soc'] = np.full(145,state)
    elif variant.scenario_count:
        from q2_scenario import plan_day_block_scenarios
        result = plan_day_block_scenarios(packet['load'], packet['pv'], price,
            packet['residual_days'], cutoff=packet['cutoff'],
            residual_available_at=packet['residual_available_at'], initial=state,
            battery=battery, terminal=6000, n_scenarios=variant.scenario_count)
        result['soc'] = np.full(145, state)
    else:
        result = checked_optimization(packet['load']+packet['margin'], packet['pv'], price, state, battery)
    return result


def execute_plan(day, price, planned, initial, variant, battery):
    control = RealtimeController(battery)
    state, actions = float(initial), []
    future_peak = np.maximum.accumulate(price[::-1])[::-1]
    for t, row in enumerate(day.itertuples(index=False)):
        mode, target = variant.controller, planned['soc'][t+1]
        if mode == 'price_reserve':
            target = battery.minimum
            if price[t] < future_peak[t]-1e-9:
                target += variant.reserve_alpha*max(0, planned['soc'][t+1]-battery.minimum)
            mode = 'reference'
        action = control.act(state, row.load_kwh, row.pv_kwh, planned['grid'][t],
                             target, enabled=True, mode=mode)
        state = action['soc_end']
        actions.append(action)
    frame = day[['date', 'interval_index', 'interval_start', 'interval_end', 'load_kwh', 'pv_kwh']].reset_index(drop=True)
    frame = pd.concat([frame, pd.DataFrame(actions)], axis=1)
    frame['price'] = frame['plan_price'] = price
    frame['planned_grid'] = frame['contract_grid'] = planned['grid']
    frame['original_fee'] = price*planned['grid']
    frame['emergency_fee'] = 5*price*frame.emergency
    frame['total_fee'] = frame.original_fee+frame.emergency_fee
    for c in ['increase_fee', 'decrease_penalty', 'refund', 'contract_increase', 'contract_decrease']:
        frame[c] = 0.
    return frame, state


def simulate_variant(days, cache, metadata, day_frames, price, variant, start, end, battery):
    state, frames, decisions = 6000., [], []
    for i in range(start, end+1):
        packet = visible_packet(days, cache, metadata, i, variant)
        plan = plan_packet(packet, variant, state, price, battery)
        decision = dict(packet['metadata'], strategy=variant.name,
                        initial_soc=state, solver=plan['solver'], config=asdict(variant),
                        decision_type='day_ahead', changed_contract=False)
        frame, state = execute_plan(day_frames[i], price, plan, state, variant, battery)
        frames.append(frame)
        decisions.append(decision)
    frame = pd.concat(frames, ignore_index=True)
    daily, monthly, summary = aggregate(frame, battery)
    summary['strategy'] = asdict(variant)
    summary['contract_modification_decisions'] = 0
    summary['initial_soc_kwh'] = 6000.
    return frame, daily, monthly, summary, decisions


def save_variant(output, variant, result):
    frame, daily, monthly, summary, decisions = result
    destination = output/variant.name
    destination.mkdir(parents=True, exist_ok=False)
    frame.to_csv(destination/'intervals.csv.gz', index=False, compression='gzip')
    daily.to_csv(destination/'daily.csv')
    monthly.to_csv(destination/'monthly.csv')
    frame.loc[frame.date.isin(['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21'])].to_csv(destination/'display_days.csv', index=False)
    (destination/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (destination/'decisions.jsonl').write_text(''.join(json.dumps(x, default=str)+'\n' for x in decisions))
    pd.DataFrame(columns=['date','issue_time','effective_from','interval_index','increase_kwh',
                          'decrease_kwh','delivery_price','increase_fee','decrease_penalty','refund']).to_csv(destination/'events.csv', index=False)


def calibrate(days, cache, metadata, day_frames, price, battery, include_scenario, include_policy=False):
    begin, end = list(days).index('2025-01-15'), list(days).index('2025-01-31')
    table, selected, history = [], [], {}
    families = {
        'hourly_risk': [Variant(f'hourly_q{q:g}',margin='hourly',quantile=q) for q in [0., .65, .8, .9]],
        'bias_hourly_risk': [Variant(f'bias_hourly_q{q:g}',bias_days=3,margin='hourly',quantile=q) for q in [0., .65, .8, .9]]}
    def choose(family, variants):
        results = []
        for variant in variants:
            result = simulate_variant(days,cache,metadata,day_frames,price,variant,begin,end,battery)
            s=result[3]
            score=s['total_fee']-(s['terminal_soc_kwh']-6000)*price[-1]/battery.eta_charge
            table.append(dict(family=family,variant=asdict(variant),cost_yuan=s['total_fee'],
                              terminal_soc=s['terminal_soc_kwh'],selection_score_yuan=score))
            results.append((score,variant,result))
        _, winner, result=min(results,key=lambda x:x[0])
        chosen=replace(winner,name=family)
        selected.append(chosen)
        history[family]=result[1]
        return chosen
    base=choose('hourly_risk',families['hourly_risk'])
    choose('bias_hourly_risk',families['bias_hourly_risk'])
    choose('price_reserve',[replace(base,name=f'reserve_{a:g}',controller='price_reserve',reserve_alpha=a) for a in [0.,.25,.5]])
    if include_scenario:
        choose('scenario',[Variant(f'scenario_{n}',scenario_count=n) for n in [3,5]])
    if include_policy:
        choose('policy_saa',[Variant(f'policy_{n}',margin='legacy',policy_history=n) for n in [14,28]])
    return selected, table, history


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',required=True)
    ap.add_argument('--end-date',default='2025-12-31')
    ap.add_argument('--scenario',action='store_true')
    ap.add_argument('--policy',action='store_true')
    args=ap.parse_args()
    output=ROOT/args.output
    output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'data/processed/2026C/actuals.csv'
    actuals=pd.read_csv(source,parse_dates=['interval_start','interval_end','available_at'])
    actuals=actuals.loc[actuals.date<=args.end_date].copy()
    price=pd.read_csv(ROOT/'data/processed/2026C/q1.csv').price.to_numpy()
    config=json.loads((ROOT/'configs/2026c.json').read_text())
    battery=Battery(config['minimum_kwh'],config['maximum_kwh'],config['power_kw'],
                    config['efficiency_charge'],config['efficiency_discharge'],config['dt_hours'])
    tick=time.perf_counter()
    days,cache,metadata=prepare_forecasts(actuals,price)
    frames=[actuals.loc[actuals.date==d].copy() for d in days]
    np.savez_compressed(output/'forecast_cache.npz',days=days,**cache)
    selected,calibration,_=calibrate(days,cache,metadata,frames,price,battery,args.scenario,args.policy)
    (output/'january_calibration.json').write_text(json.dumps(calibration,indent=2)+'\n')
    chosen=min(selected,key=lambda v:min(r['selection_score_yuan'] for r in calibration if r['family']==v.name)).name
    selection=dict(cutoff='2025-02-01T00:00:00',start='2025-01-15',end='2025-01-31',
                   selected_variants=[asdict(v) for v in selected],deployment_family=chosen,
                   criterion='January cost less terminal replacement-energy credit; all parameters frozen before February evaluation',
                   retrospective_development=True)
    (output/'selected_parameters.json').write_text(json.dumps(selection,indent=2)+'\n')
    baselines=[Variant('legacy_point_reference',controller='reference'),
               Variant('legacy_margin_reference',margin='legacy',controller='reference'),
               Variant('legacy_margin_greedy',margin='legacy'),Variant('point_greedy'),
               Variant('bias_only_greedy',bias_days=3)]
    summary={}
    start=list(days).index('2025-02-01')
    print(json.dumps({'selected':selection,'phase':'parameters_frozen','elapsed':time.perf_counter()-tick}),flush=True)
    for variant in baselines+selected:
        result=simulate_variant(days,cache,metadata,frames,price,variant,start,len(days)-1,battery)
        save_variant(output,variant,result)
        summary[variant.name]=result[3]
        print(json.dumps({'strategy':variant.name,'cost':result[3]['total_fee'],'emergency':result[3]['emergency'],'seconds':round(time.perf_counter()-tick,2)}),flush=True)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    code=[Path(__file__),ROOT/'src/dispatch.py',ROOT/'src/backtest.py',ROOT/'src/forecasting.py']
    if args.scenario:code.append(ROOT/'src/q2_scenario.py')
    if args.policy:code.append(ROOT/'src/q2_policy_saa.py')
    snap=output/'source_snapshot';snap.mkdir()
    for file in code:shutil.copy2(file,snap/file.name)
    provenance=dict(run_id=output.name,created_utc=datetime.now(timezone.utc).isoformat(),
                    args=vars(args),config=config,elapsed_seconds=time.perf_counter()-tick,
                    git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                    dirty_worktree=True,seed=2026,
                    january_actual='battery disabled at 6000; calibration is a separate virtual replay',
                    realtime='ideal within-interval average-power feedback, not future integral visible at interval start',
                    scenario='scenario recourse is optimistic planning proxy, executed contract uses separate greedy control',
                    files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in code+[source,ROOT/'data/processed/2026C/q1.csv']})
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')


if __name__=='__main__':main()
