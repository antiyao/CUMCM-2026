"""Shared-contract historical day-block planning with anticipative recourse.

Only ``grid`` is a day-ahead decision. Scenario battery trajectories are an
optimistic planning proxy; an independent causal controller must execute it.
"""

import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from dispatch import Battery


def select_day_blocks(residual_days, price, *, n_scenarios=5,
                      max_history_days=28, cutoff, residual_available_at):
    residuals = np.asarray(residual_days, dtype=float)
    price = np.asarray(price, dtype=float)
    availability = np.asarray(residual_available_at, dtype='datetime64[ns]')
    decision = np.datetime64(str(cutoff), 'ns')
    if residuals.ndim != 2 or residuals.shape[1] != len(price) or not len(residuals):
        raise ValueError('Provide at least one complete residual day, with one value per price interval')
    if len(availability) != len(residuals) or np.isnat(availability).any() or np.isnat(decision):
        raise ValueError('Each residual day needs a valid label-availability time')
    if (availability > decision).any():
        raise ValueError('Scenario source contains labels unavailable at the decision cutoff')
    if not np.isfinite(residuals).all() or not np.isfinite(price).all() or (price <= 0).any():
        raise ValueError('Residuals must be finite and planning prices strictly positive')
    if n_scenarios not in (3, 5) or max_history_days < 1:
        raise ValueError('Predeclared candidate counts are 3 or 5; history length must be positive')
    order = np.argsort(availability, kind='stable')[-max_history_days:]
    past = residuals[order]
    score = np.maximum(past, 0) @ price
    strata = np.array_split(np.argsort(score, kind='stable'), min(n_scenarios, len(past)))
    indices, weights = [], []
    for stratum in strata:
        block = past[stratum]
        distances = np.mean(np.abs(block[:, None, :]-block[None, :, :]), axis=2)
        medoid = int(stratum[np.argmin(distances.sum(axis=1))])
        indices.append(int(order[medoid]))
        weights.append(len(stratum)/len(past))
    blocks = residuals[indices].copy()
    unique, inverse = np.unique(blocks, axis=0, return_inverse=True)
    probabilities = np.zeros(len(unique))
    source_groups = [[] for _ in unique]
    for j, group in enumerate(inverse):
        probabilities[group] += weights[j]
        source_groups[group].append(indices[j])
    return unique, probabilities, {
        'selection': 'rank by tariff-weighted positive daily residual, then full-day L1 medoid within equal-count strata',
        'cutoff': str(decision), 'latest_residual_available_at': str(availability[order].max()),
        'history_days': len(past), 'requested_scenarios': n_scenarios,
        'distinct_scenarios': len(unique), 'source_row_groups': source_groups,
        'source_available_at_groups': [[str(availability[i]) for i in group] for group in source_groups],
        'probabilities': probabilities.tolist(), 'independent_time_shuffle': False,
        'scenario_reduction': 'representative-day approximation, not full empirical-distribution optimization'}


def _canonicalize_recourse(charge, discharge, unused, battery):
    removed_charge = np.minimum(charge, discharge/(battery.eta_charge*battery.eta_discharge))
    charge = charge-removed_charge
    discharge = discharge-battery.eta_charge*battery.eta_discharge*removed_charge
    unused = unused+(1-battery.eta_charge*battery.eta_discharge)*removed_charge
    return charge, discharge, unused


def solve_shared_contract(net_load_scenarios, price, *, probabilities=None,
                          initial=6000., terminal=6000., battery=Battery(),
                          emergency_multiplier=5., time_limit=15., mip_gap=1e-6):
    net = np.asarray(net_load_scenarios, dtype=float)
    price = np.asarray(price, dtype=float)
    if net.ndim != 2 or net.shape[1] != len(price) or not net.size:
        raise ValueError('Scenarios must be S by T; price must have T entries')
    s_count, n = net.shape
    probability = np.full(s_count, 1/s_count) if probabilities is None else np.asarray(probabilities, dtype=float)
    if probability.shape != (s_count,) or not np.isfinite(probability).all() or (probability <= 0).any() or not np.isclose(probability.sum(), 1):
        raise ValueError('Strictly positive probabilities must sum to one')
    if not np.isfinite(net).all() or not np.isfinite(price).all() or (price <= 0).any():
        raise ValueError('Finite net demand and strictly positive prices are required')
    if not battery.minimum <= initial <= battery.maximum:
        raise ValueError('Initial battery energy is outside physical bounds')
    if terminal is not None and not battery.minimum <= terminal <= battery.maximum:
        raise ValueError('Terminal target is outside physical bounds')
    if not (0 < battery.eta_charge <= 1 and 0 < battery.eta_discharge <= 1):
        raise ValueError('Single-trip efficiencies must be in (0, 1]')
    if min(battery.dt, battery.power_kw, emergency_multiplier, time_limit) <= 0:
        raise ValueError('Duration, power, emergency multiplier and time limit must be positive')
    block_size = 5*n+1
    z_start = n+s_count*block_size
    size = z_start+s_count*n
    objective = np.zeros(size)
    objective[:n] = price
    lower, upper = np.zeros(size), np.full(size, np.inf)
    cap = battery.power_kw*battery.dt
    upper[:n] = np.maximum(net.max(axis=0), 0)+cap
    upper[z_start:] = 1
    matrix = lil_matrix((s_count*5*n, size))
    low, high = np.full(s_count*5*n, -np.inf), np.full(s_count*5*n, np.inf)
    offsets = []
    for s in range(s_count):
        c = n+s*block_size
        d, u, w, e = c+n, c+2*n, c+3*n, c+4*n
        z = z_start+s*n
        offsets.append((c, d, u, w, e))
        objective[u:u+n] = probability[s]*emergency_multiplier*price
        upper[c:c+n] = upper[d:d+n] = cap
        max_emergency = np.maximum(net[s], 0)
        upper[u:u+n] = max_emergency
        lower[e:e+n+1], upper[e:e+n+1] = battery.minimum, battery.maximum
        lower[e] = upper[e] = initial
        if terminal is not None:
            lower[e+n] = upper[e+n] = terminal
        base = s*5*n
        for t in range(n):
            row = base+t
            matrix[row, t], matrix[row, c+t], matrix[row, d+t] = 1, -1, 1
            matrix[row, u+t], matrix[row, w+t] = 1, -1
            low[row] = high[row] = net[s, t]
            matrix[base+n+t, e+t+1], matrix[base+n+t, e+t] = 1, -1
            matrix[base+n+t, c+t], matrix[base+n+t, d+t] = -battery.eta_charge, 1/battery.eta_discharge
            low[base+n+t] = high[base+n+t] = 0
            matrix[base+2*n+t, c+t], matrix[base+2*n+t, z+t] = 1, -cap
            high[base+2*n+t] = 0
            matrix[base+3*n+t, d+t], matrix[base+3*n+t, z+t] = 1, cap
            high[base+3*n+t] = cap
            matrix[base+4*n+t, u+t], matrix[base+4*n+t, z+t] = 1, max_emergency[t]
            high[base+4*n+t] = max_emergency[t]
    constraint = LinearConstraint(matrix.tocsc(), low, high)
    integrality = np.zeros(size)
    started = time.perf_counter()
    result = milp(objective, integrality=integrality, bounds=Bounds(lower, upper),
                  constraints=constraint, options={'time_limit': time_limit})
    if result.x is None:
        raise RuntimeError('Scenario LP returned no feasible solution: '+result.message)
    lp_objective = float(result.fun)

    def unpack(solution):
        charges, discharges, emergencies, unused, states = [], [], [], [], []
        for c, d, u, w, e in offsets:
            clean_c, clean_d, clean_w = _canonicalize_recourse(
                solution[c:c+n], solution[d:d+n], solution[w:w+n], battery)
            charges.append(clean_c)
            discharges.append(clean_d)
            emergencies.append(solution[u:u+n])
            unused.append(clean_w)
            states.append(solution[e:e+n+1])
        return [np.asarray(a) for a in [charges, discharges, emergencies, unused, states]]

    charge, discharge, emergency, unused, state = unpack(result.x)
    initial_emergency_overlap = float(np.minimum(charge, emergency).max())
    fallback = initial_emergency_overlap > 1e-7
    if fallback:
        integrality[z_start:] = 1
        result = milp(objective, integrality=integrality, bounds=Bounds(lower, upper),
                      constraints=constraint, options={'time_limit': time_limit, 'mip_rel_gap': mip_gap})
        if result.x is None:
            raise RuntimeError('Scenario MILP returned no feasible solution: '+result.message)
        charge, discharge, emergency, unused, state = unpack(result.x)
    grid = result.x[:n].copy()
    planned_cost = float(price @ grid)
    expected_emergency_cost = float(probability @ (emergency @ (emergency_multiplier*price)))
    checks = {
        'bus_residual_kwh': float(abs(grid[None, :]+discharge+emergency-charge-unused-net).max()),
        'soc_residual_kwh': float(abs(np.diff(state, axis=1)-battery.eta_charge*charge+discharge/battery.eta_discharge).max()),
        'initial_residual_kwh': float(abs(state[:, 0]-initial).max()),
        'terminal_residual_kwh': float(abs(state[:, -1]-terminal).max()) if terminal is not None else 0.,
        'state_bound_violation_kwh': float(max(0, battery.minimum-state.min(), state.max()-battery.maximum)),
        'power_violation_kwh': float(max(0, charge.max()-cap, discharge.max()-cap)),
        'nonnegative_violation_kwh': float(max(0, -min(grid.min(), charge.min(), discharge.min(), emergency.min(), unused.min()))),
        'simultaneous_charge_discharge_kwh': float(np.minimum(charge, discharge).max()),
        'emergency_charge_overlap_kwh': float(np.minimum(charge, emergency).max()),
        'objective_reconciliation_yuan': float(abs(planned_cost+expected_emergency_cost-result.fun))}
    if not all(value <= 1e-5 for value in checks.values()):
        raise AssertionError(checks)
    return {'grid': grid, 'recourse': {'charge': charge, 'discharge': discharge,
            'emergency': emergency, 'unused': unused, 'soc': state, 'net_load': net.copy()},
            'probabilities': probability, 'verification': dict(checks, passed=True),
            'solver': {'status': int(result.status), 'message': result.message,
                'objective': float(result.fun), 'planned_cost': planned_cost,
                'expected_emergency_cost': expected_emergency_cost,
                'lp_lower_bound': lp_objective, 'mip_gap': getattr(result, 'mip_gap', None),
                'milp_fallback': fallback, 'lp_emergency_charge_overlap_kwh': initial_emergency_overlap,
                'runtime_seconds': time.perf_counter()-started, 'scenario_count': s_count,
                'terminal_target_kwh': terminal, 'nonanticipativity': 'shared day-ahead grid only',
                'grid_bound_basis': 'max_s positive(net demand) plus charge cap; any excess is unused in every scenario and strictly costly',
                'recourse_implementable': False,
                'objective_scope': 'optimistic complete-scenario recourse planning proxy; not online realized cost'}}


def plan_day_block_scenarios(load_kwh, pv_kwh, price, residual_days, *, cutoff,
                            residual_available_at, initial=6000., battery=Battery(),
                            terminal=6000., n_scenarios=5, max_history_days=28,
                            time_limit=15., mip_gap=1e-6):
    load, pv = np.asarray(load_kwh, dtype=float), np.asarray(pv_kwh, dtype=float)
    if load.ndim != 1 or pv.shape != load.shape or not np.isfinite(load).all() or not np.isfinite(pv).all() or min(load.min(), pv.min()) < 0:
        raise ValueError('Load and PV point forecasts must be finite, nonnegative matching vectors')
    blocks, probability, metadata = select_day_blocks(
        residual_days, price, n_scenarios=n_scenarios, max_history_days=max_history_days,
        cutoff=cutoff, residual_available_at=residual_available_at)
    result = solve_shared_contract(load[None, :]-pv[None, :]+blocks, price,
        probabilities=probability, initial=initial, terminal=terminal,
        battery=battery, time_limit=time_limit, mip_gap=mip_gap)
    result['scenario_metadata'] = metadata
    return result
