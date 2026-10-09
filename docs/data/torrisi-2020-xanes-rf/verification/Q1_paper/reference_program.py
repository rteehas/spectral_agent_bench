"""Independently fit the published pointwise coordination experiment from raw rows.

Author/evaluator only. Does not import the solver workflow or read its outputs.
The archived array audit supplies the independently recovered original row order.
"""
import argparse
import csv
import gzip
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
ELEMENTS = ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seeds', type=int, nargs='+', default=list(range(42, 52)))
    parser.add_argument('--elements', nargs='+', default=ELEMENTS, choices=ELEMENTS)
    parser.add_argument('--jobs', type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    anchors = json.loads((DATA / 'verification/source_anchor_audit.json').read_text())
    for element in args.elements:
        started = time.monotonic()
        path = DATA / 'inputs' / (element + '.jsonl.gz')
        with gzip.open(path, 'rt') as stream:
            rows = {r['source_row']: r for r in map(json.loads, stream)}
        part = anchors['elements'][element]['targets']['coord']['partitions']
        x = {}
        y = {}
        for role in ['train', 'valid', 'test']:
            ids = part[role]['source_rows']
            x[role] = np.array([rows[i]['mu'] for i in ids], dtype=float)
            y[role] = np.array([rows[i]['coordination'] for i in ids], dtype=float)
            np.testing.assert_array_equal(y[role], part[role]['y'])
        # Independent implementation of RandomOverSampler's ordered bootstrap.
        labels, counts = np.unique(y['train'], return_counts=True)
        rng = np.random.RandomState(42)
        ix = list(range(len(y['train'])))
        for label, count in zip(labels, counts):
            ix.extend(rng.choice(np.flatnonzero(y['train'] == label),
                                 int(counts.max() - count), replace=True).tolist())
        predictions = []
        metrics = []
        for seed in args.seeds:
            model = RandomForestClassifier(n_estimators=300, max_depth=35,
                                           max_features=8, min_samples_leaf=1,
                                           min_samples_split=2, criterion='gini',
                                           bootstrap=True, class_weight=None,
                                           random_state=seed, n_jobs=args.jobs)
            model.fit(x['train'][ix], y['train'][ix])
            pred = model.predict(x['test'])
            f1 = f1_score(y['test'], pred, labels=[4, 5, 6], average=None, zero_division=0)
            values = {'accuracy': float(accuracy_score(y['test'], pred)),
                      'macro_f1': float(np.mean(f1)),
                      **{f'f1_{label}': float(v) for label, v in zip([4, 5, 6], f1)}}
            metrics.append({'seed': seed, **values})
            predictions.extend({'element': element, 'seed': seed, 'source_row': i,
                                'prediction': int(p)} for i, p in zip(part['test']['source_rows'], pred))
            print(element, seed, values, flush=True)
        with (args.output / f'{element}_predictions.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(predictions[0]))
            writer.writeheader()
            writer.writerows(predictions)
        record = {'element': element, 'seeds': args.seeds,
                  'numpy': np.__version__, 'scikit_learn': sklearn.__version__,
                  'raw_input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'training_records': len(y['train']), 'oversampled_records': len(ix),
                  'test_records': len(y['test']), 'metrics': metrics,
                  'summary': {key: {'mean': float(np.mean([m[key] for m in metrics])),
                                    'std': float(np.std([m[key] for m in metrics]))}
                              for key in values},
                  'elapsed_seconds': time.monotonic() - started}
        (args.output / f'{element}.json').write_text(json.dumps(record, indent=2) + '\n')


if __name__ == '__main__':
    main()
