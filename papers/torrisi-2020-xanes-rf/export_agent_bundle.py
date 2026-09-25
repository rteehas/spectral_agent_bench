#!/usr/bin/env python3
"""Export one solver-only question; exclude paper metadata and held-back answers."""
import argparse
import json
import shutil
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question',choices=['Q1','Q2','Q3','Q4','Q5'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    root=here.parents[1]
    paper=json.loads((here/'paper.json').read_text())
    task=next(s for s in paper['scenarios'] if s['id'].endswith('-'+args.question))
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('output must be absent or empty to avoid mixing evaluator files into inputs')
    dest=args.output/'inputs';dest.mkdir(parents=True,exist_ok=True)
    for item in task['inputs']:
        source=root/'docs'/item['url']
        if '/inputs/' not in item['url']:
            raise ValueError('Refusing non-input asset')
        shutil.copyfile(source,dest/item['name'])
    prompt=task['title']+'\n\n'+task['prompt']['background']+'\n\nInputs:\n'
    prompt+='\n'.join(f'- inputs/{i["name"]}: {i["description"]}' for i in task['inputs'])
    prompt+='\n\n'+task['prompt']['instruction']+'\n'
    (args.output/'prompt.md').write_text(prompt)
    print(f'Exported {args.question}: prompt and {len(task["inputs"])} input files to {args.output}')

if __name__=='__main__':main()
