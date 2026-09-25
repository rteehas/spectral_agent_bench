"""Independent source anchors and adversarial audit for the XANES benchmark.

This is evaluator code. It deliberately does not import candidate.py. Source
anchors are reconstructed from raw JSONL records and compared with the authors'
released arrays and polynomial coefficients. The benchmark's model predictions
are a modern rerun, not archival ground truth.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
ELEMENTS = ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']
REFIT_PROBES = [('Q1', 'Ti', 'coord', 'pointwise', 'feff', True),
                ('Q2', 'Ti', 'md', 'pointwise', 'feff', False),
                ('Q3', 'Fe', 'bader', 'pointwise', 'feff', False),
                ('Q4', 'Ti', 'md', 'poly', 'feff', False),
                ('Q5', 'Ni', 'md', 'poly', 'max', False)]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_raw(path):
    """Retain only physical arrays/labels, never precomputed descriptors."""
    rows = []
    with path.open() as stream:
        for source_row, line in enumerate(stream):
            d = json.loads(line)
            rows.append({'row': source_row, 'x': d['mu'], 'energy': d['E'],
                         'coord': d.get('coordination'), 'bader': d.get('bader'),
                         'md': d.get('avg_nn_dists'),
                         'has_nn': d.get('nn_min-max') is not None})
    return rows


def quality_mask(rows):
    """Independent least-squares residual projector for twenty cubic blocks."""
    x = np.asarray([d['x'] for d in rows], dtype=float)
    eligible = np.array([d['coord'] in [4, 5, 6] or bool(d['bader']) for d in rows])
    maximum = x.max(axis=1)
    physical = ((x[:, -1] != maximum) & (maximum <= 3) &
                ~np.any(x[:, :10] == maximum[:, None], axis=1))
    # Equally spaced five-point blocks have identical fitted-value projectors,
    # independently of energy offset/scale. The raw release grids are uniform.
    for d in rows:
        e = np.asarray(d['energy'])
        assert len(e) == 100 and np.allclose(np.diff(e), np.diff(e)[0], atol=1e-10)
    design = np.vander(np.linspace(-1, 1, 5), 4, increasing=True)
    residual = np.eye(5) - design @ np.linalg.pinv(design)
    blocks = (x / maximum[:, None]).reshape(-1, 20, 5)
    errors = np.sum(np.abs(blocks @ residual.T), axis=2)
    fitted = np.all(errors <= .1, axis=1)
    mask = eligible & physical & fitted
    return mask, {'raw': len(rows), 'ineligible': int((~eligible).sum()),
                  'unphysical': int((eligible & ~physical).sum()),
                  'poor_cubic_fit': int((eligible & physical & ~fitted).sum()),
                  'retained': int(mask.sum())}


def polynomial_probe(row, normalized):
    e = np.asarray(row['energy'], dtype=float)
    y = np.asarray(row['x'], dtype=float)
    if normalized:
        y = y / y.max()
    out = {'peak': int(y.argmax())}
    for n in [4, 5, 10, 20]:
        for chunk in range(n):
            sl = slice(chunk * (100 // n), (chunk + 1) * (100 // n))
            # Deliberately solve the scaled Vandermonde system directly instead
            # of using the reference workflow's Polynomial.fit implementation.
            local_e = e[sl]
            scaled = 2 * (local_e - local_e[0]) / (local_e[-1] - local_e[0]) - 1
            design = np.vander(scaled, 4, increasing=True)
            coeff = np.linalg.lstsq(design, y[sl], rcond=None)[0]
            for degree, value in enumerate(coeff):
                out[f'loc:all,deg:3,fraction_size:{n},chunk:{chunk},coef:{degree}'] = float(value)
    return out


def build_source_anchors(release):
    anchors = {'method': 'Independent raw JSONL QC, seed-42 splits, and least-squares polynomial probes; no candidate workflow imported.',
               'release_root': 'matrio_folder', 'elements': {}, 'checks_passed': True,
               'limitations': ['Released model_data are preprocessing anchors, not saved model predictions.',
                               'Modern random forests may differ from scikit-learn 0.21.3; published aggregate tables are secondary tolerance-based checks.',
                               'The released unstratified spectrum split can contain related structures in different partitions; it does not establish unseen-material generalization.']}
    for el in ELEMENTS:
        path = release / 'spectral_data' / f'{el}_XY.json'
        rows = read_raw(path)
        mask, counts = quality_mask(rows)
        kept = [d for d, keep in zip(rows, mask) if keep]
        info = {'raw_sha256': digest(path), 'energy_eV': rows[0]['energy'], 'counts': counts, 'targets': {}, 'polynomial_checks': []}
        for target in ['coord', 'md', 'bader']:
            if target == 'coord':
                selected = [d for d in kept if d['coord'] in [4, 5, 6]]
            elif target == 'md':
                selected = [d for d in kept if d['coord'] in [4, 5, 6] and d['has_nn']]
            else:
                selected = [d for d in kept if bool(d['bader'])]
            x = np.asarray([d['x'] for d in selected])
            y = np.asarray([d[target] for d in selected], dtype=float)
            source = np.asarray([d['row'] for d in selected])
            train, test = train_test_split(np.arange(len(selected)), test_size=.1, random_state=42)
            train, valid = train_test_split(train, test_size=.1, random_state=42)
            partitions = {'train': train, 'valid': valid, 'test': test}
            entry = {'eligible_count': len(selected), 'partitions': {}, 'published_arrays': []}
            for name, idx in partitions.items():
                entry['partitions'][name] = {'source_rows': source[idx].tolist(), 'y': y[idx].tolist()}
                archival_idx = idx
                if target == 'coord' and name == 'train':
                    rng = np.random.RandomState(42)
                    labels, class_counts = np.unique(y[idx], return_counts=True)
                    added = [rng.choice(idx[y[idx] == label], size=class_counts.max() - count,
                                        replace=True) for label, count in zip(labels, class_counts)]
                    archival_idx = np.concatenate([idx] + added)
                for kind, actual in [('x', x[archival_idx]), ('y', y[archival_idx])]:
                    f = release / 'model_data' / f'{el}_{target}_{name}_{kind}.npy'
                    published = np.load(f, allow_pickle=False)
                    np.testing.assert_allclose(actual, published, rtol=0, atol=1e-12,
                                               err_msg=f.name)
                    entry['published_arrays'].append({'file': f.name, 'shape': list(published.shape),
                                                       'sha256': digest(f), 'max_absolute_difference': float(np.max(np.abs(actual-published)))})
            info['targets'][target] = entry
        for norm in ['feff', 'max']:
            f = release / 'spectral_data' / f'{el}_{norm}norm_polynomial_XY.json'
            # Samples spread through the retained list, including both ends.
            probes = set(np.linspace(0, len(kept)-1, 9).astype(int).tolist())
            n_records = 0
            with f.open() as stream:
                for i, line in enumerate(stream):
                    n_records += 1
                    if i not in probes:
                        continue
                    external = json.loads(line)
                    mine = polynomial_probe(kept[i], norm == 'max')
                    errors = [abs(v-external['labeled_coefficients'][key]) for key, v in mine.items()]
                    assert max(errors) < 1e-8, (el, norm, i, max(errors))
                    info['polynomial_checks'].append({'normalization': norm, 'retained_index': i,
                                                       'source_row': kept[i]['row'], 'features_checked': len(mine),
                                                       'maximum_absolute_difference': max(errors)})
            assert n_records == len(kept), (el, norm, 'polynomial row count')
        anchors['elements'][el] = info
        print(el, counts, 'all released arrays and polynomial probes matched', flush=True)
    published = DATA / 'verification/published'
    published.mkdir(parents=True, exist_ok=True)
    anchors['published_tables'] = []
    for norm in ['feff', 'max']:
        for representation in ['pointwise', 'poly']:
            source = release / f'figures_{norm}norm' / f'{representation}_table_{norm}.csv'
            shutil.copy2(source, published / source.name)
            anchors['published_tables'].append({'path': 'published/' + source.name,
                                                'source': str(source.relative_to(release)),
                                                'sha256': digest(source)})
    dest = DATA / 'verification/source_anchor_audit.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(anchors, indent=2) + '\n')
    return anchors


def load_verifier():
    spec = importlib.util.spec_from_file_location('torrisi_verifier', DATA / 'workflows/verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_refits(release, cache):
    """Fit archival-array models ahead of verification; preserve source hashes."""
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    cache.mkdir(parents=True, exist_ok=True)
    for q, el, target, representation, norm, balanced in REFIT_PROBES:
        prefix = el + (f'_{norm}norm_polynomial' if representation == 'poly' else '')
        source = release / 'model_data'
        paths = [source / f'{prefix}_{target}_{s}.npy' for s in ['train_x', 'train_y', 'test_x']]
        train_x, train_y, test_x = [np.load(p, allow_pickle=False) for p in paths]
        cls = RandomForestClassifier if target == 'coord' else RandomForestRegressor
        model = cls(n_estimators=100, max_depth=35, max_features=30 if representation == 'poly' else 8,
                    random_state=42, n_jobs=2)
        model.fit(train_x, train_y)
        expected = model.predict(test_x)
        key = '_'.join([el, target, representation, norm, 'balanced' if balanced else 'natural'])
        record = dict(model_id=key, seed=42, n_estimators=100, max_depth=35,
                      max_features=30 if representation == 'poly' else 8,
                      source_files={p.name: digest(p) for p in paths}, predictions=expected.tolist())
        (cache / (key + '.json')).write_text(json.dumps(record) + '\n')
        print(key, 'independent archival-array forest fitted', flush=True)


def independent_refits(runs, release, cache=None):
    """Compare candidates to independently fitted archival-array predictions."""
    import pandas as pd
    if cache is None:
        with tempfile.TemporaryDirectory(prefix='torrisi-independent-refits-') as temp:
            cache = Path(temp)
            prepare_refits(release, cache)
            return independent_refits(runs, release, cache)
    reports = []
    for q, el, target, representation, norm, balanced in REFIT_PROBES:
        key = '_'.join([el, target, representation, norm, 'balanced' if balanced else 'natural'])
        stored = json.loads((cache / (key + '.json')).read_text())
        assert stored['model_id'] == key and stored['seed'] == 42 and stored['n_estimators'] == 100
        for filename, sha in stored['source_files'].items():
            assert digest(release / 'model_data' / filename) == sha, 'Independent refit source hash differs'
        expected = np.asarray(stored['predictions'])
        frame = pd.read_csv(runs / q / 'predictions.csv')
        candidate = frame[(frame.model_id == key) & (frame.seed == 42)].y_pred.to_numpy()
        np.testing.assert_allclose(candidate, expected, rtol=0, atol=1e-8,
                                   err_msg=key + ': independent archival-array refit differs')
        evidence = DATA / 'verification/independent_refits'
        evidence.mkdir(exist_ok=True)
        shutil.copy2(cache / (key + '.json'), evidence / (key + '.json'))
        reports.append(dict(question=q, model_id=key, seed=42, source='authors released model_data arrays',
                            candidate_code_imported=False, predictions=len(expected),
                            source_files=stored['source_files'], n_estimators=100,
                            evidence='independent_refits/' + key + '.json',
                            maximum_absolute_prediction_difference=float(np.max(np.abs(candidate-expected)))))
        print(key, 'independent archival-array refit matched', flush=True)
    return reports


def published_score_comparison(runs):
    """Contextual archival table comparison, excluding deliberately changed balancing."""
    import csv
    import re
    tables = {}
    for norm in ['feff', 'max']:
        for rep in ['pointwise', 'poly']:
            p = DATA / 'verification/published' / f'{rep}_table_{norm}.csv'
            with p.open() as stream:
                rows = list(csv.reader(stream))[1:9]
            tables[(rep, norm)] = {r[0]: [float(re.match(r'\s*([-+0-9.]+)', cell).group(1)) for cell in r[1:]]
                                  for r in rows}
    comparisons, seen = [], set()
    for q in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
        result = json.loads((runs / q / 'result.json').read_text())
        for m in result['models']:
            if m['id'] in seen or m['representation'] == 'peak':
                continue
            seen.add(m['id'])
            if m['target'] == 'coord' and (not m['balanced'] or m['representation'] == 'poly'):
                continue  # Archival pointwise was balanced; archival polynomial was not.
            row = tables[(m['representation'], m['normalization'])][m['element']]
            if m['target'] == 'coord':
                targets = {'accuracy': row[1]/100, 'f1_4': row[2]/100,
                           'f1_5': row[3]/100, 'f1_6': row[4]/100}
            elif m['target'] == 'bader':
                targets = {'r2': row[5]/100, 'mae': row[6]}
            else:
                targets = {'r2': row[7]/100, 'mae': row[8]}
            for metric, published in targets.items():
                modern = m['metrics_mean'][metric]
                comparisons.append(dict(model_id=m['id'], metric=metric, published=published,
                                        modern=modern, modern_minus_published=modern-published))
    return {'role': 'Contextual, not a pass/fail oracle: different forest size, seeds and sklearn version; polynomial coordination intentionally balances classes and is excluded.',
            'comparisons': comparisons,
            'maximum_absolute_score_difference': max(abs(x['modern_minus_published']) for x in comparisons
                                                     if x['metric'] != 'mae')}


def audit_runs(runs, release=None, refit_cache=None):
    import pandas as pd
    v = load_verifier()
    anchors = DATA / 'verification/source_anchor_audit.json'
    archival = json.loads(anchors.read_text())
    reports = []
    for question in ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']:
        report = v.verify(question, runs / question, runs, anchors)
        reports.append(dict(question=question, correct_candidate_passes=report['numeric_pass'],
                            checked_models=report['model_count']))
    mutations = []

    def inconsistent_metric(folder):
        p = folder / 'result.json'; d = json.loads(p.read_text())
        d['models'][0]['metrics_mean']['mae'] += .03
        p.write_text(json.dumps(d))

    def falsified_truth(folder):
        p = folder / 'predictions.csv'; d = pd.read_csv(p); d.loc[0, 'y_true'] += .1
        d.to_csv(p, index=False)

    def missing_predictions(folder):
        p = folder / 'predictions.csv'; d = pd.read_csv(p); d.iloc[1:].to_csv(p, index=False)

    def invalid_importance(folder):
        p = folder / 'importances.csv'; d = pd.read_csv(p); d.loc[0, 'importance'] = np.nan
        d.to_csv(p, index=False)

    def split_contamination(folder):
        p = folder / 'splits.json'; d = json.loads(p.read_text()); key = next(iter(d))
        d[key]['train'][0] = d[key]['test'][0]; p.write_text(json.dumps(d))

    def remapped_feature(folder):
        p = folder / 'feature_metadata.json'; d = json.loads(p.read_text()); key = next(k for k in d if k.endswith('_poly'))
        d[key][0]['degree'] = (d[key][0]['degree'] + 1) % 4; p.write_text(json.dumps(d))

    def self_consistent_bad_predictions(folder):
        p = folder / 'predictions.csv'; d = pd.read_csv(p)
        j = folder / 'result.json'; result = json.loads(j.read_text()); m = result['models'][0]
        mask = d.model_id == m['id']; d.loc[mask, 'y_pred'] += .15
        d.to_csv(p, index=False)
        train = np.asarray(archival['elements'][m['element']]['targets'][m['target']]['partitions']['train']['y'])
        metrics = []
        for seed in m['seeds']:
            rows = d[mask & (d.seed == seed)]
            metrics.append(v.recompute_metrics(m['target'], rows.y_true.to_numpy(), rows.y_pred.to_numpy(), train))
        m['metrics_mean'] = {k: float(np.mean([s[k] for s in metrics])) for k in metrics[0]}
        m['metrics_std'] = {k: float(np.std([s[k] for s in metrics])) for k in metrics[0]}
        j.write_text(json.dumps(result))

    def wrong_experiment(folder):
        p = folder / 'result.json'; d = json.loads(p.read_text()); d['models'][0]['balanced'] = not d['models'][0]['balanced']
        p.write_text(json.dumps(d))

    def fabricated_confusion(folder):
        p = folder / 'confusion.csv'; d = pd.read_csv(p); d.loc[0, 'mean_count'] += 10
        d.to_csv(p, index=False)

    def fabricated_rank_stability(folder):
        p = folder / 'comparisons.csv'; d = pd.read_csv(p); d.loc[0, 'importance_spearman'] = -.99
        d.to_csv(p, index=False)

    controls = [('Q2', 'inconsistent_summary', inconsistent_metric),
                ('Q2', 'falsified_truth', falsified_truth),
                ('Q2', 'missing_test_prediction', missing_predictions),
                ('Q2', 'nonfinite_importance', invalid_importance),
                ('Q2', 'train_test_contamination', split_contamination),
                ('Q4', 'wrong_polynomial_feature_map', remapped_feature),
                ('Q2', 'self_consistent_but_wrong_predictions', self_consistent_bad_predictions),
                ('Q1', 'wrong_experiment_condition', wrong_experiment),
                ('Q1', 'fabricated_confusion_table', fabricated_confusion),
                ('Q5', 'fabricated_rank_stability', fabricated_rank_stability)]
    with tempfile.TemporaryDirectory(prefix='torrisi-verifier-controls-') as temp:
        benign = Path(temp) / 'benign-row-permutation'
        shutil.copytree(runs / 'Q5', benign)
        for filename in ['predictions.csv', 'importances.csv']:
            p = benign / filename
            frame = pd.read_csv(p).sample(frac=1, random_state=1234)
            frame.to_csv(p, index=False)
        v.verify('Q5', benign, runs, anchors)
        benign_control = dict(question='Q5', control='permute_prediction_and_importance_CSV_rows', accepted=True,
                              purpose='The verifier accepts equivalent outputs independently of table row order.')
        for question, label, mutate in controls:
            dest = Path(temp) / label
            shutil.copytree(runs / question, dest)
            mutate(dest)
            try:
                v.verify(question, dest, runs, anchors)
            except (AssertionError, KeyError, ValueError, TypeError) as exc:
                mutations.append(dict(question=question, control=label, rejected=True, reason=str(exc)[:300]))
            else:
                raise AssertionError(label + ': bad candidate was accepted')
    refits = independent_refits(runs, release, refit_cache) if release else []
    report = dict(candidate_run_root=str(runs.resolve()), numerical_reference_root=str(runs.resolve()),
                  source_identity='Executed workflow outputs; independently anchored to raw/released arrays and separate archival-array model fits.',
                  positive_controls=reports, benign_positive_control=benign_control,
                  negative_controls=mutations, independent_model_refits=refits,
                  published_score_comparison=published_score_comparison(runs),
                  scope='Numerical artifact consistency, raw/released-data anchors, independent model refits, and rejection controls. No OS-level solver isolation or automated scientific-prose grading claimed.')
    (DATA / 'verification/verification_audit.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--runs', type=Path)
    parser.add_argument('--independent-release', type=Path,
                        help='Release directory for independent refits, without rebuilding source anchors')
    parser.add_argument('--prepare-refits', action='store_true',
                        help='Fit archival-array models before candidate outputs finish')
    parser.add_argument('--refit-cache', type=Path)
    args = parser.parse_args()
    if args.release:
        build_source_anchors(args.release)
    if args.prepare_refits:
        if not args.refit_cache or not (args.independent_release or args.release):
            parser.error('--prepare-refits needs --refit-cache and --independent-release or --release')
        prepare_refits(args.independent_release or args.release, args.refit_cache)
    if args.runs:
        audit_runs(args.runs, args.independent_release or args.release, args.refit_cache)
    if not args.release and not args.runs and not args.prepare_refits:
        parser.error('Use --release and/or --runs')


if __name__ == '__main__':
    main()
