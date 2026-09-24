"""Frozen device-free trace qualification; preserve every attempted gate."""
from pathlib import Path
import argparse, hashlib, inspect, json, os, re, subprocess, sys, time, tomllib
import verify_x86_64_display as common
import run_qemu_x86_64_service_cpu as cpu
import native_cpu_trace as trace_reader

ROOT=common.ROOT
BASE=ROOT/'build/codex-agent/r83ce-device-free-trace'
GATES=BASE/'qualification04'
HEAD='68a947e2'
need=common.need
save=common.save
digest=common.digest

def read(p):return json.loads(Path(p).read_text())

def package():
    q=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    active=[p for p in q['packages'] if p['status']=='active']
    need(len(active)==1 and active[0]['id']==q['active_id']=='R8.3ce-device-free-trace','one active package')
    return active[0]

def sources():
    names=common.git('ls-files','--cached','--others','--exclude-standard').splitlines()
    return {n:digest(ROOT/n) for n in sorted(set(names)) if n=='Makefile' or n.startswith(
        ('arch/','kernel/','userspace/','include/','lib/','config/','scripts/','test/'))}

def scope():
    need(set(common.changed())<=set(package()['allowed_files']),'frozen scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,capture_output=True,check=True,timeout=30)

def freeze():
    scope();need(common.git('rev-parse','--short=8','HEAD')==HEAD and not GATES.exists(),'fresh frozen baseline')
    b=read(BASE/'baseline.json');need(b['passed'] and b['head'].startswith(HEAD),'clean baseline')
    for n,h in b['artifacts'].items():need(digest(BASE/'baseline'/n)==h,'preserved baseline bytes')
    save(GATES/'frozen.json',dict(head=common.git('rev-parse','HEAD'),sources=sources(),tools=common.all_tools(),
        package=package(),history={p.name:digest(p) for p in BASE.iterdir() if p.is_file()}))

def binding():
    scope();f=read(GATES/'frozen.json')
    need(f['head']==common.git('rev-parse','HEAD') and f['sources']==sources() and
         f['tools']==common.all_tools() and f['package']==package(),'frozen input binding')
    for n,h in f['history'].items():need(digest(BASE/n)==h,'preserved attempt history')
    return f

def run(command,log,limit):
    row=dict(command=list(map(str,command)),limit=limit,passed=False);save(log.with_suffix('.started.json'),row)
    t=time.monotonic()
    env=os.environ.copy()
    env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(BASE/'compiler-cache')
    try:
        with log.open('xb') as f:r=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
            timeout=limit,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row.update(passed=r.returncode==0,exit_code=r.returncode)
    finally:
        row['elapsed']=time.monotonic()-t;save(log.with_suffix('.json'),row)
    need(row['passed'],'command failed '+str(log)+': '+log.read_text(errors='replace')[-1600:])
    return row

def artifacts(folder):
    return {re.sub(r'programs-[0-9a-f]{32}','programs',p.relative_to(folder).as_posix()):digest(p)
        for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p) and
        p.suffix in ('.elf','.prg','.o','.bin','.inc','.json')}

def build(name,enabled):
    out=GATES/name;need(not out.exists(),'fresh build')
    command=['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeServiceCPU',
             '-OutputDirectory',out.relative_to(ROOT).as_posix()]
    if enabled:command+=['-NativeCPUTrace']
    run(command,GATES/(name+'.log'),300)
    return out

def defaults():
    output=build('disabled',False)
    old=artifacts(BASE/'baseline');new=artifacts(output)
    need(len(old)==56,'complete disabled artifact inventory')
    exact_objects(BASE/'baseline',output,'disabled')
    make_addition='''X86_64_NATIVE_CPU_TRACE ?= 0
ifneq ($(words $(X86_64_NATIVE_CPU_TRACE)),1)
$(error NativeCPUTrace selector must be one explicit value)
endif
ifneq ($(filter $(X86_64_NATIVE_CPU_TRACE),0 1),$(X86_64_NATIVE_CPU_TRACE))
$(error NativeCPUTrace selector must be 0 or 1)
endif
ifeq ($(X86_64_NATIVE_CPU_TRACE),1)
ifneq ($(X86_64_NATIVE_SERVICE_CPU),1)
$(error NativeCPUTrace requires device-free NativeServiceCPU)
endif
endif
'''
    additions={'Makefile':(make_addition,
        ' $(if $(filter 1,$(X86_64_NATIVE_CPU_TRACE)),-DREIST_NATIVE_CPU_TRACE=1 -DREIST_NATIVE_DEVICE_FREE_CPU_TRACE=1,)'),
        'scripts/build-x86_64-bootstrap.ps1':('    [switch]$NativeCPUTrace,\n',
        "if ($NativeCPUTrace -and -not $NativeServiceCPU) { throw 'NativeCPUTrace requires explicit device-free NativeServiceCPU.' }\n",
        '        "X86_64_NATIVE_CPU_TRACE=$([int]$NativeCPUTrace.IsPresent)" `\n')}
    for path,parts in additions.items():
        text=(ROOT/path).read_text(encoding="utf-8")
        for part in parts:text=cpu.helpers.once(text,part,'')
        need(text.rstrip()==common.git('show',HEAD+':'+path),'exact original build recipe projection')
    # The only producer changes are preprocessor admission guards. Verify that
    # the entire instruction/data body remains the accepted implementation.
    path='arch/x86_64/proc/cpu_trace.inc'
    original=common.git('show',HEAD+':'+path)
    current=(ROOT/path).read_text(encoding="utf-8").rstrip()
    need(original.split('%macro cpu_trace_save',1)[1]==current.split('%macro cpu_trace_save',1)[1],
         'unchanged complete producer instructions/data')
    # Preprocessing the production include with its original PIO profile must
    # retain every NASM token, including section/alignment/register behavior.
    nasm=common.build_tools()['nasm']['path']
    oldfile=GATES/'old-trace.inc';oldfile.write_text(original)
    prefix='%define REIST_NATIVE_CPU_TRACE 1\n%define REIST_NATIVE_SERVICE_CPU 1\n%define REIST_NATIVE_POOL_PIO 1\n'
    results=[]
    for label,target in (('old',oldfile),('current',ROOT/path)):
        src=GATES/(label+'.asm');src.write_text(prefix+'%include "'+target.as_posix()+'"\n')
        r=subprocess.run([nasm,'-E',str(src)],capture_output=True,text=True,timeout=30)
        need(r.returncode==0,'PIO preprocessing '+r.stderr)
        results.append('\n'.join(l for l in r.stdout.splitlines() if not l.startswith('%line')))
    need(results[0]==results[1],'old PIO producer tokens exact')
    save(GATES/'defaults-proof.json',dict(artifacts=new,pio_tokens_sha256=hashlib.sha256(results[0].encode()).hexdigest()))

def exact_objects(original,current,label,users_only=False):
    old=artifacts(original);new=artifacts(current)
    need(old.keys()==new.keys(),'complete artifact inventory')
    allowed={'x86_64/programs/program0.o','x86_64/programs/program1.o'}
    names=[n for n in old if not users_only or '/programs/' in n or n.endswith('/boot-programs.bin')]
    need(all(old[n]==new[n] for n in names if n not in allowed),'exact artifacts outside generated header paths')
    a=next((original/'x86_64').glob('programs-*')).relative_to(ROOT)
    b=next((current/'x86_64').glob('programs-*')).relative_to(ROOT)
    need((ROOT/a/'import_blob.h').read_bytes()==(ROOT/b/'import_blob.h').read_bytes(),'identical generated header')
    # DWARF embeds the random header directory. Recompile actual unchanged
    # source at the original header path, then compare whole raw object bytes.
    for n in (0,1):
        target=GATES/f'{label}-same-header-{n}.o'
        command=[common.build_tools()['zig']['path'],'cc','-DREIST_NATIVE_SERVICE_CPU=1',
            '-Dmain=reist_pool_finite_fixture_main','-target','x86_64-freestanding-none','-std=c11','-O2',
            '-Wall','-Wextra','-Werror','-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector',
            '-mno-red-zone','-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
            '-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include',f'-DPROGRAM_ID={n}',
            '-DPROGRAM_CASE=0','-DFAMILY_CASE=0','-DSTARTUP_CASE=0','-DPIO_CASE=0','-DMEMORY_CASE=0',
            '-DBLOCK_PROFILE_CASE=0','-DNATIVE_IMPORT=1','-include',str(a/'import_blob.h'),
            '-c','arch/x86_64/user/task_pool.c','-o',str(target)]
        run(command,GATES/f'{label}-same-header-{n}.log',60)
        need(digest(target)==old[f'x86_64/programs/program{n}.o'],'exact raw object at identical header path')
    return names

def image():return GATES/'enabled/x86_64/reist-x86_64-bootstrap.elf'

def package_build():
    out=build('enabled',True);config=cpu.pool.image_config(image());s=config['s']
    need(s['native_cpu_trace_end']-s['native_cpu_trace']==32+257*192,'exact trace extent')
    need(s['native_cpu_trace_end']<=s['scheduler_state_begin'] or s['native_cpu_trace']>=s['scheduler_state_end'],
         'trace outside scheduler reset range')
    new=artifacts(out)
    users=exact_objects(GATES/'disabled',out,'enabled',users_only=True)
    need(len(users)>=10,'complete actual userspace images')
    save(GATES/'package-proof.json',dict(artifacts=new,userspace=len(users),image_sha256=digest(image())))

def observer(config,folder,case):
    env=dict(vars(cpu));env['observer_body']=lambda:trace_reader.scope_observer(cpu.observer_body())
    exec(compile(inspect.getsource(cpu.observer),'<buffered device-free observer>','exec'),env)
    return env['observer'](config,folder,case,None)

def transport():
    env=dict(vars(cpu.transport))
    for name in ('_capture_run','_capture','capture'):
        code=inspect.getsource(getattr(cpu.transport,name))
        if name=='_capture_run':
            code=cpu.helpers.once(code,'capture_started+27 if service_cpu_budget','capture_started+57 if service_cpu_budget')
            code=cpu.helpers.once(code,'time.monotonic()-capture_started>30','time.monotonic()-capture_started>60')
        exec(compile(code,'<bounded trace capture>','exec'),env)
    return env['capture']

def replay(folder,case):
    config=cpu.pool.image_config(image());count=cpu.wide.allocations(config['child_record'])
    serial=(folder/'guest.log').read_text();trace=(folder/'frame-trace.log').read_text()
    need(len(trace.encode())<=65536,'bounded trace text')
    rows=cpu.validate_capture(serial,trace,case,None,count,hashlib.sha256(config['child_record']).hexdigest(),folder)
    records=trace_reader.validate_capture(folder,trace,cpu)
    reads=cpu.binary_capacity(folder)
    need([r['equivalence'] for r in reads if r['equivalence'] is not None]==['kernel','high'],'same-stop equivalence')
    for i,r in enumerate(reads,1):
        p=folder/'binary-memory'/r['file']
        need(r['sequence']==i and p.name==f'ram-{i:04d}.bin' and p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],
             'complete raw memory binding')
    m=read(folder/'capture-metrics.json')
    need(m['spawned'] and not m['failed'] and m['debugger_exit']==0 and m['cleanup_seconds']<=3 and
         m['stop_reason']!='deadline','closed real guest')
    return dict(tasks=len(rows),charges=len(records),trace_sha256=digest(folder/'cpu-trace-v1.bin'))

def runtime():
    config=cpu.pool.image_config(image());spent=0
    for case in (0,3):
        folder=GATES/f'guest-{case}';folder.mkdir()
        row=dict(case=case,passed=False);save(folder/'started.json',row);t=time.monotonic()
        try:
            transport()(image(),folder,observer(config,folder,case),4096,binary_memory='equivalence',
                        diagnostic_metrics=True,service_cpu_budget=True)
            row.update(replay(folder,case));row['passed']=True
        finally:
            row['elapsed']=time.monotonic()-t;save(folder/'result.json',row)
        spent+=row['elapsed'];need(row['elapsed']<=60 and spent<=120,'frozen guest budget')
        print('TRACE_GUEST_OK',case,round(row['elapsed'],3),flush=True)

def review():
    for name in ('host','defaults','package','runtime'):need(read(GATES/(name+'.json'))['passed'],'all prior gates')
    need(artifacts(GATES/'enabled')==read(GATES/'package-proof.json')['artifacts'],'immutable package bytes')
    for case in (0,3):
        folder=GATES/f'guest-{case}';row=read(folder/'result.json');need(row['passed'],'closed case')
        need(all(row[k]==v for k,v in replay(folder,case).items()),'independent full replay')
        raw=(folder/'cpu-trace-v1.bin').read_bytes();text=(folder/'frame-trace.log').read_text()
        events=[trace_reader.decode_trace_record(raw[n:n+192],n//192+1) for n in range(0,len(raw),192)]
        changed=bytearray(raw);changed[40]^=1
        for bad in (raw[:-192],bytes(changed),raw[192:384]+raw[:192]+raw[384:]):
            try:trace_reader.validate_trace_records(text,bad,events)
            except ValueError:pass
            else:raise ValueError('corrupt raw trace accepted')
    save(GATES/'review-proof.json',dict(passed=True,head=common.git('rev-parse','HEAD'),sources=sources(),
        tools=common.all_tools(),evidence={p.relative_to(GATES).as_posix():digest(p) for p in GATES.rglob('*')
        if p.is_file() and 'cache' not in str(p) and p!=GATES/'review.log'}))

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',nargs='?',choices=('freeze','all'))
    for name in ('defaults','package','runtime','review'):p.add_argument('--'+name,action='store_true')
    a=p.parse_args()
    if a.mode=='freeze':freeze();return
    if a.mode=='all':
        freeze()
        gates=[('host',[sys.executable,'test/test_x86_64_device_free_trace.py','-v'],180)]
        gates += [(n,[sys.executable,__file__,'--'+n],limit) for n,limit in
                  (('defaults',360),('package',360),('runtime',180),('review',180))]
        for name,command,limit in gates:
            binding();r=run(command,GATES/(name+'.log'),limit);binding()
            print('TRACE_GATE_OK',name,round(r['elapsed'],3),flush=True)
        proof=read(GATES/'review-proof.json')
        for n,h in proof['evidence'].items():need(digest(GATES/n)==h,'immutable reviewed evidence')
        save(GATES/'acceptance-seal.json',dict(passed=True,head=common.git('rev-parse','HEAD'),sources=sources(),
            tools=common.all_tools(),evidence={p.relative_to(GATES).as_posix():digest(p) for p in GATES.rglob('*')
            if p.is_file() and 'cache' not in str(p)}))
        return
    binding()
    actions={'defaults':defaults,'package':package_build,'runtime':runtime,'review':review}
    selected=[n for n in actions if getattr(a,n)];need(len(selected)==1,'one gate')
    actions[selected[0]]();binding()

if __name__=='__main__':main()
