#!/usr/bin/env python3
"""Independent source projection and positive/adversarial verifier audit.

Does not import or execute candidate.py. A separate agent reruns that workflow.
All mutations below are output-integrity controls, never scientific approvals.
"""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile

import numpy as np
from ase.io import read as ase_read

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/guo-2023-sulfur-xas'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verifier():
    path = DATA / 'workflows/verify.py'
    spec = importlib.util.spec_from_file_location('independent_guo_verifier', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def edit_table(folder, name, transform):
    path = folder / name
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    rows = transform(rows)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def edit_bulk(folder, transform):
    path = folder / 'bulk.npz'
    with np.load(path) as archive:
        values = {key: archive[key].copy() for key in archive.files}
    transform(values)
    np.savez_compressed(path, **values)


def projection(raw, references, release):
    """Compare every packaged array and calculation text to native release."""
    with gzip.open(DATA / 'inputs/calculations.json.gz', 'rt') as stream:
        calculations = json.load(stream)
    text_count = 0
    for mid, entry in calculations.items():
        for sid, files in [('input_SCF', entry['neutral']), *entry['sites'].items()]:
            for name, text in files.items():
                source = raw / mid / sid / name
                assert text == source.read_bytes().decode(), f'Text projection mismatch: {source}'
                text_count += 1
    sites = set()
    for path in sorted((DATA / 'inputs').glob('spectra_*.npz')):
        with np.load(path, allow_pickle=False) as archive:
            for key in archive.files:
                assert key not in sites, f'Duplicate projected site: {key}'
                sites.add(key)
                assert np.array_equal(archive[key], np.loadtxt(raw / key / 'mu.dat')), f'Array projection mismatch: {key}'
    native = {f'{path.parent.parent.name}/{path.parent.name}' for path in raw.glob('*/*/mu.dat')}
    assert sites == native and len(sites) == 2681
    with np.load(DATA / 'verification/released_material_spectra.npz') as archive:
        assert len(archive.files) == 66
        for key in archive.files:
            assert np.array_equal(archive[key], np.loadtxt(references / f'material-{int(key[1:])}_raw.txt'))
    assert (DATA / 'inputs/materials.csv').read_bytes() == (release / 'structure-index.csv').read_bytes()
    provenance = json.loads((DATA / 'provenance.json').read_text())
    for asset in provenance['input_assets']:
        assert digest(DATA / 'inputs' / asset['name']) == asset['sha256']
    for item in provenance['source_files']:
        assert digest(raw / item['path']) == item['sha256']
    return dict(site_arrays_bitwise_equal=2681, unmodified_calculation_texts=text_count,
                heldback_arrays_bitwise_equal=66, material_index_byte_equal=True,
                source_manifest_hashes_checked=len(provenance['source_files']), input_asset_hashes_checked=len(provenance['input_assets']))


def audit(candidate, raw=None, references=None, release=None):
    v = verifier()
    result = dict(scope='Source projection and numerical-integrity audit; scientific review and code execution remain separate.',
        verifier_sha256=digest(DATA / 'workflows/verify.py'), audit_sha256=digest(__file__),
        candidate_source_sha256=digest(DATA / 'workflows/candidate.py'),
        accepted=[], rejected=[], baselines={})
    if raw is not None:
        result['raw_projection'] = projection(raw, references, release)
    source_truth = v.source_truth(str((DATA / 'inputs').resolve()))
    with gzip.open(DATA / 'inputs/calculations.json.gz', 'rt') as stream:
        original_records = json.load(stream)
    maximum_geometry_difference = 0.0
    for (mid, sid), native in source_truth.items():
        atoms = ase_read(io.StringIO(original_records[mid]['sites'][sid]['POSCAR']), format='vasp')
        d = atoms.get_distances(0, np.arange(1, len(atoms)), mic=True)
        species = np.array(atoms.get_chemical_symbols()[1:])
        dp, dl = d[species == 'P'], d[species == 'Li']
        assert native['p_cn'] == int(np.sum(dp < 2.6))
        assert native['li_cn'] == int(np.sum(dl < 3.0))
        maximum_geometry_difference = max(maximum_geometry_difference,
            abs(native['nearest_p_A'] - dp.min()), abs(native['nearest_li_A'] - dl.min()))
    assert maximum_geometry_difference < 1e-10
    result['independent_source_truth'] = dict(sites=len(source_truth),
        p_coordination_counts={str(label): sum(row['p_cn'] == label for row in source_truth.values()) for label in [0, 1, 2]},
        correction_range_eV=[min(row['correction'] for row in source_truth.values()), max(row['correction'] for row in source_truth.values())],
        geometry_implementation='Verifier uses custom POSCAR parser and reciprocal-vector-bounded periodic image enumeration; no ASE or candidate imports',
        crosscheck='Audit independently checks all sites against ASE minimum-image distances and neighbor counts',
        maximum_geometry_distance_disagreement_A=float(maximum_geometry_difference))
    for question in ['Q1', 'Q2', 'Q3']:
        report = v.verify(question, candidate / question)
        assert report['integrity_pass'] and report['scientific_pass'] is None
        result['baselines'][question] = report

    with tempfile.TemporaryDirectory(prefix='guo-verifier-audit-') as tmp:
        tmp = Path(tmp)

        def exercise(name, question, mutate, accepted=False, source=None, **kwargs):
            folder = tmp / name
            shutil.copytree(source or candidate / question, folder)
            mutate(folder)
            try:
                report = v.verify(question, folder, **kwargs)
            except (AssertionError, ValueError, KeyError, FileNotFoundError) as exc:
                assert not accepted, f'Valid alternative rejected: {name}: {exc}'
                result['rejected'].append(dict(case=name, question=question, reason=str(exc)))
            else:
                assert accepted, f'Invalid output accepted: {name}'
                assert report['integrity_pass'] and report['scientific_pass'] is None
                result['accepted'].append(dict(case=name, question=question, integrity_pass=True,
                    scientific_pass=None, status=report['status']))
            return folder

        def origin_and_scale(folder):
            def change(values):
                for index, array in enumerate(values.values()):
                    array[:, 0] += 71.25
                    array[:, 1] *= 0.1 + (index + 1) / 7
            edit_bulk(folder, change)
        exercise('common_origin_and_independent_intensity_units', 'Q1', origin_and_scale, accepted=True)

        def resample(folder):
            def change(values):
                for key, array in list(values.items()):
                    values[key] = array[np.unique(np.r_[np.arange(0, len(array), 2), len(array) - 1])]
            edit_bulk(folder, change)
        exercise('alternate_energy_sampling', 'Q1', resample, accepted=True)
        exercise('missing_material_spectrum', 'Q1', lambda f: edit_bulk(f, lambda x: x.pop('m001')))
        exercise('zero_spectrum', 'Q1', lambda f: edit_bulk(f, lambda x: x['m001'].__setitem__((slice(None), 1), 0)))
        exercise('nonfinite_spectrum', 'Q1', lambda f: edit_bulk(f, lambda x: x['m001'].__setitem__((0, 1), np.nan)))
        exercise('negative_spectrum', 'Q1', lambda f: edit_bulk(f, lambda x: x['m001'].__setitem__((slice(None), 1), -x['m001'][:, 1])))
        exercise('nonmonotonic_spectrum', 'Q1', lambda f: edit_bulk(f, lambda x: x['m001'].__setitem__((0, 0), x['m001'][2, 0])))
        exercise('one_material_shifted', 'Q1', lambda f: edit_bulk(f, lambda x: x['m057'].__setitem__((slice(None), 0), x['m057'][:, 0] + .7)))

        for column, name in [(2, 'relative_alignment_removed'), (3, 'multiplicity_removed')]:
            def replace_with_ablation(folder, column=column):
                with np.load(folder / 'ablations.npz') as archive:
                    values = {key: archive[key][:, [0, column]] for key in archive.files}
                np.savez_compressed(folder / 'bulk.npz', **values)
            exercise(name, 'Q1', replace_with_ablation)

        exercise('reordered_site_table', 'Q2', lambda f: edit_table(f, 'sites.csv', lambda rows: rows[::-1]), accepted=True)

        def alternate_cutoffs(folder):
            def change(rows):
                for row in rows:
                    row['p_cutoff_A'] = '2.5'
                    row['li_cutoff_A'] = '2.8'
                    row['li_cn'] = row['li_cn_2p8']
                return rows
            edit_table(folder, 'sites.csv', change)
        exercise('alternate_declared_geometry_cutoffs', 'Q2', alternate_cutoffs, accepted=True, p_cutoff=2.5, li_cutoff=2.8)
        exercise('source_valid_subset_requires_scientific_review', 'Q2',
                 lambda f: edit_table(f, 'sites.csv', lambda rows: [row for row in rows if int(row['material']) <= 48]), accepted=True)
        exercise('empty_site_table', 'Q2', lambda f: (f / 'sites.csv').write_text('material,site,p_cn\n'))
        exercise('duplicate_site', 'Q2', lambda f: edit_table(f, 'sites.csv', lambda rows: rows + [rows[0]]))
        for field, value in [('correction', '-999'), ('p_cn', '99'), ('weight', '99'), ('peak_e', 'nan'), ('p_nearest_A', '-1'), ('p_cutoff_A', '1.2')]:
            def mutation(folder, field=field, value=value):
                def change(rows):
                    rows[0][field] = value
                    return rows
                edit_table(folder, 'sites.csv', change)
            exercise('false_site_' + field, 'Q2', mutation)

        # A minimal submission is still accepted: one method, no method IDs,
        # unused sources omitted, no metrics file. All 48 explicit targets
        # remain evaluated, with arbitrary splits unconstrained by the checker.
        def minimal(folder):
            with (folder / 'predictions.csv').open() as stream:
                row = next(csv.DictReader(stream))
            method = row['method']
            for name in ['predictions.csv', 'partitions.csv']:
                def change(rows, name=name):
                    selected = [r for r in rows if r['method'] == method and r.get('role') != 'unused']
                    for r in selected:
                        del r['method']
                        r['material'] = str(int(r['material']))
                    return selected
                edit_table(folder, name, change)
            (folder / 'metrics.json').unlink(missing_ok=True)
        simple = exercise('minimal_single_method_interface', 'Q3', minimal, accepted=True)
        exercise('unused_crystalline_geometry_omitted', 'Q3',
                 lambda f: edit_table(f, 'sites.csv', lambda rows: [row for row in rows if int(row['material']) <= 48]), accepted=True, source=simple)

        def renamed_shared(folder):
            def predictions(rows):
                expanded = []
                for method in ['Investigator model A', 'Investigator model B']:
                    expanded.extend([dict(row, method=method) for row in rows])
                return expanded
            edit_table(folder, 'predictions.csv', predictions)
        exercise('arbitrary_model_names_shared_partition_table', 'Q3', renamed_shared, accepted=True, source=simple)

        def majority(folder):
            def change(rows):
                for row in rows: row['predicted'] = '1'
                return rows
            edit_table(folder, 'predictions.csv', change)
        exercise('majority_predictions_need_scientific_review', 'Q3', majority, accepted=True, source=simple)
        exercise('missing_test_prediction', 'Q3', lambda f: edit_table(f, 'predictions.csv', lambda rows: rows[1:]), source=simple)
        exercise('duplicate_prediction', 'Q3', lambda f: edit_table(f, 'predictions.csv', lambda rows: rows + [rows[0]]), source=simple)
        def missing_glass(folder):
            edit_table(folder, 'predictions.csv', lambda rows: [row for row in rows if int(row['material']) != 1])
            edit_table(folder, 'partitions.csv', lambda rows: [row for row in rows if not (int(row['material']) == 1 and row['role'] == 'test')])
        exercise('complete_glass_target_omitted', 'Q3', missing_glass, source=simple)
        exercise('glass_geometry_omitted', 'Q3', lambda f: edit_table(f, 'sites.csv', lambda rows: rows[1:]), source=simple)
        for field, value in [('predicted', '99'), ('predicted', 'nan'), ('site', '99999_1')]:
            def mutation(folder, field=field, value=value):
                def change(rows):
                    rows[0][field] = value
                    return rows
                edit_table(folder, 'predictions.csv', change)
            exercise('invalid_prediction_' + field + '_' + value, 'Q3', mutation, source=simple)

        def overlap(folder):
            def change(rows):
                row = dict(next(row for row in rows if row['role'] == 'test'))
                row['role'] = 'train'
                return rows + [row]
            edit_table(folder, 'partitions.csv', change)
        exercise('material_train_test_overlap', 'Q3', overlap, source=simple)

        def false_truth(folder):
            edit_table(folder, 'predictions.csv', lambda rows: [dict(row, y_true='99') for row in rows])
        exercise('false_supplied_labels', 'Q3', false_truth, source=simple)

        def false_csv_metric(folder):
            (folder / 'metrics.csv').write_text('split,metric,value\nfold0,accuracy,-1\n')
        exercise('false_csv_metric', 'Q3', false_csv_metric, source=simple)

        def false_json_metric(folder):
            path = folder / 'metrics.json'
            values = json.loads(path.read_text())
            values[next(iter(values))]['accuracy'] = -1
            path.write_text(json.dumps(values))
        exercise('false_aggregate_json_metric', 'Q3', false_json_metric)

    result['accepted_count'] = len(result['accepted'])
    result['rejected_count'] = len(result['rejected'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--output', type=Path, default=DATA / 'verification/verification_audit.json')
    args = parser.parse_args()
    if args.raw:
        parser.error('--raw requires --reference and --release') if not args.reference or not args.release else None
    result = audit(args.candidate, args.raw, args.reference, args.release)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in {'baselines', 'accepted', 'rejected'}}, indent=2))


if __name__ == '__main__':
    main()
