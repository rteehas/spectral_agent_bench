#!/usr/bin/env python3
"""Publish review metadata locally, keeping worked solutions out of prompts."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'docs/data/guo-2023-sulfur-xas'
URL='data/guo-2023-sulfur-xas'

FORMAT=('These are computed sulfur K-edge spectra of lithium thiophosphates. Each NPZ key is material/site; '
        'its native columns are energy in eV and the xx, yy, zz dielectric components. calculations.json.gz '
        'contains unchanged VASP input/output text for neutral and core-hole calculations. The first atom '
        'in each core-hole POSCAR is the absorber; the site-name suffix gives its relative multiplicity. '
        'materials.csv describes each structure. The energy reference for an excitation is the core-hole '
        'minus neutral total energy; the saved spectral axis includes the core-hole Fermi-energy offset. '
        'A common offset to experimental photon energies is unknown.')
OUTPUT='Return report.md with your answer, quantitative evidence, methodological justification and limitations, supporting figures, and runnable code. '
SPECS=[
    ('Q1','When does treating inequivalent sulfur sites as interchangeable distort a material’s XANES fingerprint?',
     'Across the supplied structures, determine how much the material-level sulfur K-edge fingerprint depends on differences in site excitation energies and populations, and whether finite energy resolution changes that assessment. Identify where simplified site treatment is least reliable. '+OUTPUT+
     'Include the unbroadened material responses as bulk.npz (keys m001 through m066, each with energy and intensity columns), and numerical evidence for the comparisons.',
     'Automated XCH post-processing and material-level averaging in Methods/Fig.2. The held-back author-released raw material spectra directly anchor the reconstruction; ablations and resolution sensitivity are new benchmark experiments.',
     ['bulk.npz','effects.csv','ablations.npz','summary.json','report.md'],['effects.png','overlays.png']),
    ('Q2','Does greater local lithium coordination reliably predict a sulfur K-edge red shift?',
     'Determine whether increasing lithium coordination around sulfur predicts a red shift across these structures once phosphorus bonding and material composition are taken into account. Establish how robust the relationship is to the definitions of local coordination and spectral shift, and what the data support about its physical interpretation. '+OUTPUT+
     'Include sites.csv, identifying each observation by material and site, with the structural and spectral quantities used; define their units and meaning in the report.',
     'Local coordination and shielding hypothesis motivating Fig.1, and the limitations of bond-length/charge explanations discussed for beta-Li3PS4 near Fig.3d. The conditional analysis is a new investigation, not an author-reported regression.',
     ['sites.csv','associations.csv','definitions.json','report.md'],['associations.png']),
    ('Q3','Can sulfur K-edge spectra identify phosphorus coordination in previously unseen glassy structures?',
     'Infer the number of phosphorus neighbours of an absorbing sulfur from its spectrum alone. Determine whether inference trained on crystalline environments transfers to glasses, and whether including other glassy structures improves generalization. Evaluate all supplied glassy structures without using any site from a target structure for training or selection. Assess failures for uncommon environments and sensitivity to energy resolution. Structural information may define labels but must not enter spectral prediction. '+OUTPUT+
     'Include sites.csv with material,site,p_cn and the coordination definition in the report; predictions.csv with material,site,split,method,predicted; and partitions.csv with material,split,method,role (train,validation,test,unused).',
     'The stated use of unaveraged site spectra for local-environment fingerprinting/machine-learning interpretation. This transfer experiment operationalizes that use; the paper supplies no historical machine-learning scores.',
     ['sites.csv','predictions.csv','partitions.csv','metrics.json','definitions.json','report.md'],['transfer.png']),
]

def asset(name,path,description):return {'name':name,'url':URL+'/'+path,'description':description}
def write(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')

def main():
    scenarios=[]
    for q,title,instruction,source,outputs,figures in SPECS:
        inputs=[asset(f'spectra_{n:02d}.npz',f'inputs/spectra_{n:02d}.npz','Native site-resolved numeric spectra; material/site keys, energy and three diagonal components.') for n in range(1,7)]
        inputs += [asset('calculations.json.gz','inputs/calculations.json.gz','Raw POSCAR, OSZICAR, INCAR, KPOINTS and saved Fermi-energy text, keyed by material and calculation.'),asset('materials.csv','inputs/materials.csv','Released material identities, compositions and structure origins.')]
        workflow={'question':q,'source_derivation':source,'solver_inputs':'Only the eight inputs linked in this task; no paper, averaged spectra, code release or expected answers.',
            'environment':'Python3.12; install papers/guo-2023-sulfur-xas/requirements.txt',
            'commands':[
              'python3 -m venv /tmp/guo-bench-env',
              '/tmp/guo-bench-env/bin/python -m pip install -r papers/guo-2023-sulfur-xas/requirements.txt',
              f'python3 papers/guo-2023-sulfur-xas/export_agent_bundle.py {q} --output /tmp/guo-{q}-agent',
              f'OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MPLCONFIGDIR=/tmp/guo-mpl /tmp/guo-bench-env/bin/python docs/{URL}/workflows/candidate.py {q} --inputs /tmp/guo-{q}-agent/inputs --output /tmp/guo-{q}-answer',
              f'/tmp/guo-bench-env/bin/python docs/{URL}/workflows/verify.py --question {q} --inputs docs/{URL}/inputs --output /tmp/guo-{q}-answer'],
            'tools':['Python gzip/json/csv and NumPy for raw release parsing','ASE periodic geometry','SciPy interpolation and Gaussian filtering','NumPy least-squares/material-block bootstrap' if q=='Q2' else ('scikit-learn random forests/confusion matrices' if q=='Q3' else 'NumPy weighted sums and controlled ablations'),'Matplotlib diagnostic plots'],
            'choices':'See candidate.py, definitions.json and report.md. These are illustrative choices, not a required solver protocol.',
            'outputs':outputs+figures,'verification':'Independent source reconstruction/numerical integrity followed by scientific rubric. No acceptance threshold on classification performance or regression sign.'}
        write(BASE/'workflows'/f'{q}.json',workflow)
        reasoning={
          'Q1':'Python loads all native site arrays and calculation text. The worked candidate uses the last OSZICAR E0 values and stored Fermi energies to align excitation energies, then SciPy cubic interpolation and multiplicity ratios to form an orientationally averaged response for each material. It separately replaces site corrections by their material mean and replaces multiplicity ratios by equal weights. Gaussian resolution trials quantify changes of normalized shape and main peak. bulk.npz, ablations.npz and effects.csv preserve the evidence; effects.png and overlays.png show its structure dependence. Independently, the evaluator compares against author-released raw material averages after permitted intensity scaling and one common energy zero. The supplied code tag omits the Fermi correction; independent reconstruction of all66 released outputs establishes the convention, rather than trusting that parser. Broadened/shifted author outputs have additional undocumented normalization/calibration and are not exact targets.',
          'Q2':'ASE reads each core-hole POSCAR and obtains periodic neighbor distances about its first sulfur. NumPy/SciPy derive several near-edge shift observables on aligned spectra. The candidate compares equal-material-weighted regressions with and without material fixed effects, controlling P coordination, and changes the Li cutoff and spectral observable. A material-block bootstrap estimates conditional uncertainty. sites.csv contains2681 observations, associations.csv contains18 specifications, and the report distinguishes association from an electronic shielding mechanism. Independent geometry and energy checks verify observations. The evaluator then inspects confounding controls, uncertainty and sensitivity rather than requiring a particular slope or sign.',
          'Q3':'Python/ASE constructs coordination labels from raw structures, while only processed spectral intensities enter inference. The candidate evaluates crystal-only, glass-material-holdout and hybrid training on the same four partitions of48 glasses. Scikit-learn fits fixed random forests at two Gaussian resolutions, with a majority baseline. Predictions and partitions retain all target sites so the evaluator independently reconstructs class recalls, balanced accuracy and confusions from source-derived labels. Material-block intervals expose sampling limitations. The scientific review must assess sparse-class failures, leakage and what generalization the archive supports; no historical or candidate score is a target.'}[q]
        data=[asset('provenance.json','provenance.json','Release identity, licenses, hashes and lossless packaging manifest.'),asset('source_map.json','verification/source_map.json','Source grounding and available/missing truth.'),asset('Scientific rubric','verification/scientific_review_rubric.md','Required scientific assessment, separate from numerical integrity.')]
        if q=='Q1':data.append(asset('Released raw material spectra','verification/released_material_spectra.npz','Held-back author outputs for66 materials; independent numerical truth.'))
        data += [asset(f'{q} {f}',f'verification/{q}/{f}','Executed illustrative evidence; alternative defensible analyses need not match these choices.') for f in outputs]
        data += [asset(n,'verification/'+n,'Independent review/audit record.') for n in ['question_quality_review.json','workflow_execution_review.json','verification_audit.json','scientific_review.json']]
        scenarios.append({'id':'GUO23-'+q,'kind':'Subquestion','executionStatus':'executed_example','title':title,'inputs':inputs,
            'prompt':{'background':FORMAT,'instruction':instruction},'groundTruthReasoning':reasoning,
            'verification':{'description':'Verify raw-source consistency and numerical integrity, then review the scientific design, executable evidence and scope of conclusions. Numerical success alone does not establish a scientific pass. Negative scientific results are valid. '+('Compare all66 reconstructed native material responses with held-back released arrays, allowing a single shared energy origin and independent positive intensity scales.' if q=='Q1' else ('Audit claimed observations against raw geometry/energies, and examine composition control and definition sensitivity.' if q=='Q2' else 'Reconstruct target labels and metrics independently; audit material-level train/test exclusion, target coverage and sparse-class behavior.')),
                'data':data,'figures':[{'image':f'{URL}/verification/{q}/{f}','label':q+' '+f,'caption':'Diagnostic generated by the executed worked example; not a paper figure.'} for f in figures],
                'methods':[asset('Worked tool calls',f'workflows/{q}.json','Executable commands and workflow choices; excluded from solver inputs.'),asset('candidate.py','workflows/candidate.py','Runnable illustrative research design.'),asset('verify.py','workflows/verify.py','Independent integrity and numerical verification; scientific review remains required.')],
                'thresholds':{'origin':'benchmark-defined','generatedBy':'Benchmark authors with independent agent audit','provenance':'Tolerances and review criteria are benchmark engineering choices, not published scientific performance thresholds. No regression sign or classification score is required.','notes':[{'title':'Numerical checks','description':'Native response comparison allows interpolation differences; geometry and energy quantities are checked against original inputs. See checker and mutation audit for exact tolerances and their limits.'},{'title':'Scientific acceptance','description':'The rubric requires valid design, sensitivity, evidence-supported conclusions and reproducibility. A constant predictor or shallow correlation may pass arithmetic checks and fail scientific review.'}]}}})
    paper={'id':'guo-2023-sulfur-xas','title':'Simulated sulfur K-edge X-ray absorption spectroscopy database of lithium thiophosphate solid electrolytes','authors':'Haoyue Guo, Matthew R. Carbone et al. (2023)','doi':'10.1038/s41597-023-02262-4','category':'Sulfur K-edge XANES / solid electrolytes','facility':'VASP XCH / Materials Cloud','pdf':'https://www.nature.com/articles/s41597-023-02262-4.pdf','dataUrl':'https://doi.org/10.24435/materialscloud:6z-qm','codeUrl':'https://github.com/atomisticnet/xas-tools/releases/tag/v0.1.0','scenarios':scenarios}
    write(HERE/'paper.json',paper)
    active=ROOT/'docs/data/benchmark.json'; dataset=json.loads(active.read_text()); others=[p for p in dataset['papers'] if p['id']!=paper['id']]; dataset['papers']=others+[paper]; dataset['datasetId']='spectral-agent-v2026-09-26-guo-research-v1'; write(active,dataset)
    write(BASE/'verification/source_map.json',{'paper_doi':paper['doi'],'data_doi':'10.24435/materialscloud:6z-qm','code_tag':'v0.1.0','code_commit':'a7d08913fc59d6509459268279b33195cf20e30b','questions':{q:source for q,title,instruction,source,outputs,figures in SPECS},'external_truth':'66 author-released unbroadened material spectra; native site arrays/calculation text and atomic structures','not_available':'Raw experimental Li2S/P2S5/NiS/beta-LPS spectra, self-absorption workflow, convergence sweeps, charge density, original ML results. These are not asserted as reproduced.','code_discrepancies':'Tag parser omits stored Fermi subtraction required by the released material spectra. Its spectrum property mutates accumulated intensity. Its example broadening parameters differ from the article. Candidate implements explicit non-mutating reconstruction.'})
    print('Built Guo entry with3 questions; existing papers preserved.')

if __name__=='__main__':main()
