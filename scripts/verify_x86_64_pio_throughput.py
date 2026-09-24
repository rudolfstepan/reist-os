"""Frozen, bounded qualification of the explicit generation-bound PIO profile."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time,tomllib,shlex,re
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'build/codex-agent/r83by-pio-throughput'
BASE=EVIDENCE/'candidate08'
HEAD='cbe0cf77'
PACKAGE='R8.3by-pio-throughput'

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
    from run_qemu_x86_64_pio_throughput import PORTABLE
    from run_qemu_x86_64_math_runtime import portable_toolchain
    exe,firmware=portable_toolchain(PORTABLE)
    result=build_tools();result['hardware_binding']=link(PORTABLE)
    result['hardware_executable']=link(exe);result['hardware_firmware']=str(firmware)
    return result

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
        print('PIO_GATE',n,'PASS' if not code else 'FAIL',flush=True)
        if code:save(BASE/'stopped.json',dict(passed=False,gates=rows));raise ValueError('first gate failure '+str(n))
    save(BASE/'gates-passed.json',dict(passed=True,gates=rows))

def freeze():
    need(not BASE.exists() and git('rev-parse','--short=8','HEAD')==HEAD,'fresh candidate/base')
    p=package_row();paths=changed()
    need(set(paths)<=set(p['allowed_files']) and not git('diff','--cached','--name-only'),'exact unstaged scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==5,'five frozen gates')
    save(BASE/'frozen.json',dict(head=git('rev-parse','HEAD'),package=p,changed=paths,
        sources=sources(),tools=tools(),commands=commands,limits=[900,900,600,900,600]))

def defaults():
    from verify_x86_64_shell_session import disabled
    n='arch/x86_64/user/pool_pio.c'
    s=(ROOT/n).read_text(encoding='utf-8').replace('#if defined(REIST_NATIVE_PIO_THROUGHPUT) && PROGRAM_ID==0',
                                 '#ifdef REIST_NATIVE_PIO_THROUGHPUT')
    s=disabled(s,'REIST_NATIVE_PIO_THROUGHPUT',False)
    need(s==original(n),'unchanged default consumer')
    # Exact projection of all new opt-in build expressions, including O2.
    n='scripts/build_x86_64_boot_programs.py';s=(ROOT/n).read_text(encoding='utf-8')
    s='\n'.join(line for line in s.split('\n') if not line.strip().startswith((
        'if type(pio_throughput)', 'if pio_throughput:', "p.add_argument('--pio-throughput'")))
    s=s.replace(',pio_throughput=False):','):').replace(',a.pio_throughput)',')')
    s=s.replace("'-O2' if pio_throughput else '-Oz'","'-Oz'")
    need(s==original(n),'unchanged default producer')
    n='Makefile';s=(ROOT/n).read_text(encoding='utf-8')
    s=s.replace('X86_64_NATIVE_PIO_THROUGHPUT_HARDWARE ?= 0\n','')
    s=s.replace('X86_64_NATIVE_PIO_THROUGHPUT ?= 0\n\n','')
    s=s.replace('X86_64_MATH_HARDWARE_ASM += $(if $(filter 1,$(X86_64_NATIVE_PIO_THROUGHPUT_HARDWARE)),-DREIST_NATIVE_MATH_HARDWARE=1,)\n','')
    start=s.index('ifneq ($(words $(X86_64_NATIVE_PIO_THROUGHPUT)),1)')
    end=s.index('ifneq ($(words $(X86_64_NATIVE_POOL_PIO)),1)',start)
    s=s[:start]+s[end:]
    s=s.replace(' $(if $(filter 1,$(X86_64_NATIVE_PIO_THROUGHPUT)),--pio-throughput,)','')
    need(s==original(n),'unchanged default Make rules')
    n='scripts/build-x86_64-bootstrap.ps1';s=(ROOT/n).read_text(encoding='utf-8')
    s=s.replace('    [switch]$NativePIOThroughput,\n','')
    s=s.replace('    [switch]$NativePIOThroughputHardware,\n','')
    s=s.replace('if ($NativePIOThroughputHardware) { $NativePIOThroughput = [switch]$true }\n','')
    start=s.index('if ($NativePIOThroughput) {');end=s.index('if ($NativeLiveFile) {',start)
    s=s[:start]+s[end:]
    s=s.replace('        "X86_64_NATIVE_PIO_THROUGHPUT=$([int]$NativePIOThroughput.IsPresent)" `\n','')
    s=s.replace('        "X86_64_NATIVE_PIO_THROUGHPUT_HARDWARE=$([int]$NativePIOThroughputHardware.IsPresent)" `\n','')
    need(s==original(n),'unchanged default PowerShell rules')
    sys.path.insert(0,str(ROOT/'test'))
    import unittest
    loader=unittest.TestLoader();suite=unittest.TestSuite()
    for name in ('test_x86_64_pio','test_x86_64_pio_deadline'):
        suite.addTests(loader.loadTestsFromName(name))
    for name in ('actual_slot_owner_admission','actual_ring3_service_all_owners',
                 'actual_trace_eight_slot_bounds','generated_observer_and_oom_scope',
                 'actual_lifecycle_oracle_mutations','trace_eight_slot_decoder_and_physical_bytes'):
        suite.addTests(loader.loadTestsFromName('test_x86_64_pool_pio.PoolPioTests.test_'+name))
    need(unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful(),'legacy behavior tests')
    subprocess.run([sys.executable,'scripts/verify_x86_64_reference_artifacts.py'],cwd=ROOT,timeout=120,check=True)
    print('PIO_DEFAULTS_OK')

def package():
    binding();folder=BASE/'build';need(not folder.exists(),'one fresh package build')
    state=build_sources();tool=tools()
    cmd=[tool['pwsh']['path'],'-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
         '-NativePIOThroughputHardware','-OutputDirectory',folder.relative_to(ROOT).as_posix()]
    save(BASE/'build-started.json',dict(command=cmd,limit=300,sources=state,tools=tool))
    t=time.monotonic()
    with (BASE/'build.log').open('x') as out:
        r=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=300)
    need(r.returncode==0,'package build failed');binding()
    need(state==build_sources() and tool==tools(),'unchanged build inputs')
    import run_qemu_x86_64_pio_throughput as guest
    guest.prior.image_config(folder/'x86_64/reist-x86_64-bootstrap.elf')
    save(BASE/'package.json',dict(passed=True,elapsed=time.monotonic()-t,sources=state,tools=tool,
        artifacts={p.relative_to(ROOT).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}))

def image():
    row=read(BASE/'package.json');need(row['passed'] and row['elapsed']<=300,'bounded package build')
    need(row['sources']==build_sources() and row['tools']==tools(),'exact build binding')
    for n,sha in row['artifacts'].items():need(digest(ROOT/n)==sha,'bound artifact '+n)
    return BASE/'build/x86_64/reist-x86_64-bootstrap.elf'

def replay(img,folder,case,ram):
    import run_qemu_x86_64_pio_throughput as guest
    row=read(folder/'result.json');metrics=read(folder/'capture-metrics.json')
    need(row['passed'] and row['closed'] and row['case']==case and row['ram']==ram and
         row['elapsed']<=60 and row['image_sha256']==digest(img),'bounded successful guest')
    need(not metrics['failed'] and metrics['debugger_exit']==0 and metrics['cleanup_seconds']<=5,'capture cleanup')
    config=guest.prior.image_config(img)
    need(row.get('hardware') is True,'explicit hardware qualification')
    validate_hardware(config,folder)
    need(row['child_sha256']==hashlib.sha256(config['child_record']).hexdigest(),'actual child binding')
    rows=guest.namespace(case).validate((folder/'guest.log').read_text(encoding='utf-8'),(folder/'frame-trace.log').read_text(encoding='utf-8'),
        case,None,guest.prior.wide.allocations(config['child_record']),row['child_sha256'])
    need(len(rows)==row['tasks'],'full lifecycle replay')
    before=read(folder/'media-before.json');after=read(folder/'media-after.json')
    need(before['passed'] and after['passed'] and before['base_sha256']==after['base_sha256']==digest(folder/'generated.raw')
         and before['overlay_allocated_data']==after['overlay_allocated_data']==0,'no disk writes')
    return {p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*') if p.is_file()}

def validate_hardware(config,folder):
    import struct
    from run_qemu_x86_64_pio_throughput import PORTABLE
    from run_qemu_x86_64_math_runtime import portable_toolchain
    exe,firmware=portable_toolchain(PORTABLE);s=config['s']
    row=read(folder/'hardware-bootstrap.json')
    need(row['passed'] is True and 0<row['elapsed']<=10,'bounded hardware bootstrap')
    need(row['physical']==s['native_math_hardware_ready']-0xffffffff80000000,'bootstrap binding')
    commands=row['commands'];reads=row['reads'];names=[r['command'] for r in commands]
    need(7<=len(commands)<=140 and 1<=len(reads)<=128,'bootstrap transcript capacity')
    need(names[:4]==['qmp_capabilities','query-name','query-status','cont'] and
         names[-3:]==['stop','query-status','pmemsave'] and
         names[4:-3]==['pmemsave']*(len(reads)-1),'exact bootstrap command order')
    need(commands[2]['result']==dict(status='prelaunch',running=False) and
         commands[-2]['result']==dict(status='paused',running=False),'bootstrap paused state')
    for index,r in enumerate(reads):
        n='hardware-cells-%03d.bin'%(127 if index==len(reads)-1 else index)
        need(r['file']==n and r['values'] in ([0,0],[1,0]) and
             (folder/n).read_bytes()==struct.pack('<2Q',*r['values']),'raw bootstrap cells')
    need(reads[-1]['values']==[1,0],'ready before release')
    releases=[json.loads(line[len('BY_HARDWARE '):]) for line in
              (folder/'frame-trace.log').read_text(encoding='utf-8').splitlines() if line.startswith('BY_HARDWARE ')]
    need(len(releases)==1,'one bootstrap release');r=releases[0]
    need(s['native_math_hardware_gate64.wait']<=r['rip']<s['native_math_hardware_gate64.failed'] and
         r['cs']==8 and r['cr0']&0x80010000==0x80010000 and r['cr3']>0 and r['release']==1,'actual release registers')
    need((folder/'hardware-cleared.bin').read_bytes()==bytes(16),'one-shot cells cleared')
    need('WHPX: Failed' not in (folder/'stderr.log').read_text(errors='replace'),'hardware engine healthy')
    cmd=read(folder/'command.json')
    need(Path(cmd[0])==exe and cmd[cmd.index('-accel')+1]=='whpx,kernel-irqchip=off' and
         Path(cmd[cmd.index('-L')+1])==firmware and cmd[cmd.index('-smp')+1]=='1','actual bound hardware command')

def runtime():
    binding();img=image();import run_qemu_x86_64_pio_throughput as guest
    rows=[];t=time.monotonic()
    for case,ram in guest.CASES:
        binding();folder=BASE/'guests'/str(case)
        row=guest.run(img,folder,case,ram);row['proof']=replay(img,folder,case,ram);rows.append(row)
        save(BASE/f'case-{case}.json',row);print('PIO_CASE_OK',case,flush=True)
    need(len(rows)<=8 and time.monotonic()-t<=480,'aggregate guest lease')
    save(BASE/'matrix.json',dict(passed=True,cases=rows,elapsed=time.monotonic()-t))

def review():
    binding();img=image();import run_qemu_x86_64_pio_throughput as guest
    matrix=read(BASE/'matrix.json');need(matrix['passed'] and len(matrix['cases'])==len(guest.CASES),'complete matrix')
    for row,(case,ram) in zip(matrix['cases'],guest.CASES):
        need(replay(img,BASE/'guests'/str(case),case,ram)==row['proof'],'unchanged independent raw replay')
    need(set(changed())<=set(package_row()['allowed_files']),'final scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True)
    save(BASE/'review.json',dict(passed=True,matrix=link(BASE/'matrix.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    for name in ('freeze','gates','defaults','package','runtime','review'):g.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    globals()[next(k for k,v in vars(a).items() if v)]()
