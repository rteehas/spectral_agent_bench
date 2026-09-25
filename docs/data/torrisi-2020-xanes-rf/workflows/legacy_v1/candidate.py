#!/usr/bin/env python3
"""Worked solutions. Reads only the specified input directory; no reference imports."""
import argparse
import csv
import gzip
import json
import platform
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

ELEMENTS = ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']
SEEDS = [42, 43, 44]
TARGETS = {'coord': 'coordination', 'md': 'avg_nn_dists', 'bader': 'bader'}


def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def polynomial_features(energy, matrix):
    """Same scaled Polynomial.fit coordinates as the public numerical convention."""
    values, metadata = [], []
    for parts in [4, 5, 10, 20]:
        width = 100 // parts
        for chunk in range(parts):
            sl = slice(chunk * width, (chunk + 1) * width)
            x = energy[sl]
            scaled = (2*x-x[0]-x[-1])/(x[-1]-x[0])
            coefs = np.polynomial.polynomial.polyfit(scaled, matrix[:, sl].T, 3).T
            for degree in range(4):
                label = f'loc:all,deg:3,fraction_size:{parts},chunk:{chunk},coef:{degree}'
                values.append(coefs[:, degree])
                metadata.append(dict(label=label, degree=degree, parts=parts, chunk=chunk,
                                     energy_lo=float(x[0]), energy_hi=float(x[-1])))
    order = sorted(range(len(metadata)), key=lambda i: metadata[i]['label'])
    values = [values[i] for i in order]
    metadata = [metadata[i] for i in order]
    values.append(np.argmax(matrix, axis=1))
    metadata.append(dict(label='peak', degree=-1, parts=0, chunk=0,
                         energy_lo=float(energy[0]), energy_hi=float(energy[-1])))
    for i, m in enumerate(metadata):
        m['index'] = i
    return np.array(values).T, metadata


def prepare(inputs):
    data, audit = {}, {}
    for element in ELEMENTS:
        with gzip.open(inputs / f'{element}.jsonl.gz', 'rt') as f:
            rows = [json.loads(line) for line in f]
        energy = np.array(rows[0]['E'], dtype=float)
        x = np.array([r['mu'] for r in rows], dtype=float)
        assert x.shape == (len(rows), 100) and np.isfinite(x).all()
        assert all(np.allclose(r['E'], energy, atol=1e-9, rtol=0) for r in rows)
        eligible = np.array([r['coordination'] in [4, 5, 6] or bool(r['bader']) for r in rows])
        peak = x.max(axis=1)
        physical = (x[:, -1] != peak) & (peak <= 3) & (x[:, :10].max(axis=1) != peak)
        normalized = x / peak[:, None]
        errors = []
        for k in range(20):
            sl = slice(5*k, 5*k+5)
            block_energy = energy[sl]
            scaled = (2*block_energy-block_energy[0]-block_energy[-1])/(block_energy[-1]-block_energy[0])
            coeff = np.polynomial.polynomial.polyfit(scaled, normalized[:, sl].T, 3)
            fitted = np.polynomial.polynomial.polyval(scaled, coeff)
            errors.append(np.abs(normalized[:, sl] - fitted).sum(axis=1))
        fit_ok = np.max(errors, axis=0) <= .1
        keep = eligible & physical & fit_ok
        audit[element] = dict(raw=len(rows), ineligible=int((~eligible).sum()),
                              unphysical=int((eligible & ~physical).sum()),
                              polynomial_rejected=int((eligible & physical & ~fit_ok).sum()),
                              retained=int(keep.sum()))
        rows = [r for r, ok in zip(rows, keep) if ok]
        x = x[keep]
        data[element] = dict(rows=rows, energy=energy, x=x)
    return data, audit


def feature_matrix(item, representation, normalization):
    cache = item.setdefault('features', {})
    key = (representation, normalization)
    if key in cache:
        return cache[key]
    x = item['x'].copy()
    e = item['energy']
    if normalization == 'max':
        x /= x.max(axis=1)[:, None]
    if representation == 'poly':
        cache[key] = polynomial_features(e, x)
        return cache[key]
    if representation == 'peak':
        return np.argmax(x, axis=1)[:, None], [dict(index=0, label='peak', degree=-1,
                    parts=0, chunk=0, energy_lo=float(e[0]), energy_hi=float(e[-1]))]
    return x, [dict(index=i, label=f'mu_{i}', degree=-1, parts=0, chunk=i,
                    energy_lo=float(e[i]), energy_hi=float(e[i])) for i in range(100)]


def settings(question):
    if question == 'Q1':
        return [('coord', 'pointwise', 'feff', b) for b in [False, True]]
    if question == 'Q2':
        return [('md', 'pointwise', 'feff', False)]
    if question == 'Q3':
        return [('bader', r, 'feff', False) for r in ['pointwise', 'peak']]
    if question == 'Q4':
        return [(t, r, 'feff', t == 'coord') for t in TARGETS for r in ['pointwise', 'poly']]
    return [(t, r, n, t == 'coord') for t in ['coord', 'md']
            for r in ['pointwise', 'poly'] for n in ['feff', 'max']]


def fit_model(element, item, target, representation, normalization, balanced, jobs):
    model_id = '_'.join([element, target, representation, normalization, 'balanced' if balanced else 'natural'])
    rows = item['rows']
    if target == 'coord':
        mask = [r['coordination'] in [4, 5, 6] for r in rows]
    elif target == 'md':
        mask = [r['coordination'] in [4, 5, 6] and r['nn_min-max'] is not None for r in rows]
    else:
        mask = [bool(r['bader']) for r in rows]
    x, metadata = feature_matrix(item, representation, normalization)
    x = x[mask]
    selected = [r for r, keep in zip(rows, mask) if keep]
    y = np.array([r[TARGETS[target]] for r in selected], dtype=float)
    source_ids = np.array([r['source_row'] for r in selected])
    train, test = train_test_split(np.arange(len(y)), test_size=.1, random_state=42)
    train, valid = train_test_split(train, test_size=.1, random_state=42)
    split = {s: source_ids[a].tolist() for s, a in [('train', train), ('valid', valid), ('test', test)]}
    fit_ids = train.copy()
    if balanced:
        rng = np.random.RandomState(42)
        classes, counts = np.unique(y[train], return_counts=True)
        for cls, count in zip(classes, counts):
            fit_ids = np.concatenate([fit_ids, rng.choice(train[y[train] == cls],
                                      size=int(counts.max()-count), replace=True)])
    baseline = {}
    tail_thresholds = {}
    if target == 'coord':
        classes, counts = np.unique(y[train], return_counts=True)
        mode = classes[np.argmax(counts)]
        baseline = dict(train_mode=float(mode), accuracy=float(np.mean(y[test] == mode)),
                        train_class_counts={str(int(k)): int(v) for k, v in zip(classes, counts)})
    else:
        baseline = dict(train_mean=float(y[train].mean()),
                        mae=float(np.abs(y[test]-y[train].mean()).mean()),
                        r2=float(r2_score(y[test], np.full(len(test), y[train].mean()))))
        tail_thresholds = dict(low=float(np.quantile(y[train], .1)), high=float(np.quantile(y[train], .9)))
    metrics, predictions, importances = [], [], []
    for seed in SEEDS:
        cls = RandomForestClassifier if target == 'coord' else RandomForestRegressor
        model = cls(n_estimators=100, max_depth=35,
                    max_features={'pointwise': 8, 'poly': 30, 'peak': 1}[representation],
                    random_state=seed, n_jobs=jobs)
        model.fit(x[fit_ids], y[fit_ids])
        pred = model.predict(x[test])
        if target == 'coord':
            f1 = f1_score(y[test], pred, labels=[4, 5, 6], average=None, zero_division=0)
            m = dict(accuracy=float(accuracy_score(y[test], pred)),
                     macro_f1=float(f1.mean()), **{f'f1_{k}': float(v) for k, v in zip([4,5,6], f1)})
        else:
            m = dict(r2=float(r2_score(y[test], pred)), mae=float(mean_absolute_error(y[test], pred)))
            for name, mask_tail in [('low', y[test] <= tail_thresholds['low']),
                                    ('high', y[test] >= tail_thresholds['high'])]:
                residual = pred[mask_tail]-y[test][mask_tail]
                m[f'{name}_count'] = int(mask_tail.sum())
                m[f'{name}_mae'] = float(np.abs(residual).mean()) if len(residual) else None
                m[f'{name}_bias'] = float(residual.mean()) if len(residual) else None
        metrics.append(m)
        predictions.extend(dict(model_id=model_id, seed=seed, source_row=int(row), y_true=float(truth), y_pred=float(p))
                           for row, truth, p in zip(source_ids[test], y[test], pred))
        importances.extend(dict(model_id=model_id, seed=seed, feature_index=i, importance=float(v))
                           for i, v in enumerate(model.feature_importances_))
    means = {k: float(np.mean([m[k] for m in metrics])) if metrics[0][k] is not None else None for k in metrics[0]}
    stds = {k: float(np.std([m[k] for m in metrics])) if metrics[0][k] is not None else None for k in metrics[0]}
    summary = dict(id=model_id, element=element, target=target, representation=representation,
                   normalization=normalization, balanced=balanced, train_count=len(train),
                   fit_count=len(fit_ids), valid_count=len(valid), test_count=len(test), seeds=SEEDS,
                   metrics_mean=means, metrics_std=stds, baseline=baseline, tail_thresholds=tail_thresholds)
    print(model_id, means, flush=True)
    return summary, split, predictions, importances, metadata


def plot_and_conclude(question, models, importances, output):
    targets = sorted(set(m['target'] for m in models))
    fig, axes = plt.subplots(1, len(targets), figsize=(7*len(targets), 5), squeeze=False)
    lines = [f'# {question}: evidence from the fixed spectral-record holdout', '',
             'Each mean and standard deviation summarizes three forest seeds on the same split. '
             'These are not split uncertainty estimates or tests on unseen material families.', '']
    for ax, target in zip(axes[0], targets):
        metric = 'macro_f1' if target == 'coord' else 'r2'
        groups = sorted(set((m['representation'], m['normalization'], m['balanced']) for m in models if m['target'] == target))
        for group in groups:
            selected = [m for m in models if m['target'] == target and
                        (m['representation'], m['normalization'], m['balanced']) == group]
            label = '/'.join(map(str, group))
            ax.errorbar([ELEMENTS.index(m['element']) for m in selected],
                        [m['metrics_mean'][metric] for m in selected],
                        yerr=[m['metrics_std'][metric] for m in selected], marker='o', label=label)
            lines.append(f'{target}, {label}: mean {metric} across elements = '
                         f'{np.mean([m["metrics_mean"][metric] for m in selected]):.4f}.')
        ax.set(xticks=range(8), xticklabels=ELEMENTS, ylabel=metric, title=target)
        ax.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(output / 'plot.png', dpi=140); plt.close(fig)
    if question == 'Q1':
        for e in ELEMENTS:
            a,b = [m for m in models if m['element']==e]
            lines.append(f'{e}: balanced minus natural macro-F1 = {b["metrics_mean"]["macro_f1"]-a["metrics_mean"]["macro_f1"]:+.4f}; '
                         f'balanced accuracy minus training-mode baseline = {b["metrics_mean"]["accuracy"]-b["baseline"]["accuracy"]:+.4f}.')
        lines.append('Oversampling effects vary by element; per-class F1 is needed to assess minority classes alongside overall accuracy.')
    if question == 'Q2':
        for m in models:
            k=m['metrics_mean']
            lines.append(f'{m["element"]}: MAE {k["mae"]:.5f} Å; low/high tail MAE {k["low_mae"]:.5f}/{k["high_mae"]:.5f} Å; '
                         f'low/high signed bias {k["low_bias"]:+.5f}/{k["high_bias"]:+.5f} Å.')
        lines.append('Tail thresholds come only from training targets. Positive low-tail and negative high-tail bias indicate shrinkage toward central distances where present.')
    if question == 'Q3':
        for e in ELEMENTS:
            a,b=[m for m in models if m['element']==e]
            lines.append(f'{e}: full minus peak-only R² = {a["metrics_mean"]["r2"]-b["metrics_mean"]["r2"]:+.4f}; '
                         f'full-spectrum MAE = {a["metrics_mean"]["mae"]:.4f} charge units.')
        lines.append('This ablation tests the information retained by this white-line descriptor and model, not whether peak energy has a causal role. Bader charge is not an integer oxidation-state label.')
    if question in ['Q4', 'Q5']:
        for m in models:
            if m['representation'] != 'poly': continue
            imp=np.array([[r['importance'] for r in importances if r['model_id']==m['id'] and r['seed']==s] for s in SEEDS]).mean(axis=0)
            lines.append(f'{m["id"]}: most important feature index {int(imp.argmax())}; peak importance {imp[-1]:.5f}. '
                         'Resolve energy intervals and coefficient degree using feature_metadata.json.')
        lines.append('Impurity importance allocates credit among correlated features and is not causal evidence. Compare coefficient families and energy intervals, rather than treating exact neighboring-feature ranks as physical constants.')
    (output / 'conclusion.md').write_text('\n'.join(lines)+'\n')


def run(question, inputs, output, jobs):
    start=time.monotonic()
    data, audit=prepare(inputs)
    cache={}
    questions=['Q1','Q2','Q3','Q4','Q5'] if question=='ALL' else [question]
    for q in questions:
        dest=output/q if question=='ALL' else output
        dest.mkdir(parents=True, exist_ok=True)
        models=[]; splits={}; predictions=[]; importances=[]; metadata={}
        for element in ELEMENTS:
            for config in settings(q):
                key=(element,)+config
                if key not in cache:
                    cache[key]=fit_model(element,data[element],*config,jobs)
                summary, split, pred, imp, meta=cache[key]
                models.append(summary); splits[element+'_'+config[0]]=split
                predictions.extend(pred); importances.extend(imp)
                metadata[element+'_'+config[1]]=meta
        dump(dest/'result.json', dict(question=q, models=models, preprocessing=audit,
             protocol=dict(seeds=SEEDS,n_estimators=100,max_depth=35,split_seed=42,
                           split='sequential 10% test then 10% validation of remainder'),
             versions=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__)))
        dump(dest/'splits.json',splits);dump(dest/'feature_metadata.json',metadata)
        write_csv(dest/'predictions.csv',predictions);write_csv(dest/'importances.csv',importances)
        plot_and_conclude(q,models,importances,dest)
        from summarize import summarize
        summarize(dest)
    dump(output/'execution.json',dict(question=question,elapsed_seconds=time.monotonic()-start,
         inputs=str(inputs.resolve()),outputs=str(output.resolve()),questions=questions))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('question',choices=['ALL','Q1','Q2','Q3','Q4','Q5'])
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--jobs',type=int,default=4)
    a=p.parse_args();run(a.question,a.inputs,a.output,a.jobs)
