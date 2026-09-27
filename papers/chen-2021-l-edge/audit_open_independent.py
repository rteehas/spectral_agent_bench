#!/usr/bin/env python3
"""Independent public-contract, corruption and pending-mapping controls."""
import argparse,csv,importlib.util,json,shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];wf=root/'docs/data/chen-2021-l-edge/workflows';sys.path.insert(0,str(wf));from verify_submission import verify_submission
parser=argparse.ArgumentParser();parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--record',type=Path,required=True);args=parser.parse_args();work=args.work;work.mkdir(exist_ok=True);src=args.candidate
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def write(p,rr,fields=None):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rr[0]),extrasaction='ignore');w.writeheader();w.writerows(rr)
def copy(name):
 p=work/name
 if p.exists():shutil.rmtree(p)
 shutil.copytree(src,p);return p
checks=[]
def run(name,p,expected):
 r=verify_submission('Q3',p);checks.append({'case':name,'expected_integrity_pass':expected,'observed_integrity_pass':r['integrity_pass'],'scientific_pass':r['scientific_pass'],'numerical_validation':r['numerical_validation'],'error':r.get('error'),'pending':r['independent_review_required'],'check_agreed':r['integrity_pass']==expected});print(name,r['integrity_pass'],r.get('error'),flush=True)
p=copy('different_learner_split_public_columns');rr=read(p/'predictions.csv');pp=read(p/'partitions.csv');ss=read(p/'sites.csv')
for r in rr+pp:r['method']='alternative learner '+r['method'];r['split']='outer fold '+r['split']
write(p/'predictions.csv',rr,['name','method','split','predicted']);write(p/'partitions.csv',pp,['material','method','split','role']);write(p/'sites.csv',[{'record_name':r['name'],'reference_environment':r['geometry']} for r in ss]);run('different_learner_split_public_columns',p,True)
p=copy('corrupt_prediction_identity');rr=read(p/'predictions.csv');rr[0]['name']='not-a-native-source';write(p/'predictions.csv',rr);run('corrupt_prediction_identity',p,False)
p=copy('corrupt_observation_identity');ss=read(p/'sites.csv');ss[0]['name']='not-a-native-source';write(p/'sites.csv',ss);run('corrupt_observation_identity',p,False)
p=copy('composition_leakage');rr=read(p/'predictions.csv');pp=read(p/'partitions.csv');target=rr[0];same=[r for r in rr if r['composition_key']==target['composition_key'] and r['material']!=target['material'] and r['method']==target['method'] and r['split']==target['split']]
if not same:
 for candidate in rr:
  same=[r for r in rr if r['composition_key']==candidate['composition_key'] and r['material']!=candidate['material'] and r['method']==candidate['method'] and r['split']==candidate['split']]
  if same:target=candidate;break
assert same
other=same[0]['material']
rr=[r for r in rr if not (r['material']==other and r['method']==target['method'] and r['split']==target['split'])]
for r in pp:
 if r['material']==other and r['method']==target['method'] and r['split']==target['split']:r['role']='train'
write(p/'predictions.csv',rr);write(p/'partitions.csv',pp);run('composition_leakage',p,False)
p=copy('validation_composition_leakage');rr=read(p/'predictions.csv');pp=read(p/'partitions.csv');rr=[r for r in rr if not (r['material']==other and r['method']==target['method'] and r['split']==target['split'])]
for r in pp:
 if r['material']==other and r['method']==target['method'] and r['split']==target['split']:r['role']='validation'
write(p/'predictions.csv',rr);write(p/'partitions.csv',pp);run('validation_composition_leakage',p,False)
p=copy('nonfinite_prediction');rr=read(p/'predictions.csv');rr[0]['predicted']='nan';write(p/'predictions.csv',rr);run('nonfinite_prediction',p,False)
p=copy('role_aliases');pp=read(p/'partitions.csv')
for r in pp:r['role']={'train':'training','test':'holdout','validation':'val','unused':'unused'}[r['role']]
write(p/'partitions.csv',pp);run('role_aliases',p,True)
p=copy('custom_partition_alias');pp=read(p/'partitions.csv');pp[0]['material']='resolved_material_alias';write(p/'partitions.csv',pp);run('custom_partition_alias',p,None)
p=copy('custom_complete_alias');pp=read(p/'partitions.csv');ss=read(p/'sites.csv');rr=read(p/'predictions.csv');chosen=pp[0]['material']
for row in pp+ss+rr:
 if row.get('material')==chosen:row['material']='resolved_material_alias'
write(p/'partitions.csv',pp);write(p/'sites.csv',ss);write(p/'predictions.csv',rr);run('custom_complete_alias',p,None)
p=copy('unknown_declared_role');pp=read(p/'partitions.csv');pp[0]['role']='fitting_cohort';write(p/'partitions.csv',pp);run('unknown_declared_role',p,None)
args.record.parent.mkdir(parents=True,exist_ok=True);args.record.write_text(json.dumps(checks,indent=2)+'\n');raise SystemExit(0 if all(c['check_agreed'] for c in checks) else 1)
