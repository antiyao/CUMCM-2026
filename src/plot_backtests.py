import argparse
from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',default='results/backtests/q2-annual')
    parser.add_argument('--output',default='figures/q2')
    args=parser.parse_args()
    run,dest=ROOT/args.run,ROOT/args.output
    summary=json.loads((run/'summary.json').read_text())
    p=next(p for p in font_manager.findSystemFonts() if p.endswith('/Arial Unicode.ttf'))
    font_manager.fontManager.addfont(p)
    style={'font.family':font_manager.FontProperties(fname=p).get_name(),'font.size':10,
           'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'path',
           'axes.spines.top':False,'axes.spines.right':False}
    dest.mkdir(parents=True,exist_ok=True)
    generated=[]
    def save(fig,name):
        fig.canvas.draw()
        fig.set_layout_engine(None)
        for ext in ['png','pdf','svg']:
            p=dest/f'{name}.{ext}'
            fig.savefig(p,dpi=200,facecolor='white')
            generated.append(str(p.relative_to(ROOT)))
        plt.close(fig)
    labels={'q2_no_battery':'无储能','q2_point':'点预测','q2_margin':'校准裕量','q2_margin_greedy':'裕量＋贪心控制'}
    keys=[k for k in labels if k in summary]
    with plt.rc_context(style):
        fig,ax=plt.subplots(figsize=(160/25.4,85/25.4),layout='constrained')
        original=np.array([summary[k]['original_fee'] for k in keys])/1e4
        emergency=np.array([summary[k]['emergency_fee'] for k in keys])/1e4
        x=np.arange(len(keys))
        ax.bar(x,original,color='#0072B2',label='原计划费')
        ax.bar(x,emergency,bottom=original,color='#D55E00',hatch='///',label='紧急购电费')
        ax.set(xticks=x,xticklabels=[labels[k] for k in keys],ylabel='334天购电费用 / 万元',ylim=(0,None),title='第二问：合同收费与紧急购电代价')
        ax.legend(ncol=2,loc='upper right',fontsize=9)
        ax.grid(axis='y',alpha=.2)
        save(fig,'q2_cost')
        daily={k:pd.read_csv(run/k/'daily.csv',parse_dates=['date']).set_index('date') for k in keys}
        if 'q2_margin' in daily:
            frame=pd.read_csv(run/'q2_margin/intervals.csv.gz')
            assert len(frame)==334*144
            days=frame.date.drop_duplicates().to_numpy()
            ticks=[i for i,d in enumerate(days) if d.endswith('-01')]
            for col,name,title,cmap,limit in [('soc_start','q2_soc','第二问：校准裕量方案储能状态','cividis',(1200,10800)),
                                             ('emergency','q2_emergency','第二问：校准裕量方案紧急购电','magma',(0,None))]:
                a=frame[col].to_numpy().reshape(334,144)
                fig,ax=plt.subplots(figsize=(160/25.4,115/25.4),layout='constrained')
                im=ax.imshow(np.ma.masked_invalid(a),aspect='auto',interpolation='nearest',
                             cmap=matplotlib.colormaps[cmap].with_extremes(bad='#888888'),vmin=limit[0],vmax=limit[1])
                ax.set(xticks=[0,36,72,108,143],xticklabels=['00:00','06:00','12:00','18:00','23:50'],
                       yticks=ticks,yticklabels=[d[5:] for d in days[ticks]],xlabel='区间起点',ylabel='2025年日期',title=title)
                fig.colorbar(im,ax=ax,label='电池内部电量 / kWh' if col=='soc_start' else '区间购电量 / kWh',shrink=.85)
                save(fig,name)
        if 'q2_point' in daily and 'q2_margin' in daily:
            diff=daily['q2_point'].total_fee-daily['q2_margin'].total_fee
            fig,ax=plt.subplots(figsize=(160/25.4,80/25.4),layout='constrained')
            ax.plot(diff.index,diff.cumsum()/1e4,color='#0072B2',linewidth=1.8)
            ax.axhline(0,color='#555555',linewidth=.8)
            ax.set(xlim=(diff.index.min(),diff.index.max()),ylabel='累计节省费用 / 万元',xlabel='2025年日期',title='第二问：校准裕量相对点预测的累计费用差')
            ax.grid(alpha=.2)
            save(fig,'q2_cumulative_saving')
            pd.DataFrame({'date':diff.index,'saving_yuan':diff.values,'cumulative_saving_yuan':diff.cumsum().values}).to_csv(dest/'paired_daily_cost.csv',index=False)
    (dest/'manifest.json').write_text(json.dumps(dict(source_run=args.run,files=generated,
           transformations='daily sums; fees /10000; interval arrays reshaped 334x144; no smoothing or exclusions',
           boundary='day-ahead causal plans; idealized within-interval feedback; terminal states not forced equal'),ensure_ascii=False,indent=2)+'\n')
    print(f'Saved {len(generated)} figure files')


if __name__=='__main__':main()
