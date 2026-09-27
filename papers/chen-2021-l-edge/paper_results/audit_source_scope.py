#!/usr/bin/env python3
"""Check publication counts and Table 2 identities against the complete release."""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

TABLE2 = {
    'TiO2': {'panel': 'a', 'element': 'Ti', 'material': 'mp-2657'},
    'V2O5': {'panel': 'b', 'element': 'V', 'material': 'mp-754670'},
    'MgMn2O4': {'panel': 'c', 'element': 'Mn', 'material': 'mp-32006'},
    'LiFePO4': {'panel': 'd', 'element': 'Fe', 'material': 'mp-19017'},
    'Cu': {'panel': 'e', 'element': 'Cu', 'material': 'mp-30'},
    'Pt': {'panel': 'f', 'element': 'Pt', 'material': 'mp-126'},
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--paper-counts', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    count = collections.Counter()
    records = collections.defaultdict(list)
    wanted = {r['material'] for r in TABLE2.values()} | {'mp-761468', 'mp-849597'}
    digest = hashlib.sha256()
    with a.raw.open('rb') as source:
        for line in source:
            digest.update(line)
            r = json.loads(line)
            el = r['structure']['sites'][r['absorbing_atom']]['species'][0]['element']
            count[el] += 1
            if r['mp-id'] in wanted:
                records[r['mp-id']].append({'name': r['name'], 'element': el,
                    'edge': r['edge'], 'site': r['absorbing_atom'],
                    'native_line_sha256': hashlib.sha256(line).hexdigest()})
    assert digest.hexdigest() == '725281938c937c3aefded49253408f83c9b7d1736f59140a4f4442b69628af35'
    comparison = []
    for r in csv.DictReader(a.paper_counts.open()):
        element = r['element']
        published = int(r['paper_site_wise'])
        comparison.append({'element': element, 'published_site_wise': published,
                           'released_records': count[element],
                           'difference': count[element] - published,
                           'exact_match': count[element] == published})
    result = {
        'source_member_sha256': digest.hexdigest(),
        'release_records': sum(count.values()),
        'figure2_comparison': comparison,
        'figure2_conclusion': 'Literal published per-element site-wise counts do not all equal the versioned release record counts. No tolerance is substituted for integer equality. This census is not an active reproduction task.',
        'figure4_table2_source_audit': {
            formula: row | {'released_records': records[row['material']]} for formula, row in TABLE2.items()
        },
        'alternate_phase_records': {k: records[k] for k in ['mp-761468', 'mp-849597']},
        'identity_caveat': 'The LiFePO4 structure mp-761468 has the requested olivine phase and its computed response can be compared to Figure 4(d). It is not the exact mp-19017 calculation named in Table 2. Neither matching composition nor space group alone establishes numerical reproduction; the paper-curve gate remains mandatory.',
        'unavailable_stages': [
            'Figure 3 radius/core-hole parameter sweeps and their experimental reference arrays are absent from the release.',
            'Historical site-averaged arrays, coordination labels, and figure-generation scripts are not supplied.',
            'OCEAN and experimental spectra are not native inputs; extracted publication traces remain evaluator-only.'
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'records': sum(count.values()),
        'exact_figure2_counts': sum(r['exact_match'] for r in comparison),
        'absent_figure4_ids': [r['material'] for r in TABLE2.values() if not records[r['material']]]}))


if __name__ == '__main__':
    main()
