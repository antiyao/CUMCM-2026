import numpy as np


def check_dispatch(load, pv, price, result, eta_charge=0.9, eta_discharge=0.9,
                   minimum=1200, maximum=10800, limit=5000/6, cyclic=True):
    q, c, d, w, e = [np.asarray(result[x]) for x in ['grid','charge','discharge','unused','soc']]
    metrics = dict(
        bus_residual_kwh=float(np.max(np.abs(q+pv+d-load-c-w))),
        soc_residual_kwh=float(np.max(np.abs(np.diff(e)-eta_charge*c+d/eta_discharge))),
        lower_bound_violation_kwh=float(max(0, minimum-e.min())),
        upper_bound_violation_kwh=float(max(0, e.max()-maximum)),
        power_violation_kwh=float(max(0, max(c.max(), d.max())-limit)),
        nonnegative_violation_kwh=float(max(0, -min(q.min(), c.min(), d.min(), w.min()))),
        simultaneous_charge_discharge_kwh=float(np.max(np.minimum(c, d))),
        terminal_difference_kwh=float(abs(e[-1]-e[0])) if cyclic else 0,
        objective_recomputed_yuan=float(np.dot(price, q)),
        objective_difference_yuan=float(abs(np.dot(price,q)-result['solver']['objective'])),
        finite=bool(np.isfinite(np.r_[q,c,d,w,e]).all()))
    metrics['passed'] = metrics['finite'] and all(v < 1e-6 for k,v in metrics.items()
                  if k not in ['objective_recomputed_yuan','finite'])
    return metrics
