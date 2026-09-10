from pathlib import Path
import json
import hashlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT/'results/q1/milp_dispatch.csv'
    df = pd.read_csv(source)
    summary = json.loads((ROOT/'results/q1/summary.json').read_text())
    fonts = font_manager.findSystemFonts()
    preferred = next((p for p in fonts if p.endswith('/Arial Unicode.ttf')), None)
    if preferred is None:
        preferred = next((p for p in fonts if 'Songti.ttc' in p), None)
    if preferred is None:
        raise RuntimeError('No available CJK font; choose a local font before plotting')
    font_manager.fontManager.addfont(preferred)
    font = font_manager.FontProperties(fname=preferred).get_name()
    dest = ROOT/'figures/q1'
    dest.mkdir(parents=True, exist_ok=True)
    style = {'font.family':font, 'font.size':10, 'axes.titlesize':12,
             'axes.spines.top':False, 'axes.spines.right':False,
             'axes.unicode_minus':False, 'pdf.fonttype':42, 'svg.fonttype':'path',
             'axes.grid':True, 'grid.alpha':.18, 'figure.facecolor':'white',
             'axes.facecolor':'white', 'legend.frameon':False}
    manifest = dict(run_id=summary['run_id'],source=str(source.relative_to(ROOT)),
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    font=font, matplotlib=matplotlib.__version__, files=[])
    def save(fig,name):
        for ext in ['png','pdf','svg']:
            path=dest/f'{name}.{ext}'
            fig.savefig(path,dpi=220,facecolor='white')
            manifest['files'].append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        plt.close(fig)
    with plt.rc_context(style):
        t = df.start_minute.to_numpy()/60
        edges = np.arange(145)/6
        fig,ax=plt.subplots(figsize=(160/25.4,88/25.4),layout='constrained')
        for col,label,color,ls in [('load_kwh','负载','#222222','-'),('pv_kwh','光伏预测','#009E73','--'),('grid_kwh','计划购电','#0072B2',':')]:
            ax.stairs(df[col].to_numpy()*6,edges,label=label,color=color,linestyle=ls,linewidth=1.6)
        ax.set(xlim=(0,24),ylim=(0,None),xticks=np.arange(0,25,4),xlabel='时刻 / h',ylabel='区间平均功率 / kW',title='第一问：负载、光伏与购电调度')
        ax.legend(loc='upper left',ncol=3,fontsize=9)
        save(fig,'q1_dispatch')
        fig,ax=plt.subplots(figsize=(160/25.4,80/25.4),layout='constrained')
        soc=np.r_[df.soc_start_kwh.to_numpy(),df.soc_end_kwh.iloc[-1]]
        ax.plot(edges,soc,color='#0072B2',linewidth=1.8)
        ax.axhline(1200,color='#555555',linestyle='--',linewidth=1,label='运行上下界')
        ax.axhline(10800,color='#555555',linestyle='--',linewidth=1)
        ax.scatter([0,24],[6000,6000],color='#222222',marker='s',s=24,zorder=4,label='首末 6000 kWh')
        ax.set(xlim=(0,24),ylim=(0,12000),xticks=np.arange(0,25,4),yticks=[0,1200,6000,10800,12000],xlabel='时刻 / h',ylabel='电池内部储电量 / kWh',title='第一问：储能状态与运行边界')
        ax.legend(loc='lower center',ncol=2,fontsize=9)
        save(fig,'q1_soc')
        fig,ax=plt.subplots(figsize=(160/25.4,80/25.4),layout='constrained')
        ax.bar(t,df.charge_kwh*6,width=1/6,align='edge',color='#009E73',label='充电',linewidth=.25,edgecolor='white')
        ax.bar(t,-df.discharge_kwh*6,width=1/6,align='edge',color='#D55E00',hatch='///',label='放电',linewidth=.25,edgecolor='white')
        for bound in [-5000,0,5000]: ax.axhline(bound,color='#555555',linewidth=.7,linestyle='--' if bound else '-')
        ax.set(xlim=(0,24),ylim=(-5700,5700),xticks=np.arange(0,25,4),xlabel='时刻 / h',ylabel='交流侧功率 / kW',title='第一问：充放电功率（放电绘为负值）')
        ax.legend(loc='upper right',ncol=2,fontsize=9)
        save(fig,'q1_battery')
        fig,ax=plt.subplots(figsize=(160/25.4,70/25.4),layout='constrained')
        keys=['no_storage','simple_rule','milp']
        vals=[summary['strategies'][k]['solver']['objective'] for k in keys]
        bars=ax.barh(['无储能','低价充高价放','MILP'],vals,color=['#777777','#009E73','#0072B2'],hatch=['//','..',''])
        for b,v in zip(bars,vals): ax.text(v+650,b.get_y()+b.get_height()/2,f'{v:,.2f}',va='center',fontsize=10)
        ax.set(xlim=(0,max(vals)*1.25),xlabel='全天购电费用 / 元',title='第一问：相同初末状态下的费用比较')
        ax.invert_yaxis()
        ax.grid(axis='y',visible=False)
        save(fig,'q1_cost')
    (dest/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(f'Saved {len(manifest["files"])} files using {font}')


if __name__ == '__main__':
    main()
