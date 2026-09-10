"""One explicitly nonimplementable perfect-information Q2 diagnostic solve."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import time

import numpy as np
import pandas as pd

from dispatch import Battery, optimize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/2026c.json')
    parser.add_argument('--output', default='results/q2_iteration/oracle_bound_v4')
    parser.add_argument('--terminal', type=float, default=6136.72869169657)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    root = Path(__file__).resolve().parents[1]
    out = root/args.output
    out.mkdir(parents=True, exist_ok=False)
    processed = root/config['processed_dir']
    actual_path, tariff_path = processed/'actuals.csv', processed/'q1.csv'
    actuals = pd.read_csv(actual_path, parse_dates=['interval_start', 'interval_end'])
    frame = actuals.loc[(actuals.date >= '2025-02-01') & (actuals.date <= '2025-12-31')].copy()
    frame = frame.sort_values('interval_start').reset_index(drop=True)
    if len(frame) != 48096 or frame.date.nunique() != 334 or not (frame.groupby('date').size() == 144).all():
        raise ValueError('Oracle must cover exactly 334 complete days and 48096 intervals')
    if not np.array_equal(frame.interval_start.to_numpy()[1:], frame.interval_end.to_numpy()[:-1]):
        raise ValueError('Continuous horizon contains a gap or duplicate boundary')
    tariff = pd.read_csv(tariff_path).sort_values('interval_index').price.to_numpy()
    price = tariff[frame.interval_index.to_numpy()]
    load, pv = frame.load_kwh.to_numpy(), frame.pv_kwh.to_numpy()
    battery = Battery(config['minimum_kwh'], config['maximum_kwh'], config['power_kw'],
                      config['efficiency_charge'], config['efficiency_discharge'], config['dt_hours'])
    report = {'status': 'RUNNING', 'label': 'ORACLE_NOT_IMPLEMENTABLE',
              'created_utc': datetime.now(timezone.utc).isoformat(),
              'days': 334, 'intervals': 48096, 'initial_soc_kwh': 6000.,
              'terminal_soc_kwh_required': args.terminal, 'daily_soc_reset': False,
              'battery': asdict(battery), 'solver_time_limit_seconds': 60,
              'lower_bound_yuan': None,
              'information': 'All future actual load and PV are visible only in this isolated diagnostic.',
              'not_used_for': 'forecasting, calibration, parameter selection or operational strategy selection',
              'comparison_scope': 'ordinary tariff, same physical battery, initial energy and required final energy',
              'input_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [actual_path, tariff_path, root/args.config]},
              'versions': {name: importlib.metadata.version(name) for name in ['numpy', 'pandas', 'scipy']}}
    snapshot = out/'source_snapshot'
    snapshot.mkdir()
    for name in ['q2_oracle_bound.py', 'dispatch.py']:
        shutil.copy2(root/'src'/name, snapshot/name)
    report['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.iterdir()}
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Starting one 48096-interval ORACLE LP; 6000 -> '+str(args.terminal), flush=True)
    start = time.perf_counter()
    try:
        result = optimize(load, pv, price, initial=6000., terminal=args.terminal,
                          battery=battery, relax=True, time_limit=60)
    except Exception as exc:
        report.update(status='NOT_CERTIFIED', failure=str(exc), elapsed_seconds=time.perf_counter()-start)
        (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report, indent=2), flush=True)
        return
    report['elapsed_seconds'] = time.perf_counter()-start
    report['solver'] = result['solver']
    q, c, d, w, e = [result[name].copy() for name in ['grid', 'charge', 'discharge', 'unused', 'soc']]
    overlap_before = float(np.minimum(c, d).max())
    removed = np.minimum(c, d/(battery.eta_charge*battery.eta_discharge))
    c -= removed
    d -= battery.eta_charge*battery.eta_discharge*removed
    w += (1-battery.eta_charge*battery.eta_discharge)*removed
    recomputed = np.r_[6000., 6000.+np.cumsum(battery.eta_charge*c-d/battery.eta_discharge)]
    objective = float(price @ q)
    metrics = {
        'bus_residual_kwh': float(abs(q+pv+d-load-c-w).max()),
        'soc_step_residual_kwh': float(abs(np.diff(e)-battery.eta_charge*c+d/battery.eta_discharge).max()),
        'soc_independent_cumulative_residual_kwh': float(abs(e-recomputed).max()),
        'initial_residual_kwh': float(abs(e[0]-6000.)),
        'terminal_residual_kwh': float(abs(e[-1]-args.terminal)),
        'state_violation_kwh': float(max(0, battery.minimum-e.min(), e.max()-battery.maximum)),
        'power_violation_kwh': float(max(0, max(c.max(), d.max())-battery.power_kw*battery.dt)),
        'nonnegative_violation_kwh': float(max(0, -min(q.min(), c.min(), d.min(), w.min()))),
        'simultaneous_charge_discharge_kwh': float(np.minimum(c, d).max()),
        'objective_reconciliation_yuan': float(abs(objective-result['solver']['objective']))}
    passed = all(np.isfinite(value) and value <= 1e-5 for value in metrics.values())
    certified = result['solver']['status'] == 0 and passed
    report.update(status='CERTIFIED_ORACLE_BOUND' if certified else 'NOT_CERTIFIED',
                  lower_bound_yuan=objective if certified else None,
                  feasible_ordinary_cost_yuan=objective if passed else None,
                  physical_verification=dict(metrics, passed=passed),
                  simultaneous_overlap_before_cleanup_kwh=overlap_before,
                  cycle_cleanup_charge_kwh=float(removed.sum()),
                  cleanup='remove charge/discharge cycles at unchanged storage and cost; assign avoided losses to unused energy',
                  grid_kwh=float(q.sum()), terminal_soc_kwh_actual=float(e[-1]),
                  all_input_hashes_unchanged=all(hashlib.sha256((root/name).read_bytes()).hexdigest() == value
                      for name, value in report['input_sha256'].items()))
    output = frame[['date', 'interval_index', 'interval_start', 'interval_end', 'load_kwh', 'pv_kwh']].copy()
    output['price'] = price
    for name, values in [('grid_kwh', q), ('charge_kwh', c), ('discharge_kwh', d), ('unused_kwh', w),
                         ('soc_start_kwh', e[:-1]), ('soc_end_kwh', e[1:]), ('ordinary_cost_yuan', price*q)]:
        output[name] = values
    output.to_csv(out/'oracle_intervals.csv.gz', index=False, compression='gzip')
    daily = output.groupby('date')[['grid_kwh', 'charge_kwh', 'discharge_kwh', 'unused_kwh', 'ordinary_cost_yuan']].sum()
    daily['initial_soc_kwh'] = output.groupby('date').soc_start_kwh.first()
    daily['terminal_soc_kwh'] = output.groupby('date').soc_end_kwh.last()
    daily.to_csv(out/'oracle_daily.csv')
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
