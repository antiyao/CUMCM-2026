from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    expected = ['result1.xlsx', 'result2.xlsx', 'result3.xlsx', 'result4-2.xlsx', 'result4-3.xlsx']
    if any(not (ROOT/'results/submission'/name).exists() for name in expected):
        raise RuntimeError('Historical v1 packager is unavailable after removal of the obsolete Q2 workbook. Current results are in results/final_recommendation/.')
    patterns=['README.md','configs/*','src/*.py','src/*.mjs','tests/*.py',
              'context/PROBLEM_DECOMPOSITION.md','context/DATA_DICTIONARY.md','context/DATA_QUALITY.md',
              'context/ASSUMPTIONS.md','context/SETTLEMENT_SPEC.md','context/TEMPLATE_MAPPING.md',
              'context/BACKTEST_REPORT.md','context/Q1_REVIEW.md','context/ONLINE_REVIEW.md',
              'context/FIRST_ROUND_REPORT.md','context/DELIVERABLE_MATRIX.md',
              'context/FILE_RELOCATION_MANIFEST.csv',
              'data/templates/2026C/*.xlsx','data/processed/2026C/q1.csv',
              'data/processed/2026C/actuals.csv','data/processed/2026C/forecasts.csv',
              'results/submission/*.xlsx','results/q1/*.csv','results/q1/summary.json',
              'results/q1/export_validation.json','results/backtests/export_validation.json',
              'results/backtests/summarize.py','results/backtests/*mapping.csv',
              'results/backtests/full-evaluation-v1/*.json','results/backtests/full-evaluation-v1/*.csv',
              'results/backtests/full-evaluation-v1/*/daily.csv',
              'results/backtests/full-evaluation-v1/*/monthly.csv',
              'results/backtests/full-evaluation-v1/*/summary.json',
              'results/backtests/full-evaluation-v1/*/events.csv',
              'results/backtests/full-evaluation-v1/*/contract_event_ledger.csv',
              'results/backtests/full-evaluation-v1/source_snapshot/*.py',
              'results/audit/data*.json','results/audit/data_hashes.csv',
              'results/audit/online_review*.json','results/audit/online_review*.py',
              'results/evaluation/*','figures/FIGURE_PLAN.md','figures/q1/*.pdf','figures/q2/*.pdf',
              'paper/CLAIM_EVIDENCE_MAP.md','paper/analysis/*.tex','paper/analysis/AI工具使用详情.pdf']
    paths=sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file() and not p.is_symlink()})
    manifest=[]
    for path in paths:
        manifest.append(dict(path=path.relative_to(ROOT).as_posix(),size_bytes=path.stat().st_size,
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    out=ROOT/'paper/releases/2026C-first-round'
    out.mkdir(parents=True,exist_ok=True)
    archive=out/'support.zip'
    if archive.exists():
        raise RuntimeError('Existing support package retained; use a new release folder')
    note='''First-round reproducibility package; not a submission authorization.
All five workbooks retain TEMPLATE_TIME_LABEL_AMBIGUITY and require final human review.
Original official problem/data are not duplicated. Restore official attachments 1-4
under data/raw/2026C/ to rerun audit; processed exact inputs are included for solve/backtest.
Use Python 3.12 and configs/requirements-lock.txt in a virtual environment.
Excel export additionally needs the Codex bundled Node and @oai/artifact-tool runtime
described in README; that proprietary runtime is not redistributed in this ZIP.
The complete annual interval CSVs and previews remain in the local repository;
the five workbooks, source code, exact processed inputs, summaries and contract events
are included. Backtests regenerate all interval CSVs with the recorded configuration.
No repository secrets, .git, .venv, node_modules, teammate manuscript, or raw literature
are packaged. The paper manuscript PDF is delivered separately from support materials.
This first-round archive is not certified anonymous or ready for competition upload.
'''
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for row,path in zip(manifest,paths): z.write(path,row['path'])
        z.writestr('PACKAGE_README.txt',note)
        z.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for row in manifest:
            assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
    assert archive.stat().st_size < 20_000_000, 'Support exceeds official 20MB limit'
    report=dict(created_utc=datetime.now(timezone.utc).isoformat(),path=str(archive.relative_to(ROOT)),
                files=len(manifest),bytes=archive.stat().st_size,
                sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),all_members_verified=True,
                submission_ready=False,scope='first-round code, exact processed inputs, five outputs, audit evidence')
    (out/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
