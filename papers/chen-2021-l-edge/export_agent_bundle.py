#!/usr/bin/env python3
"""Export only native inputs and minimal task text, never evaluator assets."""
import argparse
import json
import shutil
from pathlib import Path
from questions import BACKGROUND, QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')


def export(question, output, allow_unvalidated=False):
    spec = next(q for q in QUESTIONS if q['id'] == question)
    acceptance = ROOT / 'docs/data/chen-2021-l-edge/paper_results/verification' / f'{question}_acceptance.json'
    if not allow_unvalidated and (not acceptance.is_file() or not json.loads(acceptance.read_text()).get('accepted')):
        raise ValueError(f'{question} is not validated for scoring. --allow-unvalidated is required for evaluator development only.')
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new or empty output directory')
    (output / 'inputs').mkdir(parents=True, exist_ok=True)
    inputs = []
    for e in ELEMENTS:
        name = f'{e}.jsonl.gz'
        shutil.copyfile(ROOT / 'docs/data/chen-2021-l-edge/inputs' / name, output / 'inputs' / name)
        inputs.append({'name': name, 'path': 'inputs/' + name, 'description': f'Native {e} absorbing-site calculation records.'})
    task = {'id': 'CHEN21-' + question, 'title': spec['title'], 'background': BACKGROUND,
            'instruction': spec['instruction'], 'inputs': inputs,
            'attribution': 'Data: Yiming Chen (2020), DOI 10.6084/m9.figshare.12824513.v1; MIT license https://opensource.org/licenses/MIT. All native records for the eight named absorbing elements are retained verbatim in separate gzip containers.'}
    (output / 'task.json').write_text(json.dumps(task, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'question': question, 'output': str(output.resolve()), 'files': len(inputs) + 1}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('question', choices=[q['id'] for q in QUESTIONS])
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--allow-unvalidated', action='store_true', help='Evaluator development only; does not grant scientific acceptance')
    a = p.parse_args()
    export(a.question, a.output, a.allow_unvalidated)
