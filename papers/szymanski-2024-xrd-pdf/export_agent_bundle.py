#!/usr/bin/env python3
"""Export a question without evaluator outputs, source filenames or solution code."""
import argparse,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PAPER=Path(__file__).resolve().parent

def export(question,output):
 paper=json.loads((PAPER/'paper.json').read_text())
 scenario=next(s for s in paper['scenarios'] if s['id']=='SZYMANSKI24-'+question)
 output=Path(output)
 if output.exists() and any(output.iterdir()):raise ValueError('Choose a new/empty output directory')
 (output/'inputs').mkdir(parents=True,exist_ok=True)
 names=[]
 for asset in scenario['inputs']:
  source=ROOT/'docs'/asset['url'];assert source.parent.name=='inputs'
  shutil.copyfile(source,output/'inputs'/source.name);names.append(source.name)
 # Keep referenced definitions for Q2/Q4 without copying unrelated question text.
 protocol_path=output/'inputs/protocol.json';protocol=json.loads(protocol_path.read_text())
 needed={'Q1':['Q1'],'Q2':['Q1','Q2'],'Q3':['Q3'],'Q4':['Q1','Q2','Q4']}[question]
 protocol={key:value for key,value in protocol.items() if not key.startswith('Q') or key in needed}
 protocol_path.write_text(json.dumps(protocol,indent=2)+'\n')
 schema_path=output/'inputs/output_schema.json';schema=json.loads(schema_path.read_text())
 if question=='Q3':schema.pop('classification')
 else:schema.pop('Q3');schema['classification']['questions']=[question]
 schema_path.write_text(json.dumps(schema,indent=2)+'\n')
 task={'id':scenario['id'],'title':scenario['title'],'background':scenario['prompt']['background'],'instruction':scenario['prompt']['instruction'],'inputs':[{'name':a['name'],'path':'inputs/'+a['name'],'description':a['description']} for a in scenario['inputs']]}
 (output/'task.json').write_text(json.dumps(task,indent=2)+'\n')
 (output/'README.md').write_text('Read task.json, then inputs/README.md. Use only these inputs. Build the analysis and produce the required numerical files, plots and evidence-backed conclusion. Preparation labels are evaluation-only: exclude target labels during prediction. No network or pretrained model is needed.\n')
 return {'question':question,'output':str(output.resolve()),'files':sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('question',choices=['Q1','Q2','Q3','Q4']);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(export(a.question,a.output),indent=2))
