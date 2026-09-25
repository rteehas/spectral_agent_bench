#!/usr/bin/env python3
"""Build standalone research tasks; worked methods remain evaluator-only."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
ID='torrisi-2020-xanes-rf'
BASE=f'data/{ID}'
DATA=ROOT/'docs'/BASE
ELEMENTS=['Ti','V','Cr','Mn','Fe','Co','Ni','Cu']
BACKGROUND=('The gzip JSONL files contain computed K-edge spectra for oxygen-containing compounds. E is photon energy in eV and mu is absorption on a 100-point grid. {labels} Null means unavailable. source_row identifies a record within its element; metadata may contain its material id and origin. These processed spectra are the earliest released representation. ')
TARGETS={'Q1':['coord'],'Q2':['md'],'Q3':['bader'],'Q4':['coord','md','bader'],'Q5':['coord','md']}
LABELS={'coord':'coordination is coordination number (target=coord)',
        'md':'avg_nn_dists is mean neighbor distance in Å (target=md)',
        'bader':'bader is charge in electron-charge units, not formal oxidation state (target=bader)'}
DESIGN=('Choose and justify the data treatment, models and evaluation. Use spectra as predictors; labels and provenance are for evaluation and study design. Include an assessment on previously unseen identified materials, and state what incomplete provenance permits you to conclude about the rest of the collection. Support the answer with uncertainty and sensitivity evidence. ')
OUTPUT=('Return report.md, diagnostic figures and runnable analysis code in code/. For audit, supply design.json with question and a runs list containing run_id, element, target, condition, comparison_id and generalization (spectrum or identified_material). A comparison_id groups conditions sharing row inclusion and partition assignments in one evaluation repetition. Supply predictions.csv (run_id,source_row,y_pred; exactly one prediction per test record), partitions.csv (run_id,source_row,role; role is train, validation, test or excluded, accounting for every source row of that run’s element), and metrics.csv (run_id,metric,value). {metrics} Describe methodological choices and any additional evidence in formats you find appropriate. ')
COORD_METRICS='Report per-run accuracy, macro_f1 and f1_4/f1_5/f1_6 for coordination; macro_f1 averages F1 for classes 4/5/6, assigning zero to undefined F1.'
REGRESSION_METRICS='Report per-run mae and r2 for regression.'
TASKS=[
('Q1','Can K-edge spectra reliably identify uncommon coordination environments?','',
 'Across all eight elements, determine whether coordination numbers 4, 5 and 6 can be identified reliably for uncommon environments, and whether class-imbalance treatment improves that reliability without concealing failures elsewhere. Distinguish rare-class performance from aggregate success and establish how robust the conclusion is to the evaluation design. ',
 'Use condition=untreated or treated for the class-imbalance comparison; target=coord.',
 'Coordination prediction and imbalance analysis associated with Fig. 3/Table 1. Material-group evaluation and study-design sensitivity extend the source analysis.'),
('Q2','When does inference of mean neighbor distance from K-edge spectra become unreliable?','',
 'Across all eight elements, determine how reliably mean nearest-neighbor distance can be inferred from spectra, particularly for unusually short or long environments. Identify regimes in which error or systematic bias undermines the inference and establish whether the reliability assessment holds beyond the materials used to develop it. ',
 'Use condition=model and target=md. Provide machine-readable evidence for the regimes you analyze.',
 'Distance regression and error structure associated with Fig. 6. The solver defines and validates unusual-environment regimes.'),
('Q3','How much reproducible charge information lies beyond white-line position?',
 'White-line position means the photon energy of maximum absorption. ',
 'Across all eight elements, assess the incremental information about Bader charge carried by the full spectrum beyond white-line position. Quantify the strength and uncertainty of that evidence on unseen materials, including cases where the data do not support an improvement. ',
 'Use condition=full or white_line and target=bader.',
 'Charge/white-line relationships associated with Figs. 8–9; paired predictive comparison and material grouping extend the source analysis.'),
('Q4','Can multiscale spectral shape support accurate and interpretable local-property inference?',
 'A multiscale shape representation describes local spectral behavior over more than one energy-interval size; its construction is part of the task. ',
 'Develop a multiscale spectral-shape representation and assess it against pointwise absorption for coordination, mean neighbor distance and Bader charge across all eight elements. Determine whether useful predictive information is preserved and which property-specific energy and shape associations are supported by held-out evidence. Test the reliability of the interpretation, beyond reporting an importance ranking, and identify conclusions that depend on representation or modeling choices. ',
 'Use condition=pointwise or multiscale; include coord (classes 4/5/6), md and bader. Supply machine-readable feature/energy definitions and evidence testing the claimed associations.',
 'Multiscale spectral descriptors and interpretation associated with Figs. 2–5, 7 and 9. Representation, learner and corroboration experiment remain research choices.'),
('Q5','Which spectral interpretations survive removal of absolute intensity scale?','',
 'For coordination and mean neighbor distance across all eight elements, determine which conclusions about predictive information and its energy-localized signatures survive division of each spectrum by its own maximum. Distinguish normalization effects from model-fitting and sample-selection variability, and assess whether similar prediction quality supports the same scientific interpretation. ',
 'Use condition=released or unit_peak; include coord (classes 4/5/6) and md. Supply machine-readable localization and stability evidence.',
 'Normalization sensitivity discussed in the article and the four released score tables. Interpretation stability requires additional experiments.')]
OPERATIONS={
 'Q1':'Compare untreated versus class-weighted coordination models on paired material holdouts and record holdouts of the same identified cohort. Inspect training/test class support, per-class F1, confusion counts and conditional paired uncertainty.',
 'Q2':'Fit distance regressors, define short/middle/long regimes using training-distance quantiles, and compare signed errors and MAE with a training-median baseline, including material-bootstrap intervals.',
 'Q3':'Compare full absorption vectors with photon energy at maximum absorption using independently validation-selected nonlinear regressors. Estimate paired uncertainty on charge prediction differences.',
 'Q4':'Construct 51 quadratic coefficients over 10/20/50-point windows, compare with 100-point absorption for three properties, then perturb energy-midpoint groups and coefficient families on heldout data and measure stability across material partitions.',
 'Q5':'Cross two material holdouts with two fitting seeds; pair released and unit-peak spectra for coordination and distance. Compare predictive changes, heldout permutation effects and energy-region ranks against within-condition sampling/fitting variability.'}
def worked_finding(q,example):
    import statistics
    path=example/'evidence.json'
    if not path.exists():return 'Execution pending.'
    e=json.loads(path.read_text());pairs=[p for p in e['comparisons'] if p['generalization']=='identified_material']
    if q=='Q1':return f"Class weighting increases macro-F1 in {sum(p['gain']>0 for p in pairs)}/{len(pairs)} material comparisons; {sum(p['low']>0 for p in pairs)} conditional intervals are wholly positive. Per-class performance and support still determine rare-environment reliability."
    if q=='Q2':
        parts=[]
        for name in ['short','middle','long']:
            selected=[x for x in e['regimes'] if x['regime']==name]
            parts.append(f"{name}: mean MAE {statistics.mean(x['mae'] for x in selected):.4f} Å, mean bias {statistics.mean(x['bias'] for x in selected):+.4f} Å")
        return 'Descriptive mean over eight elements and two holdouts: '+'; '.join(parts)+'. Full regime support and uncertainty are in the example, not universal calibration targets.'
    if q=='Q3':return f"Full-spectrum charge MAE is lower in {sum(p['gain']<0 for p in pairs)}/{len(pairs)} paired holdouts; {sum(p['high']<0 for p in pairs)} conditional intervals favor full spectra. The inference is conditional on learner and identified source population."
    return f"Paired gains favor the second condition in {sum(p['gain']>0 for p in pairs)}/{len(pairs)} comparisons; {sum(p['low']>0 for p in pairs)} conditional intervals are wholly positive and {sum(p['high']<0 for p in pairs)} wholly negative. Interpret differences separately by target and element; similar scores do not prove equivalence or matching attribution."
def link(name,path,description):
    return dict(name=name,url=f'{BASE}/{path}',description=description)
def build():
    for name in ['protocol.json','output_schema.json','README.md']:
        (DATA/'inputs'/name).unlink(missing_ok=True)
    scenarios=[]
    for q,title,extra,instruction,contract,source in TASKS:
        targets=TARGETS[q]
        background=BACKGROUND.format(labels='Labels: '+'; '.join(LABELS[t] for t in targets)+'. ')
        metric_sentences=([COORD_METRICS] if 'coord' in targets else [])+([REGRESSION_METRICS] if any(t!='coord' for t in targets) else [])
        output=OUTPUT.format(metrics=' '.join(metric_sentences))
        inputs=[link(f'{e}.jsonl.gz',f'inputs/{e}.jsonl.gz',f'Released {e} spectra, labels and provenance, with source-row identifiers.') for e in ELEMENTS]
        example=DATA/'verification'/q
        workflow=dict(question=q,source_derivation=source,
            illustrative_analysis=OPERATIONS[q],
            illustrative_design='Audit provenance/label coverage; use available-ID material groups with two approximately 60/20/20 train/validation/test holdouts; train ExtraTrees with 80 trees and validation-selected leaf size 1 or 5. Report conditional group-bootstrap intervals, training-only baselines and source-selection limits. These are example choices only.',
            executed_finding=worked_finding(q,example),
            solver_input_boundary='Only the standalone prompt and eight input files. Evaluator materials and the review site must be inaccessible during a benchmark attempt.',
            status='executed_example' if (example/'report.md').exists() else 'candidate_execution_pending',
            commands=[
              dict(tool='Python environment',command='python3 -m venv /tmp/xanes-bench-env\n/tmp/xanes-bench-env/bin/python -m pip install -r papers/torrisi-2020-xanes-rf/requirements.txt',purpose='Install the numerical runtime.'),
              dict(tool='Python / NumPy / scikit-learn / Matplotlib',command=f'OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/candidate.py {q} --inputs docs/{BASE}/inputs --output /tmp/xanes-answer/{q}',purpose='Execute one worked research design; its choices are examples, not solver requirements.'),
              dict(tool='Independent numerical evaluator',command=f'/tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/verify.py {q} --inputs docs/{BASE}/inputs --output /tmp/xanes-answer/{q}',purpose='Audit source-label provenance, partitions, pairing and metric arithmetic. Does not award scientific acceptance.'),
              dict(tool='Scientific review',command=f'Review report, code and evidence using docs/{BASE}/verification/scientific_review_rubric.md',purpose='Judge leakage prevention, uncertainty, fairness and whether evidence supports the conclusions; rerun code to establish prediction provenance.')],
            notes='A valid alternative can use different representations, learners, filters, splits and random seeds and reach different or null findings. Historical v1 outputs are archived, not acceptance targets.')
        (DATA/'workflows'/f'{q}.json').write_text(json.dumps(workflow,indent=2,ensure_ascii=False)+'\n')
        methods=[link('Worked workflow',f'workflows/{q}.json','Evaluator-only reproducible example, not part of the prompt.'),link('candidate.py','workflows/candidate.py','One executable research design.'),link('verify.py','workflows/verify.py','Method-independent provenance and arithmetic checks.'),link('Scientific rubric','verification/scientific_review_rubric.md','Mandatory review beyond numerical integrity.'),link('Question review','verification/question_quality_review.json','Independent difficulty and standalone-prompt review.')]
        for name in ['candidate_execution.json','flexible_verification_v2.json','workflow_execution_review.json','scientific_review.json','scientific_review_q1_q2.json','worked_q2_execution_v2.json','scientific_probes_q3_q5_v2.json','independent_q3_review_v2.json']:
            if (DATA/'verification'/name).exists():methods.append(link(name,f'verification/{name}','Recorded independent review evidence.'))
        data=[link('provenance.json','provenance.json','Raw-release URLs, hashes and lossless projection audit.'),link('source_anchor_audit.json','verification/source_anchor_audit.json','Historical independent checks against released arrays; its splits are not required.'),link('source_map.json','verification/source_map.json','Evaluator-only derivation and source locations.')]
        for name in ['pointwise_table_feff.csv','poly_table_feff.csv','pointwise_table_max.csv','poly_table_max.csv']:
            data.append(link(name,f'verification/published/{name}','Author-released contextual result; differing study designs need not match these values.'))
        for name in ['report.md','design.json','metrics.csv','predictions.csv','partitions.csv','evidence.json','comparisons.csv','regimes.csv','class_counts.csv','confusion.csv','feature_definitions.json','localization.json','shape_families.csv']:
            if (example/name).exists():data.append(link(name,f'verification/{q}/{name}','Executed illustrative result, not a numerical acceptance target.'))
        figures=[]
        for filename,caption in [('diagnostics.png','Prediction scores and sensitivity across material holdouts.'),('paired_effects.png','Paired effects with conditional material-bootstrap intervals; positive favors the condition named in the plot.'),('regime_errors.png','Distance error and signed bias in training-defined regimes.'),('localization.png','Heldout feature-group permutation effects; midpoint bins are not full feature support.')]:
            if (example/filename).exists():figures.append(dict(image=f'{BASE}/verification/{q}/{filename}',label=f'{q} '+filename,caption=caption+' Generated by the illustrative workflow, not copied from the article.'))
        reasoning=('Audit raw fields and provenance, then choose and justify eligibility, representations, learners and an evaluation design. Reserve material groups before fitting or selecting models. Fit the question’s paired conditions using the same evaluation records, quantify uncertainty and investigate sensitivity. Save row-level predictions and partitions so scores can be independently reconstructed from raw labels. Inspect task-specific evidence using the scientific rubric; published plots and tables supply context, not fixed score targets. The worked workflow documents one executable choice, which does not constrain independent solutions. Source derivation: '+source)
        scenarios.append(dict(id='TORRISI20-'+q,kind='Subquestion',executionStatus=workflow['status'],title=title,inputs=inputs,prompt=dict(background=background+extra,instruction=instruction+DESIGN+output+f'Set question="{q}" in design.json. '+contract),groundTruthReasoning=reasoning,
            verification=dict(description='Reconstruct truth from released raw labels; check source rows, complete partition accounting, material-group disjointness, paired evaluation and reported metrics. Then require scientific review of executable code, experimental design and evidence. Arithmetic success alone is not scientific acceptance. Negative results are valid; no agreement with one model or reference prediction is required.',data=data,figures=figures,methods=methods,
                thresholds=dict(origin='Benchmark-defined',generatedBy='Model-generated',provenance='Only numerical serialization tolerances apply to recomputed metrics. Scientific adequacy is judged against the rubric, without reference-score or feature-ranking cutoffs.',notes=[dict(title='Two-part evaluation',description='Numerical integrity and scientific review are separate. Independently rerun code; self-consistent predictions may otherwise be copied labels or fabricated.')],data=[]))))
    paper=dict(id=ID,title='Random forest machine learning models for interpretable X-ray absorption near-edge structure spectrum-property relationships',authors='Steven B. Torrisi et al. (2020)',doi='10.1038/s41524-020-00376-6',category='Transition-metal K-edge XANES structure–property inference',facility='Materials Project / OQMD / FEFF9',pdf='https://www.nature.com/articles/s41524-020-00376-6.pdf',dataUrl='https://data.matr.io/4/',codeUrl='https://github.com/TRI-AMDD/trixs/tree/6dbcc598c7bea235f464bed91744c1617725b7a8',scenarios=scenarios)
    (HERE/'paper.json').write_text(json.dumps(paper,indent=2,ensure_ascii=False)+'\n')
    path=ROOT/'docs/data/benchmark.json'
    dataset=json.loads(path.read_text())
    dataset['papers']=[paper if p['id']==ID else p for p in dataset['papers']]
    if not any(p['id']==ID for p in dataset['papers']):dataset['papers'].append(paper)
    if not dataset['datasetId'].endswith('-torrisi-research-v2'):dataset['datasetId']+='-torrisi-research-v2'
    path.write_text(json.dumps(dataset,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':build()
