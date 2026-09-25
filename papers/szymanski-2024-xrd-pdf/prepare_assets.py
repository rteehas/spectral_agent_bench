#!/usr/bin/env python3
"""Lossless packaging of the numeric release; never execute upstream code."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/data/szymanski-2024-xrd-pdf'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v): p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
 manifests={};source=[];inventory={}
 for chemistry in ['Li-La-Zr-O','Li-Ti-P-O']:
  for kind in ['1-Phase','2-Phase','3-Phase','Experiments']:
   directory=a.release/('Experiments' if kind=='Experiments' else 'Simulations')/chemistry
   files=sorted(directory.glob('*/*.xy') if kind=='Experiments' else (directory/kind).iterdir())
   files=[f for f in files if f.is_file() and not f.name.startswith('.')]
   stem=chemistry+'_'+kind; arrays={};rows=[]
   for i,f in enumerate(files):
    sid=stem.replace('Li-La-Zr-O','A').replace('Li-Ti-P-O','B')+'_'+str(i).zfill(4)
    xy=np.loadtxt(f);assert xy.ndim==2 and xy.shape[1]==2 and np.isfinite(xy).all() and (np.diff(xy[:,0])>0).all()
    arrays[sid]=xy
    row={'id':sid,'chemistry':chemistry,'kind':kind}
    if kind=='1-Phase':
     phase,rep=f.name.rsplit('_',1);row.update(phases=[phase],replicate=int(rep))
    elif kind=='Experiments':
     m=re.fullmatch(r'(\d+)-(.+)_(\d+)-(.+)_\d+-80_10-min\.xy',f.name);assert m,f
     row.update(phases=[m[2],m[4]],major=m[2],minor=m[4],minor_weight_percent=int(m[3]))
    else:row['phases']=f.name.split('+')
    rows.append(row);source.append(dict(row,source_path=str(f.relative_to(a.release)),sha256=sha(f)))
   if kind=='1-Phase':
    for phase in sorted({r['phases'][0] for r in rows}):
     group=sorted([r for r in rows if r['phases'][0]==phase],key=lambda r:r['replicate']);cut=max(1,int(.7*len(group)))
     for i,r in enumerate(group):r['split']='train' if i<cut else 'test'
   if kind!='Experiments':
    axis=next(iter(arrays.values()))[:,0]
    assert all(np.array_equal(v[:,0],axis) for v in arrays.values())
    arrays={'theta':axis,**{key:value[:,1] for key,value in arrays.items()}}
   np.savez_compressed(BASE/'inputs'/f'{stem}.npz',**arrays)
   write(BASE/'inputs'/f'{stem}.json',rows);manifests[stem]=rows;inventory[stem]={'patterns':len(rows),'classes':len({p for r in rows for p in r['phases']})}
 write(BASE/'verification/source_labels.json',source)
 write(BASE/'provenance.json',{'paper_doi':'10.1038/s41524-024-01230-9','data_doi':'10.6084/m9.figshare.24043410.v1','download_url':'https://ndownloader.figshare.com/files/42159903','archive_sha256':sha(a.archive),'archive_md5':hashlib.md5(a.archive.read_bytes()).hexdigest(),'archive_bytes':a.archive.stat().st_size,'license':'CC BY 4.0','attribution':'Nathan Szymanski (2023), Integrated analysis of XRD patterns and PDFs, figshare, version 1.','code_commit':'bf32082521e45c0fcf5cf9ae9bd1321e76bf9012','input_transformation':'Each numeric text file parsed into float64 arrays without resampling, normalization, cropping, or fitting. Anonymous stable IDs replace answer-bearing filenames; labels are separate metadata for scientific evaluation. All native numeric values are preserved at float64 precision.','inventory':inventory,'input_files':{f.name:sha(f) for f in sorted((BASE/'inputs').glob('*')) if f.suffix in ['.npz','.json']},'availability_limitations':['2690 simulated patterns rather than 8000 reported; 28 LLZO and 53 LTPO single-phase classes rather than article 28 and45.','No separate LiTiO2 occupancy sweep, categorized artifact dataset, training splits, CAM arrays, or historical predictions in Figshare v1.','Raw here means earliest released numeric spectra; no detector frames. Simulations contain augmentations already.']})
 print(json.dumps(inventory,indent=2))
if __name__=='__main__':main()
