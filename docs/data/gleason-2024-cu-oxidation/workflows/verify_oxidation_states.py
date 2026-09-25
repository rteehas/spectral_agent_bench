"""Q9 evaluator: compare labels against an independently supplied MP snapshot.

The reference must not be the candidate's own response. This checks row mapping
and numeric labels only; independent retrieval, identifier changes and scientific
justification require the separate evaluation protocol.
"""
import argparse
import csv
import json
import math
from pathlib import Path


def verify(inputs, output, reference, tolerance=0.0051):
    with (inputs / 'spectrum_material_ids.csv').open() as handle:
        expected_rows = list(csv.DictReader(handle))
    with (output / 'labels.csv').open() as handle:
        submitted = list(csv.DictReader(handle))
    expected = {r['spectrum_id']: r['mp_id'] for r in expected_rows}
    actual = {r['spectrum_id']: r for r in submitted}
    assert len(expected) == len(expected_rows), 'Duplicate input spectrum IDs'
    assert len(actual) == len(submitted), 'Duplicate submitted spectrum IDs'
    assert set(actual) == set(expected), 'Missing or extra spectrum rows'
    snapshot = json.loads(reference.read_text())
    assert set(snapshot['requested_ids']) == set(expected.values()), 'Reference query scope mismatch'
    assert snapshot.get('database_version_consistent') is not False, 'Reference database changed'
    assert all(r['status'] == 'complete' for r in snapshot.get('requests', [])), 'Incomplete reference retrieval'
    docs = {}
    for d in snapshot['records']:
        mid = str(d['material_id'])
        assert mid not in docs or docs[mid] == d, 'Conflicting evaluator records'
        docs[mid] = d
    assigned, unresolved, review = 0, 0, []
    for sid, mid in expected.items():
        row = actual[sid]
        assert row['mp_id'] == mid, f'{sid}: incorrect material mapping'
        assert row.get('evidence', '').strip(), f'{sid}: missing evidence reference'
        doc = docs.get(mid)
        if doc and doc.get('deprecated') is True:
            review.append({'spectrum_id': sid, 'reason': 'deprecated material; adjudicate mapping'})
            continue
        val = (doc.get('average_oxidation_states') or {}).get('Cu') if doc else None
        if val is None:
            assert row['status'] == 'unresolved' and row['cu_oxidation_state'] == '', f'{sid}: unsupported assignment'
            assert row.get('reason', '').strip(), f'{sid}: unexplained unresolved row'
            unresolved += 1
        else:
            assert not isinstance(val, bool) and isinstance(val, (int, float)) and math.isfinite(val), 'Invalid evaluator Cu value'
            assert row['status'] == 'assigned', f'{sid}: available assignment omitted'
            candidate = float(row['cu_oxidation_state'])
            assert math.isfinite(candidate) and abs(candidate - val) <= tolerance, f'{sid}: incorrect Cu average'
            assigned += 1
    return {'rows': len(submitted), 'assigned_matched': assigned, 'unresolved_matched': unresolved,
            'manual_review': review, 'numeric_check_complete': not review,
            'scope': 'Label/mapping comparison only; does not certify independent live retrieval or chemical correctness.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(verify(args.inputs, args.output, args.reference), indent=2))
