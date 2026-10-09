#!/usr/bin/env python3
"""Check packaging, source hashes and the standalone prompt boundary."""
import gzip
import hashlib
import json
import zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'docs/data/torrisi-2020-xanes-rf'
def main():
    paper=json.loads((Path(__file__).parent/'paper.json').read_text())
    dataset=json.loads((ROOT/'docs/data/benchmark.json').read_text())
    assert next(p for p in dataset['papers'] if p['id']==paper['id'])==paper
    provenance=json.loads((DATA/'provenance.json').read_text())
    total=0
    for source in provenance['sources']:
        path=DATA/source['input_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source['input_sha256']
        with gzip.open(path,'rt') as f:rows=[json.loads(line) for line in f]
        assert len(rows)==source['rows']
        assert [r['source_row'] for r in rows]==list(range(len(rows)))
        total+=len(rows)
    assert total==40907
    assert sorted(p.name for p in (DATA/'inputs').iterdir())==sorted([s['element']+'.jsonl.gz' for s in provenance['sources']]+['Q1_paper'])
    for scenario in paper['scenarios']:
        if scenario['id']=='TORRISI20-Q1':
            assert len(scenario['inputs'])==9
            assert {i['name'] for i in scenario['inputs']}=={'protocol.json'}|{s['element']+'.npz' for s in provenance['sources']}
            for item in scenario['inputs']:
                path=ROOT/'docs'/item['url']
                assert '/inputs/Q1_paper/' in item['url'] and path.is_file()
                if path.suffix=='.npz':
                    with zipfile.ZipFile(path) as archive:
                        assert set(archive.namelist())=={key+'.npy' for key in ['energy_eV','train_spectra','train_labels','train_source_rows','validation_spectra','validation_labels','validation_source_rows','test_spectra','test_source_rows']}
            assert scenario['executionStatus']=='executed_publication_reproduction'
            continue
        assert len(scenario['inputs'])==8
        assert all('/inputs/' in i['url'] and i['name'].endswith('.jsonl.gz') for i in scenario['inputs'])
        prompt=' '.join(scenario['prompt'].values()).lower()
        assert not any(s in prompt for s in ['torrisi','paper','figure 3','reproduce','doi.org','protocol.json','output_schema.json','random forest','seed 42','157 features'])
        assert 'partitions.csv' in prompt and 'predictions.csv' in prompt
        assert not any(term in prompt for term in ['for audit','provenance','design.json','metrics.csv','run_id','comparison_id','identified_material','condition=','target='])
        assert 'metadata.id' in prompt and 'metadata.origin' in prompt
        for item in scenario['inputs']:assert (ROOT/'docs'/item['url']).is_file()
    report=dict(paper_id=paper['id'],questions=len(paper['scenarios']),input_records=total,input_hashes_match=True,paper_matches_active_dataset=True,
                q1_has_prepared_partitions_without_test_labels=True,q2_q5_have_only_raw_input_assets=True,
                input_file_count_per_question={'Q1':9,'Q2':8,'Q3':8,'Q4':8,'Q5':8},
                note='Q1 exports eight prepared NPZ files and its fixed protocol; test labels are evaluator-only. Q2-Q5 export the unchanged raw projections. Evaluator website/repository and other-question input access must be denied during an attempt.')
    (DATA/'verification/packaging_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
