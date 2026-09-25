#!/usr/bin/env python3
"""Independent numerical audit of the known-target Q5 worked investigation.

This script follows that worked answer's documented numerical choices. It is not
an acceptance test for arbitrary discovery submissions and imports no candidate
functions. It cannot establish independent discovery or novelty.
"""
import argparse
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/data/szymanski-2024-xrd-pdf'
CHEMS=['Li-La-Zr-O','Li-Ti-P-O']


def read_csv(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def unit(x):return x/np.maximum(np.sqrt(np.sum(x*x,axis=-1,keepdims=True)),1e-30)


def audit(output):
    output=Path(output)
    design=json.loads((output/'design.json').read_text())
    roles={row['id']:row['role'] for row in read_csv(output/'splits.csv')}
    with np.load(output/'evidence.npz',allow_pickle=False) as archive:
        evidence={key:archive[key].copy() for key in archive.files}
    theta,r=evidence['theta'],evidence['r'];q=4*np.pi*np.sin(theta*np.pi/360)/1.5406
    assert np.all(np.diff(theta)>0) and np.all(np.diff(r)>0)
    expected_ids=[];raw_by_chem={}
    for chemistry in CHEMS:
        rows=json.loads((DATA/'inputs'/f'{chemistry}_1-Phase.json').read_text())
        with np.load(DATA/'inputs'/f'{chemistry}_1-Phase.npz',allow_pickle=False) as archive:
            values=np.stack([np.interp(theta,archive['theta'],archive[row['id']]) for row in rows])
        values-=np.quantile(values,.1,axis=1)[:,None]
        values/=np.maximum(np.max(values,axis=1)[:,None],1e-30)
        labels=np.array([row['phases'][0] for row in rows]);role=np.array([roles[row['id']] for row in rows])
        raw_by_chem[chemistry]=(rows,values,labels,role)
        expected_ids.extend([row['id'] for row in rows if roles[row['id']]=='test'][:12])
    assert list(map(str,evidence['ids']))==expected_ids
    expected_clean=np.concatenate([values[role=='test'][:12] for rows,values,labels,role in raw_by_chem.values()])
    np.testing.assert_allclose(evidence['clean_xrd'],expected_clean,rtol=1e-12,atol=1e-12)
    conditions=read_csv(output/'conditions.csv');names=list(map(str,evidence['conditions']))
    assert names==[row['condition'] for row in conditions if row['condition']!='baseline']
    perturbation_max=0.
    def added(values,name,seed):
        if name=='baseline':return values.copy()
        family,amplitude,*_=name.split('_');amplitude=float(amplitude)
        if family=='noise':delta=np.random.default_rng(seed).standard_normal(values.shape)*amplitude
        else:delta=amplitude*np.exp(-np.square(theta-35)/(2*12**2))
        return values+delta
    for j,name in enumerate(names):
        cindex=next(i for i,row in enumerate(conditions) if row['condition']==name)
        expected=[]
        for chemindex,(rows,values,labels,role) in enumerate(raw_by_chem.values()):
            expected.append(added(values[role=='test'],name,design['seed']+chemindex*10000+2000+cindex*10)[:12])
        expected=np.concatenate(expected)
        np.testing.assert_allclose(evidence['perturbed_xrd'][j],expected,rtol=1e-12,atol=1e-12)
        perturbation_max=max(perturbation_max,float(np.max(np.abs(evidence['perturbed_xrd'][j]-expected))))
    # Direct adjacent-point integration is independent of the candidate's
    # preweighted transform matrix, including its handling of nonuniform Q.
    def direct_transform(values):
        result=np.empty((len(values),len(r)))
        for start in range(0,len(r),32):
            radii=r[start:start+32]
            y=values[:,None,:]*q[None,None,:]*np.sin(radii[None,:,None]*q[None,None,:])
            result[:,start:start+len(radii)]=np.sum((y[:,:,1:]+y[:,:,:-1])*np.diff(q)[None,None,:],axis=-1)/np.pi
        return result
    max_transform=0.
    for values,observed in [(expected_clean,evidence['clean_pdf']),*zip(evidence['perturbed_xrd'],evidence['perturbed_pdf'])]:
        expected=direct_transform(values)
        np.testing.assert_allclose(observed,expected,rtol=1e-9,atol=1e-9)
        max_transform=max(max_transform,float(np.max(np.abs(observed-expected))))
    # Derive the same mathematical linear operator by adding each trapezoid's
    # separate left and right endpoint contributions, for full validation sets.
    f=np.sin(np.outer(r,q))*q
    operator=np.zeros_like(f)
    operator[:,:-1]+=f[:,:-1]*np.diff(q)[None,:]/np.pi
    operator[:,1:]+=f[:,1:]*np.diff(q)[None,:]/np.pi
    localization=read_csv(output/'validation_localization.csv')
    ablations=read_csv(output/'validation_ablation.csv')
    weak=read_csv(output/'training_pair_diagnostics.csv')
    localization_checked=ablations_checked=weak_checked=0
    expected_ablation_ids=[];expected_strong=[];expected_weak=[];expected_random=[];expected_ablation_clean=[]
    for chemindex,(chemistry,(rows,values,labels,role)) in enumerate(raw_by_chem.items()):
        tr,va=role=='train',role=='validation';clean=values[va];pdf=clean@operator.T
        valx={row['condition']:added(clean,row['condition'],design['seed']+chemindex*10000+1000+i*10) for i,row in enumerate(conditions)}
        for record in [row for row in localization if row['chemistry']==chemistry]:
            _,lo,hi=record['window'].split('_');lo,hi=float(lo),float(hi)
            mask=(r>=lo)&((r<=hi) if hi==120 else (r<hi))
            selected=[row['condition'] for row in conditions if row['condition'].startswith(record['artifact'])]
            relative=[];fractions=[]
            for name in selected:
                delta=(valx[name]-clean)@operator.T
                relative.extend(np.sqrt(np.sum(delta[:,mask]**2,axis=1)/np.sum(pdf[:,mask]**2,axis=1)))
                fractions.extend(np.sum(delta[:,mask]**2,axis=1)/np.sum(delta**2,axis=1))
            expected={'mean_relative_l2':np.mean(relative),'mean_artifact_energy_fraction':np.mean(fractions),
                      'mean_signal_energy_fraction':np.mean(np.sum(pdf[:,mask]**2,axis=1)/np.sum(pdf**2,axis=1))}
            for key,val in expected.items():assert abs(float(record[key])-val)<=1e-9,(chemistry,record['window'],key)
            localization_checked+=1
        # Independent dual ridge solve reproduces decision scores for the
        # direct-intensity validation ablations; no fitted candidate is loaded.
        classes=np.array(sorted(set(labels)));training=unit(values[tr]);targets=np.array([[1. if label==phase else -1. for phase in classes] for label in labels[tr]])
        xmean,ymean=training.mean(axis=0),targets.mean(axis=0);centered=training-xmean
        alpha=design['chemistry'][chemistry]['selection']['raw_xrd']['alpha']
        dual=np.linalg.solve(centered@centered.T+alpha*np.eye(len(centered)),targets-ymean)
        def score(x):
            decisions=(unit(x)-xmean)@centered.T@dual+ymean
            truth_index=np.searchsorted(classes,labels[va]);true=decisions[np.arange(len(x)),truth_index]
            others=decisions.copy();others[np.arange(len(x)),truth_index]=-np.inf
            return np.mean(classes[decisions.argmax(axis=1)]==labels[va]),np.mean(true-others.max(axis=1))
        baseline,margin=score(clean)
        count=max(1,int(.1*len(theta)));order=np.argsort(np.abs(clean),axis=1)
        strong=np.zeros_like(clean,dtype=bool);faint=np.zeros_like(clean,dtype=bool)
        np.put_along_axis(strong,order[:,-count:],True,axis=1);np.put_along_axis(faint,order[:,:count],True,axis=1)
        rng=np.random.default_rng(design['seed']+41);random_masks=[]
        for draw in range(20):
            mask=np.zeros_like(clean,dtype=bool)
            for index in range(len(clean)):mask[index,rng.choice(len(theta),count,replace=False)]=True
            random_masks.append(mask)
        for kind,masks in [('strongest_10percent',[strong]),('weakest_10percent',[faint]),('random_10percent',random_masks)]:
            record=next(row for row in ablations if row['chemistry']==chemistry and row['ablation']==kind)
            accuracy,changed_margin=np.mean([score(np.where(mask,0,clean)) for mask in masks],axis=0)
            expected=dict(baseline_accuracy=baseline,ablated_accuracy=accuracy,accuracy_change=accuracy-baseline,
                          mean_true_class_margin=changed_margin,margin_change=changed_margin-margin)
            for key,val in expected.items():assert abs(float(record[key])-val)<=1e-8,(chemistry,kind,key)
            ablations_checked+=1
        expected_ablation_ids.extend([row['id'] for row in rows if roles[row['id']]=='validation'][:12])
        expected_ablation_clean.append(clean[:12]);expected_strong.append(strong[:12]);expected_weak.append(faint[:12]);expected_random.append(np.stack(random_masks)[:,:12])
        for record in [row for row in weak if row['chemistry']==chemistry]:
            a,b=[values[tr&(labels==record[key])].mean(axis=0) for key in ['phase_a','phase_b']]
            mask=np.maximum(np.abs(a),np.abs(b))<.2
            expected=dict(raw_cosine=float(unit(a)@unit(b)),weak_region_fraction=float(mask.mean()),fraction_difference_energy_below_20percent_peak=float(np.sum((a-b)[mask]**2)/np.sum((a-b)**2)))
            for key,val in expected.items():assert abs(float(record[key])-val)<=1e-10,(chemistry,key)
            weak_checked+=1
    assert list(map(str,evidence['ablation_ids']))==expected_ablation_ids
    np.testing.assert_allclose(evidence['ablation_clean_xrd'],np.concatenate(expected_ablation_clean),rtol=1e-12,atol=1e-12)
    np.testing.assert_array_equal(evidence['ablation_strong_masks'],np.concatenate(expected_strong))
    np.testing.assert_array_equal(evidence['ablation_weak_masks'],np.concatenate(expected_weak))
    np.testing.assert_array_equal(evidence['ablation_random_masks'],np.concatenate(expected_random,axis=1))
    # Independently score every convenience metric and all reported paired
    # intervals. These checks concern this worked report, not solver schemas.
    source_lookup={row['id']:row for rows,_,_,_ in raw_by_chem.values() for row in rows}
    predicted=read_csv(output/'predictions.csv')
    correctness={};groups={};wrong=Counter()
    for row in predicted:
        source=source_lookup[row['id']];guess=json.loads(row['predicted'])[0]
        correct=float(guess==source['phases'][0]);key=(source['chemistry'],row['method'],row['condition'])
        correctness[row['id'],row['method'],row['condition']]=correct
        groups.setdefault(key,[]).append(correct)
        if not correct:wrong[source['chemistry'],row['method'],row['condition'],source['phases'][0],guess]+=1
    convenience=read_csv(output/'metrics.csv')
    for row in convenience:
        values=groups[row['chemistry'],row['method'],row['condition']]
        assert int(row['n'])==len(values) and abs(float(row['accuracy'])-np.mean(values))<1e-12
    reported_wrong=Counter({(row['chemistry'],row['method'],row['condition'],row['truth'],row['predicted']):int(row['count']) for row in read_csv(output/'confusion_counts.csv')})
    assert reported_wrong==wrong
    intervals=json.loads((output/'uncertainty.json').read_text())
    for row in intervals:
        rows,_,labels,role=raw_by_chem[row['chemistry']]
        ids=[source['id'] for source in rows if roles[source['id']]=='test'];phases=labels[role=='test']
        interval_names=[condition['condition'] for condition in conditions if condition['artifact']==row['artifact']]
        reference=row['contrast'].removeprefix('minus_')
        deltas=np.array([np.mean([correctness[sid,row['method'],name]-correctness[sid,reference,name] for name in interval_names]) for sid in ids])
        classes=sorted(set(phases));totals=np.array([deltas[phases==phase].sum() for phase in classes]);counts=np.array([sum(phases==phase) for phase in classes])
        sampled=np.random.default_rng(design['seed']).integers(0,len(classes),size=(2000,len(classes)))
        endpoints=np.quantile(totals[sampled].sum(axis=1)/counts[sampled].sum(axis=1),[.025,.975])
        assert abs(row['estimate']-deltas.mean())<1e-12 and row['blocks']==len(classes)
        np.testing.assert_allclose(row['ci95'],endpoints,rtol=1e-10,atol=1e-10)
    return {'passed':True,'scope':'Independent numerical reimplementation of this known-target worked investigation only; no constraints on other solver methods and no claim of independent discovery.',
            'candidate_module_imported':False,'candidate_code_sha256':hashlib.sha256((output/'run.py').read_bytes()).hexdigest(),
            'source_test_patterns_reconstructed':len(expected_ids),'source_validation_ablation_patterns_reconstructed':len(expected_ablation_ids),
            'baseline_and_perturbed_transforms_checked':len(expected_ids)*(len(names)+1),'maximum_transform_absolute_error':max_transform,
            'generated_test_conditions_reconstructed':len(names),'maximum_perturbation_absolute_error':perturbation_max,
            'full_validation_localization_rows_checked':localization_checked,'training_pair_diagnostics_checked':weak_checked,
            'validation_ablation_rows_independently_refit':ablations_checked,'ablation_masks_exactly_reconstructed':True,
            'worked_accuracy_rows_recomputed':len(convenience),'reported_confusion_cells_checked':len(wrong),'paired_bootstrap_intervals_recomputed':len(intervals),
            'ridge_reimplementation':'Centered dual solve with explicit -1/+1 targets and unpenalized intercept; full validation deletion scores and margins reconstructed.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-output',type=Path,required=True);args=parser.parse_args()
    report=audit(args.candidate_output)
    (DATA/'verification/discovery_physics_review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
