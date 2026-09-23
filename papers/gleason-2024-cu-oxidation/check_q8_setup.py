"""Check Q8 selection, FEFF setup and assembly offline; never claim a new FEFF run."""
import importlib.util
import importlib.metadata
import json
from pathlib import Path
import re
import tempfile
import zipfile
import numpy as np
import pandas as pd
from pymatgen.io.feff.inputs import Header

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/data/gleason-2024-cu-oxidation'
spec = importlib.util.spec_from_file_location('q8', BASE / 'workflows/search_and_simulate.py')
candidate = importlib.util.module_from_spec(spec); spec.loader.exec_module(candidate)


def main():
    references = json.loads((BASE / 'verification/Q8/reference_cases.json').read_text())['cases']
    records = [{'material_id': case['material_id'], 'formula': '',
                'elements': sorted({s['species'][0]['element'] for s in case['jobs'][0]['structure']['sites']}),
                'structure': case['jobs'][0]['structure'], 'deprecated': False,
                'is_stable': case['historical_is_stable'], 'theoretical': case['historical_theoretical']}
               for case in references]
    from pymatgen.core import Structure
    for r in records: r['formula'] = Structure.from_dict(r['structure']).composition.reduced_formula
    seeds = candidate.seed_ids(BASE / 'inputs/Q8')
    assert len(seeds) == 1530
    assert set(candidate.eligible(records, seeds)) == {r['material_id'] for r in records}
    assert len(candidate.eligible([records[0], records[0]], seeds)) == 1
    assert candidate.eligible([dict(records[0], material_id=next(iter(seeds)))], seeds) == {}
    assert candidate.eligible([dict(records[0], is_stable=False, theoretical=True)], seeds) == {}
    assert len(candidate.eligible([dict(records[0], is_stable=True, theoretical=True)], seeds)) == 1
    assert len(candidate.eligible([dict(records[0], is_stable=False, theoretical=False)], seeds)) == 1
    selected, _ = candidate.choose_three(candidate.eligible(records, seeds), .01)
    assert len(selected) == 3 and len(set(selected)) == 3
    metrics = []
    with tempfile.TemporaryDirectory(prefix='gleason-q8-setup-') as folder:
        output = Path(folder)
        candidate.dump(output / 'query_snapshot.json', {
            'source': 'OFFLINE TEST FIXTURE from three archived structure headers; not an MP search',
            'records': records})
        candidate.prepare(BASE / 'inputs/Q8', output)
        jobs = json.loads((output / 'jobs.json').read_text())['jobs']
        assert len(jobs) == 8
        for job in jobs:
            ref = next(j for c in references if c['material_id'] == job['material_id']
                       for j in c['jobs'] if j['site_index'] == job['site_index'] and j['edge'] == job['edge'])
            text = (output / job['directory'] / 'feff.inp').read_text()
            structure = Header.from_str(text).struct
            np.testing.assert_allclose(structure.lattice.matrix, np.asarray(ref['structure']['lattice']['matrix']), atol=1e-5)
            for key, expected in ref['tags'].items():
                actual = re.search(r'^' + key + r'\s+(.+)$', text, re.M).group(1).strip()
                try: np.testing.assert_allclose([float(v) for v in actual.split()], [float(v) for v in expected.split()], atol=1e-10)
                except ValueError: assert actual == expected, (key, actual, expected)
        try:
            candidate.prepare(BASE / 'inputs/Q8', output)
        except FileExistsError: pass
        else: raise AssertionError('Existing job decks should not be overwritten')
        # Intentionally use archived outputs only to test the assembly function.
        # Do not call the simulation runner or create a successful execution.json.
        archive_path = ROOT.parent / 'gleason_2024_cu_oxidation_state/data/Dataset_generation/FEFF_simulations/Stable_and_exp_Cu_with_results.zip'
        with zipfile.ZipFile(archive_path) as archive:
            for job in jobs:
                ref = next(j for c in references if c['material_id'] == job['material_id']
                           for j in c['jobs'] if j['site_index'] == job['site_index'] and j['edge'] == job['edge'])
                (output / job['directory'] / 'xmu.dat').write_bytes(archive.read(ref['xmu_member']))
        try:
            candidate.run(output, ['this-command-must-never-execute'])
        except FileExistsError: pass
        else: raise AssertionError('Simulation runner accepted substituted archived output')
        candidate.assemble(output)
        reference = pd.read_csv(BASE / 'verification/Q8/reference_material_spectra.csv')
        for mid in selected:
            actual = pd.read_csv(output / 'spectra' / mid / 'spectrum.csv')
            expected = reference.loc[reference.material_id == mid]
            np.testing.assert_allclose(actual[['energy_eV', 'intensity']], expected[['energy_eV', 'intensity']], rtol=1e-8, atol=1e-8)
            metrics.append({'material_id': mid, 'points': len(actual),
                            'maximum_intensity_difference': float(np.max(abs(actual.intensity.to_numpy() - expected.intensity.to_numpy())))})
        assert not (output / 'execution.json').exists()
    report = {'status': 'offline_setup_and_archived_output_assembly_passed',
              'tool_versions': {name: importlib.metadata.version(name) for name in ['mp-api', 'pymatgen', 'numpy', 'pandas', 'matplotlib']},
              'executed_command': '/tmp/gleason-preview-py310/bin/python papers/gleason-2024-cu-oxidation/check_q8_setup.py',
              'live_query_executed': False, 'new_feff_simulations_executed': False,
              'checks': ['Seed exclusion and Boolean OR selection', 'Three representative choices',
                         'Eight generated site/edge input decks agree with archived structures and control tags',
                         'Existing job decks cannot be overwritten', 'Archived outputs cannot be passed off as fresh simulations'],
              'assembly_comparisons': metrics,
              'remaining': ['Authenticated live Materials Project search', 'Fresh FEFF9 execution',
                            'Evaluator capture of current query and independent reference generation for changed/new structures']}
    candidate.dump(BASE / 'verification/Q8/setup_checks.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
