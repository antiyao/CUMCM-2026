import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--run', default='results/backtests/full-evaluation-v1')
args = parser.parse_args()
run = ROOT / args.run
provenance = json.loads((run / 'provenance.json').read_text())
actuals = pd.read_csv(ROOT / 'data/processed/2026C/actuals.csv')
actuals = actuals[actuals.date >= '2025-02-01'].reset_index(drop=True)
fixed = pd.read_csv(ROOT / 'data/processed/2026C/q1.csv').price.to_numpy()
review = {}
for directory in sorted(run.iterdir()):
    if not directory.is_dir() or not (directory / 'intervals.csv.gz').exists():
        continue
    frame = pd.read_csv(directory / 'intervals.csv.gz')
    summary = json.loads((directory / 'summary.json').read_text())
    assert len(frame) == 48096 and frame.date.nunique() == 334
    assert frame[['date', 'interval_index']].equals(actuals[['date', 'interval_index']])
    for col in ['load_kwh', 'pv_kwh']:
        assert np.max(abs(frame[col] - actuals[col])) < 1e-7
    prices = actuals.price_variable.to_numpy() if directory.name.startswith('q4') else np.tile(fixed, 334)
    assert np.max(abs(frame.price - prices)) < 1e-9
    events = pd.read_csv(directory / 'events.csv')
    increase = np.zeros(len(frame))
    decrease = np.zeros(len(frame))
    date_map = {d: i for i, d in enumerate(frame.date.unique())}
    for event in events.itertuples():
        issue = pd.Timestamp(event.issue_time)
        i = date_map[event.date] * 144 + event.interval_index
        assert event.interval_index >= event.effective_from
        assert event.effective_from == issue.hour * 6
        assert issue <= pd.Timestamp(frame.interval_start.iloc[i])
        assert issue.hour in [6, 12, 18]
        assert event.increase_kwh >= -1e-7 and event.decrease_kwh >= -1e-7
        increase[i] += event.increase_kwh
        decrease[i] += event.decrease_kwh
    assert np.max(abs(increase - frame.contract_increase)) < 1e-6
    assert np.max(abs(decrease - frame.contract_decrease)) < 1e-6
    assert np.max(abs(frame.contract_grid - frame.planned_grid - increase + decrease)) < 1e-6
    refund = prices * decrease if summary['strategy']['interpretation'] == 'B' else np.zeros(len(frame))
    independent_cost = frame.planned_grid * prices + 1.5 * increase * prices + .5 * decrease * prices - refund + 5 * frame.emergency * prices
    assert np.max(abs(independent_cost - frame.total_fee)) < 1e-6
    assert abs(math.fsum(independent_cost) - summary['total_fee']) < 1e-6
    energy, max_state_error, max_bus_error = 6000., 0., 0.
    for row in frame.itertuples():
        values = [row.planned_grid, row.contract_grid, row.charge, row.discharge, row.emergency, row.unused]
        assert all(math.isfinite(v) and v >= -1e-7 for v in values)
        assert row.charge <= 5000 / 6 + 1e-7 and row.discharge <= 5000 / 6 + 1e-7
        assert not (row.charge > 1e-7 and row.discharge > 1e-7)
        assert row.charge <= max(row.contract_grid + row.pv_kwh - row.load_kwh, 0) + 1e-7
        assert math.isclose(row.soc_start, energy, abs_tol=1e-6)
        energy += .9 * row.charge
        energy -= row.discharge / .9
        assert 1200 - 1e-6 <= energy <= 10800 + 1e-6
        max_state_error = max(max_state_error, abs(energy - row.soc_end))
        residual = row.contract_grid + row.pv_kwh + row.discharge + row.emergency - row.load_kwh - row.charge - row.unused
        max_bus_error = max(max_bus_error, abs(residual))
        assert math.isclose(row.emergency, max(row.load_kwh-row.contract_grid-row.pv_kwh-row.discharge, 0), abs_tol=1e-7)
    assert max_state_error < 1e-6 and max_bus_error < 1e-6
    decisions = [json.loads(s) for s in (directory / 'decisions.jsonl').read_text().splitlines()]
    assert sum(d['decision_type'] == 'day_ahead' for d in decisions) == 334
    for d in decisions:
        assert pd.Timestamp(d['training_label_cutoff']) <= pd.Timestamp(d['cutoff'])
        if d['attachment3_used']:
            assert pd.Timestamp(d['forecast_issue_time']) <= pd.Timestamp(d['cutoff'])
        else:
            assert directory.name.startswith('q2') or directory.name.startswith('q4_2')
    review[directory.name] = {'days': 334, 'intervals': len(frame), 'cost_yuan': math.fsum(independent_cost),
                             'event_rows': len(events), 'final_soc_kwh': energy,
                             'max_state_difference_kwh': max_state_error,
                             'max_bus_difference_kwh': max_bus_error,
                             'emergency_kwh': math.fsum(frame.emergency),
                             'checked': True}
source_hash_agreement = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha
                         for p, sha in provenance['files'].items() if p.startswith('src/')}
report = {'run': args.run, 'strategies': review, 'current_code_matches_run_hashes': source_hash_agreement,
          'evidence_boundary': 'Independent output/ledger/physics review plus metadata cutoffs; targeted causal perturbation is separately recorded. No field validation.'}
output = ROOT / 'results/audit/online_review_full.json'
output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
