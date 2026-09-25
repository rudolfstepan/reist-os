"""Bounded startup-profile evidence; archived CB is only an integration fixture."""
from pathlib import Path
import argparse, contextlib, hashlib, json, os, subprocess, sys, time, zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE='0af9682e'
EVIDENCE=ROOT/'build/codex-agent/r83cf-desktop-startup'
ARCHIVE=ROOT/'build/codex-agent/native-vmware-desktop/services-before-start-profile01/files.zip'
ARCHIVE_SHA='ee40925bd41d0f0c2ab1b66dff19e1a786fc1b6d7f6a60c78367985a18760615'
SOURCES=('userspace/sdk/include/reist/x86_64/graphical_session.h',
         'userspace/sdk/lib/x86_64/shell_graphical.inc',
         'userspace/gui/lib/native_surface.c','userspace/gui/apps/native_client.c',
         'userspace/drivers/ps2/native_session.c','scripts/build_x86_64_graphical_programs.py',
         'userspace/gui/include/reist/gui/surface.h','userspace/gui/include/reist/gui/surface_client.h',
         'userspace/gui/lib/surface_client.c')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def run(command,log,timeout):
    start=time.monotonic()
    with log.open('wb') as f:
        p=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
            timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    result=dict(command=list(map(str,command)),code=p.returncode,seconds=time.monotonic()-start,
                log=str(log.relative_to(ROOT)),sha256=digest(log.read_bytes()))
    log.with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    if p.returncode:raise ValueError(f'{log}: exit {p.returncode}; '+log.read_text(errors='replace')[-1500:])
    return result
@contextlib.contextmanager
def overlay(files,folder):
    """Save exact bytes, refuse overlap drift, restore owned temporary fixture."""
    saved={p:(ROOT/p).read_bytes() if (ROOT/p).exists() else None for p in files}
    folder.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(folder/'before.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p,raw in saved.items():
            if raw is not None:z.writestr(p,raw)
    (folder/'manifest.json').write_text(json.dumps({p:dict(before=digest(saved[p]) if saved[p] is not None else None,
        fixture=digest(raw)) for p,raw in files.items()},indent=2),encoding='utf-8')
    try:
        for p,raw in files.items():(ROOT/p).write_bytes(raw)
        yield
    finally:
        drift=[p for p,raw in files.items() if not (ROOT/p).exists() or (ROOT/p).read_bytes()!=raw]
        if drift:raise ValueError('Fixture changed unexpectedly; preserve for review: '+repr(drift))
        for p,raw in saved.items():
            if raw is None:(ROOT/p).unlink()
            else:(ROOT/p).write_bytes(raw)
        assert all(((ROOT/p).read_bytes()==raw) if raw is not None else not (ROOT/p).exists() for p,raw in saved.items())
        (folder/'restored.json').write_text('{"restored_exactly":true}',encoding='ascii')
def role_build(folder,full):
    from build_user_program import find_zig
    from build_x86_64_graphical_programs import build_roles
    zig=str(find_zig());nasm=Path('C:/tools/nasm-3.02/nasm.exe')
    if not nasm.is_file():raise ValueError('reserved NASM missing')
    build_roles(folder,[zig,'cc'],[str(nasm)],[zig,'ld.lld'],full_desktop=full)
def defaults(folder):
    folder=folder.resolve()
    folder.mkdir(parents=True,exist_ok=False)
    binding={p:digest((ROOT/p).read_bytes()) for p in SOURCES}
    old={p:subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT) for p in SOURCES}
    # The baseline function predates the keyword. Invoke its unchanged signature.
    with overlay(old,folder/'baseline-overlay'):
        code="import sys;sys.path.insert(0,'scripts');from build_user_program import find_zig;from build_x86_64_graphical_programs import build_roles;z=str(find_zig());build_roles(sys.argv[1],[z,'cc'],['C:/tools/nasm-3.02/nasm.exe'],[z,'ld.lld'])"
        run([sys.executable,'-c',code,folder/'baseline'],folder/'baseline.log',180)
    run([sys.executable,__file__,'--role-build',folder/'old'],folder/'old.log',180)
    run([sys.executable,__file__,'--role-build',folder/'full','--full'],folder/'full.log',180)
    hashes={}
    for name in ('desktop','input','text','paint'):
        before=(folder/'baseline'/f'{name}.prg').read_bytes()
        current=(folder/'old'/f'{name}.prg').read_bytes()
        if before!=current:raise ValueError('disabled role changed: '+name)
        full=(folder/'full'/f'{name}.prg').read_bytes()
        if full==current:raise ValueError('startup profile not applied: '+name)
        hashes[name]=dict(old=digest(current),full=digest(full))
    result=dict(passed=True,sources=binding,roles=hashes,baseline=BASE)
    (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
def bounded_guest_source(source):
    deadline=os.environ.get('REIST_CF_QUALIFICATION_END')
    if deadline is None:return source
    end=float(deadline)
    if not time.monotonic()<end<=time.monotonic()+1501:
        raise ValueError('qualification deadline exhausted or invalid')
    return replace_once(source,'end=started+600',
        'end=min(started+540,'+repr(end)+')')

def replace_once(source,old,new):
    if source.count(old)!=1:raise ValueError('fixture substitution not exact: '+old[:100])
    return source.replace(old,new)
def fixture_files():
    if digest(ARCHIVE.read_bytes())!=ARCHIVE_SHA:raise ValueError('CB archive identity')
    with zipfile.ZipFile(ARCHIVE) as z:
        files={p:z.read(p) for p in z.namelist() if not p.startswith('docs/')}
    # Integrate only the new deadline/profile wiring. No other CB corrections.
    header='userspace/sdk/include/reist/x86_64/graphical_session.h'
    s=files[header].decode().replace('\r\n','\n')
    current=(ROOT/header).read_text(encoding='utf-8')
    start=current[current.index('#if defined(REIST_NATIVE_FULL_DESKTOP)'):current.index('#define REIST_GRAPHICAL_RETIRE_MS')]
    s=replace_once(s,'#define REIST_GRAPHICAL_START_MS 3000U\n',start)
    files[header]=s.encode()
    p='userspace/sdk/lib/x86_64/shell_graphical.inc'
    old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT).decode()
    new=(ROOT/p).read_text(encoding='utf-8');s=files[p].decode().replace('\r\n','\n')
    # Apply each reviewed prerequisite hunk against the immutable CB context.
    import difflib
    a=old.splitlines(keepends=True);b=new.splitlines(keepends=True)
    for tag,i,j,k,l in reversed(difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()):
        if tag=='equal':continue
        if i==j:
            anchor=''.join(a[max(0,i-1):i]);added=''.join(b[k:l])
            if s.count(anchor)==1:s=replace_once(s,anchor,anchor+added)
            else:
                anchor=''.join(a[i:i+1]);s=replace_once(s,anchor,added+anchor)
        else:s=replace_once(s,''.join(a[i:j]),''.join(b[k:l]))
    # Accepted CG profile: only the actual compositor imports with64/v9.
    # Input/text/paint keep their existing32/v6 requests.
    s=replace_once(s,
        'reist_x64_task_import_large_periodic(graphical_images[role],&profile,32,&startup)',
        'reist_x64_task_import_desktop_cpu(graphical_images[role],&profile,64,&startup)')
    files[p]=s.encode()
    for p in ('userspace/sdk/include/reist/x86_64/desktop_platform.h',
              'userspace/sdk/lib/x86_64/desktop_startup.c',
              'userspace/sdk/lib/x86_64/desktop_platform.c',
              'test/x86_64_desktop_platform_host.c',
              'userspace/gui/compositor/desktop.c',
              'userspace/gui/compositor/desktop_surface_runtime.c',
              'userspace/sdk/lib/x86_64/desktop_display.c',
              'test/x86_64_desktop_display_host.c',
              'userspace/gui/include/reist/gui/surface.h',
              'userspace/gui/include/reist/gui/surface_client.h',
              'userspace/gui/lib/surface_client.c',
              'userspace/gui/compositor/desktop_surface.c',
              'userspace/sdk/lib/x86_64/shell_full_desktop.inc',
              'userspace/sdk/lib/x86_64/desktop_services.c',
              'userspace/sdk/include/reist/x86_64/desktop_services.h',
              'test/x86_64_desktop_services_host.c'):
        files[p]=(ROOT/p).read_bytes()
    p='scripts/build_x86_64_full_desktop.py';s=files[p].decode().replace('\r\n','\n')
    # Actual module imports are checked before materialization.
    old_call="old_roles(directory / 'original-role-inputs', cc, nasm, ld)"
    if old_call not in s:raise ValueError('full role builder call inventory: '+repr([l for l in s.splitlines() if 'roles(' in l]))
    files[p]=replace_once(s,old_call,"old_roles(directory / 'original-role-inputs', cc, nasm, ld, full_desktop=True)").encode()
    p='Makefile';s=files[p].decode('utf-8').replace('\r\n','\n')
    s=replace_once(s,
        '$(filter 1,$(X86_64_NATIVE_FULL_DESKTOP)),-DREIST_NATIVE_LARGE_PERIODIC=1,)',
        '$(filter 1,$(X86_64_NATIVE_FULL_DESKTOP)),-DREIST_NATIVE_LARGE_PERIODIC=1 -DREIST_NATIVE_DESKTOP_CPU=1,)')
    files[p]=s.encode('utf-8')
    p='scripts/build_x86_64_boot_programs.py';s=files[p].decode('utf-8').replace('\r\n','\n')
    s=replace_once(s,
        "'-DREIST_NATIVE_FULL_DESKTOP=1','-DREIST_NATIVE_LARGE_PERIODIC=1','-Iinclude'",
        "'-DREIST_NATIVE_FULL_DESKTOP=1','-DREIST_NATIVE_LARGE_PERIODIC=1','-DREIST_NATIVE_DESKTOP_CPU=1','-Iinclude'")
    files[p]=s.encode('utf-8')
    return files
def diagnostic(folder,capture=False):
    folder=folder.resolve()
    folder.mkdir(parents=True,exist_ok=False)
    files=fixture_files()
    with overlay(files,folder/'fixture-overlay'):
        run(['pwsh','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeFullDesktop',
             '-OutputDirectory',str((folder/'build').relative_to(ROOT))],folder/'build.log',300)
        run([sys.executable,'scripts/build_x86_64_full_desktop_media.py','--input-directory',folder/'build/x86_64',
             '--output-directory',folder/'media'],folder/'media.log',180)
        run([sys.executable,__file__,'--exercise-media',folder/'media',
             '--exercise-output',folder/'guest',*(['--capture-clients'] if capture else [])],folder/'guest.log',600)
    return dict(diagnostic=True,runtime_accepted=False)

def desktop_glyphs(ppm,text,foreground):
    """Locate actual abc glyph pixels, excluding cursor-only false positives."""
    magic,dimensions,maximum,pixels=ppm.split(b'\n',3)
    width,height=map(int,dimensions.split())
    if magic!=b'P6' or maximum!=b'255' or not 24<=width<=1024 or not 16<=height<=768 or len(pixels)!=width*height*3:
        raise ValueError('bounded canonical keyboard screenshot')
    font=(ROOT/'assets/fonts/reist-vga.psf').read_bytes()[32:32+4096]
    if text not in (b'abc',b'Type'):raise ValueError('bounded glyph oracle')
    foreground=bytes.fromhex(foreground);background=bytes.fromhex('18222d')
    span=len(text)*8
    rows=[b''.join(foreground if font[c*16+y]&(128>>x) else background
                  for c in text for x in range(8)) for y in range(16)]
    anchor=max(range(16),key=lambda y:rows[y].count(foreground));hits=[];offset=0;attempts=0
    while attempts<64:
        at=pixels.find(rows[anchor],offset)
        if at<0:break
        attempts+=1;offset=at+1;start=at-anchor*width*3
        if start<0 or start%3:continue
        x=(start//3)%width;y=start//(width*3)
        if x+span>width or y+16>height:continue
        if all(pixels[start+n*width*3:start+n*width*3+span*3]==row for n,row in enumerate(rows)):
            hits.append((x,y))
    if attempts==64:raise ValueError('ambiguous keyboard pixel search')
    return hits

def keyboard_glyphs(ppm):
    return desktop_glyphs(ppm,b'abc','eaf2fa')

def text_focus_ready(ppm):
    hits=desktop_glyphs(ppm,b'Type','a7bbce')
    _,dimensions,_,pixels=ppm.split(b'\n',3)
    # Fixed accepted diagnostic mode and existing first application task button.
    return dimensions==b'1024 768' and len(hits)==1 and pixels[(750*1024+590)*3:(750*1024+590)*3+3]==bytes.fromhex('000088')

def capture_client_audits(qmp,symbols,output,media,desktop_only=False):
    """Read existing audit buffers through paused guest page tables, no writes."""
    import struct
    folder=output/('desktop-audit' if desktop_only else 'client-audits');folder.mkdir()
    if qmp.call('query-status',{})['running']:raise ValueError('paused client capture')
    def physical(address,size,name):
        if not 0<address<address+size<=0x200000000 or not 0<size<=32768:raise ValueError('physical capture bound')
        path=folder/name
        qmp.call('pmemsave',dict(val=address,size=size,filename=str(path)))
        raw=path.read_bytes()
        if len(raw)!=size:raise ValueError('physical capture length')
        return raw
    tasks=physical(symbols['scheduler_tasks'],32768,'tasks.bin')
    cache={};mask=0x3fffff000
    def table(address):
        if address not in cache:
            if len(cache)>=96:raise ValueError('table capture bound')
            cache[address]=physical(address,4096,'table-%x.bin'%address)
        return cache[address]
    def user(cr3,address,size):
        if not 0<size<=20544 or not 0x410000<=address<address+size<=(0x500000 if desktop_only else 0x440000):raise ValueError('client range')
        raw=bytearray()
        for page in range(7):
            root=cr3
            for shift in (39,30,21):
                entry=struct.unpack_from('<Q',table(root),((address>>shift)&511)*8)[0]
                if entry&7!=7 or entry&128:raise ValueError('client table flags')
                root=entry&mask
            leaf=struct.unpack_from('<Q',table(root),((address>>12)&511)*8)[0]
            if leaf&~mask&~0x60!=(1<<63)|7:raise ValueError('client data leaf')
            count=min(size,4096-(address&4095))
            raw+=physical((leaf&mask)+(address&4095),count,'leaf-%x-%x-%x.bin'%(cr3,address,len(raw)))
            size-=count;address+=count
            if not size:return bytes(raw)
        raise ValueError('client page bound')
    bindings={}
    for slot,role in (((4,'desktop'),) if desktop_only else ((5,'input'),(6,'text'),(7,'paint'))):
        choices=list((media.parent/'build/x86_64').glob('programs-*/'+('full-desktop' if desktop_only else 'original-role-inputs')+'/'+role+'.map'))
        if len(choices)!=1:raise ValueError('unique client map')
        mapping=choices[0];rows=[r.split() for r in mapping.read_text().splitlines() if len(r.split())==5]
        state,generation,cr3=struct.unpack_from('<3Q',tasks,slot*4096)
        if state not in (1,2,5,6) or not generation or not cr3 or cr3&mask!=cr3:raise ValueError('live client task')
        bindings[role]=dict(slot=slot,generation=generation,cr3=cr3,map_sha256=digest(mapping.read_bytes()),objects={})
        objects=[('state',17128)] if desktop_only else [('reist_native_audit',20544)]
        if role=='text':objects += [('text_size',4),('text',38)]
        for name,size in objects:
            values=[int(r[0],16) for r in rows if r[4]==name]
            if len(values)!=1:raise ValueError('unique client object '+name)
            raw=user(cr3,values[0],size);(folder/(role+'-'+name+'.bin')).write_bytes(raw)
            bindings[role]['objects'][name]=dict(address=values[0],bytes=size,sha256=digest(raw))
    if physical(symbols['scheduler_tasks'],32768,'tasks-after.bin')!=tasks:raise ValueError('paused task drift')
    (folder/'binding.json').write_text(json.dumps(dict(clients=bindings,verifier_sha256=digest(Path(__file__).read_bytes())),indent=2),encoding='utf-8')

def exercise_existing(folder,existing,capture=False,keyboard_trace=False,failure_trace=False):
    folder=folder.resolve();folder.mkdir(parents=True,exist_ok=False)
    with overlay(fixture_files(),folder/'fixture-overlay'):
        return exercise(existing.resolve()/'media',folder/'guest',capture=capture,keyboard_trace=keyboard_trace,failure_trace=failure_trace)

def observer_inject(qmp,args):
    """Hardware stops can reject QMP injection before any event is delivered."""
    end=time.monotonic()+5
    for attempt in range(100):
        try:return qmp.call('input-send-event',args)
        except ValueError as error:
            if "'desc': 'VM not running'" not in str(error):raise
            if time.monotonic()>=end:raise
            time.sleep(.01)
    raise TimeoutError('observer input admission bound')

def input_failure_observer(package,link_map,port,output,end):
    """One read-only failure-site trap; no syscall-by-syscall timing trace."""
    import shutil,build_x86_64_c_payload as elf
    import check_x86_64_full_desktop_media as check
    symbols=elf.elf((package/check.KERNEL).read_bytes(),32,large_image=True)['symbols']
    slot=0xffffffff80000000+symbols['scheduler_current_slot']['value']
    tick=0xffffffff80000000+symbols['scheduler_last_tick']['value']
    hits=[int(l.split()[0],16) for l in link_map.read_text().splitlines()
          if l.split() and l.split()[-1]=='input_failure']
    if len(hits)!=1:raise ValueError('unique input failure site')
    body=r"""
import gdb,json,struct,time
class Failure(gdb.Breakpoint):
 def __init__(self):super().__init__('*'+hex(ADDR),internal=True,type=gdb.BP_HARDWARE_BREAKPOINT)
 def stop(self):
  try:
   assert time.monotonic()<END
   mem=lambda a,n:bytes(gdb.selected_inferior().read_memory(a,n))
   if struct.unpack('<I',mem(SLOT,4))[0]!=5:return False
   row={r:int(gdb.parse_and_eval('$'+r))&((1<<64)-1) for r in ('rdi','rsi','rdx','rip','rsp')}
   row['tick']=struct.unpack('<Q',mem(TICK,8))[0]
   (OUT/'input-failure.json').write_text(json.dumps(row))
  except Exception as e:(OUT/'input-failure-error.json').write_text(repr(e))
  return True
Failure()
(OUT/'input-observer-ready').write_text('ready')
"""
    script=output/'input-failure.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nfrom pathlib import Path\nOUT=Path({str(output)!r})\n'+
        f'ADDR={hits[0]}\nSLOT={slot}\nTICK={tick}\nEND={end!r}\n'+body+
        '\nend\ncontinue\ndelete breakpoints\ndetach\nquit 0\n')
    debugger=shutil.which('gdb')
    if not debugger:raise ValueError('failure observer debugger')
    log=(output/'input-failure.log').open('xb')
    try:return subprocess.Popen([debugger,'-q','-nx','-batch','-x',str(script)],cwd=ROOT,
        stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)),log
    except BaseException:log.close();raise

def exercise(media,output,capture=False,keyboard_trace=False,failure_trace=False):
    """Focus the real text task before typing; preserve existing timing checks."""
    import inspect
    import run_qemu_x86_64_full_desktop as runner
    source=bounded_guest_source(inspect.getsource(runner.diagnostic))
    source=replace_once(source,"            for name in ('a','b','c'):","""            # Pointer is536,396 after the original24,12 motion. Select the
            # existing text application's taskbar button at450,752.
            inject([dict(type='rel',data=dict(axis='x',value=-86)),
                    dict(type='rel',data=dict(axis='y',value=356))])
            settle(.3)
            inject([dict(type='btn',data=dict(down=True,button='left'))]);settle(.05)
            inject([dict(type='btn',data=dict(down=False,button='left'))]);settle(.3)
            focused=False
            for focus_turn in range(8):
                focus_path=output/('focus-check%02d.ppm'%focus_turn)
                qmp.call('screendump',dict(filename=str(focus_path)))
                check.need(focus_path.stat().st_size<=4*1024*1024,'bounded focus screenshot')
                if text_focus_ready(focus_path.read_bytes()):focused=True;break
                settle(.2)
            check.need(focused,'actual text focus before keyboard injection')
            snapshot('text-focus');qmp.call('cont',{})
            for name in ('a','b','c'):""")
    source=replace_once(source,"(output/'pointer/pixels.ppm').read_bytes()!=(output/'keyboard/pixels.ppm').read_bytes()",
                        "(output/'text-focus/pixels.ppm').read_bytes()!=(output/'keyboard/pixels.ppm').read_bytes()")
    namespace=dict(runner.__dict__);namespace['text_focus_ready']=text_focus_ready
    class ObservedQMP(runner.QMP):
        def __init__(self,*args):
            started=time.monotonic()
            try:super().__init__(*args)
            except BaseException as error:
                with (Path(output)/'qmp-operations.jsonl').open('a',encoding='ascii') as log:
                    log.write(json.dumps(dict(operation='connect',elapsed=time.monotonic()-started,error=repr(error)))+'\n')
                raise
        def call(self,operation,args):
            started=time.monotonic();row=dict(operation=operation)
            try:
                result=super().call(operation,args);row['passed']=True;return result
            except BaseException as error:row['error']=repr(error);raise
            finally:
                row['elapsed']=time.monotonic()-started
                with (Path(output)/'qmp-operations.jsonl').open('a',encoding='ascii') as log:
                    log.write(json.dumps(row)+'\n')
    namespace['QMP']=ObservedQMP
    if capture:
        source=replace_once(source,"            settle(10);snapshot('stable')",
            "            settle(10);snapshot('stable')\n            capture_clients(qmp,symbols,output)")
        namespace['capture_clients']=lambda qmp,symbols,output:capture_client_audits(qmp,symbols,output,Path(media))
    if capture:
        source=replace_once(source,"settle(.3);snapshot('keyboard');qmp.call('cont',{})",
            "settle(.3);snapshot('keyboard');capture_desktop(qmp,symbols,output);qmp.call('cont',{})")
        namespace['capture_desktop']=lambda qmp,symbols,output:capture_client_audits(qmp,symbols,output,Path(media),desktop_only=True)
    if keyboard_trace:
        namespace['observer_inject']=observer_inject
        source=replace_once(source,"args={'events':events};qmp.call('input-send-event',args)",
                            "args={'events':events};observer_inject(qmp,args)")
        start=source.index('        if input_trace is None and not desktop_trace:')
        stop=source.index("        at=len(raw);vm.stdin.write(b'desktop')",start)
        attach=source[start:stop]
        source=replace_once(source,attach,"        qmp.call('cont',{})\n")
        attach=attach[attach.index('            debugger,debugger_log='):]
        source=replace_once(source,"            snapshot('text-focus');qmp.call('cont',{})",
            "            snapshot('text-focus')\n"+attach)
    exec(compile(source,'<desktop-startup-input-exercise>','exec'),namespace)
    trace=False
    if keyboard_trace:
        trace=next((Path(media).parent/'build/x86_64').glob('programs-*/full-desktop/desktop.map'))
        namespace['desktop_observer']=lambda *args:input_path_observer(*args,keyboard=True)
    if failure_trace:
        source=source.replace("if debugger is not None and debugger.poll() is None:",
                              "if False and debugger is not None and debugger.poll() is None:",1)
        start=source.index('        if input_trace is None and not desktop_trace:')
        stop=source.index("        at=len(raw);vm.stdin.write(b'desktop')",start)
        attach=source[start:stop]
        source=replace_once(source,attach,"        qmp.call('cont',{})\n")
        attach=attach[attach.index('            debugger,debugger_log='):]
        marker="            # Pointer is536,396 after the original24,12 motion. Select the"
        source=replace_once(source,marker,"            qmp.call('stop',{})\n"+attach+marker)
        exec(compile(source,'<input-failure-diagnostic>','exec'),namespace)
        trace=next((Path(media).parent/'build/x86_64').glob('programs-*/original-role-inputs/input.map'))
        namespace['desktop_observer']=input_failure_observer
    result=namespace['diagnostic'](media,output,exercise=True,desktop_trace=trace)
    output=Path(output)
    before=keyboard_glyphs((output/'text-focus/pixels.ppm').read_bytes())
    after=keyboard_glyphs((output/'keyboard/pixels.ppm').read_bytes())
    proof=dict(before=before,after=after,adapter_sha256=digest(source.encode()),
               verifier_sha256=digest(Path(__file__).read_bytes()),passed=not before and len(after)==1)
    (output/'keyboard-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    if not proof['passed']:raise ValueError('actual focused text application must display abc')
    return result
def lifecycle_existing(folder,existing,selector=7,terminal_trace=False):
    """Observe existing text crash/CPU selectors and real replacement generations."""
    if selector not in (7,9):raise ValueError('bounded lifecycle selector')
    import inspect
    folder=folder.resolve();folder.mkdir(parents=True,exist_ok=False)
    with overlay(fixture_files(),folder/'fixture-overlay'):
        import run_qemu_x86_64_full_desktop as runner
        import run_qemu_x86_64_graphical_session as graphical
        source=bounded_guest_source(inspect.getsource(runner.diagnostic))
        source=replace_once(source,"if input_trace is not None or desktop_trace:","if True:")
        source=replace_once(source,"        qmp.call('cont',{})\n        wait(lambda:",
            "        row['selection']=select_fault(symbols,gdbport,output,end)\n        wait(lambda:")
        source=replace_once(source,"        row['passed']=True", """        qmp.call('cont',{})
        until=time.monotonic()+20
        wait(lambda:time.monotonic()>=until,21)
        snapshot('lifecycle')
        qmp.call('cont',{})
        until=time.monotonic()+20
        wait(lambda:time.monotonic()>=until,21)
        snapshot('replacement-stable')
        row['passed']=True""")
        namespace=dict(runner.__dict__)
        trace=False
        if terminal_trace:
            # QMP stop causes batch GDB to detach. Attach after the READY
            # snapshot, immediately before the actual fault observation.
            begin=source.index('        if input_trace is None and not desktop_trace:')
            finish=source.index("        at=len(raw);vm.stdin.write(b'desktop')",begin)
            attach=source[begin:finish]
            body=attach[attach.index('        else:\n')+len('        else:\n'):]
            source=replace_once(source,attach,"        qmp.call('cont',{})\n")
            source=replace_once(source,'        if exercise:\n',
                '        if True:\n'+body+'        if exercise:\n')
            trace=next((existing.resolve()/'build/x86_64').glob('programs-*/full-desktop/desktop.map'))
            namespace['desktop_observer']=terminal_observer
        namespace['SNAPSHOTS']=tuple((n,s,32768 if n=='tasks' else size) for n,s,size in runner.SNAPSHOTS)
        namespace['select_fault']=lambda symbols,port,out,end:graphical.fault_selection(
            existing.resolve()/'build/x86_64/reist-x86_64-bootstrap.elf',symbols,port,out,selector,end)
        exec(compile(source,'<startup-text-crash-diagnostic>','exec'),namespace)
        (folder/'adapter.py').write_text(source,encoding='utf-8')
        result=namespace['diagnostic'](existing.resolve()/'media',folder/'guest',desktop_trace=trace)
    import struct,re
    guest=folder/'guest'
    states={name:[struct.unpack_from('<2Q',(guest/name/'tasks.bin').read_bytes(),n*4096)
                  for n in range(8)] for name in ('desktop','lifecycle','replacement-stable')}
    initial=states['desktop'];replacement=states['lifecycle'];stable=states['replacement-stable']
    preserved=all(initial[n][1]==replacement[n][1]==stable[n][1] and
                  replacement[n][0] in (1,2,5,6) and stable[n][0] in (1,2,5,6) for n in (4,5,7))
    replaced=replacement[6][1]>initial[6][1] and replacement[6][1]==stable[6][1] and all(
        rows[6][0] in (1,2,5,6) for rows in (replacement,stable))
    visible=all(len(desktop_glyphs((guest/name/'pixels.ppm').read_bytes(),b'Type','a7bbce'))==1
                for name in ('lifecycle','replacement-stable'))
    receipts=[struct.unpack('<4I2Q',bytes.fromhex(raw)) for raw in re.findall(
        r'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-Fa-f]{64})',(guest/'guest.log').read_text(errors='replace'))]
    terminal=[r for r in receipts if r[:2]==(6,initial[6][1])]
    terminal_valid=len(terminal)==1 and terminal[0][2]==(134 if selector==7 else 256)
    proof=dict(collection_completed=bool(result['passed']),runtime_accepted=False,
               replacement_observed=replaced,unrelated_generations_preserved=preserved,
               replacement_prompt_visible=visible,tasks=states,selector=selector,terminal=terminal,
               terminal_valid=terminal_valid,passed=replaced and preserved and visible and terminal_valid)
    (guest/'lifecycle-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    if not proof['passed']:raise ValueError('stable isolated text replacement proof failed')
    return result

def deadline_existing(folder,existing):
    """Run the private full-profile startup stall through real root cleanup."""
    import inspect,struct
    folder=folder.resolve();folder.mkdir(parents=True,exist_ok=False)
    with overlay(fixture_files(),folder/'fixture-overlay'):
        import run_qemu_x86_64_full_desktop as runner
        import run_qemu_x86_64_graphical_session as graphical
        selection=replace_once(inspect.getsource(graphical.fault_selection),
            "selector in range(1,15)","selector == 15")
        selected=dict(graphical.__dict__)
        exec(compile(selection,'<full-startup-stall-selector>','exec'),selected)
        source=replace_once(bounded_guest_source(inspect.getsource(runner.diagnostic)),
            "if input_trace is not None or desktop_trace:","if True:")
        source=replace_once(source,"        qmp.call('cont',{})\n        wait(lambda:",
            "        row['selection']=select_fault(symbols,gdbport,output,end)\n        wait(lambda:")
        source=replace_once(source,
            "        check.need(b'GRAPHICAL_READY\\n' in raw and b'DESKTOP_OK\\n' in raw,'actual frontend and supervisor READY')",
            "        check.need(b'GRAPHICAL_READY\\n' not in raw and b'DESKTOP_OK\\n' not in raw and raw.count(b'C:\\\\>')>=2,'startup cancelled without READY')")
        namespace=dict(runner.__dict__)
        namespace['SNAPSHOTS']=tuple((n,s,32768 if n=='tasks' else size) for n,s,size in runner.SNAPSHOTS)
        namespace['select_fault']=lambda symbols,port,out,end:selected['fault_selection'](
            existing.resolve()/'build/x86_64/reist-x86_64-bootstrap.elf',symbols,port,out,15,end)
        exec(compile(source,'<full-startup-stall-diagnostic>','exec'),namespace)
        (folder/'adapter.py').write_text(source,encoding='utf-8')
        (folder/'selector.py').write_text(selection,encoding='utf-8')
        result=namespace['diagnostic'](existing.resolve()/'media',folder/'guest')
    guest=folder/'guest';snapshot=guest/'desktop'
    tasks=(snapshot/'tasks.bin').read_bytes();profiles=(snapshot/'profiles.bin').read_bytes()
    reaped=not any(tasks[4*4096:]) and not any(profiles[4*32:])
    root=struct.unpack_from('<2Q',tasks)
    devices={n:struct.unpack('<16Q',(snapshot/(n+'.bin')).read_bytes()) for n in ('display','input')}
    fenced=all(all(v[i]^v[i+8]==2**64-1 for i in range(8)) and (not v[0] or v[3]==1) for v in devices.values())
    raw=(guest/'guest.log').read_bytes();receipts=graphical.reap_records(raw)
    desktop=[r for r in receipts if r[0]==4]
    terminal=len(desktop)==1 and desktop[0][2] in (77,110) and desktop[0][3] in (3,4)
    proof=dict(runtime_accepted=False,reaped=reaped,fenced=fenced,root=root,desktop_receipts=desktop,
               passed=bool(result['passed']) and reaped and fenced and terminal and root[0] in (1,2,5,6) and root[1]==1)
    (guest/'deadline-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    if not proof['passed']:raise ValueError('startup deadline cancellation/reap proof failed')
    return result

def terminal_observer(package,link_map,port,output,end,scene=False,calls=False):
    """Observe terminal transition only, without modifying guest memory."""
    import shutil,build_x86_64_c_payload as elf
    import check_x86_64_full_desktop_media as check
    kernel=(package/check.KERNEL).read_bytes()
    symbols=elf.elf(kernel,32,large_image=True)['symbols']
    names=('family_terminal64.restore','scheduler_current_slot','process_run_receipt',
           'scheduler_tasks','scheduler_cpu_budgets','scheduler_cpu_windows')
    addresses={n:0xffffffff80000000+symbols[n]['value'] for n in names}
    failures=[int(row.split()[0],16) for row in Path(link_map).read_text().splitlines()
              if len(row.split())==5 and row.split()[4]=='launch_failed']
    if len(failures)!=1:raise ValueError('exact launch_failed symbol')
    addresses['launch_failed']=failures[0]
    configs=[int(row.split()[0],16) for row in Path(link_map).read_text().splitlines()
             if len(row.split())==5 and row.split()[4]=='config']
    if len(configs)!=1:raise ValueError('exact platform config symbol')
    addresses['platform_config']=configs[0]
    if calls:
        for name in ('desktop_entry_call','previous'):
            found=[int(r.split()[0],16) for r in Path(link_map).read_text().splitlines()
                   if len(r.split())==5 and r.split()[4]==name]
            if len(found)!=1:raise ValueError('exact call profile symbol '+name)
            addresses[name]=found[0]
    scene_setup=''
    if scene:
        import re
        rows=[r.split() for r in Path(link_map).read_text().splitlines()
              if len(r.split())==5 and r.split()[4]=='frontend_scene_ready']
        if len(rows)!=1:raise ValueError('scene symbol')
        address=int(rows[0][0],16);size=int(rows[0][2],16)
        program=Path(link_map).with_suffix('.prg')
        dis=subprocess.run(['objdump','-d','-Mintel',f'--start-address={address}',
            f'--stop-address={address+size}',str(program)],capture_output=True,text=True,check=True,timeout=30).stdout
        sites=re.findall(r'^\s*([0-9a-f]+):.*\bret\s*$',dis,re.M)
        if len(sites)!=1:raise ValueError('single scene return site')
        addresses.update(scene_entry=address,scene_timeout=int(sites[0],16))
        for name in ('config','previous'):
            found=[int(r.split()[0],16) for r in Path(link_map).read_text().splitlines()
                   if len(r.split())==5 and r.split()[4]==name]
            if len(found)!=1:raise ValueError('exact platform symbol '+name)
            addresses['platform_'+name]=found[0]
        layout=json.loads((EVIDENCE/'scene-layout/layout.json').read_text())
        scene_setup='LAYOUT='+repr(layout)+'\n'

    body=r'''
import gdb,struct,json,time
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
count=0
class Terminal(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(S['family_terminal64.restore']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    def stop(self):
        global count
        try:
            count+=1;assert count<=64 and time.monotonic()<END
            receipt=struct.unpack('<4I2Q',mem(S['process_run_receipt'],32))
            if receipt[0]!=4:return False
            slot=struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0];assert slot==4
            task=mem(S['scheduler_tasks']+slot*4096,4096)
            regs={n:struct.unpack_from('<Q',task,o+1984)[0] for n,o in
                [('rip',96),('rsp',104),('rdx',128),('rbp',136),('rsi',144),('rdi',152),('r8',160),('rax',232),('rcx',240)]}
            (OUT/'terminal-task.bin').write_bytes(task)
            sp=regs['rsp'];assert 0x408000<=sp<0x410000
            frame=struct.unpack_from('<Q',task,32+((sp-0x400000)//4096)*8)[0]
            (OUT/'terminal.json').write_text(json.dumps(dict(receipt=receipt,registers=regs,count=count,stack_base=sp,stack_frame=frame)))
            # A4GiB machine places RAM above the PCI hole above4GiB physical.
            assert frame and not frame%4096 and frame<0x200000000
            # Terminal handling can already use the supervisor CR3. Read only
            # the exact owned stack frame via the established direct map.
            def user_mem(address,size):
                assert 0<size<=32768 and 0<address<0x800000000000
                data=bytearray();cr3=struct.unpack_from('<Q',task,16)[0]
                while len(data)<size:
                    at=address+len(data);table=cr3
                    for shift in (39,30,21):
                        entry=struct.unpack('<Q',mem(0xffff800000000000+table+((at>>shift)&511)*8,8))[0]
                        assert entry&1 and not entry&128
                        table=entry&0x000ffffffffff000
                    leaf=struct.unpack('<Q',mem(0xffff800000000000+table+((at>>12)&511)*8,8))[0]
                    assert leaf&1
                    amount=min(size-len(data),4096-(at&4095))
                    data.extend(mem(0xffff800000000000+(leaf&0x000ffffffffff000)+(at&4095),amount))
                return bytes(data)
            (OUT/'terminal-stack.bin').write_bytes(user_mem(sp,0x410000-sp))
            config=user_mem(S['platform_config'],72)
            channel=struct.unpack_from('<Q',config,64)[0]
            (OUT/'terminal-config.bin').write_bytes(config)
            (OUT/'terminal-channels.bin').write_bytes(user_mem(channel,2592))
            for n in ('scheduler_cpu_budgets','scheduler_cpu_windows'):(OUT/(n+'.bin')).write_bytes(mem(S[n],256))
            (OUT/'terminal.json').write_text(json.dumps(dict(receipt=receipt,registers=regs,count=count,stack_base=sp,stack_frame=frame)))
            self.enabled=False
            return False
        except BaseException as error:
            (OUT/'terminal-observer-error.json').write_text(json.dumps(dict(error=repr(error))));return True
class Failure(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(S['launch_failed']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    def stop(self):
        try:
            assert time.monotonic()<END
            regs={n:int(gdb.parse_and_eval('$'+n)) for n in ('rip','rsp','rbp','rdi','rsi')}
            sp=regs['rsp'];assert 0x408000<=sp<0x410000
            (OUT/'adapter-failure.json').write_text(json.dumps(regs))
            (OUT/'adapter-failure-stack.bin').write_bytes(mem(sp,0x410000-sp))
            self.enabled=False;return False
        except BaseException as error:
            (OUT/'adapter-observer-error.json').write_text(json.dumps(dict(error=repr(error))));return True
scene_args={}
def scene_times():
    u64=lambda a:struct.unpack('<Q',mem(a,8))[0]
    c=u64(S['platform_config']+LAYOUT['reist_desktop_platform_config.channels'])
    base=c+LAYOUT['reist_desktop_channels.config']
    inp=u64(base+LAYOUT['reist_desktop_channels_config.input'])
    return dict(now=u64(S['platform_previous']),end=u64(base+LAYOUT['reist_desktop_channels_config.start_deadline_ms']),
        input_sequence=u64(inp+LAYOUT['reist_desktop_input_state.sequence']),
        input_healthy=u64(inp+LAYOUT['reist_desktop_input_state.healthy_ms']),
        app_sequence=list(struct.unpack('<2Q',mem(c+LAYOUT['reist_desktop_channels.health_sequence'],16))),
        app_healthy=list(struct.unpack('<2Q',mem(c+LAYOUT['reist_desktop_channels.health_ms'],16))))
class SceneEntry(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(S['scene_entry']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    def stop(self):
        global scene_args
        scene_args={n:int(gdb.parse_and_eval('$'+r)) for n,r in
            [('runtime','rdi'),('manager','rsi'),('windows','rdx')]}
        (OUT/'scene-entry.json').write_text(json.dumps(scene_times()))
        self.enabled=False;return False
class SceneTimeout(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(S['scene_timeout']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
        self.calls=0;self.results=[]
    def stop(self):
        try:
            self.calls+=1;assert self.calls<=2048 and scene_args and time.monotonic()<END
            value=int(gdb.parse_and_eval('$eax'))&0xffffffff
            self.results.append(dict(result=value,timing=scene_times()))
            self.results=self.results[-64:]
            if value!=0xffffff92:return False
            (OUT/'scene-returns.json').write_text(json.dumps(self.results))
            result=dict(addresses=scene_args,timing=scene_times(),slots=[],windows=[])
            for array,typ,base,count in [('slots','desktop_surface_slot_t',scene_args['manager'],LAYOUT['slots']),
                ('windows','desktop_window_t',scene_args['windows'],LAYOUT['windows'])]:
                for n in range(count):
                    row={}
                    for name,offset in LAYOUT.items():
                        if name.startswith(typ+'.'):
                            field=name.split('.')[1];words=2 if field in ('owner','handle') else 1
                            row[field]=list(struct.unpack('<'+'I'*words,mem(base+n*LAYOUT[typ]+offset,4*words)))
                    result[array].append(row)
            (OUT/'scene-timeout.json').write_text(json.dumps(result))
            self.enabled=False;return False
        except BaseException as error:
            (OUT/'scene-observer-error.json').write_text(json.dumps(dict(error=repr(error))));return True
class Calls(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(S['desktop_entry_call']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
        self.count=0;self.counts={};self.recent=[]
    def stop(self):
        try:
            self.count+=1;assert self.count<=8192 and time.monotonic()<END
            op=int(gdb.parse_and_eval('$esi'));sp=int(gdb.parse_and_eval('$rsp'))
            assert 0x408000<=sp<=0x410000-8
            ret=struct.unpack('<Q',mem(sp,8))[0]
            now=struct.unpack('<Q',mem(S['previous'],8))[0]
            key=str(op)+':'+hex(ret)
            self.counts[key]=self.counts.get(key,0)+1
            self.recent.append([self.count,now,op,ret]);self.recent=self.recent[-128:]
            (OUT/'call-profile.json').write_text(json.dumps(dict(count=self.count,counts=self.counts,recent=self.recent)))
            return False
        except BaseException as error:
            (OUT/'call-observer-error.json').write_text(json.dumps(dict(error=repr(error))));return True
Terminal()
Failure()
if 'desktop_entry_call' in S:Calls()
if 'scene_entry' in S:SceneEntry();SceneTimeout()
(OUT/'input-observer-ready').write_text('ready')
'''
    script=output/'terminal-observer.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nfrom pathlib import Path\nOUT=Path({str(output)!r})\nS={addresses!r}\nEND={end!r}\n'+
        scene_setup+body+'\nend\ncontinue\ndelete breakpoints\ndetach\nquit 0\n',encoding='ascii')
    debugger=shutil.which('gdb')
    if not debugger:raise ValueError('GDB unavailable')
    command=[debugger,'-q','-nx','-batch','-x',str(script)]
    (output/'terminal-observer.json').write_text(json.dumps(dict(command=command,
        kernel_sha256=digest(kernel),script_sha256=digest(script.read_bytes()))),encoding='utf-8')
    log=(output/'terminal-observer.log').open('xb')
    try:return subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)),log
    except BaseException:log.close();raise
def observe_terminal(folder,existing,scene=False,calls=False):
    folder=folder.resolve();existing=existing.resolve();folder.mkdir(parents=True,exist_ok=False)
    with overlay(fixture_files(),folder/'fixture-overlay'):
        import run_qemu_x86_64_full_desktop as runner
        runner.desktop_observer=lambda *args:terminal_observer(*args,scene=scene,calls=calls)
        mapping=next((existing/'build/x86_64').glob('programs-*/full-desktop/desktop.map'))
        return runner.diagnostic(existing/'media',folder/'guest',desktop_trace=mapping)
def input_path_observer(package,link_map,port,output,end,loop=False,keyboard=False):
    """Four read-only, slot-filtered hardware probes; no acceptance timing claim."""
    import shutil,build_x86_64_c_payload as elf
    import check_x86_64_full_desktop_media as check
    kernel=(package/check.KERNEL).read_bytes()
    symbols=elf.elf(kernel,32,large_image=True)['symbols']
    addresses={n:0xffffffff80000000+symbols[n]['value'] for n in
               ('scheduler_current_slot','timer_runtime_ticks')}
    driver=Path(link_map).parent.parent/'original-role-inputs/input.map'
    probes=[]
    names=([('x86os_mouse_event',link_map,4),('reist_desktop_input_push',link_map,4),
            ('x86os_pointer_update',link_map,4),('x86os_puts',link_map,4)] if loop else
           [('publish',driver,5),('reist_desktop_input_push',link_map,4),
            ('x86os_pointer_update',link_map,4),('startup_commit',link_map,4)])
    if keyboard:
        text_map=Path(link_map).parent.parent/'original-role-inputs/text.map'
        names=[('publish',driver,5),('enqueue_surface_keyboard',link_map,4),
               ('reist_native_audit_append',text_map,6),('launch_send',link_map,4)]
    for name,mapping,slot in names:
        rows=[r.split() for r in Path(mapping).read_text().splitlines()
              if len(r.split())==5 and r.split()[4]==name]
        if len(rows)!=1:raise ValueError('unique input probe '+name)
        probes.append((name,int(rows[0][0],16),slot))
    body=r'''
import gdb,struct,json,time
count=0
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
class Probe(gdb.Breakpoint):
    def __init__(self,name,address,slot):
        super().__init__('*'+hex(address),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
        self.label=name;self.slot=slot
    def stop(self):
        global count
        try:
            slot=struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]
            if slot!=self.slot:return False
            count+=1
            assert count<=4096 and time.monotonic()<END
            regs={n:int(gdb.parse_and_eval('$'+n)) & 0xffffffffffffffff for n in ('rdi','rsi','rdx')}
            row=dict(index=count,probe=self.label,ticks=struct.unpack('<Q',mem(S['timer_runtime_ticks'],8))[0],
                     host=time.monotonic(),registers=regs)
            sp=int(gdb.parse_and_eval('$rsp'));assert 0x408000<=sp<=0x410000-8
            row['return']=struct.unpack('<Q',mem(sp,8))[0]
            if self.label=='x86os_puts':
                row['text']=mem(regs['rdi'],64).split(b'\0',1)[0].decode('ascii',errors='replace')
            if self.label in ('publish','reist_desktop_input_push','startup_commit','reist_native_audit_append'):
                pointer=regs['rdi' if self.label=='publish' else 'rsi']
                assert 0x400000<=pointer<0x2000000-64
                row['raw']=mem(pointer,64).hex()
            with (OUT/'input-path.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            return False
        except BaseException as error:
            (OUT/'input-path-error.json').write_text(json.dumps(dict(error=repr(error))))
            return True
for args in PROBES:Probe(*args)
(OUT/'input-observer-ready').write_text('ready')
'''
    script=output/'input-path.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\n'+
        f'target remote 127.0.0.1:{port}\npython\nfrom pathlib import Path\nOUT=Path({str(output)!r})\nS={addresses!r}\nPROBES={probes!r}\nEND={end!r}\n'+
        body+'\nend\ncontinue\ndelete breakpoints\ndetach\nquit 0\n',encoding='ascii')
    debugger=shutil.which('gdb')
    if not debugger:raise ValueError('GDB unavailable')
    command=[debugger,'-q','-nx','-batch','-x',str(script)]
    (output/'input-path-binding.json').write_text(json.dumps(dict(command=command,
        kernel_sha256=digest(kernel),script_sha256=digest(script.read_bytes()),
        desktop_map_sha256=digest(Path(link_map).read_bytes()),input_map_sha256=digest(driver.read_bytes()),
        verifier_sha256=digest(Path(__file__).read_bytes()))),encoding='utf-8')
    log=(output/'input-path.log').open('xb')
    try:return subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)),log
    except BaseException:log.close();raise

def observe_input_path(folder,existing,loop=False):
    import inspect
    folder=folder.resolve();existing=existing.resolve();folder.mkdir(parents=True,exist_ok=False)
    with overlay(fixture_files(),folder/'fixture-overlay'):
        import run_qemu_x86_64_full_desktop as runner
        source=bounded_guest_source(inspect.getsource(runner.diagnostic))
        source=replace_once(source,'    def snapshot(label):',
            "    def snapshot(label):\n        if label in ('desktop','pointer','keyboard'):return")
        start=source.index('        if input_trace is None and not desktop_trace:')
        stop=source.index("        at=len(raw);vm.stdin.write(b'desktop')",start)
        attach=source[start:stop]
        source=replace_once(source,attach,"        qmp.call('cont',{})\n")
        attach=attach[attach.index('            debugger,debugger_log='):]
        source=replace_once(source,'        if exercise:',
            "        if exercise:\n            qmp.call('stop',{})\n"+attach)
        source=replace_once(source,"            inject([dict(type='rel',data=dict(axis='x',value=24)),",
            "            wait(lambda:(output/'input-path.jsonl').exists(),5)\n"
            "            check.need(debugger.poll() is None,'observer live before input')\n"
            "            inject([dict(type='rel',data=dict(axis='x',value=24)),")
        (folder/'adapter.py').write_text(source,encoding='utf-8')
        namespace=dict(runner.__dict__)
        namespace['desktop_observer']=lambda *args:input_path_observer(*args,loop=loop)
        exec(compile(source,'<read-only-input-path>','exec'),namespace)
        mapping=next((existing/'build/x86_64').glob('programs-*/full-desktop/desktop.map'))
        return namespace['diagnostic'](existing/'media',folder/'guest',exercise=True,desktop_trace=mapping)

QUAL=EVIDENCE/'qualification05'

def qualification_binding():
    import tomllib
    queue=tomllib.loads((ROOT/'automation/reist-s03b.toml').read_text(encoding='utf-8'))
    if queue['active_id']!='R8.3cf-desktop-startup':raise ValueError('sole active CF')
    package=next(p for p in queue['packages'] if p['id']==queue['active_id'])
    allowed=set(package['allowed_files'])
    status=subprocess.check_output(['git','status','--porcelain=v1','-z','--untracked-files=all'],cwd=ROOT)
    for entry in status.decode().split('\0'):
        if entry and (entry[:2].strip() not in ('M','??','A') or entry[3:] not in allowed):
            raise ValueError('unattributed/out-of-scope candidate '+entry)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    prefixes=('arch/','userspace/','include/','scripts/','test/','assets/','kernel/','lib/','drivers/','fs/','mm/')
    paths=sorted(p for p in set(tracked)|allowed if p and (p=='Makefile' or p.startswith(prefixes)))
    files={p:digest((ROOT/p).read_bytes()) for p in paths if (ROOT/p).is_file()}
    return dict(base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
                files=files,fixture={p:digest(raw) for p,raw in fixture_files().items()},archive=ARCHIVE_SHA,
                gates=[*package['targeted_tests'],*package['package_tests'],*package['runtime_tests']])

def freeze_qualification():
    QUAL.mkdir(parents=True,exist_ok=False)
    binding=qualification_binding()
    (QUAL/'binding.json').write_text(json.dumps(binding,indent=2),encoding='utf-8')
    return binding

def qualification_unchanged():
    frozen=json.loads((QUAL/'binding.json').read_text())
    if qualification_binding()!=frozen:raise ValueError('frozen candidate drift')

def qualification_defaults():
    qualification_unchanged()
    result=defaults(QUAL/'defaults')
    qualification_unchanged()
    return result

def qualification_runtime():
    qualification_unchanged()
    key='REIST_CF_QUALIFICATION_END'
    if key in os.environ:raise ValueError('unexpected external qualification deadline')
    os.environ[key]=repr(time.monotonic()+1500)
    try:
        diagnostic(QUAL/'normal',capture=True)
        lifecycle_existing(QUAL/'crash',QUAL/'normal',selector=7)
        lifecycle_existing(QUAL/'cpu',QUAL/'normal',selector=9)
        deadline_existing(QUAL/'deadline',QUAL/'normal')
    finally:os.environ.pop(key,None)
    qualification_unchanged()
    artifacts={}
    for name in ('normal','crash','cpu','deadline'):
        for path in sorted((QUAL/name).rglob('*')):
            if path.is_file():
                with path.open('rb') as stream:artifacts[path.relative_to(QUAL).as_posix()]=hashlib.file_digest(stream,'sha256').hexdigest()
    (QUAL/'runtime-artifacts.json').write_text(json.dumps(artifacts,indent=2),encoding='utf-8')
    return dict(passed=True,fresh_guests=4,artifacts=len(artifacts))

def review_live_roles(snapshot,tasks_path=None):
    import struct
    tasks=(tasks_path or snapshot/'tasks.bin').read_bytes()
    profiles=(snapshot/'profiles.bin').read_bytes();family=(snapshot/'family.bin').read_bytes()
    budgets=(snapshot/'cpu-budgets.bin').read_bytes()
    if len(tasks)!=32768 or len(profiles)!=256 or len(family)!=512 or len(budgets)!=256:raise ValueError('snapshot sizes')
    root_state,root_generation=struct.unpack_from('<2Q',tasks)
    if root_state not in (1,2,5,6) or root_generation!=1:raise ValueError('original live root')
    root=root_generation<<32;owners=[]
    common=sum(1<<n for n in (9,22,40,41,42,53))
    if struct.unpack_from('<2Q',budgets)!=(root_generation,64):raise ValueError('root CPU64')
    for slot in range(4,8):
        state,generation=struct.unpack_from('<2Q',tasks,slot*4096)
        if state not in (1,2,5,6) or not 0<generation<=0x7ffffffe:raise ValueError('live role')
        owner=generation<<32|slot;owners.append(owner)
        low=common|(1<<54 if slot!=5 else 0)
        if slot==4:low|=sum(1<<n for n in (4,5,15,20,49,52,55,58))
        high=(1<<49)|(1<<63) if slot==4 else 1<<49 if slot==5 else 0
        if struct.unpack_from('<4Q',profiles,slot*32)!=(generation,low,high,0):raise ValueError('role authority')
        if struct.unpack_from('<2Q',family,slot*64)!=(owner,root):raise ValueError('role parent')
        if struct.unpack_from('<2Q',budgets,slot*32)!=(generation,64 if slot==4 else 32):raise ValueError('role CPU bound')
    for name,index in (('display',0),('input',1)):
        values=struct.unpack('<16Q',(snapshot/(name+'.bin')).read_bytes())
        if not all(values[i]^values[i+8]==2**64-1 for i in range(8)):raise ValueError('device integrity')
        if values[:2]!=(owners[index],root) or not values[2] or values[3]:raise ValueError('device owner')
    return owners

def qualification_review():
    import struct
    qualification_unchanged()
    artifacts=json.loads((QUAL/'runtime-artifacts.json').read_text())
    for name,expected in artifacts.items():
        path=(QUAL/name).resolve()
        if not path.is_relative_to(QUAL.resolve()):raise ValueError('artifact path')
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected:raise ValueError('artifact drift '+name)
    for name in ('desktop','input','text','paint'):
        old=(QUAL/'defaults/old'/f'{name}.prg').read_bytes()
        if old!=(QUAL/'defaults/baseline'/f'{name}.prg').read_bytes():raise ValueError('disabled role drift')
        if old==(QUAL/'defaults/full'/f'{name}.prg').read_bytes():raise ValueError('missing selected role')
    for case in ('normal','crash','cpu','deadline'):
        result=json.loads((QUAL/case/'guest/result.json').read_text())
        if not result['passed'] or not result['closed'] or result['media_before']!=result['media_after']:raise ValueError('guest collection/integrity')
    guest=QUAL/'normal/guest'
    if keyboard_glyphs((guest/'text-focus/pixels.ppm').read_bytes()) or len(keyboard_glyphs((guest/'keyboard/pixels.ppm').read_bytes()))!=1:
        raise ValueError('raw300ms keyboard pixels')
    initial=(guest/'desktop/pixels.ppm').read_bytes();pointer=(guest/'pointer/pixels.ppm').read_bytes()
    if initial==pointer:raise ValueError('pointer frame unchanged')
    _,dimensions,maximum,pixels=pointer.split(b'\n',3)
    if dimensions!=b'1024 768' or maximum!=b'255':raise ValueError('pointer display shape')
    for y in range(12):
        for x in range(8):
            if not x or not y or x==y//2:
                offset=((396+y)*1024+536+x)*3
                if pixels[offset:offset+3]!=b'\xff'*3:raise ValueError('actual moved pointer raster')
    owners=review_live_roles(guest/'keyboard',guest/'desktop-audit/tasks.bin')
    if review_live_roles(guest/'stable',guest/'client-audits/tasks.bin')!=owners:raise ValueError('normal role loss')
    for case,status in (('crash',134),('cpu',256)):
        guest=QUAL/case/'guest'
        before=review_live_roles(guest/'desktop');after=review_live_roles(guest/'lifecycle')
        if review_live_roles(guest/'replacement-stable')!=after:raise ValueError('replacement unstable')
        if any(before[i]!=after[i] for i in (0,1,3)) or after[2]<=before[2]:raise ValueError('isolated replacement')
        import re
        receipts=[struct.unpack('<4I2Q',bytes.fromhex(h)) for h in re.findall(
            r'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})',(guest/'guest.log').read_text())]
        terminal=[r for r in receipts if r[:2]==(6,before[2]>>32)]
        if len(terminal)!=1 or terminal[0][2:4]!=(status,3):raise ValueError('actual fault terminal')
        for stage in ('lifecycle','replacement-stable'):
            if len(desktop_glyphs((guest/stage/'pixels.ppm').read_bytes(),b'Type','a7bbce'))!=1:raise ValueError('replacement scene')
    guest=QUAL/'deadline/guest';snapshot=guest/'desktop'
    if any((snapshot/'tasks.bin').read_bytes()[4*4096:]) or any((snapshot/'profiles.bin').read_bytes()[4*32:]):raise ValueError('deadline reap')
    tasks=(snapshot/'tasks.bin').read_bytes()
    if len(tasks)!=32768 or len((snapshot/'profiles.bin').read_bytes())!=256:
        raise ValueError('deadline snapshot sizes')
    state,generation=struct.unpack_from('<2Q',tasks)
    if state not in (1,2,5,6) or generation!=1:raise ValueError('deadline original root')
    raw=(guest/'guest.log').read_bytes()
    import re
    receipts=[struct.unpack('<4I2Q',bytes.fromhex(h.decode())) for h in re.findall(
        rb'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-Fa-f]{64})',raw)]
    desktop=[r for r in receipts if r[0]==4]
    if len(desktop)!=1 or desktop[0][2] not in (77,110) or desktop[0][3] not in (3,4):
        raise ValueError('actual startup terminal')
    if b'DESKTOP_OK' in raw or b'GRAPHICAL_READY' in raw or raw.count(b'C:\\>')<2:raise ValueError('deadline shell/READY')
    for name in ('display','input'):
        values=struct.unpack('<16Q',(snapshot/(name+'.bin')).read_bytes())
        if not all(values[i]^values[i+8]==2**64-1 for i in range(8)) or (values[0] and values[3]!=1):raise ValueError('deadline fence')
    with overlay(fixture_files(),QUAL/'review-fixture-overlay'):
        import check_x86_64_full_desktop_media as check
        check.verify(QUAL/'normal/media')
    qualification_unchanged()
    result=dict(passed=True,fresh_guests=4,source_binding=digest((QUAL/'binding.json').read_bytes()),
                artifacts=digest((QUAL/'runtime-artifacts.json').read_bytes()))
    (QUAL/'review.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--role-build',type=Path);g.add_argument('--development-defaults',type=Path)
    g.add_argument('--diagnostic',type=Path);g.add_argument('--defaults',action='store_true')
    g.add_argument('--runtime',action='store_true');g.add_argument('--review',action='store_true')
    g.add_argument('--observe-calls',type=Path);g.add_argument('--observe-terminal',type=Path);g.add_argument('--observe-scene',type=Path);p.add_argument('--existing',type=Path)
    g.add_argument('--exercise-media',type=Path);p.add_argument('--exercise-output',type=Path)
    g.add_argument('--observe-input-path',type=Path)
    g.add_argument('--observe-input-loop',type=Path)
    g.add_argument('--exercise-existing',type=Path)
    g.add_argument('--lifecycle-existing',type=Path)
    p.add_argument('--capture-clients',action='store_true')
    p.add_argument('--trace-keyboard',action='store_true')
    p.add_argument('--trace-input-failure',action='store_true')
    p.add_argument('--full',action='store_true');a=p.parse_args()
    if a.role_build:role_build(a.role_build,a.full);return
    if a.development_defaults:print(json.dumps(defaults(a.development_defaults)));return
    if a.diagnostic:print(json.dumps(diagnostic(a.diagnostic,capture=a.capture_clients)));return
    if a.observe_input_path or a.observe_input_loop:
        if not a.existing:p.error('--existing is required')
        print(json.dumps(observe_input_path(a.observe_input_path or a.observe_input_loop,a.existing,loop=bool(a.observe_input_loop))));return
    if a.lifecycle_existing:
        if not a.existing:p.error('--existing is required')
        print(json.dumps(lifecycle_existing(a.lifecycle_existing,a.existing)));return
    if a.exercise_existing:
        if not a.existing:p.error('--existing is required')
        print(json.dumps(exercise_existing(a.exercise_existing,a.existing,capture=a.capture_clients,keyboard_trace=a.trace_keyboard,failure_trace=a.trace_input_failure)));return
    if a.exercise_media:
        if not a.exercise_output:p.error('--exercise-output is required')
        print(json.dumps(exercise(a.exercise_media,a.exercise_output,capture=a.capture_clients)));return
    if a.observe_terminal or a.observe_scene or a.observe_calls:
        if not a.existing:p.error('--existing is required')
        print(json.dumps(observe_terminal(a.observe_terminal or a.observe_scene or a.observe_calls,a.existing,scene=bool(a.observe_scene),calls=bool(a.observe_calls))));return
    if a.defaults:print(json.dumps(qualification_defaults()));return
    if a.runtime:print(json.dumps(qualification_runtime()));return
    if a.review:print(json.dumps(qualification_review()));return
    raise ValueError('missing qualification mode')
if __name__=='__main__':main()
