import ast
import csv
import hashlib
import json
import math
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT / 'results/c2026'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def error_metrics(rows, key):
    errors = [float(r[key]) - float(r['actual_pv_kwh']) for r in rows]
    return {'mae_kwh': math.fsum(map(abs, errors)) / len(errors),
            'rmse_kwh': math.sqrt(math.fsum(e * e for e in errors) / len(errors)),
            'max_absolute_kwh': max(map(abs, errors))}


def main():
    summaries = json.loads((RESULTS / 'summaries.json').read_text())
    analysis = json.loads((RESULTS / 'analysis_results.json').read_text())
    groups = defaultdict(list)
    with (RESULTS / 'annual_slots.csv').open() as f:
        for row in csv.DictReader(f):
            if row['date'] >= '2025-02-01':
                groups[row['case']].append(row)
    annual = {}
    for name, rows in groups.items():
        numbers = [{k: float(v) for k, v in r.items()
                    if k not in ('case', 'date', 'reference_soc') and v} for r in rows]
        costs = [r['price'] * (r['adjusted'] + .5 * abs(r['adjusted'] - r['plan'])
                             + 5 * r['emergency']) for r in numbers]
        balance = [abs(r['adjusted'] + r['pv'] + r['discharge'] + r['emergency']
                       - r['load'] - r['charge'] - r['surplus']) for r in numbers]
        state = [abs(r['soc_end'] - r['soc_start'] - .9 * r['charge']
                     + r['discharge'] / .9) for r in numbers]
        expected = summaries[name].get('cost_total', summaries[name].get('total_fee'))
        result = dict(slots=len(rows), dates=len({r['date'] for r in rows}),
                      cost_yuan=math.fsum(costs), cost_difference_yuan=math.fsum(costs) - expected,
                      max_balance_residual_kwh=max(balance), max_state_residual_kwh=max(state),
                      max_continuity_residual_kwh=max(abs(a['soc_end'] - b['soc_start'])
                                                     for a, b in zip(numbers, numbers[1:])),
                      minimum_soc_kwh=min(min(r['soc_start'], r['soc_end']) for r in numbers),
                      maximum_soc_kwh=max(max(r['soc_start'], r['soc_end']) for r in numbers),
                      maximum_charge_kwh=max(r['charge'] for r in numbers),
                      maximum_discharge_kwh=max(r['discharge'] for r in numbers),
                      simultaneous_slots=sum(min(r['charge'], r['discharge']) > 1e-7 for r in numbers))
        assert result['slots'] == 48096 and result['dates'] == 334
        assert abs(result['cost_difference_yuan']) < 1e-6
        assert max(balance + state) < 1e-7
        assert result['max_continuity_residual_kwh'] < 1e-7
        assert result['minimum_soc_kwh'] >= 1200 - 1e-7
        assert result['maximum_soc_kwh'] <= 10800 + 1e-7
        assert max(result['maximum_charge_kwh'], result['maximum_discharge_kwh']) <= 5000 / 6 + 1e-7
        assert result['simultaneous_slots'] == 0
        annual[name] = result
    example = analysis['q3']['forecast_example']['rows']
    forecasts = {key: error_metrics(example, key) for key in ('issued_pv_kwh', 'fused_pv_kwh')}
    forecasts['annual_pooled_rmse_kwh'] = {}
    for method in ('发布预报', '融合修正预报'):
        records = [r for r in analysis['q3']['forecast_metrics']['rows'] if r['method'] == method]
        forecasts['annual_pooled_rmse_kwh'][method] = math.sqrt(
            math.fsum(float(r['rmse_kwh']) ** 2 * int(r['intervals']) for r in records)
            / sum(int(r['intervals']) for r in records))
    with (ROOT / 'data/processed/q1_inputs.csv').open() as f:
        prices = [float(r['price']) for r in csv.DictReader(f)]
    terminal = {'last_price': prices[-1], 'kappa': min(prices) / .9,
                'last_objective_slope_below_6000': 5 * .9 * prices[-1] - min(prices) / .9,
                'last_objective_slope_above_6000': 5 * .9 * prices[-1],
                'last_threshold_kwh': 1200}
    assert terminal['last_objective_slope_below_6000'] > 0
    with zipfile.ZipFile(HERE / 'online-source.zip') as z:
        appendix = z.read('sections/13_appendix.tex').decode()
        sources = dict(re.findall(r'\\begin\{lstlisting\}\[language=Python,caption=\{[^\n]*?'
                                 r'\\nolinkurl\{([^}]+)\}[^\n]*\]\n(.*?)\\end\{lstlisting\}', appendix, re.S))
        code = {}
        for name, text in sources.items():
            ast.parse(text)
            code[name] = {'syntax_parsed': True, 'lines': len(text.splitlines()),
                          'matches_local_source': text.strip() == (ROOT / 'src' / name).read_text().strip()}
        body = '\n'.join(z.read(n).decode() for n in z.namelist()
                         if n.startswith('sections/') and n.endswith('.tex') and '13_appendix' not in n)
        labels = set(re.findall(r'\\label\{([^}]+)\}', body))
        refs = set(re.findall(r'\\(?:ref|eqref)\{([^}]+)\}', body))
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    books = {}
    for path in sorted((RESULTS / 'submission').glob('*.xlsx')):
        with zipfile.ZipFile(path) as z:
            shared = []
            if 'xl/sharedStrings.xml' in z.namelist():
                shared = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
            def value(c):
                if c is None:
                    return None
                if c.get('t') == 'inlineStr':
                    return ''.join(c.find('s:is', ns).itertext())
                v = c.find('s:v', ns)
                return (shared[int(v.text)] if c.get('t') == 's' else v.text) if v is not None else None
            names = [s.attrib['name'] for s in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets', ns)]
            sheets = {}
            for index, name in enumerate(names, 1):
                xml = ET.fromstring(z.read(f'xl/worksheets/sheet{index}.xml'))
                rows = xml.findall('s:sheetData/s:row', ns)
                sheets[name] = {'rows': len(rows), 'sample_cells': {c.get('r'): value(c) for row in rows[:2] for c in list(row)[:3]}}
            books[path.name] = {'sha256': sha(path), 'sheets': sheets}
    package = RESULTS / 'submission/支撑材料_待补AI详情.zip'
    with zipfile.ZipFile(package) as z:
        package_info = {'size_bytes': package.stat().st_size, 'sha256': sha(package),
                        'entries': z.namelist(), 'ai_named_entries': [n for n in z.namelist() if 'AI' in n]}
    report = {'snapshot_pdf_sha256': sha(HERE / 'online-paper.pdf'), 'annual': annual,
              'forecast_errors': forecasts, 'q2_terminal': terminal, 'appendix_code': code,
              'undefined_refs': sorted(refs - labels),
              'unreferenced_figures_tables': sorted(x for x in labels - refs if x.startswith(('fig:', 'tab:'))),
              'local_workbooks': books, 'local_package': package_info,
              'scope': 'Read-only current saved-output audit; no complete model rerun.'}
    (HERE / 'audit_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'annual_checks': 'passed', 'appendix_syntax': len(code),
                      'q2_last_threshold_kwh': 1200, 'report': str(HERE / 'audit_results.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
