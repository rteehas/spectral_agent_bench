"""Write the real paper entry and reviewer-only workflow descriptions."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];DOCS=ROOT/'docs';BASE='data/gleason-2024-cu-oxidation';ASSET='assets/gleason-2024-cu-oxidation';PAPER='https://www.nature.com/articles/s41524-024-01408-1';CODE='https://github.com/smglsn12/ML_XAS_EELS/tree/85e0f34e448247f6c7a01705807dae39dd1d6cbd'

def file(q,name,description):return {'name':name,'url':f'{BASE}/inputs/{q}/{name}','description':description}
def figure(name,label,caption):return {'image':f'{ASSET}/{name}','label':label,'caption':caption,'url':PAPER}

def make(q,title,inputs,background,instruction,reason,check,steps,evidence,figures=None,thresholds=None):
    truth=[{'name':'expected.json','url':f'{BASE}/verification/{q}/expected.json','description':'Evaluator-only numerical targets; see provenance.json for their evidence type.'}]
    for name in evidence:truth.append({'name':name,'url':f'{BASE}/verification/{q}/{name}','description':'Evaluator-only numerical comparison policy.' if name.endswith('.json') else 'Evaluator-only numerical comparison table.'})
    methods=[{'name':q+'_candidate_workflow.json','url':f'{BASE}/workflows/{q}.json','description':'Worked candidate tool sequence, actual execution record, and limitations. Exclude from agent inputs.'},{'name':'candidate.py','url':f'{BASE}/workflows/candidate.py','description':'Executable worked solutions; reads only the selected question input directory. Exclude from agent inputs.'},{'name':'verify.py','url':f'{BASE}/workflows/verify.py','description':'Evaluator-side numeric checker. Interpretation and figure readability require separate review.'}]
    workflow={'scenario_id':'GLEASON24-'+q,'question':title,'tool_environment':{'python':'3.10.20','numpy':'1.26.2','pandas':'1.5.3','scipy':'1.15.3','matplotlib':'3.10.9','pymatgen':'2024.3.1 (Q1 only)'},'input_boundary':'Only the scenario inputs and its background. No released output tables, verification files, local prior traces or live API calls.','steps':[{'step':i+1,'tool':tool,'operation':op,'artifact_or_check':artifact} for i,(tool,op,artifact) in enumerate(steps)],'candidate_command':f'python candidate.py {q} --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY','verification_command':f'python verify.py {q} --output OUTPUT_DIRECTORY --truth verification/{q}','evidence':reason,'execution':{'status':'not_yet_executed'}}
    workflow_path=DOCS/BASE/'workflows'/f'{q}.json'
    if workflow_path.exists():
        previous=json.loads(workflow_path.read_text())
        workflow['execution']=previous.get('execution',workflow['execution'])
    workflow_path.write_text(json.dumps(workflow,ensure_ascii=False,indent=2)+'\n')
    verification={'description':check,'data':truth,'figures':figures or [],'methods':methods}
    if thresholds is not None:verification['thresholds']=thresholds
    return {'id':'GLEASON24-'+q,'kind':'Subquestion','title':title,'inputs':inputs,'prompt':{'background':background,'instruction':instruction},'verification':verification,'groundTruthReasoning':reason}

q1_steps=[
    ('Read the crystal structure','Python / pymatgen',
     'Read L3_001_Cu_feff.inp with Python. Extract the lattice lengths, angles, species and fractional coordinates from its header, then construct a pymatgen Structure using Lattice.from_parameters.',
     'A six-atom TbCu₅ unit cell containing one Tb atom and five Cu atoms.'),
    ('Determine the site weights','Python / pymatgen SpacegroupAnalyzer',
     'Identify equivalent atoms with SpacegroupAnalyzer(symprec=0.01).get_symmetrized_structure().equivalent_indices. Keep the Cu groups and divide each group size by the total number of Cu atoms.',
     'Zero-based representative site 1 occurs once and site 2 represents four equivalent atoms, giving weights 1/5 = 0.2 and 4/5 = 0.8.'),
    ('Load the four edge spectra','Python / NumPy',
     'Use numpy.loadtxt to read the L2 and L3 xmu.dat files for sites 001 and 002. Select column 1 for photon energy in eV and column 4 for absorption, preserving their supplied conventions.',
     'Separate L₂ and L₃ energy–intensity arrays for each Cu environment.'),
    ('Interpolate each edge','Python / NumPy',
     'For this worked solution, use numpy.arange to make a 0.1 eV grid from round(min(E)+0.15,1) to round(max(E)−0.15,1), excluding the upper bound. Use numpy.interp for linear interpolation of each edge onto its grid.',
     'Regularly sampled L₂ and L₃ curves ready for combination.'),
    ('Combine L₂ and L₃ for each site','Python / NumPy',
     'Extend L₂ down to the L₃ grid start using b(E+a)^10. Determine a and b from an intensity of 1e−10 at that start and the first interpolated L₂ point. Prepend this extension to L₂ and add it pointwise to L₃ over the L₃ grid.',
     'One combined Cu L₂,₃ spectrum for each representative site.'),
    ('Average the Cu sites','Python / NumPy',
     'Find the overlap of the two site energy ranges, build a common 0.1 eV grid excluding its upper endpoint, and interpolate both site curves onto it. Calculate S(E) = 0.2 S₁(E) + 0.8 S₂(E). The weights account for the number of Cu atoms represented by each simulation.',
     'The worked solution produces a material-averaged spectrum with 545 samples; this row count is specific to its numerical choices.'),
    ('Save the answer and plot the contributions','Python / pandas, json and Matplotlib',
     'Use pandas.DataFrame.to_csv to save energy_eV and intensity in spectrum.csv. Use Python json to save material_id, site_weights and the output row count in result.json. Use Matplotlib to overlay the weighted site contributions and their sum in plot.png.',
     'The requested numerical spectrum, result metadata and contribution plot. The archived run also retains an optional energy-reference diagnostic.'),
    ('Check the reconstructed answer','Evaluator / Python verify.py',
     'After the candidate finishes, run verify.py separately to check its site weights, reported row count and spectral agreement. The evaluator reference is the mp-1077262 row of the authors released 110222_Cu_DF_With_Spectra.joblib, previously extracted with joblib and pandas by prepare_assets.py. The candidate does not read that reference. Apply the comparison policy documented in Verification.',
     'The recorded execution passes the numerical checks, with normalized RMSE 0.0 on the comparison interval and zero reported peak-energy, peak-height and edge-area errors. Scientific interpretation and plot readability require separate review.')
]
q1_reason='\n\n'.join([
    'Worked solution: reconstruct the material spectrum from the supplied FEFF outputs using candidate.py. The interpolation and padding below follow the authors recipe as one valid numerical treatment; the benchmark also permits other justified treatments.',
    *[f'{i}. {title} ({tool})\n{operation}\nResult: {artifact}' for i,(title,tool,operation,artifact) in enumerate(q1_steps,1)],
    'Execution: python candidate.py Q1 --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY. The Q1_candidate_workflow.json link in Verification records the actual commands, program versions and outputs. Source methods: Database_Construction.ipynb cells 1, 9 and 10. FEFF is the source of the supplied simulations; no new FEFF calculation is run here.'
])
sc=[]
sc.append(make('Q1','What material-level Cu L₂,₃ spectrum is predicted for TbCu₅?',[
    file('Q1','L3_001_Cu_feff.inp','Unmodified FEFF input deck containing the six-atom unit cell; absorber indices in filenames are zero-based.'),
    *[file('Q1',f'{edge}_{site}_Cu_xmu.dat',f'Unmodified site-resolved FEFF {edge} output for Cu site {int(site)}. Column 1 is photon energy (eV) and column 4 is absorption.') for edge in ['L2','L3'] for site in ['001','002']]],
    'The supplied files contain separate Cu L₂ and L₃ FEFF spectra for the inequivalent Cu sites in TbCu₅ (Materials Project ID mp-1077262). The crystal structure is included in the FEFF input file. Use a positional symmetry tolerance of 0.01 Å when identifying equivalent Cu sites.',
    'Construct the material-averaged Cu L₂,₃ spectrum from the supplied simulations, preserving the FEFF energy and intensity conventions and resolving both edges. Determine the site weights from the structure. Save spectrum.csv with energy_eV,intensity, an overlay plot of weighted site contributions and their sum, and result.json containing material_id, site_weights keyed by zero-based site index, and points (your output row count). Justify how you combine the edges and handle interpolation, unequal energy ranges and site multiplicities.',
    q1_reason,
    'Require multiplicity-derived site weights and physically justified edge combination. Compare the reconstructed spectrum with the released material spectrum and inspect the contribution plot and reasoning. Different row counts, grids and padding functions are accepted. Numerical screening uses the separately documented benchmark thresholds below; other defensible methods need reviewer adjudication.',
    [(tool,operation,artifact) for _,tool,operation,artifact in q1_steps],['spectrum.csv'],thresholds={
        'origin':'Benchmark-defined',
        'generatedBy':'Model-generated',
        'provenance':'Note, the screening thresholds and comparison settings below were not reported in the paper and are not physical uncertainty estimates. They were produced separately during the labeling process.',
        'notes':[
            {'title':'Maximum Normalized RMSE','description':'2%, with RMSE normalized by the reference intensity range over the comparison interval.'},
            {'title':'Maximum Peak Energy Error','description':'0.2 eV for each edge.'},
            {'title':'Maximum Relative Peak Height Error','description':'5% for each edge, relative to the reference peak height.'},
            {'title':'Maximum Relative Edge Area Error','description':'5% for each edge, relative to the reference integrated area.'},
            {'title':'Boundary Exclusion','description':'Exclude 0.5 eV at each reference boundary from the comparison interval.'},
            {'title':'Comparison Method','description':'Linearly interpolate the candidate onto the reference interior energies without fitting an energy shift, amplitude scale or baseline.'},
            {'title':'Edge Windows','description':'L₃: 935–949 eV; L₂: 955–971 eV.'}
        ],
        'data':[{'name':'comparison_policy.json','url':f'{BASE}/verification/Q1/comparison_policy.json','description':'Evaluator-only, model-generated benchmark thresholds and comparison settings; includes provenance.'}]
    }))
from search_simulation_question import build_scenario
sc.append(build_scenario(DOCS,BASE))

paper={'id':'gleason-2024-cu-oxidation','title':'Prediction of the Cu oxidation state from EELS and XAS spectra using supervised machine learning','authors':'Samuel P. Gleason, Deyu Lu and Jim Ciston (2024)','doi':'10.1038/s41524-024-01408-1','category':'Cu oxidation-state spectroscopy','facility':'Materials Project / FEFF9; NCEM Molecular Foundry; CFN Brookhaven','pdf':PAPER+'.pdf','dataUrl':'https://zenodo.org/records/18142209','codeUrl':CODE,'scenarios':sc}
path=DOCS/'data/benchmark.json';data=json.loads(path.read_text());data['papers']=[p for p in data['papers'] if p['id']!=paper['id']]+[paper]
# Keep review storage stable and retain removed IDs only for saved-review compatibility.
data['retiredScenarioIds']=sorted(set(data.get('retiredScenarioIds',[]))|{'GLEASON24-Q2','GLEASON24-Q3','GLEASON24-Q4','GLEASON24-Q5','GLEASON24-Q6','GLEASON24-Q7'})
data['datasetId']='spectral-agent-v3';path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(ROOT/'papers/gleason-2024-cu-oxidation/paper.json').write_text(json.dumps(paper,ensure_ascii=False,indent=2)+'\n')
print('Added',len(sc),'independent questions to',path)
