"""Project Q9 IDs and historical references directly from the open release."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import joblib

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'docs/data/gleason-2024-cu-oxidation'


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--release', type=Path, default=ROOT.parent / 'gleason_2024_cu_oxidation_state')
    args = p.parse_args()
    paths = [args.release / 'data/Dataset_generation/110222_Cu_DF_With_Spectra.joblib',
             args.release / 'data/Cu_reproducable_alignment_df_extracted_110222.joblib']
    combined, processed = [joblib.load(p) for p in paths]
    source = combined.loc[combined.mp_id != 'Failed'].set_index('mp_id', verify_integrity=True)
    rows, references, documents = [], [], []
    for i, (_, row) in enumerate(processed.iterrows()):
        mid = str(row.mp_id); original = source.loc[mid]
        states = original.full_ox_states
        assert isinstance(states, dict)
        spectrum_id = f'spectrum_{i:04d}'
        rows.append({'spectrum_id': spectrum_id, 'mp_id': mid})
        references.append({**rows[-1], 'saved_average_oxidation_states': states,
                           'saved_avg_bv_int': original.avg_bv_int,
                           'released_processed_label': float(row['NEW BV Used For Alignment']),
                           'missing_assignment_in_archive': 'Cu' not in states})
        documents.append({'material_id': mid, 'average_oxidation_states': states})
    assert len(rows) == len({r['mp_id'] for r in rows})
    directory = DEST / 'inputs/Q9'; directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'spectrum_material_ids.csv').open('w', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=['spectrum_id', 'mp_id']); w.writeheader(); w.writerows(rows)
    dump(DEST / 'verification/Q9/historical_labels.json', {
        'evidence_type': 'Direct projection of authors released metadata and processed labels; not candidate-generated.',
        'use': 'Historical comparison only. Live labels must be evaluated against independent records from the same MP database version.',
        'records': references})
    dump(DEST / 'verification/Q9/historical_response_projection.json', {
        'source': 'Offline fixture projected from authors saved full_ox_states dictionaries; NOT a complete or live API response.',
        'database_version': None, 'requested_ids': [r['mp_id'] for r in rows],
        'records': documents,
        'missing_historical_fields': ['method', 'site valences', 'API retrieval time', 'database version', 'full structure']})
    dump(DEST / 'verification/Q9/provenance.json', {
        'paper_doi': '10.1038/s41524-024-01408-1',
        'data_url': 'https://zenodo.org/records/18142209',
        'code_commit': '85e0f34e448247f6c7a01705807dae39dd1d6cbd',
        'sources': [{'path': str(p.relative_to(args.release)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths],
        'input_projection': 'Only mp_id from the 3439-row processed spectral table, preserving order; spectrum_id is a benchmark-added row identifier. No spectra, formulas, structures or labels are supplied.',
        'prior_processing': 'The source table contains combined, Cu-site-averaged FEFF L2,3 spectra after the authors filtering, alignment, resampling and normalization. Upstream filtering removes failed IDs, invalid L3 Fermi references and Cu labels >=3. Labels informed the historical alignment. This task uses only the retained IDs and does not repeat those steps or filter the input list again.',
        'reference_projection': 'Historical dictionaries and avg_bv_int come from the independent combined table; released_processed_label comes directly from the processed table. No candidate label function creates these references.',
        'missing_label_policy': 'The historical pipeline changes missing assignments to zero. This task requires evidence-supported labels; that replacement alone is not evidence of Cu(0). Missing assignments remain unresolved in the worked solution.',
        'historical_records': len(rows),
        'historical_Cu_assignments': sum('Cu' in r['saved_average_oxidation_states'] for r in references),
        'historical_missing_Cu_assignments': sum(r['missing_assignment_in_archive'] for r in references),
        'live_reference_requirement': 'The evaluator captures oxidation-state records independently for the input IDs at the candidate database version. That capture is a runtime prerequisite and has not been executed here.'})
    print(json.dumps({'input_spectra': len(rows), 'historical_Cu_assignments': sum('Cu' in r['saved_average_oxidation_states'] for r in references)}))


if __name__ == '__main__':
    main()
