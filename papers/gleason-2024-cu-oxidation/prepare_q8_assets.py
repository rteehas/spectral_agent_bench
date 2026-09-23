"""Extract Q8 inputs and independent archived examples from the open release.

This author-side program does not query Materials Project or execute FEFF.
The three archived examples are evaluator evidence, not a current MP search oracle.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import zipfile
import joblib
import numpy as np
from pymatgen.io.feff.inputs import Header

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT.parent / 'gleason_2024_cu_oxidation_state'
BASE = ROOT / 'docs/data/gleason-2024-cu-oxidation'
IDS = ['mp-10092', 'mp-1077262', 'mp-1207193']


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    inputs, truth = BASE / 'inputs/Q8', BASE / 'verification/Q8'
    inputs.mkdir(parents=True, exist_ok=True); truth.mkdir(parents=True, exist_ok=True)
    seed_path = RELEASE / 'data/Dataset_generation/FEFF_simulations/Cu_full_df_with_spectra.joblib'
    seed = joblib.load(seed_path)
    with (inputs / 'seed_material_ids.csv').open('w') as handle:
        writer = csv.writer(handle); writer.writerow(['material_id'])
        writer.writerows([str(mid)] for mid in seed.materials_id)
    settings = {'feff_version': '9.9.1', 'cluster_radius_A': 10.0, 'symprec_A': .01,
                'feff_tags': {'CONTROL': '1 1 1 1 1 1', 'COREHOLE': 'NONE', 'S02': 0,
                              'EXCHANGE': '0 0.0 0.0 2', 'SCF': '7.0 0 100 0.2 3',
                              'FMS': '9.0 0', 'XANES': '4 0.04 0.1', 'RPATH': -1},
                'source': 'FEFF control tags from the released additional-material input decks. The 10 Å input cluster and 0.01 Å symmetry tolerance are the benchmark reproduction settings; the archived atom lists agree with a 10 Å cluster.',
                'budget': {'materials': 3, 'edges_per_inequivalent_Cu_site': ['L2', 'L3']}}
    dump(inputs / 'simulation_settings.json', settings)
    combined_path = RELEASE / 'data/Dataset_generation/110222_Cu_DF_With_Spectra.joblib'
    combined = joblib.load(combined_path)
    archive_path = RELEASE / 'data/Dataset_generation/FEFF_simulations/Stable_and_exp_Cu_with_results.zip'
    cases, spectra = [], []
    import io
    with zipfile.ZipFile(archive_path) as archive:
        for mid in IDS:
            row = combined.loc[combined.mp_id == mid].iloc[0]
            case = {'material_id': mid, 'historical_is_stable': bool(row.is_stable),
                    'historical_theoretical': bool(row.theoretical), 'jobs': []}
            for name in sorted(archive.namelist()):
                match = re.search(r'_(L[23])/' + re.escape(mid) + r'/FEFF/(\d+)_Cu/feff.inp$', name)
                if not match: continue
                edge, site = match.groups(); text = archive.read(name).decode()
                structure = Header.from_str(text).struct
                xmu_name = name[:-len('feff.inp')] + 'xmu.dat'
                raw = np.loadtxt(io.StringIO(archive.read(xmu_name).decode()))
                case['jobs'].append({'site_index': int(site), 'edge': edge,
                                     'structure': structure.as_dict(),
                                     'tags': {key: re.search(r'^' + key + r'\s+(.+)$', text, re.M).group(1).strip() for key in [*settings['feff_tags'], 'EDGE']},
                                     'input_member': name, 'xmu_member': xmu_name,
                                     'input_sha256': hashlib.sha256(archive.read(name)).hexdigest(),
                                     'xmu_sha256': hashlib.sha256(archive.read(xmu_name)).hexdigest()})
                spectra.extend([mid, int(site), edge, float(e), float(y)] for e, y in raw[:, [0, 3]])
            cases.append(case)
    dump(truth / 'reference_cases.json', {'scope': 'Historical reference cases, not mandatory simulation IDs. Compare spectra only after matching the structure, Cu absorber environment, settings and energy convention. New structures need independently generated FEFF references.', 'cases': cases})
    with (truth / 'reference_site_spectra.csv').open('w') as handle:
        writer = csv.writer(handle); writer.writerow(['material_id', 'site_index', 'edge', 'energy_eV', 'intensity']); writer.writerows(spectra)
    with (truth / 'reference_material_spectra.csv').open('w') as handle:
        writer = csv.writer(handle); writer.writerow(['material_id', 'energy_eV', 'intensity'])
        for mid in IDS:
            row = combined.loc[combined.mp_id == mid].iloc[0]
            writer.writerows([mid, float(e), float(y)] for e, y in zip(row.Energies, row.Spectrum))
    dump(truth / 'provenance.json', {
        'paper': 'https://www.nature.com/articles/s41524-024-01408-1',
        'release': 'https://zenodo.org/records/18142209',
        'sources': [{'path': str(p.relative_to(RELEASE)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in [seed_path, combined_path, archive_path]],
        'input_processing': 'Seed table projected to its material-ID column, retaining original order and Failed sentinels. No additional-material IDs, structures, metadata flags or spectra are supplied as answers.',
        'reference_processing': 'Raw site spectra copied from xmu.dat columns 1 and 4; material spectra copied from the released combined table; structure headers and control tags parsed from archived input decks. No candidate function generates these references.',
        'live_search_boundary': 'The historical roster is not a complete snapshot of the original MP search universe. A live response must be captured independently by the evaluation harness and reused for selection verification.',
        'simulation_boundary': 'FEFF9 must be provided by the runtime. No new simulation is claimed by this extraction.'})
    print(json.dumps({'seed_rows': len(seed), 'reference_cases': IDS,
                      'reference_jobs': sum(len(c['jobs']) for c in cases)}))


if __name__ == '__main__': main()
