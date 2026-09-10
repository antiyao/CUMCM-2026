import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from q2_iteration import Variant, prepare_forecasts, visible_packet, execute_plan, plan_packet
from dispatch import Battery
from q2_adaptive import select_past_policy


def test_future_shadow_results_cannot_select_current_policy():
    rows=[dict(strategy=s,date='2025-01-31',available_at='2025-02-01',
               cost_yuan=cost,start_soc=6000,end_soc=6000) for s,cost in [('a',10),('b',20)]]
    first=select_past_policy(rows,'2025-02-01',np.ones(144),.9)
    rows += [dict(strategy=s,date='2025-02-01',available_at='2025-02-02',
                 cost_yuan=cost,start_soc=6000,end_soc=6000) for s,cost in [('a',1e6),('b',0)]]
    second=select_past_policy(rows,'2025-02-01',np.ones(144),.9)
    assert first==second and first[0]=='a'


def test_future_data_does_not_change_forecast_or_hourly_buffer():
    root=Path(__file__).resolve().parents[1]
    data=pd.read_csv(root/'data/processed/2026C/actuals.csv',parse_dates=['interval_start','interval_end','available_at'])
    data=data.loc[data.date<='2025-02-02'].copy()
    price=pd.read_csv(root/'data/processed/2026C/q1.csv').price.to_numpy()
    days,cache,meta=prepare_forecasts(data,price)
    other=data.copy()
    mask=other.available_at>pd.Timestamp('2025-02-01')
    other.loc[mask,['load_kwh','pv_kwh','price_variable']]*=10
    d2,c2,m2=prepare_forecasts(other,price)
    index=list(days).index('2025-02-01')
    for v in [Variant('base',margin='hourly'),Variant('bias',bias_days=3,margin='hourly'),
              Variant('policy',margin='legacy',policy_history=14)]:
        a=visible_packet(days,cache,meta,index,v)
        b=visible_packet(d2,c2,m2,index,v)
        for key in ['load','pv','margin','residual_days']:
            np.testing.assert_array_equal(a[key],b[key])
        assert (a['residual_available_at']<=a['cutoff']).all()
        if v.policy_history:
            pa=plan_packet(a,v,6000,price,Battery())
            pb=plan_packet(b,v,6000,price,Battery())
            np.testing.assert_array_equal(pa['grid'],pb['grid'])


def test_hourly_pool_is_historical_and_zero_quantile_means_disabled():
    days=pd.date_range('2025-01-01',periods=20).strftime('%Y-%m-%d').tolist()
    cache={k:np.zeros((20,144)) for k in ['load','pv','load_error','pv_error','legacy_margin']}
    cache['load_error'][:]=np.repeat(np.arange(24),6)
    meta=[{} for _ in days]
    p=visible_packet(days,cache,meta,19,Variant('hour',margin='hourly',quantile=.8))
    np.testing.assert_array_equal(p['margin'],np.repeat(np.arange(24),6))
    p0=visible_packet(days,cache,meta,19,Variant('zero',margin='hourly',quantile=0))
    np.testing.assert_array_equal(p0['margin'],np.zeros(144))


def test_price_reserve_keeps_contract_fixed_and_emergency_not_charging():
    start=pd.Timestamp('2025-02-01')
    day=pd.DataFrame({'date':'2025-02-01','interval_index':np.arange(144),
        'interval_start':pd.date_range(start,periods=144,freq='10min'),
        'interval_end':pd.date_range(start+pd.Timedelta(minutes=10),periods=144,freq='10min'),
        'load_kwh':np.full(144,100.),'pv_kwh':np.zeros(144)})
    q=np.full(144,50.)
    plan={'grid':q,'soc':np.full(145,6000.)}
    price=np.r_[np.full(72,.5),np.ones(72)]
    frame,state=execute_plan(day,price,plan,6000,Variant('reserve',controller='price_reserve',reserve_alpha=.5),Battery())
    np.testing.assert_array_equal(frame.contract_grid,q)
    assert np.minimum(frame.emergency,frame.charge).max()==0
    assert abs(frame.original_fee.sum()-q@price)<1e-8
    assert 1200<=state<=10800
