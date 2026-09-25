"""Build Q9: assign Cu training labels from a spectrum-to-material ID list."""
import json


def build_scenario(docs, base):
    directory = docs / base

    def asset(name, subdir, description):
        return {'name': name, 'url': f'{base}/{subdir}/{name}', 'description': description}

    title = 'What average Cu oxidation state should label each simulated spectrum?'
    steps = [
        ('Read the spectrum-to-material mapping', 'Python / csv',
         'Read spectrum_material_ids.csv. Preserve every spectrum_id and mp_id pairing; query each distinct material ID once and map its result back to all associated spectra.',
         'The supplied mapping contains 3,439 spectra and 3,439 distinct MP IDs. The material IDs are projected from the released processed spectral table; spectrum_id is an added row identifier.'),
        ('Retrieve the material oxidation-state records', 'Python / mp-api MPRester',
         'Use MPRester.materials.oxidation_states.search(material_ids=..., all_fields=True) in batches, with all result pages enabled. Save returned records in query_snapshot.json along with queries, retrieval times, database versions and client version. Keep request failures distinct from successful requests that return no record or no Cu assignment. Check identifier changes or conflicting records before assigning a label.',
         'A live response snapshot tied to the input IDs. This authenticated stage has not been executed here. The offline check uses a clearly identified projection of historical dictionaries, not a new API response.'),
        ('Determine the material-average Cu label', 'Python / JSON processing; MP oxidation-state documents',
         'For each matched document, select average_oxidation_states["Cu"]. This is an average over Cu atoms; it can be fractional. Preserve the returned value and the document method where available. A separate recalculation of bond-valence descriptors is not needed for this worked solution.',
         'One supported Cu average for each record that supplies it. Offline replay of the archived dictionaries yields 2,563 available Cu averages, including fractional values.'),
        ('Represent unavailable assignments explicitly', 'Python / data validation',
         'Leave the value blank and explain an unresolved case if the Cu assignment is absent, a record is missing, a request failed or an identifier needs review. Distinguish an explicitly returned numeric zero from an absent assignment. Do not remove the associated spectrum from the output.',
         'The archived dictionaries leave 876 of the retained spectra unresolved. The paper pipeline later replaced these missing values with zero; those released zero labels are historical processing outputs, not independent evidence of Cu(0). Live coverage can differ.'),
        ('Save labels and provenance', 'Python / csv, json and hashlib',
         'Write labels.csv with spectrum_id, mp_id, cu_oxidation_state, status, reason and evidence. Link each row to its saved source record. Save a result summary identifying the snapshot and explaining the handling of fractional and unavailable assignments.',
         'A complete spectrum-to-label table, query snapshot and method explanation. The offline projection replay preserves all 3,439 input rows; it does not perform spectral simulation, alignment or model training.'),
        ('Compare the answer with independent records', 'Evaluator / mp-api and verify_oxidation_states.py',
         'Capture the same MP query scope independently at the same database version and compare material mappings, Cu averages and unavailable assignments. Review database drift against historical_labels.json separately. The numeric checker does not itself establish independent retrieval or chemical correctness.',
         'The historical replay and deliberately incorrect-answer checks are recorded in component_checks.json. Live API execution and independent live reference capture remain pending.')
    ]
    reason = 'Worked solution: retrieve material-level oxidation-state assignments and attach the Cu average to each simulated spectrum. API lookup is the candidate method; the released historical labels are held back for evaluator comparison.\n\n' + '\n\n'.join(
        f'{i}. {name} ({tool})\n{operation}\nOutput/status: {result}'
        for i, (name, tool, operation, result) in enumerate(steps, 1))
    comparison = [
        ('Compare spectrum and material coverage',
         'labels.csv spectrum_id/mp_id pairs.', 'The supplied spectrum_material_ids.csv.',
         'Join by spectrum_id and require exactly one output row for every input spectrum. Compare the associated mp_id, reporting missing rows, duplicates and changed mappings. Document and independently confirm any alias resolution instead of silently replacing an ID.'),
        ('Compare the saved source records',
         'query_snapshot.json, retrieval metadata and row-level evidence.',
         'An evaluator capture of Materials Project oxidation-state records for the same input IDs and database version, or an independently logged runtime response.',
         'Match records by material ID; compare the returned Cu assignments, method when present and query coverage. Verify that requests completed and all pages were retrieved. A failed request cannot establish that a label is unavailable. Resolve database-version or identifier differences before scoring. The candidate snapshot alone is not an independent reference.'),
        ('Compare the assigned Cu averages',
         'Each numeric cu_oxidation_state in labels.csv.',
         'The Cu value in average_oxidation_states of the independently captured matching MP record.',
         'Compare values after the verified material-ID join using the numeric comparison note below. Check fractional averages as well as integer values; do not accept integer rounding that changes a fractional label. The label is a Cu-atom average, not an average over all chemical elements or an unweighted average of inequivalent Cu sites. An alternative evidence-supported derivation needs reviewer assessment.'),
        ('Compare unresolved cases and historical differences',
         'Blank labels, status/reason fields and the explanation of missing assignments.',
         'The independent MP capture for current availability, plus historical_labels.json for archived values and missing-label provenance.',
         'Require an explanation for each unresolved spectrum and retain its row. Check that an explicit Cu value of zero is distinguished from absent data. Do not require zero just because the paper replaced an absent assignment with zero. Compare changed current values with the historical dictionaries and report the differences without treating confirmed database drift as an agent error. Missing or deprecated records and alternative chemical assignments require review; do not silently mark them chemically validated.')
    ]
    description = '\n\n'.join(f'{i}. {name}\nCompare: {candidate}\nReference: {reference}\nHow: {how}'
                              for i, (name, candidate, reference, how) in enumerate(comparison, 1))
    thresholds = {
        'origin': 'Benchmark-defined', 'generatedBy': 'Model-generated',
        'provenance': 'Note, the screening thresholds and comparison settings below were not reported in the paper and are not physical uncertainty estimates. They were produced separately during the labeling process.',
        'notes': [
            {'title': 'Maximum Absolute Label Difference', 'description': '0.0051 oxidation-state units against an unrounded reference value, allowing reporting to two decimal places. This is a numerical reporting allowance, not uncertainty in the oxidation-state assignment.'},
            {'title': 'Coverage', 'description': 'Every supplied spectrum must have an output row, including unresolved assignments. Compare mappings by spectrum_id rather than row order.'},
            {'title': 'Reference Version', 'description': 'Use an independently captured reference from the same MP database version. Historical labels are an audit reference; a changed live value is not automatically an error.'}
        ]}
    protocol = {'scenario_id': 'GLEASON24-Q9', 'comparisons': [
        {'step': i, 'title': name, 'compare': candidate, 'reference': reference, 'how': how}
        for i, (name, candidate, reference, how) in enumerate(comparison, 1)],
        'comparison_settings': thresholds,
        'execution_status': 'partially_validated; historical projection replay only, live capture pending',
        'input_boundary': 'Only inputs/Q9/spectrum_material_ids.csv, minimal background and runtime MP access. Do not supply historical dictionaries, labels, workflows or evaluation files to the agent.',
        'reference_limits': 'MP assignments are computational reference labels, not independently measured chemical truth. The supplied historical projection omits method and database version. The generic numeric checker supports direct ID matches; aliases, deprecated records and alternative chemical derivations require reviewer adjudication.'}
    (directory / 'verification/Q9/evaluation_protocol.json').write_text(json.dumps(protocol, indent=2, ensure_ascii=False) + '\n')
    check_path = directory / 'verification/Q9/component_checks.json'
    checks = json.loads(check_path.read_text()) if check_path.exists() else {'status': 'not_yet_executed'}
    workflow = {'scenario_id': 'GLEASON24-Q9', 'question': title,
        'runtime_requirements': ['Authenticated Materials Project API access via runtime MP_API_KEY', 'Python with mp-api; no FEFF executable or spectral arrays are required'],
        'input_boundary': protocol['input_boundary'],
        'steps': [{'step': i, 'tool': tool, 'operation': operation, 'artifact_or_check': result}
                  for i, (_, tool, operation, result) in enumerate(steps, 1)],
        'candidate_command': 'python assign_oxidation_states.py all --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY',
        'verification_command': 'python verify_oxidation_states.py --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY --reference INDEPENDENT_MP_SNAPSHOT.json',
        'execution': {'status': 'partially_validated', 'live_query_executed': False, 'component_checks': checks},
        'evidence': reason}
    (directory / 'workflows/Q9.json').write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + '\n')
    return {'id': 'GLEASON24-Q9', 'kind': 'Subquestion', 'executionStatus': 'partially_validated', 'title': title,
        'inputs': [asset('spectrum_material_ids.csv', 'inputs/Q9', 'One spectrum_id/mp_id pair per released processed spectrum, with labels removed. The source spectra were previously filtered, site-averaged, aligned, resampled and normalized; this task starts from their retained material IDs.')],
        'prompt': {
            'background': 'We need Cu oxidation-state labels to use simulated Cu L₂,₃ spectra as training examples for supervised oxidation-state prediction. Each spectrum corresponds to a material and is averaged over its Cu sites. The supplied table links each spectrum to a Materials Project ID. Authenticated Materials Project access is provided by the benchmark runtime.',
            'instruction': 'Assign an average Cu oxidation state to each simulated spectrum using its material ID and Materials Project records. Return labels.csv with spectrum_id, mp_id, cu_oxidation_state, status (assigned or unresolved), reason and evidence. Explain your labeling method and report any spectrum whose label cannot be established. Save the retrieved records, queries, retrieval time and database/client versions in query_snapshot.json so the assignments can be checked.'},
        'verification': {'description': description,
            'data': [asset('historical_labels.json', 'verification/Q9', 'Held-back historical Cu dictionaries and released labels for every input material; distinguishes absent assignments from the paper’s subsequent zero replacement. Current labels require an independent reference at the same MP version.'),
                     asset('provenance.json', 'verification/Q9', 'Release hashes, input projection, prior processing and historical-reference limitations.')],
            'figures': [],
            'methods': [asset('Q9.json', 'workflows', 'Step-by-step worked tool sequence and actual execution status. Exclude from agent inputs.'),
                        asset('assign_oxidation_states.py', 'workflows', 'Executable candidate for live retrieval and per-spectrum Cu labels. Exclude from agent inputs.'),
                        asset('verify_oxidation_states.py', 'workflows', 'Evaluator label/mapping checker; live provenance and alternative assignments require separate review.'),
                        asset('evaluation_protocol.json', 'verification/Q9', 'What to compare, the required independent live reference and how to handle historical differences.'),
                        asset('component_checks.json', 'verification/Q9', 'Actual offline replay and incorrect-answer checks; authenticated live retrieval remains unexecuted.')],
            'thresholds': thresholds},
        'groundTruthReasoning': reason}
