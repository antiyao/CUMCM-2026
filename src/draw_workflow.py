from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from tempfile import gettempdir

from fontTools.ttLib import TTCollection

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1600, 1000
DEST = ROOT / 'figures/overview'
NAME = '总体流程图'
INK = '#233747'
LINE = '#657B8A'


def scene():
    boxes, edges = [], []

    def box(key, x, y, w, h, lines, fill='#FFFFFF', stroke=LINE,
            size=30, color=INK, radius=14):
        boxes.append(dict(id=key, x=x, y=y, w=w, h=h, lines=lines,
                          fill=fill, stroke=stroke, size=size,
                          color=color, radius=radius))

    def edge(key, x1, y1, x2, y2, arrow=True):
        edges.append(dict(id=key, x1=x1, y1=y1, x2=x2, y2=y2,
                          arrow=arrow))

    box('shared-input', 28, 18, 1544, 132,
        ['数据校验 · 时标统一 · 约束定义'],
        fill='#F1F5F8', stroke='#61798B', size=31)

    panels = [
        dict(title=['问题一', '确定性调度'], color='#305E7B', fill='#EFF5F9',
             steps=[['负载与光伏预测'],
                    ['混合整数线性规划'],
                    ['购电与储能调度']]),
        dict(title=['问题二', '历史信息决策'], color='#2F7169', fill='#F0F7F5',
             steps=[['偏差修正', '误差分位保护'],
                    ['零点购电计划', '日内贪心控制'],
                    ['费用与补电比较']]),
        dict(title=['问题三', '日内滚动调整'], color='#8B6231', fill='#FAF6EF',
             steps=[['光伏预报更新'],
                    ['滚动规划', '购电增减计费'],
                    ['预报与调整评估']]),
        dict(title=['问题四', '波动电价扩展'], color='#665A83', fill='#F5F3F8',
             steps=[['历史电价预测', '未来价未知（暂定）'],
                    ['重算第二、三问'],
                    ['实际电价结算', '费用与补电比较']]),
    ]
    centers = []
    for i, panel in enumerate(panels):
        x = 28 + i * 396
        centers.append(x + 178)
        box(f'q{i+1}-panel', x, 208, 356, 600, [],
            fill=panel['fill'], stroke=panel['color'], radius=20)
        box(f'q{i+1}-title', x+12, 222, 332, 100, panel['title'],
            fill=panel['color'], stroke=panel['color'],
            color='#FFFFFF', size=35)
        for j, lines in enumerate(panel['steps']):
            y = 355 + j * 148
            box(f'q{i+1}-step{j+1}', x+18, y, 320, 111, lines,
                stroke=panel['color'], size=30)
            if j < 2:
                edge(f'q{i+1}-arrow{j+1}', x+178, y+117, x+178, y+141)
        edge(f'input-to-q{i+1}', x+178, 177, x+178, 200)
        edge(f'q{i+1}-to-review', x+178, 815, x+178, 847, False)

    edge('input-trunk', 800, 150, 800, 177, False)
    edge('input-distribution', centers[0], 177, centers[-1], 177, False)
    edge('review-collection', centers[0], 847, centers[-1], 847, False)
    edge('review-trunk', 800, 847, 800, 875)
    box('shared-review', 28, 884, 1544, 98,
        ['约束检验 · 信息核验 · 费用对账 · 回测比较'],
        fill='#F1F5F8', stroke='#61798B', size=31)
    return boxes, edges


def export_svg(boxes, edges, path, font):
    ns = 'http://www.w3.org/2000/svg'
    ET.register_namespace('', ns)
    root = ET.Element(f'{{{ns}}}svg', {
        'width': '160mm', 'height': '100mm', 'viewBox': f'0 0 {WIDTH} {HEIGHT}',
        'role': 'img', 'aria-labelledby': 'diagram-title diagram-description'})
    ET.SubElement(root, 'title', id='diagram-title').text = '本文总体研究流程图'
    ET.SubElement(root, 'desc', id='diagram-description').text = (
        '共同数据和物理约束分流至四问：确定性调度、历史信息决策、'
        '日内滚动调整、波动电价扩展，最终汇总开展检验。四列为问题分工，'
        '不表示第二问最终策略已直接用于第三、四问。')
    defs = ET.SubElement(root, 'defs')
    marker = ET.SubElement(defs, 'marker', id='arrowhead', markerWidth='12',
                           markerHeight='10', refX='10', refY='5',
                           orient='auto', markerUnits='userSpaceOnUse')
    ET.SubElement(marker, 'path', d='M 0 0 L 10 5 L 0 10 Z', fill=LINE)
    ET.SubElement(root, 'rect', width=str(WIDTH), height=str(HEIGHT), fill='#FFFFFF')
    edge_group = ET.SubElement(root, 'g', id='connectors', fill='none',
                               stroke=LINE, **{'stroke-width': '2.7'})
    for e in edges:
        attrs = dict(id=e['id'], d=f"M {e['x1']} {e['y1']} L {e['x2']} {e['y2']}")
        if e['arrow']:
            attrs['marker-end'] = 'url(#arrowhead)'
        ET.SubElement(edge_group, 'path', attrs)
    for b in boxes:
        g = ET.SubElement(root, 'g', id=b['id'])
        ET.SubElement(g, 'rect', x=str(b['x']), y=str(b['y']),
                      width=str(b['w']), height=str(b['h']), rx=str(b['radius']),
                      fill=b['fill'], stroke=b['stroke'], **{'stroke-width': '2.5'})
        if not b['lines']:
            continue
        text = ET.SubElement(g, 'text', {
            'font-family': f'{font}, STSong, SimSun, Noto Serif CJK SC, serif',
            'font-size': str(b['size']), 'fill': b['color'], 'text-anchor': 'middle'})
        gap = b['size'] * 1.45
        cy = b['y'] + b['h']/2
        for j, line in enumerate(b['lines']):
            baseline = cy + (j-(len(b['lines'])-1)/2)*gap + b['size']*.35
            ET.SubElement(text, 'tspan', x=str(b['x']+b['w']/2),
                          y=str(baseline)).text = line
    root.remove(edge_group)
    root.append(edge_group)
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def export_drawio(boxes, edges, path):
    root = ET.Element('mxfile', host='app.diagrams.net')
    diagram = ET.SubElement(root, 'diagram', id='workflow', name='总体流程图')
    model = ET.SubElement(diagram, 'mxGraphModel', dx='1600', dy='1000',
                          grid='1', gridSize='10', page='1', pageScale='1',
                          pageWidth='1600', pageHeight='1000')
    cells = ET.SubElement(model, 'root')
    ET.SubElement(cells, 'mxCell', id='0')
    ET.SubElement(cells, 'mxCell', id='1', parent='0')
    panels = {b['id']: b for b in boxes if b['id'].endswith('-panel')}
    for b in boxes:
        style = (f"rounded=1;whiteSpace=wrap;html=0;fillColor={b['fill']};"
                 f"strokeColor={b['stroke']};strokeWidth=2.5;fontColor={b['color']};"
                 f"fontSize={b['size']};fontFamily=STSong;align=center;"
                 'verticalAlign=middle;spacing=8;')
        parent = panels.get(b['id'].split('-')[0]+'-panel')
        if parent is b:
            parent = None
            style += 'container=1;collapsible=0;recursiveResize=0;'
        parent_id = parent['id'] if parent else '1'
        cell = ET.SubElement(cells, 'mxCell', id=b['id'], value='\n'.join(b['lines']),
                             style=style, vertex='1', parent=parent_id)
        ET.SubElement(cell, 'mxGeometry', x=str(b['x']-(parent['x'] if parent else 0)),
                      y=str(b['y']-(parent['y'] if parent else 0)),
                      width=str(b['w']), height=str(b['h']), **{'as': 'geometry'})
    for e in edges:
        style = (f"endArrow={'block' if e['arrow'] else 'none'};html=0;"
                 f'strokeColor={LINE};strokeWidth=2.7;endFill=1;')
        endpoints = {}
        match = re.fullmatch(r'(q[1-4])-arrow([12])', e['id'])
        if match:
            q, step = match.groups()
            endpoints = {'source': f'{q}-step{step}', 'target': f'{q}-step{int(step)+1}'}
            style += 'exitX=0.5;exitY=1;entryX=0.5;entryY=0;edgeStyle=orthogonalEdgeStyle;'
        elif e['id'].startswith('input-to-'):
            endpoints = {'target': e['id'].removeprefix('input-to-')+'-title'}
            style += 'entryX=0.5;entryY=0;'
        elif e['id'].endswith('-to-review'):
            endpoints = {'source': e['id'].removesuffix('-to-review')+'-step3'}
            style += 'exitX=0.5;exitY=1;'
        cell = ET.SubElement(cells, 'mxCell', id=e['id'], style=style, edge='1', parent='1')
        cell.attrib.update(endpoints)
        geo = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
        ET.SubElement(geo, 'mxPoint', x=str(e['x1']), y=str(e['y1']), **{'as': 'sourcePoint'})
        ET.SubElement(geo, 'mxPoint', x=str(e['x2']), y=str(e['y2']), **{'as': 'targetPoint'})
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


def export_pdf_png(boxes, edges, font, dest):
    pt_per_unit = 160 / 25.4 * 72 / WIDTH
    style = {'font.family': font, 'pdf.fonttype': 42, 'svg.fonttype': 'none',
             'axes.unicode_minus': False, 'figure.facecolor': 'white'}
    with plt.rc_context(style):
        fig = plt.figure(figsize=(160/25.4, 100/25.4))
        ax = fig.add_axes([0, 0, 1, 1], xlim=(0, WIDTH), ylim=(HEIGHT, 0))
        ax.axis('off')
        for e in edges:
            ax.add_patch(FancyArrowPatch((e['x1'], e['y1']), (e['x2'], e['y2']),
                         arrowstyle='-|>' if e['arrow'] else '-', mutation_scale=7,
                         linewidth=2.7*pt_per_unit, color=LINE, shrinkA=0, shrinkB=0,
                         zorder=2))
        labels = []
        for b in boxes:
            ax.add_patch(FancyBboxPatch((b['x'], b['y']), b['w'], b['h'],
                         boxstyle=f"round,pad=0,rounding_size={b['radius']}",
                         linewidth=2.5*pt_per_unit, edgecolor=b['stroke'], facecolor=b['fill'],
                         zorder=1 if b['id'].endswith('-panel') else 3))
            if b['lines']:
                t = ax.text(b['x']+b['w']/2, b['y']+b['h']/2,
                            '\n'.join(b['lines']), fontsize=b['size']*pt_per_unit,
                            linespacing=1.45, ha='center', va='center', color=b['color'], zorder=4)
                labels.append((b, t))
        fig.canvas.draw()
        for b, t in labels:
            bb = t.get_window_extent().transformed(ax.transData.inverted())
            if bb.width > b['w']-16 or abs(bb.height) > b['h']-10:
                raise ValueError(f"Text exceeds node bounds: {b['id']}")
        fig.savefig(dest / f'{NAME}.pdf', metadata={'Title': NAME, 'Author': ''})
        fig.savefig(dest / f'{NAME}.png', dpi=300)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    targets = [DEST / f'{NAME}.{ext}' for ext in ['svg', 'pdf', 'png', 'drawio']]
    if not args.overwrite and any(p.exists() for p in targets):
        raise FileExistsError('Outputs exist; review edits before using --overwrite')
    fonts = font_manager.findSystemFonts()
    preferred = next((p for p in fonts if p.endswith('/Songti.ttc')), None)
    if preferred is None:
        raise RuntimeError('Songti.ttc is required for this export')
    collection = TTCollection(preferred)
    regular = next(f for f in collection.fonts if f['name'].getDebugName(6) == 'STSong')
    font_cache = Path(gettempdir()) / 'cumcm-workflow-fonts'
    font_cache.mkdir(exist_ok=True)
    font_file = font_cache / 'STSong.ttf'
    regular.save(font_file)
    font_manager.fontManager.addfont(str(font_file))
    font = font_manager.FontProperties(fname=str(font_file)).get_name()
    boxes, edges = scene()
    export_svg(boxes, edges, targets[0], font)
    export_pdf_png(boxes, edges, font, DEST)
    export_drawio(boxes, edges, targets[3])
    manuscript = ROOT / 'paper/overleaf/figures'
    manuscript.mkdir(parents=True, exist_ok=True)
    for ext in ['svg', 'pdf', 'drawio']:
        shutil.copy2(DEST / f'{NAME}.{ext}', manuscript / f'{NAME}.{ext}')
    references = ['context/CURRENT_STATE.md', 'context/MODELING_PLAN.md',
                  'paper/analysis/第二问最终答案.md', 'paper/analysis/C题四问答案与建模审理说明.md']
    manifest = {'figure': NAME, 'kind': 'conceptual workflow, no numerical results',
                'size_mm': [160, 100], 'font': font, 'svg_text_editable': True,
                'sources': references, 'matplotlib': matplotlib.__version__,
                'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}}
    (DEST/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    print(f'Generated SVG, PDF, PNG and draw.io source: {DEST}')


if __name__ == '__main__':
    main()
