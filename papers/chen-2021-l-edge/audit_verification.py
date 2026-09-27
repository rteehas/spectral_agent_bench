#!/usr/bin/env python3
"""Execute independent provenance and verifier positive/corruption controls."""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / 'docs/data/chen-2021-l-edge'
SPEC = importlib.util.spec_from_file_location('chen_independent_verifier', BUNDLE / 'workflows/verify.py')
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


def source_audit(raw_path):
    """Match exact original line bytes; no parsing-and-reserialization shortcut."""
    selected = {element: {} for element in VERIFIER.ELEMENTS}
    total, negatives, edges, materials = 0, 0, {}, set()
    raw_hash = hashlib.sha256()
    with Path(raw_path).open('rb') as stream:
        for line in stream:
            raw_hash.update(line)
            obj = json.loads(line)
            total += 1
            if min(obj['spectrum'][1]) < 0:
                negatives += 1
            identity = (obj['mp-id'], obj['absorbing_atom'])
            edges.setdefault(identity, set()).add(obj['edge'])
            element = obj['structure']['sites'][obj['absorbing_atom']]['species'][0]['element']
            if element in selected:
                assert obj['name'] not in selected[element], 'Repeated source name'
                selected[element][obj['name']] = hashlib.sha256(line).hexdigest()
                materials.add(obj['mp-id'])
    checks = []
    for element, expected in selected.items():
        observed = {}
        stream_hash = hashlib.sha256()
        path = BUNDLE / f'inputs/{element}.jsonl.gz'
        with gzip.open(path, 'rb') as stream:
            for line in stream:
                stream_hash.update(line)
                name = json.loads(line)['name']
                assert name not in observed, 'Repeated package name'
                observed[name] = hashlib.sha256(line).hexdigest()
        assert observed == expected, f'{element}: native byte/coverage mismatch'
        checks.append(dict(element=element, records=len(observed),
                           packaged_sha256=VERIFIER.sha256(path),
                           uncompressed_sha256=stream_hash.hexdigest(), native_lines_identical=True))
    prov = json.loads((BUNDLE / 'provenance.json').read_text())
    assert prov['member']['sha256'] == raw_hash.hexdigest(), 'Source hash mismatch'
    by_element = {item['element']: item for item in checks}
    for asset in prov['input_assets']:
        obs = by_element[asset['name'].split('.')[0]]
        assert asset['sha256'] == obs['packaged_sha256']
        assert asset['uncompressed_sha256'] == obs['uncompressed_sha256']
        assert asset['records'] == obs['records']
    return dict(pass_=True, release_records=total, release_negative_records=negatives,
                release_orphan_site_records=sum(len(v) == 1 for v in edges.values()),
                package_records=sum(len(v) for v in selected.values()),
                package_materials=len(materials), raw_sha256=raw_hash.hexdigest(), elements=checks,
                caveat='Orphan count uses (mp-id, absorbing_atom); native names remain authoritative and material-ID collisions require explicit handling.')


def mirrored_tree(source, target):
    """Link large immutable artifacts; mutated artifacts must replace their link."""
    target.mkdir(parents=True)
    for path in source.rglob('*'):
        dest = target / path.relative_to(source)
        if path.is_dir():
            dest.mkdir(exist_ok=True)
        else:
            dest.symlink_to(path.resolve())


def rewrite_csv(path, change):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    change(rows)
    path.unlink()
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def rewrite_json(path, change):
    data = json.loads(path.read_text())
    change(data)
    path.unlink()
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def rewrite_npz(path, change):
    with np.load(path) as stream:
        arrays = {key: stream[key] for key in stream.files}
    change(arrays)
    path.unlink()
    np.savez_compressed(path, **arrays)


def resample_response_grid(directory):
    with np.load(directory / 'responses.npz') as data:
        key = sorted(data.files)[0]
        old = data[key]
    grid = np.linspace(old[0, 0], old[-1, 0], 137)
    # Interpolate the piecewise-linear function on a new, still complete support.
    rewrite_npz(directory / 'responses.npz', lambda arrays: arrays.__setitem__(key, np.column_stack([grid, np.interp(grid, old[:, 0], old[:, 1])])))
    def ablation(arrays):
        a = arrays[key]
        arrays[key] = np.column_stack([grid] + [np.interp(grid, a[:, 0], a[:, j]) for j in range(1, a.shape[1])])
    rewrite_npz(directory / 'ablations.npz', ablation)


def alternate_null_predictions(directory):
    """A coherent no-added-value control; scientific acceptance remains unset."""
    def change(rows):
        lookup = {(row['name'], row['method']): row['predicted'] for row in rows}
        for row in rows:
            if row['method'].startswith('L23_'):
                row['predicted'] = lookup[(row['name'], row['method'].replace('L23_', 'L3_'))]
    rewrite_csv(directory / 'predictions.csv', change)
    with (directory / 'predictions.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    config = json.loads((directory / 'definitions.json').read_text())
    def metrics(summary):
        draws = {}
        for result in summary['metrics']:
            method = result['method']
            rr = [row for row in rows if row['method'] == method]
            y, p, g = [[row[key] for row in rr] for key in ['actual', 'predicted', 'composition_key']]
            cm, draw = VERIFIER.metric_bootstrap(y, p, g, summary['bootstrap_replicates'], config['random_seed'])
            result['balanced_accuracy'] = float(VERIFIER.balanced_accuracy_score(y, p))
            result['macro_f1'] = float(VERIFIER.f1_score(y, p, average='macro'))
            result['confusion_matrix'] = cm.tolist()
            result['ci025'], result['ci975'] = np.nanquantile(draw, [.025, .975]).tolist()
            draws[method] = draw
        for result in summary['paired_differences']:
            result['L23_minus_L3_balanced_accuracy'] = 0.
            result['ci025'] = result['ci975'] = 0.
    rewrite_json(directory / 'summary.json', metrics)


def induce_composition_leak(directory):
    def change(rows):
        groups = {}
        for row in rows:
            if row['method'] == 'L3_fwhm0' and row['split'] == '0' and row['role'] == 'test':
                groups.setdefault(row['composition_key'], []).append(row)
        chosen = next(group for group in groups.values() if len(group) > 1)
        chosen[0]['role'] = 'train'
    rewrite_csv(directory / 'partitions.csv', change)


def unjustified_exclusion(directory):
    chosen = {}
    def sites(rows):
        first = next(row for row in rows if row['included'] == '1')
        chosen.update(material=first['material'], element=first['element'], edge=first['edge'])
        for row in rows:
            if all(row[key] == value for key, value in chosen.items()):
                row['included'], row['reason'] = '0', 'arbitrary_omission'
    rewrite_csv(directory / 'sites.csv', sites)
    def coverage(rows):
        for row in rows:
            if all(row[key] == value for key, value in chosen.items()):
                row['included'], row['reason'] = '0', 'arbitrary_omission'
    rewrite_csv(directory / 'coverage.csv', coverage)


def run_suite(candidate, report_directory):
    report_directory.mkdir(parents=True, exist_ok=True)
    outcomes = []
    def check(name, question, directory, expected):
        start = time.monotonic()
        result = VERIFIER.verify(question, directory, BUNDLE / 'inputs')
        result['audit_case'] = name
        result['expected_integrity_pass'] = expected
        result['control_pass'] = result['integrity_pass'] == expected
        result['elapsed_seconds'] = round(time.monotonic() - start, 3)
        (report_directory / (name + '.json')).write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
        outcomes.append({key: result[key] for key in ['audit_case', 'question', 'integrity_pass', 'scientific_pass', 'expected_integrity_pass', 'control_pass', 'elapsed_seconds']} | {'error': result.get('error')})
        print(name, 'PASS' if result['control_pass'] else 'FAIL', result.get('error', ''), flush=True)
        return result
    for q in ['Q1', 'Q2', 'Q3']:
        result = check('positive_original_' + q, q, candidate / q, True)
        if not result['control_pass']:
            raise AssertionError('Original candidate failed: ' + str(result.get('error')))
    cases = [
        ('positive_alternate_response_grid', 'Q1', True, resample_response_grid),
        ('positive_coherent_null_increment', 'Q3', True, alternate_null_predictions),
        ('negative_missing_source_id', 'Q1', False, lambda d: rewrite_csv(d / 'sites.csv', lambda r: r.pop())),
        ('negative_duplicate_source_id', 'Q1', False, lambda d: rewrite_csv(d / 'sites.csv', lambda r: r.append(r[0].copy()))),
        ('negative_wrong_multiplicity', 'Q1', False, lambda d: rewrite_csv(d / 'sites.csv', lambda r: r[0].__setitem__('multiplicity', str(int(r[0]['multiplicity']) + 1)))),
        ('negative_unjustified_group_exclusion', 'Q1', False, unjustified_exclusion),
        ('negative_missing_response', 'Q1', False, lambda d: rewrite_npz(d / 'responses.npz', lambda a: a.pop(next(iter(a))))),
        ('negative_nan_response', 'Q1', False, lambda d: rewrite_npz(d / 'responses.npz', lambda a: a[next(iter(a))].__setitem__((0, 1), np.nan))),
        ('negative_wrong_population_average', 'Q1', False, lambda d: rewrite_npz(d / 'responses.npz', lambda a: a[next(iter(a))].__setitem__((0, 1), a[next(iter(a))][0, 1] * 1.5))),
        ('negative_wrong_distortion', 'Q1', False, lambda d: rewrite_csv(d / 'effects.csv', lambda r: r[0].__setitem__('relative_shape_L2', '0.932'))),
        ('negative_wrong_shape_label', 'Q2', False, lambda d: rewrite_csv(d / 'geometry.csv', lambda r: next(x for x in r if x['cn'] == '4' and x['geometry'] == 'other').__setitem__('geometry', 'tetrahedral'))),
        ('negative_missing_geometry', 'Q2', False, lambda d: rewrite_csv(d / 'geometry.csv', lambda r: r.pop())),
        ('negative_wrong_coordination_number', 'Q2', False, lambda d: rewrite_csv(d / 'geometry.csv', lambda r: r[0].__setitem__('cn', '97'))),
        ('negative_missing_descriptor', 'Q2', False, lambda d: rewrite_csv(d / 'descriptors.csv', lambda r: r.pop())),
        ('negative_wrong_edge_integral', 'Q2', False, lambda d: rewrite_csv(d / 'descriptors.csv', lambda r: r[0].__setitem__('area_L2_3_33', '999.5'))),
        ('negative_nan_descriptor', 'Q2', False, lambda d: rewrite_csv(d / 'descriptors.csv', lambda r: r[0].__setitem__('log_ratio', 'NaN'))),
        ('negative_wrong_association', 'Q2', False, lambda d: rewrite_csv(d / 'associations.csv', lambda r: r[0].__setitem__('tetra_minus_octa_log_ratio', '0.9'))),
        ('negative_wrong_association_interval', 'Q2', False, lambda d: rewrite_csv(d / 'associations.csv', lambda r: r[0].__setitem__('ci025', '-99'))),
        ('negative_missing_prediction', 'Q3', False, lambda d: rewrite_csv(d / 'predictions.csv', lambda r: r.pop())),
        ('negative_duplicate_prediction', 'Q3', False, lambda d: rewrite_csv(d / 'predictions.csv', lambda r: r.append(r[0].copy()))),
        ('negative_wrong_target', 'Q3', False, lambda d: rewrite_csv(d / 'predictions.csv', lambda r: r[0].__setitem__('actual', 'tetrahedral' if r[0]['actual'] == 'octahedral' else 'octahedral'))),
        ('negative_wrong_prediction_unreported', 'Q3', False, lambda d: rewrite_csv(d / 'predictions.csv', lambda r: r[0].__setitem__('predicted', 'tetrahedral' if r[0]['predicted'] == 'octahedral' else 'octahedral'))),
        ('negative_composition_leakage', 'Q3', False, induce_composition_leak),
        ('negative_missing_partition', 'Q3', False, lambda d: rewrite_csv(d / 'partitions.csv', lambda r: r.pop())),
        ('negative_duplicate_partition', 'Q3', False, lambda d: rewrite_csv(d / 'partitions.csv', lambda r: r.append(r[0].copy()))),
        ('negative_wrong_metric', 'Q3', False, lambda d: rewrite_json(d / 'summary.json', lambda s: s['metrics'][0].__setitem__('balanced_accuracy', .999))),
        ('negative_wrong_paired_interval', 'Q3', False, lambda d: rewrite_json(d / 'summary.json', lambda s: s['paired_differences'][0].__setitem__('ci025', -.99))),
    ]
    with tempfile.TemporaryDirectory(prefix='chen-verifier-controls-') as tmp:
        for name, question, expected, mutate in cases:
            directory = Path(tmp) / name
            mirrored_tree(candidate / question, directory)
            mutate(directory)
            check(name, question, directory, expected)
    summary = {'validation_profile': 'worked-example-declared-conventions',
               'controls': outcomes, 'all_controls_pass': all(o['control_pass'] for o in outcomes),
               'positive_controls': sum(o['expected_integrity_pass'] for o in outcomes),
               'negative_controls': sum(not o['expected_integrity_pass'] for o in outcomes),
               'scientific_pass': None,
               'limitations': ['Coherent null predictions are a synthetic consistency control, not a scientific submission or a demonstration that submitted training code generated them.',
                              'An integrity pass does not prove absence of feature/tuning leakage; independent clean replay and scientific review are separate.',
                              'Control sensitivity and successful replay do not empirically calibrate benchmark difficulty.']}
    (report_directory / 'audit_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--reports', type=Path, default=BUNDLE / 'verification/audit')
    parser.add_argument('--raw-source', type=Path)
    args = parser.parse_args()
    if args.raw_source:
        audit = source_audit(args.raw_source)
        path = args.reports.parent / 'source_packaging_audit.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(audit, indent=2) + '\n')
    result = run_suite(args.candidate.resolve(), args.reports.resolve())
    raise SystemExit(0 if result['all_controls_pass'] else 1)


if __name__ == '__main__':
    main()
