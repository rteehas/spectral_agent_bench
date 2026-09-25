#!/usr/bin/env python3
"""Audit the lean table interface against existing scientific model outputs.

These tests change output packaging, not fitted predictions. They do not claim
new scientific validation, and the numerical gate never executes source code.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'


def module():
    spec = importlib.util.spec_from_file_location('lean_verifier', DATA / 'workflows/verify.py')
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def lean(source, destination, question):
    destination.mkdir()
    shutil.copy(source / 'report.md', destination / 'report.md')
    # Source is deliberately outside code/: no directory convention is required.
    code = next((source / 'code').glob('*.py'))
    shutil.copy(code, destination / 'analysis.py')
    plot = next(p for p in source.rglob('*') if p.suffix in {'.png', '.svg', '.pdf'})
    shutil.copy(plot, destination / plot.name)
    runs = pd.DataFrame(json.loads((source / 'design.json').read_text())['runs'])
    runs['model'] = runs.condition.map(lambda value: 'Investigator model [' + value + ']')
    runs['fold'] = runs.comparison_id
    runs['property'] = runs.target.map({'coord': 'coordination', 'md': 'avg_nn_dists', 'bader': 'bader_charge'})
    columns = ['run_id', 'element', 'model', 'fold', 'property']
    for name in ['predictions', 'partitions']:
        frame = pd.read_csv(source / (name + '.csv')).merge(runs[columns], on='run_id', validate='many_to_one')
        frame = frame.drop(columns='run_id')
        if name == 'partitions':
            frame = frame[frame.role != 'excluded']
            frame['role'] = frame.role.replace({'train': 'training', 'validation': 'valid', 'test': 'testing'})
            frame = frame.rename(columns={'role': 'membership'})
        else:
            frame = frame.rename(columns={'y_pred': 'prediction'})
        if question in ['Q1', 'Q2', 'Q3']:
            frame = frame.drop(columns='property')
        frame.to_csv(destination / (name + '.csv'), index=False)


def edit(folder, table, mutator):
    path = folder / (table + '.csv')
    frame = pd.read_csv(path)
    result = mutator(frame)
    (frame if result is None else result).to_csv(path, index=False)


def audit(output):
    v = module()
    results = dict(schema='lean-numerical-interface-v3', scope='Output-interface and numerical-integrity audit, not a scientific pass',
                   verifier_sha256=v.digest(DATA / 'workflows/verify.py'),
                   audit_script_sha256=v.digest(Path(__file__)), references=[], lean_outputs=[], alternate_layouts=[], adversarial=[])
    with tempfile.TemporaryDirectory(prefix='torrisi-lean-audit-') as tmp:
        tmp = Path(tmp)
        lean_folders = {}
        for question in v.TARGETS:
            source = DATA / 'verification' / question
            original = v.verify(question, source, DATA / 'inputs')
            results['references'].append(dict(question=question, runs=original['run_count'], status=original['status']))
            folder = tmp / question
            lean(source, folder, question)
            lean_folders[question] = folder
            report = v.verify(question, folder, DATA / 'inputs')
            assert report['scientific_pass'] is None and report['status'] == 'scientific_review_required'
            assert original['run_count'] == report['run_count']
            before = sorted(tuple(r['metrics_recomputed'][key] for key in sorted(r['metrics_recomputed'])) for r in original['checks'])
            after = sorted(tuple(r['metrics_recomputed'][key] for key in sorted(r['metrics_recomputed'])) for r in report['checks'])
            for expected, actual in zip(before, after):
                np.testing.assert_allclose(expected, actual, rtol=1e-12, atol=1e-12)
            results['lean_outputs'].append(dict(question=question, runs=report['run_count'], numerical_integrity_pass=True,
                scientific_pass=None, design_and_metrics_files_absent=True, excluded_rows_omitted=True,
                code_outside_code_directory=True, property_column_omitted=question in ['Q1', 'Q2', 'Q3'],
                custom_model_names=True, prediction_and_membership_aliases=True, metrics_match_original=True))
        # A single experiment per element needs neither target nor run/model/fold identifiers.
        minimal = tmp / 'minimal_q2'
        shutil.copytree(lean_folders['Q2'], minimal)
        chosen = pd.read_csv(minimal / 'predictions.csv').groupby('element', sort=False).fold.first().to_dict()
        def minimize(frame):
            frame = frame[frame.apply(lambda row: row.fold == chosen[row.element], axis=1)]
            return frame.drop(columns=['model', 'fold'])
        edit(minimal, 'predictions', minimize); edit(minimal, 'partitions', minimize)
        simple = v.verify('Q2', minimal, DATA / 'inputs')
        assert simple['run_count'] == 8
        results['alternate_layouts'].append(dict(case='single_target_without_run_model_split_or_property_columns', accepted=True, runs=8))
        # Multiple models can share one partition table instead of duplicating its rows.
        shared = tmp / 'shared_q3'
        shutil.copytree(lean_folders['Q3'], shared)
        edit(shared, 'partitions', lambda frame: frame.drop(columns='model').drop_duplicates())
        shared_result = v.verify('Q3', shared, DATA / 'inputs')
        results['alternate_layouts'].append(dict(case='shared_partitions_across_arbitrarily_named_models', accepted=True, runs=shared_result['run_count']))
        # Actual original random-spectrum predictions remain valid numerically:
        # material overlap is a finding, not a hidden gate.
        spectrum = tmp / 'spectrum_q1'
        shutil.copytree(lean_folders['Q1'], spectrum)
        for name in ['predictions', 'partitions']:
            edit(spectrum, name, lambda frame: frame[frame.fold.str.contains('_spectrum_')])
        spectrum_report = v.verify('Q1', spectrum, DATA / 'inputs')
        overlap = sum(sum(r['material_id_overlap'].values()) for r in spectrum_report['checks'])
        missing = sum(r['active_rows_without_material_id'] for r in spectrum_report['checks'])
        assert overlap > 0
        results['alternate_layouts'].append(dict(case='spectrum_evaluation_with_material_overlap', accepted=True,
            runs=spectrum_report['run_count'], material_overlap_count_reported=overlap,
            active_rows_without_material_ids_reported=missing, scientific_pass=None))

        # Deliberately modify a training roster with one released unidentified
        # record. Arithmetic can accept this, while source rerun must still prove
        # any submitted code really used the roster. This is an integrity control,
        # not an assertion that the archived model trained on this added row.
        unidentified = tmp / 'unidentified_training_control'
        shutil.copytree(minimal, unidentified)
        def add_unidentified(frame):
            raw, _ = v.load_raw(DATA / 'inputs', 'Ti')
            used = set(frame.loc[frame.element == 'Ti', 'source_row'])
            row = next(i for i, r in raw.items() if not r['material_id'] and r['md'] is not None and i not in used)
            return pd.concat([frame, pd.DataFrame([dict(element='Ti', source_row=row, membership='training')])], ignore_index=True)
        edit(unidentified, 'partitions', add_unidentified)
        unidentified_result = v.verify('Q2', unidentified, DATA / 'inputs')
        assert sum(r['active_rows_without_material_id'] for r in unidentified_result['checks']) > 0
        results['alternate_layouts'].append(dict(case='unidentified_training_row_integrity_control', accepted=True,
            scientific_pass=None, note='Roster mutation proves missing IDs are not an arithmetic gate; independent code rerun is still required.'))

        # Unlabelled or other-class spectra can train an auxiliary representation;
        # the checker cannot require every training row to have a supervised label.
        for question, target, control_name in [('Q3', 'bader', 'unlabelled_auxiliary_training'), ('Q1', 'coord', 'other_class_auxiliary_training')]:
            auxiliary = tmp / control_name
            shutil.copytree(lean_folders[question], auxiliary)
            def add_auxiliary(frame):
                raw, _ = v.load_raw(DATA / 'inputs', 'Ti')
                first = frame[frame.element == 'Ti'].iloc[0]
                used = set(frame.loc[(frame.element == 'Ti') & (frame.model == first.model) & (frame.fold == first.fold), 'source_row'])
                row = next(i for i, r in raw.items() if i not in used and
                           ((target == 'bader' and r[target] is None) or (target == 'coord' and r[target] not in [4, 5, 6])))
                new = dict(first); new.update(source_row=row, membership='training')
                return pd.concat([frame, pd.DataFrame([new])], ignore_index=True)
            edit(auxiliary, 'partitions', add_auxiliary)
            auxiliary_result = v.verify(question, auxiliary, DATA / 'inputs')
            count = sum(sum(r['auxiliary_rows_without_in_scope_target'].values()) for r in auxiliary_result['checks'])
            assert count > 0
            results['alternate_layouts'].append(dict(case=control_name, accepted=True,
                auxiliary_target_unavailable_count_reported=count, scientific_pass=None,
                note='Roster integrity control; submitted learning procedure still requires independent code review.'))

        def reject(name, source, question, mutate):
            folder = tmp / ('bad_' + name)
            shutil.copytree(source, folder)
            mutate(folder)
            try:
                v.verify(question, folder, DATA / 'inputs')
            except (AssertionError, ValueError, KeyError) as exc:
                results['adversarial'].append(dict(case=name, rejected=True, message=str(exc)))
            else:
                raise AssertionError('Invalid output accepted: ' + name)

        reject('unknown_source_row', minimal, 'Q2', lambda folder: edit(folder, 'predictions', lambda f: f.assign(source_row=f.source_row.where(f.index != 0, 10**9))))
        reject('missing_test_prediction', minimal, 'Q2', lambda folder: edit(folder, 'predictions', lambda f: f.iloc[1:]))
        reject('duplicate_prediction', minimal, 'Q2', lambda folder: edit(folder, 'predictions', lambda f: pd.concat([f, f.iloc[[0]]], ignore_index=True)))
        def overlap_roles(folder):
            def mutate(f):
                duplicate = f[f.membership == 'training'].iloc[[0]].copy(); duplicate['membership'] = 'testing'
                return pd.concat([f, duplicate], ignore_index=True)
            edit(folder, 'partitions', mutate)
        reject('train_test_row_overlap', minimal, 'Q2', overlap_roles)
        def bad_metric(folder):
            pd.DataFrame([dict(element='Ti', metric='mae', value=-1)]).to_csv(folder / 'metrics.csv', index=False)
        reject('false_optional_metric', minimal, 'Q2', bad_metric)
        reject('false_optional_truth', minimal, 'Q2', lambda folder: edit(folder, 'predictions', lambda f: f.assign(y_true=-999)))
        def contradictory_design(folder):
            def mutate(f):
                f['element'] = f.run_id.str.split('_').str[0]
                f.loc[0, 'element'] = 'Cu' if f.loc[0, 'element'] != 'Cu' else 'Ti'
                return f
            edit(folder, 'predictions', mutate)
        reject('contradictory_optional_design_metadata', DATA / 'verification/Q2', 'Q2', contradictory_design)
        def false_material_claim(folder):
            edit(folder, 'predictions', lambda f: f.assign(generalization='identified_material'))
        reject('false_explicit_material_independence_claim', spectrum, 'Q1', false_material_claim)
        def false_pair(folder):
            edit(folder, 'predictions', lambda f: f.assign(comparison_id='all repetitions falsely paired'))
        reject('false_explicit_pairing_claim', lean_folders['Q3'], 'Q3', false_pair)
        def unlabelled_test(folder):
            pred = pd.read_csv(folder / 'predictions.csv')
            part = pd.read_csv(folder / 'partitions.csv')
            first = pred[pred.element == 'Ti'].iloc[0]
            raw, _ = v.load_raw(DATA / 'inputs', 'Ti')
            used = set(part.loc[(part.element == 'Ti') & (part.model == first.model) & (part.fold == first.fold), 'source_row'])
            new = next(i for i, r in raw.items() if r['bader'] is None and i not in used)
            for frame, name in [(pred, 'predictions'), (part, 'partitions')]:
                mask = (frame.element == 'Ti') & (frame.model == first.model) & (frame.fold == first.fold) & (frame.source_row == first.source_row)
                frame.loc[mask, 'source_row'] = new
                frame.to_csv(folder / (name + '.csv'), index=False)
        reject('unlabelled_scored_test_row', lean_folders['Q3'], 'Q3', unlabelled_test)
        reject('missing_element_investigation', minimal, 'Q2', lambda folder: [edit(folder, name, lambda f: f[f.element != 'Cu']) for name in ['predictions', 'partitions']])
        # A solver can use different legitimate partitions without claiming pairing.
        # Keeping only one model in one repetition and another in the other is
        # deliberately a scientific-review issue, not a table-integrity failure.
        unpaired = tmp / 'unpaired_q3'
        shutil.copytree(lean_folders['Q3'], unpaired)
        pred = pd.read_csv(unpaired / 'predictions.csv')
        allowed = set()
        for element, frame in pred.groupby('element'):
            folds = sorted(frame.fold.unique()); models = sorted(frame.model.unique())
            allowed.update((element, model, folds[i % len(folds)]) for i, model in enumerate(models))
        for name in ['predictions', 'partitions']:
            edit(unpaired, name, lambda f: f[f.apply(lambda r: (r.element, r.model, r.fold) in allowed, axis=1)])
        unpaired_result = v.verify('Q3', unpaired, DATA / 'inputs')
        results['alternate_layouts'].append(dict(case='different_evaluation_partitions_without_pairing_claim', accepted=True,
            scientific_pass=unpaired_result['scientific_pass'], status=unpaired_result['status']))
    results['result'] = 'All interface and numerical-integrity checks passed; scientific review remains required.'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + '\n')
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DATA / 'verification/lean_verification_v3.json')
    args = parser.parse_args()
    result = audit(args.output)
    print(json.dumps({key: len(result[key]) for key in ['references', 'lean_outputs', 'alternate_layouts', 'adversarial']}))
