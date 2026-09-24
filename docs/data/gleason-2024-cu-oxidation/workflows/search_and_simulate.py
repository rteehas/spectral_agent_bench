"""Worked Q8 candidate: live MP search, three structures, fresh FEFF9 runs.

Stages: search, prepare, run, collect. Run each with --inputs and --output.
Credentials come only from MP_API_KEY; FEFF_COMMAND names a local FEFF9 driver.
This script never reads benchmark reference spectra or archived FEFF decks.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_ids(inputs):
    with (inputs / 'seed_material_ids.csv').open() as handle:
        return {r['material_id'] for r in csv.DictReader(handle)
                if re.fullmatch(r'mp-\d+', r['material_id'])}


def eligible(records, seeds):
    result = {}
    for r in records:
        mid = r['material_id']
        if not re.fullmatch(r'mp-\d+', mid):
            raise ValueError('Unexpected material ID')
        if mid in result:
            if result[mid] != r:
                raise ValueError('Conflicting records for the same material ID')
            continue
        if (mid not in seeds and 'Cu' in r['elements']
                and r.get('deprecated') is not True
                and (r.get('is_stable') is True or r.get('theoretical') is False)):
            result[mid] = r
    return result


def search(inputs, output):
    key = os.environ.get('MP_API_KEY')
    if not key:
        raise RuntimeError('Configure MP_API_KEY in the benchmark runtime')
    from mp_api.client import MPRester
    import importlib.metadata
    query = {'elements': ['Cu'], 'deprecated': False, 'all_fields': False,
             'fields': ['material_id', 'formula_pretty', 'elements', 'structure',
                        'is_stable', 'theoretical', 'deprecated']}
    with MPRester(key) as mpr:
        before = mpr.get_database_version()
        docs = mpr.materials.summary.search(**query)
        after = mpr.get_database_version()
    if before != after:
        raise RuntimeError('Database version changed during search; repeat it')
    records = [{'material_id': str(d.material_id), 'formula': d.formula_pretty,
                'elements': [str(e) for e in d.elements],
                'is_stable': d.is_stable, 'theoretical': d.theoretical,
                'deprecated': d.deprecated,
                'structure': d.structure.as_dict() if d.structure else None}
               for d in docs]
    snapshot = {'source': 'live Materials Project materials.summary.search',
                'retrieved_at_utc': datetime.now(timezone.utc).isoformat(),
                'database_version': before, 'query': query,
                'mp_api_version': importlib.metadata.version('mp-api'),
                'records': records}
    dump(output / 'query_snapshot.json', snapshot)
    selected = eligible(records, seed_ids(inputs))
    fields = ['material_id', 'formula', 'is_stable', 'theoretical', 'reason']
    with (output / 'additional_materials.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for mid, r in sorted(selected.items()):
            reasons = []
            if r['is_stable'] is True:
                reasons.append('predicted stable')
            if r['theoretical'] is False:
                reasons.append('experimentally synthesized (MP theoretical=False)')
            writer.writerow({**{k: r[k] for k in fields[:-1]},
                             'reason': '; '.join(reasons)})
    print(json.dumps({'returned': len(records), 'additional': len(selected)}))


def cu_groups(record, tolerance):
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    structure = Structure.from_dict(record['structure'])
    if not structure.is_ordered:
        raise ValueError('Disordered structures need an explicit treatment')
    groups = SpacegroupAnalyzer(structure, symprec=tolerance).get_symmetrized_structure().equivalent_indices
    return structure, [g for g in groups if structure[g[0]].specie.symbol == 'Cu']


def choose_three(records, tolerance):
    # A worked selection strategy; the task allows other justified selections.
    candidates = sorted((r for r in records.values() if r.get('structure')),
                        key=lambda r: (len(r['structure']['sites']), int(r['material_id'][3:])))
    chosen, cache, excluded = [], {}, []
    for want_multiple in (False, True):
        for r in candidates:
            mid = r['material_id']
            if mid not in cache:
                try:
                    _, groups = cu_groups(r, tolerance)
                    cache[mid] = len(groups)
                except (ValueError, TypeError) as exc:
                    cache[mid] = 0
                    excluded.append({'material_id': mid, 'reason': str(exc)})
            if cache[mid] and (cache[mid] > 1) == want_multiple:
                chosen.append(mid)
                break
    # Prefer a third material that adds a different synthesis/stability category.
    categories = {(records[mid]['is_stable'], records[mid]['theoretical']) for mid in chosen}
    candidates.sort(key=lambda r: ((r['is_stable'], r['theoretical']) in categories,
                                  len(r['structure']['sites']), int(r['material_id'][3:])))
    for r in candidates:
        mid = r['material_id']
        if mid in chosen:
            continue
        try:
            _, groups = cu_groups(r, tolerance)
        except (ValueError, TypeError):
            continue
        if groups:
            chosen.append(mid)
        if len(chosen) == 3:
            break
    if len(chosen) != 3:
        raise ValueError('Fewer than three runnable eligible materials found')
    return chosen, excluded


def prepare(inputs, output, material_ids=None):
    from pymatgen.io.feff.sets import FEFFDictSet
    settings = json.loads((inputs / 'simulation_settings.json').read_text())
    snapshot = json.loads((output / 'query_snapshot.json').read_text())
    records = eligible(snapshot['records'], seed_ids(inputs))
    excluded = []
    if material_ids is None:
        material_ids, excluded = choose_three(records, settings['symprec_A'])
    if len(material_ids) != 3 or len(set(material_ids)) != 3:
        raise ValueError('Select exactly three distinct materials')
    if any(mid not in records for mid in material_ids):
        raise ValueError('Simulation choices must belong to the additional-material set')
    jobs, materials = [], []
    for mid in material_ids:
        structure, groups = cu_groups(records[mid], settings['symprec_A'])
        total = sum(map(len, groups))
        materials.append({'material_id': mid, 'formula': records[mid]['formula'],
                          'structure': structure.as_dict(),
                          'groups': groups, 'cu_atoms': total})
        for group in groups:
            site = group[0]
            for edge in ('L2', 'L3'):
                relative = Path('jobs') / mid / f'{site:03d}_Cu' / edge
                directory = output / relative
                if directory.exists():
                    raise FileExistsError(f'Use fresh job directories: {relative}')
                job = FEFFDictSet(site, structure, radius=settings['cluster_radius_A'],
                                  config_dict=settings['feff_tags'], edge=edge,
                                  spectrum='XANES',
                                  spacegroup_analyzer_settings={'symprec': settings['symprec_A']})
                job.write_input(str(directory))
                jobs.append({'material_id': mid, 'site_index': site, 'edge': edge,
                             'multiplicity': len(group), 'weight': len(group) / total,
                             'directory': relative.as_posix(),
                             'input_sha256': digest(directory / 'feff.inp')})
    dump(output / 'selected_materials.json', {
        'selection': 'Three eligible structures; prefer compact single-site and multi-site Cu cases and varied synthesis/stability categories.',
        'materials': materials, 'setup_exclusions': excluded})
    dump(output / 'jobs.json', {'snapshot_sha256': digest(output / 'query_snapshot.json'),
                                'settings_sha256': digest(inputs / 'simulation_settings.json'),
                                'jobs': jobs})
    print(json.dumps({'materials': material_ids, 'edge_site_jobs': len(jobs)}))


def run(output, command):
    import numpy as np
    if not command:
        raise RuntimeError('Set FEFF_COMMAND to a FEFF9 driver, or pass --feff-command')
    jobs = json.loads((output / 'jobs.json').read_text())['jobs']
    results = []
    for job in jobs:
        directory = output / job['directory']
        if digest(directory / 'feff.inp') != job['input_sha256']:
            raise ValueError('Input deck changed after preparation')
        if (directory / 'xmu.dat').exists() or (directory / 'run.log').exists():
            raise FileExistsError('Fresh FEFF jobs required; do not substitute archived outputs')
        started = datetime.now(timezone.utc).isoformat()
        start = time.monotonic()
        with (directory / 'run.log').open('w') as log:
            completed = subprocess.run(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT)
        valid = False
        if (directory / 'xmu.dat').exists():
            try:
                values = np.loadtxt(directory / 'xmu.dat')
                valid = (values.ndim == 2 and values.shape[0] >= 3 and values.shape[1] >= 4
                         and np.isfinite(values[:, [0, 3]]).all() and (np.diff(values[:, 0]) > 0).all())
            except ValueError:
                pass
        log_text = (directory / 'run.log').read_text(errors='replace')
        converged = 'Convergence reached' in log_text
        version_match = re.search(r'FEFF\s+(9\.[0-9.]+)', log_text)
        version = version_match.group(1) if version_match else None
        record = {'directory': job['directory'], 'command': command, 'started_at_utc': started,
                  'elapsed_seconds': time.monotonic() - start, 'returncode': completed.returncode,
                  'feff_version': version, 'convergence_reported': converged, 'valid_xmu': bool(valid),
                  'input_sha256': job['input_sha256'], 'log_sha256': digest(directory / 'run.log'),
                  'xmu_sha256': digest(directory / 'xmu.dat') if valid else None,
                  'passed': bool(completed.returncode == 0 and valid and converged and version)}
        results.append(record)
        dump(output / 'execution.json', {'jobs': results, 'all_jobs_passed':
             len(results) == len(jobs) and all(r['passed'] for r in results)})
    if not all(r['passed'] for r in results):
        raise RuntimeError('Some FEFF jobs failed; inspect execution.json and logs before proceeding')


def combine_edges(l2, l3):
    import numpy as np
    grids = [np.arange(round(a[:, 0].min() + .15, 1), round(a[:, 0].max() - .15, 1), .1)
             for a in (l2, l3)]
    e2, e3 = grids
    y2, y3 = [np.interp(grid, a[:, 0], a[:, 3]) for grid, a in zip(grids, (l2, l3))]
    if y2[0] <= 0 or e2[0] <= e3[0]:
        raise ValueError('Edge ranges/intensities require a different justified padding treatment')
    ratio = (1e-10 / y2[0]) ** .1
    a = (e3[0] - e2[0] * ratio) / (ratio - 1)
    b = 1e-10 / (e3[0] + a) ** 10
    prefix = np.linspace(e3[0], e2[0] - .1, int(round(e2[0] - .1 - e3[0], 1) * 10) + 1)
    extended = np.r_[b * (prefix + a) ** 10, y2]
    if len(extended) < len(y3):
        raise ValueError('L2 does not cover the required L3 range')
    return np.round(e3, 1), y3 + extended[:len(y3)]


def assemble(output):
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    jobs = json.loads((output / 'jobs.json').read_text())['jobs']
    records = []
    for mid in sorted({j['material_id'] for j in jobs}):
        curves = []
        for site in sorted({j['site_index'] for j in jobs if j['material_id'] == mid}):
            pair = {j['edge']: j for j in jobs if j['material_id'] == mid and j['site_index'] == site}
            energy, intensity = combine_edges(*[np.loadtxt(output / pair[e]['directory'] / 'xmu.dat') for e in ('L2', 'L3')])
            curves.append((energy, intensity, pair['L2']['weight'], site))
        grid = (curves[0][0] if len(curves) == 1 else
                np.round(np.arange(max(c[0][0] for c in curves), min(c[0][-1] for c in curves), .1), 1))
        total = np.zeros(len(grid))
        plt.figure()
        for energy, intensity, weight, site in curves:
            contribution = weight * np.interp(grid, energy, intensity)
            total += contribution
            plt.plot(grid, contribution, '--', label=f'Cu site {site} × {weight:g}')
        plt.plot(grid, total, color='black', label='Material average')
        plt.xlabel('Photon energy (eV)'); plt.ylabel('FEFF absorption'); plt.title(mid); plt.legend(); plt.tight_layout()
        folder = output / 'spectra' / mid; folder.mkdir(parents=True, exist_ok=True)
        plt.savefig(folder / 'plot.png', dpi=140); plt.close()
        pd.DataFrame({'energy_eV': grid, 'intensity': total}).to_csv(folder / 'spectrum.csv', index=False)
        records.append({'material_id': mid, 'site_weights': {str(c[3]): c[2] for c in curves}, 'points': len(grid)})
    dump(output / 'result.json', {'materials': records, 'stage': 'unaligned material-averaged Cu L2,3 spectra'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['search', 'prepare', 'run', 'collect'])
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--materials', nargs=3)
    parser.add_argument('--feff-command', nargs='+')
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    if args.stage == 'search': search(args.inputs, args.output)
    elif args.stage == 'prepare': prepare(args.inputs, args.output, args.materials)
    elif args.stage == 'run': run(args.output, args.feff_command or shlex.split(os.environ.get('FEFF_COMMAND', '')))
    else:
        execution = json.loads((args.output / 'execution.json').read_text())
        jobs = json.loads((args.output / 'jobs.json').read_text())['jobs']
        if not execution['all_jobs_passed'] or len(execution['jobs']) != len(jobs):
            raise ValueError('All site/edge runs must pass before collecting the complete material spectra')
        for result in execution['jobs']:
            folder = args.output / result['directory']
            if digest(folder / 'xmu.dat') != result['xmu_sha256'] or digest(folder / 'feff.inp') != result['input_sha256']:
                raise ValueError('FEFF inputs or spectra changed after execution')
        assemble(args.output)


if __name__ == '__main__':
    main()
