import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'src'))
from backtest import RealtimeController, checked_optimization
from dispatch import Battery

data = np.load(AUDIT / 'reproduction/data/inputs.npz', allow_pickle=False)
load = data['load_kw'] / 6
solar = data['pv_kw'] / 6
prices = data['price']
external_load = load[24:358].copy()
external_pv = np.array([solar[d - 7:d].mean(axis=0) for d in range(31, 365)])
cached = pd.read_csv(ROOT / 'results/backtests/full-evaluation-v1/forecast_evaluation.csv.gz',
                     usecols=['date', 'forecast_group', 'interval_index', 'predicted_load_kwh', 'predicted_pv_kwh'])
cached = cached[(cached.date >= '2025-02-01') & (cached.forecast_group == 'fixed_historical_pv')].sort_values(['date', 'interval_index'])
assert len(cached) == 334 * 144
local_load = cached.predicted_load_kwh.to_numpy().reshape(334, 144)
local_pv = cached.predicted_pv_kwh.to_numpy().reshape(334, 144)
battery = Battery()
controller = RealtimeController(battery)
results = {}
for predictor, predicted_load, predicted_pv in [('external_fixed', external_load, external_pv), ('local_selected', local_load, local_pv)]:
    for mode in ['reference', 'greedy']:
        energy = 6000.
        planned_cost = emergency_cost = emergency_kwh = unused_kwh = 0.
        for d in range(334):
            planned = checked_optimization(predicted_load[d], predicted_pv[d], prices, energy, battery)
            planned_cost += float(np.dot(prices, planned['grid']))
            for t in range(144):
                action = controller.act(energy, load[d + 31, t], solar[d + 31, t], planned['grid'][t],
                                        planned['soc'][t + 1], True, mode)
                energy = action['soc_end']
                emergency_kwh += action['emergency']
                emergency_cost += 5 * prices[t] * action['emergency']
                unused_kwh += action['unused']
        name = predictor + '_' + mode
        results[name] = {'planned_yuan': planned_cost, 'emergency_yuan': emergency_cost,
                         'total_yuan': planned_cost + emergency_cost,
                         'emergency_kwh': emergency_kwh, 'final_kwh': energy,
                         'unutilized_kwh': unused_kwh}
        print(name, results[name], flush=True)
differences = {
    'predictor_change_external_to_local_with_reference_yuan': results['local_selected_reference']['total_yuan'] - results['external_fixed_reference']['total_yuan'],
    'predictor_change_external_to_local_with_greedy_yuan': results['local_selected_greedy']['total_yuan'] - results['external_fixed_greedy']['total_yuan'],
    'controller_change_reference_to_greedy_with_external_yuan': results['external_fixed_greedy']['total_yuan'] - results['external_fixed_reference']['total_yuan'],
    'controller_change_reference_to_greedy_with_local_yuan': results['local_selected_greedy']['total_yuan'] - results['local_selected_reference']['total_yuan'],
}
report = {'description': 'Factorial baseline diagnosis only: no margin, identical local optimizer/battery, two forecast sources and two execution controls. Forecast sources are precomputed causally; not independent unseen-data validation.',
          'results': results, 'differences': differences}
(AUDIT / 'baseline_bridge.json').write_text(json.dumps(report, indent=2) + '\n')
