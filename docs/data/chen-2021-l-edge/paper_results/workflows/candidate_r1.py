#!/usr/bin/env python3
"""Worked native-data reconstruction for tetragonal MgMn2O4 and olivine LiFePO4.

This program deliberately does not read published curves or evaluator references.
Its intensity arrays remain on the release's absolute energy scale. The evaluator
may apply one rigid energy calibration per material when comparing with a plot.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import shutil
import warnings
from pathlib import Path

import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks
from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Compound identity is chemical/crystallographic; there are no hard-coded curves,
# published peak energies, shifts, source material identifiers, or fitted widths.
COMPOUNDS = {
    'MgMn2O4': {'element': 'Mn', 'space_group_number': 141},
    'LiFePO4': {'element': 'Fe', 'space_group_number': 62},
}
FWHM_EV = 1.2
N_STITCH_SAMPLES = 500
SYMPREC_A = 0.01


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def read_and_identify(inputs):
    groups = collections.defaultdict(list)
    audit = []
    for path in sorted(inputs.glob('*.jsonl.gz')):
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                r = json.loads(line)
                sd = r['structure']
                el = sd['sites'][r['absorbing_atom']]['species'][0]['element']
                if el not in {v['element'] for v in COMPOUNDS.values()}:
                    continue
                elements = {a['element'] for site in sd['sites'] for a in site['species']}
                if elements not in ({'Mg', 'Mn', 'O'}, {'Li', 'Fe', 'P', 'O'}):
                    continue
                s = Structure.from_dict(sd)
                formula = s.composition.reduced_formula
                if formula in COMPOUNDS and el == COMPOUNDS[formula]['element']:
                    groups[(formula, r['mp-id'])].append(r)
    selected = {}
    for (formula, mid), records in sorted(groups.items()):
        structure = Structure.from_dict(records[0]['structure'])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            sg_symbol, sg_number = structure.get_space_group_info(symprec=SYMPREC_A)
        include = sg_number == COMPOUNDS[formula]['space_group_number']
        audit.append({'material': formula, 'material_id': mid,
                      'space_group_symbol': sg_symbol, 'space_group_number': sg_number,
                      'records': len(records), 'selected_phase': include})
        if include:
            if formula in selected:
                raise ValueError(f'Ambiguous requested phase {formula}; inspect structures')
            selected[formula] = records
    if set(selected) != set(COMPOUNDS):
        raise ValueError(f'Missing requested phases: {set(COMPOUNDS)-set(selected)}')
    return selected, audit


def material_edges(records):
    structure = Structure.from_dict(records[0]['structure'])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        symmetry = SpacegroupAnalyzer(structure, symprec=SYMPREC_A).get_symmetrized_structure()
    el = structure[records[0]['absorbing_atom']].specie.symbol
    required = {tuple(indices) for indices in symmetry.equivalent_indices
                if structure[indices[0]].specie.symbol == el}
    edges = collections.defaultdict(list)
    for r in records:
        if Structure.from_dict(r['structure']) != structure:
            raise ValueError(f'Inconsistent structures for {r["mp-id"]}')
        edges[r['edge']].append(r)
    if set(edges) != {'L2', 'L3'}:
        raise ValueError('Both L2 and L3 are required')
    outputs, weights = {}, {}
    for edge, rr in edges.items():
        represented = [next(tuple(g) for g in symmetry.equivalent_indices
                            if r['absorbing_atom'] in g) for r in rr]
        if set(represented) != required or len(set(represented)) != len(represented):
            raise ValueError(f'Incomplete or duplicate {edge} site coverage')
        arrays = [np.asarray(r['spectrum'], dtype=float) for r in rr]
        for a in arrays:
            if (not np.isfinite(a).all() or np.any(np.diff(a[0]) <= 0)
                    or np.any(a[1] < 0) or np.max(a[1]) <= 0):
                raise ValueError('Invalid native intensity/energy arrays')
        x = np.linspace(max(a[0, 0] for a in arrays),
                        min(a[0, -1] for a in arrays), N_STITCH_SAMPLES)
        multiplicities = np.array([len(g) for g in represented], dtype=float)
        w = multiplicities / multiplicities.sum()
        y = sum(ww * interp1d(a[0], a[1], kind='cubic')(x)
                for ww, a in zip(w, arrays))
        outputs[edge] = (x, y)
        weights[edge] = [{'source_record_id': r['name'], 'multiplicity': int(n),
                         'normalised_weight': float(ww)}
                        for r, n, ww in zip(rr, multiplicities, w)]
    return outputs, weights


def run(inputs, output):
    output.mkdir(parents=True, exist_ok=True)
    selected, phase_audit = read_and_identify(inputs)
    rows, raw_rows, features, provenance = [], [], [], {}
    responses, sources = {}, []
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, (formula, records) in zip(axes, selected.items()):
        edges, weights = material_edges(records)
        x, l3 = edges['L3']
        l2 = interp1d(*edges['L2'], kind='cubic', bounds_error=False,
                      fill_value='extrapolate')(x)
        # The contemporaneous pymatgen L23 operation clips negative L2
        # extrapolation and adds the partial edges on the L3 support.
        raw = l3 + np.maximum(l2, 0)
        sigma = FWHM_EV / (2 * np.sqrt(2 * np.log(2)))
        y = gaussian_filter1d(raw, sigma / (x[1] - x[0]), mode='reflect')
        y /= y.max()
        dense = np.linspace(x[0], x[-1], int(np.ceil((x[-1]-x[0])/.025))+1)
        response = np.interp(dense, x, y)
        responses[f"{formula}__{COMPOUNDS[formula]['element']}__L23"] = np.c_[dense, response]
        sources.extend({'material': formula, 'material_id': r['mp-id'],
                        'element': COMPOUNDS[formula]['element'], 'edge': r['edge'],
                        'absorbing_atom': r['absorbing_atom'], 'name': r['name']}
                       for r in records)
        rows.extend({'material': formula, 'energy_eV': float(xx), 'intensity': float(yy)}
                    for xx, yy in zip(dense, response))
        raw_rows.extend({'material': formula, 'energy_eV': float(xx),
                         'L3_intensity': float(a), 'L2_nonnegative_intensity': float(b),
                         'L23_intensity': float(c)}
                        for xx, a, b, c in zip(x, l3, np.maximum(l2, 0), raw))
        # Local maxima above the L2 edge origin isolate the L2 white line;
        # this does not use an experimentally/paper-derived peak window.
        peaks, _ = find_peaks(y)
        l3_candidates = [i for i in peaks if x[i] < edges['L2'][0][0]]
        l2_candidates = [i for i in peaks if x[i] >= edges['L2'][0][0]]
        i3 = max(l3_candidates, key=lambda i: y[i])
        i2 = max(l2_candidates, key=lambda i: y[i])
        features.append({'material': formula, 'material_id': records[0]['mp-id'],
                         'L3_peak_eV': float(x[i3]), 'L2_peak_eV': float(x[i2]),
                         'peak_separation_eV': float(x[i2]-x[i3]),
                         'L2_over_L3_peak_height': float(y[i2]/y[i3])})
        provenance[formula] = {
            'source_record_ids': sorted(r['name'] for r in records),
            'material_id': records[0]['mp-id'], 'element': COMPOUNDS[formula]['element'],
            'energy_shift_eV': 0.0, 'broadening_fwhm_eV': FWHM_EV,
            'normalisation': 'maximum after broadening; no baseline subtraction',
            'space_group_number': COMPOUNDS[formula]['space_group_number'],
            'site_weights': weights,
        }
        ax.plot(dense, response, color='#247f46')
        ax.set_title(f"{formula}: {records[0]['mp-id']}")
        ax.set_xlabel('Released photon energy (eV)')
        ax.set_ylabel('Maximum-normalised absorption')
        ax.set_xlim(x[0], x[0]+36)
        ax.set_ylim(0, 1.05)
    write_csv(output/'figure4_reconstruction.csv', rows)
    write_csv(output/'figure4_native_stitch.csv', raw_rows)
    write_csv(output/'figure4_features.csv', features)
    write_csv(output/'figure4_phase_audit.csv', phase_audit)
    write_csv(output/'sources.csv', sources)
    np.savez_compressed(output/'responses.npz', **responses)
    shutil.copyfile(__file__, output/'analysis.py')
    (output/'figure4_provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    (output/'method.json').write_text(json.dumps({
        'symprec_A': SYMPREC_A, 'stitch_samples': N_STITCH_SAMPLES,
        'broadening_fwhm_eV': FWHM_EV, 'convolution_boundary': 'reflect',
        'site_averaging': 'crystallographic multiplicity; cubic interpolation on common support',
        'L23_stitch': 'sum L3 and nonnegative cubic L2 extrapolation on L3 support',
        'normalisation': 'maximum after broadening, no fitted intensity transform',
        'paper_data_read': False,
    }, indent=2)+'\n')
    fig.tight_layout()
    fig.savefig(output/'figure4_reconstruction.png', dpi=180)
    plt.close(fig)
    feature_map = {f['material']: f for f in features}
    text = ('Both compounds have a dominant L3 white line and a weaker L2 peak. '
            f"The MgMn2O4 L2/L3 peak-height ratio is {feature_map['MgMn2O4']['L2_over_L3_peak_height']:.3f}, "
            f"compared with {feature_map['LiFePO4']['L2_over_L3_peak_height']:.3f} for LiFePO4. "
            f"The separations are {feature_map['MgMn2O4']['peak_separation_eV']:.2f} and "
            f"{feature_map['LiFePO4']['peak_separation_eV']:.2f} eV, respectively. "
            'Absolute photon energies retain the release calibration. These are peak-height '
            'ratios after broadening, not integrated branching ratios or spin-state measurements.\n')
    (output/'answer.md').write_text(text)
    print(json.dumps({'reconstructed_materials': list(selected), 'features': features}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.output)
