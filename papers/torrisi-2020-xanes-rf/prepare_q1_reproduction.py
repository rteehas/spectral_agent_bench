"""Prepare a label-isolated Q1 bundle from the independently audited release rows."""
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
ELEMENTS = ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']
INPUTS = DATA / 'inputs/Q1_paper'
TRUTH = DATA / 'verification/Q1_paper'


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    INPUTS.mkdir(parents=True, exist_ok=True)
    TRUTH.mkdir(parents=True, exist_ok=True)
    anchors = json.loads((DATA / 'verification/source_anchor_audit.json').read_text())
    provenance = json.loads((DATA / 'provenance.json').read_text())
    truth = {}
    audit = {}
    for element in ELEMENTS:
        source = DATA / 'inputs' / (element + '.jsonl.gz')
        sha = hashlib.sha256(source.read_bytes()).hexdigest()
        expected = next(r for r in provenance['sources'] if r['element'] == element)
        assert sha == expected['input_sha256']
        with gzip.open(source, 'rt') as stream:
            rows = list(map(json.loads, stream))
        x = np.asarray([r['mu'] for r in rows], dtype=float)
        energies = np.asarray([r['E'] for r in rows], dtype=float)
        assert x.shape[1] == 100 and np.isfinite(x).all()
        np.testing.assert_allclose(energies, np.broadcast_to(energies[0], energies.shape), rtol=0, atol=1e-10)
        peak = x.max(axis=1)
        eligible = np.array([r['coordination'] in [4, 5, 6] for r in rows])
        physical = (x[:, -1] != peak) & (peak <= 3) & ~np.any(x[:, :10] == peak[:, None], axis=1)
        vandermonde = np.vander(np.linspace(-1, 1, 5), 4, increasing=True)
        residual = np.eye(5) - vandermonde @ np.linalg.pinv(vandermonde)
        normalized = np.divide(x, peak[:, None], out=np.zeros_like(x), where=peak[:, None] != 0)
        errors = np.sum(np.abs(normalized.reshape(-1, 20, 5) @ residual.T), axis=2)
        selected = np.flatnonzero(eligible & physical & (errors <= .1).all(axis=1))
        dev, test = train_test_split(selected, test_size=.1, random_state=42)
        train, valid = train_test_split(dev, test_size=.1, random_state=42)
        parts = {'train': train, 'validation': valid, 'test': test}
        archive = anchors['elements'][element]['targets']['coord']
        assert len(selected) == archive['eligible_count']
        arrays = {'energy_eV': energies[0]}
        truth[element] = {}
        for role, indices in parts.items():
            raw_role = 'valid' if role == 'validation' else role
            assert indices.tolist() == archive['partitions'][raw_role]['source_rows']
            labels = np.array([rows[i]['coordination'] for i in indices], dtype=np.int64)
            np.testing.assert_array_equal(labels, archive['partitions'][raw_role]['y'])
            arrays[role + '_spectra'] = x[indices]
            arrays[role + '_source_rows'] = indices
            if role != 'test':
                arrays[role + '_labels'] = labels
            truth[element][role] = {'source_rows': indices.tolist(), 'labels': labels.tolist()}
        path = INPUTS / (element + '.npz')
        np.savez_compressed(path, **arrays)
        counts = np.bincount(arrays['train_labels'], minlength=7)[4:7]
        audit[element] = {'raw_input_sha256': sha, 'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'retained_records': len(selected), 'partition_counts': {k: len(v) for k, v in parts.items()},
                          'training_class_counts': dict(zip(['4', '5', '6'], map(int, counts))),
                          'oversampled_training_records': int(counts.max() * 3),
                          'matches_archived_row_order_and_labels': True,
                          'retained_origins': {str(origin): sum(rows[i]['metadata']['origin'] == origin for i in selected)
                                              for origin in sorted({r['metadata']['origin'] for r in rows})}}
        print(element, audit[element]['partition_counts'], flush=True)
    protocol = {
        'schema_version': 1, 'task': 'TORRISI20-Q1-paper-v1',
        'elements': ELEMENTS, 'classes': [4, 5, 6], 'forest_seeds': list(range(42, 52)),
        'representation': 'Use the 100 supplied absorption values directly, in column order. Preserve their post-edge normalization; do not renormalize or add metadata predictors.',
        'partitions': 'Use the supplied train/validation/test arrays in their supplied row order. No refitting on validation rows or test-based selection. The archived two-stage split is approximately 81/9/10; it is the released implementation of the paper-described 80/10/10 split.',
        'oversampling': {'method': 'Random sampling with replacement from each minority training class until all training classes match the majority count.',
                         'random_seed': 42, 'order': 'Keep all original training rows first. With one numpy.random.RandomState(42), visit class labels in increasing order and append the sampled rows for each class. Leave validation and test arrays unchanged.'},
        'estimator': 'sklearn.ensemble.RandomForestClassifier',
        'parameters': {'n_estimators': 300, 'criterion': 'gini', 'max_depth': 35, 'max_features': 8,
                       'min_samples_split': 2, 'min_samples_leaf': 1, 'min_weight_fraction_leaf': 0.0,
                       'max_leaf_nodes': None, 'min_impurity_decrease': 0.0, 'bootstrap': True,
                       'oob_score': False, 'warm_start': False, 'class_weight': None, 'ccp_alpha': 0.0,
                       'max_samples': None},
        'runtime': {'numpy': '2.5.3', 'scikit-learn': '1.9.1'},
        'runtime_note': 'This pinned modern runtime is validated separately against the published results; the paper used scikit-learn 0.21.3. n_jobs is an execution setting and may be chosen freely.',
        'output': {'predictions.csv': ['element', 'seed', 'source_row', 'prediction'],
                   'validation_predictions.csv': ['element', 'seed', 'source_row', 'prediction'],
                   'run.json': 'Record protocol_sha256, input_sha256 keyed by element, estimator, parameters, forest_seeds, runtime versions, and oversampled_training_records keyed by element.',
                   'report.md': 'Describe the reproduction and validation results. Test labels are withheld; test performance is calculated by the evaluator.',
                   'code': 'Provide runnable source and its command. The evaluation harness runs it with only the declared inputs.'},
        'evaluation_scope': 'Prediction on the released spectral-record holdout. Related materials can occur in different partitions; this does not establish unseen-material or experimental generalization.'
    }
    dump(INPUTS / 'protocol.json', protocol)
    dump(TRUTH / 'truth.json', truth)
    dump(TRUTH / 'preparation_audit.json', {
        'source': 'Lossless raw projections and independently verified author-release array memberships.',
        'original_array_audit': '../source_anchor_audit.json',
        'source_code': 'https://github.com/TRI-AMDD/trixs/blob/6dbcc598c7bea235f464bed91744c1617725b7a8/notebooks/Spectra_To_Model_Data.ipynb',
        'array_contents': 'energy_eV; train/validation spectra, labels and source rows; test spectra and source rows only. Structural metadata and other target labels are omitted.',
        'split_discrepancy': 'Paper: 80/10/10. Released two successive test_size=0.1 splits: approximately 81/9/10. Exact released membership is used.',
        'elements': audit, 'test_labels_present_in_solver_bundle': False})


if __name__ == '__main__':
    main()
