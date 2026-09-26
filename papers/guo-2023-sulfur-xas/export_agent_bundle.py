#!/usr/bin/env python3
"""Export only minimal task text and the raw release projection."""
import argparse,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def export(question,output):
    paper=json.loads((Path(__file__).parent/'paper.json').read_text()); s=next(s for s in paper['scenarios'] if s['id']=='GUO23-'+question)
    output=Path(output)
    if output.exists() and any(output.iterdir()): raise ValueError('Use a new or empty directory')
    (output/'inputs').mkdir(parents=True,exist_ok=True); inputs=[]
    for item in s['inputs']:
        source=ROOT/'docs'/item['url']
        if source.parent.name!='inputs': raise ValueError('Refusing evaluator asset')
        shutil.copyfile(source,output/'inputs'/source.name); inputs.append({'name':source.name,'path':'inputs/'+source.name,'description':item['description']})
    task={'id':s['id'],'title':s['title'],**s['prompt'],'inputs':inputs,
      'attribution':'Numeric spectra and calculation text: Haoyue Guo and coauthors, Materials Cloud v3 (2023), DOI10.24435/materialscloud:6z-qm, CC BY4.0 https://creativecommons.org/licenses/by/4.0/. Decimal numeric values preserved as float64; original text retained; archive containers changed.'}
    (output/'task.json').write_text(json.dumps(task,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'question':question,'output':str(output.resolve()),'files':len(inputs)+1}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('question',choices=['Q1','Q2','Q3']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();export(a.question,a.output)
