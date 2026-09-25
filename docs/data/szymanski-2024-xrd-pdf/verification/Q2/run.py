#!/usr/bin/env python3
"""One worked scientific analysis, not a required solver protocol.

The only data read are raw spectra and their companion metadata in --inputs.
All model choices below are this candidate's choices. Verification is model agnostic.
"""
import argparse
import csv
import hashlib
import json
import shutil
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import nnls
from scipy.special import softmax
from sklearn.linear_model import RidgeClassifier
from sklearn.svm import SVC

CHEMS = ['Li-La-Zr-O', 'Li-Ti-P-O']
THETA = np.linspace(10.02, 79.98, 2001)
R = np.linspace(1, 40, 1000)
SEED = 261025
REPS = ['XRD', 'PDF', 'Combined']
PRED_FIELDS = ['id', 'method', 'representation', 'condition', 'fold', 'predicted']
METRIC_FIELDS = ['method', 'representation', 'condition', 'fold', 'chemistry', 'group', 'metric', 'value', 'n']
NUMERICAL_METHODS = (
    'Numerical choices for this worked answer: linear interpolation onto 2,001 equally spaced two-theta points '
    'from 10.02 to 79.98 degrees; subtraction of each spectrum\'s tenth-percentile intensity followed by peak-height scaling; '
    'and unit L2 normalization of the features used for fitting and prediction. Negative residual intensities are retained. '
    'The virtual PDF is sampled on 1,000 equally spaced points from 1 to 40 Å and computed as '
    'G(r)=(2/pi) integral Q I(Q) sin(Qr) dQ with nonuniform-Q trapezoidal quadrature, '
    'Q=4pi sin(theta)/1.5406 Å, and theta half the recorded angle. This uncorrected transform is not a normalized physical PDF. '
    'The angular interval stays within the measured specimens\' support and provides one common domain for these illustrative analyses; '
    'the simulated-only analyses deliberately discard available higher-angle information. '
    'These analyst-selected preprocessing and truncation choices were not swept, so the conclusions do not establish insensitivity to them.'
)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def csvwrite(path, rows, fields=None):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load(inputs, chemistry, kind):
    stem = f'{chemistry}_{kind}'
    rows = json.loads((inputs / f'{stem}.json').read_text())
    with np.load(inputs / f'{stem}.npz', allow_pickle=False) as arrays:
        spectra = np.array([
            np.interp(THETA, arrays['theta'], arrays[row['id']])
            if 'theta' in arrays else
            np.interp(THETA, arrays[row['id']][:, 0], arrays[row['id']][:, 1])
            for row in rows
        ])
    return rows, spectra


def unit(values):
    return values / np.maximum(np.linalg.norm(values, axis=-1, keepdims=True), 1e-30)


def preprocess(values):
    values = values - np.percentile(values, 10, axis=-1, keepdims=True)
    return values / np.maximum(np.max(values, axis=-1, keepdims=True), 1e-30)


def kernel(distance):
    q = 4 * np.pi * np.sin(np.deg2rad(THETA / 2)) / 1.5406
    widths = np.empty(len(q))
    widths[0] = (q[1] - q[0]) / 2
    widths[-1] = (q[-1] - q[-2]) / 2
    widths[1:-1] = (q[2:] - q[:-2]) / 2
    return (2 / np.pi) * np.sin(distance[:, None] * q[None, :]) * (q * widths)[None, :]


def transform(values, distance=R):
    return values @ kernel(distance).T


def split(rows):
    """Disjoint repeats within phase, with no supplied benchmark split."""
    labels = np.array([row['phases'][0] for row in rows])
    role = np.full(len(rows), '', dtype='U10')
    rng = np.random.default_rng(SEED)
    for label in sorted(set(labels)):
        indexes = np.flatnonzero(labels == label)
        indexes = indexes[rng.permutation(len(indexes))]
        ntrain, nval = int(.6 * len(indexes)), max(1, int(.2 * len(indexes)))
        role[indexes[:ntrain]] = 'train'
        role[indexes[ntrain:ntrain+nval]] = 'validation'
        role[indexes[ntrain+nval:]] = 'test'
    return labels, role


def split_records(rows, roles):
    return [dict(id=row['id'], fold='0', role=str(role)) for row, role in zip(rows, roles)]


def prediction(row, method, representation, labels, condition='baseline'):
    return dict(id=row['id'], method=method, representation=representation,
                condition=condition, fold='0', predicted=sorted(labels))


def classification_metrics(question, predictions, metadata):
    lookup = {row['id']: row for row in metadata}
    grouped = {}
    for pred in predictions:
        row = lookup[pred['id']]
        group = ('all' if question in ('Q1', 'Q3') else
                 str(len(row['phases'])) if question == 'Q2' else
                 str(row['minor_weight_percent']))
        key = tuple(pred[field] for field in ['method', 'representation', 'condition', 'fold'])
        key += (row['chemistry'], group)
        grouped.setdefault(key, []).append((row, pred))
    metrics = []
    for key, pairs in sorted(grouped.items()):
        true_positive = false_positive = false_negative = exact = count_correct = minor = 0
        for row, pred in pairs:
            truth, guessed = set(row['phases']), set(pred['predicted'])
            true_positive += len(truth & guessed)
            false_positive += len(guessed - truth)
            false_negative += len(truth - guessed)
            exact += truth == guessed
            count_correct += len(truth) == len(guessed)
            if question == 'Q4':
                minor += row['minor'] in guessed
        values = dict(exact_match=exact/len(pairs),
                      micro_f1=2*true_positive/max(1, 2*true_positive+false_positive+false_negative))
        if question == 'Q2':
            values['phase_count_accuracy'] = count_correct/len(pairs)
        if question == 'Q4':
            values['minor_recall'] = minor/len(pairs)
        for metric, value in values.items():
            metrics.append(dict(zip(METRIC_FIELDS, (*key, metric, value, len(pairs)))))
    return metrics


def save_common(question, out, predictions, metadata, splits, design, report):
    csvwrite(out/'predictions.csv', [{**row, 'predicted': json.dumps(row['predicted'])} for row in predictions], PRED_FIELDS)
    metrics = classification_metrics(question, predictions, metadata)
    csvwrite(out/'metrics.csv', metrics, METRIC_FIELDS)
    csvwrite(out/'splits.csv', splits, ['id', 'fold', 'role'])
    write(out/'design.json', design)
    write(out/'result.json', dict(question=question, metrics=metrics))
    (out/'report.md').write_text('\n'.join(report)+'\n')
    shutil.copyfile(__file__, out/'run.py')
    return metrics


def model_fit(family, parameter, features, labels):
    if family == 'Ridge':
        return RidgeClassifier(alpha=parameter, solver='cholesky').fit(features, labels)
    return SVC(C=parameter, gamma='scale', decision_function_shape='ovr').fit(features, labels)


def class_scores(model, features):
    return softmax(model.decision_function(features), axis=1)


def paired_intervals(truth, predictions, classes):
    rng = np.random.default_rng(SEED)
    differences = {}
    for a, b in [('PDF', 'XRD'), ('Combined', 'XRD'), ('Combined', 'PDF')]:
        delta = (predictions[a] == truth).astype(float) - (predictions[b] == truth).astype(float)
        sums = np.array([delta[truth == label].sum() for label in classes])
        counts = np.array([(truth == label).sum() for label in classes])
        sampled = rng.integers(0, len(classes), size=(2000, len(classes)))
        resampled = sums[sampled].sum(axis=1) / counts[sampled].sum(axis=1)
        differences[f'{a}_minus_{b}'] = dict(difference=float(delta.mean()),
            cluster_bootstrap_95ci=list(map(float, np.quantile(resampled, [.025, .975]))))
    return differences


def cluster_interval(values, blocks):
    """Paired resampling preserves all observations of a sampled material block."""
    values, blocks = np.asarray(values, float), np.asarray(blocks)
    names = sorted(set(blocks))
    totals = np.array([values[blocks == name].sum() for name in names])
    counts = np.array([(blocks == name).sum() for name in names])
    draws = np.random.default_rng(SEED).integers(0, len(names), size=(2000, len(names)))
    statistic = totals[draws].sum(axis=1)/counts[draws].sum(axis=1)
    return dict(estimate=float(values.mean()), blocks=len(names),
                ci95=list(map(float,np.quantile(statistic,[.025,.975]))))


def q1(inputs, out):
    predictions, metadata, splits, evidence = [], [], [], []
    design = dict(seed=SEED, heldout_unit='augmented repeat within a known phase',
                  split='60% training, 20% validation, 20% test within each phase; seeded shuffle',
                  validation_objective='single-phase accuracy; ties prefer first parameter/weight',
                  learner_families=['Ridge', 'RBF-SVM'], bootstrap='2000 paired resamples of phase-identity blocks',
                  chemistry={})
    report = ['# Representation reliability and learner dependence', '',
        'This is one executed answer with analyst-chosen methods, not a benchmark-prescribed fitting recipe.', '',
        'Two distinct classifier families were trained and tuned separately on XRD and uncorrected sine-transform virtual PDFs. '
        'Hyperparameters and the XRD/PDF averaging weight were selected using validation spectra. '
        'Only then were the held-out test spectra scored. Both representations share the same test examples. '
        'The bootstrap resamples phase identities, carrying the repeated spectra for each phase together.', '', NUMERICAL_METHODS, '']
    figure, axes = plt.subplots(1, 2, figsize=(11, 4))
    for axis, chemistry in zip(axes, CHEMS):
        rows, raw = load(inputs, chemistry, '1-Phase')
        xrd = preprocess(raw)
        labels, roles = split(rows)
        classes = np.array(sorted(set(labels)))
        tr, va, te = [roles == role for role in ['train', 'validation', 'test']]
        features = {'XRD': unit(xrd), 'PDF': unit(transform(xrd))}
        testrows = [row for row, use in zip(rows, te) if use]
        splits += split_records(rows, roles)
        metadata += rows
        design['chemistry'][chemistry] = {}
        for family, parameters in [('Ridge', [.01, .1, 1., 10.]), ('RBF-SVM', [1., 10., 100.])]:
            validation, tested, selected = {}, {}, {}
            for representation in ['XRD', 'PDF']:
                candidates = []
                for parameter in parameters:
                    model = model_fit(family, parameter, features[representation][tr], labels[tr])
                    scores = class_scores(model, features[representation][va])
                    candidates.append((float((classes[scores.argmax(axis=1)] == labels[va]).mean()), parameter, model, scores))
                chosen = max(candidates, key=lambda item:item[0])
                selected[representation] = dict(parameter=chosen[1], validation_accuracy=chosen[0],
                    search=[dict(parameter=item[1], validation_accuracy=item[0]) for item in candidates])
                validation[representation] = chosen[3]
                tested[representation] = class_scores(chosen[2], features[representation][te])
            weights = [0., .25, .5, .75, 1.]
            weight_scores = [float((classes[(weight*validation['XRD']+(1-weight)*validation['PDF']).argmax(axis=1)] == labels[va]).mean()) for weight in weights]
            weight = weights[int(np.argmax(weight_scores))]
            tested['Combined'] = weight*tested['XRD']+(1-weight)*tested['PDF']
            predicted = {rep:classes[values.argmax(axis=1)] for rep, values in tested.items()}
            selected['combined_xrd_weight'] = weight
            selected['weight_validation_accuracy'] = dict(zip(map(str, weights), weight_scores))
            design['chemistry'][chemistry][family] = selected
            for representation in REPS:
                predictions += [prediction(row, family, representation, [label]) for row,label in zip(testrows, predicted[representation])]
            correct = {rep:predicted[rep] == labels[te] for rep in REPS}
            intervals = paired_intervals(labels[te], predicted, classes)
            complementarity = dict(both_correct=int((correct['XRD'] & correct['PDF']).sum()),
                xrd_only_correct=int((correct['XRD'] & ~correct['PDF']).sum()),
                pdf_only_correct=int((~correct['XRD'] & correct['PDF']).sum()),
                neither_correct=int((~correct['XRD'] & ~correct['PDF']).sum()))
            evidence.append(dict(chemistry=chemistry, method=family, n=len(testrows),
                complementarity=complementarity, comparisons=intervals))
            accuracies = [float(correct[rep].mean()) for rep in REPS]
            axis.plot(REPS, accuracies, 'o-', label=family)
            report.append(f'**{chemistry}, {family}.** Test accuracy: '+', '.join(f'{rep} {accuracy:.3f}' for rep,accuracy in zip(REPS,accuracies))+f'. Validation chose an XRD weight of {weight:.2f}.')
            report.append(f'Paired outcomes: {complementarity}.')
            for contrast, values in intervals.items():
                lo,hi = values['cluster_bootstrap_95ci']
                report.append(f'{contrast}: {values["difference"]:+.3f}, phase-block bootstrap 95% interval [{lo:+.3f}, {hi:+.3f}].')
            report.append('')
        axis.set(title=chemistry, ylabel='Held-out accuracy', ylim=(0, 1.03))
        axis.legend()
    for chemistry in CHEMS:
        compared = [row for row in evidence if row['chemistry'] == chemistry]
        deltas = [row['comparisons']['PDF_minus_XRD']['difference'] for row in compared]
        direction = ('PDF ranks above XRD under both learners' if min(deltas) > 0 else 'XRD ranks above PDF under both learners' if max(deltas) < 0 else 'the representation ranking changes with the learner')
        report.append(f'For {chemistry}, {direction}. The tested learner choices therefore '+('agree on the direction, although the uncertainty differs.' if min(deltas)*max(deltas)>0 else 'do not support a learner-independent representation advantage.'))
        combined = [row['comparisons']['Combined_minus_XRD']['difference'] > 0 and row['comparisons']['Combined_minus_PDF']['difference'] > 0 for row in compared]
        report.append(f'Fusion exceeds both standalone representations in {sum(combined)} of {len(combined)} tested learner families; it is not a consistent gain across learners.')
    report += ['', 'A representation-only claim requires the direction and size of its advantage to survive the learner comparison. '
        'A few discordant errors alone do not establish a reproducible fusion benefit; compare the paired intervals and both constituent baselines. '
        'The code reports all three contrasts, including when validation-selected fusion collapses to one representation.', '',
        'The test set holds out augmentations of known structures, not unseen chemical phases. '
        'The released spectra already contain simulation artifacts; their repeats may share generating assumptions. '
        'The uncorrected transform discards phase-space information through truncation and resampling and is not a normalized physical PDF. '
        'Small sample counts, training-set reuse, softmax score scale differences, and a single split constrain these conclusions. '
        'The phase-block interval addresses repeated-phase dependence in the test panel, not uncertainty over training a new model.', '',
        'All tuning values and split IDs are saved in design.json and splits.csv. comparison.json contains the paired uncertainty and discordant-error counts.']
    write(out/'comparison.json', evidence)
    per_class = []
    lookup = {row['id']:row for row in metadata}
    for chemistry in CHEMS:
        for method in ['Ridge','RBF-SVM']:
            for representation in REPS:
                subset = [row for row in predictions if lookup[row['id']]['chemistry']==chemistry and row['method']==method and row['representation']==representation]
                for label in sorted({lookup[row['id']]['phases'][0] for row in subset}):
                    selected = [row for row in subset if lookup[row['id']]['phases']==[label]]
                    per_class.append(dict(chemistry=chemistry,method=method,representation=representation,phase=label,n=len(selected),accuracy=float(np.mean([row['predicted']==[label] for row in selected]))))
    csvwrite(out/'per_class_accuracy.csv',per_class)
    figure.tight_layout(); figure.savefig(out/'diagnostics.png', dpi=150); plt.close(figure)
    return save_common('Q1', out, predictions, metadata, splits, design, report)


def coefficient_fit(references, target):
    references, target = unit(references), unit(target)
    gram = references @ references.T
    lower = np.linalg.cholesky(gram+1e-9*np.eye(len(references)))
    rhs = np.linalg.solve(lower, references @ target.T)
    coefficients = np.array([nnls(lower.T, vector, maxiter=10000)[0] for vector in rhs.T])
    return coefficients/np.maximum(coefficients.sum(axis=1, keepdims=True), 1e-30)


def generated_mixtures(xrd, labels, roles, formula=False):
    """Calibration uses validation repeats; fitting uses disjoint training repeats."""
    rng = np.random.default_rng(SEED+10+int(formula))
    classes = sorted(set(labels))
    pools = {label:np.flatnonzero((labels == label) & (roles == 'validation')) for label in classes}
    signals, truth = [], []
    for index in range(600):
        count = index%3+1
        selected = rng.choice(classes, count, replace=False)
        while formula and len({label.rsplit('_', 1)[0] for label in selected}) < count:
            selected = rng.choice(classes, count, replace=False)
        # Draw a broad intensity-contribution range; these are not weight fractions.
        weights = rng.dirichlet(np.ones(count)*1.5)
        components = xrd[[rng.choice(pools[label]) for label in selected]]
        mixture = weights @ components
        mixture += rng.normal(0, .002, len(THETA))
        signals.append(mixture)
        truth.append(set(label.rsplit('_',1)[0] for label in selected) if formula else set(selected))
    return np.array(signals), truth


def threshold_sets(scores, classes, threshold):
    guessed = []
    for score in scores:
        selected = np.flatnonzero(score >= threshold)
        if not len(selected):
            selected = [int(np.argmax(score))]
        guessed.append(set(classes[index] for index in selected))
    return guessed


def set_metrics(truth, predicted):
    tp = sum(len(a & b) for a,b in zip(truth,predicted))
    fp = sum(len(b-a) for a,b in zip(truth,predicted))
    fn = sum(len(a-b) for a,b in zip(truth,predicted))
    return dict(exact_match=float(np.mean([a == b for a,b in zip(truth,predicted)])),
                micro_f1=2*tp/max(1,2*tp+fp+fn),
                phase_count_accuracy=float(np.mean([len(a) == len(b) for a,b in zip(truth,predicted)])),
                mean_predicted_count=float(np.mean(list(map(len,predicted)))),
                false_positives=fp)


def aggregate_formulas(scores, classes):
    formulas = sorted({label.rsplit('_', 1)[0] for label in classes})
    aggregate = np.array([scores[:, [i for i,label in enumerate(classes) if label.rsplit('_',1)[0] == formula]].sum(axis=1) for formula in formulas]).T
    return aggregate, formulas


def q_mixture(question, inputs, out):
    predictions, metadata, splits = [], [], []
    design = dict(seed=SEED, training='60% single-phase repeats; 20% disjoint calibration repeats; remaining 20% unused',
        candidate_library='every simulated phase of the stated chemistry',
        calibration='600 generated mixtures, equally many one/two/three-phase; Dirichlet(1.5) intensity fractions; added Gaussian sigma0.002',
        cardinality='unknown; support threshold selected on generated calibration mixtures',
        model='NNLS of unit-norm phase-average templates; coefficients normalized to sum one',
        chemistry={})
    report = [f'# {"Unknown-cardinality mixture identification" if question == "Q2" else "Full-library simulation-to-measurement transfer"}', '',
        'This candidate infers both the phase set and its size. It uses all simulated phases of each chemistry. '
        'The true constituent count, measured abundance, experimental candidate identities, and test labels are unavailable to fitting and threshold selection. '
        'Phase-average templates use the training repeats. Thresholds and representation fusion are calibrated on 600 generated mixtures '
        'from separate validation repeats, with one, two, and three constituents in equal numbers. '
        'The calibration abundance is a spectral intensity contribution, not a mass fraction.', '', NUMERICAL_METHODS, '']
    figure, axes = plt.subplots(1, 2, figsize=(12, 4))
    detailed, uncertainty, error_examples = [], [], []
    for axis, chemistry in zip(axes, CHEMS):
        rows, raw = load(inputs, chemistry, '1-Phase')
        xrd = preprocess(raw)
        labels, roles = split(rows)
        classes = sorted(set(labels))
        templates = np.array([xrd[(roles == 'train') & (labels == label)].mean(axis=0) for label in classes])
        calibration, calibration_truth = generated_mixtures(xrd, labels, roles, formula=question == 'Q4')
        targetrows, targetraw = load(inputs, chemistry, 'Mixtures' if question == 'Q2' else 'Experiments')
        target = preprocess(targetraw)
        cal_scores, test_scores = {}, {}
        for representation, refs, cal, test in [('XRD',templates,calibration,target), ('PDF',transform(templates),transform(calibration),transform(target))]:
            cal_scores[representation] = coefficient_fit(refs, cal)
            test_scores[representation] = coefficient_fit(refs, test)
            if question == 'Q4':
                cal_scores[representation], formula_classes = aggregate_formulas(cal_scores[representation], classes)
                test_scores[representation], _ = aggregate_formulas(test_scores[representation], classes)
        if question == 'Q4':
            classes = formula_classes
        chosen = {}
        thresholds = [.01,.02,.03,.05,.075,.10,.15,.20,.25]
        for representation in REPS:
            trials = []
            for weight in ([0., .25, .5, .75, 1.] if representation == 'Combined' else [1. if representation == 'XRD' else 0.]):
                scores = weight*cal_scores['XRD']+(1-weight)*cal_scores['PDF']
                for threshold in thresholds:
                    stats = set_metrics(calibration_truth, threshold_sets(scores, classes, threshold))
                    trials.append(dict(xrd_weight=weight, threshold=threshold, **stats))
            best = max(trials, key=lambda row:(row['exact_match'], row['micro_f1']))
            chosen[representation] = dict(selected=best, search=trials)
            scores = best['xrd_weight']*test_scores['XRD']+(1-best['xrd_weight'])*test_scores['PDF']
            predicted = threshold_sets(scores, classes, best['threshold'])
            predictions += [prediction(row, 'NNLS', representation, found) for row, found in zip(targetrows, predicted)]
            truth = [set(row['phases']) for row in targetrows]
            overall = set_metrics(truth, predicted)
            blocks = ['+'.join(sorted(row['phases'])) for row in targetrows]
            exact_interval = cluster_interval([a==b for a,b in zip(truth,predicted)],blocks)
            uncertainty.append(dict(chemistry=chemistry,representation=representation,group='all',metric='exact_match',**exact_interval))
            # Formula/phase-count-stratified errors supplement the machine-scored metrics.
            detailed.append(dict(chemistry=chemistry, representation=representation, **overall))
            report.append(f'**{chemistry}, {representation}.** Calibrated support threshold {best["threshold"]:.3f}, XRD weight {best["xrd_weight"]:.2f}; '
                f'calibration exact match {best["exact_match"]:.3f}. Test exact match {overall["exact_match"]:.3f}, '
                f'micro-F1 {overall["micro_f1"]:.3f}, count accuracy {overall["phase_count_accuracy"]:.3f}, '
                f'mean predicted count {overall["mean_predicted_count"]:.2f}, false-positive constituent assignments {overall["false_positives"]}.')
            report.append(f'The exact-match 95% phase-set cluster-bootstrap interval is [{exact_interval["ci95"][0]:.3f}, {exact_interval["ci95"][1]:.3f}], based on {exact_interval["blocks"]} distinct phase-set blocks.')
            errors = [(row,found) for row,found in zip(targetrows,predicted) if set(row['phases'])!=found]
            # A few deterministic examples help expose failure modes without using them to tune.
            for row,found in errors[:3]:
                error_examples.append(dict(id=row['id'],chemistry=chemistry,representation=representation,
                    truth=json.dumps(sorted(row['phases'])),predicted=json.dumps(sorted(found)),
                    false_inclusions=json.dumps(sorted(found-set(row['phases']))),
                    false_exclusions=json.dumps(sorted(set(row['phases'])-found))))
            if errors:
                row,found = errors[0]
                report.append(f'Example {row["id"]}: false inclusions {sorted(found-set(row["phases"]))}; missing phases {sorted(set(row["phases"])-found)}. This is an evaluation example, not a case used for tuning.')
            if question == 'Q4':
                for weight in sorted({row['minor_weight_percent'] for row in targetrows}):
                    indexes=[i for i,row in enumerate(targetrows) if row['minor_weight_percent']==weight]
                    interval=cluster_interval([targetrows[i]['minor'] in predicted[i] for i in indexes],[blocks[i] for i in indexes])
                    uncertainty.append(dict(chemistry=chemistry,representation=representation,group=str(weight),metric='minor_recall',**interval))
            else:
                for count in [2,3]:
                    indexes=[i for i,row in enumerate(targetrows) if len(row['phases'])==count]
                    interval=cluster_interval([truth[i]==predicted[i] for i in indexes],[blocks[i] for i in indexes])
                    uncertainty.append(dict(chemistry=chemistry,representation=representation,group=str(count),metric='exact_match',**interval))
        design['chemistry'][chemistry] = dict(candidate_labels=classes, selection=chosen)
        splits += [entry for entry in split_records(rows, roles) if entry['role'] != 'test']
        splits += [dict(id=row['id'], fold='0', role='test') for row in targetrows]
        metadata += targetrows
        report.append('')
    metrics = classification_metrics(question, predictions, metadata)
    for axis, chemistry in zip(axes, CHEMS):
        for representation in REPS:
            selected = sorted([row for row in metrics if row['chemistry']==chemistry and row['representation']==representation and row['metric']==('minor_recall' if question=='Q4' else 'exact_match')], key=lambda row:float(row['group']))
            axis.plot([float(row['group']) for row in selected], [row['value'] for row in selected], 'o-', label=representation)
            report.append(f'{chemistry}, {representation}: '+', '.join(f'{row["group"]}: {row["value"]:.3f}' for row in selected)+(' (minor-phase recall by weight percent).' if question=='Q4' else ' (exact match by true constituent count).'))
        axis.set(title=chemistry, xlabel='Minor-phase weight percent' if question=='Q4' else 'True number of phases (evaluation only)', ylabel='Minor-phase recall' if question=='Q4' else 'Exact phase-set recovery', ylim=(0,1.03))
        axis.legend()
    report += ['', 'Threshold search, template library, and calibration results are saved in design.json; predictions can be rescored directly from source labels. '
        'A high constituent-level F1 can coexist with low exact-set recovery and incorrect constituent counts. '
        'Threshold transfer is itself part of the experiment: real release mixtures need not follow the synthetic calibration distribution. '
        'Test outcomes did not feed back into threshold selection.', '']
    report += ['Uncertainty resamples unordered phase sets as blocks, preserving repeated compositions and abundance observations. '
        'uncertainty.json contains 2,000-resample intervals for overall exact recovery and each count/abundance group. '
        'They describe variation in this panel and do not account for training or calibration uncertainty. '
        'At a boundary with no observed successes or failures, empirical bootstrap intervals can collapse to a point; '
        'this does not imply certainty about performance on future specimens. '
        'error_examples.csv records false inclusions and exclusions for three deterministic failures per chemistry/representation, when present.', '']
    if question == 'Q4':
        report += ['The experimental panel has only six unordered formula-pair blocks. Treating these as independent resampling units '
            'still ignores shared precursor identities across pairs, so the intervals give only a limited description of panel uncertainty.', '']
    if question == 'Q2':
        for chemistry in CHEMS:
            rows_for_chemistry=[row for row in detailed if row['chemistry']==chemistry]
            best=max(rows_for_chemistry,key=lambda row:row['exact_match'])
            report.append(f'{chemistry}: the highest observed overall exact recovery is {best["exact_match"]:.3f} ({best["representation"]}); even this method misses the full set in {1-best["exact_match"]:.1%} of mixtures. The larger third-phase loss and count errors show that identity ranking alone does not solve decomposition.')
        report += ['Changing the true number of phases also changes composition and relative intensities in these released mixtures. '
            'A two-versus-three-phase contrast is consequently descriptive, not a causal isolation of peak overlap. '
            'The model can return one or more constituents; it never truncates a ranking to the true count. '
            'Generated calibration mixtures use only single-phase spectra, and every released pooled mixture is held out.']
    else:
        for chemistry in CHEMS:
            records=[row for row in detailed if row['chemistry']==chemistry]
            standalone={row['representation']:row for row in records}
            report.append(f'{chemistry}: PDF exact recovery exceeds XRD by {standalone["PDF"]["exact_match"]-standalone["XRD"]["exact_match"]:+.3f}; combining scores changes it by {standalone["Combined"]["exact_match"]-standalone["PDF"]["exact_match"]:+.3f} relative to PDF. Full-library false positives and missed weak components limit transfer; the simulation-selected fusion weight does not establish an experimental improvement.')
        report += ['Polymorph coefficients were summed into formula scores before detection; no four-formula shortlist was used. '
            'There are only twelve specimens at each abundance within each chemistry, and ordered major/minor pairs recur across abundance. '
            'These measurements are not independent material families. False positives against the full simulation library matter as much as minor-phase recall. '
            'The curve is a panel-specific transfer assessment and does not establish a universal mass-fraction detection limit. '
            'Measured labels and weight fractions are used exclusively after the predictions for evaluation; simulation coefficients are not estimated mass fractions.']
    write(out/'additional_metrics.json', detailed)
    write(out/'uncertainty.json',uncertainty)
    csvwrite(out/'error_examples.csv',error_examples)
    figure.tight_layout(); figure.savefig(out/'diagnostics.png', dpi=150); plt.close(figure)
    return save_common(question, out, predictions, metadata, splits, design, report)


WINDOWS = {'r1_5':(1.,5.), 'r5_40':(5.,40.), 'r1_40':(1.,40.), 'r40_120':(40.,120.00001)}


def artifact_conditions():
    rows = [dict(condition='baseline', artifact='clean', description='Released simulated spectrum; no additional perturbation.')]
    for amplitude in [.01,.04]:
        for trial in range(3):
            rows.append(dict(condition=f'noise_{amplitude}_trial{trial}', artifact='noise', description=f'Independent additive Gaussian noise, standard deviation {amplitude} relative to preprocessed peak intensity; draw {trial}.'))
    for amplitude in [.05,.25]:
        rows.append(dict(condition=f'background_{amplitude}', artifact='background', description=f'Additive broad Gaussian background, peak {amplitude} relative to preprocessed peak intensity, center35 degrees and width12 degrees.'))
    return rows


def perturb(values, condition, seed):
    if condition == 'baseline':
        return values.copy()
    parts = condition.split('_')
    amplitude = float(parts[1])
    if parts[0] == 'noise':
        return values + np.random.default_rng(seed+int(parts[2].replace('trial',''))).normal(0, amplitude, values.shape)
    return values + amplitude*np.exp(-.5*((THETA-35)/12)**2)


def q3(inputs, out):
    chemistry = 'Li-Ti-P-O'
    rows, raw = load(inputs, chemistry, '1-Phase')
    xrd = preprocess(raw)
    labels, roles = split(rows)
    classes = np.array(sorted(set(labels)))
    tr, va, te = [roles==role for role in ['train','validation','test']]
    r = np.linspace(1,120,1191)
    transform_kernel = kernel(r)
    masks = {name:(r>=lo)&(r<hi) for name,(lo,hi) in WINDOWS.items()}
    conditions = artifact_conditions()
    testrows = [row for row,use in zip(rows,te) if use]
    models, validation, test_predictions, predictions = {}, {}, {}, []
    features = {'XRD':xrd, **{name:(xrd@transform_kernel.T)[:,mask] for name,mask in masks.items()}}
    parameters = [.01,.1,1.,10.]
    for feature, values in features.items():
        candidates = []
        for alpha in parameters:
            model = model_fit('Ridge',alpha,unit(values[tr]),labels[tr])
            accuracy = float((model.predict(unit(values[va]))==labels[va]).mean())
            candidates.append((accuracy,alpha,model))
        accuracy,alpha,model = max(candidates,key=lambda item:item[0])
        models[feature] = model
        validation[feature] = dict(alpha=alpha, clean_validation_accuracy=accuracy, condition_accuracy={})
    perturbation_evidence = {}
    clean_test_pdf = xrd[te]@transform_kernel.T
    # The first twelve held-out IDs are enough to independently check the numerical artifact evidence.
    evidence_count = min(12,len(testrows))
    distortion_records = []
    for cindex, condition in enumerate(conditions):
        name = condition['condition']
        valx = perturb(xrd[va], name, SEED+1000+cindex*100)
        testx = perturb(xrd[te], name, SEED+2000+cindex*100)
        valpdf, testpdf = valx@transform_kernel.T, testx@transform_kernel.T
        if name != 'baseline':
            perturbation_evidence[name] = (testx[:evidence_count], testpdf[:evidence_count])
        for feature in features:
            rep = 'XRD' if feature=='XRD' else 'PDF'
            method = 'Ridge' if feature=='XRD' else f'Ridge_{feature}'
            vfeatures = valx if feature=='XRD' else valpdf[:,masks[feature]]
            tfeatures = testx if feature=='XRD' else testpdf[:,masks[feature]]
            guessed = models[feature].predict(unit(tfeatures))
            validation[feature]['condition_accuracy'][name] = float((models[feature].predict(unit(vfeatures)) == labels[va]).mean())
            predictions += [prediction(row,method,rep,[label],condition=name) for row,label in zip(testrows,guessed)]
            test_predictions[(feature,name)] = guessed
            if name != 'baseline':
                clean = xrd[te] if feature=='XRD' else clean_test_pdf[:,masks[feature]]
                for i,row in enumerate(testrows):
                    distortion_records.append(dict(id=row['id'],condition=name,method=method,representation=rep,
                        relative_l2=float(np.linalg.norm(tfeatures[i]-clean[i])/max(1e-30,np.linalg.norm(clean[i]))),
                        signal_energy_fraction=1. if feature=='XRD' else float(np.sum(clean[i]**2)/max(1e-30,np.sum(clean_test_pdf[i]**2)))))
    # Give clean, noise, and background equal weight; noise draw count must not determine selection.
    for feature in validation:
        condition_values=validation[feature]['condition_accuracy']
        artifact_means={artifact:float(np.mean([condition_values[row['condition']] for row in conditions if row['artifact']==artifact])) for artifact in ['clean','noise','background']}
        validation[feature]['artifact_balanced_accuracy'] = float(np.mean(list(artifact_means.values())))
        validation[feature]['artifact_family_accuracy'] = artifact_means
    selected = max(WINDOWS,key=lambda name:validation[name]['artifact_balanced_accuracy'])
    figure,axes=plt.subplots(1,2,figsize=(12,4))
    metrics=classification_metrics('Q3',predictions,rows)
    report=['# Does artifact suppression preserve useful phase information?', '',
        f'All {len(classes)} Li-Ti-P-O simulated phases were included. The training, validation, and test repeats are disjoint within each phase. '
        'A ridge classifier was trained on clean released spectra in each representation, and its regularization was selected using clean validation spectra. '
        'Clean here means no newly added artifact: the released simulation already contains perturbations. '
        'Gaussian noise and broad smooth backgrounds were then added to validation and held-out test spectra separately. '
        'Candidate distance windows were compared using both phase-identification accuracy and distortion; retained signal energy is not a substitute for classification performance.', '',
        f'**Selected window: {selected}.** The selection maximized validation accuracy after equal weighting of clean, noise, and background artifact families. '
        'It did not use held-out classification labels. The complete window search is retained, so selection costs and failures are visible.', '']
    for feature in features:
        method='Ridge' if feature=='XRD' else f'Ridge_{feature}'
        values=[]
        for artifact in ['clean','noise','background']:
            chosen_conditions=[row['condition'] for row in conditions if row['artifact']==artifact]
            accuracy=float(np.mean([np.mean(test_predictions[(feature,name)]==labels[te]) for name in chosen_conditions]))
            values.append(accuracy)
        axes[0].plot(['clean','noise','background'],values,'o-',label=feature+(' (selected)' if feature==selected else ''))
        report.append(f'**{feature}.** Artifact-balanced validation accuracy {validation[feature]["artifact_balanced_accuracy"]:.3f}; '
            f'held-out accuracy clean/noise/background {values[0]:.3f}/{values[1]:.3f}/{values[2]:.3f}.')
    uncertainty=[]
    for artifact in ['clean','noise','background']:
        chosen_conditions=[row['condition'] for row in conditions if row['artifact']==artifact]
        delta=np.mean([(test_predictions[(selected,name)]==labels[te]).astype(float)-(test_predictions[('XRD',name)]==labels[te]).astype(float) for name in chosen_conditions],axis=0)
        interval=cluster_interval(delta,labels[te])
        uncertainty.append(dict(artifact=artifact,contrast=f'{selected}_minus_XRD',**interval))
        report.append(f'Selected-window minus XRD accuracy for {artifact}: {interval["estimate"]:+.3f}, phase-block bootstrap 95% interval [{interval["ci95"][0]:+.3f}, {interval["ci95"][1]:+.3f}]. Noise draws/severities are averaged within spectrum before resampling phase identities.')
    for artifact in ['noise','background']:
        heights=[]
        for feature in WINDOWS:
            rows_for_feature=[row for row in distortion_records if row['method']==f'Ridge_{feature}' and row['condition'].startswith(artifact)]
            heights.append(float(np.mean([row['relative_l2'] for row in rows_for_feature])))
        axes[1].plot(list(WINDOWS),heights,'o-',label=artifact)
    axes[0].set(ylabel='Held-out accuracy',ylim=(0,1.03));axes[0].legend(fontsize=8)
    axes[1].set(ylabel='Mean relative L2 distortion',xlabel='Distance window / Å');axes[1].legend()
    figure.tight_layout();figure.savefig(out/'diagnostics.png',dpi=150);plt.close(figure)
    selected_clean=float(np.mean(test_predictions[(selected,'baseline')]==labels[te]))
    full_clean=float(np.mean(test_predictions[('r1_40','baseline')]==labels[te]))
    report += ['', f'The validation-selected {selected} window changes clean held-out accuracy by {selected_clean-full_clean:+.3f} relative to the full 1–40 Å window. '
        'Its background comparison shows whether the loss of low-r information buys actual identification robustness rather than merely smaller numerical distortion. '
        'The phase-block confidence intervals above quantify that tradeoff on the held-out panel.', '',
        'A window is useful only when its apparent artifact resistance coincides with retained discriminatory information. '
        'The high-r window can contain little original signal and a large relative distortion, while a short low-r window can exclude distinguishing oscillations. '
        'The held-out curves determine which tradeoff actually works in this experiment; no universal optimal range is claimed.', '',
        'The 12-pattern evidence.npz audit subset stores the exact preprocessed clean XRD, perturbed XRD, clean virtual PDFs, perturbed virtual PDFs, '
        'and their axes and IDs. The other held-out predictions remain in predictions.csv. '
        'Perturbation arrays are indexed (condition, sample, feature); the conditions array omits baseline. '
        'PDF values use 2/pi times the trapezoidal integral of Q I(Q) sin(Qr) over the measured angular interval, with wavelength1.5406 Å. '
        'distortion.csv gives relative L2 change and retained clean-signal energy for each evaluated example and window. '
        'All generated noise draws and fitted models are reproducible from run.py and design.json.', '',
        'Limitations: one chemistry, one split, one learner family, two hand-chosen artifact families, two severity levels, and three noise draws per level. '
        'The broad Gaussian background is a controlled smooth contaminant, not a physical detector-background model. '
        'The virtual PDF is uncorrected and should not be interpreted as a quantitatively normalized real-space pair density. '
        'The observed selection is conditional on this artifact mixture and the finite angular range.']
    names=list(perturbation_evidence)
    np.savez_compressed(out/'evidence.npz',theta=THETA,r=r,ids=np.array([row['id'] for row in testrows[:evidence_count]]),conditions=np.array(names),
        clean_xrd=xrd[te][:evidence_count],clean_pdf=clean_test_pdf[:evidence_count],
        perturbed_xrd=np.stack([perturbation_evidence[name][0] for name in names]),perturbed_pdf=np.stack([perturbation_evidence[name][1] for name in names]))
    write(out/'evidence.json',dict(array_order='perturbed arrays: condition, sample, feature; clean arrays: sample,feature',
        windows={f'Ridge_{name}':[lo,hi] for name,(lo,hi) in WINDOWS.items()},
        source_preprocessing='Interpolate to theta, subtract 10th percentile per spectrum, divide by max.',
        transform='2/pi integral Q I(Q) sin(Qr) dQ; nonuniform-Q trapezoid; wavelength1.5406 Å',
        audit_subset='first twelve held-out IDs, selected before seeing predictions'))
    write(out/'uncertainty.json',uncertainty)
    csvwrite(out/'distortion.csv',distortion_records)
    csvwrite(out/'conditions.csv',conditions,['condition','artifact','description'])
    design=dict(seed=SEED, chemistry=chemistry, windows=WINDOWS, selected_window=selected,
        criterion='mean validation accuracy weighting clean/noise/background equally', conditions=conditions,
        regularization_and_window_search=validation,
        artifact_unit='relative to maximum intensity after subtracting tenth-percentile baseline and peak scaling')
    return save_common('Q3',out,predictions,rows,split_records(rows,roles),design,report)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('question',choices=['Q1','Q2','Q3','Q4','ALL'])
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    started=time.time()
    questions=['Q1','Q2','Q3','Q4'] if args.question=='ALL' else [args.question]
    for question in questions:
        out=args.output/question if args.question=='ALL' else args.output
        out.mkdir(parents=True,exist_ok=True)
        metrics=(q1(args.inputs,out) if question=='Q1' else q3(args.inputs,out) if question=='Q3' else q_mixture(question,args.inputs,out))
        print(question,json.dumps(dict(metric_rows=len(metrics),elapsed_seconds=time.time()-started)),flush=True)
    write(args.output/'execution.json',dict(questions=questions,elapsed_seconds=time.time()-started,
        input_directory=str(args.inputs.resolve()),candidate_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        numpy=np.__version__,scipy=__import__('scipy').__version__,sklearn=__import__('sklearn').__version__))

if __name__=='__main__':
    main()
