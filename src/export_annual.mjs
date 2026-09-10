import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const python = process.env.BUNDLED_PYTHON ?? path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3');
const require = createRequire(path.join(root, 'results/audit/artifact_runtime/runtime.mjs'));
const { FileBlob, SpreadsheetFile } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const config = JSON.parse(await fs.readFile(path.join(root, 'configs/2026c.json'), 'utf8'));
const files = { q2: 'result2', q3: 'result3', 'q4-2': 'result4-2', 'q4-3': 'result4-3' };
const requested = [];
const usage = 'Usage: node src/export_annual.mjs --q2 strategy-directory [--q3 directory] [--q4-2 directory] [--q4-3 directory] [--output-dir directory --report-dir directory]';
let customOutputDir = null;
let customReportDir = null;
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i].replace(/^--/, '');
  const value = process.argv[i + 1];
  if (!value || value.startsWith('--')) throw new Error(usage);
  if (key === 'output-dir') {
    if (customOutputDir !== null) throw new Error('--output-dir may only be supplied once.');
    customOutputDir = value;
  } else if (key === 'report-dir') {
    if (customReportDir !== null) throw new Error('--report-dir may only be supplied once.');
    customReportDir = value;
  } else {
    if (!files[key]) throw new Error(usage);
    requested.push({ key, basename: files[key], sourceDir: path.resolve(root, value) });
  }
}
if ((customOutputDir === null) !== (customReportDir === null)) throw new Error('--output-dir and --report-dir must be supplied together.');
const outputDir = path.resolve(root, customOutputDir ?? 'results/submission');
const reportDir = path.resolve(root, customReportDir ?? 'results/backtests');
if (!requested.length) {
  console.log('No source strategy directories supplied; no workbooks created. Use --q2/--q3/--q4-2/--q4-3 with a completed 334-day strategy directory.');
  process.exit(0);
}
const py = (code, args = []) => execFileSync(python, ['-c', code, ...args], { encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
const sha = async file => createHash('sha256').update(await fs.readFile(file)).digest('hex');
const sum = array => array.reduce((total, value) => total + value, 0);
const clock = minute => `${Math.floor(minute / 60)}:${String(minute % 60).padStart(2, '0')}`;
const interval = (start, end) => `${clock(start)}-${clock(end)}`;
const excelColumn = index => {
  let result = '';
  for (let n = index; n > 0; n = Math.floor((n - 1) / 26)) result = String.fromCharCode(65 + (n - 1) % 26) + result;
  return result;
};
const excelEpoch = Date.UTC(1899, 11, 30);
const dateISO = serial => new Date(excelEpoch + serial * 86400000).toISOString().slice(0, 10);
const csvCell = value => /[,"\n]/.test(String(value)) ? `"${String(value).replaceAll('"', '""')}"` : String(value);
const csv = rows => rows.map(row => row.map(csvCell).join(',')).join('\n') + '\n';
const semantics = {
  status: 'TEMPLATE_TIME_LABEL_AMBIGUITY',
  submission_ready: false,
  purchase_intervals: 'Each preserved template column B:EO receives internal ordinal interval 0:143; interval 0 is [00:00,00:10). Template labels are 10 minutes late and remain unchanged.',
  mapping: 'Column-mapping CSV and date-mapping CSV form an exact Cartesian mapping: Excel cell = excel_column + excel_row, for each listed sheet and date.',
  planned_daily_quantity: 'Sum of the 144 midnight planned_grid values q0, excluding emergency electricity.',
  planned_daily_cost: 'Sum of original_fee only. This is the original ordinary contract fee, not total cost including emergency electricity.',
  adjusted_daily_quantity: 'Sum of the 144 final contract_grid values; these are final ordinary contract quantities, not net adjustments.',
  adjusted_daily_cost: 'Sum of original_fee + increase_fee + decrease_penalty - refund across every interval, including all adjustment events. This ordinary contract total already includes original_fee and must not be added again to planned-sheet cost.',
  total_cost: 'Ordinary contract net fee + emergency_fee. Emergency cost and overall cost remain explicit in internal daily CSV and this independent export ledger; no extra template sheet or header added.',
  battery: 'Six 4-hour blocks per day. Charge/discharge are separate AC-bus kWh totals; state cells are battery-internal kWh at 00:00 and 24:00. Daily states are continuous, not reset.',
  emergency: 'Merge emergency intervals >1e-7 kWh only when adjacent within the same date, matching the source solver-audit tolerance. Do not merge across a zero/below-tolerance interval or midnight. Omitted positive floating-point tails are quantified in the independent ledger. A day with no active emergency has one row with interval 无 and numeric 0; it is not an emergency event.',
  emergency_active_threshold_kwh: 1e-7,
  template_expansion: 'Replace sample ellipsis blocks by all 334 days, preserving header text and repeated prototype styles. Battery has 334*6 data rows; emergency rows vary by actual event count.'
};
await fs.mkdir(reportDir, { recursive: true });
await fs.mkdir(path.join(reportDir, 'export_previews'), { recursive: true });
const reportPath = path.join(reportDir, 'export_validation.json');
const previous = await fs.readFile(reportPath, 'utf8').then(JSON.parse).catch(() => ({ workbooks: {} }));
const report = { ...previous, export_destinations: { output_dir: path.relative(root, outputDir), report_dir: path.relative(root, reportDir) }, semantics, workbooks: { ...previous.workbooks } };

const restoreTemplate = String.raw`
import copy, io, json, sys, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
template_path,output_path=map(Path,sys.argv[1:3])
sheet_specs=json.loads(sys.argv[3])
ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ET.register_namespace('',ns['s'])
ET.register_namespace('r','http://schemas.openxmlformats.org/officeDocument/2006/relationships')
tag=lambda name:'{'+ns['s']+'}'+name
col=lambda address:address.rstrip('0123456789')
def col_index(address):
    result=0
    for ch in col(address):result=result*26+ord(ch)-64
    return result
with zipfile.ZipFile(template_path) as template,zipfile.ZipFile(output_path) as authored:
    payload={info.filename:(info,template.read(info.filename)) for info in template.infolist()}
    shared=[]
    if 'xl/sharedStrings.xml' in authored.namelist():
        shared=[''.join(si.itertext()) for si in ET.fromstring(authored.read('xl/sharedStrings.xml'))]
    def transfer(target,source):
        for child in list(target):target.remove(child)
        target.attrib.pop('t',None)
        if source is None:return
        if source.find('s:f',ns) is not None:raise ValueError('Unexpected output formula')
        kind=source.attrib.get('t','n')
        value=source.find('s:v',ns)
        if kind in ('s','inlineStr','str'):
            text=shared[int(value.text)] if kind=='s' else (''.join(source.find('s:is',ns).itertext()) if kind=='inlineStr' else value.text)
            target.set('t','inlineStr')
            ET.SubElement(ET.SubElement(target,tag('is')),tag('t')).text=text
        elif value is not None:
            ET.SubElement(target,tag('v')).text=value.text
    for index,spec in enumerate(sheet_specs,1):
        name=f'xl/worksheets/sheet{index}.xml'
        original=ET.fromstring(payload[name][1])
        generated=ET.fromstring(authored.read(name))
        new_cells={c.attrib['r']:c for c in generated.findall('.//s:c',ns)}
        data=original.find('s:sheetData',ns)
        if spec['kind']=='wide':
            for row in data:
                if int(row.attrib['r'])==1:continue
                existing={c.attrib['r']:c for c in row}
                for cidx in range(2,148):
                    column=''
                    n=cidx
                    while n: n,r=divmod(n-1,26);column=chr(65+r)+column
                    address=column+row.attrib['r']
                    target=existing.get(address)
                    if target is None:target=ET.SubElement(row,tag('c'),{'r':address})
                    transfer(target,new_cells.get(address))
                row[:]=sorted(row,key=lambda c:col_index(c.attrib['r']))
        else:
            prototypes={int(row.attrib['r']):copy.deepcopy(row) for row in data if int(row.attrib['r']) in range(2,8)}
            for row in list(data):
                if int(row.attrib['r'])!=1:data.remove(row)
            for row_index in range(2,spec['last_row']+1):
                if spec['kind']=='battery':prototype=2+(row_index-2)%6
                else:prototype=2 if new_cells.get(f'A{row_index}') is not None else 3
                row=copy.deepcopy(prototypes[prototype]);row.set('r',str(row_index))
                for cell in row:cell.set('r',col(cell.attrib['r'])+str(row_index))
                existing={col(c.attrib['r']):c for c in row}
                for cidx in range(1,spec['last_col']+1):
                    column=chr(64+cidx);address=column+str(row_index)
                    target=existing.get(column)
                    if target is None:target=ET.SubElement(row,tag('c'),{'r':address})
                    transfer(target,new_cells.get(address))
                row[:]=sorted(row,key=lambda c:col_index(c.attrib['r']))
                data.append(row)
            original.find('s:dimension',ns).set('ref',f"A1:{chr(64+spec['last_col'])}{spec['last_row']}")
        payload[name]=(payload[name][0],ET.tostring(original,encoding='utf-8',xml_declaration=True))
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w') as output:
    for info,content in payload.values():output.writestr(info,content)
output_path.write_bytes(buffer.getvalue())
`;

const independentValidator = String.raw`
import csv,gzip,json,math,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timedelta
import openpyxl
root,source_dir,template_path,output_path=map(Path,sys.argv[1:5])
cfg=json.loads((root/'configs/2026c.json').read_text())
summary=json.loads((source_dir/'summary.json').read_text())
with gzip.open(source_dir/'intervals.csv.gz','rt') as handle:
    rows=[{k:(v if k in ['date','interval_start','interval_end'] else float(v)) for k,v in r.items()} for r in csv.DictReader(handle)]
source_daily={r['date']:r for r in csv.DictReader((source_dir/'daily.csv').open())}
original=openpyxl.load_workbook(template_path)
output=openpyxl.load_workbook(output_path,data_only=False)
interpretation=summary.get('strategy',{}).get('interpretation')
if interpretation is None:
    adjustment_fields=['increase_fee','decrease_penalty','refund','contract_increase','contract_decrease']
    if '调整购电量' in output.sheetnames or any(r[k]!=0.0 for r in rows for k in adjustment_fields):
        raise ValueError('Missing settlement interpretation is only allowed for a zero-adjustment Q2-style workbook.')
    interpretation='NOT_APPLICABLE_NO_ADJUSTMENTS'
elif interpretation not in ('A','B'):
    raise ValueError('Unsupported settlement interpretation.')
bydate=defaultdict(list)
for row in rows:bydate[row['date']].append(row)
dates=sorted(bydate)
checks={}
tol=1e-6
eps=1e-7
checks['334_days_48096_intervals']=len(dates)==334 and len(rows)==48096
checks['unique_contiguous_interval_keys']=all(r['date']==dates[i//144] and r['interval_index']==i%144 for i,r in enumerate(rows))
checks['full_evaluation_calendar']=dates==[(datetime(2025,2,1)+timedelta(days=i)).strftime('%Y-%m-%d') for i in range(334)]
checks['sheet_names_and_order']=original.sheetnames==output.sheetnames
checks['all_headers_unchanged']=all([c.value for c in original[s][1]]==[c.value for c in output[s][1]] for s in original.sheetnames)
checks['no_ellipsis_placeholder']=not any(c.value=='⁝' for s in output for row in s for c in row)
checks['no_output_formulas']=not any(c.data_type=='f' for s in output for row in s for c in row)
checks['finite_numeric_source']=all(math.isfinite(v) for r in rows for v in r.values() if type(v) in (float,int))
wide=['计划购电量']+(['调整购电量'] if '调整购电量' in output.sheetnames else [])
max_cell_error=0.0
all_numeric=True
headers_dates=True
daily_ledger=[]
for d,date in enumerate(dates):
    daily=bydate[date]
    original_cost=math.fsum(r['price']*r['planned_grid'] for r in daily)
    increment=math.fsum(1.5*r['price']*r['contract_increase'] for r in daily)
    reduction=math.fsum(.5*r['price']*r['contract_decrease'] for r in daily)
    refund=math.fsum(r['price']*r['contract_decrease'] for r in daily) if interpretation=='B' else 0.0
    ordinary=original_cost+increment+reduction-refund
    emergency_cost=math.fsum(5*r['price']*r['emergency'] for r in daily)
    total=ordinary+emergency_cost
    daily_ledger.append({'date':date,'original_contract_fee_yuan':original_cost,'increase_fee_yuan':increment,'decrease_penalty_yuan':reduction,'refund_yuan':refund,'ordinary_contract_net_fee_yuan':ordinary,'emergency_fee_yuan':emergency_cost,'total_fee_yuan':total})
    for sheet in wide:
        s=output[sheet]
        key='planned_grid' if sheet=='计划购电量' else 'contract_grid'
        values=[s.cell(d+2,c).value for c in range(2,148)]
        all_numeric=all_numeric and all(type(value) in (float,int) and math.isfinite(value) for value in values)
        expected=[r[key] for r in daily]+[math.fsum(r[key] for r in daily),original_cost if key=='planned_grid' else ordinary]
        max_cell_error=max(max_cell_error,max(abs(a-b) for a,b in zip(values,expected)))
        headers_dates=headers_dates and s.cell(d+2,1).value==original[sheet].cell(d+2,1).value
checks['wide_tables_334x144_and_daily_totals']=all((output[s].max_row,output[s].max_column)==(335,147) for s in wide)
checks['wide_tables_all_numeric']=all_numeric
checks['wide_tables_cellwise_equal_source_and_fee_ledger']=max_cell_error<=tol
checks['wide_table_dates_unchanged']=headers_dates
battery=output['充放电量']
battery_error=0.0
battery_labels=True
for d,date in enumerate(dates):
    daily=bydate[date]
    first=2+d*6
    battery_labels=battery_labels and battery.cell(first,1).value.strftime('%Y-%m-%d')==date
    for block in range(6):
        row=first+block
        expected_label=f'{block*4}:00-{(block+1)*4}:00'
        battery_labels=battery_labels and battery.cell(row,2).value==expected_label
        for col,key in [(3,'charge'),(4,'discharge')]:
            actual=battery.cell(row,col).value
            all_numeric=all_numeric and type(actual) in (float,int) and math.isfinite(actual)
            battery_error=max(battery_error,abs(actual-math.fsum(r[key] for r in daily[block*24:(block+1)*24])))
    battery_error=max(battery_error,abs(battery.cell(first,6).value-daily[0]['soc_start']),abs(battery.cell(first+1,6).value-daily[-1]['soc_end']))
checks['battery_2004_rows_and_labels']=(battery.max_row,battery.max_column)==(2005,6) and battery_labels
checks['battery_block_sums_and_endpoint_states']=battery_error<=tol
checks['battery_amounts_numeric']=all_numeric
expected_events=[]
for date in dates:
    daily=bydate[date]
    active=[]
    for r in daily:
        if r['emergency']>eps:
            if not active or int(r['interval_index'])!=active[-1][-1]['interval_index']+1:active.append([])
            active[-1].append(r)
    if not active:expected_events.append((date,'无',0.0))
    else:
        for segment in active:
            start=int(segment[0]['interval_index'])*10
            end=(int(segment[-1]['interval_index'])+1)*10
            label=f'{start//60}:{start%60:02d}-{end//60}:{end%60:02d}'
            expected_events.append((date,label,math.fsum(r['emergency'] for r in segment)))
actual_events=[]
active_date=None
for row in output['紧急购电量'].iter_rows(min_row=2,max_col=3,values_only=True):
    if row[0] is not None:active_date=row[0].strftime('%Y-%m-%d')
    actual_events.append((active_date,row[1],row[2]))
checks['emergency_events_adjacent_same_day_and_exact_rows']=len(actual_events)==len(expected_events) and all(a[:2]==b[:2] and type(a[2]) in (float,int) and abs(a[2]-b[2])<=tol for a,b in zip(actual_events,expected_events))
event_count=sum(label!='无' for _,label,_ in actual_events)
checks['emergency_event_count_equals_source_summary']=event_count==summary['emergency_events']
emergency_total=math.fsum(row[2] for row in actual_events)
omitted_tail=math.fsum(r['emergency'] for r in rows if 0<r['emergency']<=eps)
checks['emergency_total_reconciliation']=abs(emergency_total+omitted_tail-summary['emergency'])<=tol
bus=max(abs(r['contract_grid']+r['emergency']+r['pv_kwh']+r['discharge']-r['load_kwh']-r['charge']-r['unused']) for r in rows)
soc=max(abs(r['soc_end']-r['soc_start']-cfg['efficiency_charge']*r['charge']+r['discharge']/cfg['efficiency_discharge']) for r in rows)
continuity=max(abs(a['soc_end']-b['soc_start']) for a,b in zip(rows,rows[1:]))
states=[r['soc_start'] for r in rows]+[rows[-1]['soc_end']]
checks['independent_bus_conservation']=bus<=tol
checks['independent_soc_recursion']=soc<=tol
checks['continuous_state_including_midnight']=continuity<=tol
checks['soc_within_limits']=min(states)>=cfg['minimum_kwh']-tol and max(states)<=cfg['maximum_kwh']+tol
checks['ac_power_and_nonnegative_limits']=max(max(r['charge'],r['discharge']) for r in rows)<=cfg['power_kw']*cfg['dt_hours']+tol and all(r[k]>=-tol for r in rows for k in ['planned_grid','contract_grid','charge','discharge','emergency','unused'])
checks['no_simultaneous_charge_discharge']=not any(r['charge']>eps and r['discharge']>eps for r in rows)
checks['no_emergency_direct_charging']=not any(r['charge']>eps and r['emergency']>eps for r in rows)
checks['unused_sources_reconcile']=max(abs(r['unused']-r['unused_pv']-r['unused_purchased']) for r in rows)<=tol
fee_residual=max(abs(r['total_fee']-(r['price']*r['planned_grid']+1.5*r['price']*r['contract_increase']+.5*r['price']*r['contract_decrease']-(r['price']*r['contract_decrease'] if interpretation=='B' else 0)+5*r['price']*r['emergency'])) for r in rows)
checks['interval_contract_emergency_fee_formula']=fee_residual<=tol
checks['contract_adjustments_reconcile']=max(abs(r['contract_grid']-r['planned_grid']-r['contract_increase']+r['contract_decrease']) for r in rows)<=tol
event_path=source_dir/'events.csv'
event_audit={'available':event_path.exists(),'event_rows':0}
if event_path.exists():
    events=list(csv.DictReader(event_path.open()))
    source_by_key={(r['date'],int(r['interval_index'])):r for r in rows}
    current={key:r['planned_grid'] for key,r in source_by_key.items()}
    cumulative=defaultdict(lambda:[0.0,0.0])
    event_fees=[]
    history_nonnegative=True
    unique=set()
    valid_time=True
    valid_amounts=True
    valid_prices=True
    valid_event_fees=True
    for e in sorted(events,key=lambda r:(r['date'],r['issue_time'],int(r['interval_index']))):
        key=(e['date'],int(e['interval_index']))
        inc,dec=float(e['increase_kwh']),float(e['decrease_kwh'])
        price=float(e['delivery_price'])
        effective=int(e['effective_from'])
        issue=datetime.fromisoformat(e['issue_time'])
        valid_time=valid_time and issue.strftime('%Y-%m-%d')==e['date'] and effective==(issue.hour*60+issue.minute)//10 and int(e['interval_index'])>=effective and (e['date'],e['issue_time'],e['interval_index']) not in unique
        unique.add((e['date'],e['issue_time'],e['interval_index']))
        valid_amounts=valid_amounts and inc>=-tol and dec>=-tol and min(inc,dec)<=tol
        valid_prices=valid_prices and abs(price-source_by_key[key]['price'])<=tol
        expected_refund=price*dec if interpretation=='B' else 0.0
        valid_event_fees=valid_event_fees and abs(float(e['increase_fee'])-1.5*price*inc)<=tol and abs(float(e['decrease_penalty'])-.5*price*dec)<=tol and abs(float(e['refund'])-expected_refund)<=tol
        current[key]+=inc-dec
        history_nonnegative=history_nonnegative and current[key]>=-tol
        cumulative[key][0]+=inc;cumulative[key][1]+=dec
        event_fees.append(1.5*price*inc+.5*price*dec-expected_refund)
    event_reconcile=max(abs(current[key]-r['contract_grid']) for key,r in source_by_key.items())
    cumulative_reconcile=max(max(abs(cumulative[key][0]-r['contract_increase']),abs(cumulative[key][1]-r['contract_decrease'])) for key,r in source_by_key.items())
    checks['event_history_only_unexecuted_unique_targets']=valid_time
    checks['event_history_nonnegative_contracts_and_deltas']=valid_amounts and history_nonnegative
    checks['event_history_prices_and_component_fees']=valid_prices and valid_event_fees
    checks['event_history_reconstructs_final_contract']=event_reconcile<=tol and cumulative_reconcile<=tol
    event_audit={'available':True,'event_rows':len(events),'reconstructed_contract_max_error_kwh':event_reconcile,'cumulative_increase_decrease_error_kwh':cumulative_reconcile,'net_adjustment_fee_from_events_yuan':math.fsum(event_fees)}
elif '调整购电量' in output.sheetnames:
    checks['event_history_exists_for_adjustment_sheet']=False
daily_difference=max(abs(row['total_fee_yuan']-float(source_daily[row['date']]['total_fee'])) for row in daily_ledger)
total_cost=math.fsum(row['total_fee_yuan'] for row in daily_ledger)
checks['daily_fee_ledger_equals_source_daily']=daily_difference<=tol
checks['annual_fee_ledger_equals_source_summary']=abs(total_cost-summary['total_fee'])<=tol
namespace={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(template_path) as old,zipfile.ZipFile(output_path) as new:
    checks['non_worksheet_package_parts_byte_preserved']=set(old.namelist())==set(new.namelist()) and all(old.read(n)==new.read(n) for n in old.namelist() if not n.startswith('xl/worksheets/sheet'))
    style_refs=True
    for index,name in enumerate(original.sheetnames,1):
        if name not in wide:continue
        member=f'xl/worksheets/sheet{index}.xml'
        left=ET.fromstring(old.read(member));right=ET.fromstring(new.read(member))
        right_cells={c.attrib['r']:c for c in right.findall('.//s:c',namespace)}
        style_refs=style_refs and all(c.attrib.get('s')==right_cells[c.attrib['r']].attrib.get('s') for c in left.findall('.//s:c',namespace))
    checks['wide_template_cell_style_references_preserved']=style_refs
result={'checks':checks,'all_checks_passed':all(checks.values()),'check_count':len(checks),'bus_residual_kwh':bus,'soc_residual_kwh':soc,'continuity_residual_kwh':continuity,'max_wide_cell_error_kwh_or_yuan':max_cell_error,'max_battery_cell_error_kwh':battery_error,'interval_fee_residual_yuan':fee_residual,'annual_total_cost_yuan':total_cost,'annual_original_fee_yuan':math.fsum(d['original_contract_fee_yuan'] for d in daily_ledger),'annual_ordinary_contract_net_fee_yuan':math.fsum(d['ordinary_contract_net_fee_yuan'] for d in daily_ledger),'annual_emergency_fee_yuan':math.fsum(d['emergency_fee_yuan'] for d in daily_ledger),'annual_total_difference_yuan':total_cost-summary['total_fee'],'emergency_event_count':event_count,'emergency_active_threshold_kwh':eps,'omitted_positive_float_tail_kwh':omitted_tail,'initial_soc_kwh':states[0],'terminal_soc_kwh':states[-1],'daily_ledger':daily_ledger,'event_history':event_audit,'validator':'Independent bundled Python openpyxl readback, math.fsum, and direct physical/settlement formulas; no optimization or backtest code imported.'}
result['settlement_interpretation']=interpretation
print(json.dumps(result,allow_nan=False))
`;

for (const task of requested) {
  const entry = { source_dir: path.relative(root, task.sourceDir), source_run_id: path.basename(path.dirname(task.sourceDir)), status: 'PENDING', submission_ready: false, export_config: config, export_code_sha256: await sha(fileURLToPath(import.meta.url)) };
  report.workbooks[task.basename] = entry;
  try {
    const sourcePath = path.join(task.sourceDir, 'intervals.csv.gz');
    const summaryPath = path.join(task.sourceDir, 'summary.json');
    entry.source_summary = JSON.parse(await fs.readFile(summaryPath, 'utf8'));
    if (entry.source_summary.verification?.passed !== true) throw new Error('Source summary does not report a completed passing physical verification.');
    entry.source_sha256 = await sha(sourcePath);
    entry.source_summary_sha256 = await sha(summaryPath);
    const input = JSON.parse(py(String.raw`
import csv,gzip,json,sys
fields=['interval_index','load_kwh','pv_kwh','price','plan_price','planned_grid','contract_grid','charge','discharge','soc_start','soc_end','emergency','unused','unused_pv','unused_purchased','original_fee','increase_fee','decrease_penalty','refund','emergency_fee','total_fee','contract_increase','contract_decrease']
with gzip.open(sys.argv[1],'rt') as file:
    rows=[{'date':r['date'],**{k:float(r[k]) for k in fields}} for r in csv.DictReader(file)]
print(json.dumps(rows,allow_nan=False))
`, [sourcePath]));
    const templatePath = path.join(root, config.template_dir, `${task.basename}.xlsx`);
    entry.template_sha256 = await sha(templatePath);
    const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
    const purchase = workbook.worksheets.getItem('计划购电量');
    const dates = purchase.getRange('A2:A335').values.map(row => ({ serial: row[0], date: dateISO(row[0]) }));
    const labels = purchase.getRange('B1:EO1').values[0];
    if (dates.length !== 334 || dates[0].date !== '2025-02-01' || dates.at(-1).date !== '2025-12-31' || labels[0] !== '0:10-0:20' || labels.at(-1) !== '0:00-0:10+1') throw new Error('Official template calendar or time labels changed.');
    if (input.length !== 334 * 144 || input.some((row, index) => row.date !== dates[Math.floor(index / 144)].date || row.interval_index !== index % 144)) {
      entry.status = 'INCOMPLETE_OR_NONCANONICAL_COVERAGE';
      entry.interval_count = input.length;
      console.log(`${task.basename}: incomplete 334-day source; no workbook exported.`);
      continue;
    }
    const hasAdjustment = ['q3', 'q4-3'].includes(task.key);
    const sheets = ['计划购电量', ...(hasAdjustment ? ['调整购电量'] : []), '充放电量', '紧急购电量'];
    for (const sheetName of sheets) {
      const range = sheetName.endsWith('购电量') && sheetName !== '紧急购电量' ? 'A1:F5' : sheetName === '充放电量' ? 'A1:F9' : 'A1:C11';
      const image = await workbook.render({ sheetName, range, scale: 1.5 });
      await fs.writeFile(path.join(reportDir, 'export_previews', `${task.basename}_template_${sheets.indexOf(sheetName)}.png`), new Uint8Array(await image.arrayBuffer()));
    }
    const purchaseValues = [];
    const adjustedValues = [];
    const batteryValues = [];
    const emergencyValues = [];
    const dateMappings = [['date', 'excel_row', 'battery_first_row', 'battery_last_row', 'emergency_first_row', 'emergency_last_row']];
    let eventCount = 0;
    for (let d = 0; d < dates.length; d++) {
      const daily = input.slice(d * 144, (d + 1) * 144);
      const planned = daily.map(row => row.planned_grid);
      const contracted = daily.map(row => row.contract_grid);
      purchaseValues.push([...planned, sum(planned), sum(daily.map(row => row.original_fee))]);
      adjustedValues.push([...contracted, sum(contracted), sum(daily.map(row => row.original_fee + row.increase_fee + row.decrease_penalty - row.refund))]);
      for (let block = 0; block < 6; block++) {
        const rows = daily.slice(block * 24, (block + 1) * 24);
        batteryValues.push([block === 0 ? dates[d].serial : null, interval(block * 240, (block + 1) * 240), sum(rows.map(row => row.charge)), sum(rows.map(row => row.discharge)), block === 0 ? 0 : block === 1 ? '24:00' : null, block === 0 ? daily[0].soc_start : block === 1 ? daily.at(-1).soc_end : null]);
      }
      const events = [];
      for (let i = 0; i < 144;) {
        if (daily[i].emergency <= semantics.emergency_active_threshold_kwh) { i++; continue; }
        const start = i;
        let quantity = 0;
        while (i < 144 && daily[i].emergency > semantics.emergency_active_threshold_kwh) quantity += daily[i++].emergency;
        events.push([interval(start * 10, i * 10), quantity]);
      }
      eventCount += events.length;
      const firstEmergencyRow = emergencyValues.length + 2;
      if (!events.length) emergencyValues.push([dates[d].serial, '无', 0]);
      else for (let i = 0; i < events.length; i++) emergencyValues.push([i === 0 ? dates[d].serial : null, ...events[i]]);
      dateMappings.push([dates[d].date, d + 2, d * 6 + 2, d * 6 + 7, firstEmergencyRow, emergencyValues.length + 1]);
    }
    purchase.getRange('B2:EQ335').values = purchaseValues;
    if (hasAdjustment) workbook.worksheets.getItem('调整购电量').getRange('B2:EQ335').values = adjustedValues;
    const battery = workbook.worksheets.getItem('充放电量');
    battery.getRange('A2:F2005').clear({ applyTo: 'contents' });
    for (let d = 1; d < 334; d++) battery.getRange(`A${d * 6 + 2}:F${d * 6 + 7}`).copyFrom(battery.getRange('A2:F7'), 'all');
    battery.getRange('A2:F2005').values = batteryValues;
    const emergency = workbook.worksheets.getItem('紧急购电量');
    emergency.getRange(`A2:C${Math.max(11, emergencyValues.length + 1)}`).clear({ applyTo: 'contents' });
    for (let i = 1; i < emergencyValues.length; i++) emergency.getRange(`A${i + 2}:C${i + 2}`).copyFrom(emergency.getRange('A2:C2'), 'all');
    emergency.getRange(`A2:C${emergencyValues.length + 1}`).values = emergencyValues;
    workbook.recalculate();
    const inspection = await workbook.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 10 }, maxChars: 1500 });
    entry.formula_error_scan = inspection.ndjson;
    const outputPath = path.join(outputDir, `${task.basename}.xlsx`);
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await (await SpreadsheetFile.exportXlsx(workbook)).save(outputPath);
    await fs.rename(`${outputPath}.inspect.ndjson`, path.join(reportDir, `${task.basename}_artifact_inspection.ndjson`)).catch(error => { if (error.code !== 'ENOENT') throw error; });
    py(restoreTemplate, [templatePath, outputPath, JSON.stringify(sheets.map(name => name === '充放电量' ? { kind: 'battery', last_row: 2005, last_col: 6 } : name === '紧急购电量' ? { kind: 'emergency', last_row: emergencyValues.length + 1, last_col: 3 } : { kind: 'wide' }))]);
    const saved = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
    const previewRanges = sheets.flatMap(sheetName => sheetName === '充放电量' ? [[sheetName, 'A1:F9'], [sheetName, 'A1994:F2005']] : sheetName === '紧急购电量' ? [[sheetName, 'A1:C12'], [sheetName, `A${Math.max(2, emergencyValues.length - 9)}:C${emergencyValues.length + 1}`]] : [[sheetName, 'A1:F5'], [sheetName, 'EM1:EQ5'], [sheetName, 'EM332:EQ335']]);
    entry.previews = [];
    for (let i = 0; i < previewRanges.length; i++) {
      const [sheetName, range] = previewRanges[i];
      const image = await saved.render({ sheetName, range, scale: 1.5 });
      const target = path.join(reportDir, 'export_previews', `${task.basename}_${i}.png`);
      await fs.writeFile(target, new Uint8Array(await image.arrayBuffer()));
      entry.previews.push({ sheet: sheetName, range, path: path.relative(root, target) });
    }
    const mappingRows = [['sheet', 'interval_index', 'excel_column', 'template_label', 'actual_start_minute', 'actual_end_minute', 'actual_interval', 'status']];
    for (const sheet of ['计划购电量', ...(hasAdjustment ? ['调整购电量'] : [])]) for (let i = 0; i < 144; i++) mappingRows.push([sheet, i, excelColumn(i + 2), labels[i], i * 10, (i + 1) * 10, interval(i * 10, (i + 1) * 10), semantics.status]);
    await fs.writeFile(path.join(reportDir, `${task.basename}_template_mapping.csv`), csv(mappingRows));
    await fs.writeFile(path.join(reportDir, `${task.basename}_date_mapping.csv`), csv(dateMappings));
    entry.output = path.relative(root, outputPath);
    entry.output_sha256 = await sha(outputPath);
    entry.event_count = eventCount;
    entry.emergency_rows = emergencyValues.length;
    entry.battery_rows = batteryValues.length;
    entry.interval_count = input.length;
    entry.status = semantics.status;
    entry.visual_qa = previous.workbooks?.[task.basename]?.output_sha256 === entry.output_sha256 && previous.workbooks[task.basename].visual_qa?.passed ? { ...previous.workbooks[task.basename].visual_qa, reused_unchanged_workbook_bytes: true } : { passed: null, state: 'Rendered saved workbook; manual review pending.' };
    entry.template_hash_unchanged = await sha(templatePath) === entry.template_sha256;
    entry.independent_validation = JSON.parse(py(independentValidator, [root, task.sourceDir, templatePath, outputPath]));
    if (!entry.independent_validation.all_checks_passed) throw new Error('Independent export checks failed; see export_validation.json.');
    console.log(`${task.basename}: exported ${input.length} intervals, ${eventCount} emergency events; ${entry.independent_validation.check_count} independent checks passed.`);
  } catch (error) {
    entry.status = 'EXPORT_FAILED';
    entry.error = error.message;
    console.error(`${task.basename}: ${error.message}`);
  } finally {
    report.all_four_annual_outputs_exported = Object.values(files).every(name => report.workbooks[name]?.status === semantics.status);
    report.all_available_outputs_numerically_verified = Object.values(report.workbooks).every(value => value.status === semantics.status && value.independent_validation?.all_checks_passed === true);
    report.all_available_outputs_visually_reviewed = Object.values(report.workbooks).every(value => value.status === semantics.status && value.visual_qa?.passed === true);
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
  }
}
if (Object.values(report.workbooks).some(entry => entry.status === 'EXPORT_FAILED')) process.exitCode = 1;
