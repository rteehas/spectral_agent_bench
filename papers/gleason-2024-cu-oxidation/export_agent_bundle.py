"""Export only the selected agent prompt and declared inputs; no solutions/evidence."""
import argparse,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PUBLIC=ROOT/'docs'

def export(question,out):
    data=json.loads((PUBLIC/'data/benchmark.json').read_text());paper=next(p for p in data['papers'] if p['id']=='gleason-2024-cu-oxidation');sid=question if question.startswith('GLEASON24-') else 'GLEASON24-'+question
    task=next(s for s in paper['scenarios'] if s['id']==sid)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new or empty bundle directory to avoid carrying evaluator files into an agent run')
    out.mkdir(parents=True,exist_ok=True);dest=out/'inputs';dest.mkdir(exist_ok=True)
    for source in task['inputs']:
        path=(PUBLIC/source['url']).resolve()
        if PUBLIC.resolve() not in path.parents:raise ValueError('Input path outside docs/')
        shutil.copyfile(path,dest/source['name'])
    prompt=task['prompt'];text=task['title']+'\n\nBackground\n'+prompt['background']+'\n\nInputs\n'+'\n'.join(f"- inputs/{f['name']}: {f['description']}" for f in task['inputs'])+'\n\nQuestion\n'+prompt['instruction']+'\n'
    (out/'prompt.txt').write_text(text)
    return {'scenario':sid,'files':['prompt.txt']+['inputs/'+f['name'] for f in task['inputs']]}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('question');p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(export(a.question,a.output),indent=2))
