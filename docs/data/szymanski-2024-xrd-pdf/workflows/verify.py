#!/usr/bin/env python3
"""Evaluator-only checks anchored to release filenames and raw numerical data.

This module never imports candidate.py. Deterministic reference predictions are
benchmark reruns, not predictions released by the article's authors.
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1]
MODELS = ('XRD', 'PDF', 'Fused')
FORMULAS = {
    'Li-La-Zr-O': {'Li2CO3', 'LiOH', 'La(OH)3', 'ZrO2'},
    'Li-Ti-P-O': {'Li2CO3', 'Li2TiO3', 'Li3PO4', 'TiO2'},
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    with Path(path).open() as stream:
        return json.load(stream)


def source_truth(data=DATA):
    """Decode identities from original source filenames, not packaged labels."""
    truth = {}
    singles = defaultdict(list)
    for record in read_json(data / 'verification/source_labels.json'):
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
            singles[chemistry, phase].append(row)
        else:
            row['phases'] = path.name.split('+')
            require(len(row['phases']) == int(kind[0]), f'Wrong phase count {path}')
        require(row['id'] not in truth, 'Duplicate source ID')
        truth[row['id']] = row
    for group in singles.values():
        ordered = sorted(group, key=lambda row: row['replicate'])
        cutoff = max(1, int(.7 * len(ordered)))
        for index, row in enumerate(ordered):
            row['split'] = 'train' if index < cutoff else 'test'
    return truth


def task_rows(question, truth):
    if question == 'Q1':
        return {sid: row for sid, row in truth.items()
                if row['kind'] == '1-Phase' and row['split'] == 'test'}
    if question == 'Q2':
        return {sid: row for sid, row in truth.items() if row['kind'] in ('2-Phase', '3-Phase')}
    if question == 'Q4':
        return {sid: row for sid, row in truth.items() if row['kind'] == 'Experiments'}
    raise AssertionError(f'Unsupported prediction question: {question}')


def group_name(question, row):
    return ('single' if question == 'Q1' else row['kind'] if question == 'Q2'
            else str(row['minor_weight_percent']))


def load_predictions(path):
    predictions = {}
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(set(reader.fieldnames or []) == {'id', 'chemistry', 'model', 'predicted', 'scores'},
                'Prediction CSV columns differ from contract')
        for row in reader:
            key = row['id'], row['model']
            require(key not in predictions, f'Duplicate prediction {key}')
            row['predicted'] = json.loads(row['predicted'])
            row['scores'] = json.loads(row['scores'])
            require(isinstance(row['predicted'], list), f'Predicted labels must be a list: {key}')
            require(isinstance(row['scores'], dict), f'Scores must be a mapping: {key}')
            predictions[key] = row
    return predictions


def independent_metrics(question, predictions, rows):
    grouped = defaultdict(list)
    for sid, row in rows.items():
        grouped[row['chemistry'], group_name(question, row)].append(sid)
    summaries, complementarity = [], []
    for (chemistry, group), ids in sorted(grouped.items()):
        for model in MODELS:
            tp = fp = fn = exact = minor = 0
            for sid in ids:
                expected = set(rows[sid]['phases'])
                observed = set(predictions[sid, model]['predicted'])
                tp += len(expected & observed)
                fp += len(observed - expected)
                fn += len(expected - observed)
                exact += expected == observed
                if question == 'Q4':
                    minor += rows[sid]['minor'] in observed
            item = {'chemistry': chemistry, 'group': group, 'model': model,
                    'n': len(ids), 'micro_f1': 2 * tp / (2 * tp + fp + fn),
                    'exact_match': exact / len(ids)}
            if question == 'Q4':
                item['minor_recall'] = minor / len(ids)
            summaries.append(item)
        counts = {'chemistry': chemistry, 'group': group, 'n': len(ids),
                  'xrd_only_correct': 0, 'pdf_only_correct': 0,
                  'both_correct': 0, 'neither_correct': 0}
        for sid in ids:
            target = set(rows[sid]['phases'])
            left = set(predictions[sid, 'XRD']['predicted']) == target
            right = set(predictions[sid, 'PDF']['predicted']) == target
            name = ('both_correct' if left and right else 'xrd_only_correct' if left
                    else 'pdf_only_correct' if right else 'neither_correct')
            counts[name] += 1
        complementarity.append(counts)
    return {'question': question, 'summaries': summaries, 'complementarity': complementarity}


def compare_json(actual, expected, path='', tolerance=1e-10):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f'JSON keys differ: {path}')
        for key, value in expected.items():
            compare_json(actual[key], value, f'{path}/{key}', tolerance)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f'JSON list differs: {path}')
        # Summary and complementarity records are identified by semantic keys.
        if expected and isinstance(expected[0], dict) and 'chemistry' in expected[0]:
            key = lambda row: (row['chemistry'], str(row.get('group', '')), row.get('model', ''))
            actual, expected = sorted(actual, key=key), sorted(expected, key=key)
        for index, (a, b) in enumerate(zip(actual, expected)):
            compare_json(a, b, f'{path}/{index}', tolerance)
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        require(isinstance(actual, (float, int)) and not isinstance(actual, bool), f'Not numeric: {path}')
        require(np.isfinite(actual) and abs(actual - expected) <= tolerance,
                f'Numerical mismatch {path}: {actual} vs {expected}')
    else:
        require(actual == expected, f'Value differs: {path}')


def resampled_source(sid, truth, data=DATA):
    """Reconstruct the frozen baseline directly from the lossless input arrays."""
    row = truth[sid]
    path = data / 'inputs' / f'{row["chemistry"]}_{row["kind"]}.npz'
    with np.load(path, allow_pickle=False) as archive:
        array = archive[sid]
        theta, intensity = (archive['theta'], array) if 'theta' in archive else (array[:, 0], array[:, 1])
        axis = np.linspace(10.02, 79.98, 2001)
        spectrum = np.interp(axis, theta, intensity)
    spectrum = spectrum - np.quantile(spectrum, .1)
    spectrum = spectrum / max(float(spectrum.max()), 1e-30)
    return axis, spectrum


def check_probe(path, question, data=DATA):
    """Independent direct trapezoidal sine integral; no candidate code used."""
    with np.load(path, allow_pickle=False) as archive:
        for name in ('theta', 'r', 'xrd', 'pdf'):
            require(name in archive, f'Missing transform probe field {name}')
        theta, radii = archive['theta'], archive['r']
        xrd, pdf = archive['xrd'], archive['pdf']
        require('probe_id' in archive, 'Probe is missing source ID')
        sid = str(archive['probe_id'].item())
    truth = source_truth(data)
    eligible = (sorted(sid for sid, row in truth.items() if row['kind'] == '1-Phase' and row['chemistry'] == 'Li-Ti-P-O' and row['phases'] == ['Li2TiO3_15'])
                if question == 'Q3' else sorted(task_rows(question, truth)))
    require(sid == eligible[0], 'Probe ID is not the first evaluated source required by the contract')
    expected_r = np.linspace(1, 120, 1191) if question == 'Q3' else np.linspace(1, 40, 1000)
    np.testing.assert_array_equal(radii, expected_r, err_msg='Wrong frozen probe distance grid')
    require(xrd.ndim == pdf.ndim == 1, 'The fixed probe must contain one spectrum')
    source_theta, source_xrd = resampled_source(sid, truth, data)
    np.testing.assert_array_equal(theta, source_theta, err_msg='Wrong probe angle grid')
    np.testing.assert_allclose(xrd, source_xrd, rtol=1e-12, atol=1e-12,
                               err_msg='Probe baseline does not match raw release data')
    require(theta.ndim == radii.ndim == 1, 'Probe axes must be 1D')
    require(np.isfinite(theta).all() and np.isfinite(radii).all(), 'Non-finite probe axes')
    require((np.diff(theta) > 0).all() and (np.diff(radii) > 0).all(), 'Unordered probe axes')
    require(xrd.shape[-1] == len(theta) and pdf.shape[-1] == len(radii), 'Probe dimensions differ')
    require(xrd.shape[:-1] == pdf.shape[:-1], 'Probe sample dimensions differ')
    require(np.isfinite(xrd).all() and np.isfinite(pdf).all(), 'Non-finite probe values')
    q = 4 * np.pi * np.sin(theta * np.pi / 360) / 1.5406
    xrows, prows = np.atleast_2d(xrd), np.atleast_2d(pdf)
    maximum = 0.
    for spectrum, observed in zip(xrows, prows):
        expected = []
        for radius in radii:
            y = q * spectrum * np.sin(q * radius)
            expected.append(np.sum((y[:-1] + y[1:]) * np.diff(q) / 2) * 2 / np.pi)
        expected = np.asarray(expected)
        np.testing.assert_allclose(observed, expected, rtol=1e-9, atol=1e-9,
                                   err_msg='Virtual-PDF probe violates frozen sine-transform convention')
        maximum = max(maximum, float(np.max(np.abs(observed - expected))))
    return {'independent_transform_max_absolute_error': maximum}


def check_partitions(path, truth):
    trace = read_json(path)
    require(set(trace) == set(FORMULAS), 'Split trace chemistry keys differ')
    for chemistry in FORMULAS:
        require(set(trace[chemistry]) == {'train', 'test'}, 'Split trace partition keys differ')
        for partition in ('train', 'test'):
            ids = trace[chemistry][partition]
            require(isinstance(ids, list) and len(ids) == len(set(ids)), 'Duplicate split-trace IDs')
            expected = {sid for sid, row in truth.items() if row['chemistry'] == chemistry
                        and row['kind'] == '1-Phase' and row['split'] == partition}
            require(set(ids) == expected, f'Source-derived split differs: {chemistry}/{partition}')
        require(not set(trace[chemistry]['train']) & set(trace[chemistry]['test']),
                f'Train/test overlap in {chemistry}')


def check_explanatory_outputs(output):
    plots = [p for p in output.iterdir() if p.suffix.lower() in ('.png', '.svg', '.pdf')]
    require(any(p.stat().st_size > 100 for p in plots), 'No nonempty plot artifact')
    conclusions = [output / name for name in ('conclusion.md', 'conclusion.txt')]
    require(any(p.is_file() and len(p.read_text().strip()) >= 40 for p in conclusions),
            'Missing substantive conclusion artifact')


def verify(question, output, reference, data=DATA):
    output, reference, data = Path(output), Path(reference), Path(data)
    check_explanatory_outputs(output)
    probe = check_probe(output / 'probe.npz', question, data)
    if question == 'Q3':
        return verify_robustness(output, reference, probe, data)
    truth = source_truth(data)
    check_partitions(output / 'split_trace.json', truth)
    rows = task_rows(question, truth)
    actual = load_predictions(output / 'predictions.csv')
    expected = load_predictions(reference / 'predictions.csv')
    keys = {(sid, model) for sid in rows for model in MODELS}
    require(set(actual) == keys, 'Missing or unexpected prediction rows')
    require(set(expected) == keys, 'Reference prediction row set is incomplete')
    classes = {chemistry: sorted({r['phases'][0] for r in truth.values()
               if r['chemistry'] == chemistry and r['kind'] == '1-Phase'})
               for chemistry in FORMULAS}
    for key in sorted(keys):
        sid, model = key
        row, source = actual[key], rows[sid]
        require(row['chemistry'] == source['chemistry'], f'Chemistry mismatch: {key}')
        labels = sorted(FORMULAS[source['chemistry']]) if question == 'Q4' else classes[source['chemistry']]
        scores = row['scores']
        require(set(scores) == set(labels), f'Incomplete or unknown score labels: {key}')
        values = np.array([scores[label] for label in labels], dtype=float)
        require(np.isfinite(values).all() and (values >= -1e-12).all(), f'Invalid scores: {key}')
        require(abs(values.sum() - 1) <= 1e-7, f'Scores do not sum to one: {key}')
        count = 1 if question == 'Q1' else 2 if question == 'Q4' else int(source['kind'][0])
        chosen = sorted(labels, key=lambda label: (-scores[label], label))[:count]
        require(row['predicted'] == chosen, f'Predictions violate top-K selection: {key}')
        require(row['predicted'] == expected[key]['predicted'], f'Predictions differ from deterministic reference: {key}')
        np.testing.assert_allclose(values, [expected[key]['scores'][label] for label in labels],
                                   rtol=1e-6, atol=1e-7, err_msg=f'Scores differ: {key}')
        if model == 'Fused':
            fused = np.array([(actual[sid, 'XRD']['scores'][label] +
                               actual[sid, 'PDF']['scores'][label]) / 2 for label in labels])
            np.testing.assert_allclose(values, fused, rtol=1e-10, atol=1e-10,
                                       err_msg=f'Incorrect score fusion: {sid}')
    metrics = independent_metrics(question, actual, rows)
    compare_json(read_json(output / 'result.json'), metrics)
    return {'question': question, 'passed': True, 'prediction_rows': len(actual),
            'source_filename_truth': True, 'independent_metric_recomputation': True,
            'source_derived_partitions_checked': True,
            **probe, 'manual_review_required': 'Plot meaning, conclusions, and causal limits.'}


def source_robustness(data=DATA):
    """Rebuild artifact curves/metrics from release arrays and declared seeds."""
    truth = source_truth(data)
    ordered = read_json(data / 'inputs/Li-Ti-P-O_1-Phase.json')
    sources = [(index, row['id']) for index, row in enumerate(ordered)
               if truth[row['id']]['phases'] == ['Li2TiO3_15']]
    require(len(sources) == 11, 'Expected eleven released Li2TiO3_15 patterns')
    radii = np.linspace(1, 120, 1191)
    theta = np.linspace(10.02, 79.98, 2001)
    q = 4 * np.pi * np.sin(theta * np.pi / 360) / 1.5406
    sine = np.sin(radii[:, None] * q)
    def integrate(values):
        integrand = sine * q * values
        return ((integrand[:, :-1] + integrand[:, 1:]) @ np.diff(q)) / np.pi
    windows = {'1-5': (radii >= 1) & (radii < 5),
               '5-40': (radii >= 5) & (radii < 40),
               '1-40': (radii >= 1) & (radii < 40),
               '40-120': (radii >= 40) & (radii <= 120)}
    curves, metrics = {'r': radii}, []
    for index, sid in sources:
        _, spectrum = resampled_source(sid, truth, data)
        baseline = integrate(spectrum)
        curves[sid + '_base'] = baseline
        for artifact, levels, trials in (('noise', (.01, .03), 5), ('background', (.05, .20), 1)):
            for amplitude in levels:
                for trial in range(trials):
                    if artifact == 'noise':
                        random = np.random.default_rng(202409 + index * 100 + trial)
                        delta = random.normal(0, amplitude, theta.size)
                    else:
                        delta = amplitude * np.exp(-.5 * ((theta - 35) / 12) ** 2)
                    # Transform added artifacts independently, exploiting the
                    # linearity of the declared unrenormalized experiment.
                    difference = integrate(delta)
                    curves[f'{sid}_{artifact}_{amplitude}_{trial}'] = baseline + difference
                    for window, mask in windows.items():
                        metrics.append({'id': sid, 'artifact': artifact,
                                        'amplitude': amplitude, 'trial': trial, 'window': window,
                                        'xrd_relative_l2': float(np.sqrt(np.sum(delta ** 2) / np.sum(spectrum ** 2))),
                                        'pdf_relative_l2': float(np.sqrt(np.sum(difference[mask] ** 2) / np.sum(baseline[mask] ** 2))),
                                        'signal_energy_fraction': float(np.sum(baseline[mask] ** 2) / np.sum(baseline ** 2)),
                                        'artifact_energy_fraction': float(np.sum(difference[mask] ** 2) / np.sum(difference ** 2))})
    summaries = []
    values = ('xrd_relative_l2', 'pdf_relative_l2', 'signal_energy_fraction', 'artifact_energy_fraction')
    for artifact in ('noise', 'background'):
        for amplitude in sorted({row['amplitude'] for row in metrics if row['artifact'] == artifact}):
            for window in windows:
                selected = [row for row in metrics if row['artifact'] == artifact and row['amplitude'] == amplitude and row['window'] == window]
                summaries.append({'artifact': artifact, 'amplitude': amplitude, 'window': window,
                                  'n': len(selected), **{name: sum(row[name] for row in selected) / len(selected) for name in values}})
    return curves, metrics, {'question': 'Q3', 'source_patterns': len(sources), 'summaries': summaries}


def verify_robustness(output, reference, probe, data=DATA):
    curves, metrics, result = source_robustness(data)
    with np.load(output / 'curves.npz', allow_pickle=False) as actual:
        require(set(actual.files) == set(curves), 'Missing/unexpected artifact curves')
        for key, expected in curves.items():
            require(np.isfinite(actual[key]).all(), f'Non-finite artifact curve {key}')
            np.testing.assert_allclose(actual[key], expected, rtol=1e-8, atol=1e-9,
                                       err_msg=f'Source-reconstructed artifact curve differs: {key}')
    with (output / 'metrics.csv').open(newline='') as stream:
        actual = list(csv.DictReader(stream))
    require(len(actual) == len(metrics) == 528, 'Wrong number of artifact metric CSV rows')
    key = lambda row: (row['id'], row['artifact'], float(row['amplitude']), int(row['trial']), row['window'])
    actual = {key(row): row for row in actual}
    require(len(actual) == len(metrics) == 528, 'Wrong artifact metric row count or duplicate keys')
    for expected in metrics:
        require(key(expected) in actual, f'Missing artifact metric: {key(expected)}')
        row = actual[key(expected)]
        require(set(row) == set(expected), 'Artifact metric CSV fields differ')
        for name, value in expected.items():
            compare_json(float(row[name]) if isinstance(value, (float, int)) else row[name], value,
                         path=f'{key(expected)}/{name}', tolerance=1e-9)
    compare_json(read_json(output / 'result.json'), result, tolerance=1e-9)
    return {'question': 'Q3', 'passed': True, 'curves_reconstructed_from_source': len(curves) - 1,
            'independent_metric_rows': len(metrics), **probe,
            'manual_review_required': 'Plot meaning, window tradeoffs, and causal limits.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--question', choices=['Q1', 'Q2', 'Q3', 'Q4'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.question, args.output, args.reference or DATA / 'verification' / args.question), indent=2))


if __name__ == '__main__':
    main()
