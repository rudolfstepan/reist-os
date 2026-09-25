"""Query-return helpers. Diagnostics do not constitute frozen acceptance."""
from pathlib import Path
import argparse, hashlib, json, sys, types, zipfile, subprocess, time, tomllib
import verify_x86_64_desktop_cpu as common
import run_qemu_x86_64_query_return as guest

ROOT=common.ROOT
BASE=ROOT/'build/codex-agent/r83ch-query-return'
ARCHIVE=ROOT/'build/codex-agent/r83cf-desktop-startup/before-query-prerequisite01/files.zip'
ARCHIVE_SHA='4219e710cc0c2acb08d6cd0f3ffd0a6f31685cecd2222997024b497404fe2eda'
GATES=BASE/'qualification01'
CASES=((0,None),(4,None),(5,None),(6,26),(3,None),(1,None),(7,None),(8,None),(9,None))
need=common.need
save=common.save
read=common.read
digest=common.digest

def package():
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text())
    active=[p for p in queue['packages'] if p['status']=='active']
    need(len(active)==1 and queue['active_id']==active[0]['id']=='R8.3ch-query-return','one active CH package')
    return active[0]

def scope():
    need(set(common.common.changed())<=set(package()['allowed_files']),'frozen CH source scope')
    subprocess.run(['git','diff','--check'],cwd=ROOT,check=True,capture_output=True,timeout=30)

def freeze():
    scope()
    need(common.common.git('rev-parse','--short=8','HEAD')=='aecdfa84','CH contract baseline')
    need(not GATES.exists(),'fresh qualification')
    need(common.artifacts(BASE/'baseline01')==read(BASE/'baseline-artifacts.json'),'preserved baseline56')
    save(GATES/'frozen.json',dict(head=common.common.git('rev-parse','HEAD'),
        sources=common.sources(),tools=common.common.all_tools(),package=package(),
        contract=digest(ROOT/'docs/architecture/NATIVE_QUERY_RETURN_CONTRACT.md'),
        font=digest(ROOT/'assets/fonts/reist-vga.psf'),
        baseline=read(BASE/'baseline-artifacts.json'),archive=ARCHIVE_SHA,
        history={p.name:digest(p) for p in BASE.iterdir() if p.is_file()}))

def binding():
    scope();f=read(GATES/'frozen.json')
    need(f['head']==common.common.git('rev-parse','HEAD') and f['sources']==common.sources() and
         f['tools']==common.common.all_tools() and f['package']==package(),'immutable qualification inputs')
    need(f['contract']==digest(ROOT/'docs/architecture/NATIVE_QUERY_RETURN_CONTRACT.md'),'approved frozen contract')
    need(f['font']==digest(ROOT/'assets/fonts/reist-vga.psf'),'immutable pixel oracle font')
    need(digest(ARCHIVE)==f['archive'] and common.artifacts(BASE/'baseline01')==f['baseline'],'immutable baseline/archive')
    for name,sha in f['history'].items():need(digest(BASE/name)==sha,'retained development history')
    return f

def defaults():
    common.BASE=BASE;common.GATES=GATES
    common.defaults()

def make_package():
    common.GATES=GATES
    common.make_package()

def media_binding():
    p=read(GATES/'package.json')
    need(common.artifacts(GATES/'enabled')==p['artifacts'],'immutable selected artifacts')
    return ROOT/p['image']

def runtime():
    image=media_binding();rows=[];started=time.monotonic()
    for case,oom in CASES:
        binding();folder=GATES/f'guest-{case}'
        save(GATES/f'guest-{case}-started.json',dict(case=case,oom=oom,limit=360))
        begin=time.monotonic();proof=guest.capture(image,folder,case,oom)
        elapsed=time.monotonic()-begin;need(elapsed<=360,'individual guest deadline')
        row=dict(case=case,oom=oom,elapsed=elapsed,proof=proof)
        save(GATES/f'guest-{case}-passed.json',row);rows.append(row)
        print('QUERY_GUEST_OK',case,round(elapsed,3),flush=True)
    need(time.monotonic()-started<=3240,'aggregate nine-guest deadline')
    save(GATES/'runtime.json',rows)

def cf_fixture():
    need(digest(ARCHIVE)==ARCHIVE_SHA,'immutable CF archive')
    with zipfile.ZipFile(ARCHIVE) as archive:
        files={name:archive.read(name) for name in archive.namelist()
               if name.startswith(('scripts/','test/','userspace/'))}
    name='scripts/verify_x86_64_desktop_startup.py'
    module=types.ModuleType('query_cf_fixture');module.__file__=str(ROOT/name)
    sys.modules[module.__name__]=module
    exec(compile(files[name],module.__file__,'exec'),module.__dict__)
    return module,files

def gui_proof(folder):
    """Replay existing snapshots. abc remains mandatory at the CF boundary."""
    import struct
    module,_=cf_fixture();p=Path(folder)/'guest';r=read(p/'result.json')
    need(r['passed'] and r['closed'] and r['input_diagnostic'] and r['elapsed']<=600,'closed GUI run')
    need(r['media_before']==r['media_after'],'unchanged GUI media')
    raw=(p/'guest.log').read_bytes()
    need(b'GRAPHICAL_READY\n' in raw and b'DESKTOP_OK\n' in raw,'real frontend and supervisor READY')
    identities=None
    for phase in ('desktop','pointer','text-focus','keyboard','stable'):
        tasks=(p/phase/'tasks.bin').read_bytes();need(len(tasks)==32768,'full eight-task snapshot')
        roles=[]
        for slot in (4,5,6,7):
            state,generation,cr3=struct.unpack_from('<3Q',tasks,slot*4096)
            need(state in (1,2,5,6) and 0<generation<=0x7fffffff and cr3 and not cr3%4096,'live isolated GUI role')
            roles.append((generation,cr3))
        if identities is None:identities=roles
        need(identities==roles,'no GUI role loss or replacement')
    need((p/'desktop/pixels.ppm').read_bytes()!=(p/'pointer/pixels.ppm').read_bytes(),'original pointer300ms')
    need(module.text_focus_ready((p/'text-focus/pixels.ppm').read_bytes()),'actual text focus')
    before=module.keyboard_glyphs((p/'text-focus/pixels.ppm').read_bytes())
    after=module.keyboard_glyphs((p/'keyboard/pixels.ppm').read_bytes())
    stable=module.keyboard_glyphs((p/'stable/pixels.ppm').read_bytes())
    old=read(p/'keyboard-proof.json')
    need(old['before']==json.loads(json.dumps(before)) and old['after']==json.loads(json.dumps(after)) and
         old['passed']==(not before and len(after)==1),'original abc oracle, no altered deadline')
    need(not before and len(stable)==1,'eventual exact abc, no lost input')
    return dict(pointer300ms=True,abc300ms=old['passed'],abc_stable=stable,
                roles=identities,elapsed=r['elapsed'],abc_required_in_CF=True)

def gui():
    module,files=cf_fixture();folder=GATES/'gui';folder.mkdir()
    baseline=ROOT/'build/codex-agent/r83cf-desktop-startup/diagnostic68'
    baseline_hashes={p.relative_to(baseline).as_posix():digest(p) for p in baseline.rglob('*')
        if p.is_file() and (p.name=='pixels.ppm' or p.name in ('guest.json','keyboard-proof.json') or
           ('media' in p.relative_to(baseline).parts and p.name in ('reist-x86_64-bootstrap.elf',
            'reist-x86_64.img','system.ext2','desktop.prg','text.prg','paint.prg','input.prg')))}
    need(baseline_hashes,'retained GUI baseline evidence')
    with module.overlay(files,folder/'cf-overlay'):
        fixture=module.fixture_files();need(not any(p.startswith('arch/') for p in fixture),'fixture cannot replace kernel')
        with module.overlay(fixture,folder/'integration-overlay'):
            common.run(['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeFullDesktop',
                '-OutputDirectory',str((folder/'build').relative_to(ROOT))],folder/'build.log',300)
            common.run([sys.executable,'scripts/build_x86_64_full_desktop_media.py','--input-directory',
                str(folder/'build/x86_64'),'--output-directory',str(folder/'media')],folder/'media.log',180)
            import run_qemu_x86_64_full_desktop as runner
            # Diagnostic originally captured only the old 1KiB task layout.
            # Read the full existing 8*4KiB table; no guest writes or extra stops.
            need(runner.SNAPSHOTS[0]==('tasks','scheduler_tasks',8192),'known diagnostic task extent')
            runner.SNAPSHOTS=(('tasks','scheduler_tasks',32768),)+runner.SNAPSHOTS[1:]
            try:module.exercise(folder/'media',folder/'guest')
            except ValueError as error:
                need(str(error)=='actual focused text application must display abc','only approved deferred abc failure')
                need(read(folder/'guest/keyboard-proof.json')['passed'] is False,'explicit deferred abc receipt')
    proof=gui_proof(folder)
    for role in ('desktop','text','paint','input'):
        before=list((baseline/'media').rglob(role+'.prg'))
        after=list((folder/'media').rglob(role+'.prg'))
        need(len(before)==len(after)==1 and digest(before[0])==digest(after[0]),'identical CF application image '+role)
    for name,sha in baseline_hashes.items():need(digest(baseline/name)==sha,'preserved GUI baseline')
    save(GATES/'gui.json',dict(proof=proof,baseline=str(baseline.relative_to(ROOT)),baseline_hashes=baseline_hashes,
                              artifacts=common.artifacts(folder/'build')))

def review():
    from unittest.mock import patch
    need(all(read(GATES/f'gate-{i}.json')['passed'] for i in range(1,6)),'all five preceding gates')
    binding();image=media_binding();rows=read(GATES/'runtime.json')
    need([(r['case'],r['oom']) for r in rows]==list(CASES),'all nine frozen cases')
    fixture=next(image.parent.glob('programs-*'))
    from build_x86_64_large_image import prepare
    count=guest.cpu.legacy.allocations(prepare((fixture/'program2.prg').read_bytes(),[]))
    for row in rows:
        folder=GATES/f"guest-{row['case']}"
        proof=guest.replay(folder,(folder/'serial.txt').read_text(),(folder/'trace.txt').read_text(),count)
        need(json.loads(json.dumps(proof))==row['proof'],'independent raw runtime replay')
        command=read(folder/'command.json')
        need(('-icount' in command)==(row['case'] in (8,9)),'only query cases use instruction time')
        if '-icount' in command:need(command[command.index('-icount')+1]=='shift=3,sleep=on','fixed query clock')
    folder=GATES/'guest-8';raw=(folder/'reads.bin').read_bytes();config=read(folder/'config.json')
    entries=[json.loads(line) for line in (folder/'reads.jsonl').read_text().splitlines()]
    address=config['s']['query_state64']
    observation=next(e for e in entries if e.get('address')==address and e.get('bytes')==48)
    original=Path.read_bytes
    for offset in (0,8,16,24,32,40):
        bad=bytearray(raw);bad[observation['offset']+offset]^=1;rejected=False
        with patch.object(Path,'read_bytes',lambda p:bytes(bad) if p==folder/'reads.bin' else original(p)):
            try:guest.replay(folder,(folder/'serial.txt').read_text(),(folder/'trace.txt').read_text(),count)
            except ValueError:rejected=True
        need(rejected,'independent rejection of corrupt query owner/budget/complement')
    d=read(GATES/'defaults.json');old=read(BASE/'baseline-artifacts.json');key='x86_64/programs/program0.o'
    need(common.artifacts(GATES/'disabled')==d['artifacts'] and d['baseline']==old and
         all(d['artifacts'][k]==old[k] for k in old if k!=key) and
         digest(GATES/'same-header-path-program0.o')==old[key],'independent exact default56 comparison')
    g=read(GATES/'gui.json')
    need(json.loads(json.dumps(gui_proof(GATES/'gui')))==g['proof'],'independent GUI replay')
    need(common.artifacts(GATES/'gui/build')==g['artifacts'],'GUI build binding')
    for name,sha in g['baseline_hashes'].items():need(digest(ROOT/g['baseline']/name)==sha,'baseline pixels retained')
    binding();scope()
    save(GATES/'review-proof.json',dict(passed=True,frozen=read(GATES/'frozen.json'),
        evidence={p.relative_to(GATES).as_posix():digest(p) for p in GATES.rglob('*')
                  if p.is_file() and 'cache' not in str(p) and p.name!='gate-6.log'}))

def gates():
    freeze();p=package();commands=p['targeted_tests']+p['package_tests']+p['runtime_tests']
    need(len(commands)==6,'six frozen gates')
    for i,(command,limit) in enumerate(zip(commands,(180,600,600,3600,1800,300)),1):
        binding();common.run(command.split(),GATES/f'gate-{i}.log',limit);binding()
        print('QUERY_GATE_OK',i,flush=True)
    for name,sha in read(GATES/'review-proof.json')['evidence'].items():need(digest(GATES/name)==sha,'closed reviewed evidence')
    save(GATES/'acceptance-seal.json',dict(passed=True,frozen=read(GATES/'frozen.json'),
        evidence={p.relative_to(GATES).as_posix():digest(p) for p in GATES.rglob('*')
                  if p.is_file() and 'cache' not in str(p)}))

def diagnostic_gui(folder,existing=None):
    """Exact saved CF inputs; no queue restoration, and exact overlay cleanup."""
    folder=Path(folder).resolve()
    common.need(folder.is_relative_to(BASE) and not folder.exists(),'fresh owned diagnostic')
    common.need(hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()==ARCHIVE_SHA,'immutable CF fixture')
    with zipfile.ZipFile(ARCHIVE) as archive:
        files={name:archive.read(name) for name in archive.namelist()
               if name.startswith(('scripts/','test/','userspace/'))}
    name='scripts/verify_x86_64_desktop_startup.py'
    module=types.ModuleType('query_cf_fixture')
    module.__file__=str(ROOT/name)
    sys.modules[module.__name__]=module
    exec(compile(files[name],module.__file__,'exec'),module.__dict__)
    folder.mkdir(parents=True)
    common.save(folder/'started.json',dict(accepted=False,archive=ARCHIVE_SHA,
                sources=common.sources(),tools=common.common.all_tools()))
    with module.overlay(files,folder/'cf-overlay'):
        integration=module.fixture_files()
        common.need(not any(p.startswith('arch/') for p in integration),'fixture cannot replace kernel')
        result=(module.exercise_existing(folder/'integration',Path(existing),capture=True)
                if existing is not None else module.diagnostic(folder/'integration'))
    common.save(folder/'result.json',result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--diagnostic-gui',type=Path)
    for name in ('gates','defaults','package','runtime','gui','review'):
        group.add_argument('--'+name,action='store_true')
    parser.add_argument('--existing',type=Path)
    args=parser.parse_args()
    if args.diagnostic_gui:print(json.dumps(diagnostic_gui(args.diagnostic_gui,args.existing),sort_keys=True))
    elif args.gates:gates()
    else:
        binding()
        {'defaults':defaults,'package':make_package,'runtime':runtime,'gui':gui,'review':review}[
            next(name for name in ('defaults','package','runtime','gui','review') if getattr(args,name))]()
