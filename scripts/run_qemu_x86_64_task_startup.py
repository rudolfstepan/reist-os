"""Native immutable startup/IPC proof. All production fault knobs stay in Ring3."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid
import run_qemu_x86_64_task_family as family
from run_qemu_x86_64_task_frames import BEFORE,AFTER,FREE
from run_qemu_x86_64_runtime_clock import once
ROOT=Path(__file__).resolve().parents[1]

def creation_allocations(record):
    if len(record)!=36896 or record[:8]!=b'RNPGv1\0\0':raise ValueError('startup catalog record')
    flags=record[24:32]
    if any(f not in (0,4,5,6) for f in flags):raise ValueError('startup catalog flags')
    return sum(bool(f) for f in flags)+sum(bool(f&2) for f in flags)+5

def injection_guard(s,oom):
    # Runs at CREATE completion, not at the next allocation/boot boundary.
    return f'''python
checked_owner=0
class StartupInjectionEnd(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['family_create64.parent_result']}),internal=True)
    def stop(self):
        global armed,checked_owner
        if armed:
            armed=False
            gdb.write('STARTUP_OBSERVER_FAIL injection missed CREATE\\n');gdb.execute('quit 64')
            return True
        if injected and checked_owner!=injection_owner:
            if reg('rax')!=0xfffffffffffffff4:
                gdb.write('STARTUP_OBSERVER_FAIL injected CREATE did not return ENOMEM\\n');gdb.execute('quit 65')
                return True
            checked_owner=injection_owner
            gdb.write('STARTUP_OOM_BOUNDARY owner=%d acquired={oom} result=-12\\n'%checked_owner)
        return False
StartupInjectionEnd()
end
'''

def observer(s,c,folder,ram,oom=None):
    code=family.proof_observer(s,c,folder,ram,oom)
    old="""            argc,a0,a1,argvnull,envnull=struct.unpack_from('<5Q',stack,off)
            assert (argc,argvnull,envnull)==(2,0,0)
            assert stack[a0-0x408000:].split(b'\\0')[0]==('program%d.prg'%(ident-3)).encode()
            assert stack[a1-0x408000:].split(b'\\0')[0]==str(ident-3).encode()
"""
    new="""            argc=u64(0xffff800000000000+t[3]+off)
            assert argc<=8
            v=struct.unpack_from('<'+'Q'*(argc+6),stack,off)
            assert v[argc+1:]==(0,0,0x52534901,0,0)
            actual=[]
            for a in v[1:argc+1]:
                assert 0x408000<=a<0x409000
                text=stack[a-0x408000:].split(b'\\0')[0]
                assert len(text)<128;actual.append(text)
            expected=[('program%d.prg'%(ident-3)).encode(),str(ident-3).encode()] if slot<2 else captured[gen]
            assert actual==expected
            if slot==2:gdb.write('STARTUP_ARGS gen=%d argc=%d immutable=1\\n'%(gen,argc))
"""
    code=once(code,old,new)
    pre=f'''python
captured={{}}
class StartupCopy(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['family_create64.stack_ready']}),internal=True)
    def stop(self):
        try:
            assert struct.unpack('<I',mem({s['family_request']},4))[0]==2
            raw=mem({s['family_startup']},1040);version,size,argc,flags=struct.unpack_from('<4I',raw)
            assert (version,size,flags)==(1,1040,0) and argc<=8
            gen=u64(reg('r12')+8);assert gen not in captured
            captured[gen]=[raw[16+i*128:144+i*128].split(b'\\0')[0] for i in range(argc)]
            assert len(captured)<=16
        except Exception as error:
            gdb.write('STARTUP_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 62')
        return False
class StartupScrub(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['process_run_resume64']}),internal=True)
    def stop(self):
        try:
            if u64({s['syscall_rax']})==132:
                assert not any(mem({s['family_request']},64)) and not any(mem({s['family_startup']},4096))
                gdb.write('STARTUP_SCRUB bytes=4096 complete=1\\n')
        except Exception as error:
            gdb.write('STARTUP_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 63')
        return False
StartupCopy();StartupScrub()
end
'''
    return code[:-len('continue\n')]+pre+(injection_guard(s,oom) if oom is not None else '')+'continue\n'

def validate(serial,trace,oom=None):
    count=9 if oom is not None else 10
    markers=[m for m in family.REQUIRED_MARKERS if 'SHELL' not in m]+[family.process.SUCCESS]
    if any(m in serial for m in family.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('startup fatal/observer')
    if any(serial.count(m)!=1 for m in markers) or [serial.index(m) for m in markers]!=sorted(serial.index(m) for m in markers):raise ValueError('startup kernel progress')
    ends=list(re.finditer(family.process.DONE,serial));receipts=list(family.process.REAP.finditer(serial));rows=[]
    if len(ends)!=2 or len(receipts)!=count*2 or serial.count('PROCESS_REAP_OK')!=len(receipts):raise ValueError('startup count')
    for run in range(2):
        seen=set()
        for m in receipts[run*count:(run+1)*count]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]));n=gen-run*count
            if not 1<=n<=count or n in seen or slot!=(n-1 if n<=2 else 2):raise ValueError('startup generation/slot')
            seen.add(n)
            expected=(70,4) if n==1 else (71,4) if n==2 else (60,4) if n==3 else (61,4) if n==4 else (134,3) if n==6 else (0,3) if n in (7,9) else (68,4)
            if (status,state)!=expected or ticks>32 or not 0x400000<=rip<0x401000:raise ValueError('startup outcome '+str((slot,gen,status,state,ticks)))
            if not (ends[run-1].end() if run else -1)<m.start()<m.end()<=ends[run].start():raise ValueError('startup receipt order')
            rows.append((slot,gen,state))
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('startup caller order')
    before=list(BEFORE.finditer(trace));after=list(AFTER.finditer(trace));frees=list(FREE.finditer(trace))
    if len(before)!=17+len(rows) or len(after)!=len(before):raise ValueError('startup frame count')
    expected={(m,s,s+1):(4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)}
    expected.update({(4,s,10+s):3 if s==3 else 4 for s in range(4)})
    expected.update({(5,s,20+s):4 for s in range(4)})
    expected.update({(6,0,30):4,(6,1,31):8,(6,1,32):8})
    expected.update({(8,s,g):state for s,g,state in rows})
    seen=set();native=[];consumed=0
    for i,(b,a) in enumerate(zip(before,after),1):
        seq,mode,slot,gen,state,root,active,free,fp,fs=b.groups()
        seq,mode,slot,gen,state,free,fp=map(int,(seq,mode,slot,gen,state,free,fp))
        key=(mode,slot,gen);frames=[int(f,16) for f in fs.split(',')];owned=[f for f in frames if f]
        if seq!=i or key in seen or expected.get(key)!=state or fp!=1:raise ValueError('startup frame identity')
        seen.add(key)
        if mode==8:native.append((slot,gen,state))
        if len(frames)!=13 or not all(frames[8:]) or len(set(owned))!=len(owned) or any(not 0<f<0x400000000 or f%4096 for f in owned):raise ValueError('startup frame ownership')
        root,active=int(root,16),int(active,16)
        if root!=frames[-1] or root==active or not 0<active<0x400000000 or active%4096:raise ValueError('startup active root')
        if tuple(map(int,a.groups()))!=(i,gen,state,1,free+len(owned),1) or not 0<free<free+len(owned)<=4194304:raise ValueError('startup frame balance')
        if not (after[i-2].end() if i>1 else -1)<b.start()<b.end()<a.start():raise ValueError('startup frame order')
        calls=[f for f in frees if b.end()<=f.start()<a.start()];consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(i,f) for f in owned]:raise ValueError('startup backend frees')
    if consumed!=len(frees) or seen!=set(expected) or native!=rows:raise ValueError('startup unowned release')
    fences=list(re.finditer(r'FAMILY_FENCE slot=(\d+) gen=(\d+) ipc=1 heap=1 profile=1',trace))
    if [tuple(map(int,m.groups())) for m in fences]!=[(s,g) for s,g,_ in rows]:raise ValueError('startup fences')
    for i,f in enumerate(fences,17):
        if not after[i-1].end()<f.start()<f.end()<before[i].start():raise ValueError('startup fence after free')
    starts=list(re.finditer(r'FAMILY_START slot=(\d+) gen=(\d+) image=(\d+) high=1 wx=1 argv=1',trace))
    if len(starts)!=len(rows) or {tuple(map(int,m.groups())) for m in starts}!={(s,g,3+s) for s,g,_ in rows}:raise ValueError('startup exact mapping')
    for m in starts:
        i=next(i for i,r in enumerate(rows) if r[1]==int(m[2]))
        if m.end()>fences[i].start():raise ValueError('startup map order')
    args=list(re.finditer(r'STARTUP_ARGS gen=(\d+) argc=(\d+) immutable=1',trace))
    want={(g,0 if (g-1)%count+1==3 else 1 if (g-1)%count+1==4 else 8) for s,g,_ in rows if s==2}
    if len(args)!=len(want) or {tuple(map(int,m.groups())) for m in args}!=want:raise ValueError('startup immutable arguments')
    zeros=list(re.finditer(r'PROCESS_ZERO_OK run=(\d+) zero=(\d+) free=(\d+) initial=(\d+) reaps=(\d+) generation=(\d+) ticks=(\d+)',trace))
    if len(zeros)!=2 or re.findall(r'FAMILY_ZERO run=(\d+) complete=1',trace)!=['1','2']:raise ValueError('startup final zero')
    for n,z in enumerate(zeros,1):
        run,zero,free,initial,reaps,gen,ticks=map(int,z.groups())
        if (run,zero,reaps,gen)!=(n,1,count,n*count) or not 0<free==initial<=4194304 or not 0<ticks<1<<60:raise ValueError('startup final balance')
        if after[16+n*count].end()>z.start() or n==1 and z.end()>before[17+count].start():raise ValueError('startup zero order')
    cancel=[tuple(map(int,m)) for m in re.findall(r'FAMILY_CANCEL slot=(\d+) gen=(\d+) state=(\d+) ipc=(\d+) heap=(\d+) reason=(\d+)',trace)]
    if len(cancel)!=4 or set(cancel)!={(2,r*count+n,6,0,0,2) for r in range(2) for n in (7,9)}:raise ValueError('startup cancellation')
    if re.findall(r'FAMILY_OOM acquired=(\d+)',trace)!=([str(oom)]*2 if oom is not None else []):raise ValueError('startup exact OOM')
    boundaries=list(re.finditer(r'STARTUP_OOM_BOUNDARY owner=(\d+) acquired=(\d+) result=-12',trace))
    wanted=[((r*count+1)<<32,oom) for r in range(2)] if oom is not None else []
    if [tuple(map(int,m.groups())) for m in boundaries]!=wanted:raise ValueError('startup OOM scope')
    injections=list(re.finditer(r'FAMILY_OOM acquired=\d+',trace))
    for i,b in enumerate(boundaries):
        first=next(m for m in starts if int(m[2])==i*count+3)
        if not injections[i].end()<b.start()<b.end()<first.start():raise ValueError('startup injection outside CREATE')
    scrub=re.findall(r'STARTUP_SCRUB bytes=4096 complete=1',trace)
    if len(scrub)<40:raise ValueError('startup request scrub')
    for label,n in (('TASK_FRAMES_BEFORE',len(before)),('TASK_FRAMES_AFTER',len(after)),('TASK_FRAMES_FREE',len(frees)),('FAMILY_FENCE',len(fences)),('FAMILY_START',len(starts)),('STARTUP_ARGS',len(args)),('PROCESS_ZERO_OK',2),('FAMILY_ZERO',2),('FAMILY_CANCEL',4),('FAMILY_OOM',2 if oom is not None else 0),('STARTUP_OOM_BOUNDARY',len(boundaries)),('STARTUP_SCRUB',len(scrub))):
        if trace.count(label)!=n:raise ValueError('startup malformed '+label)
    return len(rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    folder=family.evidence_directory(a.evidence)/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    started=time.monotonic();summary=dict(passed=False,cases=[])
    try:
        image=a.image.resolve();reference=None
        for case in range(2):
            if case:
                out=folder/'oom-build';out.mkdir()
                with (out/'build.log').open('wb') as f:
                    r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeStartup','-StartupCase','1','-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode:raise ValueError('startup OOM fixture build')
                image=out/'x86_64/reist-x86_64-bootstrap.elf'
            names=('cooperative_scheduler','syscall_profile','bootstrap_core','identity_core','queue_core','cpu_budget','task_frames','fp_context','timer_interrupt','startup_stack')
            hashes={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if reference is not None and reference!=hashes:raise ValueError('startup mechanism drift')
            reference=hashes
            catalog=(image.parent/'boot-programs.bin').read_bytes()
            if len(catalog)!=4*36896 or creation_allocations(catalog[2*36896:3*36896])!=10:
                raise ValueError('startup fixture must expose all ten CREATE allocations')
            inner=family.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=family.payload.validate(inner)
            family.payload.verify_outer(inner,family.payload.read_bounded(image))
            if c['layout_version']!=4:raise ValueError('startup C layout')
            s=family.symbols(image)
            variants=[(4096,n) for n in (0,1,2,3,6,9)] if case else [(4096,None),(8192,None)]
            for ram,oom in variants:
                out=folder/f'guest-{ram}-{oom}';out.mkdir()
                serial,trace=family.programs.capture(image,out,observer(s,c,out,ram,oom),ram)
                tasks=validate(serial,trace,oom)
                summary['cases'].append(dict(ram=ram,oom=oom,tasks=tasks));print('STARTUP_GUEST_OK',ram,oom,flush=True)
        summary['passed']=True;summary['mechanisms']=reference
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('STARTUP_FAIL',error);return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('STARTUP_EVIDENCE',folder)
    return 0

if __name__=='__main__':raise SystemExit(main())
