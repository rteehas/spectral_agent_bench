#!/usr/bin/env python3
"""Independent charge-information analysis. No inputs except the eight released JSONL files."""
import os
for v in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[v]='1'
import argparse, gzip, json, hashlib, platform, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
import sklearn, scipy
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge
from sklearn.svm import SVR
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ELEMENTS=['Ti','V','Cr','Mn','Fe','Co','Ni','Cu']
SEEDS=[1729,2718,31415,57721,81173]

def read_element(path):
    with gzip.open(path,'rt') as f: d=[json.loads(x) for x in f]
    X=np.asarray([r['mu'] for r in d],float); E=np.asarray([r['E'] for r in d],float)
    y=np.asarray([np.nan if r['bader'] is None else r['bader'] for r in d])
    ids=np.asarray([str((r.get('metadata') or {}).get('id') or '') for r in d])
    rows=np.asarray([r['source_row'] for r in d]); origin=np.asarray([(r.get('metadata') or {}).get('origin','unknown') for r in d])
    assert len(set(rows))==len(d)
    assert X.shape==E.shape and X.shape[1]==100
    good=np.isfinite(X).all(1)&np.isfinite(E).all(1)&(np.diff(E,axis=1)>0).all(1)&np.isfinite(y)
    assert np.all(E==E[0]), 'Independent analysis assumes shared per-element energy grids; revise if not true.'
    wl=E[np.arange(len(d)),np.argmax(X,axis=1)]
    return d,X,E,y,ids,rows,origin,good,wl

def split(indices,ids,grouped,seed):
    rng=np.random.default_rng(seed)
    units=np.unique(ids[indices]) if grouped else indices.copy()
    rng.shuffle(units)
    ntest=max(1,int(np.ceil(.2*len(units)))); nval=max(1,int(np.ceil(.2*len(units))))
    test_u=units[:ntest]; val_u=units[ntest:ntest+nval]; train_u=units[ntest+nval:]
    if grouped:
        return tuple(indices[np.isin(ids[indices],u)] for u in [train_u,val_u,test_u])
    return train_u,val_u,test_u

def group_weights(ids):
    _, inv, count=np.unique(ids,return_inverse=True,return_counts=True)
    return 1./count[inv]

def models(seed):
    for alpha in [1.,100.]:
        yield f'ridge_alpha{alpha:g}', 'ridge', TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),Ridge(alpha=alpha)),transformer=StandardScaler())
    for gamma_factor in [.1,1.]:
        # After StandardScaler, scale gamma is approximately 1 / number_of_features.
        yield f'svr_gammafactor{gamma_factor:g}', 'svr', TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),SVR(C=10,epsilon=.05,gamma='scale' if gamma_factor==1 else None)),transformer=StandardScaler()), gamma_factor
    for leaf in [2,8]:
        yield f'extratrees_leaf{leaf}', 'extra_trees', ExtraTreesRegressor(n_estimators=100,min_samples_leaf=leaf,max_features=1.,n_jobs=1,random_state=seed)

def bootstrap_delta(y,pw,pf,groups,seed,B=4000):
    d=np.abs(y-pw)-np.abs(y-pf)
    table=pd.DataFrame({'g':groups,'d':d,'ew':np.abs(y-pw),'ef':np.abs(y-pf)}).groupby('g').mean()
    a=table['d'].to_numpy(); rng=np.random.default_rng(seed)
    means=np.mean(a[rng.integers(0,len(a),size=(B,len(a)))],axis=1)
    return dict(delta_material=float(a.mean()),ci_low=float(np.quantile(means,.025)),ci_high=float(np.quantile(means,.975)),fraction_bootstrap_nonpositive=float(np.mean(means<=0)),mae_white_material=float(table.ew.mean()),mae_full_material=float(table.ef.mean()),n_test_units=len(a))

def one_element(args):
    element,inp,out=args
    path=Path(inp)/f'{element}.jsonl.gz'
    d,X,E,y,ids,rows,origin,good,wl=read_element(path)
    n=len(d); known=good&(ids!=''); unknown=good&(ids=='')
    counts=dict(element=element,n_total=n,n_label=int(np.isfinite(y).sum()),n_valid=int(good.sum()),n_identified_label=int(known.sum()),n_unidentified_label=int(unknown.sum()),n_identified_materials=len(np.unique(ids[known])),n_missing_bader=int(np.isnan(y).sum()),n_invalid_other=int((np.isfinite(y)&~good).sum()),bader_mean=float(np.nanmean(y)),bader_sd=float(np.nanstd(y)),bader_min=float(np.nanmin(y)),bader_max=float(np.nanmax(y)),step_eV=float(E[0,1]-E[0,0]),common_grid=bool(np.all(E==E[0])),exact_duplicate_spectra=n-len(np.unique(X,axis=0)),origin_counts=dict(pd.Series(origin).value_counts().items()),labeled_origin_counts=dict(pd.Series(origin[good]).value_counts().items()))
    studies=[('primary',s,True,known,'raw') for s in SEEDS]
    studies += [('unit_peak_normalized',SEEDS[0],True,known,'peak'),('spectrum_identified',SEEDS[0],False,known,'raw'),('spectrum_all',SEEDS[0],False,good,'raw')]
    runs=[]; pred=[]; partitions=[]; metrics=[]; comparisons=[]; choices=[]; family=[]
    for study,seed,grouped,eligible,normalization in studies:
        inds=np.flatnonzero(eligible); train,val,test=split(inds,ids,grouped,seed)
        if grouped:
            assert not(set(ids[train])&set(ids[val]) or set(ids[train])&set(ids[test]) or set(ids[val])&set(ids[test]))
        compare=f'{element}_{study}_{seed}'
        role=np.full(n,'excluded',dtype=object); role[train]='train'; role[val]='validation'; role[test]='test'
        weights=group_weights(ids[val]) if grouped else np.ones(len(val))
        xp=X if normalization=='raw' else X/np.maximum(np.max(np.abs(X),axis=1,keepdims=True),1e-12)
        features={'white_line':wl[:,None], 'full':np.column_stack([xp,wl])}
        pp={}; family_pp={}
        for condition,xx in features.items():
            run_id=f'{compare}_{condition}'
            best=None; best_val=np.inf; per_family={}
            for candidate in models(seed):
                name,fam,model=candidate[:3]
                if len(candidate)==4 and candidate[3]!=1:
                    model.regressor[-1].gamma=candidate[3]/xx.shape[1]
                model.fit(xx[train],y[train]); pv=model.predict(xx[val]); score=mean_absolute_error(y[val],pv,sample_weight=weights)
                choices.append(dict(run_id=run_id,candidate=name,family=fam,validation_mae=score))
                if fam not in per_family or score<per_family[fam][0]: per_family[fam]=(score,name,model)
                if score<best_val: best_val=score; best=(name,fam,model)
            name,fam,model=best
            pt=model.predict(xx[test]); pp[condition]=pt
            for ff,(_,nn,mm) in per_family.items(): family_pp[(condition,ff)]=mm.predict(xx[test])
            metrics.extend([dict(run_id=run_id,metric='mae',value=float(mean_absolute_error(y[test],pt))),dict(run_id=run_id,metric='r2',value=float(r2_score(y[test],pt)))])
            pred.extend(dict(run_id=run_id,source_row=int(r),y_pred=float(p)) for r,p in zip(rows[test],pt))
            partitions.extend(dict(run_id=run_id,source_row=int(r),role=rr) for r,rr in zip(rows,role))
            runs.append(dict(run_id=run_id,element=element,target='bader',condition=condition,comparison_id=compare,generalization='identified_material' if grouped else 'spectrum',study=study,seed=seed,normalization=normalization,chosen_model=name,validation_mae=float(best_val),selection_weighting='equal_material' if grouped else 'equal_spectrum',n_train=len(train),n_validation=len(val),n_test=len(test),n_excluded=int((role=='excluded').sum()),train_materials=len(set(ids[train])-set([''])),test_materials=len(set(ids[test])-set([''])),features='100 absorption intensities plus white-line energy' if condition=='full' else 'white-line energy only',refit_validation=False))
        groups=ids[test] if grouped else np.array([f'row_{r}' for r in rows[test]])
        bs=bootstrap_delta(y[test],pp['white_line'],pp['full'],groups,seed)
        comparisons.append(dict(comparison_id=compare,element=element,study=study,seed=seed,generalization='identified_material' if grouped else 'spectrum',delta_spectrum=float(mean_absolute_error(y[test],pp['white_line'])-mean_absolute_error(y[test],pp['full'])),**bs))
        for ff in ['ridge','svr','extra_trees']:
            bb=bootstrap_delta(y[test],family_pp[('white_line',ff)],family_pp[('full',ff)],groups,seed,B=1000)
            family.append(dict(comparison_id=compare,element=element,study=study,seed=seed,family=ff,**bb))
        # Truth, predictions and material IDs are diagnostic outputs, never predictors.
        diagnostic=pd.DataFrame({'source_row':rows[test],'material_id':ids[test],'origin':origin[test],'bader':y[test],'white_line':wl[test],'pred_white_line':pp['white_line'],'pred_full':pp['full']})
        diagnostic.to_csv(Path(out)/'diagnostics'/f'{compare}.csv',index=False)
        print(f'{element} {study} {seed}: material/unit MAE WL={bs["mae_white_material"]:.4f}, full={bs["mae_full_material"]:.4f}, delta={bs["delta_material"]:.4f} [{bs["ci_low"]:.4f},{bs["ci_high"]:.4f}]',flush=True)
    return counts,runs,pred,partitions,metrics,comparisons,choices,family

def plots(out,counts,comparisons):
    primary=comparisons[comparisons.study=='primary']; summary=primary.groupby('element',sort=False).agg(delta=('delta_material','mean'),low=('delta_material','min'),high=('delta_material','max'),wl=('mae_white_material','mean'),full=('mae_full_material','mean')).loc[ELEMENTS]
    fig,ax=plt.subplots(figsize=(9,5))
    for i,el in enumerate(ELEMENTS):
        dd=primary[primary.element==el]
        ax.errorbar(dd.delta_material,np.arange(len(dd))*.12+i-.24,xerr=np.array([dd.delta_material-dd.ci_low,dd.ci_high-dd.delta_material]),fmt='o',markersize=4,capsize=2,color=plt.cm.tab10(i))
    ax.axvline(0,c='k',lw=1); ax.set_yticks(range(8),ELEMENTS); ax.invert_yaxis(); ax.set_xlabel('Paired reduction in equal-material MAE (e): white line − full spectrum'); ax.set_title('Unseen identified materials: five split estimates and paired 95% bootstrap intervals'); fig.tight_layout(); fig.savefig(out/'figures'/'material_effect_uncertainty.png',dpi=170); plt.close(fig)
    fig,axs=plt.subplots(2,4,figsize=(14,7))
    for ax,el in zip(axs.flat,ELEMENTS):
        dd=pd.read_csv(out/'diagnostics'/f'{el}_primary_{SEEDS[0]}.csv')
        ax.scatter(dd.bader,dd.pred_white_line,s=9,alpha=.4,label='White line',color='#c87425'); ax.scatter(dd.bader,dd.pred_full,s=9,alpha=.4,label='Full spectrum',color='#237eb0')
        lo=min(dd.bader.min(),dd.pred_full.min(),dd.pred_white_line.min()); hi=max(dd.bader.max(),dd.pred_full.max(),dd.pred_white_line.max()); ax.plot([lo,hi],[lo,hi],c='k',lw=.8)
        ax.set_title(el); ax.set_xlabel('True Bader charge (e)'); ax.set_ylabel('Predicted charge (e)')
    axs.flat[0].legend(fontsize=8); fig.suptitle('First material holdout: charge predictions'); fig.tight_layout(); fig.savefig(out/'figures'/'heldout_predictions.png',dpi=170); plt.close(fig)
    ss=comparisons[comparisons.seed==SEEDS[0]]
    fig,ax=plt.subplots(figsize=(10,5)); studies=['primary','unit_peak_normalized','spectrum_identified','spectrum_all']
    labels=['Material split, released amplitudes','Material split, unit peak','Spectrum split, identified subset','Spectrum split, all labeled']
    for j,(study,label) in enumerate(zip(studies,labels)):
        dd=ss[ss.study==study].set_index('element').loc[ELEMENTS]; ax.bar(np.arange(8)+(j-1.5)*.19,dd.delta_material,width=.18,label=label)
    ax.axhline(0,c='k',lw=.8); ax.set_xticks(range(8),ELEMENTS); ax.set_ylabel('MAE reduction (e)'); ax.set_title('Sensitivity: normalization, split unit and eligible population'); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(out/'figures'/'sensitivity.png',dpi=170); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4)); c=counts.set_index('element').loc[ELEMENTS]
    ax.bar(ELEMENTS,c.n_identified_label,label='Labeled, material ID'); ax.bar(ELEMENTS,c.n_unidentified_label,bottom=c.n_identified_label,label='Labeled, no material ID'); ax.bar(ELEMENTS,c.n_missing_bader,bottom=c.n_label,label='No Bader label')
    ax.set_ylabel('Spectra'); ax.set_title('Available labels and material provenance'); ax.legend(); fig.tight_layout(); fig.savefig(out/'figures'/'coverage.png',dpi=170); plt.close(fig)
    summary.to_csv(out/'primary_summary.csv')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--inputs',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--workers',type=int,default=4); args=ap.parse_args(); out=args.output; out.mkdir(parents=True,exist_ok=True); (out/'figures').mkdir(exist_ok=True); (out/'diagnostics').mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool: results=list(pool.map(one_element,[(e,str(args.inputs),str(out)) for e in ELEMENTS]))
    joined=[sum([r[i] if isinstance(r[i],list) else [r[i]] for r in results],[]) for i in range(8)]
    counts,runs,pred,partitions,metrics,comparisons,choices,family=joined
    for name,records in [('coverage',counts),('predictions',pred),('partitions',partitions),('metrics',metrics),('comparisons',comparisons),('model_selection',choices),('family_sensitivity',family)]: pd.DataFrame(records).to_csv(out/f'{name}.csv',index=False)
    design={'question':'Q3','question_text':'How much reproducible charge information lies beyond white-line position?','runs':runs,'primary_estimand':'Reduction in equal-material test mean absolute error for Bader charge, conditioned on labeled spectra with known material IDs. Positive favors full spectrum.','candidate_selection':'Minimum validation MAE, grouped equal-material weighting for material splits. No fitting or candidate selection on test records; no validation refit.','full_predictors':'100 released absorption values plus white-line energy (a deterministic spectrum-derived feature); no labels or provenance predictors.','white_line':'Photon energy at first maximum absorption on the released 100-point grid.','partition_method':'Randomly shuffle material IDs (identified_material) or source rows (spectrum); ceil(20%) test, ceil(20%) validation, remainder training. IDs of excluded records do not contribute to training.','seeds':SEEDS,'uncertainty':'4000 paired test-material bootstrap resamples, 95% percentile intervals; models held fixed. Primary split estimates repeated five times; intervals are per split, not pooled as independent.','input_sha256':{f'{el}.jsonl.gz':hashlib.sha256((args.inputs/f'{el}.jsonl.gz').read_bytes()).hexdigest() for el in ELEMENTS},'software':{'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'scipy':scipy.__version__,'platform':platform.platform()}}
    (out/'design.json').write_text(json.dumps(design,indent=2))
    plots(out,pd.DataFrame(counts),pd.DataFrame(comparisons))
    print('Completed:',out,flush=True)
if __name__=='__main__': main()
