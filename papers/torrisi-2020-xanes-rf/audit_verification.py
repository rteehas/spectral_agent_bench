"""Historical release-array provenance audit for the XANES benchmark.

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


def main():
    parser=argparse.ArgumentParser(description='Reconstruct historical released arrays as source-provenance evidence. These splits are not requirements for revised research tasks.')
    parser.add_argument('--release',type=Path,required=True)
    args=parser.parse_args()
    build_source_anchors(args.release)

if __name__=='__main__':main()
