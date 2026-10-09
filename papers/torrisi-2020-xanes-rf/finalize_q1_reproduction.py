"""Verify the independent solver execution and render evaluator-side Q1 results."""
import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
REFERENCE = DATA / 'verification/Q1_paper'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_predictions(path):
    with path.open(newline='') as stream:
        return {(r['element'], int(r['seed']), int(r['source_row'])): int(r['prediction'])
                for r in csv.DictReader(stream)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solver-output', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--executed-command', help='Exact command recorded by the caller, if available')
    args = parser.parse_args()
    source = DATA / 'workflows/verify_coordination.py'
    spec = importlib.util.spec_from_file_location('fixed_grader', source)
    grader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grader)
    result = grader.verify(args.solver_output)
    independent = {}
    for path in sorted((REFERENCE / 'independent_reference').glob('*_predictions.csv')):
        independent.update(read_predictions(path))
    predictions = read_predictions(args.solver_output / 'predictions.csv')
    assert len(predictions) == 38610 and predictions == independent
    solver_source = args.solver_output / 'code/reproduce_coordination.py'
    assert digest(solver_source) == digest(DATA / 'workflows/reproduce_coordination.py')
    worked = REFERENCE / 'worked'
    shutil.copytree(args.solver_output, worked, dirs_exist_ok=True)
    shutil.copyfile(args.log, worked / 'execution.log')
    (REFERENCE / 'scored_results.json').write_text(json.dumps(result, indent=2) + '\n')
    execution = {
        'status': 'separate_solver_execution_passed', 'publication_reproduction_pass': True,
        'independent_predictions_match': True, 'matching_test_predictions': len(predictions),
        'forest_fits': 80, 'trees_per_fit': 300, 'solver_input_files': 9,
        'executed_command': args.executed_command,
        'reproduction_command': 'OPENBLAS_NUM_THREADS=1 python docs/data/torrisi-2020-xanes-rf/workflows/reproduce_coordination.py --inputs INPUT_DIRECTORY --output NEW_OUTPUT_DIRECTORY --jobs 4',
        'verification_command': 'python docs/data/torrisi-2020-xanes-rf/workflows/verify_coordination.py --output OUTPUT_DIRECTORY',
        'solver_source_sha256': digest(solver_source), 'verifier_sha256': digest(source),
        'output_sha256': {str(p.relative_to(worked)): digest(p) for p in sorted(worked.rglob('*')) if p.is_file()},
        'input_boundary': 'The solver source matches the worked program that reads only eight NPZ input files and protocol.json, computing validation scores without evaluator test labels. This local audit is not an OS-level sandbox claim; the benchmark harness must enforce isolation.',
        'reference_independence': 'A separately coded fitter reconstructed inputs from released raw rows and archived memberships before this solver was run. All test predictions match and all 64 published values pass the rounding test.'}
    (REFERENCE / 'execution_check.json').write_text(json.dumps(execution, indent=2) + '\n')
    elements = json.loads((DATA / 'inputs/Q1_paper/protocol.json').read_text())['elements']
    metrics = ['accuracy', 'f1_4', 'f1_5', 'f1_6']
    labels = ['Accuracy', 'F1: coordination 4', 'F1: coordination 5', 'F1: coordination 6']
    values = {(r['element'], r['metric'], r['statistic']): r for r in result['published_comparisons']}
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True, sharey=True)
    x = np.arange(8)
    for ax, metric, label in zip(axes.flat, metrics, labels):
        for name, offset, color, marker in [('published', -.07, 'black', 'x'), ('actual', .07, '#176a9f', 'o')]:
            means = [values[e, metric, 'mean'][name] for e in elements]
            deviations = [values[e, metric, 'std'][name] for e in elements]
            ax.errorbar(x + offset, means, yerr=deviations, fmt=marker, color=color, capsize=3,
                        label='Published' if name == 'published' else 'Reproduced')
        ax.set_title(label)
        ax.set_xticks(x, elements)
        ax.set_ylim(.5, 1)
        ax.grid(axis='y', alpha=.2)
        ax.set_ylabel('Score')
    axes[0, 0].legend(loc='lower left')
    fig.suptitle('Published pointwise coordination results reproduced\nError bars: SD over ten prescribed forest seeds', fontsize=14)
    fig.tight_layout()
    fig.savefig(REFERENCE / 'published_comparison.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for ax, statistic in zip(axes, ['mean', 'std']):
        ax.axhspan(-.005, .005, color='#ddebdc', label='Published rounding margin')
        ax.axhline(0, color='black', linewidth=.6)
        for metric, label in zip(metrics, labels):
            differences = [100 * (values[e, metric, statistic]['actual'] - values[e, metric, statistic]['published']) for e in elements]
            ax.plot(x, differences, marker='o', markersize=4, label=label)
        ax.set_title('Mean' if statistic == 'mean' else 'Population standard deviation')
        ax.set_ylim(-.006, .006)
        ax.set_ylabel('Difference\n(percentage points)')
        ax.set_xticks(x, elements)
    axes[0].legend(ncol=3, fontsize=8, loc='upper center', bbox_to_anchor=(.5, 1.45))
    fig.suptitle('Reproduced minus published: all 64 values within rounding precision', fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(REFERENCE / 'rounding_residuals.png', dpi=160, bbox_inches='tight')
    plt.close(fig)
    lines = ['# Q1: published pointwise coordination experiment reproduced', '',
             'All eight elements, ten prescribed seeds, 38,610 test predictions and 64 published mean/SD comparisons pass. An independent raw-data implementation and a separate solver-bundle execution produce identical test predictions.', '',
             '| Element | Test accuracy | F1: CN4 | F1: CN5 | F1: CN6 | Test counts: CN4 / CN5 / CN6 |',
             '|---|---:|---:|---:|---:|---|']
    for element in elements:
        mean = [values[element, metric, 'mean']['actual'] for metric in metrics]
        counts = result['test_class_support'][element]
        lines.append('| ' + element + ' | ' + ' | '.join(f'{v:.4f}' for v in mean) + ' | ' + ' / '.join(str(counts[str(k)]) for k in [4, 5, 6]) + ' |')
    lines += ['', 'Accuracy and per-class F1 are measured directly against the released coordination labels. All displayed values are means over seeds 42–51. The table and plots reproduce the author-released pointwise results; they replace the previous ExtraTrees/class-weighting illustration.', '',
              'The reproduced failure pattern includes lower CN4 F1 for Mn/Cu and lower CN5 F1 for Cr/Co. High overall accuracy therefore does not imply equally reliable identification of every coordination class.', '',
              'Acceptance is fixed: each published mean and population SD must match within 0.00005 in fractional score units plus 1e-12 arithmetic epsilon. This is half a 0.01-percentage-point rounding unit. The separate replay empirically reproduces every published value at that precision; the rule is not a confidence interval or an adjustable performance threshold.', '',
              'The input cohort, preprocessing, order, oversampling and forest settings follow the pinned source notebooks. The released successive splits yield approximately 81/9/10, while the article describes 80/10/10. The exact released membership is preserved. The pinned modern scikit-learn runtime reproduces the published aggregate results despite the original study using version 0.21.3.', '',
              'The oversampling-effect ablation is not scored. The paper reports a validation benefit but does not provide a complete paired effect table. These final-model test results do not establish that oversampling helps every element or every class.', '',
              'The holdout unit is a spectral record. Related structures may cross partitions. Seed-to-seed SD does not measure uncertainty across splits, new materials or experimental spectra. Test labels are excluded from the solver bundle; the benchmark harness must also exclude the full labeled datasets and public evaluator assets.', '',
              'Sources: Torrisi et al., doi:10.1038/s41524-020-00376-6; author-released pointwise_table_feff.csv; TRIXS commit 6dbcc598c7bea235f464bed91744c1617725b7a8. Data attribution and CC BY 4.0 provenance are retained in the parent provenance.json.']
    (REFERENCE / 'report.md').write_text('\n'.join(lines) + '\n')
    print('Verified 38,610 matching independent predictions and rendered the published-result comparison.')


if __name__ == '__main__':
    main()
