from pathlib import Path
import csv
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results/c2026'
CASES = ('q2', 'q3', 'q4_2', 'q4_3')


def read_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def consolidate():
    for kind in ('slots', 'daily'):
        tables = [(case, *read_rows(RESULTS / 'annual' / f'{case}_{kind}.csv')) for case in CASES]
        columns = list(dict.fromkeys(column for _, fields, _ in tables for column in fields))
        with (RESULTS / f'annual_{kind}.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['case', *columns])
            writer.writeheader()
            for case, _, records in tables:
                writer.writerows(dict(case=case, **row) for row in records)
    summaries = {'q1': json.loads((RESULTS / 'q1/summary.json').read_text())}
    summaries.update({case: json.loads((RESULTS / 'annual' / f'{case}_summary.json').read_text()) for case in CASES})
    write_json(RESULTS / 'summaries.json', summaries)
    analysis = {'q1': {}, 'q3': {}}
    for key, directory in [('q1', RESULTS / 'q1'), ('q3', RESULTS / 'evidence/q3')]:
        for path in sorted(directory.glob('*.csv')):
            if path.name == 'schedule.csv':
                continue
            fields, records = read_rows(path)
            analysis[key][path.stem] = {'columns': fields, 'rows': records}
    analysis['q3']['evidence'] = json.loads((RESULTS / 'evidence/q3/evidence.json').read_text())
    analysis['verification'] = {
        'excel': json.loads((RESULTS / 'verification/excel_audit.json').read_text()),
        'previous_model_checks': json.loads((RESULTS / 'verification/model_checks.json').read_text()),
    }
    current = RESULTS / 'verification/appendix_consolidation.json'
    if current.exists():
        analysis['verification']['consolidation'] = json.loads(current.read_text())
    write_json(RESULTS / 'analysis_results.json', analysis)


def entries():
    return [
        ('results/c2026/submission/result1.xlsx', '问题一：购电策略与储能运行结果'),
        ('results/c2026/submission/result2.xlsx', '问题二：购电、充放电与紧急购电结果'),
        ('results/c2026/submission/result3.xlsx', '问题三：购电调整与储能运行结果'),
        ('results/c2026/submission/result4-2.xlsx', '波动电价下问题二的运行结果'),
        ('results/c2026/submission/result4-3.xlsx', '波动电价下问题三的运行结果'),
        ('data/processed/actuals_power.csv', '全年负载、光伏与电价记录'),
        ('data/processed/actuals_energy.csv', '十分钟电量及数据可用时间'),
        ('data/processed/pv_forecasts.csv', '分时发布的光伏预报'),
        ('data/processed/q1_inputs.csv', '问题一输入与固定分时电价'),
        ('results/c2026/q1/schedule.csv', '问题一逐时段购电与储能轨迹'),
        ('results/c2026/annual_slots.csv', '问题二至四全年逐时段运行轨迹'),
        ('results/c2026/annual_daily.csv', '问题二至四逐日费用与电量汇总'),
        ('data/processed/annual_inputs.npz', '求解所需全年输入数组'),
        ('configs/q3_current.json', '问题三最终策略参数'),
        ('results/c2026/summaries.json', '四问费用、策略参数与结果摘要'),
        ('results/c2026/analysis_results.json', '敏感性、预报价值与计算核验结果'),
        ('src/problem1.py', '问题一：线性规划求解与检验'),
        ('src/problem2.py', '问题二：日前预测与购电策略'),
        ('src/problem3.py', '问题三：预报融合与分段更新'),
        ('src/problem4.py', '问题四：电价预测与购电策略'),
        ('src/microgrid.py', '公共模型、储能控制与结果导出'),
        ('configs/requirements.txt', 'Python依赖及版本'),
        ('README.md', '运行方法与完整文件清单'),
    ]


def build():
    consolidate()
    files = entries()
    readme = (ROOT / 'docs/REPRODUCE.md').read_text()
    readme += '\n## 文件清单\n\n| 文件 | 功能 |\n|---|---|\n'
    readme += ''.join(f'| {name} | {description} |\n' for name, description in files)
    destination = RESULTS / 'submission/支撑材料_待补AI详情.zip'
    temporary = destination.with_suffix('.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, _ in files:
            info = zipfile.ZipInfo(name, (2026, 9, 12, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            archive.writestr(info, readme if name == 'README.md' else (ROOT / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    temporary.replace(destination)
    previous = (ROOT / 'paper/overleaf/sections/13_appendix.tex').read_text()
    settings = previous[previous.index('\\renewcommand{\\lstlistingname}'):previous.index('\\needspace')]
    appendix = r'''\clearpage
\begingroup
\section*{附录 A\quad 文件列表}
\begingroup\small\setlength{\tabcolsep}{8pt}\renewcommand{\arraystretch}{1.12}
\begin{longtable}{@{}p{0.39\textwidth}p{\dimexpr0.61\textwidth-2\tabcolsep\relax}@{}}
\toprule \textbf{文件名} & \textbf{功能描述} \\ \midrule\endfirsthead
\toprule \textbf{文件名} & \textbf{功能描述} \\ \midrule\endhead
\bottomrule\endfoot
'''
    for index, (name, description) in enumerate(files):
        if index and Path(name).suffix != Path(files[index - 1][0]).suffix:
            appendix += '\\addlinespace[4pt]\n'
        appendix += '\\nolinkurl{' + Path(name).name + '} & ' + description + ' \\\\\n'
    appendix += '\\end{longtable}\\endgroup\n\\clearpage\n\\section*{附录 B\\quad 代码}\n' + settings
    for name, description in files:
        if not name.endswith('.py'):
            continue
        appendix += '\\needspace{6\\baselineskip}\n\\begin{lstlisting}[language=Python,caption={' + description + '（\\nolinkurl{' + Path(name).name + '}）}]\n'
        appendix += (ROOT / name).read_text().rstrip() + '\n\\end{lstlisting}\n'
    appendix += '\\endgroup\n'
    (ROOT / 'paper/overleaf/sections/13_appendix.tex').write_text(appendix)
    print(json.dumps({'files': len(files), 'bytes': destination.stat().st_size}, ensure_ascii=False))


if __name__ == '__main__':
    build()
