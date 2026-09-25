#!/usr/bin/env python3
"""Build the review entry without replacing other papers or fictional examples."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ID='torrisi-2020-xanes-rf'
BASE=f'data/{ID}'
PUBLIC=ROOT/'docs'/BASE
ELEMENTS=['Ti','V','Cr','Mn','Fe','Co','Ni','Cu']

PROTOCOL={
 'scope':'Eight independent element-specific models; spectral inputs only as features. Labels and metadata must not be included in feature matrices.',
 'quality_control':{
  'eligibility':'Keep a row if coordination is 4, 5 or 6, or bader is non-null and nonzero.',
  'unphysical':'Exclude if the final mu equals the global maximum, maximum mu exceeds 3, or a global maximum occurs among the first 10 samples.',
  'fit_fidelity':'Divide mu by its maximum. Fit a degree-3 polynomial separately to each of 20 consecutive nonoverlapping 5-sample blocks, using local coordinates spanning [-1,1]. Exclude a spectrum if any block sum of absolute residuals exceeds 0.1.',
  'targets':{'coord':'coordination in {4,5,6}', 'md':'coordination in {4,5,6} and nn_min-max is not null; label avg_nn_dists in angstrom', 'bader':'non-null, nonzero bader; label in electron-charge units'}},
 'splitting':{'order':'Preserve source-row order after quality control and target selection.',
  'method':'scikit-learn train_test_split with test_size=0.1, random_state=42, shuffle=True, stratify=None; then apply the same call to the remaining training indices to reserve validation. This gives approximately 81/9/10. Reserve validation; do not fit on it.',
  'pairing':'Use identical target-specific train/validation/test row IDs for every paired representation, normalization and balancing comparison.'},
 'representations':{
  'pointwise':'The 100 supplied mu values, in energy order.',
  'peak':'The zero-based index of the first maximum of mu. Within one element, the grid is fixed, so energy and index are equivalent monotone encodings.',
  'poly':'Partition the 100 samples into 4, 5, 10 and 20 contiguous equal-sized blocks. Fit a cubic to each block in local coordinates spanning [-1,1], yielding 156 coefficients a0..a3. Add the first maximum index. Blocks do not overlap within a scale, but scales overlap. Sort coefficient labels lexicographically as loc:all,deg:3,fraction_size:N,chunk:j,coef:d, then append peak.'},
 'normalizations':{'feff':'Use supplied mu values without additional endpoint rescaling.', 'max':'Divide each spectrum by its own maximum before constructing features.'},
 'forest':{'trees':100,'seeds':[42,43,44],'max_depth':35,'max_features':{'pointwise':8,'poly':30,'peak':1},
  'classification':'RandomForestClassifier; criterion=gini, bootstrap=True, min_samples_leaf=1, min_samples_split=2, class_weight=None.',
  'regression':'RandomForestRegressor; criterion=squared_error, bootstrap=True, min_samples_leaf=1, min_samples_split=2.',
  'oversampling':'For balanced coordination runs only: retain original training order, then use numpy RandomState(42) to append replacement samples of each class in sorted class order until all classes equal the largest training class. Never oversample validation/test.',
  'settings':'Q1: coordination pointwise/feff with and without oversampling. Q2: distance pointwise/feff. Q3: Bader pointwise and peak/feff. Q4: all three targets, pointwise and poly/feff, balanced coordination. Q5: coordination and distance, pointwise and poly, feff and max, balanced coordination.'},
 'metrics':{'coord':'accuracy, F1 for classes 4/5/6, unweighted macro-F1; baseline predicts the training-set modal class.',
  'regression':'R2 and MAE; baseline predicts the training-target mean.',
  'tails':'For all regression output records, low/high tails use the training-target 10th/90th quantiles, inclusive. On test rows in each tail report count, MAE and mean(prediction-label). These common diagnostics are the focus of the distance question.',
  'aggregation':'Mean and population standard deviation (ddof=0) across the three seeds; no pooling before computing nonlinear metrics.',
  'attribution':'Mean impurity feature_importances_ across seeds. Report polynomial degree-family sums, separate peak importance, and top 12 features with energy intervals. Q5 compares matched representations with Spearman correlation of mean importance and Jaccard overlap of the top-12 feature sets.'},
 'outputs':{
  'common':'result.json (model settings, counts, per-seed aggregate metrics, baseline), splits.json (source_row lists by element_target), predictions.csv (model_id,seed,source_row,y_true,y_pred), importances.csv (model_id,seed,feature_index,importance), feature_metadata.json (element_representation -> feature index,label,degree,parts,chunk,energy_lo,energy_hi), plot.png, diagnostics.png, conclusion.md.',
  'specific':'Q1 confusion.csv and comparisons.csv. Q3 comparisons.csv. Q4/Q5 comparisons.csv, ranked_features.csv and coefficient_families.csv.',
  'model_id':'element_target_representation_normalization_balanced-or-natural; e.g. Ti_coord_pointwise_feff_balanced.',
  'schema':'The evaluator canonical JSON/CSV schema is in output_schema.json. Equivalent independently implemented calculations are acceptable; submit the canonical fields for automatic screening.'}
}

SCHEMA={
 'result.json':{'question':'Q1..Q5','models':[{'id':'model_id','element':'Ti..Cu','target':'coord|md|bader','representation':'pointwise|poly|peak','normalization':'feff|max','balanced':'boolean','train_count':'before oversampling','fit_count':'after oversampling','valid_count':'integer','test_count':'integer','seeds':[42,43,44],'metrics_mean':'metric -> numeric','metrics_std':'metric -> numeric','baseline':'coord: train_mode,accuracy,train_class_counts; regression: train_mean,mae,r2','tail_thresholds':'regression: low,high'}], 'preprocessing':'element -> raw,ineligible,unphysical,polynomial_rejected,retained','protocol':'seeds,n_estimators,max_depth,split_seed,split','versions':'python,numpy,sklearn'},
 'metrics_keys':{'coord':['accuracy','macro_f1','f1_4','f1_5','f1_6'],'regression':['r2','mae','low_count','low_mae','low_bias','high_count','high_mae','high_bias']},
 'splits.json':'element_target -> train,valid,test lists of source_row integers before oversampling',
 'coefficient_families.csv':['model_id','degree_0','degree_1','degree_2','degree_3','peak','peak_rank'],
 'ranked_features.csv':['model_id','rank','importance','label','degree','parts','chunk','energy_lo','energy_hi','index'],
 'comparisons.csv':{'Q1':['element','delta_macro_f1','accuracy_gain_over_mode'],'Q3':['element','delta_r2','mae_reduction'],'Q4':['element','target','metric','pointwise','poly','delta'],'Q5':['element','target','representation','metric','delta','importance_spearman','top12_jaccard']},
 'confusion.csv':['element','true_class','predicted_class','mean_count'],
 'field_definitions':{
  'comparisons':'Q1 delta_macro_f1 = balanced minus natural; accuracy_gain_over_mode = balanced accuracy minus training-mode baseline. Q3 delta_r2 = full minus peak; mae_reduction = peak minus full. Q4 delta = polynomial minus pointwise. Q5 delta = maximum normalization minus supplied normalization. Coordination comparison metric is macro_f1; regression is r2.',
  'confusion':'Use only balanced coordination models; mean_count is the cell count averaged across three seeds, not row-normalized.',
  'feature_metadata':'Pointwise feature i: label=mu_i, degree=-1, parts=0, chunk=i, energy_lo=energy_hi=E[i]. Peak: label=peak, degree=-1, parts=0, chunk=0, energy_lo/hi are the full descriptor domain bounds, not an observed peak position. Polynomial: degree=d, parts=N, chunk=j, energy_lo/hi are first/last sampled energy in that block. Feature indices follow the protocol ordering.',
  'ranks':'Rank mean impurity importance using numpy.argsort(-mean_importance) with default sorting; ranks start at 1. Top-12 sets use these indices, including peak if selected.',
  'tail_thresholds':'Coordination records use an empty object. Regression records use low/high training quantiles.',
  'paired_variability':'Comparison CSVs contain mean paired changes. Per-model metrics_mean and metrics_std describe seed variability; they are not the standard deviation of a paired difference.'},
 'nonfinite':'Do not emit NaN or infinity. Use null only for genuinely empty tail groups and explain them.'
}

TASKS=[
 ('Q1','Does coordination-number prediction resolve rare environments as well as common ones?',
  'The coordination classification target is restricted to 4, 5 or 6, and their frequencies can differ by element. Overall classification accuracy can conceal poor recognition of rare coordination environments.',
  'Across Ti, V, Cr, Mn, Fe, Co, Ni and Cu, determine how much spectral prediction improves on a dominant-class baseline, and whether training-set oversampling helps the less common environments. Use the paired protocol. Report class distributions, held-out accuracy, per-class and macro-F1, seed variability, and confusion matrices. Explain which conclusions about rare environments are supported by the results.',
  'Coordination classification and class imbalance; anchored to released pointwise performance table and published Fig. 3. The paired no-oversampling ablation is a benchmark extension.'),
 ('Q2','How reliably do K-edge spectra determine mean neighbor distance, including unusually short or long environments?',
  'avg_nn_dists is the labeled mean nearest-neighbor distance in angstrom. Small overall error can hide systematic errors in the tails of its distribution.',
  'Determine the predictive accuracy of element-specific spectral models for mean nearest-neighbor distance across the eight elements. Compare with the training-mean baseline and quantify errors and signed bias in the short- and long-distance tails using the supplied protocol. Return parity plots, MAE and R² with seed variability, tail counts and diagnostics, and a conclusion about where the inferred distances are reliable.',
  'Distance regression and error localization; anchored to released distance labels/performance table and published Fig. 6. Quantile-based tail diagnostics are benchmark-defined.'),
 ('Q3','How much local-charge information do full spectra contain beyond white-line position?',
  'bader is a continuous released charge label, not a formal integer oxidation state. The white-line descriptor identifies the maximum absorption on the supplied energy grid.',
  'Compare matched full-spectrum and white-line-only models of Bader charge for each of the eight elements. Quantify out-of-sample R², MAE, improvements over the training-mean baseline, the mean paired change between representations, and seed variability for each model. Show charge parity plots and explain what the ablation supports about information beyond peak position, including its limitations.',
  'Charge regression and white-line interpretation; full-spectrum results anchored to released performance tables and published Figs. 8–9. Peak-only prediction is a new controlled ablation, not a published result.'),
 ('Q4','Can multiscale spectral-shape descriptors retain predictive accuracy while identifying local-property signatures?',
  'Pointwise features describe absorption at each energy. Cubic coefficients over several interval sizes separate local magnitude, slope and curvature; the supplied protocol defines the coordinate and ordering conventions.',
  'Compare pointwise and multiscale polynomial representations for coordination, mean neighbor distance and Bader charge across the eight elements, using paired data splits and the fixed settings specified for each representation. Quantify changes in predictive performance. Map the twelve most important polynomial features to coefficient degree and energy interval and summarize importance by degree and peak position. Use the evidence to assess whether the descriptors preserve predictive usefulness and which signatures distinguish the three properties; discuss limits of interpreting impurity importance.',
  'Representation design and feature interpretation; polynomial values anchored directly to released polynomial JSON, with performance and interpretation context in Figs. 3–5, 7, 9. Both representations balance coordination training for the controlled comparison.'),
 ('Q5','Which inferred spectral signatures are stable under intensity normalization?',
  'The supplied absorption and absorption divided by its maximum preserve peak position but differ in magnitude information. Model predictions and feature rankings may respond differently to that transformation.',
  'For coordination and mean neighbor distance across the eight elements, compare supplied and maximum-normalized spectra using both pointwise and polynomial representations with the paired protocol. Quantify performance changes, feature-rank correlation and top-feature overlap, and compare coefficient-family importance and energy-localized rankings. Explain which conclusions are stable under normalization and whether similar predictive performance can coexist with different attribution.',
  'Normalization as an interpretation control; anchored to released feff/max polynomial vectors and four published performance tables, with discussion/SI context. Rank-stability summaries are benchmark-defined.')
]

OPERATIONS={
 'Q1':('Fit matched natural-frequency and oversampled coordination classifiers. Compute training-mode baselines, class frequencies and per-class F1; average balanced-model confusion-cell counts across seeds. Compare balanced minus natural macro-F1 and balanced accuracy minus mode-baseline accuracy.', ['confusion.csv','comparisons.csv']),
 'Q2':('Fit distance regressors. Compute training-mean baselines and training-only 10th/90th target quantiles. Apply those cutoffs to held-out labels; compute tail counts, MAE and signed prediction-minus-label residuals. Plot seed-42 parity while reporting metrics across all seeds.', []),
 'Q3':('Fit full-spectrum and first-maximum-index Bader regressors on identical rows. Compute each model against the training-mean baseline. Pair full minus peak R² and peak minus full MAE; distinguish model seed variation from uncertainty in a paired difference.', ['comparisons.csv']),
 'Q4':('Construct polynomial coefficient vectors from spectra, retaining each scale, interval and degree. Fit paired pointwise/polynomial models for all three labels. Aggregate impurity importance across seeds, rank all 157 features, sum coefficient families and keep peak separate. Save twelve ranked features per condition and plot six for readability.', ['comparisons.csv','ranked_features.csv','coefficient_families.csv']),
 'Q5':('Repeat coordination and distance fits after per-spectrum maximum normalization, retaining the same row splits and random seeds. Pair max minus supplied scores within each representation. Recompute Spearman rank correlation and top-12 Jaccard from the two mean-importance vectors; compare polynomial degree-family totals and energy intervals.', ['comparisons.csv','ranked_features.csv','coefficient_families.csv'])}

def link(name,path,description):return dict(name=name,url=f'{BASE}/{path}',description=description)

def build():
    (PUBLIC/'inputs').mkdir(parents=True,exist_ok=True)
    for name,obj in [('protocol.json',PROTOCOL),('output_schema.json',SCHEMA)]:
        (PUBLIC/'inputs'/name).write_text(json.dumps(obj,indent=2)+'\n')
    scenarios=[]
    for q,title,background,instruction,derivation in TASKS:
        inputs=[link(f'{e}.jsonl.gz',f'inputs/{e}.jsonl.gz',f'All released {e} spectral rows; lossless projection of E, mu, labels and provenance with source_row.') for e in ELEMENTS]
        inputs += [link('protocol.json','inputs/protocol.json','Fixed comparison design, preprocessing conventions and compute budget; no fitted outputs or expected conclusions.'),link('output_schema.json','inputs/output_schema.json','Answer-format contract for numerical screening; no ground-truth values.'),link('README.md','inputs/README.md','Input field definitions and units.')]
        methods=[link(f'{q}_workflow.json',f'workflows/{q}.json','Worked tool sequence and execution evidence; evaluator-only.'),link('candidate.py','workflows/candidate.py','Executable candidate: loads only the input bundle.'),link('summarize.py','workflows/summarize.py','Task-specific comparisons, plots and scientific summary from candidate outputs.'),link('verify.py','workflows/verify.py','Independent evaluator: checks source-derived memberships/labels and output consistency.')]
        methods += [link('candidate_execution.json','verification/candidate_execution.json','Recorded independent execution, environment and final artifact checks.'),link('question_quality_review.json','verification/question_quality_review.json','Independent standalone-question and input-contract review.')]
        methods += [link('source_map.json','verification/source_map.json','Pinned notebook cell locations and evaluator-side paper-figure mapping.')]
        expected=PUBLIC/'verification'/q/'result.json'
        result_note='The executed numerical reference is stored in verification/'+q+'/result.json.'
        if expected.exists():
            d=json.loads(expected.read_text());score='macro_f1' if q=='Q1' else 'r2'
            chosen=[m for m in d['models'] if score in m['metrics_mean']]
            if chosen:result_note+=f' There are {len(d["models"])} element/target/representation conditions, each evaluated with three forest seeds.'
        conclusion=PUBLIC/'verification'/q/'conclusion.md'
        if conclusion.exists():
            paragraphs=[s for s in conclusion.read_text().split('\n\n') if s and not s.startswith('#')]
            result_note+=' Executed finding: '+' '.join(paragraphs[1:3])
        workflow=dict(question=q,source_derivation=derivation,solver_input_boundary='Only the eleven listed input files. Workflow code, ground truth, source paper and derived release arrays are evaluator/author material, not solver inputs.',
          commands=[
            {'tool':'shell/python venv + pip','command':'python3 -m venv /tmp/xanes-bench-env; /tmp/xanes-bench-env/bin/python -m pip install -r papers/torrisi-2020-xanes-rf/requirements.txt','purpose':'Install the recorded numerical runtime.'},
            {'tool':'Python gzip/json/NumPy/scikit-learn','command':f'OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/candidate.py {q} --inputs docs/{BASE}/inputs --output /tmp/xanes-answer/{q} --jobs 4','purpose':'Screen released spectra, construct paired splits and features, train fresh models, and write predictions, metrics, diagnostics and conclusion.'},
            {'tool':'Python evaluator','command':f'/tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/verify.py {q} --output /tmp/xanes-answer/{q}','purpose':'After completion, compare source-derived labels/memberships, recalculate scores and apply the benchmark comparison policy.'}],
          batch_command=f'OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/xanes-mpl /tmp/xanes-bench-env/bin/python docs/{BASE}/workflows/candidate.py ALL --inputs docs/{BASE}/inputs --output /tmp/xanes-answer --jobs 4',
          execution_record=f'{BASE}/verification/candidate_execution.json',verification_audit=f'{BASE}/verification/verification_audit.json',
          output_files=['result.json','splits.json','predictions.csv','importances.csv','feature_metadata.json','plot.png','diagnostics.png','conclusion.md']+OPERATIONS[q][1],
          question_specific_operations=OPERATIONS[q][0],
          notes='ALL reuses identical fits within that run. Each individual Q command is independently runnable and requires no answer from another question. Scientific conclusions and visual readability require human review after automated numeric checks.')
        (PUBLIC/'workflows'/f'{q}.json').write_text(json.dumps(workflow,indent=2)+'\n')
        reasoning=(f'1. Load the eight gzip JSONL input files using Python gzip and json, retaining source_row identifiers. Use NumPy to apply the declared eligibility, unphysical-spectrum and cubic-fit residual screens. The independent source audit checks this reconstruction against released arrays.\n\n'
          '2. Select the target labels and use scikit-learn train_test_split twice with seed 42. Retain disjoint training, validation and test identifiers; oversample only training coordination records in balanced conditions. Compute baselines and tail cutoffs from training labels.\n\n'
          '3. Build the representations required by the research question using NumPy. For polynomial descriptors, fit cubics on local [-1,1] coordinates at four partition sizes and retain coefficient metadata. The independently checked released coefficient vectors anchor this calculation.\n\n'
          '4. Train the specified fresh random forests using scikit-learn with 100 trees and seeds 42, 43, 44. Save every held-out prediction and impurity importance. Calculate scores separately per seed, then their mean and population standard deviation.\n\n'
          '5. Run summarize.py (called by candidate.py) with NumPy, SciPy and Matplotlib to produce the task-specific paired comparisons, diagnostics and conclusion. '+OPERATIONS[q][0]+' '+result_note+'\n\n'
          '6. Evaluator only: run verify.py against source_anchor_audit.json and held-back reference outputs. Check labels and test membership, recalculate metrics from predictions, validate paired differences and feature attribution summaries, and apply declared numerical tolerances. Inspect diagnostics.png and conclusion.md for scientific interpretation. Numerical success is not a substitute for that review.\n\n'
          'Provenance: '+derivation+' These are controlled benchmark reruns using a smaller forest budget and current software, not exact reproductions of published scores. See candidate_execution.json for independent execution and verification_audit.json for checker controls.')
        scenarios.append(dict(id='TORRISI20-'+q,kind='Subquestion',executionStatus='validated',title=title,inputs=inputs,
          prompt=dict(background='The inputs contain site-resolved computed K-edge spectra and labels for oxygen-containing compounds of eight transition metals. The spectra are the earliest released representation: 100-point processed absorption arrays, with missing labels marked null. '+background,
                      instruction=instruction+' Follow protocol.json and output_schema.json, and return a concise evidence-backed conclusion alongside the numerical files and plots.'),
          groundTruthReasoning=reasoning,
          verification=dict(description='Check the exact source-row split and labels against independently reconstructed released data; recompute reported scores from predictions and inspect the paired scientific comparisons. Compare model outputs with the held-back modern reference under the documented benchmark tolerances. Published tables provide contextual evidence rather than exact targets for the smaller training budget. Require plots and an evidence-backed conclusion; attribution is predictive association, not causation.',
            data=[link('result.json',f'verification/{q}/result.json','Held-back controlled-run numerical targets with version and model metadata.'),link('predictions.csv',f'verification/{q}/predictions.csv','Executed held-out predictions with source-row identities, target labels and seeds.'),link('importances.csv',f'verification/{q}/importances.csv','Executed feature importances with model, seed and feature indices.'),link('source_anchor_audit.json','verification/source_anchor_audit.json','Independent exact checks against 144 released pointwise arrays and sampled released polynomial coefficients.'),link('provenance.json','provenance.json','Source URLs, archive/member hashes and lossless input projection.'),link('verification_audit.json','verification/verification_audit.json','Independent checker positive and adversarial-control results.')]+[link(name,f'verification/published/{name}','Unmodified author-released numerical score table; contextual ground truth, not the smaller-forest reference.') for name in (['pointwise_table_feff.csv'] if q in ['Q1','Q2','Q3'] else ['pointwise_table_feff.csv','poly_table_feff.csv'] if q=='Q4' else ['pointwise_table_feff.csv','poly_table_feff.csv','pointwise_table_max.csv','poly_table_max.csv'])],
            figures=[dict(image=f'{BASE}/verification/{q}/diagnostics.png',label=f'{q} executed diagnostic',caption='Generated from the executed candidate and released spectral data; this is not an image copied from the article.')],
            methods=methods,
            thresholds=dict(origin='Benchmark-defined',generatedBy='Model-generated',provenance='The numerical screening tolerances are benchmark engineering choices, not paper-reported uncertainties. Three-seed spread estimates forest randomness only.',notes=[dict(title='Comparison policy',description='Use the evaluator policy for score, prediction and feature-importance tolerances. Exact data membership and labels are independently anchored to the release. Alternative scientific analyses require adjudication if they depart from the fixed comparison protocol.')],data=[link('comparison_policy.json','verification/comparison_policy.json','Evaluator numerical settings, provenance, and limitations.')]))))
    paper=dict(id=ID,title='Random forest machine learning models for interpretable X-ray absorption near-edge structure spectrum-property relationships',authors='Steven B. Torrisi et al. (2020)',doi='10.1038/s41524-020-00376-6',category='Transition-metal K-edge XANES structure–property inference',facility='Materials Project / OQMD / FEFF9',pdf='https://www.nature.com/articles/s41524-020-00376-6.pdf',dataUrl='https://data.matr.io/4/',codeUrl='https://github.com/TRI-AMDD/trixs/tree/6dbcc598c7bea235f464bed91744c1617725b7a8',scenarios=scenarios)
    (Path(__file__).parent/'paper.json').write_text(json.dumps(paper,indent=2)+'\n')
    dataset_path=ROOT/'docs/data/benchmark.json';dataset=json.loads(dataset_path.read_text())
    dataset['papers']=[p for p in dataset['papers'] if p['id']!=ID]+[paper]
    dataset['datasetId']='spectral-agent-v4'
    dataset_path.write_text(json.dumps(dataset,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':build()
