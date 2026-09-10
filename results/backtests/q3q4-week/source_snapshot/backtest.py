import argparse
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from dispatch import Battery, optimize
from forecasting import ForecastProvider, historical_snapshot, issued_pv_integrals
from settlement import SettlementLedger


@dataclass(frozen=True)
class Strategy:
    name: str
    margin: bool = False
    battery: bool = True
    variable_price: bool = False
    controller: str = 'reference'
    forecasts: str = 'none'
    adjustments: str = 'none'
    interpretation: str = 'A'


STRATEGIES = {
    'q2_no_battery': Strategy('q2_no_battery', battery=False),
    'q2_point': Strategy('q2_point'),
    'q2_margin': Strategy('q2_margin', margin=True),
    'q2_margin_greedy': Strategy('q2_margin_greedy', margin=True, controller='greedy'),
    'q4_2_margin': Strategy('q4_2_margin', margin=True, variable_price=True),
    'q3_midnight': Strategy('q3_midnight', margin=True, forecasts='midnight'),
    'q3_frozen_update': Strategy('q3_frozen_update', margin=True, forecasts='frozen_update'),
    'q3_battery_update': Strategy('q3_battery_update', margin=True, forecasts='four'),
    'q3_adjust_A': Strategy('q3_adjust_A', margin=True, forecasts='four', adjustments='all'),
    'q3_selective_A': Strategy('q3_selective_A', margin=True, forecasts='four', adjustments='selective'),
    'q3_adjust_B': Strategy('q3_adjust_B', margin=True, forecasts='four', adjustments='all', interpretation='B'),
    'q4_3_adjust_A': Strategy('q4_3_adjust_A', margin=True, variable_price=True, forecasts='four', adjustments='all'),
    'q4_3_adjust_B': Strategy('q4_3_adjust_B', margin=True, variable_price=True, forecasts='four', adjustments='all', interpretation='B'),
}


def checked_optimization(load, pv, price, initial, battery):
    result = optimize(load, pv, price, initial=initial, terminal=6000,
                      battery=battery, relax=True)
    overlap = float(np.minimum(result['charge'], result['discharge']).max())
    if overlap > 1e-7:
        result = optimize(load, pv, price, initial=initial, terminal=6000,
                          battery=battery, relax=False)
    c, d, q, w, e = [result[x] for x in ['charge', 'discharge', 'grid', 'unused', 'soc']]
    residual = max(float(abs(q+pv+d-load-c-w).max()),
                   float(abs(np.diff(e)-battery.eta_charge*c+d/battery.eta_discharge).max()),
                   float(np.minimum(c, d).max()), float(max(0, battery.minimum-e.min(), e.max()-battery.maximum)))
    if residual > 1e-5:
        raise AssertionError(f'Planning feasibility failed: {residual}')
    result['solver']['maximum_checked_residual_kwh'] = residual
    return result


class DayAheadPlanner:
    def __init__(self, battery=Battery()):
        self.battery = battery

    def plan(self, bundle, strategy, initial, fixed_price, pv_override=None):
        load = bundle.load + (bundle.margin if strategy.margin else 0)
        pv = bundle.pv if pv_override is None else pv_override
        price = bundle.price if strategy.variable_price else fixed_price
        if strategy.battery:
            result = checked_optimization(load, pv, price, initial, self.battery)
        else:
            result = {'grid': np.maximum(load-pv, 0), 'charge': np.zeros(144),
                      'discharge': np.zeros(144), 'soc': np.full(145, initial),
                      'solver': {'status': 'NO_BATTERY', 'relax': False}}
        result['forecast_load'], result['forecast_pv'], result['forecast_price'] = load, pv, price
        return result


class RealtimeController:
    """Ideal within-interval feedback using piecewise-constant average powers.

    This is an execution approximation, not availability of completed interval
    integrals at their start. Day-ahead forecasts use completed past labels only.
    """
    def __init__(self, battery=Battery()):
        self.battery = battery

    def act(self, state, load, pv, contract, target_next, enabled=True, mode='reference'):
        b = self.battery
        balance = contract+pv-load
        charge = discharge = 0.
        if enabled and balance >= 0:
            charge = min(balance, b.power_kw*b.dt, max(0., (b.maximum-state)/b.eta_charge))
        elif enabled:
            floor = b.minimum if mode == 'greedy' else max(b.minimum, min(b.maximum, target_next))
            discharge = min(-balance, b.power_kw*b.dt, max(0., (state-floor)*b.eta_discharge))
        emergency = max(0., load-contract-pv-discharge)
        unused = max(0., contract+pv+discharge-load-charge)
        state_next = state+b.eta_charge*charge-discharge/b.eta_discharge
        used_pv = min(pv, load+charge)
        used_purchase = min(contract, max(0., load+charge-used_pv-discharge))
        return {'charge': charge, 'discharge': discharge, 'soc_start': state,
                'soc_end': state_next, 'emergency': emergency, 'unused': unused,
                'unused_pv': pv-used_pv, 'unused_purchased': contract-used_purchase}


def replan_remaining(load, pv, price, old_contract, initial, battery,
                     allow_change=False, interpretation='A'):
    n = len(load)
    increase, decrease, emergency, c, d, w, e, z, slack = 0, n, 2*n, 3*n, 4*n, 5*n, 6*n, 7*n+1, 8*n+1
    size = slack+1
    objective = np.zeros(size)
    objective[increase:increase+n] = 1.5*price
    objective[decrease:decrease+n] = (.5 if interpretation == 'A' else -.5)*price
    objective[emergency:emergency+n] = 5*price
    objective[slack] = price.min()/battery.eta_charge
    lower, upper = np.zeros(size), np.full(size, np.inf)
    cap = battery.power_kw*battery.dt
    upper[c:c+n] = upper[d:d+n] = cap
    lower[e:e+n+1], upper[e:e+n+1] = battery.minimum, battery.maximum
    lower[e] = upper[e] = initial
    upper[z:z+n] = 1
    if not allow_change:
        upper[increase:increase+n] = upper[decrease:decrease+n] = 0
        upper[c:c+n] = np.minimum(cap, np.maximum(old_contract+pv-load, 0))
        upper[d:d+n] = np.minimum(cap, np.maximum(load-old_contract-pv, 0))
    else:
        upper[decrease:decrease+n] = old_contract if interpretation == 'B' else 0
    a = lil_matrix((4*n+1, size))
    low, high = np.full(4*n+1, -np.inf), np.full(4*n+1, np.inf)
    for t in range(n):
        a[t, increase+t], a[t, decrease+t], a[t, emergency+t] = 1, -1, 1
        a[t, c+t], a[t, d+t], a[t, w+t] = -1, 1, -1
        low[t] = high[t] = load[t]-pv[t]-old_contract[t]
        a[n+t, e+t+1], a[n+t, e+t] = 1, -1
        a[n+t, c+t], a[n+t, d+t] = -battery.eta_charge, 1/battery.eta_discharge
        low[n+t] = high[n+t] = 0
        a[2*n+t, c+t], a[2*n+t, z+t] = 1, -cap
        high[2*n+t] = 0
        a[3*n+t, d+t], a[3*n+t, z+t] = 1, cap
        high[3*n+t] = cap
    a[-1, e+n], a[-1, slack] = 1, 1
    low[-1] = 6000
    integral = np.zeros(size)
    tic = time.perf_counter()
    result = milp(objective, integrality=integral, bounds=Bounds(lower, upper),
                  constraints=LinearConstraint(a.tocsc(), low, high), options={'time_limit': 60})
    if result.x is None:
        raise RuntimeError(result.message)
    if np.minimum(result.x[c:c+n], result.x[d:d+n]).max() > 1e-7:
        integral[z:z+n] = 1
        result = milp(objective, integrality=integral, bounds=Bounds(lower, upper),
                      constraints=LinearConstraint(a.tocsc(), low, high),
                      options={'time_limit': 60, 'mip_rel_gap': 1e-8})
    if result.x is None:
        raise RuntimeError(result.message)
    x = result.x
    if max(np.minimum(x[c:c+n], x[d:d+n]).max(),
           np.minimum(x[c:c+n], x[emergency:emergency+n]).max()) > 1e-6:
        raise AssertionError('Replan uses simultaneous charge/discharge or emergency charging')
    return {'grid': old_contract+x[increase:increase+n]-x[decrease:decrease+n],
            'charge': x[c:c+n], 'discharge': x[d:d+n], 'soc': x[e:e+n+1],
            'solver': {'status': int(result.status), 'objective': float(result.fun),
                       'runtime_seconds': time.perf_counter()-tic, 'relax': not integral.any(),
                       'mip_gap': getattr(result, 'mip_gap', None),
                       'terminal_shortfall_penalty_value': float(objective[slack]),
                       'message': result.message}}


def verify_intervals(frame, battery):
    b = battery
    bus = frame.contract_grid+frame.pv_kwh+frame.discharge+frame.emergency-frame.load_kwh-frame.charge-frame.unused
    dynamics = frame.soc_end-frame.soc_start-b.eta_charge*frame.charge+frame.discharge/b.eta_discharge
    total = frame.original_fee+frame.increase_fee+frame.decrease_penalty-frame.refund+frame.emergency_fee
    metrics = {'bus_residual_kwh': float(abs(bus).max()),
               'soc_recursion_residual_kwh': float(abs(dynamics).max()),
               'soc_lower_violation_kwh': float(max(0., b.minimum-frame.soc_end.min())),
               'soc_upper_violation_kwh': float(max(0., frame.soc_end.max()-b.maximum)),
               'power_violation_kwh': float(max(0., frame.charge.max()-b.power_kw*b.dt,
                                              frame.discharge.max()-b.power_kw*b.dt)),
               'simultaneous_charge_discharge_kwh': float(np.minimum(frame.charge, frame.discharge).max()),
               'emergency_and_charge_overlap_kwh': float(np.minimum(frame.emergency, frame.charge).max()),
               'fee_reconciliation_yuan': float(abs(total-frame.total_fee).max()),
               'unused_source_reconciliation_kwh': float(abs(frame.unused-frame.unused_pv-frame.unused_purchased).max()),
               'continuous_state_residual_kwh': float(np.max(abs(frame.soc_start.to_numpy()[1:]-frame.soc_end.to_numpy()[:-1]))),
               'nonnegative_violation_kwh': float(max(0, -frame[['planned_grid', 'contract_grid', 'charge', 'discharge', 'emergency', 'unused']].min().min()))}
    metrics['passed'] = all(v < 1e-6 for v in metrics.values())
    if not metrics['passed']:
        raise AssertionError(metrics)
    return metrics


def aggregate(frame, battery):
    amount_cols = ['planned_grid', 'contract_grid', 'charge', 'discharge', 'emergency', 'unused',
                   'unused_pv', 'unused_purchased', 'original_fee', 'increase_fee', 'decrease_penalty',
                   'refund', 'emergency_fee', 'total_fee', 'contract_increase', 'contract_decrease']
    daily = frame.groupby('date')[amount_cols].sum()
    daily['initial_soc'] = frame.groupby('date').soc_start.first()
    daily['terminal_soc'] = frame.groupby('date').soc_end.last()
    active = frame.emergency > 1e-7
    starts = active & (~active.shift(fill_value=False) | frame.date.ne(frame.date.shift()))
    daily['emergency_events'] = starts.groupby(frame.date).sum()
    daily['emergency_intervals'] = active.groupby(frame.date).sum()
    monthly = daily[amount_cols+['emergency_events', 'emergency_intervals']].groupby(daily.index.str[:7]).sum()
    monthly.index.name = 'month'
    tail = daily.total_fee.quantile(.95)
    summary = {k: float(frame[k].sum()) for k in amount_cols}
    summary.update({'days': len(daily), 'intervals': len(frame), 'start_date': frame.date.iloc[0],
                    'end_date': frame.date.iloc[-1], 'initial_soc_kwh': float(frame.soc_start.iloc[0]),
                    'terminal_soc_kwh': float(frame.soc_end.iloc[-1]),
                    'daily_cost_p95_yuan': float(tail),
                    'daily_cost_tail_mean_yuan': float(daily.loc[daily.total_fee >= tail, 'total_fee'].mean()),
                    'emergency_events': int(daily.emergency_events.sum()),
                    'soc_min_kwh': float(min(frame.soc_start.min(), frame.soc_end.min())),
                    'soc_max_kwh': float(max(frame.soc_start.max(), frame.soc_end.max())),
                    'terminal_energy_delta_kwh': float(frame.soc_end.iloc[-1]-frame.soc_start.iloc[0]),
                    'terminal_credit_sensitivity_yuan': float((frame.soc_end.iloc[-1]-frame.soc_start.iloc[0])*frame.plan_price.iloc[-144:].min()/battery.eta_charge)})
    summary['total_fee_less_terminal_credit_sensitivity'] = summary['total_fee']-summary['terminal_credit_sensitivity_yuan']
    summary['verification'] = verify_intervals(frame, battery)
    return daily, monthly, summary


class Simulator:
    def __init__(self, actuals, forecasts, fixed_price, battery=Battery()):
        self.actuals = actuals
        self.forecasts = forecasts
        self.fixed_price = fixed_price
        self.battery = battery

    def run(self, strategies, end_date, output, progress_every=14):
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
        groups = {(s.variable_price, s.forecasts != 'none') for s in strategies}
        providers = {group: ForecastProvider() for group in groups}
        planner, controller = DayAheadPlanner(self.battery), RealtimeController(self.battery)
        states = {s.name: 6000. for s in strategies}
        records = {s.name: [] for s in strategies}
        decisions = {s.name: [] for s in strategies}
        all_events = {s.name: [] for s in strategies}
        prediction_metrics = []
        forecast_rows = []
        tic = time.perf_counter()
        days = sorted(self.actuals.date.unique())
        for number, date in enumerate(days):
            if date > end_date:
                break
            day = self.actuals.loc[self.actuals.date == date].copy()
            cutoff = pd.Timestamp(date)
            history = historical_snapshot(self.actuals, cutoff)
            if number == 0:
                continue
            bundles = {}
            for group, provider in providers.items():
                variable, external_pv = group
                local_history = history.copy(deep=True)
                if not variable:
                    local_history['price_variable'] = self.fixed_price[local_history.interval_index.to_numpy()]
                current_bundle = provider.predict(local_history, cutoff)
                if external_pv:
                    released = self.forecasts.loc[self.forecasts.available_at <= cutoff].copy()
                    pv_curve = issued_pv_integrals(released, cutoff, history.pv_kw.iloc[-1])
                    metadata = dict(current_bundle.metadata, attachment3_used=True,
                                    forecast_issue_time=cutoff.isoformat(),
                                    pv_prediction='issued-hourly-points-linear-integral',
                                    lead_zero='last-completed-interval-average-proxy')
                    current_bundle = replace(current_bundle, pv=pv_curve, metadata=metadata)
                bundles[group] = current_bundle
            bundle = bundles[next(iter(providers))]
            if number >= 7:
                truth = day[['load_kwh', 'pv_kwh']].to_numpy()
                pred = np.column_stack([bundle.load, bundle.pv])
                for k, target in enumerate(['load', 'pv']):
                    error = pred[:, k]-truth[:, k]
                    denom = np.mean(abs(history[target+'_kwh'].to_numpy()[144:]-history[target+'_kwh'].to_numpy()[:-144]))
                    prediction_metrics.append({'date': date, 'target': target, 'mae_kwh': float(abs(error).mean()),
                        'rmse_kwh': float(np.sqrt(np.mean(error**2))), 'mase_lag144': float(abs(error).mean()/max(denom, 1e-8)),
                        'daylight_mae_kwh': float(abs(error[truth[:, 1] > 0]).mean()) if target == 'pv' else None})
                net_resid = truth[:, 0]-truth[:, 1]-bundle.load+bundle.pv
                forecast_rows.append(pd.DataFrame({'date': date, 'interval_index': np.arange(144),
                    'predicted_load_kwh': bundle.load, 'predicted_pv_kwh': bundle.pv,
                    'predicted_price': bundle.price, 'margin_kwh': bundle.margin,
                    'actual_net_residual_kwh': net_resid,
                    'net_upper_covered': net_resid <= bundle.margin,
                    'net_quantile_pinball_kwh': np.maximum(bundle.metadata['margin_quantile']*(net_resid-bundle.margin),
                                                          (bundle.metadata['margin_quantile']-1)*(net_resid-bundle.margin))}))
            if date >= '2025-02-01':
                for strategy in strategies:
                    bundle = bundles[(strategy.variable_price, strategy.forecasts != 'none')]
                    plan = planner.plan(bundle, strategy, states[strategy.name], self.fixed_price)
                    ledger = SettlementLedger(plan['grid'], strategy.interpretation)
                    decision = dict(bundle.metadata, strategy=strategy.name, initial_soc=states[strategy.name],
                                    solver=plan['solver'], decision_type='day_ahead', changed_contract=False,
                                    margin_price_calibration='variable-paired-historical' if strategy.variable_price else 'fixed-tariff')
                    decisions[strategy.name].append(decision)
                    actions = []
                    for t, row in enumerate(day.itertuples(index=False)):
                        if strategy.forecasts in ('four', 'frozen_update') and t in (36, 72, 108):
                            issue = cutoff+pd.Timedelta(minutes=10*t)
                            visible = historical_snapshot(self.actuals, issue)
                            released = self.forecasts.loc[self.forecasts.available_at <= issue].copy()
                            latest_pv = (bundle.pv[t:] if strategy.forecasts == 'frozen_update' else
                                         issued_pv_integrals(released, issue, visible.pv_kw.iloc[-1])[:144-t])
                            price = plan['forecast_price'][t:]
                            load = bundle.load[t:]+(bundle.margin[t:] if strategy.margin else 0)
                            unchanged = replan_remaining(load, latest_pv, price, ledger.contract[t:],
                                                         states[strategy.name], self.battery)
                            chosen = unchanged
                            gain, threshold = 0., 0.
                            if strategy.adjustments != 'none':
                                candidate = replan_remaining(load, latest_pv, price, ledger.contract[t:],
                                    states[strategy.name], self.battery, True, strategy.interpretation)
                                gain = unchanged['solver']['objective']-candidate['solver']['objective']
                                if strategy.adjustments == 'selective':
                                    threshold = float(np.sum(price*bundle.margin[t:]))
                                if gain > max(1e-6, threshold):
                                    chosen = candidate
                            contract = ledger.contract.copy()
                            contract[t:] = chosen['grid']
                            changed = ledger.revise(contract, t, issue)
                            plan['soc'][t:] = chosen['soc']
                            decisions[strategy.name].append({'cutoff': issue.isoformat(), 'strategy': strategy.name,
                                'decision_type': 'intraday', 'training_label_cutoff': bundle.metadata['training_label_cutoff'],
                                'forecast_issue_time': (cutoff if strategy.forecasts == 'frozen_update' else issue).isoformat(),
                                'lead_zero': 'last-completed-interval-average-proxy',
                                'margin_calibration': 'historical-midnight-version-residuals; not lead-specific calibrated intervals',
                                'attachment3_used': True, 'changed_contract': changed,
                                'expected_improvement_yuan': gain, 'selection_threshold_yuan': threshold,
                                'solver': chosen['solver']})
                        action = controller.act(states[strategy.name], row.load_kwh, row.pv_kwh,
                                                ledger.contract[t], plan['soc'][t+1], strategy.battery, strategy.controller)
                        states[strategy.name] = action['soc_end']
                        actions.append(action)
                    frame = day[['date', 'interval_index', 'interval_start', 'interval_end', 'load_kwh', 'pv_kwh']].reset_index(drop=True)
                    frame = pd.concat([frame, pd.DataFrame(actions)], axis=1)
                    actual_price = day.price_variable.to_numpy() if strategy.variable_price else self.fixed_price
                    frame['price'], frame['plan_price'] = actual_price, plan['forecast_price']
                    frame['planned_grid'], frame['contract_grid'] = ledger.original, ledger.contract
                    for key, value in ledger.settle(actual_price, frame.emergency).items():
                        frame[key] = value
                    for event in ledger.events:
                        for index in np.flatnonzero(event['increase']+event['decrease'] > 1e-7):
                            all_events[strategy.name].append({'date': date, 'issue_time': event['issue_time'],
                                'effective_from': event['effective_from'], 'interval_index': int(index),
                                'increase_kwh': float(event['increase'][index]),
                                'decrease_kwh': float(event['decrease'][index]),
                                'delivery_price': float(actual_price[index]),
                                'increase_fee': float(1.5*actual_price[index]*event['increase'][index]),
                                'decrease_penalty': float(.5*actual_price[index]*event['decrease'][index]),
                                'refund': float(actual_price[index]*event['decrease'][index]) if strategy.interpretation == 'B' else 0.})
                    records[strategy.name].append(frame)
                if (number-30) % progress_every == 0 or date == end_date:
                    print(json.dumps({'date_completed': date, 'elapsed_seconds': round(time.perf_counter()-tic, 2),
                                      'states': states}), flush=True)
            for group, provider in providers.items():
                variable, _ = group
                local_day = day.copy()
                if not variable:
                    local_day['price_variable'] = self.fixed_price
                provider.observe_completed_day(bundles[group], local_day,
                                                day.price_variable.to_numpy() if variable else self.fixed_price)
        all_summaries = {}
        for strategy in strategies:
            destination = output/strategy.name
            destination.mkdir()
            frame = pd.concat(records[strategy.name], ignore_index=True)
            daily, monthly, summary = aggregate(frame, self.battery)
            summary['contract_modification_decisions'] = sum(x['changed_contract'] for x in decisions[strategy.name])
            summary['intraday_forecast_updates'] = sum(x['decision_type'] == 'intraday' for x in decisions[strategy.name])
            summary['contract_event_rows'] = len(all_events[strategy.name])
            summary['strategy'] = asdict(strategy)
            frame.to_csv(destination/'intervals.csv.gz', index=False, compression='gzip')
            daily.to_csv(destination/'daily.csv')
            monthly.to_csv(destination/'monthly.csv')
            frame.loc[frame.date.isin(['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21'])].to_csv(destination/'display_days.csv', index=False)
            (destination/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
            (destination/'decisions.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in decisions[strategy.name]))
            pd.DataFrame(all_events[strategy.name], columns=['date', 'issue_time', 'effective_from', 'interval_index',
                'increase_kwh', 'decrease_kwh', 'delivery_price', 'increase_fee', 'decrease_penalty', 'refund']).to_csv(destination/'events.csv', index=False)
            all_summaries[strategy.name] = summary
        pd.DataFrame(prediction_metrics).to_csv(output/'forecast_metrics.csv', index=False)
        pd.concat(forecast_rows, ignore_index=True).to_csv(output/'forecast_evaluation.csv.gz', index=False, compression='gzip')
        (output/'summary.json').write_text(json.dumps(all_summaries, indent=2)+'\n')
        return all_summaries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/2026c.json')
    parser.add_argument('--strategies', default='q2_no_battery,q2_point,q2_margin,q2_margin_greedy')
    parser.add_argument('--end-date', default='2025-12-31')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    processed = Path(config['processed_dir'])
    actuals = pd.read_csv(processed/'actuals.csv', parse_dates=['interval_start', 'interval_end', 'available_at'])
    forecasts = pd.read_csv(processed/'forecasts.csv', parse_dates=['issue_time', 'available_at', 'target_time'])
    fixed_price = pd.read_csv(processed/'q1.csv').price.to_numpy()
    battery = Battery(config['minimum_kwh'], config['maximum_kwh'], config['power_kw'],
                      config['efficiency_charge'], config['efficiency_discharge'], config['dt_hours'])
    chosen = [STRATEGIES[name] for name in args.strategies.split(',')]
    simulation = Simulator(actuals, forecasts, fixed_price, battery)
    summary = simulation.run(chosen, args.end_date, args.output)
    provenance = {'created_utc': datetime.now(timezone.utc).isoformat(), 'config': config,
                  'arguments': vars(args), 'battery': asdict(battery),
                  'january_warmup': 'battery disabled, initial and final energy 6000 kWh',
                  'real_time_observation': 'ideal within-interval feedback: each measured 10-minute average is a piecewise-constant representative power available for interval balancing; not a measured future integral known at the interval start',
                  'execution_information_boundary': 'strict past-observation-only feedback remains an unimplemented sensitivity; day-ahead forecasts and contracts see only labels completed by cutoff',
                  'price_availability': 'variable prices predicted from completed history; actual delivery price used only by settlement',
                  'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                            [processed/'actuals.csv', processed/'forecasts.csv', processed/'q1.csv',
                             Path('src/backtest.py'), Path('src/forecasting.py'), Path('src/settlement.py'), Path('src/dispatch.py')]}}
    (Path(args.output)/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    snapshot = Path(args.output)/'source_snapshot'
    snapshot.mkdir()
    for name in ['backtest', 'forecasting', 'settlement', 'dispatch']:
        shutil.copy2(Path('src')/(name+'.py'), snapshot/(name+'.py'))
    (Path(args.output)/'git_worktree_status.txt').write_text(subprocess.run(
        ['git', 'status', '--short'], capture_output=True, text=True, check=True).stdout)
    print(json.dumps({name: {'total_fee': data['total_fee'], 'emergency': data['emergency'],
                             'terminal_soc_kwh': data['terminal_soc_kwh'], 'verification': data['verification']}
                      for name, data in summary.items()}, indent=2))


if __name__ == '__main__':
    main()
