#!/usr/bin/env python3
"""Independent output integrity checks; scientific review remains mandatory.

Q1 uses the authors' held-back material spectra, never the candidate workflow.
Q2/Q3 decode structures and calculation energies independently from raw inputs.
Geometry conventions are evaluator arguments, not an estimator prescription.
The checker neither executes submitted code nor grades scientific reasoning.
"""
import argparse
import csv
import gzip
import itertools
import json
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar

DATA = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def table(path, required):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        require(len(fields) == len(set(fields)), f'Duplicate columns: {path}')
        require(set(required) <= set(fields), f'Missing columns: {set(required) - set(fields)}')
        rows = list(reader)
    require(rows, f'Empty table: {path}')
    require(all(None not in row and all(value is not None for value in row.values()) for row in rows), f'Malformed table: {path}')
    return rows


def material(value):
    text = str(value).strip()
    require(re.fullmatch(r'(?:m)?\d+', text) is not None, f'Invalid material: {value}')
    return f'{int(text.lstrip("m")):03d}'


def number(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise AssertionError(f'Non-numeric {name}: {value}') from exc
    require(np.isfinite(result), f'Non-finite {name}')
    return result


def total_energy(text):
    matches = re.findall(r'\bE0\s*=\s*([+\-\.\dEe]+)', text)
    require(matches, 'No final E0 in OSZICAR')
    return float(matches[-1])


def poscar(text):
    """Small independent VASP5 parser, including duplicate S species groups."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    scale = float(lines[1])
    cell = np.array([[float(x) for x in line.split()[:3]] for line in lines[2:5]])
    scale = (-scale / abs(np.linalg.det(cell))) ** (1 / 3) if scale < 0 else scale
    cell *= scale
    elements = lines[5].split()
    counts = [int(value) for value in lines[6].split()]
    require(len(elements) == len(counts), 'POSCAR species/count mismatch')
    species = np.repeat(elements, counts)
    start = 7 + int(lines[7].lower().startswith('s'))
    direct = lines[start].lower().startswith('d')
    coords = np.array([[float(x) for x in line.split()[:3]] for line in lines[start + 1:start + 1 + len(species)]])
    require(coords.shape == (len(species), 3), 'Incomplete POSCAR')
    fractional = coords if direct else (coords * scale) @ np.linalg.inv(cell)
    return cell, species, fractional


def distances_from_first(cell, fractional):
    """Exact nearest periodic image search with bounds from reciprocal vectors.

    An initial image supplies an upper bound. Reciprocal-vector bounds then
    exclude every translation that cannot be closer, including skew cells.
    This deliberately does not use the candidate's geometry implementation.
    """
    difference = fractional[1:] - fractional[0]
    difference -= np.rint(difference)
    initial = np.linalg.norm(difference @ cell, axis=1)
    radius = initial.max()
    bounds = np.ceil(radius * np.linalg.norm(np.linalg.inv(cell), axis=0) + 0.5).astype(int)
    shifts = np.array(list(itertools.product(*(range(-int(b), int(b) + 1) for b in bounds))))
    result = np.full(len(difference), np.inf)
    for shift in shifts:
        result = np.minimum(result, np.linalg.norm((difference + shift) @ cell, axis=1))
    return result


@lru_cache(maxsize=4)
def source_truth(inputs, p_cutoff=2.6, li_cutoff=3.0):
    inputs = Path(inputs)
    require(p_cutoff > 0 and li_cutoff > 0, 'Neighbor cutoffs must be positive')
    with gzip.open(inputs / 'calculations.json.gz', 'rt') as stream:
        calculations = json.load(stream)
    index = {material(row['Index']): row for row in table(inputs / 'materials.csv', {'Index', 'Type'})}
    truth = {}
    for mid, entry in calculations.items():
        _, neutral_species, _ = poscar(entry['neutral']['POSCAR'])
        neutral_energy = total_energy(entry['neutral']['OSZICAR'])
        require(mid in index, f'Material missing from source index: {mid}')
        for sid, source in entry['sites'].items():
            cell, species, fractional = poscar(source['POSCAR'])
            require(species[0] == 'S', f'First atom is not sulfur: {mid}/{sid}')
            require(re.search(r'\bCLNT\s*=\s*1(?:\s|$)', source['INCAR']) is not None, 'Unsupported core-hole species selection')
            distances = distances_from_first(cell, fractional)
            p_distances = distances[species[1:] == 'P']
            li_distances = distances[species[1:] == 'Li']
            delta = total_energy(source['OSZICAR']) - neutral_energy * len(species) / len(neutral_species)
            fermi = float(source['efermi.txt'])
            truth[mid, sid] = dict(material=mid, site=sid, kind=index[mid]['Type'],
                p_cn=int(np.sum(p_distances < p_cutoff)), li_cn=int(np.sum(li_distances < li_cutoff)),
                p_cutoff_A=p_cutoff, li_cutoff_A=li_cutoff,
                li_cn_2p8=int(np.sum(li_distances < 2.8)), li_cn_3p2=int(np.sum(li_distances < 3.2)),
                nearest_p_A=float(np.min(p_distances)), nearest_li_A=float(np.min(li_distances)),
                excitation_delta=delta, fermi_energy=fermi, correction=delta - fermi,
                multiplicity=int(sid.split('_')[1]))
    require(len(truth) == 2681 and len(calculations) == 66, 'Incomplete source inventory')
    return truth


def identity(row, truth):
    mid = material(row['material'])
    sid = row['site'].strip()
    require(re.fullmatch(r'\d+_\d+', sid) is not None, f'Invalid site: {sid}')
    if (mid, sid) not in truth:
        pair = tuple(map(int, sid.split('_')))
        options = [s for m, s in truth if m == mid and tuple(map(int, s.split('_'))) == pair]
        require(len(options) == 1, f'Unknown source site: {mid}/{sid}')
        sid = options[0]
    return mid, sid


def check_sites(path, truth, question):
    required = {'material', 'site'} | ({'p_cn'} if question == 'Q3' else set())
    rows = table(path, required)
    seen = set()
    checked = defaultdict(int)
    unchecked = set()
    for row in rows:
        key = identity(row, truth)
        require(key not in seen, f'Duplicate site row: {key}')
        seen.add(key)
        descriptors = set(row) - {'material', 'site'}
        require(descriptors, f'No descriptors for site: {key}')
        for field in descriptors:
            value = row[field]
            canonical = {'weight': 'multiplicity', 'p_nearest_A': 'nearest_p_A',
                         'li_nearest_A': 'nearest_li_A'}.get(field, field)
            # Text labels/descriptions are allowed, but all numeric quantities
            # must be finite. Standard descriptors receive source checks.
            if canonical in truth[key] and canonical not in {'kind', 'material', 'site'}:
                observed = number(value, field)
                expected = truth[key][canonical]
                tolerance = 0 if canonical in {'p_cn', 'li_cn', 'li_cn_2p8', 'li_cn_3p2', 'multiplicity'} else 1e-5
                require(abs(observed - expected) <= tolerance, f'Source disagreement {key}/{field}: {observed} versus {expected}')
                checked[field] += 1
            else:
                require(str(value).strip(), f'Blank descriptor {key}/{field}')
                try:
                    numeric = float(value)
                except ValueError:
                    unchecked.add(field)
                else:
                    require(np.isfinite(numeric), f'Non-finite descriptor {key}/{field}')
                    unchecked.add(field)
    if question == 'Q3':
        targets = {key for key, row in truth.items() if row['kind'] == 'glassy'}
        require(targets <= seen, 'Site table omits glass target sites')
    return dict(site_count=len(seen), independently_checked_fields=dict(checked),
                omitted_source_sites=len(set(truth) - seen),
                omitted_materials=sorted({key[0] for key in truth} - {key[0] for key in seen}),
                fields_requiring_scientific_review=sorted(unchecked),
                selection_note='Q2 source-valid subsets are accepted numerically; exclusions and representativeness require scientific review. Q3 requires every glass target site, but unused crystalline sites may be omitted.')


def curve(array, name):
    array = np.asarray(array)
    require(array.ndim == 2 and array.shape[1] == 2 and len(array) >= 3, f'Invalid curve dimensions: {name}')
    require(np.issubdtype(array.dtype, np.number) and not np.iscomplexobj(array) and np.isfinite(array).all(), f'Non-real or non-finite curve: {name}')
    x, y = array.T
    require(np.all(np.diff(x) > 0), f'Non-increasing energy axis: {name}')
    require(y.max() > 0 and y.min() >= -1e-5 * y.max(), f'Zero or negative spectrum: {name}')
    return x.astype(float), y.astype(float)


def check_bulk(path, reference, relative_rmse=0.02):
    with np.load(reference, allow_pickle=False) as archive:
        expected = {key: curve(archive[key], key) for key in archive.files}
    with np.load(path, allow_pickle=False) as archive:
        require(set(archive.files) == set(expected), 'Missing, duplicate or extra material spectra')
        require(len(archive.files) == len(set(archive.files)), 'Duplicate NPZ material key')
        submitted = {key: curve(archive[key], key) for key in archive.files}
    offsets = []
    for key, (rx, ry) in expected.items():
        sx, sy = submitted[key]
        offsets.append(np.trapezoid(rx * ry, rx) / np.trapezoid(ry, rx)
                       - np.trapezoid(sx * sy, sx) / np.trapezoid(sy, sx))

    def errors(offset, details=False):
        scores = []
        records = []
        for key, (rx, ry) in expected.items():
            sx, sy = submitted[key]
            values = np.interp(rx, sx + offset, sy, left=0, right=0)
            denominator = np.dot(values, values)
            if denominator == 0:
                scores.append(1.0)
                records.append(dict(material=key, relative_rmse=1.0, intensity_scale=None))
                continue
            scale = np.dot(values, ry) / denominator
            error = float(np.linalg.norm(scale * values - ry) / np.linalg.norm(ry))
            scores.append(error)
            records.append(dict(material=key, relative_rmse=error, intensity_scale=float(scale)))
        return records if details else float(np.mean(np.square(scores)))

    center = float(np.median(offsets))
    grid = np.linspace(center - 5, center + 5, 101)
    start = float(grid[np.argmin([errors(value) for value in grid])])
    optimum = minimize_scalar(errors, bounds=(start - .15, start + .15), method='bounded',
                              options={'xatol': 1e-10})
    offset = float(optimum.x)
    records = errors(offset, details=True)
    for row in records:
        require(row['intensity_scale'] is not None and row['intensity_scale'] > 0,
                f'No positive intensity agreement: {row["material"]}')
        require(row['relative_rmse'] <= relative_rmse,
                f'Released-spectrum mismatch {row["material"]}: relative RMSE {row["relative_rmse"]:.6g} > {relative_rmse}')
    return dict(material_count=len(records), common_energy_offset_eV=offset,
                relative_rmse_tolerance=relative_rmse, material_comparisons=records,
                maximum_relative_rmse=max(row['relative_rmse'] for row in records))


def identifier(row, name, default):
    if name not in row:
        return default
    result = row[name].strip()
    require(result, f'Blank {name}')
    return result


def classification_metrics(y_true, y_pred):
    truth = np.array(y_true, dtype=int)
    predicted = np.array(y_pred, dtype=int)
    labels = sorted(int(value) for value in set(truth) | set(predicted))
    support = {str(label): int(np.sum(truth == label)) for label in labels}
    recall, f1 = {}, []
    for label in labels:
        tp = np.sum((truth == label) & (predicted == label))
        fp = np.sum((truth != label) & (predicted == label))
        fn = np.sum((truth == label) & (predicted != label))
        if tp + fn:
            recall[str(label)] = float(tp / (tp + fn))
        f1.append(float(2 * tp / (2 * tp + fp + fn)) if 2 * tp + fp + fn else 0.0)
    confusion = [[int(np.sum((truth == left) & (predicted == right))) for right in labels] for left in labels]
    return dict(n=len(truth), accuracy=float(np.mean(truth == predicted)),
                balanced_accuracy=float(np.mean(list(recall.values()))), macro_f1=float(np.mean(f1)),
                class_support=support, class_recall=recall, confusion_labels=labels, confusion=confusion,
                test_majority_fraction=max(support.values()) / len(truth))


def check_predictions(output, truth):
    roles = {'train': 'train', 'training': 'train', 'validation': 'validation', 'valid': 'validation',
             'val': 'validation', 'test': 'test', 'testing': 'test', 'unused': 'unused', 'excluded': 'unused'}
    partitions = defaultdict(lambda: defaultdict(set))
    seen = set()
    all_materials = {mid for mid, _ in truth}
    for row in table(output / 'partitions.csv', {'material', 'role'}):
        mid = material(row['material'])
        split = identifier(row, 'split', 'default')
        method = identifier(row, 'method', '*')
        require(mid in all_materials, f'Unknown partition material: {mid}')
        require(row['role'].strip() in roles, f'Unknown partition role: {row["role"]}')
        role = roles[row['role'].strip()]
        key = method, split, mid
        require(key not in seen, f'Duplicate or overlapping material roles: {key}')
        seen.add(key)
        partitions[method, split][role].add(mid)

    predictions = defaultdict(dict)
    for row in table(output / 'predictions.csv', {'material', 'site', 'predicted'}):
        key = identity(row, truth)
        split = identifier(row, 'split', 'default')
        method = identifier(row, 'method', 'default')
        require(key not in predictions[method, split], f'Duplicate prediction: {method}/{split}/{key}')
        value = number(row['predicted'], 'predicted')
        require(value.is_integer() and int(value) in {r['p_cn'] for r in truth.values()}, 'Unknown coordination class')
        for field in ['true', 'truth', 'p_cn', 'y_true']:
            if field in row:
                require(number(row[field], field) == truth[key]['p_cn'], f'False supplied truth: {key}')
        predictions[method, split][key] = int(value)

    results = []
    consumed = set()
    for (method, split), values in sorted(predictions.items()):
        roster_key = (method, split) if (method, split) in partitions else ('*', split)
        require(roster_key in partitions, f'Missing partitions: {method}/{split}')
        consumed.add(roster_key)
        roster = partitions[roster_key]
        require(roster['train'] and roster['test'], f'No training or test materials: {method}/{split}')
        require(not (roster['train'] & roster['test'] or roster['validation'] & roster['test'] or roster['train'] & roster['validation']), 'Training/validation/test material overlap')
        expected = {key for key in truth if key[0] in roster['test']}
        require(set(values) == expected, f'Missing or extra predictions for declared test materials: {method}/{split}')
        require(all(truth[key]['kind'] == 'glassy' for key in expected), 'Q3 test targets must be glassy materials')
        ordered = sorted(values)
        metrics = classification_metrics([truth[key]['p_cn'] for key in ordered], [values[key] for key in ordered])
        results.append(dict(method=method, split=split, train_materials=sorted(roster['train']),
            validation_materials=sorted(roster['validation']), test_materials=sorted(roster['test']), **metrics))
    require(consumed == set(partitions), 'Partition roster without predictions or ambiguous shared roster')

    optional = output / 'metrics.csv'
    if optional.exists():
        by_run = {(row['method'], row['split']): row for row in results}
        seen_metrics = set()
        for row in table(optional, {'metric', 'value'}):
            key = identifier(row, 'method', 'default'), identifier(row, 'split', 'default')
            metric = row['metric'].strip()
            require(key in by_run, f'Unknown metric run: {key}')
            require((key, metric) not in seen_metrics, f'Duplicate metric: {key}/{metric}')
            seen_metrics.add((key, metric))
            value = number(row['value'], 'metric value')
            aliases = {'balanced_acc': 'balanced_accuracy', 'f1_macro': 'macro_f1'}
            canonical = aliases.get(metric, metric)
            require(canonical in {'accuracy', 'balanced_accuracy', 'macro_f1', 'test_majority_fraction'}, f'Unsupported reported metric requires separate scientific review: {metric}')
            require(abs(value - by_run[key][canonical]) <= 1e-8, f'False reported metric: {key}/{metric}')
            if 'n' in row:
                require(number(row['n'], 'metric n') == by_run[key]['n'], f'False metric sample count: {key}')
    aggregated = []
    for method in sorted({method for method, split in predictions}):
        occurrences = [(key, value) for (m, split), values in predictions.items() if m == method for key, value in values.items()]
        keys = [key for key, _ in occurrences]
        mids = sorted({key[0] for key in keys})
        metrics = classification_metrics([truth[key]['p_cn'] for key, _ in occurrences], [value for _, value in occurrences])
        aggregated.append(dict(method=method, unique_test_sites=len(set(keys)), unique_test_materials=len(mids),
            all_48_glasses_evaluated=len(mids) == 48, repeated_test_occurrences=len(keys) - len(set(keys)), **metrics))
        require(len(mids) == 48, f'Method omits glassy target materials: {method}')
    optional_json = output / 'metrics.json'
    if optional_json.exists():
        reported = json.loads(optional_json.read_text())
        def finite_tree(value):
            if isinstance(value, dict):
                for child in value.values(): finite_tree(child)
            elif isinstance(value, list):
                for child in value: finite_tree(child)
            elif isinstance(value, (int, float)):
                require(np.isfinite(value), 'Non-finite reported JSON metric')
        finite_tree(reported)
        require(isinstance(reported, dict), 'metrics.json must map method identifiers to reported metrics')
        by_method = {row['method']: row for row in aggregated}
        for method, values in reported.items():
            require(method in by_method and isinstance(values, dict), f'Unknown metrics.json method: {method}')
            expected = by_method[method]
            for metric in ['accuracy', 'balanced_accuracy', 'macro_f1']:
                if metric in values:
                    require(abs(number(values[metric], metric) - expected[metric]) <= 1e-8, f'False aggregate metric: {method}/{metric}')
            if 'confusion' in values:
                observed = np.asarray(values['confusion'], dtype=float)
                require(observed.shape == np.asarray(expected['confusion']).shape and np.isfinite(observed).all()
                        and np.array_equal(observed, expected['confusion']), f'False aggregate confusion: {method}')
            if 'recall' in values:
                observed = np.asarray(values['recall'], dtype=float)
                wanted = np.array([expected['class_recall'].get(str(label), np.nan) for label in expected['confusion_labels']])
                require(observed.shape == wanted.shape and np.isfinite(observed).all() and np.allclose(observed, wanted, rtol=0, atol=1e-8), f'False aggregate recall: {method}')
    return dict(run_count=len(results), runs=results, aggregated_by_method=aggregated)


def verify(question, output, inputs=DATA / 'inputs', reference=DATA / 'verification/released_material_spectra.npz',
           p_cutoff=2.6, li_cutoff=3.0, relative_rmse=0.02):
    output, inputs = Path(output), Path(inputs)
    require(question in {'Q1', 'Q2', 'Q3'}, 'Unknown question')
    require((output / 'report.md').is_file() and len((output / 'report.md').read_text().strip()) >= 80, 'Missing substantive report.md')
    code = [path for path in output.rglob('*') if path.is_file() and path.suffix.lower() in {'.py', '.ipynb', '.r', '.jl', '.m', '.sh'}]
    require(code, 'Missing submitted analysis code')
    result = dict(question=question, integrity_pass=True, scientific_pass=None,
        status='scientific_review_required',
        scope='Numerical/source integrity only. Independent execution and scientific rubric review are mandatory.',
        submitted_code=[str(path.relative_to(output)) for path in code])
    if question == 'Q1':
        result['checks'] = check_bulk(output / 'bulk.npz', reference, relative_rmse)
    else:
        truth = source_truth(str(inputs.resolve()), p_cutoff, li_cutoff)
        result['geometry_convention'] = dict(p_cutoff_A=p_cutoff, li_cutoff_A=li_cutoff,
            neighbor_definition='Distinct atoms within a strict radius using nearest periodic images, centered on the core-hole first S atom.')
        result['checks'] = check_sites(output / 'sites.csv', truth, question)
        if question == 'Q3':
            result['predictions'] = check_predictions(output, truth)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question_pos', nargs='?', choices=['Q1', 'Q2', 'Q3'])
    parser.add_argument('output_pos', nargs='?', type=Path)
    parser.add_argument('--question', choices=['Q1', 'Q2', 'Q3'])
    parser.add_argument('--output', type=Path, help='Submitted output directory (also accepted as second positional argument).')
    parser.add_argument('--inputs', type=Path, default=DATA / 'inputs')
    parser.add_argument('--reference', type=Path, default=DATA / 'verification/released_material_spectra.npz')
    parser.add_argument('--p-cutoff', type=float, default=2.6, help='Set to the submitted P coordination definition.')
    parser.add_argument('--li-cutoff', type=float, default=3.0, help='Set to the submitted Li coordination definition.')
    parser.add_argument('--relative-rmse', type=float, default=.02)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    question, output = args.question or args.question_pos, args.output or args.output_pos
    if question is None or output is None:
        parser.error('Supply question and output, using positional arguments or --question/--output.')
    if args.question and args.question_pos and args.question != args.question_pos:
        parser.error('Conflicting question arguments.')
    if args.output and args.output_pos and args.output != args.output_pos:
        parser.error('Conflicting output arguments.')
    result = verify(question, output, args.inputs, args.reference,
                    args.p_cutoff, args.li_cutoff, args.relative_rmse)
    text = json.dumps(result, indent=2) + '\n'
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
