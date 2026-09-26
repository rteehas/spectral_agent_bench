from pathlib import Path
import numpy as np,re,json,argparse
from scipy.interpolate import interp1d
from ase.io import read
parser=argparse.ArgumentParser(description='Independent all-material reconstruction from extracted public releases')
parser.add_argument('--raw-root',type=Path,required=True)
parser.add_argument('--reference-root',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
root=args.raw_root; refs=args.reference_root
def e0(p):return float(re.findall(r'E0=\s*([-+.\dEe]+)',(p/'OSZICAR').read_text())[-1])
res=[]
for n in range(1,67):
 p=root/f'{n:03d}'; neutral=e0(p/'input_SCF'); size0=len(read(p/'input_SCF'/'POSCAR'))
 target=np.loadtxt(refs/f'material-{n}_raw.txt'); tx,ty=target.T
 data=[]; zs=[]
 for d in sorted(p.glob('*_*')):
  if d.name=='input_SCF':continue
  raw=np.loadtxt(d/'mu.dat'); x=raw[:,0]; y=raw[:,1:].sum(axis=1)
  dE=e0(d)-neutral*(len(read(d/'POSCAR'))/size0)-float((d/'efermi.txt').read_text()); mult=int(d.name.split('_')[1]);data.append((x+dE,y,mult));zs.append(len(x))
 pred=sum(m*interp1d(x,y,kind='cubic',bounds_error=False,fill_value=0)(tx) for x,y,m in data)
 lows=[d[0][0] for d in data]; highs=[d[0][-1] for d in data];steps=[np.diff(d[0]).mean() for d in data]
 row=dict(material=n,nrmse=float(np.linalg.norm(pred-ty)/np.linalg.norm(ty)),min_diff=min(lows)-tx[0],max_diff=max(highs)-tx[-1],count=len(tx),suggest_min_step=round((max(highs)-min(lows))/min(steps)),suggest_mean_step=round((max(highs)-min(lows))/np.mean(steps)),suggest_first_step=round((max(highs)-min(lows))/steps[0]),num_input_min=min(zs),num_input_max=max(zs),step_ratio=float(np.diff(tx).mean()/steps[0]))
 res.append(row);print(json.dumps(row),flush=True)
args.output.write_text(json.dumps(res,indent=2)+'\n')
assert all(r['nrmse'] < 1e-10 for r in res)
assert all(r['count']==r['num_input_max'] for r in res)
