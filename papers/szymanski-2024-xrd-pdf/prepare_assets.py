#!/usr/bin/env python3
"""Lossless raw-value packaging. No model, split, or analysis settings are inputs."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/data/szymanski-2024-xrd-pdf'
CHEMS=['Li-La-Zr-O','Li-Ti-P-O']
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,required=True);parser.add_argument('--archive',type=Path,required=True);args=parser.parse_args()
 source=[];inventory={};expected=set()
 for chemistry in CHEMS:
  for kind in ['1-Phase','Mixtures','Experiments']:
   if kind=='Experiments':files=list((args.release/'Experiments'/chemistry).glob('*/*.xy'))
   elif kind=='Mixtures':files=[f for n in [2,3] for f in (args.release/'Simulations'/chemistry/f'{n}-Phase').iterdir() if f.is_file() and not f.name.startswith('.')]
   else:files=[f for f in (args.release/'Simulations'/chemistry/kind).iterdir() if f.is_file() and not f.name.startswith('.')]
   pairs=[]
   for file in files:
    relative=file.relative_to(args.release).as_posix()
    opaque=hashlib.sha256(relative.encode()).hexdigest()[:16]
    sid=('A' if chemistry==CHEMS[0] else 'B')+'_'+{'1-Phase':'S','Mixtures':'M','Experiments':'E'}[kind]+'_'+opaque
    pairs.append((sid,file,relative))
   arrays={};rows=[]
   for sid,file,relative in sorted(pairs):
    xy=np.loadtxt(file);assert xy.ndim==2 and xy.shape[1]==2 and np.isfinite(xy).all() and np.all(np.diff(xy[:,0])>0)
    arrays[sid]=xy
    row={'id':sid,'chemistry':chemistry}
    if kind=='1-Phase':
     phase,rep=file.name.rsplit('_',1);row.update(phases=[phase],replicate=int(rep))
    elif kind=='Mixtures':row['phases']=file.name.split('+')
    else:
     match=re.fullmatch(r'(\d+)-(.+)_(\d+)-(.+)_\d+-80_10-min\.xy',file.name);assert match
     row.update(phases=[match[2],match[4]],major=match[2],minor=match[4],minor_weight_percent=int(match[3]))
    rows.append(row);source.append(dict(row,kind=Path(relative).parts[2] if kind!='Experiments' else 'Experiments',source_path=relative,sha256=sha(file)))
   stem=chemistry+'_'+kind
   if kind!='Experiments':
    theta=next(iter(arrays.values()))[:,0];assert all(np.array_equal(v[:,0],theta) for v in arrays.values())
    arrays={'theta':theta,**{key:arr[:,1] for key,arr in arrays.items()}}
   np.savez_compressed(BASE/'inputs'/f'{stem}.npz',**arrays);write(BASE/'inputs'/f'{stem}.json',rows)
   expected.update([stem+'.npz',stem+'.json'])
   inventory[stem]={'patterns':len(rows),'phase_labels':len({p for row in rows for p in row['phases']})}
 for file in (BASE/'inputs').iterdir():
  if file.is_file() and file.name not in expected:file.unlink()
 write(BASE/'verification/source_labels.json',source)
 write(BASE/'provenance.json',{'version':'open-research-v2','paper_doi':'10.1038/s41524-024-01230-9','data_doi':'10.6084/m9.figshare.24043410.v1','download_url':'https://ndownloader.figshare.com/files/42159903','archive_sha256':sha(args.archive),'archive_md5':hashlib.md5(args.archive.read_bytes()).hexdigest(),'archive_bytes':args.archive.stat().st_size,'license':'CC BY 4.0','attribution':'Nathan Szymanski (2023), Integrated analysis of XRD patterns and PDFs, figshare version 1.','code_commit':'bf32082521e45c0fcf5cf9ae9bd1321e76bf9012','input_transformation':'Parse every original numeric file as float64 without resampling, normalization, filtering or fitting. Opaque IDs hash the source path; two/three-phase spectra are pooled and sorted by opaque ID. Label tables retain raw labels for scientific evaluation, with no predefined split or analysis settings. Shared native simulation axes are stored once.','inventory':inventory,'input_files':{f.name:sha(f) for f in sorted((BASE/'inputs').iterdir()) if f.is_file()},'availability_limitations':['The archive contains 2690 simulations and240 experiments, not the complete reported historical test sets.','No historical CNN predictions, original splits, occupancy sweep or categorized artifact dataset are available in this archive.','Raw denotes earliest released numeric spectra, not detector frames.','Target labels remain available for scientific scoring. Published/ exported files do not enforce blinded evaluation: reviewers must inspect submitted code and execution traces for target leakage.']})
 print(json.dumps(inventory,indent=2))
if __name__=='__main__':main()
