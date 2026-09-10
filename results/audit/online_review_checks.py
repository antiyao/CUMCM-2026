import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from backtest import DayAheadPlanner, STRATEGIES
from forecasting import ForecastProvider, historical_snapshot
from settlement import SettlementLedger

sources = [ROOT / 'src' / n for n in ['backtest.py', 'forecasting.py', 'settlement.py']]
fingerprints = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
actuals = pd.read_csv(ROOT / 'data/processed/2026C/actuals.csv', parse_dates=['interval_start', 'interval_end', 'available_at'])
fixed = pd.read_csv(ROOT / 'data/processed/2026C/q1.csv').price.to_numpy()
provider = ForecastProvider()
for d in sorted(actuals.date.unique())[1:31]:
    cutoff = pd.Timestamp(d)
    bundle = provider.predict(historical_snapshot(actuals, cutoff), cutoff)
    day = actuals.loc[actuals.date == d]
    provider.observe_completed_day(bundle, day, fixed)
cutoff = pd.Timestamp('2025-02-01')
modified = actuals.copy(deep=True)
future = modified.available_at > cutoff
modified.loc[future, ['load_kw', 'load_kwh', 'pv_kw', 'pv_kwh', 'price_variable']] *= 1000
baseline = provider.predict(historical_snapshot(actuals, cutoff), cutoff)
perturbed = provider.predict(historical_snapshot(modified, cutoff), cutoff)
planner = DayAheadPlanner()
a = planner.plan(baseline, STRATEGIES['q2_margin'], 6000, fixed)
b = planner.plan(perturbed, STRATEGIES['q2_margin'], 6000, fixed)
checks = {'future_actual_change_plan_max_abs_kwh': float(np.max(abs(a['grid'] - b['grid'])))}
shadow = copy.deepcopy(provider)
future_record = copy.deepcopy(shadow.records[-1])
future_record['available_at'] = cutoff + pd.Timedelta(days=1)
future_record['net_residual'] = np.full(144, 1e9)
future_record['candidate_mse'] = {k: [-1e20, -1e20, -1e20] for k in baseline.candidates}
shadow.records.append(future_record)
future_bundle = shadow.predict(historical_snapshot(actuals, cutoff), cutoff)
checks['future_validation_label_change_prediction_max_abs_kwh'] = float(max(
    np.max(abs(baseline.load - future_bundle.load)), np.max(abs(baseline.pv - future_bundle.pv))))
checks['future_validation_label_change_margin_max_abs_kwh'] = float(np.max(abs(baseline.margin - future_bundle.margin)))
ledger_cases = []
for interpretation in ['A', 'B']:
    for revisions in [[], [80], [120], [120, 80], [80, 100]]:
        ledger = SettlementLedger(np.array([100.]), interpretation)
        expected, previous = 100., 100.
        for n, revised in enumerate(revisions):
            delta = revised - previous
            expected += 1.5 * max(delta, 0) + (.5 if interpretation == 'A' else -.5) * max(-delta, 0)
            ledger.revise(np.array([revised]), 0, f'event-{n}')
            previous = revised
        result = float(ledger.settle(np.ones(1), np.zeros(1))['total_fee'][0])
        assert math.isclose(result, expected, abs_tol=1e-9)
        ledger_cases.append({'interpretation': interpretation, 'revisions': revisions, 'cost': result})
annual = ROOT / 'results/backtests/q2-annual'
reviewed = {}
for directory in sorted(annual.iterdir()):
    if not directory.is_dir():
        continue
    frame = pd.read_csv(directory / 'intervals.csv.gz')
    summary = json.loads((directory / 'summary.json').read_text())
    assert len(frame) == 334 * 144
    assert frame.date.nunique() == 334
    cost = math.fsum(float(r.planned_grid) * float(r.price) + 5 * float(r.price) * float(r.emergency)
                     for r in frame.itertuples())
    energy = 6000.
    max_soc_difference = 0.
    max_bus_difference = 0.
    for r in frame.itertuples():
        assert min(r.charge, r.discharge, r.emergency, r.planned_grid, r.unused) >= -1e-7
        assert r.charge <= 5000 / 6 + 1e-7 and r.discharge <= 5000 / 6 + 1e-7
        assert not (r.charge > 1e-7 and r.discharge > 1e-7)
        assert not (r.charge > 1e-7 and r.emergency > 1e-7)
        assert r.charge <= max(r.contract_grid + r.pv_kwh - r.load_kwh, 0) + 1e-7
        assert math.isclose(r.contract_grid, r.planned_grid, abs_tol=1e-7)
        assert math.isclose(r.soc_start, energy, abs_tol=1e-6)
        energy += .9 * r.charge
        energy -= r.discharge / .9
        assert 1200 - 1e-6 <= energy <= 10800 + 1e-6
        max_soc_difference = max(max_soc_difference, abs(energy - r.soc_end))
        bus = r.contract_grid + r.pv_kwh + r.discharge + r.emergency - r.load_kwh - r.charge - r.unused
        max_bus_difference = max(max_bus_difference, abs(bus))
        assert math.isclose(r.emergency, max(r.load_kwh-r.contract_grid-r.pv_kwh-r.discharge, 0), abs_tol=1e-7)
    assert abs(cost-summary['total_fee']) < 1e-6
    assert max_soc_difference < 1e-6 and max_bus_difference < 1e-6
    decisions = [json.loads(line) for line in (directory / 'decisions.jsonl').read_text().splitlines()]
    assert len(decisions) == 334
    assert all(pd.Timestamp(d['training_label_cutoff']) <= pd.Timestamp(d['cutoff']) for d in decisions)
    assert all(not d['attachment3_used'] for d in decisions)
    reviewed[directory.name] = {'days': len(decisions), 'total_cost_yuan': cost,
        'max_independent_soc_difference_kwh': max_soc_difference, 'max_bus_difference_kwh': max_bus_difference,
        'initial_soc_kwh': 6000., 'final_soc_kwh': energy,
        'contract_fee_recomputed_yuan': math.fsum(frame.planned_grid * frame.price),
        'emergency_kwh': math.fsum(frame.emergency),
        'soc_full_emergency_intervals': int(((frame.soc_start > 10799.999999) & (frame.emergency > 1e-7)).sum())}
checks['reviewed_code_unchanged_during_check'] = fingerprints == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
assert all(v == 0 for k, v in checks.items() if k.endswith('max_abs_kwh'))
assert checks['reviewed_code_unchanged_during_check']
report = {'code_hashes': fingerprints, 'checks': checks, 'ledger_cases': ledger_cases,
          'annual_q2_independent_results': reviewed,
          'scope': 'Q2 334-day outputs, Feb1 future-perturbation test, and scalar A/B event-ledger tests; Q3/Q4 full review pending'}
(ROOT / 'results/audit/online_review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
