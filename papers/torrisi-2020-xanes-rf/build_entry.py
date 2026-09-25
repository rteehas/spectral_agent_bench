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
BACKGROUND=('The gzip JSONL files contain computed K-edge spectra for oxygen-containing compounds. E is photon energy in eV and mu is absorption on a 100-point grid. {labels} Null means unavailable. source_row identifies a record within its element. metadata.id identifies the material when available; metadata.origin labels the data source. These are processed spectra. ')
TARGETS={'Q1':['coord'],'Q2':['md'],'Q3':['bader'],'Q4':['coord','md','bader'],'Q5':['coord','md']}
LABELS={'coord':'coordination is coordination number',
        'md':'avg_nn_dists is mean neighbor distance in Å',
        'bader':'bader is charge in electron-charge units, not formal oxidation state'}
DESIGN=('Base predictions on the supplied spectra. Choose and justify your analysis and evaluation. Support your conclusions with quantitative evidence, uncertainty and limitations. ')
OUTPUT=('Return report.md, diagnostic figures and runnable code, plus predictions.csv and partitions.csv containing test predictions and training/validation/test membership. Identify records by element and source_row, and distinguish models, properties and evaluation splits where needed.')
TASKS=[
('Q1','Can K-edge spectra reliably identify uncommon coordination environments?','',
 'Across all eight elements, determine whether coordination numbers 4, 5 and 6 can be identified reliably for uncommon environments, and whether class-imbalance treatment improves that reliability without concealing failures elsewhere. Distinguish rare-class performance from aggregate success and establish how robust the conclusion is to the evaluation design. ',
 'Coordination prediction and imbalance analysis associated with Fig. 3/Table 1. Evaluation design is left to the solver.'),
('Q2','When does inference of mean neighbor distance from K-edge spectra become unreliable?','',
 'Across all eight elements, determine how reliably mean nearest-neighbor distance can be inferred from spectra, particularly for unusually short or long environments. Identify regimes in which error or systematic bias undermines the inference and assess the stability of your conclusions. ',
 'Distance regression and error structure associated with Fig. 6. The solver defines and validates unusual-environment regimes.'),
('Q3','How much reproducible charge information lies beyond white-line position?',
 'White-line position means the photon energy of maximum absorption. ',
 'Across all eight elements, assess the incremental information about Bader charge carried by the full spectrum beyond white-line position. Quantify the strength and uncertainty of that evidence, including cases where the data do not support an improvement. ',
 'Charge/white-line relationships associated with Figs. 8–9; predictive comparison extends the source analysis.'),
('Q4','Can multiscale spectral shape support accurate and interpretable local-property inference?',
 'A multiscale shape representation describes local spectral behavior over more than one energy-interval size; its construction is part of the task. ',
 'Develop a multiscale spectral-shape representation and assess it against pointwise absorption for coordination numbers 4, 5 and 6, mean neighbor distance and Bader charge across all eight elements. Determine whether useful predictive information is preserved and which property-specific energy and shape associations are supported by held-out evidence. Test the reliability of the interpretation, beyond reporting an importance ranking, and identify conclusions that depend on representation or modeling choices. ',
 'Multiscale spectral descriptors and interpretation associated with Figs. 2–5, 7 and 9. Representation, learner and corroboration experiment remain research choices.'),
('Q5','Which spectral interpretations survive removal of absolute intensity scale?','',
 'For coordination numbers 4, 5 and 6 and mean neighbor distance across all eight elements, determine which conclusions about predictive information and its energy-localized signatures survive division of each spectrum by its own maximum. Distinguish normalization effects from model-fitting and sample-selection variability, and assess whether similar prediction quality supports the same scientific interpretation. ',
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
    for q,title,extra,instruction,source in TASKS:
        targets=TARGETS[q]
        background=BACKGROUND.format(labels='Labels: '+'; '.join(LABELS[t] for t in targets)+'.')
        inputs=[link(f'{e}.jsonl.gz',f'inputs/{e}.jsonl.gz',f'Released {e} spectra and labels, with record numbers, available material IDs and source labels.') for e in ELEMENTS]
        example=DATA/'verification'/q
        workflow=dict(question=q,source_derivation=source,
            illustrative_analysis=OPERATIONS[q],
            illustrative_design='Inspect source labels, material IDs and target availability; use available-ID material groups with two approximately 60/20/20 train/validation/test holdouts; train ExtraTrees with 80 trees and validation-selected leaf size 1 or 5. Report conditional group-bootstrap intervals, training-only baselines and source-selection limits. These are example choices only.',
            executed_finding=worked_finding(q,example),
            solver_input_boundary='Only the standalone prompt and eight input files. Evaluator materials and the review site must be inaccessible during a benchmark attempt.',
            status='executed_example' if (example/'report.md').exists() else 'candidate_execution_pending',
            commands=[
              dict(tool='Python environment',command='python3 -m venv /tmp/xanes-bench-env\n/tmp/xanes-bench-env/bin/python -m pip install -r papers/torrisi-2020-xanes-rf/requirements.txt',purpose='Install the numerical runtime.'),
              dict(tool='Python / NumPy / scikit-learn / Matplotlib',command=f'OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/candidate.py {q} --inputs docs/{BASE}/inputs --output /tmp/xanes-answer/{q}',purpose='Execute one worked research design; its choices are examples, not solver requirements.'),
              dict(tool='Independent numerical evaluator',command=f'/tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/verify.py {q} --inputs docs/{BASE}/inputs --output /tmp/xanes-answer/{q}',purpose='Check record identities, data partitions, prediction coverage and numerical consistency. Does not award scientific acceptance.'),
              dict(tool='Scientific review',command=f'Review report, code and evidence using docs/{BASE}/verification/scientific_review_rubric.md',purpose='Judge leakage prevention, uncertainty, fairness and whether evidence supports the conclusions; rerun code to confirm how the predictions were produced.')],
            notes='A valid alternative can use different representations, learners, filters, splits and random seeds and reach different or null findings. Historical v1 outputs are archived, not acceptance targets.')
        (DATA/'workflows'/f'{q}.json').write_text(json.dumps(workflow,indent=2,ensure_ascii=False)+'\n')
        methods=[link('Worked workflow',f'workflows/{q}.json','Evaluator-only reproducible example, not part of the prompt.'),link('candidate.py','workflows/candidate.py','One executable research design.'),link('verify.py','workflows/verify.py','Checks record identities, data partitions and numerical results without requiring a fixed study design.'),link('Scientific rubric','verification/scientific_review_rubric.md','Mandatory review beyond numerical integrity.'),link('Question review','verification/question_quality_review.json','Independent difficulty and standalone-prompt review.')]
        for name in ['candidate_execution.json','lean_verification_v3.json','lean_output_execution_review.json','flexible_verification_v2.json','workflow_execution_review.json','scientific_review.json','scientific_review_q1_q2.json','worked_q2_execution_v2.json','scientific_probes_q3_q5_v2.json','independent_q3_review_v2.json']:
            if (DATA/'verification'/name).exists():methods.append(link(name,f'verification/{name}','Historical v2 checker audit; superseded by the lean v3 check.' if name=='flexible_verification_v2.json' else 'Recorded independent review evidence.'))
        data=[link('provenance.json','provenance.json','Raw-release URLs, hashes and lossless projection audit.'),link('source_anchor_audit.json','verification/source_anchor_audit.json','Historical independent checks against released arrays; its splits are not required.'),link('source_map.json','verification/source_map.json','Evaluator-only derivation and source locations.')]
        for name in ['pointwise_table_feff.csv','poly_table_feff.csv','pointwise_table_max.csv','poly_table_max.csv']:
            data.append(link(name,f'verification/published/{name}','Author-released contextual result; differing study designs need not match these values.'))
        for name in ['report.md','design.json','metrics.csv','predictions.csv','partitions.csv','evidence.json','comparisons.csv','regimes.csv','class_counts.csv','confusion.csv','feature_definitions.json','localization.json','shape_families.csv']:
            if (example/name).exists():data.append(link(name,f'verification/{q}/{name}','Executed illustrative result, not a numerical acceptance target.'))
        figures=[]
        for filename,caption in [('diagnostics.png','Prediction scores and sensitivity across material holdouts.'),('paired_effects.png','Paired effects with conditional material-bootstrap intervals; positive favors the condition named in the plot.'),('regime_errors.png','Distance error and signed bias in training-defined regimes.'),('localization.png','Heldout feature-group permutation effects; midpoint bins are not full feature support.')]:
            if (example/filename).exists():figures.append(dict(image=f'{BASE}/verification/{q}/{filename}',label=f'{q} '+filename,caption=caption+' Generated by the illustrative workflow, not copied from the article.'))
        reasoning=('Inspect the released spectra, labels, material IDs and data-source labels, then choose and justify eligibility, representations, learners and evaluation. Fit the question’s comparison conditions with a defensible evaluation design, quantify uncertainty and investigate sensitivity. The example holds out material IDs; other designs are judged against their stated scientific claims. Save row-level predictions and partitions so scores can be independently reconstructed from raw labels. Inspect task-specific evidence using the scientific rubric; published plots and tables supply context, not fixed score targets. The worked workflow documents one executable choice, which does not constrain independent solutions. Source derivation: '+source)
        scenarios.append(dict(id='TORRISI20-'+q,kind='Subquestion',executionStatus=workflow['status'],title=title,inputs=inputs,prompt=dict(background=background+extra,instruction=instruction+DESIGN+OUTPUT),groundTruthReasoning=reasoning,
            verification=dict(description='Reconstruct truth from released labels; check record identities, training/test separation and prediction coverage, and calculate scores. Report shared material IDs and missing IDs so the reviewer can assess the claimed evaluation scope. Check explicitly declared pairing or material separation when provided. Then require scientific review of executable code, experimental design and evidence. Arithmetic success alone is not scientific acceptance. Negative results are valid; no agreement with one model or reference prediction is required.',data=data,figures=figures,methods=methods,
                thresholds=dict(origin='Benchmark-defined',generatedBy='Model-generated',provenance='Only numerical serialization tolerances apply to recomputed metrics. Scientific adequacy is judged against the rubric, without reference-score or feature-ranking cutoffs.',notes=[dict(title='Two-part evaluation',description='Numerical integrity and scientific review are separate. Independently rerun code; self-consistent predictions may otherwise be copied labels or fabricated.')],data=[]))))
    paper=dict(id=ID,title='Random forest machine learning models for interpretable X-ray absorption near-edge structure spectrum-property relationships',authors='Steven B. Torrisi et al. (2020)',doi='10.1038/s41524-020-00376-6',category='Transition-metal K-edge XANES structure–property inference',facility='Materials Project / OQMD / FEFF9',pdf='https://www.nature.com/articles/s41524-020-00376-6.pdf',dataUrl='https://data.matr.io/4/',codeUrl='https://github.com/TRI-AMDD/trixs/tree/6dbcc598c7bea235f464bed91744c1617725b7a8',scenarios=scenarios)
    (HERE/'paper.json').write_text(json.dumps(paper,indent=2,ensure_ascii=False)+'\n')
    path=ROOT/'docs/data/benchmark.json'
    dataset=json.loads(path.read_text())
    dataset['papers']=[paper if p['id']==ID else p for p in dataset['papers']]
    if not any(p['id']==ID for p in dataset['papers']):dataset['papers'].append(paper)
    for suffix in ['-torrisi-research-v2','-torrisi-prompts-v3']:
        if dataset['datasetId'].endswith(suffix):dataset['datasetId']=dataset['datasetId'][:-len(suffix)]
    dataset['datasetId']+='-torrisi-prompts-v3'
    path.write_text(json.dumps(dataset,indent=2,ensure_ascii=False)+'\n')
if __name__=='__main__':build()
