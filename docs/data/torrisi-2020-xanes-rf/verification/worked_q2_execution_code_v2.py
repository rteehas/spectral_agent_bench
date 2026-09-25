#!/usr/bin/env python3
"""One worked research design. No choice here is a benchmark requirement.

Only the eight source JSONL files are read. Independently rerunnable per question.
Two material holdouts measure sensitivity to selection; Q1 also compares record
holdouts, Q5 repeats fitting seeds. Uncertainty intervals are conditional on the
fitted models, not population-wide confidence statements.
"""
import argparse
import csv
import gzip
import hashlib
import json
import shutil
import time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split
import sklearn

ELEMENTS=['Ti','V','Cr','Mn','Fe','Co','Ni','Cu']
TARGETS={'coord':'coordination','md':'avg_nn_dists','bader':'bader'}
CONDITIONS={'Q1':{'coord':['untreated','treated']},'Q2':{'md':['model']},'Q3':{'bader':['full','white_line']},'Q4':{t:['pointwise','multiscale'] for t in TARGETS},'Q5':{t:['released','unit_peak'] for t in ['coord','md']}}

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def write_csv(path,rows,fields=None):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def score(y,p,target):
    if target=='coord':
        f=f1_score(y,p,labels=[4,5,6],average=None,zero_division=0)
        return dict(accuracy=float(accuracy_score(y,p)),macro_f1=float(f.mean()),**{f'f1_{k}':float(v) for k,v in zip([4,5,6],f)})
    return dict(mae=float(mean_absolute_error(y,p)),r2=float(r2_score(y,p)))
def loss(y,p,target):
    if target!='coord':return float(np.mean(abs(y-p)))
    # Direct confusion-count implementation keeps clustered bootstrap affordable.
    cm=np.bincount((y.astype(int)-4)*3+p.astype(int)-4,minlength=9).reshape(3,3)
    denom=cm.sum(0)+cm.sum(1)
    return 1-float(np.divide(2*np.diag(cm),denom,out=np.zeros(3),where=denom>0).mean())
def group_bootstrap(y,p0,p1,groups,target,seed=101):
    """Paired gain in macro-F1 or reduction in MAE, resampling material groups."""
    rng=np.random.default_rng(seed);ids=np.unique(groups)
    members=[np.flatnonzero(groups==g) for g in ids]
    values=[]
    for _ in range(250):
        ix=np.concatenate([members[j] for j in rng.integers(len(ids),size=len(ids))])
        values.append(loss(y[ix],p0[ix],target)-loss(y[ix],p1[ix],target))
    return dict(gain=loss(y,p0,target)-loss(y,p1,target),low=float(np.quantile(values,.025)),high=float(np.quantile(values,.975)),bootstrap_units=len(ids))
def representation(X,E,condition):
    definitions=[]
    if condition=='white_line':
        return E[np.argmax(X,axis=1),None], [dict(feature=0,kind='peak_position',start_eV=float(E.min()),end_eV=float(E.max()))]
    if condition=='unit_peak':X=X/X.max(axis=1,keepdims=True)
    if condition=='multiscale':
        blocks=[]
        for width in [10,20,50]:
            for start in range(0,100,width):
                stop=start+width
                t=np.linspace(-1,1,width)
                c=(np.linalg.pinv(np.polynomial.polynomial.polyvander(t,2))@X[:,start:stop].T).T
                blocks.append(c)
                for degree in range(3):
                    definitions.append(dict(feature=len(definitions),kind=f'degree_{degree}',width_points=width,start_eV=float(E[start]),end_eV=float(E[stop-1])))
        return np.concatenate(blocks,axis=1),definitions
    return X.copy(),[dict(feature=i,kind='absorption',start_eV=float(e),end_eV=float(e)) for i,e in enumerate(E)]
def split_rows(indices,groups,mode,seed):
    if mode=='identified_material':
        dev,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=seed).split(indices,groups=groups[indices]))
        train,val=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=seed+1).split(indices[dev],groups=groups[indices[dev]]))
        return indices[dev[train]],indices[dev[val]],indices[test]
    dev,test=train_test_split(indices,test_size=.2,random_state=seed)
    train,val=train_test_split(dev,test_size=.25,random_state=seed+1)
    return train,val,test

def fit_model(Z,y,train,val,target,condition,seed,jobs):
    cls=ExtraTreesClassifier if target=='coord' else ExtraTreesRegressor
    trials=[];best=None
    for leaf in [1,5]:
        kw=dict(n_estimators=80,min_samples_leaf=leaf,max_features=.8,random_state=seed,n_jobs=jobs)
        if target=='coord':kw['class_weight']='balanced' if condition=='treated' else None
        m=cls(**kw).fit(Z[train],y[train]);v=loss(y[val],m.predict(Z[val]),target)
        trials.append(dict(min_samples_leaf=leaf,validation_loss=v))
        if best is None or v<best[0]:best=(v,m,leaf)
    return best[1],trials,best[2]

def localize(model,Z,y,test,target,definitions,E,seed):
    """Joint permutation of energy-associated features; predictive reliance only."""
    rng=np.random.default_rng(seed)
    baseline=loss(y[test],model.predict(Z[test]),target)
    edges=np.linspace(E.min(),E.max(),6)
    result=[]
    for b in range(5):
        center=np.array([(d['start_eV']+d['end_eV'])/2 for d in definitions])
        inds=np.flatnonzero((center>=edges[b])&((center<edges[b+1]) if b<4 else (center<=edges[b+1])))
        gains=[]
        for rep in range(3):
            work=Z[test].copy();permutation=rng.permutation(len(test));work[:,inds]=work[permutation[:,None],inds]
            gains.append(loss(y[test],model.predict(work),target)-baseline)
        result.append(dict(region=b,start_eV=float(edges[b]),end_eV=float(edges[b+1]),features=inds.tolist(),loss_increase=float(np.mean(gains)),permutation_sd=float(np.std(gains)),repeats=3))
    families=[]
    if any(d['kind'].startswith('degree_') for d in definitions):
        for degree in range(3):
            inds=np.array([i for i,d in enumerate(definitions) if d['kind']==f'degree_{degree}'])
            work=Z[test].copy();p=rng.permutation(len(test));work[:,inds]=work[p[:,None],inds]
            families.append(dict(degree=degree,loss_increase=loss(y[test],model.predict(work),target)-baseline))
    return result,families

def run(question,inputs,output,jobs=2):
    started=time.time();output.mkdir(parents=True,exist_ok=True)
    (output/'code').mkdir(exist_ok=True)
    own=Path(__file__).resolve();dest=output/'code/candidate.py'
    if own!=dest.resolve():shutil.copyfile(own,dest)
    runs=[];predictions=[];partitions=[];metrics=[];audits=[];pairs=[];regimes=[];localization=[];families=[];definitions={};confusions=[];class_counts=[];baselines=[]
    design=dict(question=question,runs=runs,example_only=True,
        learner='ExtraTrees; 80 trees; max_features .8; min_samples_leaf in {1,5} selected separately on validation loss; no refit using validation rows.',
        eligibility='Finite 100-point E/mu; valid target; positive maximum. Coordination restricted to4/5/6, distance positive. Main analysis uses available material IDs only. No outcome-dependent spectrum-quality screening.',
        partitions='Two repetitions, seeds17/83, roughly60/20/20 train/validation/test by material group. Q1 adds record holdouts on the identical identified cohort to assess evaluation sensitivity.',
        uncertainty='250 paired bootstrap resamples of test material IDs, conditional on fitted models. Spectrum runs instead resample rows. Repeated heldout cohorts overlap, so they are sensitivity analyses, not independent replications.',
        representation='Pointwise released absorption, except white_line=argmax energy; multiscale=quadratic coefficients on nonoverlapping10/20/50point intervals with local coordinate[-1,1]; unit_peak=divide spectrum by its maximum.',
        localization='Joint test-set permutation of features whose energy-interval midpoint lies in one of5equal-width energy bands;3permutations per band. Multiscale coefficients also permuted jointly by degree. Holdout use is diagnostic, never used to tune models; comparisons across correlated representations are qualitative.',
        fitting_variability='Q5 seeds113/211 are crossed with the2material partitions; all other tasks use113.',
        source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs.glob('*.gz'))},
        versions=dict(numpy=np.__version__,sklearn=sklearn.__version__))
    for element in ELEMENTS:
        with gzip.open(inputs/f'{element}.jsonl.gz','rt') as f:rows=[json.loads(s) for s in f]
        X=np.array([r['mu'] for r in rows]);Es=np.array([r['E'] for r in rows]);E=Es[0]
        assert X.shape[1]==100 and np.allclose(Es,E), 'This example assumes a shared per-element grid; inspect input first.'
        rawid=[r.get('metadata',{}).get('id') for r in rows]
        groups=np.array([str(g) if g is not None else '' for g in rawid]);known=groups!=''
        origins={s:dict(records=sum(r.get('metadata',{}).get('origin')==s for r in rows),identified=sum(r.get('metadata',{}).get('origin')==s and rawid[i] is not None for i,r in enumerate(rows))) for s in sorted({str(r.get('metadata',{}).get('origin')) for r in rows})}
        finite=np.isfinite(X).all(axis=1)&np.isfinite(Es).all(axis=1)&(X.max(axis=1)>0)
        for target,conditions in CONDITIONS[question].items():
            y=np.array([np.nan if r[TARGETS[target]] is None else r[TARGETS[target]] for r in rows],dtype=float)
            eligible=finite&np.isfinite(y)&(np.isin(y,[4,5,6]) if target=='coord' else ((y>0) if target=='md' else True))
            indices=np.flatnonzero(eligible&known)
            coverage=dict(element=element,target=target,source_records=len(rows),valid_target_records=int(eligible.sum()),identified_valid_records=len(indices),identified_materials=len(np.unique(groups[indices])),origins=origins,
                identified_target_mean=float(np.mean(y[eligible&known])),unidentified_target_mean=float(np.mean(y[eligible&~known])) if (eligible&~known).any() else None)
            audits.append(coverage)
            modes=['identified_material','spectrum'] if question=='Q1' else ['identified_material']
            for mode in modes:
                for repeat,splitseed in enumerate([17,83]):
                    train,val,test=split_rows(indices,groups,mode,splitseed)
                    roles=np.full(len(rows),'excluded',dtype=object);roles[train]='train';roles[val]='validation';roles[test]='test'
                    for fitseed in ([113,211] if question=='Q5' else [113]):
                        comparison=f'{element}_{target}_{mode}_r{repeat}_s{fitseed}'
                        comparison_results=[]
                        for condition in conditions:
                            run_id=f'{comparison}_{condition}'
                            Z,defs=representation(X,E,condition)
                            model,trials,leaf=fit_model(Z,y,train,val,target,condition,fitseed,jobs)
                            pred=model.predict(Z[test]);values=score(y[test],pred,target)
                            run_spec=dict(run_id=run_id,element=element,target=target,condition=condition,comparison_id=comparison,generalization=mode,repeat=repeat,fit_seed=fitseed,split_seed=splitseed,selected_min_samples_leaf=leaf,validation_trials=trials)
                            runs.append(run_spec)
                            predictions.extend(dict(run_id=run_id,source_row=int(i),y_pred=float(p)) for i,p in zip(test,pred))
                            partitions.extend(dict(run_id=run_id,source_row=i,role=r) for i,r in enumerate(roles))
                            metrics.extend(dict(run_id=run_id,metric=k,value=v) for k,v in values.items())
                            comparison_results.append((condition,pred))
                            base=float(np.bincount(y[train].astype(int)).argmax()) if target=='coord' else float(np.median(y[train]))
                            baselines.append(dict(run_id=run_id,training_constant=base,metrics=score(y[test],np.full(len(test),base),target)))
                            definitions[element+'_'+condition]=defs
                            if target=='coord':
                                for role,ii in [('train',train),('validation',val),('test',test)]:
                                    for k in [4,5,6]:class_counts.append(dict(run_id=run_id,role=role,coordination=k,count=int((y[ii]==k).sum())))
                                for a in [4,5,6]:
                                    for b in [4,5,6]:confusions.append(dict(run_id=run_id,true_coordination=a,predicted_coordination=b,count=int(((y[test]==a)&(pred==b)).sum())))
                            if question=='Q2':
                                low,high=np.quantile(y[train],[.1,.9]);base=np.median(y[train])
                                for name,mask in [('all',np.ones(len(test),bool)),('short',y[test]<low),('middle',(y[test]>=low)&(y[test]<=high)),('long',y[test]>high)]:
                                    if not mask.any():continue
                                    yt,yp=y[test][mask],pred[mask];err=yp-yt
                                    bootstrap=group_bootstrap(yt,np.full(len(yt),base),yp,groups[test][mask],target)
                                    regimes.append(dict(run_id=run_id,regime=name,records=int(mask.sum()),materials=len(np.unique(groups[test][mask])),low_cutoff=float(low),high_cutoff=float(high),mae=float(np.mean(abs(err))),bias=float(err.mean()),baseline_mae=float(np.mean(abs(yt-base))),baseline_gain_low=bootstrap['low'],baseline_gain_high=bootstrap['high']))
                            if question in ['Q4','Q5']:
                                loc,fam=localize(model,Z,y,test,target,defs,E,fitseed+repeat)
                                for row in loc:localization.append(dict(run_id=run_id,**row))
                                for row in fam:families.append(dict(run_id=run_id,**row))
                            print(f'{question} {run_id} {values}',flush=True)
                        if len(comparison_results)==2:
                            (c0,p0),(c1,p1)=comparison_results
                            bootgroups=groups[test] if mode=='identified_material' else np.array([str(i) for i in test])
                            pairs.append(dict(comparison_id=comparison,element=element,target=target,generalization=mode,repeat=repeat,fit_seed=fitseed,first=c0,second=c1,metric='macro_f1_gain' if target=='coord' else 'mae_reduction',**group_bootstrap(y[test],p0,p1,bootgroups,target)))
            # Save recoverable artifacts after each target, rather than losing a long run.
            dump(output/'design.json',design)
            write_csv(output/'metrics.csv',metrics)
    dump(output/'design.json',design)
    write_csv(output/'predictions.csv',predictions)
    write_csv(output/'partitions.csv',partitions)
    write_csv(output/'metrics.csv',metrics)
    write_csv(output/'comparisons.csv',pairs)
    write_csv(output/'regimes.csv',regimes)
    write_csv(output/'class_counts.csv',class_counts)
    write_csv(output/'confusion.csv',confusions)
    dump(output/'feature_definitions.json',definitions)
    dump(output/'localization.json',localization)
    write_csv(output/'shape_families.csv',families)
    # Descriptive stability across heldout groups and fitting seeds; no causal claim.
    stability=[];lookup={r['run_id']:r for r in runs}
    for element in ELEMENTS:
        for target in CONDITIONS[question]:
            selected=[r for r in runs if r['element']==element and r['target']==target and r['generalization']=='identified_material']
            for i,a in enumerate(selected):
                for b in selected[i+1:]:
                    la=[x['loss_increase'] for x in localization if x['run_id']==a['run_id']];lb=[x['loss_increase'] for x in localization if x['run_id']==b['run_id']]
                    if not la or not lb:continue
                    rho=float(spearmanr(la,lb).statistic)
                    stability.append(dict(first_run=a['run_id'],second_run=b['run_id'],same_condition=a['condition']==b['condition'],same_partition=a['repeat']==b['repeat'],same_fit_seed=a['fit_seed']==b['fit_seed'],spearman=rho if np.isfinite(rho) else None,top_region_same=bool(np.argmax(la)==np.argmax(lb))))
    evidence=dict(coverage=audits,baselines=baselines,comparisons=pairs,regimes=regimes,localization_stability=stability,elapsed_seconds=time.time()-started,
        limitations=['Available material IDs occur only in the scrape origin; identified-material results do not establish generalization to the unidentified feff origin.',
        'Identifier disjointness cannot exclude cross-database aliases or structural near-duplicates without structures.',
        'Conditional test-group bootstrap omits uncertainty over training samples; two resplits and (Q5) two fitting seeds only assess limited sensitivity.',
        'All finite spectra retained: unusual maxima are not automatically treated as bad data; results depend on this choice.',
        'Permutation perturbations can break spectral correlations. Regions overlap in physical support for multiscale features; degree and energy effects indicate predictive reliance, not causal spectroscopy.'])
    dump(output/'evidence.json',evidence)
    summarize(question,output,runs,metrics,evidence,localization,families)
    return evidence

def summarize(question,out,runs,metrics,evidence,localization,families):
    vals={}
    for row in metrics:vals.setdefault(row['run_id'],{})[row['metric']]=row['value']
    targets=list(CONDITIONS[question]);fig,axes=plt.subplots(len(targets),1,figsize=(11,4*len(targets)),squeeze=False)
    lines=[f'# {question}: executed illustrative analysis','',
      'This is one defensible, limited research design, not a reference-score target. ExtraTrees models were selected using separate validation data; test predictions were produced only after that choice. Details, run memberships and hashes are in design.json and the row-level audit tables.','',
      'Primary evaluation holds out material identifiers. Missing IDs occur in the feff-origin records, whereas identified records come from scrape. The restriction changes the source population; these results support claims only about the identified population. Unknown-ID records were excluded, not relabeled as new materials. Coverage and target shifts are in evidence.json.','',
      'Training-only constant baselines (majority class or median regression label) and their test scores are recorded in evidence.json. Two material partitions assess selection sensitivity. Intervals resample test material groups conditional on the fitted models; they exclude training uncertainty and the partitions overlap. A broad claim of universal predictive reliability would exceed this evidence.','',
      '| Element / target | Condition | Mean test score | Range across material holdouts/fits |','|---|---|---:|---:|']
    for ti,target in enumerate(targets):
        ax=axes[ti,0];key='macro_f1' if target=='coord' else 'mae'
        for ci,condition in enumerate(CONDITIONS[question][target]):
            points=[];spreads=[]
            for element in ELEMENTS:
                selected=[r for r in runs if r['element']==element and r['target']==target and r['condition']==condition and r['generalization']=='identified_material']
                a=[vals[r['run_id']][key] for r in selected]
                points.append(np.mean(a));spreads.append(np.std(a))
                lines.append(f'| {element} / {target} | {condition} | {np.mean(a):.4f} | {min(a):.4f}–{max(a):.4f} |')
            ax.errorbar(np.arange(8)+.1*ci,points,yerr=spreads,marker='o',capsize=3,label=condition)
        ax.set_xticks(range(8),ELEMENTS);ax.set_ylabel(key);ax.set_title(f'{target}: identified-material test results (bars: split/fit SD, not confidence intervals)');ax.legend()
    fig.tight_layout();fig.savefig(out/'diagnostics.png',dpi=160);plt.close(fig)
    lines+=['','Paired gains and conditional 95% intervals are in comparisons.csv where applicable. Positive gain favors the second condition; regression gain is a reduction in MAE, classification gain is an increase in macro-F1. Individual intervals are descriptive and are not multiplicity-adjusted.','']
    if question=='Q1':
        mat=[p for p in evidence['comparisons'] if p['generalization']=='identified_material']
        lines += [f'Class weighting had positive macro-F1 gain in {sum(p["gain"]>0 for p in mat)}/{len(mat)} material holdouts; only {sum(p["low"]>0 for p in mat)} conditional intervals were wholly above zero. Overall success must therefore be judged by per-class F1 and confusion counts, not accuracy alone.','']
        for e in ELEMENTS:
            rr=[r for r in runs if r['element']==e and r['generalization']=='identified_material']
            f={k:np.mean([vals[r['run_id']][f'f1_{k}'] for r in rr if r['condition']=='untreated']) for k in [4,5,6]}
            spectrum=[vals[r['run_id']]['macro_f1'] for r in runs if r['element']==e and r['condition']=='untreated' and r['generalization']=='spectrum']
            material=[vals[r['run_id']]['macro_f1'] for r in rr if r['condition']=='untreated']
            lines.append(f'- {e}: untreated class F1(4,5,6)={f[4]:.3f}, {f[5]:.3f}, {f[6]:.3f}; record versus material macro-F1={np.mean(spectrum):.3f} versus {np.mean(material):.3f}. See class_counts.csv for prevalence and confusion.csv for error tradeoffs. Record holdouts can share IDs with training and do not estimate new-material performance.')
        lines += ['','Class weighting is one imbalance intervention; failure of this intervention does not show that rare-environment prediction is irreducibly poor. Small class support and unstable material holdouts limit conclusions.']
    elif question=='Q2':
        lines+=['Regimes were defined by the training-distance10th/90th percentiles. This retrospective error stratification uses test truth to characterize failure; it is not a deployable confidence detector. The training median supplies a non-spectral baseline.','']
        for e in ELEMENTS:
            rr=[x for x in evidence['regimes'] if x['run_id'].startswith(e+'_')]
            parts=[]
            for regime in ['short','middle','long']:
                z=[x for x in rr if x['regime']==regime]
                parts.append(f'{regime} MAE={np.mean([x["mae"] for x in z]):.4f} Å, bias={np.mean([x["bias"] for x in z]):+.4f} Å')
            lines.append(f'- {e}: '+ '; '.join(parts)+'.')
        lines+=['','Positive tail bias means predicted distances are too long; negative means too short. Tail support, group counts and conditional improvement intervals are in regimes.csv. These estimates describe the supplied computed distribution; experimental reliability is untested.']
    elif question=='Q3':
        # Pair stored first full, second white_line; positive means white-line better.
        lines+=['For this task comparisons.csv stores full first and white_line second, so negative gain favors the full spectrum.','']
        for e in ELEMENTS:
            p=[x for x in evidence['comparisons'] if x['element']==e]
            lines.append(f'- {e}: full-spectrum MAE reduction relative to white line averages {-np.mean([x["gain"] for x in p]):.4f} charge units; {sum(x["high"]<0 for x in p)}/{len(p)} conditional intervals support reduction. The flexible white-line learner receives independent validation selection, so this comparison is not restricted to a linear charge–peak relationship.')
        lines+=['','Incremental predictive information is model- and cohort-dependent. This analysis does not establish a direct physical inversion or a unique oxidation-state assignment.']
    elif question in ['Q4','Q5']:
        stable=evidence['localization_stability'];paired=[s for s in stable if not s['same_condition'] and s['same_partition'] and s['same_fit_seed']]
        lines += ['Held-out joint permutations test whether prediction relies on energy-localized inputs. Features were grouped by energy midpoint before evaluation; multiscale intervals may extend across neighboring regions. The full interval/degree definitions are in feature_definitions.json. Repeated permutations and holdouts corroborate reliance, but correlated features and out-of-distribution perturbations prevent a causal or unique attribution.','',f'Across paired conditions, the highest-loss energy region agrees in {sum(x["top_region_same"] for x in paired)}/{len(paired)} comparisons. Agreement in predictive score therefore does not by itself establish agreement in interpretation. localization.json gives region effects and permutation variability; evidence.json separates within-condition and between-condition stability.','']
        for e in ELEMENTS:
            for t in targets:
                rr=[r for r in runs if r['element']==e and r['target']==t and r['generalization']=='identified_material']
                parts=[]
                for c in CONDITIONS[question][t]:
                    ids=[r['run_id'] for r in rr if r['condition']==c]
                    loc=[x for x in localization if x['run_id'] in ids]
                    mean=np.array([np.mean([x['loss_increase'] for x in loc if x['region']==b]) for b in range(5)])
                    top=int(mean.argmax());interval=next(x for x in loc if x['region']==top)
                    parts.append(f'{c}: {interval["start_eV"]:.1f}–{interval["end_eV"]:.1f} eV (mean loss increase {mean[top]:.4f})')
                lines.append(f'- {e}/{t}: '+ '; '.join(parts)+'.')
        if question=='Q4':
            lines+=['','The51 quadratic descriptors retain coarse amplitude/slope/curvature across three scales, while discarding residual within-window structure. shape_families.csv tests each degree family jointly on held-out data. Each family can be redundant across scales, so its loss increase is conditional on the remaining representation. Ranking families without this perturbation evidence would overstate interpretation.']
            for t in targets:
                selected={r['run_id'] for r in runs if r['target']==t}
                f=[x for x in families if x['run_id'] in selected]
                lines.append(f'- {t} mean loss increases by coefficient degree0/1/2: '+', '.join(f'{np.mean([x["loss_increase"] for x in f if x["degree"]==d]):.4f}' for d in range(3))+'. Aggregation is descriptive; individual elements and runs can differ.')
        else:
            for label,selection in [('fitting seed',lambda s:s['same_condition'] and s['same_partition'] and not s['same_fit_seed']),('material partition',lambda s:s['same_condition'] and not s['same_partition'] and s['same_fit_seed'])]:
                z=[s for s in stable if selection(s)];rho=[s['spearman'] for s in z if s['spearman'] is not None]
                lines.append(f'- Across {label} changes, mean region-rank correlation is {np.mean(rho):.3f} and the top region agrees in {sum(s["top_region_same"] for s in z)}/{len(z)} comparisons. This supplies a variability scale for judging normalization changes.')
            lines+=['','Normalization is paired within the same material partition and fitting seed; leaf size is selected separately, so the contrast describes the best of this small candidate set under each representation. It does not isolate only a fixed-estimator algebraic effect.']
    lines+=['','Limitations:']+['- '+s for s in evidence['limitations']]
    (out/'report.md').write_text('\n'.join(lines)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('question',choices=list(CONDITIONS)+['ALL']);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
    for q in CONDITIONS if a.question=='ALL' else [a.question]:run(q,a.inputs,a.output/q if a.question=='ALL' else a.output,a.jobs)
if __name__=='__main__':main()
