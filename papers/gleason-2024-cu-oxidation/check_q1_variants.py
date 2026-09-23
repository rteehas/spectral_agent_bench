"""Exercise Q1 grading with alternative valid numerics and scientifically wrong outputs."""
import importlib.util,json,shutil,tempfile
from pathlib import Path
import numpy as np,pandas as pd
from scipy.interpolate import PchipInterpolator
ROOT=Path(__file__).resolve().parents[2];DATA=ROOT/'docs/data/gleason-2024-cu-oxidation'
spec=importlib.util.spec_from_file_location('verifier',DATA/'workflows/verify.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


def alternative(step=.1, method='linear', trim=.0, weights=(.2,.8), include_l2=True):
    energy=np.arange(934.2+trim,988.6-trim+1e-8,step);signal=np.zeros(len(energy))
    for site,weight in zip([1,2],weights):
        for edge in (['L2','L3'] if include_l2 else ['L3']):
            raw=np.loadtxt(DATA/'inputs/Q1'/f'{edge}_{site:03d}_Cu_xmu.dat')
            use=(energy>=raw[0,0])&(energy<=raw[-1,0]);curve=np.zeros(len(energy))
            if method=='linear':curve[use]=np.interp(energy[use],raw[:,0],raw[:,3])
            else:curve[use]=PchipInterpolator(raw[:,0],raw[:,3])(energy[use])
            signal+=weight*curve
    return pd.DataFrame({'energy_eV':energy,'intensity':signal})


def main():
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix='gleason-q1-variants-') as temp:
        def attempt(name,table,expected_pass,weights=None):
            output=Path(temp)/name;output.mkdir();table.to_csv(output/'spectrum.csv',index=False)
            shutil.copyfile(DATA/'workflows/outputs/Q1/plot.png',output/'plot.png')
            result={'material_id':'mp-1077262','site_weights':weights or {'1':.2,'2':.8},'points':len(table)}
            (output/'result.json').write_text(json.dumps(result))
            try:
                metrics=v.verify('Q1',output,DATA/'verification/Q1')['spectrum_comparison'];passed=True;reason=None
            except AssertionError as e:
                metrics=None;passed=False;reason=str(e)
            assert passed==expected_pass,(name,passed,reason)
            outcomes.append({'variant':name,'expected_pass':expected_pass,'actual_pass':passed,'metrics':metrics,'rejection':reason})
        attempt('released_candidate',pd.read_csv(DATA/'workflows/outputs/Q1/spectrum.csv'),True)
        attempt('linear_zero_pad_0p05_eV',alternative(step=.05),True)
        attempt('linear_zero_pad_0p2_eV',alternative(step=.2),True)
        attempt('pchip_zero_pad_0p1_eV',alternative(method='pchip'),True)
        attempt('trimmed_endpoints',alternative(trim=.2),True)
        attempt('equal_site_weights',alternative(weights=(.5,.5)),False,{'1':.5,'2':.5})
        attempt('omitted_L2',alternative(include_l2=False),False)
        shifted=alternative();shifted.energy_eV+=1.;attempt('one_eV_shift',shifted,False)
        scaled=alternative();scaled.intensity/=scaled.intensity.max();attempt('unauthorized_peak_normalization',scaled,False)
        truncated=alternative();truncated=truncated[truncated.energy_eV<949.];attempt('L3_only_energy_range',truncated,False)
        attempt('five_eV_sampling',alternative(step=5.),False)
    report={'dataset_id':'spectral-agent-v3','all_checks_passed':True,'cases':outcomes,'scope':'Numerical evaluator tests. Plots are placeholders here; scientific/visual justification remains a separate review requirement. Tolerances are benchmark choices, not paper-derived uncertainty.'}
    (DATA/'verification/Q1/variant_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'accepted_valid_variants':sum(x['actual_pass'] for x in outcomes),'rejected_invalid_variants':sum(not x['actual_pass'] for x in outcomes),'all_checks_passed':True}))
if __name__=='__main__':main()
