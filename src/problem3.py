from __future__ import annotations
import argparse
import json
from pathlib import Path
from dataclasses import dataclass,asdict,replace
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from microgrid import ROOT,Battery,ValueBattery,optimize,AdjustmentLedger,replan,aggregate
from microgrid import build_rolling_value_table,execute_rolling_value_policy
from microgrid import export_annual

@dataclass(frozen=True)
class ForecastBundle:
    cutoff: pd.Timestamp
    load: np.ndarray
    pv: np.ndarray
    price: np.ndarray
    margin: np.ndarray
    metadata: dict
    candidates: dict

def historical_snapshot(actuals, cutoff):
    cutoff = pd.Timestamp(cutoff)
    return actuals.loc[actuals.available_at <= cutoff].copy(deep=True)

class ForecastProvider:

    def __init__(self, training_days=60, selection_days=14, calibration_days=28):
        self.training_days = training_days
        self.selection_days = selection_days
        self.calibration_days = calibration_days
        self.records = []

    @staticmethod
    def _features(values, dates, index):
        t = np.arange(144) / 144
        previous = values[index - 1]
        week = values[max(0, index - 7)]
        mean = values[max(0, index - 7):index].mean(axis=0)
        dow = pd.Timestamp(dates[index]).dayofweek
        return np.column_stack([previous, week, mean, np.full(144, previous.mean()), np.sin(2 * np.pi * t), np.cos(2 * np.pi * t), np.sin(4 * np.pi * t), np.cos(4 * np.pi * t), np.full(144, dow >= 5)])

    def predict(self, history, cutoff):
        cutoff = pd.Timestamp(cutoff)
        if len(history) and history.available_at.max() > cutoff:
            raise ValueError('History contains unavailable labels')
        history = history.loc[history.interval_end <= cutoff]
        day_counts = history.groupby('date').size()
        full_dates = day_counts.index[day_counts == 144]
        history = history.loc[history.date.isin(full_dates)].sort_values('interval_start')
        m = len(history) // 144
        if not m:
            raise ValueError('At least one completed day is required')
        columns = ['load_kwh', 'pv_kwh', 'price_variable']
        values = history[columns].to_numpy().reshape(m, 144, 3)
        dates = list(full_dates) + [cutoff.date().isoformat()]
        candidates = {'yesterday': values[-1].copy(), 'last_week': values[max(0, m - 7)].copy()}
        ridge = np.empty((144, 3))
        for k in range(3):
            v = values[:, :, k]
            if m >= 9:
                indices = range(max(7, m - self.training_days), m)
                x = np.vstack([self._features(v, dates, j) for j in indices])
                y = np.concatenate([v[j] for j in indices])
                scaler = StandardScaler().fit(x)
                model = Ridge(alpha=10.0).fit(scaler.transform(x), y)
                ridge[:, k] = model.predict(scaler.transform(self._features(v, dates, m)))
            else:
                ridge[:, k] = v[max(0, m - 7):].mean(axis=0)
        candidates['ridge'] = ridge
        for a in candidates.values():
            a[:, :2] = np.maximum(a[:, :2], 0)
            a[:, 2] = np.maximum(a[:, 2], max(1e-06, values[:, :, 2].min()))
        eligible = [r for r in self.records if r['available_at'] <= cutoff][-self.selection_days:]
        (selected, scores) = ([], {})
        for (k, col) in enumerate(columns):
            scores[col] = {name: float(np.mean([r['candidate_mse'][name][k] for r in eligible])) for name in candidates} if eligible else {name: None for name in candidates}
            selected.append(min(candidates, key=lambda n: scores[col][n]) if eligible else 'last_week')
        prediction = np.column_stack([candidates[name][:, k] for (k, name) in enumerate(selected)])
        (margin, quantile, validation_costs) = self._margin(cutoff)
        metadata = {'cutoff': cutoff.isoformat(), 'training_label_cutoff': history.available_at.max().isoformat(), 'training_days_available': m, 'training_window_days': self.training_days, 'selection_validation_days': len(eligible), 'selected': dict(zip(columns, selected)), 'candidate_mse': scores, 'margin_quantile': quantile, 'margin_validation_cost_proxy': validation_costs, 'ridge_alpha': 10.0, 'ridge_scaling': 'training-fold-only', 'attachment3_used': False}
        return ForecastBundle(cutoff, prediction[:, 0], prediction[:, 1], prediction[:, 2], margin, metadata, candidates)

    def _margin(self, cutoff):
        rows = [r for r in self.records if r['available_at'] <= cutoff][-self.calibration_days:]
        if not rows:
            return (np.zeros(144), 0.8, {})
        errors = np.vstack([r['net_residual'] for r in rows])
        prices = np.vstack([r['price'] for r in rows])
        levels = [0.5, 0.65, 0.8, 0.9, 0.95]
        groups = np.arange(144) // 24

        def fit(a, level):
            return np.array([max(0, np.quantile(a[:, groups == g], level)) for g in groups])
        costs = {}
        if len(rows) >= 14:
            (train, valid) = (errors[:-7], errors[-7:])
            for level in levels:
                b = fit(train, level)
                costs[str(level)] = float(np.mean(prices[-7:] * (b + 5 * np.maximum(valid - b, 0))))
            best = min(levels, key=lambda a: costs[str(a)])
        else:
            best = 0.8
        return (fit(errors, best), best, costs)

    def observe_completed_day(self, bundle, completed_actuals, settlement_price):
        if len(completed_actuals) != 144:
            raise ValueError('Only a complete labelled day may enter validation records')
        truth = completed_actuals[['load_kwh', 'pv_kwh', 'price_variable']].to_numpy()
        candidate_mse = {name: np.mean((x - truth) ** 2, axis=0).tolist() for (name, x) in bundle.candidates.items()}
        self.records.append({'available_at': completed_actuals.available_at.max(), 'candidate_mse': candidate_mse, 'net_residual': truth[:, 0] - truth[:, 1] - bundle.load + bundle.pv, 'price': np.asarray(settlement_price).copy()})

def issued_pv_integrals(released_forecasts, issue_time, lead_zero_kw):
    issue_time = pd.Timestamp(issue_time)
    if (released_forecasts.available_at > issue_time).any():
        raise ValueError('Unpublished forecasts supplied to the forecast interface')
    rows = released_forecasts.loc[released_forecasts.issue_time == issue_time].sort_values('lead_time')
    if list(rows.lead_time) != list(range(1, 25)):
        raise ValueError('One complete forecast issue with leads 1..24 is required')
    boundary_kw = np.interp(np.arange(145) / 6, np.arange(25), np.r_[max(0, lead_zero_kw), np.maximum(rows.value.to_numpy(), 0)])
    return (boundary_kw[:-1] + boundary_kw[1:]) / 12

def lookahead_value_policy(bundle, virtual_contract, candidate, battery, begin):
    vb = ValueBattery(lo=battery.minimum, hi=battery.maximum, power=battery.power_kw, eta_c=battery.eta_charge, eta_d=battery.eta_discharge)
    weight = candidate.terminal_weight if candidate.dp_terminal_weight is None else candidate.dp_terminal_weight
    target = candidate.terminal if candidate.rolling_terminal is None else candidate.rolling_terminal
    if not 0.0 <= candidate.future_error_scale <= 1.0:
        raise ValueError('Future residual scale must be in [0,1]')
    kernels = [samples if t < 36 else np.zeros(1) if candidate.future_error_scale == 0 else candidate.future_error_scale * samples for (t, samples) in enumerate(bundle['residual_kernels'])]
    (policy, diagnostics) = build_rolling_value_table(virtual_contract, bundle['load'] - bundle['pv'], kernels, bundle['price'], battery=vb, step_kwh=candidate.soc_step_kwh, terminal_kappa=weight * float(np.min(bundle['price'])) / battery.eta_charge, terminal_target_kwh=target, start_slot=begin, vectorized=True, value_discount=candidate.value_discount)
    info = dict(value_function=diagnostics, control_start_interval=begin, control_stop_interval=min(begin + 36, 144), lookahead_stop_interval=144, virtual_contract_scope='remaining_day_current_forecast_only', virtual_tail_is_not_committed=True, future_error_scale=candidate.future_error_scale, value_assumption='Future virtual contracts held fixed within this value evaluation; recomputed at next issue')
    return (policy, info)

def execute_lookahead_action(contract, load, pv, state, price, policy, t, battery):
    vb = ValueBattery(lo=battery.minimum, hi=battery.maximum, power=battery.power_kw, eta_c=battery.eta_charge, eta_d=battery.eta_discharge)
    (action, explanation) = execute_rolling_value_policy(contract, load, pv, state, price, policy.next_values(t), policy.grid, battery=vb, general_search=True)
    action['unused'] = action.pop('surplus')
    action['soc_start'] = state
    used_pv = min(pv, load + action['charge'])
    used_grid = min(contract, max(0.0, load + action['charge'] - used_pv - action['discharge']))
    action['unused_pv'] = pv - used_pv
    action['unused_purchased'] = contract - used_grid
    action['held_with_emergency'] = explanation['economic_hold_with_emergency']
    return action

@dataclass(frozen=True)
class Candidate:
    name: str
    question: str
    blend: float = 1.0
    quantile: float = 0.8
    window: int = 14
    bias: bool = True
    adjustment: str = 'next6'
    terminal: float = 6000.0
    load_feedback: float = 0.0
    price_days: int = 0
    interpretation: str = 'B'
    reference_mode: str = 'initial_final'
    intraday_quantile: float | None = None
    terminal_weight: float = 1.0
    forecast_updates: str = 'latest'
    skip_hours: tuple = ()
    allow_decrease: bool = True
    early_quantile: float | None = None
    rolling_terminal: float | None = None
    reserve_fraction: float = 0.0
    controller: str = 'lookahead_dp'
    soc_step_kwh: float = 50.0
    dp_terminal_weight: float | None = None
    future_error_scale: float = 1.0
    value_discount: float = 1.0

    def __post_init__(self):
        if self.interpretation != 'B':
            raise ValueError('Only corrected 50-percent cancellation pricing is supported')
        if self.reference_mode not in ('initial_final', 'sequential', 'unspecified'):
            raise ValueError('Invalid multi-adjustment reference')
        if self.adjustment != 'none' and self.reference_mode == 'unspecified':
            raise ValueError('Specify the multi-adjustment reference before running')

def ordered_actuals(frame):
    frame = frame.sort_values(['date', 'interval_index']).reset_index(drop=True)
    if frame.duplicated(['date', 'interval_index']).any():
        raise ValueError('Duplicate date/interval key')
    for (_, day) in frame.groupby('date', sort=True):
        if not np.array_equal(day.interval_index.to_numpy(), np.arange(144)):
            raise ValueError('Incomplete day')
    if not np.array_equal(frame.interval_end.to_numpy()[:-1], frame.interval_start.to_numpy()[1:]):
        raise ValueError('Non-continuous interval timestamps')
    return frame

def prepare(actuals, forecasts, fixed_price):
    actuals = ordered_actuals(actuals)
    days = np.array(sorted(actuals.date.unique()))
    n = len(days)
    cache = {k: np.full((n, 144), np.nan) for k in ['load', 'historical_pv', 'price']}
    cache['issued_pv'] = np.full((n, 4, 144), np.nan)
    cache['truth_load'] = actuals.load_kwh.to_numpy().reshape(n, 144)
    cache['truth_pv'] = actuals.pv_kwh.to_numpy().reshape(n, 144)
    cache['truth_price'] = actuals.price_variable.to_numpy().reshape(n, 144)
    cache['fixed_price'] = fixed_price
    metadata = [None] * n
    provider = ForecastProvider()
    for (i, date) in enumerate(days):
        if i == 0:
            continue
        cutoff = pd.Timestamp(str(date))
        history = historical_snapshot(actuals, cutoff)
        bundle = provider.predict(history, cutoff)
        for (key, value) in [('load', bundle.load), ('historical_pv', bundle.pv), ('price', bundle.price)]:
            cache[key][i] = value
        metadata[i] = bundle.metadata
        for (j, t) in enumerate([0, 36, 72, 108]):
            issue = cutoff + pd.Timedelta(minutes=10 * t)
            visible = historical_snapshot(actuals, issue)
            released = forecasts.loc[forecasts.available_at <= issue]
            cache['issued_pv'][i, j, t:] = issued_pv_integrals(released, issue, visible.pv_kw.iloc[-1])[:144 - t]
        day = actuals.loc[actuals.date == date]
        provider.observe_completed_day(bundle, day, day.price_variable.to_numpy())
        if i % 60 == 0 or i == n - 1:
            print(json.dumps({'phase': 'forecast_cache', 'date': date}), flush=True)
    return (days, cache, metadata)

def base_prediction(cache, i, j, candidate):
    t = 36 * j
    source_issue = 0 if candidate.forecast_updates == 'frozen_midnight' else j
    load = cache['load'][i, t:].copy()
    historical = cache['historical_pv'][i, t:]
    pv = (1 - candidate.blend) * historical + candidate.blend * cache['issued_pv'][i, source_issue, t:] if candidate.question != 'Q4-2' else historical.copy()
    if candidate.bias and i > 1:
        begin = max(1, i - 3)
        load += np.mean(cache['truth_load'][begin:i, t:] - cache['load'][begin:i, t:], axis=0)
        past_pv = cache['historical_pv'][begin:i, t:]
        if candidate.question != 'Q4-2':
            past_pv = (1 - candidate.blend) * past_pv + candidate.blend * cache['issued_pv'][begin:i, source_issue, t:]
        pv += np.mean(cache['truth_pv'][begin:i, t:] - past_pv, axis=0)
    if j and candidate.load_feedback:
        (midnight_load, _) = base_prediction(cache, i, 0, candidate)
        correction = np.mean(cache['truth_load'][i, max(0, t - 12):t] - midnight_load[max(0, t - 12):t])
        load += candidate.load_feedback * correction * np.exp(-np.arange(144 - t) / 36)
    return (np.maximum(load, 0), np.maximum(pv, 0))

def packet(days, cache, metadata, i, j, candidate):
    t = j * 36
    (load, pv) = base_prediction(cache, i, j, candidate)
    begin = max(1, i - candidate.window)
    residuals = []
    for past in range(begin, i):
        (pl, pp) = base_prediction(cache, past, j, candidate)
        residuals.append(cache['truth_load'][past, t:] - cache['truth_pv'][past, t:] - pl + pp)
    margin = np.zeros(144 - t)
    quantile = candidate.intraday_quantile if j and candidate.intraday_quantile is not None else candidate.quantile
    kernels = [np.zeros(1) for _ in range(144 - t)]
    if residuals:
        residuals = np.array(residuals)
        groups = residuals.reshape(len(residuals), (144 - t) // 6, 6).transpose(1, 0, 2).reshape((144 - t) // 6, -1)
        kernels = [groups[h // 6].copy() for h in range(144 - t)]
        if quantile > 0:
            margin = np.repeat(np.maximum(np.quantile(groups, quantile, axis=1), 0), 6)
        if j == 0 and candidate.early_quantile is not None:
            margin[:36] = np.repeat(np.maximum(np.quantile(groups[:6], candidate.early_quantile, axis=1), 0), 6)
    price = cache['fixed_price'][t:] if candidate.question == 'Q3' else cache['price'][i, t:]
    if candidate.question != 'Q3' and candidate.price_days:
        price = cache['truth_price'][max(0, i - candidate.price_days):i, t:].mean(axis=0)
    info = dict(metadata[i], cutoff=str(pd.Timestamp(str(days[i])) + pd.Timedelta(minutes=10 * t)), issue_hour=j * 6, last_calibration_date=str(days[i - 1]), calibration_window_days=i - begin, attachment3_used=candidate.question != 'Q4-2' and candidate.blend > 0, forecast_blend=candidate.blend, bias_corrected=candidate.bias, margin_quantile=quantile, load_feedback=candidate.load_feedback, forecast_issue_hour=0 if candidate.forecast_updates == 'frozen_midnight' else j * 6, price_history_days=candidate.price_days)
    info['early_quantile'] = candidate.early_quantile
    return dict(load=load, pv=pv, margin=margin, price=price.copy(), metadata=info, residual_kernels=kernels)

def day_plan(bundle, state, candidate, battery):
    result = optimize(bundle['load'] + bundle['margin'], bundle['pv'], bundle['price'], initial=state, terminal=candidate.terminal, battery=battery, relax=True)
    if result['solver']['status'] != 0:
        raise RuntimeError('Uncertified day-ahead solve: ' + str(result['solver']))
    if np.minimum(result['charge'], result['discharge']).max() > 1e-07:
        result = optimize(bundle['load'] + bundle['margin'], bundle['pv'], bundle['price'], initial=state, terminal=candidate.terminal, battery=battery)
    if result['solver']['status'] != 0:
        raise RuntimeError('Uncertified MILP day-ahead solve')
    return result

def run_candidate(days, cache, metadata, actuals, candidate, start, end, battery=Battery()):
    if candidate.controller != 'lookahead_dp' or candidate.question not in ('Q3', 'Q4-3') or candidate.adjustment != 'next6':
        raise ValueError('Only the current Q3/Q4-3 lookahead-DP structure is supported')
    (state, frames, decisions, event_rows) = (6000.0, [], [], [])
    by_day = dict(tuple(actuals.groupby('date', sort=True)))
    for i in range(start, end + 1):
        date = str(days[i])
        day = by_day[date]
        p = packet(days, cache, metadata, i, 0, candidate)
        plan = day_plan(p, state, candidate, battery)
        mode = candidate.reference_mode if candidate.reference_mode != 'unspecified' else 'initial_final'
        ledger = AdjustmentLedger(plan['grid'], mode)
        (policy, value_info) = lookahead_value_policy(p, plan['grid'], candidate, battery, 0)
        decisions.append(dict(p['metadata'], strategy=candidate.name, decision_type='day_ahead', initial_soc=state, solver=plan['solver'], changed_contract=False, **value_info))
        actions = []
        actual_price = cache['fixed_price'] if candidate.question == 'Q3' else cache['truth_price'][i]
        control_price = actual_price if candidate.question == 'Q3' else p['price'].copy()
        for (t, row) in enumerate(day.itertuples(index=False)):
            if t in (36, 72, 108) and candidate.adjustment != 'none' and (t // 6 not in candidate.skip_hours):
                updated = packet(days, cache, metadata, i, t // 36, candidate)
                reference = ledger.original[t:] if mode == 'initial_final' else ledger.contract[t:]
                proposed = replan(updated['load'] + updated['margin'], updated['pv'], updated['price'], reference, state, candidate.terminal if candidate.rolling_terminal is None else candidate.rolling_terminal, battery, candidate.terminal_weight, minimum_contract=ledger.contract[t:] if not candidate.allow_decrease else None)
                if proposed['solver']['status'] != 0:
                    raise RuntimeError('Uncertified replan')
                grid = ledger.contract.copy()
                stop = min(t + 36, 144) if candidate.adjustment == 'next6' else 144
                grid[t:stop] = proposed['grid'][:stop - t]
                issue = pd.Timestamp(date) + pd.Timedelta(minutes=10 * t)
                changed = ledger.revise(grid, t, issue)
                plan['soc'][t:] = proposed['soc']
                (policy, value_info) = lookahead_value_policy(updated, proposed['grid'], candidate, battery, t)
                decisions.append(dict(updated['metadata'], strategy=candidate.name, decision_type='intraday', initial_soc=state, solver=proposed['solver'], changed_contract=changed, committed_until_interval=stop, proposal_scope='remaining day; only stated commit window applied', **value_info))
            action = execute_lookahead_action(ledger.contract[t], row.load_kwh, row.pv_kwh, state, control_price[t], policy, t, battery)
            state = action['soc_end']
            actions.append(action)
        frame = day[['date', 'interval_index', 'interval_start', 'interval_end', 'load_kwh', 'pv_kwh']].reset_index(drop=True)
        frame = pd.concat([frame, pd.DataFrame(actions)], axis=1)
        (frame['price'], frame['plan_price']) = (actual_price, p['price'])
        if candidate.question == 'Q4-3':
            frame['control_price'] = control_price
        (frame['planned_grid'], frame['contract_grid']) = (ledger.original, ledger.contract)
        for (key, values) in ledger.settle(actual_price, frame.emergency).items():
            frame[key] = values
        for event in ledger.events:
            if mode == 'initial_final':
                (before_delta, after_delta) = (event['before'] - ledger.original, event['after'] - ledger.original)
                inc_component = np.maximum(after_delta, 0) - np.maximum(before_delta, 0)
                dec_component = np.maximum(-after_delta, 0) - np.maximum(-before_delta, 0)
            else:
                (inc_component, dec_component) = (event['increase'], event['decrease'])
            for t in np.flatnonzero(event['increase'] + event['decrease'] > 1e-07):
                event_rows.append(dict(date=date, issue_time=event['issue_time'], effective_from=event['effective_from'], interval_index=int(t), increase_kwh=float(event['increase'][t]), decrease_kwh=float(event['decrease'][t]), delivery_price=float(actual_price[t]), increase_fee=float(1.5 * actual_price[t] * inc_component[t]), decrease_penalty=float(0.5 * actual_price[t] * dec_component[t]), refund=float(actual_price[t] * dec_component[t])))
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    (daily, monthly, summary) = aggregate(frame, battery)
    summary.update(strategy=asdict(candidate), contract_modification_decisions=sum((d['changed_contract'] for d in decisions)), intraday_forecast_updates=sum((d['decision_type'] == 'intraday' for d in decisions)), contract_event_rows=len(event_rows), optimality='BEST_FOUND_POLICY_NOT_GLOBAL_OPTIMUM')
    summary['value_table_rebuilds'] = len(decisions)
    summary['economic_hold_intervals'] = int(frame.held_with_emergency.sum())
    events = pd.DataFrame(event_rows, columns=['date', 'issue_time', 'effective_from', 'interval_index', 'increase_kwh', 'decrease_kwh', 'delivery_price', 'increase_fee', 'decrease_penalty', 'refund'])
    return (frame, daily, monthly, summary, decisions, events)

def forecast_accuracy(days,cache,metadata,candidate,first):
    metrics=[];example=[]
    for issue in range(4):
        raw_errors=[];fused_errors=[]
        for day in range(first,len(days)):
            bundle=packet(days,cache,metadata,day,issue,candidate)
            start=36*issue
            truth=cache['truth_pv'][day,start:start+36]
            raw=cache['issued_pv'][day,issue,start:start+36]
            raw_errors.extend(raw-truth);fused_errors.extend(bundle['pv'][:36]-truth)
            if str(days[day])=='2025-03-20':
                for t in range(36):
                    example.append(dict(interval_index=start+t,issue_hour=issue*6,actual_pv_kwh=float(truth[t]),
                        issued_pv_kwh=float(raw[t]),fused_pv_kwh=float(bundle['pv'][t]),
                        load_forecast_kwh=float(bundle['load'][t]),margin_kwh=float(bundle['margin'][t])))
        for name,errors in [('发布预报',raw_errors),('融合修正预报',fused_errors)]:
            errors=np.asarray(errors)
            metrics.append(dict(issue_hour=issue*6,method=name,intervals=len(errors),
                rmse_kwh=float(np.sqrt(np.mean(errors**2))),mae_kwh=float(np.mean(abs(errors)))))
    return pd.DataFrame(metrics),pd.DataFrame(example)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--checks',action='store_true');args=parser.parse_args()
    actual=ordered_actuals(pd.read_csv(ROOT/'data/processed/actuals_energy.csv',parse_dates=['interval_start','interval_end','available_at']))
    forecasts=pd.read_csv(ROOT/'data/processed/pv_forecasts.csv',parse_dates=['issue_time','available_at','target_time'])
    price=pd.read_csv(ROOT/'data/processed/q1_inputs.csv').sort_values('interval_index').price.to_numpy()
    candidate=Candidate(**json.loads((ROOT/'configs/q3_current.json').read_text())[0])
    days,cache,metadata=prepare(actual,forecasts,price)
    start=list(days).index('2025-02-01')
    result=run_candidate(days,cache,metadata,actual,candidate,start,len(days)-1)
    summary=export_annual(result[0],args.out,asdict(candidate),result[3])
    if args.checks:
        metrics,example=forecast_accuracy(days,cache,metadata,candidate,start)
        metrics.to_csv(args.out/'forecast_metrics.csv',index=False)
        example.to_csv(args.out/'forecast_example.csv',index=False)
        for name,setting in [('frozen_forecast',replace(candidate,forecast_updates='frozen_midnight')),('grid25',replace(candidate,soc_step_kwh=25.))]:
            comparison=run_candidate(days,cache,metadata,actual,setting,start,len(days)-1)
            export_annual(comparison[0],args.out/name,asdict(setting),comparison[3])
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
