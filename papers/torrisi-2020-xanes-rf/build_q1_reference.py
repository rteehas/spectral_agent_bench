"""Freeze Q1 targets from the published table after an independent replay matches."""
import argparse
import csv
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'docs/data/torrisi-2020-xanes-rf'
TRUTH = DATA / 'verification/Q1_paper'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-output', type=Path, required=True)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--executed-command', help='Exact command recorded by the caller, if available')
    args = parser.parse_args()
    table = DATA / 'verification/published/pointwise_table_feff.csv'
    protocol_path = DATA / 'inputs/Q1_paper/protocol.json'
    protocol = json.loads(protocol_path.read_text())
    targets = {'source': '../published/pointwise_table_feff.csv', 'source_sha256': digest(table),
               'units': 'Fractions: published percentages divided by 100.',
               'statistics': 'Mean and population standard deviation over ten forest fits on the same held-out spectral records.',
               'elements': {}}
    with table.open(newline='') as stream:
        for row in list(csv.reader(stream))[1:9]:
            targets['elements'][row[0]] = {}
            for metric, text in zip(['accuracy', 'f1_4', 'f1_5', 'f1_6'], row[2:6]):
                numbers = [float(v) / 100 for v in re.findall(r'\d+(?:\.\d+)?', text)]
                assert len(numbers) == 2
                targets['elements'][row[0]][metric] = dict(zip(['mean', 'std'], numbers))
    assert list(targets['elements']) == protocol['elements']
    comparisons = []
    references = TRUTH / 'independent_reference'
    references.mkdir(exist_ok=True)
    for element in protocol['elements']:
        path = args.reference_output / (element + '.json')
        run = json.loads(path.read_text())
        assert run['seeds'] == protocol['forest_seeds']
        assert run['numpy'] == protocol['runtime']['numpy']
        assert run['scikit_learn'] == protocol['runtime']['scikit-learn']
        for metric, statistics in targets['elements'][element].items():
            for statistic, expected in statistics.items():
                actual = run['summary'][metric][statistic]
                error = abs(actual - expected)
                # The table prints two decimal places in percentage units.
                assert error <= .00005 + 1e-12, (element, metric, statistic, actual, expected)
                comparisons.append({'element': element, 'metric': metric, 'statistic': statistic,
                                    'published': expected, 'reproduced': actual, 'absolute_difference': error})
        shutil.copyfile(path, references / path.name)
        path = args.reference_output / (element + '_predictions.csv')
        shutil.copyfile(path, references / path.name)
    shutil.copyfile(args.log, references / 'execution.log')
    dump(TRUTH / 'published_targets.json', targets)
    policy = {
        'task': protocol['task'], 'status': 'validated_against_all_64_published_mean_and_std_values',
        'origin': 'Benchmark acceptance rule derived from author-released table precision.',
        'absolute_tolerance': .00005, 'floating_point_epsilon': 1e-12,
        'explanation': 'Published accuracy and class-specific F1 means/stds are rounded to 0.01 percentage points. Accept each reconstructed fraction within half that rounding unit (0.005 percentage points = 0.00005), plus 1e-12 arithmetic epsilon. These are rounding bins, not statistical confidence intervals, physical uncertainties, or minimum-score thresholds.',
        'statistics': ['mean', 'population_std'], 'metrics': ['accuracy', 'f1_4', 'f1_5', 'f1_6'],
        'protocol_sha256': digest(protocol_path), 'published_targets_sha256': digest(TRUTH / 'published_targets.json'),
        'truth_sha256': digest(TRUTH / 'truth.json'),
        'oversampling_effect': 'Not scored: this task reproduces the final oversampled-model test results. The paper reports an improvement on validation but does not provide a complete paired effect table; no positive effect for every element/class is imposed.',
        'acceptance': 'Require exact prescribed test/validation record and seed coverage, valid coordination predictions, matching input/protocol declarations and oversampling counts, and agreement with all 64 published values. A failed numerical comparison cannot be waived by a narrative claim.',
        'runtime_boundary': 'The benchmark harness executes submitted code with only the declared solver bundle. Published tables, full labeled records for other questions, and all evaluator assets must be inaccessible. The offline checker does not itself establish execution isolation.'}
    dump(TRUTH / 'comparison_policy.json', policy)
    dump(TRUTH / 'reference_validation.json', {
        'status': 'published_table_reproduced_to_reported_precision',
        'independent_program': 'papers/torrisi-2020-xanes-rf/reproduce_q1_reference.py',
        'independent_program_sha256': digest(ROOT / 'papers/torrisi-2020-xanes-rf/reproduce_q1_reference.py'),
        'executed_command': args.executed_command,
        'reproduction_command': 'OPENBLAS_NUM_THREADS=1 python papers/torrisi-2020-xanes-rf/reproduce_q1_reference.py --output NEW_REFERENCE_DIRECTORY --jobs 4',
        'source_notebooks': json.loads((DATA / 'verification/source_map.json').read_text())['code_notebooks'],
        'models_fitted': 80, 'trees_per_model': 300, 'test_predictions': sum(len(json.loads((references / (e + '.json')).read_text())['metrics']) * json.loads((references / (e + '.json')).read_text())['test_records'] for e in protocol['elements']),
        'published_statistics_checked': len(comparisons), 'maximum_absolute_difference': max(r['absolute_difference'] for r in comparisons),
        'comparisons': comparisons, 'reference_artifacts_sha256': {p.name: digest(p) for p in sorted(references.iterdir())},
        'independence': 'Reference fitting reads raw released projections and archived row memberships. It does not import or read the solver workflow or its outputs. The solver is checked separately from the bundle without test labels.',
        'limitations': 'The model runtime is modern and pinned. Agreement is established with the authors released aggregate table; individual original forest predictions were not released. The same fixed spectral-record holdout is used, so the fit-to-fit SD does not estimate split or new-material uncertainty.'})
    print(f'All {len(comparisons)} published statistics match; fixed rounding tolerance 0.00005.')


if __name__ == '__main__':
    main()
