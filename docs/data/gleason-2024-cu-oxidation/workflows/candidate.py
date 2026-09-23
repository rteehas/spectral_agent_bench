"""Worked candidate solutions. Reads ONLY the requested task's input directory.

Usage: python candidate.py Q1 --inputs PATH --output PATH
No verification files, prior local traces, joblib objects, web calls or API keys are used.
"""
import argparse,json,re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def save_json(folder,obj):
    (folder/'result.json').write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')


def finish_plot(folder,title,xlabel='Energy (eV)',ylabel='Intensity'):
    plt.xlabel(xlabel);plt.ylabel(ylabel);plt.title(title);plt.legend(fontsize=8)
    plt.tight_layout();plt.savefig(folder/'plot.png',dpi=140);plt.close()


def selected_records(folder):
    records=json.loads((folder/'material_records.json').read_text());selected=[]
    for record in records:
        if record['material_id']=='Failed' or record['L3_reference_status']!='ok':continue
        ox=record['average_oxidation_states'] or {};missing='Cu' not in ox
        label=0.0 if missing else round(ox['Cu'],2)
        if label>=3:continue
        selected.append({**record,'label':label,'imputed_zero':missing})
    return selected


def q1(folder,out):
    from pymatgen.core import Lattice,Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    text=next(folder.glob('*feff.inp')).read_text()
    def values(key):return [float(v) for v in re.search(r'^TITLE '+key+r':(.*)$',text,re.M).group(1).split()]
    sites=re.findall(r'^\*\s+\d+\s+([A-Z][a-z]?)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)',text,re.M)
    structure=Structure(Lattice.from_parameters(*values('abc'),*values('angles')),[x[0] for x in sites],[[float(v) for v in x[1:]] for x in sites])
    groups=SpacegroupAnalyzer(structure,symprec=.01).get_symmetrized_structure().equivalent_indices
    groups=[g for g in groups if structure[g[0]].specie.symbol=='Cu'];total=sum(map(len,groups));weights={g[0]:len(g)/total for g in groups}
    curves=[];markers=[]
    for site,w in weights.items():
        l2=np.loadtxt(folder/f'L2_{site:03d}_Cu_xmu.dat');l3=np.loadtxt(folder/f'L3_{site:03d}_Cu_xmu.dat')
        markers.append(float(l3[np.flatnonzero(l3[:,2]==0)[0],0]))
        grid3=np.arange(round(l3[:,0].min()+.15,1),round(l3[:,0].max()-.15,1),.1)
        grid2=np.arange(round(l2[:,0].min()+.15,1),round(l2[:,0].max()-.15,1),.1)
        y3=np.interp(grid3,l3[:,0],l3[:,3]);y2=np.interp(grid2,l2[:,0],l2[:,3])
        lo,hi=grid3[0],grid2[0];power=10
        ratio=(1e-10/y2[0])**(1/power);shift=(lo-hi*ratio)/(ratio-1);scale=1e-10/(lo+shift)**power
        stop=hi-.1;prefix=np.linspace(lo,stop,int(round(stop-lo,1)*10)+1)
        tail=(prefix+shift)**power*scale
        curves.append((site,np.round(grid3,1),y3+np.r_[tail,y2][:len(grid3)],w))
    lo=max(c[1][0] for c in curves);hi=min(c[1][-1] for c in curves)
    common=np.round(np.arange(lo,hi,.1),1);intensity=np.zeros(len(common))
    for site,e,y,w in curves:
        local=np.interp(common,e,y);intensity+=w*local;plt.plot(common,w*local,'--',label=f'Site {site} × {w:g}')
    plt.plot(common,intensity,label='TbCu5 material spectrum',color='black')
    finish_plot(out,'Multiplicity-weighted Cu L₂,₃ spectrum')
    pd.DataFrame({'energy_eV':common,'intensity':intensity}).to_csv(out/'spectrum.csv',index=False)
    save_json(out,{'material_id':'mp-1077262','site_weights':{str(k):v for k,v in weights.items()},'L3_reference_eV':float(np.mean(markers)),'points':len(common)})


def q2(folder,out):
    records=selected_records(folder);labels=np.array([x['label'] for x in records]);integer=np.isin(labels,[0,1,2]);zero=[x for x in records if x['label']==0]
    result={'retained':len(records),'integer_counts':{str(i):int((labels==i).sum()) for i in range(3)},'fractional':int((~integer).sum()),'integer_fraction':float(integer.mean()),'above_two_below_three':int((labels>2).sum()),'zero_from_missing':sum(x['imputed_zero'] for x in zero),'zero_explicit':sum(not x['imputed_zero'] for x in zero)}
    save_json(out,result)
    plt.bar(['0','1','2','fractional'],[*result['integer_counts'].values(),result['fractional']]);plt.ylabel('Materials');plt.xlabel('Cu label');plt.title('Base-set oxidation-state coverage');plt.tight_layout();plt.savefig(out/'plot.png',dpi=140);plt.close()


def q3(folder,out):
    records=selected_records(folder);stable=np.array([r['is_stable'] is True for r in records]);exp=np.array([r['theoretical'] is False for r in records])
    result={'retained':len(records),'stable':int(stable.sum()),'experimentally_known':int(exp.sum()),'both':int((stable&exp).sum()),'stable_only':int((stable&~exp).sum()),'experimentally_known_only':int((~stable&exp).sum()),'neither':int((~stable&~exp).sum())};save_json(out,result)
    keys=['stable_only','both','experimentally_known_only','neither'];plt.bar(['Stable only','Both','Known only','Neither'],[result[k] for k in keys]);plt.ylabel('Materials');plt.title('Material provenance in the retained release');plt.tight_layout();plt.savefig(out/'plot.png',dpi=140);plt.close()


def q4(folder,out):
    d=pd.read_csv(folder/'reference_spectra.csv');result={'energy_eV':d.energy_eV}
    for name in ['Cu','Cu2O','CuO']:
        # Left-endpoint cumulative convention: exclude the current sample.
        y=d[name].to_numpy();c=np.r_[0.,np.cumsum(y[:-1])];c/=c.max();result[name]=c;plt.plot(d.energy_eV,c,label=name)
    pd.DataFrame(result).to_csv(out/'cumulative.csv',index=False);finish_plot(out,'Cumulative model inputs',ylabel='Normalized cumulative intensity')
    save_json(out,{'materials':['mp-30','mp-361','mp-704645'],'points':len(d),'first_value':0.,'last_value':1.})


def q5(folder,out):
    d=pd.read_csv(folder/'parent_spectra.csv');parents=list(d.columns[1:]);w=np.array([.33,.33,.33]);pieces=d[parents].to_numpy().T*w[:,None];mix=pieces.sum(axis=0)
    for i,y in enumerate(pieces):plt.plot(d.energy_eV,y,'--',label=f'0.33 × {parents[i]}')
    plt.plot(d.energy_eV,mix,color='red',label='Mixture');finish_plot(out,'Figure 1 ternary spectral example')
    pd.DataFrame({'energy_eV':d.energy_eV,'weighted_0':pieces[0],'weighted_1':pieces[1],'weighted_2':pieces[2],'mixture':mix}).to_csv(out/'mixture.csv',index=False)
    save_json(out,{'parent_ids':parents,'coefficients':w.tolist(),'coefficient_sum':float(w.sum()),'points':len(d)})


def q6(folder,out):
    base=pd.read_csv(folder/'ordered_base_labels.csv');pools=[base.loc[base.label==v,'material_id'].tolist() for v in range(3)];rows=[]
    ascending=np.linspace(0,1,101);descending=np.linspace(1,0,101)
    for family in ['all','0-1','1-2']:
        rng=np.random.RandomState(32)
        for draw in range(100):
            ids=[pool[rng.randint(0,len(pool))] for pool in pools]
            w0=rng.choice(descending,20) if family!='1-2' else np.zeros(20)
            w2=rng.choice(ascending,20) if family!='0-1' else np.zeros(20)
            w1=rng.choice(ascending,20)
            for k in range(20):
                total=w0[k]+w1[k]+w2[k]
                if total==0:continue
                w=np.array([w0[k],w1[k],w2[k]])/total
                rows.append([family,*ids,*w,round(w[0]*0+w[1]*1+w[2]*2,2)])
    manifest=pd.DataFrame(rows,columns=['type','id_0','id_1','id_2','weight_0','weight_1','weight_2','label']);manifest.to_csv(out/'manifest.csv',index=False)
    labels=np.r_[base.label.to_numpy(),manifest.label.to_numpy()];fractional=labels[~np.isin(labels,[0,1,2])];counts,edges=np.histogram(fractional,bins=np.linspace(0,2,21))
    result={'base_rows':len(base),'generated_by_family':manifest.type.value_counts().to_dict(),'generated':len(manifest),'augmented':len(labels),'synthetic_integer_labels':int(manifest.label.isin([0,1,2]).sum()),'augmented_integer_counts':{str(i):int((labels==i).sum()) for i in range(3)},'histogram_counts':counts.tolist(),'histogram_edges':edges.tolist(),'histogram_total':int(counts.sum()),'fractional_outside_histogram':int(((fractional<0)|(fractional>2)).sum())};save_json(out,result)
    plt.bar([0,1,2],list(result['augmented_integer_counts'].values()),width=.3,label='Exact integer labels');plt.hist(fractional,bins=edges,color='red',alpha=.7,label='Other labels');finish_plot(out,'Oxidation-state coverage after augmentation',xlabel='Cu oxidation-state label',ylabel='Spectra')


def q7(folder,out):
    peaks={}
    for name in ['Cu Metal','Cu2O','CuO']:
        d=pd.read_csv(folder/(name+' XAS.csv'));window=d.loc[d['Energy (eV)'].between(930,940)];peaks[name]=float(window.loc[window.Intensity.idxmax(),'Energy (eV)'])
        local=window.sort_values('Energy (eV)');y=local.Intensity.to_numpy();y=(y-y.min())/(y.max()-y.min());line,=plt.plot(local['Energy (eV)'],y,lw=.7,alpha=.55,label=f'{name}: {peaks[name]:.2f} eV');plt.axvline(peaks[name],color=line.get_color(),ls='--',lw=1.2);plt.scatter([peaks[name]],[1.],color=line.get_color(),s=24,zorder=5)
    finish_plot(out,'Experimental XAS L₃ peak positions',ylabel='Window-normalized intensity')
    save_json(out,{'L3_peak_eV':peaks,'Cu2O_minus_Cu_eV':peaks['Cu2O']-peaks['Cu Metal'],'CuO_minus_Cu_eV':peaks['CuO']-peaks['Cu Metal'],'CuO_minus_Cu2O_eV':peaks['CuO']-peaks['Cu2O']})


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('question',choices=[f'Q{i}' for i in range(1,8)]);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    globals()[a.question.lower()](a.inputs,a.output)
    result=json.loads((a.output/'result.json').read_text())
    if a.question=='Q1':
        conclusion=f"The structure gives site weights {result['site_weights']}. Equal weighting of the two inequivalent sites would ignore their different Cu atom multiplicities. The reconstructed material curve has {result['points']} points; its arithmetic L3 reference is {result['L3_reference_eV']:.6f} eV. These are calculated spectra, not experimental measurements."
    elif a.question=='Q2':
        conclusion=f"Among {result['retained']} retained materials, {100*result['integer_fraction']:.4f}% have integer labels and {result['fractional']} have fractional labels. All {result['zero_from_missing']} imputed-zero records lack a Cu assignment; only {result['zero_explicit']} zeros were explicitly returned. The archive establishes a labeling convention, not the chemical correctness of every Cu(0) assignment."
    elif a.question=='Q3':
        conclusion=f"The stable and experimentally known groups overlap in {result['both']} materials. Adding the two inclusive counts double-counts this intersection. The four exclusive categories sum to {result['retained']}. Experimental structure provenance does not turn a calculated spectrum into a measured one."
    elif a.question=='Q4':
        conclusion="The normalized left-exclusive cumulative curves run from zero to one. Strong absorption features produce steep rises, while weaker features contribute more gradually. The CuO rise occurs at lower energy than the main Cu/Cu2O rises in these inputs. This transformation supplies model features; it does not itself infer an oxidation state or establish model accuracy."
    elif a.question=='Q5':
        conclusion=f"The curve is the pointwise sum of three nonnegative weighted contributions, so it can exceed each individual contribution. The display coefficients sum to {result['coefficient_sum']:.2f}; they were not renormalized. They parameterize this spectral illustration and are not independently measured mass or volume fractions."
    elif a.question=='Q6':
        conclusion=f"The nominal 6,000 attempts yield {result['generated']} mixtures because {6000-result['generated']} all-zero coefficient triples are skipped. Appending them gives {result['augmented']} rows. Rounded integer synthetic labels contribute {result['synthetic_integer_labels']} rows to the bars; {result['fractional_outside_histogram']} original fractional labels fall outside the 0–2 histogram. This reproduces the specified release/sampling protocol, not an independently stored historical augmentation."
    else:
        conclusion=f"Cu2O minus Cu is {result['Cu2O_minus_Cu_eV']:.4f} eV; CuO minus Cu2O is {result['CuO_minus_Cu2O_eV']:.4f} eV. Cu/Cu2O peak positions nearly coincide, whereas CuO lies lower. Peak energy alone therefore has limited power to separate all three references. This does not make their complete spectra indistinguishable, and the conclusion is limited to these supplied spectra."
    (a.output/'conclusion.md').write_text(conclusion+'\n')
    print(json.dumps({'question':a.question,'outputs':[x.name for x in sorted(a.output.iterdir())],'result':json.loads((a.output/'result.json').read_text())}),flush=True)
if __name__=='__main__':main()
