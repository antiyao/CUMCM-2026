import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from backtest import DayAheadPlanner, RealtimeController, STRATEGIES, replan_remaining
from dispatch import Battery
from forecasting import ForecastProvider, historical_snapshot, issued_pv_integrals
from settlement import SettlementLedger


@pytest.mark.parametrize('target,a,b', [(100, 100, 100), (120, 130, 130), (80, 110, 90)])
def test_settlement_examples(target, a, b):
    for interpretation, expected in [('A', a), ('B', b)]:
        ledger = SettlementLedger(np.array([100.]), interpretation)
        ledger.revise(np.array([target]), 0, '2025-02-01 06:00')
        assert ledger.settle([1], [0])['total_fee'][0] == expected


def test_multiple_contract_events_and_no_cycle_profit():
    for interpretation in ['A', 'B']:
        ledger = SettlementLedger(np.array([100.]), interpretation)
        ledger.revise([120.], 0, '06:00')
        ledger.revise([100.], 0, '12:00')
        assert len(ledger.events) == 2
        assert not ledger.revise([100.], 0, '18:00')
        assert ledger.settle([1], [0])['total_fee'][0] == (140 if interpretation == 'A' else 120)
    with pytest.raises(ValueError):
        SettlementLedger(np.array([100., 100.])).revise([80., 120.], 1, '06:00')


def test_future_actuals_do_not_change_plan():
    root = Path(__file__).resolve().parents[1]
    source = pd.read_csv(root/'data/processed/2026C/actuals.csv',
                         parse_dates=['interval_start', 'interval_end', 'available_at'])
    cutoff = pd.Timestamp('2025-02-01')
    perturbed = source.copy()
    future = perturbed.available_at > cutoff
    perturbed.loc[future, ['load_kwh', 'pv_kwh', 'price_variable']] *= 11
    first = ForecastProvider().predict(historical_snapshot(source, cutoff), cutoff)
    second = ForecastProvider().predict(historical_snapshot(perturbed, cutoff), cutoff)
    for name in ['load', 'pv', 'price', 'margin']:
        np.testing.assert_array_equal(getattr(first, name), getattr(second, name))
    fixed = pd.read_csv(root/'data/processed/2026C/q1.csv').price.to_numpy()
    a = DayAheadPlanner().plan(first, STRATEGIES['q2_margin'], 6000, fixed)
    b = DayAheadPlanner().plan(second, STRATEGIES['q2_margin'], 6000, fixed)
    np.testing.assert_array_equal(a['grid'], b['grid'])
    assert not first.metadata['attachment3_used']
    with pytest.raises(ValueError):
        ForecastProvider().predict(source, cutoff)


def test_forecast_versions_and_integration():
    issue = pd.Timestamp('2025-02-01 06:00')
    leads = np.arange(1, 25)
    released = pd.DataFrame({'issue_time': issue, 'available_at': issue,
                            'lead_time': leads, 'value': 600*leads})
    energy = issued_pv_integrals(released, issue, 0)
    assert len(energy) == 144
    assert np.isclose(energy.sum(), 24*14400/2)
    assert np.all(energy >= 0)
    future = released.copy()
    future['available_at'] += pd.Timedelta(hours=6)
    with pytest.raises(ValueError):
        issued_pv_integrals(future, issue, 0)
    with pytest.raises(ValueError):
        issued_pv_integrals(released, issue+pd.Timedelta(hours=6), 0)


@pytest.mark.parametrize('state,load,pv,q', [(1200, 1000, 0, 0), (10800, 0, 1000, 0),
                                           (6000, 1000, 0, 2000), (6000, 1000, 0, 0)])
def test_realtime_boundaries(state, load, pv, q):
    out = RealtimeController().act(state, load, pv, q, 6000, mode='greedy')
    assert 1200 <= out['soc_end'] <= 10800
    assert min(out['charge'], out['discharge']) == 0
    assert min(out['charge'], out['emergency']) == 0
    assert abs(q+pv+out['discharge']+out['emergency']-load-out['charge']-out['unused']) < 1e-8
    assert max(out['charge'], out['discharge']) <= 5000/6


def test_no_battery_and_perfect_prediction_reference():
    control = RealtimeController()
    off = control.act(6000, 1000, 0, 0, 6000, enabled=False)
    assert off['soc_end'] == 6000 and off['emergency'] == 1000
    assert Battery().dt*Battery().power_kw == pytest.approx(833.3333333333334)
    for net in [-200., 0., 200.]:
        out = control.act(6000, 1000, 0, 1000+net, 6000+net*(.9 if net > 0 else 1/.9))
        assert out['emergency'] == pytest.approx(0)


def test_contract_A_does_not_reduce_and_unchanged_option_remains():
    load, pv, price, old = np.full(12, 1000.), np.zeros(12), np.ones(12), np.full(12, 800.)
    fixed = replan_remaining(load, pv, price, old, 6000, Battery())
    amended = replan_remaining(load, pv, price, old, 6000, Battery(), True, 'A')
    assert np.min(amended['grid']-old) >= -1e-7
    assert amended['solver']['objective'] <= fixed['solver']['objective']+1e-6
    np.testing.assert_allclose(fixed['grid'], old, atol=1e-7)


def test_future_forecast_values_do_not_change_visible_version():
    issue = pd.Timestamp('2025-02-01 06:00')
    rows = []
    for hours in [0, 6]:
        release = issue+pd.Timedelta(hours=hours)
        for lead in range(1, 25):
            rows.append({'issue_time': release, 'available_at': release, 'lead_time': lead, 'value': float(lead)})
    forecasts = pd.DataFrame(rows)
    original = issued_pv_integrals(forecasts.loc[forecasts.available_at <= issue], issue, 3.)
    forecasts.loc[forecasts.available_at > issue, 'value'] *= 1000
    changed = issued_pv_integrals(forecasts.loc[forecasts.available_at <= issue], issue, 3.)
    np.testing.assert_array_equal(original, changed)
