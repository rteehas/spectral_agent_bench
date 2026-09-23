"""Evaluator-side numerical checks. Never include this or verification/ in agent inputs."""
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd


def compare_q1_spectrum(actual, reference, limits):
    """Compare physical features after resampling, without fitting shifts/scales."""
    for name, table in [('candidate', actual), ('reference', reference)]:
        if not {'energy_eV', 'intensity'}.issubset(table):
            raise AssertionError(name+': missing energy_eV or intensity')
        values=table[['energy_eV','intensity']].to_numpy(dtype=float)
        if len(values)<3 or not np.isfinite(values).all():
            raise AssertionError(name+': need finite spectral samples')
        if not (np.diff(values[:,0])>0).all():
            raise AssertionError(name+': energy must be strictly increasing')
    x=actual.energy_eV.to_numpy(dtype=float);y=actual.intensity.to_numpy(dtype=float)
    rx=reference.energy_eV.to_numpy(dtype=float);ry=reference.intensity.to_numpy(dtype=float)
    margin=limits['boundary_margin_eV']
    core=(rx>=rx[0]+margin-1e-9)&(rx<=rx[-1]-margin+1e-9)
    grid=rx[core];target=ry[core]
    if x[0]>grid[0]+1e-9 or x[-1]<grid[-1]-1e-9:
        raise AssertionError('Spectrum omits the required interior energy range')
    sampled=np.interp(grid,x,y)
    scale=float(np.ptp(target))
    if scale<=0:raise AssertionError('Invalid reference spectrum')
    shape_error=float(np.sqrt(np.mean((sampled-target)**2))/scale)
    if shape_error>limits['maximum_normalized_rmse']:
        raise AssertionError(f'Spectral shape error {shape_error:.6g} exceeds tolerance')
    metrics={'candidate_points':len(x),'reference_points':len(rx),
             'comparison_range_eV':[float(grid[0]),float(grid[-1])],
             'normalized_rmse':shape_error,'edge_features':{}}
    for edge,(lo,hi) in limits['edge_windows_eV'].items():
        mask=(grid>=lo)&(grid<=hi);ex=grid[mask];a=sampled[mask];b=target[mask]
        peak_delta=float(abs(ex[a.argmax()]-ex[b.argmax()]))
        height_error=float(abs(a.max()/b.max()-1))
        area_error=float(abs(np.trapz(a,ex)/np.trapz(b,ex)-1))
        if peak_delta>limits['maximum_peak_energy_error_eV']+1e-9:
            raise AssertionError(edge+': peak position differs')
        if max(height_error,area_error)>limits['maximum_relative_feature_error']:
            raise AssertionError(edge+': peak height or integrated intensity differs')
        metrics['edge_features'][edge]={'peak_energy_error_eV':peak_delta,
            'relative_peak_height_error':height_error,'relative_area_error':area_error}
    return metrics


def check(actual,expected,path,tolerance):
    if isinstance(expected,dict):
        if not isinstance(actual,dict):raise AssertionError(path+': expected an object')
        for k,v in expected.items():
            if k not in actual:raise AssertionError(path+': missing '+k)
            check(actual[k],v,path+'.'+k,tolerance)
    elif isinstance(expected,list):
        if not isinstance(actual,list) or len(actual)!=len(expected):raise AssertionError(path+': wrong list length')
        for i,(a,e) in enumerate(zip(actual,expected)):check(a,e,f'{path}[{i}]',tolerance)
    elif isinstance(expected,(int,float)) and not isinstance(expected,bool):
        if isinstance(actual,bool) or not isinstance(actual,(int,float)) or not math.isfinite(actual):raise AssertionError(path+': expected a finite number')
        limit=0 if isinstance(expected,int) else tolerance
        if not math.isclose(actual,expected,rel_tol=0,abs_tol=limit):raise AssertionError(f'{path}: {actual} != {expected} (atol={limit})')
    elif actual!=expected:raise AssertionError(f'{path}: {actual!r} != {expected!r}')


def verify(question,output,truth):
    if not (output/'plot.png').is_file():raise AssertionError('Missing requested plot.png')
    tolerance=.05 if question=='Q7' else 1e-9
    expected=json.loads((truth/'expected.json').read_text());actual=json.loads((output/'result.json').read_text())
    if question=='Q1':
        check(actual,{key:expected[key] for key in ['material_id','site_weights']},'result',1e-8)
        if set(actual['site_weights'])!=set(expected['site_weights']):
            raise AssertionError('Site weights must describe the supplied Cu sites')
        table=pd.read_csv(output/'spectrum.csv');reference=pd.read_csv(truth/'spectrum.csv')
        if actual.get('points')!=len(table):raise AssertionError('points must match the supplied table length')
        limits=json.loads((truth/'comparison_policy.json').read_text())
        metrics=compare_q1_spectrum(table,reference,limits)
        return {'question':question,'numeric_pass':True,'spectrum_comparison':metrics,
                'plot_present':True,'interpretation_and_visual_review':
                'Required: justify edge combination, site multiplicities and interpolation/boundary treatment. Thresholds are benchmark screening choices, not physical uncertainty estimates; other defensible methods require reviewer adjudication.'}
    check(actual,expected,'result',tolerance)
    comparisons=[]
    for file in truth.glob('*.csv'):
        a=pd.read_csv(output/file.name);e=pd.read_csv(file)
        if len(a)!=len(e):raise AssertionError(file.name+': row count differs')
        for col in e:
            if col not in a:raise AssertionError(file.name+': missing column '+col)
            if pd.api.types.is_numeric_dtype(e[col]):
                if not np.isfinite(a[col].to_numpy(dtype=float)).all():raise AssertionError(file.name+': nonfinite values')
                np.testing.assert_allclose(a[col],e[col],rtol=1e-7,atol=1e-8,err_msg=file.name+' '+col)
            elif not a[col].astype(str).equals(e[col].astype(str)):raise AssertionError(file.name+': identity/order mismatch '+col)
        comparisons.append({'file':file.name,'rows':len(e),'columns':list(e.columns)})
    return {'question':question,'numeric_pass':True,'compared_tables':comparisons,'plot_present':(output/'plot.png').is_file(),'interpretation_and_visual_review':'Required separately; numeric checks do not assess scientific prose or plot readability.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('question');p.add_argument('--output',type=Path,required=True);p.add_argument('--truth',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(verify(a.question,a.output,a.truth),indent=2))
    except (AssertionError,KeyError,OSError,ValueError,TypeError) as e:raise SystemExit('Verification failed: '+str(e))
if __name__=='__main__':main()
