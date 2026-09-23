"""Author-side extraction of minimal inputs and separately held verification data.

Requires the downloaded open release; never used inside an agent task.
No candidate workflow is called to create the released-output ground truth.
"""
import argparse,hashlib,json,shutil,sys,zipfile
from pathlib import Path
import joblib,numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'docs/data/gleason-2024-cu-oxidation'
ASSETS=ROOT/'docs/assets/gleason-2024-cu-oxidation'

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--release',type=Path,default=ROOT.parent/'gleason_2024_cu_oxidation_state');a=p.parse_args()
    data=a.release/'data';combined_path=data/'Dataset_generation/110222_Cu_DF_With_Spectra.joblib';processed_path=data/'Cu_reproducable_alignment_df_extracted_110222.joblib'
    combined=joblib.load(combined_path);processed=joblib.load(processed_path);sources=[]
    for f in [combined_path,processed_path]:sources.append({'path':str(f.relative_to(a.release)),'sha256':sha(f)})
    I=DEST/'inputs';V=DEST/'verification';I.mkdir(parents=True,exist_ok=True);V.mkdir(parents=True,exist_ok=True)
    # Q1: raw FEFF files are byte-for-byte copies, including the full structure header.
    mid='mp-1077262';archive=data/'Dataset_generation/FEFF_simulations/Stable_and_exp_Cu_with_results.zip'
    with zipfile.ZipFile(archive) as z:
        refs=[]
        for n in z.namelist():
            if f'/{mid}/' not in n:continue
            if not (n.endswith('/xmu.dat') or n.endswith('/feff.inp')):continue
            edge='L2' if '_L2/' in n else 'L3';site=n.split('/FEFF/')[1].split('/')[0]
            if n.endswith('/feff.inp') and (edge!='L3' or site!='001_Cu'):continue
            dest=I/'Q1'/f'{edge}_{site}_{Path(n).name}';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(n))
            refs.append({'asset':str(dest.relative_to(DEST)),'zip_member':n,'sha256':sha(dest)})
    row=combined.loc[combined.mp_id==mid].iloc[0]
    (V/'Q1').mkdir(exist_ok=True)
    pd.DataFrame({'energy_eV':row.Energies,'intensity':row.Spectrum}).to_csv(V/'Q1/spectrum.csv',index=False)
    dump(V/'Q1/expected.json',{'material_id':mid,'site_weights':{'1':.2,'2':.8},'L3_reference_eV':float(row.L3_avg_Fermi),'points':len(row.Energies)})
    sources.append({'path':str(archive.relative_to(a.release)),'sha256':sha(archive),'members':refs})
    # Q2/Q3: only upstream dictionaries/statuses, never final labels or selection.
    records=[]
    for index,r in combined.iterrows():
        f=r.L3_avg_Fermi
        status='error' if isinstance(f,str) else 'missing' if pd.isna(f) else 'ok'
        ox=r.full_ox_states if isinstance(r.full_ox_states,dict) else None
        records.append({'record':int(index),'material_id':str(r.mp_id),'average_oxidation_states':ox,'L3_reference_status':status,'is_stable':bool(r.is_stable) if isinstance(r.is_stable,(bool,np.bool_)) else None,'theoretical':bool(r.theoretical) if isinstance(r.theoretical,(bool,np.bool_)) else None})
    # Each task gets exactly the metadata fields it needs.
    for q,fields in [('Q2',['record','material_id','average_oxidation_states','L3_reference_status']),('Q3',['record','material_id','average_oxidation_states','L3_reference_status','is_stable','theoretical'])]:
        dump(I/q/'material_records.json',[{k:r[k] for k in fields} for r in records])
    labels=processed['NEW BV Used For Alignment'].astype(float);ids=set(processed.mp_id.astype(str))
    zero_ids=set(processed.loc[labels.eq(0),'mp_id']);missing=[r for r in records if r['material_id'] in ids and (not r['average_oxidation_states'] or 'Cu' not in r['average_oxidation_states'])]
    dump(V/'Q2/expected.json',{'retained':len(processed),'integer_counts':{str(v):int(labels.eq(v).sum()) for v in [0,1,2]},'fractional':int((~labels.isin([0,1,2])).sum()),'integer_fraction':float(labels.isin([0,1,2]).mean()),'above_two_below_three':int(labels.gt(2).sum()),'zero_from_missing':len([r for r in missing if r['material_id'] in zero_ids]),'zero_explicit':int(sum(r['material_id'] in zero_ids and r['average_oxidation_states'] and r['average_oxidation_states'].get('Cu')==0 for r in records if r['average_oxidation_states']))})
    stable=processed.is_stable.eq(True);exp=processed.theoretical.eq(False)
    dump(V/'Q3/expected.json',{'retained':len(processed),'stable':int(stable.sum()),'experimentally_known':int(exp.sum()),'both':int((stable&exp).sum()),'stable_only':int((stable&~exp).sum()),'experimentally_known_only':int((~stable&exp).sum()),'neither':int((~stable&~exp).sum())})
    raw='TEAM_1_aligned_925_970';cum='Cumulative_Spectra_TEAM_1_aligned_925_970';energy='new Scaled Energies use';proc=processed.set_index('mp_id')
    # Q4 ordinary spectra only; cumulative target is held back in verification/.
    refids=['mp-30','mp-361','mp-704645'];names=['Cu','Cu2O','CuO'];d={};c={}
    for mid,name in zip(refids,names):
        d[name]=np.asarray(proc.loc[mid,raw]);c[name]=np.asarray(proc.loc[mid,cum])
    d={'energy_eV':proc.loc[refids[0],energy],**d};c={'energy_eV':proc.loc[refids[0],energy],**c}
    (I/'Q4').mkdir(exist_ok=True);(V/'Q4').mkdir(exist_ok=True)
    pd.DataFrame(d).to_csv(I/'Q4/reference_spectra.csv',index=False);pd.DataFrame(c).to_csv(V/'Q4/cumulative.csv',index=False)
    dump(V/'Q4/expected.json',{'materials':refids,'points':451,'first_value':0.0,'last_value':1.0})
    # Q5: figure parents are inputs; weighted components and sum are held back.
    mixids=['mp-12007','mp-8120','mp-1188453'];d={'energy_eV':proc.loc[mixids[0],energy]}
    for mid in mixids:d[mid]=proc.loc[mid,raw]
    (I/'Q5').mkdir(exist_ok=True);(V/'Q5').mkdir(exist_ok=True)
    pd.DataFrame(d).to_csv(I/'Q5/parent_spectra.csv',index=False)
    shutil.copyfile(a.release/'panel_iii_mixtures/output/figure_example.csv',V/'Q5/mixture.csv')
    dump(V/'Q5/expected.json',{'parent_ids':mixids,'coefficients':[.33,.33,.33],'coefficient_sum':.99,'points':451})
    # Q6 concerns label coverage; spectra are unnecessary and are not exposed.
    (I/'Q6').mkdir(exist_ok=True);(V/'Q6').mkdir(exist_ok=True)
    pd.DataFrame({'material_id':processed.mp_id.astype(str),'label':labels}).to_csv(I/'Q6/ordered_base_labels.csv',index=False)
    prior=pd.read_csv(a.release/'panel_iii_mixtures/output/mixture_manifest.csv')
    prior[['type','id_0','id_1','id_2','weight_0','weight_1','weight_2','label']].to_csv(V/'Q6/manifest.csv',index=False)
    all_labels=np.r_[labels.to_numpy(),prior.label.to_numpy()];fractional=all_labels[~np.isin(all_labels,[0,1,2])];hist,edges=np.histogram(fractional,bins=np.linspace(0,2,21))
    dump(V/'Q6/expected.json',{'base_rows':len(processed),'generated_by_family':prior.type.value_counts().to_dict(),'generated':len(prior),'augmented':len(all_labels),'synthetic_integer_labels':int(prior.label.isin([0,1,2]).sum()),'augmented_integer_counts':{str(v):int((all_labels==v).sum()) for v in [0,1,2]},'histogram_counts':hist.tolist(),'histogram_edges':edges.tolist(),'histogram_total':int(hist.sum()),'fractional_outside_histogram':int(((fractional<0)|(fractional>2)).sum())})
    # Q7: unchanged literature XAS CSVs, no peaks or shifts precomputed in inputs.
    peaks={}
    for name in ['Cu Metal','Cu2O','CuO']:
        src=data/'xas paper'/(name+' XAS.csv');dst=I/'Q7'/src.name;dst.parent.mkdir(exist_ok=True);shutil.copyfile(src,dst)
        table=pd.read_csv(src);window=table.loc[table['Energy (eV)'].between(930,940)]
        peaks[name]=float(window.loc[window.Intensity.idxmax(),'Energy (eV)'])
        sources.append({'path':str(src.relative_to(a.release)),'sha256':sha(src),'copied_to':str(dst.relative_to(DEST))})
    dump(V/'Q7/expected.json',{'L3_peak_eV':peaks,'Cu2O_minus_Cu_eV':peaks['Cu2O']-peaks['Cu Metal'],'CuO_minus_Cu_eV':peaks['CuO']-peaks['Cu Metal'],'CuO_minus_Cu2O_eV':peaks['CuO']-peaks['Cu2O']})
    ASSETS.mkdir(parents=True,exist_ok=True)
    for source,name in [('panel_iii_mixtures/source_evidence/paper_figures_cell_16_output_2.png','notebook-ternary-mixture.png'),('panel_iii_mixtures/source_evidence/paper_figures_cell_13_output_0.png','notebook-augmented-distribution.png'),('repository/ML_XAS_EELS/Figures/Figure 1/ML EELS Figure 1.png','paper-figure-1.png'),('repository/ML_XAS_EELS/Figures/Figure S1/ML EELS Figure S1.png','paper-figure-s1.png')]:
        shutil.copyfile(a.release/source,ASSETS/name)
    dump(DEST/'provenance.json',{'paper_doi':'10.1038/s41524-024-01408-1','data_url':'https://zenodo.org/records/18142209','zenodo_zip_md5':'1246825b838f77b926d0e58f6ca68e45','code_commit':'85e0f34e448247f6c7a01705807dae39dd1d6cbd','sources':sources,'input_transformations':{'Q1':'Byte-identical FEFF input/output subset for mp-1077262, sites 1 and 2, edges L2/L3.','Q2':'Projection of saved pre-label dictionaries and ID/reference status; excludes saved labels, retained masks and spectra.','Q3':'Q2 projection plus saved stability/theoretical flags.','Q4':'Three ordinary aligned spectra projected to CSV; cumulative output withheld. These are released intermediate spectra, not unprocessed measurements.','Q5':'Three different ordinary aligned spectra projected to CSV; weighted outputs withheld. These are released intermediate spectra.','Q6':'Released base IDs and labels in original row order; excludes all synthetic rows and coverage counts.','Q7':'Three byte-identical XAS CSVs. The open release describes literature spectra; do not call these detector-raw measurements.'},'verification_independence':{'Q1':'Material spectrum copied from released pre-alignment intermediate; no candidate function used. Weights independently inferred from six-site structure header.','Q2':'Counts from independently released processed labels; imputation provenance checked against saved dictionaries.','Q3':'Flags/counts from independently released retained rows. Figure 1 is contextual, not exact count truth.','Q4':'Cumulative arrays copied directly from released processed table, not generated by candidate.','Q5':'Numerical reference recomputed previously from released parents and original plotting call; authors embedded plot independently checks shape. No separately released mixture array.','Q6':'Prior replay of structurally unchanged author generation methods on the released base table; no independent historical mixture table.','Q7':'Peak values independently reduced from raw-release CSVs; qualitative comparison to Figure S1. No independently published exact peak table.'},'asset_hashes':{str(f.relative_to(DEST)):sha(f) for f in sorted(DEST.rglob('*')) if f.is_file() and f.name!='provenance.json' and 'workflows' not in f.parts}})
    print('Prepared seven input bundles and separate verification data.',flush=True)
if __name__=='__main__':main()
