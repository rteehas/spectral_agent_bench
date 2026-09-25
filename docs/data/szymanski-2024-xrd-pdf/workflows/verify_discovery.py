#!/usr/bin/env python3
"""Q5 numerical integrity only; discovery and scientific quality require review.

Free method identifiers are deliberately not inspected for a preferred idea.
Labels come from original source filenames, never candidate/reference outputs.
"""
import argparse
import csv
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1]
CHEMISTRIES = {'Li-La-Zr-O', 'Li-Ti-P-O'}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_csv(path, required):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        require(len(fields) == len(set(fields)), f'Duplicate columns: {path.name}')
        require(required <= set(fields), f'Missing required columns: {path.name}/{sorted(required - set(fields))}')
        rows = list(reader)
    require(rows, f'Empty table: {path.name}')
    require(all(all(isinstance(row.get(field), str) and row[field].strip() for field in required) for row in rows), f'Empty required table cell: {path.name}')
    return rows, fields


def optional_identifier(row, name, default):
    if name not in row:
        row[name] = default
    require(isinstance(row[name], str) and row[name].strip(), f'Blank supplied {name}; omit the whole column when unnecessary')


def source_truth(data=DATA):
    truth = {}
    with (Path(data) / 'verification/source_labels.json').open() as stream:
        sources = json.load(stream)
    for source in sources:
        path = Path(source['source_path'])
        if path.parts[0] != 'Simulations' or path.parts[2] != '1-Phase':
            continue
        label, replicate = path.name.rsplit('_', 1)
        row = dict(id=source['id'], chemistry=path.parts[1], phase=label,
                   replicate=int(replicate), source_path=source['source_path'], sha256=source['sha256'])
        require(row['chemistry'] in CHEMISTRIES and row['id'] not in truth, 'Invalid or duplicate source identity')
        truth[row['id']] = row
    require(truth, 'No eligible source spectra')
    return truth


def load_splits(path, truth):
    rows, _ = read_csv(path, {'id', 'role'})
    folds = defaultdict(lambda: defaultdict(set))
    seen = set()
    for row in rows:
        optional_identifier(row, 'fold', 'default')
        sid, fold, role = row['id'], row['fold'], row['role']
        require(sid in truth, f'Unknown or ineligible source ID: {sid}')
        require(role in {'train', 'validation', 'test'}, f'Unknown split role: {role}')
        require((sid, fold) not in seen, f'Overlapping or duplicate source partition: {sid}/{fold}')
        seen.add((sid, fold))
        folds[fold][role].add(sid)
    for fold, roles in folds.items():
        require(roles['train'] and roles['test'], f'Missing training or held-out sources: {fold}')
        for chemistry in {truth[sid]['chemistry'] for sid in roles['test']}:
            require(any(truth[sid]['chemistry'] == chemistry for sid in roles['train']), f'No reference/training sources for {chemistry}/{fold}')
    require({truth[sid]['chemistry'] for roles in folds.values() for sid in roles['test']} == CHEMISTRIES, 'Both supplied chemistries must be evaluated')
    return folds


def load_predictions(path, truth, folds):
    rows, fields = read_csv(path, {'id', 'method', 'predicted'})
    predictions, cells = {}, defaultdict(set)
    vocabulary = {chemistry: {row['phase'] for row in truth.values() if row['chemistry'] == chemistry} for chemistry in CHEMISTRIES}
    for row in rows:
        optional_identifier(row, 'fold', 'default')
        optional_identifier(row, 'condition', 'original')
        sid, method, fold, condition = (row[field] for field in ('id', 'method', 'fold', 'condition'))
        require(sid in truth and fold in folds, f'Unknown prediction source or fold: {sid}/{fold}')
        require(sid in folds[fold]['test'], f'Prediction is not a declared held-out source: {sid}/{fold}')
        labels = json.loads(row['predicted'])
        require(isinstance(labels, list) and len(labels) == 1 and isinstance(labels[0], str), f'Expected one phase ID in a JSON list: {sid}/{method}')
        require(labels[0] in vocabulary[truth[sid]['chemistry']], f'Unknown phase for source chemistry: {sid}/{labels[0]}')
        key = (sid, method, fold, condition)
        require(key not in predictions, f'Ambiguous duplicate prediction: {key}')
        predictions[key] = dict(id=sid, method=method, fold=fold, condition=condition, predicted=labels[0])
        cells[method, fold, condition].add(sid)
    require({fold for _, fold, _ in cells} == set(folds), 'A declared fold has no evaluation predictions')
    for (method, fold, condition), ids in cells.items():
        require(ids == folds[fold]['test'], f'Incomplete held-out comparison: {method}/{fold}/{condition}')
    return predictions, 'condition' in fields


def check_conditions(output, predictions, condition_column):
    names = {row['condition'] for row in predictions.values()}
    path = output / 'conditions.csv'
    descriptions = {}
    if path.exists():
        rows, _ = read_csv(path, {'condition', 'description'})
        for row in rows:
            require(row['condition'] not in descriptions, f'Duplicate condition description: {row["condition"]}')
            descriptions[row['condition']] = row['description']
        require(set(descriptions) == names, 'Condition descriptions do not match the evaluated conditions')
    elif condition_column:
        raise AssertionError('Named conditions require conditions.csv descriptions')
    return {'conditions': sorted(names), 'descriptions': descriptions,
            'condition_origin_check': 'Manual: descriptions and execution must distinguish native data from artificial changes; no physical meaning is inferred from condition names.'}


def numerical_metrics(predictions, truth):
    groups = defaultdict(list)
    for row in predictions.values():
        key = (truth[row['id']]['chemistry'], row['method'], row['fold'], row['condition'])
        groups[key].append(row)
    summaries, confusions = [], []
    for (chemistry, method, fold, condition), rows in sorted(groups.items()):
        pairs = Counter((truth[row['id']]['phase'], row['predicted']) for row in rows)
        labels = sorted({label for pair in pairs for label in pair})
        correct = sum(n for (actual, predicted), n in pairs.items() if actual == predicted)
        f1, recalls = [], []
        for label in labels:
            tp = pairs[label, label]
            support = sum(n for (actual, _), n in pairs.items() if actual == label)
            called = sum(n for (_, predicted), n in pairs.items() if predicted == label)
            f1.append(2 * tp / (support + called))
            if support:
                recalls.append(tp / support)
        identity = dict(chemistry=chemistry, method=method, fold=fold, condition=condition)
        summaries.append({**identity, 'n': len(rows), 'accuracy': correct / len(rows),
                          'micro_f1': correct / len(rows), 'macro_f1': float(np.mean(f1)),
                          'balanced_accuracy': float(np.mean(recalls)),
                          'macro_f1_labels': labels,
                          'tested_phase_count': len({truth[row['id']]['phase'] for row in rows})})
        confusions.extend({**identity, 'actual': actual, 'predicted': predicted, 'n': n}
                          for (actual, predicted), n in sorted(pairs.items()))
    return summaries, confusions


def paired_comparisons(predictions, truth):
    panels = defaultdict(lambda: defaultdict(dict))
    for row in predictions.values():
        key = (truth[row['id']]['chemistry'], row['fold'], row['condition'])
        panels[key][row['method']][row['id']] = row['predicted'] == truth[row['id']]['phase']
    result = []
    for (chemistry, fold, condition), methods in sorted(panels.items()):
        for left, right in itertools.combinations(sorted(methods), 2):
            require(set(methods[left]) == set(methods[right]), 'Unpaired method comparison')
            counts = Counter((methods[left][sid], methods[right][sid]) for sid in methods[left])
            result.append(dict(chemistry=chemistry, fold=fold, condition=condition,
                               left_method=left, right_method=right, n=len(methods[left]),
                               both_correct=counts[True, True], left_only_correct=counts[True, False],
                               right_only_correct=counts[False, True], neither_correct=counts[False, False]))
    return result


def check_artifacts(output):
    require((output / 'report.md').is_file() and (output / 'report.md').read_text().strip(), 'Missing report.md')
    files = [path for path in output.rglob('*') if path.is_file()]
    require(any(path.suffix.lower() in {'.py', '.ipynb'} and path.stat().st_size for path in files), 'Missing analysis code')
    require(any(path.suffix.lower() in {'.png', '.svg', '.pdf'} and path.stat().st_size for path in files), 'Missing diagnostic figures')
    evidence = output / 'evidence.npz'
    numeric_arrays = 0
    if evidence.exists():
        with np.load(evidence, allow_pickle=False) as arrays:
            for key in arrays.files:
                array = arrays[key]
                require(array.size > 0, f'Empty numerical evidence array: {key}')
                if np.issubdtype(array.dtype, np.number):
                    require(np.isfinite(array).all(), f'Nonfinite numerical evidence: {key}')
                    numeric_arrays += 1
        require(numeric_arrays > 0, 'No numeric arrays in evidence.npz')
    return {'numerical_evidence_present': evidence.exists(), 'numeric_arrays': numeric_arrays,
            'generated_signal_provenance_status': 'Manual review required: match saved arrays to every claimed generated signal.' if evidence.exists() else 'No evidence archive supplied: manually determine whether generated signals are claimed; if so, the required provenance evidence is missing.',
            'evidence_check_scope': 'Array presence and finiteness only; generation, source linkage, physical transformations, and their interpretation need execution/evidence review.'}


def verify(output, data=DATA):
    output = Path(output)
    artifacts = check_artifacts(output)
    truth = source_truth(data)
    folds = load_splits(output / 'splits.csv', truth)
    predictions, condition_column = load_predictions(output / 'predictions.csv', truth, folds)
    conditions = check_conditions(output, predictions, condition_column)
    summaries, confusions = numerical_metrics(predictions, truth)
    return {'question': 'Q5', 'integrity_passed': True,
            'scientific_quality': 'NOT SCORED: mandatory code/execution and scientific review.',
            'discovery_target': 'NOT ASSESSED: numerical integrity cannot establish discovery.',
            'preferred_method_names_checked': False, 'performance_threshold_applied': False,
            'source_filename_truth': True, 'prediction_rows': len(predictions),
            'summaries': summaries, 'confusions': confusions,
            'paired_comparisons': paired_comparisons(predictions, truth),
            'metrics_source': 'Independently recomputed from predictions and original source identities; all submitted report/metric claims remain subject to scientific review.',
            **conditions, **artifacts,
            'review_rubric': 'verification/discovery_rubric.md',
            'limitations': ['Readable evaluation labels require code and data-flow auditing; declared held-out IDs alone do not prove label separation.',
                           'Related augmented spectra may share underlying structures even with disjoint IDs.',
                           'Low accuracy and a non-target physical method are not automatic failures.',
                           'Any artificial alteration, including a sole named condition, requires saved source-linked evidence and code review; condition names do not prove its origin.',
                           'A claimed discovery requires correct physical implementation and mechanistic validation, not a name or a high score.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--save', type=Path)
    args = parser.parse_args()
    report = verify(args.output, args.data)
    encoded = json.dumps(report, indent=2) + '\n'
    if args.save:
        args.save.write_text(encoded)
    else:
        print(encoded, end='')


if __name__ == '__main__':
    main()
