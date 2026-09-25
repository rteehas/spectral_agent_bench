#!/usr/bin/env python3
"""Independently reconstruct Q1/Q2 scientific evidence from source rows.

This audits the executed illustrative design, not alternative solver methods.
No candidate or numerical-verifier helper is imported. It recomputes the
freeform evidence which the method-independent core verifier does not check.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
LABELS = {'coord': 'coordination', 'md': 'avg_nn_dists'}


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual, expected):
    np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=1e-9)


def metrics(truth, prediction, target):
    if target == 'coord':
        values = {}
        for label in [4, 5, 6]:
            tp = np.count_nonzero((truth == label) & (prediction == label))
            denominator = np.count_nonzero(truth == label) + np.count_nonzero(prediction == label)
            values[f'f1_{label}'] = 2 * tp / denominator if denominator else 0.
        values['macro_f1'] = sum(values.values()) / 3
        values['accuracy'] = np.mean(truth == prediction)
        return values
    residual = prediction - truth
    return {'mae': np.mean(abs(residual)),
            'r2': 1 - np.sum(residual ** 2) / np.sum((truth - truth.mean()) ** 2)}


def gain(truth, first, second, target):
    if target != 'coord':
        return np.mean(abs(first - truth)) - np.mean(abs(second - truth))
    return metrics(truth, second, target)['macro_f1'] - metrics(truth, first, target)['macro_f1']


def interval(truth, first, second, groups, target):
    """Independently reproduce the documented conditional group bootstrap."""
    group_names = sorted(set(groups))
    membership = {name: np.where(groups == name)[0] for name in group_names}
    rng = np.random.default_rng(101)
    gains = []
    for _ in range(250):
        sampled_names = [group_names[i] for i in rng.integers(0, len(group_names), len(group_names))]
        chosen = np.concatenate([membership[name] for name in sampled_names])
        gains.append(gain(truth[chosen], first[chosen], second[chosen], target))
    return np.quantile(gains, [.025, .975])


def audit(question, data=DATA):
    directory = data / 'verification' / question
    design = read_json(directory / 'design.json')
    evidence = read_json(directory / 'evidence.json')
    report = (directory / 'report.md').read_text()
    predictions = pd.read_csv(directory / 'predictions.csv')
    partitions = pd.read_csv(directory / 'partitions.csv')
    declared_metrics = pd.read_csv(directory / 'metrics.csv')
    sources = {}
    for element in {run['element'] for run in design['runs']}:
        with gzip.open(data / 'inputs' / f'{element}.jsonl.gz', 'rt') as stream:
            sources[element] = [json.loads(line) for line in stream]
    baselines = {row['run_id']: row for row in evidence['baselines']}
    details = {}
    coverage_by_element = {row['element']: row for row in evidence['coverage']}
    eligibility_by_element = {}
    for element, rows in sources.items():
        target = 'coord' if question == 'Q1' else 'md'
        y = np.array([np.nan if r[LABELS[target]] is None else r[LABELS[target]] for r in rows])
        identified = np.array([r['metadata'].get('id') is not None for r in rows])
        spectra = np.array([r['mu'] for r in rows])
        energy = np.array([r['E'] for r in rows])
        eligible = np.isfinite(spectra).all(1) & np.isfinite(energy).all(1) & (spectra.max(1) > 0) & np.isfinite(y)
        eligible &= np.isin(y, [4, 5, 6]) if target == 'coord' else y > 0
        eligibility_by_element[element] = set(np.where(eligible & identified)[0])
        coverage = coverage_by_element[element]
        assert coverage['source_records'] == len(rows)
        assert coverage['valid_target_records'] == np.count_nonzero(eligible)
        assert coverage['identified_valid_records'] == len(eligibility_by_element[element])
        assert coverage['identified_materials'] == len({rows[i]['metadata']['id'] for i in eligibility_by_element[element]})
        close(coverage['identified_target_mean'], y[eligible & identified].mean())
        close(coverage['unidentified_target_mean'], y[eligible & ~identified].mean())
        for origin, declared in coverage['origins'].items():
            members = [i for i, row in enumerate(rows) if row['metadata'].get('origin') == origin]
            assert declared['records'] == len(members)
            assert declared['identified'] == sum(identified[i] for i in members)
    if question == 'Q1':
        counts = pd.read_csv(directory / 'class_counts.csv')
        confusion = pd.read_csv(directory / 'confusion.csv')
    else:
        regimes = pd.read_csv(directory / 'regimes.csv')
    count_checks = confusion_checks = tail_checks = 0
    for run in design['runs']:
        name, element, target = run['run_id'], run['element'], run['target']
        rows = sources[element]
        y = np.array([np.nan if r[LABELS[target]] is None else r[LABELS[target]] for r in rows])
        groups = np.array([str(r['metadata']['id']) if r['metadata'].get('id') is not None else '' for r in rows])
        part = partitions[partitions.run_id == name]
        role = dict(zip(part.source_row, part.role))
        assert set(role) == set(range(len(rows)))
        assert {i for i in role if role[i] != 'excluded'} == eligibility_by_element[element]
        tr = np.array([i for i in role if role[i] == 'train'])
        va = np.array([i for i in role if role[i] == 'validation'])
        prediction = predictions[predictions.run_id == name]
        te = prediction.source_row.to_numpy()
        pred = prediction.y_pred.to_numpy()
        assert set(te) == {i for i in role if role[i] == 'test'}
        assert all(groups[i] for i in list(tr) + list(va) + list(te))
        if run['generalization'] == 'identified_material':
            assert not (set(groups[tr]) & set(groups[te]))
            assert not (set(groups[tr]) & set(groups[va]))
            assert not (set(groups[va]) & set(groups[te]))
        recomputed = metrics(y[te], pred, target)
        declared = declared_metrics[declared_metrics.run_id == name].set_index('metric').value
        for metric, value in recomputed.items():
            close(declared[metric], value)
        constant = min([4, 5, 6], key=lambda label: (-np.count_nonzero(y[tr] == label), label)) if target == 'coord' else np.median(y[tr])
        close(baselines[name]['training_constant'], constant)
        for metric, value in metrics(y[te], np.full(len(te), constant), target).items():
            close(baselines[name]['metrics'][metric], value)
        if question == 'Q1':
            for phase, indices in [('train', tr), ('validation', va), ('test', te)]:
                for label in [4, 5, 6]:
                    row = counts[(counts.run_id == name) & (counts.role == phase) & (counts.coordination == label)]
                    assert len(row) == 1 and int(row.iloc[0]['count']) == np.count_nonzero(y[indices] == label)
                    count_checks += 1
            for truth_label in [4, 5, 6]:
                for predicted_label in [4, 5, 6]:
                    row = confusion[(confusion.run_id == name) & (confusion.true_coordination == truth_label) & (confusion.predicted_coordination == predicted_label)]
                    assert len(row) == 1 and int(row.iloc[0]['count']) == np.count_nonzero((y[te] == truth_label) & (pred == predicted_label))
                    confusion_checks += 1
        else:
            low, high = np.quantile(y[tr], [.1, .9])
            masks = {'all': np.ones(len(te), dtype=bool), 'short': y[te] < low,
                     'middle': (y[te] >= low) & (y[te] <= high), 'long': y[te] > high}
            for regime, mask in masks.items():
                if not np.any(mask):
                    continue
                row = regimes[(regimes.run_id == name) & (regimes.regime == regime)]
                assert len(row) == 1
                row = row.iloc[0]
                truth, prediction = y[te][mask], pred[mask]
                residual = prediction - truth
                close(row.low_cutoff, low)
                close(row.high_cutoff, high)
                assert row.records == len(truth)
                assert row.materials == len(set(groups[te][mask]))
                close(row.mae, np.mean(abs(residual)))
                close(row.bias, np.mean(residual))
                close(row.baseline_mae, np.mean(abs(truth - constant)))
                expected_interval = interval(truth, np.full(len(truth), constant), prediction, groups[te][mask], target)
                close([row.baseline_gain_low, row.baseline_gain_high], expected_interval)
                tail_checks += 1
        details[name] = dict(truth=y[te], prediction=pred, test=te, groups=groups[te], train=tr,
                             validation=va, all_labels=y, metrics=recomputed, run=run)

    main = [d for d in details.values() if d['run']['generalization'] == 'identified_material']
    score_key = 'macro_f1' if question == 'Q1' else 'mae'
    for element in sources:
        for condition in {d['run']['condition'] for d in main}:
            values = [d['metrics'][score_key] for d in main if d['run']['element'] == element and d['run']['condition'] == condition]
            target = 'coord' if question == 'Q1' else 'md'
            expected = f'| {element} / {target} | {condition} | {np.mean(values):.4f} | {min(values):.4f}–{max(values):.4f} |'
            assert expected in report
    for condition in {d['run']['condition'] for d in main}:
        selected = [d for d in main if d['run']['condition'] == condition]
        gains = [d['metrics'][score_key] - baselines[d['run']['run_id']]['metrics'][score_key] for d in selected]
        if question == 'Q2':
            gains = [-v for v in gains]
        target = 'coord' if question == 'Q1' else 'md'
        expected = f'- {target}/{condition}: {np.mean(gains):.4f} mean gain, range {min(gains):.4f}–{max(gains):.4f}'
        assert expected in report

    interval_checks = 0
    if question == 'Q1':
        comparison_table = pd.read_csv(directory / 'comparisons.csv').set_index('comparison_id')
        for comparison in evidence['comparisons']:
            runs = [run for run in design['runs'] if run['comparison_id'] == comparison['comparison_id']]
            first = details[next(r['run_id'] for r in runs if r['condition'] == comparison['first'])]
            second = details[next(r['run_id'] for r in runs if r['condition'] == comparison['second'])]
            assert np.array_equal(first['test'], second['test'])
            group = first['groups'] if comparison['generalization'] == 'identified_material' else first['test'].astype(str)
            observed = gain(first['truth'], first['prediction'], second['prediction'], 'coord')
            bounds = interval(first['truth'], first['prediction'], second['prediction'], group, 'coord')
            close(comparison['gain'], observed)
            close([comparison['low'], comparison['high']], bounds)
            close(comparison['bootstrap_units'], len(set(group)))
            table_row = comparison_table.loc[comparison['comparison_id']]
            close([table_row.gain, table_row.low, table_row.high], [observed, *bounds])
            interval_checks += 1
        material_comparisons = [c for c in evidence['comparisons'] if c['generalization'] == 'identified_material']
        for element in sources:
            comparisons = [c for c in material_comparisons if c['element'] == element]
            intervals = '; '.join(f'[{c["low"]:.4f}, {c["high"]:.4f}]' for c in comparisons)
            expected = f'| {element} / coord | treated vs untreated | {np.mean([c["gain"] for c in comparisons]):.4f} | {intervals} |'
            assert expected in report
        positive = sum(c['gain'] > 0 for c in material_comparisons)
        supported = sum(c['low'] > 0 for c in material_comparisons)
        assert f'positive macro-F1 gain in {positive}/{len(material_comparisons)}' in report
        assert f'only {supported} conditional intervals were wholly above zero' in report
        for element in sources:
            model_rows = [d for d in details.values() if d['run']['element'] == element and d['run']['condition'] == 'untreated']
            material_rows = [d for d in model_rows if d['run']['generalization'] == 'identified_material']
            spectrum_rows = [d for d in model_rows if d['run']['generalization'] == 'spectrum']
            f1 = [np.mean([d['metrics'][f'f1_{label}'] for d in material_rows]) for label in [4, 5, 6]]
            spectrum_score = np.mean([d['metrics']['macro_f1'] for d in spectrum_rows])
            material_score = np.mean([d['metrics']['macro_f1'] for d in material_rows])
            expected = f'- {element}: untreated class F1(4,5,6)={f1[0]:.3f}, {f1[1]:.3f}, {f1[2]:.3f}; record versus material macro-F1={spectrum_score:.3f} versus {material_score:.3f}.'
            assert expected in report
        report_facts = {'positive_imbalance_gains': positive, 'material_comparisons': len(material_comparisons), 'intervals_entirely_positive': supported}
    else:
        assert 'training-distance10th/90thpercentiles' in ''.join(report.split())
        assert 'it is not a deployable confidence detector' in report
        report_facts = {'regression_regimes': tail_checks}
        assert len(evidence['regimes']) == len(regimes)
        for row in evidence['regimes']:
            csv_row = regimes[(regimes.run_id == row['run_id']) & (regimes.regime == row['regime'])].iloc[0]
            for key, value in row.items():
                if isinstance(value, (int, float)):
                    close(csv_row[key], value)
        for element in sources:
            for regime in ['short', 'middle', 'long']:
                subset = regimes[(regimes.run_id.str.startswith(element + '_')) & (regimes.regime == regime)]
                assert f'{regime} MAE={subset.mae.mean():.4f} Å, bias={subset.bias.mean():+.4f} Å' in report

    # One independently reconstructed fit per task checks prediction provenance
    # without pretending that every model was independently rerun in this audit.
    selected = next(r for r in design['runs'] if r['generalization'] == 'identified_material')
    d = details[selected['run_id']]
    source = sources[selected['element']]
    X = np.array([row['mu'] for row in source])
    cls = ExtraTreesClassifier if question == 'Q1' else ExtraTreesRegressor
    candidates = []
    for leaf in [1, 5]:
        options = dict(n_estimators=80, min_samples_leaf=leaf, max_features=.8, random_state=selected['fit_seed'], n_jobs=2)
        if question == 'Q1':
            options['class_weight'] = 'balanced' if selected['condition'] == 'treated' else None
        estimator = cls(**options).fit(X[d['train']], d['all_labels'][d['train']])
        scores = metrics(d['all_labels'][d['validation']], estimator.predict(X[d['validation']]), selected['target'])
        val_loss = 1 - scores['macro_f1'] if question == 'Q1' else scores['mae']
        candidates.append((val_loss, leaf, estimator))
        recorded = next(v for v in selected['validation_trials'] if v['min_samples_leaf'] == leaf)
        close(recorded['validation_loss'], val_loss)
    best = min(candidates, key=lambda x: x[0])
    assert best[1] == selected['selected_min_samples_leaf']
    independent_prediction = best[2].predict(X[d['test']])
    close(independent_prediction, d['prediction'])

    artifact_hashes = {str(p.relative_to(ROOT)): digest(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    return dict(question=question, verdict='pass_with_stated_limits', runs_audited=len(design['runs']),
                coverage_source_composition_and_eligibility_reconstructed=True,
                all_core_metrics_and_training_only_baselines_reconstructed=True,
                class_support_cells_reconstructed=count_checks, confusion_cells_reconstructed=confusion_checks,
                paired_bootstrap_intervals_reconstructed=interval_checks, regime_rows_and_intervals_reconstructed=tail_checks,
                report_facts=report_facts,
                independent_model_refit={'run_id': selected['run_id'], 'validation_trials_repeated': [1, 5],
                                         'chosen_leaf_matches': True, 'all_test_predictions_match': True,
                                         'max_absolute_difference': float(np.max(abs(independent_prediction - d['prediction'])))},
                artifact_sha256=artifact_hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--questions', nargs='+', choices=['Q1', 'Q2'], default=['Q1', 'Q2'])
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    results = [audit(q, args.data) for q in args.questions]
    report = dict(review_scope='Independent source-code review, raw-data reconstruction of Q1/Q2 scientific evidence, and one independently reconstructed selected fit per task. This is not a rerun of every forest.',
                  verdict='pass_with_stated_limits', questions=results,
                  reviewed_candidate_sha256=digest(args.data / 'workflows/candidate.py'),
                  audit_source_sha256=digest(Path(__file__)),
                  scientific_findings=[
                      'Finite-spectrum and valid-target eligibility precedes fitting. IDs define material partitions; validation selects leaf size and test outcomes do not choose it.',
                      'Training-only prevalence/median baselines, class weighting and tail thresholds are correct. All audited freeform evidence is reconstructed from the released labels and submitted predictions.',
                      'Q1 record holdouts use the same identified cohort but can share materials with training; the report explicitly limits their interpretation.',
                      'Q2 signed residuals use prediction minus truth; train-defined short/long regimes are retrospective diagnostics, not deployment-time uncertainty estimates.',
                      'The reports disclose source-confounded provenance coverage, structural aliases, conditional bootstrap uncertainty and overlapping repeated holdouts.'
                  ],
                  limitations=[
                      'These methods are one illustrative design, not benchmark requirements or exact numerical targets.',
                      'Only one selected fit per task is independently reconstructed here; complete artifact verification relies also on source inspection and independent evidence reconstruction.',
                      'Two held-out partitions and conditional material bootstraps give limited sensitivity evidence. They cannot establish population-wide or experimental reliability.',
                      'Recorded material identifiers cannot resolve structural near-duplicates or unknown-ID feff records.'
                  ])
    output = args.output or args.data / 'verification/scientific_review_q1_q2.json'
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'verdict': report['verdict'], 'questions': [{k: v for k, v in q.items() if k != 'artifact_sha256'} for q in results]}, indent=2))


if __name__ == '__main__':
    main()
