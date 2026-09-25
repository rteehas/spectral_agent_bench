#!/usr/bin/env python3
"""Check the open-research revision, raw-only exports and public asset links."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DATA=ROOT/'docs/data/szymanski-2024-xrd-pdf'
CHEMS=['Li-La-Zr-O','Li-Ti-P-O']
KINDS={'Q1':['1-Phase'],'Q2':['1-Phase','Mixtures'],'Q3':['1-Phase'],'Q4':['1-Phase','Experiments']}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def require(value,message):
    if not value:raise ValueError(message)
def expected_inputs(q):
    return {f'{chem}_{kind}.{extension}' for chem in (['Li-Ti-P-O'] if q=='Q3' else CHEMS)
            for kind in KINDS[q] for extension in ['npz','json']}
def main():
    paper=json.loads((HERE/'paper.json').read_text())
    dataset=json.loads((ROOT/'docs/data/benchmark.json').read_text())
    require(next(p for p in dataset['papers'] if p['id']==paper['id'])==paper,'Paper registration differs')
    require(len(paper['scenarios'])==4,'Expected four questions')
    provenance=json.loads((DATA/'provenance.json').read_text())
    require(provenance['version']=='open-research-v2','Stale provenance revision')
    raw_files={f'{chem}_{kind}.{ext}' for chem in CHEMS for kind in ['1-Phase','Mixtures','Experiments'] for ext in ['npz','json']}
    require({p.name for p in (DATA/'inputs').iterdir() if p.is_file()}==raw_files,'Inputs include missing/extra non-raw assets')
    require(set(provenance['input_files'])==raw_files,'Provenance file set differs')
    for name,digest in provenance['input_files'].items():require(sha(DATA/'inputs'/name)==digest,'Input hash differs: '+name)
    sample_ids=set();inventory=[]
    for chem in CHEMS:
        for kind in ['1-Phase','Mixtures','Experiments']:
            stem=f'{chem}_{kind}';rows=json.loads((DATA/'inputs'/f'{stem}.json').read_text())
            allowed={'id','chemistry','phases'} | ({'replicate'} if kind=='1-Phase' else {'major','minor','minor_weight_percent'} if kind=='Experiments' else set())
            with np.load(DATA/'inputs'/f'{stem}.npz',allow_pickle=False) as archive:
                keys={row['id'] for row in rows}
                require(set(archive.files)==keys | ({'theta'} if kind!='Experiments' else set()),'Archive/metadata keys differ: '+stem)
                require(len(keys)==len(rows),'Duplicate metadata IDs')
                for row in rows:
                    sid=row['id'];require(set(row)==allowed,'Unnecessary metadata field/split in '+stem)
                    require(re.fullmatch(r'[AB]_[SME]_[0-9a-f]{16}',sid),'ID exposes source label/count: '+sid)
                    require(sid not in sample_ids,'Duplicate ID');sample_ids.add(sid)
                    require(row['chemistry']==chem,'Wrong chemistry')
                    arr=archive[sid]
                    require(arr.dtype==np.float64 and np.isfinite(arr).all(),'Nonfinite or non-float64 source array')
                    if kind=='Experiments':
                        require(arr.ndim==2 and arr.shape[1]==2,'Experimental shape differs');axis=arr[:,0]
                    else:
                        axis=archive['theta'];require(arr.ndim==1 and len(arr)==len(axis),'Simulation shape differs')
                    require(np.all(np.diff(axis)>0),'Nonmonotone raw angle axis')
            inventory.append({'chemistry':chem,'kind':kind,'patterns':len(rows)})
    require(len(sample_ids)==2930,'Raw record coverage differs')
    exports=[]
    with tempfile.TemporaryDirectory(prefix='szymanski-v2-export-check-') as temporary:
        for scenario in paper['scenarios']:
            q=scenario['id'].rsplit('-',1)[-1];expected=expected_inputs(q)
            require({a['name'] for a in scenario['inputs']}==expected,'Wrong per-question raw input set')
            prompt='\n'.join(scenario['prompt'].values())
            for token in ['protocol.json','output_schema.json','RidgeClassifier','NNLS','paired training/test protocol','prescribed single-phase training']:
                require(token not in prompt,'Hidden recipe in prompt: '+token)
            for field in ['predictions.csv','splits.csv','metrics.csv','report.md']:
                require(field in prompt,'Output essentials not inline: '+field)
            require('the paper' not in prompt.lower() and 'doi.org' not in prompt.lower(),'Paper-dependent prompt')
            dest=Path(temporary)/q
            command=[sys.executable,str(HERE/'export_agent_bundle.py'),q,'--output',str(dest)]
            result=subprocess.run(command,capture_output=True,text=True)
            require(result.returncode==0,result.stderr)
            paths={f.relative_to(dest).as_posix() for f in dest.rglob('*') if f.is_file()}
            require(paths=={'task.json'} | {'inputs/'+name for name in expected},'Export contains non-input assets')
            for name in expected:require(sha(dest/'inputs'/name)==sha(DATA/'inputs'/name),'Export mutates raw input')
            task=json.loads((dest/'task.json').read_text())
            require(set(task)=={'id','title','background','instruction','inputs','data_attribution'},'Unexpected task fields')
            require(task['background']==scenario['prompt']['background'] and task['instruction']==scenario['prompt']['instruction'],'Prompt differs in export')
            require(task['inputs']==[{'name':a['name'],'path':'inputs/'+a['name'],'description':a['description']} for a in scenario['inputs']],'Input manifest differs')
            require(subprocess.run(command,capture_output=True).returncode!=0,'Exporter accepts contaminated destination')
            exports.append({'question':q,'raw_input_files':len(expected),'exact_allowlist':True,'raw_hashes_match':True,'prompt_is_self_contained':True,'nonempty_destination_rejected':True})
    check=subprocess.run([sys.executable,str(ROOT/'scripts/validate_data.py')],capture_output=True,text=True)
    require(check.returncode==0,check.stdout+check.stderr)
    report={'revision':'open-research-v2','status':'passed','sample_count':len(sample_ids),'inventory':inventory,'exports':exports,
            'input_only_files':sorted(raw_files),'protocol_and_schema_files_absent':True,'preassigned_splits_absent':True,
            'pooled_mixture_ids_opaque':True,'schema_validation':check.stdout.strip(),
            'label_boundary':'Labels remain readable for scientific evaluation; target separation requires submitted-code/execution review, not just CSV checks.'}
    (DATA/'verification/packaging_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
