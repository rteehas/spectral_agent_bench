"""Check the Q1 solver boundary and fixed grader's rejection of wrong results."""
import csv
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
REFERENCE = DATA / 'verification/Q1_paper'


def main():
    spec = importlib.util.spec_from_file_location('fixed_q1', DATA / 'workflows/verify_coordination.py')
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    good = REFERENCE / 'worked'
    assert grader.verify(good)['publication_reproduction_pass']
    truth = json.loads((REFERENCE / 'truth.json').read_text())
    labels = {(e, int(i)): int(v) for e, d in truth.items() for i, v in zip(d['test']['source_rows'], d['test']['labels'])}
    for path in (DATA / 'inputs/Q1_paper').glob('*.npz'):
        with np.load(path, allow_pickle=False) as arrays:
            assert set(arrays.files) == {'energy_eV', 'train_spectra', 'train_labels', 'train_source_rows',
                                          'validation_spectra', 'validation_labels', 'validation_source_rows',
                                          'test_spectra', 'test_source_rows'}
            for role in ['train', 'validation', 'test']:
                assert arrays[role + '_spectra'].shape[1] == 100
    cases = ['missing_test_row', 'duplicate_test_row', 'unknown_record', 'invalid_class',
             'majority_predictions', 'copied_test_labels', 'wrong_seed', 'missing_validation',
             'wrong_forest_settings', 'wrong_oversampling_count', 'changed_input_hash']
    results = []
    with tempfile.TemporaryDirectory(prefix='torrisi-q1-rejections-') as directory:
        minimal = Path(directory) / 'documented_manifest'
        shutil.copytree(good, minimal)
        manifest_path = minimal / 'run.json'
        manifest = json.loads(manifest_path.read_text())
        for field in ['task', 'oversampling_seed', 'elapsed_seconds']:
            manifest.pop(field)
        manifest_path.write_text(json.dumps(manifest))
        assert grader.verify(minimal)['publication_reproduction_pass']
        for case in cases:
            output = Path(directory) / case
            shutil.copytree(good, output)
            path = output / 'predictions.csv'
            with path.open(newline='') as stream:
                rows = list(csv.DictReader(stream))
            if case == 'missing_test_row':
                rows.pop()
            elif case == 'duplicate_test_row':
                rows.append(rows[0].copy())
            elif case == 'unknown_record':
                rows[0]['source_row'] = '999999'
            elif case == 'invalid_class':
                rows[0]['prediction'] = '7'
            elif case == 'wrong_seed':
                rows[0]['seed'] = '999'
            elif case == 'majority_predictions':
                modes = {e: max([4, 5, 6], key=d['train']['labels'].count) for e, d in truth.items()}
                for row in rows:
                    row['prediction'] = modes[row['element']]
            elif case == 'copied_test_labels':
                for row in rows:
                    row['prediction'] = labels[row['element'], int(row['source_row'])]
            elif case == 'missing_validation':
                (output / 'validation_predictions.csv').unlink()
            else:
                manifest_path = output / 'run.json'
                manifest = json.loads(manifest_path.read_text())
                if case == 'wrong_forest_settings':
                    manifest['parameters']['class_weight'] = 'balanced'
                elif case == 'wrong_oversampling_count':
                    manifest['oversampled_training_records']['Ti'] -= 1
                else:
                    manifest['input_sha256']['Ti'] = 'not-the-input-hash'
                manifest_path.write_text(json.dumps(manifest))
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['element', 'seed', 'source_row', 'prediction'])
                writer.writeheader()
                writer.writerows(rows)
            try:
                grader.verify(output)
            except (ValueError, OSError) as exc:
                results.append({'case': case, 'rejected': True, 'reason': str(exc)})
            else:
                raise AssertionError('Incorrect result was accepted: ' + case)
    report = {'status': 'pass', 'correct_reproduction_accepted': True,
              'documented_manifest_without_optional_fields_accepted': True,
              'test_labels_and_structural_metadata_absent_from_bundle': True,
              'rejection_checks': results,
              'scope': 'Numerical integrity and fixed published-result acceptance. Copied perfect labels fail because this is a prescribed experiment reproduction. This does not replace harness-enforced source execution and access isolation.'}
    (REFERENCE / 'adversarial_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Correct reproduction passes; all', len(results), 'incorrect submissions rejected; solver boundary checked.')


if __name__ == '__main__':
    main()
