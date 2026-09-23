"""Evaluator-side numerical checks. Never include this or verification/ in agent inputs."""
import argparse,json,math
from pathlib import Path
import numpy as np
import pandas as pd


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
    expected=json.loads((truth/'expected.json').read_text());actual=json.loads((output/'result.json').read_text());check(actual,expected,'result',tolerance)
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
