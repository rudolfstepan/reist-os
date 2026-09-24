"""Frozen qualification for CREATE-v8; all failures retain their receipts."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys, time, tomllib
import verify_x86_64_display as common
import run_qemu_x86_64_large_periodic as guest

ROOT=common.ROOT
BASE=ROOT/'build/codex-agent/r83cd-large-periodic'
GATES=BASE/'qualification05'
HEAD='7068ee69'
need=common.need
save=common.save
digest=common.digest


def read(path): return json.loads(Path(path).read_text())


def package():
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    active=[p for p in queue['packages'] if p['status']=='active']
    need(len(active)==1 and active[0]['id']==queue['active_id']=='R8.3cd-large-periodic','one package')
    return active[0]


def sources():
    names=common.git('ls-files','--cached','--others','--exclude-standard').splitlines()
    return {p:digest(ROOT/p) for p in sorted(set(names)) if p=='Makefile' or p.startswith(
        ('arch/','kernel/','userspace/','include/','lib/','config/','scripts/','test/'))}


def scope():
    need(set(common.changed())<=set(package()['allowed_files']),'frozen scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True,capture_output=True,timeout=30)


def freeze():
    scope();need(common.git('rev-parse','--short=8','HEAD')==HEAD,'contract baseline')
    need(not GATES.exists(),'fresh qualification')
    baseline=read(BASE/'build01.json')
    need(baseline['passed'] and baseline['head'].startswith('6f5dfc65'),'preimplementation baseline')
    for name,sha in baseline['artifacts'].items():need(digest(ROOT/name)==sha,'preserved baseline')
    save(GATES/'frozen.json',dict(head=common.git('rev-parse','HEAD'),sources=sources(),
         tools=common.all_tools(),package=package(),baseline=digest(BASE/'build01.json'),
         history={p.name:digest(p) for p in BASE.iterdir() if p.is_file()}))


def binding():
    scope();f=read(GATES/'frozen.json')
    need(f['head']==common.git('rev-parse','HEAD') and f['sources']==sources() and
         f['tools']==common.all_tools() and f['package']==package(),'frozen inputs')
    need(digest(BASE/'build01.json')==f['baseline'],'baseline receipt')
    for name,sha in f['history'].items():need(digest(BASE/name)==sha,'preserved history')
    return f


def run(command,log,limit,env=None):
    t=time.monotonic();row=dict(command=list(map(str,command)),limit=limit,passed=False)
    save(log.with_suffix('.started.json'),row)
    try:
        with log.open('xb') as stream:
            r=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                timeout=limit,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        row.update(passed=r.returncode==0,exit_code=r.returncode)
    finally:
        row['elapsed']=time.monotonic()-t;save(log.with_suffix('.json'),row)
    need(row['passed'],'command failed '+str(log)+': '+log.read_text(errors='replace')[-1800:])
    return row


def artifacts(folder):
    return {re.sub(r'programs-[0-9a-f]{32}','programs',p.relative_to(folder).as_posix()):digest(p)
        for p in folder.rglob('*') if p.is_file() and 'cache' not in str(p) and
        p.suffix in ('.elf','.prg','.o','.bin','.inc','.json')}


def build(label,enabled):
    output=GATES/label;need(not output.exists(),'fresh build')
    run(['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
         '-NativeLargePeriodic' if enabled else '-NativeLargeImage',
         '-OutputDirectory',str(output.relative_to(ROOT)),*(['-NativeCPUTrace'] if enabled else [])],GATES/(label+'.log'),300)
    return output


def defaults():
    output=build('disabled',False)
    old=artifacts(BASE/'baseline01');new=artifacts(output)
    key='x86_64/programs/program0.o'
    need(old.keys()==new.keys() and len(old)==56,'complete disabled artifacts')
    need(all(old[k]==new[k] for k in old if k!=key),'exact disabled non-root artifacts')
    # Generated import headers carry their random directory into DWARF. Compile
    # CURRENT production source against the exact same byte-identical header
    # path as the baseline, retaining the original output as evidence. Compare
    # whole objects, never strip or normalize debug bytes or executable code.
    original=next((BASE/'baseline01/x86_64').glob('programs-*')).relative_to(ROOT)
    current=next((output/'x86_64').glob('programs-*')).relative_to(ROOT)
    need((ROOT/original/'import_blob.h').read_bytes()==(ROOT/current/'import_blob.h').read_bytes(),
         'identical generated input header')
    target=GATES/'same-header-path-program0.o'
    command=[common.build_tools()['zig']['path'],'cc','-DREIST_NATIVE_LARGE_IMAGE=1',
        '-target','x86_64-freestanding-none','-std=c11','-O2','-Wall','-Wextra','-Werror',
        '-ffreestanding','-nostdlib','-fno-builtin','-fno-stack-protector','-mno-red-zone',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-fno-pic','-fno-pie',
        '-mno-mmx','-mno-sse','-mno-sse2','-Iuserspace/sdk/include',
        '-DPROGRAM_ID=0','-DPROGRAM_CASE=0','-DFAMILY_CASE=0','-DSTARTUP_CASE=0',
        '-DPIO_CASE=0','-DMEMORY_CASE=0','-DBLOCK_PROFILE_CASE=0','-DNATIVE_IMPORT=1',
        '-include',str(original/'import_blob.h'),'-c','arch/x86_64/user/large_image.c','-o',str(target)]
    env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
    env['ZIG_LOCAL_CACHE_DIR']=str(GATES/'same-header-cache')
    run(command,GATES/'same-header.log',60,env)
    need(digest(target)==old[key],'entire root object exact with identical input path')
    save(GATES/'defaults.json',dict(artifacts=new,baseline=old,exact_root=digest(target),
                                  header=str(original/'import_blob.h')))


def make_package():
    output=build('enabled',True);image=output/'x86_64/reist-x86_64-bootstrap.elf'
    guest.legacy.payload.verify_outer((image.parent/'reist-x86_64-c-core.elf').read_bytes(),
                                     image.read_bytes(),large_image=True)
    save(GATES/'package.json',dict(artifacts=artifacts(output),image=str(image.relative_to(ROOT))))


def media_binding():
    p=read(GATES/'package.json');need(artifacts(GATES/'enabled')==p['artifacts'],'immutable enabled image')
    return ROOT/p['image']


def runtime():
    image=media_binding();rows=[];started=time.monotonic()
    # Normal, exhaustion, cancel, partial-construction OOM, RX write, guard.
    for case,oom in ((0,None),(4,None),(5,None),(6,26),(3,None),(1,None)):
        binding();folder=GATES/f'guest-{case}';t=time.monotonic()
        save(GATES/f'guest-{case}-started.json',dict(case=case,oom=oom,limit=360))
        proof=guest.capture(image,folder,case,oom)
        elapsed=time.monotonic()-t;need(elapsed<=360,'guest deadline')
        row=dict(case=case,oom=oom,elapsed=elapsed,proof=proof)
        save(GATES/f'guest-{case}-passed.json',row);rows.append(row)
        print('LARGE_PERIODIC_GUEST_OK',case,round(elapsed,3),flush=True)
    need(time.monotonic()-started<=2160,'aggregate guest deadline')
    save(GATES/'runtime.json',rows)


def review():
    from unittest.mock import patch
    need(all(read(GATES/f'gate-{i}.json')['passed'] for i in range(1,5)),
         'all preceding frozen gates passed')
    image=media_binding();rows=read(GATES/'runtime.json');need(len(rows)==6,'six complete cases')
    fixture=next(image.parent.glob('programs-*'))
    from build_x86_64_large_image import prepare
    count=guest.legacy.allocations(prepare((fixture/'program2.prg').read_bytes(),[]))
    for row in rows:
        folder=GATES/f"guest-{row['case']}"
        serial=(folder/'serial.txt').read_text();trace=(folder/'trace.txt').read_text()
        proof=guest.replay(folder,serial,trace,count)
        need(json.loads(json.dumps(proof))==row['proof'],'independent replay exact')
    folder=GATES/'guest-0';raw=(folder/'reads.bin').read_bytes();index=read(folder/'config.json')
    entries=[json.loads(line) for line in (folder/'reads.jsonl').read_text().splitlines()]
    phase=next(e['event'] for e in entries if e.get('event',{}).get('kind')=='phase'
               and e['event']['gen']==5)
    addresses=[(index['s']['scheduler_cpu_budgets']+64,16),(index['s']['scheduler_cpu_windows']+64,16),
               (index['s']['process_run_plan'],16),(index['s']['elf_import_record'],16),
               (phase['address'],0)]
    original=Path.read_bytes
    mutations=[(next(e for e in entries if e.get('address')==address and e.get('bytes',0)>offset),offset)
               for address,offset in addresses]
    block=None
    for e in entries:
        if 'begin' in e:block=e['begin']
        elif index['s']['native_cpu_trace']+32<=e.get('address',0)<index['s']['native_cpu_trace']+32+256*192 and e.get('bytes',0)>=192:
            mutations.append((e,104+16));break
    need(len(mutations)==6,'initial, post-charge and phase corruption cases')
    for r,offset in mutations:
        bad=bytearray(raw);bad[r['offset']+offset]^=1
        rejected=False
        with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==folder/'reads.bin' else original(p)):
            try:guest.replay(folder,(folder/'serial.txt').read_text(),(folder/'trace.txt').read_text(),count)
            except ValueError:rejected=True
        need(rejected,'raw corruption rejected')
    binding();scope()
    save(GATES/'review-proof.json',dict(passed=True,frozen=read(GATES/'frozen.json'),runtime=rows,
         package=read(GATES/'package.json'),defaults=read(GATES/'defaults.json'),
         evidence={p.relative_to(GATES).as_posix():digest(p) for p in GATES.rglob('*')
                   if p.is_file() and 'cache' not in str(p) and p!=GATES/'gate-5.log'}))


def gates():
    freeze();p=package();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    for i,(command,limit) in enumerate(zip(commands,(180,300,600,2400,1200)),1):
        binding();run(command.split(),GATES/f'gate-{i}.log',limit);binding()
        print('LARGE_PERIODIC_GATE_OK',i,flush=True)
    proof=read(GATES/'review-proof.json')
    for name,sha in proof['evidence'].items():need(digest(GATES/name)==sha,'closed reviewed evidence')
    save(GATES/'acceptance-seal.json',dict(passed=True,frozen=read(GATES/'frozen.json'),
        evidence={p.relative_to(GATES).as_posix():digest(p) for p in GATES.rglob('*')
                  if p.is_file() and 'cache' not in str(p)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    for name in ('gates','defaults','package','runtime','review'):group.add_argument('--'+name,action='store_true')
    args=parser.parse_args()
    if args.gates:gates()
    else:
        binding()
        if args.defaults:defaults()
        elif args.package:make_package()
        elif args.runtime:runtime()
        else:review()
