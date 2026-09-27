#!/usr/bin/env python3
"""Register the researched tasks and evaluator-only worked evidence locally."""
import json
from pathlib import Path
from questions import BACKGROUND, QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/data/chen-2021-l-edge'
URL = 'data/chen-2021-l-edge'
ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')


def asset(name, relative, description):
    return {'name': name, 'url': URL + '/' + relative, 'description': description}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def main():
    scenarios = []
    for spec in QUESTIONS:
        q = spec['id']
        output = BASE / 'verification' / q
        assert (output / 'report.md').is_file(), f'Execute {q} before indexing it'
        workflow = {
            'question': q, 'source_derivation': spec['derivation'],
            'solver_inputs': 'Only eight native JSONL gzip streams and the minimal task. No paper, code, derived label, precomputed feature, expected answer or verifier is exported.',
            'environment': 'Python 3.12; requirements.txt pins direct dependencies; requirements-lock.txt records all installed packages.',
            'commands': [
                'python3 -m venv /tmp/chen-bench-env',
                '/tmp/chen-bench-env/bin/python -m pip install -r papers/chen-2021-l-edge/requirements.txt',
                f'python3 papers/chen-2021-l-edge/export_agent_bundle.py {q} --output /tmp/chen-{q}-agent',
                f'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/chen-mpl /tmp/chen-bench-env/bin/python docs/{URL}/workflows/candidate.py {q} --inputs /tmp/chen-{q}-agent/inputs --output /tmp/chen-{q}-answer',
                f'/tmp/chen-bench-env/bin/python docs/{URL}/workflows/verify.py --question {q} --inputs docs/{URL}/inputs --output /tmp/chen-{q}-answer',
            ],
            'tools': ['Python gzip/json/csv for original record parsing', 'NumPy and SciPy for native-grid spectral calculations',
                      'pymatgen periodic geometry and spglib symmetry',
                      'NumPy material-block regression/bootstrap' if q == 'Q2' else ('scikit-learn composition-held-out classification and NumPy paired group bootstrap' if q == 'Q3' else 'NumPy weighted interpolation and SciPy Gaussian resolution comparisons'),
                      'Matplotlib figures'],
            'choices': 'The candidate selects its symmetry tolerance, geometric labels, supports, metrics, models and uncertainty design. These are illustrative choices, not requirements imposed on solvers.',
            'outputs': sorted(p.name for p in output.iterdir() if p.is_file()),
                'verification': 'verify.py audits the explicit worked-example protocol only. Alternative submissions use verify_submission.py for source/partition integrity and require independent reconstruction of their own declared quantities plus the scientific rubric. Neither checker grants scientific acceptance.',
        }
        write(BASE / 'workflows' / f'{q}.json', workflow)
        reasoning = {
            'Q1': 'Python reads the native calculation records and checks material identities against geometry. spglib derives symmetry equivalence classes and populations. The worked candidate establishes complete absorbing-site coverage before averaging, preserving physical photon energies and relative intensities. NumPy constructs population-weighted responses by linear interpolation only within common native support, then compares equal-site and single-representative approximations under several Gaussian resolutions. Response arrays, coverage/exclusion records and numerical effects make the result auditable. The evaluator independently reconstructs source populations and responses rather than loading the candidate arrays as truth. No historical material-average output is present in the release.',
            'Q2': 'pymatgen enumerates periodic neighbors; the candidate distinguishes tetrahedral and octahedral shapes using radial and angular geometry, retaining other sites in its audit. NumPy integrates native L2 and L3 intensities in declared windows and preserves their relative scale. Weighted conditional contrasts and material-cluster resampling examine chemical confounding, including exact-composition overlap, while alternate window and shape definitions test sensitivity. Raw finite-window areas are explicitly distinguished from continuum-subtracted experimental branching ratios. The evaluator independently derives geometry and edge integrals from source records; scientific review judges adjustment, overlap, uncertainty and interpretation. Neither a sign nor the example coefficient is a required answer.',
            'Q3': 'The worked candidate derives regular-environment reference labels from structures and constructs matched spectral features from paired native edges. Scikit-learn compares L3-only and joint-edge classifiers on identical composition-held-out folds, with majority and chemistry-prior controls and altered resolution. Predictions, material partitions and class-specific support expose dependence and chemistry effects. NumPy uses paired composition-block resampling to assess incremental performance. The evaluator recovers source compositions and reference geometry, checks partition exclusion and recomputes prediction metrics without reading candidate scores as truth. The scientific assessment audits feature provenance and the conditional scope of the information claim; historical model performance is not supplied or assumed.',
        }[q]
        summary = json.loads((output / 'summary.json').read_text())
        if q == 'Q1':
            equal = next(r for r in summary['statistics'] if r['approximation'] == 'equal_sites' and r['fwhm_eV'] == 1)
            single = next(r for r in summary['statistics'] if r['approximation'] == 'first_representative' and r['fwhm_eV'] == 1)
            finding = (f"The executed example reconstructs {summary['complete_responses']} complete edge responses and excludes {summary['excluded_responses']} observed groups. Another 142 whole edge groups have no released records and are not reconstructed. "
                       f"At 1 eV FWHM, the 95th-percentile shape errors among multisite responses are {equal['q95']:.4f} for equal populations and {single['q95']:.4f} for one representative. "
                       'These are descriptive results under the declared populations/support and error definitions, not acceptance thresholds.')
        elif q == 'Q2':
            exact = next(r for r in summary['associations'] if r['adjustment'] == 'exact_composition' and r['feature'] == 'log_ratio' and r['geometry_definition'] == 'geometry')
            finding = (f"The exact-composition comparison uses {exact['n_sites']} sites from {exact['n_materials']} materials. Its tetrahedral-minus-octahedral log-area contrast is "
                       f"{exact['tetra_minus_octa_log_ratio']:.5f}, with material-bootstrap interval [{exact['ci025']:.5f}, {exact['ci975']:.5f}]. "
                       'The example therefore does not establish a composition-invariant geometry effect, despite a clearer association under partial chemistry adjustment. Limited overlap is part of the answer.')
        else:
            delta = next(r for r in summary['paired_differences'] if r['fwhm_eV'] == 0)
            finding = (f"The example evaluates {summary['n_sites']} regular-environment sites across {summary['n_compositions']} held-out composition groups. "
                       f"Adding L2 changes balanced accuracy by {delta['L23_minus_L3_balanced_accuracy']:.5f}, with paired composition-bootstrap interval [{delta['ci025']:.5f}, {delta['ci975']:.5f}]. "
                       'The incremental benefit is unresolved in this experiment; high overall label accuracy does not establish added information from the second edge.')
        reasoning += '\n\n' + finding
        data = [asset('Source provenance', 'provenance.json', 'Versioned archive, MIT license, lossless selection and native/package hashes.'),
                asset('Source map', 'verification/source_map.json', 'Available and missing evidence; historical code inspection and truth boundaries.'),
                asset('Release census', 'verification/release_census.json', 'Source-derived census and numerical/identity caveats; evaluator only.'),
                asset('Scientific review rubric', 'verification/scientific_review_rubric.md', 'Scientific validity criteria, separate from automatic numerical integrity.')]
        for p in sorted(output.iterdir()):
            if p.is_file() and p.suffix in {'.json', '.csv', '.npz', '.md'}:
                data.append(asset(q + ' ' + p.name, f'verification/{q}/{p.name}', 'Executed worked evidence; source data and independent checks establish truth, not exact imitation of this analysis.'))
        for name in ['question_quality_review.json', 'workflow_execution_review.json', 'verification_audit.json', 'scientific_review.json', 'source_packaging_audit.json', 'open_submission_audit.json', 'open_submission_independent_review.json', 'open_submission_independent_controls.json']:
            assert (BASE / 'verification' / name).exists(), f'Missing independent evidence: {name}'
            data.append(asset(name, 'verification/' + name, 'Recorded independent review or applied audit.'))
        figures = [{'image': f'{URL}/verification/{q}/{p.name}', 'label': q + ' · ' + p.stem,
                    'caption': 'Generated diagnostic from the executed candidate; not a reproduction of a historical paper figure.'}
                   for p in sorted(output.glob('*.png'))]
        scenarios.append({
            'id': 'CHEN21-' + q, 'kind': 'Subquestion', 'executionStatus': 'executed_example', 'title': spec['title'],
            'inputs': [asset(f'{e}.jsonl.gz', f'inputs/{e}.jsonl.gz', f'Native {e} absorbing-site calculation records, including separate-edge spectra, structures and FEFF input parameters.') for e in ELEMENTS],
            'prompt': {'background': BACKGROUND, 'instruction': spec['instruction']},
            'groundTruthReasoning': reasoning,
            'verification': {
                'description': 'For open submissions, verify_submission.py checks native-source identities and declared composition exclusion without imposing the candidate protocol. Its numerical validation is partial and cannot grant scientific acceptance: independently reconstruct submitted geometric/spectral quantities, inspect and execute code, and apply the rubric. verify.py separately audits the complete worked-example protocol and is not a universal grading contract. Alternative defensible methods and negative results are permitted; example conclusions are not fixed targets.',
                'data': data, 'figures': figures,
                'methods': [asset('Worked tool calls', f'workflows/{q}.json', 'Environment, executable commands, analysis choices and outputs.'),
                            asset('candidate.py', 'workflows/candidate.py', 'Executed illustrative solution; evaluator-only.'),
                            asset('verify.py', 'workflows/verify.py', 'Independent numerical audit of the declared worked-example profile; not a universal submission contract.'),
                            asset('verify_submission.py', 'workflows/verify_submission.py', 'Open-submission source/partition checks with explicit unresolved scientific/numerical review obligations.')],
                'thresholds': {'origin': 'benchmark-defined', 'generatedBy': 'Benchmark authors with independent agent verification audit',
                               'provenance': 'Numerical tolerances are implementation checks, not paper-reported effect sizes or predictive targets. Scientific acceptance is assessed separately.',
                               'notes': [{'title': 'Numerical integrity', 'description': 'Check finite quantities, native identities, geometric populations, declared source-derived observations and metrics. Unsupported alternative definitions require independent scientific/numerical review; they do not earn full verification from format checks.'},
                                         {'title': 'Scientific acceptance', 'description': 'Require a justified nontrivial investigation, valid dependence/chemistry controls, sensitivity and conclusions supported by executable evidence. No particular coefficient, direction or classification score is required.'}]},
            },
        })
    paper = {'id': 'chen-2021-l-edge', 'title': 'Database of ab initio L-edge X-ray absorption near edge structure',
             'authors': 'Yiming Chen, Chi Chen, Chen Zheng et al. (2021)', 'doi': '10.1038/s41597-021-00936-5',
             'category': 'Transition-metal L-edge XANES', 'facility': 'FEFF9 / Materials Project',
             'pdf': 'https://www.nature.com/articles/s41597-021-00936-5.pdf',
             'dataUrl': 'https://doi.org/10.6084/m9.figshare.12824513.v1',
             'codeUrl': 'https://github.com/materialsproject/pymatgen/blob/v2020.12.31/pymatgen/analysis/xas/spectrum.py',
             'scenarios': scenarios}
    write(HERE / 'paper.json', paper)
    target = ROOT / 'docs/data/benchmark.json'
    dataset = json.loads(target.read_text())
    dataset['papers'] = [p for p in dataset['papers'] if p['id'] != paper['id']] + [paper]
    dataset['datasetId'] = 'spectral-agent-v2026-09-26-chen-research-v1'
    write(target, dataset)
    print('Added Chen 2021: 3 research questions; other entries preserved.')


if __name__ == '__main__':
    main()
