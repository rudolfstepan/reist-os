"""One frozen AX transaction, exact gates and immutable bounded evidence."""
from pathlib import Path
import argparse,hashlib,json,shlex,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
from verify_x86_64_service_console import disabled
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'build/codex-agent/r83ax-session-admission';BASE=PARENT/'candidate06'
REUSE=PARENT/'candidate05'
IMAGE=PARENT/'native-ipc-wait/x86_64/reist-x86_64-bootstrap.elf'
BASELINE='fee850d2'
PRIOR=ROOT/'build/codex-agent/r83aw-file-capture/candidate02/verification-status-file-capture-final.json'
PRIOR_SHA='bede32654369d5a3565cc5b1fbfef255855b0a32f66d50c9851285ca619045b1'
DOCS={'automation/reist-s03b.toml','docs/architecture/NATIVE_SESSION_ADMISSION_CONTRACT.md',
      'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,indent=2,sort_keys=True)

def changed():
    return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))

def prior():
    need(digest(PRIOR)==PRIOR_SHA,'AW receipt pin');old=read(PRIOR)
    need(old['accepted'] and old['clean_worktree'] and old['implementation_commit']=='e70c454c352eb69ad98467654449f3e2e22a44a7','accepted AW')
    verify_files(old['tools']);return old

def freeze():
    need(not (BASE/'frozen.json').exists(),'one fresh AX adapter window')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=queue['packages'][0]
    need(queue['active_id']==p['id']=='R8.3ax-session-admission' and p['status']=='active','AX active scope')
    old=prior();edits=changed();need(set(edits)<=set(p['allowed_files']),'AX changed scope')
    previous=REUSE;stop=previous/'stopped.json'
    need(digest(stop)=='495a62406ca27de452e899b1b8612298fdd4727091214e1e0cbeb15928718970','AX preserved runtime stop')
    stopped=read(stop);need(stopped['failed_gate']==7 and stopped['image']==link(IMAGE),'AX third image retained')
    need(digest(IMAGE)=='7b2f6a2f035ade5bdcd93990d8d733afbb0297940d0df5a2844cdf2303edb159','AX third image pin')
    matrix=read(ROOT/stopped['matrix']['path']);need(len(matrix['cases'])==15 and matrix['guest_elapsed']==209.75541709995014 and not matrix['passed'],'AX fifteen further spent guests')
    need(all(row['passed'] for row in matrix['cases'][:14]) and not matrix['cases'][14]['passed'],'AX exact passed prefix')
    diagnostic=PARENT/'diagnostic03/result.json'
    need(digest(diagnostic)=='63727a612e48b41fcda80fd4b661a29e7c28b6d78a24f9c4e23d89c23439f786','AX third diagnostic seal')
    diag=read(diagnostic);need(diag['closed'] and not diag['acceptance'] and diag['elapsed']==0.9575534000177868,'AX spent third diagnostic')
    previous_sources=read(previous/'frozen.json')['sources']
    permitted=DOCS|{'test/test_x86_64_session_admission.py','scripts/run_qemu_x86_64_session_admission.py',
        'scripts/verify_x86_64_session_admission.py'}
    verify_files({n:sha for n,sha in previous_sources.items() if n not in permitted})
    before=(previous/'sources/scripts/run_qemu_x86_64_session_admission.py').read_text(encoding='utf-8')
    observer=(ROOT/'scripts/run_qemu_x86_64_session_admission.py').read_text(encoding='utf-8')
    from run_qemu_x86_64_session_admission import pool
    projected=pool.helpers.once(observer,"Hook('scheduler_enter_task64.state_published',start)","Hook('process_run_resume64',start)")
    need(projected==before,'AX only early selector hook correction')
    names=set(git('ls-files').splitlines())|set(p['allowed_files'])
    sources={n:digest(ROOT/n) for n in sorted(names) if (ROOT/n).is_file()}
    for name in edits:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==9,'nine AX gates')
    retained={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/'build/codex-agent').glob('r83ax-before-*.log')}
    retained.update({p.relative_to(ROOT).as_posix():digest(p) for p in previous.rglob('*') if p.is_file()})
    for directory in (PARENT/'candidate01',PARENT/'candidate02',PARENT/'candidate03',PARENT/'candidate04',PARENT/'diagnostic01',PARENT/'diagnostic02',PARENT/'diagnostic03',PARENT/'native',PARENT/'native-retention',IMAGE.parent.parent):
        for path in directory.rglob('*'):
            if path.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in path.parts):retained[path.relative_to(ROOT).as_posix()]=digest(path)
    value=dict(head=git('rev-parse','HEAD'),package=p,changed=edits,sources=sources,tools=old['tools'],
        commands=commands,prior=link(PRIOR),retained=retained,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=3,guests=32,guest_seconds=452.6803156999813),reserved=dict(builds=0,guests=3,guest_seconds=30,total_guest_seconds=90))
    save(BASE/'frozen.json',value);binding();print('SESSION_FROZEN',len(sources),flush=True)

def binding():
    f=read(BASE/'frozen.json');need(git('rev-parse','HEAD')==f['head'],'AX frozen HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    need(queue['active_id']==f['package']['id'] and queue['packages'][0]==f['package'],'AX frozen contract')
    verify_files(f['sources']);verify_files(f['tools']);verify_files(f['retained'])
    need(changed()==f['changed'] and set(changed())<=set(f['package']['allowed_files']),'AX exact changed scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'AX whitespace/staging')
    need(digest(PRIOR)==PRIOR_SHA,'AX predecessor');return f

def defaults():
    binding();prior();names=[]
    def before(name):return subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=10).decode().replace('\r\n','\n')
    for name in ('arch/x86_64/proc/task_family.inc','arch/x86_64/kernel/bootstrap_core.c','arch/x86_64/user/task_pool.c'):
        after=disabled((ROOT/name).read_text(encoding='utf-8'),'REIST_NATIVE_SESSION',name.endswith('.inc'))
        need(after==before(name),'AX exact disabled source '+name);names.append(name)
    name='scripts/build-x86_64-bootstrap.ps1';after=(ROOT/name).read_text(encoding='utf-8')
    for line in ('    [switch]$NativeSession,\n','if ($NativeSession) { $NativeServiceCPU = [switch]$true }\n',
                 '        "X86_64_NATIVE_SESSION=$([int]$NativeSession.IsPresent)" `\n'):
        need(after.count(line)==1,'AX explicit PS addition');after=after.replace(line,'')
    need(after==before(name),'AX exact prior PS dispatch');names.append(name)
    name='scripts/build_x86_64_boot_programs.py';after=(ROOT/name).read_text(encoding='utf-8')
    for text in (',session=False',',a.session',
        "    if type(session) is not bool or session and not service_cpu:raise ValueError('session requires explicit device-free service CPU')\n",
        "    if session:cc=[*cc,'-DREIST_NATIVE_SESSION=1']\n","    p.add_argument('--session',action='store_true')\n",
        "             *(['-DREIST_SESSION_GUEST=1'] if session and n<2 else []),\n",
        "'test/x86_64_session_admission_host.c' if session and n<2 else ",
        "             *(['--wrap=main'] if session and n<2 else []),\n"):
        need(after.count(text)==1,'AX explicit producer addition');after=after.replace(text,'')
    need(after==before(name),'AX exact prior producer');names.append(name)
    name='Makefile';after=(ROOT/name).read_text(encoding='utf-8')
    block=after[after.index('X86_64_NATIVE_SESSION ?= 0\n'):after.index('X86_64_NATIVE_SERVICE_PIO ?=')]
    need(block.count('endif\n')==4 and 'requires explicit device-free NativeServiceCPU' in block,'AX Make profile admission')
    after=after.replace(block,'')
    for text in ('X86_64_SERVICE_CPU_FLAGS += $(if $(filter 1,$(X86_64_NATIVE_SESSION)),-DREIST_NATIVE_SESSION=1,)\n',
                 'X86_64_SESSION_ARG = $(if $(filter 1,$(X86_64_NATIVE_SESSION)),--session,)\n',' $(X86_64_SESSION_ARG)'):
        need(after.count(text)==1,'AX Make selector wiring');after=after.replace(text,'')
    need(after==before(name),'AX exact prior Make recipes');names.append(name)
    return dict(passed=True,exact_disabled_sources=names)

def profile(config):
    import run_qemu_x86_64_session_admission as run
    import struct
    inner=run.wide.payload.elf((IMAGE.parent/'reist-x86_64-c-core.elf').read_bytes(),64)
    symbol=inner['symbols']['native_session_profile_v1'];section=inner['sections']['.rodata']
    offset=symbol['value']-section['address']
    need(symbol['size']==40 and section['data'][offset:offset+40]==struct.pack('<5Q',1,40,0,8,1000),'AX boot witness')
    need(all(n in config['s'] for n in ('family_session_window','session_admission64','family_session_apply64')),'AX kernel symbols')

def cases():
    import run_qemu_x86_64_session_admission as run
    return [('cpu',case,ram) for case,ram in run.cpu.CASES]+[('cpu-fatal',k,4096) for k in run.cpu.FATAL_CASES]+[
        ('session',12,4096)]+[('session-fatal',k,4096) for k in run.FATAL_CASES]

def evaluate(row,folder,config):
    import run_qemu_x86_64_session_admission as run
    kind=row['kind'];serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
    if kind=='cpu':
        count=run.wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
        result=run.cpu.validate_capture(serial,trace,row['case'],row['oom'],count,sha,folder)
        dumps=run.cpu.binary_capacity(folder)
        need([v['equivalence'] for v in dumps if v['equivalence'] is not None]==['kernel','high'],'AX independent memory equality')
        return dict(tasks=len(result))
    if kind=='cpu-fatal':return dict(writes=run.cpu.validate_fatal(serial,trace,row['case'],folder))
    if kind=='session':return run.validate(serial,trace,folder,config)
    return dict(writes=run.validate_fatal(serial,trace,row['case'],folder))

def runtime():
    import run_qemu_x86_64_session_admission as run
    f=binding();need(not (BASE/'guests').exists(),'AX no guest retry')
    folder=BASE/'guests';folder.mkdir();config=run.pool.image_config(IMAGE);profile(config)
    count=run.wide.allocations(config['child_record']);begin=time.monotonic()
    summary=dict(passed=False,closed=False,candidate=f['candidate'],image=link(IMAGE),cases=[],guest_elapsed=0.0,reused=0)
    try:
        for kind,case,ram in cases():
            need(link(IMAGE)==summary['image'],'AX immutable common image')
            if kind in ('cpu','cpu-fatal'):
                source=read(REUSE/'guests/summary.json')['cases'][summary['reused']]
                need((source['kind'],source['case'],source['ram'])==(kind,case,ram) and source['passed'],'AX prefix reuse identity')
                out=ROOT/source['folder'];need(out.is_relative_to(REUSE/'guests'),'AX reuse path')
                need(source['proof']==evaluate(source,out,config),'AX unchanged raw prefix replay')
                row=dict(source,reused_from=link(REUSE/'guests/summary.json'))
                summary['cases'].append(row);summary['reused']+=1
                print('SESSION_GUEST_REUSE',kind,case,flush=True);continue
            out=folder/f'{kind}-{case}-{ram}';out.mkdir();oom={7:0,8:count//2,9:count-1}.get(case) if kind=='cpu' else None
            row=dict(kind=kind,case=case,ram=ram,oom=oom,folder=out.relative_to(ROOT).as_posix(),passed=False)
            summary['cases'].append(row);started=time.monotonic()
            try:
                if kind=='cpu':code=run.cpu.observer(config,out,case,oom)
                elif kind=='cpu-fatal':code=run.cpu.fatal_observer(config,out,case)
                elif kind=='session':code=run.observer(config,out)
                else:code=run.fatal_observer(config,out,case)
                run.transport.capture(IMAGE,out,code,ram,halt_witness='fatal' in kind,
                    binary_memory='equivalence' if kind=='cpu' else None,diagnostic_metrics=True,service_cpu_budget=True)
                row['proof']=evaluate(row,out,config);row['passed']=True
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed']
            need(row['elapsed']<=30 and summary['guest_elapsed']<=90,'AX inclusive guest budget')
            print('SESSION_GUEST_PASS',kind,case,round(row['elapsed'],3),flush=True)
        need(len(summary['cases'])==17 and summary['reused']==14 and time.monotonic()-begin<=600,'AX complete bounded matrix')
        summary['passed']=True;return dict(passed=True,matrix=(folder/'summary.json').relative_to(ROOT).as_posix())
    except Exception as error:summary['error']=str(error);raise
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-begin);save(folder/'summary.json',summary)

def review():
    import run_qemu_x86_64_session_admission as run
    f=binding();prior()
    for n in range(1,9):
        row=read(BASE/f'gate-{n:02d}.json')
        need(row['passed'] and row['candidate']==f['candidate'] and row['command']==f['commands'][n-1] and
             row['log']==link(ROOT/row['log']['path']),'AX exact passed gate')
    summary=read(BASE/'guests/summary.json');config=run.pool.image_config(IMAGE);profile(config)
    need(summary['passed'] and summary['closed'] and summary['candidate']==f['candidate'] and
         summary['image']==link(IMAGE) and summary['elapsed']<=600,'AX bound complete matrix')
    need([(r['kind'],r['case'],r['ram']) for r in summary['cases']]==cases(),'AX exact case coverage')
    need(summary['reused']==14 and summary['guest_elapsed']==sum(r['elapsed'] for r in summary['cases'] if 'reused_from' not in r)<=90,'AX guest ledger')
    evidence={}
    for row in summary['cases']:
        folder=ROOT/row['folder']
        if 'reused_from' in row:
            need(row['kind'] in ('cpu','cpu-fatal') and row['reused_from']==link(REUSE/'guests/summary.json') and folder.is_relative_to(REUSE/'guests'),'AX exact reused guest path')
        else:need(folder.is_relative_to(BASE/'guests'),'AX fresh guest path')
        need(row['passed'] and 0<row['elapsed']<=30 and row['proof']==evaluate(row,folder,config),'AX raw proof replay')
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
             metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','AX actual cleanup')
    for directory in (BASE/'guests',IMAGE.parent.parent):
        for path in directory.rglob('*'):
            if path.is_file() and not any(n in ('cache','zig-cache','.zig-cache') for n in path.parts):
                need(not path.is_symlink(),'AX evidence no link');evidence[path.relative_to(ROOT).as_posix()]=digest(path)
    return dict(passed=True,candidate=f['candidate'],image=link(IMAGE),matrix=link(BASE/'guests/summary.json'),
        evidence_sha256=evidence,builds=0,guests=17,fresh_guests=3,reused_guests=14,guest_elapsed=summary['guest_elapsed'])

def gates():
    f=binding();need(not list(BASE.glob('gate-*.json')),'AX no unchanged gate retry')
    for n,command in enumerate(f['commands'],1):
        binding();limit=300 if n<=4 else 600 if n==7 else 180
        log=BASE/f'gate-{n:02d}.log';started=time.monotonic();result=dict(passed=False,candidate=f['candidate'],command=command,limit=limit)
        try:
            with log.open('xb') as out:
                if n==6:
                    old=read(REUSE/'gate-06.json')
                    need(old['passed'] and old['command']==command and old['log']==link(ROOT/old['log']['path']),'AX exact build obligation reuse')
                    need(link(IMAGE)==read(REUSE/'guests/summary.json')['image'],'AX exact reused image')
                    out.write((ROOT/old['log']['path']).read_bytes())
                    result.update(passed=True,exit_code=0,reused_from=link(REUSE/'gate-06.json'))
                else:
                    child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    result.update(passed=child.returncode==0,exit_code=child.returncode)
        except Exception as error:result['error']=str(error)
        result.update(elapsed=time.monotonic()-started,log=link(log));save(BASE/f'gate-{n:02d}.json',result)
        print('SESSION_GATE',n,'PASS' if result['passed'] else 'FAIL',round(result['elapsed'],3),flush=True)
        if not result['passed']:
            matrix=BASE/'guests/summary.json'
            save(BASE/'stopped.json',dict(frozen=link(BASE/'frozen.json'),failed_gate=n,result=result,
                image=link(IMAGE) if IMAGE.exists() else None,matrix=link(matrix) if matrix.exists() else None))
            print(log.read_text(errors='replace')[-3500:],flush=True);return 1
    return 0

def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','runtime','review'):g.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.freeze:freeze();return 0
    if args.gates:return gates()
    name=next(n for n in ('defaults','runtime','review') if getattr(args,n));started=time.monotonic();result=dict(passed=False)
    try:result=globals()[name]();print('SESSION_'+name.upper()+'_PASS',flush=True);return 0
    except Exception as error:result['error']=str(error);print('SESSION_VERIFY_FAIL',repr(error),flush=True);return 1
    finally:result['elapsed']=time.monotonic()-started;save(BASE/(name+'-'+uuid.uuid4().hex+'.json'),result)

if __name__=='__main__':raise SystemExit(main())
