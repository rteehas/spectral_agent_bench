#!/usr/bin/env python3
"""Independent Q5 integrity controls and explicit scientific-review fixtures.

Synthetic fixtures are not scientific solutions. One genuine direct-profile
classifier is executed to show that the numerical checker has no preferred
representation or method-name requirement. No discovery candidate is imported.
"""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/szymanski-2024-xrd-pdf'
spec = importlib.util.spec_from_file_location('discovery_verifier', DATA / 'workflows/verify_discovery.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csvread(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def csvwrite(path, fields, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mutate_csv(path, mutation):
    fields, rows = csvread(path)
    mutation(rows)
    csvwrite(path, fields, rows)


def omit_columns(path, omitted):
    fields, rows = csvread(path)
    fields = [field for field in fields if field not in omitted]
    csvwrite(path, fields, [{field: row[field] for field in fields} for row in rows])


def source_audit(release):
    truth = v.source_truth(DATA)
    found = set()
    for chemistry in sorted(v.CHEMISTRIES):
        metadata = json.loads((DATA / 'inputs' / f'{chemistry}_1-Phase.json').read_text())
        with np.load(DATA / 'inputs' / f'{chemistry}_1-Phase.npz', allow_pickle=False) as arrays:
            for row in metadata:
                source = truth[row['id']]
                v.require(row['phases'] == [source['phase']], 'Metadata differs from original filename identity')
                original = release / source['source_path']
                v.require(sha(original) == source['sha256'], 'Original raw file hash differs')
                np.testing.assert_array_equal(np.column_stack((arrays['theta'], arrays[row['id']])), np.loadtxt(original))
                found.add(row['id'])
    v.require(found == set(truth) and len(found) == 1090, 'Q5 raw source inventory incomplete')
    return {'passed': True, 'single_phase_spectra_compared_exactly': len(found), 'labels_independently_decoded_from_original_source_filenames': True}


ALTERNATIVE_CODE = r'''#!/usr/bin/env python3
"""Physical baseline: match complete Bragg intensity profiles to phase averages.
No coordinate transform is used. Strong/weak peak weighting is left unchanged;
this baseline tests fingerprint similarity and makes no broad robustness claim.
"""
import argparse,csv,json,shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
predictions=[];splits=[];scores=[]
for chemistry in ['Li-La-Zr-O','Li-Ti-P-O']:
    rows=json.loads((a.inputs/f'{chemistry}_1-Phase.json').read_text())
    labels=np.array([row['phases'][0] for row in rows]);classes=sorted(set(labels));roles=np.full(len(rows),'test',dtype='U5')
    rng=np.random.default_rng(9351)
    for phase in classes:
        indices=np.flatnonzero(labels==phase);rng.shuffle(indices)
        roles[indices[:max(1,int(.7*len(indices)))]]='train'
    with np.load(a.inputs/f'{chemistry}_1-Phase.npz',allow_pickle=False) as source:
        intensity=np.stack([source[row['id']] for row in rows])
    intensity=np.maximum(intensity-np.quantile(intensity,.1,axis=1)[:,None],0)
    intensity/=np.maximum(np.linalg.norm(intensity,axis=1)[:,None],1e-30)
    templates=np.stack([intensity[(roles=='train')&(labels==phase)].mean(axis=0) for phase in classes])
    templates/=np.maximum(np.linalg.norm(templates,axis=1)[:,None],1e-30)
    chosen=np.array(classes)[(intensity[roles=='test']@templates.T).argmax(axis=1)]
    tests=[row for row,role in zip(rows,roles) if role=='test']
    predictions.extend(dict(id=row['id'],method='bragg_profile_similarity',predicted=json.dumps([str(phase)])) for row,phase in zip(tests,chosen))
    splits.extend(dict(id=row['id'],role=str(role)) for row,role in zip(rows,roles))
    # Evaluation labels are consulted after prediction; none fit a test model.
    scores.append(float(np.mean(chosen==labels[roles=='test'])))
for name,rows in [('predictions',predictions),('splits',splits)]:
    with (a.output/f'{name}.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
fig,axis=plt.subplots(figsize=(6,3));axis.bar(['Li-La-Zr-O','Li-Ti-P-O'],scores);axis.set(ylabel='Held-out accuracy',ylim=(0,1));fig.tight_layout();fig.savefig(a.output/'diagnostics.png');plt.close(fig)
(a.output/'report.md').write_text('Direct Bragg-profile similarity hypothesis: phase-specific peak positions and relative intensities distinguish the supplied structures. Phase-average training templates are compared with held-out native profiles using cosine similarity. This is a limited executed non-target baseline, not a complete robustness investigation or claimed discovery. It does not test artificial artifacts or infer new real-space structure. No derived coordinate is constructed.\n')
if Path(__file__).resolve()!=(a.output/'run.py').resolve():shutil.copyfile(__file__,a.output/'run.py')
'''


LEAKAGE_CODE = r'''#!/usr/bin/env python3
# Deliberately invalid test fixture: target-label copying, not scientific inference.
import argparse,csv,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
lookup={}
for file in a.inputs.glob('*_1-Phase.json'):
    lookup.update({row['id']:row['phases'] for row in json.loads(file.read_text())})
with (a.output/'predictions.csv').open(newline='') as stream:
    reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
for row in rows:
    row['predicted']=json.dumps(lookup[row['id']]);row['method']='target_label_copy'
with (a.output/'predictions.csv').open('w',newline='') as stream:
    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
'''


def compact(result):
    return {key: result[key] for key in ('integrity_passed', 'scientific_quality', 'discovery_target', 'preferred_method_names_checked', 'performance_threshold_applied', 'prediction_rows', 'numerical_evidence_present')}


def corrupt_evidence(folder):
    path = folder / 'evidence.npz'
    with np.load(path, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    key = next(key for key, array in arrays.items() if np.issubdtype(array.dtype, np.floating))
    arrays[key].flat[0] = np.nan
    np.savez_compressed(path, **arrays)


def remove_artifacts(folder, suffixes):
    for path in folder.rglob('*'):
        if path.is_file() and path.suffix.lower() in suffixes:
            path.unlink()


def audit_controls(candidate):
    truth = v.source_truth(DATA)
    report = {'worked_candidate_integrity': compact(v.verify(candidate))}
    with tempfile.TemporaryDirectory(prefix='discovery-audit-') as temporary:
        base = Path(temporary)
        controls = {
            'missing_prediction': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows.pop()),
            'duplicate_prediction': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows.append(copy.deepcopy(rows[0]))),
            'unknown_phase': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('predicted','["Invented_1"]')),
            'not_single_phase': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('predicted','[]')),
            'unknown_id': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('id','unknown-source')),
            'blank_method': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('method','')),
            'missing_method': lambda folder: omit_columns(folder/'predictions.csv', {'method'}),
            'blank_fold': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('fold','')),
            'unmatched_fold_omission': lambda folder: omit_columns(folder/'predictions.csv', {'fold'}),
            'overlapping_partition': lambda folder: mutate_csv(folder/'splits.csv', lambda rows: rows.append({**next(row for row in rows if row['role']=='test'),'role':'train'})),
            'test_moved_to_training': lambda folder: mutate_csv(folder/'splits.csv', lambda rows: next(row for row in rows if row['role']=='test').__setitem__('role','train')),
            'unknown_split_id': lambda folder: mutate_csv(folder/'splits.csv', lambda rows: rows[0].__setitem__('id','invented-source')),
            'incomplete_method_cell': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('method','a_new_method_with_one_sample')),
            'unknown_condition': lambda folder: mutate_csv(folder/'predictions.csv', lambda rows: rows[0].__setitem__('condition','undeclared-condition')),
            'missing_condition_descriptions': lambda folder: (folder/'conditions.csv').unlink(),
            'duplicate_condition_description': lambda folder: mutate_csv(folder/'conditions.csv', lambda rows: rows.append(copy.deepcopy(rows[0]))),
            'blank_condition_description': lambda folder: mutate_csv(folder/'conditions.csv', lambda rows: rows[0].__setitem__('description','')),
            'missing_report': lambda folder: (folder/'report.md').unlink(),
            'missing_code': lambda folder: remove_artifacts(folder,{'.py','.ipynb'}),
            'missing_figure': lambda folder: remove_artifacts(folder,{'.png','.svg','.pdf'}),
            'nonfinite_evidence': corrupt_evidence,
        }
        rejected = []
        for name, mutate in controls.items():
            folder = base/name;shutil.copytree(candidate,folder);mutate(folder)
            try:
                v.verify(folder)
            except (AssertionError,ValueError,FileNotFoundError,KeyError) as error:
                rejected.append({'control':name,'rejected':True,'reason':str(error).splitlines()[0][:240]})
            else:
                raise AssertionError(f'Invalid integrity fixture accepted: {name}')
        report['invalid_integrity_controls'] = rejected
        accepted = []
        renamed=base/'free_method_names';shutil.copytree(candidate,renamed)
        fields, rows=csvread(renamed/'predictions.csv');mapping={name:f'analysis_{i}' for i,name in enumerate(sorted({row['method'] for row in rows}))}
        for row in rows:row['method']=mapping[row['method']]
        csvwrite(renamed/'predictions.csv',fields,rows)
        accepted.append({'control':'no_preferred_method_keyword',**compact(v.verify(renamed))})
        changed=base/'low_accuracy';shutil.copytree(candidate,changed)
        def wrong_labels(rows):
            for row in rows:
                actual=truth[row['id']]
                vocabulary=sorted({source['phase'] for source in truth.values() if source['chemistry']==actual['chemistry']})
                row['predicted']=json.dumps([next(label for label in vocabulary if label!=actual['phase'])])
        mutate_csv(changed/'predictions.csv',wrong_labels)
        checked=v.verify(changed);v.require(all(row['accuracy']==0 for row in checked['summaries']),'Low accuracy fixture is not zero')
        accepted.append({'control':'zero_accuracy_consistent_fixture_is_not_automatic_failure','synthetic_fixture_not_scientific_solution':True,**compact(checked)})
        minimal=base/'native_minimal';shutil.copytree(candidate,minimal)
        fields,rows=csvread(minimal/'predictions.csv');condition=next(row['condition'] for row in rows if row['condition']=='baseline')
        rows=[row for row in rows if row['condition']==condition];csvwrite(minimal/'predictions.csv',fields,rows)
        omit_columns(minimal/'predictions.csv',{'fold','condition'});omit_columns(minimal/'splits.csv',{'fold'})
        (minimal/'conditions.csv').unlink();(minimal/'evidence.npz').unlink()
        accepted.append({'control':'native_single_condition_needs_no_magic_condition_name_or_evidence','synthetic_schema_fixture':True,**compact(v.verify(minimal))})
        # Execute a genuine non-target classifier using only the raw projections.
        alternative=base/'executed_physical_alternative';alternative.mkdir();(alternative/'run.py').write_text(ALTERNATIVE_CODE)
        subprocess.run([sys.executable,str(alternative/'run.py'),'--inputs',str(DATA/'inputs'),'--output',str(alternative)],check=True,capture_output=True,text=True)
        checked=v.verify(alternative)
        accepted.append({'control':'executed_direct_bragg_profile_classifier','source_inputs_only':True,'actual_method_implemented':'Normalized direct intensity profiles, phase-average training templates, cosine similarity; no change to a real-space coordinate.',
                         'scientific_scope':'A physically interpretable baseline demonstrating numerical admissibility; not a complete robustness answer and not discovery-target attainment.',
                         'accuracy_by_chemistry':{row['chemistry']:row['accuracy'] for row in checked['summaries']},**compact(checked)})
        boundary=[]
        falseclaim=base/'false_physical_claim';shutil.copytree(alternative,falseclaim)
        (falseclaim/'report.md').write_text('Claim under audit: this executable constructs Q-weighted sine-transformed diffraction intensity in real space and proves a physical discovery. This claim is deliberately false: the saved executable only computes direct angular-profile cosine similarity.\n')
        boundary.append({'fixture':'false_target_claim_with_unchanged_direct_profile_code','numerical_result':compact(v.verify(falseclaim)),
                         'reviewed_code_evidence':'Executable ALTERNATIVE_CODE contains direct normalized intensity templates and cosine similarity; it never constructs Q, a distance axis, or a sine integral.',
                         'manual_review_verdict':'Claim rejected; target stage 0. Numerical integrity cannot establish a physical operation.'})
        leaked=base/'target_label_copy';shutil.copytree(alternative,leaked);(leaked/'run.py').write_text(LEAKAGE_CODE)
        subprocess.run([sys.executable,str(leaked/'run.py'),'--inputs',str(DATA/'inputs'),'--output',str(leaked)],check=True,capture_output=True,text=True)
        checked=v.verify(leaked);v.require(all(row['accuracy']==1 for row in checked['summaries']),'Label-copy fixture not perfect')
        boundary.append({'fixture':'executed_target_label_copy_with_disjoint_declared_splits','numerical_result':compact(checked),
                         'reviewed_code_evidence':'LEAKAGE_CODE reads input phase-label JSON and directly copies lookup[id] into every prediction; no spectrum is used.',
                         'manual_review_verdict':'Scientific validity gate fails for target-label leakage despite perfect accuracy; no validated discovery claim.'})
        absent=base/'missing_known_generated_evidence';shutil.copytree(candidate,absent);(absent/'evidence.npz').unlink()
        boundary.append({'fixture':'missing_evidence_for_the_known_generated_noise_background_worked_experiment','numerical_result':compact(v.verify(absent)),
                         'reviewed_code_evidence':'This fixture retains the worked code/report with explicit generated-noise/background claims while its required numerical evidence archive has been removed.',
                         'manual_review_verdict':'Generated-signal provenance requirement not met; mechanistic claim unverified. Condition names alone were not used to infer generation.'})
        report['accepted_neutrality_controls']=accepted
        report['scientific_review_boundary_fixtures']=boundary
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release',type=Path,required=True);parser.add_argument('--candidate-output',type=Path,required=True)
    args=parser.parse_args()
    report={'source_audit':source_audit(args.release),'verifier_sha256':sha(DATA/'workflows/verify_discovery.py'),'worked_candidate_code_sha256':sha(args.candidate_output/'run.py'),**audit_controls(args.candidate_output)}
    report['invalid_integrity_controls_rejected']=len(report['invalid_integrity_controls'])
    report['neutrality_controls_accepted']=len(report['accepted_neutrality_controls'])
    report['scientific_boundary_fixtures_reviewed']=len(report['scientific_review_boundary_fixtures'])
    report['scope']='Numerical integrity tests plus explicitly inspected synthetic scientific-boundary fixtures; not an automated discovery or scientific-quality grader.'
    (DATA/'verification/discovery_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
