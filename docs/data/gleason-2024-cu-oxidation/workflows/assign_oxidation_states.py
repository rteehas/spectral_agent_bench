"""Worked Q9 candidate. Fetch live MP records, then label a spectrum-ID table.

Only spectrum_material_ids.csv and runtime API access are agent inputs.
The label stage also supports explicitly identified offline response fixtures;
such replay is not a live candidate run. No evaluator references are read here.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path


def dump(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def read_inputs(inputs):
    with (inputs / 'spectrum_material_ids.csv').open() as handle:
        rows = list(csv.DictReader(handle))
    if not rows or len({r['spectrum_id'] for r in rows}) != len(rows):
        raise ValueError('Require nonempty, unique spectrum IDs')
    if any(not re.fullmatch(r'mp-\d+', r['mp_id']) for r in rows):
        raise ValueError('Invalid MP ID in input')
    return rows


def fetch(inputs, output):
    from mp_api.client import MPRester
    key = os.environ.get('MP_API_KEY')
    if not key:
        raise RuntimeError('The runtime must supply MP_API_KEY')
    ids = sorted({r['mp_id'] for r in read_inputs(inputs)})
    records, requests = [], []
    started = datetime.now(timezone.utc).isoformat()
    with MPRester(key, use_document_model=False, monty_decode=False) as mpr:
        before = mpr.get_database_version()
        for offset in range(0, len(ids), 200):
            batch = ids[offset:offset + 200]
            query = {'material_ids': batch, 'all_fields': True,
                     'num_chunks': None, 'chunk_size': 1000}
            try:
                found = mpr.materials.oxidation_states.search(**query)
            except Exception as exc:
                # Do not persist exception text: request URLs can contain secrets.
                requests.append({'query': query, 'status': 'failed',
                                 'error_type': type(exc).__name__})
                continue
            records.extend(found)
            requests.append({'query': query, 'status': 'complete',
                             'returned_ids': [str(d['material_id']) for d in found]})
        after = mpr.get_database_version()
    snapshot = {'source': 'live Materials Project materials.oxidation_states.search',
                'started_at_utc': started,
                'completed_at_utc': datetime.now(timezone.utc).isoformat(),
                'mp_api_version': version('mp-api'),
                'database_version': before, 'database_version_after': after,
                'database_version_consistent': before == after,
                'requested_ids': ids, 'requests': requests, 'records': records}
    dump(output / 'query_snapshot.json', snapshot)
    if before != after:
        raise RuntimeError('Database version changed; snapshot retained, repeat retrieval')


def assign(inputs, output):
    rows = read_inputs(inputs)
    path = output / 'query_snapshot.json'
    snapshot = json.loads(path.read_text())
    if snapshot.get('database_version_consistent') is False:
        raise ValueError('Cannot label from a snapshot spanning database versions')
    wanted = {r['mp_id'] for r in rows}
    if set(snapshot['requested_ids']) != wanted:
        raise ValueError('Snapshot does not cover this input ID list')
    by_id, conflicts = {}, set()
    for record in snapshot['records']:
        mid = str(record['material_id'])
        if mid not in wanted:
            raise ValueError('Snapshot includes an unrequested material')
        if mid in by_id and by_id[mid] != record:
            conflicts.add(mid)
        by_id[mid] = record
    failed = {mid for request in snapshot.get('requests', [])
              if request['status'] == 'failed'
              for mid in request['query']['material_ids']}
    results = []
    for row in rows:
        mid = row['mp_id']; doc = by_id.get(mid)
        value, reason = None, ''
        if mid in conflicts:
            reason = 'conflicting_records'
        elif mid in failed:
            reason = 'query_failed'
        elif doc is None:
            reason = 'record_not_returned'
        elif doc.get('deprecated') is True:
            reason = 'deprecated_record_needs_identifier_review'
        else:
            states = doc.get('average_oxidation_states') or {}
            value = states.get('Cu')
            if value is None:
                reason = 'Cu_assignment_unavailable'
            elif isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                value, reason = None, 'invalid_Cu_assignment'
        results.append({**row, 'cu_oxidation_state': value,
                        'status': 'assigned' if value is not None else 'unresolved',
                        'reason': reason,
                        'evidence': f"query_snapshot.json:material_id={mid}; method={doc.get('method') if doc else None}"})
    with (output / 'labels.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['spectrum_id', 'mp_id', 'cu_oxidation_state',
                                                    'status', 'reason', 'evidence'])
        writer.writeheader(); writer.writerows(results)
    summary = {'spectra': len(results), 'assigned': sum(r['status'] == 'assigned' for r in results),
               'unresolved': sum(r['status'] == 'unresolved' for r in results),
               'snapshot_source': snapshot['source'],
               'snapshot_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'method': 'Use the returned average Cu oxidation state without integer rounding or missing-to-zero imputation.'}
    dump(output / 'result.json', summary)
    print(json.dumps(summary))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', choices=['fetch', 'label', 'all'])
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    if args.stage in ('fetch', 'all'):
        fetch(args.inputs, args.output)
    if args.stage in ('label', 'all'):
        assign(args.inputs, args.output)


if __name__ == '__main__':
    main()
