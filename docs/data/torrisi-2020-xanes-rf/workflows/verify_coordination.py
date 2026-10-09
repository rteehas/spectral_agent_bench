#!/usr/bin/env python3
"""Fixed Q1 reproduction grader: raw labels -> scores -> published rounding bins.

The harness must execute submitted source with only the solver bundle. This
checker never executes submission code or accepts prose in place of predictions.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score_file(path, role, protocol, truth):
    groups = {}
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames is not None and len(reader.fieldnames) == 4 and
                set(reader.fieldnames) == {'element', 'seed', 'source_row', 'prediction'},
                f'{path.name}: expected element,seed,source_row,prediction')
        for row in reader:
            require(None not in row, f'{path.name}: malformed row')
            element = row['element']
            seed, source_row, prediction = (int(row[k]) for k in ['seed', 'source_row', 'prediction'])
            require(element in protocol['elements'] and seed in protocol['forest_seeds'], 'Unknown element or seed')
            require(prediction in protocol['classes'], 'Prediction must be coordination 4, 5, or 6')
            group = groups.setdefault((element, seed), {})
            require(source_row not in group, f'{path.name}: duplicate prediction')
            group[source_row] = prediction
    expected = {(e, s) for e in protocol['elements'] for s in protocol['forest_seeds']}
    require(set(groups) == expected, f'{path.name}: missing element/seed coverage')
    scores = []
    support = {}
    for element, seed in sorted(expected):
        reference = truth[element][role]
        ids = reference['source_rows']
        pred = groups[(element, seed)]
        require(set(pred) == set(ids), f'{path.name}: incorrect {element}/{seed} {role} membership')
        y = np.asarray(reference['labels'], dtype=int)
        p = np.asarray([pred[i] for i in ids], dtype=int)
        confusion = np.bincount((y - 4) * 3 + p - 4, minlength=9).reshape(3, 3)
        denominator = confusion.sum(axis=0) + confusion.sum(axis=1)
        f1 = np.divide(2 * np.diag(confusion), denominator,
                       out=np.zeros(3, dtype=float), where=denominator > 0)
        scores.append({'element': element, 'seed': seed, 'accuracy': float(np.trace(confusion) / len(y)),
                       'macro_f1': float(f1.mean()), **{f'f1_{k}': float(v) for k, v in zip([4, 5, 6], f1)}})
        support[element] = {str(k): int((y == k).sum()) for k in [4, 5, 6]}
    return scores, support


def verify(output, inputs=DATA / 'inputs/Q1_paper', reference=DATA / 'verification/Q1_paper'):
    output, inputs, reference = Path(output), Path(inputs), Path(reference)
    protocol = json.loads((inputs / 'protocol.json').read_text())
    policy = json.loads((reference / 'comparison_policy.json').read_text())
    truth = json.loads((reference / 'truth.json').read_text())
    published = json.loads((reference / 'published_targets.json').read_text())
    preparation = json.loads((reference / 'preparation_audit.json').read_text())
    manifest = json.loads((output / 'run.json').read_text())
    require(digest(inputs / 'protocol.json') == policy['protocol_sha256'], 'Wrong input protocol')
    require(digest(reference / 'published_targets.json') == policy['published_targets_sha256'], 'Changed published targets')
    require(digest(reference / 'truth.json') == policy['truth_sha256'], 'Changed evaluator labels')
    for field in ['estimator', 'parameters', 'forest_seeds', 'runtime']:
        require(manifest.get(field) == protocol[field], 'Incorrect declared ' + field)
    if 'task' in manifest:
        require(manifest['task'] == protocol['task'], 'Incorrect declared task')
    require(manifest.get('protocol_sha256') == policy['protocol_sha256'], 'Run used a different protocol')
    hashes = {e: digest(inputs / (e + '.npz')) for e in protocol['elements']}
    require(hashes == {e: preparation['elements'][e]['bundle_sha256'] for e in protocol['elements']}, 'Changed input arrays')
    require(manifest.get('input_sha256') == hashes, 'Run input hashes differ from the bundle')
    if 'oversampling_seed' in manifest:
        require(manifest['oversampling_seed'] == protocol['oversampling']['random_seed'], 'Incorrect oversampling seed')
    require(manifest.get('oversampled_training_records') ==
            {e: preparation['elements'][e]['oversampled_training_records'] for e in protocol['elements']},
            'Incorrect training oversampling counts')
    require((output / 'report.md').is_file() and (output / 'report.md').read_text().strip(), 'Missing report.md')
    require(any(p.stat().st_size for p in (output / 'code').rglob('*.py')), 'Missing runnable Python source under code/')
    test, support = score_file(output / 'predictions.csv', 'test', protocol, truth)
    validation, _ = score_file(output / 'validation_predictions.csv', 'validation', protocol, truth)
    comparisons = []
    for element in protocol['elements']:
        selected = [row for row in test if row['element'] == element]
        for metric in ['accuracy', 'f1_4', 'f1_5', 'f1_6']:
            values = np.asarray([row[metric] for row in selected])
            for statistic, actual in [('mean', values.mean()), ('std', values.std(ddof=0))]:
                expected = published['elements'][element][metric][statistic]
                difference = abs(float(actual) - expected)
                bound = policy['absolute_tolerance'] + policy['floating_point_epsilon']
                require(difference <= bound,
                        f'Published result mismatch: {element} {metric} {statistic} '
                        f'={actual:.10f}; expected {expected:.5f} within {bound:.10f}')
                comparisons.append({'element': element, 'metric': metric, 'statistic': statistic,
                                    'actual': float(actual), 'published': expected, 'absolute_difference': difference})
    return {'question': 'TORRISI20-Q1', 'status': 'pass', 'numerical_integrity_pass': True,
            'publication_reproduction_pass': True, 'test_prediction_count': sum(sum(v.values()) for v in support.values()) * len(protocol['forest_seeds']),
            'fits': len(test), 'published_comparisons': comparisons, 'test_class_support': support,
            'test_scores': test, 'validation_scores': validation,
            'scope': 'Fixed-protocol numerical reproduction of the published pointwise coordination results. A prose claim cannot override a failed numerical check. Source execution and solver isolation are responsibilities of the evaluation harness.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, default=DATA / 'inputs/Q1_paper')
    parser.add_argument('--reference', type=Path, default=DATA / 'verification/Q1_paper')
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.output, args.inputs, args.reference), indent=2))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({'question': 'TORRISI20-Q1', 'status': 'fail', 'reason': str(exc)}))
        raise SystemExit(1)
