import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from backtest import RealtimeController
from dispatch import Battery
from q2_policy_saa import greedy_saa_objective, plan_greedy_saa


def test_piecewise_gradient_matches_finite_differences_away_from_kinks():
    rng = np.random.default_rng(218)
    net = rng.uniform(50, 650, (5, 17))
    grid = rng.uniform(150, 600, 17)
    price = rng.uniform(.3, 1.4, 17)
    b = Battery(minimum=1200, maximum=2100, power_kw=2100)
    _, gradient, _ = greedy_saa_objective(grid, net, price, initial=1553, battery=b)
    numeric = np.empty(17)
    for t in range(17):
        delta = np.zeros(17)
        delta[t] = 1e-4
        high = greedy_saa_objective(grid+delta, net, price, initial=1553, battery=b)[0]
        low = greedy_saa_objective(grid-delta, net, price, initial=1553, battery=b)[0]
        numeric[t] = (high-low)/2e-4
    np.testing.assert_allclose(gradient, numeric, atol=2e-6, rtol=2e-6)


def test_forward_simulation_matches_independent_existing_greedy_controller():
    rng = np.random.default_rng(2026)
    load, pv, q = rng.uniform(400, 1200, 40), rng.uniform(0, 700, 40), rng.uniform(0, 900, 40)
    _, _, detail = greedy_saa_objective(q, (load-pv)[None, :], np.ones(40))
    control, state = RealtimeController(), 6000.
    for t in range(40):
        action = control.act(state, load[t], pv[t], q[t], 6000, mode='greedy')
        state = action['soc_end']
        for key in ['charge', 'discharge', 'emergency', 'unused']:
            assert detail[key][0, t] == pytest.approx(action[key], abs=1e-8)
        assert detail['soc'][0, t+1] == pytest.approx(state, abs=1e-8)


def test_identical_prefixes_have_identical_actions_despite_changed_future():
    q, price = np.full(12, 600.), np.ones(12)
    net = np.vstack([np.full(12, 800.), np.r_[np.full(6, 800.), np.full(6, -500.)]])
    _, _, result = greedy_saa_objective(q, net, price)
    for key in ['charge', 'discharge', 'emergency', 'unused']:
        np.testing.assert_array_equal(result[key][0, :6], result[key][1, :6])
    np.testing.assert_array_equal(result['soc'][0, :7], result['soc'][1, :7])


def test_optimizer_retains_initial_or_improves_past_policy_objective():
    result = plan_greedy_saa(np.full(8, 700.), np.full(8, 100.), np.linspace(.3, 1.3, 8),
        np.array([np.full(8, -100.), np.full(8, 80.), np.arange(8)*20]),
        '2025-02-01', ['2025-01-29', '2025-01-30', '2025-01-31'],
        6000., Battery(), np.full(8, 800.), max_history_days=14)
    assert result['verification']['passed']
    assert result['solver']['objective'] <= result['solver']['initial_objective']+1e-7
    assert not result['solver']['scenario_control_uses_future']
    assert result['solver']['max_iterations'] == 50


def test_future_labels_rejected():
    with pytest.raises(ValueError, match='unavailable'):
        plan_greedy_saa(np.ones(4), np.zeros(4), np.ones(4), np.zeros((2, 4)),
            '2025-02-01', ['2025-01-31', '2025-02-02'], 6000, Battery(), np.ones(4))


def test_full_empty_battery_and_no_battery_limits():
    battery = Battery(minimum=6000, maximum=6000)
    _, gradient, result = greedy_saa_objective([100., 100.], [[300., -100.]], [1., 1.], battery=battery)
    np.testing.assert_array_equal(result['soc'], 6000.)
    np.testing.assert_array_equal(result['charge'], 0.)
    np.testing.assert_array_equal(result['discharge'], 0.)
    np.testing.assert_allclose(result['emergency'], [[200., 0.]])
    np.testing.assert_allclose(gradient, [-4., 1.])
