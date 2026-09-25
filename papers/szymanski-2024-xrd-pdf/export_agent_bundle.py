#!/usr/bin/env python3
"""Export the complete inline prompt and only its raw data/label inputs."""
import argparse
import json
import shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent

def export(question, output):
    paper=json.loads((HERE/'paper.json').read_text())
    scenario=next(s for s in paper['scenarios'] if s['id']=='SZYMANSKI24-'+question)
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('Choose a new/empty output directory')
    (output/'inputs').mkdir(parents=True,exist_ok=True)
    inputs=[]
    for entry in scenario['inputs']:
        source=ROOT/'docs'/entry['url']
        if source.parent.name!='inputs' or source.suffix not in {'.npz','.json'}:raise ValueError('Non-raw input asset')
        shutil.copyfile(source,output/'inputs'/source.name)
        inputs.append({'name':source.name,'path':'inputs/'+source.name,'description':entry['description']})
    task={'id':scenario['id'],'title':scenario['title'],**scenario['prompt'],'inputs':inputs,
          'data_attribution':'Nathan Szymanski (2023), Integrated analysis of XRD patterns and PDFs, figshare v1, DOI 10.6084/m9.figshare.24043410.v1; CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Numeric values are preserved; records are renamed and label metadata separated.'}
    (output/'task.json').write_text(json.dumps(task,indent=2)+'\n')
    return {'question':question,'output':str(output.resolve()),'files':sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('question',choices=['Q1','Q2','Q3','Q4']);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(export(args.question,args.output),indent=2))
