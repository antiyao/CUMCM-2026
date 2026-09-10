import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from dispatch import Battery, optimize
import q2_scenario
from q2_scenario import (_canonicalize_recourse, _repair_shared_emergency_charge,
                         plan_day_block_scenarios, select_day_blocks, solve_shared_contract)


def test_day_blocks_preserve_whole_observed_paths_and_weights():
    residuals = np.arange(12*24, dtype=float).reshape(12, 24)-100
    times = pd.date_range('2025-01-02', periods=12)
    blocks, weights, metadata = select_day_blocks(residuals, np.ones(24), n_scenarios=5,
        cutoff='2025-02-01', residual_available_at=times, max_history_days=8)
    assert weights.sum() == pytest.approx(1)
    assert len(blocks) == 5
    np.testing.assert_allclose(weights, .2)
    assert all(any(np.array_equal(block, row) for row in residuals[-8:]) for block in blocks)
    assert metadata['history_days'] == 8
    assert not metadata['independent_time_shuffle']
    assert 'not exact empirical frequencies' in metadata['probability_basis']


def test_future_labels_rejected_and_inputs_not_mutated():
    residuals = np.zeros((3, 4))
    original = residuals.copy()
    with pytest.raises(ValueError, match='unavailable'):
        select_day_blocks(residuals, np.ones(4), cutoff='2025-02-01',
                          residual_available_at=['2025-01-01', '2025-01-02', '2025-02-02'])
    np.testing.assert_array_equal(residuals, original)


def test_identical_scenarios_match_deterministic_real_q1():
    root = Path(__file__).resolve().parents[1]
    q1 = pd.read_csv(root/'data/processed/2026C/q1.csv')
    result = solve_shared_contract(np.tile((q1.load_kwh-q1.pv_kwh).to_numpy(), (3, 1)), q1.price.to_numpy())
    deterministic = optimize(q1.load_kwh, q1.pv_kwh, q1.price, relax=True)
    assert result['solver']['objective'] == pytest.approx(deterministic['solver']['objective'], abs=1e-5)
    assert result['recourse']['emergency'].sum() < 1e-6
    assert result['verification']['passed']
    assert not result['solver']['recourse_implementable']
    assert result['grid'].shape == (144,)


def test_no_battery_newsvendor_uses_shared_contract():
    battery = Battery(minimum=6000, maximum=6000, power_kw=5000)
    result = solve_shared_contract([[0.], [10.], [20.]], [1.], battery=battery)
    assert result['grid'][0] == pytest.approx(20.)
    assert result['solver']['objective'] == pytest.approx(20.)
    assert result['recourse']['charge'].sum() == pytest.approx(0.)


def test_emergency_charge_relaxation_is_not_executed():
    battery = Battery(minimum=0, maximum=10, power_kw=10, eta_charge=1, eta_discharge=1, dt=1)
    result = solve_shared_contract([[5., 0.], [10., 10.]], [.2, .5], probabilities=[.95, .05],
                                   initial=0, terminal=0, battery=battery)
    assert result['verification']['passed']
    assert result['solver']['milp_fallback']
    assert result['solver']['lp_lower_bound'] == pytest.approx(2.3125)
    assert result['solver']['objective'] == pytest.approx(2.5)
    assert np.minimum(result['recourse']['charge'], result['recourse']['emergency']).max() < 1e-6
    assert result['solver']['lp_lower_bound'] <= result['solver']['objective']+1e-7


def test_zero_error_wrapper_and_bounds():
    load, pv, price = np.full(6, 500.), np.zeros(6), np.ones(6)
    result = plan_day_block_scenarios(load, pv, price, np.zeros((3, 6)),
        cutoff='2025-02-01', residual_available_at=['2025-01-29', '2025-01-30', '2025-01-31'], n_scenarios=3)
    assert result['scenario_metadata']['distinct_scenarios'] == 1
    assert result['solver']['objective'] == pytest.approx(3000.)
    assert result['verification']['passed']


def test_equal_probability_repair_preserves_states_bus_and_cost():
    b = Battery()
    grid = np.array([100.])
    c, d, u, w = np.zeros((5, 1)), np.zeros((5, 1)), np.zeros((5, 1)), np.zeros((5, 1))
    c[0, 0], u[0, 0] = 50., 25.
    net = grid[None, :]+d+u-c-w
    energy_delta = b.eta_charge*c-d/b.eta_discharge
    original_cost = grid.sum()+5*np.mean(u.sum(axis=1))
    fixed_q, fixed_u, fixed_w, increase, eligible = _repair_shared_emergency_charge(
        grid, c, u, w, np.full(5, .2), 5.)
    assert eligible and increase[0] == pytest.approx(25.)
    np.testing.assert_allclose(fixed_q[None, :]+d+fixed_u-c-fixed_w, net)
    np.testing.assert_array_equal(b.eta_charge*c-d/b.eta_discharge, energy_delta)
    assert fixed_q.sum()+5*np.mean(fixed_u.sum(axis=1)) == pytest.approx(original_cost)
    assert np.minimum(c, fixed_u).max() == 0


def test_cycle_and_emergency_waste_cancellation_reduces_cost():
    b = Battery()
    c, d, u, w = (np.array([[x]]) for x in [100., 20., 30., 10.])
    original_net = d+u-c-w
    original_energy = b.eta_charge*c-d/b.eta_discharge
    fixed_c, fixed_d, fixed_u, fixed_w = _canonicalize_recourse(c, d, u, w, b)
    np.testing.assert_allclose(fixed_d+fixed_u-fixed_c-fixed_w, original_net)
    np.testing.assert_allclose(b.eta_charge*fixed_c-fixed_d/b.eta_discharge, original_energy)
    assert fixed_u[0, 0] < u[0, 0]
    assert np.minimum(fixed_c, fixed_d).max() == 0
    assert np.minimum(fixed_u, fixed_w).max() == 0


def test_unproven_lp_primal_is_not_labelled_lower_bound(monkeypatch):
    real_milp = q2_scenario.milp
    def unproven(*args, **kwargs):
        result = real_milp(*args, **kwargs)
        result.status = 1
        result.message = 'Synthetic status-only test: feasible point without certificate'
        return result
    monkeypatch.setattr(q2_scenario, 'milp', unproven)
    result = solve_shared_contract([[100.]], [1.])
    assert result['solver']['lp_status'] == 1
    assert result['solver']['lp_lower_bound'] is None
    assert result['solver']['lp_primal_objective'] == pytest.approx(100.)
