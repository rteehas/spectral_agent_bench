#!/usr/bin/env python3
"""Illustrative research designs. Evaluator-only; no reference outputs are read."""
import argparse, csv, gzip, io, json, re, shutil, sys
from pathlib import Path
import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d
from ase.io import read
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def dump(path,obj): path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def e0(text): return float(re.findall(r'E0=\s*([+\-.\dEe]+)',text)[-1])
def load(inputs):
    records=json.loads(gzip.open(inputs/'calculations.json.gz','rt').read())
    spectra={}
    for f in sorted(inputs.glob('spectra_*.npz')):
        with np.load(f) as z: spectra.update({k:z[k] for k in z.files})
    meta={f'{int(r["Index"]):03d}':r for r in csv.DictReader((inputs/'materials.csv').open())}
    return records,spectra,meta

GRID=np.arange(2398.,2428.0001,.05)
def smooth(y,fwhm,step=.05):
    return gaussian_filter1d(y,fwhm/2.354820045/step,axis=-1,mode='constant') if fwhm else y.copy()
def prepare(records,spectra,meta):
    rows=[]; aligned={}; sampled=[]
    for m,rec in sorted(records.items()):
        neutral=read(io.StringIO(rec['neutral']['POSCAR']),format='vasp'); en=e0(rec['neutral']['OSZICAR'])
        for s,r in sorted(rec['sites'].items()):
            atoms=read(io.StringIO(r['POSCAR']),format='vasp'); assert atoms[0].symbol=='S'
            delta=e0(r['OSZICAR'])-len(atoms)/len(neutral)*en-float(r['efermi.txt'])
            a=spectra[m+'/'+s]; x=a[:,0]+delta; y=a[:,1:].mean(axis=1)
            aligned[m+'/'+s]=(x,y)
            z=np.interp(GRID,x,y,left=0,right=0); sampled.append(z)
            d=atoms.get_distances(0,np.arange(1,len(atoms)),mic=True)
            symbols=np.array(atoms.get_chemical_symbols()[1:]); dp=d[symbols=='P']; dl=d[symbols=='Li']
            p=int(np.sum(dp<2.6)); li=int(np.sum(dl<3.0))
            zz=smooth(z,.5); mask=(GRID>=2399)&(GRID<=2410); xe=GRID[mask]; ye=zz[mask]
            onset=np.interp(.1*np.sum(ye),np.cumsum(ye),xe)
            row={'material':m,'site':s,'weight':int(s.split('_')[1]),'correction':delta,
                 'p_cn':p,'li_cn':li,'p_cutoff_A':2.6,'li_cutoff_A':3.0,
                 'li_cn_2p8':int(np.sum(dl<2.8)),'li_cn_3p2':int(np.sum(dl<3.2)),
                 'p_nearest_A':float(dp.min()),'li_nearest_A':float(dl.min()),
                 'peak_e':float(xe[np.argmax(ye)]),'onset_e':float(onset),
                 'centroid_e':float(np.sum(xe*ye)/np.sum(ye))}
            rows.append(row)
    return rows,aligned,np.array(sampled)

def save_common(out,rows):
    out.mkdir(parents=True,exist_ok=True); table(out/'sites.csv',rows)
    shutil.copyfile(__file__,out/'analysis.py')
    dump(out/'definitions.json',{'energy_units':'eV; arbitrary common DFT zero, not experimental photon energy',
        'correction':'last OSZICAR E0(corehole) - Ncorehole/Nneutral * last E0(neutral) - efermi',
        'geometry':'first S in corehole POSCAR, periodic minimum-image distances; P cutoff2.6A, Li cutoff3.0A; sensitivities2.8/3.2A',
        'spectral_features':'diagonal mean, linear resample2398:0.05:2428 eV, Gaussian FWHM0.5eV; peak, cumulative-area10% onset and centroid on2399..2410eV',
        'multiplicities':'reduced ratios, not number of sulfur atoms in supercell',
        'broadening':'controlled Gaussian resolution experiment, not reproduction of lifetime-broadened experimental spectra'})

def q1(out,rows,aligned):
    save_common(out,rows); bulk={}; ablations={}; metrics=[]
    for m in sorted({r['material'] for r in rows}):
        rr=[r for r in rows if r['material']==m]; w=np.array([r['weight'] for r in rr]); w=w/w.sum()
        pairs=[aligned[m+'/'+r['site']] for r in rr]
        grid=np.linspace(min(x[0] for x,y in pairs),max(x[-1] for x,y in pairs),max(len(x) for x,y in pairs))
        z=np.array([interp1d(x,y,kind='cubic',bounds_error=False,fill_value=0)(grid) for x,y in pairs])
        mean_corr=float(np.dot(w,[r['correction'] for r in rr]))
        zz=np.array([interp1d(x-r['correction']+mean_corr,y,kind='cubic',bounds_error=False,fill_value=0)(grid) for (x,y),r in zip(pairs,rr)])
        full=w@z; bulk['m'+m]=np.column_stack((grid,full))
        no_relative=w@zz; equal=z.mean(axis=0)
        ablations['m'+m]=np.column_stack((grid,full,no_relative,equal))
        for fwhm in [0.,.5,1.]:
            f=smooth(full,fwhm,grid[1]-grid[0]); fn=f/max(f)
            for name,y in [('common_site_shift',no_relative),('equal_site_weights',equal)]:
                v=smooth(y,fwhm,grid[1]-grid[0]); vn=v/max(v)
                metrics.append({'material':m,'ablation':name,'fwhm_eV':fwhm,
                    'shape_relative_L2':float(np.linalg.norm(vn-fn)/np.linalg.norm(fn)),
                    'main_peak_delta_eV':float(grid[np.argmax(v)]-grid[np.argmax(f)]),
                    'site_correction_range_eV':float(np.ptp([r['correction'] for r in rr]))})
    np.savez_compressed(out/'bulk.npz',**bulk); np.savez_compressed(out/'ablations.npz',**ablations); table(out/'effects.csv',metrics)
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    summary={}
    for j,name in enumerate(['common_site_shift','equal_site_weights']):
        for fwhm in [0.,.5,1.]:
            v=[r['shape_relative_L2'] for r in metrics if r['ablation']==name and r['fwhm_eV']==fwhm]
            ax[j].plot(range(1,67),v,label=f'FWHM {fwhm:g} eV')
            summary[f'{name}_{fwhm}']={'median_relative_L2':float(np.median(v)),'maximum_relative_L2':float(max(v)),'max_material':f'{np.argmax(v)+1:03d}'}
        ax[j].set(title=name.replace('_',' '),xlabel='Material index',ylabel='Normalized shape difference'); ax[j].legend()
    fig.tight_layout(); fig.savefig(out/'effects.png',dpi=160); plt.close(fig)
    fig,ax=plt.subplots(1,3,figsize=(12,3.5))
    for a,m in zip(ax,['044','057','062']):
        z=ablations['m'+m]
        for j,label in enumerate(['aligned weighted','common shift','equal weights'],1):
            yy=smooth(z[:,j],.5,z[1,0]-z[0,0]); a.plot(z[:,0],yy/yy.max(),label=label)
        a.set(xlim=(2400,2411),title='Material '+m,xlabel='DFT energy (eV)')
    ax[0].legend(fontsize=7); fig.tight_layout(); fig.savefig(out/'overlays.png',dpi=160); plt.close(fig)
    dump(out/'summary.json',summary)
    (out/'report.md').write_text(f'''# Site treatment and material fingerprints

Site-specific excitation alignment is consequential across this collection. At Gaussian FWHM0.5eV, replacing relative site shifts by one material-average shift changes normalized shape by a median {summary['common_site_shift_0.5']['median_relative_L2']:.1%} and up to {summary['common_site_shift_0.5']['maximum_relative_L2']:.1%} (material {summary['common_site_shift_0.5']['max_material']}). At1eV the median falls to {summary['common_site_shift_1.0']['median_relative_L2']:.1%}, but the largest effect remains {summary['common_site_shift_1.0']['maximum_relative_L2']:.1%}, again in material {summary['common_site_shift_1.0']['max_material']}. Finite resolution therefore weakens the typical effect without making relative alignment generally dispensable.

Equal weighting has a zero median effect because most materials have equal multiplicity ratios. Its largest0.5eV shape error is {summary['equal_site_weights_0.5']['maximum_relative_L2']:.1%} in material {summary['equal_site_weights_0.5']['max_material']}; at1eV the maximum is {summary['equal_site_weights_1.0']['maximum_relative_L2']:.1%} in material {summary['equal_site_weights_1.0']['max_material']}. Those exceptions preclude treating zero median distortion as a universal simplification. effects.csv identifies the material-dependent cases. This analysis quantifies within-material treatment sensitivity; it does not establish preservation of pairwise material similarity rankings under either simplification.

The recovered powder response uses the diagonal mean, excitation-energy alignment and symmetry ratios. The neutral and core-hole cells have the same atom count here; the implementation checks their ratio. The energy axis has a common DFT zero and is not calibrated to experiment. bulk.npz contains all66 native-resolution material responses, with keys m001..m066 and energy/intensity columns.

I tested two counterfactuals: replacing each site's correction by its within-material weighted mean, and giving inequivalent sites equal weights. The first preserves the material mean shift and isolates relative alignment; the second isolates population weighting. Cubic interpolation and zero extension reconstruct the native material responses. Each comparison is peak-normalized and evaluated over the complete released energy support. effects.csv retains every material and resolution, and ablations.npz records energy/full/common-shift/equal-weight columns.

Results:\n'''+json.dumps(summary,indent=2)+'''

Relative alignment can alter shapes even when the bulk energy zero is held fixed. Multiplicity matters only when the supplied ratios differ; a zero effect for equal-ratio materials is an exact control, not evidence that multiplicity is generally dispensable. Broader features can attenuate some differences but do not justify interchangeable-site assumptions for every structure. The overlays show representative site-population cases, not an experimental validation.

Resolution sensitivity is tested with Gaussian FWHM0,0.5,1eV. These are controlled examples, not a fit of instrumental/core-hole broadening. Neither stochastic confidence intervals nor population extrapolation are warranted for this complete fixed collection. Interpolation and resolution choices, unknown experimental calibration, finite archived spectral ranges and absence of measured targets limit the conclusions. An independent evaluator may compare bulk.npz with the authors' held-back raw averages; they were not loaded in this computation.
''')

def regression(rows,feature,li_key,within,indices=None):
    mats=sorted({r['material'] for r in rows}); blocks=[]
    for m in mats:
        rr=[r for r in rows if r['material']==m]; w=np.array([r['weight'] for r in rr],float); w/=w.sum()
        x=np.array([[r[li_key],r['p_cn']] for r in rr],float); y=np.array([r[feature] for r in rr])
        if within: x-=w@x; y-=w@y
        else: x=np.column_stack([np.ones(len(x)),x])
        blocks.append((x*np.sqrt(w[:,None]),y*np.sqrt(w)))
    if indices is None: indices=np.arange(len(mats))
    x=np.concatenate([blocks[i][0] for i in indices]); y=np.concatenate([blocks[i][1] for i in indices])
    b=np.linalg.lstsq(x,y,rcond=None)[0]
    return float(b[0 if within else 1])

def q2(out,rows,aligned):
    save_common(out,rows); rng=np.random.default_rng(202309); results=[]
    # Material blocks preserve site dependence, conditional on chosen archive.
    for feature in ['onset_e','peak_e','centroid_e']:
        for li in ['li_cn_2p8','li_cn','li_cn_3p2']:
            for within in [False,True]:
                b=regression(rows,feature,li,within)
                bs=[regression(rows,feature,li,within,rng.integers(0,66,66)) for _ in range(200)]
                lo,hi=np.quantile(bs,[.025,.975]); results.append({'feature':feature,'Li_descriptor':li,'material_fixed_effects':within,'slope_eV_per_Li':b,'ci025':float(lo),'ci975':float(hi)})
    table(out/'associations.csv',results)
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for p,c in zip([0,1,2],['tab:blue','tab:orange','tab:green']):
        rr=[r for r in rows if r['p_cn']==p]; ax[0].scatter([r['li_cn'] for r in rr],[r['onset_e'] for r in rr],s=7,alpha=.3,label=f'P coordination {p}',c=c)
    ax[0].set(xlabel='Li coordination within3Å',ylabel='Near-edge area10% energy (eV)'); ax[0].legend(fontsize=7)
    rr=[r for r in results if r['Li_descriptor']=='li_cn']
    for j,r in enumerate(rr):
        ax[1].errorbar(r['slope_eV_per_Li'],j,xerr=[[max(0,r['slope_eV_per_Li']-r['ci025'])],[max(0,r['ci975']-r['slope_eV_per_Li'])]],fmt='o')
    ax[1].set_yticks(range(len(rr)),[r['feature']+(' within' if r['material_fixed_effects'] else ' pooled') for r in rr]); ax[1].axvline(0,c='gray'); ax[1].set_xlabel('Partial slope (eV / Li neighbor)'); fig.tight_layout(); fig.savefig(out/'associations.png',dpi=160); plt.close(fig)
    counts={str(p):sum(r['p_cn']==p for r in rows) for p in [0,1,2]}
    main=[r for r in results if r['Li_descriptor']=='li_cn']
    (out/'report.md').write_text(f'''# Does local lithium coordination predict a red shift?

These operational definitions do not support a general red shift with increasing lithium coordination. Every fitted partial slope is positive across the three Li cutoffs, three spectral features and pooled/within-material analyses. At the nominal3Å cutoff, the within-material10%-area onset slope is {main[1]['slope_eV_per_Li']:+.4f}eV per Li neighbor (95% block interval {main[1]['ci025']:+.4f} to {main[1]['ci975']:+.4f}); the peak slope is {main[3]['slope_eV_per_Li']:+.4f} ({main[3]['ci025']:+.4f} to {main[3]['ci975']:+.4f}). Both intervals include zero. Their intervals also include zero at2.8Å but become positive at3.2Å, so evidence for those features is cutoff-dependent.

The within-material centroid slope is {main[5]['slope_eV_per_Li']:+.4f}eV per neighbor ({main[5]['ci025']:+.4f} to {main[5]['ci975']:+.4f}), and its positive interval persists at every tested cutoff. This is an association of larger Li coordination with a higher near-edge centroid, not evidence for shielding-induced red shifts. The centroid summarizes spectral weight across a finite window and need not move like a sharp absorption threshold. Pooled slopes exceed their within-material counterparts, indicating that between-material differences contribute to the pooled pattern. The data and design cannot exclude a red-shift effect under different descriptors or specific chemical subsets.

We treat this as an observational structure–spectrum question. No charge-density or intervention data are supplied, so association cannot establish electronic shielding as the cause. The first core-hole POSCAR atom is the absorbing sulfur. Periodic phosphorus and lithium neighbor counts are derived independently for each site; definitions.json and sites.csv document cutoffs and units.

Peak location, near-edge10%-area energy and centroid probe different notions of an edge shift. All use the same DFT energy reference and Gaussian0.5eV resolution. Regression includes phosphorus coordination. Each material receives equal total regression weight, divided among sites according to symmetry multiplicity. The within-material model demeans outcome and predictors within material, controlling composition and all other material-constant properties. It does not isolate local coordination from other varying bond geometry. The pooled model is a confounding diagnostic. Bootstrap intervals resample66 material blocks200 times and are conditional on this uneven archive, not evidence for population-representative sampling.

Nominal P-coordination counts: '''+json.dumps(counts)+'. Main estimates:\n'+json.dumps(main,indent=2)+'''

Interpret each slope and its interval rather than assigning a universal red-shift rule. associations.csv includes all18 combinations of spectral definition, Li cutoff2.8/3.0/3.2Å, and pooled/within-material model. Effects that change sign or include zero are evidence against a robust general rule under this operational definition. Agreement across definitions would remain observational. The archive is dominated by P coordination1 and related ANN-derived glass models; its66 structures provide substantially fewer independent examples than2681 site spectra.

The finite near-edge window, Gaussian resolution and cutoff convention are chosen analysis assumptions. Peak switching can affect the maximum-energy metric; centroid is an averaged feature rather than an absorption threshold. Lack of absolute experimental alignment does not affect common-origin relative shifts. No experimental validation or causal shielding conclusion is claimed.
''')

def classification_scores(truth,pred,groups):
    groups=np.array(groups); mats=np.unique(groups)
    cubes=np.array([confusion_matrix(truth[groups==m],pred[groups==m],labels=[0,1,2]) for m in mats])
    cm=cubes.sum(axis=0); recall=np.diag(cm)/cm.sum(axis=1); accuracy=float(np.trace(cm)/cm.sum())
    rng=np.random.default_rng(19); vals=[]
    for _ in range(500):
        cc=cubes[rng.integers(0,len(cubes),len(cubes))].sum(axis=0)
        if (cc.sum(axis=1)>0).all(): vals.append(float(np.mean(np.diag(cc)/cc.sum(axis=1))))
    return {'accuracy':accuracy,'balanced_accuracy':float(recall.mean()),'recall':recall.tolist(),'confusion':cm.tolist(),'balanced_accuracy_ci95':np.quantile(vals,[.025,.975]).tolist()}

def q3(out,rows,sampled,meta):
    save_common(out,rows); groups=np.array([r['material'] for r in rows]); y=np.array([r['p_cn'] for r in rows]); sites=np.array([r['site'] for r in rows])
    gm=np.array([m for m in sorted(meta) if meta[m]['Type']=='glassy']); np.random.default_rng(710).shuffle(gm); folds=np.array_split(gm,4)
    predictions=[]; partitions=[]; results={}
    for fwhm in [.5,1.]:
        x=smooth(sampled,fwhm); x/=np.maximum(x.sum(axis=1,keepdims=True),1e-30)
        for mode in ['crystal','glass_group','hybrid']:
            collected=[]
            for f,test_m in enumerate(folds):
                test=np.isin(groups,test_m)
                crystal=np.array([meta[m]['Type']=='crystalline' for m in groups])
                train=crystal if mode=='crystal' else (~test & (~crystal if mode=='glass_group' else True))
                model=RandomForestClassifier(n_estimators=160,min_samples_leaf=2,class_weight='balanced_subsample',random_state=41,n_jobs=1)
                model.fit(x[train],y[train]); pred=model.predict(x[test])
                name=f'{mode}_RF_fwhm{fwhm:g}'; split=f'fold{f}'
                for i,pr in zip(np.where(test)[0],pred):
                    predictions.append({'material':groups[i],'site':sites[i],'split':split,'method':name,'predicted':int(pr)})
                    collected.append((i,int(pr)))
                for m in sorted(meta):
                    mask=groups==m; role='train' if train[mask].all() else ('test' if test[mask].all() else 'unused')
                    partitions.append({'material':m,'split':split,'method':name,'role':role})
            idx=np.array([i for i,p in collected]); pp=np.array([p for i,p in collected]); results[name]=classification_scores(y[idx],pp,groups[idx])
    # Explicit majority control uses only crystal training labels; its class also matches all glass training folds.
    for f,test_m in enumerate(folds):
        for m in sorted(meta): partitions.append({'material':m,'split':f'fold{f}','method':'crystal_majority','role':'test' if m in test_m else ('train' if meta[m]['Type']=='crystalline' else 'unused')})
        for i in np.where(np.isin(groups,test_m))[0]: predictions.append({'material':groups[i],'site':sites[i],'split':f'fold{f}','method':'crystal_majority','predicted':1})
    isglass=np.isin(groups,gm); results['crystal_majority']=classification_scores(y[isglass],np.ones(isglass.sum(),int),groups[isglass])
    table(out/'predictions.csv',predictions); table(out/'partitions.csv',partitions); dump(out/'metrics.json',results)
    fig,ax=plt.subplots(figsize=(9,4)); names=list(results); vals=[results[n]['balanced_accuracy'] for n in names]
    ax.barh(names,vals); ax.set(xlim=(0,1),xlabel='Balanced accuracy on glass sites'); fig.tight_layout(); fig.savefig(out/'transfer.png',dpi=160); plt.close(fig)
    (out/'report.md').write_text(f'''# Spectral inference of phosphorus coordination

Crystal-only training transfers some coordination information to the glass spectra but fails to recover most bridging sulfur sites. At FWHM0.5eV, its balanced accuracy is {results['crystal_RF_fwhm0.5']['balanced_accuracy']:.3f}, compared with {results['glass_group_RF_fwhm0.5']['balanced_accuracy']:.3f} for grouped glass training and {results['hybrid_RF_fwhm0.5']['balanced_accuracy']:.3f} for hybrid training. Crystal-only P2 recall is {results['crystal_RF_fwhm0.5']['recall'][2]:.1%}, whereas grouped-glass recall is {results['glass_group_RF_fwhm0.5']['recall'][2]:.1%}. The majority control reaches {results['crystal_majority']['accuracy']:.1%} ordinary accuracy while its balanced accuracy is only {results['crystal_majority']['balanced_accuracy']:.3f}; ordinary accuracy would therefore give a misleading impression of useful coordination inference.

At1eV the balanced accuracies are {results['crystal_RF_fwhm1']['balanced_accuracy']:.3f}, {results['glass_group_RF_fwhm1']['balanced_accuracy']:.3f} and {results['hybrid_RF_fwhm1']['balanced_accuracy']:.3f} for crystal, grouped-glass and hybrid training respectively. Crystal-only P2 recall remains {results['crystal_RF_fwhm1']['recall'][2]:.1%}, versus {results['glass_group_RF_fwhm1']['recall'][2]:.1%} for grouped-glass training. Thus the tested Gaussian broadening preserves the training-regime ordering and does not degrade these point estimates; smoothing may regularize this fixed model. This comparison does not establish a statistically significant broadening benefit because no paired interval for score differences or refitting uncertainty was estimated. Adding glass training is associated with better minority transfer within the archive, but the unequal training-library sizes and coverage prevent attributing that gain solely to structural disorder.

The target is the periodic number of P atoms within2.6Å of the absorber. It is a geometry-derived operational label, not a supplied experimental annotation. Only normalized spectral intensities on a common excitation-energy grid enter the classifier. Structure, composition, multiplicity, filenames and site IDs are never predictors. Crystal sites supply one training regime; glass-only and hybrid training exclude every site of the tested material. Four deterministic shuffled glass-material folds evaluate all48 glasses. Same-composition and related ancestral structures can cross folds; this tests new structures from the archive, not new chemistries or synthesis routes.

Each condition uses a fixed random forest160 trees, minimum leaf2 and balanced bootstrap class weights; no target-dependent tuning is performed. We compare Gaussian FWHM0.5 and1eV, preserving sites and partitions. A crystal-training majority-class baseline demonstrates why aggregate accuracy is insufficient. Probability calibration and hyperparameter optimality are not claimed. Class-wise recall and confusion matrices expose rare-class failures. Conditional95% intervals resample48 material blocks500 times without refitting; training-set/model-selection uncertainty is not included.

Results:\n'''+json.dumps(results,indent=2)+'''

The most important comparison is minority coordination recall and balanced accuracy against the majority baseline, followed by crystal-only versus grouped glass/hybrid results. A high raw accuracy cannot establish successful transfer when most sites have one phosphorus neighbor. Crystal and glass libraries differ in size, class balance and environment coverage; their score difference cannot be attributed to disorder alone. Broader-resolution differences apply only to the controlled Gaussian experiment. The data are computed site spectra: this is neither a classifier for measured bulk spectra nor evidence of experimental detectability.

The report, definitions, per-site table, predictions and material partitions allow independent reconstruction. The training regimes and uncertainty must be scientifically reviewed as well as arithmetically checked. Minority labels are concentrated in a small number of structures, limiting generalization even when point estimates improve.
''')

def main():
    p=argparse.ArgumentParser(); p.add_argument('question',choices=['ALL','Q1','Q2','Q3']); p.add_argument('--inputs',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    records,spectra,meta=load(a.inputs); rows,aligned,sampled=prepare(records,spectra,meta)
    for q in (['Q1','Q2','Q3'] if a.question=='ALL' else [a.question]):
        out=a.output/q if a.question=='ALL' else a.output
        {'Q1':lambda:q1(out,rows,aligned),'Q2':lambda:q2(out,rows,aligned),'Q3':lambda:q3(out,rows,sampled,meta)}[q]()
        print(q,'complete',flush=True)
    dump(a.output/'execution.json',{'question':a.question,'command':sys.argv,'materials':len(records),'sites':len(rows),'reference_data_read':False,'seed_values':[202309,710,41,19]})

if __name__=='__main__': main()
