"""v09 entry point. Legacy transport is used only to invoke Codex, never to admit knowledge."""
import argparse
import copy
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import ksu
import reporting
import legacy_transport as transport
from e2_group_a import static_base_a_check
ROOT=Path(__file__).resolve().parents[1]
DISPLAY_MODE='short'

def read(p):return Path(p).read_text(encoding='utf-8')
def write(p,obj):Path(p).write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
def rows():
    with (ROOT/'manifest.csv').open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def group(r):return 'E3' if r['run_id'].startswith('E3') else ('E2' if r['run_id'].startswith('E2') else 'E1')
def policy(r):return json.loads(read(ROOT/'EPISODE_CONTROLS.json'))[r['run_id']]
def schema():return json.loads(read(ROOT/'schemas/checked_v09.schema.json'))
def check():
    frozen=json.loads(read(ROOT/'V09_SHA256.json'));problems=[]
    for name,sha in frozen.items():
        p=ROOT/name
        if not p.exists() or transport.sha_file(p)!=sha:problems.append('changed/missing: '+name)
    for r in rows():
        p=policy(r)
        if p['construction_allowed']!=(r['construction_allowed'].lower()=='true'):problems.append('construction control mismatch '+r['run_id'])
    print('Package integrity: '+('PASS' if not problems else 'FAIL'))
    for p in problems:print(p)
    return not problems

def prompt(r,ks):
    return (read(ROOT/'CHECKED_PROTOCOL.md')+'\n\nP0:\n'+read(transport.P0)+
            ('\n'+read(transport.P0_E3) if group(r)=='E3' else '')+
            '\nEPISODE_CONTROLS:\n'+json.dumps(policy(r))+'\nTASK:\n'+read(ROOT/r['task_file'])+
            '\nVISIBLE_KS:\n'+ks+ ('\nUNTRUSTED_META (not semantic support):\n'+read(ROOT/r['meta_file']) if r.get('meta_file') else '')+
            '\nReturn only the JSON specified by OUTPUT_SCHEMA. No external fact may enter the trace.')

def gate(r,ks,data):
    task=read(ROOT/r['task_file'])
    try:
        ksu.validate_schema(data,schema())
    except ksu.Invalid as exc:
        return {'decision':'REJECT','reason':str(exc),'ks_after':ks,'admitted':[],'proposal_decisions':[]}
    data=copy.deepcopy(data)
    for item in data['proposals']:
        item['description']={k:v for k,v in item['description'].items() if v != '' and v != []}
    result=ksu.evaluate(ks,task,r['task_id'],policy(r),data)
    if group(r)=='E2':
        static=static_base_a_check(ROOT/r['task_file'],r['task_id'])
        result['e2_static']=static
        if not static['formal_supported'] and result['decision'] in ('ACCEPT','NO_LOCAL_SOLUTION'):
            result.update(decision='REJECT' if data.get('outcome')=='SOLUTION' else 'NO_LOCAL_SOLUTION',
                          reason='E2 represented task fails independent structural/type checks',ks_after=ks,admitted=[],proposal_decisions=[])
    return result

def show_execution_error(out, post):
    print('\nCodex did not return a usable response.')
    print('Exit code:', post.get('codex_exit_code'))
    print('Run folder:', Path(out).resolve())
    if post.get('parse_error'):
        print('JSON parsing error:', post['parse_error'])
    for name in ('stderr.txt', 'stdout.txt'):
        p=Path(out)/name
        if p.exists():
            text=p.read_text(encoding='utf-8',errors='replace').strip()
            if text:
                print('\n'+name+' (last 30 lines):')
                print('\n'.join(text.splitlines()[-30:]))
    print('\nThe exit code alone does not identify the cause. The logs above are needed.')

def trial(r,ks,parent):
    out=parent/r['run_id'];task=read(ROOT/r['task_file'])
    displayed_task=reporting.task_lines(transport,r,policy(r),ksu.digest(ks))
    for line in displayed_task:print(line,flush=True)
    post,data,runtime=transport.execute_request(r['run_id'],prompt(r,ks),schema(),
        {'envelope_version':'v09','episode_controls':policy(r),'visible_ks_sha256':ksu.digest(ks),'task_sha256':ksu.digest(task)},
        lambda d:(isinstance(d,dict) and d.get('protocol')=='KS_CHECKED_V09',{'protocol':isinstance(d,dict) and d.get('protocol')=='KS_CHECKED_V09'}),out)
    (out/'TASK.txt').write_text('\n'.join(displayed_task)+'\n',encoding='utf-8')
    (out/'VISIBLE_KS.dspl').write_text(ks,encoding='utf-8');(out/'CURRENT_TASK.dspl').write_text(task,encoding='utf-8')
    if post.get('transport_status')!='READY_FOR_REVIEW':
        result={'decision':'EXECUTION_ERROR','reason':'model/transport failure','ks_after':ks,'admitted':[]}
        show_execution_error(out,post)
    else:result=gate(r,ks,data)
    after=result.pop('ks_after');(out/'KS_AFTER.dspl').write_text(after,encoding='utf-8')
    result.update(ks_before_sha256=ksu.digest(ks),ks_after_sha256=ksu.digest(after),episode_controls=policy(r))
    write(out/'KSU_RESULT.json',result)
    reporting.report(out,r,data,result,DISPLAY_MODE)
    transport.audit_zip(out)
    return after,result

def experiment(g,run_id=None,output_root=None):
    rs=[r for r in rows() if group(r)==g and (not run_id or r['run_id']==run_id)]
    if not rs:raise ValueError('unknown episode')
    parent=(output_root or ROOT/'runs')/('V09_'+g+'_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'));parent.mkdir(parents=True)
    ks=read(ROOT/rs[0]['ks_file']);summary=[]
    if run_id:write(parent/'MODE.json',{'mode':'isolated checkpoint test','persistent_curriculum_demonstration':False})
    failed=False
    for r in rs:
        # E2 is a fixed-state control; developmental E1/E3 consume actual KSU state.
        if g=='E2':ks=read(ROOT/r['ks_file'])
        before=ks
        ks,result=trial(r,ks,parent)
        # Expected controls may reject unsupported LLM proposals; distinguish that from proposer success.
        expected_control=(not policy(r)['construction_allowed'] and not policy(r)['insertion_allowed'])
        contained_control=expected_control and result['decision']=='REJECT' and not ksu.survivors(before,read(ROOT/r['task_file']),r['task_id'])
        result['proposer_status']='ACCEPTED' if result['decision']=='ACCEPT' else 'NO_LOCAL_SOLUTION' if result['decision']=='NO_LOCAL_SOLUTION' else 'REJECTED'
        result['experiment_status']='CONTROL_CONTAINED' if contained_control else result['decision']
        summary.append({'run_id':r['run_id'],**result})
        if result['decision']=='EXECUTION_ERROR' or (g!='E2' and result['decision'] not in ('ACCEPT','NO_LOCAL_SOLUTION') and not contained_control):
            failed=True;break
    write(parent/'SUMMARY.json',summary)
    readable=[]
    for row in rs:
        episode=parent/row['run_id']
        for filename in ('TASK.txt','MINIMAL_RESULT.txt'):
            p=episode/filename
            if p.exists():readable.append(read(p))
    (parent/'READER_SUMMARY.txt').write_text('\n'.join(readable),encoding='utf-8')
    print('Run summary:',(parent/'READER_SUMMARY.txt').resolve(),flush=True)
    return 4 if failed else 0

def main():
    global DISPLAY_MODE
    ap=argparse.ArgumentParser();ap.add_argument('--display',choices=['short','full'],default='short');ap.add_argument('--model');ap.add_argument('--reasoning-effort',default='medium');ap.add_argument('--proposer-profile',choices=['PAPER','LEGACY'])
    sub=ap.add_subparsers(dest='cmd');sub.add_parser('check');sub.add_parser('health');sub.add_parser('menu');sub.add_parser('full');sub.add_parser('all-experiments')
    exp=sub.add_parser('experiment');exp.add_argument('--id',required=True,choices=['E1','E2','E3']);exp.add_argument('--run-id')
    one=sub.add_parser('run');one.add_argument('--run-id',required=True)
    a=ap.parse_args()
    DISPLAY_MODE=a.display
    if not check():return 2
    if a.cmd=='check':return 0
    if a.model:transport.set_proposer_configuration(model=a.model,reasoning_effort=a.reasoning_effort,source='v09_cli')
    elif a.proposer_profile:transport.set_proposer_configuration(a.proposer_profile,source='v09_cli')
    else:transport.select_proposer_configuration_interactive()
    if a.cmd=='health':return transport.health()
    if a.cmd in (None,'menu'):
        g=input('Experiment E1 / E2 / E3: ').strip().upper();return experiment(g)
    if a.cmd=='experiment':return experiment(a.id,a.run_id)
    if a.cmd=='run':
        r=next(r for r in rows() if r['run_id']==a.run_id);return experiment(group(r),a.run_id)
    if a.cmd=='full':return experiment('E1')
    if a.cmd=='all-experiments':
        return max(experiment(g) for g in ('E1','E2','E3'))
    return 2
if __name__=='__main__':sys.exit(main())
