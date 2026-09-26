#!/usr/bin/env python3
"""Losslessly package native numeric arrays and unmodified calculation text."""
import argparse, csv, gzip, hashlib, json, shutil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/data/guo-2023-sulfur-xas'

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--raw',type=Path,required=True); p.add_argument('--release',type=Path,required=True); p.add_argument('--reference',type=Path,required=True)
    a=p.parse_args(); inp=BASE/'inputs'; inp.mkdir(parents=True,exist_ok=True)
    ver=BASE/'verification'; ver.mkdir(exist_ok=True)
    records={}; arrays={}; manifest=[]
    for m in sorted(a.raw.iterdir()):
        if not m.is_dir() or not m.name.isdigit(): continue
        records[m.name]={'neutral':{},'sites':{}}
        for path in sorted(m.iterdir()):
            if not path.is_dir(): continue
            target=records[m.name]['neutral'] if path.name=='input_SCF' else records[m.name]['sites'].setdefault(path.name,{})
            for f in sorted(path.iterdir()):
                if f.name not in {'POSCAR','OSZICAR','INCAR','KPOINTS','efermi.txt','mu.dat'}: continue
                key=f'{m.name}/{path.name}/{f.name}'
                manifest.append({'path':key,'sha256':sha(f),'bytes':f.stat().st_size})
                if f.name=='mu.dat':
                    arr=np.loadtxt(f); arrays[f'{m.name}/{path.name}']=arr
                    assert arr.ndim==2 and arr.shape[1]==4 and np.isfinite(arr).all()
                else: target[f.name]=f.read_text()
        if int(m.name)%11==0:
            dest=inp/f'spectra_{(int(m.name)-1)//11+1:02d}.npz'
            np.savez_compressed(dest,**arrays); arrays={}
    with gzip.GzipFile(filename=str(inp/'calculations.json.gz'),mode='wb',mtime=0) as f:
        f.write(json.dumps(records,sort_keys=True).encode())
    shutil.copyfile(a.release/'structure-index.csv',inp/'materials.csv')
    references={}
    for f in sorted(a.reference.glob('material-*_raw.txt')):
        references[f'm{int(f.name.split("-")[1].split("_")[0]):03d}']=np.loadtxt(f)
    np.savez_compressed(ver/'released_material_spectra.npz',**references)
    provenance={'doi':'10.24435/materialscloud:6z-qm','version':3,'license':'CC BY 4.0',
        'creators':'Haoyue Guo, Matthew R. Carbone, Chuntian Cao, Jianzhou Qu, Feng Wang, Shinjae Yoo, Nongnuch Artrith, Alexander Urban, Deyu Lu',
        'source':'https://archive.materialscloud.org/records/g5aby-h6029',
        'transformation':'mu.dat decimal text parsed to float64 without resampling, normalization, alignment or feature extraction. Calculation text is unchanged inside gzip JSON. materials.csv is byte-identical to structure-index.csv. Reference averages are evaluator-only.',
        'archives':[{ 'name':f.name,'sha256':sha(f),'bytes':f.stat().st_size} for f in a.release.glob('*.tar.bz2')],
        'input_assets':[{ 'name':f.name,'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(inp.iterdir())],
        'materials':len(records),'site_spectra':sum(len(r['sites']) for r in records.values()),'source_files':manifest}
    (BASE/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({k:v for k,v in provenance.items() if k not in {'source_files','input_assets'}},indent=2))

if __name__=='__main__': main()
