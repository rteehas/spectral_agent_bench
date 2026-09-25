#!/usr/bin/env python3
"""Check packaging, source hashes and the standalone prompt boundary."""
import gzip
import hashlib
import json
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
    assert sorted(p.name for p in (DATA/'inputs').iterdir())==sorted(s['element']+'.jsonl.gz' for s in provenance['sources'])
    for scenario in paper['scenarios']:
        assert len(scenario['inputs'])==8
        assert all('/inputs/' in i['url'] and i['name'].endswith('.jsonl.gz') for i in scenario['inputs'])
        prompt=' '.join(scenario['prompt'].values()).lower()
        assert not any(s in prompt for s in ['torrisi','paper','figure 3','reproduce','doi.org','protocol.json','output_schema.json','random forest','seed 42','157 features'])
        assert 'design.json' in prompt and 'partitions.csv' in prompt and 'predictions.csv' in prompt
        for item in scenario['inputs']:assert (ROOT/'docs'/item['url']).is_file()
    report=dict(paper_id=paper['id'],questions=len(paper['scenarios']),input_records=total,input_hashes_match=True,paper_matches_active_dataset=True,
                all_scenarios_have_only_raw_input_assets=True,solver_prompts_have_no_paper_references=True,input_file_count_per_question=8,
                protocol_and_schema_files_absent=True,
                note='Exported solver bundles contain prompt.md and eight raw projections only. Evaluator website/repository access must be denied during an attempt.')
    (DATA/'verification/packaging_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
