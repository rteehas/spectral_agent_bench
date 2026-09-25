#!/usr/bin/env python3
"""Create task-specific scientific diagnostics from saved candidate predictions."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

ELEMENTS=['Ti','V','Cr','Mn','Fe','Co','Ni','Cu']

def write_csv(path, rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def summarize(folder):
    result=json.loads((folder/'result.json').read_text())
    q=result['question']; models=result['models']
    with (folder/'predictions.csv').open() as f: predictions=list(csv.DictReader(f))
    with (folder/'importances.csv').open() as f: importances=list(csv.DictReader(f))
    metadata=json.loads((folder/'feature_metadata.json').read_text())
    avg_imp={}
    for m in models:
        a=np.array([[float(r['importance']) for r in importances if r['model_id']==m['id'] and int(r['seed'])==s] for s in m['seeds']])
        avg_imp[m['id']]=a.mean(axis=0)
    lines=[f'# {q}: fixed-holdout research result','',
           'Means and standard deviations summarize three random-forest seeds on the same spectral-record split. '
           'They measure forest randomness, not uncertainty across new compounds, splits, or experimental spectra.','']
    comparisons=[]; ranked=[]; families=[]
    for m in models:
        if m['representation']!='poly':continue
        imp=avg_imp[m['id']]; meta=metadata[m['element']+'_poly']
        for rank,idx in enumerate(np.argsort(-imp)[:12],1):
            ranked.append(dict(model_id=m['id'],rank=rank,importance=float(imp[idx]),**meta[idx]))
        family={f'degree_{d}':float(sum(imp[i] for i,v in enumerate(meta) if v['degree']==d)) for d in range(4)}
        families.append(dict(model_id=m['id'],**family,peak=float(imp[-1]),peak_rank=int(np.flatnonzero(np.argsort(-imp)==len(imp)-1)[0]+1)))
    if ranked:
        write_csv(folder/'ranked_features.csv',ranked);write_csv(folder/'coefficient_families.csv',families)
    if q=='Q1':
        fig,axes=plt.subplots(2,4,figsize=(13,6));conf=[]
        for e,ax in zip(ELEMENTS,axes.flat):
            a,b=[m for m in models if m['element']==e]
            row=dict(element=e,delta_macro_f1=b['metrics_mean']['macro_f1']-a['metrics_mean']['macro_f1'],
                     accuracy_gain_over_mode=b['metrics_mean']['accuracy']-b['baseline']['accuracy'])
            comparisons.append(row)
            mat=np.zeros((3,3))
            for p in predictions:
                if p['model_id']==b['id']:mat[int(float(p['y_true']))-4,int(float(p['y_pred']))-4]+=1/len(b['seeds'])
            for i in range(3):
                for j in range(3):conf.append(dict(element=e,true_class=i+4,predicted_class=j+4,mean_count=mat[i,j]))
            ax.imshow(mat,cmap='Blues');ax.set(title=e,xticks=range(3),xticklabels=[4,5,6],yticks=range(3),yticklabels=[4,5,6],xlabel='Predicted',ylabel='True')
            for i in range(3):
                for j in range(3):ax.text(j,i,f'{mat[i,j]:.1f}',ha='center',va='center',fontsize=8)
            minority=min(b['baseline']['train_class_counts'],key=b['baseline']['train_class_counts'].get)
            lines.append(f'{e}: training minority class CN={minority}; balanced accuracy {b["metrics_mean"]["accuracy"]:.3f} '
                         f'versus mode baseline {b["baseline"]["accuracy"]:.3f}; minority F1 {b["metrics_mean"]["f1_"+minority]:.3f}; '
                         f'oversampling changes macro-F1 by {row["delta_macro_f1"]:+.4f}.')
        write_csv(folder/'confusion.csv',conf)
        improved=sum(r['delta_macro_f1']>0 for r in comparisons)
        lines.insert(3,f'Balanced spectral models exceed the training-mode accuracy baseline for {sum(r["accuracy_gain_over_mode"]>0 for r in comparisons)}/8 elements. '
                     f'Oversampling improves macro-F1 for {improved}/8 elements, with mean paired change {np.mean([r["delta_macro_f1"] for r in comparisons]):+.4f}.')
        lines.append('Assess minority-class F1 and confusion together: a high total accuracy alone does not establish balanced class resolution. Oversampling benefits are element dependent.')
    elif q in ['Q2','Q3']:
        fig,axes=plt.subplots(2,4,figsize=(13,6))
        for e,ax in zip(ELEMENTS,axes.flat):
            selected=[m for m in models if m['element']==e]
            m=selected[0];pp=[p for p in predictions if p['model_id']==m['id'] and int(p['seed'])==42]
            y=np.array([float(p['y_true']) for p in pp]);p=np.array([float(p['y_pred']) for p in pp])
            ax.scatter(y,p,s=6,alpha=.45);lim=[min(y.min(),p.min()),max(y.max(),p.max())];ax.plot(lim,lim,'k--',lw=1)
            ax.set(title=e,xlabel='Label (Å)' if q=='Q2' else 'Charge label',ylabel='Prediction (Å)' if q=='Q2' else 'Charge prediction')
            k=m['metrics_mean']
            if q=='Q2':
                lines.append(f'{e}: R²={k["r2"]:.3f}, MAE={k["mae"]:.5f} Å '
                             f'(training-mean baseline R²={m["baseline"]["r2"]:.3f}, MAE={m["baseline"]["mae"]:.5f} Å). '
                             f'Low/high training-quantile tail MAE={k["low_mae"]:.5f}/{k["high_mae"]:.5f} Å; '
                             f'signed bias={k["low_bias"]:+.5f}/{k["high_bias"]:+.5f} Å '
                             f'(n={int(k["low_count"])}/{int(k["high_count"])} test spectra).')
            else:
                b=selected[1]
                row=dict(element=e,delta_r2=k['r2']-b['metrics_mean']['r2'],mae_reduction=b['metrics_mean']['mae']-k['mae'])
                comparisons.append(row)
                lines.append(f'{e}: full-spectrum R²={k["r2"]:.3f}, peak-only R²={b["metrics_mean"]["r2"]:.3f}; '
                             f'full-spectrum MAE={k["mae"]:.4f}, peak-only MAE={b["metrics_mean"]["mae"]:.4f} charge units '
                             f'(training-mean baseline R²={m["baseline"]["r2"]:.3f}, MAE={m["baseline"]["mae"]:.4f}).')
        if q=='Q2':
            lines.insert(3,f'Full-spectrum models beat the training-mean baseline MAE for {sum(m["metrics_mean"]["mae"]<m["baseline"]["mae"] for m in models)}/8 elements. '
                         f'High-tail MAE exceeds overall MAE for {sum(m["metrics_mean"]["high_mae"]>m["metrics_mean"]["mae"] for m in models)}/8; '
                         f'low-tail MAE does so for {sum(m["metrics_mean"]["low_mae"]>m["metrics_mean"]["mae"] for m in models)}/8.')
            lines.append('Positive low-tail and negative high-tail residuals indicate regression toward common distances where observed. Quantile boundaries were estimated on training labels only.')
        else:
            lines.insert(3,f'The full spectrum improves R² over peak position alone for {sum(r["delta_r2"]>0 for r in comparisons)}/8 elements. '
                         f'The mean paired R² gain is {np.mean([r["delta_r2"] for r in comparisons]):.3f}; the mean MAE reduction is {np.mean([r["mae_reduction"] for r in comparisons]):.4f} charge units.')
            lines.append('The paired full-versus-peak comparison estimates additional predictive information under this model and holdout. It is not a causal test or a measurement of formal oxidation states.')
    elif q=='Q4':
        fig,axes=plt.subplots(8,3,figsize=(16,22))
        colors=['#4575b4','#91bfdb','#fc8d59','#d73027']
        for i,e in enumerate(ELEMENTS):
            for j,t in enumerate(['coord','md','bader']):
                a,b=[m for m in models if m['element']==e and m['target']==t]
                metric='macro_f1' if t=='coord' else 'r2'
                comparisons.append(dict(element=e,target=t,metric=metric,pointwise=a['metrics_mean'][metric],poly=b['metrics_mean'][metric],delta=b['metrics_mean'][metric]-a['metrics_mean'][metric]))
                top=[r for r in ranked if r['model_id']==b['id']][:6];ax=axes[i,j]
                for k,r in enumerate(top):
                    if r['label']=='peak':
                        ax.text(.5,k,'white-line index',transform=ax.get_yaxis_transform(),ha='center',va='center',fontsize=8)
                        continue
                    ax.plot([r['energy_lo'],r['energy_hi']],[k,k],lw=max(2,r['importance']*70),c=colors[r['degree']])
                ax.set(title=f'{e} {t}',xlabel='Energy (eV)',yticks=range(len(top)),yticklabels=[f'#{r["rank"]}: '+('peak' if r['degree']==-1 else f'a{r["degree"]}') for r in top]);ax.invert_yaxis()
                top0=top[0]
                family=next(r for r in families if r['model_id']==b['id'])
                location=('the white-line index descriptor (argmax over the full domain)' if top0['label']=='peak' else
                          f'{top0["label"]} at {top0["energy_lo"]:.2f}–{top0["energy_hi"]:.2f} eV')
                lines.append(f'{e} {t}: polynomial minus pointwise {metric}={comparisons[-1]["delta"]:+.4f}; '
                             f'top feature {location}; '
                             f'constant/linear/quadratic/cubic importance totals '+ '/'.join(f'{family[f"degree_{d}"]:.3f}' for d in range(4))+'.')
        lines.append('The feature intervals show where the model allocates predictive importance; coefficient degrees distinguish magnitude and shape. Overlapping descriptors are correlated, so this ranking is not a unique physical decomposition.')
        for t in ['coord','md','bader']:
            paired=[r for r in comparisons if r['target']==t]
            related=[r for r in families if '_'+t+'_' in r['model_id']]
            means=[np.mean([r[f'degree_{d}'] for r in related]) for d in range(4)]
            lines.insert(3,f'{t}: mean polynomial-minus-pointwise score change {np.mean([r["delta"] for r in paired]):+.4f}; '
                         f'largest absolute element-level change {max(abs(r["delta"]) for r in paired):.4f}. '
                         f'Average coefficient-family importance (a0/a1/a2/a3) is '+ '/'.join(f'{v:.3f}' for v in means)+
                         f'; the largest family is a{int(np.argmax(means))}. Energy locations vary by element and are listed below.')
    else:
        fig,axes=plt.subplots(8,2,figsize=(12,20))
        for i,e in enumerate(ELEMENTS):
            for j,t in enumerate(['coord','md']):
                for rep in ['pointwise','poly']:
                    a,b=[m for m in models if m['element']==e and m['target']==t and m['representation']==rep]
                    x,y=avg_imp[a['id']],avg_imp[b['id']]
                    metric='macro_f1' if t=='coord' else 'r2'
                    overlap=len(set(np.argsort(-x)[:12])&set(np.argsort(-y)[:12]))/len(set(np.argsort(-x)[:12])|set(np.argsort(-y)[:12]))
                    row=dict(element=e,target=t,representation=rep,metric=metric,delta=b['metrics_mean'][metric]-a['metrics_mean'][metric],importance_spearman=float(spearmanr(x,y).statistic),top12_jaccard=overlap)
                    comparisons.append(row)
                    lines.append(f'{e} {t} {rep}: max minus supplied normalization {metric}={row["delta"]:+.4f}; '
                                 f'importance rank correlation={row["importance_spearman"]:.3f}; top-12 Jaccard={overlap:.3f}.')
                    if rep=='pointwise':
                        ax=axes[i,j];energy=[v['energy_lo'] for v in metadata[e+'_pointwise']]
                        ax.plot(energy,x,label='Supplied');ax.plot(energy,y,label='Maximum');ax.set(title=f'{e} {t}',xlabel='Energy (eV)',ylabel='Importance');ax.legend(fontsize=7)
        lines.append('Similar prediction scores can coexist with changing attribution. Rank correlation and overlap quantify stability within a representation; correlated features and impurity bias limit causal interpretation.')
        for t in ['coord','md']:
            for rep in ['pointwise','poly']:
                rows=[r for r in comparisons if r['target']==t and r['representation']==rep]
                unstable=min(rows,key=lambda r:r['importance_spearman'])
                lines.insert(3,f'{t}/{rep}: normalization changes the score by {min(r["delta"] for r in rows):+.4f} to {max(r["delta"] for r in rows):+.4f}; '
                             f'importance rank correlations range {min(r["importance_spearman"] for r in rows):.3f}–{max(r["importance_spearman"] for r in rows):.3f}. '
                             f'{unstable["element"]} has the lowest rank stability (score change {unstable["delta"]:+.4f}, top-12 overlap {unstable["top12_jaccard"]:.3f}).')
            feff=[r for r in families if '_'+t+'_' in r['model_id'] and '_feff_' in r['model_id']]
            maxn=[r for r in families if '_'+t+'_' in r['model_id'] and '_max_' in r['model_id']]
            shifts=[np.mean([r[f'degree_{d}'] for r in maxn])-np.mean([r[f'degree_{d}'] for r in feff]) for d in range(4)]
            lines.insert(3,f'{t}: mean maximum-minus-supplied changes in polynomial family importance (a0/a1/a2/a3) are '+ '/'.join(f'{v:+.3f}' for v in shifts)+'.')
    fig.tight_layout();fig.savefig(folder/'diagnostics.png',dpi=120);plt.close(fig)
    if comparisons:write_csv(folder/'comparisons.csv',comparisons)
    (folder/'conclusion.md').write_text('\n\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
    summarize(a.output)
