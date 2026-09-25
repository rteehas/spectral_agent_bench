"""Offline Q9 response-projection replay, input-boundary and grading checks."""
import csv
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from export_agent_bundle import export, ROOT

DATA = ROOT / 'docs/data/gleason-2024-cu-oxidation'
WORK = DATA / 'workflows'


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    spec = importlib.util.spec_from_file_location('q9_verifier', WORK / 'verify_oxidation_states.py')
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    spec = importlib.util.spec_from_file_location('q9_candidate', WORK / 'assign_oxidation_states.py')
    candidate = importlib.util.module_from_spec(spec); spec.loader.exec_module(candidate)
    reference = DATA / 'verification/Q9/historical_response_projection.json'
    calls, rejected = [], []
    with tempfile.TemporaryDirectory(prefix='gleason-q9-') as tmp:
        root = Path(tmp); bundle = root / 'agent'; export('Q9', bundle)
        assert {str(f.relative_to(bundle)) for f in bundle.rglob('*') if f.is_file()} == {'prompt.txt', 'inputs/spectrum_material_ids.csv'}
        source_rows = read(bundle / 'inputs/spectrum_material_ids.csv')
        assert all(set(row) == {'spectrum_id', 'mp_id'} for row in source_rows)
        output = root / 'offline_projection_replay'; output.mkdir()
        # Harness fixture, explicitly outside the agent bundle. Not live API work.
        shutil.copyfile(reference, output / 'query_snapshot.json')
        cmd = [sys.executable, str(WORK / 'assign_oxidation_states.py'), 'label',
               '--inputs', str(bundle / 'inputs'), '--output', str(output)]
        run = subprocess.run(cmd, capture_output=True, text=True, check=True)
        calls.append({'command': cmd, 'stdout': run.stdout, 'stderr': run.stderr, 'exit_code': run.returncode})
        checked = verifier.verify(bundle / 'inputs', output, reference)
        assert checked['rows'] == 3439 and checked['assigned_matched'] == 2563 and checked['unresolved_matched'] == 876
        rows = read(output / 'labels.csv')
        historical = {r['spectrum_id']: r for r in json.loads((DATA / 'verification/Q9/historical_labels.json').read_text())['records']}
        for row in rows:
            old = historical[row['spectrum_id']]
            if row['status'] == 'assigned':
                assert round(float(row['cu_oxidation_state']), 2) == old['saved_avg_bv_int']
                assert round(float(row['cu_oxidation_state']), 2) == old['released_processed_label']
            else:
                assert old['missing_assignment_in_archive'] and old['released_processed_label'] == 0
        unresolved = next(i for i, r in enumerate(rows) if r['status'] == 'unresolved')
        fractional = next(i for i, r in enumerate(rows) if r['status'] == 'assigned' and abs(float(r['cu_oxidation_state']) - round(float(r['cu_oxidation_state']))) > .05)
        # Deliberate errors should be caught by the evaluator, not just by a
        # candidate assertion that mirrors its own implementation.
        for case in ['missing_to_zero', 'fractional_to_integer', 'wrong_mapping', 'duplicate_row', 'missing_row']:
            changed = [dict(r) for r in rows]
            if case == 'missing_to_zero':
                changed[unresolved].update(cu_oxidation_state='0', status='assigned')
            elif case == 'fractional_to_integer':
                changed[fractional]['cu_oxidation_state'] = str(round(float(changed[fractional]['cu_oxidation_state'])))
            elif case == 'wrong_mapping':
                changed[0]['mp_id'] = changed[1]['mp_id']
            elif case == 'duplicate_row':
                changed.append(dict(changed[0]))
            else:
                changed.pop()
            write(output / 'labels.csv', changed)
            try:
                verifier.verify(bundle / 'inputs', output, reference)
            except AssertionError:
                rejected.append(case)
            else:
                raise AssertionError(f'Invalid output accepted: {case}')
        write(output / 'labels.csv', rows)
        # A separate synthetic fixture covers explicit zero and repeated MP IDs,
        # neither of which occurs in the chosen historical input/reference pair.
        fixture = root / 'synthetic'; fixture.mkdir(); fixture_inputs = fixture / 'inputs'; fixture_inputs.mkdir()
        write(fixture_inputs / 'spectrum_material_ids.csv', [
            {'spectrum_id': 'a', 'mp_id': 'mp-1'}, {'spectrum_id': 'b', 'mp_id': 'mp-2'},
            {'spectrum_id': 'c', 'mp_id': 'mp-2'}, {'spectrum_id': 'd', 'mp_id': 'mp-3'}])
        snap = {'source': 'synthetic unit fixture; not a Materials Project response',
                'requested_ids': ['mp-1', 'mp-2', 'mp-3'],
                'records': [{'material_id': 'mp-1', 'average_oxidation_states': {'Cu': 0}},
                            {'material_id': 'mp-2', 'average_oxidation_states': {'Cu': 5 / 3}},
                            {'material_id': 'mp-3', 'average_oxidation_states': {}}]}
        (fixture / 'query_snapshot.json').write_text(json.dumps(snap))
        candidate.assign(fixture_inputs, fixture)
        values = read(fixture / 'labels.csv')
        assert values[0]['status'] == 'assigned' and float(values[0]['cu_oxidation_state']) == 0
        assert values[1]['cu_oxidation_state'] == values[2]['cu_oxidation_state']
        assert values[3]['status'] == 'unresolved'
        # Numeric comparison permits two-decimal reporting, but not integer rounding.
        values[1]['cu_oxidation_state'] = values[2]['cu_oxidation_state'] = '1.67'
        write(fixture / 'labels.csv', values)
        verifier.verify(fixture_inputs, fixture, fixture / 'query_snapshot.json')
        retained = WORK / 'outputs/Q9'; retained.mkdir(parents=True, exist_ok=True)
        for name in ['labels.csv', 'result.json']:
            shutil.copyfile(output / name, retained / name)
    report = {'status': 'offline_components_passed_live_lookup_not_run',
              'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'command': f'{sys.executable} papers/gleason-2024-cu-oxidation/check_q9_labels.py',
              'live_query_executed': False, 'independent_live_reference_captured': False,
              'input_bundle_contains_only_prompt_and_ids': True,
              'historical_projection_replay': checked,
              'assigned_labels_match_released_values_after_two_decimal_rounding': True,
              'rejected_incorrect_answers': rejected,
              'synthetic_checks': ['Explicit zero retained as assigned', 'Repeated material ID maps back to all spectra', 'Fractional average preserved', 'Two-decimal reporting accepted'],
              'tool_calls': calls,
              'limitations': 'The response projection was supplied by the test harness; this is component validation, not an end-to-end run from IDs using a live API. No OS access-control sandbox was imposed.'}
    (DATA / 'verification/Q9/component_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'tool_calls'}, indent=2))


if __name__ == '__main__':
    main()
