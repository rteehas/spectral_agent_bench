#!/usr/bin/env python3
"""Independent numerical probes of the *illustrative worked Q3 candidate*.

These checks follow that candidate's documented choices. They are NOT part of
verify.py and must never be used to require other submissions to use its choices.
No candidate functions are imported.
"""
import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/szymanski-2024-xrd-pdf'


def read_json(path):
    return json.loads(path.read_text())


def load_evidence(path):
    with np.load(path, allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def audit_q3(output):
    output = Path(output)
    arrays = load_evidence(output / 'evidence.npz')
    design = read_json(output / 'design.json')
    description = read_json(output / 'evidence.json')
    theta, radii = arrays['theta'], arrays['r']
    ids, conditions = list(map(str, arrays['ids'])), list(map(str, arrays['conditions']))
    assert np.all(np.diff(theta) > 0) and np.all(np.diff(radii) > 0)
    with (output / 'splits.csv').open(newline='') as stream:
        partitions = {row['id']: row['role'] for row in csv.DictReader(stream)}
    assert all(partitions[sid] == 'test' for sid in ids)
    source_rows = read_json(DATA / 'inputs/Li-Ti-P-O_1-Phase.json')
    test_ids = [row['id'] for row in source_rows if partitions[row['id']] == 'test']
    assert ids == test_ids[:len(ids)]
    with np.load(DATA / 'inputs/Li-Ti-P-O_1-Phase.npz', allow_pickle=False) as source:
        raw = np.stack([np.interp(theta, source['theta'], source[sid]) for sid in ids])
    shifted = raw - np.quantile(raw, .1, axis=1)[:, None]
    expected_xrd = shifted / np.maximum(shifted.max(axis=1)[:, None], 1e-30)
    np.testing.assert_allclose(arrays['clean_xrd'], expected_xrd, rtol=1e-12, atol=1e-12)
    declared_conditions = design['conditions']
    assert conditions == [row['condition'] for row in declared_conditions if row['artifact'] != 'clean']
    artifact_errors = []
    for index, condition in enumerate(conditions):
        cindex = next(i for i, row in enumerate(declared_conditions) if row['condition'] == condition)
        family, amplitude, *extra = condition.split('_')
        amplitude = float(amplitude)
        if family == 'noise':
            trial = int(extra[0].removeprefix('trial'))
            generator = np.random.default_rng(design['seed'] + 2000 + cindex * 100 + trial)
            delta = generator.standard_normal((len(test_ids), len(theta)))[:len(ids)] * amplitude
        else:
            delta = amplitude * np.exp(-((theta - 35.) ** 2) / (2 * 12. ** 2))
        expected = expected_xrd + delta
        observed = arrays['perturbed_xrd'][index]
        np.testing.assert_allclose(observed, expected, rtol=1e-12, atol=1e-12)
        artifact_errors.append({'condition': condition, 'source_patterns_checked': len(ids),
                                'maximum_absolute_error': float(np.max(np.abs(expected - observed)))})
    # Explicit adjacent-point trapezoids, independently of the candidate's
    # preweighted linear transform matrix. Process radii in bounded blocks.
    q = 4 * np.pi * np.sin(theta * np.pi / 360) / 1.5406
    def direct_transform(xrd):
        result = np.empty((len(xrd), len(radii)))
        for start in range(0, len(radii), 32):
            rblock = radii[start:start + 32]
            integrands = xrd[:, None, :] * q[None, None, :] * np.sin(rblock[None, :, None] * q[None, None, :])
            result[:, start:start + len(rblock)] = np.sum((integrands[:, :, 1:] + integrands[:, :, :-1]) * np.diff(q)[None, None, :], axis=2) / np.pi
        return result
    baseline = direct_transform(expected_xrd)
    np.testing.assert_allclose(arrays['clean_pdf'], baseline, rtol=1e-9, atol=1e-9)
    maximum = float(np.max(np.abs(arrays['clean_pdf'] - baseline)))
    for index in range(len(conditions)):
        expected = direct_transform(arrays['perturbed_xrd'][index])
        np.testing.assert_allclose(arrays['perturbed_pdf'][index], expected, rtol=1e-9, atol=1e-9)
        maximum = max(maximum, float(np.max(np.abs(arrays['perturbed_pdf'][index] - expected))))
    with (output / 'distortion.csv').open(newline='') as stream:
        distortion = list(csv.DictReader(stream))
    checked = 0
    for row in distortion:
        if row['id'] not in ids:
            continue
        sample, condition = ids.index(row['id']), conditions.index(row['condition'])
        if row['representation'] == 'XRD':
            before, after = expected_xrd[sample], arrays['perturbed_xrd'][condition, sample]
            energy = 1.
        else:
            lo, hi = description['windows'][row['method']]
            mask = (radii >= lo) & (radii < hi)
            before, after = baseline[sample, mask], arrays['perturbed_pdf'][condition, sample, mask]
            energy = float(np.sum(before * before) / np.sum(baseline[sample] * baseline[sample]))
        relative = float(np.sqrt(np.sum((after - before) ** 2) / np.sum(before ** 2)))
        assert abs(float(row['relative_l2']) - relative) <= 1e-8
        assert abs(float(row['signal_energy_fraction']) - energy) <= 1e-8
        checked += 1
    # Re-derive the selection solely from saved validation accuracies. This
    # does not prove the trace is honest; the separate code/execution audit does.
    selections = design['regularization_and_window_search']
    scores = {}
    for method, record in selections.items():
        means = [np.mean([record['condition_accuracy'][row['condition']] for row in declared_conditions if row['artifact'] == family]) for family in ('clean', 'noise', 'background')]
        score = float(np.mean(means))
        assert abs(score - record['artifact_balanced_accuracy']) <= 1e-12
        if method != 'XRD':
            scores[method] = score
    assert design['selected_window'] == max(scores, key=scores.get)
    return {'passed': True, 'scope': 'Independent numerical audit of the documented worked candidate only; not a universal solver constraint.',
            'candidate_module_imported': False, 'source_patterns_reconstructed': len(ids),
            'baseline_and_perturbed_transforms_checked': len(ids) * (1 + len(conditions)),
            'transform_maximum_absolute_error': maximum, 'perturbation_checks': artifact_errors,
            'independently_recomputed_distortion_rows': checked,
            'validation_selection_arithmetic_checked': True,
            'limitations': 'These source/transform/perturbation probes do not refit classifiers or establish absence of label leakage by themselves.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate-runs', type=Path, required=True)
    args = parser.parse_args()
    output = args.candidate_runs / 'Q3'
    if (output / 'output').is_dir():
        output = output / 'output'
    report = audit_q3(output)
    with tempfile.TemporaryDirectory(prefix='szymanski-candidate-evidence-control-') as temporary:
        corrupted = Path(temporary) / 'output'
        shutil.copytree(output, corrupted)
        arrays = load_evidence(corrupted / 'evidence.npz')
        arrays['perturbed_pdf'] *= 7
        np.savez_compressed(corrupted / 'evidence.npz', **arrays)
        try:
            audit_q3(corrupted)
        except AssertionError:
            report['candidate_specific_corrupted_transform_rejected'] = True
        else:
            raise AssertionError('Candidate evidence audit accepted a deliberately corrupted transform')
    report['candidate_code_sha256'] = hashlib.sha256((output / 'run.py').read_bytes()).hexdigest()
    target = DATA / 'verification/independent_candidate_evidence_review.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
