#!/usr/bin/env python3
"""Independent validation of the alternative Q3 study and its full code rerun."""
import argparse,gzip,hashlib,json,shutil
from pathlib import Path
import numpy as np
import pandas as pd

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--rerun',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--numeric-report',type=Path,required=True);a=p.parse_args()
    numeric=json.loads(a.numeric_report.read_text());assert numeric['numerical_integrity_pass'] and numeric['scientific_pass'] is None
    tables=[]
    for file in sorted(a.original.glob('*.csv')):
        other=a.rerun/file.name;assert other.exists(),file
        x,y=pd.read_csv(file),pd.read_csv(other);pd.testing.assert_frame_equal(x,y,check_exact=False,rtol=0,atol=1e-12)
        tables.append(dict(file=file.name,rows=len(x),agreement='all values, numeric atol1e-12'))
    diagnostic_count=0
    for file in sorted((a.original/'diagnostics').glob('*.csv')):
        pd.testing.assert_frame_equal(pd.read_csv(file),pd.read_csv(a.rerun/'diagnostics'/file.name),check_exact=False,rtol=0,atol=1e-12);diagnostic_count+=1
    assert (a.original/'report.md').read_text()==(a.rerun/'report.md').read_text()
    figures=[]
    for file in sorted((a.original/'figures').glob('*.png')):
        assert sha(file)==sha(a.rerun/'figures'/file.name);figures.append(file.name)
    roster=json.loads((a.original/'design.json').read_text())['runs'];prediction=pd.read_csv(a.original/'predictions.csv');comparisons=pd.read_csv(a.original/'comparisons.csv')
    raw={}
    for el in sorted({r['element'] for r in roster}):
        with gzip.open(a.inputs/(el+'.jsonl.gz'),'rt') as f:raw[el]={r['source_row']:r for r in map(json.loads,f)}
    independent=[]
    for cid,runs in pd.DataFrame(roster).groupby('comparison_id'):
        run=runs.iloc[0];source=raw[run.element]
        frames={condition:prediction[prediction.run_id==runs[runs.condition==condition].run_id.iloc[0]].set_index('source_row').sort_index() for condition in ['full','white_line']}
        ids=frames['full'].index.to_numpy();assert frames['full'].index.equals(frames['white_line'].index)
        truth=np.array([source[int(i)]['bader'] for i in ids]);groups=np.array([source[int(i)]['metadata']['id'] for i in ids]) if run.generalization=='identified_material' else np.array([f'row_{i}' for i in ids])
        ew=np.abs(truth-frames['white_line'].y_pred.to_numpy());ef=np.abs(truth-frames['full'].y_pred.to_numpy())
        group_errors=np.array([[ew[groups==g].mean(),ef[groups==g].mean()] for g in np.unique(groups)])
        difference=group_errors[:,0]-group_errors[:,1];rng=np.random.default_rng(int(run.seed));sample=difference[rng.integers(len(difference),size=(4000,len(difference)))].mean(1)
        actual=[group_errors[:,0].mean(),group_errors[:,1].mean(),difference.mean(),*np.quantile(sample,[.025,.975]),np.mean(sample<=0)]
        record=comparisons[comparisons.comparison_id==cid].iloc[0]
        wanted=[record.mae_white_material,record.mae_full_material,record.delta_material,record.ci_low,record.ci_high,record.fraction_bootstrap_nonpositive]
        np.testing.assert_allclose(actual,wanted,rtol=0,atol=1e-12)
        independent.append(dict(comparison_id=cid,raw_reconstruction_max_error=float(np.max(np.abs(np.array(actual)-wanted)))))
    shutil.copytree(a.original,a.destination,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(a.numeric_report,a.destination/'numerical_integrity_review.json')
    result=dict(status='scientific_pass_for_qualified_Q3_claim',reviewer='Independent flexible-verifier subagent',
                source='Separate input-only solver attempt, followed by independent full source execution and scientific review.',
                information_boundary=dict(solver_declared_task_specific_access='Only exported Q3 prompt and eight input files, plus installed numerical libraries.',os_enforced_isolation=False),
                numerical_integrity=dict(runs=numeric['run_count'],comparisons=numeric['comparison_count'],status=numeric['status']),
                full_rerun=dict(commands=['python code/analyze.py --inputs INPUT_DIRECTORY --output CLEAN_DIRECTORY --workers 2','python code/audit_and_summarize.py --inputs INPUT_DIRECTORY --output CLEAN_DIRECTORY','python code/write_report.py --output CLEAN_DIRECTORY'],
                                tables=tables,diagnostic_tables=diagnostic_count,identical_figures=figures,identical_report=True),
                independent_raw_pair_reconstruction=independent,
                scientific_criteria={
                    'source_execution':'satisfied: all128 fits/runs, all64 paired comparisons, diagnostic tables, uncertainty tables, figures and report regenerated; all scalar/cell outputs agree within1e-12.',
                    'feature_lineage_and_no_test_tuning':'satisfied: white-line predictor contains argmax photon energy only; full predictor contains100 raw absorption values plus deterministic white-line energy. All scalers and models fit training rows; six-candidate selection uses validation only; no test refit or test-driven candidate selection.',
                    'material_and_source_scope':'satisfied: raw metadata IDs remain partition-disjoint; unidentified rows excluded from primary runs. Report explicitly restricts claims to identified labeled scrape population, addresses source confounding, aliases and near-duplicates, and confines optional random-row results to spectrum claims.',
                    'fair_scientific_comparison':'satisfied: both conditions receive same candidate families and validation budget; matched test rows; nonlinear white-line models avoid a linear-only straw baseline. Material-weighted primary loss is distinguished from required spectrum-weighted metrics.',
                    'uncertainty_and_negative_evidence':'satisfied: five overlapping material resplits, per-split material bootstrap, fixed-first-split multiplicity sensitivity, model-family and normalization sensitivity. Report distinguishes conditional model-fixed intervals from training/population uncertainty and honestly reports unsupported Ni ridge gains.',
                    'supporting_artifacts_and_conclusion':'satisfied:64 paired comparisons independently rebuilt from raw labels and material identities, including interval endpoints; full source rerun reproduces family/multiplicity/coverage summaries. Inspected uncertainty figure matches tabulated direction and units. Conclusion is predictive incremental information, not causal charge inversion, formal oxidation states, or experimental generalization.'},
                limitations=['Model-search space is finite; differences are not information-theoretic lower bounds.','No structures are available to exclude related materials or aliases.','A public reference repository is not an access-control boundary; isolation of future solver runs remains necessary.'],
                hashes=dict(report=sha(a.original/'report.md'),design=sha(a.original/'design.json'),source={str(f.relative_to(a.original)):sha(f) for f in (a.original/'code').glob('*') if f.is_file()}))
    (a.destination.parent/'independent_q3_review_v2.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','numerical_integrity']},indent=2))
if __name__=='__main__':main()
