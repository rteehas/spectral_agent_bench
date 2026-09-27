#!/usr/bin/env python3
"""Evaluator-only worked research workflow. Reads only exported native raw records.

The operational definitions below are candidate choices, not solver prescriptions.
"""
import argparse, csv, gzip, hashlib, json, shutil, warnings
from collections import defaultdict, Counter
from pathlib import Path
import numpy as np
import spglib
from scipy.ndimage import gaussian_filter1d
from scipy.stats import spearmanr
from pymatgen.core import Structure
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import balanced_accuracy_score, f1_score, confusion_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ELEMENTS=('Ti','V','Cr','Mn','Fe','Co','Ni','Cu')
CONFIG={'symprec_A':0.01,'angle_tolerance_degrees':5.0,
 'neighbor_radius_A':6.0,'shell_ratio':1.2,'shell_ratio_sensitivity':[1.15,1.25],
 'angular_rms_cosine_max':0.15,'radial_cv_max':0.12,
 'geometry':'All periodic neighbors at distance <= shell_ratio times nearest distance; ideal sorted pair cosine RMS for tetrahedral CN4 or octahedral CN6, plus radial CV. Other geometries are retained in audit but not binary comparison.',
 'origin':'Each edge first released photon energy; matched excess energy window, not independently inferred experimental thresholds.',
 'area_windows_eV':[[3.,23.],[3.,33.],[3.,43.]],'area_method':'Piecewise-linear trapezoidal integral of raw positive intensity; no continuum subtraction or L3/L2 statistical weighting.',
 'feature_grid_eV':[3.,43.,0.5],'resolution_FWHM_eV':[0.,1.],
 'broadening':'Gaussian after linear interpolation at 0.1eV; nearest extension only for convolution; metric/features exclude first/last3eV. No extrapolation for stored material responses.',
 'composition_key':'Sorted elemental reduced integer composition, using pymatgen reduced_composition; MP identifiers are not composition groups.',
 'random_seed':20260926}

def dump(path,obj): path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def table(path,rows):
    assert rows, str(path)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def f(x): return float(x)
def smooth(y,width,step):
    return gaussian_filter1d(y,width/2.354820045/step,mode='nearest') if width else y.copy()
def integrate(x,y,lo,hi):
    if x[0]>lo or x[-1]<hi: return np.nan
    xx=np.r_[lo,x[(x>lo)&(x<hi)],hi]
    return f(np.trapezoid(np.interp(xx,x,y),xx))
def composition_key(s):
    c=s.composition.reduced_composition.get_el_amt_dict()
    return '|'.join(f'{k}:{v:g}' for k,v in sorted(c.items()))
def prepare(inputs):
    structures={}; raw=[]; seen=set()
    for path in sorted(inputs.glob('*.jsonl.gz')):
        with gzip.open(path,'rt') as fd:
            for line in fd:
                r=json.loads(line); m=r['mp-id']; i=int(r['absorbing_atom']); edge=r['edge']
                if r['name'] in seen: raise ValueError('Duplicate source name '+r['name'])
                seen.add(r['name']); sd=r['structure']; el=sd['sites'][i]['species'][0]['element']
                if el not in ELEMENTS: raise ValueError('Unexpected element '+el)
                physical={'matrix':sd['lattice']['matrix'],'sites':[(z['abc'],z['species']) for z in sd['sites']]}
                sh=hashlib.sha256(json.dumps(physical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                if m not in structures: structures[m]={'dict':sd,'hash':sh,'consistent':True}
                if sh!=structures[m]['hash']:structures[m]['consistent']=False
                a=np.asarray(r['spectrum'],float)
                valid=a.ndim==2 and a.shape[0]==2 and a.shape[1]>=4 and np.isfinite(a).all() and np.all(np.diff(a[0])>0) and np.all(a[1]>=0) and np.max(a[1])>0
                raw.append({'name':r['name'],'material':m,'element':el,'site':i,'edge':edge,'x':a[0],'y':a[1],
                    'valid':bool(valid),'same_structure':sh==structures[m]['hash']})
    if not raw: raise ValueError('No *.jsonl.gz raw inputs')
    print(f'Loaded {len(raw)} records / {len(structures)} materials',flush=True)
    mats=defaultdict(list)
    for r in raw:
        r['same_structure']=structures[r['material']]['consistent']
        mats[r['material']].append(r)
    geometry=[]
    for j,(m,ss) in enumerate(sorted(structures.items())):
        s=Structure.from_dict(ss.pop('dict')); syms=[z.specie.symbol for z in s]
        cell=(s.lattice.matrix,s.frac_coords,[z.specie.Z for z in s])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            ds=spglib.get_symmetry_dataset(cell,symprec=CONFIG['symprec_A'],angle_tolerance=CONFIG['angle_tolerance_degrees'])
        eq=np.asarray(ds.equivalent_atoms) if ds is not None else np.arange(len(s))
        counts=Counter(eq); ss['equiv']=eq.tolist(); ss['symbols']=syms; ss['symmetry_success']=ds is not None
        ss['composition_key']=composition_key(s)
        ss['equiv_sensitivity']={}
        for tol in [.001,.1]:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                alt=spglib.get_symmetry_dataset(cell,symprec=tol,angle_tolerance=CONFIG['angle_tolerance_degrees'])
            ss['equiv_sensitivity'][str(tol)]=np.asarray(alt.equivalent_atoms).tolist() if alt is not None else None
        for el,i in sorted({(r['element'],r['site']) for r in mats[m]}):
            ns=s.get_neighbors(s[i],CONFIG['neighbor_radius_A'])
            ns=sorted([n for n in ns if n.nn_distance>1.e-6],key=lambda n:n.nn_distance)
            if not ns: raise ValueError(f'No neighbors {m} {i}')
            dmin=ns[0].nn_distance
            def label(ratio,angular=CONFIG['angular_rms_cosine_max']):
                nn=[n for n in ns if n.nn_distance<=ratio*dmin+1.e-8]
                dd=np.array([n.nn_distance for n in nn]); vectors=np.array([n.coords-s[i].coords for n in nn]); u=vectors/dd[:,None]
                dots=np.sort((u@u.T)[np.triu_indices(len(nn),1)])
                cn=len(nn); cv=f(dd.std()/dd.mean())
                if cn==4: ideal=np.full(6,-1/3); candidate='tetrahedral'
                elif cn==6: ideal=np.r_[[-1.]*3,[0.]*12]; candidate='octahedral'
                else: ideal=None; candidate='other'
                rms=f(np.sqrt(np.mean((dots-ideal)**2))) if ideal is not None else None
                lab=candidate if rms is not None and rms<=angular and cv<=CONFIG['radial_cv_max'] else 'other'
                return lab,cn,rms,cv,dd,nn
            lab,cn,rms,cv,dd,nn=label(CONFIG['shell_ratio'])
            ligand='|'.join(sorted({n.specie.symbol for n in nn}))
            native=sorted([r for r in mats[m] if r['element']==el and r['site']==i],key=lambda r:r['edge'],reverse=True)
            g={'name':native[0]['name'],'material':m,'element':el,'site':i,'composition_key':ss['composition_key'],
                'geometry':lab,'source_consistent':int(ss['consistent']),'cn':cn,'angular_rms':rms if rms is not None else '', 'radial_cv':cv,
                'bond_length_A':f(dd.mean()),'nearest_distance_A':f(dmin),'ligand_family':ligand,
                'absorber_fraction':f(s.composition[el]/len(s)),
                'geometry_shell_1p15':label(1.15)[0],'geometry_shell_1p25':label(1.25)[0],
                'geometry_angular_0p10':label(1.2,.10)[0],
                'multiplicity':int(counts[eq[i]]),'symmetry_class':int(eq[i])}
            geometry.append(g)
        if (j+1)%1000==0: print('Geometry',j+1,flush=True)
    geom={(g['material'],g['element'],g['site']):g for g in geometry}
    for r in raw:
        g=geom[(r['material'],r['element'],r['site'])]; r['multiplicity']=g['multiplicity'];r['symmetry_class']=g['symmetry_class']
    print('Geometry counts',Counter(g['geometry'] for g in geometry),flush=True)
    return raw,structures,geometry

def base(out,geometry=None):
    out.mkdir(parents=True,exist_ok=True);shutil.copyfile(__file__,out/'analysis.py');dump(out/'definitions.json',CONFIG)
    if geometry is not None: table(out/'geometry.csv',geometry)

def q1(out,raw,structures,geometry):
    base(out); groups=defaultdict(list)
    for r in raw: groups[(r['material'],r['element'],r['edge'])].append(r)
    audit=[];coverage=[];responses={};ablations={};effects=[];symmetry=[]
    for (m,el,edge),rr in sorted(groups.items()):
        ss=structures[m]; needed={int(ss['equiv'][i]) for i,a in enumerate(ss['symbols']) if a==el}
        present=[r['symmetry_class'] for r in rr]; reason=[]
        if not ss['symmetry_success']: reason.append('symmetry_failure')
        if set(present)!=needed: reason.append('incomplete_symmetry_coverage')
        if len(set(present))!=len(present): reason.append('duplicate_symmetry_class')
        if not all(r['valid'] for r in rr): reason.append('invalid_spectrum')
        if not all(r['same_structure'] for r in rr): reason.append('inconsistent_structure')
        lo=max(r['x'][0] for r in rr);hi=min(r['x'][-1] for r in rr)
        if hi-lo<6:reason.append('insufficient_common_support')
        include=not reason
        for tol,equ in ss['equiv_sensitivity'].items():
            if equ is None:
                symmetry.append({'material':m,'element':el,'edge':edge,'symprec_A':float(tol),'same_equivalence_partition':0,'complete_coverage':0,'multiplicity_changes':-1})
            else:
                nneed={equ[i] for i,a in enumerate(ss['symbols']) if a==el}; npresent=[equ[r['site']] for r in rr]; cc=Counter(equ)
                symmetry.append({'material':m,'element':el,'edge':edge,'symprec_A':float(tol),'same_equivalence_partition':int(equ==ss['equiv']),'complete_coverage':int(set(npresent)==nneed and len(set(npresent))==len(npresent)),'multiplicity_changes':sum(cc[equ[r['site']]]!=r['multiplicity'] for r in rr)})
        coverage.append({'material':m,'element':el,'edge':edge,'included':int(include),'reason':';'.join(reason),
            'representatives':len(rr),'expected_classes':len(needed),'represented_atoms':sum(r['multiplicity'] for r in rr),
            'element_atoms':sum(a==el for a in ss['symbols']),'common_min_eV':f(lo),'common_max_eV':f(hi)})
        for r in rr:
            audit.append({k:r[k] for k in ['name','material','element','site','edge','multiplicity','symmetry_class']}|{'included':int(include),'reason':';'.join(reason)})
        if not include:continue
        key=f'{m}__{el}__{edge}';grid=np.unique(np.concatenate([r['x'][(r['x']>=lo)&(r['x']<=hi)] for r in rr]+[np.array([lo,hi])]))
        yy=np.array([np.interp(grid,r['x'],r['y']) for r in rr]);ww=np.array([r['multiplicity'] for r in rr],float);ww/=ww.sum()
        full=ww@yy; equal=yy.mean(axis=0); representative=min(range(len(rr)),key=lambda j:rr[j]['site']);single=yy[representative]
        responses[key]=np.c_[grid,full];ablations[key]=np.c_[grid,full,equal,single]
        if len(rr)==1:continue
        fine=np.arange(lo,hi+.00001,.1);fine=fine[fine<=hi]
        baseline=np.interp(fine,grid,full)
        for width in [0.,1.,2.]:
            target=smooth(baseline,width,.1);mask=(fine>=lo+3)&(fine<=hi-3)
            tn=target[mask]/np.trapezoid(target[mask],fine[mask])
            for name,other in [('equal_sites',equal),('first_representative',single)]:
                y=smooth(np.interp(fine,grid,other),width,.1);yn=y[mask]/np.trapezoid(y[mask],fine[mask])
                effects.append({'material':m,'element':el,'edge':edge,'approximation':name,'fwhm_eV':width,'n_sites':len(rr),
                    'multiplicity_cv':f(np.std(ww)/np.mean(ww)),'relative_shape_L2':f(np.linalg.norm(yn-tn)/np.linalg.norm(tn)),
                    'relative_area_error':f(np.trapezoid(y[mask],fine[mask])/np.trapezoid(target[mask],fine[mask])-1),
                    'peak_shift_eV':f(fine[mask][np.argmax(y[mask])]-fine[mask][np.argmax(target[mask])]),
                    'representative_site':rr[representative]['site']})
    table(out/'sites.csv',audit);table(out/'coverage.csv',coverage);table(out/'effects.csv',effects);table(out/'symmetry_sensitivity.csv',symmetry)
    np.savez_compressed(out/'responses.npz',**responses);np.savez_compressed(out/'ablations.npz',**ablations)
    stats=[]
    for name in ['equal_sites','first_representative']:
        for width in [0.,1.,2.]:
            rr=[r for r in effects if r['approximation']==name and r['fwhm_eV']==width]; v=np.array([r['relative_shape_L2'] for r in rr]); order=np.argsort(v)
            stats.append({'approximation':name,'fwhm_eV':width,'n_multisite_responses':len(rr),'median':f(np.median(v)),
                'q95':f(np.quantile(v,.95)),'max':f(v.max()),'fraction_over_5pct':f(np.mean(v>.05)),
                'worst_material':rr[order[-1]]['material'],'worst_element':rr[order[-1]]['element'],'worst_edge':rr[order[-1]]['edge']})
    rankings=[]
    for name in ['equal_sites','first_representative']:
        values={}
        for width in [0.,1.,2.]:
            scores=defaultdict(float)
            for r in effects:
                if r['approximation']==name and r['fwhm_eV']==width:scores[r['material']]=max(scores[r['material']],round(r['relative_shape_L2'],12))
            values[width]=scores
        material=sorted(values[0.]);v0=np.array([values[0.][m] for m in material]);top0=set(sorted(material,key=lambda m:(-values[0.][m],m))[:50])
        for width in [1.,2.]:
            vv=np.array([values[width][m] for m in material]);top=set(sorted(material,key=lambda m:(-values[width][m],m))[:50])
            rankings.append({'approximation':name,'fwhm_eV':width,'n_materials':len(material),'spearman_vs_unbroadened':f(spearmanr(v0,vv).statistic),'top50_overlap':len(top&top0),'top50_jaccard':len(top&top0)/len(top|top0),'worst_material':max(material,key=lambda m:values[width][m])})
    table(out/'ranking_sensitivity.csv',rankings)
    summary={'raw_records':len(raw),'complete_responses':len(responses),'excluded_responses':sum(not r['included'] for r in coverage),
        'exclusion_reasons':dict(Counter(r['reason'] for r in coverage if not r['included'])),'symmetry_sensitivity':{tol:{'changed_equivalence_groups':sum(not r['same_equivalence_partition'] for r in symmetry if r['symprec_A']==tol),'changed_multiplicity_records':sum(max(0,r['multiplicity_changes']) for r in symmetry if r['symprec_A']==tol)} for tol in [.001,.1]},'statistics':stats,'resolution_rank_stability':rankings}
    dump(out/'summary.json',summary)
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    for ax,name in zip(axs,['equal_sites','first_representative']):
        for width in [0.,1.,2.]:
            v=np.sort([r['relative_shape_L2'] for r in effects if r['approximation']==name and r['fwhm_eV']==width])
            ax.plot(v,np.arange(1,len(v)+1)/len(v),label=f'{width:g} eV')
        ax.set(xlabel='Area-normalized relative L2 error',ylabel='Fraction of multi-site responses',title=name.replace('_',' '));ax.legend();ax.set_xscale('symlog',linthresh=.001)
    fig.tight_layout();fig.savefig(out/'sensitivity.png',dpi=160);plt.close(fig)
    ranked=sorted([r for r in effects if r['approximation']=='first_representative' and r['fwhm_eV']==1.],key=lambda r:r['relative_shape_L2'],reverse=True)[:3]
    fig,axs=plt.subplots(1,3,figsize=(12,3.5))
    for ax,r in zip(axs,ranked):
        a=ablations[f"{r['material']}__{r['element']}__{r['edge']}"]
        for j,l in [(1,'population weighted'),(2,'equal sites'),(3,'first site')]:ax.plot(a[:,0],a[:,j]/np.trapezoid(a[:,j],a[:,0]),label=l)
        ax.set(title=f"{r['material']} {r['element']} {r['edge']}",xlabel='Photon energy (eV)')
    axs[0].legend(fontsize=7);fig.tight_layout();fig.savefig(out/'examples.png',dpi=160);plt.close(fig)
    a=[s for s in stats if s['fwhm_eV']==1.]
    (out/'report.md').write_text(f'''# Inequivalent sites and material fingerprints

Reconstruction yields {len(responses)} complete material/element/edge responses and excludes {summary['excluded_responses']} groups. At 1 eV Gaussian FWHM, equal-site averaging has median shape error {a[0]['median']:.2%} and 95th percentile {a[0]['q95']:.2%} among {a[0]['n_multisite_responses']} complete multisite edge responses. Choosing the lowest-index representative has median {a[1]['median']:.2%} and 95th percentile {a[1]['q95']:.2%}. The fractions exceeding 5% are {a[0]['fraction_over_5pct']:.2%} and {a[1]['fraction_over_5pct']:.2%}, respectively. Thus the validity of either simplification is material dependent; a small median does not validate it in every material.

The symmetry equivalence classes and their atom counts come from the released periodic structure using spglib (0.01 Å, 5 degrees). Each included edge must contain one valid record for every equivalence class of its absorbing element. Multiplicities are normalized only after this completeness test. We do not silently renormalize a partial set into a complete response. coverage.csv and sites.csv retain all records and exclusions. Symmetry-failure groups are excluded. Physical lattice/coordinates/species equality is audited; optional metadata differences do not invalidate a structure, while all records of a conflicting structure identifier are excluded. Symmetry tolerances 0.001 and 0.1 Å are re-evaluated in symmetry_sensitivity.csv, including coverage and multiplicity changes. L2 and L3 are reconstructed separately at their physical photon energies; their finite energy ranges need not overlap, so an unmeasured zero-filled combined spectrum is not manufactured.

responses.npz stores energy/intensity columns on the union of native knots restricted to the intersection of all included site's supports. This is an exact piecewise-linear population average on measured support. No edge is individually normalized before averaging. The equal-site ablation changes only population weights; the representative ablation takes the lowest-index absorbing site, an explicit arbitrary site-choice rule. ablations.npz stores energy/full/equal/representative columns.

The shape metric compares area-normalized spectra on a 0.1 eV grid after a controlled Gaussian FWHM 0, 1 or 2 eV convolution; the first and last 3 eV are excluded to reduce boundary-extension effects. Amplitude error and peak displacement are also retained in effects.csv. Single-site groups are exact zero-effect controls and excluded from the sensitivity distribution so they cannot dilute the multisite question. Equal multiplicities likewise force exact equal-site invariance. We show extreme representative failures rather than selecting visually appealing average cases.

The collection is fixed, so these are descriptive distributions rather than sampling-population confidence intervals. Broadening experiments test finite-resolution robustness; they do not fit an experimental instrument. For each approximation, ranking_sensitivity.csv ranks materials by their largest edge/element shape distortion and compares 1/2 eV with unbroadened spectra using Spearman correlation and top-50 overlap. This directly tests whether resolution changes the high-risk material list. The arbitrary representative rule does not show that every possible chosen site is equally poor. Absolute FEFF amplitudes, symmetry tolerance, support truncation and the dataset's chemical selection bound the conclusions. Geometry and magnetic/spin populations are not inferred from these reconstructions.

Full numerical summary:\n\n```json\n'''+json.dumps(summary,indent=2)+'\n```\n')

def paired(raw,geometry):
    by=defaultdict(dict)
    for r in raw:by[(r['material'],r['element'],r['site'])][r['edge']]=r
    rows=[]; pairs={}; audit=[]
    for g in geometry:
        key=(g['material'],g['element'],g['site']); ee=by[key]
        reason=[]
        if not {'L2','L3'}<=set(ee):reason.append('missing_paired_edge')
        if not all(r['valid'] and r['same_structure'] for r in ee.values()):reason.append('invalid_or_inconsistent_record')
        if not reason:
            for edge,r in ee.items():
                if r['x'][-1]-r['x'][0]<46.:reason.append('short_spectral_support')
        if not reason:pairs[g['name']]=(ee['L2'],ee['L3'])
        for edge,r in ee.items():audit.append({k:r[k] for k in ['name','material','element','site','edge','multiplicity']}|{'included':int(not reason),'reason':';'.join(reason),'geometry':g['geometry']})
        row=g.copy();row['included']=int(not reason);row['reason']=';'.join(reason);rows.append(row)
    return rows,pairs,audit

def cluster_fit(rows,ykey,geometry_key,adjustment,nboot=400):
    rr=[r for r in rows if r[geometry_key] in ['tetrahedral','octahedral'] and np.isfinite(r[ykey])]
    if adjustment=='unadjusted':strata=['all']*len(rr)
    elif adjustment=='element':strata=[r['element'] for r in rr]
    elif adjustment=='exact_composition':strata=[r['element']+'::'+r['composition_key'] for r in rr]
    else:strata=[r['element']+'::'+r['ligand_family'] for r in rr]
    groups=defaultdict(list)
    for i,st in enumerate(strata):groups[st].append(i)
    eligible=set(st for st,ii in groups.items() if len({rr[i][geometry_key] for i in ii})==2)
    keep=[i for i,st in enumerate(strata) if st in eligible];rr=[rr[i] for i in keep];strata=[strata[i] for i in keep]
    if not rr:return None
    levels=sorted(set(strata)); lookup={v:i for i,v in enumerate(levels)}
    z=np.array([[float(r[geometry_key]=='tetrahedral'),r['bond_length_A'],r['absorber_fraction']] for r in rr])
    # Fixed-effect absorb chemistry before estimating linear nuisance effects. Cluster bootstrap
    # resamples material sufficient statistics and refits all fixed effects each time.
    if adjustment=='unadjusted':z=z[:,:1]
    z[:,1:]=(z[:,1:]-z[:,1:].mean(axis=0))/np.maximum(z[:,1:].std(axis=0),1.e-12)
    st=np.array([lookup[st] for st in strata]);x=z;y=np.array([r[ykey] for r in rr]);w=np.array([r['multiplicity'] for r in rr],float)
    wm=defaultdict(float)
    for r,v in zip(rr,w):wm[r['material']]+=v
    w/=np.array([wm[r['material']] for r in rr])
    mats=sorted({r['material'] for r in rr}); mid={m:i for i,m in enumerate(mats)};mi=np.array([mid[r['material']] for r in rr]);p=x.shape[1]
    def solve(k):
        ww=w*k[mi];sw=np.bincount(st,weights=ww,minlength=len(levels));den=np.maximum(sw,1.e-30)
        sx=np.array([np.bincount(st,weights=ww*x[:,j],minlength=len(levels)) for j in range(p)]).T
        sy=np.bincount(st,weights=ww*y,minlength=len(levels))
        xx=x.T@(ww[:,None]*x)-sx.T@(sx/den[:,None]);xy=x.T@(ww*y)-sx.T@(sy/den)
        return f((np.linalg.pinv(xx,rcond=1.e-10)@xy)[0])
    b=solve(np.ones(len(mats)));rng=np.random.default_rng(CONFIG['random_seed']);bb=[]
    for _ in range(nboot):
        k=np.bincount(rng.integers(0,len(mats),len(mats)),minlength=len(mats));bb.append(solve(k))
    ci=np.quantile(bb,[.025,.975])
    return {'feature':ykey,'geometry_definition':geometry_key,'adjustment':adjustment,'n_sites':len(rr),'n_materials':len(mats),'n_chemical_strata':len(levels),
        'tetra_minus_octa_log_ratio':b,'ci025':f(ci[0]),'ci975':f(ci[1]),'bootstrap_replicates':nboot}

def q2(out,raw,structures,geometry):
    base(out,geometry);rows,pairs,audit=paired(raw,geometry);table(out/'sites.csv',audit)
    desc=[]
    for g in rows:
        if not g['included']:continue
        r=g.copy();a,b=pairs[g['name']]
        for lo,hi in CONFIG['area_windows_eV']:
            aa=integrate(a['x']-a['x'][0],a['y'],lo,hi);bb=integrate(b['x']-b['x'][0],b['y'],lo,hi)
            k=f'{int(lo)}_{int(hi)}';r['area_L2_'+k]=aa;r['area_L3_'+k]=bb;r['log_ratio_'+k]=f(np.log(bb/aa))
        r['area_L2']=r['area_L2_3_33'];r['area_L3']=r['area_L3_3_33'];r['log_ratio']=r['log_ratio_3_33'];desc.append(r)
    table(out/'descriptors.csv',desc)
    dm={(r['material'],r['element'],r['site']):r for r in desc};gm={(r['material'],r['element'],r['site']):r for r in geometry}
    for r in audit:
        k=(r['material'],r['element'],r['site']);g=gm[k];d=dm.get(k,{})
        for key in ['cn','angular_rms','radial_cv','bond_length_A','ligand_family','absorber_fraction']:r[key]=g[key]
        for key in ['area_L2','area_L3','log_ratio']:r[key]=d.get(key,'')
    table(out/'sites.csv',audit);assoc=[]
    for adj in ['unadjusted','element','element_ligand','exact_composition']:
        res=cluster_fit(desc,'log_ratio','geometry',adj)
        if res:assoc.append(res)
    for hi in [23,43]:
        for adj in ['element_ligand','exact_composition']:
            res=cluster_fit(desc,f'log_ratio_3_{hi}','geometry',adj)
            if res:assoc.append(res)
    for geo in ['geometry_shell_1p15','geometry_shell_1p25','geometry_angular_0p10']:
        for adj in ['element_ligand','exact_composition']:
            res=cluster_fit(desc,'log_ratio',geo,adj)
            if res:assoc.append(res)
    table(out/'associations.csv',assoc)
    strata=[]
    for el in ELEMENTS:
        for geo in ['tetrahedral','octahedral','other']:
            rr=[r for r in desc if r['element']==el and r['geometry']==geo]
            strata.append({'element':el,'geometry':geo,'n_sites':len(rr),'n_materials':len({r['material'] for r in rr}),
                'median_L3_L2_ratio':f(np.median([np.exp(r['log_ratio']) for r in rr])) if rr else ''})
    table(out/'strata.csv',strata);dump(out/'summary.json',{'paired_sites':len(desc),'geometry_counts':dict(Counter(r['geometry'] for r in desc)),'associations':assoc})
    fig,axs=plt.subplots(1,2,figsize=(14,6.0))
    for j,geo in enumerate(['tetrahedral','octahedral']):
        data=[[np.exp(r['log_ratio']) for r in desc if r['element']==el and r['geometry']==geo] for el in ELEMENTS]
        for i,d in enumerate(data):
            if d:
                q=np.quantile(d,[.25,.5,.75]);axs[0].errorbar(i+(.12 if j else -.12),q[1],yerr=[[q[1]-q[0]],[q[2]-q[1]]],fmt='o',color=['tab:blue','tab:orange'][j],label=geo if i==0 else None)
    axs[0].set_xticks(range(8),ELEMENTS);axs[0].set(ylabel='L3/L2 integrated raw area; median/IQR');axs[0].legend()
    for i,r in enumerate(assoc):axs[1].plot([r['ci025'],r['ci975']],[i,i],c='tab:blue');axs[1].plot(r['tetra_minus_octa_log_ratio'],i,'o',c='tab:blue')
    axs[1].set_yticks(range(len(assoc)),[r['adjustment']+' '+r['feature']+' '+r['geometry_definition'] for r in assoc],fontsize=7);axs[1].axvline(0,c='gray');axs[1].set_xlabel('Tetrahedral − octahedral log area ratio (95% material bootstrap)')
    fig.tight_layout();fig.savefig(out/'associations.png',dpi=160);plt.close(fig)
    exact=next(r for r in assoc if r['adjustment']=='exact_composition' and r['feature']=='log_ratio' and r['geometry_definition']=='geometry')
    main=assoc[2];observed='positive' if main['ci025']>0 else ('negative' if main['ci975']<0 else 'not separated from zero')
    (out/'report.md').write_text(f'''# Local geometry and L3/L2 spectral weight

At fixed reduced composition the tetrahedral-minus-octahedral log area-ratio contrast is {exact['tetra_minus_octa_log_ratio']:+.4f} (95% material-bootstrap interval {exact['ci025']:+.4f} to {exact['ci975']:+.4f}), supported by only {exact['n_sites']} sites in {exact['n_materials']} materials and {exact['n_chemical_strata']} element/composition strata. This limited overlap does not establish a composition-invariant geometry effect.

The more broadly supported element-and-ligand-adjusted contrast is {main['tetra_minus_octa_log_ratio']:+.4f} (95% material-bootstrap interval {main['ci025']:+.4f} to {main['ci975']:+.4f}); it is {observed} under the nominal definitions. This contrast uses {main['n_sites']} sites from {main['n_materials']} materials in {main['n_chemical_strata']} chemistry strata containing both geometries. The paired archive has {len(desc)} sites; geometry counts and element-specific support are reported separately, so the fitted subset is not presented as the whole archive.

Labels are derived from periodic coordinates, never from spectra or file names. A radial first shell at 1.2 times the nearest distance must contain four or six neighbors and meet an angular RMS-cosine distortion tolerance of 0.15 plus radial coefficient of variation <=0.12. Sorted pair cosine patterns distinguish tetrahedral from square-planar CN4 and octahedral from other CN6 arrangements. Sites failing these shape conditions remain other. The finite radius is 6 Å. Tightening/loosening shell ratio to 1.15/1.25 and angular tolerance to 0.10 tests sensitivity. These operational labels favor relatively regular environments; ambiguous or distorted sites are not silently assigned a perfect-polyhedron label.

Each raw spectrum has a nonuniform physical energy grid. We integrate its piecewise-linear cross section from 3 to 33 eV above its first released energy, using the same excess-energy window for both edges. We preserve the supplied absolute relative amplitudes and report ln(area L3 / area L2). Windows 3–23 and 3–43 eV test how the continuum/window definition influences the contrast. The first archived energy is a reproducible FEFF-grid origin, not a measured onset; these are finite-window raw-area ratios, not experimental white-line branching ratios or spin-sum-rule observables. There is no physically justified universal continuum subtraction in these raw arrays, so we do not call the ratio a spin measurement.

We fit weighted linear contrasts with a tetrahedral indicator, standardized mean neighbor distance and absorbing-element atomic fraction. Chemistry fixed effects are first absorbing element, then absorbing element crossed with the set of neighbor species. A further exact reduced-composition fixed-effect comparison holds full elemental stoichiometry constant and reports its smaller overlap population separately. Only chemistry strata containing both shapes support the adjusted geometry coefficient. Multiplicity weights are normalized to give each material total weight one. Confidence intervals resample complete material clusters (400 replicates, fixed seed), refitting all coefficients. Bond length and stoichiometric absorber fraction provide limited chemical/charge proxies; they are not oxidation-state assignments. Ligand identity, element and stoichiometry can still leave residual chemical confounding, so an adjusted association is not causal geometry or spin evidence. Sites of one material are not treated as independent uncertainty units.

associations.csv reports the unadjusted, element-adjusted and element/ligand-adjusted estimates, both alternate windows and all geometry sensitivities. strata.csv displays class coverage by element. Geometry and descriptors are retained for all paired sites; other sites do not enter the binary contrast. The forest plot exposes sign/interval sensitivity without imposing a required positive result. The element/ligand coefficient stays negative over the tested windows and shape choices, while the exact-composition contrast is less precise; the latter prevents treating the broader partial-adjustment association as a universal geometry effect. Element-specific median ratios can have either direction, reinforcing the need to keep pooled and conditional claims distinct. Results are conditional on this archived computational collection, the model's core-hole treatment, finite integration supports and the selected regular-geometry subpopulation.

Numerical contrasts:\n\n```json\n'''+json.dumps(assoc,indent=2)+'\n```\n')

def group_metric_ci(y,p,groups,nboot=500):
    classes=['octahedral','tetrahedral'];ii={x:i for i,x in enumerate(sorted(set(groups)))};cm=np.zeros((len(ii),2,2),int)
    for yy,pp,g in zip(y,p,groups):cm[ii[g],classes.index(yy),classes.index(pp)]+=1
    def score(c):return np.mean(np.diag(c)/c.sum(axis=1)) if np.all(c.sum(axis=1)>0) else np.nan
    rng=np.random.default_rng(CONFIG['random_seed']);scores=[]
    for _ in range(nboot):
        k=np.bincount(rng.integers(0,len(ii),len(ii)),minlength=len(ii));scores.append(score(np.einsum('g,gij->ij',k,cm)))
    return np.nanquantile(scores,[.025,.975]).tolist(),np.array(scores)

def q3(out,raw,structures,geometry):
    base(out,geometry);rows,pairs,audit=paired(raw,geometry)
    rows=[r for r in rows if r['included'] and r['geometry'] in ['tetrahedral','octahedral']]
    eligible={(r['material'],r['element'],r['site']) for r in rows}
    for r in audit:
        site_key=(r['material'],r['element'],r['site'])
        if site_key not in eligible:r['included']=0;r['reason']=r['reason'] or 'outside_regular_binary_geometry'
    table(out/'sites.csv',audit)
    y=np.array([r['geometry'] for r in rows]);groups=np.array([r['composition_key'] for r in rows]);el=np.array([r['element'] for r in rows])
    folds=list(StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=CONFIG['random_seed']).split(np.zeros(len(rows)),y,groups))
    grid=np.arange(3.,43.0001,.5);fine=np.arange(0.,46.0001,.1);features={}
    for width in CONFIG['resolution_FWHM_eV']:
        both=[];only=[]
        for g in rows:
            a,b=pairs[g['name']];arr=[]
            for r in [b,a]:
                yr=smooth(np.interp(fine,r['x']-r['x'][0],r['y']),width,.1);arr.append(np.interp(grid,fine,yr))
            l3,l2=arr;norm=np.trapezoid(l3,grid);only.append(l3/norm);both.append(np.r_[l3,l2]/norm)
        features[f'L3_fwhm{width:g}']=np.array(only);features[f'L23_fwhm{width:g}']=np.array(both)
    predictions=[];partitions=[];method_preds={};importances=[]
    for method,x in features.items():
        pred=np.empty(len(rows),dtype='<U12');print('Train',method,x.shape,flush=True)
        for fold,(train,test) in enumerate(folds):
            assert not set(groups[train])&set(groups[test]);assert len(set(y[train]))==2
            model=RandomForestClassifier(n_estimators=240,max_features='sqrt',min_samples_leaf=2,class_weight='balanced_subsample',random_state=CONFIG['random_seed']+fold,n_jobs=1)
            model.fit(x[train],y[train]);pred[test]=model.predict(x[test])
            for i in test:predictions.append({'name':rows[i]['name'],'material':rows[i]['material'],'element':rows[i]['element'],'site':rows[i]['site'],'composition_key':groups[i], 'method':method,'split':fold,'actual':y[i],'predicted':pred[i]})
            for role,idx in [('train',train),('test',test)]:
                for m in sorted({rows[i]['material'] for i in idx}):
                    partitions.append({'material':m,'method':method,'split':fold,'role':role,'composition_key':structures[m]['composition_key']})
            importances.append({'method':method,'split':fold,'L2_importance_sum':f(model.feature_importances_[len(grid):].sum()) if method.startswith('L23') else 0.})
        method_preds[method]=pred
    for method in ['majority','element_prior']:
        pred=np.empty(len(rows),dtype='<U12')
        for fold,(train,test) in enumerate(folds):
            overall=Counter(y[train]).most_common(1)[0][0]
            prior={e:Counter(y[train][el[train]==e]).most_common(1)[0][0] for e in sorted(set(el[train]))}
            for i in test:
                pred[i]=overall if method=='majority' else prior.get(el[i],overall)
                predictions.append({'name':rows[i]['name'],'material':rows[i]['material'],'element':rows[i]['element'],'site':rows[i]['site'],'composition_key':groups[i], 'method':method,'split':fold,'actual':y[i],'predicted':pred[i]})
            for role,idx in [('train',train),('test',test)]:
                for m in sorted({rows[i]['material'] for i in idx}):partitions.append({'material':m,'method':method,'split':fold,'role':role,'composition_key':structures[m]['composition_key']})
        method_preds[method]=pred
    table(out/'predictions.csv',predictions);table(out/'partitions.csv',partitions);table(out/'feature_importances.csv',importances)
    results=[];draws={};counts=[]
    for method,p in method_preds.items():
        ci,draw=group_metric_ci(y.tolist(),p.tolist(),groups.tolist());draws[method]=draw
        results.append({'method':method,'n_test_sites':len(y),'balanced_accuracy':f(balanced_accuracy_score(y,p)),'macro_f1':f(f1_score(y,p,average='macro')),'ci025':f(ci[0]),'ci975':f(ci[1]),'confusion_matrix':confusion_matrix(y,p,labels=['octahedral','tetrahedral']).tolist()})
        for e in ELEMENTS:
            ix=el==e
            if ix.any():counts.append({'method':method,'element':e,'n_sites':int(ix.sum()),'n_octahedral':int(np.sum(y[ix]=='octahedral')),'n_tetrahedral':int(np.sum(y[ix]=='tetrahedral')),'balanced_accuracy':f(balanced_accuracy_score(y[ix],p[ix])) if len(set(y[ix]))==2 else ''})
    differences=[]
    for width in CONFIG['resolution_FWHM_eV']:
        a=f'L23_fwhm{width:g}';b=f'L3_fwhm{width:g}';d=draws[a]-draws[b];lo,hi=np.quantile(d,[.025,.975])
        delta=next(r['balanced_accuracy'] for r in results if r['method']==a)-next(r['balanced_accuracy'] for r in results if r['method']==b)
        differences.append({'fwhm_eV':width,'L23_minus_L3_balanced_accuracy':delta,'ci025':f(lo),'ci975':f(hi)})
    # Unchanged OOF predictions evaluated only on sites retaining their label under shell perturbation.
    robust=np.array([r['geometry_shell_1p15']==r['geometry']==r['geometry_shell_1p25'] for r in rows]);robust_results=[]
    for method,p in method_preds.items():robust_results.append({'method':method,'n_stable_sites':int(robust.sum()),'balanced_accuracy':f(balanced_accuracy_score(y[robust],p[robust]))})
    per_element=[]
    for e in ELEMENTS:
        rr={r['method']:r for r in counts if r['element']==e}
        if rr['L3_fwhm0']['balanced_accuracy']!='':per_element.append({'element':e,'n_tetrahedral':rr['L3_fwhm0']['n_tetrahedral'],'n_octahedral':rr['L3_fwhm0']['n_octahedral'],'L23_minus_L3_balanced_accuracy':rr['L23_fwhm0']['balanced_accuracy']-rr['L3_fwhm0']['balanced_accuracy']})
    summary={'n_sites':len(y),'n_materials':len({r['material'] for r in rows}),'n_compositions':len(set(groups)), 'class_counts':dict(Counter(y.tolist())), 'classes_confusion_order':['octahedral','tetrahedral'],'bootstrap_replicates':500,'metrics':results,'paired_differences':differences,'label_stability_subset':robust_results,'per_element_differences':per_element}
    dump(out/'summary.json',summary);table(out/'element_metrics.csv',counts)
    fig,axs=plt.subplots(1,2,figsize=(11,4.5))
    for i,r in enumerate(results):axs[0].plot([r['ci025'],r['ci975']],[i,i],c='tab:blue');axs[0].plot(r['balanced_accuracy'],i,'o',c='tab:blue')
    axs[0].set_yticks(range(len(results)),[r['method'] for r in results]);axs[0].axvline(.5,c='gray');axs[0].set_xlabel('Composition-held-out balanced accuracy (95% bootstrap)')
    for i,r in enumerate(differences):axs[1].plot([r['ci025'],r['ci975']],[i,i],c='tab:orange');axs[1].plot(r['L23_minus_L3_balanced_accuracy'],i,'o',c='tab:orange')
    axs[1].set_yticks(range(len(differences)),[f"FWHM {r['fwhm_eV']:g} eV" for r in differences]);axs[1].axvline(0,c='gray');axs[1].set_xlabel('Paired L2+L3 − L3 balanced accuracy')
    fig.tight_layout();fig.savefig(out/'prediction.png',dpi=160);plt.close(fig)
    d=differences[0];conclusion='supports a positive incremental association' if d['ci025']>0 else ('supports worse prediction with the added edge' if d['ci975']<0 else 'does not resolve an incremental benefit from zero')
    (out/'report.md').write_text(f'''# Does L2 improve coordination prediction on unseen compositions?

On {len(y)} regularly tetrahedral or octahedral sites from {summary['n_materials']} materials and {summary['n_compositions']} reduced compositions, adding L2 changes composition-held-out balanced accuracy by {d['L23_minus_L3_balanced_accuracy']:+.4f}, with a paired 95% composition-bootstrap interval {d['ci025']:+.4f} to {d['ci975']:+.4f}. This {conclusion} for the fixed model and operational labels. The broadened comparison is independently reported below, and the element-prior control exposes the accuracy available from class/chemistry imbalance alone.

Periodic geometry labels use the same explicit nearest-shell and ideal angular-shape test recorded in definitions.json and geometry.csv. Square-planar CN4 does not pass the tetrahedral criterion. Other/ambiguous geometry and missing/invalid paired spectra are excluded with reasons in exhaustive sites.csv. Both spectral models see exactly the same paired sites, labels, train/test compositions and seed. Four shuffled stratified-group folds hold out the canonical reduced elemental composition, so polymorphs and multiple sites of a formula cannot cross train/test partitions. partitions.csv declares every material's training/test role for each method/fold; every eligible site has one OOF prediction per method.

Features are linearly interpolated raw intensities sampled on 3:0.5:43 eV above each edge's first archived energy. L3 is area-normalized; in the combined model both edges are divided by that same L3 area, preserving relative L2/L3 intensity. This removes overall amplitude while retaining the added edge's shape and relative weight. No element, formula, MP ID, structure or geometry descriptor enters either spectral classifier. The only chemistry-feature predictor is the explicitly labeled element-prior control, not a spectral model. It and the global-majority control fit only training labels. Nonuniform native array indices are never treated as a uniform energy axis.

Random forests use 240 trees, balanced-subsample class weights, minimum leaf size 2 and square-root feature subsampling, fixed in advance without tuning on held-out labels. This model comparison establishes achievable information for one transparent model, not the Bayes-optimal value of L2. Repeating the entire matched comparison at Gaussian FWHM 1 eV tests loss of resolution. We also evaluate unchanged OOF predictions on the subset retaining geometry labels under shell ratios 1.15 and 1.25; that is a label-stability sensitivity, not a retraining experiment.

Balanced accuracy, macro F1, ordered confusion matrices and per-element support/accuracy expose class imbalance. The nominal per-element L2 increments range from {min(r['L23_minus_L3_balanced_accuracy'] for r in per_element):+.4f} to {max(r['L23_minus_L3_balanced_accuracy'] for r in per_element):+.4f}; element_metrics.csv and the per-element summary retain all class counts and point differences. These are descriptive chemical heterogeneity checks, not eight independent claims of significance, and the smallest classes provide weaker evidence. Uncertainty uses 500 resamples of reduced-composition groups from the fixed OOF predictions; identical resamples yield paired differences. These intervals reflect test-composition variation conditional on the fitted folds, not training/model-selection variability. No random site split or site-independent confidence interval is used. Composition holdout does not by itself test transfer to new elements, ligands, experimental noise, uncertain energy alignment or experimental spectra. FEFF approximations and the narrow regular-geometry label subset limit external interpretation; predictive success cannot imply spin or oxidation-state determination.

Full quantitative results:\n\n```json\n'''+json.dumps(summary,indent=2)+'\n```\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('question',choices=['Q1','Q2','Q3','all']);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raw,structures,geometry=prepare(a.inputs)
    for q in (['Q1','Q2','Q3'] if a.question=='all' else [a.question]):
        out=a.output/q if a.question=='all' else a.output
        print('Executing',q,flush=True);globals()[q.lower()](out,raw,structures,geometry);print('Completed',q,flush=True)
if __name__=='__main__':main()
