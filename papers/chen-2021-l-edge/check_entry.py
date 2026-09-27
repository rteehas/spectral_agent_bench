#!/usr/bin/env python3
"""Check the local index, native asset hashes and solver/evaluator boundary."""
import hashlib
import json
import tempfile
from pathlib import Path
from export_agent_bundle import export
from questions import BACKGROUND, QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/data/chen-2021-l-edge'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def main():
    paper = json.loads((HERE / 'paper.json').read_text())
    active = json.loads((ROOT / 'docs/data/benchmark.json').read_text())
    assert next(p for p in active['papers'] if p['id'] == paper['id']) == paper
    prov = json.loads((BASE / 'provenance.json').read_text())
    for asset in prov['input_assets']:
        assert sha(BASE / 'inputs' / asset['name']) == asset['sha256']
    checks = []
    for spec in QUESTIONS:
        scenario = next(s for s in paper['scenarios'] if s['id'] == 'CHEN21-' + spec['id'])
        assert scenario['prompt'] == {'background': BACKGROUND, 'instruction': spec['instruction']}
        with tempfile.TemporaryDirectory(prefix='chen-export-check-') as temp:
            out = Path(temp) / 'agent'
            export(spec['id'], out)
            task = json.loads((out / 'task.json').read_text())
            assert set(task) == {'id', 'title', 'background', 'instruction', 'inputs', 'attribution'}
            assert task['background'] == BACKGROUND and task['instruction'] == spec['instruction']
            expected = {'task.json'} | {'inputs/' + a['name'] for a in prov['input_assets']}
            assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()} == expected
            for asset in prov['input_assets']:
                assert sha(out / 'inputs' / asset['name']) == asset['sha256']
            checks.append({'question': spec['id'], 'files': len(expected), 'native_inputs_match': True,
                           'no_evaluator_files': True, 'prompt_matches_index': True})
    result = {'passed': True, 'input_hashes_checked': len(prov['input_assets']),
              'active_index_matches': True, 'questions': checks}
    (BASE / 'verification/packaging_checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
