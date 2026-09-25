"""Build the discovery task without exposing its evaluator-side target."""
import json


TITLE = 'How can phase identification from ordinary powder diffraction become more reliable without additional measurements?'
BACKGROUND = (
    'The supplied single-phase simulations cover two chemical systems. Each NPZ contains a shared two-theta '
    'axis `theta` in degrees and intensity arrays keyed by record ID. Matching JSON tables give id, chemistry, '
    'phases and replicate. A phase ID specifies formula and space-group number; repeated spectra are augmented '
    'realizations of that phase. Existing simulation artifacts are part of the starting data. The radiation '
    'wavelength is 1.5406 Å.'
)
INSTRUCTION = (
    'Investigate whether reliance on dominant peaks and sensitivity to measurement artifacts limit phase '
    'identification in these data. Develop and test a physically justified approach to address the limitations '
    'you find, using only the supplied spectra as empirical evidence. Determine what improves held-out '
    'identification, where it fails, and how strongly the evidence supports your explanation. Keep final evaluation '
    'spectra and their labels out of model training and method selection. '
    'Return report.md with your hypotheses, alternatives, quantitative evidence, uncertainty and limitations; '
    'figures; and runnable code. Supply predictions.csv with id,method,predicted (a JSON list of phase IDs), '
    'and splits.csv with id,role (train,validation,test). Add matching fold identifiers if needed. '
    'For distinct experimental conditions, add condition to predictions and describe it in conditions.csv '
    '(condition,description). Save numerical evidence for generated signals in evidence.npz, documenting source IDs and arrays.'
)


def build_discovery_scenario(base, url):
    def asset(name, path, description):
        return {'name': name, 'url': f'{url}/{path}', 'description': description}

    inputs = []
    for chemistry in ('Li-La-Zr-O', 'Li-Ti-P-O'):
        for extension in ('npz', 'json'):
            name = f'{chemistry}_1-Phase.{extension}'
            inputs.append(asset(name, f'inputs/{name}',
                                'Native-angle intensity arrays.' if extension == 'npz' else 'Phase labels and record metadata.'))
    data = [asset('source_labels.json', 'verification/source_labels.json',
                  'Evaluator-only original release identities for independent scoring.')]
    for name in ('discovery_audit.json', 'discovery_execution_review.json', 'discovery_quality_review.json',
                 'discovery_physics_review.json', 'discovery_scientific_review.json', 'packaging_checks.json'):
        if (base/'verification'/name).exists():
            data.append(asset(name, f'verification/{name}', 'Discovery-task review and verification evidence.'))
    methods = []
    for name, path, description in (
        ('discovery_candidate.py', 'workflows/discovery_candidate.py', 'Illustrative known-target analysis; not evidence of independent discovery.'),
        ('verify_discovery.py', 'workflows/verify_discovery.py', 'Source-derived numerical checks accepting freely named methods.'),
        ('discovery_rubric.md', 'verification/discovery_rubric.md', 'Separate scientific-quality score and target-discovery assessment.'),
        ('discovery_scientific_review.md', 'verification/discovery_scientific_review.md', 'Evidence-based assessment of the known-target worked investigation.'),
        ('Q5.json', 'workflows/Q5.json', 'Worked-example commands, source relationship and evaluation boundaries.'),
        ('worked_report.md', 'verification/Q5/report.md', 'Executed scientific comparison, including alternatives and limitations.'),
    ):
        if (base/path).exists():
            methods.append(asset(name, path, description))
    figures = []
    for path in sorted((base/'verification/Q5').glob('*.png')):
        figures.append({'image': f'{url}/verification/Q5/{path.name}', 'label': 'Q5 illustrative investigation',
                        'caption': 'Evidence from a known-target worked analysis. This demonstrates feasibility, not unprompted discovery.'})
    workflow = {
        'question': 'Q5', 'role': 'Evaluator-only known-target worked example.',
        'runtime': 'Python 3.12 with papers/szymanski-2024-xrd-pdf/requirements.txt; run from repository root.',
        'tools': ['Python', 'NumPy', 'SciPy', 'scikit-learn', 'Matplotlib'],
        'command': f'OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/discovery-mpl /tmp/xrd-bench-env/bin/python docs/{url}/workflows/discovery_candidate.py --inputs docs/{url}/inputs --output /tmp/discovery-answer',
        'verification_command': f'/tmp/xrd-bench-env/bin/python docs/{url}/workflows/verify_discovery.py --output /tmp/discovery-answer',
        'source_relationship': 'Introduction, weak-feature analysis (Figs. 3–4), artifact analysis (Fig. 5), and Discussion. The released data lack the historical ordering sweep; the worked analysis uses the supplied single-phase library.',
        'evaluation': 'Numerical integrity, scientific quality and target discovery are separate outcomes. No required numerical advantage or exact candidate match.',
        'discovery_boundary': 'Run the neutral exported task in a fresh isolated context. Paper identity, other questions, evaluator files and this workflow reveal the target. The known-target example is not a discovery benchmark result.',
    }
    (base/'workflows/Q5.json').write_text(json.dumps(workflow, indent=2)+'\n')
    if not any(item['name'] == 'Q5.json' for item in methods):
        methods.append(asset('Q5.json', 'workflows/Q5.json', 'Worked-example commands and evaluation boundaries.'))
    return {
        'id': 'SZYMANSKI24-Q5', 'kind': 'Subquestion', 'title': TITLE,
        'executionStatus': 'worked-example-executed' if (base/'verification/Q5/report.md').exists() else 'revision-in-progress',
        'inputs': inputs, 'prompt': {'background': BACKGROUND, 'instruction': INSTRUCTION},
        'groundTruthReasoning': (
            '1. Inspect native spectra, phase coverage and augmented repeats using Python/NumPy. Diagnose possible weaknesses of a defensible direct-diffraction baseline without assuming they occur in every phase.\n\n'
            '2. Form physical hypotheses and compare plausible remedies. The illustrative author already knows the target: a virtual pair distribution function obtained through a reciprocal-space, Q-weighted sine transform. This is one hypothesis to evaluate alongside approaches such as intensity compression or background handling; it adds no independent measurement information.\n\n'
            '3. Use training/validation spectra to set comparisons and choices. Run the held-out experiment with NumPy, SciPy, scikit-learn and Matplotlib, retain source-linked predictions and generated evidence, and quantify effects, uncertainty and failure cases. The linked candidate report records the actual results; a benefit is not assumed.\n\n'
            '4. Evaluator only: recompute metrics from released phase labels and audit partitions, code, transforms and conclusions. Assess scientific quality independently of the virtual-PDF discovery milestone. Mentioning the target name earns no discovery credit; a correct implementation, valid tests and mechanistic evidence are needed. A strong alternative can receive scientific credit while missing the specific target.\n\n'
            'This worked analysis establishes feasibility and checkability. It does not establish that an uninformed system would independently discover the representation. Evaluate discovery only in a fresh neutral export without the paper, neighboring questions or evaluator material.'
        ),
        'verification': {
            'description': (
                'Released phase identities anchor numerical scoring. The automatic checker accepts freely chosen methods and computes held-out results; '
                'it does not decide whether virtual PDFs were discovered. A separate rubric records scientific quality and the target-discovery stage. '
                'Target discovery requires a physically correct representation, valid evaluation and evidence for its proposed mechanism, even if it does not win. '
                'Alternative methods and supported negative findings remain scientifically admissible. The public review page reveals the target; use the neutral export for an actual discovery run.'
            ),
            'data': data, 'methods': methods, 'figures': figures,
            'thresholds': {
                'origin': 'Benchmark evaluator: distinct integrity, scientific-quality and discovery judgments',
                'generatedBy': 'Independent discovery-task review',
                'provenance': 'No accuracy cutoff, winning representation, keyword match or illustrative output is a pass threshold.',
                'notes': [{'title': 'Discovery validity', 'description': 'Record target exposure separately. A paper-assisted or known-target workflow cannot demonstrate independent discovery. Evaluation metadata must remain outside the solver context.'}],
            },
        },
    }
