from __future__ import annotations
import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter
import numpy as np
from numba import njit
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix, csr_matrix, hstack, vstack

@dataclass(frozen=True)
class Battery:
    lower_kwh: float = 1200.0
    upper_kwh: float = 10800.0
    power_kw: float = 5000.0
    eta_charge: float = 0.9
    eta_discharge: float = 0.9
    dt_hours: float = 1.0 / 6.0

    def __post_init__(self):
        if not 0 <= self.lower_kwh <= self.upper_kwh:
            raise ValueError('Invalid battery energy bounds')
        if self.power_kw < 0 or self.dt_hours <= 0:
            raise ValueError('Invalid power or time step')
        if not (0 < self.eta_charge <= 1 and 0 < self.eta_discharge <= 1):
            raise ValueError('Invalid efficiency')

def _problem(price, load_kw, pv_kw, battery, initial, terminal):
    (p, load, pv) = (np.asarray(x, dtype=float) for x in (price, load_kw, pv_kw))
    if p.ndim != 1 or not p.shape == load.shape == pv.shape or (not p.size):
        raise ValueError('price/load/PV must be equal-length nonempty vectors')
    if not all((np.isfinite(x).all() for x in (p, load, pv))):
        raise ValueError('Nonfinite input')
    if min(p.min(), load.min(), pv.min()) < 0:
        raise ValueError('Q1 assumes nonnegative prices, load and PV')
    if terminal not in {'fixed', 'cyclic_free', 'none'}:
        raise ValueError('Unknown terminal condition')
    if terminal != 'cyclic_free' and (not battery.lower_kwh <= initial <= battery.upper_kwh):
        raise ValueError('Initial energy is outside battery bounds')
    n = len(p)
    m = 5 * n + 1
    (rows, cols, vals, rhs) = ([], [], [], [])
    net = (load - pv) * battery.dt_hours
    for t in range(n):
        rows.extend([t] * 4)
        cols.extend([t, n + t, 2 * n + t, 3 * n + t])
        vals.extend([1.0, -1.0, 1.0, -1.0])
        rhs.append(net[t])
    for t in range(n):
        rows.extend([n + t] * 4)
        cols.extend([4 * n + t + 1, 4 * n + t, n + t, 2 * n + t])
        vals.extend([1.0, -1.0, -battery.eta_charge, 1 / battery.eta_discharge])
        rhs.append(0.0)
    if terminal in {'fixed', 'cyclic_free'}:
        rows.extend([2 * n, 2 * n])
        cols.extend([4 * n + n, 4 * n])
        vals.extend([1.0, -1.0])
        rhs.append(0.0)
    aeq = coo_matrix((vals, (rows, cols)), shape=(len(rhs), m)).tocsr()
    low = np.zeros(m)
    high = np.full(m, np.inf)
    high[n:3 * n] = battery.power_kw * battery.dt_hours
    low[4 * n:] = battery.lower_kwh
    high[4 * n:] = battery.upper_kwh
    if terminal != 'cyclic_free':
        low[4 * n] = high[4 * n] = initial
    objective = np.zeros(m)
    objective[:n] = p
    return (p, net, aeq, np.asarray(rhs), low, high, objective)

def audit(schedule, price, load_kw, pv_kw, battery=Battery(), initial=6000.0, terminal='fixed'):
    (g, c, d, w, e) = (np.asarray(schedule[k]) for k in ('grid_kwh', 'charge_kwh', 'discharge_kwh', 'disposed_kwh', 'energy_kwh'))
    balance = g + np.asarray(pv_kw) * battery.dt_hours + d - np.asarray(load_kw) * battery.dt_hours - c - w
    state = np.diff(e) - battery.eta_charge * c + d / battery.eta_discharge
    bounds = max(0.0, battery.lower_kwh - e.min(), e.max() - battery.upper_kwh, max(c.max(), d.max()) - battery.power_kw * battery.dt_hours, -min(g.min(), c.min(), d.min(), w.min()))
    out = {'max_balance_residual_kwh': float(np.max(np.abs(balance))), 'max_state_residual_kwh': float(np.max(np.abs(state))), 'max_bound_violation_kwh': float(bounds), 'max_simultaneous_energy_kwh': float(np.minimum(c, d).max()), 'initial_residual_kwh': 0.0 if terminal == 'cyclic_free' else float(abs(e[0] - initial)), 'terminal_residual_kwh': 0.0 if terminal == 'none' else float(abs(e[-1] - e[0])), 'recomputed_cost_yuan': float(np.dot(price, g))}
    out['passed'] = bool(max((v for (k, v) in out.items() if k.endswith('kwh'))) <= 1e-05)
    return out

def _extract(x, n, battery, repair=True):
    (g, c, d, w, e) = (x[a:b].copy() for (a, b) in [(0, n), (n, 2 * n), (2 * n, 3 * n), (3 * n, 4 * n), (4 * n, 5 * n + 1)])
    if repair:
        rho = battery.eta_charge * battery.eta_discharge
        delta = np.minimum(c, d / rho)
        c -= delta
        d -= rho * delta
        w += (1 - rho) * delta
    for vector in (g, c, d, w):
        vector[np.abs(vector) < 1e-09] = 0.0
    return dict(grid_kwh=g, charge_kwh=c, discharge_kwh=d, disposed_kwh=w, energy_kwh=e)

def solve_lp(price, load_kw, pv_kw, battery=Battery(), initial=6000.0, terminal='fixed', lexicographic=True):
    start = perf_counter()
    (p, net, aeq, rhs, low, high, objective) = _problem(price, load_kw, pv_kw, battery, initial, terminal)
    options = {'primal_feasibility_tolerance': 1e-08, 'dual_feasibility_tolerance': 1e-08}
    result = linprog(objective, A_eq=aeq, b_eq=rhs, bounds=np.column_stack([low, high]), method='highs', options=options)
    if not result.success:
        raise RuntimeError(f'LP failed: {result.message}')
    finite_upper = np.isfinite(high)
    dual_objective = float(rhs @ result.eqlin.marginals + low @ result.lower.marginals + high[finite_upper] @ result.upper.marginals[finite_upper])
    dual_residual = float(np.max(np.abs(objective - aeq.T @ result.eqlin.marginals - result.lower.marginals - result.upper.marginals)))
    if abs(result.fun - dual_objective) > 0.01 or dual_residual > 1e-07:
        raise AssertionError('LP primal-dual certificate failed')
    n = len(p)
    x = result.x
    if lexicographic:
        secondary = np.zeros_like(objective)
        secondary[n:3 * n] = 1.0
        tie = linprog(secondary, A_ub=csr_matrix(objective[None, :]), b_ub=[result.fun + 1e-07], A_eq=aeq, b_eq=rhs, bounds=np.column_stack([low, high]), method='highs', options=options)
        if not tie.success:
            raise RuntimeError(f'Lexicographic LP failed: {tie.message}')
        x = tie.x
    schedule = _extract(x, n, battery)
    certificate = audit(schedule, p, load_kw, pv_kw, battery, initial, terminal)
    if not certificate['passed']:
        raise AssertionError(f'LP physical audit failed: {certificate}')
    return {**schedule, 'cost_yuan': float(p @ schedule['grid_kwh']), 'lower_bound_yuan': dual_objective, 'audit': certificate, 'primal_dual_gap_yuan': float(result.fun - dual_objective), 'max_dual_stationarity_residual': dual_residual, 'solve_seconds': perf_counter() - start, 'solver_status': result.message, 'battery': asdict(battery), 'terminal': terminal}

def solve_milp(price, load_kw, pv_kw, battery=Battery(), initial=6000.0, terminal='fixed'):
    start = perf_counter()
    (p, net, aeq, rhs, low, high, objective) = _problem(price, load_kw, pv_kw, battery, initial, terminal)
    (n, m) = (len(p), len(objective))
    eq = hstack([aeq, csr_matrix((aeq.shape[0], n))]).tocsr()
    (rows, cols, vals) = ([], [], [])
    q = battery.power_kw * battery.dt_hours
    for t in range(n):
        rows.extend([t, t, n + t, n + t])
        cols.extend([n + t, m + t, 2 * n + t, m + t])
        vals.extend([1, -q, 1, q])
    aub = coo_matrix((vals, (rows, cols)), shape=(2 * n, m + n)).tocsr()
    result = milp(np.r_[objective, np.zeros(n)], integrality=np.r_[np.zeros(m), np.ones(n)], bounds=Bounds(np.r_[low, np.zeros(n)], np.r_[high, np.ones(n)]), constraints=[LinearConstraint(eq, rhs, rhs), LinearConstraint(aub, np.full(2 * n, -np.inf), np.r_[np.zeros(n), np.full(n, q)])], options={'mip_rel_gap': 1e-10, 'time_limit': 180.0})
    if result.x is None:
        raise RuntimeError(f'MILP failed: {result.message}')
    schedule = _extract(result.x[:m], n, battery, repair=False)
    certificate = audit(schedule, p, load_kw, pv_kw, battery, initial, terminal)
    if not certificate['passed']:
        raise AssertionError(f'MILP audit failed: {certificate}')
    return {**schedule, 'cost_yuan': float(p @ schedule['grid_kwh']), 'audit': certificate, 'lower_bound_yuan': float(result.mip_dual_bound), 'mip_gap': float(result.mip_gap), 'solve_seconds': perf_counter() - start, 'solver_status': result.message}

@njit(cache=True)
def _grid_dp_kernel(price, net, grid, eta_c, eta_d, qmax, initial_index):
    (n, m) = (price.size, grid.size)
    values = np.full(m, np.inf)
    values[initial_index] = 0.0
    choices = np.full((n, m), -1, np.int32)
    step = grid[1] - grid[0]
    rmin = int(np.ceil(-qmax / eta_d / step - 1e-10))
    rmax = int(np.floor(qmax * eta_c / step + 1e-10))
    for t in range(n - 1, -1, -1):
        fresh = np.full(m, np.inf)
        for i in range(m):
            (jmin, jmax) = (max(0, i + rmin), min(m - 1, i + rmax))
            for j in range(jmin, jmax + 1):
                change = grid[j] - grid[i]
                if change >= 0:
                    grid_purchase = max(0.0, net[t] + change / eta_c)
                else:
                    grid_purchase = max(0.0, net[t] + change * eta_d)
                candidate = price[t] * grid_purchase + values[j]
                if candidate < fresh[i]:
                    fresh[i] = candidate
                    choices[t, i] = j
        values = fresh
    trajectory = np.empty(n + 1)
    trajectory[0] = grid[initial_index]
    idx = initial_index
    for t in range(n):
        idx = choices[t, idx]
        if idx < 0:
            raise ValueError('DP has no feasible path')
        trajectory[t + 1] = grid[idx]
    return (values[initial_index], trajectory)

def solve_grid_dp(price, load_kw, pv_kw, step_kwh, battery=Battery(), initial=6000.0):
    (p, net, *_) = _problem(price, load_kw, pv_kw, battery, initial, 'fixed')
    count = (battery.upper_kwh - battery.lower_kwh) / step_kwh
    index = (initial - battery.lower_kwh) / step_kwh
    if abs(count - round(count)) > 1e-07 or abs(index - round(index)) > 1e-07:
        raise ValueError('DP grid must contain both bounds and exact initial/terminal state')
    grid = battery.lower_kwh + np.arange(round(count) + 1) * step_kwh
    start = perf_counter()
    (value, e) = _grid_dp_kernel(p, net, grid, battery.eta_charge, battery.eta_discharge, battery.power_kw * battery.dt_hours, round(index))
    change = np.diff(e)
    c = np.maximum(change, 0) / battery.eta_charge
    d = np.maximum(-change, 0) * battery.eta_discharge
    g = np.maximum(net + c - d, 0)
    w = g + d - c - net
    schedule = dict(grid_kwh=g, charge_kwh=c, discharge_kwh=d, disposed_kwh=w, energy_kwh=e)
    certificate = audit(schedule, p, load_kw, pv_kw, battery, initial)
    if not certificate['passed'] or abs(value - p @ g) > 0.01:
        raise AssertionError(f'DP audit failed: {certificate}')
    return {**schedule, 'cost_yuan': float(p @ g), 'audit': certificate, 'step_kwh': step_kwh, 'state_count': len(grid), 'solve_seconds': perf_counter() - start}

def optimal_purchase_ranges(price, load_kw, pv_kw, indices, lower_bound, battery=Battery()):
    (p, net, aeq, rhs, low, high, obj) = _problem(price, load_kw, pv_kw, battery, 6000.0, 'fixed')
    rows = []
    for t in indices:
        extrema = []
        for sign in (1, -1):
            target = np.zeros_like(obj)
            target[t] = sign
            res = linprog(target, A_ub=csr_matrix(obj[None, :]), b_ub=[lower_bound + 1e-07], A_eq=aeq, b_eq=rhs, bounds=np.column_stack([low, high]), method='highs')
            if not res.success:
                raise RuntimeError(f'Optimal range LP failed: {res.message}')
            schedule = _extract(res.x, len(p), battery)
            check = audit(schedule, p, load_kw, pv_kw, battery)
            if not check['passed']:
                raise AssertionError(check)
            extrema.append(float(schedule['grid_kwh'][t]))
        rows.append(dict(slot_index=t, interval=_label(t), minimum_grid_kwh=extrema[0], maximum_grid_kwh=extrema[1], cost_tolerance_yuan=1e-07))
    return rows

def _label(t):
    return f'{t // 6:02d}:{t % 6 * 10:02d}-{(t + 1) // 6:02d}:{(t + 1) % 6 * 10:02d}'

def _write_csv(path, rows):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def run(input_path, out_dir):
    (input_path, out_dir) = (Path(input_path), Path(out_dir))
    data = np.load(input_path, allow_pickle=False)
    (p, load, pv) = (data[k] for k in ('q1_price', 'q1_load', 'q1_pv'))
    if len(p) != 144:
        raise ValueError('Official Q1 must have 144 ten-minute slots')
    out_dir.mkdir(parents=True, exist_ok=True)
    battery = Battery()
    lp = solve_lp(p, load, pv)
    integer = solve_milp(p, load, pv)
    delta = abs(lp['cost_yuan'] - integer['cost_yuan'])
    if delta > 0.01:
        raise AssertionError(f'LP/MILP objective mismatch: {delta}')
    dp_rows = []
    previous = np.inf
    for step in (100.0, 50.0, 25.0, 12.5, 6.25, 3.125, 1.5625):
        dp = solve_grid_dp(p, load, pv, step)
        gap = (dp['cost_yuan'] - lp['lower_bound_yuan']) / max(1.0, abs(lp['lower_bound_yuan']))
        if gap < -1e-08 or dp['cost_yuan'] > previous + 0.01:
            raise AssertionError('DP violates a lower bound or nested-grid monotonicity')
        previous = dp['cost_yuan']
        dp_rows.append(dict(step_kwh=step, state_count=dp['state_count'], cost_yuan=dp['cost_yuan'], lower_bound_yuan=lp['lower_bound_yuan'], relative_gap=gap, solve_seconds=dp['solve_seconds'], audit_passed=dp['audit']['passed']))
        print(f"Q1 DP step={step:g} kWh, cost={dp['cost_yuan']:.8f}, gap={100 * gap:.6f}%", flush=True)
        if step <= 6.25 and gap <= 0.001:
            break
    if dp_rows[-1]['relative_gap'] > 0.001:
        raise AssertionError('DP gap target not reached; extend grid refinement before publishing')
    _write_csv(out_dir / 'dp_convergence.csv', dp_rows)
    schedule = []
    for t in range(144):
        schedule.append(dict(slot_index=t, interval=_label(t), price_yuan_per_kwh=float(p[t]), load_kw=float(load[t]), pv_kw=float(pv[t]), grid_kwh=float(lp['grid_kwh'][t]), charge_kwh=float(lp['charge_kwh'][t]), discharge_kwh=float(lp['discharge_kwh'][t]), disposed_kwh=float(lp['disposed_kwh'][t]), energy_start_kwh=float(lp['energy_kwh'][t]), energy_end_kwh=float(lp['energy_kwh'][t + 1]), purchase_cost_yuan=float(p[t] * lp['grid_kwh'][t])))
    _write_csv(out_dir / 'schedule.csv', schedule)
    _write_csv(out_dir / 'dp_schedule.csv', [dict(slot_index=t, interval=_label(t), grid_kwh=float(dp['grid_kwh'][t]), charge_kwh=float(dp['charge_kwh'][t]), discharge_kwh=float(dp['discharge_kwh'][t]), energy_start_kwh=float(dp['energy_kwh'][t]), energy_end_kwh=float(dp['energy_kwh'][t + 1])) for t in range(144)])
    _write_csv(out_dir / 'optimal_ranges.csv', optimal_purchase_ranges(p, load, pv, [60, 72, 84, 96, 108, 120], lp['lower_bound_yuan']))
    capacity = []
    for usable in (4800.0, 7200.0, 9600.0, 12000.0, 14400.0):
        for power in (2500.0, 3750.0, 5000.0, 6250.0, 7500.0):
            b = Battery(lower_kwh=1200.0, upper_kwh=1200.0 + usable, power_kw=power)
            solution = solve_lp(p, load, pv, battery=b, lexicographic=False)
            capacity.append(dict(usable_capacity_kwh=usable, fixed_reserve_kwh=1200.0, upper_energy_kwh=1200.0 + usable, power_kw=power, cost_yuan=solution['cost_yuan'], grid_kwh=float(solution['grid_kwh'].sum()), audit_passed=solution['audit']['passed']))
    for usable in sorted({row['usable_capacity_kwh'] for row in capacity}):
        costs = [row['cost_yuan'] for row in capacity if row['usable_capacity_kwh'] == usable]
        if np.any(np.diff(costs) > 0.01):
            raise AssertionError('Power capacity monotonicity failed')
    for power in sorted({row['power_kw'] for row in capacity}):
        costs = [row['cost_yuan'] for row in capacity if row['power_kw'] == power]
        if np.any(np.diff(costs) > 0.01):
            raise AssertionError('Energy capacity monotonicity failed')
    _write_csv(out_dir / 'capacity_power.csv', capacity)
    sensitivity = []
    cases = [('main_each_way_90pct', battery, 6000.0, 'fixed'), ('roundtrip_90pct', Battery(eta_charge=np.sqrt(0.9), eta_discharge=np.sqrt(0.9)), 6000.0, 'fixed'), ('free_cyclic_initial', battery, 6000.0, 'cyclic_free'), ('NO_TERMINAL_INVALID_COMPARISON', battery, 6000.0, 'none')]
    cases += [(f'fixed_cyclic_initial_{initial:g}', battery, initial, 'fixed') for initial in (1200.0, 3000.0, 9000.0, 10800.0)]
    for (name, b, initial, terminal) in cases:
        sol = solve_lp(p, load, pv, b, initial, terminal)
        sensitivity.append(dict(case=name, cost_yuan=sol['cost_yuan'], grid_kwh=float(sol['grid_kwh'].sum()), initial_energy_kwh=float(sol['energy_kwh'][0]), terminal_energy_kwh=float(sol['energy_kwh'][-1]), eta_charge=b.eta_charge, eta_discharge=b.eta_discharge, cost_difference_from_main_yuan=sol['cost_yuan'] - lp['cost_yuan'], admissible_main_comparison=name != 'NO_TERMINAL_INVALID_COMPARISON'))
    _write_csv(out_dir / 'assumption_sensitivity.csv', sensitivity)
    no_battery_grid = np.maximum((load - pv) * battery.dt_hours, 0)
    grouped = []
    for a in range(0, 144, 24):
        grouped.append(dict(interval=f'{a // 6:02d}:00-{(a + 24) // 6:02d}:00', charge_kwh=float(lp['charge_kwh'][a:a + 24].sum()), discharge_kwh=float(lp['discharge_kwh'][a:a + 24].sum()), energy_start_kwh=float(lp['energy_kwh'][a]), energy_end_kwh=float(lp['energy_kwh'][a + 24])))
    _write_csv(out_dir / 'battery_4h.csv', grouped)
    summary = {'schema_version': '1.0', 'generated_by': 'problem1', 'question_id': 'Q1', 'generated_at': datetime.now(timezone.utc).isoformat(), 'status': 'validated', 'input_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(), 'battery': asdict(battery), 'initial_energy_kwh': 6000.0, 'terminal_energy_kwh': float(lp['energy_kwh'][-1]), 'cost_yuan': lp['cost_yuan'], 'lp_lower_bound_yuan': lp['lower_bound_yuan'], 'lp_primal_dual_gap_yuan': lp['primal_dual_gap_yuan'], 'lp_max_dual_stationarity_residual': lp['max_dual_stationarity_residual'], 'milp_cost_yuan': integer['cost_yuan'], 'milp_lower_bound_yuan': integer['lower_bound_yuan'], 'milp_gap': integer['mip_gap'], 'lp_milp_cost_difference_yuan': delta, 'lp_seconds': lp['solve_seconds'], 'milp_seconds': integer['solve_seconds'], 'dp_final_relative_gap': dp_rows[-1]['relative_gap'], 'dp_final_step_kwh': dp_rows[-1]['step_kwh'], 'grid_kwh': float(lp['grid_kwh'].sum()), 'charge_kwh': float(lp['charge_kwh'].sum()), 'discharge_kwh': float(lp['discharge_kwh'].sum()), 'disposed_kwh': float(lp['disposed_kwh'].sum()), 'battery_loss_kwh': float((1 - battery.eta_charge) * lp['charge_kwh'].sum() + (1 / battery.eta_discharge - 1) * lp['discharge_kwh'].sum()), 'no_battery_cost_yuan': float(p @ no_battery_grid), 'no_battery_grid_kwh': float(no_battery_grid.sum()), 'total_load_kwh': float(load.sum() * battery.dt_hours), 'total_pv_kwh': float(pv.sum() * battery.dt_hours), 'no_battery_disposed_kwh': float(np.maximum((pv - load) * battery.dt_hours, 0).sum()), 'state_lower_bound_slot_count': int(np.sum(np.abs(lp['energy_kwh'] - battery.lower_kwh) < 1e-05)), 'state_upper_bound_slot_count': int(np.sum(np.abs(lp['energy_kwh'] - battery.upper_kwh) < 1e-05)), 'charge_power_bound_slot_count': int(np.sum(np.abs(lp['charge_kwh'] - battery.power_kw * battery.dt_hours) < 1e-05)), 'discharge_power_bound_slot_count': int(np.sum(np.abs(lp['discharge_kwh'] - battery.power_kw * battery.dt_hours) < 1e-05)), 'savings_yuan': float(p @ no_battery_grid - lp['cost_yuan']), 'savings_fraction': float(1 - lp['cost_yuan'] / (p @ no_battery_grid)), 'lp_audit': lp['audit'], 'milp_audit': integer['audit'], 'dp_audit': dp['audit'], 'arbitrage_threshold': 'eta_charge*eta_discharge*p_high > p_low; necessary local criterion, not a complete policy', 'capacity_sensitivity_definition': 'Vary usable energy by increasing upper bound with lower reserve fixed at 1200 kWh; feasible sets are nested. This is not proportional SOC bounds under different nominal capacities.', 'evidence_boundary': 'Internal mathematical and numerical validation, not independent real-world deployment validation.', 'canonical_tie_break': 'Minimize AC charge+discharge throughput subject to primary cost <= optimum+1e-7 yuan; equal-cost trajectories may remain nonunique.'}
    (out_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return summary
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='data/processed/annual_inputs.npz')
    parser.add_argument('--out', default='results/c2026/q1')
    args = parser.parse_args()
    run(args.input, args.out)
