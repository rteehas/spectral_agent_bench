"""Author-side execution audit: stage declared inputs, run candidates, verify separately."""
import argparse,datetime,importlib.util,json,os,shutil,subprocess,sys,time
from pathlib import Path
from export_agent_bundle import export,ROOT
DATA=ROOT/'docs/data/gleason-2024-cu-oxidation';WORKFLOW=DATA/'workflows'

def main():
    p=argparse.ArgumentParser();p.add_argument('--workdir',type=Path,required=True);p.add_argument('--questions',nargs='+',default=[f'Q{i}' for i in range(1,8)]);a=p.parse_args();a.workdir.mkdir(parents=True,exist_ok=True)
    reports=[]
    for q in a.questions:
        bundle=a.workdir/q;export(q,bundle);output=bundle/'output';env=dict(os.environ,MPLBACKEND='Agg',MPLCONFIGDIR=str(a.workdir/'mpl-cache'))
        cmd=[sys.executable,str(WORKFLOW/'candidate.py'),q,'--inputs',str((bundle/'inputs').resolve()),'--output',str(output.resolve())]
        start=time.monotonic();run=subprocess.run(cmd,cwd=bundle,env=env,text=True,capture_output=True)
        verify_cmd=[sys.executable,str(WORKFLOW/'verify.py'),q,'--output',str(output.resolve()),'--truth',str(WORKFLOW.parent/'verification'/q)]
        verified=subprocess.run(verify_cmd,cwd=bundle,env=env,text=True,capture_output=True) if run.returncode==0 else None
        trace={'run_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'passed' if verified and verified.returncode==0 else 'failed','candidate_exit_code':run.returncode,'verifier_exit_code':verified.returncode if verified else None,'wall_seconds':round(time.monotonic()-start,3),'tool_calls':[{'tool':'shell / Python','command':cmd,'stdout':run.stdout,'stderr':run.stderr},{'tool':'shell / evaluator Python','command':verify_cmd,'stdout':verified.stdout if verified else None,'stderr':verified.stderr if verified else None}],'candidate_input_access':'Candidate code only opens its staged inputs. This audit does not impose an OS/network sandbox; benchmark deployment must restrict evaluator/solution access.','input_files':sorted(x.name for x in (bundle/'inputs').iterdir())}
        path=WORKFLOW/(q+'.json');doc=json.loads(path.read_text());doc['execution']=trace;path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
        if trace['status']=='passed':
            retained=WORKFLOW/'outputs'/q
            shutil.copytree(output,retained,dirs_exist_ok=True)
            doc['execution']['retained_outputs']=[str(f.relative_to(ROOT/'docs')) for f in sorted(retained.iterdir()) if f.is_file()]
            path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
        reports.append({'question':q,'status':trace['status'],'wall_seconds':trace['wall_seconds']});print(json.dumps(reports[-1]),flush=True)
        if trace['status']=='failed':print(run.stderr,verified.stderr if verified else '',flush=True)
    summary_path=DATA/'verification/candidate_execution.json'
    previous=json.loads(summary_path.read_text()).get('questions',[]) if summary_path.exists() else []
    merged={x['question']:x for x in previous}
    merged.update({x['question']:x for x in reports})
    summary=list(sorted(merged.values(),key=lambda x:x['question']))
    summary_path.write_text(json.dumps({'questions':summary,'all_numeric_checks_passed':all(x['status']=='passed' for x in summary)},indent=2)+'\n')
    if not all(x['status']=='passed' for x in reports):raise SystemExit(1)
if __name__=='__main__':main()
