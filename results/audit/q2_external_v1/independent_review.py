import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import platform

import numpy as np
import pandas as pd
import scipy


ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
SOURCE = Path('/Users/anti_yao/Downloads/C2026_Q2_优化第一轮')
NAMES = ['A_baseline', 'B_bias_corrected', 'C_risk_only', 'D_bias_and_risk']


def independent_forecasts(load, solar, corrected):
    demand = load / 6
    pv = solar / 6
    prediction_load = np.full_like(demand, np.nan)
    prediction_pv = np.full_like(pv, np.nan)
    for day in range(7, len(load)):
        prediction_load[day] = demand[day - 7]
        prediction_pv[day] = np.sum(pv[day - 7:day], axis=0) / 7
    original_load = prediction_load.copy()
    original_pv = prediction_pv.copy()
    if corrected:
        for day in range(10, len(load)):
            correction_load = np.sum(demand[day - 3:day] - original_load[day - 3:day], axis=0) / 3
            correction_pv = np.sum(pv[day - 3:day] - original_pv[day - 3:day], axis=0) / 3
            prediction_load[day] = np.maximum(original_load[day] + correction_load, 0)
            prediction_pv[day] = np.maximum(original_pv[day] + correction_pv, 0)
    return prediction_load, prediction_pv


def review_trace(directory, name, load, pv, prices):
    summary = json.loads((directory / name / 'summary.json').read_text())
    frame = pd.read_csv(directory / name / 'trace.csv')
    corrected = name in ['B_bias_corrected', 'D_bias_and_risk']
    predicted_load, predicted_pv = independent_forecasts(load, pv, corrected)
    errors = (load - pv) / 6 - predicted_load + predicted_pv
    margins = np.zeros((365, 144))
    if summary['q']:
        for day in range(31, 365):
            for hour in range(24):
                previous_errors = errors[max(7, day - 14):day, hour * 6:hour * 6 + 6]
                value = max(0, np.quantile(previous_errors.ravel(), summary['q']))
                margins[day, hour * 6:hour * 6 + 6] = value
    assert len(frame) == 334 * 144
    expected_dates = np.repeat(pd.date_range('2025-02-01', '2025-12-31').strftime('%Y-%m-%d'), 144)
    assert np.array_equal(frame.date, expected_dates)
    assert np.array_equal(frame.step, np.tile(np.arange(144), 334))
    checks = {
        'input_load_max_abs_kwh': float(np.max(abs(frame.actual_load_kwh - load[31:].ravel() / 6))),
        'input_pv_max_abs_kwh': float(np.max(abs(frame.actual_pv_kwh - pv[31:].ravel() / 6))),
        'input_price_max_abs': float(np.max(abs(frame.price - np.tile(prices, 334)))),
        'forecast_load_max_abs_kwh': float(np.max(abs(frame.forecast_load_kwh - predicted_load[31:].ravel()))),
        'forecast_pv_max_abs_kwh': float(np.max(abs(frame.forecast_pv_kwh - predicted_pv[31:].ravel()))),
        'margin_max_abs_kwh': float(np.max(abs(frame.risk_buffer_kwh - margins[31:].ravel()))),
    }
    expected_cutoffs = np.repeat(np.arange(30, 364), 144)
    assert np.array_equal(frame.forecast_last_day_index, expected_cutoffs)
    assert np.array_equal(frame.residual_last_day_index, expected_cutoffs)
    energy = 6000.
    worst_state = worst_bus = worst_action = 0.
    for row in frame.itertuples():
        grid = row.planned_grid_kwh
        residual = grid + row.actual_pv_kwh - row.actual_load_kwh
        if residual >= 0:
            charge = min(residual, 5000 / 6, max(0., (10800 - energy) / .9))
            discharge = emergency = 0.
            unused = residual - charge
        else:
            charge = unused = 0.
            discharge = min(-residual, 5000 / 6, max(0., .9 * (energy - 1200)))
            emergency = -residual - discharge
        worst_action = max(worst_action, abs(charge - row.charge_kwh), abs(discharge - row.discharge_kwh),
                           abs(emergency - row.emergency_kwh), abs(unused - row.unutilized_kwh))
        assert math.isclose(energy, row.energy_start_kwh, abs_tol=1e-6)
        assert all(v >= -1e-7 and math.isfinite(v) for v in [grid, charge, discharge, emergency, unused])
        assert not (charge > 1e-7 and emergency > 1e-7)
        energy += .9 * charge - discharge / .9
        assert 1200 - 1e-6 <= energy <= 10800 + 1e-6
        worst_state = max(worst_state, abs(energy - row.energy_end_kwh))
        worst_bus = max(worst_bus, abs(grid + row.actual_pv_kwh + discharge + emergency - row.actual_load_kwh - charge - unused))
    plan_cost = math.fsum(frame.planned_grid_kwh * frame.price)
    emergency_cost = math.fsum(5 * frame.emergency_kwh * frame.price)
    checks.update({'state_max_abs_kwh': worst_state, 'bus_max_abs_kwh': worst_bus,
                   'greedy_action_max_abs_kwh': worst_action,
                   'cost_max_abs_yuan': max(abs(plan_cost - summary['planned_yuan']),
                                          abs(emergency_cost - summary['emergency_yuan']),
                                          abs(plan_cost + emergency_cost - summary['total_yuan']))})
    assert all(v < 1e-6 for v in checks.values()), checks
    daily = pd.read_csv(directory / name / 'daily.csv')
    for d, values in enumerate(daily.itertuples()):
        part = frame.iloc[d * 144:(d + 1) * 144]
        assert values.date == part.date.iloc[0]
        assert abs(values.total_yuan - math.fsum(part.planned_cost_yuan + part.emergency_cost_yuan)) < 1e-6
        assert abs(values.initial_kwh - part.energy_start_kwh.iloc[0]) < 1e-6
        assert abs(values.final_kwh - part.energy_end_kwh.iloc[-1]) < 1e-6
    return {'passed': True, 'rows': len(frame), 'q': summary['q'], 'total_yuan': plan_cost + emergency_cost,
            'planned_yuan': plan_cost, 'emergency_yuan': emergency_cost,
            'emergency_kwh': math.fsum(frame.emergency_kwh), 'unutilized_kwh': math.fsum(frame.unutilized_kwh),
            'initial_kwh': 6000., 'final_kwh': energy,
            'net_load_mae_kw': float(np.mean(abs(errors[31:])) * 6), 'checks': checks}


def main():
    with np.load(SOURCE / 'data/inputs.npz', allow_pickle=False) as data:
        load, pv, prices = data['load_kw'].copy(), data['pv_kw'].copy(), data['price'].copy()
    results = {name: review_trace(SOURCE / 'results', name, load, pv, prices) for name in NAMES}
    copied = AUDIT / 'reproduction'
    reproduced = {name: review_trace(copied / 'results', name, load, pv, prices) for name in NAMES}
    sys.path.insert(0, str(copied))
    spec = importlib.util.spec_from_file_location('reviewed_external_experiment', copied / 'run_experiment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = {}
    for corrected in [False, True]:
        before, residual_before = module.forecast_and_errors(load, pv, corrected)
        altered_load, altered_pv = load.copy(), pv.copy()
        altered_load[31:] *= 3
        altered_pv[31:] *= 2
        after, residual_after = module.forecast_and_errors(altered_load, altered_pv, corrected)
        key = 'corrected' if corrected else 'base'
        checks[key + '_feb1_forecast_difference_kwh'] = float(np.max(abs(before[31] - after[31])))
        checks[key + '_feb1_margin_difference_kwh'] = float(np.max(abs(module.safety(residual_before[:31], .8) - module.safety(residual_after[:31], .8))))
    assert all(v == 0 for v in checks.values())
    baseline = json.loads((AUDIT / 'source_manifest.json').read_text())
    current = {str(p.relative_to(SOURCE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.rglob('*') if p.is_file()}
    assert current == baseline['full_input_hashes_before']
    parameters = json.loads((copied / 'results/selected_parameters.json').read_text())
    source_parameters = json.loads((SOURCE / 'results/selected_parameters.json').read_text())
    assert parameters == source_parameters == {'base': .8, 'corrected': .8}
    report = {'external_results_independently_verified': results,
              'local_rerun_independently_verified': reproduced,
              'selected_parameters_match': parameters,
              'local_environment': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
              'external_environment': json.loads((SOURCE / 'results/environment.json').read_text()),
              'future_perturbation_checks': checks,
              'original_directory_unchanged': True,
              'scope': 'All downloaded trajectories, their source inputs, prefix forecasts, risk margins, greedy actions and actual billings. External original files were not written.'}
    (AUDIT / 'independent_review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
