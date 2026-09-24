"""Build the live-search / fresh-simulation question with explicit execution status."""
import json


def build_scenario(docs, base):
    def asset(name, directory, description):
        return {'name': name, 'url': f'{base}/{directory}/{name}', 'description': description}

    steps = [
        ('Search Materials Project', 'Python / mp-api MPRester',
         'Query all current, non-deprecated Cu-containing materials, retrieving material IDs, structures, predicted-stability flags and the theoretical flag used to identify experimentally synthesized materials. Record the query, client version, database version before/after retrieval and retrieval timestamp. Save the full returned records before selection.',
         'query_snapshot.json. This authenticated live query has not yet been executed in the benchmark environment.'),
        ('Identify additions to the seed set', 'Python / CSV and JSON processing',
         'Read seed_material_ids.csv, discard Failed sentinels and form the valid seed-ID set. Retain returned materials that are predicted stable OR experimentally synthesized, using is_stable=True and theoretical=False as the respective indicators, exclude the seed IDs, and deduplicate by material ID. Record the reason for every retained ID. Flag alias/deprecation issues instead of treating an unresolved identifier as proof of novelty.',
         'additional_materials.csv. Boolean selection and seed exclusion have been tested on an offline fixture; there is no fixed historical target count for a live search.'),
        ('Choose three representative structures', 'Python / pymatgen Structure and SpacegroupAnalyzer',
         'Use the returned compositions and structures to identify inequivalent Cu sites with the supplied symmetry tolerance. Choose exactly three eligible structures and explain which chemical environments they contribute as candidate training examples, including a single-Cu-environment case and a multiple-Cu-environment case when available. One worked strategy favors compact cells and adds a different synthesis/stability category for the third choice. Inspect the resulting compositions and Cu site groups to explain their relevance to the prediction problem.',
         'selected_materials.json containing the structures, Cu multiplicities and selection rationale. The offline examples span Cu–Te, Tb–Cu and K–Cu–Se compositions: CuTe₂ and KCu₄Se₃ each have one inequivalent Cu environment, while TbCu₅ has two. These IDs are not mandatory answers to the live task, and this variety alone does not establish oxidation-state coverage or improved model accuracy.'),
        ('Generate site-specific FEFF inputs', 'Python / pymatgen FEFFDictSet; Lightshow is an alternative setup tool',
         'For each selected structure, create an absorber-centered cluster for every inequivalent Cu site. Write separate L₂ and L₃ feff.inp files using simulation_settings.json. Preserve site multiplicities and associate every job with its structure, absorber, edge and input hash.',
         'jobs.json and job directories. The offline check generated eight decks for the three archived examples and checked their structures and control tags against the release.'),
        ('Execute and inspect FEFF calculations', 'FEFF9 / runtime-provided driver; Python subprocess',
         'Run a fresh FEFF calculation in each site/edge directory. Save the command, version, return status, elapsed time, output hashes and full log. Inspect convergence and the xmu.dat energy/intensity arrays. Record failures and resolve or explicitly report incomplete material spectra; a file left by a failed run is not sufficient evidence of success.',
         'Fresh xmu.dat files, run.log files and execution.json. This stage has not been run here: no FEFF executable is configured. Archived outputs used in the offline postprocessing check are not presented as new simulations.'),
        ('Construct the material spectra', 'Python / NumPy, pandas and Matplotlib',
         'Combine the new L₂ and L₃ spectra for each Cu environment on compatible energy grids, then average the environments by their Cu multiplicities. Save one energy/intensity CSV and a plot of weighted contributions for each material, preserving the unaligned FEFF conventions. Document the interpolation and boundary treatment.',
         'spectra/MATERIAL_ID/spectrum.csv, plot.png and result.json. Assembly from the archived example outputs reproduces their separately released material curves; fresh-run validation remains pending.'),
        ('Verify the search and simulation results', 'Evaluator / independent MP response capture, pymatgen and FEFF9',
         'Recompute selection against the query response captured by the evaluation harness. Check the chosen structures, absorber environments, multiplicities and FEFF settings. Compare with archived site/material spectra only when those inputs match. For new or changed structures, an evaluator must independently generate FEFF references from the captured structures; an archived spectrum with the same material ID alone is not an adequate reference.',
         'An evaluated live-search snapshot and three spectral comparisons. Numerical FEFF acceptance limits need pilot validation before this draft is used for scoring.')
    ]
    reason = '\n\n'.join([
        'Worked candidate workflow — partially validated. The purpose is to obtain candidate training spectra across Cu chemical environments for oxidation-state prediction. These spectra would subsequently need alignment and oxidation-state labels before model training. Selection logic, FEFF input generation and assembly from archived example outputs have been checked. The authenticated live search and fresh FEFF calculations remain unexecuted. The steps below describe the complete intended workflow and distinguish its tested parts.',
        *[f'{i}. {title} ({tool})\n{operation}\nOutput/status: {result}'
          for i, (title, tool, operation, result) in enumerate(steps, 1)],
        'Program: search_and_simulate.py, run in stages search → prepare → run → collect with --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY. MP_API_KEY and a FEFF9 driver configured through FEFF_COMMAND belong to the runtime. The agent reads no evaluator reference files. Source: the paper’s Training set generation methods, released FEFF decks/results and Database_Construction.ipynb.'
    ])
    protocol = {
        'status': 'draft_requires_live_search_and_fresh_FEFF_validation',
        'question': 'GLEASON24-Q8',
        'search_ground_truth': {
            'source': 'Full live Materials Project response independently captured by the evaluation harness, pinned to database version and timestamp.',
            'predicate': 'Cu-containing, non-deprecated, (is_stable is True OR theoretical is False), and not in the valid seed-ID set.',
            'completeness': 'Check query scope and pagination against the harness capture. A list of self-reported selected IDs does not establish search completeness.',
            'id_changes': 'Check reported aliases/deprecations; the candidate must not silently reinterpret unresolved seed IDs as novel materials.',
            'historical_count': 'Do not require exactly 2,175 IDs or the paper figure counts from today’s database.'},
        'simulation_ground_truth': {
            'budget': 'Exactly three eligible materials, with single-site and multiple-site Cu environments represented when available.',
            'scientific_rationale': 'Review the selected compositions and Cu environments as candidate training examples for oxidation-state prediction. Do not infer improved prediction accuracy or established oxidation-state coverage from three simulations alone.',
            'setup': 'Independently check crystal structure, equivalent Cu groups, multiplicity weights, L2/L3 job coverage and declared FEFF settings.',
            'fresh_execution': 'Require a benchmark-managed FEFF execution trace, convergence checks and raw output files. Candidate-authored logs alone are not proof of computation.',
            'archived_references': 'Use reference_cases.json and the site/material CSVs only after checking that the structures, absorber environments, settings and energy conventions agree.',
            'new_or_changed_inputs': 'Generate independent evaluator FEFF references from the pinned current structures. Do not grade new structures against unrelated archived curves.',
            'failure_handling': 'Record incomplete/failed calculations and missing multiplicity coverage. Do not declare a complete three-material answer by silently omitting failed sites.',
            'comparison': 'Assess energy axes, edge features, relative intensities, material averaging and contribution plots. No numerical FEFF threshold is claimed as calibrated before the fresh-run pilot.'},
        'input_boundary': 'Only seed IDs, simulation settings, necessary scientific background, live MP access and the runtime FEFF installation go to the agent. Keep reference_cases, archived spectra, runtime audit, candidate code and setup-check fixtures on the evaluator side.'
    }
    directory = docs / base
    (directory / 'verification/Q8/evaluation_protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    checks = json.loads((directory / 'verification/Q8/setup_checks.json').read_text())
    workflow = {
        'scenario_id': 'GLEASON24-Q8', 'execution_status': 'partially_validated',
        'program': 'search_and_simulate.py',
        'runtime_requirements': ['Authenticated Materials Project access via MP_API_KEY',
                                 'FEFF9 installation/driver supplied by the benchmark host',
                                 'CPU allocation and Python with mp-api, pymatgen, NumPy, pandas and Matplotlib'],
        'input_boundary': protocol['input_boundary'],
        'steps': [{'step': i, 'tool': tool, 'operation': operation, 'artifact_or_check': result}
                  for i, (_, tool, operation, result) in enumerate(steps, 1)],
        'candidate_commands': [f'python search_and_simulate.py {stage} --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY'
                               for stage in ['search', 'prepare', 'run', 'collect']],
        'verification': 'Evaluator protocol in verification/Q8/evaluation_protocol.json; not covered by the Q1–Q7 numerical checker.',
        'evidence': reason,
        'execution': {'status': 'offline_components_passed_live_stages_not_run',
                      'executed_command': '/tmp/gleason-preview-py310/bin/python papers/gleason-2024-cu-oxidation/check_q8_setup.py',
                      'checks': checks,
                      'live_query_executed': False, 'fresh_feff_executed': False}
    }
    (directory / 'workflows/Q8.json').write_text(json.dumps(workflow, indent=2, ensure_ascii=False) + '\n')
    return {
        'id': 'GLEASON24-Q8', 'kind': 'Subquestion', 'executionStatus': 'partially_validated',
        'title': 'Which Cu materials can supply training spectra for oxidation-state prediction across different chemical environments?',
        'inputs': [
            asset('seed_material_ids.csv', 'inputs/Q8', 'Material-ID column projected from Cu_full_df_with_spectra.joblib, retaining its 1,533 records and Failed sentinels. No additional-material roster or spectra are supplied.'),
            asset('simulation_settings.json', 'inputs/Q8', 'FEFF control settings recovered from the open release, benchmark structure/cluster settings, and the three-material simulation budget. No completed input decks or spectra.')],
        'prompt': {
            'background': 'The research goal is to predict the average Cu oxidation state from XAS and EELS spectra across different compounds. Cu L₂,₃ spectral shape depends on the local chemical environment as well as oxidation state, so examples spanning different Cu environments are relevant to learning a relationship that transfers between compounds. The supplied seed list identifies materials in an existing collection of simulated spectra. Other Cu-containing structures in Materials Project offer candidate training examples; their spectra can be calculated with FEFF.\n\nTo focus on potentially experimentally accessible materials, consider Cu-containing materials that have been experimentally synthesized or are predicted to be thermodynamically stable. The spectra are simulated in this task. Use current non-deprecated MP records and exclude valid IDs in the seed list. Use the supplied simulation settings. The benchmark runtime must provide Materials Project API access and a working FEFF9 installation.',
            'instruction': 'Identify candidate materials that could broaden the training examples for this oxidation-state prediction problem, and obtain simulated spectra for three representative cases. Perform a live Materials Project search for the full eligible additional-material set. Save the query, retrieval time, database/client versions and all returned records in query_snapshot.json, and save the deduplicated selected IDs with selection reasons in additional_materials.csv. Document unresolved identifier aliases or deprecations. Select exactly three representative eligible materials and justify the choice in terms of their chemistry and Cu environments; include both a single-Cu-environment case and a multiple-Cu-environment case when available. Obtain their structures, identify the inequivalent Cu absorbers, generate and execute separate FEFF L₂ and L₃ calculations for each, and construct their material-averaged spectra. Return the selected structures and rationale, site multiplicities, input decks, commands, complete execution/convergence logs, raw xmu.dat outputs, one spectrum.csv and weighted-contribution plot per material, and a summary of failures or incomplete coverage. Preserve FEFF energy/intensity conventions and explain the edge combination and averaging. Do not replace fresh simulations with downloaded reference spectra.'},
        'verification': {
            'description': 'Execution status: draft, partially validated. Offline checks cover selection logic, generated input decks and postprocessing of archived examples. The live MP query and fresh FEFF9 runs have not yet been executed here. Verify the live search against an independently captured response, then check selection, structures, site/edge coverage and benchmark-managed FEFF execution. Archived spectra are valid numerical references only for matching simulation inputs; new or changed structures require independent evaluator simulations. Review how the three selected compositions and Cu environments contribute candidate training examples, along with their contribution plots. The answer establishes sources of training spectra; improved prediction accuracy would require a separate model evaluation. See evaluation_protocol.json for the complete procedure.',
            'data': [
                asset('reference_cases.json', 'verification/Q8', 'Three historical reference cases with archived structures, absorber indices, control tags and source hashes. These are not a fixed answer to the current search.'),
                asset('reference_site_spectra.csv', 'verification/Q8', 'Raw site/edge spectra copied from the release; use only after matching the simulation inputs.'),
                asset('reference_material_spectra.csv', 'verification/Q8', 'Material-averaged spectra copied independently from the authors combined pre-alignment table.'),
                asset('provenance.json', 'verification/Q8', 'Input projections, archived-reference sources and hashes, and limits of historical verification.')],
            'figures': [],
            'methods': [
                asset('Q8.json', 'workflows', 'Worked tool sequence and actual component-check record; excludes unexecuted stages from claims of success.'),
                asset('search_and_simulate.py', 'workflows', 'Candidate program for live search, input generation, fresh FEFF execution and spectral assembly. Exclude from agent inputs.'),
                asset('evaluation_protocol.json', 'verification/Q8', 'Evaluator procedure for a live search and fresh simulations, including reference matching and outstanding validation.'),
                asset('setup_checks.json', 'verification/Q8', 'Actual offline component checks; explicitly records that live search and fresh simulation were not executed.'),
                asset('runtime_audit.json', 'verification/Q8', 'Historical timing evidence for computational planning; not a runtime guarantee or answer target.')]
        },
        'groundTruthReasoning': reason
    }
