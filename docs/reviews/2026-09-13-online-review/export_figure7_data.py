from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))

from microgrid import ValueBattery, build_midnight_value_table, execute_midnight_value_policy, load_verified_input
from problem2 import _q2_kernels, _terminal_kappa, build_prediction_packet


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clock(slot):
    return f'{slot // 6:02d}:{slot % 6 * 10:02d}'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default='2025-09-08')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError(out)
    data = load_verified_input(ROOT / 'data/processed/annual_inputs.npz', ROOT / 'data/processed/actuals_power.csv')
    day = int(np.flatnonzero(data['dates'].astype(str) == args.date)[0])
    observed = {k: data[k][:day + 1] for k in ('dates', 'actual_load', 'actual_pv')}
    print('Rebuilding causal fixed-Ridge forecasts through ' + args.date, flush=True)
    packet = build_prediction_packet(observed, 'fixed_ridge')
    source_path = ROOT / 'results/c2026/annual_slots.csv'
    saved = pd.read_csv(source_path)
    saved = saved.loc[(saved['case'] == 'q2') & (saved.date == args.date)].sort_values('slot').reset_index(drop=True)
    assert np.array_equal(saved.slot, np.arange(144))
    battery = ValueBattery()
    price = np.asarray(data['q1_price'], dtype=float)
    q = saved.plan.to_numpy()
    corrected = packet['corrected_kwh'][day]
    net = corrected[:, 0] - corrected[:, 1]
    kernels = _q2_kernels(packet, day, range(144))
    kappa = _terminal_kappa(data, day, price, battery, variable_price=False)
    policy, diagnostics = build_midnight_value_table(q, net, kernels, price, battery=battery,
                                                   step_kwh=50., terminal_kappa=kappa)
    grid, values = policy.grid, policy.values
    objectives = values[1:] + 5 * price[:, None] * battery.eta_d * grid[None, :]
    thresholds = np.array([grid[np.flatnonzero(row <= row.min() + 1e-10)[0]] for row in objectives])
    state = float(saved.soc_start.iloc[0])
    replay = []
    held = []
    for slot in range(144):
        action, explanation = execute_midnight_value_policy(q[slot], saved.load.iloc[slot],
                saved.pv.iloc[slot], state, price[slot], values[slot + 1], grid, battery=battery)
        replay.append(action)
        held.append(explanation['economic_hold_with_emergency'])
        state = action['soc_end']
    replay = pd.DataFrame(replay)
    differences = {name: float(np.max(np.abs(replay[name] - saved[name])))
                   for name in ('charge', 'discharge', 'soc_end', 'emergency', 'surplus')}
    assert max(differences.values()) < 1e-6, differences
    marginal = -np.diff(values, axis=1) / np.diff(grid)[None, :]
    assert values.shape == (145, 193) and marginal.shape == (145, 192)
    assert np.isfinite(values).all() and np.isfinite(marginal).all()
    assert thresholds[-1] == 1200
    np.testing.assert_allclose(values[-1], kappa * np.maximum(6000 - grid, 0), atol=1e-10)
    np.testing.assert_allclose(marginal[-1], np.where(grid[1:] <= 6000, kappa, 0), atol=1e-10)
    assert marginal.min() >= -1e-7
    out.mkdir(parents=True)
    encoding = 'utf-8-sig'
    curve = pd.DataFrame({'date': args.date, 'state_index': np.arange(145),
                          'time': [clock(t) for t in range(145)], 'time_hour': np.arange(145) / 6,
                          'actual_soc_kwh': np.r_[saved.soc_start.iloc[0], saved.soc_end],
                          'reserve_threshold_kwh': np.r_[thresholds, np.nan]})
    for name in ('load', 'pv', 'plan', 'charge', 'discharge', 'emergency', 'surplus'):
        curve[name + '_kwh'] = np.r_[saved[name], np.nan]
    curve['price_yuan_per_kwh'] = np.r_[price, np.nan]
    curve['forecast_load_kwh'] = np.r_[corrected[:, 0], np.nan]
    curve['forecast_pv_kwh'] = np.r_[corrected[:, 1], np.nan]
    curve['margin_kwh'] = np.r_[packet['margin_kwh'][day], np.nan]
    curve['emergency_flag'] = np.r_[(saved.emergency > 1e-7).astype(int), np.nan]
    curve['economic_hold_flag'] = np.r_[np.asarray(held, dtype=int), np.nan]
    curve['marginal_current_at_actual_soc_yuan_per_kwh'] = [
        marginal[t, min(max(np.searchsorted(grid, curve.actual_soc_kwh.iloc[t], side='right') - 1, 0), 191)]
        for t in range(145)]
    curve.to_csv(out / '阈值与运行轨迹.csv', index=False, encoding=encoding, float_format='%.15g')
    heatmap = pd.DataFrame({'state_index': np.repeat(np.arange(145), 192),
                            'time_hour': np.repeat(np.arange(145) / 6, 192),
                            'energy_lower_kwh': np.tile(grid[:-1], 145),
                            'energy_upper_kwh': np.tile(grid[1:], 145),
                            'energy_midpoint_kwh': np.tile((grid[:-1] + grid[1:]) / 2, 145),
                            'marginal_value_yuan_per_kwh': marginal.ravel()})
    heatmap.to_csv(out / '边际价值热力图.csv', index=False, encoding=encoding, float_format='%.15g')
    pd.DataFrame(values.T, index=pd.Index(grid, name='energy_kwh'),
                 columns=[clock(t) for t in range(145)]).to_csv(out / '原始价值函数矩阵.csv',
                    encoding=encoding, float_format='%.15g')
    pd.DataFrame(marginal.T, index=pd.Index((grid[:-1] + grid[1:]) / 2, name='energy_midpoint_kwh'),
                 columns=[clock(t) for t in range(145)]).to_csv(out / '边际价值矩阵.csv',
                    encoding=encoding, float_format='%.15g')
    residuals = []
    for previous in range(day - 14, day):
        for t in range(144):
            residuals.append({'date': str(data['dates'][previous]), 'slot': t, 'hour_group': t // 6,
                              'corrected_net_error_kwh': packet['corrected_net_errors_kwh'][previous, t]})
    pd.DataFrame(residuals).to_csv(out / '历史残差样本.csv', index=False, encoding=encoding, float_format='%.15g')
    np.savez_compressed(out / 'figure7_arrays.npz', time_hour=np.arange(145) / 6,
                        energy_grid_kwh=grid, energy_midpoint_kwh=(grid[:-1] + grid[1:]) / 2,
                        value_yuan=values, marginal_value_yuan_per_kwh=marginal,
                        reserve_threshold_kwh=thresholds,
                        actual_soc_kwh=curve.actual_soc_kwh.to_numpy(),
                        emergency_kwh=saved.emergency.to_numpy(), plan_kwh=q,
                        forecast_net_kwh=net, price_yuan_per_kwh=price,
                        residual_kernels_kwh=np.vstack(kernels), terminal_kappa=kappa)
    files = list(out.iterdir())
    metadata = {'date': args.date, 'case': 'q2 fixed_ridge_dp_natural',
                'source_scope': 'Frozen main Q2 plan and actual initial state; causal forecasts and DP recomputed using current repository code.',
                'not_frozen_greedy_comparison': True, 'forecast_information_cutoff': args.date + ' 00:00:00',
                'last_observed_date': str(data['dates'][day - 1]),
                'grid_step_kwh': 50, 'state_grid_points': 193, 'time_points': 145,
                'heatmap_rows': len(heatmap), 'kernel_samples_per_hour': 84,
                'derivative': '-(V[t,j+1]-V[t,j])/50; each value applies over [E[j],E[j+1]); no smoothing or clipping.',
                'threshold': 'argmin_j V[t+1,j]+5*p[t]*0.9*E[j], ties within 1e-10 select smallest energy.',
                'terminal_kappa_yuan_per_kwh': kappa, 'final_decision_threshold_kwh': float(thresholds[-1]),
                'marginal_min': float(marginal.min()), 'marginal_max': float(marginal.max()),
                'replay_maximum_differences_kwh': differences, 'diagnostics': diagnostics,
                'emergency_intervals': int((saved.emergency > 1e-7).sum()),
                'economic_hold_intervals': int(sum(held)),
                'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                             'scipy': scipy.__version__, 'pandas': pd.__version__, 'sklearn': sklearn.__version__},
                'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in [
                    ROOT / 'src/problem2.py', ROOT / 'src/microgrid.py', source_path,
                    ROOT / 'data/processed/annual_inputs.npz', ROOT / 'data/processed/actuals_power.csv']},
                'output_sha256': {p.name: digest(p) for p in files}}
    (out / '核验记录.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
