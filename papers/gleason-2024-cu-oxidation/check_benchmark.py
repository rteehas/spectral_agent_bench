"""Check input boundaries and that each numerical grader rejects a wrong answer."""
import argparse,copy,importlib.util,json,shutil,tempfile
from pathlib import Path
from export_agent_bundle import ROOT,export
DATA=ROOT/'docs/data/gleason-2024-cu-oxidation'
spec=importlib.util.spec_from_file_location('gleason_verifier',DATA/'workflows/verify.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate-runs',type=Path,required=True);a=p.parse_args();reports=[]
    fields={'Q1':('points',1),'Q6':('generated',1),'Q7':('CuO_minus_Cu2O_eV',1.)}
    dataset=json.loads((ROOT/'docs/data/benchmark.json').read_text());paper=next(x for x in dataset['papers'] if x['id']=='gleason-2024-cu-oxidation')
    with tempfile.TemporaryDirectory(prefix='gleason-bench-check-') as temp:
        base=Path(temp)
        for task in paper['scenarios']:
            q=task['id'].split('-')[-1];bundle=base/q;manifest=export(q,bundle)
            expected={'prompt.txt'}|{'inputs/'+x['name'] for x in task['inputs']};actual={str(x.relative_to(bundle)) for x in bundle.rglob('*') if x.is_file()}
            assert actual==expected,(q,'bundle differs from declared input boundary')
            text=(bundle/'prompt.txt').read_text();assert task['groundTruthReasoning'] not in text
            assert 'verification/' not in text and 'candidate.py' not in text and 'expected.json' not in text
            for f in task['inputs']:
                source=ROOT/'docs'/f['url'];assert source.read_bytes()==(bundle/'inputs'/f['name']).read_bytes()
            if task.get('executionStatus')=='partially_validated':
                reports.append({'question':q,'input_bundle_only_declared_files':True,
                                'end_to_end_check':'not_run','reason':'Live MP access and fresh FEFF9 execution require separate runtime validation; see setup_checks.json.'})
                continue
            original=a.candidate_runs/q/'output';v.verify(q,original,DATA/'verification'/q)
            wrong=bundle/'wrong';shutil.copytree(original,wrong);j=json.loads((wrong/'result.json').read_text());field,delta=fields[q];j[field]+=delta;(wrong/'result.json').write_text(json.dumps(j))
            rejected=False
            try:v.verify(q,wrong,DATA/'verification'/q)
            except AssertionError:rejected=True
            assert rejected,(q,'incorrect answer was accepted')
            reports.append({'question':q,'input_bundle_only_declared_files':True,'correct_candidate_passes':True,'perturbed_answer_rejected':True})
        # Array-level rejection, independent of the scalar result.json checks.
        q='Q6';wrong=base/'wrong-mixture-weight';shutil.copytree(a.candidate_runs/q/'output',wrong)
        import pandas as pd
        d=pd.read_csv(wrong/'manifest.csv');d.loc[200,'weight_0']+=.1;d.to_csv(wrong/'manifest.csv',index=False)
        try:v.verify(q,wrong,DATA/'verification'/q)
        except AssertionError:array_rejected=True
        else:array_rejected=False
        assert array_rejected,'altered mixture weight was accepted'
    report={'checks':reports,'perturbed_mixture_weight_rejected':array_rejected,'scope':'Active questions only: input export and verifier sensitivity, not an OS-level data-access isolation test.'}
    (DATA/'verification/benchmark_checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
