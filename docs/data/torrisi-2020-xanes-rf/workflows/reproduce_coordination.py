#!/usr/bin/env python3
"""Q1 worked reproduction. Reads only the label-isolated solver bundle."""
import argparse
import csv
import hashlib
import json
import shutil
import time
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(inputs, output, jobs=4):
    inputs, output = Path(inputs), Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an absent or empty output directory.')
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    protocol = json.loads((inputs / 'protocol.json').read_text())
    versions = {'numpy': np.__version__, 'scikit-learn': sklearn.__version__}
    if versions != protocol['runtime']:
        raise ValueError(f'Use the protocol runtime: {protocol["runtime"]}; found {versions}')
    manifest = {'task': protocol['task'], 'protocol_sha256': sha(inputs / 'protocol.json'),
                'input_sha256': {}, 'estimator': protocol['estimator'],
                'parameters': protocol['parameters'], 'forest_seeds': protocol['forest_seeds'],
                'runtime': versions, 'oversampled_training_records': {},
                'oversampling_seed': protocol['oversampling']['random_seed']}
    records = {'test': [], 'validation': []}
    validation_scores = []
    for element in protocol['elements']:
        path = inputs / (element + '.npz')
        manifest['input_sha256'][element] = sha(path)
        with np.load(path, allow_pickle=False) as data:
            train_x, train_y = data['train_spectra'], data['train_labels']
            classes, frequencies = np.unique(train_y, return_counts=True)
            rng = np.random.RandomState(protocol['oversampling']['random_seed'])
            indices = [np.arange(len(train_y))]
            for label, frequency in zip(classes, frequencies):
                indices.append(rng.choice(np.flatnonzero(train_y == label),
                                          size=int(frequencies.max() - frequency), replace=True))
            indices = np.concatenate(indices)
            manifest['oversampled_training_records'][element] = len(indices)
            for seed in protocol['forest_seeds']:
                model = RandomForestClassifier(**protocol['parameters'], random_state=seed, n_jobs=jobs)
                model.fit(train_x[indices], train_y[indices])
                for role in records:
                    predicted = model.predict(data[role + '_spectra'])
                    records[role].extend({'element': element, 'seed': seed, 'source_row': int(row),
                                          'prediction': int(value)}
                                         for row, value in zip(data[role + '_source_rows'], predicted))
                    if role == 'validation':
                        truth = data['validation_labels']
                        scores = f1_score(truth, predicted, labels=[4, 5, 6], average=None, zero_division=0)
                        validation_scores.append({'element': element, 'seed': seed,
                                                  'accuracy': float(accuracy_score(truth, predicted)),
                                                  **{f'f1_{k}': float(v) for k, v in zip([4, 5, 6], scores)}})
                print(f'{element} seed {seed}: fitted 300 trees and saved validation/test predictions', flush=True)
        # Checkpoint complete outputs while preserving the expected final contract.
        for role, rows in records.items():
            name = 'predictions.csv' if role == 'test' else 'validation_predictions.csv'
            with (output / name).open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['element', 'seed', 'source_row', 'prediction'])
                writer.writeheader()
                writer.writerows(rows)
    manifest['elapsed_seconds'] = time.monotonic() - started
    (output / 'run.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'validation_metrics.json').write_text(json.dumps(validation_scores, indent=2) + '\n')
    lines = ['# Pointwise coordination reproduction', '',
             'Random forests use the supplied 100-point spectra, fixed partitions, training-only random oversampling, and ten prescribed seeds. Validation rows are never added to training. No test labels are available to this program.', '',
             '| Element | Validation accuracy | Validation F1: CN4 | CN5 | CN6 |',
             '|---|---:|---:|---:|---:|']
    for element in protocol['elements']:
        selected = [r for r in validation_scores if r['element'] == element]
        means = [np.mean([r[key] for r in selected]) for key in ['accuracy', 'f1_4', 'f1_5', 'f1_6']]
        lines.append('| ' + element + ' | ' + ' | '.join(f'{v:.4f}' for v in means) + ' |')
    lines += ['', 'These are validation scores. The evaluator computes final test scores from the submitted predictions and withheld labels. The ten fits vary the forest seed, not the split; this experiment does not establish unseen-material or experimental generalization.', '',
              'Run: `python code/reproduce_coordination.py --inputs INPUT_DIRECTORY --output NEW_OUTPUT_DIRECTORY --jobs 4`.']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    (output / 'code').mkdir(exist_ok=True)
    shutil.copyfile(__file__, output / 'code/reproduce_coordination.py')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    run(args.inputs, args.output, args.jobs)
