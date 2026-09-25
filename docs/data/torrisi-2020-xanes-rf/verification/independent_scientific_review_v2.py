#!/usr/bin/env python3
"""Independent raw-label, paired-effect, and selected model/attribution probes.

This is evaluator evidence for the particular worked solution, not constraints
on other submissions. No functions are imported from candidate.py.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesClassifier,ExtraTreesRegressor
from sklearn.metrics import f1_score

FIELDS={'coord':'coordination','md':'avg_nn_dists','bader':'bader'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read_raw(inputs,element):
    with gzip.open(inputs/(element+'.jsonl.gz'),'rt') as f:return [json.loads(s) for s in f]
def loss(y,p,target):
    if target!='coord':return np.abs(y-p).mean()
    counts=np.array([[np.sum((y==a)&(p==b)) for b in [4,5,6]] for a in [4,5,6]])
    denom=counts.sum(0)+counts.sum(1)
    return 1-np.divide(2*np.diag(counts),denom,out=np.zeros(3),where=denom!=0).mean()
def paired(y,p0,p1,groups,target):
    unique=np.unique(groups);members=[np.where(groups==g)[0] for g in unique]
    rng=np.random.default_rng(101);draws=[]
    for _ in range(250):
        selected=np.concatenate([members[i] for i in rng.integers(len(unique),size=len(unique))])
        draws.append(loss(y[selected],p0[selected],target)-loss(y[selected],p1[selected],target))
    return [loss(y,p0,target)-loss(y,p1,target),*np.quantile(draws,[.025,.975]),len(unique)]

def check_example(question,root,inputs):
    folder=root/question;design=json.loads((folder/'design.json').read_text());roster=design['runs']
    predictions=pd.read_csv(folder/'predictions.csv');partitions=pd.read_csv(folder/'partitions.csv');comparisons=pd.read_csv(folder/'comparisons.csv')
    raw={el:read_raw(inputs,el) for el in sorted({r['element'] for r in roster})};rawmap={el:{r['source_row']:r for r in rows} for el,rows in raw.items()}
    pair_checks=[]
    for cid,runs in pd.DataFrame(roster).groupby('comparison_id'):
        record=comparisons[comparisons.comparison_id==cid].iloc[0]
        ordered=[runs[runs.condition==c].iloc[0] for c in [record['first'],record['second']]]
        frames=[predictions[predictions.run_id==r.run_id].set_index('source_row').sort_index() for r in ordered]
        assert frames[0].index.equals(frames[1].index)
        r=ordered[0];source=rawmap[r.element];ids=frames[0].index.to_numpy()
        y=np.array([source[int(i)][FIELDS[r.target]] for i in ids]);groups=np.array([source[int(i)]['metadata']['id'] for i in ids])
        actual=paired(y,frames[0].y_pred.to_numpy(),frames[1].y_pred.to_numpy(),groups,r.target)
        np.testing.assert_allclose(actual,[record.gain,record.low,record.high,record.bootstrap_units],rtol=0,atol=1e-12)
        pair_checks.append(dict(comparison_id=cid,gain=float(actual[0]),low=float(actual[1]),high=float(actual[2])))
    probes=[('Fe','bader')] if question=='Q3' else [('Ti','coord'),('Ni','md')]
    probes_out=[];localizations=json.loads((folder/'localization.json').read_text())
    for el,target in probes:
        for run in [r for r in roster if r['element']==el and r['target']==target and r['repeat']==0 and r['fit_seed']==113]:
            rows=raw[el];X=np.asarray([r['mu'] for r in rows]);E=np.asarray(rows[0]['E']);y=np.array([np.nan if r[FIELDS[target]] is None else r[FIELDS[target]] for r in rows])
            index={r['source_row']:i for i,r in enumerate(rows)};part=partitions[partitions.run_id==run['run_id']]
            train=np.array([index[i] for i in part.loc[part.role=='train','source_row']]);val=np.array([index[i] for i in part.loc[part.role=='validation','source_row']]);test=np.array([index[i] for i in part.loc[part.role=='test','source_row']])
            Z=E[X.argmax(axis=1)][:,None] if run['condition']=='white_line' else X/X.max(axis=1,keepdims=True) if run['condition']=='unit_peak' else X
            cls=ExtraTreesClassifier if target=='coord' else ExtraTreesRegressor;models=[]
            for leaf in [1,5]:
                model=cls(n_estimators=80,min_samples_leaf=leaf,max_features=.8,random_state=113,n_jobs=2).fit(Z[train],y[train])
                models.append((loss(y[val],model.predict(Z[val]),target),leaf,model))
            validation,leaf,model=min(models,key=lambda t:t[0]);assert leaf==run['selected_min_samples_leaf']
            expected=predictions[predictions.run_id==run['run_id']].set_index('source_row').loc[[rows[i]['source_row'] for i in test]].y_pred.to_numpy()
            actual=model.predict(Z[test]);np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-12)
            max_localization_error=None
            if question=='Q5':
                rng=np.random.default_rng(113);edges=np.linspace(E.min(),E.max(),6);baseline=loss(y[test],actual,target);errors=[]
                for region in range(5):
                    cols=np.where((E>=edges[region])&((E<edges[region+1]) if region<4 else (E<=edges[region+1])))[0];effects=[]
                    for _ in range(3):
                        modified=Z[test].copy();perm=rng.permutation(len(test));modified[:,cols]=modified[perm[:,None],cols]
                        effects.append(loss(y[test],model.predict(modified),target)-baseline)
                    stored=next(d for d in localizations if d['run_id']==run['run_id'] and d['region']==region)
                    assert cols.tolist()==stored['features'];np.testing.assert_allclose([np.mean(effects),np.std(effects)],[stored['loss_increase'],stored['permutation_sd']],rtol=0,atol=1e-12)
                    errors.extend([abs(np.mean(effects)-stored['loss_increase']),abs(np.std(effects)-stored['permutation_sd'])])
                max_localization_error=float(max(errors))
            probes_out.append(dict(run_id=run['run_id'],features=int(Z.shape[1]),selected_leaf=leaf,
                                   max_prediction_error=float(np.max(np.abs(actual-expected))),max_localization_error=max_localization_error,
                                   source_row_probe=int(rows[test[0]]['source_row']),first_feature_values=Z[test[0],:5].tolist()))
    stability_checks=0
    if question=='Q5':
        evidence=json.loads((folder/'evidence.json').read_text())
        for s in evidence['localization_stability']:
            a=[l['loss_increase'] for l in localizations if l['run_id']==s['first_run']];b=[l['loss_increase'] for l in localizations if l['run_id']==s['second_run']]
            rho=spearmanr(a,b).statistic
            assert s['spearman'] is None if not np.isfinite(rho) else np.isclose(rho,s['spearman'],atol=1e-12)
            assert (np.argmax(a)==np.argmax(b))==s['top_region_same'];stability_checks+=1
    return dict(question=question,paired_intervals_reconstructed=len(pair_checks),selected_independent_raw_model_refits=probes_out,
                stability_records_reconstructed=stability_checks,code_sha256=digest(folder/'code/candidate.py'),report_sha256=digest(folder/'report.md'),
                pair_checks=pair_checks,scope='Independent arithmetic, selected model/predictor/perturbation probes, plus separate human report/code assessment. These model settings describe this submission only.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--questions',nargs='+',default=['Q3','Q5']);a=p.parse_args()
    result={q:check_example(q,a.root,a.inputs) for q in a.questions}
    (a.root/'scientific_probes_q3_q5_v2.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
