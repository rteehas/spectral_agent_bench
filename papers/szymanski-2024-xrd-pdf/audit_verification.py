#!/usr/bin/env python3
"""Independent release anchors and adversarial verification-loop controls.

Neither the candidate workflow nor its model-fitting helpers are imported.
Run with the downloaded numeric release and completed candidate output folders.
"""
import argparse
import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/szymanski-2024-xrd-pdf'
spec = importlib.util.spec_from_file_location('szymanski_verifier', DATA / 'workflows/verify.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def audit_source(release):
    truth = v.source_truth(DATA)
    inventory, hashes, native_grids = {}, set(), {}
    count = 0
    for manifest in sorted((DATA / 'inputs').glob('*.json')):
        records = v.read_json(manifest)
        if not isinstance(records, list) or not records or 'id' not in records[0]:
            continue
        archive = manifest.with_suffix('.npz')
        if not archive.is_file():
            continue
        with np.load(archive, allow_pickle=False) as arrays:
            v.require(set(arrays.files) - {'theta'} == {row['id'] for row in records}, f'Input archive IDs: {archive.name}')
            for row in records:
                source = truth[row['id']]
                for field in ('phases', 'chemistry', 'kind', 'split', 'replicate', 'major', 'minor', 'minor_weight_percent'):
                    if field in row:
                        v.require(row[field] == source[field], f'Incorrect source label {row["id"]}/{field}')
                path = release / source['source_path']
                digest = sha(path)
                v.require(digest == source['sha256'], f'Source hash mismatch: {path}')
                v.require(digest not in hashes, f'Duplicated raw spectrum: {path}')
                hashes.add(digest)
                raw = np.loadtxt(path)
                packaged = np.column_stack((arrays['theta'], arrays[row['id']])) if 'theta' in arrays else arrays[row['id']]
                np.testing.assert_array_equal(raw, packaged, err_msg=f'Packaging changed numeric data: {path}')
                v.require(np.isfinite(raw).all(), f'Non-finite source: {path}')
                v.require((np.diff(raw[:, 0]) > 0).all(), f'Unsorted source: {path}')
                grid = f'{len(raw)} points, {raw[0, 0]:.9f} to {raw[-1, 0]:.9f} degrees'
                native_grids[grid] = native_grids.get(grid, 0) + 1
                count += 1
        inventory[manifest.stem] = {'spectra': len(records),
                                    'phase_labels': len({p for row in records for p in row['phases']})}
    v.require(count == len(truth) == 2930, 'Release audit did not cover all 2930 numeric spectra')
    return {'passed': True, 'raw_spectra_compared_exactly': count,
            'byte_unique_source_files': len(hashes), 'inventory': inventory,
            'native_grids': native_grids,
            'label_anchor': 'Original release basenames, checked independently against all input metadata.',
            'data_anchor': 'All float64 NPZ arrays equal np.loadtxt(original release file) exactly.',
            'limitations': ['Source labels establish nominal composition and phase identity; they are not independently measured sample purity.',
                            'The release has 2690 simulated and 240 experimental spectra; it does not supply the complete historical model test set.',
                            'Deterministic prediction references are new benchmark baseline outputs, not author-released predictions.']}


def change_result(path):
    record = v.read_json(path / 'result.json')
    if 'summaries' in record:
        record['summaries'][0]['n'] += 1
    else:
        # Any numeric leaf is suitable for a metric corruption control.
        def mutate(item):
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        item[key] = value + 1
                        return True
                    if mutate(value):
                        return True
            elif isinstance(item, list):
                return any(mutate(value) for value in item)
            return False
        v.require(mutate(record), 'No numeric result leaf for negative control')
    write_json(path / 'result.json', record)


def change_predictions(path, kind):
    filename = path / 'predictions.csv'
    with filename.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    if kind == 'missing_prediction_row':
        rows.pop()
    elif kind == 'duplicate_prediction_row':
        rows.append(copy.deepcopy(rows[0]))
    elif kind == 'unknown_phase':
        rows[0]['predicted'] = json.dumps(['InventedPhase_1'])
    else:
        scores = json.loads(rows[0]['scores'])
        key = next(iter(scores))
        if kind == 'nonfinite_score':
            scores[key] = float('nan')
        else:
            largest = max(scores, key=scores.get)
            other = next(label for label in scores if label != largest)
            amount = min(.01, scores[largest] / 4)
            scores[largest] -= amount
            scores[other] += amount
            # Preserve all schema, simplex, and top-K rules: only a numerical
            # reference/source check can reject this otherwise valid answer.
            count = len(json.loads(rows[0]['predicted']))
            rows[0]['predicted'] = json.dumps(sorted(scores, key=lambda label: (-scores[label], label))[:count])
        rows[0]['scores'] = json.dumps(scores)
    with filename.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def change_probe(path):
    filename = path / 'probe.npz'
    with np.load(filename, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    arrays['pdf'] = arrays['pdf'] * 1.2 + .01
    np.savez_compressed(filename, **arrays)


def remove_plots(path):
    for filename in path.iterdir():
        if filename.suffix.lower() in ('.png', '.svg', '.pdf'):
            filename.unlink()


def duplicate_artifact_metric(path):
    filename = path / 'metrics.csv'
    lines = filename.read_text().splitlines()
    filename.write_text('\n'.join(lines + [lines[1]]) + '\n')


def corrupt_artifact_curve(path):
    filename = path / 'curves.npz'
    with np.load(filename, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    key = next(key for key in arrays if key != 'r')
    arrays[key][100] += .2
    np.savez_compressed(filename, **arrays)


def wrong_partition(path):
    filename = path / 'split_trace.json'
    trace = v.read_json(filename)
    chemistry = next(iter(trace))
    # Swap IDs while retaining sizes and disjointness; only independent split
    # reconstruction detects this incorrect but superficially valid split.
    trace[chemistry]['train'][0], trace[chemistry]['test'][0] = trace[chemistry]['test'][0], trace[chemistry]['train'][0]
    write_json(filename, trace)


def wrong_probe(path, kind):
    filename = path / 'probe.npz'
    with np.load(filename, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    if kind == 'wrong_probe_id':
        arrays['probe_id'] = np.array('B_1-Phase_0000')
    else:
        arrays['r'] = arrays['r'] + .05
        q = 4 * np.pi * np.sin(arrays['theta'] * np.pi / 360) / 1.5406
        y = q * arrays['xrd'] * np.sin(np.outer(arrays['r'], q))
        arrays['pdf'] = np.sum((y[:, :-1] + y[:, 1:]) * np.diff(q), axis=1) / np.pi
    np.savez_compressed(filename, **arrays)


def candidate_dir(root, question):
    nested = root / question / 'output'
    return nested if nested.is_dir() else root / question


def audit_controls(candidate_runs):
    report = []
    with tempfile.TemporaryDirectory(prefix='szymanski-verifier-audit-') as temporary:
        base = Path(temporary)
        for question in ('Q1', 'Q2', 'Q3', 'Q4'):
            original = candidate_dir(candidate_runs, question)
            reference = DATA / 'verification' / question
            positive = v.verify(question, original, reference)
            controls = {'wrong_reported_metric': change_result,
                        'incorrect_sine_transform': change_probe,
                        'missing_plot': remove_plots,
                        'wrong_probe_id': lambda folder: wrong_probe(folder, 'wrong_probe_id'),
                        'wrong_probe_grid': lambda folder: wrong_probe(folder, 'wrong_probe_grid')}
            if question != 'Q3':
                for name in ('missing_prediction_row', 'duplicate_prediction_row', 'unknown_phase', 'nonfinite_score', 'incorrect_scores'):
                    controls[name] = lambda folder, kind=name: change_predictions(folder, kind)
                controls['wrong_split'] = wrong_partition
                controls['missing_split'] = lambda folder: (folder / 'split_trace.json').unlink()
            else:
                controls['duplicated_artifact_metric'] = duplicate_artifact_metric
                controls['corrupted_artifact_curve'] = corrupt_artifact_curve
            rejected = []
            for name, mutate in controls.items():
                wrong = base / question / name
                shutil.copytree(original, wrong)
                mutate(wrong)
                try:
                    v.verify(question, wrong, reference)
                except (AssertionError, ValueError, FileNotFoundError) as error:
                    rejected.append({'control': name, 'rejected': True,
                                     'reason': next((line for line in str(error).splitlines() if line.strip()), type(error).__name__)[:240]})
                else:
                    raise AssertionError(f'{question} accepted negative control: {name}')
            report.append({'question': question, 'positive_control': positive,
                           'negative_controls': rejected})
    return report


def audit_independent_model_probes(candidate_runs):
    """Refit selected predictions via different algebra and solver inputs."""
    from scipy.optimize import nnls
    truth = v.source_truth(DATA)
    axis = np.linspace(10.02, 79.98, 2001)
    radii = np.linspace(1, 40, 1000)
    q = 4 * np.pi * np.sin(axis * np.pi / 360) / 1.5406
    f = 2 / np.pi * np.sin(np.outer(radii, q)) * q
    # Endpoint contributions implement trapezoidal integration explicitly.
    operator = np.zeros_like(f)
    operator[:, :-1] += f[:, :-1] * np.diff(q) / 2
    operator[:, 1:] += f[:, 1:] * np.diff(q) / 2
    def normalized(array):
        return array / np.maximum(np.sqrt(np.sum(array * array, axis=1, keepdims=True)), 1e-30)
    report = []
    for chemistry in sorted(v.FORMULAS):
        rows = [row for row in truth.values() if row['chemistry'] == chemistry and row['kind'] == '1-Phase']
        rows.sort(key=lambda row: row['id'])
        rawfile = DATA / 'inputs' / f'{chemistry}_1-Phase.npz'
        with np.load(rawfile, allow_pickle=False) as archive:
            raw = np.array([np.interp(axis, archive['theta'], archive[row['id']]) for row in rows])
        xrd = raw - np.quantile(raw, .1, axis=1, keepdims=True)
        xrd /= np.maximum(xrd.max(axis=1, keepdims=True), 1e-30)
        train = np.array([row['split'] == 'train' for row in rows])
        labels = np.array([row['phases'][0] for row in rows])
        for question in ('Q1', 'Q2', 'Q4'):
            predictions = v.load_predictions(candidate_dir(candidate_runs, question) / 'predictions.csv')
            eligible = sorted(sid for sid, row in v.task_rows(question, truth).items() if row['chemistry'] == chemistry)
            ids = [eligible[0], eligible[len(eligible) // 2], eligible[-1]]
            target = np.array([v.resampled_source(sid, truth, DATA)[1] for sid in ids])
            classes = sorted(set(labels))
            if question == 'Q4':
                classes = [label for label in classes if label.rsplit('_', 1)[0] in v.FORMULAS[chemistry]]
            templates = np.array([xrd[train & (labels == label)].mean(axis=0) for label in classes])
            for model in ('XRD', 'PDF'):
                training = normalized(xrd[train] if model == 'XRD' else xrd[train] @ operator.T)
                targets = normalized(target if model == 'XRD' else target @ operator.T)
                if question == 'Q1':
                    # Independently solve centered multivariate ridge in the
                    # sample-space dual, including the unregularized intercept.
                    encoded = np.array([[1. if label == phase else -1. for phase in classes] for label in labels[train]])
                    xmean, ymean = training.mean(axis=0), encoded.mean(axis=0)
                    centered = training - xmean
                    dual = np.linalg.solve(centered @ centered.T + np.eye(len(centered)), encoded - ymean)
                    decisions = (targets - xmean) @ centered.T @ dual + ymean
                    exponentials = np.exp(decisions - decisions.max(axis=1, keepdims=True))
                    scores = exponentials / exponentials.sum(axis=1, keepdims=True)
                    names = classes
                else:
                    refs = normalized(templates if model == 'XRD' else templates @ operator.T)
                    # Candidate uses a Cholesky normal-equation compression.
                    # This independent solve uses the tall original spectral
                    # matrix with explicit epsilon regularization rows.
                    design = np.vstack((refs.T, np.sqrt(1e-10) * np.eye(len(refs))))
                    coefficients = np.array([nnls(design, np.r_[y, np.zeros(len(refs))], maxiter=10000)[0] for y in targets])
                    scores = coefficients / np.maximum(coefficients.sum(axis=1, keepdims=True), 1e-30)
                    names = classes
                    if question == 'Q4':
                        names = sorted(v.FORMULAS[chemistry])
                        scores = np.array([scores[:, [i for i, phase in enumerate(classes) if phase.rsplit('_', 1)[0] == name]].sum(axis=1) for name in names]).T
                expected = np.array([[predictions[sid, model]['scores'][label] for label in names] for sid in ids])
                np.testing.assert_allclose(scores, expected, rtol=1e-6, atol=1e-7,
                                           err_msg=f'Independent model refit differs: {question}/{chemistry}/{model}')
                report.append({'question': question, 'chemistry': chemistry, 'model': model,
                               'source_ids': ids, 'scores_checked': scores.size,
                               'maximum_absolute_difference': float(np.max(np.abs(scores - expected)))})
    return {'passed': True, 'candidate_module_imported': False,
            'ridge_method': 'Centered dual linear solve with explicit -1/+1 targets and softmax.',
            'nnls_method': 'Direct tall spectral design plus sqrt(1e-10) identity rows.',
            'probes': report}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--candidate-runs', type=Path)
    args = parser.parse_args()
    report = {'source_audit': audit_source(args.release)}
    if args.candidate_runs:
        report['verification_controls'] = audit_controls(args.candidate_runs)
        report['independent_model_probes'] = audit_independent_model_probes(args.candidate_runs)
    report['scope'] = 'Independent source and numerical checks; scientific interpretation and plot legibility also require reviewer inspection.'
    target = DATA / 'verification/verification_audit.json'
    write_json(target, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
