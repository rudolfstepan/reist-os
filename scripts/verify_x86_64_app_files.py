"""One source-bound BC transaction, one image, sixteen finite guests, first failure stop."""
from pathlib import Path
import argparse,ast,hashlib,inspect,json,os,shlex,subprocess,time,tomllib
from concurrent.futures import ThreadPoolExecutor
import run_qemu_x86_64_app_files as guest
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83bc-application-files/candidate08'
PREVIOUS=BASE.parent/'candidate07'
OUTPUT=BASE.parent/'native-app-files-ipc'
IMAGE=OUTPUT/'x86_64/reist-x86_64-bootstrap.elf'
HEAD='2e05a01d'
PRIOR=ROOT/'build/codex-agent/r83bb-wide-shell-media/candidate02/verification-status-wide-shell-media-final.json'
PRIOR_SHA='496442d7a594b347915ad28313474ab6bec2728e84d80e74bd33acd61d7ae4d4'
LIMITS=(300,300,180,360,180,5400,180,300,180)
need=guest.require

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def evidence_hashes(names):
    names=list(names);need(len(names)<=50000,'BC bounded host archive inventory')
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(names,pool.map(lambda n:digest(ROOT/n),names)))
def link(path):return dict(path=Path(path).relative_to(ROOT).as_posix(),sha256=digest(path))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as out:json.dump(value,out,indent=2,sort_keys=True)
def git(*args):return subprocess.check_output(['git','-c','core.safecrlf=false',*args],cwd=ROOT,timeout=30).decode().strip()
def changed():
    return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3bc-application-files' and p['status']=='active','BC active package');return p
def sources():
    return {n:digest(ROOT/n) for n in sorted(set(git('ls-files').splitlines())|set(package()['allowed_files'])) if (ROOT/n).is_file()}
def retained():
    need(digest(PRIOR)==PRIOR_SHA,'BC accepted predecessor receipt')
    p=read(PRIOR);need(p['accepted'] and p['clean_worktree'] and
        p['implementation_commit']=='813606cf7f6fcd6eb42fe8e8a38658f8ce2cf0e7','BC accepted clean BB')
    for path,sha in p['tools'].items():need(digest(path)==sha,'BC predecessor tool '+path)
    for name in ('seal','commit_ready'):need(link(ROOT/p[name]['path'])==p[name],'BC retained predecessor '+name)
    allowed=set(package()['allowed_files'])
    for name,sha in p['sources'].items():
        if name not in allowed:need(digest(ROOT/name)==sha,'BC unchanged prerequisite '+name)
    for name,sha in p['artifacts'].items():need(digest(ROOT/name)==sha,'BC retained accepted artifact '+name)
    return p
def queue_scope():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    old=tomllib.loads(subprocess.check_output(['git','show',HEAD+':automation/reist-s03b.toml'],cwd=ROOT,timeout=30).decode())
    actual=q['packages'][0];expected=old['packages'][0]
    additions=['arch/x86_64/ipc/native_ipc.c','test/test_x86_64_ipc_cost.py','test/x86_64_ipc_cost_host.c']
    need(actual['allowed_files']==expected['allowed_files']+additions,'BC exact authorized IPC scope')
    actual['allowed_files']=expected['allowed_files']
    amended=[s.replace('no kernel source, syscall number',
        'only authorized native IPC EAGAIN publication optimization; no new syscall number') for s in expected['invariants']]
    need(actual['invariants']==amended,'BC exact amended IPC invariant');actual['invariants']=expected['invariants']
    for key,prefix in (
        ('relative_clock_proof_window','2026-09-20 candidate02:'),
        ('revocation_exit_proof_window','2026-09-20 candidate03:'),
        ('hang_exit_proof_window','2026-09-20 candidate04:'),
        ('budget_client_window','2026-09-20 candidate05:'),
        ('budget_buffer_window','2026-09-20 candidate06:'),
        ('stopped_budget_outcome','2026-09-20 candidate06:'),
        ('ipc_core_correction_window','2026-09-21 user ja mach weiter'),
        ('ipc_host_reference_window','2026-09-21:'),
        ('ipc_runtime_window','2026-09-21 candidate07:'),
        ('budget_enqueue_proof_window','2026-09-21 candidate08:')):
        need(actual.pop(key,'').startswith(prefix),'BC recorded bounded window '+key)
    need(q==old,'BC original nine gates, old queue and unchanged authorities')

def history():
    previous=BASE.parent/'candidate06'
    need(digest(previous/'stopped.json')=='05383adc4a8735d622bc545f120280c2fa7ed70ce9b4c3b614b5870cf5e49183',
        'BC preserve last failed quota attempt')
    original=read(previous/'frozen.json')
    files=dict(original['reused']['files'])
    need(evidence_hashes(files)==files,'BC unchanged complete historical raw archive')
    for n in range(1,7):
        folder=BASE.parent/('candidate%02d'%n)
        need(read(folder/'stopped.json')['failed_gate']==6 and not (folder/'gate-07.json').exists(),
            'BC all original first-failure stops')
    summary=read(previous/'runtime/summary.json')
    need(not summary['passed'] and summary['closed'] and len(summary['cases'])==16 and
        summary['guest_elapsed']==1588.3585832000244,'BC historical eighteen physical guests')
    files.update(evidence_hashes(p.relative_to(ROOT).as_posix() for p in previous.rglob('*') if p.is_file()))
    for n in (1,5,6):
        row=read(BASE.parent/('candidate%02d'%n)/'build.json')
        for name,sha in row['artifacts'].items():
            need(digest(ROOT/name)==sha,'BC preserve previous image/client '+name);files[name]=sha
    return files

def ipc_host_proof():
    folder=BASE.parent/'ipc-host-window';proof=read(folder/'passed.json')
    need(proof['passed'] and proof['sources']==read(folder/'frozen.json')['sources'],'BC complete IPC host manifest')
    state=sources()
    later={'automation/reist-s03b.toml','docs/architecture/NATIVE_APPLICATION_FILES_CONTRACT.md',
        'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md',
        'scripts/verify_x86_64_app_files.py','scripts/run_qemu_x86_64_app_files.py',
        'test/test_x86_64_app_files_runtime.py'}
    need(set(state)==set(proof['sources']) and
        {n for n in state if state[n]!=proof['sources'][n]}<=later,'BC exact tested IPC dependency sources')
    for name in ('native_ipc','bulk_ipc','ipc_completion','ipc_handoff'):
        row=read(folder/(name+'.json'))
        need(row['passed'] and row['returncode']==0 and 0<row['elapsed']<=600 and
            row['command']==['python','test/test_x86_64_'+name+'.py','-v'] and
            row['log']==link(folder/(name+'.log')),'BC actual IPC host result '+name)
    costs=BASE.parent/'ipc-cost-e34f83385808463186e7daf12b673c20'
    need(read(costs/'sources.json')['candidate']==digest(ROOT/'arch/x86_64/ipc/native_ipc.c'),
        'BC exact cost-tested adapter')
    transcript=(BASE.parent/'ipc-core-green2.log').read_text(encoding='utf-8')
    for opt in ('0','2'):
        for pool in ('0','1'):
            need('IPC_COST_EQUIVALENT O'+opt+' pool='+pool in transcript,'BC both optimizations/pools')
    need('Ran 1 test' in transcript and transcript.rstrip().endswith('OK'),'BC completed cost/fault test')
    files={p.relative_to(ROOT).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}
    files.update({p.relative_to(ROOT).as_posix():digest(p) for p in costs.iterdir() if
        p.is_file() and p.suffix in ('.json','.log','.c')})
    for name in ('ipc-core-red.log','ipc-core-green.log','ipc-core-green2.log'):
        p=BASE.parent/name;files[p.relative_to(ROOT).as_posix()]=digest(p)
    return files

def corrected_budget(state):
    need(digest(PREVIOUS/'stopped.json')=='bc602b09cd7e58a66eba4e637e03040fea2caf1bac7f3172230aaf9d404584fa' and
        not (PREVIOUS/'gate-07.json').exists(),'BC preserved actual candidate07 stop')
    old=read(PREVIOUS/'frozen.json')
    allowed={'automation/reist-s03b.toml','docs/architecture/NATIVE_APPLICATION_FILES_CONTRACT.md',
        'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md',
        'scripts/verify_x86_64_app_files.py','scripts/run_qemu_x86_64_app_files.py',
        'test/test_x86_64_app_files_runtime.py'}
    need(set(state)==set(old['sources']) and {n for n in state if state[n]!=old['sources'][n]}<=allowed,
        'BC unchanged complete image/client/production dependencies')
    name='scripts/run_qemu_x86_64_app_files.py'
    def functions(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef)}
    before=functions(PREVIOUS/'sources'/name);after=functions(ROOT/name)
    need(set(before)==set(after) and {n for n in before if before[n]!=after[n]}==
        {'qualified_outcome','validate_objects','run_matrix'},'BC unchanged actual observer/input/other predicates')
    for path,sha in old['tools'].items():need(digest(path)==sha,'BC exact capture tool '+path)
    built=read(PREVIOUS/'build.json')
    need(built['passed'] and built['builds']==1 and built['cumulative_builds']==2,'BC one actual replacement image')
    need(evidence_hashes(built['artifacts'])==built['artifacts'],'BC exact captured image artifacts')
    summary=read(PREVIOUS/'runtime/summary.json')
    need(not summary['passed'] and summary['closed'] and len(summary['cases'])==1 and
        summary['guest_elapsed']==80.74180430005072 and summary['cumulative_guests']==19 and
        summary['error']=='shell session BC actual 81st request rejected after revocation','BC exact omitted ordering')
    original=summary['cases'][0];need(not original['passed'] and not original['reused'],'BC retain original failed flag')
    label,case,layout,ram,_=guest.case_order(True)[0]
    need(tuple(original[k] for k in ('label','case','layout','ram'))==(label,case,layout,ram),'BC exact reuse member')
    module=guest.namespace(label);config,records,files=guest.image_config(IMAGE,label);module.app_files=files
    proof=module.evaluate(ROOT/original['folder'],config,records,(IMAGE.parent/'boot-programs.bin').read_bytes(),case,layout,files)
    return dict(original,passed=True,reused=True,original_passed=False,proof=proof)

def freeze():
    need(git('rev-parse','--short=8','HEAD')==HEAD and not BASE.exists(),'BC fresh corrected proof boundary')
    p=package();need(set(changed())<=set(p['allowed_files']),'BC scope before freeze')
    queue_scope();need(not git('diff','--cached','--name-only') and not git('diff','--check'),'BC index/whitespace')
    prior=retained();state=sources();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==len(LIMITS) and all((ROOT/n).is_file() for n in p['allowed_files']),'BC complete source/gate inventory')
    evidence=history();evidence.update(ipc_host_proof());reused=corrected_budget(state)
    evidence.update(read(PREVIOUS/'build.json')['artifacts'])
    evidence.update(evidence_hashes(p.relative_to(ROOT).as_posix() for p in PREVIOUS.rglob('*') if p.is_file()))
    client_prefix=guest.BUDGET_PROBE.relative_to(ROOT).as_posix()+'/'
    # Failed raw captures are archive only, never reused to qualify this image.
    # Fully bind them here and at final review, not between every fresh guest.
    active_evidence={n:sha for n,sha in evidence.items() if n.startswith(client_prefix) or
        Path(n).name in ('stopped.json','frozen.json','build.json','passed.json','sources.json') or
        n.startswith((PREVIOUS/'runtime/request-budget').relative_to(ROOT).as_posix()+'/') or
        n.startswith((BASE.parent/'ipc-host-window').relative_to(ROOT).as_posix()+'/') or
        n.startswith((BASE.parent/'ipc-cost-e34f83385808463186e7daf12b673c20').relative_to(ROOT).as_posix()+'/')}
    value=dict(head=git('rev-parse','HEAD'),package=p,sources=state,changed=changed(),commands=commands,limits=LIMITS,
        tools=prior['tools'],prior=link(PRIOR),matrix=guest.case_order(True),historical_files=evidence,
        active_evidence=active_evidence,reused_budget=reused,
        input_plans={s[0]:[[[due,raw.hex()] for due,raw in part] for part in guest.input_plan(s[0])] for s in guest.CASES},
        reserved=dict(builds=0,guests=15,guest_seconds=4500,per_guest_seconds=300,cleanup_seconds=3),
        previous=dict(builds=2,test_client_builds=2,guests=19,guest_seconds=1669.1003875000752),
        candidate=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest())
    save(BASE/'frozen.json',value)
    for name in changed():
        path=BASE/'sources'/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as out:out.write((ROOT/name).read_bytes())
    print('BC_FROZEN',value['candidate'],flush=True)
def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and sources()==f['sources'] and package()==f['package'] and
        changed()==f['changed'],'BC exact frozen source/queue/scope')
    for path,sha in f['tools'].items():need(digest(path)==sha,'BC exact frozen tool '+path)
    need(link(PRIOR)==f['prior'],'BC retained predecessor')
    need(evidence_hashes(f['active_evidence'])==f['active_evidence'],'BC retained active evidence')
    return f
def command(args,limit,log):
    started=time.monotonic();result=dict(command=list(args),passed=False)
    with log.open('xb') as out:
        proc=subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:result['returncode']=proc.wait(timeout=limit);result['passed']=result['returncode']==0
        except subprocess.TimeoutExpired:
            result['error']='absolute command deadline'
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=3)
            else:proc.kill()
            proc.wait(timeout=3)
        finally:result['elapsed']=time.monotonic()-started
    result['log']=link(log);return result
def dependencies():
    f=binding();retained();ipc_host_proof();original=guest.wide.namespace();module=guest.namespace('fat12')
    for name in ('validate_cpu','validate_image_start','validate_identity','validate_terminal',
                 'validate_ipc_delivery','validate_policy','validate_pio_records','validate_probe_steps'):
        need(ast.dump(ast.parse(inspect.getsource(getattr(module,name))))==
            ast.dump(ast.parse(inspect.getsource(getattr(original,name)))),'BC retained safety predicate '+name)
    from verify_x86_64_shell_session import default_projection
    need(default_projection(),'BC old defaults unchanged')
    save(BASE/'dependencies.json',dict(candidate=f['candidate'],passed=True,prior=PRIOR_SHA))
def build():
    f=binding();old=read(PREVIOUS/'build.json')
    need(old['passed'] and old['builds']==1 and old['cumulative_builds']==2,'BC existing replacement build')
    need(evidence_hashes(old['artifacts'])==old['artifacts'],'BC all exact existing image artifacts')
    guest.image_config(IMAGE,'request-budget')
    save(BASE/'build.json',dict(old,candidate=f['candidate'],builds=0,reused_from=link(PREVIOUS/'build.json')))

def image_binding():
    row=read(BASE/'build.json');need(row['passed'] and row['builds']==0 and row['cumulative_builds']==2 and
        row['reused_from']==link(PREVIOUS/'build.json') and row['image']==IMAGE.relative_to(ROOT).as_posix(),'BC exact reused replacement image')
    need(evidence_hashes(row['artifacts'])==row['artifacts'],'BC exact built artifacts')
    return row

def media_check():
    f=binding();built=image_binding();config,records,files=guest.image_config(IMAGE,'fat12')
    layouts=[]
    for layout in guest.media.LAYOUTS:
        raw=guest.media.image(layout,files);guest.verify_media(raw,layout,files)
        layouts.append(dict(layout=layout,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    need(set(records)==set(range(2,8)),'BC all ordinary tools and services prepared')
    save(BASE/'media.json',dict(candidate=f['candidate'],passed=True,layouts=layouts,image=built['artifacts'][IMAGE.relative_to(ROOT).as_posix()]))
def runtime():
    f=binding();image_binding()
    guest.run_matrix(IMAGE,BASE/'runtime',f['candidate'],binding,reused_budget=f['reused_budget'],budget_first=True)
def review():
    f=binding();image_binding();summary=read(BASE/'runtime/summary.json')
    need(evidence_hashes(f['historical_files'])==f['historical_files'],'BC complete historical archive unchanged')
    need(summary['passed'] and summary['closed'] and len(summary['cases'])==16 and
        summary['candidate']==f['candidate'] and summary['guest_elapsed']<=4800,'BC complete sixteen-case matrix')
    catalog=(IMAGE.parent/'boot-programs.bin').read_bytes();proofs=[]
    for row,spec in zip(summary['cases'],guest.case_order(True)):
        label,case,layout,ram,_=spec
        reuse=label=='request-budget';origin=PREVIOUS if reuse else BASE
        need(row['passed'] and tuple(row[k] for k in ('label','case','layout','ram'))==spec[:4] and
            row['reused']==reuse and 0<row['elapsed']<=300 and row['folder']==(origin/'runtime'/label).relative_to(ROOT).as_posix(),'BC exact successful case')
        module=guest.namespace(label);config,records,files=guest.image_config(IMAGE,label);module.app_files=files
        proof=module.evaluate(ROOT/row['folder'],config,records,catalog,case,layout,files)
        need(proof==row['proof'],'BC complete independent raw replay '+label);proofs.append(proof)
    save(BASE/'review.json',dict(candidate=f['candidate'],passed=True,proofs=proofs))
    files={p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
    files.update(f['historical_files'])
    save(BASE/'raw-hashes.json',files)
def scope():
    f=binding();retained();queue_scope()
    need(set(changed())<=set(f['package']['allowed_files']) and not git('diff','--check') and
        not git('diff','--cached','--name-only'),'BC final scope/index/whitespace')
    need(read(BASE/'review.json')['passed'],'BC full raw review before scope')
    save(BASE/'scope.json',dict(candidate=f['candidate'],passed=True,changed=changed()))
def all_gates():
    f=binding();need(not (BASE/'started.json').exists(),'BC single frozen execution')
    save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();row=command(shlex.split(cmd),limit,BASE/f'gate-{n:02d}.log')
        row.update(candidate=f['candidate'],gate=n);save(BASE/f'gate-{n:02d}.json',row)
        print('BC_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:
            save(BASE/'stopped.json',dict(candidate=f['candidate'],failed_gate=n,receipt=row))
            raise ValueError('BC first failed gate; no subsequent execution')
    save(BASE/'gates-passed.json',dict(candidate=f['candidate'],passed=True,gates=9))
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for flag in ('freeze','all','dependencies','build','media','runtime','review','scope'):g.add_argument('--'+flag,action='store_true')
    args=p.parse_args();action=next(k for k,v in vars(args).items() if v)
    {'freeze':freeze,'all':all_gates,'dependencies':dependencies,'build':build,'media':media_check,
        'runtime':runtime,'review':review,'scope':scope}[action]()
