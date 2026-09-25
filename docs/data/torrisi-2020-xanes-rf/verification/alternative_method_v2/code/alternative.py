#!/usr/bin/env python3
"""Independent alternative Q2 experiment; no candidate/verifier imports."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error,r2_score
from sklearn.model_selection import GroupShuffleSplit

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    runs=[];predictions=[];partitions=[];metrics=[];tails=[];results=[]
    for el in ['Ti','V','Cr','Mn','Fe','Co','Ni','Cu']:
        with gzip.open(args.inputs/(el+'.jsonl.gz'),'rt') as stream:
            rows=[json.loads(line) for line in stream]
        eligible=[r for r in rows if r['metadata'].get('id') and r['coordination'] in [4,5,6]
                  and r['avg_nn_dists'] is not None and np.isfinite(r['avg_nn_dists'])
                  and np.isfinite(r['mu']).all() and max(r['mu'])>0]
        rawx=np.asarray([r['mu'] for r in eligible]);y=np.asarray([r['avg_nn_dists'] for r in eligible])
        # Fixed spectral-only transform, no fitting and no metadata predictors.
        x=np.concatenate([rawx[:,::3],np.diff(rawx,axis=1)[:,::3]],axis=1)
        ids=np.asarray([r['metadata']['id'] for r in eligible])
        develop,test=next(GroupShuffleSplit(n_splits=1,test_size=.27,random_state=701).split(x,y,ids))
        localtrain,localvalid=next(GroupShuffleSplit(n_splits=1,test_size=.18,random_state=702).split(x[develop],y[develop],ids[develop]))
        train,valid=develop[localtrain],develop[localvalid]
        model=ExtraTreesRegressor(n_estimators=23,max_depth=14,min_samples_leaf=3,max_features=.6,random_state=703,n_jobs=2)
        model.fit(x[train],y[train]);p=model.predict(x[test]);name=el+'_alternative'
        assignment={r['source_row']:'excluded' for r in rows}
        for role,indices in [('train',train),('validation',valid),('test',test)]:
            for i in indices:assignment[eligible[i]['source_row']]=role
        partitions.extend(dict(run_id=name,source_row=i,role=role) for i,role in assignment.items())
        predictions.extend(dict(run_id=name,source_row=eligible[i]['source_row'],y_pred=float(v)) for i,v in zip(test,p))
        scores=dict(mae=float(mean_absolute_error(y[test],p)),r2=float(r2_score(y[test],p)))
        metrics.extend(dict(run_id=name,metric=k,value=v) for k,v in scores.items())
        baseline=np.full(len(test),float(np.mean(y[train])))
        cutoffs=np.quantile(y[train],[.1,.9])
        for region,mask,threshold in [('short',y[test]<=cutoffs[0],cutoffs[0]),('long',y[test]>=cutoffs[1],cutoffs[1])]:
            error=p[mask]-y[test][mask]
            tails.append(dict(run_id=name,region=region,threshold=float(threshold),count=int(mask.sum()),
                              mae=float(np.abs(error).mean()),bias=float(error.mean()),
                              mean_baseline_mae=float(np.abs(baseline[mask]-y[test][mask]).mean())))
        runs.append(dict(run_id=name,element=el,target='md',condition='model',comparison_id=el+'_holdout',generalization='identified_material'))
        results.append(dict(element=el,test_count=len(test),**scores,baseline_mae=float(mean_absolute_error(y[test],baseline))))
    for name,values in [('predictions',predictions),('partitions',partitions),('metrics',metrics),('tails',tails)]:
        pd.DataFrame(values).to_csv(out/(name+'.csv'),index=False)
    design=dict(question='Q2',runs=runs,method='ExtraTreesRegressor',parameters=dict(n_estimators=23,max_depth=14,min_samples_leaf=3,max_features=.6,random_state=703),
                eligibility='Known material ID, coordination in 4/5/6, finite distance/spectrum, positive spectral maximum.',
                features='Every third raw absorption sample concatenated with every third adjacent absorption difference; no learned transform.',
                split='GroupShuffleSplit by metadata.id, 27% groups test with seed 701; 18% remaining groups validation with seed 702.',
                tails='Training-distance 10th and 90th percentiles, separately by element.',
                reproduce_command='python code/alternative.py --inputs INPUT_DIRECTORY --output NEW_OUTPUT_DIRECTORY')
    (out/'design.json').write_text(json.dumps(design,indent=2)+'\n')
    summary=pd.DataFrame(results)
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(summary.element,summary.mae,label='spectral model')
    ax.plot(summary.element,summary.baseline_mae,'o--',label='training mean')
    ax.set_ylabel('Held-out identified-material MAE (angstrom)');ax.legend();fig.tight_layout();fig.savefig(out/'errors.png');plt.close(fig)
    lines=['# Alternative distance investigation','',
           'This independent experiment uses ExtraTrees and downsampled intensities plus discrete spectral differences. It keeps known material IDs disjoint, chooses a different split and model budget, and includes all finite spectra with positive maxima; no archived preprocessing or predictions are used. Parameters were fixed before evaluating test performance. Validation rows are reserved but unused by this fixed-parameter audit experiment.','',
           'Only identified records are analyzed. All such records have origin=scrape; this experiment cannot establish generalization to origin=feff or unidentified materials. Material identifiers do not resolve aliases or structural similarity. This single grouped holdout is an audit of numerical flexibility, not a complete uncertainty study or a benchmark-passing research answer.','',
           'The training-mean baseline and short/long cohorts use training labels only. Tail signed bias is prediction minus raw distance. The independent audit recomputes these quantities directly from the raw records.','',summary.to_csv(index=False),'',pd.DataFrame(tails).to_csv(index=False)]
    (out/'report.md').write_text('\n'.join(lines))
if __name__=='__main__':main()
