from pathlib import Path
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import scipy

from dispatch import Battery, optimize, simple_rule
from validate_dispatch import check_dispatch

ROOT = Path(__file__).resolve().parents[1]


def main():
    cfg = json.loads((ROOT/'configs/2026c.json').read_text())
    inp = ROOT/cfg['processed_dir']/'q1.csv'
    df = pd.read_csv(inp)
    load, pv, price = (df[x].to_numpy() for x in ['load_kwh','pv_kwh','price'])
    battery = Battery(cfg['minimum_kwh'], cfg['maximum_kwh'], cfg['power_kw'],
                      cfg['efficiency_charge'], cfg['efficiency_discharge'], cfg['dt_hours'])
    q0 = np.maximum(load-pv, 0)
    solutions = {'no_storage': dict(grid=q0, charge=np.zeros(144), discharge=np.zeros(144),
                 unused=np.maximum(pv-load,0), soc=np.full(145,6000.),
                 solver=dict(status='BASELINE', objective=float(price@q0))),
                 'simple_rule':simple_rule(load,pv,price,battery),
                 'milp': optimize(load,pv,price,battery=battery, time_limit=cfg['solver_time_limit_seconds'], mip_gap=cfg['mip_gap']),
                 'lp_relaxation': optimize(load,pv,price,battery=battery,relax=True)}
    out = ROOT/'results/q1'
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    for name, sol in solutions.items():
        checks = check_dispatch(load,pv,price,sol)
        if name != 'lp_relaxation':
            assert checks['passed'], (name,checks)
        detail = df.copy()
        for key, col in [('grid','grid_kwh'),('charge','charge_kwh'),('discharge','discharge_kwh'),('unused','unused_kwh')]:
            detail[col] = sol[key]
        detail['soc_start_kwh'], detail['soc_end_kwh'] = sol['soc'][:-1], sol['soc'][1:]
        detail.to_csv(out/f'{name}_dispatch.csv', index=False)
        report[name] = dict(solver=sol['solver'], validation=checks, grid_kwh=float(sol['grid'].sum()),
                           charge_kwh=float(sol['charge'].sum()), discharge_kwh=float(sol['discharge'].sum()),
                           unused_kwh=float(sol['unused'].sum()), soc_min_kwh=float(sol['soc'].min()),
                           soc_max_kwh=float(sol['soc'].max()))
    assert solutions['lp_relaxation']['solver']['objective'] <= solutions['milp']['solver']['objective']+1e-6
    sensitivity = []
    for name, b, l, v in [
        ('round_trip_90_percent',Battery(eta_charge=np.sqrt(.9),eta_discharge=np.sqrt(.9)),load,pv),
        ('instantaneous_points_periodic_linear',battery,(load+np.roll(load,1))/2,(pv+np.roll(pv,1))/2)]:
        s = optimize(l,v,price,battery=b)
        chk=check_dispatch(l,v,price,s,eta_charge=b.eta_charge,eta_discharge=b.eta_discharge)
        assert chk['passed'],chk
        sensitivity.append(dict(case=name,cost_yuan=s['solver']['objective'],grid_kwh=float(s['grid'].sum()),validation=chk))
    best=solutions['milp']
    pd.DataFrame([dict(start_minute=t*10,end_minute=(t+1)*10,grid_kwh=best['grid'][t]) for t in [60,72,84,96,108,120]]).to_csv(out/'table1.csv',index=False)
    pd.DataFrame([dict(start_hour=k*4,end_hour=(k+1)*4,charge_kwh=best['charge'][k*24:(k+1)*24].sum(),
                  discharge_kwh=best['discharge'][k*24:(k+1)*24].sum()) for k in range(6)]).to_csv(out/'table2.csv',index=False)
    summary=dict(run_id=datetime.now(timezone.utc).strftime('q1-%Y%m%dT%H%M%SZ'), config=cfg,
                 input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),
                 code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'src/dispatch.py',ROOT/'src/validate_dispatch.py']},
                 git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                 dirty_worktree=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)),
                 environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__),
                 total_load_kwh=float(load.sum()),total_pv_kwh=float(pv.sum()),strategies=report,
                 sensitivity=sensitivity, template_status='TEMPLATE_TIME_LABEL_AMBIGUITY',
                 evidence_boundary='Optimization certificate and independent physical checks for the discretized assumed model, not external field validation')
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:dict(cost=v['solver']['objective'],grid_kwh=v['grid_kwh'],validated=v['validation']['passed']) for k,v in report.items()},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
