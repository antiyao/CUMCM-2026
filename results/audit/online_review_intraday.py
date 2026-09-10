import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from backtest import Simulator, STRATEGIES

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
output = ROOT / args.output
output.mkdir(parents=True, exist_ok=False)
actual = pd.read_csv(ROOT / 'data/processed/2026C/actuals.csv', parse_dates=['interval_start', 'interval_end', 'available_at'])
forecasts = pd.read_csv(ROOT / 'data/processed/2026C/forecasts.csv', parse_dates=['issue_time', 'available_at', 'target_time'])
fixed = pd.read_csv(ROOT / 'data/processed/2026C/q1.csv').price.to_numpy()
cutoff = pd.Timestamp('2025-02-01T06:00:00')
changed = actual.copy(deep=True)
changed.loc[changed.available_at > cutoff, ['load_kw', 'load_kwh', 'pv_kw', 'pv_kwh', 'price_variable']] *= 1.5
changed_forecasts = forecasts.copy(deep=True)
changed_forecasts.loc[changed_forecasts.available_at > cutoff, 'value'] += 137
strategy = 'q4_3_adjust_B'
destinations = [output / 'baseline', output / 'future-perturbed']
for data, issued, destination in [(actual, forecasts, destinations[0]), (changed, changed_forecasts, destinations[1])]:
    Simulator(data, issued, fixed).run([STRATEGIES[strategy]], '2025-02-01', destination)
frames = [pd.read_csv(p / strategy / 'intervals.csv.gz') for p in destinations]
decisions = [[json.loads(s) for s in (p / strategy / 'decisions.jsonl').read_text().splitlines()] for p in destinations]
events = [pd.read_csv(p / strategy / 'events.csv') for p in destinations]
checks = {'planned_grid_max_abs_kwh': float(abs(frames[0].planned_grid - frames[1].planned_grid).max())}
for hour in [0, 6]:
    pair = [next(d for d in rows if pd.Timestamp(d['cutoff']).hour == hour) for rows in decisions]
    checks[f'decision_{hour}h_objective_difference_yuan'] = abs(pair[0]['solver']['objective'] - pair[1]['solver']['objective'])
columns = ['date', 'issue_time', 'effective_from', 'interval_index', 'increase_kwh', 'decrease_kwh']
early = [f.loc[pd.to_datetime(f.issue_time) <= cutoff, columns] for f in events]
assert len(early[0]) > 0
assert early[0].to_dict('records') == early[1].to_dict('records')
assert all(value == 0 for value in checks.values())
checks['contract_event_rows_through_6h'] = len(early[0])
checks['contract_event_quantities_through_6h_identical'] = True
checks['settlement_realized_prices_may_differ_by_design'] = True
(output / 'checks.json').write_text(json.dumps(checks, indent=2) + '\n')
print(json.dumps(checks, indent=2))
