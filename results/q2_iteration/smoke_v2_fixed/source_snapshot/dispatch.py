from dataclasses import dataclass
import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix


@dataclass(frozen=True)
class Battery:
    minimum: float = 1200
    maximum: float = 10800
    power_kw: float = 5000
    eta_charge: float = 0.9
    eta_discharge: float = 0.9
    dt: float = 1 / 6


def optimize(load, pv, price, initial=6000, terminal=6000, battery=Battery(),
             relax=False, time_limit=60, mip_gap=1e-8):
    load, pv, price = (np.asarray(x, dtype=float) for x in (load, pv, price))
    n = len(load)
    assert len(pv) == len(price) == n and n > 0
    assert np.all(np.isfinite(np.r_[load, pv, price]))
    assert np.all(load >= 0) and np.all(pv >= 0) and np.all(price > 0)
    q, c, d, w, e, z = 0, n, 2*n, 3*n, 4*n, 5*n+1
    size = 6*n + 1
    obj = np.zeros(size)
    obj[q:q+n] = price
    lb, ub = np.zeros(size), np.full(size, np.inf)
    cap = battery.power_kw * battery.dt
    ub[c:c+n] = ub[d:d+n] = cap
    lb[e:e+n+1], ub[e:e+n+1] = battery.minimum, battery.maximum
    lb[e] = ub[e] = initial
    if terminal is not None:
        lb[e+n] = ub[e+n] = terminal
    ub[z:z+n] = 1
    a = lil_matrix((4*n, size))
    low, high = np.full(4*n, -np.inf), np.full(4*n, np.inf)
    for t in range(n):
        a[t, q+t], a[t, c+t], a[t, d+t], a[t, w+t] = 1, -1, 1, -1
        low[t] = high[t] = load[t] - pv[t]
        a[n+t, e+t+1], a[n+t, e+t] = 1, -1
        a[n+t, c+t], a[n+t, d+t] = -battery.eta_charge, 1/battery.eta_discharge
        low[n+t] = high[n+t] = 0
        a[2*n+t, c+t], a[2*n+t, z+t] = 1, -cap
        high[2*n+t] = 0
        a[3*n+t, d+t], a[3*n+t, z+t] = 1, cap
        high[3*n+t] = cap
    integral = np.zeros(size)
    if not relax:
        integral[z:z+n] = 1
    tic = time.perf_counter()
    sol = milp(obj, integrality=integral, bounds=Bounds(lb, ub),
               constraints=LinearConstraint(a.tocsc(), low, high),
               options={'time_limit': time_limit, 'mip_rel_gap': mip_gap})
    elapsed = time.perf_counter()-tic
    if sol.x is None:
        raise RuntimeError(f'No feasible optimization result: {sol.message}')
    x = sol.x
    return dict(grid=x[q:q+n], charge=x[c:c+n], discharge=x[d:d+n],
                unused=x[w:w+n], soc=x[e:e+n+1],
                solver=dict(status=int(sol.status), message=sol.message, objective=float(sol.fun),
                            runtime_seconds=elapsed, mip_gap=getattr(sol, 'mip_gap', None),
                            dual_bound=getattr(sol, 'mip_dual_bound', None), relax=relax))


def simple_rule(load, pv, price, battery=Battery(), initial=6000):
    load, pv = np.asarray(load), np.asarray(pv)
    n = len(load)
    c, d = np.zeros(n), np.zeros(n)
    soc = np.full(n+1, float(initial))
    cap = battery.power_kw*battery.dt
    removable = np.maximum(load[96:]-pv[96:], 0).sum()/battery.eta_discharge
    top = min(battery.maximum, initial+removable)
    for t in range(n):
        if t < 36:
            c[t] = min(cap, max(0, (top-soc[t])/battery.eta_charge))
        elif t >= 96:
            d[t] = min(cap, max(load[t]-pv[t], 0), max(0, (soc[t]-initial)*battery.eta_discharge))
        soc[t+1] = soc[t]+battery.eta_charge*c[t]-d[t]/battery.eta_discharge
    q = np.maximum(load-pv+c-d, 0)
    w = q+pv+d-load-c
    return dict(grid=q, charge=c, discharge=d, unused=w, soc=soc,
                solver=dict(status='RULE', objective=float(np.dot(q, price))))
