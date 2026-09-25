#!/usr/bin/env python3
"""Method-neutral submission integrity and metric checks, NOT scientific grading.

Ground truth is decoded independently from original release filenames. No model,
transform, split fraction, fusion rule, or reference predictions are prescribed.
A separate scientific review and execution/code audit remain mandatory.
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1]
REPRESENTATIONS = {'XRD', 'PDF', 'Combined'}
PREDICTION_FIELDS = {'id', 'representation', 'predicted'}
METRIC_FIELDS = {'chemistry', 'group', 'method', 'representation', 'condition', 'fold', 'metric', 'value', 'n'}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    with Path(path).open() as stream:
        return json.load(stream)


def read_csv(path, required):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(len(reader.fieldnames or []) == len(set(reader.fieldnames or [])), f'Duplicate CSV columns: {path.name}')
        require(required <= set(reader.fieldnames or []), f'Missing CSV columns in {path.name}: {sorted(required - set(reader.fieldnames or []))}')
        rows = list(reader)
    require(rows, f'Empty CSV: {path.name}')
    require(all(all(row.get(field) is not None for field in required) for row in rows), f'Missing CSV cells: {path.name}')
    return rows


def source_truth(data=DATA):
    """Source filename identities are evaluator-only, never candidate outputs."""
    truth = {}
    for record in read_json(Path(data) / 'verification/source_labels.json'):
        path = Path(record['source_path'])
        chemistry = path.parts[1]
        kind = 'Experiments' if path.parts[0] == 'Experiments' else path.parts[2]
        row = {'id': record['id'], 'chemistry': chemistry, 'kind': kind,
               'source_path': record['source_path'], 'sha256': record['sha256']}
        if kind == 'Experiments':
            match = re.fullmatch(r'(\d+)-(.+)_(\d+)-(.+)_\d+-\d+_10-min\.xy', path.name)
            require(match is not None, f'Unrecognized experimental filename {path}')
            require(int(match[1]) + int(match[3]) == 100, f'Invalid fractions {path}')
            row.update(phases=[match[2], match[4]], major=match[2], minor=match[4],
                       minor_weight_percent=int(match[3]))
        elif kind == '1-Phase':
            phase, replicate = path.name.rsplit('_', 1)
            row.update(phases=[phase], replicate=int(replicate))
        else:
            row['phases'] = path.name.split('+')
            require(len(row['phases']) == int(kind[0]), f'Wrong source phase count {path}')
        require(row['id'] not in truth, 'Duplicate source ID')
        truth[row['id']] = row
    return truth


def default_identifier(row, field, default):
    """Only absent columns get defaults; mixed blank identifiers are ambiguous."""
    if field not in row:
        row[field] = default
    require(isinstance(row[field], str) and row[field].strip(), f'Blank or missing supplied {field} identifier')


def load_predictions(path, question=None):
    predictions = {}
    required = PREDICTION_FIELDS | ({'condition'} if question == 'Q3' else set())
    for row in read_csv(Path(path), required):
        default_identifier(row, 'method', 'default')
        default_identifier(row, 'fold', 'default')
        default_identifier(row, 'condition', 'baseline')
        key = tuple(row[field] for field in ('id', 'method', 'representation', 'condition', 'fold'))
        require(key not in predictions, f'Duplicate prediction: {key}')
        require(all(str(item).strip() for item in key), f'Empty prediction identifier: {key}')
        row['predicted'] = json.loads(row['predicted'])
        labels = row['predicted']
        require(isinstance(labels, list) and all(isinstance(label, str) for label in labels), f'Predicted labels must be a JSON string list: {key}')
        require(len(labels) == len(set(labels)), f'Duplicate predicted phase: {key}')
        require(row['representation'] in REPRESENTATIONS, f'Unknown representation: {key}')
        predictions[key] = row
    return predictions


def check_partitions(path, question, truth):
    splits = defaultdict(lambda: defaultdict(set))
    seen = set()
    allowed_kinds = {'1-Phase'} if question in ('Q1', 'Q3') else {'1-Phase', '2-Phase', '3-Phase'} if question == 'Q2' else {'1-Phase', 'Experiments'}
    for row in read_csv(Path(path), {'id', 'role'}):
        default_identifier(row, 'fold', 'default')
        sid, fold, role = row['id'], row['fold'], row['role']
        require(sid in truth, f'Unknown split source ID: {sid}')
        require(fold.strip() and role in {'train', 'validation', 'test'}, f'Invalid split role/fold: {row}')
        require((sid, fold) not in seen, f'Duplicate or overlapping split ID: {sid}/{fold}')
        seen.add((sid, fold))
        require(truth[sid]['kind'] in allowed_kinds, f'Ineligible source for {question}: {sid}')
        if question == 'Q3':
            require(truth[sid]['chemistry'] == 'Li-Ti-P-O', f'Source chemistry is outside Q3 inputs: {sid}')
        if role in {'train', 'validation'}:
            require(truth[sid]['kind'] == '1-Phase', f'Target source included in fitting/tuning: {sid}')
        elif question in ('Q2', 'Q4'):
            require(truth[sid]['kind'] != '1-Phase', f'Unexpected single-phase test target for {question}: {sid}')
        splits[fold][role].add(sid)
    for fold, roles in splits.items():
        require(roles['train'] and roles['test'], f'Fold needs train and test sources: {fold}')
        require(not roles['train'] & roles['test'] and not roles['validation'] & roles['test'] and not roles['train'] & roles['validation'], f'Overlapping split: {fold}')
        if question in ('Q2', 'Q4'):
            kinds = {'2-Phase', '3-Phase'} if question == 'Q2' else {'Experiments'}
            expected = {sid for sid, row in truth.items() if row['kind'] in kinds}
            require(roles['test'] == expected, f'Fold omits or adds evaluation-only targets: {fold}')
        # Every evaluated chemistry needs training sources. Class coverage and
        # broader sampling representativeness are assessed in scientific review.
        for chemistry in {truth[sid]['chemistry'] for sid in roles['test']}:
            require(any(truth[sid]['chemistry'] == chemistry for sid in roles['train']), f'No training sources for {chemistry}/{fold}')
    required_chemistries = {'Li-Ti-P-O'} if question == 'Q3' else {'Li-La-Zr-O', 'Li-Ti-P-O'}
    require({truth[sid]['chemistry'] for roles in splits.values() for sid in roles['test']} == required_chemistries, 'Missing evaluated chemistry from the question')
    return splits


def group_name(question, row):
    return str(len(row['phases'])) if question == 'Q2' else str(row['minor_weight_percent']) if question == 'Q4' else 'all'


def independent_metrics(question, predictions, truth):
    grouped = defaultdict(list)
    for row in predictions.values():
        source = truth[row['id']]
        key = (source['chemistry'], group_name(question, source), row['method'], row['representation'], row['condition'], row['fold'])
        grouped[key].append(row)
    results = []
    for key, rows in sorted(grouped.items()):
        tp = fp = fn = exact = count_correct = minor = 0
        for row in rows:
            source = truth[row['id']]
            expected, observed = set(source['phases']), set(row['predicted'])
            tp += len(expected & observed)
            fp += len(observed - expected)
            fn += len(expected - observed)
            exact += expected == observed
            count_correct += len(expected) == len(observed)
            if question == 'Q4':
                minor += source['minor'] in observed
        metrics = {'exact_match': exact / len(rows), 'micro_f1': 2 * tp / (2 * tp + fp + fn)}
        if question == 'Q2':
            metrics['phase_count_accuracy'] = count_correct / len(rows)
        if question == 'Q4':
            metrics['minor_recall'] = minor / len(rows)
        identity = dict(zip(('chemistry', 'group', 'method', 'representation', 'condition', 'fold'), key))
        results.extend({**identity, 'metric': metric, 'value': value, 'n': len(rows)} for metric, value in metrics.items())
    return results


def complementarity(predictions, truth):
    groups = defaultdict(dict)
    for row in predictions.values():
        key = (row['method'], row['condition'], row['fold'], truth[row['id']]['chemistry'])
        groups[key][row['id'], row['representation']] = set(row['predicted']) == set(truth[row['id']]['phases'])
    result = []
    for key, rows in sorted(groups.items()):
        ids = sorted({sid for sid, representation in rows if representation == 'XRD'} & {sid for sid, representation in rows if representation == 'PDF'})
        if not ids:
            continue
        counts = dict(both_correct=0, xrd_only_correct=0, pdf_only_correct=0, neither_correct=0)
        for sid in ids:
            left, right = rows[sid, 'XRD'], rows[sid, 'PDF']
            name = 'both_correct' if left and right else 'xrd_only_correct' if left else 'pdf_only_correct' if right else 'neither_correct'
            counts[name] += 1
        result.append(dict(zip(('method', 'condition', 'fold', 'chemistry'), key)) | {'n': len(ids), **counts})
    return result


def check_prediction_coverage(question, predictions, splits, truth, conditions):
    grouped = defaultdict(set)
    classes = defaultdict(set)
    for source in truth.values():
        if source['kind'] == '1-Phase':
            classes[source['chemistry']].add(source['phases'][0])
    for row in predictions.values():
        sid, fold = row['id'], row['fold']
        require(sid in truth and fold in splits, f'Unknown prediction source or fold: {sid}/{fold}')
        require(sid in splits[fold]['test'], f'Prediction is not held out: {sid}/{fold}')
        require(row['condition'] in conditions, f'Undeclared condition: {row["condition"]}')
        source = truth[sid]
        labels = classes[source['chemistry']]
        if question == 'Q4':
            labels = {label.rsplit('_', 1)[0] for label in labels}
        require(set(row['predicted']) <= labels, f'Unknown predicted phase for chemistry: {sid}')
        if question in ('Q1', 'Q3'):
            require(len(row['predicted']) == 1, f'Single-phase prediction must have one phase: {sid}')
        key = (row['method'], row['representation'], row['condition'], fold)
        grouped[key].add(sid)
    require({key[3] for key in grouped} == set(splits), 'A declared fold has no predictions')
    for key, ids in grouped.items():
        require(ids == splits[key[3]]['test'], f'Missing or extra evaluation targets: {key}')
    if question != 'Q3':
        comparisons = {(method, fold, condition) for method, _, condition, fold in grouped}
        for method, fold, condition in comparisons:
            required = {'XRD', 'PDF'} if question == 'Q2' else REPRESENTATIONS
            require(required <= {representation for m, representation, c, f in grouped if (m, f, c) == (method, fold, condition)}, f'Missing representation comparison: {method}/{fold}/{condition}')
    else:
        require({'XRD', 'PDF'} <= {key[1] for key in grouped}, 'Q3 needs XRD and PDF classification comparisons')
        for method, representation, _, fold in grouped:
            present = {condition for m, r, condition, f in grouped if (m, r, f) == (method, representation, fold)}
            require(present == set(conditions), f'Missing baseline/perturbed comparison: {method}/{representation}/{fold}')
    return len(grouped)


def check_metrics(path, expected, optional_metrics=()):
    identity_fields = ('chemistry', 'group', 'method', 'representation', 'condition', 'fold', 'metric')
    actual = {}
    for row in read_csv(Path(path), METRIC_FIELDS):
        key = tuple(row[field] for field in identity_fields)
        require(key not in actual, f'Duplicate metric row: {key}')
        value, n = float(row['value']), float(row['n'])
        require(np.isfinite(value) and np.isfinite(n) and n > 0 and n.is_integer(), f'Invalid metric numeric values: {key}')
        actual[key] = value, int(n)
    for row in expected:
        key = tuple(row[field] for field in identity_fields)
        if key not in actual and row['metric'] in optional_metrics:
            continue
        require(key in actual, f'Missing reported core metric: {key}')
        value, n = actual.pop(key)
        require(n == row['n'] and abs(value - row['value']) <= 1e-8, f'Reported metric disagrees with source-derived truth: {key}')
    return [{'identity': list(key), 'value': value[0], 'n': value[1]} for key, value in sorted(actual.items())]


def check_artifacts(output, question):
    require((output / 'report.md').is_file() and len((output / 'report.md').read_text().strip()) >= 80, 'Missing substantive report.md')
    files = [path for path in output.rglob('*') if path.is_file()]
    require(any(path.suffix.lower() in {'.png', '.svg', '.pdf'} and path.stat().st_size > 100 for path in files), 'Missing nonempty figure artifact')
    require(any(path.suffix.lower() in {'.py', '.ipynb'} and path.stat().st_size > 80 for path in files), 'Missing runnable analysis code artifact')
    if question != 'Q3':
        return {'numeric_evidence_check': 'Not applicable'}
    archives = [output / 'evidence.npz']
    require(archives[0].is_file(), 'Q3 needs evidence.npz with saved numeric perturbation and representation evidence')
    numeric_arrays = numeric_values = 0
    for path in archives:
        with np.load(path, allow_pickle=False) as arrays:
            for key in arrays.files:
                array = arrays[key]
                require(array.size > 0, f'Empty evidence array: {path.name}/{key}')
                if np.issubdtype(array.dtype, np.number):
                    require(np.isfinite(array).all(), f'Non-finite numeric evidence: {path.name}/{key}')
                    numeric_arrays += 1
                    numeric_values += array.size
    require(numeric_arrays > 0, 'Saved evidence.npz contains no numeric arrays')
    return {'numeric_evidence_check': 'Presence and finite numeric arrays only; source provenance, axes, transforms, and perturbation construction require execution/code review.', 'numeric_arrays': numeric_arrays, 'numeric_values': numeric_values}


def verify(question, output, reference=None, data=DATA):
    """reference is accepted for old callers but intentionally NEVER consumed."""
    require(question in {'Q1', 'Q2', 'Q3', 'Q4'}, f'Unknown question: {question}')
    output, data = Path(output), Path(data)
    evidence = check_artifacts(output, question)
    truth = source_truth(data)
    splits = check_partitions(output / 'splits.csv', question, truth)
    conditions = {'baseline': {'artifact': 'clean'}}
    if question == 'Q3':
        conditions = {}
        for row in read_csv(output / 'conditions.csv', {'condition', 'artifact', 'description'}):
            require(row['condition'].strip() and row['condition'] not in conditions, 'Duplicate/empty condition')
            require(row['artifact'] in {'clean', 'noise', 'background'} and row['description'].strip(), 'Unknown or undescribed perturbation condition')
            conditions[row['condition']] = row
        require({row['artifact'] for row in conditions.values()} == {'clean', 'noise', 'background'}, 'Q3 requires clean, noise, and background conditions')
    predictions = load_predictions(output / 'predictions.csv', question)
    if question != 'Q3':
        conditions = {row['condition']: {'artifact': 'clean'} for row in predictions.values()}
    comparisons = check_prediction_coverage(question, predictions, splits, truth, conditions)
    metrics = independent_metrics(question, predictions, truth)
    optional_metrics = {'micro_f1'} if question in {'Q1', 'Q3'} else set()
    metric_path = output / 'metrics.csv'
    metric_table_status = 'absent_recomputed_only'
    metric_columns, unchecked_metrics = [], []
    if metric_path.exists():
        with metric_path.open(newline='') as stream:
            metric_columns = next(csv.reader(stream), [])
        if METRIC_FIELDS <= set(metric_columns):
            unchecked_metrics = check_metrics(metric_path, metrics, optional_metrics)
            metric_table_status = 'legacy_table_checked'
        else:
            metric_table_status = 'supplemental_table_requires_review'
    return {'question': question, 'integrity_passed': True,
            'scientific_correctness': 'NOT DETERMINED: mandatory execution/code audit and scored scientific review remain.',
            'reference_predictions_compared': False, 'source_filename_truth': True,
            'prediction_rows': len(predictions), 'comparison_cells': comparisons,
            'core_metric_rows_independently_recomputed': len(metrics), 'metrics': metrics,
            'optional_metric_table_checked': metric_table_status == 'legacy_table_checked',
            'optional_metric_table_status': metric_table_status,
            'supplemental_metric_columns': metric_columns if metric_table_status == 'supplemental_table_requires_review' else [],
            'report_claims_checked': False,
            'complementarity': complementarity(predictions, truth),
            'unchecked_extra_metrics': unchecked_metrics, **evidence,
            'limitations': ['Quantitative claims in report.md require scientific review against the evaluator-recomputed metrics; a submitted metrics.csv is optional.',
                           'Output declarations cannot prove that test labels were not used in fitting, tuning, phase-count selection, or interpretation.',
                           'Disjoint sample IDs do not establish independence of augmented or related source structures.',
                           'Plots, code presence, and finite evidence arrays do not establish physical or scientific validity.',
                           'No minimum accuracy or preferred representation is imposed; meaningful negative findings can earn full scientific credit.'],
            'review_rubric': 'verification/scientific_review_rubric.md'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--question', choices=['Q1', 'Q2', 'Q3', 'Q4'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--reference', type=Path, help='Deprecated compatibility argument; ignored. No candidate output is a correctness target.')
    args = parser.parse_args()
    print(json.dumps(verify(args.question, args.output, data=args.data), indent=2))


if __name__ == '__main__':
    main()
