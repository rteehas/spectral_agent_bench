#!/usr/bin/env python3
"""Check packaging, input boundaries and exact material-ID overlap."""
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
    anchors=json.loads((DATA/'verification/source_anchor_audit.json').read_text())
    total=0; overlaps=[]
    for source in provenance['sources']:
        element=source['element'];path=DATA/source['input_path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source['input_sha256']
        with gzip.open(path,'rt') as f:rows=[json.loads(line) for line in f]
        assert len(rows)==source['rows']
        assert [r['source_row'] for r in rows]==list(range(len(rows)))
        total+=len(rows)
        for target,t in anchors['elements'][element]['targets'].items():
            train=t['partitions']['train']['source_rows'];test=t['partitions']['test']['source_rows']
            def material(i):
                m=rows[i]['metadata']
                return str(m.get('id')) if m and m.get('id') is not None else None
            train_ids={material(i) for i in train}-{None}
            n=sum(material(i) in train_ids for i in test)
            overlaps.append(dict(element=element,target=target,test_records=len(test),
                                 test_records_with_material_id_in_training=n,overlap_fraction=n/len(test)))
    assert total==40907
    for scenario in paper['scenarios']:
        assert len(scenario['inputs'])==11
        assert all('/inputs/' in i['url'] for i in scenario['inputs'])
        prompt=' '.join(scenario['prompt'].values()).lower()
        assert not any(s in prompt for s in ['torrisi','paper','figure 3','reproduce','doi.org'])
        for item in scenario['inputs']:
            assert (ROOT/'docs'/item['url']).is_file()
    report=dict(paper_id=paper['id'],questions=len(paper['scenarios']),input_records=total,
                input_hashes_match=True,paper_matches_active_dataset=True,
                all_scenarios_have_only_input_assets=True,solver_prompts_have_no_paper_references=True,
                input_file_count_per_question=11,
                note='Exported solver bundles omit all workflows, published output arrays, ground truth and paper metadata.')
    (DATA/'verification/packaging_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    (DATA/'verification/material_overlap_audit.json').write_text(json.dumps(dict(
        meaning='Exact released metadata.id appears in training and test. This does not resolve structural equivalence or cross-database aliases.',
        conclusion='These splits test held-out spectral records, not held-out material identifiers.',
        conditions=overlaps),indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
