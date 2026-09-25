#!/usr/bin/env python3
"""Author-side recovery: reuse completed matching Q4 fits, checkpoint Q5 new fits.

This is reference-run recovery only. Each solver question remains independently
runnable with candidate.py. Q4 FEFF conditions are identical to Q5 FEFF conditions.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'docs/data/torrisi-2020-xanes-rf/workflows'
sys.path.insert(0,str(WORK))
import candidate as c
from summarize import summarize

def read_csv(path, integer_keys):
    with path.open() as f: rows=list(csv.DictReader(f))
    return [{k:(v if k=='model_id' else int(v) if k in integer_keys else float(v))
             for k,v in row.items()} for row in rows]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--q4',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoints',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();start=time.monotonic()
    a.output.mkdir(parents=True,exist_ok=True);a.checkpoints.mkdir(parents=True,exist_ok=True)
    prior=json.loads((a.q4/'result.json').read_text())
    oldsplits=json.loads((a.q4/'splits.json').read_text())
    oldmeta=json.loads((a.q4/'feature_metadata.json').read_text())
    oldpred=read_csv(a.q4/'predictions.csv',{'seed','source_row'})
    oldimp=read_csv(a.q4/'importances.csv',{'seed','feature_index'})
    data,audit=c.prepare(a.inputs)
    signature=hashlib.sha256((WORK/'candidate.py').read_bytes()).hexdigest()
    signature+=hashlib.sha256((a.q4/'result.json').read_bytes()).hexdigest()
    for f in sorted(a.inputs.glob('*.jsonl.gz')):signature+=hashlib.sha256(f.read_bytes()).hexdigest()
    models=[];splits={};predictions=[];importances=[];metadata={}
    fresh=0;resumed=0
    for element in c.ELEMENTS:
        for config in c.settings('Q5'):
            t,r,n,b=config
            model_id='_'.join([element,t,r,n,'balanced' if b else 'natural'])
            if n=='feff':
                model=next(m for m in prior['models'] if m['id']==model_id)
                record=(model,oldsplits[element+'_'+t],
                        [v for v in oldpred if v['model_id']==model_id],
                        [v for v in oldimp if v['model_id']==model_id],oldmeta[element+'_'+r])
            else:
                checkpoint=a.checkpoints/(model_id+'.json')
                if checkpoint.exists():
                    saved=json.loads(checkpoint.read_text())
                    if saved['signature']!=signature:raise ValueError('Checkpoint inputs or code differ')
                    record=saved['record'];resumed+=1
                else:
                    record=c.fit_model(element,data[element],*config,a.jobs)
                    c.dump(checkpoint,dict(signature=signature,record=record));fresh+=1
            model,split,pred,imp,meta=record
            models.append(model);splits[element+'_'+t]=split
            predictions.extend(pred);importances.extend(imp);metadata[element+'_'+r]=meta
    c.dump(a.output/'result.json',dict(question='Q5',models=models,preprocessing=audit,
                                     protocol=prior['protocol'],versions=prior['versions']))
    c.dump(a.output/'splits.json',splits);c.dump(a.output/'feature_metadata.json',metadata)
    c.write_csv(a.output/'predictions.csv',predictions);c.write_csv(a.output/'importances.csv',importances)
    c.plot_and_conclude('Q5',models,importances,a.output);summarize(a.output)
    c.dump(a.output/'execution.json',dict(question='Q5',elapsed_seconds=time.monotonic()-start,
          method='Reused 32 identical completed Q4 FEFF model conditions; trained or resumed 32 maximum-normalized conditions from raw inputs.',
          reused_q4_conditions=32,fresh_conditions=fresh,resumed_checkpoint_conditions=resumed,
          q4=str(a.q4.resolve()),inputs=str(a.inputs.resolve()),output=str(a.output.resolve())))
    print('Completed reference Q5',flush=True)

if __name__=='__main__':main()
