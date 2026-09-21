"""One opt-in image, targeted immutable network/DMA qualification."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time,tomllib,shlex,re
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'build/codex-agent/r83bj-network-dma'
BASE=EVIDENCE/'candidate02'
HEAD='c6533954'
PACKAGE='R8.3bj-network-dma'
BUILD='03'
def need(ok,message):
    if not ok:raise ValueError(message)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,sort_keys=True,indent=2)
def link(p):return dict(path=Path(p).relative_to(ROOT).as_posix(),sha256=digest(p))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,timeout=30).decode().strip()
def original(p):return subprocess.check_output(['git','show',HEAD+':'+p],cwd=ROOT,timeout=30).decode('utf-8').replace('\r\n','\n')
def changed():return sorted(set(git('diff','--name-only').splitlines()+git('ls-files','--others','--exclude-standard').splitlines()))
def package_row():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'));rows=[p for p in q['packages'] if p['status']=='active']
    need(q['active_id']==PACKAGE and len(rows)==1 and rows[0]['id']==PACKAGE,'one active package');return rows[0]
def sources():return {n:digest(ROOT/n) for n in git('ls-files','--cached','--others','--exclude-standard').splitlines()}
def build_sources():
    return {n:digest(ROOT/n) for n in git('ls-files','--cached','--others','--exclude-standard').splitlines()
        if n=='Makefile' or n.startswith(('arch/','kernel/','userspace/','include/','lib/','config/')) or n.startswith('scripts/build') and n.endswith(('.py','.ps1'))}
def tools():
    from verify_x86_64_input import build_tools
    return build_tools()
def development_build():
    folder=EVIDENCE/('build'+BUILD);receipt=EVIDENCE/('build'+BUILD+'.json');need(not folder.exists() and not receipt.exists(),'fresh reserved build')
    state=build_sources();tool=tools();cmd=[tool['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeNetworkDMA','-OutputDirectory',folder.relative_to(ROOT).as_posix()]
    log=EVIDENCE/('build'+BUILD+'.log');save(EVIDENCE/('build'+BUILD+'-started.json'),dict(command=cmd,sources=state,tools=tool,limit=300));t=time.monotonic()
    row=dict(passed=False,command=cmd,sources=state,tools=tool,limit=300)
    try:
        with log.open('xb') as out:r=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=300)
        need(r.returncode==0,'build failed: '+log.read_text(errors='replace')[-1800:]);need(state==build_sources() and tool==tools(),'unchanged build inputs')
        row['artifacts']={p.relative_to(ROOT).as_posix():digest(p) for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p) and p.suffix in ('.elf','.prg','.bin','.json','.inc','.map','.o')}
        row['passed']=True
    except BaseException as error:row['error']=str(error);raise
    finally:row.update(elapsed=time.monotonic()-t,log=link(log));save(receipt,row)
    print('NETWORK_BUILD_OK',row['elapsed'])
def image():
    row=read(EVIDENCE/('build'+BUILD+'.json'));need(row['passed'] and row['elapsed']<=300,'bounded successful build')
    need(row['sources']==build_sources() and row['tools']==tools(),'exact build binding')
    for n,sha in row['artifacts'].items():need(digest(ROOT/n)==sha,'bound artifact '+n)
    return EVIDENCE/('build'+BUILD)/'x86_64/reist-x86_64-bootstrap.elf'
def defaults():
    from verify_x86_64_shell_session import disabled
    for n in ('arch/x86_64/proc/cooperative_scheduler.asm','arch/x86_64/proc/process_run.inc','arch/x86_64/proc/task_family.inc'):
        current=disabled((ROOT/n).read_text(encoding='utf-8'),'REIST_NATIVE_NETWORK_DMA',True)
        need(current.rstrip('\n')==original(n).rstrip('\n'),'exact disabled assembly '+n)
    n='Makefile';s=(ROOT/n).read_text(encoding='utf-8')
    s=re.sub(r'# NativeNetworkDMA: independent hardware-mediation profile\.\n.*?# End NativeNetworkDMA selector\.\n','',s,flags=re.S)
    for part in ('X86_64_POOL_FLAGS += $(X86_64_NETWORK_FLAGS)\n','X86_64_SESSION_ARG += $(if $(filter 1,$(X86_64_NATIVE_NETWORK_DMA)),--network-dma,)\n',
        'ifeq ($(X86_64_NATIVE_NETWORK_DMA),1)\n\t@$(X86_64_CC) $(X86_64_CFLAGS) -I. $(X86_64_NETWORK_FLAGS) -c arch/x86_64/devices/network_dma.c -o $(X86_64_BOOTSTRAP_DIR)/network_dma.o\nendif\n',
        '\t\t$(if $(filter 1,$(X86_64_NATIVE_NETWORK_DMA)),$(X86_64_BOOTSTRAP_DIR)/network_dma.o,) \\\n'):
        need(s.count(part)==1,'exact network Make addition');s=s.replace(part,'')
    need(s==original(n),'full old Make rules')
    n='scripts/build-x86_64-bootstrap.ps1';s=(ROOT/n).read_text(encoding='utf-8')
    for part in ('    [switch]$NativeNetworkDMA,\n','if ($NativeNetworkDMA) { $NativeTaskPool = [switch]$true }\n','        "X86_64_NATIVE_NETWORK_DMA=$([int]$NativeNetworkDMA.IsPresent)" `\n'):
        need(s.count(part)==1,'exact PS addition');s=s.replace(part,'')
    need(s==original(n),'full old PowerShell rules')
    n='scripts/build_x86_64_c_payload.py';s=(ROOT/n).read_text(encoding='utf-8')
    s=s.replace(",'reist_native_network':'C_NATIVE_NETWORK_ENTRY'",'').replace(' if name!=\'reist_native_network\' or name in p["symbols"]','')
    need(s==original(n),'full payload parser and old exports')
    n='scripts/build_x86_64_boot_programs.py';s=(ROOT/n).read_text(encoding='utf-8')
    for part in ('    if type(network_dma) is not bool or network_dma and (not task_pool or any((pool_pio,service_cpu,service_pio,console,graphical_session))):raise ValueError("network DMA requires separate plain task pool")\n',
                 "    if network_dma:cc=[*cc,'-DREIST_NATIVE_NETWORK_DMA=1']\n","    p.add_argument('--network-dma',action='store_true')\n"):
        need(s.count(part)==1,'exact builder addition');s=s.replace(part,'')
    s=s.replace(',network_dma=False):','):').replace("'arch/x86_64/user/network_dma.c' if network_dma else ",'').replace(',a.network_dma)',')')
    need(s==original(n),'full old program builder')
    old=read(ROOT/'build/codex-agent/r83bi-graphical-session/development-build07.json')
    need(all(digest(ROOT/n)==sha for n,sha in old['artifacts'].items()),'all accepted graphical artifacts unchanged')
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=ROOT,timeout=120,check=True)
    print('NETWORK_DEFAULTS_OK')
def freeze():
    need(not BASE.exists() and git('rev-parse','--short=8','HEAD')==HEAD,'fresh candidate/base');p=package_row();paths=changed()
    need(set(paths)<=set(p['allowed_files']) and not git('diff','--cached','--name-only'),'exact unstaged package scope');subprocess.run(['git','diff','--check'],check=True,cwd=ROOT)
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests'];need(len(commands)==5,'five targeted gates')
    save(BASE/'frozen.json',dict(head=git('rev-parse','HEAD'),package=p,changed=paths,sources=sources(),tools=tools(),commands=commands,limits=[600,180,180,600,180],image=link(image())))
def binding():
    f=read(BASE/'frozen.json');need(f['head']==git('rev-parse','HEAD') and f['package']==package_row() and f['changed']==changed() and f['sources']==sources() and f['tools']==tools(),'frozen candidate');return f
def gates():
    f=binding();save(BASE/'started.json',dict(commands=f['commands']));rows=[]
    for n,(cmd,limit) in enumerate(zip(f['commands'],f['limits']),1):
        binding();log=BASE/f'gate-{n:02d}.log';t=time.monotonic()
        try:
            with log.open('xb') as out:r=subprocess.run(shlex.split(cmd),cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=limit);code=r.returncode
        except subprocess.TimeoutExpired:code=124
        row=dict(command=cmd,passed=code==0,exit_code=code,elapsed=time.monotonic()-t,limit=limit,log=link(log));rows.append(row);save(BASE/f'gate-{n:02d}.json',row)
        print('NETWORK_GATE',n,'PASS' if not code else 'FAIL',flush=True)
        if code:save(BASE/'stopped.json',dict(passed=False,gates=rows));raise ValueError('first gate failure '+str(n))
    save(BASE/'gates-passed.json',dict(passed=True,gates=rows))
def runtime():
    binding();img=image();import run_qemu_x86_64_network_dma as guest
    rows=[]
    for spec in guest.CASES:
        binding();row=guest.run(img,BASE/'guests'/spec[0],spec);row['proof']=guest.review(img,BASE/'guests'/spec[0],spec);rows.append(row)
        save(BASE/(spec[0]+'.json'),row);print('NETWORK_CASE_OK',spec[0],flush=True)
    need(sum(r['elapsed'] for r in rows)<=360,'aggregate guest limit');save(BASE/'matrix.json',dict(passed=True,cases=rows))
def review():
    binding();import run_qemu_x86_64_network_dma as guest
    matrix=read(BASE/'matrix.json');need(matrix['passed'] and len(matrix['cases'])==8,'complete fresh matrix')
    for row,spec in zip(matrix['cases'],guest.CASES):need(guest.review(image(),BASE/'guests'/spec[0],spec)==row['proof'],'independent raw replay')
    need(set(changed())<=set(package_row()['allowed_files']) and not git('diff','--cached','--name-only'),'final scope');subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    save(BASE/'review.json',dict(passed=True,raw={p.relative_to(ROOT).as_posix():digest(p) for p in (BASE/'guests').rglob('*') if p.is_file()}))
if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('development-build','freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    if a.development_build:development_build()
    elif a.freeze:freeze()
    elif a.gates:gates()
    elif a.defaults:defaults()
    elif a.package:binding();save(BASE/'package.json',dict(passed=True,image=link(image())))
    elif a.runtime:runtime()
    elif a.review:review()
