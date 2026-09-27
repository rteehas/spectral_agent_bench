#!/usr/bin/env python3
"""Evaluator-only WORKED-PROFILE audit; not a universal solver-output validator.

This module does not import or execute candidate code. Source spectra, symmetry,
local environments, compositions and metrics are independently reconstructed.
This implements the explicitly declared conventions in the worked example.
Other defensible methods use verify_submission.py and explicit scientific review;
the additional worked-profile filenames and algorithms are not question rules.
No candidate score or sign of a scientific effect is an acceptance target.
"""
import argparse
import csv
from functools import lru_cache
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import spglib
from scipy.ndimage import gaussian_filter1d
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')
DEFAULT_INPUTS = Path(__file__).resolve().parents[1] / 'inputs'
ASSOCIATION_INTERVAL_CACHE = {}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def close(actual, expected, message, rtol=2e-6, atol=2e-9):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all()
            and np.allclose(a, b, rtol=rtol, atol=atol), message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def table(path, fields):
    with Path(path).open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(set(fields) <= set(reader.fieldnames or []), f'{path.name}: missing columns {set(fields) - set(reader.fieldnames or [])}')
        rows = list(reader)
    require(rows, f'{path.name}: empty table')
    return rows


def number(value):
    result = float(value)
    require(math.isfinite(result), 'Nonfinite numerical artifact value')
    return result


def integer(value):
    result = number(value)
    require(result == int(result), 'Noninteger identifier/count')
    return int(result)


def boolean(value):
    require(str(value).lower() in {'true', 'false', '1', '0'}, 'Invalid Boolean')
    return str(value).lower() in {'true', '1'}


def unique(rows, fields, label):
    keys = [tuple(row[field] for field in fields) for row in rows]
    require(len(set(keys)) == len(keys), f'{label}: duplicate identifiers')
    return dict(zip(keys, rows))


def canonical_composition(structure):
    """Reduced integer composition, without using submitted formulas or labels."""
    counts = {}
    for site in structure['sites']:
        require(len(site['species']) == 1 and site['species'][0]['occu'] == 1,
                'Disordered occupancy requires independent scientific review')
        symbol = site['species'][0]['element']
        counts[symbol] = counts.get(symbol, 0) + 1
    divisor = math.gcd(*counts.values())
    return '|'.join(f'{symbol}:{counts[symbol] // divisor}' for symbol in sorted(counts))


def normalize_composition(value):
    counts = {key: integer(amount) for key, amount in (part.split(':') for part in value.split('|'))}
    require(all(count > 0 for count in counts.values()), 'Invalid composition amount')
    divisor = math.gcd(*counts.values())
    return '|'.join(f'{symbol}:{counts[symbol] // divisor}' for symbol in sorted(counts))


def physical_structure(structure):
    return (structure['lattice']['matrix'],
            [(site['abc'], site['species']) for site in structure['sites']])


class Truth:
    def __init__(self, inputs):
        self.inputs = Path(inputs)
        self.records, self.structures, self.groups = {}, {}, {}
        self.inconsistent_materials = set()
        self.counts = {}
        for element in ELEMENTS:
            count = 0
            with gzip.open(self.inputs / f'{element}.jsonl.gz', 'rt') as stream:
                for line in stream:
                    raw = json.loads(line)
                    name, material, site, edge = raw['name'], raw['mp-id'], raw['absorbing_atom'], raw['edge']
                    require(name not in self.records, 'Duplicate native source ID')
                    structure = raw['structure']
                    require(structure['sites'][site]['species'][0]['element'] == element,
                            'Element package does not match absorbing atom')
                    x, y = np.asarray(raw['spectrum'], dtype=float)
                    valid = bool(len(x) > 1 and np.isfinite(x).all() and np.isfinite(y).all()
                                 and np.all(np.diff(x) > 0) and np.min(y) >= 0)
                    self.records[name] = dict(name=name, material=material, element=element,
                                              site=site, edge=edge, x=x, y=y, valid=valid)
                    if material in self.structures:
                        if physical_structure(self.structures[material]) != physical_structure(structure):
                            self.inconsistent_materials.add(material)
                    else:
                        self.structures[material] = structure
                    self.groups.setdefault((material, element, edge), []).append(name)
                    count += 1
            self.counts[element] = count
        self.compositions = {material: canonical_composition(structure)
                             for material, structure in self.structures.items()}

    @lru_cache(maxsize=None)
    def equivalence(self, material, symprec, angle_tolerance=5.0):
        structure = self.structures[material]
        symbols = [site['species'][0]['element'] for site in structure['sites']]
        mapping = {symbol: i + 1 for i, symbol in enumerate(sorted(set(symbols)))}
        cell = (structure['lattice']['matrix'], [site['abc'] for site in structure['sites']],
                [mapping[symbol] for symbol in symbols])
        result = spglib.get_symmetry_dataset(cell, symprec=symprec, angle_tolerance=angle_tolerance)
        require(result is not None, f'No symmetry result for {material}')
        eq = np.asarray(result.equivalent_atoms)
        return eq

    def multiplicity(self, record, symprec, angle_tolerance=5.0):
        eq = self.equivalence(record['material'], symprec, angle_tolerance)
        return int(np.count_nonzero(eq == eq[record['site']]))

    @lru_cache(maxsize=None)
    def environment(self, material, site, factor=1.2, radius=6.0):
        """Enumerate periodic images directly, independently of candidate neighbor API."""
        structure = self.structures[material]
        lattice = np.asarray(structure['lattice']['matrix'], dtype=float)
        frac = np.asarray([atom['abc'] for atom in structure['sites']], dtype=float)
        center = frac[site]
        bound = np.ceil(radius * np.linalg.norm(np.linalg.inv(lattice), axis=0) + 1).astype(int)
        shifts = np.asarray(list(itertools.product(*(range(-b, b + 1) for b in bound))))
        displacement = (frac[None, :, :] + shifts[:, None, :] - center) @ lattice
        distance = np.linalg.norm(displacement, axis=2)
        possible = (distance > 1e-7) & (distance <= radius + 1e-8)
        require(possible.any(), 'No neighbors in declared search sphere')
        minimum = distance[possible].min()
        selected = possible & (distance <= minimum * factor + 1e-8)
        d = distance[selected]
        vectors = displacement[selected] / d[:, None]
        n = len(d)
        products = (vectors @ vectors.T)[np.triu_indices(n, 1)]
        rms = None
        if n == 4:
            rms = float(np.sqrt(np.mean((np.sort(products) + 1 / 3) ** 2)))
        elif n == 6:
            ideal = np.asarray([-1.] * 3 + [0.] * 12)
            rms = float(np.sqrt(np.mean((np.sort(products) - ideal) ** 2)))
        symbols = [atom['species'][0]['element'] for atom in structure['sites']]
        ligands = sorted({symbols[i] for _, i in zip(*np.where(selected))})
        return dict(cn=n, angular_rms=rms, radial_cv=float(d.std() / d.mean()),
                    mean_distance=float(d.mean()), ligands=ligands)


@lru_cache(maxsize=4)
def load_truth(inputs):
    return Truth(inputs)


def provenance(truth):
    return {'element_record_counts': truth.counts,
            'records': len(truth.records), 'materials': len(truth.structures),
            'negative_records': int(sum(np.min(row['y']) < 0 for row in truth.records.values())),
            'inconsistent_materials': sorted(truth.inconsistent_materials),
            'sha256': {element: sha256(truth.inputs / f'{element}.jsonl.gz') for element in ELEMENTS}}


def geometry_label(env, angular, radial):
    if env['cn'] not in {4, 6} or env['angular_rms'] > angular or env['radial_cv'] > radial:
        return 'other'
    return {4: 'tetrahedral', 6: 'octahedral'}[env['cn']]


def site_audit(output, truth, config):
    rows = table(output / 'sites.csv', ['name', 'material', 'element', 'site', 'edge', 'multiplicity', 'included', 'reason'])
    unique(rows, ['name'], 'sites')
    require({r['name'] for r in rows} == set(truth.records), 'sites: missing or unknown source IDs / undercoverage')
    result = {}
    for row in rows:
        native = truth.records[row['name']]
        for field in ('material', 'element', 'edge'):
            require(row[field] == native[field], 'sites: incorrect ' + field)
        require(integer(row['site']) == native['site'], 'sites: wrong absorbing site')
        included = boolean(row['included'])
        if native['material'] in truth.inconsistent_materials:
            require(not included and row['reason'], 'Inconsistent structures cannot be silently pooled by material ID')
        else:
            mult = truth.multiplicity(native, number(config['symprec_A']), number(config.get('angle_tolerance_degrees', 5)))
            require(integer(row['multiplicity']) == mult, 'sites: wrong structural multiplicity')
        require(not included or native['valid'], 'Invalid native spectrum declared included')
        require(included or row['reason'].strip(), 'Excluded source row has no reason')
        result[row['name']] = row
    return result


def geometry_audit(output, truth, config):
    rows = table(output / 'geometry.csv', ['name', 'material', 'element', 'site', 'composition_key', 'geometry', 'cn', 'angular_rms', 'radial_cv', 'bond_length_A', 'ligand_family'])
    indexed = unique(rows, ['material', 'element', 'site'], 'geometry')
    expected = {(r['material'], r['element'], str(r['site'])) for r in truth.records.values()
                if r['material'] not in truth.inconsistent_materials}
    observed = {key for key in indexed if key[0] not in truth.inconsistent_materials}
    require(observed == expected, 'geometry: missing or unknown absorbing sites / undercoverage')
    factor, radius = number(config['shell_ratio']), number(config['neighbor_radius_A'])
    angular, radial = number(config['angular_rms_cosine_max']), number(config['radial_cv_max'])
    require(1 < factor < 2 and 0 < radius <= 20 and 0 < angular < 1 and 0 < radial < 1,
            'Invalid declared geometry parameters')
    for key, row in indexed.items():
        material, element, site = key
        if material in truth.inconsistent_materials:
            continue
        i = integer(site)
        env = truth.environment(material, i, factor, radius)
        require(normalize_composition(row['composition_key']) == truth.compositions[material], 'geometry: wrong reduced composition')
        require(integer(row['cn']) == env['cn'], 'geometry: incorrect periodic coordination number')
        close(number(row['radial_cv']), env['radial_cv'], 'geometry: incorrect radial distortion')
        close(number(row['bond_length_A']), env['mean_distance'], 'geometry: wrong neighbor distance')
        require(row['ligand_family'] == '|'.join(env['ligands']), 'geometry: wrong ligand identities')
        if env['angular_rms'] is not None:
            close(number(row['angular_rms']), env['angular_rms'], 'geometry: incorrect angular shape')
        require(row['geometry'] == geometry_label(env, angular, radial), 'geometry: incorrect shape label')
        for col, fac, ang in [('geometry_shell_1p15', 1.15, angular), ('geometry_shell_1p25', 1.25, angular),
                              ('geometry_angular_0p10', factor, .10)]:
            if col in row:
                other = truth.environment(material, i, fac, radius)
                require(row[col] == geometry_label(other, ang, radial), 'geometry: wrong sensitivity label')
        if 'absorber_fraction' in row:
            structure = truth.structures[material]
            count = sum(atom['species'][0]['element'] == element for atom in structure['sites'])
            close(number(row['absorber_fraction']), count / len(structure['sites']), 'geometry: wrong absorber fraction')
    return indexed


def q1_audit(output, truth, config, sites, review):
    coverage = table(output / 'coverage.csv', ['material', 'element', 'edge', 'included', 'reason'])
    coverage = unique(coverage, ['material', 'element', 'edge'], 'coverage')
    require(set(coverage) == set(truth.groups), 'coverage: missing or unknown material/element/edge groups')
    expected_keys, source_groups = set(), {}
    for key, row in coverage.items():
        records = [truth.records[name] for name in truth.groups[key]]
        include = boolean(row['included'])
        require(all(boolean(sites[r['name']]['included']) == include for r in records), 'Coverage/site inclusion disagreement')
        material, element, edge = key
        if material not in truth.inconsistent_materials:
            eq = truth.equivalence(material, number(config['symprec_A']), number(config.get('angle_tolerance_degrees', 5)))
            symbols = [site['species'][0]['element'] for site in truth.structures[material]['sites']]
            required_classes = {eq[i] for i, symbol in enumerate(symbols) if symbol == element}
            observed_classes = [eq[r['site']] for r in records]
            expected_include = (all(r['valid'] for r in records) and set(observed_classes) == required_classes
                                and len(set(observed_classes)) == len(records)
                                and min(r['x'][-1] for r in records) - max(r['x'][0] for r in records) >= 6)
            require(include == expected_include, 'coverage: inclusion contradicts declared completeness/validity rule')
        if not include:
            require(row['reason'].strip(), 'Excluded group lacks a reason')
            continue
        material, element, edge = key
        require(material not in truth.inconsistent_materials, 'Inconsistent material group included')
        eq = truth.equivalence(material, number(config['symprec_A']), number(config.get('angle_tolerance_degrees', 5)))
        symbols = [site['species'][0]['element'] for site in truth.structures[material]['sites']]
        expected_classes = {eq[i] for i, symbol in enumerate(symbols) if symbol == element}
        actual_classes = [eq[r['site']] for r in records]
        require(set(actual_classes) == expected_classes and len(set(actual_classes)) == len(records),
                'Incomplete/duplicated symmetry representatives declared a complete average')
        native_key = '__'.join(key)
        expected_keys.add(native_key)
        source_groups[native_key] = records
    require(expected_keys, 'No complete responses submitted')
    with np.load(output / 'responses.npz', allow_pickle=False) as responses, np.load(output / 'ablations.npz', allow_pickle=False) as ablations:
        require(set(responses.files) == expected_keys, 'responses: missing/unknown groups / undercoverage')
        require(set(ablations.files) == expected_keys, 'ablations: missing/unknown groups')
        for key in expected_keys:
            records = source_groups[key]
            a = np.asarray(responses[key], dtype=float)
            require(a.ndim == 2 and a.shape[1] == 2 and len(a) > 1 and np.isfinite(a).all(), 'responses: nonfinite or malformed array')
            x = a[:, 0]
            require(np.all(np.diff(x) > 0), 'responses: nonmonotone energy')
            lo, hi = max(r['x'][0] for r in records), min(r['x'][-1] for r in records)
            require(x[0] >= lo - 1e-8 and x[-1] <= hi + 1e-8, 'responses: extrapolation outside common support')
            require(x[0] <= lo + 1e-6 and x[-1] >= hi - 1e-6, 'responses: unexplained support undercoverage')
            yy = np.asarray([np.interp(x, r['x'], r['y']) for r in records])
            weights = np.asarray([truth.multiplicity(r, number(config['symprec_A']), number(config.get('angle_tolerance_degrees', 5))) for r in records], float)
            full = weights @ yy / weights.sum()
            close(a[:, 1], full, 'responses: wrong population-weighted average')
            first = min(range(len(records)), key=lambda i: records[i]['site'])
            expected = np.column_stack([x, full, yy.mean(axis=0), yy[first]])
            close(ablations[key], expected, 'ablations: incorrect populations or representative')
    effects = table(output / 'effects.csv', ['material', 'element', 'edge', 'approximation', 'fwhm_eV', 'relative_shape_L2', 'relative_area_error', 'peak_shift_eV'])
    unique(effects, ['material', 'element', 'edge', 'approximation', 'fwhm_eV'], 'effects')
    multi = {key for key, rr in source_groups.items() if len(rr) > 1}
    conditions = {(r['approximation'], number(r['fwhm_eV'])) for r in effects}
    require({'equal_sites', 'first_representative'} <= {c[0] for c in conditions}, 'Missing site simplification comparison')
    require(len({c[1] for c in conditions}) >= 2, 'Missing resolution sensitivity')
    require({('__'.join((r['material'], r['element'], r['edge'])), r['approximation'], number(r['fwhm_eV'])) for r in effects}
            == {(k, a, w) for k in multi for a, w in conditions}, 'effects: missing or unknown comparison cases / undercoverage')
    for row in effects:
        key = '__'.join((row['material'], row['element'], row['edge']))
        rr = source_groups[key]
        lo, hi = max(r['x'][0] for r in rr), min(r['x'][-1] for r in rr)
        x = np.arange(lo, hi + .00001, .1)
        x = x[x <= hi]
        yy = np.asarray([np.interp(x, r['x'], r['y']) for r in rr])
        w = np.asarray([truth.multiplicity(r, number(config['symprec_A']), number(config.get('angle_tolerance_degrees', 5))) for r in rr], float)
        target = w @ yy / w.sum()
        approximation = row['approximation']
        require(approximation in {'equal_sites', 'first_representative'}, 'Unsupported approximation: independent review required')
        y = yy.mean(axis=0) if approximation == 'equal_sites' else yy[min(range(len(rr)), key=lambda i: rr[i]['site'])]
        width = number(row['fwhm_eV'])
        require(width >= 0, 'Negative broadening width')
        if width:
            target = gaussian_filter1d(target, width / 2.354820045 / .1, mode='nearest')
            y = gaussian_filter1d(y, width / 2.354820045 / .1, mode='nearest')
        mask = (x >= lo + 3) & (x <= hi - 3)
        ia, ib = np.trapezoid(target[mask], x[mask]), np.trapezoid(y[mask], x[mask])
        expected = np.linalg.norm(y[mask] / ib - target[mask] / ia) / np.linalg.norm(target[mask] / ia)
        close(number(row['relative_shape_L2']), expected, 'effects: wrong shape distortion')
        close(number(row['relative_area_error']), ib / ia - 1, 'effects: wrong area distortion')
        close(number(row['peak_shift_eV']), x[mask][np.argmax(y[mask])] - x[mask][np.argmax(target[mask])], 'effects: wrong peak displacement', atol=.100001)
    summary = json.loads((output / 'summary.json').read_text())
    require(integer(summary['raw_records']) == len(truth.records), 'summary: wrong raw record count')
    require(integer(summary['complete_responses']) == len(expected_keys), 'summary: wrong complete response count')
    for stat in summary['statistics']:
        values = np.asarray([number(r['relative_shape_L2']) for r in effects if r['approximation'] == stat['approximation'] and number(r['fwhm_eV']) == number(stat['fwhm_eV'])])
        require(len(values) == integer(stat['n_multisite_responses']), 'summary: wrong distortion cohort size')
        for field, expected in [('median', np.median(values)), ('q95', np.quantile(values, .95)), ('max', values.max()), ('fraction_over_5pct', np.mean(values > .05))]:
            close(number(stat[field]), expected, 'summary: wrong ' + field)
    rankings = table(output / 'ranking_sensitivity.csv', ['approximation', 'fwhm_eV', 'n_materials', 'spearman_vs_unbroadened', 'top50_overlap', 'top50_jaccard'])
    for row in rankings:
        collections = []
        for width in [0., number(row['fwhm_eV'])]:
            values = {}
            for effect in effects:
                if effect['approximation'] == row['approximation'] and number(effect['fwhm_eV']) == width:
                    material = effect['material']
                    values[material] = max(values.get(material, 0.), round(number(effect['relative_shape_L2']), 12))
            collections.append(values)
        a, b = collections
        require(set(a) == set(b) and integer(row['n_materials']) == len(a), 'Wrong rank-comparison material coverage')
        names = sorted(a)
        close(number(row['spearman_vs_unbroadened']), spearmanr([a[m] for m in names], [b[m] for m in names]).statistic, 'Wrong resolution rank correlation')
        top_a = set(sorted(names, key=lambda m: (-a[m], m))[:50])
        top_b = set(sorted(names, key=lambda m: (-b[m], m))[:50])
        require(integer(row['top50_overlap']) == len(top_a & top_b), 'Wrong resolution top-50 overlap')
        close(number(row['top50_jaccard']), len(top_a & top_b) / len(top_a | top_b), 'Wrong resolution rank-set similarity')
    sensitivity = table(output / 'symmetry_sensitivity.csv', ['material', 'element', 'edge', 'symprec_A', 'same_equivalence_partition', 'complete_coverage', 'multiplicity_changes'])
    unique(sensitivity, ['material', 'element', 'edge', 'symprec_A'], 'symmetry sensitivity')
    require({(r['material'], r['element'], r['edge']) for r in sensitivity} == set(truth.groups), 'Symmetry sensitivity group undercoverage')
    for row in sensitivity:
        key = row['material'], row['element'], row['edge']
        if key[0] in truth.inconsistent_materials:
            continue
        try:
            eq = truth.equivalence(key[0], number(row['symprec_A']), number(config.get('angle_tolerance_degrees', 5)))
        except AssertionError:
            require(integer(row['multiplicity_changes']) == -1 and not boolean(row['complete_coverage']), 'Missing-symmetry sensitivity incorrectly described')
            continue
        original = truth.equivalence(key[0], number(config['symprec_A']), number(config.get('angle_tolerance_degrees', 5)))
        rr = [truth.records[name] for name in truth.groups[key]]
        need = {eq[i] for i, site in enumerate(truth.structures[key[0]]['sites']) if site['species'][0]['element'] == key[1]}
        present = [eq[r['site']] for r in rr]
        require(boolean(row['same_equivalence_partition']) == bool(np.array_equal(eq, original)), 'Wrong symmetry-tolerance partition sensitivity')
        require(boolean(row['complete_coverage']) == (set(present) == need and len(set(present)) == len(present)), 'Wrong symmetry-tolerance coverage')
        changes = sum(np.count_nonzero(eq == eq[r['site']]) != np.count_nonzero(original == original[r['site']]) for r in rr)
        require(integer(row['multiplicity_changes']) == changes, 'Wrong symmetry-tolerance multiplicity changes')
    review.append('Q1: assess exclusions and representative-site convention, energy-support choices, symmetry sensitivity and scientific meaning of distortion distributions.')
    return {'complete_edge_responses': len(expected_keys), 'multisite_edge_responses': len(multi), 'reconstructed_comparisons': len(effects)}


def paired_sources(truth):
    pairs = {}
    for native in truth.records.values():
        pairs.setdefault((native['material'], native['element'], str(native['site'])), {})[native['edge']] = native
    return pairs


def integral(record, lo, hi):
    x, y = record['x'] - record['x'][0], record['y']
    require(lo >= x[0] and hi <= x[-1], 'Integral window outside native support')
    knots = np.r_[lo, x[(x > lo) & (x < hi)], hi]
    return float(np.trapezoid(np.interp(knots, x, y), knots))


def q2_audit(output, truth, config, sites, geometry, review):
    rows = table(output / 'descriptors.csv', ['name', 'material', 'element', 'site', 'geometry', 'area_L2', 'area_L3', 'log_ratio'])
    unique(rows, ['name'], 'descriptors')
    pairs = paired_sources(truth)
    check_paired_eligibility(truth, pairs, sites, geometry, False)
    included = {r['name'] for r in truth.records.values() if r['edge'] == 'L3' and boolean(sites[r['name']]['included'])}
    require({row['name'] for row in rows} == included, 'descriptors: missing or unknown included paired sites / undercoverage')
    for row in rows:
        key = row['material'], row['element'], str(integer(row['site']))
        pair = pairs[key]
        require(set(pair) == {'L2', 'L3'} and all(r['valid'] for r in pair.values()), 'Invalid/unpaired descriptor')
        require(row['name'] == pair['L3']['name'], 'Descriptor does not name native L3 record')
        require(all(boolean(sites[r['name']]['included']) for r in pair.values()), 'Unequal pair inclusion')
        g = geometry[key]
        for field in ['geometry', 'geometry_shell_1p15', 'geometry_shell_1p25', 'geometry_angular_0p10', 'ligand_family', 'composition_key']:
            if field in g:
                require(row[field] == g[field], 'Descriptor/geometry disagreement: ' + field)
        for field in ['bond_length_A', 'absorber_fraction', 'multiplicity']:
            close(number(row[field]), number(g[field]), 'Descriptor/geometry disagreement: ' + field)
        for lo, hi in config['area_windows_eV']:
            k = f'{int(lo)}_{int(hi)}'
            l2, l3 = integral(pair['L2'], lo, hi), integral(pair['L3'], lo, hi)
            require(l2 > 0 and l3 > 0, 'Nonpositive edge integral')
            for col, expected in [('area_L2_' + k, l2), ('area_L3_' + k, l3), ('log_ratio_' + k, np.log(l3 / l2))]:
                close(number(row[col]), expected, 'Wrong native edge descriptor: ' + col)
        for base in ['area_L2', 'area_L3', 'log_ratio']:
            close(number(row[base]), number(row[base + '_3_33']), 'Wrong primary descriptor alias')
    assoc = table(output / 'associations.csv', ['feature', 'geometry_definition', 'adjustment', 'n_sites', 'n_materials', 'tetra_minus_octa_log_ratio', 'ci025', 'ci975'])
    unique(assoc, ['feature', 'geometry_definition', 'adjustment'], 'associations')
    for row in assoc:
        coefficient, n, nm, ns = association_coefficient(rows, row)
        close(number(row['tetra_minus_octa_log_ratio']), coefficient, 'Wrong adjusted geometry contrast', rtol=2e-5, atol=2e-7)
        require(integer(row['n_sites']) == n and integer(row['n_materials']) == nm, 'Wrong association support')
        require(integer(row['n_chemical_strata']) == ns, 'Wrong chemistry overlap support')
        require(number(row['ci025']) <= number(row['ci975']), 'Reversed uncertainty interval')
        key = (sha256(output / 'descriptors.csv'), row['feature'], row['geometry_definition'], row['adjustment'], integer(row['bootstrap_replicates']), integer(config['random_seed']))
        if key not in ASSOCIATION_INTERVAL_CACHE:
            ASSOCIATION_INTERVAL_CACHE[key] = association_interval(rows, row, integer(config['random_seed']))
        close([number(row['ci025']), number(row['ci975'])], ASSOCIATION_INTERVAL_CACHE[key], 'Wrong material-bootstrap association interval', rtol=3e-5, atol=3e-7)
    review.append('Q2: assess effect support, residual confounding, integration conventions and sensitivity; descriptors, point contrasts and material-bootstrap intervals were independently reconstructed.')
    return {'paired_descriptors': len(rows), 'source_integrals_reconstructed': len(rows) * len(config['area_windows_eV']) * 2, 'adjusted_contrasts_reconstructed': len(assoc)}


def association_coefficient(rows, declaration):
    """Weighted within-stratum demeaning, independent of candidate dummy-matrix solve."""
    geometry, feature, adjustment = declaration['geometry_definition'], declaration['feature'], declaration['adjustment']
    rr = [row for row in rows if row[geometry] in {'tetrahedral', 'octahedral'}]
    def stratum(row):
        if adjustment == 'unadjusted':
            return 'all'
        if adjustment == 'element':
            return row['element']
        if adjustment == 'element_ligand':
            return row['element'] + '::' + row['ligand_family']
        if adjustment in {'composition', 'composition_fixed_effect'}:
            return row['composition_key']
        if adjustment == 'exact_composition':
            return row['element'] + '::' + row['composition_key']
        raise AssertionError('Unsupported chemistry adjustment requires independent scientific review')
    labels = {}
    for row in rr:
        labels.setdefault(stratum(row), set()).add(row[geometry])
    rr = [row for row in rr if len(labels[stratum(row)]) == 2]
    require(rr, 'No within-chemistry geometry overlap')
    w = np.asarray([number(row['multiplicity']) for row in rr])
    total = {}
    for row, weight in zip(rr, w):
        total[row['material']] = total.get(row['material'], 0) + weight
    w /= [total[row['material']] for row in rr]
    y = np.asarray([number(row[feature]) for row in rr])
    x = np.asarray([[float(row[geometry] == 'tetrahedral'), number(row['bond_length_A']), number(row['absorber_fraction'])] for row in rr])
    if adjustment == 'unadjusted':
        x = x[:, :1]
    elif x.shape[1] > 1:
        x[:, 1:] = (x[:, 1:] - x[:, 1:].mean(axis=0)) / np.maximum(x[:, 1:].std(axis=0), 1e-12)
    strata = np.asarray([stratum(row) for row in rr])
    for label in set(strata):
        selected = strata == label
        x[selected] -= np.average(x[selected], axis=0, weights=w[selected])
        y[selected] -= np.average(y[selected], weights=w[selected])
    coef = np.linalg.lstsq(x * np.sqrt(w[:, None]), y * np.sqrt(w), rcond=1e-10)[0][0]
    return coef, len(rr), len(total), len(set(strata))


def check_paired_eligibility(truth, pairs, sites, geometry, binary):
    for key, pair in pairs.items():
        expected = (key[0] not in truth.inconsistent_materials and set(pair) == {'L2', 'L3'}
                    and all(r['valid'] and r['x'][-1] - r['x'][0] >= 46 for r in pair.values()))
        if expected and binary:
            expected = geometry[key]['geometry'] in {'tetrahedral', 'octahedral'}
        require(all(boolean(sites[r['name']]['included']) == expected for r in pair.values()),
                'sites: inclusion contradicts declared paired-spectrum/geometry eligibility rule')


def association_interval(rows, declaration, seed):
    """Bootstrap direct residualized weighted least squares, not moment subtraction."""
    geometry, feature, adjustment = declaration['geometry_definition'], declaration['feature'], declaration['adjustment']
    def key(row):
        if adjustment == 'unadjusted': return 'all'
        if adjustment == 'element': return row['element']
        if adjustment == 'element_ligand': return row['element'] + '::' + row['ligand_family']
        if adjustment == 'exact_composition': return row['element'] + '::' + row['composition_key']
        return row['composition_key']
    rr = [row for row in rows if row[geometry] in {'tetrahedral', 'octahedral'}]
    shapes = {}
    for row in rr:
        shapes.setdefault(key(row), set()).add(row[geometry])
    rr = [row for row in rr if len(shapes[key(row)]) == 2]
    strata = {label: i for i, label in enumerate(sorted({key(row) for row in rr}))}
    materials = {label: i for i, label in enumerate(sorted({row['material'] for row in rr}))}
    st = np.asarray([strata[key(row)] for row in rr])
    mi = np.asarray([materials[row['material']] for row in rr])
    w = np.asarray([number(row['multiplicity']) for row in rr])
    w /= np.bincount(mi, weights=w)[mi]
    y = np.asarray([number(row[feature]) for row in rr])
    x = np.asarray([[float(row[geometry] == 'tetrahedral'), number(row['bond_length_A']), number(row['absorber_fraction'])] for row in rr])
    if adjustment == 'unadjusted':
        x = x[:, :1]
    else:
        x[:, 1:] = (x[:, 1:] - x[:, 1:].mean(axis=0)) / np.maximum(x[:, 1:].std(axis=0), 1e-12)
    rng = np.random.default_rng(seed)
    results = []
    for _ in range(integer(declaration['bootstrap_replicates'])):
        counts = np.bincount(rng.integers(0, len(materials), len(materials)), minlength=len(materials))
        weight = w * counts[mi]
        totals = np.bincount(st, weights=weight, minlength=len(strata))
        denom = np.maximum(totals, 1e-30)
        centered_x = x - np.column_stack([np.bincount(st, weights=weight * x[:, j], minlength=len(strata)) / denom for j in range(x.shape[1])])[st]
        centered_y = y - (np.bincount(st, weights=weight * y, minlength=len(strata)) / denom)[st]
        sw = np.sqrt(weight)
        results.append(float(np.linalg.lstsq(centered_x * sw[:, None], centered_y * sw, rcond=1e-5)[0][0]))
    return np.quantile(results, [.025, .975])


def metric_bootstrap(truth_labels, predictions, compositions, replicates, seed):
    """Independent confusion-count resampling, grouped by source composition."""
    classes = ['octahedral', 'tetrahedral']
    groups = sorted(set(compositions))
    lookup = {key: i for i, key in enumerate(groups)}
    counts = np.zeros((len(groups), 2, 2), dtype=np.int64)
    for actual, prediction, composition in zip(truth_labels, predictions, compositions):
        counts[lookup[composition], classes.index(actual), classes.index(prediction)] += 1
    confusion = counts.sum(axis=0)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(replicates):
        selected = rng.integers(0, len(groups), len(groups))
        resampled = counts[selected].sum(axis=0)
        if np.all(resampled.sum(axis=1) > 0):
            draws.append(float(np.mean(np.diag(resampled) / resampled.sum(axis=1))))
        else:
            draws.append(np.nan)
    return confusion, np.asarray(draws)


def q3_audit(output, truth, config, sites, geometry, review):
    predictions = table(output / 'predictions.csv', ['name', 'material', 'element', 'site', 'composition_key', 'method', 'split', 'actual', 'predicted'])
    unique(predictions, ['name', 'method'], 'predictions')
    partitions = table(output / 'partitions.csv', ['material', 'method', 'split', 'role', 'composition_key'])
    unique(partitions, ['material', 'method', 'split'], 'partitions')
    eligible = {r['name'] for r in truth.records.values() if r['edge'] == 'L3' and boolean(sites[r['name']]['included'])}
    pairs = paired_sources(truth)
    check_paired_eligibility(truth, pairs, sites, geometry, True)
    require(eligible, 'No eligible prediction sites')
    for name in eligible:
        r = truth.records[name]
        key = r['material'], r['element'], str(r['site'])
        pair = pairs[key]
        require(set(pair) == {'L2', 'L3'} and all(p['valid'] and boolean(sites[p['name']]['included']) for p in pair.values()), 'Q3 includes invalid/unpaired edge')
        require(geometry[key]['geometry'] in {'tetrahedral', 'octahedral'}, 'Q3 target outside declared regular geometry classes')
    methods = sorted({p['method'] for p in predictions})
    require(any(m.startswith('L3_') for m in methods) and any(m.startswith('L23_') for m in methods), 'Missing matched spectral comparison')
    require('majority' in methods, 'Missing training-prevalence baseline')
    require({p['method'] for p in partitions} == set(methods), 'Partition/prediction method disagreement')
    partition_index = {(p['material'], p['method'], p['split']): p['role'] for p in partitions}
    splits = sorted({p['split'] for p in predictions})
    require(len(splits) >= 2, 'Held-out evaluation requires multiple folds')
    material_set = {truth.records[name]['material'] for name in eligible}
    require(set(partition_index) == {(m, method, split) for m in material_set for method in methods for split in splits},
            'Incomplete or unknown partition material coverage')
    for row in partitions:
        require(row['role'] in {'train', 'test'}, 'Unsupported partition role')
        require(normalize_composition(row['composition_key']) == truth.compositions[row['material']], 'Wrong partition composition')
    for method in methods:
        method_rows = [p for p in predictions if p['method'] == method]
        require({p['name'] for p in method_rows} == eligible, 'predictions: missing/unknown test IDs / undercoverage')
        for split in splits:
            train_materials = {m for m in material_set if partition_index[(m, method, split)] == 'train'}
            test_materials = material_set - train_materials
            require(train_materials and test_materials, 'Empty train/test fold')
            train_compositions = {truth.compositions[m] for m in train_materials}
            test_compositions = {truth.compositions[m] for m in test_materials}
            require(not train_compositions & test_compositions, 'Train/test reduced-composition leakage')
            test_rows = [p for p in method_rows if p['split'] == split]
            require({p['name'] for p in test_rows} == {name for name in eligible if truth.records[name]['material'] in test_materials},
                    'OOF predictions disagree with complete test partition')
        for p in method_rows:
            native = truth.records[p['name']]
            require(native['edge'] == 'L3', 'Prediction does not identify native L3 site')
            require(p['material'] == native['material'] and p['element'] == native['element'] and integer(p['site']) == native['site'], 'Prediction source identity mismatch')
            key = native['material'], native['element'], str(native['site'])
            require(p['actual'] == geometry[key]['geometry'], 'Prediction target does not match reconstructed geometry')
            require(p['predicted'] in {'tetrahedral', 'octahedral'}, 'Invalid class prediction')
            require(normalize_composition(p['composition_key']) == truth.compositions[native['material']], 'Wrong prediction composition')
            require(partition_index[(native['material'], method, p['split'])] == 'test', 'Prediction is not held out')
    # The intervention must be paired, including baselines.
    reference_folds = {p['name']: p['split'] for p in predictions if p['method'] == methods[0]}
    require(all(p['split'] == reference_folds[p['name']] for p in predictions), 'Methods use different held-out specimens/folds')
    for method in methods:
        require(all(partition_index[(m, method, s)] == partition_index[(m, methods[0], s)] for m in material_set for s in splits), 'Methods use different training partitions')
    # Reconstruct baseline predictions directly from training-only labels.
    baseline_cache = {}
    for p in predictions:
        if p['method'] not in {'majority', 'element_prior'}:
            continue
        cache_key = (p['method'], p['split'], p['element'] if p['method'] == 'element_prior' else '')
        if cache_key in baseline_cache:
            require(p['predicted'] in baseline_cache[cache_key], 'Baseline prediction did not use training-only prevalence')
            continue
        train_names = [name for name in eligible if partition_index[(truth.records[name]['material'], p['method'], p['split'])] == 'train']
        if p['method'] == 'element_prior':
            specific = [name for name in train_names if truth.records[name]['element'] == p['element']]
            train_names = specific or train_names
        labels = [geometry[(truth.records[name]['material'], truth.records[name]['element'], str(truth.records[name]['site']))]['geometry'] for name in train_names]
        counts = {label: labels.count(label) for label in set(labels)}
        modes = {label for label, count in counts.items() if count == max(counts.values())}
        baseline_cache[cache_key] = modes
        require(p['predicted'] in modes, 'Baseline prediction did not use training-only prevalence')
    summary = json.loads((output / 'summary.json').read_text())
    require(integer(summary['n_sites']) == len(eligible) and integer(summary['n_materials']) == len(material_set), 'Wrong evaluation cohort size')
    require(integer(summary['n_compositions']) == len({truth.compositions[m] for m in material_set}), 'Wrong held-out composition count')
    metrics = {row['method']: row for row in summary['metrics']}
    require(len(metrics) == len(summary['metrics']) and set(metrics) == set(methods), 'Missing/duplicate/unknown model metrics')
    draws = {}
    for method in methods:
        rows = sorted([p for p in predictions if p['method'] == method], key=lambda p: p['name'])
        y, pred = [p['actual'] for p in rows], [p['predicted'] for p in rows]
        # Preserve declared composition-string sorting for exact bootstrap replay;
        # every string has already been independently chemically validated.
        compositions = [p['composition_key'] for p in rows]
        scores = metrics[method]
        require(integer(scores['n_test_sites']) == len(rows), 'Wrong metric sample count')
        close(number(scores['balanced_accuracy']), balanced_accuracy_score(y, pred), 'Wrong held-out balanced accuracy')
        close(number(scores['macro_f1']), f1_score(y, pred, labels=['octahedral', 'tetrahedral'], average='macro'), 'Wrong held-out macro F1')
        cm, draw = metric_bootstrap(y, pred, compositions, integer(summary['bootstrap_replicates']), integer(config['random_seed']))
        close(scores['confusion_matrix'], cm, 'Wrong confusion matrix')
        close([number(scores['ci025']), number(scores['ci975'])], np.nanquantile(draw, [.025, .975]), 'Wrong composition-bootstrap interval')
        draws[method] = draw
    for contrast in summary['paired_differences']:
        width = number(contrast['fwhm_eV'])
        a, b = f'L23_fwhm{width:g}', f'L3_fwhm{width:g}'
        require(a in metrics and b in metrics, 'Missing paired resolution comparison')
        expected = number(metrics[a]['balanced_accuracy']) - number(metrics[b]['balanced_accuracy'])
        close(number(contrast['L23_minus_L3_balanced_accuracy']), expected, 'Wrong paired incremental score')
        close([number(contrast['ci025']), number(contrast['ci975'])], np.nanquantile(draws[a] - draws[b], [.025, .975]), 'Wrong paired composition-bootstrap interval')
    review.append('Q3: inspect and rerun training code to rule out feature/tuning leakage; numerical checks prove declared composition partitions, labels, predictions/metrics and paired uncertainty are internally consistent, not that submitted model code used them.')
    return {'test_sites_per_method': len(eligible), 'materials': len(material_set), 'compositions': summary['n_compositions'], 'methods': methods, 'folds': len(splits), 'predictions_checked': len(predictions)}


def verify(question, output, inputs=DEFAULT_INPUTS):
    output = Path(output)
    report = {'question': question, 'validation_profile': 'worked-example-declared-conventions',
              'scope': 'Audits the worked artifacts and explicitly declared conventions; additional filenames/algorithms are not solver-facing requirements. Other methods use verify_submission.py plus scientific review.',
              'integrity_pass': False, 'scientific_pass': None,
              'checks': {}, 'scientific_review_required': []}
    try:
        require(question in {'Q1', 'Q2', 'Q3'}, 'Unknown question')
        require((output / 'analysis.py').is_file() and (output / 'report.md').is_file(), 'Missing reproducible analysis or scientific report')
        config = json.loads((output / 'definitions.json').read_text())
        truth = load_truth(str(Path(inputs).resolve()))
        report['source_provenance'] = provenance(truth)
        source_manifest = json.loads((DEFAULT_INPUTS.parent / 'provenance.json').read_text())
        for asset in source_manifest['input_assets']:
            element = asset['name'].split('.')[0]
            require(report['source_provenance']['sha256'][element] == asset['sha256'], 'Raw package differs from verified release bytes')
        sites = site_audit(output, truth, config)
        report['checks']['native_site_records'] = len(sites)
        review = report['scientific_review_required']
        if question == 'Q1':
            report['checks'].update(q1_audit(output, truth, config, sites, review))
        else:
            geometry = geometry_audit(output, truth, config)
            report['checks']['independent_periodic_environments'] = len(geometry)
            function = q2_audit if question == 'Q2' else q3_audit
            report['checks'].update(function(output, truth, config, sites, geometry, review))
        report['integrity_pass'] = True
        review.append('Apply verification/scientific_review_rubric.md and retain actual clean execution plus claim-level scientific review. A numerical pass is not final acceptance and does not calibrate difficulty.')
    except (AssertionError, ValueError, KeyError, IndexError, TypeError, OSError) as error:
        report['error'] = f'{type(error).__name__}: {error}'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question', nargs='?', choices=['Q1', 'Q2', 'Q3'])
    parser.add_argument('--question', dest='question_flag', choices=['Q1', 'Q2', 'Q3'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inputs', type=Path, default=DEFAULT_INPUTS)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    question = args.question_flag or args.question
    parser.error('Supply a question positionally or with --question') if question is None else None
    result = verify(question, args.output, args.inputs)
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text, end='')
    raise SystemExit(0 if result['integrity_pass'] else 1)


if __name__ == '__main__':
    main()
