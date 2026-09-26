#!/usr/bin/env python3
"""Packaging, export-boundary and cross-index checks (standard library only)."""
import hashlib,json,tempfile
from pathlib import Path
from export_agent_bundle import export
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'docs/data/guo-2023-sulfur-xas'
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def main():
    paper=json.loads((HERE/'paper.json').read_text()); active=json.loads((ROOT/'docs/data/benchmark.json').read_text()); prov=json.loads((BASE/'provenance.json').read_text())
    assert next(p for p in active['papers'] if p['id']==paper['id'])==paper
    for item in prov['input_assets']:assert sha(BASE/'inputs'/item['name'])==item['sha256']
    checks=[]
    for s in paper['scenarios']:
        q=s['id'].split('-')[-1]
        with tempfile.TemporaryDirectory(prefix='guo-export-audit-') as d:
            output=Path(d)/'agent';export(q,output)
            task=json.loads((output/'task.json').read_text())
            assert set(task)=={'id','title','background','instruction','inputs','attribution'}
            expected={'task.json'}|{'inputs/'+i['name'] for i in s['inputs']}
            actual={str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()}
            assert actual==expected and len(actual)==9
            assert not any(w in (task['background']+' '+task['instruction']).lower() for w in ['figure 3','guo et','candidate.py','verify.py','randomforest','random forest','2.6 å'])
            for i in s['inputs']:assert sha(output/'inputs'/i['name'])==sha(ROOT/'docs'/i['url'])
            checks.append({'question':q,'export_file_count':len(actual),'inputs_match':True,'no_evaluator_files':True})
    result={'passed':True,'input_hashes_checked':len(prov['input_assets']),'questions':checks,'active_index_matches':True}
    (BASE/'verification/packaging_checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
