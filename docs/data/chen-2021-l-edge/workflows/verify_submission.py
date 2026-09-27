#!/usr/bin/env python3
"""Open-submission integrity routing, without imposing the worked protocol.

This checks the public output contract, native identities and composition
exclusion. It never awards a scientific pass. Unspecified geometry, spectral
definitions and models require independent numerical and scientific review.
Use verify.py only for the separately documented worked-example profile.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from verify import DEFAULT_INPUTS, load_truth


class NeedsMapping(Exception):
    """A valid alternative vocabulary/identity scheme needs evaluator mapping."""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(path):
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        result = list(reader)
    require(result and reader.fieldnames, f'Empty table: {path.name}')
    return result, reader.fieldnames


def column(headers, possibilities):
    return next((name for name in possibilities if name in headers), None)


def finite(value, label):
    number = float(value)
    require(math.isfinite(number), f'Nonfinite {label}')
    return number


def verify_submission(question, output, inputs=DEFAULT_INPUTS):
    output = Path(output)
    result = {'question': question, 'profile': 'open-submission', 'integrity_pass': False,
              'numerical_validation': 'partial', 'scientific_pass': None,
              'checks': {}, 'independent_review_required': [],
              'meaning': 'A pass covers only the checks explicitly listed. It is not correctness of a scientific answer or acceptance of a research method.'}
    pending = result['independent_review_required']
    try:
        require(question in {'Q1', 'Q2', 'Q3'}, 'Unknown question')
        truth = load_truth(str(Path(inputs).resolve()))
        site_rows, headers = rows(output / 'sites.csv')
        identity = column(headers, ['name', 'source_id', 'record', 'record_name'])
        site_map = {}
        if identity:
            for row in site_rows:
                name = row[identity]
                require(name in truth.records, 'Unknown native source identity: ' + name)
                native = truth.records[name]
                for field in ['material', 'element', 'edge']:
                    if field in row:
                        if field == 'material' and row[field] != native[field] and (row[field] not in truth.structures or native[field] in truth.inconsistent_materials):
                            raise NeedsMapping('Map custom/resolved material identifiers to each native record and its actual structure before checking source quantities.')
                        require(row[field] == native[field], 'Wrong source ' + field)
                if 'site' in row:
                    require(finite(row['site'], 'site') == native['site'], 'Wrong source absorbing index')
                site_map.setdefault(name, []).append(row)
            result['checks']['native_observation_rows'] = len(site_rows)
            result['checks']['distinct_native_records'] = len(site_map)
            if len(site_map) < len(site_rows):
                pending.append('Repeated source observations require declared condition/definition identifiers and a duplicate-versus-repeated-analysis audit.')
        else:
            pending.append('Map the submitted observation identifiers to native calculation names; the public prompt does not prescribe a sites.csv column vocabulary.')
        for row in site_rows:
            for field, value in row.items():
                if str(value).strip().lower() in {'nan', '+nan', '-nan', 'inf', '+inf', '-inf', 'infinity'}:
                    raise ValueError('Nonfinite site observation: ' + str(field))
        config_path = output / 'definitions.json'
        config = json.loads(config_path.read_text()) if config_path.exists() else {}
        if question == 'Q1':
            population = column(headers, ['multiplicity', 'population', 'weight'])
            if population and identity:
                included = [r for r in site_rows if r.get('included', '1').lower() not in {'0', 'false', 'no'}]
                require(included, 'No contributing site observations')
                for row in included:
                    require(finite(row[population], 'site population') > 0, 'Nonpositive site population')
                if population == 'multiplicity' and 'symprec_A' in config:
                    tolerance = finite(config['symprec_A'], 'symmetry tolerance')
                    require(tolerance > 0, 'Nonpositive symmetry tolerance')
                    checked = 0
                    for row in included:
                        native = truth.records[row[identity]]
                        if native['material'] in truth.inconsistent_materials:
                            pending.append('Independently validate how the material-identifier collision was resolved before accepting these populations.')
                            continue
                        expected = truth.multiplicity(native, tolerance, float(config.get('angle_tolerance_degrees', 5)))
                        require(finite(row[population], 'multiplicity') == expected, 'Incorrect declared crystallographic multiplicity')
                        checked += 1
                    result['checks']['source_multiplicities'] = checked
                else:
                    pending.append('Independently reconstruct declared populations from periodic geometry, accounting for normalization and the chosen symmetry definition.')
            else:
                pending.append('Identify and independently verify the reported site populations; no hidden population-column name is imposed.')
            with np.load(output / 'responses.npz', allow_pickle=False) as responses:
                require(responses.files, 'Empty material-response archive')
                checked = 0
                for key in responses.files:
                    a = np.asarray(responses[key], dtype=float)
                    require(a.ndim == 2 and a.shape[1] == 2 and len(a) >= 2, 'Response must have energy/intensity columns')
                    require(np.isfinite(a).all() and np.all(np.diff(a[:, 0]) > 0), 'Nonfinite or nonmonotone material response')
                    parts = key.split('__')
                    require(len(parts) == 3, 'Response key must be material__element__edge')
                    if tuple(parts) in truth.groups:
                        checked += 1
                    else:
                        pending.append('Validate non-native response group identity (for example a resolved material collision): ' + key)
                result['checks']['finite_monotone_responses'] = len(responses.files)
                result['checks']['native_response_groups'] = checked
            pending.append('Independently reconstruct material responses under the declared interpolation, support, population and exclusion conventions. Check complete crystallographic coverage, quantitative simplification effects and finite-resolution rankings. The worked-profile auditor is applicable only if those conventions match.')
        elif question == 'Q2':
            pending.append('Reconstruct structural labels and spectral observables under the submitted definitions directly from native coordinates/arrays; do not substitute the worked example definitions. Check chemical overlap, adjustment, dependent uncertainty and definition sensitivity, including every reported quantitative claim.')
        else:
            predictions, pred_headers = rows(output / 'predictions.csv')
            partitions, part_headers = rows(output / 'partitions.csv')
            require({'name', 'method', 'split', 'predicted'} <= set(pred_headers), 'Missing public prediction-contract columns')
            require({'material', 'method', 'split', 'role'} <= set(part_headers), 'Missing public partition-contract columns')
            roles = {}
            method_splits = set()
            for row in partitions:
                material, method, split, role = (row[k] for k in ['material', 'method', 'split', 'role'])
                if material not in truth.structures or material in truth.inconsistent_materials:
                    raise NeedsMapping('Partition uses custom or physically ambiguous material IDs; independently map them through native record names/structures before checking composition exclusion.')
                role = role.strip().lower().replace('-', '_').replace(' ', '_')
                role = {'training': 'train', 'development': 'validation', 'valid': 'validation', 'val': 'validation',
                        'holdout': 'test', 'held_out': 'test', 'evaluation': 'test', 'testing': 'test', 'excluded': 'unused'}.get(role, role)
                if role not in {'train', 'validation', 'test', 'unused'}:
                    raise NeedsMapping('Map the declared partition-role vocabulary to development, test and unused observations before checking leakage.')
                key = material, method, split
                require(key not in roles, 'Duplicate/conflicting material partition')
                roles[key] = role
                method_splits.add((method, split))
            for method, split in method_splits:
                development = {truth.compositions[m] for (m, a, b), role in roles.items() if (a, b) == (method, split) and role in {'train', 'validation'}}
                test = {truth.compositions[m] for (m, a, b), role in roles.items() if (a, b) == (method, split) and role == 'test'}
                require(not development & test, 'Composition leakage from development into test')
            seen = set()
            per_method = {}
            for row in predictions:
                name, method, split = (row[k] for k in ['name', 'method', 'split'])
                require(name in truth.records, 'Unknown prediction source name')
                require(row['predicted'].strip(), 'Empty prediction')
                require(row['predicted'].strip().lower() not in {'nan', '+nan', '-nan', 'inf', '+inf', '-inf', 'infinity'}, 'Nonfinite prediction label')
                key = name, method, split
                require(key not in seen, 'Duplicate prediction within method/split')
                seen.add(key)
                native = truth.records[name]
                require(roles.get((native['material'], method, split)) == 'test', 'Prediction is not assigned to its declared test partition')
                for field in ['material', 'element']:
                    if field in row:
                        require(row[field] == native[field], 'Prediction source identity mismatch')
                per_method.setdefault(method, []).append(row)
            result['checks']['native_predictions_in_test_partitions'] = len(predictions)
            result['checks']['composition_disjoint_method_splits'] = len(method_splits)
            result['checks']['method_names'] = sorted(per_method)
            label_field = column(headers, ['geometry', 'environment', 'reference_environment', 'label'])
            if identity and label_field:
                labels = {}
                for name, records in site_map.items():
                    values = {r[label_field] for r in records if r[label_field].strip()}
                    if len(values) == 1:
                        labels[name] = values.pop()
                scores = []
                for method, rr in per_method.items():
                    if not all(r['name'] in labels for r in rr):
                        continue
                    actual, predicted = [labels[r['name']] for r in rr], [r['predicted'] for r in rr]
                    scores.append({'method': method, 'n': len(rr), 'accuracy': float(accuracy_score(actual, predicted)),
                                   'balanced_accuracy': float(balanced_accuracy_score(actual, predicted)),
                                   'macro_f1': float(f1_score(actual, predicted, average='macro', zero_division=0))})
                result['checks']['metrics_against_submitted_labels_NOT_independent_geometry_truth'] = scores
            pending.append('Derive reference environments independently from native structures using the declared scientific definition. Audit spectra-only features, model selection, complete declared evaluation cohorts, repeated-condition identifiers, matched edge comparisons, chemistry controls, resolution and uncertainty. Scores against submitted labels above are arithmetic only, not validation of those labels.')
        result['checks']['report_files'] = sorted(p.name for p in output.iterdir() if p.suffix.lower() in {'.md', '.txt', '.pdf'})
        result['checks']['runnable_code_files'] = sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.suffix.lower() in {'.py', '.ipynb', '.r', '.jl', '.sh'})
        pending.append('Inspect the report, figures and runnable code; execute the analysis and apply scientific_review_rubric.md. Surface consistency alone never establishes scientific correctness. Missing or unsupported evidence cannot receive final acceptance.')
        result['integrity_pass'] = True
    except NeedsMapping as error:
        result['integrity_pass'] = None
        result['numerical_validation'] = 'pending_identifier_or_vocabulary_mapping'
        pending.append(str(error))
        pending.append('This is an unresolved representation mapping, not a demonstrated scientific error. Complete the independent mapping and source checks before acceptance.')
    except (AssertionError, ValueError, KeyError, TypeError, OSError, IndexError) as error:
        result['error'] = f'{type(error).__name__}: {error}'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', required=True, choices=['Q1', 'Q2', 'Q3'])
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify_submission(args.question, args.output, args.inputs)
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.report:
        args.report.write_text(text)
    print(text, end='')
    raise SystemExit(2 if result['integrity_pass'] is None else (0 if result['integrity_pass'] else 1))
