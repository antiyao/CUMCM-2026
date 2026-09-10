from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'results/final_recommendation'
ENTRIES = [
    ('Q1', 'result1.xlsx', 'milp', 'results/submission/result1.xlsx', 'results/q1/summary.json'),
    ('Q2', 'result2.xlsx', 'bias_hourly_risk', 'results/q2_iteration/review_candidate_v4/submission/result2.xlsx', 'results/q2_iteration/policy_annual_v4/bias_hourly_risk/summary.json'),
    ('Q3', 'result3.xlsx', 'q3_adjust_A', 'results/submission/result3.xlsx', 'results/backtests/full-evaluation-v1/q3_adjust_A/summary.json'),
    ('Q4-2', 'result4-2.xlsx', 'q4_2_margin', 'results/submission/result4-2.xlsx', 'results/backtests/full-evaluation-v1/q4_2_margin/summary.json'),
    ('Q4-3', 'result4-3.xlsx', 'q4_3_adjust_A', 'results/submission/result4-3.xlsx', 'results/backtests/full-evaluation-v1/q4_3_adjust_A/summary.json'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    entries = []
    for question, filename, strategy, source_name, summary_name in ENTRIES:
        source, target, summary_path = ROOT/source_name, DEST/filename, ROOT/summary_name
        summary = json.loads(summary_path.read_text())
        if not target.exists() and not args.check:
            shutil.copy2(source, target)
        if not target.exists() or digest(target) != digest(source):
            raise ValueError(f'Workbook differs from verified source: {filename}')
        if question == 'Q1':
            result = summary['strategies']['milp']
            cost = result['solver']['objective']
            if not result['validation']['passed']:
                raise ValueError('Q1 validation failed')
            period, days, intervals = '附件1给定单日', 1, 144
        else:
            cost = summary['total_fee']
            days, intervals = summary['days'], summary['intervals']
            period = f"{summary['start_date']} 至 {summary['end_date']}"
            if not summary['verification']['passed'] or days != 334 or intervals != 48096:
                raise ValueError(f'Invalid coverage or verification: {question}')
            with summary_path.with_name('daily.csv').open() as f:
                daily = list(csv.DictReader(f))
            actual = math.fsum(float(row['total_fee']) for row in daily)
            if len(daily) != days or abs(actual-cost) > 1e-6:
                raise ValueError(f'Daily totals disagree: {question}')
        if question == 'Q2':
            selection = json.loads((DEST/'Q2_SELECTION.json').read_text())
            if (selection['sha256'] != digest(source)
                    or selection['recommended_strategy'] != strategy
                    or abs(selection['total_fee_yuan']-cost) > 1e-6):
                raise ValueError('Q2 selection metadata disagrees')
        entries.append(dict(question=question, workbook=filename, strategy=strategy,
                            total_fee_yuan=cost, period=period, days=days, intervals=intervals,
                            source_workbook=source_name, source_summary=summary_name,
                            workbook_sha256=digest(target), source_summary_sha256=digest(summary_path),
                            existing_validation_passed=True))
    result = dict(status='current_review_results', submission_ready=False,
                  unresolved=['模板时间标签语义', '效率、端口、结算与信息边界的暂定解释'],
                  selection_note='Q2 is a retrospective recommendation; Q3/Q4 retain the verified v1 policies.',
                  entries=entries)
    path = DEST/'CURRENT_RESULTS.json'
    if args.check:
        if json.loads(path.read_text()) != result:
            raise ValueError('Current result catalog is stale')
    else:
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        lines = ['# 当前结果统一入口', '',
                 '本目录的五本工作簿是当前审阅入口，均为已核验来源的原字节副本。当前状态为可审阅结果，尚未确认可正式提交。', '',
                 '| 问题 | 当前方案 | 总购电费用/元 | 工作簿 |', '|---|---|---:|---|']
        for e in entries:
            lines.append(f"| {e['question']} | `{e['strategy']}` | {e['total_fee_yuan']:,.2f} | [{e['workbook']}]({e['workbook']}) |")
        lines += ['', 'Q1为附件1的单日；其余四项均覆盖2025-02-01至2025-12-31，共334天、48096个10分钟区间。', '',
                  '## 版本与结论边界', '',
                  '- Q2使用最新`bias_hourly_risk`；旧`q2_margin`交付表已删除，14,056,248.25元的有效基线仍见`results/backtests/full-evaluation-v1/q2_margin/`。',
                  '- Q3/Q4仍为v1已验证方案，不代表全期最优。不能将新Q2与v1 Q3的费用差当作新增预报的价值；应使用v1内部同机会对照。',
                  '- Q2是当前已试可行策略的回溯推荐，不是1月事前跨家族盲测赢家；全知ORACLE不属于可实施策略。',
                  '- 五本均保持`submission_ready=false`。模板标签晚10分钟及现有暂定解释仍需审阅；整理文件不代表消歧完成。', '',
                  '## 核验与来源', '',
                  '`CURRENT_RESULTS.json`保存精确费用、范围、原始结果路径与哈希；`Q2_SELECTION.json`保留第二问选择依据。',
                  '在仓库根目录运行`.venv/bin/python src/catalog_results.py --check`，核验五本镜像、年度日汇总、已有验证状态与目录索引。',
                  '需创建缺少的镜像或重建索引时运行不带`--check`的命令；已有工作簿若与来源不一致会报错，不会覆盖。',
                  '完整物理与逐区间费用检查记录见各来源run的`independent_audit.json`、`summary.json`和导出验证文件。', '']
        (DEST/'README.md').write_text('\n'.join(lines))
    print(f'{len(entries)} current workbooks verified; all annual daily totals agree.')


if __name__ == '__main__':
    main()
