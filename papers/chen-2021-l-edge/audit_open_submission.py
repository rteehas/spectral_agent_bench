#!/usr/bin/env python3
"""Exercise the public-contract route without requiring worked-profile artifacts."""
import argparse,csv,hashlib,json,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/data/chen-2021-l-edge'
sys.path.insert(0,str(BASE/'workflows'))
from verify_submission import verify_submission


def csv_read(path):
    with path.open(newline='') as f:
        reader=csv.DictReader(f);return list(reader),reader.fieldnames

def csv_write(path,rows,fields):
    if path.is_symlink():path.unlink()
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows([{k:r[k] for k in fields} for r in rows])

def alter(path,fn):
    r,h=csv_read(path);fn(r);csv_write(path,r,h)

def mirror(source,target):
    target.mkdir()
    for p in source.iterdir():
        if p.is_file(): (target/p.name).symlink_to(p.resolve())

def minimal_q3(path):
    for name in ['geometry.csv','definitions.json','summary.json','element_metrics.csv','feature_importances.csv']:
        p=path/name
        if p.exists():p.unlink()
    r,_=csv_read(path/'predictions.csv')
    mapping={v:f'freely_named_method_{i}' for i,v in enumerate(sorted({x['method'] for x in r}))}
    for row in r:row['method']=mapping[row['method']]
    csv_write(path/'predictions.csv',r,['name','method','split','predicted'])
    r,_=csv_read(path/'partitions.csv')
    for row in r:row['method']=mapping[row['method']]
    csv_write(path/'partitions.csv',r,['material','method','split','role'])
    r,_=csv_read(path/'sites.csv');csv_write(path/'sites.csv',r,['name','geometry'])

def minimal_q1(path):
    for name in ['ablations.npz','coverage.csv','effects.csv','definitions.json','summary.json','ranking_sensitivity.csv','symmetry_sensitivity.csv']:
        p=path/name
        if p.exists():p.unlink()
    r,_=csv_read(path/'sites.csv');r=[x for x in r if x['included']=='1']
    for row in r:row['population']=row['multiplicity']
    csv_write(path/'sites.csv',r,['name','population'])

def minimal_q2(path):
    for name in ['geometry.csv','definitions.json','summary.json','descriptors.csv','associations.csv','strata.csv']:
        p=path/name
        if p.exists():p.unlink()
    r,h=csv_read(path/'sites.csv');csv_write(path/'sites.csv',r,[k for k in h if k not in ['multiplicity','reason','included']])

def validation_leak(path):
    r,h=csv_read(path/'partitions.csv')
    # Keep a native prediction in test while changing an otherwise-unused test
    # material of the same composition to validation, if present.
    from verify_submission import load_truth,DEFAULT_INPUTS
    truth=load_truth(str(DEFAULT_INPUTS.resolve()))
    for a in r:
        if a['role']!='test':continue
        for b in r:
            if b['material']!=a['material'] and b['method']==a['method'] and b['split']==a['split'] and b['role']=='test' and truth.compositions[a['material']]==truth.compositions[b['material']]:
                b['role']='validation';csv_write(path/'partitions.csv',r,h);return
    raise RuntimeError('No same-composition test material pair')

def run(candidate):
    cases=[
      ('valid_minimal_Q1','Q1',True,minimal_q1),
      ('valid_minimal_Q2','Q2',True,minimal_q2),
      ('valid_minimal_Q3_free_method_names','Q3',True,minimal_q3),
      ('valid_partition_role_synonyms','Q3',True,lambda p:alter(p/'partitions.csv',lambda r:[x.__setitem__('role',{'train':'training','test':'holdout'}[x['role']]) for x in r])),
      ('pending_custom_material_mapping','Q3',None,lambda p:alter(p/'partitions.csv',lambda r:r[0].__setitem__('material','resolved-structure-alias'))),
      ('invalid_unknown_site','Q2',False,lambda p:alter(p/'sites.csv',lambda r:r[0].__setitem__('name','not-a-source'))),
      ('invalid_nonfinite_site','Q2',False,lambda p:alter(p/'sites.csv',lambda r:r[0].__setitem__('log_ratio','NaN'))),
      ('invalid_unknown_prediction','Q3',False,lambda p:alter(p/'predictions.csv',lambda r:r[0].__setitem__('name','not-a-source'))),
      ('invalid_nonfinite_prediction','Q3',False,lambda p:alter(p/'predictions.csv',lambda r:r[0].__setitem__('predicted','NaN'))),
      ('invalid_duplicate_prediction','Q3',False,lambda p:alter(p/'predictions.csv',lambda r:r.append(r[0].copy()))),
      ('invalid_conflicting_partition','Q3',False,lambda p:alter(p/'partitions.csv',lambda r:r.append(r[0]|{'role':'validation'}))),
      ('invalid_validation_composition_leak','Q3',False,validation_leak),
      ('invalid_nonpositive_population','Q1',False,lambda p:alter(p/'sites.csv',lambda r:next(x for x in r if x['included']=='1').__setitem__('multiplicity','0'))),
    ]
    results=[]
    with tempfile.TemporaryDirectory(prefix='chen-open-controls-') as temp:
        for name,q,expected,modify in cases:
            p=Path(temp)/name;mirror(candidate/q,p);modify(p)
            check=verify_submission(q,p)
            result={'control':name,'question':q,'expected_integrity_pass':expected,'observed_integrity_pass':check['integrity_pass'],'control_pass':check['integrity_pass']==expected,'report':check}
            results.append(result);print(name,result['control_pass'],check.get('error'),flush=True)
    report={'all_controls_pass':all(r['control_pass'] for r in results),'profile':'open-submission','positive_controls':sum(r['expected_integrity_pass'] is True for r in results),'negative_controls':sum(r['expected_integrity_pass'] is False for r in results),'pending_mapping_controls':sum(r['expected_integrity_pass'] is None for r in results),'scientific_pass':None,'scope':'Public-contract integrity only. Valid alternative scientific definitions retain explicit independent-reconstruction obligations; these controls do not validate new scientific conclusions.','checker_sha256':hashlib.sha256((BASE/'workflows/verify_submission.py').read_bytes()).hexdigest(),'controls':results}
    (BASE/'verification/open_submission_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['all_controls_pass']:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);run(p.parse_args().candidate.resolve())
