#!/usr/bin/env python3
"""Export only native inputs and minimal task text, never evaluator assets."""
import argparse
import json
import shutil
from pathlib import Path
from questions import BACKGROUND, QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')


def export(question, output):
    spec = next(q for q in QUESTIONS if q['id'] == question)
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
    p.add_argument('question', choices=['Q1', 'Q2', 'Q3'])
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    export(a.question, a.output)
