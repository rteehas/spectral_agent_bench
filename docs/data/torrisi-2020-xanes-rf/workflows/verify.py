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
ROLES = {'train', 'validation', 'test', 'excluded'}
# Names are conveniences for reading ordinary scientific tables, not required
# modeling choices. Shared extra columns named for experiments may also identify them.
IDENTIFIERS = ['run_id', 'model', 'condition', 'split_id', 'fold', 'repeat',
               'evaluation_id', 'representation', 'seed', 'experiment_id', 'trial']
COLUMN_ALIASES = {
    'prediction': 'y_pred', 'predicted': 'y_pred', 'predicted_value': 'y_pred',
    'truth': 'y_true', 'true_value': 'y_true', 'observed': 'y_true',
    'property': 'target', 'target_property': 'target',
    'run': 'run_id', 'method': 'model', 'estimator': 'model', 'model_id': 'model', 'model_name': 'model',
    'experiment': 'experiment_id', 'trial_id': 'trial',
    'partition': 'role', 'membership': 'role', 'dataset_role': 'role',
    'evaluation_split': 'split_id', 'split': 'split_id',
}
ROLE_ALIASES = {'training': 'train', 'validation': 'validation', 'valid': 'validation',
                'val': 'validation', 'testing': 'test', 'heldout': 'test',
                'held_out': 'test', 'exclude': 'excluded'}
TARGET_ALIASES = {'coordination': 'coord', 'coordination_number': 'coord',
                  'mean_neighbor_distance': 'md', 'mean_nearest_neighbor_distance': 'md',
                  'avg_nn_dists': 'md', 'distance': 'md',
                  'bader_charge': 'bader', 'charge': 'bader'}
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
        'Check the chosen class-imbalance intervention and the comparability of its evaluation, with uncertainty. Improvements in aggregate accuracy alone cannot establish improved minority-class discrimination.',
    ],
    'Q2': [
        'Independently reconstruct the submitted short-/long-distance or other justified tail cohorts from raw distances and the declared rule; check tail counts, errors, signed biases, baseline comparisons, and uncertainty.',
        'Require evidence assessing regression toward common distances and the support for extreme environments; overall MAE or R2 alone does not answer the question. Inspect the choice of diagnostic thresholds for test-driven selection.',
    ],
    'Q3': [
        'Reconstruct the white-line estimator from energy and absorption; ensure the white-line condition uses only that energy and the full condition uses spectral information, with no target-derived peak selection.',
        'Verify the charge-prediction comparison, its evaluation design, baselines, uncertainty, and evidence about deviations from a simple white-line relationship. Interpret the numerical released Bader label without inventing an unsupported oxidation-state mapping.',
    ],
    'Q4': [
        'Reconstruct the multiscale representation from E/mu and map descriptors or attributed intervals back to physical energy regions. The representation must actually encode more than one spectral scale.',
        'Verify predictive comparisons for all three targets and independent held-out perturbation/ablation or other defensible validation of attributed spectral information. Model importance rankings alone do not establish a physical mechanism.',
    ],
    'Q5': [
        'Reconstruct unit-peak normalization as mu/max(mu), verify defensible sample comparisons and otherwise comparable representations/learners, and check the handling of invalid maxima.',
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


def canonical_target(value):
    key = str(value).strip().lower().replace(' ', '_').replace('-', '_')
    return TARGET_ALIASES.get(key, key)


def table(path, required):
    frame = pd.read_csv(path, keep_default_na=False)
    require(len(frame) > 0, path.name + ': empty table')
    for old, new in COLUMN_ALIASES.items():
        if old not in frame:
            continue
        if new in frame:
            require((frame[old].astype(str) == frame[new].astype(str)).all(),
                    path.name + ': conflicting columns ' + old + '/' + new)
            frame = frame.drop(columns=old)
        else:
            frame = frame.rename(columns={old: new})
    # A column named "split" commonly describes either membership or a fold.
    if 'role' not in frame and 'split_id' in frame:
        possible = frame.split_id.astype(str).str.lower().map(lambda x: ROLE_ALIASES.get(x, x))
        if set(possible) <= ROLES:
            frame = frame.rename(columns={'split_id': 'role'})
    require(set(required) <= set(frame.columns), path.name + ': missing columns ' + str(set(required) - set(frame.columns)))
    if 'target' in frame:
        frame['target'] = frame.target.map(canonical_target)
    if 'role' in frame:
        frame['role'] = frame.role.astype(str).str.lower().map(lambda x: ROLE_ALIASES.get(x, x))
        require(set(frame.role) <= ROLES, path.name + ': unknown partition role')
    for name in IDENTIFIERS:
        if name in frame:
            frame[name] = frame[name].astype(str)
            require(frame[name].str.strip().ne('').all(), path.name + ': blank ' + name)
    return frame


def enrich(frame, design, question, label):
    """Resolve optional legacy run IDs; inline metadata must agree if provided."""
    runs = design.get('runs', [])
    if runs and 'run_id' in frame:
        require(all(isinstance(r, dict) and 'run_id' in r for r in runs), 'Invalid optional run metadata')
        roster = pd.DataFrame(runs)
        require(not roster.run_id.duplicated().any(), 'Duplicate optional run_id')
        roster['run_id'] = roster.run_id.astype(str)
        require(set(frame.run_id) <= set(roster.run_id), label + ': run_id absent from optional design')
        roster = roster.set_index('run_id')
        for key in ['element', 'target', 'condition', 'model', 'comparison_id', 'generalization']:
            if key not in roster:
                continue
            values = frame.run_id.map(roster[key])
            if key == 'target':
                values = values.map(canonical_target)
            if key in frame:
                require((frame[key].astype(str) == values.astype(str)).all(), label + ': contradictory ' + key)
            else:
                frame[key] = values
    if 'target' not in frame and len(TARGETS[question]) == 1:
        frame['target'] = TARGETS[question][0]
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
                r2=float(r2_score(truth, predictions)) if len(truth) >= 2 and np.ptp(truth) > 0 else None)


def artifacts(output):
    report = output / 'report.md'
    require(report.is_file() and report.read_text().strip(), 'Missing nonempty report.md')
    # Language and file naming are the submitter's choice. Whether these files
    # form executable source is checked by the mandatory independent rerun.
    code = [p for p in output.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts
            and p.suffix.lower() in {'.py', '.ipynb', '.r', '.jl', '.m', '.sh', '.c', '.cpp', '.rmd'}]
    require(code and any(p.stat().st_size for p in code), 'Missing runnable analysis source')
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
    design = read_json(output / 'design.json') if (output / 'design.json').exists() else {}
    require(isinstance(design, dict), 'Optional design.json must be an object')
    require(design.get('question', question) == question, 'Wrong question in optional design.json')
    predictions = enrich(table(output / 'predictions.csv', ['source_row', 'y_pred']), design, question, 'predictions')
    partitions = enrich(table(output / 'partitions.csv', ['source_row', 'role']), design, question, 'partitions')
    metrics = (enrich(table(output / 'metrics.csv', ['metric', 'value']), design, question, 'metrics')
               if (output / 'metrics.csv').exists() else None)
    for frame, name in [(predictions, 'predictions'), (partitions, 'partitions')]:
        row_ids(frame, name)
        require('element' in frame, name + ': element is needed to identify source records')
        require(set(frame.element) <= set(ELEMENTS), name + ': unknown element')
    require('target' in predictions, 'Multiple target properties: identify the property in predictions')
    require(set(predictions.target) <= set(TARGETS[question]), 'Prediction target outside this question')
    require(np.isfinite(pd.to_numeric(predictions.y_pred, errors='raise')).all(), 'Nonfinite prediction')
    if metrics is not None:
        require(np.isfinite(pd.to_numeric(metrics.value, errors='raise')).all(), 'Nonfinite optional metric')
    artifact_evidence = artifacts(output)
    # Shared experiment identifiers can have arbitrary values. Partitions may
    # omit model/target columns when one assignment applies to several models.
    ignored = {'source_row', 'role', 'y_pred', 'y_true', 'element', 'target',
               'comparison_id', 'generalization', 'metric', 'value'}
    shared_extra = sorted(key for key in (set(predictions) & set(partitions)) - ignored - set(IDENTIFIERS)
                          if any(token in key.lower() for token in ['model', 'method', 'experiment', 'trial', 'split', 'fold', 'run', 'repeat', 'condition', 'representation']))
    identifiers = [key for key in IDENTIFIERS if key in predictions] + shared_extra
    keys = ['element', 'target'] + identifiers
    require(not predictions.duplicated(keys + ['source_row']).any(),
            'Duplicate predictions; identify distinct models or evaluation splits if needed')
    partition_keys = ['element'] + [key for key in ['target'] + identifiers if key in partitions]
    require(not partitions.duplicated(partition_keys + ['source_row']).any(),
            'Overlapping or repeated row memberships; identify evaluation splits if needed')
    checks, comparisons, coverage, input_hashes, used_partition_indices, used_metric_indices = [], {}, set(), {}, set(), set()
    for identity, pred in predictions.groupby(keys, dropna=False, sort=False):
        identity = identity if isinstance(identity, tuple) else (identity,)
        run = dict(zip(keys, identity))
        element, target = run['element'], run['target']
        name = str(run.get('run_id', '|'.join(str(run[k]) for k in keys)))
        part = partitions
        for key in partition_keys:
            part = part[part[key].astype(str) == str(run[key])]
        require(len(part) > 0, name + ': missing data partition')
        used_partition_indices.update(part.index)
        part = part.set_index('source_row').sort_index()
        pred = pred.set_index('source_row').sort_index()
        raw, sha = load_raw(inputs, element)
        input_hashes[element] = sha
        require(set(part.index) <= set(raw), name + ': partition references unknown source rows')
        active = part[part.role != 'excluded']
        role_rows = {role: set(part.index[part.role == role]) for role in sorted(ROLES)}
        truth_by_row = {}
        # Auxiliary spectra may legitimately be used without labels during
        # representation learning. Only scored test rows require target truth.
        auxiliary_labels = {role: 0 for role in ['train', 'validation']}
        for role in ['train', 'validation', 'test']:
            for source_row in role_rows[role]:
                value = raw[int(source_row)][target]
                usable = (isinstance(value, (int, float)) and not isinstance(value, bool)
                          and np.isfinite(value) and (target != 'coord' or value in [4, 5, 6]))
                if role == 'test':
                    require(usable, name + ': scored test row lacks a finite in-scope raw target')
                    truth_by_row[int(source_row)] = float(value)
                elif not usable:
                    auxiliary_labels[role] += 1
        require(role_rows['train'] and role_rows['test'], name + ': empty training or test set')
        require(set(pred.index) == role_rows['test'], name + ': predictions do not cover exactly the declared test rows')
        truth = np.asarray([truth_by_row[int(i)] for i in pred.index])
        if 'y_true' in pred:
            np.testing.assert_allclose(pd.to_numeric(pred.y_true), truth, rtol=0, atol=1e-12,
                                       err_msg=name + ': truth labels differ from raw release')
        materials = {role: {str(raw[int(i)]['material_id']) for i in role_rows[role]
                            if raw[int(i)]['material_id'] is not None and str(raw[int(i)]['material_id']).strip()}
                     for role in ['train', 'validation', 'test']}
        missing = {role: sum(raw[int(i)]['material_id'] is None or not str(raw[int(i)]['material_id']).strip()
                             for i in role_rows[role]) for role in ['train', 'validation', 'test']}
        overlaps = {a + '_' + b: len(materials[a] & materials[b])
                    for a, b in [('train', 'test'), ('train', 'validation'), ('validation', 'test')]}
        claims = {}
        for key in ['generalization', 'comparison_id']:
            values = set()
            for frame in [pred, part]:
                if key in frame:
                    values.update(frame[key].astype(str))
            require(len(values) <= 1, name + ': contradictory optional ' + key)
            if values:
                claims[key] = next(iter(values))
        if claims.get('generalization') == 'identified_material':
            require(sum(missing.values()) == 0, name + ': explicit identified_material claim includes missing material IDs')
            require(not any(overlaps.values()), name + ': explicit identified_material claim contradicts partition overlap')
        calculated = recompute_metrics(target, truth, pd.to_numeric(pred.y_pred).to_numpy())
        additional = []
        if metrics is not None:
            selected = metrics
            for key in keys:
                if key in selected:
                    selected = selected[selected[key].astype(str) == str(run[key])]
            # A metric table without enough experiment identifiers is ambiguous;
            # it is not silently assigned to every experiment.
            require(not selected.metric.duplicated().any(), name + ': optional metrics need model/split identifiers')
            used_metric_indices.update(selected.index)
            aliases = {'mean_absolute_error': 'mae', 'r2_score': 'r2', 'f1_macro': 'macro_f1'}
            for item in selected.itertuples():
                metric = aliases.get(str(item.metric).lower(), str(item.metric).lower())
                if metric in calculated:
                    expected = calculated[metric]
                    require(expected is not None and np.isclose(float(item.value), expected, atol=1e-8, rtol=1e-7),
                            name + ': inconsistent optional ' + metric)
                else:
                    additional.append(str(item.metric))
        if 'comparison_id' in claims:
            # This historical optional declaration explicitly claims identical
            # row inclusion and assignments. Unpaired studies need not supply it.
            group_key = (element, target, claims['comparison_id'])
            group = comparisons.setdefault(group_key, [])
            for other in group:
                require(part.role.equals(other), name + ': optional paired comparison changes partition assignments')
            group.append(part.role)
        coverage.add((element, target))
        checks.append(dict(run_id=name, experiment=run, source_labels='read directly from supplied element records',
                           partitions={role: len(rows) for role, rows in role_rows.items()},
                           supplied_rows_not_listed=len(set(raw) - set(part.index)),
                           auxiliary_rows_without_in_scope_target=auxiliary_labels,
                           distinct_material_ids={role: len(v) for role, v in materials.items()},
                           material_id_overlap=overlaps, rows_without_material_id=missing,
                           active_rows_without_material_id=int(sum(missing.values())),
                           active_source_counts=pd.Series([raw[int(i)]['origin'] for i in active.index]).value_counts(dropna=False).to_dict(),
                           optional_claims=claims, metrics_recomputed=calculated,
                           additional_metrics_requiring_review=sorted(set(additional))))
    require(used_partition_indices == set(partitions.index), 'Partition rows reference experiments without predictions')
    if metrics is not None:
        require(used_metric_indices == set(metrics.index), 'Optional metric rows reference experiments without predictions')
    expected = {(element, target) for element in ELEMENTS for target in TARGETS[question]}
    require(coverage == expected, 'Missing requested elements/properties: ' + str(sorted(expected - coverage)))
    return dict(question=question, numerical_integrity_pass=True, scientific_pass=None,
                status='scientific_review_required', run_count=len(checks), comparison_count=len(comparisons),
                source_input_sha256=input_hashes, artifacts=artifact_evidence, checks=checks,
                required_independent_review=REVIEW['common'] + REVIEW[question],
                interpretation='Passing establishes source-row/label/partition consistency and recalculates scores. Material-ID overlap and missing IDs are reported; a grouped-material split is not required. Optional explicit pairing/generalization claims and recognized scores are checked if supplied. This does not prove code used those partitions, prevent fabricated predictions, validate scientific conclusions, or accept an investigation. Independent code rerun and scientific review remain necessary. No archived result or prescribed modeling recipe is an acceptance target.')


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
