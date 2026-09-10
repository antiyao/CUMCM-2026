from pathlib import Path
from copy import deepcopy
import html
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import toColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figures/overview/canva'
W, H = 1600, 720
BLUE, GRAY, PALE = '#254e70', '#71828d', '#e9f2f8'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    svg = ET.Element(f'{{{NS}}}svg', width='160mm', height='72mm',
                     viewBox=f'0 0 {W} {H}', role='img')
    ET.SubElement(svg, 'title').text = '微网四问总体研究流程（方法示意）'
    ET.SubElement(svg, 'desc').text = '仿照神秘卷3四栏图示组织。小图表示方法，不表示实际数值结果。'
    parts = []

    def elem(tag, **kw):
        return ET.SubElement(svg, tag, {k.replace('_', '-'):str(v) for k,v in kw.items()})

    def rect(key, x,y,w,h,fill='white',stroke=BLUE,r=12,lw=2.2):
        elem('rect', id=key,x=x,y=y,width=w,height=h,rx=r,fill=fill,stroke=stroke,stroke_width=lw)
        parts.append(f'<div id="{key}" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;border:{lw}px solid {stroke};border-radius:{r}px;background:{fill};box-sizing:border-box;"></div>')

    def text(key,x,y,value,size=29,color=BLUE):
        e=elem('text',id=key,x=x,y=y,fill=color,font_family='STSong, SimSun, Noto Serif SC, serif',font_size=size,text_anchor='middle')
        e.text=value
        parts.append(f'<div id="{key}" style="position:absolute;left:{x-190}px;top:{y-size}px;width:380px;height:{size*1.35}px;font-family:STSong,SimSun,\'Noto Serif SC\',serif;font-size:{size}px;line-height:1.3;color:{color};text-align:center;">{html.escape(value)}</div>')

    def arrow(key,points,color=GRAY,lw=3):
        d='M '+' L '.join(f'{x} {y}' for x,y in points)
        elem('path',id=key,d=d,fill='none',stroke=color,stroke_width=lw)
        x,y=points[-1];px,py=points[-2]
        import math
        a=math.atan2(y-py,x-px);length=11;spread=5
        tip=[(x,y),(x-length*math.cos(a)+spread*math.sin(a),y-length*math.sin(a)-spread*math.cos(a)),(x-length*math.cos(a)-spread*math.sin(a),y-length*math.sin(a)+spread*math.cos(a))]
        elem('polygon',points=' '.join(f'{x},{y}' for x,y in tip),fill=color)
        parts.append(f'<svg style="position:absolute;left:0;top:0;width:{W}px;height:{H}px;" viewBox="0 0 {W} {H}" xmlns="{NS}"><path d="{d}" fill="none" stroke="{color}" stroke-width="{lw}"/><polygon points="'+ ' '.join(f'{x},{y}' for x,y in tip)+f'" fill="{color}"/></svg>')

    def icon(key,name,x,y,w,h):
        source=ET.parse(OUT/'icons'/name).getroot()
        group=elem('g',id=key,transform=f'translate({x},{y}) scale({w/160},{h/120})')
        group.attrib.update({k:v for k,v in source.attrib.items() if k in ['fill','stroke','stroke-width','stroke-linecap','stroke-linejoin']})
        for child in source:
            if child.tag.split('}')[-1] not in ['title','desc','metadata']:
                group.append(deepcopy(child))
        source.attrib.update(width=str(w),height=str(h),style=f'position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;')
        parts.append(ET.tostring(source,encoding='unicode').replace('ns0:','').replace(':ns0',''))

    elem('rect',x=0,y=0,width=W,height=H,fill='white')
    headers=[('问题一','确定性调度','solar_home.svg'),('问题二','日前计划','plan_plug.svg'),('问题三','日内调整','update_clock.svg'),('问题四','电价扩展','price_ledger.svg')]
    arrow('study-sequence',[(12,118),(1585,118)],BLUE,3)
    for i,(num,title,symbol) in enumerate(headers):
        x=24+i*396
        rect(f'q{i+1}-panel',x,180,364,506,r=24)
        icon(f'q{i+1}-symbol',symbol,x+145,15,74,56)
        rect(f'q{i+1}-header',x+12,84,340,76,r=0,lw=2)
        text(f'q{i+1}-number',x+182,112,num,28)
        text(f'q{i+1}-title',x+182,146,title,31)

    x=24
    icon('q1-energy','solar_home.svg',x+55,212,245,184)
    text('q1-balance',x+182,424,'功率平衡')
    arrow('q1-arrow',[(x+266,430),(x+274,458),(x+237,486)],'#669ea6')
    rect('q1-method-tag',x+24,440,152,45,PALE,'#8ba6ba',6,1.4)
    text('q1-method',x+100,473,'整数规划',27)
    icon('q1-battery','battery_cycle.svg',x+79,498,206,155)
    text('q1-output',x+182,674,'储能调度')

    x=420
    icon('q2-predict','forecast_error.svg',x+58,214,245,184)
    text('q2-correct',x+182,423,'偏差修正 · 误差保护',27)
    text('q2-schematic',x+298,386,'示意',17,GRAY)
    arrow('q2-arrow',[(x+83,438),(x+66,474),(x+104,505)],'#669ea6')
    icon('q2-execute','plan_plug.svg',x+70,485,225,169)
    text('q2-output',x+182,674,'计划与紧急补电')

    x=816
    icon('q3-update','update_clock.svg',x+12,204,174,131)
    text('q3-update-label',x+100,362,'预报更新',26)
    text('q3-times',x+100,388,'0 / 6 / 12 / 18',22)
    arrow('q3-update-arrow',[(x+165,278),(x+220,316)],'#669ea6')
    icon('q3-contract','contract_pm.svg',x+178,311,166,125)
    text('q3-adjust-label',x+261,465,'滚动调整',26)
    arrow('q3-cost-arrow',[(x+246,479),(x+223,512)],'#669ea6')
    icon('q3-cost','cost_balance.svg',x+80,480,204,153)
    text('q3-output',x+182,674,'预报与调整价值')

    x=1212
    icon('q4-predict','price_ledger.svg',x+70,212,228,171)
    text('q4-price-label',x+182,415,'电价预测')
    text('q4-assumption',x+182,445,'未来价未知（暂定）',22,GRAY)
    arrow('q4-branch-left',[(x+182,459),(x+182,481),(x+102,481),(x+102,506)],'#669ea6')
    arrow('q4-branch-right',[(x+182,481),(x+267,481),(x+267,506)],'#669ea6')
    for j,cx in enumerate([x+102,x+267]):
        rect(f'q4-plan{j}',cx-46,512,92,91,'#f3f7fa','#6e8fa6',5,2)
        for k in range(3):
            elem('line',x1=cx-30,y1=535+k*18,x2=cx+30,y2=535+k*18,stroke='#8ba6ba',stroke_width=3)
        text(f'q4-plan-label{j}',cx,633,'日前' if j==0 else '日内',26)
    text('q4-output',x+182,674,'两类重算 · 实际价结算',26)
    text('schematic-label',1495,713,'方法示意',16,GRAY)

    stem=OUT/'微网研究流程图_图示版'
    ET.indent(svg)
    ET.ElementTree(svg).write(stem.with_suffix('.svg'),encoding='utf-8',xml_declaration=True)
    document=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>微网研究流程图</title></head><body style="margin:0;background:#fff"><main data-document-role="page" data-label="微网四问图示流程" style="position:relative;width:{W}px;height:{H}px;overflow:hidden;background:white">'+''.join(parts)+'</main></body></html>'
    stem.with_suffix('.html').write_text(document)
    export_pdf(svg,stem.with_suffix('.pdf'))
    subprocess.run(['pdftoppm','-singlefile','-scale-to','2200','-png',str(stem.with_suffix('.pdf')),str(stem)],check=True)
    print(stem.with_suffix('.html'))


def export_pdf(root,path):
    font=Path(tempfile.gettempdir())/'cumcm-workflow-fonts'/'STSong.ttf'
    pdfmetrics.registerFont(TTFont('STSong',str(font)))
    scale=160/25.4*72/W
    c=canvas.Canvas(str(path),pagesize=(W*scale,H*scale))
    c.setTitle('微网四问总体研究流程')
    c.setAuthor('')
    c.translate(0,H*scale);c.scale(scale,-scale)

    def walk(e,inherit=None):
        tag=e.tag.split('}')[-1]
        if tag in ['title','desc','metadata']:return
        attrs={**(inherit or {}),**e.attrib}
        c.saveState()
        transform=e.get('transform','')
        for name,args in re.findall(r'(translate|scale)\(([^)]+)\)',transform):
            a=[float(n) for n in re.split(r'[ ,]+',args)]
            if name=='translate':c.translate(a[0],a[1] if len(a)>1 else 0)
            else:c.scale(a[0],a[1] if len(a)>1 else a[0])
        fill=attrs.get('fill','black');stroke=attrs.get('stroke','none')
        if fill!='none':c.setFillColor(toColor(fill))
        if stroke!='none':c.setStrokeColor(toColor(stroke))
        c.setLineWidth(float(attrs.get('stroke-width',1)))
        dash=attrs.get('stroke-dasharray','none')
        c.setDash([] if dash=='none' else [float(v) for v in re.split(r'[ ,]+',dash)])
        c.setLineCap(1);c.setLineJoin(1)
        flags=dict(fill=int(fill!='none'),stroke=int(stroke!='none'))
        val=lambda k,d=0:float(e.get(k,d))
        if tag=='rect':c.roundRect(val('x'),val('y'),val('width'),val('height'),val('rx'),**flags)
        elif tag=='circle':c.circle(val('cx'),val('cy'),val('r'),**flags)
        elif tag=='ellipse':c.ellipse(val('cx')-val('rx'),val('cy')-val('ry'),val('cx')+val('rx'),val('cy')+val('ry'),**flags)
        elif tag=='line':c.line(val('x1'),val('y1'),val('x2'),val('y2'))
        elif tag in ['polyline','polygon']:
            nums=[float(x) for x in re.findall(r'-?\d+(?:\.\d+)?',e.get('points',''))]
            p=c.beginPath();p.moveTo(*nums[:2])
            for i in range(2,len(nums),2):p.lineTo(*nums[i:i+2])
            if tag=='polygon':p.close()
            c.drawPath(p,**flags)
        elif tag=='path':
            p=c.beginPath();tokens=re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',e.get('d',''))
            i=0;cmd=None;x=y=sx=sy=0
            counts={'M':2,'L':2,'H':1,'V':1,'C':6,'Q':4}
            while i<len(tokens):
                if tokens[i].isalpha():cmd=tokens[i];i+=1
                op=cmd.upper();relative=cmd.islower()
                if op=='Z':p.close();x,y=sx,sy;cmd=None;continue
                if op not in counts:raise ValueError(f'Unsupported SVG path {op}')
                n=counts[op];a=list(map(float,tokens[i:i+n]));i+=n
                if relative:
                    if op=='H':a[0]+=x
                    elif op=='V':a[0]+=y
                    else:
                        for j in range(0,n,2):a[j]+=x;a[j+1]+=y
                if op=='M':x,y=a;p.moveTo(x,y);sx,sy=x,y;cmd='l' if relative else 'L'
                elif op=='L':x,y=a;p.lineTo(x,y)
                elif op=='H':x=a[0];p.lineTo(x,y)
                elif op=='V':y=a[0];p.lineTo(x,y)
                elif op=='C':p.curveTo(*a);x,y=a[-2:]
                elif op=='Q':
                    qx,qy,ex,ey=a;p.curveTo(x+2*(qx-x)/3,y+2*(qy-y)/3,ex+2*(qx-ex)/3,ey+2*(qy-ey)/3,ex,ey);x,y=ex,ey
            c.drawPath(p,**flags)
        elif tag=='text':
            c.translate(val('x'),val('y'));c.scale(1,-1);c.setFont('STSong',val('font-size',29))
            c.drawCentredString(0,0,e.text or '')
        for child in e:
            inherited={k:v for k,v in attrs.items() if k in ['fill','stroke','stroke-width']}
            walk(child,inherited)
        c.restoreState()

    walk(root)
    c.save()


if __name__=='__main__':main()
