#!/usr/bin/env python3
"""Executable controlled experiments. Reads only the specified input directory."""
import argparse,csv,json,time
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
from scipy.special import softmax
from sklearn.linear_model import RidgeClassifier
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
CHEMS=['Li-La-Zr-O','Li-Ti-P-O'];MODELS=['XRD','PDF','Fused']
THETA=np.linspace(10.02,79.98,2001);R=np.linspace(1,40,1000)
PRIOR={'Li-La-Zr-O':['La(OH)3','Li2CO3','LiOH','ZrO2'],'Li-Ti-P-O':['Li2CO3','Li2TiO3','Li3PO4','TiO2']}
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def load(inp,chem,kind):
 stem=f'{chem}_{kind}';rows=json.loads((inp/f'{stem}.json').read_text())
 with np.load(inp/f'{stem}.npz',allow_pickle=False) as f:
  y=np.array([np.interp(THETA,f['theta'],f[r['id']]) if 'theta' in f else np.interp(THETA,f[r['id']][:,0],f[r['id']][:,1]) for r in rows])
 return rows,y
def unit(y):return y/np.maximum(np.linalg.norm(y,axis=-1,keepdims=True),1e-30)
def prep(y):
 # One shared declared operational baseline; retain negative residual/noise values.
 y=y-np.percentile(y,10,axis=-1,keepdims=True)
 return y/np.maximum(np.max(y,axis=-1,keepdims=True),1e-30)
def kernel(r):
 q=4*np.pi*np.sin(np.deg2rad(THETA/2))/1.5406
 w=np.empty(len(q));w[0]=(q[1]-q[0])/2;w[-1]=(q[-1]-q[-2])/2;w[1:-1]=(q[2:]-q[:-2])/2
 return 2/np.pi*np.sin(r[:,None]*q[None,:])*(q*w)[None,:]
def ft(y,r=R):return y@kernel(r).T
def top(scores,k):return sorted(scores,key=lambda x:(-scores[x],x))[:k]
def record(row,model,scores,k):return dict(id=row['id'],chemistry=row['chemistry'],model=model,predicted=top(scores,k),scores=scores)
def save_predictions(out,records):
 with (out/'predictions.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=['id','chemistry','model','predicted','scores']);w.writeheader()
  for row in records:w.writerow({**row,'predicted':json.dumps(row['predicted']),'scores':json.dumps(row['scores'])})
def summarize(question,records,metadata):
 byid={r['id']:r for r in metadata};groups={}
 for p in records:
  r=byid[p['id']];group='single' if question=='Q1' else (str(r['minor_weight_percent']) if question=='Q4' else r['kind'])
  groups.setdefault((r['chemistry'],group,p['model']),[]).append((r,p))
 summaries=[];complement=[]
 for (chem,group,model),pairs in sorted(groups.items()):
  tp=fp=fn=exact=minor=0
  for r,p in pairs:
   truth=set(r['phases']);pred=set(p['predicted']);tp+=len(truth&pred);fp+=len(pred-truth);fn+=len(truth-pred);exact+=pred==truth
   if question=='Q4':minor+=r['minor'] in pred
  s=dict(chemistry=chem,group=group,model=model,n=len(pairs),micro_f1=2*tp/(2*tp+fp+fn),exact_match=exact/len(pairs))
  if question=='Q4':s['minor_recall']=minor/len(pairs)
  summaries.append(s)
 for chem,group in sorted({k[:2] for k in groups}):
  x={r['id']:set(p['predicted'])==set(r['phases']) for r,p in groups[(chem,group,'XRD')]}
  p={r['id']:set(p['predicted'])==set(r['phases']) for r,p in groups[(chem,group,'PDF')]}
  complement.append(dict(chemistry=chem,group=group,n=len(x),xrd_only_correct=sum(x[i] and not p[i] for i in x),pdf_only_correct=sum(p[i] and not x[i] for i in x),both_correct=sum(x[i] and p[i] for i in x),neither_correct=sum(not x[i] and not p[i] for i in x)))
 return dict(question=question,summaries=summaries,complementarity=complement)
def fit_coefficients(reference,target):
 # Solve the declared ridge-regularized NNLS objective on unit-length template columns.
 d=unit(reference);y=unit(target);g=d@d.T
 l=np.linalg.cholesky(g+1e-10*np.eye(len(d)))
 b=np.linalg.solve(l,(d@y.T))
 c=np.array([nnls(l.T,v,maxiter=10000)[0] for v in b.T])
 return c/np.maximum(c.sum(axis=1,keepdims=True),1e-30)
def classify(question,inp,out):
 records=[];meta=[];splits={};probed=False
 for chem in CHEMS:
  rows,raw=load(inp,chem,'1-Phase');x=prep(raw);train=np.array([r['split']=='train' for r in rows]);labels=np.array([r['phases'][0] for r in rows]);splits[chem]={'train':[r['id'] for r in rows if r['split']=='train'],'test':[r['id'] for r in rows if r['split']=='test']}
  if question=='Q1':
   targetrows=[r for r in rows if r['split']=='test'];targets=x[~train];classes=sorted(set(labels));scores={}
   for name,features in [('XRD',x),('PDF',ft(x))]:
    clf=RidgeClassifier(alpha=1.0,solver='cholesky').fit(unit(features[train]),labels[train]);scores[name]=softmax(clf.decision_function(unit(features[~train])),axis=1);assert list(clf.classes_)==classes
  else:
   if question=='Q2':
    targetrows=[];ys=[]
    for kind in ['2-Phase','3-Phase']:
     rr,yy=load(inp,chem,kind);targetrows+=rr;ys.append(yy)
    targets=prep(np.concatenate(ys));classes=sorted(set(labels))
   else:
    targetrows,yy=load(inp,chem,'Experiments');targets=prep(yy);classes=sorted(c for c in set(labels) if c.rsplit('_',1)[0] in PRIOR[chem])
   templates=np.array([x[train & (labels==c)].mean(axis=0) for c in classes]);scores={}
   for name,refs,ys in [('XRD',templates,targets),('PDF',ft(templates),ft(targets))]:scores[name]=fit_coefficients(refs,ys)
   if question=='Q4':
    old=classes;classes=sorted(PRIOR[chem]);scores={name:np.array([v[:,[i for i,c in enumerate(old) if c.rsplit('_',1)[0]==formula]].sum(axis=1) for formula in classes]).T for name,v in scores.items()}
  scores['Fused']=(scores['XRD']+scores['PDF'])/2
  for name in MODELS:
   for i,row in enumerate(targetrows):records.append(record(row,name,dict(zip(classes,map(float,scores[name][i]))),1 if question=='Q1' else (int(row['kind'][0]) if question=='Q2' else 2)))
  meta+=targetrows
  if not probed:
   np.savez_compressed(out/'probe.npz',theta=THETA,r=R,xrd=targets[0],pdf=ft(targets[:1])[0],probe_id=targetrows[0]['id']);probed=True
 save_predictions(out,records);write(out/'split_trace.json',splits);result=summarize(question,records,meta);write(out/'result.json',result)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,chem in zip(axes,CHEMS):
  for model in MODELS:
   ss=sorted([s for s in result['summaries'] if s['chemistry']==chem and s['model']==model],key=lambda s:int(s['group']) if question=='Q4' else s['group'])
   ax.plot([s['group'] for s in ss],[s['minor_recall'] if question=='Q4' else s['micro_f1'] for s in ss],'o-',label=model)
  ax.set(title=chem,ylabel='Secondary-phase recall' if question=='Q4' else 'Micro F1',xlabel='Secondary wt%' if question=='Q4' else 'Mixture group',ylim=(0,1.02));ax.legend()
 fig.tight_layout();fig.savefig(out/'diagnostics.png',dpi=150);plt.close(fig)
 lines=[f'# {question}: executed controlled baseline','']
 for chem in CHEMS:
  ss=[s for s in result['summaries'] if s['chemistry']==chem]
  for group in sorted({s['group'] for s in ss},key=lambda v:int(v) if question=='Q4' else v):
   group_rows=[s for s in ss if s['group']==group]
   lines.append(chem+' '+group+': '+', '.join(f"{s['model']} F1={s['micro_f1']:.4f}, exact={s['exact_match']:.4f}"+(f", secondary recall={s['minor_recall']:.4f}" if question=='Q4' else '') for s in group_rows)+'.')
 lines.append('')
 for chem in CHEMS:
  groups=sorted({v['group'] for v in result['summaries'] if v['chemistry']==chem},key=lambda v:int(v) if question=='Q4' else v)
  values={(v['group'],v['model']):v for v in result['summaries'] if v['chemistry']==chem}
  if question=='Q1':
   x,p,f=[values[('single',m)]['micro_f1'] for m in MODELS]
   c=next(v for v in result['complementarity'] if v['chemistry']==chem)
   lines.append(f'{chem}: PDF minus XRD accuracy is {p-x:+.4f}; fusion minus the better standalone accuracy is {f-max(x,p):+.4f}. There are {c["xrd_only_correct"]+c["pdf_only_correct"]} cases solved by exactly one representation. This establishes partially complementary errors in this fixed within-phase split; averaging scores exploits some of that complementarity.')
  elif question=='Q2':
   for m in MODELS:
    a,b=[values[(g,m)] for g in ['2-Phase','3-Phase']]
    lines.append(f'{chem}, {m}: from two to three constituents, micro-F1 changes {b["micro_f1"]-a["micro_f1"]:+.4f} and exact recovery changes {b["exact_match"]-a["exact_match"]:+.4f}.')
   lines.append('The larger loss in complete phase-set recovery shows why high average constituent recall can conceal unsuccessful mixture identification. These are different mixtures at each cardinality, so composition and abundance differences may also contribute; this is not a pure causal isolation of peak overlap.')
  else:
   for m in MODELS:
    recalls=[values[(g,m)]['minor_recall'] for g in groups]
    falls=sum(b<a for a,b in zip(recalls,recalls[1:]))
    lines.append(f'{chem}, {m}: secondary recall is {recalls[0]:.3f} at 2 wt% and {recalls[-1]:.3f} at 20 wt% (change {recalls[-1]-recalls[0]:+.3f}); {falls} of nine adjacent abundance steps decrease. The abundance dependence is therefore '+('not strictly monotonic.' if falls else 'nondecreasing on this panel.'))
   lines.append('Each abundance point contains only 12 ordered mixtures; reciprocal major/minor pairs reuse component identities. This limits precision and independence. Performance measures transfer of this restricted simulation template library to these measured mixtures; it is not directly comparable with unconstrained larger-library classification.')
 lines+=['','These are controlled ridge/template baselines. Representation and fusion benefits depend on the group; no CNN or historical-score reproduction is claimed.']
 if question=='Q1':lines.append('Splits hold out augmented repeats of already represented phase identities, not unseen phases or experimental materials. Softmax scores are uncalibrated relative scores.')
 if question=='Q2':lines.append('The true number of phases is supplied. Exact phase-set recovery is stricter than micro F1. Coefficients measure spectral contribution, not mass fraction. Ordered duplicates of phase combinations remain separate measured/simulated patterns; they are not independent material families.')
 if question=='Q4':lines.append('Formula-level scoring merges polymorphs. The candidate library is restricted to four formulas per chemistry. Measured minor fractions are evaluation covariates only; fitting does not use them. Coefficients are not weight fractions, and these samples do not establish a universal detection limit.')
 (out/'conclusion.md').write_text('\n'.join(lines)+'\n')
 return result
WINDOWS={'1-5':(1,5),'5-40':(5,40),'1-40':(1,40),'40-120':(40,120.00001)}
def artifacts(inp,out):
 rows,raw=load(inp,'Li-Ti-P-O','1-Phase');idx=[i for i,r in enumerate(rows) if r['phases']==['Li2TiO3_15']];r=np.linspace(1,120,1191);k=kernel(r);metrics=[];curves={};probed=False
 for i in idx:
  row=rows[i];baseline=prep(raw[i:i+1])[0];basepdf=baseline@k.T
  curves[row['id']+'_base']=basepdf
  for artifact,levels,trials in [('noise',[.01,.03],5),('background',[.05,.20],1)]:
   for level in levels:
    for trial in range(trials):
     seed=202409+(i*100)+trial
     delta=np.random.default_rng(seed).normal(0,level,len(THETA)) if artifact=='noise' else level*np.exp(-.5*((THETA-35)/12)**2)
     changed=(baseline+delta)@k.T;diff=changed-basepdf
     name=f"{row['id']}_{artifact}_{level}_{trial}";curves[name]=changed
     if not probed:
      np.savez_compressed(out/'probe.npz',theta=THETA,r=r,xrd=baseline,pdf=basepdf,probe_id=row['id']);probed=True
     for window,(lo,hi) in WINDOWS.items():
      m=(r>=lo)&(r<hi)
      metrics.append(dict(id=row['id'],artifact=artifact,amplitude=level,trial=trial,window=window,xrd_relative_l2=float(np.linalg.norm(delta)/np.linalg.norm(baseline)),pdf_relative_l2=float(np.linalg.norm(diff[m])/np.linalg.norm(basepdf[m])),signal_energy_fraction=float(np.sum(basepdf[m]**2)/np.sum(basepdf**2)),artifact_energy_fraction=float(np.sum(diff[m]**2)/np.sum(diff**2))))
 np.savez_compressed(out/'curves.npz',r=r,**curves)
 with (out/'metrics.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
 summary=[]
 for artifact in ['noise','background']:
  for level in sorted({v['amplitude'] for v in metrics if v['artifact']==artifact}):
   for window in WINDOWS:
    rr=[v for v in metrics if v['artifact']==artifact and v['amplitude']==level and v['window']==window]
    summary.append(dict(artifact=artifact,amplitude=level,window=window,n=len(rr),**{key:float(np.mean([v[key] for v in rr])) for key in ['xrd_relative_l2','pdf_relative_l2','signal_energy_fraction','artifact_energy_fraction']}))
 result={'question':'Q3','source_patterns':len(idx),'summaries':summary};write(out/'result.json',result)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,artifact in zip(axes,['noise','background']):
  for level in sorted({s['amplitude'] for s in summary if s['artifact']==artifact}):
   ss=[s for s in summary if s['artifact']==artifact and s['amplitude']==level];ax.plot([s['window'] for s in ss],[s['pdf_relative_l2'] for s in ss],'o-',label=str(level))
  ax.set(title=artifact,xlabel='r window / Å',ylabel='Relative L2 distortion');ax.legend(title='Added amplitude')
 fig.tight_layout();fig.savefig(out/'diagnostics.png',dpi=150);plt.close(fig)
 lines=['# Artifact/window tradeoff','',f'Computed paired perturbations of {len(idx)} released Li2TiO3 patterns, each of which already contains simulated artifacts.']
 for s in summary:
  if s['amplitude'] in [.03,.20]:lines.append(f"{s['artifact']} amplitude {s['amplitude']}, {s['window']} Å: distortion {s['pdf_relative_l2']:.4f}, original-signal energy fraction {s['signal_energy_fraction']:.4f}, artifact energy fraction {s['artifact_energy_fraction']:.4f}.")
 lines+=['','For these perturbations, 5–40 Å is a useful compromise: it excludes the low-r region most distorted by smooth background and avoids the greater relative noise distortion at 40–120 Å, while retaining about 60% of sampled baseline energy. That preference is conditional on the chosen noise/background amplitudes and finite angular range, and discards about 40% of baseline energy.', 'Window selection trades artifact suppression against retained baseline signal. The uncorrected sine transform is not a normalized physical PDF; retained energy does not establish retained classification information. Added noise uses five draws per pattern; the smooth background is deterministic. No historical robustness F1 score is implied.']
 (out/'conclusion.md').write_text('\n'.join(lines)+'\n');return result

def main():
 p=argparse.ArgumentParser();p.add_argument('question',choices=['Q1','Q2','Q3','Q4','ALL']);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();started=time.time()
 qs=['Q1','Q2','Q3','Q4'] if a.question=='ALL' else [a.question]
 for q in qs:
  out=a.output/q if a.question=='ALL' else a.output;out.mkdir(parents=True,exist_ok=True);result=artifacts(a.inputs,out) if q=='Q3' else classify(q,a.inputs,out);print(q,json.dumps(result),flush=True)
 write(a.output/'execution.json',{'questions':qs,'elapsed_seconds':time.time()-started,'input_directory':str(a.inputs.resolve()),'candidate_sha256':__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest(),'numpy':np.__version__,'scipy':__import__('scipy').__version__,'sklearn':__import__('sklearn').__version__})
if __name__=='__main__':main()
