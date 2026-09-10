from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'results/q2_iteration/evaluation_v4'
    data=pd.read_csv(source/'comparison.csv').set_index('strategy')
    months=pd.read_csv(source/'monthly_best_vs_old.csv')
    out=ROOT/'figures/q2_iteration';out.mkdir(exist_ok=True)
    font=next(p for p in font_manager.findSystemFonts() if p.endswith('/Arial Unicode.ttf'))
    font_manager.fontManager.addfont(font)
    style={'font.family':font_manager.FontProperties(fname=font).get_name(),'font.size':10,
           'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'path',
           'axes.spines.top':False,'axes.spines.right':False}
    files=[]
    def save(fig,name):
        fig.canvas.draw();fig.set_layout_engine(None)
        for ext in ['png','pdf','svg']:
            p=out/f'{name}.{ext}';fig.savefig(p,dpi=220,facecolor='white');files.append(str(p.relative_to(ROOT)))
        plt.close(fig)
    with plt.rc_context(style):
        fig,ax=plt.subplots(figsize=(7,4.1),layout='constrained')
        keys=['legacy_margin_reference','legacy_margin_greedy','bias_hourly_risk','policy_saa']
        labels=['原主方案','已有贪心对照','偏差＋小时保护','执行一致SAA']
        colors=['#777777','#0072B2','#009E73','#D55E00']
        markers=['s','o','D','^']
        for k,label,color,marker in zip(keys,labels,colors,markers):
            r=data.loc[k]
            ax.scatter(r.total_fee/1e6,r.emergency_kwh/1000,label=label,color=color,marker=marker,s=65)
        ax.set(xlabel='334天总费用 / 百万元',ylabel='紧急购电量 / MWh',title='第二问：费用与紧急购电的实际取舍')
        ax.grid(alpha=.18);ax.legend(loc='upper left',fontsize=9)
        save(fig,'cost_risk')
        fig,ax=plt.subplots(figsize=(7,3.8),layout='constrained')
        vals=months.saving_yuan/1000
        bars=ax.bar(months.iloc[:,0].str[5:],vals,color=['#009E73' if x>=0 else '#D55E00' for x in vals],edgecolor='#333333',linewidth=.4)
        for b,v in zip(bars,vals):
            if v<0:b.set_hatch('///')
        ax.axhline(0,color='#222222',linewidth=.8)
        ax.set(xlabel='2025年月份',ylabel='候选相对已有贪心的节省 / 千元',title='小幅全年节省并非每月都成立')
        ax.grid(axis='y',alpha=.18)
        save(fig,'monthly_saving')
    (out/'manifest.json').write_text(json.dumps(dict(source=str(source.relative_to(ROOT)),files=files,
        transforms='fees/1e6, emergency/1000, monthly savings/1000; no smoothing or exclusions',
        claim='retrospective comparison; nonzero scatter x-axis encodes position; monthly bars start at zero'),ensure_ascii=False,indent=2)+'\n')
    print('Wrote 6 figure files')


if __name__=='__main__':main()
