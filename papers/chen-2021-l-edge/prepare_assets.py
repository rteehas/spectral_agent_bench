#!/usr/bin/env python3
"""Losslessly project the versioned release; no solver-visible derived labels."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/data/chen-2021-l-edge'
ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')
EXPECTED_SHA256 = '39d25a0e8085af41d3f0a06bbab0b0e1a8a91968aa21bef23a2397774ccf9537'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def prepare(raw, archive, metadata):
    assert sha(archive) == EXPECTED_SHA256, 'Wrong release archive'
    inputs = BASE / 'inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    handles = {e: gzip.GzipFile(filename=str(inputs / f'{e}.jsonl.gz'), mode='wb', mtime=0) for e in ELEMENTS}
    counts, negative, selected = collections.Counter(), collections.Counter(), collections.Counter()
    materials, pairs, names = set(), collections.defaultdict(set), set()
    cohort_materials, cohort_pairs = set(), collections.defaultdict(set)
    cohort_groups, cohort_edge_groups = set(), set()
    structures = {}
    inconsistent_structures = set()
    source_hash = hashlib.sha256()
    native_hashes = {e: hashlib.sha256() for e in ELEMENTS}
    with Path(raw).open('rb') as f:
        for line in f:
            source_hash.update(line)
            d = json.loads(line)
            assert d['name'] not in names, 'Duplicate release name'
            names.add(d['name'])
            site = d['structure']['sites'][d['absorbing_atom']]
            assert len(site['species']) == 1 and site['species'][0]['occu'] == 1
            element = site['species'][0]['element']
            counts[element] += 1
            materials.add(d['mp-id'])
            pairs[(d['mp-id'], d['absorbing_atom'])].add(d['edge'])
            if min(d['spectrum'][1]) < 0:
                negative[element] += 1
            if element in handles:
                handles[element].write(line)
                native_hashes[element].update(line)
                selected[element] += 1
                cohort_materials.add(d['mp-id'])
                cohort_groups.add((d['mp-id'], element))
                cohort_edge_groups.add((d['mp-id'], element, d['edge']))
                cohort_pairs[(d['mp-id'], d['absorbing_atom'])].add(d['edge'])
                value = hashlib.sha256(json.dumps(d['structure'], sort_keys=True).encode()).hexdigest()
                previous = structures.setdefault(d['mp-id'], value)
                if previous != value:
                    inconsistent_structures.add(d['mp-id'])
    for h in handles.values():
        h.close()
    def pair_counts(p):
        return dict(collections.Counter('+'.join(sorted(v)) for v in p.values()))
    census = {
        'release_records': sum(counts.values()), 'release_materials': len(materials),
        'records_by_element': dict(counts), 'negative_records_by_element': dict(negative),
        'release_edge_pair_counts': pair_counts(pairs),
        'cohort_records': sum(selected.values()), 'cohort_materials': len(cohort_materials),
        'cohort_records_by_element': dict(selected), 'cohort_edge_pair_counts': pair_counts(cohort_pairs),
        'cohort_material_element_groups': len(cohort_groups), 'cohort_observed_edge_groups': len(cohort_edge_groups),
        'cohort_wholly_absent_edge_groups': 2 * len(cohort_groups) - len(cohort_edge_groups),
        'cohort_structure_inconsistencies': sorted(inconsistent_structures),
        'scope': 'Every released record whose absorbing element is Ti, V, Cr, Mn, Fe, Co, Ni or Cu; no selection by outcome, geometry, completeness or spectral validity.'
    }
    write(BASE / 'verification/release_census.json', census)
    meta = json.loads(Path(metadata).read_text())
    write(BASE / 'verification/figshare-v1.json', meta)
    write(BASE / 'provenance.json', {
        'paper_doi': '10.1038/s41597-021-00936-5',
        'data_doi': '10.6084/m9.figshare.12824513.v1',
        'creator': 'Yiming Chen (2020)',
        'license': meta['license'],
        'archive': {'name': 'L-XAS.json.tgz', 'bytes': Path(archive).stat().st_size,
                    'sha256': EXPECTED_SHA256, 'md5': '0dc8d5e3daaeb584167b49a57f15bc5e',
                    'url': 'https://ndownloader.figshare.com/files/24332060'},
        'member': {'name': 'L_XAS.json', 'bytes': Path(raw).stat().st_size, 'sha256': source_hash.hexdigest()},
        'selection': census['scope'],
        'transformation': 'Original JSON lines copied verbatim into per-absorber gzip streams; no numbers, keys, structures, FEFF parameters or ordering changed. No labels or processed spectra added.',
        'raw_meaning': 'Earliest numeric spectra in the release, already calculated by FEFF; neither experimental detector data nor FEFF intermediate output is released.',
        'input_assets': [
            {'name': f'{e}.jsonl.gz', 'records': selected[e], 'bytes': (inputs / f'{e}.jsonl.gz').stat().st_size,
             'sha256': sha(inputs / f'{e}.jsonl.gz'), 'uncompressed_sha256': native_hashes[e].hexdigest()}
            for e in ELEMENTS],
    })
    print(json.dumps(census, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--metadata', type=Path, required=True)
    a = p.parse_args()
    prepare(a.raw, a.archive, a.metadata)
