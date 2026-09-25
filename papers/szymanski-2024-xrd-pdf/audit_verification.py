#!/usr/bin/env python3
"""Source projection audit plus positive and adversarial verifier controls.

The candidate workflow is not imported. This audit proves specific checks work;
it cannot certify scientific reasoning or absence of undeclared label leakage.
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


def csv_rows(path):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def audit_source(release):
    truth = v.source_truth(DATA)
    inventory, hashes, native_grids, seen = {}, set(), {}, set()
    for manifest in sorted((DATA / 'inputs').glob('*.json')):
        records = v.read_json(manifest)
        v.require(isinstance(records, list) and records and 'id' in records[0], f'Unexpected solver input JSON: {manifest}')
        archive = manifest.with_suffix('.npz')
        v.require(archive.is_file(), f'Missing raw archive: {archive}')
        with np.load(archive, allow_pickle=False) as arrays:
            v.require(set(arrays.files) - {'theta'} == {row['id'] for row in records}, f'Input archive IDs: {archive.name}')
            for row in records:
                source = truth[row['id']]
                v.require(row['id'] not in seen, f'Duplicate packaged spectrum: {row["id"]}')
                seen.add(row['id'])
                v.require('split' not in row and 'kind' not in row, f'Prescribed split or cardinality grouping in metadata: {row["id"]}')
                for field in ('phases', 'chemistry', 'replicate', 'major', 'minor', 'minor_weight_percent'):
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
                v.require(np.isfinite(raw).all() and (np.diff(raw[:, 0]) > 0).all(), f'Invalid source values/grid: {path}')
                grid = f'{len(raw)} points, {raw[0, 0]:.9f} to {raw[-1, 0]:.9f} degrees'
                native_grids[grid] = native_grids.get(grid, 0) + 1
        inventory[manifest.stem] = {'spectra': len(records), 'phase_labels': len({phase for row in records for phase in truth[row['id']]['phases']})}
    v.require(seen == set(truth) and len(seen) == 2930, 'Release audit did not cover all 2930 numeric spectra')
    v.require(not (DATA / 'inputs/protocol.json').exists() and not (DATA / 'inputs/output_schema.json').exists(), 'Removed instructional JSON files are still present')
    return {'passed': True, 'raw_spectra_compared_exactly': len(seen),
            'byte_unique_source_files': len(hashes), 'inventory': inventory, 'native_grids': native_grids,
            'label_anchor': 'Original release basenames; each packaged metadata label checked independently.',
            'data_anchor': 'Every float64 NPZ array equals np.loadtxt(original release file) exactly.',
            'limitations': ['Source labels establish nominal composition and identity, not independently measured experimental purity.',
                           'The released spectra are the benchmark data, not the complete historical training/test set.',
                           'Readable target metadata labels are for scoring; declared partitions alone cannot prove they were not used during inference.']}


def mutate_csv(path, transform):
    fields, rows = csv_rows(path)
    transform(rows)
    write_csv(path, fields, rows)


def change_prediction(folder, kind):
    def transform(rows):
        if kind == 'missing_prediction':
            rows.pop()
        elif kind == 'duplicate_prediction':
            rows.append(copy.deepcopy(rows[0]))
        elif kind == 'unknown_phase':
            rows[0]['predicted'] = '["InventedPhase_1"]'
        elif kind == 'duplicate_phase':
            label = json.loads(rows[0]['predicted'])[0]
            rows[0]['predicted'] = json.dumps([label, label])
        elif kind == 'unknown_fold':
            rows[0]['fold'] = 'undeclared-fold'
        elif kind == 'missing_representation':
            rows[:] = [row for row in rows if row['representation'] != 'PDF']
        elif kind == 'unknown_condition':
            rows[0]['condition'] = 'undeclared-condition'
    mutate_csv(folder / 'predictions.csv', transform)


def bad_partition(folder, kind):
    def transform(rows):
        test = next(row for row in rows if row['role'] == 'test')
        if kind == 'overlapping_partition':
            rows.append({**test, 'role': 'train'})
        elif kind == 'test_target_used_in_training':
            test['role'] = 'train'
        elif kind == 'unknown_split_id':
            rows[0]['id'] = 'invented-source'
    mutate_csv(folder / 'splits.csv', transform)


def bad_metric(folder, kind):
    def transform(rows):
        if kind == 'wrong_metric':
            rows[0]['value'] = str(float(rows[0]['value']) + .02)
        elif kind == 'wrong_metric_count':
            rows[0]['n'] = str(int(rows[0]['n']) + 1)
        elif kind == 'nonfinite_metric':
            rows[0]['value'] = 'nan'
        elif kind == 'duplicate_metric':
            rows.append(copy.deepcopy(rows[0]))
        elif kind == 'missing_metric':
            rows.pop(0)
    mutate_csv(folder / 'metrics.csv', transform)


def remove_suffixes(folder, suffixes):
    for filename in folder.rglob('*'):
        if filename.is_file() and filename.suffix.lower() in suffixes:
            filename.unlink()


def bad_evidence(folder):
    filename = next(folder.rglob('*.npz'))
    with np.load(filename, allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    name = next(key for key, array in arrays.items() if np.issubdtype(array.dtype, np.floating))
    arrays[name].flat[0] = np.nan
    np.savez_compressed(filename, **arrays)


def candidate_dir(root, question):
    nested = root / question / 'output'
    return nested if nested.is_dir() else root / question


def recompute_metrics(folder, question, truth):
    expected = v.independent_metrics(question, v.load_predictions(folder / 'predictions.csv'), truth)
    fields = ['chemistry', 'group', 'method', 'representation', 'condition', 'fold', 'metric', 'value', 'n']
    write_csv(folder / 'metrics.csv', fields, expected)


def alternate_predictions(folder, question, truth):
    """Deliberately different, internally consistent answer must be accepted.

This is synthetic test data for integrity checks, not a claimed scientific run.
"""
    def transform(rows):
        first = rows[0]
        chemistry = truth[first['id']]['chemistry']
        vocabulary = sorted({source['phases'][0] for source in truth.values() if source['kind'] == '1-Phase' and source['chemistry'] == chemistry})
        if question == 'Q4':
            vocabulary = sorted({phase.rsplit('_', 1)[0] for phase in vocabulary})
        observed = json.loads(first['predicted'])
        alternatives = [phase for phase in vocabulary if phase not in observed]
        first['predicted'] = json.dumps([alternatives[0]])
        for row in rows:
            row['method'] = 'alternative_' + row['method']
    mutate_csv(folder / 'predictions.csv', transform)
    recompute_metrics(folder, question, truth)


def alternate_split(folder, truth):
    fields, rows = csv_rows(folder / 'splits.csv')
    tested = next(row for row in rows if row['role'] == 'test')
    fitted = next(row for row in rows if row['role'] == 'train' and row['fold'] == tested['fold'] and truth[row['id']]['chemistry'] == truth[tested['id']]['chemistry'])
    old, new, fold = tested['id'], fitted['id'], tested['fold']
    tested['role'], fitted['role'] = 'train', 'test'
    write_csv(folder / 'splits.csv', fields, rows)
    def transform(predictions):
        for row in predictions:
            if row['id'] == old and row['fold'] == fold:
                row['id'] = new
    mutate_csv(folder / 'predictions.csv', transform)
    recompute_metrics(folder, 'Q1', truth)


def omit_csv_columns(path, omitted):
    fields, rows = csv_rows(path)
    kept = [field for field in fields if field not in omitted]
    write_csv(path, kept, [{field: row[field] for field in kept} for row in rows])


def minimal_submission(folder, question):
    """Keep an unambiguous comparison and omit evaluator-only bookkeeping."""
    fields, rows = csv_rows(folder / 'predictions.csv')
    fold = rows[0]['fold']
    rows = [row for row in rows if row['fold'] == fold]
    if question == 'Q3':
        # Multiple PDF interval names genuinely need identifiers. Select one
        # interval plus XRD before omitting method, preserving each condition.
        methods = {representation: next(row['method'] for row in rows if row['representation'] == representation)
                   for representation in ('XRD', 'PDF')}
        rows = [row for row in rows if row['representation'] in methods and row['method'] == methods[row['representation']]]
    else:
        method = rows[0]['method']
        rows = [row for row in rows if row['method'] == method]
    write_csv(folder / 'predictions.csv', fields, rows)
    mutate_csv(folder / 'splits.csv', lambda records: records.__setitem__(slice(None), [row for row in records if row['fold'] == fold]))
    omitted = {'method', 'fold'} | ({'condition'} if question != 'Q3' else set())
    omit_csv_columns(folder / 'predictions.csv', omitted)
    omit_csv_columns(folder / 'splits.csv', {'fold'})
    (folder / 'metrics.csv').unlink()


def mixed_identifier(folder, kind):
    if kind == 'blank_prediction_method':
        mutate_csv(folder / 'predictions.csv', lambda rows: rows[0].__setitem__('method', ''))
    elif kind == 'blank_prediction_fold':
        mutate_csv(folder / 'predictions.csv', lambda rows: rows[0].__setitem__('fold', ''))
    elif kind == 'blank_prediction_condition':
        mutate_csv(folder / 'predictions.csv', lambda rows: rows[0].__setitem__('condition', ''))
    elif kind == 'blank_split_fold':
        mutate_csv(folder / 'splits.csv', lambda rows: rows[0].__setitem__('fold', ''))
    elif kind == 'fold_omitted_in_predictions_only':
        omit_csv_columns(folder / 'predictions.csv', {'fold'})
    elif kind == 'fold_omitted_in_splits_only':
        omit_csv_columns(folder / 'splits.csv', {'fold'})
    elif kind == 'ambiguous_method_omission':
        omit_csv_columns(folder / 'predictions.csv', {'method'})
    elif kind == 'missing_q3_condition_column':
        omit_csv_columns(folder / 'predictions.csv', {'condition'})


def compact_check(result):
    return {key: result[key] for key in ('question', 'integrity_passed', 'scientific_correctness', 'reference_predictions_compared', 'prediction_rows', 'core_metric_rows_independently_recomputed', 'optional_metric_table_status')}


def audit_controls(candidate_runs):
    report = []
    truth = v.source_truth(DATA)
    with tempfile.TemporaryDirectory(prefix='szymanski-verifier-audit-') as temporary:
        base = Path(temporary)
        for question in ('Q1', 'Q2', 'Q3', 'Q4'):
            original = candidate_dir(candidate_runs, question)
            positive = compact_check(v.verify(question, original))
            controls = {'missing_report': lambda folder: (folder / 'report.md').unlink(),
                        'missing_figure': lambda folder: remove_suffixes(folder, {'.png', '.svg', '.pdf'}),
                        'missing_code': lambda folder: remove_suffixes(folder, {'.py', '.ipynb'})}
            for name in ('missing_prediction', 'duplicate_prediction', 'unknown_phase', 'duplicate_phase', 'unknown_fold', 'missing_representation', 'unknown_condition'):
                controls[name] = lambda folder, kind=name: change_prediction(folder, kind)
            for name in ('overlapping_partition', 'test_target_used_in_training', 'unknown_split_id'):
                controls[name] = lambda folder, kind=name: bad_partition(folder, kind)
            for name in ('wrong_metric', 'wrong_metric_count', 'nonfinite_metric', 'duplicate_metric', 'missing_metric'):
                controls[name] = lambda folder, kind=name: bad_metric(folder, kind)
            for name in ('blank_prediction_method', 'blank_prediction_fold', 'blank_prediction_condition', 'blank_split_fold', 'fold_omitted_in_predictions_only', 'fold_omitted_in_splits_only'):
                controls[name] = lambda folder, kind=name: mixed_identifier(folder, kind)
            if question in {'Q1', 'Q3'}:
                controls['ambiguous_method_omission'] = lambda folder: mixed_identifier(folder, 'ambiguous_method_omission')
                controls['wrong_optional_micro_f1'] = lambda folder: mutate_csv(folder / 'metrics.csv', lambda rows: next(row for row in rows if row['metric'] == 'micro_f1').__setitem__('value', '.123456789'))
            if question == 'Q3':
                controls['missing_q3_condition_column'] = lambda folder: mixed_identifier(folder, 'missing_q3_condition_column')
                controls['nonfinite_evidence'] = bad_evidence
                controls['missing_numeric_evidence'] = lambda folder: remove_suffixes(folder, {'.npz'})
                controls['missing_background_condition'] = lambda folder: mutate_csv(folder / 'conditions.csv', lambda rows: rows.__setitem__(slice(None), [row for row in rows if row['artifact'] != 'background']))
                controls['duplicate_condition'] = lambda folder: mutate_csv(folder / 'conditions.csv', lambda rows: rows.append(copy.deepcopy(rows[0])))
            rejected = []
            for name, mutate in controls.items():
                wrong = base / question / name
                shutil.copytree(original, wrong)
                mutate(wrong)
                try:
                    v.verify(question, wrong)
                except (AssertionError, ValueError, FileNotFoundError, KeyError) as error:
                    rejected.append({'control': name, 'rejected': True, 'reason': next((line for line in str(error).splitlines() if line.strip()), type(error).__name__)[:240]})
                else:
                    raise AssertionError(f'{question} accepted invalid integrity control: {name}')
            alternatives = []
            minimal = base / question / 'minimal_predictions_and_splits_no_metrics'
            shutil.copytree(original, minimal)
            minimal_submission(minimal, question)
            checked = v.verify(question, minimal)
            v.require(checked['optional_metric_table_status'] == 'absent_recomputed_only', 'Absent metrics status differs')
            alternatives.append({'control': 'minimal_predictions_and_splits_omit_optional_identifiers_and_metrics', **compact_check(checked)})
            supplemental = base / question / 'alternative_metrics_schema'
            shutil.copytree(minimal, supplemental)
            write_csv(supplemental / 'metrics.csv', ['analysis', 'estimate'], [{'analysis': 'custom_summary', 'estimate': '.123'}])
            checked = v.verify(question, supplemental)
            v.require(checked['optional_metric_table_status'] == 'supplemental_table_requires_review' and not checked['optional_metric_table_checked'], 'Supplemental metrics falsely marked checked')
            alternatives.append({'control': 'alternative_optional_metric_table_is_supplemental_not_hidden_schema_failure', **compact_check(checked)})
            if question != 'Q3':
                renamed = base / question / 'arbitrary_consistent_condition_name'
                shutil.copytree(original, renamed)
                mutate_csv(renamed / 'predictions.csv', lambda rows: [row.__setitem__('condition', 'native_specimens') for row in rows])
                recompute_metrics(renamed, question, truth)
                alternatives.append({'control': 'condition_name_is_not_a_prescribed_constant', **compact_check(v.verify(question, renamed))})
            if question in {'Q1', 'Q3'}:
                minimal = base / question / 'minimal_requested_metrics'
                shutil.copytree(original, minimal)
                mutate_csv(minimal / 'metrics.csv', lambda rows: rows.__setitem__(slice(None), [row for row in rows if row['metric'] != 'micro_f1']))
                alternatives.append({'control': 'optional_redundant_micro_f1_omitted', **compact_check(v.verify(question, minimal))})
            changed = base / question / 'alternate_consistent_predictions'
            shutil.copytree(original, changed)
            alternate_predictions(changed, question, truth)
            alternatives.append({'control': 'different_method_and_predictions_with_correctly_recomputed_metrics', **compact_check(v.verify(question, changed))})
            if question == 'Q3':
                changed = base / question / 'finite_but_scientifically_unsupported_evidence'
                shutil.copytree(original, changed)
                filename = changed / 'evidence.npz'
                with np.load(filename, allow_pickle=False) as archive:
                    arrays = {key: archive[key].copy() for key in archive.files}
                arrays['perturbed_pdf'] *= 7
                np.savez_compressed(filename, **arrays)
                alternatives.append({'control': 'finite_but_scientifically_unsupported_transform_is_outside_automatic_scope',
                    'review_required': 'The saved transform is deliberately corrupted. Numerical presence checks cannot certify its physical validity; execution/code/evidence audit must reject the claimed transform.',
                    **compact_check(v.verify(question, changed))})
            if question == 'Q1':
                changed = base / question / 'alternate_disjoint_split'
                shutil.copytree(original, changed)
                alternate_split(changed, truth)
                alternatives.append({'control': 'different_disjoint_solver_chosen_split', **compact_check(v.verify(question, changed))})
            report.append({'question': question, 'candidate_integrity_control': positive,
                           'synthetic_alternative_integrity_controls': alternatives,
                           'invalid_integrity_controls': rejected})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--candidate-runs', type=Path)
    args = parser.parse_args()
    report = {'source_audit': audit_source(args.release), 'verifier_sha256': sha(DATA / 'workflows/verify.py')}
    if args.candidate_runs:
        report['verification_controls'] = audit_controls(args.candidate_runs)
        report['invalid_controls_rejected'] = sum(len(row['invalid_integrity_controls']) for row in report['verification_controls'])
        report['alternative_integrity_controls_accepted'] = sum(len(row['synthetic_alternative_integrity_controls']) for row in report['verification_controls'])
    report['scope'] = 'Source projection and automated integrity checks only. Alternative controls are synthetic verifier tests, not scientific results. Mandatory execution/code audit and scored scientific review are separate.'
    target = DATA / 'verification/verification_audit.json'
    write_json(target, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
