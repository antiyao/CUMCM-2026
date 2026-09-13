from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from microgrid import ROOT, ValueBattery, daily_plan, greedy_step, close_plan, execute_close
from microgrid import build_midnight_value_table, execute_midnight_value_policy, load_verified_input
from microgrid import export_annual

METHODS=('previous','weekly','ridge')
TARGETS=('load','pv')
KEYS=['date','slot']

def configuration():
    return dict(methods=METHODS,ridge_alpha=10.,history_days=60,bias_days=3,residual_days=14,risk_quantile=.8)

def normalize_actual_records(data):
    if isinstance(data, pd.DataFrame):
        frame = data.copy()
    elif 'records' in data:
        frame = pd.DataFrame(data['records']).copy()
    else:
        dates = np.asarray(data['dates']).astype(str)
        (load, pv) = (np.asarray(data['actual_load']), np.asarray(data['actual_pv']))
        if load.shape != (len(dates), 144) or pv.shape != load.shape:
            raise ValueError('actual array shape must be (number of dates, 144)')
        frame = pd.DataFrame({'date': np.repeat(dates, 144), 'slot': np.tile(np.arange(144), len(dates)), 'load_kw': load.ravel(), 'pv_kw': pv.ravel()})
    required = KEYS + ['load_kw', 'pv_kw']
    if set(required) - set(frame):
        raise ValueError(f'missing columns: {set(required) - set(frame)}')
    frame = frame[required].copy()
    frame['date'] = pd.to_datetime(frame.date, errors='raise').dt.strftime('%Y-%m-%d')
    slots = pd.to_numeric(frame.slot, errors='raise').to_numpy(dtype=float)
    if not np.isfinite(slots).all() or np.any(slots != np.floor(slots)) or np.any((slots < 0) | (slots > 143)):
        raise ValueError('slot must be an integer in 0..143')
    frame['slot'] = slots.astype(int)
    if frame.duplicated(KEYS).any():
        raise ValueError('duplicate actual date+slot key')
    values = frame[['load_kw', 'pv_kw']].to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any(values < 0):
        raise ValueError('actual load/PV must be finite and nonnegative')
    frame[['load_kw', 'pv_kw']] = values
    frame = frame.sort_values(KEYS).reset_index(drop=True)
    dates = frame.date.unique()
    if not len(dates):
        raise ValueError('empty history')
    expected_dates = pd.date_range(dates[0], dates[-1], freq='D').strftime('%Y-%m-%d').to_numpy()
    if not np.array_equal(dates, expected_dates):
        raise ValueError('missing calendar day')
    expected_keys = pd.MultiIndex.from_product([dates, np.arange(144)], names=KEYS)
    if not pd.MultiIndex.from_frame(frame[KEYS]).equals(expected_keys):
        raise ValueError('missing actual date+slot key')
    return frame

def align_residual_records(actual, forecast):
    if actual.duplicated(KEYS).any() or forecast.duplicated(KEYS).any():
        raise ValueError('duplicate actual or forecast date+slot key')
    joined = actual.merge(forecast, on=KEYS, how='outer', validate='one_to_one', indicator=True)
    if not (joined['_merge'] == 'both').all():
        raise ValueError('missing or extra actual/forecast date+slot key')
    joined = joined.drop(columns='_merge').sort_values(KEYS).reset_index(drop=True)
    for name in TARGETS:
        joined[f'actual_{name}_kwh'] = joined[f'{name}_kw'] / 6.0
        joined[f'base_error_{name}_kwh'] = joined[f'actual_{name}_kwh'] - joined[f'base_{name}_kwh']
    joined['corrected_net_error_kwh'] = joined.actual_load_kwh - joined.actual_pv_kwh - joined.corrected_load_kwh + joined.corrected_pv_kwh
    numeric = joined.select_dtypes(include=[np.number]).to_numpy()
    if not np.isfinite(numeric).all():
        raise ValueError('nonfinite residual inputs')
    return joined

def features_for_day(history_kwh, date):
    history = np.asarray(history_kwh, dtype=float)
    if history.ndim != 3 or history.shape[1:] != (144, 2):
        raise ValueError('history must have shape (days,144,2)')
    if len(history) == 0:
        return np.zeros((144, 2, 9))
    previous = history[-1]
    weekly = history[-7] if len(history) >= 7 else history[0]
    recent = history[-7:].mean(axis=0)
    phase = 2 * np.pi * np.arange(144) / 144
    shared = np.column_stack([np.sin(phase), np.cos(phase), np.sin(2 * phase), np.cos(2 * phase), np.full(144, pd.Timestamp(date).dayofweek >= 5)])
    return np.stack([np.column_stack([previous[:, k], weekly[:, k], recent[:, k], np.full(144, previous[:, k].mean()), shared]) for k in range(2)], axis=1)

def build_predictions(data):
    records = normalize_actual_records(data)
    dates = records.date.unique()
    nd = len(dates)
    actual = records[['load_kw', 'pv_kw']].to_numpy().reshape(nd, 144, 2) / 6.0
    candidates = np.zeros((nd, 3, 144, 2))
    base = np.zeros((nd, 144, 2))
    corrected = np.zeros_like(base)
    bias = np.zeros_like(base)
    margin = np.zeros((nd, 144))
    scores = np.zeros((nd, 3, 2))
    selected = np.zeros((nd, 2), dtype=int)
    candidate_mse = np.zeros((nd, 3, 2))
    base_errors = np.zeros_like(base)
    net_errors = np.zeros((nd, 144))
    (daily_info, completed, features) = ([], [], [])
    with threadpool_limits(limits=1):
        for (d, date) in enumerate(dates):
            feature_today = features_for_day(actual[:d], date)
            features.append(feature_today)
            if d:
                candidates[d, 0] = actual[d - 1]
                candidates[d, 1] = actual[d - 7] if d >= 7 else actual[0]
                candidates[d, 2] = actual[max(0, d - 7):d].mean(axis=0)
            training_dates = []
            if d >= 9:
                training_dates = list(range(max(7, d - 60), d))
                for target in range(2):
                    xtrain = np.concatenate([features[j][:, target] for j in training_dates])
                    ytrain = actual[training_dates, :, target].ravel()
                    scaler = StandardScaler().fit(xtrain)
                    model = Ridge(alpha=10.0, fit_intercept=True, solver='cholesky')
                    model.fit(scaler.transform(xtrain), ytrain)
                    candidates[d, 2, :, target] = np.maximum(model.predict(scaler.transform(feature_today[:, target])), 0.0)
            if d:
                scores[d] = candidate_mse[max(0, d - 14):d].mean(axis=0)
                selected[d] = scores[d].argmin(axis=0)
                bias[d] = base_errors[max(0, d - 3):d].mean(axis=0)
                for hour in range(24):
                    samples = net_errors[max(0, d - 14):d, hour * 6:hour * 6 + 6].ravel()
                    margin[d, hour * 6:hour * 6 + 6] = max(0.0, float(np.quantile(samples, 0.8, method='linear')))
            for target in range(2):
                base[d, :, target] = candidates[d, selected[d, target], :, target]
            corrected[d] = np.maximum(base[d] + bias[d], 0.0)
            predicted = pd.DataFrame({'date': date, 'slot': np.arange(144), 'forecast_available_at': date + ' 00:00:00', 'residual_available_at': (pd.Timestamp(date) + pd.Timedelta(days=1)).isoformat(), 'base_load_kwh': base[d, :, 0], 'base_pv_kwh': base[d, :, 1], 'corrected_load_kwh': corrected[d, :, 0], 'corrected_pv_kwh': corrected[d, :, 1], 'bias_load_kwh': bias[d, :, 0], 'bias_pv_kwh': bias[d, :, 1], 'margin_kwh': margin[d], 'residual_samples_per_hour': min(d, 14) * 6})
            for (m, method) in enumerate(METHODS):
                for (target, name) in enumerate(TARGETS):
                    predicted[f'{method}_{name}_kwh'] = candidates[d, m, :, target]
            actual_day = records.loc[records.date == date]
            aligned = align_residual_records(actual_day, predicted)
            for (target, name) in enumerate(TARGETS):
                base_errors[d, :, target] = aligned[f'base_error_{name}_kwh']
                for (m, method) in enumerate(METHODS):
                    candidate_mse[d, m, target] = np.mean((aligned[f'{method}_{name}_kwh'] - aligned[f'actual_{name}_kwh']) ** 2)
            net_errors[d] = aligned.corrected_net_error_kwh
            completed.append(aligned)
            daily_info.append({'date': date, 'decision_at': date + ' 00:00:00', 'latest_observed_date': None if d == 0 else str(dates[d - 1]), 'load_method': METHODS[selected[d, 0]], 'pv_method': METHODS[selected[d, 1]], 'mse_completed_days': min(d, 14), 'bias_completed_days': min(d, 3), 'risk_completed_days': min(d, 14), 'risk_samples_per_hour': min(d, 14) * 6, 'ridge_training_dates': [str(dates[j]) for j in training_dates], 'candidate_mse_kwh2': {method: {name: float(scores[d, m, k]) for (k, name) in enumerate(TARGETS)} for (m, method) in enumerate(METHODS)}})
    digest = hashlib.sha256(records.to_csv(index=False, float_format='%.17g').encode()).hexdigest()
    return {'dates': dates, 'base_kwh': base, 'corrected_kwh': corrected, 'bias_kwh': bias, 'margin_kwh': margin, 'candidate_kwh': candidates, 'selection_mse_kwh2': scores, 'selected_method_indices': selected, 'base_errors_kwh': base_errors, 'corrected_net_errors_kwh': net_errors, 'records': pd.concat(completed, ignore_index=True), 'daily_info': daily_info, 'actual_records_sha256': digest, 'config': configuration()}

def fixed_candidate_packet(packet: dict, actual_kwh: np.ndarray, method: str='ridge', risk_quantile: float=0.8) -> dict:
    if method not in METHODS:
        raise ValueError(f'unknown method {method!r}')
    actual = np.asarray(actual_kwh, dtype=float)
    candidates = np.asarray(packet['candidate_kwh'], dtype=float)
    if actual.shape != candidates.shape[:1] + candidates.shape[2:]:
        raise ValueError('actual and candidate shapes do not agree')
    method_index = METHODS.index(method)
    base = candidates[:, method_index].copy()
    corrected = np.zeros_like(base)
    bias = np.zeros_like(base)
    base_errors = np.zeros_like(base)
    net_errors = np.zeros(base.shape[:2], dtype=float)
    margin = np.zeros(base.shape[:2], dtype=float)
    for day in range(len(base)):
        if day:
            bias[day] = base_errors[max(0, day - 3):day].mean(axis=0)
            for hour in range(24):
                samples = net_errors[max(0, day - 14):day, hour * 6:hour * 6 + 6].reshape(-1)
                margin[day, hour * 6:hour * 6 + 6] = max(0.0, float(np.quantile(samples, risk_quantile, method='linear')))
        corrected[day] = np.maximum(base[day] + bias[day], 0.0)
        base_errors[day] = actual[day] - base[day]
        net_errors[day] = actual[day, :, 0] - actual[day, :, 1] - corrected[day, :, 0] + corrected[day, :, 1]
    result = copy.copy(packet)
    result.update({'base_kwh': base, 'corrected_kwh': corrected, 'bias_kwh': bias, 'margin_kwh': margin, 'base_errors_kwh': base_errors, 'corrected_net_errors_kwh': net_errors, 'forecast_family': f'fixed_{method}'})
    return result

def build_prediction_packet(data: dict, forecast_family: str) -> dict:
    selected = build_predictions(data)
    if forecast_family == 'rolling_selector':
        selected['forecast_family'] = forecast_family
        return selected
    if forecast_family == 'fixed_ridge':
        actual = np.stack([np.asarray(data['actual_load'], dtype=float) / 6.0, np.asarray(data['actual_pv'], dtype=float) / 6.0], axis=-1)
        return fixed_candidate_packet(selected, actual, 'ridge', 0.8)
    raise ValueError('forecast_family must be rolling_selector or fixed_ridge')

def moving_block_interval(delta: np.ndarray, *, block_days: int=7, repetitions: int=10000, seed: int=2026) -> dict:
    values = np.asarray(delta, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(values)
    starts = np.arange(n - block_days + 1)
    draws = np.empty(repetitions)
    blocks_needed = int(np.ceil(n / block_days))
    for i in range(repetitions):
        chosen = rng.choice(starts, size=blocks_needed, replace=True)
        sample = np.concatenate([values[s:s + block_days] for s in chosen])[:n]
        draws[i] = sample.sum()
    return {'observed_yuan': float(values.sum()), 'ci95_yuan': [float(x) for x in np.quantile(draws, [0.025, 0.975])], 'probability_positive': float(np.mean(draws > 0)), 'block_days': block_days, 'repetitions': repetitions, 'seed': seed}

def metrics(packet: dict, actual: np.ndarray, mask: np.ndarray) -> dict:
    err = np.asarray(packet['corrected_kwh'])[mask] - actual[mask]
    return {target: {'rmse_kwh': float(np.sqrt(np.mean(err[:, :, index] ** 2))), 'mae_kwh': float(np.mean(np.abs(err[:, :, index])))} for (index, target) in enumerate(('load', 'pv'))}

def _q2_kernels(packet: dict, day: int, slots) -> list[np.ndarray]:
    result = []
    for slot in slots:
        hour = int(slot) // 6
        sample = packet['corrected_net_errors_kwh'][max(0, day - 14):day, hour * 6:hour * 6 + 6].reshape(-1)
        result.append(sample.copy() if len(sample) else np.zeros(1))
    return result

def _terminal_kappa(data: dict, day: int, decision_price: np.ndarray, battery: ValueBattery, *, variable_price: bool) -> float:
    if day == len(data['dates']) - 1:
        return 0.0
    if not variable_price:
        return float(np.min(decision_price) / battery.eta_c)
    if day:
        historical_min = np.min(data['actual_price'][max(0, day - 14):day], axis=1)
        return float(np.median(historical_min) / battery.eta_c)
    return float(np.min(decision_price) / battery.eta_c)

def simulate(data, packet, controller='value_dp', common_closure=False,
             price_forecast=None, grid_step_kwh=50., risk_quantile=.8, fixed_plans=None):
    dates=np.asarray(data['dates']).astype(str)
    battery=ValueBattery()
    state=battery.target
    rows=[]
    for day, date_value in enumerate(dates):
        date=str(date_value)
        january=pd.Timestamp(date).month==1
        settle=(np.asarray(data['actual_price'][day],dtype=float) if price_forecast is not None
                else np.asarray(data['q1_price'],dtype=float))
        price=(np.asarray(price_forecast[day],dtype=float) if price_forecast is not None else settle.copy())
        load_point=packet['corrected_kwh'][day,:,0]
        pv_point=packet['corrected_kwh'][day,:,1]
        kernels=_q2_kernels(packet,day,range(144))
        margin=np.asarray([max(0.,float(np.quantile(x,risk_quantile,method='linear'))) for x in kernels])
        if fixed_plans is not None:
            plan=np.asarray(fixed_plans[date],dtype=float).copy()
        elif january:
            plan=np.maximum(load_point+margin-pv_point,0.)
        else:
            plan=daily_plan(np.column_stack([load_point,pv_point]),margin,price,state,battery)['q']
        if common_closure and day==len(dates)-1 and fixed_plans is None:
            plan=close_plan(plan,data,day,battery=battery,close_slots=8)
        policy=None
        if controller=='value_dp' and not january:
            kappa=_terminal_kappa(data,day,price,battery,variable_price=price_forecast is not None)
            policy,_=build_midnight_value_table(plan,load_point-pv_point,kernels,price,
                battery=battery,step_kwh=grid_step_kwh,terminal_kappa=kappa,start_slot=0)
        for slot in range(144):
            load=float(data['actual_load'][day,slot]/6.)
            pv=float(data['actual_pv'][day,slot]/6.)
            if january:
                charge=discharge=0.;nxt=state
                emergency=max(load-pv-plan[slot],0.)
                surplus=max(plan[slot]+pv-load,0.)
            elif common_closure and day==len(dates)-1 and slot>=136:
                charge,discharge,nxt,emergency,surplus=execute_close(plan[slot],load,pv,state,battery=battery)
            elif controller=='greedy':
                charge,discharge,nxt,emergency,surplus=greedy_step(plan[slot],load,pv,state,battery)
            else:
                action,_=execute_midnight_value_policy(plan[slot],load,pv,state,price[slot],
                    policy.next_values(slot),policy.grid,battery=battery)
                charge,discharge,nxt,emergency,surplus=[action[k] for k in ('charge','discharge','soc_end','emergency','surplus')]
            cp=plan[slot]*settle[slot];ce=5.*settle[slot]*emergency
            rows.append(dict(date=date,slot=slot,load=load,pv=pv,price=settle[slot],decision_price=price[slot],
                plan=plan[slot],adjusted=plan[slot],up=0.,down=0.,emergency=emergency,charge=charge,
                discharge=discharge,soc_start=state,soc_end=nxt,surplus=surplus,cost_plan=cp,
                cost_up=0.,cost_down=0.,cost_emergency=ce,cost_total=cp+ce,reference_soc=np.nan))
            state=nxt
    return pd.DataFrame(rows)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=ROOT/'data/processed/annual_inputs.npz')
    parser.add_argument('--actuals',type=Path,default=ROOT/'data/processed/actuals_power.csv')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--checks',action='store_true')
    args=parser.parse_args()
    data=load_verified_input(args.input,args.actuals)
    packet=build_prediction_packet(data,'fixed_ridge')
    frame=simulate(data,packet)
    summary=export_annual(frame,args.out,dict(question='q2',controller='value_dp',forecast='fixed_ridge'))
    if args.checks:
        greedy=simulate(data,packet,'greedy')
        fixed={date:part.plan.to_numpy() for date,part in greedy.groupby('date',sort=True)}
        grid_results={}
        for step in (100.,50.,25.):
            trial=simulate(data,packet,fixed_plans=fixed,grid_step_kwh=step)
            grid_results[str(step)]=export_annual(trial,args.out/f'grid_{step:g}',dict(grid_step_kwh=step,fixed_plan=True))
        export_annual(greedy,args.out/'greedy',dict(controller='greedy'))
        (args.out/'grid_comparison.json').write_text(json.dumps(grid_results,indent=2))
        comparison=[]
        for controller in ('greedy','value_dp'):
            candidate=simulate(data,packet,controller,True)
            daily=candidate[candidate.date>='2025-02-01'].groupby('date').cost_total.sum()
            comparison.append(daily)
        interval=moving_block_interval((comparison[0]-comparison[1]).to_numpy())
        (args.out/'controller_comparison.json').write_text(json.dumps(interval,indent=2))
        selected=build_prediction_packet(data,'rolling_selector')
        selected_frame=simulate(data,selected,common_closure=True)
        export_annual(selected_frame,args.out/'forecast_comparison',dict(forecast='rolling_selector'))
        selected_daily=selected_frame[selected_frame.date>='2025-02-01'].groupby('date').cost_total.sum()
        forecast_interval=moving_block_interval((selected_daily-comparison[1]).to_numpy())
        (args.out/'forecast_comparison.json').write_text(json.dumps(forecast_interval,indent=2))
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
