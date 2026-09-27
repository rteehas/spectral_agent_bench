#!/usr/bin/env python3
"""Publish paper-result tasks only after all independent acceptance gates pass."""
import json
from pathlib import Path
from questions import BACKGROUND, QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/data/chen-2021-l-edge'
RESULTS = BASE / 'paper_results'
URL = 'data/chen-2021-l-edge'
ELEMENTS = ('Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu')


def asset(name, relative, description):
    assert (BASE / relative).is_file(), relative
    return {'name': name, 'url': URL + '/' + relative, 'description': description}


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def main():
    scenarios = []
    for spec in QUESTIONS:
        q = spec['id']
        reference = RESULTS / 'verification' / q
        acceptance = json.loads((RESULTS / 'verification' / f'{q}_acceptance.json').read_text())
        accepted = acceptance['accepted']
        number = 4 if q == 'R1' else 5
        contract = f'paper_results/verification/figures/figure{number}_comparison_contract.json'
        common = [
            asset('Native input provenance', 'provenance.json', 'Exact versioned archive and lossless native input hashes.'),
            asset('Publication target provenance', 'paper_results/verification/figures/provenance.json', 'Published PDF, extraction method, CC BY attribution and limitations.'),
            asset('Source and scope audit', 'paper_results/verification/source_scope.json', 'Full-release audit of missing Table 2 IDs and Figure 2 count discrepancies; excluded tasks are not counted as reproductions.'),
            asset('Mandatory paper comparison policy', contract, 'Frozen independently of candidate discrepancies; failure cannot be replaced by a source-integrity pass.'),
            asset('Combined acceptance', f'paper_results/verification/{q}_acceptance.json', 'Paper agreement, independent raw-data replay, and scientific review are all required and bound to the output hashes.'),
        ]
        if q == 'R1':
            common += [asset('Original Figure 4 vector coordinates', 'paper_results/verification/figures/figure4_traces.csv', 'Literal published curves, affine-calibrated from axis ticks; evaluator-only numerical ground truth.'),
                       asset('Figure 4 axis calibration', 'paper_results/verification/figures/figure4_calibration.json', 'Tick coordinates, clipping bounds and source stroke widths.'),
                       asset('Excluded Figure 4 panels', 'paper_results/verification/figure4_feasibility.json', 'Absent source IDs and failed exploratory reconstructions are disclosed; no relaxed tolerance.')]
            description = ('Every retained material must reproduce its published Figure 4 FEFF curve. '
                           'The evaluator extracts the original PDF vector paths and compares the complete visible line shape, '
                           'L2 peak position and L2 intensity after a single L3-peak energy registration and global maximum normalization. '
                           'Both Mn and Fe panels must pass. Native-source replay and scientific review are additionally mandatory. '
                           'Only panels (c,d) are validated: the published Fe ID is absent, and the released olivine phase has a different ID. '
                           'The four other panels are not represented as reproduced.')
            reasoning = ('Python identifies spinel MgMn2O4 and olivine LiFePO4 from native composition and crystallography, '
                         'checks absorber-site coverage, constructs the combined edge response, and applies the stated energy resolution. '
                         'The worked example uses crystallographic populations, cubic interpolation and the contemporaneous pymatgen L23 convention, '
                         'then measures the peak structure. Its curves are predictions from raw records, not the answer key. '
                         'The independent answer key is the green vector trace in Figure 4(c,d). The evaluator fixes the single permitted energy '
                         'translation using the L3 maximum and checks the entire visible trace plus the L2 feature. '
                         'The worked comparison gives normalized RMSE 0.00581 for Mn and 0.01180 for Fe, below the fixed 0.02 bound. '
                         'No intensity-baseline fitting, separate edge scaling, bandwidth fitting or energy warping is permitted. '
                         'MgMn2O4 uses the exact Table 2 ID mp-32006. LiFePO4 uses released olivine mp-761468, because mp-19017 is absent; '
                         'this reproduces the plotted phase response rather than establishing exact historical calculation identity.')
            threshold_notes = [
                {'title': 'Mandatory numerical paper agreement', 'description': 'For BOTH published curves: normalized RMSE ≤ 0.02, maximum pointwise residual ≤ 0.07, secondary-peak intensity error ≤ 0.05, and position error ≤ max(0.1 eV, the published stroke width). At least 98% of the visible curve must be covered, with no endpoint gap larger than one stroke.'},
                {'title': 'Additional acceptance gates', 'description': 'Independently rerun the submitted analysis from native inputs, inspect its source and scientific conclusions, and bind the review to the resulting artifacts. Numerical agreement alone cannot certify provenance.'},
            ]
        else:
            description = ('All eight published Figure 5 panels are mandatory targets. '
                           'Compare the complete red/blue spectral ensembles on calibrated energy and intensity axes using the fixed raster contract, '
                           'and independently inspect the published and reconstructed plots for the coordination-dependent line shapes and evolution across the series. '
                           'Raw-data replay and scientific interpretation must also pass. Color opacity is not treated as a recoverable class count, density or quantile. '
                           'A failed paper comparison cannot be replaced by correct formatting, source integrity, plausible trends or agreement with a newly generated reference.')
            reasoning = ('Python derives local environments from periodic structures, joins the separately released edges by physical site identity, '
                         'and reconstructs normalized site-level L2,3 responses for each absorbing element. '
                         'The worked candidate uses CrystalNN neighborhoods and local structural order parameters, retaining excluded records and other motifs in an audit. '
                         'Matplotlib renders the full coordination-colored ensembles. The scientific targets are the eight published Figure 5 panels, '
                         'including their peak locations, line-shape spread, color-dependent L2 response and changing white-line contrast. '
                         'The evaluator uses the retained publisher raster and frozen coordinate/color criteria, followed by mandatory full-panel scientific review. '
                         'The release has no author geometry labels or figure-generating arrays; candidate label counts and descriptive summaries therefore '
                         'remain reproducibility evidence, not replacements for the paper target. Max-normalized plots support relative contrast, not an absolute oscillator-strength trend.')
            threshold_notes = [
                {'title': 'Mandatory plot comparison', 'description': 'Apply the frozen Figure 5 raster policy to every element and both coordination colors; retain all panel-level results and apply the required independent visual rubric. No averaging away a failed panel.'},
                {'title': 'Additional acceptance gates', 'description': 'Independently replay the workflow, audit source identity and structural labels, and review the physical interpretation. No causal coordination claim or absolute-intensity inference from max-normalized overplots.'},
            ]
        for name in ['question_quality.json', 'workflow_execution.json', 'scientific_review.json', 'verification_audit.json']:
            common.append(asset(name, 'paper_results/verification/reviews/' + name, 'Independent review for this revision; previous extension-task reviews are retired.'))
        common.append(asset('Combined acceptance rejection controls', 'paper_results/verification/reviews/combined_acceptance_controls.json', 'Applied positive and negative checks, including changed raw inputs, stale approvals and changed publication targets.'))
        common.append(asset('Paper comparison result', f'paper_results/verification/{q}_paper_comparison.json', 'Every mandatory publication comparison, including any unresolved failures.'))
        if q == 'R2':
            common.extend([
                asset('Original raster comparison failure', 'paper_results/verification/R2_paper_comparison_v1.json', 'Preserved first result; it was not silently replaced by a pass.'),
                asset('Independent source-only renderer calibration', 'paper_results/verification/reviews/source_renderer_independent_audit.json', 'Checks the source-measured stroke-width correction; scientific thresholds remain unchanged.'),
            ])
        for p in sorted(reference.iterdir()):
            if p.is_file() and p.suffix in {'.json', '.csv', '.npz', '.md'}:
                common.append(asset(q + ' · ' + p.name, f'paper_results/verification/{q}/{p.name}', 'Executed candidate evidence. The published figure, not this candidate output, supplies the scientific target.'))
        figures = [{'image': URL + f'/paper_results/verification/figures/figure{number}.png',
                    'label': f'Published Figure {number}',
                    'caption': 'Chen et al. (2021), Scientific Data, CC BY 4.0. Retained publication target; evaluator-only.'}]
        figures += [{'image': URL + '/paper_results/verification/' + q + '/' + p.name,
                     'label': q + ' reconstructed · ' + p.stem,
                     'caption': 'Worked reconstruction generated from native records. Compare with the published figure above.'}
                    for p in sorted(reference.glob('*.png'))]
        overlay = RESULTS / 'verification' / f'{q}_paper_overlay.png'
        if overlay.exists():
            figures.append({'image': URL + '/paper_results/verification/' + overlay.name,
                            'label': q + ' · direct publication overlay',
                            'caption': 'Actual paper trace and raw-data reconstruction overlaid using only the permitted registration. No curve fitting or error-dependent cropping.'})
        if not accepted:
            description = ('UNVALIDATED — withheld from scoring. The worked example has not passed every required publication comparison. '
                           'The full failing report is retained and no weaker acceptance path is provided. ' + description)
        scenarios.append({
            'id': 'CHEN21-' + q, 'kind': 'Subquestion',
            'executionStatus': 'paper_verified_example' if accepted else 'unvalidated_paper_comparison',
            'scoringEligible': accepted,
            'title': spec['title'] if accepted else '[UNVALIDATED] ' + spec['title'],
            'inputs': [asset(e + '.jsonl.gz', 'inputs/' + e + '.jsonl.gz', 'Native ' + e + ' absorbing-site spectra, periodic structures and FEFF inputs.') for e in ELEMENTS],
            'prompt': {'background': BACKGROUND, 'instruction': spec['instruction']},
            'groundTruthReasoning': reasoning,
            'verification': {'description': description, 'data': common, 'figures': figures,
                'methods': [
                    asset('Worked workflow and tool calls', 'paper_results/workflows/' + q + '.json', 'Complete executable workflow, inputs, tools and mandatory acceptance gates; evaluator-only.'),
                    asset('candidate_' + q.lower() + '.py', 'paper_results/workflows/candidate_' + q.lower() + '.py', 'Worked raw-data solution; never exported to solvers.'),
                    asset('verify_' + q.lower() + '.py', 'paper_results/workflows/verify_' + q.lower() + '.py', 'Mandatory comparison against the published figure.'),
                    asset('check_acceptance.py', 'paper_results/workflows/check_acceptance.py', 'Requires publication agreement and independent reviews tied to these output files; no weaker fallback.'),
                ],
                'thresholds': {'origin': 'publication figure; benchmark comparison tolerances',
                    'generatedBy': 'Independent publication-target extraction and verification agents',
                    'provenance': 'The answer key comes from the published figure. Numerical tolerances follow source stroke/raster precision and were frozen independently of candidate residuals. Scientific and raw-data replay review remain mandatory.',
                    'notes': threshold_notes, 'data': [asset('Frozen figure comparison policy', contract, 'Exact acceptance criteria and rationale.')]},
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
    dataset['datasetId'] = 'spectral-agent-v2026-09-27-chen-paper-results-v2'
    dataset['retiredScenarioIds'] = sorted(set(dataset.get('retiredScenarioIds', [])) | {'CHEN21-Q1', 'CHEN21-Q2', 'CHEN21-Q3'})
    write(target, dataset)
    print(f"Added Chen 2021: {sum(s['scoringEligible'] for s in scenarios)} paper-verified questions, "
          f"{sum(not s['scoringEligible'] for s in scenarios)} unvalidated candidates; other entries preserved.")


if __name__ == '__main__':
    main()
