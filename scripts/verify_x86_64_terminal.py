"""One-image bounded terminal qualification with exclusive frozen receipts."""
from pathlib import Path
import argparse,hashlib,json,shlex,subprocess,time,tomllib,uuid
from verify_x86_64_task_pool import digest,read,link,git,need,verify_files
from verify_x86_64_service_console import disabled
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'build/codex-agent/r83av-terminal';BASE=PARENT/'candidate05'
IMAGE=PARENT/'native-descriptor-fix/x86_64/reist-x86_64-bootstrap.elf'
BASELINE='53dd42d54abd6bdcd3ed62a03143ddeced9205ce'
PRIOR=ROOT/'build/codex-agent/r83au-service-console/scoped-start-fix/verification-status-service-console-final.json'
PRIOR_SHA='8a2633907e2e0c4f7899641e16778f759021a58cfea452eedc8576f8f645cd07'
PREVIOUS=PARENT/'candidate03'
REUSE_BASE=PARENT/'candidate04'
PROOF_ONLY={'automation/reist-s03b.toml','docs/development/CURRENT_WORK.md',
    'scripts/run_qemu_x86_64_terminal.py','scripts/verify_x86_64_terminal.py','test/test_x86_64_terminal.py'}
REUSE=(2,3,4,5,6,7,8,10,11)

def same_production(old,new):
    need(set(old)==set(new) and {n for n in old if old[n]!=new[n]}<=PROOF_ONLY,'terminal exact transitive production inventory')

def reuse(n,f):
    need(n in REUSE,'terminal explicit reusable gate');old=read(REUSE_BASE/'frozen.json')
    same_production(old['sources'],f['sources']);need(old['tools']==f['tools'] and old['head']==f['head'],'terminal reuse tool/head identity')
    path=REUSE_BASE/f'gate-{n:02d}.json';row=read(path)
    need(row['passed'] and row['exit_code']==0 and row['candidate']==old['candidate'] and
         row['command']==old['commands'][n-1]==f['commands'][n-1] and row['log']==link(ROOT/row['log']['path']),'terminal exact successful prior command/log')
    if n==10:need(row['image']==link(IMAGE),'terminal exact reused image')
    if n==11:qualified_normal(f)
    return dict(row,candidate=f['candidate'],execution='exact-bound-reuse',reused_from=link(path))

def qualified_prefix(f):
    import run_qemu_x86_64_terminal as run
    old=read(PREVIOUS/'frozen.json');same_production(old['sources'],f['sources'])
    need(old['tools']==f['tools'],'terminal prefix exact tools')
    need(digest(PREVIOUS/'stopped.json')=='f45a7d42cf97faa6d2d5d25144442e8229e9e2aca0f341e8ccd0152b0d13074d','terminal preserved observer stop')
    stopped=read(PREVIOUS/'stopped.json');path=ROOT/stopped['matrix'][0]['path']
    need(link(path)==stopped['matrix'][0],'terminal previous matrix exact bytes');matrix=read(path)
    need(matrix['closed'] and not matrix['passed'] and matrix['candidate']==old['candidate'] and matrix['image']==link(IMAGE) and
         len(matrix['cases'])==7 and not matrix['cases'][-1]['passed'],'terminal six complete cases only')
    prefix=matrix['cases'][:6]
    need([(r['case'],r['layout'],r['ram'],r['point']) for r in prefix]==list(run.CASES[:6]) and
         all(r['passed'] and 0<r['elapsed']<=45 for r in prefix),'terminal exact healthy prefix')
    return [dict(row,reused_from=link(path),executed=False) for row in prefix]

def qualified_normal(f):
    import run_qemu_x86_64_terminal as run
    old=read(REUSE_BASE/'frozen.json');same_production(old['sources'],f['sources'])
    need(old['tools']==f['tools'],'terminal complete matrix tools')
    need(digest(REUSE_BASE/'stopped.json')=='0e9a3f8d294aae4393e0f441c74bbecbd7a34a7a1e4f000dc368b72193a682c5','terminal preserved fatal adapter failure')
    paths=list((REUSE_BASE/'guests').glob('attempt-*/summary.json'));need(len(paths)==1,'terminal one full normal matrix')
    need(link(paths[0]) in read(REUSE_BASE/'stopped.json')['matrix'],'terminal exact normal matrix receipt')
    matrix=read(paths[0])
    need(matrix['passed'] and matrix['closed'] and matrix['fatal'] is False and matrix['candidate']==old['candidate'] and
         matrix['image']==link(IMAGE) and len(matrix['cases'])==25 and matrix['new_guests']==19,'terminal complete normal success')
    need(matrix['cases'][:6]==qualified_prefix(f) and
         [(r['case'],r['layout'],r['ram'],r['point']) for r in matrix['cases']]==list(run.CASES) and
         all(r['passed'] and 0<r['elapsed']<=45 for r in matrix['cases']),'terminal exact complete normal coverage')
    return matrix

def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2,sort_keys=True)

def binding():
    f=read(BASE/'frozen.json');need(git('rev-parse','HEAD')==f['head'],'terminal frozen HEAD')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    need(queue['active_id']==f['package']['id']=='R8.3av-terminal-lease' and queue['packages'][0]==f['package'],'terminal frozen queue')
    verify_files(f['sources']);verify_files(f['tools'])
    need(digest(PRIOR)==PRIOR_SHA,'terminal accepted predecessor pin')
    changed=set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines())
    need(changed==set(f['changed']) and changed<=set(f['package']['allowed_files']),'terminal exact candidate scope')
    need(not git('diff','--cached','--name-only') and not git('diff','--check'),'terminal empty staging/whitespace')
    need(hashlib.sha256(json.dumps(f['sources'],sort_keys=True).encode()).hexdigest()==f['candidate'],'terminal candidate hash')
    return f

def prior():
    need(digest(PRIOR)==PRIOR_SHA,'terminal predecessor receipt pin');old=read(PRIOR)
    need(old['accepted'] and old['clean_worktree'],'terminal accepted clean predecessor')
    verify_files(old['evidence_sha256']);verify_files(old['tools'])
    return old

def without_wide_build_selector(source,make=False):
    """Exact disabled BA additions only; never mask surrounding/default drift."""
    from verify_x86_64_display import without_display_build_selector
    source=without_display_build_selector(source,make=make)
    from build_x86_64_app_files import without_app_build_selector
    source=without_app_build_selector(source,make=make)
    if make:
        parts=(
            'X86_64_NATIVE_WIDE_FILE ?= 0\n'
            'ifneq ($(words $(X86_64_NATIVE_WIDE_FILE)),1)\n'
            '$(error NativeWideFile selector must be one explicit value)\nendif\n'
            'ifneq ($(filter $(X86_64_NATIVE_WIDE_FILE),0 1),$(X86_64_NATIVE_WIDE_FILE))\n'
            '$(error NativeWideFile selector must be 0 or 1)\nendif\n'
            'ifeq ($(X86_64_NATIVE_WIDE_FILE),1)\n'
            'ifneq ($(X86_64_NATIVE_SHELL_SESSION),1)\n'
            '$(error NativeWideFile requires explicit NativeShellSession)\nendif\nendif\n',
            'X86_64_SERVICE_CPU_FLAGS += $(if $(filter 1,$(X86_64_NATIVE_WIDE_FILE)),-DREIST_NATIVE_WIDE_FILE=1,)\n',
            'X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_WIDE_FILE)),--wide-file,)\n')
    else:
        parts=('    [switch]$NativeWideFile,\n',
            'if ($NativeWideFile) { $NativeShellSession = [switch]$true }\n',
            '        "X86_64_NATIVE_WIDE_FILE=$([int]$NativeWideFile.IsPresent)" `\n')
    tokens=('NativeWideFile','NATIVE_WIDE_FILE','--wide-file')
    if not any(token in source for token in tokens):return source
    for part in parts:
        need(source.count(part)==1,'BA exact disabled build selector')
        source=source.replace(part,'')
    need(not any(token in source for token in tokens),'BA unexpected build selector use')
    return source

def default_sources():
    names=('arch/x86_64/proc/cooperative_scheduler.asm','arch/x86_64/proc/process_run.inc',
        'arch/x86_64/proc/task_family.inc','arch/x86_64/proc/native_console.inc',
        'arch/x86_64/user/service_console.c','arch/x86_64/user/live_file.c',
        'arch/x86_64/user/file_program.c','userspace/sdk/lib/x86_64/shell_platform.c')
    for name in names:
        before=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=10).decode('utf-8').replace('\r\n','\n')
        after=(ROOT/name).read_text(encoding='utf-8')
        # Versioned opt-in successors compose above AV, never replace the AU
        # reference. Everything outside these disabled branches remains exact.
        for macro in ('REIST_NATIVE_TERMINAL_SERVICE','REIST_NATIVE_INPUT','REIST_NATIVE_DISPLAY','REIST_NATIVE_SHELL_SESSION','REIST_NATIVE_SESSION','REIST_NATIVE_TERMINAL'):
            after=disabled(after,macro,name.endswith(('.inc','.asm')))
        need(before==after,'terminal exact disabled source '+name)
    name='scripts/build-x86_64-bootstrap.ps1'
    before=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=10).decode('utf-8').replace('\r\n','\n')
    after=without_wide_build_selector((ROOT/name).read_text(encoding='utf-8'))
    successors=(
        ('NativeShellSession',('    [switch]$NativeShellSession,\n',
            'if ($NativeShellSession) {\n'
            '    if ($NativeSession -or $NativeShell -or $NativeConsole -or $NativeServiceCPU) {\n'
            "        throw 'NativeShellSession excludes finite shell and device-free session fixtures.'\n"
            '    }\n    $NativeTerminal = [switch]$true\n}\n',
            '        "X86_64_NATIVE_SHELL_SESSION=$([int]$NativeShellSession.IsPresent)" `\n')),
        ('NativeSession',('    [switch]$NativeSession,\n',
            'if ($NativeSession) { $NativeServiceCPU = [switch]$true }\n',
            '        "X86_64_NATIVE_SESSION=$([int]$NativeSession.IsPresent)" `\n')))
    for selector,parts in successors:
        if '$'+selector not in after:continue
        for part in parts:
            need(after.count(part)==1,'terminal PS exact successor '+selector)
            after=after.replace(part,'')
        need('$'+selector not in after,'terminal PS unexpected successor use '+selector)
    for line in ('    [switch]$NativeTerminal,\n','if ($NativeTerminal) { $NativeServiceConsole = [switch]$true }\n',
                 '        "X86_64_NATIVE_TERMINAL=$([int]$NativeTerminal.IsPresent)" `\n'):
        need(after.count(line)==1,'terminal PS selector exact addition');after=after.replace(line,'')
    need(after==before,'terminal exact legacy PS dispatch')
    return list(names)+[name]

def defaults():
    f=binding();prior();names=default_sources()
    changed=set(git('diff','--name-only',BASELINE).splitlines())
    need(changed<=set(f['package']['allowed_files']),'terminal baseline allowed scope')
    gate=read(BASE/'gate-01.json');need(gate['passed'] and gate['candidate']==f['candidate'],'terminal producer/SDK/selector host proof')
    return dict(passed=True,prior=link(PRIOR),source_equality=names,producer_host=link(BASE/'gate-01.json'))

def review():
    import run_qemu_x86_64_terminal as run
    f=binding();prior();verify_files(f['retained'])
    for n in range(1,14):
        receipt=read(BASE/f'gate-{n:02d}.json')
        need(receipt['passed'] and receipt['candidate']==f['candidate'] and receipt['command']==f['commands'][n-1] and
             receipt['log']==link(ROOT/receipt['log']['path']),'terminal exact completed gates')
    config,counts,raw=run.live.image_config(IMAGE);evidence={};spent=0.0
    for fatal in (False,True):
        paths=list((BASE/'fatal' if fatal else REUSE_BASE/'guests').glob('attempt-*/summary.json'));need(len(paths)==1,'terminal unique qualification matrix')
        summary=read(paths[0]);need(summary['passed'] and summary['closed'] and summary['fatal']==fatal and
            summary['candidate']==(f['candidate'] if fatal else read(REUSE_BASE/'frozen.json')['candidate']) and summary['image']==link(IMAGE),'terminal qualified image/matrix')
        expected=[(k,2,4096,None) for k in run.FATAL_CASES] if fatal else list(run.CASES)
        prefix=[] if fatal else qualified_normal(f)['cases']
        need(summary['cases'][:len(prefix)]==prefix and summary['new_guests']==(2 if fatal else 19),'terminal full matrix exact reused/fresh partition')
        need([(r['case'],r['layout'],r['ram'],r['point']) for r in summary['cases']]==expected,'terminal full matrix order')
        need(summary['guest_elapsed']==sum(r['elapsed'] for r in summary['cases']) and summary['elapsed']<=(120 if fatal else 1200),'terminal matrix elapsed')
        spent+=summary['guest_elapsed']
        for row in summary['cases']:
            need(row['passed'] and 0<row['elapsed']<=45,'terminal per-guest deadline');folder=ROOT/row['folder']
            need(folder.is_relative_to(paths[0].parent) or row in prefix,'terminal bounded evidence path')
            serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
            if fatal:run.validate_fatal(serial,trace,row['case'],folder)
            else:run.validate(serial,trace,row['case'],row['layout'],row['oom'],counts,raw,folder)
            metrics=read(folder/'capture-metrics.json')
            need(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
                 metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','terminal capture cleanup')
            if not fatal:
                dumps=run.live.cpu.binary_capacity(folder)
                extras=[folder/run.live.cpu.CPU_FILE,folder/'cpu-trace-v1.bin',folder/run.LEDGER]
                need(len(dumps)+3<=2048 and sum(r['bytes'] for r in dumps)+sum(p.stat().st_size for p in extras)<=128*1024*1024,'terminal raw aggregate bounds')
                need([r['equivalence'] for r in dumps if r['equivalence'] is not None]==['kernel','high'],'terminal independent memory equality')
                for n,row in enumerate(dumps,1):
                    path=folder/'binary-memory'/row['file']
                    need(row['sequence']==n and path.name==f'ram-{n:04d}.bin' and path.stat().st_size==row['bytes'] and digest(path)==row['sha256'],'terminal actual binary bytes')
    need(spent<=1215,'terminal cumulative guest bound')
    for folder in (BASE,IMAGE.parent.parent):
        for path in folder.rglob('*'):
            if path.is_file():
                need(not path.is_symlink(),'terminal evidence no symlink')
                if path.name!='gate-14.log':evidence[path.relative_to(ROOT).as_posix()]=digest(path)
    fresh_spent=spent-qualified_normal(f)['guest_elapsed']
    need(fresh_spent<=90,'terminal fresh cumulative guest bound')
    return dict(passed=True,cases=27,builds=0,guest_elapsed=spent,image=link(IMAGE),evidence_sha256=evidence,
        reused_guests=25,fresh_guests=2,cumulative_builds=f['previous_spent']['builds'],
        cumulative_guests=f['previous_spent']['guests']+2,cumulative_guest_elapsed=f['previous_spent']['guest_elapsed']+fresh_spent)

def freeze():
    need(not (BASE/'frozen.json').exists() and digest(IMAGE)=='e2e9172277e67edcf0cbb932a6ba1d725e995ec48723d8f6c42135653c130e10','terminal new proof candidate, no build')
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));p=queue['packages'][0]
    need(queue['active_id']==p['id']=='R8.3av-terminal-lease' and p['status']=='active','terminal active package')
    previous=prior();names=set(previous['sources']) if 'sources' in previous else set()
    names.update(git('ls-files').splitlines());names.update(p['allowed_files'])
    names={n for n in names if (ROOT/n).is_file()}
    sources={n:digest(ROOT/n) for n in sorted(names)}
    import run_qemu_x86_64_terminal as run
    before=(PREVIOUS/'sources/scripts/run_qemu_x86_64_terminal.py').read_text(encoding='utf-8')
    after=(ROOT/'scripts/run_qemu_x86_64_terminal.py').read_text(encoding='utf-8')
    for name in ('decode_ledger','validate_terminal','validate','fatal_mutation','fatal_observer','validate_fatal'):
        need(run.live.function(before,name)==run.live.function(after,name),'terminal unchanged proof predicate '+name)
    scoped=(REUSE_BASE/'sources/scripts/run_qemu_x86_64_terminal.py').read_text(encoding='utf-8')
    need(scoped.split('FATAL_BODY=',1)[0]==after.split('FATAL_BODY=',1)[0],'terminal exact normal observer/oracle')
    old_body=scoped.split("FATAL_BODY=r'''",1)[1].split("'''",1)[0]
    need(old_body.replace('try:self.observe()','try:self.capture()').replace('    def observe(self):','    def capture(self):')==run.FATAL_BODY,'terminal fatal callback rename only')
    tools=previous['tools'];verify_files(tools)
    changed=sorted(set(git('diff','--name-only').splitlines())|set(git('ls-files','--others','--exclude-standard').splitlines()))
    need(set(changed)<=set(p['allowed_files']),'terminal candidate scope')
    for name in changed:
        target=BASE/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write((ROOT/name).read_bytes())
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==14,'terminal fourteen gates')
    retained={path.relative_to(ROOT).as_posix():digest(path) for path in PARENT.rglob('*') if path.is_file() and not path.is_relative_to(BASE)}
    # Only completed host/preflight logs, never this still-open freeze stdout.
    for path in (ROOT/'build/codex-agent').glob('terminal-*.log'):
        if 'freeze' not in path.name and 'gates' not in path.name:retained[path.relative_to(ROOT).as_posix()]=digest(path)
    need(digest(PARENT/'candidate01/frozen.json')=='8e759a9442d855d936072dc1dcd1f4af9f8d29c322141dd9618e55bf3c1f01d3' and
         not list((PARENT/'candidate01').glob('gate-*.json')),'terminal preserved pre-gate self-log correction')
    retained['build/codex-agent/terminal-freeze.log']='c33408d9fe7c2a602a5bbd7a785ec7cb93f9e5501c76d07684305252af16ba89'
    need(digest(PARENT/'candidate02/stopped.json')=='7dd503fc89334e05dc333a257896d9fd54b35ee64d2e11d4d8d24c69acde69f7','terminal retained first guest failure')
    need(digest(PARENT/'observer-control/result.json')=='2863507346ab63a8eeb44e56df92f3b28acb24259ead0cdb1224a4737b8ab7d8','terminal retained control result')
    diagnostic=read(PARENT/'observer-control/result.json')
    need(diagnostic['passed'] and not diagnostic['acceptance'] and diagnostic['closed'] and diagnostic['sources_unchanged'],'terminal diagnostic, not acceptance')
    helper=ROOT/'build/codex-agent/terminal_observer_control.py'
    need(digest(helper)==read(PARENT/'observer-control/frozen.json')['helper'],'terminal original diagnostic helper')
    for path in (helper,ROOT/'build/codex-agent/r83av-control-host.log',ROOT/'build/codex-agent/r83av-control-run.log'):
        retained[path.relative_to(ROOT).as_posix()]=digest(path)
    old_normal=read(next((REUSE_BASE/'guests').glob('attempt-*/summary.json')))
    old_fatal=read(next((REUSE_BASE/'fatal').glob('attempt-*/summary.json')))
    need(old_fatal['closed'] and not old_fatal['passed'] and len(old_fatal['cases'])==1,'terminal retained unqualified fatal attempt')
    f=dict(head=git('rev-parse','HEAD'),package=p,commands=commands,changed=changed,
        sources=sources,tools=tools,retained=retained,prior=link(PRIOR),
        candidate=hashlib.sha256(json.dumps(sources,sort_keys=True).encode()).hexdigest(),
        previous_spent=dict(builds=2,guests=29,guest_elapsed=diagnostic['previous_spent']['guest_elapsed']+diagnostic['elapsed']+old_normal['new_guest_elapsed']+old_fatal['guest_elapsed']),
        reserved=dict(builds=0,guests=2,guest_seconds=45,total_guest_seconds=90))
    f['prefix']=qualified_normal(f)['cases']
    for n in REUSE:reuse(n,f)
    save(BASE/'frozen.json',f)
    binding();print('TERMINAL_FROZEN',len(sources),flush=True)

def gates():
    f=binding();need(not list(BASE.glob('gate-*.json')),'terminal no unchanged retry')
    for n,command in enumerate(f['commands'],1):
        binding();limit=300 if n<=8 else 1200 if n==11 else 120 if n==12 else 180
        log=BASE/f'gate-{n:02d}.log';begin=time.monotonic()
        result=dict(passed=False,candidate=f['candidate'],command=command,limit=limit,execution='fresh')
        try:
            if n in REUSE:
                result.update(reuse(n,f))
                with log.open('x') as output:json.dump(result,output,indent=2)
            else:
                with log.open('xb') as output:
                    child=subprocess.run(shlex.split(command),cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
                        timeout=limit,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                result.update(exit_code=child.returncode,passed=child.returncode==0)
        except Exception as error:result['error']=str(error)
        result.update(elapsed=time.monotonic()-begin,log=link(log))
        if n==10 and IMAGE.exists():result['image']=link(IMAGE)
        save(BASE/f'gate-{n:02d}.json',result)
        print('TERMINAL_GATE',n,'PASS' if result['passed'] else 'FAIL',round(result['elapsed'],3),flush=True)
        if not result['passed']:
            save(BASE/'stopped.json',dict(frozen=link(BASE/'frozen.json'),failed_gate=n,result=result,
                builds=0,previous_spent=f['previous_spent'],matrix=[link(p) for p in BASE.glob('*/attempt-*/summary.json')]))
            print(log.read_text(errors='replace')[-3500:],flush=True);return 1
    return 0

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','review'):group.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.freeze:freeze();return 0
    if args.gates:return gates()
    name='defaults' if args.defaults else 'review';begin=time.monotonic();result=dict(passed=False)
    try:
        result=defaults() if args.defaults else review();print('TERMINAL_'+name.upper()+'_OK');return 0
    except Exception as error:result['error']=str(error);print('TERMINAL_VERIFY_FAIL',error);return 1
    finally:result['elapsed']=time.monotonic()-begin;save(BASE/(name+'-'+uuid.uuid4().hex+'.json'),result)
if __name__=='__main__':raise SystemExit(main())
