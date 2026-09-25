#!/usr/bin/env python3
"""Evaluator-only numerical checks for method-flexible XANES investigations.

Exit 0 means that the declared artifacts are numerically consistent with the
released rows, NOT that the scientific investigation passes. Final acceptance
requires the independent scientific/code review listed in the returned report.
No archived prediction, split, feature vector, hyperparameter, or score is used
as an acceptance target. Never execute an untrusted submission from this check.
"""
import argparse
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score

ELEMENTS = ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']
DEFAULT_INPUT = Path(__file__).resolve().parents[1] / 'inputs'
TARGET_FIELDS = {'coord': 'coordination', 'md': 'avg_nn_dists', 'bader': 'bader'}
TARGETS = {'Q1': ['coord'], 'Q2': ['md'], 'Q3': ['bader'],
           'Q4': ['coord', 'md', 'bader'], 'Q5': ['coord', 'md']}
CONDITIONS = {'Q1': {'untreated', 'treated'}, 'Q2': {'model'},
              'Q3': {'full', 'white_line'}, 'Q4': {'pointwise', 'multiscale'},
              'Q5': {'released', 'unit_peak'}}
ROLES = {'train', 'validation', 'test', 'excluded'}
GENERALIZATION = {'spectrum', 'identified_material'}
REVIEW = {
    'common': [
        'Rerun submitted code from the supplied raw records in a clean environment. Compare the regenerated partitions, predictions, metrics, and supporting tables to the submission; recording a command alone is insufficient.',
        'Inspect feature construction and fitting: target labels, label-derived metadata, held-out labels, and material identities must not enter spectral predictors. Every fitted transformation, feature selection, class adjustment, tuning decision, and model selection must use training/validation data only.',
        'Check filtering and split design, material-identifier coverage, source composition, duplicate/related spectra, and uncertainty. Known IDs occur only for one released origin; identified-material results cannot establish generalization to every source or to unidentified materials. Disjoint declared row IDs do not prove absence of other leakage. Small tail cohorts or missing coordination classes must not be presented as strong evidence of reliability.',
        'Check that comparison conditions actually implement their declared interventions, keep the scientific comparison fair, and receive defensible tuning effort. Equal partition files alone cannot establish this.',
        'Require substantive spectral modeling and justified baselines, adequate held-out evidence, uncertainty, reproducible figures, and conclusions supported by the results. Negative results are valid when their design and evidence are sound; no fixed accuracy threshold or agreement with an archived model is required.',
    ],
    'Q1': [
        'Assess whether the spectral evidence distinguishes coordination classes 4/5/6 beyond class prevalence; verify class support, confusion patterns, an appropriate prevalence baseline, and minority-class performance.',
        'Check the chosen class-imbalance intervention and paired changes with uncertainty. Improvements in aggregate accuracy alone cannot establish improved minority-class discrimination.',
    ],
    'Q2': [
        'Independently reconstruct the submitted short-/long-distance or other justified tail cohorts from raw distances and the declared rule; check tail counts, errors, signed biases, baseline comparisons, and uncertainty.',
        'Require evidence assessing regression toward common distances and the support for extreme environments; overall MAE or R2 alone does not answer the question. Inspect the choice of diagnostic thresholds for test-driven selection.',
    ],
    'Q3': [
        'Reconstruct the white-line estimator from energy and absorption; ensure the white-line condition uses only that energy and the full condition uses spectral information, with no target-derived peak selection.',
        'Verify the paired charge-prediction comparison, baselines, uncertainty, and evidence about deviations from a simple white-line relationship. Interpret the numerical released Bader label without inventing an unsupported oxidation-state mapping.',
    ],
    'Q4': [
        'Reconstruct the multiscale representation from E/mu and map descriptors or attributed intervals back to physical energy regions. The representation must actually encode more than one spectral scale.',
        'Verify predictive comparisons for all three targets and independent held-out perturbation/ablation or other defensible validation of attributed spectral information. Model importance rankings alone do not establish a physical mechanism.',
    ],
    'Q5': [
        'Reconstruct unit-peak normalization as mu/max(mu), verify paired sample coverage and otherwise comparable representations/learners, and check the handling of invalid maxima.',
        'Check predictive changes for both targets separately from stability of the inferred informative energy regions/features; recompute the submitted stability evidence and validate important regions with held-out perturbation/ablation or another justified check. Compare physical energy regions or consistently defined descriptors, not arbitrary coefficient indices from incompatible representations.',
    ],
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


@lru_cache(maxsize=16)
def _read_raw_cached(path, mtime_ns, size):
    del mtime_ns, size  # Cache key invalidates when a file changes.
    rows = {}
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            record = json.loads(line)
            row = record['source_row']
            require(isinstance(row, int) and not isinstance(row, bool) and row >= 0,
                    'Raw input has invalid source_row')
            require(row not in rows, 'Raw input repeats a source_row')
            metadata = record.get('metadata') or {}
            rows[row] = {target: record.get(field) for target, field in TARGET_FIELDS.items()}
            rows[row].update(material_id=metadata.get('id'), origin=metadata.get('origin'))
    return rows, digest(path)


def load_raw(inputs, element):
    path = (Path(inputs) / (element + '.jsonl.gz')).resolve()
    stat = path.stat()
    return _read_raw_cached(str(path), stat.st_mtime_ns, stat.st_size)


def table(path, columns, identities):
    frame = pd.read_csv(path, keep_default_na=False)
    require(set(columns).issubset(frame.columns), path.name + ': missing required columns')
    require(len(frame) > 0, path.name + ': empty table')
    require(not frame.duplicated(identities).any(), path.name + ': duplicate identities')
    return frame


def row_ids(frame, label):
    values = pd.to_numeric(frame.source_row, errors='raise').to_numpy(dtype=float)
    require(np.isfinite(values).all() and (values >= 0).all()
            and np.equal(values, np.floor(values)).all(), label + ': invalid source_row')
    frame['source_row'] = values.astype(np.int64)


def recompute_metrics(target, truth, predictions):
    truth, predictions = np.asarray(truth), np.asarray(predictions)
    if target == 'coord':
        require(np.isin(predictions, [4, 5, 6]).all(),
                'Coordination predictions must be class labels 4, 5, or 6')
        scores = f1_score(truth, predictions, labels=[4, 5, 6], average=None, zero_division=0)
        return dict(accuracy=float(accuracy_score(truth, predictions)),
                    macro_f1=float(np.mean(scores)),
                    **{f'f1_{k}': float(v) for k, v in zip([4, 5, 6], scores)})
    return dict(mae=float(mean_absolute_error(truth, predictions)),
                r2=float(r2_score(truth, predictions)))


def artifacts(output):
    report = output / 'report.md'
    require(report.is_file() and report.read_text().strip(), 'Missing nonempty report.md')
    # Language and file naming are the submitter's choice. Whether these files
    # form executable source is checked by the mandatory independent rerun.
    code = [p for p in (output / 'code').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    require(code and any(p.stat().st_size for p in code), 'Missing reproducible source in code/')
    plots = [p for p in output.rglob('*')
             if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.svg', '.pdf'}]
    require(plots, 'Missing a figure')
    for plot in plots:
        if plot.suffix.lower() == '.svg':
            require(ET.parse(plot).getroot().tag.endswith('svg'), 'Invalid SVG figure')
        elif plot.suffix.lower() == '.pdf':
            require(plot.read_bytes().startswith(b'%PDF-'), 'Invalid PDF figure')
        else:
            from PIL import Image
            with Image.open(plot) as img:
                img.verify()
    return dict(report_sha256=digest(report), code_files={str(p.relative_to(output)): digest(p) for p in code},
                figures=[str(p.relative_to(output)) for p in plots])


def verify(question, output, inputs=DEFAULT_INPUT):
    require(question in TARGETS, 'Unknown question')
    output, inputs = Path(output), Path(inputs)
    design = read_json(output / 'design.json')
    require(design.get('question') == question, 'Wrong question in design.json')
    runs = design.get('runs')
    require(isinstance(runs, list) and runs, 'design.json: runs must be a nonempty list')
    required = {'run_id', 'element', 'target', 'condition', 'comparison_id', 'generalization'}
    for run in runs:
        require(isinstance(run, dict) and required.issubset(run), 'Incomplete run declaration')
        require(all(isinstance(run[k], str) and run[k].strip() for k in required),
                'Run identifiers and declarations must be nonempty strings')
        require(run['element'] in ELEMENTS, 'Unknown element')
        require(run['target'] in TARGETS[question], 'Target is outside this question')
        require(run['generalization'] in GENERALIZATION, 'Unknown generalization claim')
    ids = {r['run_id'] for r in runs}
    require(len(ids) == len(runs), 'Duplicate run_id')
    predictions = table(output / 'predictions.csv', ['run_id', 'source_row', 'y_pred'], ['run_id', 'source_row'])
    partitions = table(output / 'partitions.csv', ['run_id', 'source_row', 'role'], ['run_id', 'source_row'])
    metrics = table(output / 'metrics.csv', ['run_id', 'metric', 'value'], ['run_id', 'metric'])
    row_ids(predictions, 'predictions.csv')
    row_ids(partitions, 'partitions.csv')
    for frame, name in [(predictions, 'predictions'), (partitions, 'partitions'), (metrics, 'metrics')]:
        require(set(frame.run_id) == ids, name + ': missing or undeclared runs')
    require(set(partitions.role) <= ROLES, 'Unknown partition role')
    require(np.isfinite(pd.to_numeric(predictions.y_pred, errors='raise')).all(), 'Nonfinite prediction')
    require(np.isfinite(pd.to_numeric(metrics.value, errors='raise')).all(), 'Nonfinite metric')
    artifact_evidence = artifacts(output)
    comparisons, checks, coverage, input_hashes = {}, [], set(), {}
    for run in runs:
        name, element, target = run['run_id'], run['element'], run['target']
        raw, sha = load_raw(inputs, element)
        input_hashes[element] = sha
        part = partitions[partitions.run_id == name].set_index('source_row').sort_index()
        require(set(part.index) == set(raw), name + ': partitions must account for every supplied element row')
        active = part[part.role != 'excluded']
        truth_by_row = {}
        for source_row in active.index:
            value = raw[int(source_row)][target]
            require(isinstance(value, (int, float)) and not isinstance(value, bool) and np.isfinite(value),
                    name + ': active row lacks a finite raw target')
            require(target != 'coord' or value in [4, 5, 6], name + ': active coordination label outside 4/5/6')
            truth_by_row[int(source_row)] = float(value)
        role_rows = {role: set(part.index[part.role == role]) for role in ROLES}
        require(role_rows['train'] and len(role_rows['test']) >= 2, name + ': empty training set or fewer than two test rows')
        materials = {role: {str(raw[int(i)]['material_id']) for i in role_rows[role]
                            if raw[int(i)]['material_id'] is not None and str(raw[int(i)]['material_id']).strip()}
                     for role in ['train', 'validation', 'test']}
        missing_ids = sum(raw[int(i)]['material_id'] is None or not str(raw[int(i)]['material_id']).strip()
                          for i in active.index)
        overlaps = {a + '_' + b: len(materials[a] & materials[b])
                    for a, b in [('train', 'test'), ('train', 'validation'), ('validation', 'test')]}
        if run['generalization'] == 'identified_material':
            require(missing_ids == 0, name + ': identified_material run contains rows without material IDs')
            require(not any(overlaps.values()), name + ': material identity leaks between declared partitions')
        pred = predictions[predictions.run_id == name].set_index('source_row').sort_index()
        require(set(pred.index) == role_rows['test'], name + ': predictions do not cover exactly the declared test rows')
        truth = np.asarray([truth_by_row[int(i)] for i in pred.index])
        require(target == 'coord' or np.ptp(truth) > 0, name + ': test targets are constant; R2 is uninformative')
        # Redundant columns are optional, but may not contradict the raw source/roster.
        for column, expected in [('element', element), ('target', target)]:
            if column in pred:
                require((pred[column] == expected).all(), name + ': contradictory ' + column)
        if 'y_true' in pred:
            np.testing.assert_allclose(pd.to_numeric(pred.y_true), truth, rtol=0, atol=1e-12,
                                       err_msg=name + ': truth labels differ from raw release')
        calculated = recompute_metrics(target, truth, pd.to_numeric(pred.y_pred).to_numpy())
        declared = metrics[metrics.run_id == name].set_index('metric').value
        require(set(calculated) <= set(declared.index), name + ': missing core metrics')
        for metric, expected in calculated.items():
            require(np.isclose(float(declared[metric]), expected, atol=1e-8, rtol=1e-7),
                    name + ': inconsistent ' + metric)
        group_key = (element, target, run['generalization'], run['comparison_id'])
        group = comparisons.setdefault(group_key, [])
        require(not any(other['condition'] == run['condition'] for other, _ in group),
                name + ': duplicate condition within a comparison')
        for other, other_part in group:
            require(part.role.equals(other_part.role),
                    name + ': paired comparison changes row inclusion or partition assignments')
        group.append((run, part))
        checks.append(dict(run_id=name, source_labels='read directly from supplied element records',
                           partitions={role: len(rows) for role, rows in role_rows.items()},
                           distinct_material_ids={role: len(v) for role, v in materials.items()},
                           material_id_overlap=overlaps, active_rows_without_material_id=int(missing_ids),
                           active_source_counts=pd.Series([raw[int(i)]['origin'] for i in active.index]).value_counts(dropna=False).to_dict(),
                           metrics_recomputed=calculated,
                           additional_metrics_requiring_review=sorted(set(declared.index) - set(calculated))))
    for (element, target, generalization, comparison_id), group in comparisons.items():
        if generalization == 'identified_material' and CONDITIONS[question] <= {run['condition'] for run, _ in group}:
            coverage.add((element, target))
    expected_coverage = {(element, target) for element in ELEMENTS for target in TARGETS[question]}
    require(coverage == expected_coverage,
            'Missing identified-material investigation/paired conditions for: ' + str(sorted(expected_coverage - coverage)))
    return dict(question=question, numerical_integrity_pass=True, scientific_pass=None,
                status='scientific_review_required', run_count=len(runs), comparison_count=len(comparisons),
                source_input_sha256=input_hashes, artifacts=artifact_evidence, checks=checks,
                required_independent_review=REVIEW['common'] + REVIEW[question],
                interpretation='Passing this check establishes declared row/label/partition consistency and core score arithmetic only. It cannot prove the fitted code used those partitions, prevent fabricated predictions, validate optional diagnostic tables, or judge scientific conclusions. Final acceptance requires an independent code rerun and all scientific rubric items; archived results are illustrative, never numeric pass thresholds.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question', choices=list(TARGETS))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--inputs', default=DEFAULT_INPUT, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.question, args.output, args.inputs), indent=2))
    except (AssertionError, KeyError, ValueError, TypeError, OSError) as exc:
        raise SystemExit('Numerical integrity check failed: ' + str(exc))


if __name__ == '__main__':
    main()
