"""Finite BA transaction: freeze, run each gate once, retain every failure."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,subprocess,time,tomllib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'build/codex-agent/r83ba-wide-file/candidate12'
PARENT=BASE.parent
STOP=PARENT/'candidate11/stopped.json'
STOP_SHA='12842bf6de4f6a24fff803a99b18bd32352490a1078389a7143034be4cf72582'
REUSED_BUILD=STOP.parent/'build.json'
REUSED_BUILD_SHA='175026d37bd5762ffbc195413e7cb3c50bc76f64e1b7bbb63ac1899fe958af06'
REUSED_CANDIDATE='b9e55dc9371503127b100c63d5256af069a25c7d683156083318686abef95868'
BUILT=PARENT/'candidate03/build.json'
BUILT_SHA='f9fdbda37c2312dac7ad933a4c70f8494de2c64e1c396f2defc7b61eb3fa45d6'
PROOF_ONLY={'scripts/verify_x86_64_wide_file.py','scripts/run_qemu_x86_64_wide_file.py',
    'test/test_x86_64_wide_file_runtime.py','docs/architecture/NATIVE_WIDE_FILE_CONTRACT.md',
    'docs/development/CURRENT_WORK.md','docs/development/X86_64_COMPLETION_WORK_PAPER.md'}
HEAD='ccd6ff46'
PRIOR=ROOT/'build/codex-agent/r83az-shell-boot-media/candidate10/verification-status-shell-boot-media-final.json'
PRIOR_SHA='f38a35397b14d6073e5c99f289ab6d7ede550fd55348b6b3e1705731b169b79f'
LIMITS=(300,300,900,180,360,4800,180,180,180)

def need(value,message):
    if not value:raise ValueError('BA '+message)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,sort_keys=True)
def git(*args):return subprocess.check_output(['git','-c','core.safecrlf=false',*args],cwd=ROOT,timeout=30).decode().strip()
def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    p=q['packages'][0]
    need(q['active_id']==p['id']=='R8.3ba-wide-file' and p['status']=='active','active package')
    return p
def changed():
    return sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
def sources():
    names=set(git('ls-files').splitlines())|set(package()['allowed_files'])
    return {name:digest(ROOT/name) for name in sorted(names) if (ROOT/name).is_file()}
def pin_prior():
    need(digest(PRIOR)==PRIOR_SHA,'accepted AZ final receipt')
    p=read(PRIOR)
    need(p['accepted'] and p['clean_worktree'] and p['implementation_commit']=='5db38510b205d1a8fdcecc28bdf437fac5978212','accepted predecessor')
    for path,sha in p['tools'].items():need(digest(path)==sha,'tool identity '+path)
    return p
def freeze():
    need(git('rev-parse','--short=8','HEAD')==HEAD and not BASE.exists(),'fresh contract boundary')
    p=package();need(set(changed())<=set(p['allowed_files']),'scope before freeze')
    queue_scope()
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'unstaged clean whitespace')
    prior=pin_prior();state=sources();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(digest(STOP)==STOP_SHA and read(STOP)['failed_gate']==6,'preserved failed predecessor')
    need(not (STOP.parent/'gate-07.json').exists(),'first-failure stop')
    built_images(state);reuse=reused_evidence(replay=True)
    need(len(commands)==len(LIMITS),'nine frozen gates')
    need(all((ROOT/n).is_file() for n in p['allowed_files']),'complete candidate source inventory')
    value=dict(head=git('rev-parse','HEAD'),sources=state,package=p,commands=commands,limits=LIMITS,
        tools=prior['tools'],changed=changed(),prior=dict(path=str(PRIOR.relative_to(ROOT)),sha256=PRIOR_SHA),
        reused=reuse,
        reserved=dict(builds=0,new_guests=6,legacy_guests=18,guest_seconds=3210,cleanup_seconds=3),
        previous=dict(path=STOP.relative_to(ROOT).as_posix(),sha256=STOP_SHA,spent_builds=4,spent_guests=24,
            guest_seconds=1932.9222295999061,prelaunch_seconds=0.11856989999068901),
        candidate=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest())
    save(BASE/'frozen.json',value)
    for name in changed():
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as out:out.write((ROOT/name).read_bytes())
    print('WIDE_FILE_FROZEN',value['candidate'],flush=True)
def binding():
    f=read(BASE/'frozen.json')
    need(git('rev-parse','HEAD')==f['head'] and sources()==f['sources'],'exact frozen sources/head')
    need(package()==f['package'] and changed()==f['changed'],'exact queue and scope')
    for path,sha in f['tools'].items():need(digest(path)==sha,'exact frozen tool '+path)
    need(reused_evidence(replay=False)==f['reused'],'exact reused evidence binding')
    return f
def command(args,limit,log):
    log.parent.mkdir(parents=True,exist_ok=True);started=time.monotonic()
    result=dict(command=list(args),passed=False,elapsed=0)
    with log.open('xb') as out:
        proc=subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            result['returncode']=proc.wait(timeout=limit);result['passed']=result['returncode']==0
        except subprocess.TimeoutExpired:
            result['error']='absolute command deadline'
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=3)
            else:proc.kill()
            proc.wait(timeout=3)
        finally:result['elapsed']=time.monotonic()-started
    result.update(log=log.relative_to(ROOT).as_posix(),sha256=digest(log))
    return result
def legacy_hosts():
    f=binding();folder=BASE/'legacy-hosts';need(not folder.exists(),'one legacy host pass');folder.mkdir()
    rows=[];started=time.monotonic()
    try:
        for n,cmd in enumerate(f['package']['subsystem_host_tests']):
            remaining=min(300,880-(time.monotonic()-started));need(remaining>0,'legacy host aggregate deadline')
            row=command(shlex.split(cmd),remaining,folder/f'{n:02d}.log');rows.append(row)
            print('LEGACY_HOST',n,row['passed'],round(row['elapsed'],3),flush=True)
            need(row['passed'],'legacy host failure '+cmd)
    finally:save(folder/'summary.json',dict(commands=rows,elapsed=time.monotonic()-started))
def dependencies():
    f=binding();pin_prior()
    import run_qemu_x86_64_wide_file as runtime
    module=runtime.namespace()
    runtime.cpu_default_projection()
    import inspect
    need(inspect.getsource(module.validate_cpu).replace('sum(charges.values())<=262144',
        'sum(charges.values())<=2048')==inspect.getsource(runtime.old.validate_cpu),'exact CPU accounting except diagnostic count')
    for name in ('validate_image_start','validate_io_and_faults','validate_identity','validate_terminal','validate_ipc_delivery'):
        import ast,inspect
        need(ast.dump(ast.parse(inspect.getsource(getattr(module,name))))==
             ast.dump(ast.parse(inspect.getsource(getattr(runtime.old,name)))),'retained exact safety predicate '+name)
    save(BASE/'dependencies.json',dict(candidate=f['candidate'],passed=True,prior=PRIOR_SHA))
def images():
    return {n:PARENT/('wide-pacing' if n=='wide' else n)/'x86_64/reist-x86_64-bootstrap.elf' for n in ('wide','legacy')}

def block_legacy_projection():
    name='userspace/storage/lib/native_block.c';old=read(BUILT.parent/'frozen.json')
    archived=BUILT.parent/'sources'/name
    need(digest(archived)==old['sources'][name],'original block source pin')
    source=(ROOT/name).read_text()
    clause=('    /* Wide ready=1 retains the initial guard until a successful physical read.\n'
        '     * Rejected requests/failed waits charge attempts, never consume that guard.\n'
        '     * Legacy ready stays1 and its spacing remains100 throughout. */\n'
        '    unsigned pace=spacing==50 && s->ready==1?100:spacing;')
    update='    if(!status && spacing==50)s->ready=2;\n'
    need(source.count(clause)==source.count(update)==1,'exact wide first-read correction')
    source=source.replace(clause,'    unsigned pace=s->requests==1?100:spacing;').replace(update,'')
    need(source==archived.read_text(),'unchanged block code outside two wide-only spacing branches')
    # Both retained legacy wrappers pass spacing100, so both expressions are100
    # and neither ready update executes. Actual O0/O2 hosts check this path too.
    need('block_dispatch(s,b,q,reply,8,0,3000,100)' in source and
         'block_dispatch(s,b,q,reply,p->request_limit,p->deadline_ms,3000,100)' in source,
         'both legacy block entrypoints retain spacing100')
def original_images(state):
    old=read(BUILT.parent/'frozen.json')
    need(set(old['sources'])==set(state) and
         {n for n in state if state[n]!=old['sources'][n]}<=PROOF_ONLY|{
             'automation/reist-s03b.toml','arch/x86_64/proc/cpu_trace.inc',
             'userspace/storage/lib/native_block.c','test/x86_64_wide_file_host.c'},'built sources except diagnostic and proven wide-only pacing correction')
    import run_qemu_x86_64_wide_file as runtime
    runtime.cpu_default_projection();block_legacy_projection();queue_scope()
    need(digest(BUILT)==BUILT_SHA,'original successful build receipt')
    record=read(BUILT);rows=record['builds']
    need(record['candidate']==old['candidate'] and [r['name'] for r in rows]==['wide','legacy'],
         'complete two-image provenance')
    for row in rows:
        need(row['passed'] and row['returncode']==0 and digest(ROOT/row['log'])==row['sha256'],
             'successful bound build command/log')
        for path,sha in row['artifacts'].items():need(digest(ROOT/path)==sha,'exact build artifact '+path)
        need(digest(PARENT/row['name']/'x86_64/reist-x86_64-bootstrap.elf')==row['image'],'same original kernel image')
    for path,sha in old['tools'].items():need(digest(path)==sha,'same build tool '+path)
    return rows
def built_images(state):
    original=original_images(state);old=read(STOP.parent/'frozen.json')
    need(old['candidate']==REUSED_CANDIDATE and
         hashlib.sha256(json.dumps(old['sources'],sort_keys=True).encode()).hexdigest()==REUSED_CANDIDATE,
         'corrected-image frozen source identity')
    need(set(state)==set(old['sources']) and
         {n for n in state if state[n]!=old['sources'][n]}<=PROOF_ONLY|{'automation/reist-s03b.toml'},
         'no production changes since corrected image')
    need(digest(REUSED_BUILD)==REUSED_BUILD_SHA,'corrected-image build receipt')
    record=read(REUSED_BUILD);rows=record['builds']
    need(record['candidate']==REUSED_CANDIDATE and record['new_builds']==1 and
         [r['name'] for r in rows]==['wide','legacy'] and rows[1]==original[1],'complete corrected-image provenance')
    for row in rows:
        need(row['passed'] and row['returncode']==0 and digest(ROOT/row['log'])==row['sha256'],'bound build result/log')
        for path,sha in row['artifacts'].items():need(digest(ROOT/path)==sha,'same corrected artifact '+path)
        need(digest(images()[row['name']])==row['image'],'same corrected image')
    for path,sha in old['tools'].items():need(digest(path)==sha,'same corrected build tool '+path)
    return rows

def normal_collector_projection():
    import ast
    name='scripts/run_qemu_x86_64_wide_file.py';old=read(STOP.parent/'frozen.json')
    archived=STOP.parent/'sources'/name
    need(digest(archived)==old['sources'][name],'normal collector archived source')
    source=(ROOT/name).read_text()
    changes=[
        ('def namespace(*,full=False):\n    if type(full) is not bool:raise ValueError(\'wide explicit full selector\')',
         'def namespace():'),
        ("    if full:source=full_source(source);name+='_full';filename='<reist-wide-file-full>'\n",''),
        ('        self.wide_full=False\n',''),
        ('        limit=900 if self.wide_full else 300\n        remaining=self.started+limit-time.monotonic()\n'
         "        if not 0<remaining<=limit:raise ValueError('wide media absolute deadline')",
         '        remaining=self.started+300-time.monotonic()\n'
         "        if not 0<remaining<=300:raise ValueError('wide media absolute deadline')"),
        ('def bounded_fixture(folder,layout,app,started,*,full=False):\n'
         "    if type(full) is not bool:raise ValueError('wide explicit full fixture selector')",
         'def bounded_fixture(folder,layout,app,started):'),
        ('    fixture.wide_full=full\n','')]
    import run_qemu_x86_64_wide_file as run
    for before,after in changes:source=run.replace(source,before,after)
    def projection(text,exclude):
        tree=ast.parse(text)
        tree.body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name not in exclude]
        return ast.dump(tree)
    need(projection(source,{'run_matrix','configure_binary_full','full_source','reuse_prefix'})==
         projection(archived.read_text(),{'run_matrix'}),'exact normal collector and semantic replay projection')

def reused_evidence(*,replay):
    import run_qemu_x86_64_wide_file as run
    normal_collector_projection()
    summary_path=STOP.parent/'wide-guests/summary.json';summary=read(summary_path)
    need(summary['candidate']==REUSED_CANDIDATE and summary['closed'] and not summary['passed'] and
         len(summary['cases'])==7 and not summary['cases'][-1]['passed'] and
         summary['cases'][-1]['label']=='full','six pass then failed full; never reuse partial case')
    rows=summary['cases'][:6];run.reuse_prefix(rows)
    need(summary['image_sha256']==digest(images()['wide']),'reused current image')
    files={}
    for row in rows:
        folder=STOP.parent/'wide-guests'/row['label']
        need(ROOT/row['folder']==folder and folder.resolve()==folder,'original raw evidence location')
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                need(path.resolve().is_relative_to(folder),'raw evidence stays in original folder')
                files[path.relative_to(ROOT).as_posix()]=digest(path)
    for path in (STOP,STOP.parent/'frozen.json',REUSED_BUILD,summary_path):
        files[path.relative_to(ROOT).as_posix()]=digest(path)
    need(files[STOP.relative_to(ROOT).as_posix()]==STOP_SHA and
         files[REUSED_BUILD.relative_to(ROOT).as_posix()]==REUSED_BUILD_SHA,'preserved reuse receipts')
    if replay:
        module=run.namespace();config,records,app=module.image_config(images()['wide'])
        catalog=(images()['wide'].parent/'boot-programs.bin').read_bytes()
        for row in rows:
            need(module.evaluate(ROOT/row['folder'],config,records,catalog,row['case'],row['layout'],app)==row['proof'],
                 'complete original raw replay '+row['label'])
            print('BA_REUSED_RAW_PASS',row['label'],flush=True)
    return dict(rows=rows,files=files,guest_seconds=sum(r['elapsed'] for r in rows),candidate=REUSED_CANDIDATE)

def build():
    f=binding();rows=built_images(f['sources'])
    save(BASE/'build.json',dict(candidate=f['candidate'],builds=rows,
        reused_from=REUSED_BUILD.relative_to(ROOT).as_posix(),new_builds=0))
def runtime():
    f=binding();builds=read(BASE/'build.json')['builds'];need(len(builds)==2 and all(r['passed'] for r in builds),'two admitted images')
    for row in builds:
        for path,sha in row['artifacts'].items():need(digest(ROOT/path)==sha,'exact build artifact '+path)
    import run_qemu_x86_64_wide_file as run
    run.run_matrix(images()['wide'],BASE/'wide-guests',f['candidate'],binding,reused=f['reused']['rows'])
    run.old.run_matrix(images()['legacy'],BASE/'legacy-guests',f['candidate'],binding)

def review():
    f=binding();import run_qemu_x86_64_wide_file as run
    proofs=[]
    for name in ('wide','legacy'):
        module=run.namespace() if name=='wide' else run.old
        image=images()[name];config,records,app=module.image_config(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
        summary=read(BASE/(name+'-guests')/'summary.json')
        need(summary['passed'] and summary['closed'] and len(summary['cases'])==(12 if name=='wide' else 18),'complete matrix '+name)
        for row in summary['cases']:
            need(row['passed'],'case passed before review')
            if name=='wide':module=run.namespace(full=row['full'])
            raw=app+bytes(524288-len(app)) if row.get('full') else app
            proof=module.evaluate(ROOT/row['folder'],config,records,catalog,row['case'],row['layout'],raw)
            need(proof==row['proof'],'complete independent raw replay '+row['folder']);proofs.append(proof)
    files={p.relative_to(ROOT).as_posix():digest(p) for p in BASE.rglob('*') if p.is_file()}
    files.update(f['reused']['files'])
    save(BASE/'review.json',dict(candidate=f['candidate'],passed=True,proofs=proofs,files=files))
def scope():
    f=binding();need(set(changed())<=set(f['package']['allowed_files']),'frozen scope')
    need(not git('diff','--check') and not git('diff','--cached','--name-only'),'whitespace and no staged implementation')
    queue_scope()
    save(BASE/'scope.json',dict(candidate=f['candidate'],passed=True,changed=changed()))
def queue_scope():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    oldq=tomllib.loads(subprocess.check_output(['git','show',HEAD+':automation/reist-s03b.toml'],cwd=ROOT).decode())
    active=q['packages'][0]
    need(active.pop('full_deadline_authority','').startswith('2026-09-20 renewed ja mach weiter approves ONLY full512KiB two-root host900s/observe897s/cleanup3s;'),
         'explicit full-only host deadline authority')
    need(active.pop('diagnostic_scope_authority','').startswith('2026-09-20 renewed ja mach weiter approves arch/x86_64/proc/cpu_trace.inc,'),
         'explicit diagnostic scope/build authority')
    need(active.pop('projection_scope_authority','').startswith('2026-09-20 renewed ja mach weiter explicitly approves ONLY adding '),
         'explicit two-adapter authority')
    additions=['scripts/verify_x86_64_shell_session.py','scripts/verify_x86_64_terminal.py','arch/x86_64/proc/cpu_trace.inc']
    need(active['allowed_files']==oldq['packages'][0]['allowed_files']+additions,'exact two-path scope extension')
    active['allowed_files']=oldq['packages'][0]['allowed_files']
    need(q==oldq,'no premature queue transition')
def all_gates():
    f=binding();need(not (BASE/'started.json').exists(),'single frozen execution')
    save(BASE/'started.json',dict(candidate=f['candidate'],commands=f['commands']))
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();row=command(shlex.split(cmd),limit,BASE/f'gate-{n:02d}.log')
        row.update(candidate=f['candidate'],gate=n);save(BASE/f'gate-{n:02d}.json',row)
        print('BA_GATE',n,'PASS' if row['passed'] else 'FAIL',round(row['elapsed'],3),flush=True)
        if not row['passed']:
            save(BASE/'stopped.json',dict(candidate=f['candidate'],failed_gate=n,receipt=row))
            raise ValueError('first failed gate; no subsequent execution')
    save(BASE/'gates-passed.json',dict(candidate=f['candidate'],passed=True,gates=9))
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for flag in ('freeze','all','legacy-hosts','dependencies','build','runtime','review','scope'):g.add_argument('--'+flag,action='store_true')
    a=p.parse_args()
    action=next(k for k,v in vars(a).items() if v)
    {'freeze':freeze,'all':all_gates,'legacy_hosts':legacy_hosts,'dependencies':dependencies,
     'build':build,'runtime':runtime,'review':review,'scope':scope}[action]()
