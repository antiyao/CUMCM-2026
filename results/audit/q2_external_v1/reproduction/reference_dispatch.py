"""C2026 Q1: deterministic dispatch under EXPLICIT provisional conventions.

Run:
    python solve_q1.py --input model_inputs.npz --out outputs/q1
    python verify_q1.py --input model_inputs.npz --csv outputs/q1/q1_dispatch_review.csv

This script does not edit the official Excel templates. Their interval labels
need reconciliation with the 00:00--24:00 horizon before final submission.
Requires Python 3.10+, NumPy and SciPy.
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from typing import Any
import numpy as np
import scipy
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import lil_matrix

def dispatch(
    load_kwh: np.ndarray, pv_kwh: np.ndarray, price: np.ndarray,
    *, initial: float = 6000.0, terminal: float = 6000.0,
    eta_c: float = 0.9, eta_d: float = 0.9, integer_mode: bool = True,
) -> dict[str, Any]:
    """Grid-side charge/discharge energies; surplus may be curtailed, never sold."""
    L, V, p = [np.asarray(x, dtype=float) for x in (load_kwh, pv_kwh, price)]
    if L.ndim != 1 or L.shape != V.shape or L.shape != p.shape:
        raise ValueError("load, PV and price must have the same one-dimensional shape")
    if not all(np.isfinite(x).all() for x in (L, V, p)):
        raise ValueError("Non-finite inputs are not permitted")
    if np.any(L < 0) or np.any(V < 0) or np.any(p <= 0):
        raise ValueError("This baseline expects nonnegative load/PV and strictly positive prices")
    if not (0 < eta_c <= 1 and 0 < eta_d <= 1):
        raise ValueError("Efficiencies must be in (0, 1]")
    if not (1200 <= initial <= 10800 and 1200 <= terminal <= 10800):
        raise ValueError("Initial and terminal storage must satisfy physical bounds")
    n = len(p)
    m = (6 if integer_mode else 5) * n + 1
    ix = {
        "grid": np.arange(n),
        "charge": np.arange(n, 2*n),
        "discharge": np.arange(2*n, 3*n),
        "surplus": np.arange(3*n, 4*n),
        "energy": np.arange(4*n, 5*n+1),
    }
    objective = np.zeros(m)
    objective[ix["grid"]] = p
    lower = np.zeros(m)
    upper = np.full(m, np.inf)
    cap = 5000.0 / 6.0
    upper[ix["charge"]] = cap
    upper[ix["discharge"]] = cap
    lower[ix["energy"]] = 1200
    upper[ix["energy"]] = 10800
    lower[ix["energy"][0]] = upper[ix["energy"][0]] = initial
    lower[ix["energy"][-1]] = upper[ix["energy"][-1]] = terminal
    A = lil_matrix((2*n, m))
    b = np.zeros(2*n)
    for t in range(n):
        A[t, ix["grid"][t]] = 1
        A[t, ix["charge"][t]] = -1
        A[t, ix["discharge"][t]] = 1
        A[t, ix["surplus"][t]] = -1
        b[t] = L[t] - V[t]
        A[n+t, ix["energy"][t+1]] = 1
        A[n+t, ix["energy"][t]] = -1
        A[n+t, ix["charge"][t]] = -eta_c
        A[n+t, ix["discharge"][t]] = 1 / eta_d
    A = A.tocsc()
    if integer_mode:
        mode = np.arange(5*n+1, 6*n+1)
        upper[mode] = 1
        integrality = np.zeros(m, dtype=int)
        integrality[mode] = 1
        U = lil_matrix((2*n, m))
        u = np.zeros(2*n)
        for t in range(n):
            U[t, ix["charge"][t]] = 1
            U[t, mode[t]] = -cap
            U[n+t, ix["discharge"][t]] = 1
            U[n+t, mode[t]] = cap
            u[n+t] = cap
        result = milp(
            objective, integrality=integrality, bounds=Bounds(lower, upper),
            constraints=[LinearConstraint(A, b, b),
                         LinearConstraint(U.tocsc(), -np.inf, u)],
            options={"time_limit": 30.0, "mip_rel_gap": 1e-9},
        )
    else:
        result = linprog(objective, A_eq=A, b_eq=b,
                         bounds=np.column_stack((lower, upper)), method="highs")
    if not result.success or result.x is None:
        raise RuntimeError(f"Optimization did not finish successfully: {result.message}")
    s: dict[str, Any] = {key: result.x[idx].copy() for key, idx in ix.items()}
    s["cost"] = float(p @ s["grid"])
    s["solver_status"] = int(result.status)
    s["solver_message"] = str(result.message)
    s["mip_gap"] = float(getattr(result, "mip_gap", 0.0))
    return s

def clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("model_inputs.npz"))
    parser.add_argument("--out", type=Path, default=Path("outputs/q1"))
    parser.add_argument("--eta-c", type=float, default=0.9)
    parser.add_argument("--eta-d", type=float, default=0.9)
    args = parser.parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    with np.load(args.input, allow_pickle=False) as data:
        p = data["q1_price"].copy()
        L = data["q1_load_kw"].copy() / 6.0
        V = data["q1_pv_kw"].copy() / 6.0
    if len(p) != 144:
        raise ValueError("The supplied Q1 snapshot must contain 144 observations")
    sol = dispatch(L, V, p, eta_c=args.eta_c, eta_d=args.eta_d)
    relaxed = dispatch(L, V, p, eta_c=args.eta_c, eta_d=args.eta_d, integer_mode=False)
    args.out.mkdir(parents=True, exist_ok=True)
    file_path = args.out / "q1_dispatch_review.csv"
    with file_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["step", "interval_start_assumed", "interval_end_assumed",
                         "source_time", "price_yuan_per_kwh", "load_kwh", "pv_kwh",
                         "grid_kwh", "charge_grid_side_kwh", "discharge_grid_side_kwh",
                         "surplus_kwh", "energy_start_kwh", "energy_end_kwh",
                         "grid_cost_yuan"])
        for t in range(144):
            writer.writerow([t, clock(t*10), clock((t+1)*10),
                             clock((t+1)*10) if t < 143 else "0:00+1",
                             p[t], L[t], V[t], sol["grid"][t], sol["charge"][t],
                             sol["discharge"][t], sol["surplus"][t],
                             sol["energy"][t], sol["energy"][t+1],
                             p[t]*sol["grid"][t]])
    summary = {
        "scope": "Q1 conditional benchmark, NOT final official template output",
        "source": "Attachment 1 Sheet1 B2:D145; C problem Appendix 1",
        "conventions": {
            "interval": "source sample at 00:10 represents the preceding 00:00--00:10 interval",
            "power_to_energy": "representative power multiplied by 1/6 hour",
            "initial_terminal_kwh": [6000, 6000],
            "eta_charge": args.eta_c, "eta_discharge": args.eta_d,
            "energy_metering": "charge and discharge are measured on the microgrid AC side",
            "surplus": "unutilized surplus allowed; no sales revenue",
            "templates": "original templates NOT modified because their time labels are offset",
        },
        "numpy_version": np.__version__, "scipy_version": scipy.__version__,
        "solver_status": sol["solver_status"], "mip_gap": sol["mip_gap"],
        "cost_yuan": sol["cost"], "lp_relaxation_cost_yuan": relaxed["cost"],
        "no_storage_cost_yuan": float(p @ np.maximum(L-V, 0)),
        "grid_kwh": float(sol["grid"].sum()),
        "charge_kwh": float(sol["charge"].sum()),
        "discharge_kwh": float(sol["discharge"].sum()),
        "surplus_kwh": float(sol["surplus"].sum()),
        "min_energy_kwh": float(sol["energy"].min()),
        "max_energy_kwh": float(sol["energy"].max()),
        "max_bus_balance_error_kwh": float(np.abs(sol["grid"]+V+sol["discharge"]
                                                      -L-sol["charge"]-sol["surplus"]).max()),
        "max_storage_error_kwh": float(np.abs(np.diff(sol["energy"])
                                       -args.eta_c*sol["charge"]+sol["discharge"]/args.eta_d).max()),
        "simultaneous_charge_discharge_steps": int(np.sum((sol["charge"]>1e-6)&(sol["discharge"]>1e-6))),
    }
    (args.out / "q1_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
