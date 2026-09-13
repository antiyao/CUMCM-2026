from __future__ import annotations
import argparse
import json
import tempfile
import warnings
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from microgrid import ROOT,Battery,ValueBattery,optimize,daily_plan,AdjustmentLedger,replan,aggregate,load_verified_input
from microgrid import build_rolling_value_table,execute_rolling_value_policy
from problem2 import build_prediction_packet,simulate,moving_block_interval
from problem3 import Candidate,ordered_actuals,prepare as prepare_q3,base_prediction,ForecastProvider
from microgrid import export_annual

FEATURE_COLUMNS = ([0, 1, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14], [0, 1, 3, 4, 6, 7, 9, 10, 11, 12, 13, 14], [2, 5, 8, 9, 10, 11, 12, 13, 14])

def baseline(history, fallback, day, method='recent', lead=0):
    if day == 0:
        return np.asarray(fallback).copy()
    if method == 'previous':
        return history[day - 1].copy()
    same_weekday = [j for j in range(max(0, day - 28), day) if (day + lead - j) % 7 == 0]
    seasonal = history[same_weekday[-3:]].mean(axis=0) if same_weekday else history[max(0, day - 7):day].mean(axis=0)
    if method == 'weekly':
        return seasonal
    return 0.5 * seasonal + 0.5 * history[max(0, day - 7):day].mean(axis=0)

def features(history, fallback, day, lead=0):
    slot = np.arange(144)
    prev = baseline(history, fallback, day, 'previous', lead)
    week = baseline(history, fallback, day, 'weekly', lead)
    recent = baseline(history, fallback, day, 'recent', lead)
    return np.column_stack([prev, week, recent, np.sin(2 * np.pi * slot / 144), np.cos(2 * np.pi * slot / 144), np.full(144, (day + lead + 2) % 7), np.full(144, np.sin(2 * np.pi * (day + lead) / 365)), np.full(144, np.cos(2 * np.pi * (day + lead) / 365)), np.full(144, lead)])

def build_forecasts(actual, fallback, method='recent', days=None):
    nd = len(actual) if days is None else min(days, len(actual))
    result = np.zeros((nd, 3, 144, 3))
    models = None
    fitted_at = []
    with threadpool_limits(limits=1):
        for d in range(nd):
            if method == 'hgb' and d >= 14 and (models is None or d % 7 == 0):
                origins = range(max(1, d - 60), d - 2)
                xx = np.vstack([features(actual, fallback, j, lead) for j in origins for lead in (0, 1, 2)])
                yy = np.vstack([actual[j + lead] for j in origins for lead in (0, 1, 2)])
                models = []
                for k in range(3):
                    reg = HistGradientBoostingRegressor(max_iter=60, max_leaf_nodes=15, learning_rate=0.08, l2_regularization=1.0, random_state=2026, early_stopping=False)
                    reg.fit(xx[:, FEATURE_COLUMNS[k]], yy[:, k])
                    models.append(reg)
                fitted_at.append(d)
            for lead in range(3):
                if method != 'hgb' or models is None:
                    y = baseline(actual, fallback, d, 'recent' if method == 'hgb' else method, lead)
                else:
                    x = features(actual, fallback, d, lead)
                    y = np.column_stack([reg.predict(x[:, FEATURE_COLUMNS[k]]) for (k, reg) in enumerate(models)])
                result[d, lead] = np.maximum(y, 0)
                result[d, lead, :, 2] = np.maximum(result[d, lead, :, 2], 0.001)
    return (result, fitted_at)

def predict_prices(dates, prices, return_candidates=False):
    dates = [str(date) for date in dates]
    prices = np.asarray(prices, dtype=float)
    if prices.shape != (len(dates), 144) or not np.isfinite(prices).all() or np.any(prices <= 0):
        raise ValueError('Expected complete positive daily price arrays')
    names = ('previous', 'weekly', 'ridge')
    candidates = np.full((len(dates), 3, 144), np.nan)
    prediction = np.full_like(prices, np.nan)
    losses = np.full((len(dates), 3), np.nan)
    records = []
    with threadpool_limits(limits=1):
        for d in range(1, len(dates)):
            candidates[d, 0] = prices[d - 1]
            candidates[d, 1] = prices[max(0, d - 7)]
            candidates[d, 2] = prices[max(0, d - 7):d].mean(axis=0)
            if d >= 9:
                indices = range(max(7, d - 60), d)
                x = np.vstack([ForecastProvider._features(prices, dates, j) for j in indices])
                y = prices[list(indices)].ravel()
                scaler = StandardScaler().fit(x)
                model = Ridge(alpha=10.0, solver='cholesky').fit(scaler.transform(x), y)
                candidates[d, 2] = model.predict(scaler.transform(ForecastProvider._features(prices, dates, d)))
            candidates[d] = np.maximum(candidates[d], 1e-06)
            begin = max(1, d - 14)
            scores = losses[begin:d].mean(axis=0) if d > 1 else np.zeros(3)
            chosen = int(np.argmin(scores)) if d > 1 else 1
            prediction[d] = candidates[d, chosen]
            records.append(dict(date=str(dates[d]), cutoff=str(dates[d]) + 'T00:00:00', latest_observed_date=str(dates[d - 1]), selected=names[chosen], selection_days=d - begin, scores=dict(zip(names, scores.tolist()))))
            losses[d] = np.mean((candidates[d] - prices[d]) ** 2, axis=1)
    rows = []
    mask = np.asarray(dates) >= '2025-02-01'
    for (name, forecast) in [('selected', prediction)] + [(name, candidates[:, j]) for (j, name) in enumerate(names)]:
        error = forecast[mask] - prices[mask]
        rows.append(dict(method=name, mae_yuan_per_kwh=float(np.abs(error).mean()), rmse_yuan_per_kwh=float(np.sqrt(np.mean(error ** 2)))))
    result = (prediction, records, pd.DataFrame(rows))
    return (*result, candidates) if return_candidates else result

def price_family(dates, truth):
    (selected, records, metrics, candidates) = predict_prices(dates, truth, return_candidates=True)
    ridge = candidates[:, 2]
    smooth = np.repeat(ridge.reshape(-1, 24, 6).mean(axis=2), 6, axis=1)
    profile = np.full_like(selected, np.nan)
    for day in range(1, len(dates)):
        history = truth[max(0, day - 28):day]
        shape = (history / history.mean(axis=1, keepdims=True)).mean(axis=0)
        profile[day] = shape * ridge[day].mean()
    return (dict(selected=selected, ridge=ridge, smooth_ridge=smooth, weekly=candidates[:, 1], profile=profile), records, metrics)

def decision_prices(family, truth, day, begin, method, bias_weight=0.0, bias_window=3, feedback=0.0):
    base = family[method][day].copy()
    if bias_weight and day > 1:
        first = max(1, day - bias_window)
        base += bias_weight * (truth[first:day] - family[method][first:day]).mean(axis=0)
    base = np.maximum(base, 1e-06)
    if begin and feedback:
        offset = float(np.mean(truth[day, max(0, begin - 12):begin] - base[max(0, begin - 12):begin]))
        base[begin:] += feedback * offset * np.exp(-np.arange(144 - begin) / 36)
    return np.maximum(base[begin:], 1e-06)

@dataclass(frozen=True)
class Policy:
    part: str
    price_method: str = 'selected'
    bias_weight: float = 0.0
    bias_window: int = 3
    price_feedback: float = 0.0
    risk: float = 0.8
    intraday_risk: float = 0.625
    residual_days: int = 14
    price_weighted_margin: bool = False
    plan_terminal: float = 6000.0
    terminal_weight: float = 1.0
    discount: float = 1.0
    grid_step: float = 50.0
    final_depletion: bool = False

def default_policy(part):
    if part == '2':
        return Policy(part='2')
    return Policy(part='3', risk=0.65, residual_days=56, plan_terminal=2400.0, terminal_weight=1.5, discount=0.95)

def margins_and_kernels(cache, policy, day, issue):
    begin = issue * 36
    first = max(1, day - policy.residual_days)
    errors = cache['errors'][first:day, issue, begin:]
    groups = errors.reshape(len(errors), -1, 6).transpose(1, 0, 2).reshape((144 - begin) // 6, -1)
    risk = policy.intraday_risk if issue else policy.risk
    if policy.price_weighted_margin:
        weights = cache['truth_price'][first:day, begin:].reshape(len(errors), -1, 6).transpose(1, 0, 2).reshape(groups.shape)
        values = []
        for (samples, w) in zip(groups, weights):
            order = np.argsort(samples, kind='stable')
            values.append(np.interp(risk, (np.cumsum(w[order]) - 0.5 * w[order]) / w.sum(), samples[order]))
        margin = np.repeat(np.maximum(values, 0), 6)
    else:
        margin = np.repeat(np.maximum(np.quantile(groups, risk, axis=1), 0), 6)
    return (margin, [groups[t // 6] for t in range(144 - begin)])

def run(cache, family, policy, start=31, stop=None, collect=False, progress=False, initial_soc=6000.0):
    dates = cache['dates']
    stop = len(dates) if stop is None else stop
    state = float(initial_soc)
    total = 0.0
    emergency_total = 0.0
    frames = []
    logs = []
    event_rows = []
    daily_rows = []
    physical = Battery()
    value_battery = ValueBattery()
    for day in range(start, stop):
        date = str(dates[day])
        day_start = state
        last = policy.final_depletion and date == '2025-12-31'
        terminal = 1200.0 if last else policy.plan_terminal
        midnight = decision_prices(family, cache['truth_price'], day, 0, policy.price_method, policy.bias_weight, policy.bias_window)
        (margin, kernels) = margins_and_kernels(cache, policy, day, 0)
        forecast = cache['base'][day, 0]
        if policy.part == '2':
            planned = daily_plan(forecast, margin, midnight, state, replace(value_battery, target=terminal))
            q = planned['q']
            solver = dict(status=0, objective=planned['objective'], maximum_residual_kwh=planned['residual'])
        else:
            planned = optimize(forecast[:, 0] + margin, forecast[:, 1], midnight, initial=state, terminal=terminal, relax=True)
            if np.minimum(planned['charge'], planned['discharge']).max() > 1e-07:
                planned = optimize(forecast[:, 0] + margin, forecast[:, 1], midnight, initial=state, terminal=terminal)
            q = planned['grid']
            solver = planned['solver']
        if solver['status'] != 0:
            raise RuntimeError(solver)
        ledger = AdjustmentLedger(q, 'initial_final')
        control = midnight.copy()
        virtual = q.copy()
        actions = []
        update_times = (0, 36, 72, 108) if policy.part == '3' or policy.price_feedback else (0,)
        for t in range(144):
            if t in update_times:
                issue = t // 36
                prices = decision_prices(family, cache['truth_price'], day, t, policy.price_method, policy.bias_weight, policy.bias_window, policy.price_feedback)
                control[t:] = prices
                if t and policy.part == '3':
                    forecast = cache['base'][day, issue, t:]
                    (margin, kernels) = margins_and_kernels(cache, policy, day, issue)
                    proposed = replan(forecast[:, 0] + margin, forecast[:, 1], prices, ledger.original[t:], state, 1200.0 if last else 6000.0, physical, 0.0 if last else policy.terminal_weight)
                    target = ledger.contract.copy()
                    target[t:t + 36] = proposed['grid'][:36]
                    ledger.revise(target, t, pd.Timestamp(date) + pd.Timedelta(minutes=10 * t))
                    virtual = proposed['grid']
                    solver = proposed['solver']
                elif t:
                    forecast = cache['base'][day, 0, t:]
                    (_, all_kernels) = margins_and_kernels(cache, policy, day, 0)
                    kernels = all_kernels[t:]
                    virtual = ledger.contract[t:]
                kappa = 0.0 if last else policy.terminal_weight * float(prices.min()) / 0.9
                (vp, diag) = build_rolling_value_table(virtual, forecast[:, 0] - forecast[:, 1], kernels, prices, terminal_kappa=kappa, terminal_target_kwh=6000.0, step_kwh=policy.grid_step, start_slot=t, vectorized=True, value_discount=policy.discount)
                if collect:
                    cutoff = pd.Timestamp(date) + pd.Timedelta(minutes=10 * t)
                    logs.append(dict(date=date, cutoff=str(cutoff), issue_hour=t // 6, decision_type='day_ahead' if not t else 'intraday', initial_soc=state, solver=solver, last_calibration_date=str(dates[day - 1]), training_label_cutoff=str(pd.Timestamp(date)), value_function=diag, price_forecast=dict(method=policy.price_method, latest_observed_date=str(dates[day - 1]), feedback_through=str(cutoff) if t and policy.price_feedback else date + ' 00:00:00'), predicted_prices=prices.tolist(), control_start_interval=t, lookahead_stop_interval=144, control_stop_interval=min(t + 36, 144) if len(update_times) > 1 else 144, committed_until_interval=min(t + 36, 144) if policy.part == '3' and t else 144, virtual_tail_is_not_committed=policy.part == '3', final_depletion=last))
            load = cache['truth_load'][day, t]
            pv = cache['truth_pv'][day, t]
            (action, _) = execute_rolling_value_policy(ledger.contract[t], load, pv, state, control[t], vp.next_values(t), vp.grid, general_search=policy.part == '3')
            action['soc_start'] = state
            action['unused'] = action.pop('surplus')
            used_pv = min(pv, load + action['charge'])
            used_grid = min(ledger.contract[t], max(0.0, load + action['charge'] - used_pv - action['discharge']))
            action['unused_pv'] = pv - used_pv
            action['unused_purchased'] = ledger.contract[t] - used_grid
            state = action['soc_end']
            actions.append(action)
        emergency = np.array([a['emergency'] for a in actions])
        fees = ledger.settle(cache['truth_price'][day], emergency)
        amount = float(fees['total_fee'].sum())
        total += amount
        emergency_total += emergency.sum()
        daily_rows.append(dict(date=date, total_fee=amount, initial_soc=day_start, terminal_soc=state, emergency=float(emergency.sum())))
        if collect:
            times = pd.date_range(date, periods=144, freq='10min')
            frame = pd.DataFrame(dict(date=date, interval_index=np.arange(144), interval_start=times, interval_end=times + pd.Timedelta(minutes=10), load_kwh=cache['truth_load'][day], pv_kwh=cache['truth_pv'][day], price=cache['truth_price'][day], plan_price=midnight, control_price=control, planned_grid=ledger.original, contract_grid=ledger.contract))
            frame = pd.concat([frame, pd.DataFrame(actions)], axis=1)
            for (key, values) in fees.items():
                frame[key] = values
            frames.append(frame)
            for event in ledger.events:
                for k in np.flatnonzero(event['increase'] + event['decrease'] > 1e-07):
                    event_rows.append(dict(date=date, issue_time=event['issue_time'], effective_from=event['effective_from'], interval_index=int(k), increase_kwh=float(event['increase'][k]), decrease_kwh=float(event['decrease'][k]), delivery_price=float(cache['truth_price'][day, k]), increase_fee=float(1.5 * cache['truth_price'][day, k] * event['increase'][k]), decrease_penalty=float(0.5 * cache['truth_price'][day, k] * event['decrease'][k]), refund=float(cache['truth_price'][day, k] * event['decrease'][k])))
        if progress and (day == stop - 1 or str(dates[day + 1])[:7] != date[:7]):
            print(json.dumps(dict(part=policy.part, completed=date, total_fee=total)), flush=True)
    if not collect:
        return dict(total_fee=total, terminal_soc=state, emergency=emergency_total, daily=daily_rows)
    frame = pd.concat(frames, ignore_index=True)
    (daily, monthly, summary) = aggregate(frame, physical)
    summary.update(strategy=dict(**asdict(policy), question='Q4-' + policy.part, reference_mode='initial_final', interpretation='B', adjustment='next6' if policy.part == '3' else 'none', controller='empirical_dp'), optimality='Fixed empirical-DP policy; no global online optimality certificate', submission_ready=False)
    return (frame, daily, monthly, summary, logs, pd.DataFrame(event_rows, columns=['date', 'issue_time', 'effective_from', 'interval_index', 'increase_kwh', 'decrease_kwh', 'delivery_price', 'increase_fee', 'decrease_penalty', 'refund']))

def prepare_price_cache(part, output):
    if part != '3':
        raise ValueError('Only final Q4-3 cache preparation is supported')
    actual = ordered_actuals(pd.read_csv(ROOT / 'data/processed/actuals_energy.csv', parse_dates=['interval_start', 'interval_end', 'available_at']))
    dates = np.asarray(actual.date.unique(), dtype=str)
    n = len(dates)
    base = np.full((n, 4, 144, 2), np.nan)
    cache = {'dates': dates, 'truth_load': actual.load_kwh.to_numpy().reshape(-1, 144), 'truth_pv': actual.pv_kwh.to_numpy().reshape(-1, 144), 'truth_price': actual.price_variable.to_numpy().reshape(-1, 144)}
    forecasts = pd.read_csv(ROOT / 'data/processed/pv_forecasts.csv', parse_dates=['issue_time', 'available_at', 'target_time'])
    tariff = pd.read_csv(ROOT / 'data/processed/q1_inputs.csv').sort_values('interval_index').price.to_numpy()
    with threadpool_limits(limits=1), warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        (_, q3cache, _) = prepare_q3(actual, forecasts, tariff)
        candidate = Candidate(**json.loads((ROOT / 'configs/q3_current.json').read_text())[0])
        for day in range(1, n):
            for issue in range(4):
                (load_prediction, pv_prediction) = base_prediction(q3cache, day, issue, candidate)
                base[day, issue, issue * 36:] = np.column_stack([load_prediction, pv_prediction])
    cache['base'] = base
    cache['errors'] = cache['truth_load'][:, None, :] - cache['truth_pv'][:, None, :] - base[:, :, :, 0] + base[:, :, :, 1]
    np.savez_compressed(output, **cache)

def load(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}

def price_forecasts(data):
    actual=np.stack([data['actual_load'],data['actual_pv'],data['actual_price']],axis=-1)
    fallback=np.zeros((144,3));fallback[:,2]=.5
    predicted,_=build_forecasts(actual,fallback,method='hgb')
    return predicted[:,0,:,2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--part',choices=['2','3'],required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--checks',action='store_true')
    args=parser.parse_args()
    data=load_verified_input(ROOT/'data/processed/annual_inputs.npz',ROOT/'data/processed/actuals_power.csv')
    predicted=price_forecasts(data)
    if args.part=='2':
        packet=build_prediction_packet(data,'fixed_ridge')
        frame=simulate(data,packet,price_forecast=predicted)
        summary=export_annual(frame,args.out,dict(question='q4_2',controller='value_dp',forecast='fixed_ridge'))
        if args.checks:
            checks=[]
            for controller in ('greedy','value_dp'):
                trial=simulate(data,packet,controller,True,price_forecast=predicted)
                checks.append(trial[trial.date>='2025-02-01'].groupby('date').cost_total.sum())
            (args.out/'controller_comparison.json').write_text(json.dumps(moving_block_interval((checks[0]-checks[1]).to_numpy()),indent=2))
    else:
        with tempfile.TemporaryDirectory() as temporary:
            cachefile=Path(temporary)/'forecast.npz';prepare_price_cache('3',cachefile);cache=load(cachefile)
        policy=Policy(part='3',price_method='hgb',risk=.65,intraday_risk=.625,residual_days=56,
                      plan_terminal=2400.,terminal_weight=1.5,discount=.95,grid_step=50.)
        with threadpool_limits(limits=1):result=run(cache,{'hgb':predicted},policy,collect=True,progress=True)
        summary=export_annual(result[0],args.out,asdict(policy),result[3])
        if args.checks:
            with threadpool_limits(limits=1):trial=run(cache,{'hgb':predicted},replace(policy,grid_step=25.),collect=True)
            export_annual(trial[0],args.out/'grid25',asdict(replace(policy,grid_step=25.)),trial[3])
    error=predicted[31:]-data['actual_price'][31:]
    (args.out/'price_metrics.json').write_text(json.dumps(dict(mae=float(np.abs(error).mean()),rmse=float(np.sqrt(np.mean(error**2)))),indent=2))
    if args.checks:
        price_family(data['dates'],data['actual_price'])[2].to_csv(args.out/'price_baselines.csv',index=False)
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
