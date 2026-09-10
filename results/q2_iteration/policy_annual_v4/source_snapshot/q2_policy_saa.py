"""Historical sample-average planning with the actual greedy battery policy.

The optimizer changes only the common day-ahead contract. Each residual day
is executed forward using the same current-interval greedy balance rule.
"""

import time

import numpy as np
from scipy.optimize import minimize

from dispatch import Battery


def greedy_saa_objective(grid, net_scenarios, price, *, initial=6000., battery=Battery()):
    """Return cost, branchwise adjoint gradient and causal forward trajectories.

    Derivatives are exact away from min/max switching points. At switching
    points the deterministic active branch supplies the nonsmooth optimizer.
    """
    q = np.asarray(grid, dtype=float)
    net = np.asarray(net_scenarios, dtype=float)
    p = np.asarray(price, dtype=float)
    if q.ndim != 1 or p.shape != q.shape or net.ndim != 2 or net.shape[1] != len(q) or not net.size:
        raise ValueError('Expected a shared T-vector grid, T-vector prices and S-by-T net demand')
    if not all(np.isfinite(a).all() for a in [q, net, p]) or (q < 0).any() or (p <= 0).any():
        raise ValueError('Finite inputs, nonnegative grid and positive prices are required')
    if not battery.minimum <= initial <= battery.maximum:
        raise ValueError('Initial storage is outside physical bounds')
    if not (0 < battery.eta_charge <= 1 and 0 < battery.eta_discharge <= 1 and battery.dt > 0 and battery.power_kw >= 0):
        raise ValueError('Invalid battery efficiency, duration or power')
    s_count, n = net.shape
    cap = battery.power_kw*battery.dt
    state = np.empty((s_count, n+1))
    state[:, 0] = initial
    charge, discharge, emergency, unused = [np.zeros_like(net) for _ in range(4)]
    state_state, state_grid, emergency_state, emergency_grid = [np.zeros_like(net) for _ in range(4)]
    for t in range(n):
        balance = q[t]-net[:, t]
        surplus = balance >= 0
        room = np.maximum((battery.maximum-state[:, t])/battery.eta_charge, 0)
        energy_available = np.maximum((state[:, t]-battery.minimum)*battery.eta_discharge, 0)
        charging_limits = np.column_stack([np.maximum(balance, 0), np.full(s_count, cap), room])
        discharging_limits = np.column_stack([np.maximum(-balance, 0), np.full(s_count, cap), energy_available])
        charging_mode = np.argmin(charging_limits, axis=1)
        discharging_mode = np.argmin(discharging_limits, axis=1)
        charge[:, t] = np.where(surplus, charging_limits.min(axis=1), 0)
        discharge[:, t] = np.where(surplus, 0, discharging_limits.min(axis=1))
        emergency[:, t] = np.where(surplus, 0, -balance-discharge[:, t])
        unused[:, t] = np.where(surplus, balance-charge[:, t], 0)
        state[:, t+1] = state[:, t]+battery.eta_charge*charge[:, t]-discharge[:, t]/battery.eta_discharge
        state_state[:, t] = np.where(surplus, charging_mode != 2, discharging_mode != 2)
        state_grid[:, t] = np.where(surplus,
            np.where(charging_mode == 0, battery.eta_charge, 0),
            np.where(discharging_mode == 0, 1/battery.eta_discharge, 0))
        emergency_grid[:, t] = np.where(~surplus & (discharging_mode != 0), -1., 0.)
        emergency_state[:, t] = np.where(~surplus & (discharging_mode == 2), -battery.eta_discharge, 0.)
    terminal_value = float(p.min()/battery.eta_charge)
    terminal_shortfall = np.maximum(6000-state[:, -1], 0)
    ordinary_cost = float(p @ q)
    scenario_emergency_cost = emergency @ (5*p)
    objective = ordinary_cost+float(scenario_emergency_cost.mean()+terminal_value*terminal_shortfall.mean())
    adjoint = np.where(state[:, -1] < 6000, -terminal_value, 0.)
    gradient = p.copy()
    for t in range(n-1, -1, -1):
        gradient[t] += np.mean(5*p[t]*emergency_grid[:, t]+adjoint*state_grid[:, t])
        adjoint = 5*p[t]*emergency_state[:, t]+adjoint*state_state[:, t]
    details = {'charge': charge, 'discharge': discharge, 'emergency': emergency, 'unused': unused,
               'soc': state, 'ordinary_cost': ordinary_cost,
               'expected_emergency_cost': float(scenario_emergency_cost.mean()),
               'terminal_shortfall_value_yuan_per_kwh': terminal_value,
               'expected_terminal_shortfall_cost': float(terminal_value*terminal_shortfall.mean()),
               'scenario_emergency_cost': scenario_emergency_cost}
    return objective, gradient, details


def _verify_greedy(grid, net, details, battery):
    c, d, u, w, e = [details[k] for k in ['charge', 'discharge', 'emergency', 'unused', 'soc']]
    cap = battery.power_kw*battery.dt
    checks = {
        'bus_residual_kwh': float(abs(grid[None, :]+d+u-c-w-net).max()),
        'soc_residual_kwh': float(abs(np.diff(e, axis=1)-battery.eta_charge*c+d/battery.eta_discharge).max()),
        'state_bound_violation_kwh': float(max(0, battery.minimum-e.min(), e.max()-battery.maximum)),
        'power_violation_kwh': float(max(0, c.max()-cap, d.max()-cap)),
        'nonnegative_violation_kwh': float(max(0, -min(grid.min(), c.min(), d.min(), u.min(), w.min()))),
        'simultaneous_charge_discharge_kwh': float(np.minimum(c, d).max()),
        'emergency_charge_overlap_kwh': float(np.minimum(c, u).max()),
        'emergency_only_load_residual_kwh': float(abs(u-np.maximum(net-grid[None, :]-d, 0)).max())}
    checks['passed'] = all(np.isfinite(value) and value <= 1e-6 for value in checks.values())
    return checks


def plan_greedy_saa(load, pv, price, residual_days, cutoff, residual_available_at,
                    initial, battery, initial_grid, max_history_days=14):
    load, pv, price, first = [np.asarray(a, dtype=float) for a in [load, pv, price, initial_grid]]
    errors = np.asarray(residual_days, dtype=float)
    available = np.asarray(residual_available_at, dtype='datetime64[ns]')
    decision = np.datetime64(str(cutoff), 'ns')
    if max_history_days not in (14, 28):
        raise ValueError('The predeclared history candidates are 14 and 28 days')
    if load.ndim != 1 or pv.shape != load.shape or price.shape != load.shape or first.shape != load.shape:
        raise ValueError('Point forecasts, price and initial contract must have matching shapes')
    if not np.isfinite(load).all() or not np.isfinite(pv).all() or (load < 0).any() or (pv < 0).any():
        raise ValueError('Load/PV forecasts must be finite and nonnegative')
    if errors.ndim != 2 or not len(errors) or errors.shape[1] != len(load) or len(available) != len(errors):
        raise ValueError('Provide complete residual days with matching availability times')
    if np.isnat(available).any() or np.isnat(decision) or (available > decision).any():
        raise ValueError('Residual labels are invalid or unavailable at the decision cutoff')
    selected = np.argsort(available, kind='stable')[-max_history_days:]
    net = load[None, :]-pv[None, :]+errors[selected]
    started = time.perf_counter()
    first_value, _, first_details = greedy_saa_objective(first, net, price, initial=initial, battery=battery)
    first_checks = _verify_greedy(first, net, first_details, battery)
    if not first_checks['passed']:
        raise AssertionError(first_checks)
    best_grid, best_value = first.copy(), first_value
    evaluations = 0

    def objective(q):
        nonlocal best_grid, best_value, evaluations
        value, gradient, _ = greedy_saa_objective(q, net, price, initial=initial, battery=battery)
        evaluations += 1
        if np.isfinite(value) and value < best_value-1e-8:
            best_grid, best_value = q.copy(), value
        return value, gradient

    result = minimize(objective, first.copy(), jac=True, method='L-BFGS-B',
                      bounds=[(0., None)]*len(first),
                      options={'maxiter': 50, 'maxls': 30, 'ftol': 1e-10, 'gtol': 1e-6})
    value, gradient, details = greedy_saa_objective(best_grid, net, price, initial=initial, battery=battery)
    checks = _verify_greedy(best_grid, net, details, battery)
    if not checks['passed'] or value > first_value+1e-7:
        best_grid, value, details, checks = first.copy(), first_value, first_details, first_checks
    return {'grid': best_grid, 'verification': checks,
            'scenario_terminal_soc': details['soc'][:, -1].copy(),
            'solver': {'method': 'L-BFGS-B on-policy historical SAA', 'status': int(result.status),
                'message': str(result.message), 'objective': float(value), 'initial_objective': float(first_value),
                'in_sample_improvement_yuan': float(first_value-value),
                'ordinary_cost': details['ordinary_cost'], 'expected_emergency_cost': details['expected_emergency_cost'],
                'expected_terminal_shortfall_cost': details['expected_terminal_shortfall_cost'],
                'terminal_shortfall_value_yuan_per_kwh': details['terminal_shortfall_value_yuan_per_kwh'],
                'initial_grid_retained': bool(np.array_equal(best_grid, first)),
                'iterations': int(result.nit), 'evaluations': evaluations, 'max_iterations': 50,
                'runtime_seconds': time.perf_counter()-started, 'scenario_count': len(selected),
                'max_history_days': max_history_days, 'cutoff': str(decision),
                'latest_residual_available_at': str(available[selected].max()),
                'selected_residual_rows': selected.tolist(),
                'policy': 'same piecewise-constant-interval greedy battery feedback as actual execution',
                'nonanticipativity': 'shared contract; identical observed history yields identical greedy actions',
                'optimality': 'best-found nonsmooth policy optimization; no global certificate',
                'gradient': 'forward branch Jacobians and reverse adjoint; deterministic active branch at kinks',
                'scenario_control_uses_future': False}}
