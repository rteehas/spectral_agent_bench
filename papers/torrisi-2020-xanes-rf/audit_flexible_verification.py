#!/usr/bin/env python3
"""Exercise the flexible numerical gate with independent fits and bad artifacts.

The alternative Q2 experiment below is deliberately independent of the worked
candidate. It demonstrates acceptance of legitimate methodological differences,
not a ground-truth performance threshold. Scientific decisions still require
review and rerunning submitted source.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'

ALTERNATE_SOURCE = r'''#!/usr/bin/env python3
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
'''


def verifier():
    spec = importlib.util.spec_from_file_location('flexible_verifier', DATA / 'workflows/verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_alternative(output, inputs):
    source = output / 'code/alternative.py'
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(ALTERNATE_SOURCE)
    subprocess.run([sys.executable, str(source), '--inputs', str(inputs), '--output', str(output)], check=True)


def edit_json(folder, mutate):
    path = folder / 'design.json'
    record = json.loads(path.read_text()); mutate(record)
    path.write_text(json.dumps(record))


def edit_table(folder, name, mutate):
    path = folder / (name + '.csv')
    frame = pd.read_csv(path); result = mutate(frame)
    (frame if result is None else result).to_csv(path, index=False)


def audit_alternative_diagnostics(v, folder, inputs):
    """Separate raw reconstruction, not trusting model-produced tail summaries."""
    design = json.loads((folder / 'design.json').read_text())
    partitions = pd.read_csv(folder / 'partitions.csv')
    predictions = pd.read_csv(folder / 'predictions.csv')
    tails = pd.read_csv(folder / 'tails.csv')
    count = 0
    for run in design['runs']:
        raw, _ = v.load_raw(inputs, run['element'])
        part = partitions[partitions.run_id == run['run_id']]
        train = np.array([raw[int(row)]['md'] for row in part.loc[part.role == 'train', 'source_row']])
        pred = predictions[predictions.run_id == run['run_id']]
        truth = np.array([raw[int(row)]['md'] for row in pred.source_row])
        error = pred.y_pred.to_numpy() - truth
        for region, cutoff in zip(['short', 'long'], np.quantile(train, [.1, .9])):
            record = tails[(tails.run_id == run['run_id']) & (tails.region == region)].iloc[0]
            mask = truth <= cutoff if region == 'short' else truth >= cutoff
            assert int(record['count']) == int(mask.sum())
            actual = [record['threshold'], record['mae'], record['bias'], record['mean_baseline_mae']]
            expected = [cutoff, np.abs(error[mask]).mean(), error[mask].mean(), np.abs(truth[mask]-train.mean()).mean()]
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-10)
            count += 1
    return dict(independent_raw_tail_checks=count, candidate_verifier_metrics_not_imported_for_tail_calculation=True)


def audit(runs, alternative, inputs):
    v = verifier()
    positive = []
    if runs:
        for q in v.TARGETS:
            report = v.verify(q, runs / q, inputs)
            positive.append(dict(question=q, numerical_integrity_pass=report['numerical_integrity_pass'],
                                 scientific_pass=report['scientific_pass'], status=report['status'], runs=report['run_count']))
    report = v.verify('Q2', alternative, inputs)
    assert report['scientific_pass'] is None and report['status'] == 'scientific_review_required'
    alternate_evidence = dict(method='ExtraTreesRegressor', parameters=json.loads((alternative / 'design.json').read_text())['parameters'],
                              input_hashes=report['source_input_sha256'], run_metrics=[dict(run_id=r['run_id'],**r['metrics_recomputed']) for r in report['checks']],
                              numerical_integrity_pass=True, scientific_pass=None,
                              role='Independent alternate-method integrity acceptance, not a complete scientific-answer acceptance.',
                              diagnostics=audit_alternative_diagnostics(v, alternative, inputs))
    rejects = []
    def wrong_metric(folder): edit_table(folder, 'metrics', lambda d: d.assign(value=d.value + .07))
    def missing_prediction(folder): edit_table(folder, 'predictions', lambda d: d.iloc[1:])
    def duplicate_prediction(folder): edit_table(folder, 'predictions', lambda d: pd.concat([d,d.iloc[:1]],ignore_index=True))
    def bogus_row(folder): edit_table(folder,'predictions',lambda d: d.assign(source_row=np.where(d.index==0,999999,d.source_row)))
    def missing_partition(folder): edit_table(folder,'partitions',lambda d: d.iloc[1:])
    def overlap_roles(folder):
        edit_table(folder,'partitions',lambda d: pd.concat([d,d[d.role=='test'].iloc[:1].assign(role='train')],ignore_index=True))
    def nonfinite_prediction(folder): edit_table(folder,'predictions',lambda d: d.assign(y_pred=np.where(d.index==0,np.nan,d.y_pred)))
    def fake_truth(folder): edit_table(folder,'predictions',lambda d: d.assign(y_true=0.12345))
    def out_of_scope_claim(folder): edit_json(folder,lambda d: d['runs'][0].update(generalization='spectrum'))
    def unaccounted_run(folder): edit_json(folder,lambda d: d['runs'].pop())
    def missing_code(folder): shutil.rmtree(folder/'code')
    def leaked_material(folder):
        design=json.loads((folder/'design.json').read_text());run=design['runs'][0]
        raw,_=v.load_raw(inputs,run['element'])
        p=folder/'partitions.csv';frame=pd.read_csv(p);mask=frame.run_id==run['run_id']
        subset=frame[mask];testids={raw[int(i)]['material_id'] for i in subset.loc[subset.role=='test','source_row']}
        chosen=next(i for i in subset.index if subset.loc[i,'role']=='test' and raw[int(subset.loc[i,'source_row'])]['material_id'] in testids
                    and sum(raw[int(j)]['material_id']==raw[int(subset.loc[i,'source_row'])]['material_id'] for j in subset.loc[subset.role=='test','source_row'])>1)
        frame.loc[chosen,'role']='train';frame.to_csv(p,index=False)
    controls=[('forged_core_metric',wrong_metric),('missing_test_prediction',missing_prediction),
              ('duplicate_test_prediction',duplicate_prediction),('out_of_range_raw_row',bogus_row),
              ('unaccounted_raw_row',missing_partition),('row_in_multiple_partitions',overlap_roles),
              ('nonfinite_prediction',nonfinite_prediction),('contradictory_optional_raw_truth',fake_truth),
              ('missing_required_material_scope',out_of_scope_claim),('undeclared_run',unaccounted_run),
              ('missing_reproducible_code',missing_code),('known_material_identity_leakage',leaked_material)]
    with tempfile.TemporaryDirectory(prefix='torrisi-flexible-controls-') as temp:
        temp=Path(temp)
        for label,mutate in controls:
            folder=temp/label;shutil.copytree(alternative,folder);mutate(folder)
            try:v.verify('Q2',folder,inputs)
            except (AssertionError,KeyError,ValueError,TypeError,OSError) as exc:
                rejects.append(dict(control=label,rejected=True,reason=str(exc)[:300]))
            else:raise AssertionError('Invalid control accepted: '+label)
        benign=temp/'row-order';shutil.copytree(alternative,benign)
        for name in ['predictions','partitions','metrics']:
            edit_table(benign,name,lambda d:d.sample(frac=1,random_state=819))
        assert v.verify('Q2',benign,inputs)['numerical_integrity_pass']
        # Numerically consistent fabricated predictions are a review control,
        # never a claimed negative control that this arithmetic gate detects.
        fake=temp/'target-copy';shutil.copytree(alternative,fake)
        design=json.loads((fake/'design.json').read_text());pred=pd.read_csv(fake/'predictions.csv');met=[]
        for run in design['runs']:
            raw,_=v.load_raw(inputs,run['element']);mask=pred.run_id==run['run_id']
            truth=np.array([raw[int(i)]['md'] for i in pred.loc[mask,'source_row']]);pred.loc[mask,'y_pred']=truth
            met.extend([dict(run_id=run['run_id'],metric='mae',value=0.),dict(run_id=run['run_id'],metric='r2',value=1.)])
        pred.to_csv(fake/'predictions.csv',index=False);pd.DataFrame(met).to_csv(fake/'metrics.csv',index=False)
        copied=v.verify('Q2',fake,inputs)
        assert copied['numerical_integrity_pass'] and copied['scientific_pass'] is None
        rerun=temp/'target-copy-rerun';subprocess.run([sys.executable,str(fake/'code/alternative.py'),'--inputs',str(inputs),'--output',str(rerun)],check=True)
        regenerated=pd.read_csv(rerun/'predictions.csv').sort_values(['run_id','source_row']).y_pred.to_numpy()
        original=pd.read_csv(alternative/'predictions.csv').sort_values(['run_id','source_row']).y_pred.to_numpy()
        np.testing.assert_allclose(regenerated,original,rtol=0,atol=1e-12)
        alternate_evidence['independent_source_rerun_matches']=True
        alternate_evidence['source_review']=dict(
            predictors='Only raw absorption samples and adjacent differences; no structural label, material identity, or released derived descriptor is a feature.',
            fitting='ExtraTrees fit receives x[train] and y[train]; validation unused; test predictions generated only after fit.',
            grouping='Known metadata.id supplied to GroupShuffleSplit; unknown IDs excluded. All groups checked for overlap by the independent verifier.',
            limitation='This concrete alternate demonstrates method flexibility; its single holdout is not a full uncertainty analysis.')
        fabricated=pred.sort_values(['run_id','source_row']).y_pred.to_numpy()
        mismatch=float(np.max(np.abs(regenerated-fabricated)))
        assert mismatch>0.01,'Independent rerun did not distinguish fabricated predictions'
        review_controls=[dict(control='self_consistent_target_copy',numerical_integrity_pass=True,scientific_pass=None,
                              final_review='rejected_by_independent_source_rerun',maximum_prediction_discrepancy=mismatch,
                              lesson='Arithmetic checks cannot detect fabricated predictions; source execution is a required separate gate.')]
        fake_tail=temp/'fabricated-tail';shutil.copytree(alternative,fake_tail)
        edit_table(fake_tail,'tails',lambda d:d.assign(mae=d.mae+.2))
        assert v.verify('Q2',fake_tail,inputs)['scientific_pass'] is None
        try:audit_alternative_diagnostics(v,fake_tail,inputs)
        except AssertionError:
            review_controls.append(dict(control='fabricated_freeform_tail_table',numerical_integrity_pass=True,scientific_pass=None,
                                        final_review='rejected_by_independent_raw_cohort_reconstruction',
                                        lesson='Optional diagnostic tables need method-aware independent validation; the core gate does not silently treat them as verified.'))
        else:raise AssertionError('Fabricated tail diagnostics passed independent reconstruction')
        if runs:
            # A scientifically controlled comparison may not silently alter its test/train membership.
            folder=temp/'unpaired-conditions';shutil.copytree(runs/'Q1',folder)
            design=json.loads((folder/'design.json').read_text());roster=design['runs'];first=roster[0]
            paired=next(r for r in roster if r['element']==first['element'] and r['comparison_id']==first['comparison_id'] and r['run_id']!=first['run_id'])
            path=folder/'partitions.csv';part=pd.read_csv(path);ix=part[(part.run_id==paired['run_id'])&(part.role=='train')].index[0]
            part.loc[ix,'role']='excluded';part.to_csv(path,index=False)
            try:v.verify('Q1',folder,inputs)
            except (AssertionError,KeyError,ValueError,TypeError,OSError) as exc:
                rejects.append(dict(control='unpaired_condition_membership',rejected=True,reason=str(exc)[:300]))
            else:raise AssertionError('Unpaired conditions accepted')
    archived=DATA/'verification/alternative_method_v2'
    shutil.copytree(alternative,archived,dirs_exist_ok=True)
    alternate_evidence['artifact_directory']='verification/alternative_method_v2'
    alternate_evidence['source_sha256']=v.digest(archived/'code/alternative.py')
    result=dict(version=2,verifier='workflows/verify.py',candidate_integrity_checks=positive,
                independent_alternate_method=alternate_evidence,
                benign_controls=[dict(control='CSV_row_permutation',accepted=True)],
                rejected_controls=rejects,mandatory_review_controls=review_controls,
                full_scientific_acceptance_claimed=False,
                scope='Audit of numerical gate flexibility, source provenance, material partitions, score arithmetic, and independent-rerun rejection of fabricated predictions. It does not automatically grade freeform scientific reports or optional supporting tables.')
    destination=DATA/'verification/flexible_verification_v2.json';destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',type=Path)
    parser.add_argument('--alternative',type=Path,default=Path('/tmp/torrisi-flexible-alternative-v2'))
    parser.add_argument('--inputs',type=Path,default=DATA/'inputs')
    parser.add_argument('--skip-build-alternative',action='store_true')
    args=parser.parse_args()
    if not args.skip_build_alternative:build_alternative(args.alternative,args.inputs)
    audit(args.runs,args.alternative,args.inputs)

if __name__=='__main__':main()
