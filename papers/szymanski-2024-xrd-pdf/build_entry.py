#!/usr/bin/env python3
"""Build open research questions; analysis recipes remain evaluator-side only."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'docs/data/szymanski-2024-xrd-pdf'
URL = 'data/szymanski-2024-xrd-pdf'
CHEMS = ['Li-La-Zr-O', 'Li-Ti-P-O']

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

def asset(name, relative, description):
    return {'name': name, 'url': f'{URL}/{relative}', 'description': description}

PHYSICS = ('The radiation wavelength is 1.5406 Å. Here a virtual PDF is the uncorrected representation '
           'G(r)=(2/π)∫Q I(Q) sin(Qr)dQ, with Q=4π sin(θ)/λ and θ half the recorded angle; '
           'it is not a quantitatively normalized total-scattering PDF.')
SIM_FORMAT = ('Simulation NPZ files contain a shared two-theta axis `theta` in degrees and one native intensity array per record ID. '
              'The matching JSON tables give `id`, `chemistry`, and `phases`; single-phase records also have a native `replicate` index. '
              'Simulated phase IDs combine formula and space-group number. Repeated spectra are augmented realizations of those phases.')
OUTPUT = ('Return report.md with your scientific answer, methodological justification, uncertainty and limitations; '
          'diagnostic figures; and runnable analysis code. For numerical checking, supply predictions.csv with columns '
          'id,method,representation,condition,fold,predicted, where predicted is a JSON list of phase IDs '
          'and representation is XRD, PDF or Combined. Supply splits.csv with id,fold,role '
          '(train,validation,test; each fold records disjoint source-record partitions). '
          'Use consistent method/fold identifiers across comparisons. Supply metrics.csv with '
          'chemistry,group,method,representation,condition,fold,metric,value,n; n is the number of evaluated records. ')
QUESTIONS = [
    {
        'q': 'Q1',
        'title': 'Does diffraction representation offer a reproducible advantage for phase identification?',
        'background': SIM_FORMAT + ' ' + PHYSICS,
        'instruction': ('Determine whether XRD or virtual PDFs give more reliable phase identification in each chemistry, '
                        'and whether combining their information improves it. Establish how strongly your conclusion depends '
                        'on reasonable analysis choices and whether the two representations fail on the same cases. '
                        'Use genuinely held-out spectra; target labels and record IDs must not enter prediction as features. '
                        'Choose and justify the analysis and evaluation design. ' + OUTPUT +
                        'For Q1 use condition=baseline and group=all; report exact_match. '
                        'Include XRD, PDF and Combined predictions on the same held-out records within each fold.'),
        'kinds': ['1-Phase'],
        'chems': CHEMS,
        'source': ('Representation comparison and complementary errors in the single-phase part of Fig. 2. '
                   'The benchmark asks the solver to design the validation and assess sensitivity to analysis choices; '
                   'no historical CNN score or particular learner is a target.'),
        'solution': ('One candidate creates its own train/validation/test partitions, constructs both representations, '
                     'compares two learner families and selects combination settings using validation data. '
                     'It records held-out predictions, paired comparisons and uncertainty before drawing a scoped conclusion. '
                     'These are worked-example choices, not solver requirements.'),
    },
    {
        'q': 'Q2',
        'title': 'How reliably can diffraction data determine both the identities and number of phases in a mixture?',
        'background': SIM_FORMAT + ' Mixture spectra are pooled under opaque IDs. Their phase-label tables are for evaluation only; '
                      'constituent identities and counts are unavailable to the inference procedure. ' + PHYSICS,
        'instruction': ('Recover constituent identities and their number from the mixture spectra using the available single-phase data. '
                        'Compare XRD and virtual-PDF evidence, investigate disagreement and failure cases, and determine what '
                        'the results support about mixture complexity. Choose and justify any training, calibration and model-selection '
                        'procedures without using the released mixture labels until final evaluation; do not use the true phase count '
                        'to select predictions. Evaluate every released mixture. ' + OUTPUT +
                        'For Q2 use condition=baseline and group equal to the true phase count at scoring time; '
                        'report exact_match, micro_f1 and phase_count_accuracy. Each fold places all released mixtures in test '
                        'and uses only single-phase source records for training or validation. Include XRD and PDF predictions; '
                        'Combined predictions are optional.'),
        'kinds': ['1-Phase', 'Mixtures'],
        'chems': CHEMS,
        'source': ('Multiphase phase identification in Fig. 2 and iterative identification in Methods. '
                   'The v2 question removes the earlier supplied-cardinality shortcut. '
                   'The released mixture cohorts differ in component identities and amounts as well as count; '
                   'a causal explanation requires evidence beyond aggregate score differences.'),
        'solution': ('One candidate builds a reference library from a solver-chosen subset of single-phase spectra and fits '
                     'nonnegative contributions in each representation. It chooses support thresholds using newly generated '
                     'validation mixtures without reading released target labels, then infers variable-size phase sets for '
                     'all released mixtures. Other calibrated identification strategies are admissible.'),
    },
    {
        'q': 'Q3',
        'title': 'Which real-space interval preserves phase identification under noise and smooth background?',
        'background': SIM_FORMAT + ' These inputs cover the Li-Ti-P-O chemistry. Their existing simulation artifacts remain '
                      'part of the starting spectra. ' + PHYSICS,
        'instruction': ('Determine whether a real-space interval can make phase identification more robust to added measurement '
                        'noise and smooth background without sacrificing discrimination among phases. Design a controlled '
                        'investigation across the supplied phase library, establish whether the interval choice generalizes '
                        'beyond the cases used to select it, and quantify the robustness–discrimination tradeoff relative to XRD. '
                        'Choose and justify perturbations, severities, intervals and validation; changes in signal energy alone '
                        'do not establish phase-identification performance. ' + OUTPUT +
                        'For Q3 use group=all and report exact_match for clean and perturbed held-out spectra. '
                        'Use method to distinguish interval/model choices and condition to distinguish perturbations and trials; '
                        'provide conditions.csv with condition,artifact,description, where artifact is clean,noise or background. '
                        'Save the generated numerical perturbation evidence in evidence.npz and document its arrays in the report '
                        'so the experiment can be reconstructed. Include XRD and PDF predictions. Record IDs always refer to '
                        'the original spectrum, so every derivative of a test record stays out of training and selection.'),
        'kinds': ['1-Phase'],
        'chems': ['Li-Ti-P-O'],
        'source': ('Artifact localization and distance-range selection in Fig. 5 and Methods/Discussion. '
                   'The separated historical artifact dataset is unavailable. The solver generates a controlled experiment '
                   'from released raw baselines and must test predictive discrimination, extending the earlier energy-only task.'),
        'solution': ('One candidate chooses several real-space intervals and realistic added-noise/background levels, '
                     'trains phase classifiers on clean training data, and selects an interval using perturbed validation data. '
                     'It evaluates clean and perturbed held-out records, retains paired numerical evidence and compares '
                     'classification performance with signal distortion. Its intervals and perturbations are illustrative.'),
    },
    {
        'q': 'Q4',
        'title': 'Does virtual-PDF evidence improve detection of secondary phases in measured mixtures?',
        'background': SIM_FORMAT + ' Experimental NPZ entries are native two-column arrays (two-theta in degrees, intensity). '
                      'Their JSON labels give major and minor formulas and minor_weight_percent from sample preparation, '
                      'for scoring only. Experimental identities are evaluated at formula level, which does not distinguish polymorphs. '
                      'The candidate phases are the full supplied simulation library for that chemistry. ' + PHYSICS,
        'instruction': ('Identify the phases in the measured patterns using the simulation library and determine whether '
                        'integrating virtual-PDF evidence helps detect secondary phases as their abundance falls. '
                        'Assess missed and spurious phases, differences between chemistries and the strength of any '
                        'abundance-dependent conclusion. Choose and justify the transfer and validation strategy without '
                        'using experimental identities or abundances for fitting, tuning or candidate restriction. '
                        'Evaluate every experimental spectrum. ' + OUTPUT.replace('JSON list of phase IDs', 'JSON list of formulas') +
                        'For Q4 predicted contains formulas, condition=baseline, and group is the secondary weight percentage '
                        'as a string at scoring time; report exact_match, micro_f1 and minor_recall. Each fold places all '
                        'experimental records in test and uses only simulated single-phase records for training or validation. '
                        'Include XRD, PDF and Combined predictions.'),
        'kinds': ['1-Phase', 'Experiments'],
        'chems': CHEMS,
        'source': ('Transfer to measured specimens and secondary-phase abundance in Fig. 6. '
                   'The v2 question removes the four-formula shortlist. Formula-level preparation labels are independent '
                   'scoring anchors, but are not independent measurements of sample purity or a universal detection limit.'),
        'solution': ('One candidate calibrates full-library phase-support thresholds using simulated validation mixtures, '
                     'then evaluates raw experimental spectra after documented preprocessing. It combines polymorph evidence '
                     'at formula level and compares standalone/integrated inference using preparation labels only after '
                     'predictions are saved. Abundance-specific recall, false positives and uncertainty support the conclusion.'),
    },
]

def main():
    scenarios = []
    for spec in QUESTIONS:
        q = spec['q']
        inputs = []
        for chem in spec['chems']:
            for kind in spec['kinds']:
                stem = f'{chem}_{kind}'
                inputs.extend([
                    asset(stem+'.npz', 'inputs/'+stem+'.npz', 'Native-angle numeric spectra keyed by opaque record ID; no derived features.'),
                    asset(stem+'.json', 'inputs/'+stem+'.json', 'Raw phase/preparation labels and record metadata; no assigned split or analysis settings.'),
                ])
        evidence = [
            asset('source_labels.json', 'verification/source_labels.json', 'Evaluator-only original source paths and raw labels for independent scoring.'),
            asset('provenance.json', 'provenance.json', 'Source archive identity, raw-value projection and availability limits.'),
        ]
        for name in ['verification_audit.json', 'workflow_execution_review.json', 'question_quality_review.json',
                     'scientific_review.json', 'independent_candidate_evidence_review.json', 'packaging_checks.json']:
            if (BASE/'verification'/name).exists():
                evidence.append(asset(name, 'verification/'+name, 'Independent audit/review evidence for this open research revision.'))
        methods = [asset('candidate.py', 'workflows/candidate.py', 'One executed worked solution; model and numerical choices are not mandatory.'),
                   asset('verify.py', 'workflows/verify.py', 'Method-neutral submission-integrity checks and independent metric recomputation.'),
                   asset(q+'.json', 'workflows/'+q+'.json', 'Worked-example tool calls and source relationship.')]
        rubric = BASE/'verification/scientific_review_rubric.md'
        if rubric.exists():
            methods.append(asset(rubric.name, 'verification/'+rubric.name, 'Scientific validity and evidence rubric, separate from numerical integrity.'))
        for name in ['report.md', 'metrics.csv', 'design.json']:
            if (BASE/'verification'/q/name).exists():
                methods.append(asset('worked_'+name, f'verification/{q}/{name}', 'Illustrative worked-example output; not an exact answer key.'))
        figures = []
        if (BASE/'verification'/q/'diagnostics.png').exists():
            figures.append({'image':f'{URL}/verification/{q}/diagnostics.png','label':q+' worked-example diagnostics',
                            'caption':'An executed illustrative analysis. Alternative valid methods can produce different results. '+spec['source']})
        worked = ('1. Inspect the supplied native spectra and raw metadata using Python/NumPy; identify data support, class coverage '
                  'and appropriate evaluation units. Choose the analysis without reading evaluator references.\n\n'
                  '2. '+spec['solution']+'\n\n'
                  '3. Execute the candidate with NumPy, SciPy, scikit-learn and Matplotlib. Save prediction-level evidence, '
                  'source-record partitions, reported metrics, plots and a scientific report. The linked report records '
                  'the actual findings and limitations of this worked example.\n\n'
                  '4. Evaluator only: independently recover truth from the original release filenames, recompute metrics '
                  'from predictions, and check source partitions and artifact evidence. Do not compare a solver’s predictions '
                  'with the candidate’s exact outputs. Apply the scientific rubric to validity of design, physical handling, '
                  'uncertainty, reproducibility and the support for conclusions; a numerical integrity pass is not a research-quality pass.\n\n'
                  'Source relationship: '+spec['source'])
        scenarios.append({'id':'SZYMANSKI24-'+q,'kind':'Subquestion','executionStatus':'worked-example-executed' if figures else 'revision-in-progress',
                          'title':spec['title'],'inputs':inputs,'prompt':{'background':spec['background'],'instruction':spec['instruction']},
                          'groundTruthReasoning':worked,
                          'verification':{'description':'Ground truth is the released phase/preparation metadata. The checker recomputes metrics '
                                          'and checks numerical/evaluation integrity without requiring a particular model, split, normalization, '
                                          'score fusion, perturbation, interval or outcome. Scientific success requires the separate evidence rubric '
                                          'and review of runnable code, figures and conclusions. The worked solution is illustrative, not a prediction target.',
                                          'data':evidence,'methods':methods,'figures':figures,
                                          'thresholds':{'origin':'Benchmark evaluator: arithmetic checks and scientific rubric','generatedBy':'Independent verification review',
                                                        'provenance':'Numerical tolerances concern arithmetic consistency only. No historical or candidate performance number is a pass threshold.',
                                                        'notes':[{'title':'Scientific judgment','description':'Method choice and negative findings are allowed. '
                                                                  'Checks cannot prove absence of target-label leakage from outputs alone; inspect code and execution evidence. '
                                                                  'Alternative outcomes require evidence, not agreement with the worked example.'}]}}})
        workflow = {'question':q,'role':'Evaluator-only illustrative workflow; none of these choices is a solver requirement.',
                    'runtime':'Python 3.12 with the entry requirements; run from spectral_agent_bench root.',
                    'tools':['Python','NumPy','SciPy','scikit-learn','Matplotlib'],
                    'command':f'OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xrd-mpl /tmp/xrd-bench-env/bin/python docs/{URL}/workflows/candidate.py {q} --inputs docs/{URL}/inputs --output /tmp/xrd-answer/{q}',
                    'verification_command':f'/tmp/xrd-bench-env/bin/python docs/{URL}/workflows/verify.py --question {q} --output /tmp/xrd-answer/{q}',
                    'worked_approach':spec['solution'],'source_relationship':spec['source'],
                    'verification':'Independent metrics plus submission-integrity checks; scientific rubric required. No exact-reference matching.'}
        write(BASE/'workflows'/f'{q}.json',workflow)
    paper = {'id':'szymanski-2024-xrd-pdf','title':'Integrated analysis of X-ray diffraction patterns and pair distribution functions for machine-learned phase identification',
             'authors':'Nathan J. Szymanski, Sean Fu, Ellen Persson and Gerbrand Ceder (2024)','doi':'10.1038/s41524-024-01230-9',
             'category':'Powder XRD and virtual pair distribution functions','facility':'Simulated powder diffraction / laboratory Cu Kα XRD',
             'pdf':'https://www.nature.com/articles/s41524-024-01230-9.pdf','dataUrl':'https://doi.org/10.6084/m9.figshare.24043410.v1',
             'codeUrl':'https://github.com/njszym/XRD-AutoAnalyzer/tree/bf32082521e45c0fcf5cf9ae9bd1321e76bf9012','scenarios':scenarios}
    write(HERE/'paper.json',paper)
    path=ROOT/'docs/data/benchmark.json';dataset=json.loads(path.read_text())
    dataset['papers']=[p for p in dataset['papers'] if p['id']!=paper['id']]+[paper]
    dataset['datasetId']='spectral-agent-v1-20260925-szymanski-research-v2';write(path,dataset)

if __name__=='__main__':main()
