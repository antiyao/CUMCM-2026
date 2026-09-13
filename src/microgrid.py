from __future__ import annotations
import argparse
import csv
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta
from xml.sax.saxutils import escape
from dataclasses import dataclass, field, asdict
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp, linprog
from scipy.sparse import coo_matrix, lil_matrix

ROOT=Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Battery:
    minimum: float = 1200
    maximum: float = 10800
    power_kw: float = 5000
    eta_charge: float = 0.9
    eta_discharge: float = 0.9
    dt: float = 1 / 6

def optimize(load, pv, price, initial=6000, terminal=6000, battery=Battery(), relax=False, time_limit=60, mip_gap=1e-08):
    (load, pv, price) = (np.asarray(x, dtype=float) for x in (load, pv, price))
    n = len(load)
    assert len(pv) == len(price) == n and n > 0
    assert np.all(np.isfinite(np.r_[load, pv, price]))
    assert np.all(load >= 0) and np.all(pv >= 0) and np.all(price > 0)
    (q, c, d, w, e, z) = (0, n, 2 * n, 3 * n, 4 * n, 5 * n + 1)
    size = 6 * n + 1
    obj = np.zeros(size)
    obj[q:q + n] = price
    (lb, ub) = (np.zeros(size), np.full(size, np.inf))
    cap = battery.power_kw * battery.dt
    ub[c:c + n] = ub[d:d + n] = cap
    (lb[e:e + n + 1], ub[e:e + n + 1]) = (battery.minimum, battery.maximum)
    lb[e] = ub[e] = initial
    if terminal is not None:
        lb[e + n] = ub[e + n] = terminal
    ub[z:z + n] = 1
    a = lil_matrix((4 * n, size))
    (low, high) = (np.full(4 * n, -np.inf), np.full(4 * n, np.inf))
    for t in range(n):
        (a[t, q + t], a[t, c + t], a[t, d + t], a[t, w + t]) = (1, -1, 1, -1)
        low[t] = high[t] = load[t] - pv[t]
        (a[n + t, e + t + 1], a[n + t, e + t]) = (1, -1)
        (a[n + t, c + t], a[n + t, d + t]) = (-battery.eta_charge, 1 / battery.eta_discharge)
        low[n + t] = high[n + t] = 0
        (a[2 * n + t, c + t], a[2 * n + t, z + t]) = (1, -cap)
        high[2 * n + t] = 0
        (a[3 * n + t, d + t], a[3 * n + t, z + t]) = (1, cap)
        high[3 * n + t] = cap
    integral = np.zeros(size)
    if not relax:
        integral[z:z + n] = 1
    tic = time.perf_counter()
    sol = milp(obj, integrality=integral, bounds=Bounds(lb, ub), constraints=LinearConstraint(a.tocsc(), low, high), options={'time_limit': time_limit, 'mip_rel_gap': mip_gap})
    elapsed = time.perf_counter() - tic
    if sol.x is None:
        raise RuntimeError(f'No feasible optimization result: {sol.message}')
    x = sol.x
    return dict(grid=x[q:q + n], charge=x[c:c + n], discharge=x[d:d + n], unused=x[w:w + n], soc=x[e:e + n + 1], solver=dict(status=int(sol.status), message=sol.message, objective=float(sol.fun), runtime_seconds=elapsed, mip_gap=getattr(sol, 'mip_gap', None), dual_bound=getattr(sol, 'mip_dual_bound', None), relax=relax))

@dataclass(frozen=True)
class ValueBattery:
    lo: float = 1200.0
    hi: float = 10800.0
    power: float = 5000.0
    eta_c: float = 0.9
    eta_d: float = 0.9
    target: float = 6000.0

    @property
    def limit(self):
        return self.power / 6.0

def purchase_plan(scenarios, initial, battery=ValueBattery(), existing=None, refund=False, current_slots=144, terminal=6000.0):
    (ns, nt, _) = scenarios.shape
    net = (scenarios[:, :, 0] - scenarios[:, :, 1]) / 6.0
    prices = scenarios[:, :, 2]
    meanp = prices.mean(axis=0)
    nbase = 4 * nt + ns * nt
    nadj = 2 * current_slots if existing is not None and refund else 0
    nv = nbase + nadj
    objective = np.zeros(nv)
    objective[:nt] = meanp
    objective[nt:3 * nt] = 1e-08
    objective[4 * nt:nbase] = (5 * prices / ns).ravel()
    bounds = [(0.0, None)] * nv
    bounds[nt:3 * nt] = [(0.0, battery.limit)] * (2 * nt)
    bounds[3 * nt:4 * nt] = [(battery.lo, battery.hi)] * nt
    bounds[4 * nt - 1] = (terminal, terminal)
    if existing is not None:
        old = np.asarray(existing[:current_slots])
        if refund:
            objective[:current_slots] = 0
            objective[nbase:nbase + current_slots] = 1.5 * meanp[:current_slots]
            objective[nbase + current_slots:] = -0.5 * meanp[:current_slots]
            bounds[nbase + current_slots:] = [(0.0, float(v)) for v in old]
        else:
            objective[:current_slots] = 1.5 * meanp[:current_slots]
            bounds[:current_slots] = [(float(v), None) for v in old]
    (eqr, eqc, eqv) = ([], [], [])
    rhs = np.zeros(nt + (current_slots if nadj else 0))
    rhs[0] = initial
    for t in range(nt):
        for (col, val) in ((3 * nt + t, 1.0), (nt + t, -battery.eta_c), (2 * nt + t, 1 / battery.eta_d)):
            eqr.append(t)
            eqc.append(col)
            eqv.append(val)
        if t:
            eqr.append(t)
            eqc.append(3 * nt + t - 1)
            eqv.append(-1.0)
    if nadj:
        rhs[nt:] = old
        for t in range(current_slots):
            for (col, val) in ((t, 1.0), (nbase + t, -1.0), (nbase + current_slots + t, 1.0)):
                eqr.append(nt + t)
                eqc.append(col)
                eqv.append(val)
    rows = np.repeat(np.arange(ns * nt), 4)
    times = np.tile(np.arange(nt), ns)
    cols = np.column_stack([times, nt + times, 2 * nt + times, 4 * nt + np.arange(ns * nt)]).ravel()
    vals = np.tile([-1.0, 1.0, -1.0, -1.0], ns * nt)
    sol = linprog(objective, A_ub=coo_matrix((vals, (rows, cols)), shape=(ns * nt, nv)).tocsr(), b_ub=-net.ravel(), A_eq=coo_matrix((eqv, (eqr, eqc)), shape=(len(rhs), nv)).tocsr(), b_eq=rhs, bounds=bounds, method='highs', options={'dual_feasibility_tolerance': 1e-07, 'primal_feasibility_tolerance': 1e-07})
    if not sol.success:
        raise RuntimeError(f'Scenario LP failed: {sol.status} {sol.message}')
    q = np.maximum(sol.x[:nt], 0)
    c = np.maximum(sol.x[nt:2 * nt], 0)
    discharge = np.maximum(sol.x[2 * nt:3 * nt], 0)
    rho = battery.eta_c * battery.eta_d
    eliminate = np.minimum(c, discharge / rho)
    c -= eliminate
    discharge -= rho * eliminate
    soc = np.r_[initial, sol.x[3 * nt:4 * nt]]
    return {'q': q, 'charge': c, 'discharge': discharge, 'soc': soc, 'objective': float(sol.fun), 'iterations': int(sol.nit), 'residual': float(np.max(np.abs(np.diff(soc) - battery.eta_c * c + discharge / battery.eta_d)))}

def daily_plan(corrected_kwh, margin_kwh, price, initial, battery=ValueBattery()):
    corrected = np.asarray(corrected_kwh, dtype=float)
    margin = np.asarray(margin_kwh, dtype=float)
    price = np.asarray(price, dtype=float)
    if corrected.shape != (144, 2) or margin.shape != (144,) or price.shape != (144,):
        raise ValueError('daily plan expects corrected (144,2), margin/price (144,)')
    if not np.isfinite(np.r_[corrected.ravel(), margin, price, initial]).all():
        raise ValueError('nonfinite daily planning input')
    if np.any(corrected < 0) or np.any(margin < 0) or np.any(price <= 0):
        raise ValueError('nonnegative forecast/margin and strictly positive tariffs required')
    scenario = np.column_stack([(corrected[:, 0] + margin) * 6.0, corrected[:, 1] * 6.0, price])[None]
    result = purchase_plan(scenario, float(initial), battery=battery, current_slots=144, terminal=battery.target)
    net = corrected[:, 0] + margin - corrected[:, 1]
    implied_emergency = np.maximum(net + result['charge'] - result['discharge'] - result['q'], 0.0)
    result['max_implied_planned_emergency_kwh'] = float(implied_emergency.max())
    if implied_emergency.max() > 1e-05:
        raise AssertionError('point-scenario planner used emergency electricity')
    if np.max(np.minimum(result['charge'], result['discharge'])) > 1e-07:
        raise AssertionError('planner charge/discharge recovery failed')
    return result

def greedy_step(plan, load, pv, soc, battery=ValueBattery()):
    if min(plan, load, pv) < -1e-07 or not battery.lo - 1e-06 <= soc <= battery.hi + 1e-06:
        raise ValueError('invalid physical input')
    balance = float(plan + pv - load)
    if balance >= 0:
        charge = min(balance, battery.limit, max(0.0, (battery.hi - soc) / battery.eta_c))
        discharge = emergency = 0.0
        surplus = balance - charge
    else:
        charge = surplus = 0.0
        discharge = min(-balance, battery.limit, max(0.0, (soc - battery.lo) * battery.eta_d))
        emergency = -balance - discharge
    following = soc + battery.eta_c * charge - discharge / battery.eta_d
    if charge > 1e-07 and emergency > 1e-07:
        raise AssertionError('emergency charging is forbidden')
    return (charge, discharge, following, emergency, surplus)

def close_plan(q, data, day, battery=ValueBattery(), close_slots=8):
    if day <= 0:
        raise ValueError('Closing plan requires past observed load')
    result = np.asarray(q, dtype=float).copy()
    ordinary_floor = float(np.max(data['actual_load'][:day]) / 6 + battery.limit)
    result[-close_slots:] = np.maximum(result[-close_slots:], ordinary_floor)
    return result

def execute_close(plan, load, pv, soc, reference=None, battery=ValueBattery(), remaining=None):
    if soc < battery.target:
        charge = min(battery.limit, (battery.target - soc) / battery.eta_c, max(plan + pv - load, 0.0))
        discharge = 0.0
    else:
        charge = 0.0
        discharge = min(battery.limit, (soc - battery.target) * battery.eta_d, max(load, 0.0))
    nxt = soc + battery.eta_c * charge - discharge / battery.eta_d
    deficit = load + charge - pv - plan - discharge
    return (charge, discharge, nxt, max(deficit, 0.0), max(-deficit, 0.0))

def ordinary_cost(original, adjusted, price):
    (original, adjusted, price) = np.broadcast_arrays(np.asarray(original, dtype=float), np.asarray(adjusted, dtype=float), np.asarray(price, dtype=float))
    if not np.isfinite(np.r_[original.ravel(), adjusted.ravel(), price.ravel()]).all():
        raise ValueError('Nonfinite contract input')
    if (original < 0).any() or (adjusted < 0).any() or (price <= 0).any():
        raise ValueError('Contract quantities must be nonnegative and prices positive')
    return price * adjusted + 0.5 * price * np.abs(adjusted - original)

@dataclass
class AdjustmentLedger:
    original: np.ndarray
    reference_mode: str
    events: list = field(default_factory=list)

    def __post_init__(self):
        if self.reference_mode not in ('initial_final', 'sequential'):
            raise ValueError('Choose initial_final or sequential explicitly')
        self.original = np.asarray(self.original, dtype=float).copy()
        if not np.isfinite(self.original).all() or (self.original < 0).any():
            raise ValueError('Invalid original contract')
        self.contract = self.original.copy()

    def revise(self, target, effective_from, issue_time):
        target = np.asarray(target, dtype=float)
        if target.shape != self.contract.shape or not np.isfinite(target).all() or (target < -1e-07).any():
            raise ValueError('Invalid revised contract')
        if not np.allclose(target[:effective_from], self.contract[:effective_from], atol=1e-07, rtol=0):
            raise ValueError('Cannot change delivered intervals')
        target = np.maximum(target, 0)
        delta = target - self.contract
        if np.max(np.abs(delta)) <= 1e-07:
            return False
        self.events.append(dict(issue_time=str(issue_time), effective_from=effective_from, before=self.contract.copy(), after=target.copy(), increase=np.maximum(delta, 0), decrease=np.maximum(-delta, 0)))
        self.contract = target
        return True

    def settle(self, price, emergency):
        price = np.asarray(price, dtype=float)
        gross_increase = sum((e['increase'] for e in self.events), np.zeros_like(self.original))
        gross_decrease = sum((e['decrease'] for e in self.events), np.zeros_like(self.original))
        if not np.allclose(self.original + gross_increase - gross_decrease, self.contract, atol=1e-06, rtol=0):
            raise AssertionError('Events do not reconstruct contract')
        if self.reference_mode == 'initial_final':
            increase = np.maximum(self.contract - self.original, 0)
            decrease = np.maximum(self.original - self.contract, 0)
        else:
            (increase, decrease) = (gross_increase, gross_decrease)
        original_fee = price * self.original
        (increase_fee, decrease_penalty, refund) = (1.5 * price * increase, 0.5 * price * decrease, price * decrease)
        emergency_fee = 5 * price * np.asarray(emergency)
        total = original_fee + increase_fee + decrease_penalty - refund + emergency_fee
        if self.reference_mode == 'initial_final' and (not np.allclose(total, ordinary_cost(self.original, self.contract, price) + emergency_fee, atol=1e-06, rtol=0)):
            raise AssertionError('Final-quantity settlement does not match piecewise price')
        return dict(original_fee=original_fee, increase_fee=increase_fee, decrease_penalty=decrease_penalty, refund=refund, emergency_fee=emergency_fee, total_fee=total, contract_increase=increase, contract_decrease=decrease, gross_contract_increase=gross_increase, gross_contract_decrease=gross_decrease)

def replan(load, pv, price, reference, initial, terminal, battery=Battery(), terminal_weight=1.0, minimum_contract=None, terminal_curve=None, fixed_contract=False, relaxation_only=False):
    (load, pv, price, reference) = [np.asarray(x, dtype=float) for x in (load, pv, price, reference)]
    n = len(load)
    if n == 0 or any((len(x) != n for x in (pv, price, reference))) or (not np.isfinite(np.r_[load, pv, price, reference]).all()):
        raise ValueError('Invalid planning vectors')
    if min(load.min(), pv.min(), reference.min()) < -1e-07 or price.min() <= 0:
        raise ValueError('Invalid sign in planning input')
    (inc, dec, u, c, d, w, e, z, slack) = (0, n, 2 * n, 3 * n, 4 * n, 5 * n, 6 * n, 7 * n + 1, 8 * n + 1)
    size = slack + 1
    objective = np.zeros(size)
    objective[inc:inc + n] = 1.5 * price
    objective[dec:dec + n] = -0.5 * price
    objective[u:u + n] = 5 * price
    objective[slack] = terminal_weight * price.min() / battery.eta_charge
    slopes = intercepts = None
    if terminal_curve is not None:
        (knots, values) = [np.asarray(v, dtype=float) for v in terminal_curve]
        if len(knots) < 2 or values.shape != knots.shape or (not np.isfinite(np.r_[knots, values]).all()):
            raise ValueError('Invalid terminal curve')
        if np.any(np.diff(knots) <= 0) or knots[0] > battery.minimum or knots[-1] < battery.maximum:
            raise ValueError('Terminal curve must cover the battery interval')
        slopes = np.diff(values) / np.diff(knots)
        if np.min(np.diff(slopes), initial=0.0) < -1e-07 or slopes.max() > 1e-07:
            raise ValueError('Terminal curve must be convex and nonincreasing')
        intercepts = values[:-1] - slopes * knots[:-1]
        objective[slack] = 1.0
    (lower, upper) = (np.zeros(size), np.full(size, np.inf))
    cap = battery.power_kw * battery.dt
    upper[dec:dec + n] = reference
    if fixed_contract:
        upper[inc:inc + n] = upper[dec:dec + n] = 0.0
    if terminal_curve is not None:
        lower[slack] = -np.inf
    upper[u:u + n] = load
    upper[c:c + n] = upper[d:d + n] = cap
    (lower[e:e + n + 1], upper[e:e + n + 1]) = (battery.minimum, battery.maximum)
    lower[e] = upper[e] = initial
    upper[z:z + n] = 1
    extra = n if minimum_contract is not None else 0
    terminal_rows = 1 if slopes is None else len(slopes)
    a = lil_matrix((5 * n + terminal_rows + extra, size))
    (lo, hi) = (np.full(a.shape[0], -np.inf), np.full(a.shape[0], np.inf))
    for t in range(n):
        for (col, value) in [(inc + t, 1), (dec + t, -1), (u + t, 1), (c + t, -1), (d + t, 1), (w + t, -1)]:
            a[t, col] = value
        lo[t] = hi[t] = load[t] - pv[t] - reference[t]
        for (col, value) in [(e + t + 1, 1), (e + t, -1), (c + t, -battery.eta_charge), (d + t, 1 / battery.eta_discharge)]:
            a[n + t, col] = value
        lo[n + t] = hi[n + t] = 0
        (a[2 * n + t, c + t], a[2 * n + t, z + t]) = (1, -cap)
        hi[2 * n + t] = 0
        (a[3 * n + t, d + t], a[3 * n + t, z + t]) = (1, cap)
        hi[3 * n + t] = cap
        (a[4 * n + t, u + t], a[4 * n + t, z + t]) = (1, load[t])
        hi[4 * n + t] = load[t]
    if slopes is None:
        (a[5 * n, e + n], a[5 * n, slack]) = (1, 1)
        lo[5 * n] = terminal
    else:
        for (row, (slope, intercept)) in enumerate(zip(slopes, intercepts), 5 * n):
            (a[row, e + n], a[row, slack]) = (-slope, 1)
            lo[row] = intercept
    if minimum_contract is not None:
        for t in range(n):
            (a[5 * n + terminal_rows + t, inc + t], a[5 * n + terminal_rows + t, dec + t]) = (1, -1)
            lo[5 * n + terminal_rows + t] = minimum_contract[t] - reference[t]
    integrality = np.zeros(size)
    tic = time.perf_counter()
    result = milp(objective, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(a.tocsc(), lo, hi), options={'time_limit': 30, 'mip_rel_gap': 1e-08})
    if result.x is None or result.status != 0:
        raise RuntimeError('Replan was not solved to optimality: ' + result.message)
    x = result.x
    if not relaxation_only and max(np.minimum(x[c:c + n], x[d:d + n]).max(), np.minimum(x[c:c + n], x[u:u + n]).max()) > 1e-07:
        integrality[z:z + n] = 1
        result = milp(objective, integrality=integrality, bounds=Bounds(lower, upper), constraints=LinearConstraint(a.tocsc(), lo, hi), options={'time_limit': 30, 'mip_rel_gap': 1e-08})
        if result.x is None or result.status != 0:
            raise RuntimeError('Integer replan was not solved to optimality: ' + result.message)
        x = result.x
    grid = np.maximum(reference + x[inc:inc + n] - x[dec:dec + n], 0)
    residual = max(abs(grid + pv + x[d:d + n] + x[u:u + n] - load - x[c:c + n] - x[w:w + n]).max(), np.minimum(x[c:c + n], x[d:d + n]).max(), np.minimum(x[c:c + n], x[u:u + n]).max())
    if residual > 1e-06 and (not relaxation_only):
        raise AssertionError('Replan physical check failed')
    return dict(grid=grid, soc=x[e:e + n + 1], charge=x[c:c + n], discharge=x[d:d + n], solver=dict(status=int(result.status), objective=float(result.fun), relax=not integrality.any(), runtime_seconds=time.perf_counter() - tic, mip_gap=getattr(result, 'mip_gap', None), maximum_residual_kwh=float(residual)))

@dataclass(frozen=True)
class ValuePolicy:
    grid: np.ndarray
    values: np.ndarray
    decision_price: np.ndarray
    start_slot: int
    tie_break: str = 'more_discharge'
    value_discount: float = 1.0

    def next_values(self, absolute_slot: int) -> np.ndarray:
        row = absolute_slot - self.start_slot + 1
        if row < 1 or row >= len(self.values):
            raise IndexError('slot outside value-table interval')
        return self.values[row] if self.value_discount == 1.0 else self.value_discount * self.values[row]

def _as_kernels(residual_kernels, nt: int) -> list[np.ndarray]:
    if isinstance(residual_kernels, np.ndarray) and residual_kernels.ndim == 2:
        source = [residual_kernels[t] for t in range(nt)]
    else:
        source = list(residual_kernels)
    if len(source) != nt:
        raise ValueError('one residual kernel is required for every slot')
    result = []
    for samples in source:
        a = np.asarray(samples, dtype=float).reshape(-1)
        if not len(a) or not np.isfinite(a).all():
            raise ValueError('residual kernels must be finite and non-empty')
        result.append(a)
    return result

def make_soc_grid(battery: ValueBattery=ValueBattery(), step_kwh: float=50.0) -> np.ndarray:
    if not np.isfinite(step_kwh) or step_kwh <= 0:
        raise ValueError('positive finite SOC grid step required')
    span = battery.hi - battery.lo
    count = int(round(span / step_kwh))
    if abs(count * step_kwh - span) > 1e-09:
        raise ValueError('SOC step must divide the usable battery interval')
    return np.linspace(battery.lo, battery.hi, count + 1)

def _convex_nonincreasing_diagnostics(grid: np.ndarray, values: np.ndarray) -> dict:
    first = np.diff(values) / np.diff(grid)
    second = np.diff(first)
    return {'max_monotonicity_violation': float(max(0.0, np.max(first, initial=-np.inf))), 'max_convexity_violation': float(max(0.0, -np.min(second, initial=np.inf)))}

def reachable_minimum(grid, objective, lower, upper):
    (lower, upper) = np.broadcast_arrays(lower, upper)
    choices = np.concatenate([lower[..., None], upper[..., None], np.broadcast_to(grid, lower.shape + (len(grid),))], axis=-1)
    scores = np.interp(choices, grid, objective)
    scores = np.where((choices >= lower[..., None] - 1e-10) & (choices <= upper[..., None] + 1e-10), scores, np.inf)
    best = scores.min(axis=-1, keepdims=True)
    return np.min(np.where(scores <= best + 1e-10, choices, np.inf), axis=-1)

def build_rolling_value_table(effective_q_kwh, forecast_net_kwh, residual_kernels, decision_price, *, battery: ValueBattery=ValueBattery(), step_kwh: float=50.0, terminal_kappa: float=0.0, terminal_target_kwh: float=6000.0, start_slot: int=0, terminal_values=None, vectorized: bool=False, value_discount: float=1.0) -> tuple[ValuePolicy, dict]:
    q = np.asarray(effective_q_kwh, dtype=float).reshape(-1)
    if not 0.0 < value_discount <= 1.0:
        raise ValueError('Value discount must be in (0,1]')
    net = np.asarray(forecast_net_kwh, dtype=float).reshape(-1)
    price = np.asarray(decision_price, dtype=float).reshape(-1)
    nt = len(q)
    if len(net) != nt or len(price) != nt or nt == 0:
        raise ValueError('q, forecast net load and decision price must align')
    if not np.isfinite(np.r_[q, net, price]).all() or np.any(q < -1e-09) or np.any(price < 0):
        raise ValueError('invalid value-DP input')
    kernels = _as_kernels(residual_kernels, nt)
    grid = make_soc_grid(battery, step_kwh)
    values = np.zeros((nt + 1, len(grid)), dtype=float)
    values[-1] = float(terminal_kappa) * np.maximum(float(terminal_target_kwh) - grid, 0.0)
    if terminal_values is not None:
        supplied = np.asarray(terminal_values, dtype=float)
        if supplied.shape != grid.shape or not np.isfinite(supplied).all():
            raise ValueError('Terminal values must match the SOC grid')
        if np.max(np.diff(supplied), initial=0.0) > 1e-07:
            raise ValueError('Terminal values must be nonincreasing')
        values[-1] = supplied
    if terminal_kappa < 0:
        raise ValueError('terminal continuation coefficient must be nonnegative')
    max_mono = max_convex = 0.0
    targets = np.empty(nt, dtype=float)
    for t in range(nt - 1, -1, -1):
        continuation = values[t + 1] if value_discount == 1.0 else value_discount * values[t + 1]
        shape = _convex_nonincreasing_diagnostics(grid, continuation)
        convex = shape['max_convexity_violation'] <= 1e-07
        objective = continuation + 5.0 * price[t] * battery.eta_d * grid
        best = np.flatnonzero(objective <= objective.min() + 1e-10)[0]
        target = grid[best]
        targets[t] = target
        sample_values = np.empty((len(kernels[t]), len(grid)), dtype=float)
        samples = [] if vectorized and convex else kernels[t]
        if vectorized and convex:
            balance = q[t] - (net[t] + kernels[t][:, None])
            charge = np.minimum(np.maximum(balance, 0.0), battery.limit)
            charged = np.minimum(battery.hi, grid + battery.eta_c * charge)
            deficit = np.maximum(-balance, 0.0)
            lower = np.maximum(battery.lo, grid - np.minimum(deficit, battery.limit) / battery.eta_d)
            nxt = np.minimum(grid, np.maximum(lower, target))
            discharged = battery.eta_d * (grid - nxt)
            sample_values = np.where(balance >= 0, np.interp(charged, grid, continuation), 5.0 * price[t] * (deficit - discharged) + np.interp(nxt, grid, continuation))
        for (j, error) in enumerate(samples):
            balance = q[t] - (net[t] + error)
            if balance >= 0:
                charge = min(balance, battery.limit)
                nxt = np.minimum(battery.hi, grid + battery.eta_c * charge)
                sample_values[j] = np.interp(nxt, grid, continuation)
            else:
                deficit = -balance
                lower = np.maximum(battery.lo, grid - min(deficit, battery.limit) / battery.eta_d)
                nxt = np.minimum(grid, np.maximum(lower, target))
                if not convex:
                    nxt = reachable_minimum(grid, objective, lower, grid)
                discharge = battery.eta_d * (grid - nxt)
                emergency = deficit - discharge
                sample_values[j] = 5.0 * price[t] * emergency + np.interp(nxt, grid, continuation)
        values[t] = sample_values.mean(axis=0)
        diag = _convex_nonincreasing_diagnostics(grid, values[t])
        max_mono = max(max_mono, diag['max_monotonicity_violation'])
        max_convex = max(max_convex, diag['max_convexity_violation'])
    policy = ValuePolicy(grid=grid, values=values, decision_price=price, start_slot=int(start_slot), value_discount=value_discount)
    return (policy, {'soc_grid_step_kwh': float(step_kwh), 'soc_grid_points': int(len(grid)), 'time_slots': int(nt), 'residual_samples_min': int(min(map(len, kernels))), 'residual_samples_max': int(max(map(len, kernels))), 'terminal_kappa_yuan_per_kwh': float(terminal_kappa), 'terminal_curve_supplied': terminal_values is not None, 'value_discount': value_discount, 'max_monotonicity_violation': float(max_mono), 'max_convexity_violation': float(max_convex), 'reserve_target_min_kwh': float(targets.min()), 'reserve_target_max_kwh': float(targets.max())})

def execute_rolling_value_policy(q_kwh: float, actual_load_kwh: float, actual_pv_kwh: float, actual_soc_kwh: float, decision_price: float, next_value_grid, grid, *, battery: ValueBattery=ValueBattery(), general_search: bool=False) -> tuple[dict, dict]:
    (q, load, pv, soc, price) = map(float, (q_kwh, actual_load_kwh, actual_pv_kwh, actual_soc_kwh, decision_price))
    continuation = np.asarray(next_value_grid, dtype=float)
    grid = np.asarray(grid, dtype=float)
    if min(q, load, pv, price) < -1e-09 or not battery.lo - 1e-07 <= soc <= battery.hi + 1e-07:
        raise ValueError('invalid physical execution input')
    if continuation.shape != grid.shape or not np.isfinite(continuation).all():
        raise ValueError('invalid continuation value')
    balance = q + pv - load
    held_value = float(np.interp(soc, grid, continuation))
    if balance >= 0:
        charge = min(balance, battery.limit, max(0.0, (battery.hi - soc) / battery.eta_c))
        discharge = emergency = 0.0
        nxt = soc + battery.eta_c * charge
        surplus = balance - charge
        target = soc
    else:
        deficit = -balance
        objective = continuation + 5.0 * price * battery.eta_d * grid
        target = float(grid[np.flatnonzero(objective <= objective.min() + 1e-10)[0]])
        lower = max(battery.lo, soc - min(deficit, battery.limit) / battery.eta_d)
        nxt = min(soc, max(lower, target))
        if general_search:
            nxt = float(reachable_minimum(grid, objective, lower, soc))
        discharge = battery.eta_d * (soc - nxt)
        emergency = max(0.0, deficit - discharge)
        charge = surplus = 0.0
    result = {'charge': float(charge), 'discharge': float(discharge), 'soc_end': float(nxt), 'emergency': float(emergency), 'surplus': float(surplus)}
    explanation = {'reserve_target_kwh': float(target), 'actual_gap_kwh': float(max(-balance, 0.0)), 'immediate_saving_yuan': float(5.0 * price * discharge), 'continuation_value_before_yuan': held_value, 'continuation_value_after_yuan': float(np.interp(nxt, grid, continuation)), 'economic_hold_with_emergency': bool(emergency > 1e-07 and discharge + 1e-07 < min(max(-balance, 0.0), battery.limit, max(0.0, (soc - battery.lo) * battery.eta_d)))}
    if charge > 1e-07 and emergency > 1e-07:
        raise AssertionError('emergency electricity may not charge the battery')
    return (result, explanation)

@dataclass(frozen=True)
class MidnightValuePolicy:
    grid: np.ndarray
    values: np.ndarray
    decision_price: np.ndarray
    start_slot: int
    tie_break: str = 'more_discharge'

    def next_values(self, absolute_slot: int) -> np.ndarray:
        row = absolute_slot - self.start_slot + 1
        if row < 1 or row >= len(self.values):
            raise IndexError('slot outside value-table interval')
        return self.values[row]

def build_midnight_value_table(effective_q_kwh, forecast_net_kwh, residual_kernels, decision_price, *, battery: ValueBattery=ValueBattery(), step_kwh: float=50.0, terminal_kappa: float=0.0, terminal_target_kwh: float=6000.0, start_slot: int=0) -> tuple[MidnightValuePolicy, dict]:
    q = np.asarray(effective_q_kwh, dtype=float).reshape(-1)
    net = np.asarray(forecast_net_kwh, dtype=float).reshape(-1)
    price = np.asarray(decision_price, dtype=float).reshape(-1)
    nt = len(q)
    if len(net) != nt or len(price) != nt or nt == 0:
        raise ValueError('q, forecast net load and decision price must align')
    if not np.isfinite(np.r_[q, net, price]).all() or np.any(q < -1e-09) or np.any(price < 0):
        raise ValueError('invalid value-DP input')
    kernels = _as_kernels(residual_kernels, nt)
    grid = make_soc_grid(battery, step_kwh)
    values = np.zeros((nt + 1, len(grid)), dtype=float)
    values[-1] = float(terminal_kappa) * np.maximum(float(terminal_target_kwh) - grid, 0.0)
    if terminal_kappa < 0:
        raise ValueError('terminal continuation coefficient must be nonnegative')
    max_mono = max_convex = 0.0
    targets = np.empty(nt, dtype=float)
    for t in range(nt - 1, -1, -1):
        continuation = values[t + 1]
        objective = continuation + 5.0 * price[t] * battery.eta_d * grid
        best = np.flatnonzero(objective <= objective.min() + 1e-10)[0]
        target = grid[best]
        targets[t] = target
        sample_values = np.empty((len(kernels[t]), len(grid)), dtype=float)
        for (j, error) in enumerate(kernels[t]):
            balance = q[t] - (net[t] + error)
            if balance >= 0:
                charge = min(balance, battery.limit)
                nxt = np.minimum(battery.hi, grid + battery.eta_c * charge)
                sample_values[j] = np.interp(nxt, grid, continuation)
            else:
                deficit = -balance
                lower = np.maximum(battery.lo, grid - min(deficit, battery.limit) / battery.eta_d)
                nxt = np.minimum(grid, np.maximum(lower, target))
                discharge = battery.eta_d * (grid - nxt)
                emergency = deficit - discharge
                sample_values[j] = 5.0 * price[t] * emergency + np.interp(nxt, grid, continuation)
        values[t] = sample_values.mean(axis=0)
        diag = _convex_nonincreasing_diagnostics(grid, values[t])
        max_mono = max(max_mono, diag['max_monotonicity_violation'])
        max_convex = max(max_convex, diag['max_convexity_violation'])
    policy = MidnightValuePolicy(grid=grid, values=values, decision_price=price, start_slot=int(start_slot))
    return (policy, {'soc_grid_step_kwh': float(step_kwh), 'soc_grid_points': int(len(grid)), 'time_slots': int(nt), 'residual_samples_min': int(min(map(len, kernels))), 'residual_samples_max': int(max(map(len, kernels))), 'terminal_kappa_yuan_per_kwh': float(terminal_kappa), 'max_monotonicity_violation': float(max_mono), 'max_convexity_violation': float(max_convex), 'reserve_target_min_kwh': float(targets.min()), 'reserve_target_max_kwh': float(targets.max())})

def execute_midnight_value_policy(q_kwh: float, actual_load_kwh: float, actual_pv_kwh: float, actual_soc_kwh: float, decision_price: float, next_value_grid, grid, *, battery: ValueBattery=ValueBattery()) -> tuple[dict, dict]:
    (q, load, pv, soc, price) = map(float, (q_kwh, actual_load_kwh, actual_pv_kwh, actual_soc_kwh, decision_price))
    continuation = np.asarray(next_value_grid, dtype=float)
    grid = np.asarray(grid, dtype=float)
    if min(q, load, pv, price) < -1e-09 or not battery.lo - 1e-07 <= soc <= battery.hi + 1e-07:
        raise ValueError('invalid physical execution input')
    if continuation.shape != grid.shape or not np.isfinite(continuation).all():
        raise ValueError('invalid continuation value')
    balance = q + pv - load
    held_value = float(np.interp(soc, grid, continuation))
    if balance >= 0:
        charge = min(balance, battery.limit, max(0.0, (battery.hi - soc) / battery.eta_c))
        discharge = emergency = 0.0
        nxt = soc + battery.eta_c * charge
        surplus = balance - charge
        target = soc
    else:
        deficit = -balance
        objective = continuation + 5.0 * price * battery.eta_d * grid
        target = float(grid[np.flatnonzero(objective <= objective.min() + 1e-10)[0]])
        lower = max(battery.lo, soc - min(deficit, battery.limit) / battery.eta_d)
        nxt = min(soc, max(lower, target))
        discharge = battery.eta_d * (soc - nxt)
        emergency = max(0.0, deficit - discharge)
        charge = surplus = 0.0
    result = {'charge': float(charge), 'discharge': float(discharge), 'soc_end': float(nxt), 'emergency': float(emergency), 'surplus': float(surplus)}
    explanation = {'reserve_target_kwh': float(target), 'actual_gap_kwh': float(max(-balance, 0.0)), 'immediate_saving_yuan': float(5.0 * price * discharge), 'continuation_value_before_yuan': held_value, 'continuation_value_after_yuan': float(np.interp(nxt, grid, continuation)), 'economic_hold_with_emergency': bool(emergency > 1e-07 and discharge + 1e-07 < min(max(-balance, 0.0), battery.limit, max(0.0, (soc - battery.lo) * battery.eta_d)))}
    if charge > 1e-07 and emergency > 1e-07:
        raise AssertionError('emergency electricity may not charge the battery')
    return (result, explanation)

def verify_intervals(frame, battery):
    b = battery
    bus = frame.contract_grid + frame.pv_kwh + frame.discharge + frame.emergency - frame.load_kwh - frame.charge - frame.unused
    dynamics = frame.soc_end - frame.soc_start - b.eta_charge * frame.charge + frame.discharge / b.eta_discharge
    total = frame.original_fee + frame.increase_fee + frame.decrease_penalty - frame.refund + frame.emergency_fee
    metrics = {'bus_residual_kwh': float(abs(bus).max()), 'soc_recursion_residual_kwh': float(abs(dynamics).max()), 'soc_lower_violation_kwh': float(max(0.0, b.minimum - frame.soc_end.min())), 'soc_upper_violation_kwh': float(max(0.0, frame.soc_end.max() - b.maximum)), 'power_violation_kwh': float(max(0.0, frame.charge.max() - b.power_kw * b.dt, frame.discharge.max() - b.power_kw * b.dt)), 'simultaneous_charge_discharge_kwh': float(np.minimum(frame.charge, frame.discharge).max()), 'emergency_and_charge_overlap_kwh': float(np.minimum(frame.emergency, frame.charge).max()), 'fee_reconciliation_yuan': float(abs(total - frame.total_fee).max()), 'unused_source_reconciliation_kwh': float(abs(frame.unused - frame.unused_pv - frame.unused_purchased).max()), 'continuous_state_residual_kwh': float(np.max(abs(frame.soc_start.to_numpy()[1:] - frame.soc_end.to_numpy()[:-1]))), 'nonnegative_violation_kwh': float(max(0, -frame[['planned_grid', 'contract_grid', 'charge', 'discharge', 'emergency', 'unused']].min().min()))}
    metrics['passed'] = all((v < 1e-06 for v in metrics.values()))
    if not metrics['passed']:
        raise AssertionError(metrics)
    return metrics

def aggregate(frame, battery):
    amount_cols = ['planned_grid', 'contract_grid', 'charge', 'discharge', 'emergency', 'unused', 'unused_pv', 'unused_purchased', 'original_fee', 'increase_fee', 'decrease_penalty', 'refund', 'emergency_fee', 'total_fee', 'contract_increase', 'contract_decrease']
    daily = frame.groupby('date')[amount_cols].sum()
    daily['initial_soc'] = frame.groupby('date').soc_start.first()
    daily['terminal_soc'] = frame.groupby('date').soc_end.last()
    active = frame.emergency > 1e-07
    starts = active & (~active.shift(fill_value=False) | frame.date.ne(frame.date.shift()))
    daily['emergency_events'] = starts.groupby(frame.date).sum()
    daily['emergency_intervals'] = active.groupby(frame.date).sum()
    monthly = daily[amount_cols + ['emergency_events', 'emergency_intervals']].groupby(daily.index.str[:7]).sum()
    monthly.index.name = 'month'
    tail = daily.total_fee.quantile(0.95)
    summary = {k: float(frame[k].sum()) for k in amount_cols}
    summary.update({'days': len(daily), 'intervals': len(frame), 'start_date': frame.date.iloc[0], 'end_date': frame.date.iloc[-1], 'initial_soc_kwh': float(frame.soc_start.iloc[0]), 'terminal_soc_kwh': float(frame.soc_end.iloc[-1]), 'daily_cost_p95_yuan': float(tail), 'daily_cost_tail_mean_yuan': float(daily.loc[daily.total_fee >= tail, 'total_fee'].mean()), 'emergency_events': int(daily.emergency_events.sum()), 'soc_min_kwh': float(min(frame.soc_start.min(), frame.soc_end.min())), 'soc_max_kwh': float(max(frame.soc_start.max(), frame.soc_end.max())), 'terminal_energy_delta_kwh': float(frame.soc_end.iloc[-1] - frame.soc_start.iloc[0]), 'terminal_credit_sensitivity_yuan': float((frame.soc_end.iloc[-1] - frame.soc_start.iloc[0]) * frame.plan_price.iloc[-144:].min() / battery.eta_charge)})
    summary['total_fee_less_terminal_credit_sensitivity'] = summary['total_fee'] - summary['terminal_credit_sensitivity_yuan']
    summary['verification'] = verify_intervals(frame, battery)
    return (daily, monthly, summary)

def check_dispatch(load, pv, price, result, eta_charge=0.9, eta_discharge=0.9, minimum=1200, maximum=10800, limit=5000 / 6, cyclic=True):
    (q, c, d, w, e) = [np.asarray(result[x]) for x in ['grid', 'charge', 'discharge', 'unused', 'soc']]
    metrics = dict(bus_residual_kwh=float(np.max(np.abs(q + pv + d - load - c - w))), soc_residual_kwh=float(np.max(np.abs(np.diff(e) - eta_charge * c + d / eta_discharge))), lower_bound_violation_kwh=float(max(0, minimum - e.min())), upper_bound_violation_kwh=float(max(0, e.max() - maximum)), power_violation_kwh=float(max(0, max(c.max(), d.max()) - limit)), nonnegative_violation_kwh=float(max(0, -min(q.min(), c.min(), d.min(), w.min()))), simultaneous_charge_discharge_kwh=float(np.max(np.minimum(c, d))), terminal_difference_kwh=float(abs(e[-1] - e[0])) if cyclic else 0, objective_recomputed_yuan=float(np.dot(price, q)), objective_difference_yuan=float(abs(np.dot(price, q) - result['solver']['objective'])), finite=bool(np.isfinite(np.r_[q, c, d, w, e]).all()))
    metrics['passed'] = metrics['finite'] and all((v < 1e-06 for (k, v) in metrics.items() if k not in ['objective_recomputed_yuan', 'finite']))
    return metrics

def align_actuals(frame, dates):
    keys = ['date', 'slot']
    columns = ['load_kw', 'pv_kw', 'price_yuan_kwh']
    f = frame.copy()
    f['date'] = pd.to_datetime(f['date'], errors='raise').dt.strftime('%Y-%m-%d')
    raw = pd.to_numeric(f['slot'], errors='raise')
    if not np.all(raw == np.floor(raw)):
        raise ValueError('Noninteger slot')
    f['slot'] = raw.astype(int)
    if f.duplicated(keys).any():
        raise ValueError('Duplicate date/slot keys')
    expected = pd.MultiIndex.from_product([list(dates), range(144)], names=keys)
    actual = pd.MultiIndex.from_frame(f[keys])
    if len(expected.difference(actual)) or len(actual.difference(expected)):
        raise ValueError('Missing or unexpected date/slot keys')
    f = f.set_index(keys).reindex(expected)
    values = f[columns].to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite actual data')
    return values.reshape(len(dates), 144, 3)

def load_verified_input(npz='data/processed/annual_inputs.npz', csv='data/processed/actuals_power.csv'):
    with np.load(npz, allow_pickle=False) as source:
        data = {name: source[name].copy() for name in source.files}
    dates = data['dates'].astype(str)
    if len(np.unique(dates)) != len(dates) or not np.all(dates[1:] > dates[:-1]):
        raise ValueError('NPZ dates must be unique chronological keys')
    aligned = align_actuals(pd.read_csv(csv), dates)
    for (i, name) in enumerate(('actual_load', 'actual_pv', 'actual_price')):
        if not np.allclose(aligned[:, :, i], data[name], atol=1e-09, rtol=0):
            raise ValueError(f'Keyed CSV/NPZ mismatch: {name}')
        data[name] = aligned[:, :, i].copy()
    return data


RESULTS = ROOT / 'results/c2026'
WORK = ROOT / 'results/c2026/rebuild'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
FILES = ['result1.xlsx', 'result2.xlsx', 'result3.xlsx', 'result4-2.xlsx', 'result4-3.xlsx']
KEYS = ['q1', 'q2', 'q3', 'q4_2', 'q4_3']
_FILE_BY_CASE = dict(zip(KEYS, FILES))
EMERGENCY_TOL_KWH = 1e-07
SUMCOLS = ['plan', 'adjusted', 'up', 'down', 'emergency', 'charge', 'discharge', 'surplus', 'cost_plan', 'cost_up', 'cost_down', 'cost_emergency', 'cost_total']

def canonical_frame(frame):
    if 'slot' in frame:
        return frame.copy()
    mapping = {'date': 'date', 'slot': 'interval_index', 'load': 'load_kwh', 'pv': 'pv_kwh', 'price': 'price', 'decision_price': 'plan_price', 'plan': 'planned_grid', 'adjusted': 'contract_grid', 'up': 'contract_increase', 'down': 'contract_decrease', 'emergency': 'emergency', 'charge': 'charge', 'discharge': 'discharge', 'soc_start': 'soc_start', 'soc_end': 'soc_end', 'surplus': 'unused', 'cost_plan': 'original_fee', 'cost_up': 'increase_fee', 'cost_emergency': 'emergency_fee', 'cost_total': 'total_fee'}
    result = pd.DataFrame({key: frame[value] for (key, value) in mapping.items()})
    result['cost_down'] = frame.decrease_penalty - frame.refund
    return result

def verify_frame(frame):
    balance = frame.adjusted + frame.pv + frame.discharge + frame.emergency - frame.load - frame.charge - frame.surplus
    state = frame.soc_end - frame.soc_start - 0.9 * frame.charge + frame.discharge / 0.9
    cost = frame.cost_plan + frame.cost_up + frame.cost_down + frame.cost_emergency - frame.cost_total
    checks = dict(balance=float(np.abs(balance).max()), state=float(np.abs(state).max()), cost=float(np.abs(cost).max()), lower=max(0.0, float(1200 - frame.soc_end.min())), upper=max(0.0, float(frame.soc_end.max() - 10800)), power=max(0.0, float(frame.charge.max() - 5000 / 6), float(frame.discharge.max() - 5000 / 6)), simultaneous=float(np.minimum(frame.charge, frame.discharge).max()), emergency_charging=float(np.minimum(frame.charge, frame.emergency).max()), continuity=float(np.max(np.abs(frame.soc_start.to_numpy()[1:] - frame.soc_end.to_numpy()[:-1]))))
    assert all((abs(x) < 1e-06 for x in checks.values())), checks
    return checks

def export_annual(frame, output, parameters, summary=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    slots = canonical_frame(frame)
    checks = verify_frame(slots)
    slots = slots[slots.date >= '2025-02-01'].reset_index(drop=True)
    daily = slots.groupby('date', sort=True)[SUMCOLS].sum()
    daily['soc_start'] = slots.groupby('date').soc_start.first()
    daily['soc_end'] = slots.groupby('date').soc_end.last()
    result = dict(summary or {})
    result.update({key: float(slots[key].sum()) for key in SUMCOLS})
    result.update(reported_start=str(slots.date.iloc[0]), reported_end=str(slots.date.iloc[-1]), reported_days=int(slots.date.nunique()), reported_initial_soc_kwh=float(slots.soc_start.iloc[0]), reported_final_soc_kwh=float(slots.soc_end.iloc[-1]), strategy=parameters, verification=checks)
    output.mkdir(parents=True)
    slots.to_csv(output / 'slots.csv', index=False, float_format='%.12f')
    daily.to_csv(output / 'daily.csv', float_format='%.12f')
    (output / 'summary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def number(row: dict, key: str) -> float:
    if key not in row or row[key] in (None, ''):
        raise ValueError(f'Missing required value {key}: {row}')
    value = float(row[key])
    if not math.isfinite(value):
        raise ValueError(f'Nonfinite {key}')
    return value

def close(a: float, b: float, label: str) -> None:
    if abs(a - b) > max(1e-05, 1e-08 * abs(b)):
        raise ValueError(f'Reconciliation failed {label}: {a} != {b}')

def clock(slot: int) -> str:
    return f'{slot // 6:02d}:{10 * (slot % 6):02d}'

def interval(slot: int, stop: int | None=None) -> str:
    return f'{clock(slot)}-{clock(slot + 1 if stop is None else stop)}'

def is_effective_emergency(value: float) -> bool:
    return value > EMERGENCY_TOL_KWH

def excel_date(iso: str) -> int:
    return (date.fromisoformat(iso) - date(1899, 12, 30)).days

def q1_payload(root: Path) -> dict:
    path = root / 'q1' / 'schedule.csv'
    records = rows(path)
    summary_path = root / 'summaries.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))['q1']
    if len(records) != 144 or [int(r['slot_index']) for r in records] != list(range(144)):
        raise ValueError('Q1 must contain exactly ordered slots 0..143')
    for (i, row) in enumerate(records):
        if row['interval'] != interval(i):
            raise ValueError(f'Q1 time mapping differs at slot {i}')
    battery = []
    for group in range(6):
        part = records[24 * group:24 * (group + 1)]
        battery.append([interval(24 * group, 24 * (group + 1)), sum((number(r, 'charge_kwh') for r in part)), sum((number(r, 'discharge_kwh') for r in part)), '00:00' if group == 0 else '24:00' if group == 1 else None, number(records[0], 'energy_start_kwh') if group == 0 else number(records[-1], 'energy_end_kwh') if group == 1 else None])
    grid = sum((number(r, 'grid_kwh') for r in records))
    cost = sum((number(r, 'purchase_cost_yuan') for r in records))
    close(grid, summary['grid_kwh'], 'Q1 grid')
    close(cost, summary['cost_yuan'], 'Q1 cost')
    return {'key': 'q1', 'filename': _FILE_BY_CASE['q1'], 'plan': [[interval(i), number(r, 'grid_kwh')] for (i, r) in enumerate(records)], 'battery': battery, 'controls': {'grid_kwh': grid, 'cost_yuan': cost}, 'source_hashes': {str(path.relative_to(ROOT)): sha(path), str(summary_path.relative_to(ROOT)): sha(summary_path)}}

def annual_payload(root: Path, key: str) -> dict:
    (slot_path, daily_path) = (root / 'annual_slots.csv', root / 'annual_daily.csv')
    records = [r for r in rows(slot_path) if r['case'] == key]
    daily_rows = [r for r in rows(daily_path) if r['case'] == key]
    daily = {r['date']: r for r in daily_rows}
    if len(daily) != len(daily_rows):
        raise ValueError(f'{key}: duplicate daily date keys')
    by_date: dict[str, list[dict]] = {}
    for row in records:
        by_date.setdefault(row['date'], []).append(row)
    expected = [(date(2025, 2, 1) + timedelta(days=i)).isoformat() for i in range(334)]
    if any((day not in by_date or day not in daily for day in expected)):
        raise ValueError(f'{key}: missing reporting days')
    (plan, adjusted, battery, emergency) = ([], [], [], [])
    total_controls = {x: 0.0 for x in ('plan', 'adjusted', 'charge', 'discharge', 'emergency', 'cost_plan', 'cost_up', 'cost_down', 'cost_emergency', 'cost_total')}
    for day in expected:
        part = sorted(by_date[day], key=lambda r: int(r['slot']))
        if len(part) != 144 or [int(r['slot']) for r in part] != list(range(144)):
            raise ValueError(f'{key}/{day}: slots are not exactly 0..143')
        sums = {field: sum((number(r, field) for r in part)) for field in total_controls}
        for (field, value) in sums.items():
            close(value, number(daily[day], field), f'{key}/{day}/{field}')
            total_controls[field] += value
        for row in part:
            close(number(row, 'cost_total'), sum((number(row, f) for f in ('cost_plan', 'cost_up', 'cost_down', 'cost_emergency'))), 'transaction sum')
        serial = excel_date(day)
        plan.append([serial] + [number(r, 'plan') for r in part] + [sums['plan'], sums['cost_plan']])
        adjusted.append([serial] + [number(r, 'adjusted') for r in part] + [sums['adjusted'], sums['cost_plan'] + sums['cost_up'] + sums['cost_down']])
        for group in range(6):
            block = part[group * 24:(group + 1) * 24]
            battery.append([serial if group == 0 else None, interval(group * 24, (group + 1) * 24), sum((number(r, 'charge') for r in block)), sum((number(r, 'discharge') for r in block)), '00:00' if group == 0 else '24:00' if group == 1 else None, number(part[0], 'soc_start') if group == 0 else number(part[-1], 'soc_end') if group == 1 else None])
        daily_emergency = []
        start = None
        for i in range(145):
            active = i < 144 and is_effective_emergency(number(part[i], 'emergency'))
            if active and start is None:
                start = i
            if not active and start is not None:
                daily_emergency.append([serial if not daily_emergency else None, interval(start, i), sum((number(r, 'emergency') for r in part[start:i]))])
                start = None
        if not daily_emergency:
            daily_emergency = [[serial, '无', 0.0]]
        close(sum((r[2] for r in daily_emergency)), sums['emergency'], 'emergency grouping')
        emergency.extend(daily_emergency)
    return {'key': key, 'filename': _FILE_BY_CASE[key], 'plan': plan, 'adjusted': adjusted if key in ('q3', 'q4_3') else None, 'battery': battery, 'emergency': emergency, 'controls': total_controls, 'first_date': expected[0], 'last_date': expected[-1], 'report_days': len(expected), 'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in (slot_path, daily_path)}}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def column(index):
    result = ''
    while index:
        (index, remainder) = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result

def column_number(address):
    value = 0
    for char in re.match('[A-Z]+', address).group():
        value = value * 26 + ord(char) - 64
    return value

def value_of(cell, shared):
    node = cell.find('s:v', NS)
    if node is not None and node.text is not None:
        if cell.get('t') == 's':
            return shared[int(node.text)]
        return node.text if cell.get('t') in ('str', 'e') else float(node.text)
    node = cell.find('s:is', NS)
    return ''.join(node.itertext()) if node is not None else None

def contents(archive, sheet_path):
    shared = []
    if 'xl/sharedStrings.xml' in archive.namelist():
        shared = [''.join(n.itertext()) for n in ET.fromstring(archive.read('xl/sharedStrings.xml'))]
    root = ET.fromstring(archive.read(sheet_path))
    cells = {c.get('r'): c for c in root.findall('s:sheetData/s:row/s:c', NS)}
    values = {a: value_of(c, shared) for (a, c) in cells.items()}
    return (root, cells, values)

def dated_groups(rows):
    result = defaultdict(list)
    day = None
    for row in rows:
        if row[0] is not None:
            day = int(row[0])
        result[day].append(row)
    return result

def prepare():
    WORK.mkdir(parents=True, exist_ok=True)
    payloads = [q1_payload(ROOT / 'results/c2026') if key == 'q1' else annual_payload(ROOT / 'results/c2026', key) for key in KEYS]
    books = []
    for (filename, payload) in zip(FILES, payloads):
        template = RESULTS / 'submission' / filename
        sheets = []
        with zipfile.ZipFile(template) as z:
            names = [n.attrib['name'] for n in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', NS)]
            for (index, name) in enumerate(names, 1):
                member = f'xl/worksheets/sheet{index}.xml'
                (root, cells, values) = contents(z, member)
                (fills, blocks, dates) = ({}, [], set())

                def assign(address, value):
                    assert address not in fills
                    assert cells.get(address) is None or cells[address].find('s:f', NS) is None
                    if isinstance(value, (int, float)):
                        assert math.isfinite(value)
                    fills[address] = value
                if name in ('计划购电量', '调整购电量'):
                    if payload['key'] == 'q1':
                        matrix = [[r[1]] for r in payload['plan']]
                        for (row, line) in enumerate(matrix, 2):
                            assign(f'B{row}', line[0])
                        blocks.append({'range': 'B2:B145', 'values': matrix})
                    else:
                        rows = payload['plan' if name == '计划购电量' else 'adjusted']
                        by_date = {int(row[0]): row[1:] for row in rows}
                        matrix = []
                        for row in range(2, 336):
                            day = int(values[f'A{row}'])
                            dates.add(day)
                            line = by_date[day]
                            matrix.append(line)
                            for (col, number) in enumerate(line, 2):
                                assign(f'{column(col)}{row}', number)
                        blocks.append({'range': 'B2:EQ335', 'values': matrix})
                elif name == '充放电量':
                    if payload['key'] == 'q1':
                        for (row, line) in enumerate(payload['battery'], 2):
                            assign(f'B{row}', line[1])
                            assign(f'C{row}', line[2])
                            if line[4] is not None:
                                assign(f'E{row}', line[4])
                    else:
                        by_date = dated_groups(payload['battery'])
                        day = None
                        for row_node in root.findall('s:sheetData/s:row', NS)[1:]:
                            row = int(row_node.get('r'))
                            label = values.get(f'A{row}')
                            if isinstance(label, (int, float)):
                                day = int(label)
                                dates.add(day)
                            elif label is not None:
                                day = None
                            if day is None:
                                continue
                            period = values.get(f'B{row}')
                            hour = int(str(period).split(':')[0])
                            assert hour in (0, 4, 8, 12, 16, 20), (filename, row, period)
                            record = by_date[day][hour // 4]
                            assign(f'C{row}', record[2])
                            assign(f'D{row}', record[3])
                            point = values.get(f'E{row}')
                            if point is not None:
                                assert point in (0, '24:00'), point
                                assign(f'F{row}', by_date[day][0 if point == 0 else 1][5])
                elif name == '紧急购电量':
                    available = defaultdict(list)
                    day = None
                    for row_node in root.findall('s:sheetData/s:row', NS)[1:]:
                        row = int(row_node.get('r'))
                        label = values.get(f'A{row}')
                        if isinstance(label, (int, float)):
                            day = int(label)
                            dates.add(day)
                        elif label is not None:
                            day = None
                        if day is not None:
                            available[day].append(row)
                    grouped = dated_groups(payload['emergency'])
                    for (day, positions) in available.items():
                        events = grouped[day]
                        assert len(events) <= len(positions), (filename, day, 'Insufficient template rows')
                        for (row, event) in zip(positions, events):
                            assign(f'B{row}', event[1])
                            assign(f'C{row}', event[2])
                else:
                    raise ValueError(name)
                if not blocks:
                    blocks = [{'range': a, 'values': [[v]]} for (a, v) in fills.items()]
                sheets.append({'name': name, 'member': member, 'fills': fills, 'blocks': blocks, 'dates': [str(date(1899, 12, 30) + timedelta(days=d)) for d in sorted(dates)], 'dimension': root.find('s:dimension', NS).get('ref'), 'preview': 'A1:F8' if name == '充放电量' else 'A1:C11' if name == '紧急购电量' else 'A1:H5' if payload['key'] != 'q1' else 'A1:B8'})
        books.append({'filename': filename, 'template': str(template), 'template_sha256': digest(template.read_bytes()), 'sheets': sheets, 'controls': payload['controls'], 'source_hashes': payload['source_hashes']})
    (WORK / 'fill_plan.json').write_text(json.dumps({'workbooks': books}, ensure_ascii=False))
    print(json.dumps({b['filename']: {s['name']: {'cells': len(s['fills']), 'dates': s['dates'] if len(s['dates']) < 10 else '334 days'} for s in b['sheets']} for b in books}, ensure_ascii=False))

def data_cell(address, value, original=None):
    if original is None:
        opening = f'<c r="{address}">'
    else:
        opening = re.match('<c\\b[^>]*>', original).group().replace('/>', '>')
    if isinstance(value, str):
        opening = re.sub('\\s+t="[^"]*"', '', opening)[:-1] + ' t="inlineStr">'
        inside = '<is><t>' + escape(value) + '</t></is>'
    else:
        opening = re.sub('\\s+t="[^"]*"', '', opening)
        inside = '<v>' + format(float(value), '.17g') + '</v>'
    return opening + inside + '</c>'
CELL = re.compile('<c\\b[^>]*?(?:/>|>.*?</c>)', re.S)
ROW = re.compile('(<row\\b[^>]*>)(.*?)(</row>)', re.S)

def patch_sheet(xml, fills):
    grouped = defaultdict(dict)
    for (address, value) in fills.items():
        grouped[int(re.search('\\d+', address).group())][address] = value
    consumed = set()

    def row_replace(match):
        row = int(re.search('\\br="(\\d+)"', match.group(1)).group(1))
        if row not in grouped:
            return match.group()
        wanted = grouped[row]
        existing = {}
        remainder = CELL.sub('', match.group(2))
        assert not remainder.strip(), remainder
        for cell in CELL.finditer(match.group(2)):
            address = re.search('\\br="([A-Z]+\\d+)"', cell.group()).group(1)
            existing[address] = cell.group()
        for (address, value) in wanted.items():
            existing[address] = data_cell(address, value, existing.get(address))
            consumed.add(address)
        ordered = ''.join((existing[a] for a in sorted(existing, key=column_number)))
        return match.group(1) + ordered + match.group(3)
    result = ROW.sub(row_replace, xml)
    assert consumed == set(fills)
    return result

def finalize(verify_artifact=False):
    plan = json.loads((WORK / 'fill_plan.json').read_text())
    reports = []
    staging = WORK / 'filled'
    staging.mkdir(exist_ok=True)
    for book in plan['workbooks']:
        template = Path(book['template'])
        assert digest(template.read_bytes()) == book['template_sha256']
        destination = staging / book['filename']
        with zipfile.ZipFile(template) as original:
            replacements = {}
            for sheet in book['sheets']:
                replacements[sheet['member']] = patch_sheet(original.read(sheet['member']).decode(), sheet['fills']).encode()
            with zipfile.ZipFile(destination, 'w') as out:
                out.comment = original.comment
                for info in original.infolist():
                    out.writestr(info, replacements.get(info.filename, original.read(info.filename)))
        with zipfile.ZipFile(template) as original, zipfile.ZipFile(destination) as result:
            assert original.namelist() == result.namelist()
            for member in original.namelist():
                if member not in replacements:
                    assert original.read(member) == result.read(member), member
            for sheet in book['sheets']:
                (old_root, old_cells, old_values) = contents(original, sheet['member'])
                (new_root, new_cells, new_values) = contents(result, sheet['member'])
                assert [(r.tag, r.attrib) for r in old_root.findall('s:sheetData/s:row', NS)] == [(r.tag, r.attrib) for r in new_root.findall('s:sheetData/s:row', NS)]
                for (a, c) in old_cells.items():
                    if a not in sheet['fills']:
                        assert ET.tostring(c) == ET.tostring(new_cells[a]), (sheet['name'], a)
                    else:
                        assert {k: v for (k, v) in c.attrib.items() if k != 't'} == {k: v for (k, v) in new_cells[a].attrib.items() if k != 't'}, (book['filename'], sheet['name'], a)
                for (a, v) in sheet['fills'].items():
                    actual = new_values[a]
                    assert actual == v or (isinstance(v, (int, float)) and math.isclose(actual, v, rel_tol=1e-13, abs_tol=1e-10))
                old_root.remove(old_root.find('s:sheetData', NS))
                new_root.remove(new_root.find('s:sheetData', NS))
                assert ET.tostring(old_root) == ET.tostring(new_root), sheet['name']
        for (relative, expected) in book['source_hashes'].items():
            assert digest((ROOT / relative).read_bytes()) == expected, relative
        reports.append({'filename': book['filename'], 'template_sha256': book['template_sha256'], 'output_sha256': digest(destination.read_bytes()), 'only_authorized_data_cells_changed': True, 'source_unchanged': True, 'independent_saved_xlsx_check': {'engine': 'OOXML readback', 'passed': True, 'checked_cells': sum((len(s['fills']) for s in book['sheets'])), 'scope': 'All filled cells and all preserved original cells and workbook parts'}, 'unchanged_row_count_and_attributes': True, 'unchanged_styles_headers_metadata_and_other_parts': True, 'filled_cells': sum((len(s['fills']) for s in book['sheets'])), 'sheet_coverage': {s['name']: s['dates'] if len(s['dates']) < 10 else '334 days' for s in book['sheets']}})
    (WORK / 'audit.json').write_text(json.dumps({'schema': 'c2026-template-data-only-v1', 'row_policy': 'Preserve all base workbook rows and existing labels, including omission marks.', 'time_policy': 'Preserve template labels; retain the accepted ordinal slot mapping.', 'workbooks': reports}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(reports, ensure_ascii=False))

def main():
    global WORK
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['verify', 'rebuild'])
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.phase == 'verify':
        report = {}
        frames = pd.read_csv(RESULTS / 'annual_slots.csv')
        for name in ('q2', 'q3', 'q4_2', 'q4_3'):
            frame = frames.loc[frames['case'] == name]
            report[name] = verify_frame(frame)
        print(json.dumps(report, indent=2))
        return
    if args.out is None:
        parser.error('--out is required for rebuild')
    if args.out.exists():
        raise FileExistsError(args.out)
    WORK = args.out.resolve()
    prepare()
    finalize(False)
if __name__ == '__main__':
    main()
