#!/usr/bin/env python3
"""Independently check assets, solver export boundaries and public data schema."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / 'docs/data/szymanski-2024-xrd-pdf'
CHEMISTRIES = ['Li-La-Zr-O', 'Li-Ti-P-O']
KINDS = {
    'Q1': ['1-Phase'],
    'Q2': ['1-Phase', '2-Phase', '3-Phase'],
    'Q3': ['1-Phase'],
    'Q4': ['1-Phase', 'Experiments'],
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_inputs(question):
    chems = ['Li-Ti-P-O'] if question == 'Q3' else CHEMISTRIES
    return {
        f'{chem}_{kind}.{extension}'
        for chem in chems for kind in KINDS[question]
        for extension in ['json', 'npz']
    } | {'protocol.json', 'output_schema.json', 'README.md'}


def main():
    paper = json.loads((HERE / 'paper.json').read_text())
    dataset = json.loads((ROOT / 'docs/data/benchmark.json').read_text())
    require(next(p for p in dataset['papers'] if p['id'] == paper['id']) == paper,
            'Paper entry differs from the active dataset')
    require(len(paper['scenarios']) == 4, 'Expected exactly four questions')
    provenance = json.loads((DATA / 'provenance.json').read_text())
    for filename, digest in provenance['input_files'].items():
        require(sha(DATA / 'inputs' / filename) == digest, f'Input hash mismatch: {filename}')

    inventories = []
    sample_ids = set()
    for chem in CHEMISTRIES:
        for kind in ['1-Phase', '2-Phase', '3-Phase', 'Experiments']:
            stem = f'{chem}_{kind}'
            rows = json.loads((DATA / 'inputs' / f'{stem}.json').read_text())
            allowed = {'id', 'chemistry', 'kind', 'phases'} | (
                {'replicate', 'split'} if kind == '1-Phase' else
                {'major', 'minor', 'minor_weight_percent'} if kind == 'Experiments' else set())
            with np.load(DATA / 'inputs' / f'{stem}.npz', allow_pickle=False) as archive:
                keys = {r['id'] for r in rows}
                require(set(archive.files) == keys | ({'theta'} if kind != 'Experiments' else set()),
                        f'Unexpected numeric archive keys in {stem}')
                for row in rows:
                    require(set(row) == allowed, f'Unexpected metadata fields in {stem}')
                    require(row['chemistry'] == chem and row['kind'] == kind,
                            f'Inconsistent metadata in {stem}')
                    require(re.fullmatch(r'[AB]_(?:[123]-Phase|Experiments)_\d{4}', row['id']),
                            f'Non-anonymous sample ID: {row["id"]}')
                    require(row['id'] not in sample_ids, f'Duplicate sample ID: {row["id"]}')
                    sample_ids.add(row['id'])
                    values = archive[row['id']]
                    require(values.dtype == np.dtype('float64') and np.isfinite(values).all(),
                            f'Invalid numeric spectrum: {row["id"]}')
                    if kind == 'Experiments':
                        require(values.ndim == 2 and values.shape[1] == 2,
                                f'Invalid measured scan shape: {row["id"]}')
                        theta = values[:, 0]
                    else:
                        require(values.ndim == 1 and len(values) == len(archive['theta']),
                                f'Invalid simulated scan shape: {row["id"]}')
                        theta = archive['theta']
                    require(np.all(np.diff(theta) > 0), f'Invalid angle axis: {row["id"]}')
            inventories.append({'chemistry': chem, 'kind': kind, 'patterns': len(rows)})
    require(len(sample_ids) == 2930, 'Unexpected total spectrum count')

    exports = []
    with tempfile.TemporaryDirectory(prefix='szymanski-export-audit-') as temp:
        temp = Path(temp)
        for scenario in paper['scenarios']:
            question = scenario['id'].rsplit('-', 1)[-1]
            expected = expected_inputs(question)
            require({a['name'] for a in scenario['inputs']} == expected,
                    f'Irrelevant or missing input asset in {question}')
            for asset in scenario['inputs']:
                require(asset['url'] == f'data/szymanski-2024-xrd-pdf/inputs/{asset["name"]}',
                        f'Non-input asset in {question}: {asset["url"]}')
            prompt = '\n'.join(scenario['prompt'].values()).lower()
            require(not any(term in prompt for term in ['szymanski', 'the paper', 'figure ', 'doi.org', 'reproduce']),
                    f'Paper-facing question wording in {question}')
            destination = temp / question
            command = [sys.executable, str(HERE / 'export_agent_bundle.py'), question,
                       '--output', str(destination)]
            completed = subprocess.run(command, text=True, capture_output=True)
            require(completed.returncode == 0, f'Export failed: {question}: {completed.stderr}')
            expected_paths = {'task.json', 'README.md'} | {f'inputs/{name}' for name in expected}
            actual_paths = {p.relative_to(destination).as_posix()
                            for p in destination.rglob('*') if p.is_file()}
            require(actual_paths == expected_paths,
                    f'Export contains missing, irrelevant or answer assets: {question}')
            for name in expected - {'protocol.json', 'output_schema.json'}:
                require(sha(destination / 'inputs' / name) == sha(DATA / 'inputs' / name),
                        f'Export transformed input unexpectedly: {question}/{name}')
            protocol = json.loads((DATA / 'inputs/protocol.json').read_text())
            needed = {'Q1': {'Q1'}, 'Q2': {'Q1', 'Q2'}, 'Q3': {'Q3'},
                      'Q4': {'Q1', 'Q2', 'Q4'}}[question]
            expected_protocol = {k: v for k, v in protocol.items()
                                 if not k.startswith('Q') or k in needed}
            require(json.loads((destination / 'inputs/protocol.json').read_text()) == expected_protocol,
                    f'Export protocol includes irrelevant or missing instructions: {question}')
            schema = json.loads((DATA / 'inputs/output_schema.json').read_text())
            if question == 'Q3':
                del schema['classification']
            else:
                del schema['Q3']
                schema['classification']['questions'] = [question]
            require(json.loads((destination / 'inputs/output_schema.json').read_text()) == schema,
                    f'Export schema includes irrelevant or missing instructions: {question}')
            task = json.loads((destination / 'task.json').read_text())
            require(set(task) == {'id', 'title', 'background', 'instruction', 'inputs'},
                    f'Unexpected exported task fields: {question}')
            require(task['instruction'] == scenario['prompt']['instruction'] and
                    task['background'] == scenario['prompt']['background'],
                    f'Export changed the question: {question}')
            require(task['inputs'] == [{'name': a['name'], 'path': 'inputs/' + a['name'],
                                       'description': a['description']} for a in scenario['inputs']],
                    f'Export input manifest differs from task: {question}')
            # An existing nonempty destination must be rejected, preserving the clean boundary.
            rejected = subprocess.run(command, text=True, capture_output=True)
            require(rejected.returncode != 0, f'Exporter accepts contaminated/nonempty destination: {question}')
            exports.append({'question': question, 'input_files': len(expected),
                            'exact_allowlist_passed': True, 'raw_input_hashes_match': True,
                            'protocol_and_schema_have_only_relevant_sections': True,
                            'nonempty_destination_rejected': True})

    schema = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_data.py')],
                            text=True, capture_output=True)
    require(schema.returncode == 0, schema.stdout + schema.stderr)
    report = {
        'paper_id': paper['id'], 'status': 'passed', 'questions': 4,
        'sample_count': len(sample_ids), 'inventory': inventories,
        'input_hashes_match': True, 'paper_matches_active_dataset': True,
        'exports': exports, 'schema_validation': schema.stdout.strip(),
        'answer_boundary': 'Exports contain only task.json, reading instructions and the exact relevant numeric inputs, '
                           'released label/split metadata, protocol, output schema and field definitions. '
                           'No candidate implementation, fitted parameters, predictions, reference '
                           'results, verification files or paper metadata are exported. Released '
                           'labels are evaluation data; output-only validation cannot prove no target-label leakage.',
    }
    (DATA / 'verification/packaging_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
