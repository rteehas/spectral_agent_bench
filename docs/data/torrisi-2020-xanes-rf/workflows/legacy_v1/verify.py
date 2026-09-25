#!/usr/bin/env python3
"""Evaluator-only checks, backed by independent raw/release preprocessing anchors.

The modern reference is a reproducibility target, not a claim of bitwise
agreement with the 2020 forests. Numeric screening does not grade scientific
interpretation, prove absence of leakage, or establish unseen-material accuracy.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score

ELEMENTS = ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']
SEEDS = [42, 43, 44]
DEFAULT_REFERENCE = Path(__file__).resolve().parents[1] / 'verification'


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    return json.loads(path.read_text())


def close(actual, expected, path, atol=1e-9):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), path + ': object keys differ')
        for key in expected:
            close(actual[key], expected[key], path + '.' + key, atol)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), path + ': list length differs')
        for i, value in enumerate(expected):
            close(actual[i], value, f'{path}[{i}]', atol)
    elif expected is None or isinstance(expected, (bool, str)):
        require(actual == expected, path + ': value differs')
    else:
        require(isinstance(actual, (int, float)) and not isinstance(actual, bool) and np.isfinite(actual),
                path + ': value must be finite')
        require(abs(actual - expected) <= atol, path + ': numerical mismatch')


def configurations(question):
    if question == 'Q1':
        configs = [('coord', 'pointwise', 'feff', b) for b in [False, True]]
    elif question == 'Q2':
        configs = [('md', 'pointwise', 'feff', False)]
    elif question == 'Q3':
        configs = [('bader', r, 'feff', False) for r in ['pointwise', 'peak']]
    elif question == 'Q4':
        configs = [(t, r, 'feff', t == 'coord') for t in ['coord', 'md', 'bader']
                   for r in ['pointwise', 'poly']]
    elif question == 'Q5':
        configs = [(t, r, n, t == 'coord') for t in ['coord', 'md']
                   for r in ['pointwise', 'poly'] for n in ['feff', 'max']]
    else:
        raise AssertionError('Unknown question')
    return {(el,) + config for el in ELEMENTS for config in configs}


def expected_metadata(energy, representation):
    if representation == 'pointwise':
        return [dict(index=i, label=f'mu_{i}', degree=-1, parts=0, chunk=i,
                     energy_lo=e, energy_hi=e) for i, e in enumerate(energy)]
    peak = dict(label='peak', degree=-1, parts=0, chunk=0,
                energy_lo=energy[0], energy_hi=energy[-1])
    features = []
    if representation == 'poly':
        for n in [4, 5, 10, 20]:
            width = 100 // n
            for chunk in range(n):
                for degree in range(4):
                    features.append(dict(label=f'loc:all,deg:3,fraction_size:{n},chunk:{chunk},coef:{degree}',
                                         degree=degree, parts=n, chunk=chunk,
                                         energy_lo=energy[chunk*width], energy_hi=energy[(chunk+1)*width-1]))
        features.sort(key=lambda d: d['label'])
    features.append(peak)
    return [dict(index=i, **f) for i, f in enumerate(features)]


def recompute_metrics(target, truth, pred, train):
    if target == 'coord':
        require(np.isin(pred, [4, 5, 6]).all(), 'Coordination predictions must be class labels')
        f1 = f1_score(truth, pred, labels=[4, 5, 6], average=None, zero_division=0)
        return dict(accuracy=float(accuracy_score(truth, pred)), macro_f1=float(f1.mean()),
                    **{f'f1_{k}': float(v) for k, v in zip([4, 5, 6], f1)})
    metrics = dict(r2=float(r2_score(truth, pred)), mae=float(mean_absolute_error(truth, pred)))
    for name, mask in [('low', truth <= np.quantile(train, .1)),
                       ('high', truth >= np.quantile(train, .9))]:
        error = pred[mask] - truth[mask]
        metrics[name + '_count'] = int(mask.sum())
        metrics[name + '_mae'] = float(np.abs(error).mean()) if len(error) else None
        metrics[name + '_bias'] = float(error.mean()) if len(error) else None
    return metrics


def check_derived_tables(question, output, models, predictions, importances, metadata):
    """Recompute the scientific comparisons from predictions/importance, not reference tables."""
    def table(name, expected, keys):
        frame = pd.read_csv(output / name)
        desired = pd.DataFrame(expected)
        require(set(frame.columns) == set(desired.columns), name + ': columns differ')
        require(len(frame) == len(desired) and not frame.duplicated(keys).any(), name + ': row coverage differs')
        frame = frame.set_index(keys).sort_index()
        desired = desired.set_index(keys).sort_index()
        require(frame.index.equals(desired.index), name + ': identities differ')
        for column in desired:
            if pd.api.types.is_numeric_dtype(desired[column]):
                values = frame[column].to_numpy(dtype=float)
                require(np.isfinite(values).all(), name + ': nonfinite values')
                np.testing.assert_allclose(values, desired[column], rtol=0, atol=1e-8,
                                           err_msg=name + '.' + column)
            else:
                require(frame[column].equals(desired[column]), name + ': string labels differ')
    mean_importance = {}
    ranked, families, comparisons = [], [], []
    for model in models:
        values = importances[importances.model_id == model['id']].groupby('feature_index').importance.mean().sort_index().to_numpy()
        mean_importance[model['id']] = values
        if model['representation'] != 'poly':
            continue
        mapping = metadata[model['element'] + '_poly']
        order = np.argsort(-values)
        for rank, index in enumerate(order[:12], 1):
            ranked.append(dict(model_id=model['id'], rank=rank, importance=float(values[index]), **mapping[index]))
        family = {f'degree_{degree}': float(sum(values[i] for i, f in enumerate(mapping) if f['degree'] == degree))
                  for degree in range(4)}
        families.append(dict(model_id=model['id'], **family, peak=float(values[-1]),
                             peak_rank=int(np.flatnonzero(order == len(values)-1)[0]+1)))
    if ranked:
        table('ranked_features.csv', ranked, ['model_id', 'rank'])
        table('coefficient_families.csv', families, ['model_id'])
    for el in ELEMENTS:
        subset = [m for m in models if m['element'] == el]
        if question == 'Q1':
            natural = next(m for m in subset if not m['balanced'])
            balanced = next(m for m in subset if m['balanced'])
            comparisons.append(dict(element=el, delta_macro_f1=balanced['metrics_mean']['macro_f1']-natural['metrics_mean']['macro_f1'],
                                    accuracy_gain_over_mode=balanced['metrics_mean']['accuracy']-balanced['baseline']['accuracy']))
        elif question == 'Q3':
            full = next(m for m in subset if m['representation'] == 'pointwise')
            peak = next(m for m in subset if m['representation'] == 'peak')
            comparisons.append(dict(element=el, delta_r2=full['metrics_mean']['r2']-peak['metrics_mean']['r2'],
                                    mae_reduction=peak['metrics_mean']['mae']-full['metrics_mean']['mae']))
        elif question == 'Q4':
            for target in ['coord', 'md', 'bader']:
                a = next(m for m in subset if m['target'] == target and m['representation'] == 'pointwise')
                b = next(m for m in subset if m['target'] == target and m['representation'] == 'poly')
                metric = 'macro_f1' if target == 'coord' else 'r2'
                comparisons.append(dict(element=el, target=target, metric=metric, pointwise=a['metrics_mean'][metric],
                                        poly=b['metrics_mean'][metric], delta=b['metrics_mean'][metric]-a['metrics_mean'][metric]))
        elif question == 'Q5':
            from scipy.stats import spearmanr
            for target in ['coord', 'md']:
                for representation in ['pointwise', 'poly']:
                    a = next(m for m in subset if m['target'] == target and m['representation'] == representation and m['normalization'] == 'feff')
                    b = next(m for m in subset if m['target'] == target and m['representation'] == representation and m['normalization'] == 'max')
                    x, y = mean_importance[a['id']], mean_importance[b['id']]
                    tops = [set(np.argsort(-array)[:12]) for array in [x, y]]
                    metric = 'macro_f1' if target == 'coord' else 'r2'
                    comparisons.append(dict(element=el, target=target, representation=representation, metric=metric,
                                            delta=b['metrics_mean'][metric]-a['metrics_mean'][metric],
                                            importance_spearman=float(spearmanr(x, y).statistic),
                                            top12_jaccard=len(tops[0] & tops[1])/len(tops[0] | tops[1])))
    if comparisons:
        keys = ['element'] + (['target'] if question in ['Q4', 'Q5'] else []) + (['representation'] if question == 'Q5' else [])
        table('comparisons.csv', comparisons, keys)
    if question == 'Q1':
        confusion = []
        for model in models:
            if not model['balanced']:
                continue
            rows = predictions[predictions.model_id == model['id']]
            for truth in [4, 5, 6]:
                for predicted in [4, 5, 6]:
                    count = int(((rows.y_true == truth) & (rows.y_pred == predicted)).sum()) / len(SEEDS)
                    confusion.append(dict(element=model['element'], true_class=truth,
                                          predicted_class=predicted, mean_count=count))
        table('confusion.csv', confusion, ['element', 'true_class', 'predicted_class'])


def verify(question, output, reference=DEFAULT_REFERENCE, anchors=None):
    output, reference = Path(output), Path(reference)
    anchors = Path(anchors) if anchors else reference / 'source_anchor_audit.json'
    archival = read_json(anchors)
    require(archival.get('checks_passed') is True, 'Source anchor audit has not passed')
    actual = read_json(output / 'result.json')
    reference_dir = reference / question
    expected = read_json(reference_dir / 'result.json')
    require(actual.get('question') == question, 'Wrong question in result.json')
    for key, value in dict(seeds=SEEDS, n_estimators=100, max_depth=35, split_seed=42).items():
        close(actual['protocol'][key], value, 'protocol.' + key, 0)
    models = actual['models']
    require(len({m['id'] for m in models}) == len(models), 'Repeated model id')
    signature = lambda m: (m['element'], m['target'], m['representation'], m['normalization'], m['balanced'])
    require(len(models) == len(configurations(question)) and {signature(m) for m in models} == configurations(question),
            'Missing, extra, or duplicate experiment conditions')
    references = {signature(m): m for m in expected['models']}
    splits, metadata = read_json(output / 'splits.json'), read_json(output / 'feature_metadata.json')
    required_splits = {m['element'] + '_' + m['target'] for m in models}
    required_meta = {m['element'] + '_' + m['representation'] for m in models}
    require(set(splits) == required_splits, 'Missing or extra split identifiers')
    require(set(metadata) == required_meta, 'Missing or extra feature maps')
    for el in ELEMENTS:
        counts = archival['elements'][el]['counts']
        desired = dict(raw=counts['raw'], ineligible=counts['ineligible'],
                       unphysical=counts['unphysical'], polynomial_rejected=counts['poor_cubic_fit'],
                       retained=counts['retained'])
        close(actual['preprocessing'][el], desired, el + '.preprocessing', atol=0)
    pred = pd.read_csv(output / 'predictions.csv')
    imp = pd.read_csv(output / 'importances.csv')
    refpred = pd.read_csv(reference_dir / 'predictions.csv')
    refimp = pd.read_csv(reference_dir / 'importances.csv')
    for frame, keys, values, label in [(pred, ['model_id', 'seed', 'source_row'], ['y_true', 'y_pred'], 'predictions'),
                                      (imp, ['model_id', 'seed', 'feature_index'], ['importance'], 'importances')]:
        require(set(keys + values).issubset(frame.columns), label + ': missing columns')
        require(not frame.duplicated(keys).any(), label + ': duplicate row identifiers')
        require(np.isfinite(frame[keys[1:] + values].to_numpy(dtype=float)).all(), label + ': nonfinite values')
        require(set(frame.model_id) == {m['id'] for m in models}, label + ': missing or extra models')
        for key in keys[1:]:
            require(np.equal(frame[key], np.floor(frame[key])).all(), label + ': noninteger identity')
    checks = []
    for model in models:
        el, target, representation, _, balanced = signature(model)
        name = model['id']
        partition = archival['elements'][el]['targets'][target]['partitions']
        desired_splits = {s: p['source_rows'] for s, p in partition.items()}
        close(splits[el + '_' + target], desired_splits, name + '.splits', atol=0)
        train = np.asarray(partition['train']['y'])
        truth = np.asarray(partition['test']['y'])
        test_rows = partition['test']['source_rows']
        for subset in ['train', 'valid', 'test']:
            close(model[subset + '_count'], len(partition[subset]['y']), name + '.' + subset + '_count', 0)
        desired_fit_count = len(train)
        if balanced:
            desired_fit_count = 3 * int(np.unique(train, return_counts=True)[1].max())
        close(model['fit_count'], desired_fit_count, name + '.fit_count', 0)
        close(model['seeds'], SEEDS, name + '.seeds', 0)
        if target == 'coord':
            labels, counts = np.unique(train, return_counts=True)
            mode = labels[counts.argmax()]
            baseline = dict(train_mode=float(mode), accuracy=float(np.mean(truth == mode)),
                            train_class_counts={str(int(k)): int(n) for k, n in zip(labels, counts)})
            thresholds = {}
        else:
            baseline = dict(train_mean=float(train.mean()), mae=float(np.abs(truth-train.mean()).mean()),
                            r2=float(r2_score(truth, np.full(len(truth), train.mean()))))
            thresholds = dict(low=float(np.quantile(train, .1)), high=float(np.quantile(train, .9)))
        close(model['baseline'], baseline, name + '.baseline')
        close(model['tail_thresholds'], thresholds, name + '.tail_thresholds')
        featuremap = expected_metadata(archival['elements'][el]['energy_eV'], representation)
        close(metadata[el + '_' + representation], featuremap, name + '.feature_metadata', 1e-7)
        group = pred[pred.model_id == name]
        importance = imp[imp.model_id == name]
        require(set(group.seed) == set(SEEDS) and set(importance.seed) == set(SEEDS), name + ': seed coverage differs')
        refmodel = references[signature(model)]
        seed_metrics, distances, importance_distances = [], [], []
        for seed in SEEDS:
            rows = group[group.seed == seed].set_index('source_row')
            require(set(rows.index) == set(test_rows) and len(rows) == len(test_rows), name + ': test row coverage differs')
            rows = rows.loc[test_rows]
            np.testing.assert_allclose(rows.y_true, truth, rtol=0, atol=1e-12, err_msg=name + ': truth labels differ')
            predictions = rows.y_pred.to_numpy()
            seed_metrics.append(recompute_metrics(target, truth, predictions, train))
            r = refpred[(refpred.model_id == refmodel['id']) & (refpred.seed == seed)].set_index('source_row').loc[test_rows]
            if target == 'coord':
                distance = float(np.mean(predictions != r.y_pred.to_numpy()))
                require(distance <= .08, name + ': excessive prediction disagreement')
            else:
                distance = float(np.sqrt(np.mean((predictions-r.y_pred.to_numpy())**2)))
                require(distance <= (.020 if target == 'md' else .060), name + ': prediction RMSE from reference is too large')
            distances.append(distance)
            weights = importance[importance.seed == seed].set_index('feature_index')
            require(set(weights.index) == set(range(len(featuremap))), name + ': feature coverage differs')
            weights = weights.loc[range(len(featuremap))].importance.to_numpy()
            require(np.all(weights >= 0) and abs(weights.sum()-1) < 1e-8, name + ': invalid importance mass')
            rw = refimp[(refimp.model_id == refmodel['id']) & (refimp.seed == seed)].set_index('feature_index').loc[range(len(featuremap))].importance.to_numpy()
            l1 = float(np.abs(weights-rw).sum())
            require(l1 <= .5, name + ': importance distribution differs excessively')
            importance_distances.append(l1)
        means = {k: float(np.mean([s[k] for s in seed_metrics])) if seed_metrics[0][k] is not None else None for k in seed_metrics[0]}
        stds = {k: float(np.std([s[k] for s in seed_metrics])) if seed_metrics[0][k] is not None else None for k in seed_metrics[0]}
        close(model['metrics_mean'], means, name + '.metrics_mean')
        close(model['metrics_std'], stds, name + '.metrics_std')
        for key, value in means.items():
            expected_value = refmodel['metrics_mean'][key]
            if key.endswith('_count') or value is None:
                close(value, expected_value, name + '.' + key, 0)
                continue
            tolerance = .04 if key == 'r2' else .03 if key == 'accuracy' else .07 if 'f1' in key else .010 if target == 'md' else .025
            require(abs(value - expected_value) <= tolerance, name + ': ' + key + ' outside benchmark tolerance')
        checks.append(dict(model_id=name, all_test_labels_match_raw_release=True,
                           metrics_recomputed=True, maximum_prediction_distance=max(distances),
                           maximum_importance_l1=max(importance_distances)))
    check_derived_tables(question, output, models, pred, imp, metadata)
    from PIL import Image
    for name in ['plot.png', 'diagnostics.png']:
        require((output / name).is_file(), 'Missing ' + name)
        with Image.open(output / name) as plot:
            plot.verify()
    require((output / 'conclusion.md').is_file() and len((output / 'conclusion.md').read_text().strip()) >= 100,
            'Missing substantive conclusion.md')
    return dict(question=question, numeric_pass=True, model_count=len(models), checks=checks,
                anchor='Independent raw-to-published-array and polynomial-coefficient audit',
                protocol_note='Three seeds and 100 trees with current scikit-learn; archived results used ten seeds and 300 trees with scikit-learn 0.21.3. Tolerances are benchmark adjudication limits, not physical uncertainty.',
                manual_review_required='Check requested research conclusions, numerical evidence, error bars and plots. Numeric passing alone is insufficient; verify tail discussion, per-class comparisons, white-line limitation, and/or interpretable feature families as applicable. No OS-level isolation or proof of no label leakage is claimed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question', choices=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--reference', default=DEFAULT_REFERENCE, type=Path)
    parser.add_argument('--anchors', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.question, args.output, args.reference, args.anchors), indent=2))
    except (AssertionError, KeyError, ValueError, TypeError, OSError) as exc:
        raise SystemExit('Verification failed: ' + str(exc))


if __name__ == '__main__':
    main()
