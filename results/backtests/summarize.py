import argparse
import importlib.metadata
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run
    summary = json.loads((run/'summary.json').read_text())
    fields = ['total_fee', 'original_fee', 'increase_fee', 'decrease_penalty', 'refund',
              'emergency_fee', 'emergency', 'emergency_events', 'unused', 'terminal_soc_kwh',
              'terminal_credit_sensitivity_yuan', 'contract_modification_decisions']
    table = pd.DataFrame([{k: v[k] for k in fields} | {'strategy': name} for name, v in summary.items()])
    table.to_csv(run/'comparison.csv', index=False)
    for name, totals in summary.items():
        events = pd.read_csv(run/name/'events.csv')
        if events.empty:
            continue
        intervals = pd.read_csv(run/name/'intervals.csv.gz').set_index(['date', 'interval_index'])
        current = intervals.planned_grid.to_dict()
        expanded = []
        for event in events.itertuples(index=False):
            key = (event.date, event.interval_index)
            before = current[key]
            after = before+event.increase_kwh-event.decrease_kwh
            current[key] = after
            slot = intervals.loc[key]
            expanded.append({'decision_time': event.issue_time,
                'delivery_interval': slot.interval_start+'/'+slot.interval_end,
                'previous_contract': before, 'new_contract': after,
                'delta_plus': event.increase_kwh, 'delta_minus': event.decrease_kwh,
                'decision_price': slot.plan_price, 'settlement_price': event.delivery_price,
                'adjustment_charge': event.increase_fee+event.decrease_penalty-event.refund,
                'settlement_rule': totals['strategy']['interpretation']})
        assert max(abs(current[key]-value) for key, value in intervals.contract_grid.items()) < 1e-5
        pd.DataFrame(expanded).to_csv(run/name/'contract_event_ledger.csv', index=False)
    comparisons = {}
    pairs = [('q2_point', 'q2_margin'), ('q2_margin', 'q2_margin_greedy'),
             ('q3_frozen_update', 'q3_battery_update'), ('q3_battery_update', 'q3_adjust_A'),
             ('q3_adjust_A', 'q3_selective_A'), ('q3_adjust_A', 'q3_adjust_B')]
    rng = np.random.default_rng(2026)
    for before, after in pairs:
        a = pd.read_csv(run/before/'daily.csv').set_index('date')
        b = pd.read_csv(run/after/'daily.csv').set_index('date')
        delta = (a.total_fee-b.total_fee).to_numpy()
        n = len(delta)
        starts = rng.integers(0, n, size=(1000, (n+6)//7))
        indices = ((starts[:, :, None]+np.arange(7)) % n).reshape(1000, -1)[:, :n]
        draws = delta[indices].sum(axis=1)
        comparisons[before+' -> '+after] = {
            'saving_yuan_positive_means_after_cheaper': float(delta.sum()),
            'saving_percent': float(100*delta.sum()/a.total_fee.sum()),
            'days_after_cheaper': int((delta > 1e-6).sum()),
            'days_after_more_expensive': int((delta < -1e-6).sum()),
            'paired_circular_7day_block_bootstrap_95percent_interval': np.quantile(draws, [.025, .975]).tolist(),
            'bootstrap_replicates': 1000,
            'monthly_saving_yuan': dict((a.total_fee-b.total_fee).groupby(a.index.str[:7]).sum())}
    metrics = pd.read_csv(run/'forecast_metrics.csv')
    metrics = metrics.loc[metrics.date >= '2025-02-01']
    forecast = []
    for (group, target), values in metrics.groupby(['forecast_group', 'target']):
        forecast.append({'forecast_group': group, 'target': target,
                         'mae_kwh': float(values.mae_kwh.mean()),
                         'rmse_kwh': float(np.sqrt(np.mean(values.rmse_kwh**2))),
                         'mean_daily_mase': float(values.mase_lag144.mean()),
                         'daylight_mae_kwh': float(values.daylight_mae_kwh.mean()) if target == 'pv' else None})
    pd.DataFrame(forecast).to_csv(run/'forecast_summary.csv', index=False)
    evaluation = pd.read_csv(run/'forecast_evaluation.csv.gz')
    evaluation = evaluation.loc[evaluation.date >= '2025-02-01']
    interval = evaluation.groupby('forecast_group').agg(
        upper_buffer_empirical_coverage=('net_upper_covered', 'mean'),
        mean_pinball_kwh=('net_quantile_pinball_kwh', 'mean'),
        mean_margin_kwh=('margin_kwh', 'mean'))
    interval.to_csv(run/'margin_summary.csv')
    truth = pd.read_csv('data/processed/2026C/actuals.csv',
                        usecols=['date', 'interval_index', 'price_variable'])
    evaluated = evaluation.merge(truth, on=['date', 'interval_index'], validate='many_to_one')
    price_scores = []
    for group, values in evaluated.groupby('forecast_group'):
        if not group.startswith('variable'):
            continue
        error = values.predicted_price-values.price_variable
        price_scores.append({'forecast_group': group, 'mae_yuan_per_kwh': float(abs(error).mean()),
                             'rmse_yuan_per_kwh': float(np.sqrt(np.mean(error**2))),
                             'price_error_netload_residual_correlation_descriptive_only':
                                 float(error.corr(values.actual_net_residual_kwh))})
    pd.DataFrame(price_scores).to_csv(run/'price_forecast_summary.csv', index=False)
    (run/'paired_comparisons.json').write_text(json.dumps(comparisons, indent=2)+'\n')
    versions = {name: importlib.metadata.version(name) for name in
                ['numpy', 'pandas', 'scipy', 'scikit-learn', 'pytest']}
    versions['python'] = platform.python_version()
    (run/'runtime_versions.json').write_text(json.dumps(versions, indent=2)+'\n')
    print(table[['strategy', 'total_fee', 'emergency', 'terminal_soc_kwh']].to_string(index=False))
    print(json.dumps({key: value['saving_yuan_positive_means_after_cheaper'] for key, value in comparisons.items()}, indent=2))


if __name__ == '__main__':
    main()
