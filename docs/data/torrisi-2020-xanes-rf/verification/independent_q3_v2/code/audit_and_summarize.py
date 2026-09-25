#!/usr/bin/env python3
"""Audit all required run artifacts; calculate a multiplicity-aware primary sensitivity."""
import argparse,json,gzip
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.metrics import mean_absolute_error,r2_score

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();o=a.output
    d=json.loads((o/'design.json').read_text()); preds=pd.read_csv(o/'predictions.csv');parts=pd.read_csv(o/'partitions.csv');met=pd.read_csv(o/'metrics.csv');runs=pd.DataFrame(d['runs'])
    assert d['question']=='Q3'
    assert not preds.duplicated(['run_id','source_row']).any()
    assert not parts.duplicated(['run_id','source_row']).any()
    assert set(runs.run_id)==set(preds.run_id)==set(parts.run_id)==set(met.run_id)
    sources={}
    for el in runs.element.unique():
        with gzip.open(a.inputs/f'{el}.jsonl.gz','rt') as f: sources[el]={r['source_row']:r for r in map(json.loads,f)}
    for r in d['runs']:
        rid=r['run_id'];s=sources[r['element']];pa=parts[parts.run_id==rid].set_index('source_row');pr=preds[preds.run_id==rid].set_index('source_row')
        assert set(pa.index)==set(s)
        assert set(pa.role)<=set(['train','validation','test','excluded'])
        assert set(pr.index)==set(pa[pa.role=='test'].index)
        assert np.isfinite(pr.y_pred).all()
        yy=[s[i]['bader'] for i in pr.index]
        for k,v in {'mae':mean_absolute_error(yy,pr.y_pred),'r2':r2_score(yy,pr.y_pred)}.items():
            recorded=met[(met.run_id==rid)&(met.metric==k)].value.item();assert np.isclose(v,recorded,atol=1e-12)
        assert all(s[i]['bader'] is not None for i in pa[pa.role!='excluded'].index)
        if r['generalization']=='identified_material':
            groups={role:set(s[i]['metadata'].get('id','') for i in pa[pa.role==role].index) for role in ['train','validation','test']}
            assert all('' not in x for x in groups.values())
            assert not(groups['train']&groups['validation'] or groups['train']&groups['test'] or groups['validation']&groups['test'])
    for cid,g in runs.groupby('comparison_id'):
        assert len(g)==2 and set(g.condition)=={'white_line','full'}
        p1=parts[parts.run_id==g.run_id.iloc[0]].set_index('source_row').role.sort_index();p2=parts[parts.run_id==g.run_id.iloc[1]].set_index('source_row').role.sort_index();assert p1.equals(p2)
    overlap=[]
    for r in d['runs']:
        if r['generalization']!='spectrum' or r['condition']!='full': continue
        pa=parts[parts.run_id==r['run_id']];ss=sources[r['element']]
        trained=set(ss[i]['metadata'].get('id','') for i in pa[pa.role.isin(['train','validation'])].source_row)-{''}
        testrows=pa[pa.role=='test'].source_row.to_numpy()
        idtest=np.array([ss[i]['metadata'].get('id','') for i in testrows])
        overlap.append(dict(run_id=r['run_id'],element=r['element'],study=r['study'],n_test=len(testrows),n_test_identified=int(sum(idtest!='')),n_test_id_in_train_or_validation=int(sum(np.isin(idtest,list(trained)))),fraction_test_known_overlap=float(np.mean(np.isin(idtest[idtest!=''],list(trained))))))
    pd.DataFrame(overlap).to_csv(o/'spectrum_overlap.csv',index=False)
    # Fixed first split, Bonferroni alpha=.05/8 over eight per-element comparisons.
    corrected=[]
    for el in runs.element.unique():
        dd=pd.read_csv(o/'diagnostics'/f'{el}_primary_1729.csv')
        dd['delta']=np.abs(dd.bader-dd.pred_white_line)-np.abs(dd.bader-dd.pred_full)
        z=dd.groupby('material_id').delta.mean().to_numpy();rng=np.random.default_rng(918273)
        boot=[]
        for j in range(40): boot.extend(z[rng.integers(len(z),size=(500,len(z)))].mean(axis=1))
        lo,hi=np.quantile(boot,[.003125,.996875])
        corrected.append(dict(element=el,seed=1729,n_materials=len(z),delta=float(z.mean()),bonferroni_99_375_low=lo,bonferroni_99_375_high=hi,n_bootstrap=20000))
    pd.DataFrame(corrected).to_csv(o/'first_split_multiplicity.csv',index=False)
    report={'status':'PASS','n_runs':len(runs),'n_comparisons':runs.comparison_id.nunique(),'n_predictions':len(preds),'n_partition_rows':len(parts),'checks':['one partition role for every source record per run','one finite prediction per test record and no others','metrics exactly recomputed from released Bader labels','paired conditions have identical inclusion and train/validation/test/excluded assignments','material identifiers disjoint across train, validation and test','no missing Bader values enter fitting or scoring','only full/white_line and target bader declared']}
    assert set(runs.target)=={'bader'} and set(runs.condition)=={'full','white_line'}
    (o/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    primary=pd.read_csv(o/'comparisons.csv');primary=primary[primary.study=='primary']
    print('\nPrimary (equal-material MAE and error reduction, e):')
    print(primary.groupby('element').agg(wl=('mae_white_material','mean'),full=('mae_full_material','mean'),delta=('delta_material','mean'),min_delta=('delta_material','min'),max_delta=('delta_material','max'),min_ci_low=('ci_low','min')).round(5).to_string())
    print('\nFirst-split multiplicity intervals:');print(pd.DataFrame(corrected).round(5).to_string(index=False))
if __name__=='__main__':main()
