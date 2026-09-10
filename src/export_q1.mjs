import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'results/audit/artifact_runtime/runtime.mjs'));
const { FileBlob, SpreadsheetFile, Workbook } = await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const resultsDir = path.join(root, 'results/q1');
const previousValidation = await fs.readFile(path.join(resultsDir, 'export_validation.json'), 'utf8').then(JSON.parse).catch(() => null);
const summary = JSON.parse(await fs.readFile(path.join(resultsDir, 'summary.json'), 'utf8'));
const config = summary.config;
const templatePath = path.join(root, config.template_dir, 'result1.xlsx');
const outputPath = path.join(root, 'results/submission/result1.xlsx');
const python = process.env.BUNDLED_PYTHON ?? path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3');
const hash = async (p) => createHash('sha256').update(await fs.readFile(p)).digest('hex');
const templateHash = await hash(templatePath);
const dispatchPath = path.join(resultsDir, 'milp_dispatch.csv');
const dataWorkbook = await Workbook.fromCSV(await fs.readFile(dispatchPath, 'utf8'), { sheetName: 'Dispatch' });
const matrix = dataWorkbook.worksheets.getItem('Dispatch').getUsedRange().values;
const headers = matrix[0];
const records = matrix.slice(1).map(row => Object.fromEntries(headers.map((name, j) => [name, Number(row[j])])));
const needed = ['start_minute', 'end_minute', 'load_kwh', 'pv_kwh', 'price', 'grid_kwh', 'charge_kwh', 'discharge_kwh', 'unused_kwh', 'soc_start_kwh', 'soc_end_kwh'];
if (records.length !== 144 || needed.some(name => !headers.includes(name)) || records.some(row => needed.some(name => !Number.isFinite(row[name])))) {
  throw new Error('Q1 requires exactly 144 complete numeric dispatch records.');
}
if (records.some((row, index) => row.start_minute !== index * 10 || row.end_minute !== (index + 1) * 10)) {
  throw new Error('Q1 dispatch must cover [00:00, 24:00) once on the ten-minute grid.');
}

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(templatePath));
const purchase = workbook.worksheets.getItem('计划购电量');
const battery = workbook.worksheets.getItem('充放电量');
const templateLabels = purchase.getRange('A2:A145').values.map(row => row[0]);
const batteryLabels = battery.getRange('A2:A7').values.map(row => row[0]);
const initialStateLabels = battery.getRange('D2:D3').values.map(row => row[0]);
if (templateLabels[0] !== '0:10-0:20' || templateLabels[143] !== '0:00+1-0:10+1') {
  throw new Error('Template time labels changed: review ordinal mapping before export.');
}
const clock = (minute) => `${Math.floor(minute / 60)}:${String(minute % 60).padStart(2, '0')}`;
const interval = (start, end) => `${clock(start)}-${clock(end)}`;
if (batteryLabels.some((label, index) => label !== interval(index * 240, (index + 1) * 240)) || initialStateLabels.join(',') !== '0:00,24:00') {
  throw new Error('Template battery labels changed: review aggregates before export.');
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
for (const [sheetName, range, name] of [['计划购电量', 'A1:B15', 'template_purchase'], ['充放电量', 'A1:E8', 'template_battery']]) {
  const image = await workbook.render({ sheetName, range, scale: 1.5 });
  await fs.writeFile(path.join(resultsDir, `${name}.png`), new Uint8Array(await image.arrayBuffer()));
}

const aggregates = Array.from({ length: 6 }, (_, block) => {
  const rows = records.filter(row => row.start_minute >= block * 240 && row.end_minute <= (block + 1) * 240);
  if (rows.length !== 24) throw new Error('Each battery reporting block must contain 24 intervals.');
  return ['charge_kwh', 'discharge_kwh'].map(key => rows.reduce((total, row) => total + row[key], 0));
});
purchase.getRange('B2:B145').values = records.map(row => [row.grid_kwh]);
battery.getRange('B2:C7').values = aggregates;
battery.getRange('E2:E3').values = [[records[0].soc_start_kwh], [records.at(-1).soc_end_kwh]];
workbook.recalculate();

const inspections = [];
for (const range of ['计划购电量!A1:B5', '计划购电量!A72:B75', '计划购电量!A142:B145', '充放电量!A1:E7']) {
  inspections.push((await workbook.inspect({ kind: 'table', range, include: 'values,formulas', tableMaxRows: 7, tableMaxCols: 5, maxChars: 3000 })).ndjson);
}
inspections.push((await workbook.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 20 }, summary: 'Q1 final formula error scan', maxChars: 2000 })).ndjson);
await fs.writeFile(path.join(resultsDir, 'export_inspection.ndjson'), inspections.join('\n'));
await (await SpreadsheetFile.exportXlsx(workbook)).save(outputPath);
await fs.rename(`${outputPath}.inspect.ndjson`, path.join(resultsDir, 'artifact_export_inspection.ndjson')).catch(error => { if (error.code !== 'ENOENT') throw error; });
execFileSync(python, ['-c', String.raw`
import io, sys, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ET.register_namespace('',ns['s'])
ET.register_namespace('r','http://schemas.openxmlformats.org/officeDocument/2006/relationships')
source_path,output_path = map(Path,sys.argv[1:])
with zipfile.ZipFile(source_path) as template, zipfile.ZipFile(output_path) as authored:
    payload = {info.filename:(info,template.read(info.filename)) for info in template.infolist()}
    targets = {'xl/worksheets/sheet1.xml':{f'B{r}' for r in range(2,146)},'xl/worksheets/sheet2.xml':{f'{c}{r}' for c in 'BC' for r in range(2,8)}|{'E2','E3'}}
    for name,addresses in targets.items():
        original = ET.fromstring(payload[name][1])
        generated = ET.fromstring(authored.read(name))
        old_cells = {c.attrib['r']:c for c in original.findall('.//s:c',ns)}
        new_cells = {c.attrib['r']:c for c in generated.findall('.//s:c',ns)}
        for address in sorted(addresses):
            if address not in old_cells:
                row_number=''.join(ch for ch in address if ch.isdigit())
                row=original.find(f".//s:row[@r='{row_number}']",ns)
                old_cells[address]=ET.SubElement(row,'{'+ns['s']+'}c',{'r':address})
                row[:]=sorted(row,key=lambda cell:cell.attrib.get('r','').rstrip('0123456789'))
            old,new = old_cells[address],new_cells[address]
            if old.find('s:f',ns) is not None or new.attrib.get('t','n') != 'n':
                raise ValueError(f'Expected blank target and authored numeric cell {name}:{address}')
            value = new.find('s:v',ns)
            if value is None:
                raise ValueError(f'Missing Artifact Tool numeric value {name}:{address}')
            for child in list(old):
                old.remove(child)
            old.attrib.pop('t',None)
            ET.SubElement(old,'{'+ns['s']+'}v').text = value.text
        payload[name]=(payload[name][0],ET.tostring(original,encoding='utf-8',xml_declaration=True))
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w') as restored:
    for info,content in payload.values():
        restored.writestr(info,content)
output_path.write_bytes(buffer.getvalue())
`, templatePath, outputPath]);
const reloaded = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
for (const [sheetName, range, name] of [['计划购电量', 'A1:B17', 'result1_purchase_top'], ['计划购电量', 'A60:B77', 'result1_purchase_mid'], ['计划购电量', 'A132:B145', 'result1_purchase_end'], ['充放电量', 'A1:E8', 'result1_battery']]) {
  const image = await reloaded.render({ sheetName, range, scale: 1.5 });
  await fs.writeFile(path.join(resultsDir, `${name}.png`), new Uint8Array(await image.arrayBuffer()));
}

const mappings = records.map((row, index) => [index, index + 2, `计划购电量!B${index + 2}`, templateLabels[index], row.start_minute, row.end_minute, interval(row.start_minute, row.end_minute), row.grid_kwh, 'kWh', 'TEMPLATE_TIME_LABEL_AMBIGUITY']);
const csvCell = value => /[,"\n]/.test(String(value)) ? `"${String(value).replaceAll('"', '""')}"` : String(value);
await fs.writeFile(path.join(resultsDir, 'template_mapping.csv'), [['interval_index', 'excel_row', 'cell', 'template_label', 'actual_start_minute', 'actual_end_minute', 'actual_interval', 'grid_kwh', 'unit', 'status'], ...mappings].map(row => row.map(csvCell).join(',')).join('\n') + '\n');
const existingMapping = await fs.readFile(path.join(root, 'context/TEMPLATE_MAPPING.md'), 'utf8').catch(() => '');
const annualMappingStart = existingMapping.indexOf('\n## Q2–Q4 年度模板映射');
const annualMappingSuffix = annualMappingStart >= 0 ? existingMapping.slice(annualMappingStart) : '';
await fs.writeFile(path.join(root, 'context/TEMPLATE_MAPPING.md'), `# 第一问模板映射\n\n状态：TEMPLATE_TIME_LABEL_AMBIGUITY。当前 result1.xlsx 为已填值、已校验的模板候选，尚不能称为最终确认可提交版本。\n\n官方原模板 data/templates/2026C/result1.xlsx 的“计划购电量”A2:A145 共144个标签，从0:10-0:20到0:00+1-0:10+1，整体比题面当日[0:00,24:00)晚10分钟。模板未覆盖0:00-0:10，却多含次日0:00-0:10。源数据前置区间平均功率解释与模板错位是两个独立问题，不能用改动数据解释消除标签冲突。\n\n为保留模板名称、表头、布局及全部标签，B2:B145按内部区间序号0–143填写。B2实际对应0:00-0:10，B145实际对应23:50-24:00；全部逐行关系见results/q1/template_mapping.csv。未擅自改写或循环移位时间标签。提交前需核对官方更正，或由队伍明确决定如何修复此模板矛盾。\n\n“充放电量”B2:C7按0–4、4–8、8–12、12–16、16–20、20–24时分别汇总，每段24个区间。B列为交流母线输入充电量，C列为交流母线输出放电量，均为kWh，独立汇总且不取净值。E2、E3为0:00和24:00电池内部储电量kWh；递推为 E(t+1)=E(t)+0.9c(t)-d(t)/0.9。\n\n仅填写上述158个数值单元格，原模板未添加公式、工作表、备注或说明。完整精度写入，展示沿用原模板格式。原模板SHA256：${templateHash}。结果源运行：${summary.run_id}。\n`);

if (annualMappingSuffix) await fs.appendFile(path.join(root, 'context/TEMPLATE_MAPPING.md'), annualMappingSuffix);
const validation = execFileSync(python, ['-c', String.raw`
import copy, csv, hashlib, json, math, sys, zipfile
from pathlib import Path
import openpyxl
root = Path(sys.argv[1])
q1 = root / 'results/q1'
summary = json.loads((q1 / 'summary.json').read_text())
cfg = summary['config']
rows = [{k: float(v) for k,v in r.items()} for r in csv.DictReader((q1/'milp_dispatch.csv').open())]
template_path = root / cfg['template_dir'] / 'result1.xlsx'
output_path = root / 'results/submission/result1.xlsx'
a = openpyxl.load_workbook(template_path)
b = openpyxl.load_workbook(output_path, data_only=False)
checks = {}
checks['sheet_names_and_order'] = a.sheetnames == b.sheetnames
checks['same_dimensions'] = all((a[s].max_row,a[s].max_column)==(b[s].max_row,b[s].max_column) for s in a.sheetnames)
cells = {('计划购电量', f'B{r}') for r in range(2,146)} | {('充放电量', f'{c}{r}') for c in 'BC' for r in range(2,8)} | {('充放电量', 'E2'), ('充放电量','E3')}
style_changes, other_value_changes, feature_changes = [], [], []
for s in a.sheetnames:
    x,y = a[s],b[s]
    for row in x:
        for cell in row:
            target = y[cell.coordinate]
            if (s,cell.coordinate) not in cells and cell.value != target.value:
                other_value_changes.append([s,cell.coordinate])
            if any(copy.copy(getattr(cell,k)) != copy.copy(getattr(target,k)) for k in ['font','fill','border','alignment','number_format','protection']):
                style_changes.append([s,cell.coordinate])
    for key in ['merged_cells','freeze_panes']:
        if str(getattr(x,key)) != str(getattr(y,key)):
            feature_changes.append([s,key])
    if x.auto_filter.ref != y.auto_filter.ref:
        feature_changes.append([s,'auto_filter'])
    if x.sheet_view.showGridLines != y.sheet_view.showGridLines:
        feature_changes.append([s,'gridlines'])
    for key in x.column_dimensions:
        left,right = x.column_dimensions[key],y.column_dimensions[key]
        if any(getattr(left,k)!=getattr(right,k) for k in ['width','hidden','min','max']):
            feature_changes.append([s,'column_dimension',key])
    for key in x.row_dimensions:
        left,right = x.row_dimensions[key],y.row_dimensions[key]
        if any(getattr(left,k)!=getattr(right,k) for k in ['height','hidden']):
            feature_changes.append([s,'row_dimension',key])
checks['untouched_values_preserved'] = not other_value_changes
checks['all_cell_styles_preserved'] = not style_changes
checks['template_layout_preserved'] = not feature_changes
values = [b[s][c].value for s,c in cells]
checks['filled_count_158'] = len(values)==158
checks['all_filled_cells_finite_numeric'] = all(type(v) in (float,int) and math.isfinite(v) for v in values)
checks['no_output_formulas'] = all(b[s][c].data_type != 'f' for s,c in cells)
tol = 1e-7
grid = [b['计划购电量'].cell(i+2,2).value for i in range(144)]
checks['purchase_cellwise_equal_csv'] = max(abs(v-r['grid_kwh']) for v,r in zip(grid,rows)) <= tol
checks['grid_coverage'] = len(rows)==144 and all(r['start_minute']==i*10 and r['end_minute']==(i+1)*10 for i,r in enumerate(rows))
block_diffs=[]
for block in range(6):
    for col,key in [(2,'charge_kwh'),(3,'discharge_kwh')]:
        block_diffs.append(abs(b['充放电量'].cell(block+2,col).value - math.fsum(r[key] for r in rows[block*24:(block+1)*24])))
checks['battery_block_totals_equal_csv'] = max(block_diffs) <= tol
checks['state_cells_equal_csv'] = abs(b['充放电量']['E2'].value-rows[0]['soc_start_kwh'])<=tol and abs(b['充放电量']['E3'].value-rows[-1]['soc_end_kwh'])<=tol
bus=max(abs(g+r['pv_kwh']+r['discharge_kwh']-r['load_kwh']-r['charge_kwh']-r['unused_kwh']) for g,r in zip(grid,rows))
soc=max(abs(r['soc_end_kwh']-r['soc_start_kwh']-cfg['efficiency_charge']*r['charge_kwh']+r['discharge_kwh']/cfg['efficiency_discharge']) for r in rows)
continuity=max(abs(rows[i]['soc_end_kwh']-rows[i+1]['soc_start_kwh']) for i in range(143))
endpoints=[r['soc_start_kwh'] for r in rows]+[rows[-1]['soc_end_kwh']]
checks['bus_conservation'] = bus<=tol
checks['soc_efficiency_recursion'] = soc<=tol
checks['state_continuity'] = continuity<=tol
checks['state_bounds'] = min(endpoints)>=cfg['minimum_kwh']-tol and max(endpoints)<=cfg['maximum_kwh']+tol
checks['initial_and_cyclic_state'] = abs(endpoints[0]-cfg['initial_kwh'])<=tol and abs(endpoints[0]-endpoints[-1])<=tol
checks['no_simultaneous_charge_discharge'] = not any(r['charge_kwh']>tol and r['discharge_kwh']>tol for r in rows)
checks['power_bounds'] = max(max(r['charge_kwh'],r['discharge_kwh']) for r in rows) <= cfg['power_kw']*cfg['dt_hours']+tol
checks['all_flows_nonnegative'] = all(r[k]>=-tol for r in rows for k in ['grid_kwh','charge_kwh','discharge_kwh','unused_kwh'])
cost=math.fsum(g*r['price'] for g,r in zip(grid,rows))
cost_difference=abs(cost-summary['strategies']['milp']['solver']['objective'])
checks['purchase_contract_cost_ledger'] = cost_difference<=tol
checks['template_hash_unchanged'] = hashlib.sha256(template_path.read_bytes()).hexdigest()==sys.argv[2]
with zipfile.ZipFile(template_path) as original,zipfile.ZipFile(output_path) as exported:
    exempt={'xl/worksheets/sheet1.xml','xl/worksheets/sheet2.xml'}
    checks['non_worksheet_package_parts_byte_preserved'] = set(original.namelist())==set(exported.namelist()) and all(original.read(n)==exported.read(n) for n in original.namelist() if n not in exempt)
report={'run_id':summary['run_id'],'status':'TEMPLATE_TIME_LABEL_AMBIGUITY','submission_ready':False,'numerical_export_passed':all(v for k,v in checks.items() if k not in ['all_cell_styles_preserved','template_layout_preserved']),'all_checks_passed':all(checks.values()),'checks':checks,'bus_residual_kwh':bus,'soc_residual_kwh':soc,'continuity_residual_kwh':continuity,'contract_cost_recomputed_yuan':cost,'contract_cost_difference_yuan':cost_difference,'total_grid_kwh':math.fsum(grid),'soc_min_kwh':min(endpoints),'soc_max_kwh':max(endpoints),'tolerance_kwh_or_yuan':tol,'style_changes':style_changes,'layout_changes':feature_changes,'unrelated_value_changes':other_value_changes,'template_sha256':sys.argv[2],'output_sha256':hashlib.sha256(output_path.read_bytes()).hexdigest(),'dispatch_sha256':hashlib.sha256((q1/'milp_dispatch.csv').read_bytes()).hexdigest(),'validation_engine':'independent bundled Python openpyxl readback and math.fsum; no optimization model code imported','visual_qa':'Rendered saved workbook, manual inspection pending','scope':'AC bus charging/discharging kWh, battery internal state kWh; source interval mapping remains explicit'}
report['format_preservation_method']='Artifact Tool authored numeric values transplanted into original OOXML template cells using Python stdlib zipfile/XML; preserves unsupported font charset/family and empty border structures, with no openpyxl authoring'
(q1/'export_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['all_checks_passed','numerical_export_passed','checks','contract_cost_recomputed_yuan']},ensure_ascii=False))
if not report['all_checks_passed']:
    raise SystemExit('Q1 export validation failed; see export_validation.json')
`, root, templateHash], { encoding: 'utf8' });
console.log(validation.trim());
if (await hash(templatePath) !== templateHash) throw new Error('Original template was changed.');
if (previousValidation?.visual_qa?.passed && previousValidation.output_sha256 === await hash(outputPath)) {
  const reportPath = path.join(resultsDir, 'export_validation.json');
  const report = JSON.parse(await fs.readFile(reportPath, 'utf8'));
  report.visual_qa = { ...previousValidation.visual_qa, reused_unchanged_workbook_bytes: true };
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
}
console.log(`Exported ${outputPath}; status TEMPLATE_TIME_LABEL_AMBIGUITY.`);
