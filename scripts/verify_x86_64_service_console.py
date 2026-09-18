"""Finite visible-worktree gate execution and immutable service-console evidence."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,subprocess,sys,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'build/codex-agent/r83au-service-console'
BASE=PARENT/'scoped-start-fix'
REUSED_GATES=(2,3,4,5,6,7,9)
PROOF_ONLY={'automation/reist-s03b.toml','docs/architecture/NATIVE_SERVICE_CONSOLE_CONTRACT.md',
    'scripts/run_qemu_x86_64_service_console.py','scripts/verify_x86_64_service_console.py',
    'test/test_x86_64_service_console.py'}
IMAGE=PARENT/'native/x86_64/reist-x86_64-bootstrap.elf'
PRIOR=ROOT/'build/codex-agent/r83at-shell/buffered/verification-status-shell-final.json'
PRIOR_SHA='3de19c4a29ad2a0dc8e722848eedd9f9c32aee65b1d73169044556d55624de1f'
BASELINE='473da11c2eb37131e4cbc9019f1b06699fa13028'

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2,sort_keys=True)

def binding():
    f=read(BASE/'frozen.json')
    verify_files(f['retained']);verify_files(f['artifacts'])
    need(digest(PARENT/'adapter-fix/stopped.json')=='57f6c09e71eb1361a4d8a2d013aa7f5defb9ad225388249edf878c31b82cdecb','service console preserved schema stop')
    need(digest(PARENT/'verification-status-service-console-blocked.json')=='1956c56b3c9764f965444585a6063262f97ae4e5372d530274065c4d71e00148','service console preserved scope stop')
    need(digest(PARENT/'label-fix/stopped.json')=='aeecc5cbc6c81d566f10b41ae28f80ef2c58f305f8a0976df3c9dc82eae5d61b','service console preserved size failure')
    need(digest(PARENT/'frozen.json')=='154f21cba84c376a1de19af1be3e2d5eeb2b96b29bb8900640a9d96f46f2c3d7','service console original frozen candidate')
    stopped=read(PARENT/'stopped.json')
    need(stopped['failed_gate']==1 and stopped['new_images']==0 and stopped['matrix']==[] and
         link(ROOT/stopped['result']['log']['path'])==stopped['result']['log'],'service console retained first stop')
    need(git('rev-parse','HEAD')==f['head'],'service console frozen HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    need(queue['active_id']=='R8.3au-service-console' and queue['packages'][0]==f['package'],'service console frozen queue')
    verify_files(f['sources']);verify_files(f['tools'])
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(f['changed']) and changed<=set(f['package']['allowed_files']),'service console exact scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'service console clean staging/whitespace')
    need(hashlib.sha256(json.dumps(f['sources'],sort_keys=True).encode()).hexdigest()==f['candidate'],'service console candidate hash')
    return f


def reuse_sources(previous,current):
    need(set(previous)==set(current),'service console reuse exact input inventory')
    need({n for n in previous if previous[n]!=current[n]}<=PROOF_ONLY,'service console reuse production/source drift')


def reuse(n,f):
    need(n in REUSED_GATES,'service console explicit reusable obligation')
    old=read(PARENT/'proof-fix/frozen.json');reuse_sources(old['sources'],f['sources'])
    need(old['tools']==f['tools'] and old['head']==f['head'],'service console reuse tools/head')
    path=PARENT/'proof-fix'/f'gate-{n:02d}.json';receipt=read(path)
    need(receipt['passed'] and receipt['exit_code']==0 and receipt['candidate']==old['candidate'] and
         receipt['command']==old['commands'][n-1]==f['commands'][n-1], 'service console reusable exact successful command')
    need(link(ROOT/receipt['log']['path'])==receipt['log'],'service console original successful log')
    if n==9:need(receipt['image']==link(IMAGE),'service console exact built image')
    return dict(receipt,candidate=f['candidate'],reused_from=link(path),execution='exact-bound-reuse')

def disabled(source,macro,asm=False):
    """Project only the explicit opt-in block, preserving every other byte."""
    begin='%ifdef '+macro if asm else '#ifdef '+macro
    alternate='#if '+macro
    lines=source.splitlines(keepends=True);out=[];i=0
    while i<len(lines):
        if lines[i].strip() not in (begin,alternate):out.append(lines[i]);i+=1;continue
        i+=1;depth=1;take=False
        while depth:
            line=lines[i];word=line.strip();i+=1
            if word.startswith(('%if','#if')):depth+=1
            if word in ('%endif','#endif'):depth-=1
            if depth==1 and word in ('%else','#else'):take=True;continue
            if depth and take:out.append(line)
    return ''.join(out)

def defaults():
    f=binding();need(digest(PRIOR)==PRIOR_SHA,'service console accepted AT pin')
    old=read(PRIOR);need(old['accepted'] and old['clean_worktree'],'service console accepted predecessor')
    verify_files(old['evidence_sha256']);verify_files(old['tools'])
    allowed=set(f['package']['allowed_files'])
    for name in git('ls-tree','-r','--name-only',BASELINE).splitlines():
        if name not in allowed:
            # Git compares tracked files in one bounded command below.
            continue
    changed=set(git('diff','--name-only',BASELINE).splitlines())
    need(changed<=allowed,'service console baseline scope')
    for name in ('arch/x86_64/proc/process_run.inc','arch/x86_64/kernel/bootstrap_core.c',
                 'arch/x86_64/user/live_file.c','arch/x86_64/user/file_program.c'):
        before=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=10).decode('utf-8').replace('\r\n','\n')
        after=disabled((ROOT/name).read_text(encoding='utf-8'),'REIST_NATIVE_SERVICE_CONSOLE',name.endswith('.inc'))
        if name.endswith('bootstrap_core.c'):
            after=after.replace('#define NATIVE_SERVICE_ROOT_MASK NATIVE_RUN_MASK\n','').replace('NATIVE_SERVICE_ROOT_MASK','NATIVE_RUN_MASK')
        need(before==after,'service console exact disabled source '+name)
    return dict(passed=True,prior=link(PRIOR),unchanged_child_profile=True,unchanged_uart_mediator=True)

def review():
    import run_qemu_x86_64_service_console as run
    f=binding()
    for n in range(1,12):need(read(BASE/f'gate-{n:02d}.json')['passed'],'service console previous gate')
    paths=list((BASE/'guests').glob('attempt-*/summary.json'));need(len(paths)==1,'service console unique matrix')
    summary=read(paths[0]);need(summary['passed'] and summary['closed'] and summary['candidate']==f['candidate'] and
                              summary['image']==link(IMAGE),'service console qualified matrix')
    need([(r['case'],r['layout'],r['ram'],r['point']) for r in summary['cases']]==list(run.CASES),'service console all25 cases')
    need(summary['guest_elapsed']<=1125 and summary['elapsed']<=1200,'service console aggregate bound')
    config,counts,raw=run.live.image_config(IMAGE);evidence={}
    for row in summary['cases']:
        need(row['passed'] and 0<row['elapsed']<=45,'service console guest bound');folder=ROOT/row['folder']
        serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
        run.validate(serial,trace,row['case'],row['layout'],row['oom'],counts,raw,
                     (folder/run.live.cpu.CPU_FILE).read_bytes(),(folder/'cpu-trace-v1.bin').read_bytes())
        metrics=read(folder/'capture-metrics.json')
        need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
             metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','service console cleanup')
        dumps=run.live.cpu.binary_capacity(folder)
        extra=[folder/run.live.cpu.CPU_FILE,folder/'cpu-trace-v1.bin']
        need(len(dumps)+2<=2048 and sum(r['bytes'] for r in dumps)+sum(p.stat().st_size for p in extra)<=128*1024*1024,
             'service console full raw aggregate')
        need([r['equivalence'] for r in dumps if r['equivalence'] is not None]==['kernel','high'],'service console independent transport equality')
        for n,row in enumerate(dumps,1):
            path=folder/'binary-memory'/row['file']
            need(row['sequence']==n and path.name==f'ram-{n:04d}.bin' and path.stat().st_size==row['bytes'] and
                 digest(path)==row['sha256'],'service console raw bytes')
        for path in folder.rglob('*'):
            if path.is_file():need(not path.is_symlink(),'service console symlink');evidence[path.relative_to(ROOT).as_posix()]=digest(path)
    return dict(passed=True,cases=25,image=link(IMAGE),matrix=link(paths[0]),evidence_sha256=evidence)

def freeze():
    need(not (BASE/'frozen.json').exists(),'service console no refreeze')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=queue['packages'][0]
    need(queue['active_id']==p['id']=='R8.3au-service-console' and p['status']=='active','service console active package')
    previous=read(ROOT/'build/codex-agent/r83at-shell/buffered/frozen.json')
    names=set(previous['sources'])|set(p['allowed_files'])
    # Include all kernel/build/SDK/test transitive sources, not just edited paths.
    names.update(n for n in git('ls-files').splitlines() if n.startswith(('arch/x86_64/','userspace/','config/','scripts/','test/')))
    names={n for n in names if (ROOT/n).is_file()}
    sources={n:digest(ROOT/n) for n in sorted(names)}
    tools=previous['tools'];verify_files(tools)
    changed=sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
    need(set(changed)<=set(p['allowed_files']),'service console candidate scope')
    for name in changed:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write((ROOT/name).read_bytes())
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==12,'service console12 gates')
    old=read(PARENT/'proof-fix/frozen.json');reuse_sources(old['sources'],sources)
    diagnostic=read(PARENT/'cpu-diagnostic/frozen.json')
    artifacts=diagnostic['artifacts'];verify_files(artifacts)
    need(digest(IMAGE)=='8adc4814f311e951e3b5e0a66a62c35285bad9e711c9d78caf899f708587a0aa','service console unchanged qualified build')
    retained={}
    for folder in (PARENT/'proof-fix',PARENT/'cpu-diagnostic',PARENT/'observer-control',PARENT/'scoped-observer'):
        for path in folder.rglob('*'):
            if path.is_file():retained[path.relative_to(ROOT).as_posix()]=digest(path)
    save(BASE/'frozen.json',dict(head=git('rev-parse','HEAD'),package=p,commands=commands,changed=changed,
        sources=sources,tools=tools,retained=retained,artifacts=artifacts,
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=1,guests=4,guest_elapsed=31.835290899995016),
        reserved=dict(builds=0,guests=25,guest_seconds=45,total_guest_seconds=1125),
        red='Actual old descriptor admission failed test/x86_64_service_console_host.c line20 before implementation; retained r83p-retirement/SERVICE_CONSOLE_ADMISSION-* host log. Zero OS builds/guests.'))
    binding();print('SERVICE_CONSOLE_FROZEN',len(sources),flush=True)

def gates():
    f=binding();need(not list(BASE.glob('gate-*.json')),'service console no unchanged retry')
    for n,command in enumerate(f['commands'],1):
        binding();limit=300 if n<=7 else 1200 if n==10 else 180
        log=BASE/f'gate-{n:02d}.log';begin=time.monotonic();result=dict(passed=False,candidate=f['candidate'],command=command,limit=limit)
        try:
            if n in REUSED_GATES:
                result.update(reuse(n,f))
                with log.open('x') as output:output.write(json.dumps(result,indent=2))
            else:
                with log.open('xb') as output:
                    child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
                        timeout=limit,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                result.update(exit_code=child.returncode,passed=child.returncode==0,execution='fresh')
        except Exception as error:result['error']=str(error)
        result.update(elapsed=time.monotonic()-begin,log=link(log))
        if n==9 and IMAGE.exists():result['image']=link(IMAGE)
        save(BASE/f'gate-{n:02d}.json',result)
        print('SERVICE_CONSOLE_GATE',n,'PASS' if result['passed'] else 'FAIL',round(result['elapsed'],3),flush=True)
        if not result['passed']:
            save(BASE/'stopped.json',dict(frozen=link(BASE/'frozen.json'),failed_gate=n,result=result,
                new_images=0,previous_spent=f['previous_spent'],matrix=[link(p) for p in (BASE/'guests').glob('attempt-*/summary.json')]))
            print(log.read_text(errors='replace')[-3500:],flush=True);return 1
    return 0

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','review'):group.add_argument('--'+name,action='store_true')
    a=parser.parse_args()
    if a.freeze:freeze();return 0
    if a.gates:return gates()
    name='defaults' if a.defaults else 'review';begin=time.monotonic();result=dict(passed=False)
    try:
        result=defaults() if a.defaults else review();print('SERVICE_CONSOLE_'+name.upper()+'_OK');return 0
    except Exception as error:result['error']=str(error);print('SERVICE_CONSOLE_VERIFY_FAIL',error);return 1
    finally:
        result['elapsed']=time.monotonic()-begin;save(BASE/(name+'-'+uuid.uuid4().hex+'.json'),result)
if __name__=='__main__':raise SystemExit(main())
