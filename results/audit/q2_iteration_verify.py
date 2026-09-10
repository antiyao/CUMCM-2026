import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True


def max_error(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert a.shape == b.shape and np.array_equal(np.isnan(a), np.isnan(b))
    finite = np.isfinite(a)
    return float(np.max(abs(a[finite] - b[finite]))) if finite.any() else 0.


def check_trace(directory, expected_actual, price, cached, days):
    frame = pd.read_csv(directory / 'intervals.csv.gz')
    summary = json.loads((directory / 'summary.json').read_text())
    assert len(frame) == len(expected_actual)
    assert frame[['date', 'interval_index']].equals(expected_actual[['date', 'interval_index']])
    metrics = {column + '_source_error': max_error(frame[column], expected_actual[column]) for column in ['load_kwh', 'pv_kwh']}
    metrics['price_source_error'] = max_error(frame.price, np.tile(price, summary['days']))
    metrics['contract_change_error'] = max_error(frame.planned_grid, frame.contract_grid)
    cost = math.fsum(frame.planned_grid * frame.price + 5 * frame.emergency * frame.price)
    metrics['total_cost_error_yuan'] = abs(cost - summary['total_fee'])
    metrics['ordinary_fee_error_yuan'] = max_error(frame.original_fee, frame.planned_grid * frame.price)
    metrics['emergency_fee_error_yuan'] = max_error(frame.emergency_fee, 5 * frame.emergency * frame.price)
    assert float(frame[['increase_fee', 'decrease_penalty', 'refund', 'contract_increase', 'contract_decrease']].abs().max().max()) < 1e-7
    energy, maximum_state, maximum_bus = 6000., 0., 0.
    for row in frame.itertuples():
        values = [row.planned_grid, row.contract_grid, row.charge, row.discharge, row.emergency, row.unused]
        assert all(math.isfinite(v) and v >= -1e-7 for v in values)
        assert row.charge <= 5000 / 6 + 1e-7 and row.discharge <= 5000 / 6 + 1e-7
        assert not (row.charge > 1e-7 and row.discharge > 1e-7)
        assert row.charge <= max(row.contract_grid + row.pv_kwh - row.load_kwh, 0) + 1e-7
        assert abs(row.soc_start - energy) < 1e-6
        energy += .9 * row.charge
        energy -= row.discharge / .9
        assert 1200 - 1e-6 <= energy <= 10800 + 1e-6
        maximum_state = max(maximum_state, abs(energy - row.soc_end))
        maximum_bus = max(maximum_bus, abs(row.contract_grid + row.pv_kwh + row.discharge + row.emergency - row.load_kwh - row.charge - row.unused))
        assert abs(row.emergency - max(row.load_kwh-row.contract_grid-row.pv_kwh-row.discharge, 0)) < 1e-7
        assert abs(row.unused-row.unused_pv-row.unused_purchased) < 1e-7
    metrics['state_recursion_max_error_kwh'] = maximum_state
    metrics['bus_max_error_kwh'] = maximum_bus
    metrics['final_state_error_kwh'] = abs(energy - summary['terminal_soc_kwh'])
    decisions = [json.loads(s) for s in (directory / 'decisions.jsonl').read_text().splitlines()]
    assert len(decisions) == summary['days']
    daily = pd.read_csv(directory / 'daily.csv')
    for index, decision in enumerate(decisions):
        assert not decision['attachment3_used'] and not decision['changed_contract']
        cutoff = pd.Timestamp(decision['cutoff'])
        assert pd.Timestamp(decision['training_label_cutoff']) <= cutoff
        for date in decision.get('bias_error_dates', []):
            assert pd.Timestamp(date) + pd.Timedelta(days=1) <= cutoff
        assert pd.Timestamp(decision['residual_last_date']) + pd.Timedelta(days=1) <= cutoff
        assert pd.Timestamp(decision['residual_first_date']) < cutoff
        group = frame.iloc[index * 144:(index + 1) * 144]
        assert group.date.nunique() == 1 and group.date.iloc[0] == cutoff.strftime('%Y-%m-%d')
        assert abs(decision['initial_soc'] - group.soc_start.iloc[0]) < 1e-7
        config = decision.get('config', decision.get('active_variant', summary['strategy']))
        if not config.get('scenario_count', 0) and not config.get('policy_history', 0):
            assert abs(decision['solver']['objective'] - math.fsum(group.original_fee)) < 1e-6
        assert abs(daily.total_fee.iloc[index] - math.fsum(group.total_fee)) < 1e-6
        assert abs(daily.initial_soc.iloc[index] - group.soc_start.iloc[0]) < 1e-6
        assert abs(daily.terminal_soc.iloc[index] - group.soc_end.iloc[-1]) < 1e-6
    assert all(value < 1e-6 for value in metrics.values()), metrics
    return {'passed': True, 'days': summary['days'], 'intervals': len(frame),
            'cost_yuan': cost, 'emergency_kwh': math.fsum(frame.emergency),
            'initial_soc_kwh': 6000., 'final_soc_kwh': energy, 'metrics': metrics}, decisions


def load_snapshot(run):
    snapshot = run / 'source_snapshot'
    sys.path.insert(0, str(snapshot))
    sys.path.insert(1, str(ROOT / 'src'))
    spec = importlib.util.spec_from_file_location('q2_reviewed_snapshot', snapshot / 'q2_iteration.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def independent_greedy(q, net, price, initial):
    net = np.atleast_2d(np.asarray(net, float))
    energy = np.full(len(net), initial)
    charges, discharges, emergencies, states = [], [], [], [energy.copy()]
    for t in range(len(price)):
        need = net[:, t] - q[t]
        charge = np.minimum(np.minimum(np.maximum(-need, 0), 5000 / 6), np.maximum(10800 - energy, 0) / .9)
        discharge = np.minimum(np.minimum(np.maximum(need, 0), 5000 / 6), np.maximum(energy - 1200, 0) * .9)
        emergency = np.maximum(need - discharge, 0)
        energy = energy + .9 * charge - discharge / .9
        charges.append(charge)
        discharges.append(discharge)
        emergencies.append(emergency)
        states.append(energy.copy())
    c, d, u = [np.asarray(values).T for values in [charges, discharges, emergencies]]
    ordinary = float(np.dot(price, q))
    emergency_cost = np.sum(u * (5 * price), axis=1)
    terminal = float(price.min() / .9 * np.maximum(6000 - energy, 0).mean())
    return {'objective': ordinary + float(emergency_cost.mean()) + terminal,
            'ordinary': ordinary, 'emergency_cost': emergency_cost,
            'terminal_cost': terminal, 'charge': c, 'discharge': d, 'emergency': u,
            'soc': np.asarray(states).T}


def packet_for_decision(module, days, cached, decision):
    config = decision.get('config', decision.get('active_variant'))
    variant = module.Variant(**config)
    index = days.index(decision['cutoff'][:10])
    meta = [None] * len(days)
    meta[index] = decision
    return module.visible_packet(days, cached, meta, index, variant), variant


def check_specialized(run, module, cached, days, metadata, actuals, price, all_decisions):
    result = {}
    for name, decisions in all_decisions.items():
        frame = pd.read_csv(run / name / 'intervals.csv.gz')
        policy_days = 0
        scenario_days = 0
        policy_metrics = {'final_objective_error_yuan': 0., 'initial_objective_reproduction_error_yuan': 0.,
                          'improvement_accounting_error_yuan': 0., 'actual_greedy_action_error_kwh': 0.,
                          'scenario_greedy_action_error_kwh': 0.}
        statuses = {}
        for i, decision in enumerate(decisions):
            config = decision.get('config', decision.get('active_variant', {}))
            block = frame.iloc[i * 144:(i + 1) * 144]
            if config.get('controller') == 'greedy':
                real = independent_greedy(block.planned_grid.to_numpy(), block.load_kwh.to_numpy() - block.pv_kwh.to_numpy(), price, block.soc_start.iloc[0])
                for field in ['charge', 'discharge', 'emergency']:
                    policy_metrics['actual_greedy_action_error_kwh'] = max(policy_metrics['actual_greedy_action_error_kwh'], max_error(real[field][0], block[field]))
            if config.get('policy_history', 0):
                packet, variant = packet_for_decision(module, days, cached, decision)
                net = packet['load'][None, :] - packet['pv'][None, :] + packet['residual_days']
                q = block.planned_grid.to_numpy()
                independent = independent_greedy(q, net, price, decision['initial_soc'])
                solver = decision['solver']
                assert solver['iterations'] <= solver['max_iterations'] == 50
                assert solver['objective'] <= solver['initial_objective'] + 1e-7
                assert pd.Timestamp(solver['latest_residual_available_at']) <= pd.Timestamp(decision['cutoff'])
                assert solver['scenario_control_uses_future'] is False
                assert solver['scenario_count'] == len(packet['residual_days'])
                policy_metrics['final_objective_error_yuan'] = max(policy_metrics['final_objective_error_yuan'], abs(independent['objective'] - solver['objective']))
                policy_metrics['improvement_accounting_error_yuan'] = max(policy_metrics['improvement_accounting_error_yuan'], abs(solver['initial_objective'] - solver['objective'] - solver['in_sample_improvement_yuan']))
                initial = module.checked_optimization(packet['load'] + packet['margin'], packet['pv'], price, decision['initial_soc'], module.Battery())
                starting = independent_greedy(initial['grid'], net, price, decision['initial_soc'])
                policy_metrics['initial_objective_reproduction_error_yuan'] = max(policy_metrics['initial_objective_reproduction_error_yuan'], abs(starting['objective'] - solver['initial_objective']))
                saa = importlib.import_module('q2_policy_saa')
                _, _, details = saa.greedy_saa_objective(q, net, price, initial=decision['initial_soc'], battery=module.Battery())
                for field in ['charge', 'discharge', 'emergency', 'soc']:
                    policy_metrics['scenario_greedy_action_error_kwh'] = max(policy_metrics['scenario_greedy_action_error_kwh'], max_error(details[field], independent[field]))
                statuses[str(solver['status'])] = statuses.get(str(solver['status']), 0) + 1
                policy_days += 1
            elif config.get('scenario_count', 0):
                solver = decision['solver']
                assert solver['recourse_implementable'] is False
                assert abs(solver['objective'] - solver['planned_cost'] - solver['expected_emergency_cost']) < 1e-6
                assert solver['lp_lower_bound'] is None or solver['lp_lower_bound'] <= solver['objective'] + 1e-6
                assert abs(math.fsum(block.original_fee) - solver['planned_cost']) < 1e-6
                assert 1 <= solver['scenario_count'] <= config['scenario_count']
                scenario_days += 1
        assert policy_metrics['actual_greedy_action_error_kwh'] < 1e-6
        if policy_days:
            assert policy_metrics['final_objective_error_yuan'] < 1e-6
            assert policy_metrics['scenario_greedy_action_error_kwh'] < 1e-6
            assert policy_metrics['improvement_accounting_error_yuan'] < 1e-6
            result[name] = {'days': policy_days, 'metrics': policy_metrics, 'solver_status_counts': statuses,
                            'best_found_not_worse_than_recorded_initial_all_days': True,
                            'iteration_limit_all_days': 50,
                            'limit': 'Final best-found objectives and forward policy checked; per-evaluation objective history was not saved, and no global optimum is certified.'}
        if scenario_days:
            result[name] = {'days': scenario_days, 'actual_greedy_action_max_error_kwh': policy_metrics['actual_greedy_action_error_kwh'],
                            'shared_plan_fee_and_proxy_objective_reconciliation': True,
                            'lp_bound_not_above_saved_proxy_objective': True,
                            'anticipative_scenario_recourse_disclosed_all_days': True,
                            'limit': 'Actual trajectories independently verified. Scenario recourse is an optimistic planning proxy; per-scenario latent trajectories are not in the saved annual trace.'}
    if (run / 'shadow_daily_scores.csv').exists():
        shadow = pd.read_csv(run / 'shadow_daily_scores.csv', parse_dates=['available_at'])
        assert not shadow[['strategy', 'date']].duplicated().any()
        for _, group in shadow.groupby('strategy'):
            group = group.sort_values('date')
            assert abs(group.start_soc.iloc[0] - 6000) < 1e-7
            assert max_error(group.start_soc.iloc[1:], group.end_soc.iloc[:-1]) < 1e-7
            assert group.start_soc.between(1200 - 1e-6, 10800 + 1e-6).all()
            assert group.end_soc.between(1200 - 1e-6, 10800 + 1e-6).all()
            expected_available = pd.to_datetime(group.date) + pd.Timedelta(days=1)
            assert np.array_equal(group.available_at.to_numpy(), expected_available.to_numpy())
        decisions = all_decisions['adaptive_selector']
        frame = pd.read_csv(run / 'adaptive_selector/intervals.csv.gz')
        max_score_error, max_actual_replan_error = 0., 0.
        different_state_days = 0
        for i, decision in enumerate(decisions):
            cutoff = pd.Timestamp(decision['cutoff'])
            visible = shadow[shadow.available_at <= cutoff]
            last = sorted(visible.date.unique())[-14:]
            visible = visible[visible.date.isin(last)].copy()
            visible['adjusted'] = visible.cost_yuan - (visible.end_soc - visible.start_soc) * price.min() / .9
            scores = visible.groupby('strategy', sort=False).adjusted.mean().to_dict()
            assert set(scores) == set(decision['selection_scores_yuan'])
            max_score_error = max(max_score_error, max(abs(scores[k] - decision['selection_scores_yuan'][k]) for k in scores))
            assert last == decision['selection_dates']
            assert last[-1] == decision['selection_last_date'] < cutoff.strftime('%Y-%m-%d')
            assert min(scores, key=scores.get) == decision['active_variant']['name']
            packet, variant = packet_for_decision(module, days, cached, decision)
            plan = module.plan_packet(packet, variant, decision['initial_soc'], price, module.Battery())
            block = frame.iloc[i * 144:(i + 1) * 144]
            max_actual_replan_error = max(max_actual_replan_error, abs(math.fsum(block.original_fee) - plan['solver']['objective']))
            shadow_state = shadow[(shadow.date == decision['cutoff'][:10]) & (shadow.strategy == variant.name)].start_soc.iloc[0]
            different_state_days += abs(shadow_state - decision['initial_soc']) > 1e-7
        assert max_score_error < 1e-6 and max_actual_replan_error < 1e-6
        adaptive_spec = importlib.util.spec_from_file_location('q2_adaptive_review', run / 'source_snapshot/q2_adaptive.py')
        adaptive = importlib.util.module_from_spec(adaptive_spec)
        adaptive_spec.loader.exec_module(adaptive)
        perturb = {}
        for cutoff in ['2025-02-01', '2025-07-01', '2025-12-01']:
            changed = shadow.copy()
            changed.loc[changed.available_at > pd.Timestamp(cutoff), 'cost_yuan'] *= 1000
            a = adaptive.select_past_policy(shadow.to_dict('records'), cutoff, price, .9)
            b = adaptive.select_past_policy(changed.to_dict('records'), cutoff, price, .9)
            assert a == b
            perturb[cutoff] = {'selection_and_scores_unchanged': True, 'chosen': a[0]}
        result['adaptive_selector'] = {'days': len(decisions), 'shadow_rows': len(shadow),
             'max_past_score_error_yuan': max_score_error, 'max_actual_state_replan_objective_error_yuan': max_actual_replan_error,
             'actual_initial_different_from_selected_shadow_days': int(different_state_days),
             'selection_before_current_day_all_days': True, 'future_shadow_cost_perturbation': perturb,
             'limit': 'Shadow scores use each candidate own state path and a proxy energy credit; this is not an exact common-state counterfactual cost comparison.'}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    run = ROOT / args.run
    provenance = json.loads((run / 'provenance.json').read_text())
    source_checks = {}
    for name, expected in provenance['files'].items():
        actual = run / 'source_snapshot' / Path(name).name if name.startswith('src/') else ROOT / name
        source_checks[name] = hashlib.sha256(actual.read_bytes()).hexdigest() == expected
    assert all(source_checks.values())
    actuals = pd.read_csv(ROOT / 'data/processed/2026C/actuals.csv', parse_dates=['interval_start', 'interval_end', 'available_at'])
    price = pd.read_csv(ROOT / 'data/processed/2026C/q1.csv').price.to_numpy()
    module = load_snapshot(run)
    if (run / 'forecast_cache.npz').exists():
        saved = np.load(run / 'forecast_cache.npz', allow_pickle=False)
        days = saved['days'].tolist()
        cached = {key: saved[key] for key in saved.files if key != 'days'}
    else:
        last_day = provenance.get('actual_end', actuals.date.max())
        days, cached, _ = module.prepare_forecasts(actuals[actuals.date <= last_day].copy(), price)
    truth = actuals[actuals.date.isin(days)].sort_values(['date', 'interval_index'])
    load = truth.load_kwh.to_numpy().reshape(len(days), 144)
    pv = truth.pv_kwh.to_numpy().reshape(len(days), 144)
    cache_checks = {}
    for target, values in [('load', load), ('pv', pv)]:
        cache_checks[target + '_error_identity'] = max_error(cached[target + '_error'][1:], values[1:] - cached[target][1:])
        expected_bias = np.full_like(values, np.nan)
        for day in range(1, len(days)):
            previous = cached[target + '_error'][max(1, day - 3):day]
            correction = previous.mean(axis=0) if len(previous) else np.zeros(144)
            expected_bias[day] = np.maximum(cached[target][day] + correction, 0)
        cache_checks['bias_' + target + '_prefix_identity'] = max_error(cached['bias_' + target], expected_bias)
        cache_checks['bias_' + target + '_error_identity'] = max_error(cached['bias_' + target + '_error'][1:], values[1:] - expected_bias[1:])
    old_forecasts = pd.read_csv(ROOT / 'results/backtests/full-evaluation-v1/forecast_evaluation.csv.gz',
                                usecols=['date', 'forecast_group', 'interval_index', 'predicted_load_kwh', 'predicted_pv_kwh', 'margin_kwh'])
    old_forecasts = old_forecasts[(old_forecasts.forecast_group == 'fixed_historical_pv') & old_forecasts.date.isin(days)].sort_values(['date', 'interval_index'])
    old_days = old_forecasts.date.unique()
    indices = [days.index(day) for day in old_days]
    for stored_key, old_key in [('load', 'predicted_load_kwh'), ('pv', 'predicted_pv_kwh'), ('legacy_margin', 'margin_kwh')]:
        cache_checks[stored_key + '_v1_cache_agreement'] = max_error(cached[stored_key][indices].ravel(), old_forecasts[old_key])
    assert all(value < 1e-7 for value in cache_checks.values()), cache_checks
    summary = json.loads((run / 'summary.json').read_text())
    results, all_decisions = {}, {}
    for name in summary:
        start, end = summary[name]['start_date'], summary[name]['end_date']
        relevant = actuals[(actuals.date >= start) & (actuals.date <= end)].reset_index(drop=True)
        results[name], all_decisions[name] = check_trace(run / name, relevant, price, cached, days)
    reference_names = {'legacy_point_reference': 'q2_point', 'legacy_margin_reference': 'q2_margin', 'legacy_margin_greedy': 'q2_margin_greedy'}
    baseline_checks = {}
    old_summary = json.loads((ROOT / 'results/backtests/full-evaluation-v1/summary.json').read_text())
    for name, old_name in reference_names.items():
        if name in summary:
            baseline_checks[name] = abs(summary[name]['total_fee'] - old_summary[old_name]['total_fee'])
    assert all(v < 1e-6 for v in baseline_checks.values())
    calibration = json.loads((run / 'january_calibration.json').read_text()) if (run / 'january_calibration.json').exists() else []
    selection = json.loads((run / 'selected_parameters.json').read_text()) if (run / 'selected_parameters.json').exists() else None
    score_errors = []
    for item in calibration:
        recomputed = item['cost_yuan'] - (item['terminal_soc'] - 6000) * price[-1] / .9
        score_errors.append(abs(recomputed - item['selection_score_yuan']))
    assert max(score_errors, default=0) < 1e-7
    if selection:
        assert pd.Timestamp(selection['end']) + pd.Timedelta(days=1) <= pd.Timestamp(selection['cutoff'])
    for chosen in selection['selected_variants'] if selection else []:
        family = [item for item in calibration if item['family'] == chosen['name']]
        if family:
            best = min(family, key=lambda item: item['selection_score_yuan'])['variant']
            assert {k: v for k, v in best.items() if k != 'name'} == {k: v for k, v in chosen.items() if k != 'name'}
    if selection:
        family_scores = {v['name']: min(r['selection_score_yuan'] for r in calibration if r['family'] == v['name'])
                         for v in selection['selected_variants']}
        assert min(family_scores, key=family_scores.get) == selection['deployment_family']
    prefix = actuals[actuals.date <= '2025-02-02'].copy()
    altered = prefix.copy(deep=True)
    cutoff = pd.Timestamp('2025-02-01')
    altered.loc[altered.available_at > cutoff, ['load_kw', 'pv_kw', 'load_kwh', 'pv_kwh', 'price_variable']] *= 3
    test_days, original_cache, metadata = module.prepare_forecasts(prefix, price)
    changed_days, changed_cache, changed_metadata = module.prepare_forecasts(altered, price)
    test_index = test_days.index('2025-02-01')
    causal = {}
    for name in ['load', 'pv', 'legacy_margin', 'bias_load', 'bias_pv']:
        causal[name + '_future_perturbation'] = max_error(original_cache[name][1:test_index + 1], changed_cache[name][1:test_index + 1])
        causal[name + '_saved_prefix_agreement'] = max_error(original_cache[name][1:test_index + 1], cached[name][1:test_index + 1])
    warnings = []
    original_legacy = [json.loads(line) for line in (ROOT / 'results/backtests/full-evaluation-v1/q2_margin/decisions.jsonl').read_text().splitlines()]
    original_quantiles = {d['cutoff'][:10]: d['margin_quantile'] for d in original_legacy}
    packet_checks = {}
    for name, decisions in all_decisions.items():
        configuration = decisions[0].get('config', decisions[0].get('active_variant', summary[name]['strategy']))
        allowed = set(module.Variant.__dataclass_fields__)
        if not set(configuration).issubset(allowed):
            warnings.append(f'{name}: future-plan test needs adapter for configuration fields {set(configuration) - allowed}')
            continue
        variant = module.Variant(**configuration)
        first = module.visible_packet(test_days, original_cache, metadata, test_index, variant)
        second = module.visible_packet(changed_days, changed_cache, changed_metadata, test_index, variant)
        for key in ['load', 'pv', 'margin', 'residual_days']:
            causal[name + '_' + key + '_packet_perturbation'] = max_error(first[key], second[key])
        plan1 = module.plan_packet(first, variant, 6000., price, module.Battery())
        plan2 = module.plan_packet(second, variant, 6000., price, module.Battery())
        causal[name + '_plan_perturbation'] = max_error(plan1['grid'], plan2['grid'])
        legacy_mismatch = 0
        for decision in decisions:
            configuration = decision.get('config', decision.get('active_variant', summary[name]['strategy']))
            variant = module.Variant(**configuration)
            index = days.index(decision['cutoff'][:10])
            prefix_key = 'bias_' if configuration.get('bias_days') else ''
            residual = cached[prefix_key + 'load_error'][max(1, index - 14):index] - cached[prefix_key + 'pv_error'][max(1, index - 14):index]
            if configuration.get('margin') == 'hourly':
                independent_margin = np.array([max(0, np.quantile(residual[:, h * 6:h * 6 + 6].ravel(), configuration['quantile'])) if configuration['quantile'] else 0 for h in range(24)]).repeat(6)
                fake_metadata = [None] * len(days)
                fake_metadata[index] = decision
                packet = module.visible_packet(days, cached, fake_metadata, index, variant)
                packet_checks[name] = max(packet_checks.get(name, 0), max_error(independent_margin, packet['margin']))
            if configuration.get('margin') == 'legacy' and abs(decision['margin_quantile'] - original_quantiles[decision['cutoff'][:10]]) > 1e-9:
                legacy_mismatch += 1
        if legacy_mismatch:
            warnings.append(f'{name}: {legacy_mismatch} margin_quantile metadata values differ from the dynamically selected v1 quantile; numerical legacy margins agree with v1')
    assert all(v < 1e-7 for v in causal.values())
    assert all(v < 1e-7 for v in packet_checks.values())
    specialized = check_specialized(run, module, cached, days, metadata, actuals, price, all_decisions)
    best_name = min(results, key=lambda name: results[name]['cost_yuan'])
    report = {'run_id': run.name, 'status': 'PASS_WITH_METADATA_LIMITATIONS' if warnings else 'PASS',
              'source_snapshot_and_input_hashes': source_checks, 'trajectory_checks': results,
              'cache_checks': cache_checks, 'risk_packet_independent_checks': packet_checks,
              'v1_baseline_cost_differences': baseline_checks,
              'calibration_max_score_error_yuan': max(score_errors, default=0),
              'january_deployment_family': selection['deployment_family'] if selection else None,
              'retrospective_cheapest_saved_candidate': best_name,
              'selection_boundary': 'The retrospective cheapest candidate is not automatically the January-selected deployment family.',
              'specialized_checks': specialized,
              'future_perturbation_and_prefix_checks': causal, 'warnings': warnings,
              'scope': 'All saved trajectories and cache algebra; all hourly margin packets; selected January scores; Feb1 future-perturbation forecast/margin/plans. Does not certify unseen-data generalization or all solver paths.'}
    (run / 'independent_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'run_id': run.name, 'status': report['status'], 'strategies': len(results),
                      'total_intervals': sum(x['intervals'] for x in results.values()),
                      'max_cache_error': max(cache_checks.values()), 'max_future_plan_error': max(causal.values()),
                      'warnings': warnings}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
