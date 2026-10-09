"""The fixed, publication-verified Q1 definition; Q2-Q5 remain open investigations."""
import hashlib
import json
import shutil


def build_scenario(root, data, base):
    reference = data / 'verification/Q1_paper'
    validation = json.loads((reference / 'reference_validation.json').read_text())
    execution = json.loads((reference / 'execution_check.json').read_text())
    assert validation['published_statistics_checked'] == 64
    assert execution['publication_reproduction_pass'] and execution['independent_predictions_match']

    def link(name, path, description):
        return {'name': name, 'url': f'{base}/{path}', 'description': description}

    shutil.copyfile(root / 'papers/torrisi-2020-xanes-rf/reproduce_q1_reference.py',
                    reference / 'reference_program.py')
    reasoning = (
        '1. Recover the published cohort and exact row order (Python / NumPy / source notebooks).\n'
        'Apply the released spectral-quality filters and keep coordination labels 4, 5 and 6 from both data sources. Reconstruct the seed-42 split and compare every membership and label with the independent archived-array audit. The released split is approximately 81/9/10, despite the paper describing 80/10/10. Exact released memberships take precedence. preparation_audit.json records all counts and hashes.\n\n'
        '2. Prepare the solver bundle (Python / NumPy).\n'
        'Preserve the post-edge-normalized 100-point spectral arrays. Supply training and validation labels, but omit test labels and all structural metadata/other targets. Test truth remains evaluator-only.\n\n'
        '3. Balance training classes (NumPy random sampling).\n'
        'Use the released RandomOverSampler-equivalent seed-42 bootstrap: retain original training rows, then append minority-class samples in ascending class order until each matches the training majority count. Validation and test rows are not sampled or fitted.\n\n'
        '4. Fit the published pointwise random forests (scikit-learn).\n'
        'Use 300 trees, maximum depth 35, eight candidate features per split, and the other protocol settings. Fit seeds 42 through 51 separately for all eight elements: 80 forests. The solver reads only its prepared input bundle and emits 38,610 test predictions plus validation predictions. It has no test labels.\n\n'
        '5. Reconstruct the published results (independent evaluator).\n'
        'Join test predictions to the original released labels by element/source_row. Recompute accuracy and F1 for classes 4, 5 and 6 for each seed, then their ten-fit means and population standard deviations. All 64 values reproduce the author-released pointwise_table_feff.csv within its printed rounding precision. The independently coded reference starts from the full raw projections and archived split rather than the solver bundle; its test predictions also match the separate worked solver run.\n\n'
        '6. Interpret the reproduced class-specific performance.\n'
        'Overall accuracy is high, but difficult classes remain: pointwise F1 is about 0.6143 for Mn CN4, 0.6311 for Cu CN4, 0.6809 for Cr CN5 and 0.6870 for Co CN5. These are the published final-model results. This task does not claim a quantified oversampling benefit: that separate validation ablation lacks a complete published paired reference table.\n\n'
        '7. Apply the fixed acceptance rule.\n'
        'Require complete prescribed prediction coverage, matching protocol/input declarations and training counts, and agreement with every published mean/std within 0.00005 in fractional score units plus 1e-12 numerical epsilon. This is half the table rounding unit, not a statistical confidence interval. Numerical failure cannot be waived by a narrative claim. The harness executes source with only the solver bundle; the checker does not execute untrusted source or establish isolation itself.'
    )
    workflow = {
        'question': 'Q1', 'status': 'executed_publication_reproduction',
        'source_derivation': 'Published Fig. 3 coordination results and the author-released pointwise_table_feff.csv; pinned TRIXS preprocessing/training notebooks.',
        'solver_program': 'reproduce_coordination.py', 'evaluator_program': 'verify_coordination.py',
        'solver_command': 'python reproduce_coordination.py --inputs INPUT_DIRECTORY --output NEW_OUTPUT_DIRECTORY --jobs 4',
        'verification_command': 'python verify_coordination.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY',
        'input_boundary': 'Only eight prepared NPZ files and protocol.json. Test labels, original full labeled records, paper, repository and evaluator outputs are inaccessible to the solver.',
        'execution_evidence': 'verification/Q1_paper/execution_check.json',
        'independent_reference_evidence': 'verification/Q1_paper/reference_validation.json',
        'reasoning': reasoning,
        'oversampling_effect': 'Excluded from scoring. Reproduce final oversampled-model performance; do not impose an unverified before/after effect.',
        'historical_example': 'verification/Q1 and its label-refresh receipt preserve the former class-weighted ExtraTrees investigation. It is superseded and is not a reference for this release.'}
    (data / 'workflows/Q1.json').write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + '\n')
    figures = []
    for name, caption in [('published_comparison.png', 'Published and independently reproduced accuracy and per-class F1. Error bars are population SD over ten forest seeds on the fixed spectral-record split.'),
                          ('rounding_residuals.png', 'Differences from published means and standard deviations. The acceptance band is the table rounding margin: ±0.005 percentage points.')]:
        path = reference / name
        figures.append({'image': f'{base}/verification/Q1_paper/{name}?v={hashlib.sha256(path.read_bytes()).hexdigest()[:12]}',
                        'label': name, 'caption': caption + ' Generated from the verified reproduction; not a paper image.'})
    return {
        'id': 'TORRISI20-Q1', 'kind': 'Subquestion', 'executionStatus': 'executed_publication_reproduction',
        'title': 'How accurately do pointwise K-edge spectra identify coordination numbers 4, 5 and 6?',
        'inputs': [link(e + '.npz', f'inputs/Q1_paper/{e}.npz',
                        f'{e} spectra on the released 100-point energy grid with fixed train/validation/test arrays and source-row IDs. Only training and validation labels are supplied.')
                   for e in ['Ti', 'V', 'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu']] +
                  [link('protocol.json', 'inputs/Q1_paper/protocol.json',
                        'Fixed random-forest parameters, training-only oversampling, ten seeds, runtime versions, NPZ conventions and output schema. Contains no expected scores or test labels.')],
        'prompt': {
            'background': 'The supplied NPZ files contain computed K-edge spectra for oxygen-containing compounds. energy_eV is the shared photon-energy axis; each row of a *_spectra array contains 100 post-edge-normalized absorption values. *_source_rows identify original records within each element. train_labels and validation_labels are coordination numbers 4, 5 or 6. Test labels are withheld. The fixed partitions and protocol define a reproducible spectral-record prediction experiment.',
            'instruction': 'Reproduce pointwise coordination classification for all eight elements using protocol.json. Implement its random forests, training-only oversampling and prescribed seeds. Preserve the supplied arrays and partitions. Return test predictions.csv and validation_predictions.csv with element,seed,source_row,prediction, covering every provided record for every prescribed seed; run.json as specified by the protocol; runnable Python source under code/ with its reproduction command; and report.md describing the procedure, validation performance by class, and the limits of this evaluation. The evaluator will calculate final test accuracy and per-class F1 directly from your predictions and withheld labels. Do not claim test performance from validation results.'},
        'groundTruthReasoning': reasoning,
        'verification': {
            'description': 'Execute the submitted source with only the nine declared input files. Verify exact element/seed/test-row coverage, valid coordination predictions, input/protocol hashes and training oversampling counts. Join predictions to the released test labels; independently recompute accuracy and class-specific F1 for each seed. For each element and metric, compare the mean and population standard deviation over seeds 42–51 with the author-released pointwise table: all 64 comparisons must be within the published rounding margin. The checker returns pass or fail; an opposite narrative or a low-performing negative result cannot override a failed comparison. Validation predictions are checked and scored separately. This task scores final oversampled-model reproduction, not an unverified oversampling-effect ablation. The historical ExtraTrees/class-weighting figures are not acceptance targets.',
            'data': [link('Published pointwise results', 'verification/published/pointwise_table_feff.csv', 'Author-released numerical reference, in percent; includes per-element accuracy and F1 means/stds.'),
                     link('published_targets.json', 'verification/Q1_paper/published_targets.json', 'Deterministic extraction of the published accuracy and class-F1 targets, converted to fractions.'),
                     link('truth.json', 'verification/Q1_paper/truth.json', 'Evaluator-only original labels and fixed record membership. Never provide this file to the solver.'),
                     link('scored_results.json', 'verification/Q1_paper/scored_results.json', 'Scores reconstructed from the separately executed solver and released truth; includes all 64 paper comparisons.'),
                     link('report.md', 'verification/Q1_paper/report.md', 'Validated reproduction results, numerical acceptance and experimental limits.')],
            'figures': figures,
            'methods': [link('Worked workflow', 'workflows/Q1.json', 'Executed source-to-result workflow and input boundary.'),
                        link('reproduce_coordination.py', 'workflows/reproduce_coordination.py', 'Worked solver that reads only the input bundle, without test labels.'),
                        link('verify_coordination.py', 'workflows/verify_coordination.py', 'Fixed numerical grader; reconstructs scores from labels and checks published rounding bins.'),
                        link('reference_program.py', 'verification/Q1_paper/reference_program.py', 'Independent reference fitter using raw release projections and archived memberships.'),
                        *[link(name, 'verification/Q1_paper/' + name, description) for name, description in [
                            ('preparation_audit.json', 'Exact recovered memberships, source hashes, preparation counts and test-label exclusion.'),
                            ('reference_validation.json', 'Independent 80-forest replay and agreement with all 64 published means/stds.'),
                            ('execution_check.json', 'Separate execution from the solver bundle and comparison with the independent reference.'),
                            ('adversarial_checks.json', 'Checks that incorrect predictions, missing rows and altered protocol declarations fail.')]]],
            'thresholds': {'origin': 'Benchmark-defined from published table precision',
                           'generatedBy': 'Deterministic table extraction and independently executed reproduction',
                           'provenance': 'The publication reports percentages rounded to two decimal places. The benchmark requires the prescribed fixed experiment and uses half that rounding unit as its acceptance margin. All 64 reference comparisons and the separate solver replay satisfy it. This margin is not a statistical confidence interval or physical uncertainty.',
                           'notes': [{'title': 'Published Result Agreement', 'description': 'Each of 64 mean/std comparisons must differ by at most 0.00005 in fractional score units (0.005 percentage points), plus 1e-12 arithmetic epsilon.'},
                                     {'title': 'Exact Coverage', 'description': 'Eight elements × ten prescribed forest seeds, with exactly the supplied test and validation records for each fit; predictions must be coordination labels 4, 5 or 6.'},
                                     {'title': 'No Narrative Waiver', 'description': 'Numerical reproduction has a fixed pass/fail result. A report claiming an alternative or negative finding does not waive failed checks.'}],
                           'data': [link('comparison_policy.json', 'verification/Q1_paper/comparison_policy.json', 'Fixed policy, provenance and reference/input hashes.')]
                           }
        }
    }
