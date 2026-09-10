import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = {
    'q2_margin': '第二问：校准裕量方案',
    'q3_adjust_A': '第三问：允许调整，A口径',
    'q4_2_margin': '第四问对应第二问：因果价格方案',
    'q4_3_adjust_A': '第四问对应第三问：调整A口径',
}
DATES = ['2025-03-20', '2025-06-21', '2025-09-23', '2025-12-21']
THRESHOLD = 1e-7


def stamp(minute):
    return f'{int(minute) // 60:02d}:{int(minute) % 60:02d}'


def span(start, end, latex=False):
    return stamp(start) + ('--' if latex else '-') + stamp(end)


def number(value):
    return f'{value:.6f}'


def read_designated(run, strategy):
    directory = run / strategy
    summary = json.loads((directory / 'summary.json').read_text())
    first = pd.Timestamp(summary['start_date'])
    keep = {0}
    for date in DATES:
        offset = (pd.Timestamp(date) - first).days * 144
        keep.update(range(offset + 1, offset + 145))
    columns = ['date', 'interval_index', 'interval_start', 'interval_end', 'planned_grid',
               'contract_grid', 'emergency', 'price', 'charge', 'discharge', 'soc_start',
               'soc_end', 'original_fee', 'increase_fee', 'decrease_penalty', 'refund',
               'emergency_fee', 'total_fee', 'contract_increase', 'contract_decrease']
    frame = pd.read_csv(directory / 'intervals.csv.gz', usecols=columns,
                        skiprows=lambda line: line not in keep)
    assert len(frame) == 576 and sorted(frame.date.unique()) == DATES
    return frame


def amounts(rows):
    fields = {'planned_grid_kwh': 'planned_grid', 'final_contract_kwh': 'contract_grid',
              'emergency_kwh': 'emergency', 'total_fee_yuan': 'total_fee',
              'original_fee_yuan': 'original_fee', 'increase_fee_yuan': 'increase_fee',
              'decrease_penalty_yuan': 'decrease_penalty', 'refund_yuan': 'refund',
              'emergency_fee_yuan': 'emergency_fee'}
    result = {key: math.fsum(rows[column]) for key, column in fields.items()}
    result['purchased_kwh'] = result['final_contract_kwh'] + result['emergency_kwh']
    independent_cost = math.fsum(rows.planned_grid * rows.price +
        1.5 * rows.contract_increase * rows.price + .5 * rows.contract_decrease * rows.price +
        5 * rows.emergency * rows.price)
    assert abs(independent_cost - result['total_fee_yuan']) < 1e-7
    assert result['refund_yuan'] == 0
    return result


def emergency_events(rows, strategy, date):
    events = []
    start = None
    for index in range(145):
        active = index < 144 and rows.emergency.iloc[index] > THRESHOLD
        if active and start is None:
            start = index
        if not active and start is not None:
            events.append({'strategy': strategy, 'date': date, 'event_index': len(events) + 1,
                'status': 'event', 'start_minute': start * 10, 'end_minute': index * 10,
                'interval_start': rows.interval_start.iloc[start],
                'interval_end': rows.interval_end.iloc[index - 1],
                'emergency_kwh': math.fsum(rows.emergency.iloc[start:index]),
                'interval_count': index - start, 'positive_threshold_kwh': THRESHOLD})
            assert (rows.emergency.iloc[start:index] > THRESHOLD).all()
            start = None
    if not events:
        events.append({'strategy': strategy, 'date': date, 'event_index': 0,
            'status': 'no_emergency', 'start_minute': None, 'end_minute': None,
            'interval_start': None, 'interval_end': None, 'emergency_kwh': 0.,
            'interval_count': 0, 'positive_threshold_kwh': THRESHOLD})
    assert abs(math.fsum(e['emergency_kwh'] for e in events) - math.fsum(rows.emergency)) < 1e-7
    return events


def render_group(label, date, singles, total, blocks, events):
    lines = [rf'\subsection{{{label}，{date}}}', r'\begingroup\small',
             r'\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.08}',
             r'\setlength{\LTpre}{4pt}\setlength{\LTpost}{4pt}',
             r'\noindent 购电量均为最终普通合同量加紧急购电量，包含已付费但未利用的合同电量；不等同于实际利用电量。时间使用内部当日标准网格，所有电量单位为kWh，费用单位为元。',
             r'\begin{center}\textbf{表1\quad 指定时段购电量与全天购电量、购电费}\par\smallskip',
             r'\begin{tabular}{lr lr lr}\toprule',
             r'时间段 & 购电量 & 时间段 & 购电量 & 时间段 & 购电量\\\midrule']
    for offset in [0, 3]:
        cells = []
        for row in singles[offset:offset + 3]:
            cells.extend([span(row['start_minute'], row['end_minute'], True), number(row['purchased_kwh'])])
        lines.append(' & '.join(cells) + r'\\')
    lines += [r'\midrule',
              rf'\multicolumn{{2}}{{l}}{{全天购电量}} & {number(total["purchased_kwh"])} & \multicolumn{{2}}{{l}}{{全天购电费}} & {number(total["total_fee_yuan"])}\\',
              r'\bottomrule\end{tabular}\end{center}',
              rf'\noindent 0点原计划量：{number(total["planned_grid_kwh"])}；最终普通合同量：{number(total["final_contract_kwh"])}；紧急量：{number(total["emergency_kwh"])}。',
              rf'全天费用含原计划费{number(total["original_fee_yuan"])}、增购费{number(total["increase_fee_yuan"])}、减购违约费{number(total["decrease_penalty_yuan"])}、退款扣减{number(total["refund_yuan"])}及紧急费{number(total["emergency_fee_yuan"])}。',
              r'\begin{center}\textbf{表2\quad 指定时段充放电量与0点、24点储电量}\par\smallskip',
              r'\begin{tabular}{lrr lrr}\toprule',
              r'时间段 & 充电量 & 放电量 & 时间段 & 充电量 & 放电量\\\midrule']
    for offset in [0, 2, 4]:
        cells = []
        for block in blocks[offset:offset + 2]:
            cells.extend([span(block['start_minute'], block['end_minute'], True),
                          number(block['charge_kwh']), number(block['discharge_kwh'])])
        lines.append(' & '.join(cells) + r'\\')
    lines += [r'\midrule',
              rf'\multicolumn{{2}}{{l}}{{0:00储电量}} & {number(blocks[0]["day_initial_soc_kwh"])} & \multicolumn{{2}}{{l}}{{24:00储电量}} & {number(blocks[0]["day_terminal_soc_kwh"])}\\',
              r'\bottomrule\end{tabular}\end{center}',
              r'\noindent 充电、放电分别为交流母线侧输入、输出；储电量为电池内部状态。同一四小时段可分别发生充电和放电，逐10分钟区间保持互斥。',
              r'\begin{center}\textbf{表3\quad 当日全部紧急购电事件}\end{center}',
              r'\begin{longtable}{llr}\toprule 日期 & 紧急购电时间段 & 紧急购电量\\\midrule\endfirsthead',
              r'\toprule 日期 & 紧急购电时间段 & 紧急购电量\\\midrule\endhead',
              r'\bottomrule\endfoot']
    for i, event in enumerate(events):
        date_cell = date if i == 0 else ''
        time_cell = (span(event['start_minute'], event['end_minute'], True)
                     if event['status'] == 'event' else '无紧急购电事件')
        lines.append(f'{date_cell} & {time_cell} & {number(event["emergency_kwh"])}' + r'\\')
    lines += [rf'\midrule\multicolumn{{2}}{{l}}{{当日事件电量合计}} & {number(math.fsum(e["emergency_kwh"] for e in events))}\\',
              r'\end{longtable}',
              r'\noindent 事件阈值为$10^{-7}$kWh；连续超阈值区间合并，不跨零值、不跨日。',
              r'\endgroup']
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='results/backtests/full-evaluation-v1')
    args = parser.parse_args()
    run = ROOT / args.run
    table1, table2, table3 = [], [], []
    tex = [r'\clearpage', r'\section{指定日期的分时购电、储能与紧急事件}',
           r'\label{sec:designated_details}']
    totals = []
    for strategy, label in STRATEGIES.items():
        selected = read_designated(run, strategy)
        for date in DATES:
            rows = selected.loc[selected.date == date].reset_index(drop=True)
            assert rows.interval_index.tolist() == list(range(144))
            actual_start = pd.to_datetime(rows.interval_start)
            actual_end = pd.to_datetime(rows.interval_end)
            expected = pd.Timestamp(date) + pd.to_timedelta(np.arange(144) * 10, unit='m')
            assert np.array_equal(actual_start.to_numpy(), expected.to_numpy())
            assert ((actual_end - actual_start).dt.total_seconds() == 600).all()
            assert np.max(abs(rows.soc_start.iloc[1:].to_numpy() - rows.soc_end.iloc[:-1].to_numpy())) < 1e-7
            common = {'strategy': strategy, 'date': date}
            singles = []
            for t in [60, 72, 84, 96, 108, 120]:
                singles.append(dict(common, record_type='selected_interval', interval_index=t,
                                    start_minute=t * 10, end_minute=(t + 1) * 10,
                                    **amounts(rows.iloc[t:t + 1])))
            total = dict(common, record_type='daily_total', interval_index=None,
                         start_minute=0, end_minute=1440, **amounts(rows))
            table1.extend(singles + [total])
            blocks = []
            for block in range(6):
                chunk = rows.iloc[block * 24:(block + 1) * 24]
                blocks.append(dict(common, block_index=block, start_minute=block * 240,
                    end_minute=(block + 1) * 240, charge_kwh=math.fsum(chunk.charge),
                    discharge_kwh=math.fsum(chunk.discharge),
                    block_initial_soc_kwh=float(chunk.soc_start.iloc[0]),
                    block_terminal_soc_kwh=float(chunk.soc_end.iloc[-1]),
                    day_initial_soc_kwh=float(rows.soc_start.iloc[0]),
                    day_terminal_soc_kwh=float(rows.soc_end.iloc[-1])))
            assert abs(math.fsum(b['charge_kwh'] for b in blocks) - math.fsum(rows.charge)) < 1e-7
            assert abs(math.fsum(b['discharge_kwh'] for b in blocks) - math.fsum(rows.discharge)) < 1e-7
            table2.extend(blocks)
            events = emergency_events(rows, strategy, date)
            table3.extend(events)
            if totals:
                tex.append(r'\clearpage')
            tex.extend(render_group(label, date, singles, total, blocks, events))
            totals.append(dict(common, purchased_kwh=total['purchased_kwh'],
                               total_fee_yuan=total['total_fee_yuan'],
                               emergency_kwh=total['emergency_kwh'],
                               emergency_events=sum(e['status'] == 'event' for e in events)))
    destination = ROOT / 'results/evaluation'
    max_readback_error = 0.
    for name, records in [('designated_table1', table1), ('designated_table2', table2), ('designated_table3', table3)]:
        path = destination / f'{name}.csv'
        original = pd.DataFrame(records)
        original.to_csv(path, index=False)
        back = pd.read_csv(path)
        assert len(back) == len(records) and back.groupby(['strategy', 'date']).ngroups == 16
        for column in original.select_dtypes(include='number'):
            first = original[column].to_numpy(dtype=float)
            second = back[column].to_numpy(dtype=float)
            assert np.array_equal(np.isnan(first), np.isnan(second))
            finite = np.isfinite(first)
            max_readback_error = max(max_readback_error, float(np.max(abs(first[finite] - second[finite]))))
    assert max_readback_error < 1e-7
    assert len(table1) == 112 and len(table2) == 96
    fragment = ROOT / 'paper/analysis/designated_details.tex'
    fragment.write_text('\n'.join(tex) + '\n')
    assert fragment.read_text().count(r'\subsection{') == 16
    print(json.dumps({'groups': 16, 'source_intervals': 2304, 'table1_rows': len(table1),
                      'table2_rows': len(table2), 'table3_rows': len(table3),
                      'emergency_event_count': sum(t['emergency_events'] for t in totals),
                      'no_emergency_groups': sum(t['emergency_events'] == 0 for t in totals),
                      'daily_summaries': totals, 'max_csv_readback_error': max_readback_error,
                      'validation_tolerance': 1e-7}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
