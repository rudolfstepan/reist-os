"""Bounded native family guest proof; diagnostic captures are not acceptance."""
from pathlib import Path
import argparse,struct,uuid,re,json,time,subprocess,hashlib
import run_qemu_x86_64_boot_programs as programs
from run_qemu_x86_64_spawn_oom import symbols
from run_qemu_x86_64_boot import FAILURES,REQUIRED_MARKERS
import run_qemu_x86_64_process_run as process
import run_qemu_x86_64_native_heap as heap
import build_x86_64_c_payload as payload
from run_qemu_x86_64_runtime_clock import once
ROOT=Path(__file__).resolve().parents[1]

def observer(s,folder):
    return f'''set logging file {str(folder/'frame-trace.log').replace(chr(92),'/')}
set logging overwrite on
set logging enabled on
set $family_runs=0
break *{s['process_run_resume64']:#x}
commands
silent
if *(unsigned long long*){s['syscall_rax']:#x}==132
printf "FAMILY_RESUME result=%ld slot=%d\\n",$rax,*(unsigned int*){s['scheduler_current_slot']:#x}
x/16gx {s['family_profiles']:#x}
x/8gx {s['syscall_rax']:#x}
end
continue
end
break *{s['x86_64_c_process_run64.restore']:#x}
commands
silent
set $family_runs=$family_runs+1
if $family_runs==2
detach
quit
end
continue
end
break *{s['family_result64']:#x}
commands
silent
printf "FAMILY_RESULT result=%ld\\n",$rax
x/8gx {s['family_request']:#x}
continue
end
break *{s['scheduler_fail']:#x}
commands
silent
printf "FAMILY_FAILURE_DIAGNOSTIC\\n"
info registers rax rbx rcx rdx rsi rdi r8 r9 r10 r11 r12 r13 r14 r15 rip rsp cr3
x/32gx {s['family_records']:#x}
x/16gx {s['family_profiles']:#x}
x/4wx {s['process_run_generations']:#x}
x/4wx {s['family_total']:#x}
x/8gx $rsp
detach
quit
end
break *{s['process_run_validate64.bad']:#x}
commands
silent
printf "FAMILY_OWNERSHIP_DIAGNOSTIC\\n"
info registers rax rbx rcx rdx rsi rdi r8 r9 r10 r11 r12 r13 r14 r15 rip rsp
x/8gx $rsp
continue
end
continue
'''

def proof_observer(s,c,folder,ram,oom=None):
    code=heap.batch_zero_checks(process.observer_commands(s,folder/'frame-trace.log'))
    code=once(code,'$seq>=25','$seq>=53')
    def at(n,t='unsigned int'):return f'*({t}*){s[n]:#x}'
    code=once(code,f'if {at("timer_ticks")}!={at("timer_eoi_count")} || {at("timer_ticks")}>=256 ||',
        f'if {at("timer_runtime_ticks","unsigned long long")}!={at("timer_runtime_eois","unsigned long long")} || {at("timer_runtime_ticks","unsigned long long")}>=1152921504606846976 ||')
    code=once(code,'generation=%u ticks=%u\\n','generation=%u ticks=%llu\\n')
    code=once(code,at('process_run_generation')+','+at('timer_ticks'),at('process_run_generation')+','+at('timer_runtime_ticks','unsigned long long'))
    cs=c['symbols'];client=cs['clients']['value'];pending=cs['pending']['value'];caps=cs['ipc_capability_records']['value']
    state=cs['native_heap_state']['value']
    pre=f'''python
import gdb,struct
def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a&0xffffffffffffffff,n))
def u64(a):return struct.unpack('<Q',mem(a,8))[0]
started=set()
end
'''
    code=pre+code
    fence=f'''python
slot=int(gdb.parse_and_eval('$slot'));gen=u64(int(gdb.parse_and_eval('$task'))+8)
assert not any(mem({s['family_profiles']}+slot*32,32))
assert not any(mem({client}+slot*108,108)) and not any(mem({pending}+slot*2144,2144))
cap=mem({caps},2048)
for i in range(0,2048,32):
    assert not cap[i] or struct.unpack_from('<2I',cap,i+16)!=(gen,gen)
task={state}+232+slot*99368
ctl=struct.unpack('<16Q',mem(task,128))
assert ctl[:8]==(0,gen,0,0,0,0x20000000,0,0) and not any(ctl[8:])
assert not any(mem(task+552,5120)) and not any(mem(task+32808,12288))
gdb.write('FAMILY_FENCE slot=%d gen=%d ipc=1 heap=1 profile=1\\n'%(slot,gen))
end
'''
    code=once(code,'printf "PROCESS_FENCE_OK',fence+'printf "PROCESS_FENCE_OK')
    finish=f'''python
assert not any(mem({s['family_begin']},{s['family_end']-s['family_begin']}))
assert not any(mem({s['process_heap_pending_mask']},8))
for a in [{s['elf_context_window']}]+[{s['elf_context_store']}+i*88 for i in range(7)]:
    r=mem(a,88);assert not any(r[:72]) and not any(r[76:])
assert u64({s['timer_runtime_ticks']})==u64({s['scheduler_last_tick']})==u64({s['timer_runtime_eois']})
gdb.write('FAMILY_ZERO run=%d complete=1\\n'%int(gdb.parse_and_eval('$runs')))
end
'''
    code=once(code,'if $runs==2\ndetach',finish+'if $runs==2\ndetach')
    extra=f'''python
class Start(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['scheduler_enter_task64.state_published']}),internal=True)
    def stop(self):
        try:
            if mem({s['scheduler_mode']},1)!=b'\\x08':return False
            slot=struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]
            t=struct.unpack('<32Q',mem({s['scheduler_tasks']}+slot*256,256));gen=t[1]
            if gen in started:return False
            assert t[0]==2 and gen and slot<4 and not reg('eflags')&512
            plan=struct.unpack('<4Q',mem({s['process_run_plan']}+16+slot*32,32));ident=plan[3]
            r=mem({s['boot_program_catalog']}+(ident-3)*36896,36896)
            assert t[12]==struct.unpack_from('<Q',r,16)[0] and t[13]%16==0
            assert struct.unpack('<4Q',mem({s['family_profiles']}+slot*32,32))==(gen,plan[1],0,16 if slot<2 else 0)
            private=[]
            for page in range(9):
                va=0x400000+page*4096;node=t[2]
                for shift in (39,30,21):
                    entry=u64(0xffff800000000000+node+((va>>shift)&511)*8)
                    assert entry&7==7 and not entry&128
                    node=entry&0x3fffff000
                leaf=u64(0xffff800000000000+node+((va>>12)&511)*8)
                pf=r[24+page] if page<8 else 6
                if not pf:assert leaf==0;continue
                frame=leaf&0x3fffff000
                flags=5|(2 if pf&2 else 0)|(0 if pf&1 else 1<<63)
                assert leaf&~0x60==frame|flags and frame>=0x100000000
                if pf&2:
                    assert frame==(t[4+page] if page<8 else t[3]);private.append(frame)
                if page<8:assert mem(0xffff800000000000+frame,4096)==r[32+page*4096:32+(page+1)*4096]
            assert len(private)==len(set(private))
            stack=mem(0xffff800000000000+t[3],4096);off=t[13]-0x408000
            argc,a0,a1,argvnull,envnull=struct.unpack_from('<5Q',stack,off)
            assert (argc,argvnull,envnull)==(2,0,0)
            assert stack[a0-0x408000:].split(b'\\0')[0]==('program%d.prg'%(ident-3)).encode()
            assert stack[a1-0x408000:].split(b'\\0')[0]==str(ident-3).encode()
            started.add(gen);assert len(started)<=36
            gdb.write('FAMILY_START slot=%d gen=%d image=%d high=1 wx=1 argv=1\\n'%(slot,gen,ident))
        except Exception as e:
            gdb.write('FAMILY_OBSERVER_FAIL '+repr(e)+'\\n');gdb.execute('quit 61')
        return False
Start()
class Cancel(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['family_cancel_one64']}),internal=True)
    def stop(self):
        slot=reg('rdi');t=struct.unpack('<3Q',mem({s['scheduler_tasks']}+slot*256,24))
        ipc=struct.unpack('<I',mem({pending}+slot*2144+2140,4))[0]
        hp=struct.unpack('<I',mem({s['process_heap_pending_mask']},4))[0]>>slot&1
        reason=struct.unpack('<I',mem({s['family_reasons']}+slot*4,4))[0]
        gdb.write('FAMILY_CANCEL slot=%d gen=%d state=%d ipc=%d heap=%d reason=%d\\n'%(slot,t[1],t[0],ipc,hp,reason))
        return False
Cancel()
end
'''
    if oom is not None:
        extra+=f'''python
injection_count=0;armed=False;injected=False;injection_owner=0
class Arm(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['family_create64.found']}),internal=True)
    def stop(self):
        global armed,injection_owner,injected,injection_count
        owner=u64({s['family_records']})
        if owner!=injection_owner:injection_owner=owner;injected=False;injection_count=0
        if not injected:armed=True
        return False
class Allocation(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['physical_frame_alloc64']}),internal=True)
    def stop(self):
        global injection_count,armed,injected
        if not armed or injected:return False
        if injection_count=={oom}:
            ret=u64(reg('rsp'));gdb.execute('set $rax=0');gdb.execute('set $rsp=$rsp+8');gdb.execute('set $rip='+hex(ret))
            injected=True;armed=False;gdb.write('FAMILY_OOM acquired={oom}\\n')
        else:injection_count+=1
        return False
Arm();Allocation()
end
'''
    return code[:-len('continue\n')]+extra+'continue\n'

def validate(serial,trace,case,oom=None):
    common=[m for m in REQUIRED_MARKERS if 'SHELL' not in m]+[process.SUCCESS]
    if any(x in serial for x in FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('family kernel/observer failure')
    if any(serial.count(m)!=1 for m in common) or [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):raise ValueError('family kernel progress')
    ends=list(re.finditer(process.DONE,serial));receipts=list(process.REAP.finditer(serial))
    count=4 if case==1 else 9 if case==4 else 10
    if len(ends)!=2 or len(receipts)!=count*2 or serial.count('PROCESS_REAP_OK')!=count*2:raise ValueError('family receipt count')
    rows=[]
    for run in range(2):
        seen=set()
        for m in receipts[run*count:(run+1)*count]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]));n=gen-run*count
            expected_slot=n-1 if n<=4 else 2
            if not 1<=n<=count or n in seen or slot!=expected_slot:raise ValueError('family generation/slot')
            seen.add(n)
            expected=(134,3) if case==1 and slot==0 else (0,3) if slot==3 or case==1 and slot==2 else ((134 if case==2 else 256),3) if slot==2 and case in (2,3) else (40+slot,4)
            if (status,state)!=expected or ticks>32 or slot==2 and case==3 and ticks!=32:raise ValueError('family outcome '+str((case,slot,gen,status,state,ticks)))
            if not 0x400000<=rip<0x401000 or not (ends[run-1].end() if run else -1)<m.start()<m.end()<=ends[run].start():raise ValueError('family instruction/order')
            rows.append(dict(slot=slot,generation=gen,state=state))
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('family final caller order')
    from run_qemu_x86_64_task_frames import BEFORE,AFTER,FREE
    starts=list(BEFORE.finditer(trace));afters=list(AFTER.finditer(trace));frees=list(FREE.finditer(trace))
    if len(starts)!=17+len(rows) or len(afters)!=len(starts):raise ValueError('family frame count')
    baseline={(m,s,s+1):(4 if s==0 else 3 if m==1 else 5) for m in (1,2,3) for s in (0,1)}
    baseline.update({(4,s,10+s):3 if s==3 else 4 for s in range(4)})
    baseline.update({(5,s,20+s):4 for s in range(4)})
    baseline.update({(6,0,30):4,(6,1,31):8,(6,1,32):8})
    native=[];consumed=0;seen=set()
    for i,(b,a) in enumerate(zip(starts,afters),1):
        seq,mode,slot,gen,state,root,active,free,fp,frames=b.groups()
        seq,mode,slot,gen,state,free,fp=map(int,(seq,mode,slot,gen,state,free,fp))
        fs=[int(v,16) for v in frames.split(',')];owned=[f for f in fs if f]
        if (mode,slot,gen) in seen:raise ValueError('duplicate frame owner')
        seen.add((mode,slot,gen))
        if i<=17 and baseline.get((mode,slot,gen))!=state:raise ValueError('legacy frame identity')
        if i>17 and mode!=8:raise ValueError('family frame mode')
        if not (afters[i-2].end() if i>1 else -1)<b.start()<b.end()<a.start():raise ValueError('family release order')
        if seq!=i or fp!=1 or len(fs)!=13 or not all(fs[8:]) or len(owned)!=len(set(owned)):raise ValueError('family frame ownership')
        active=int(active,16)
        if any(f%4096 or not 0<f<0x400000000 for f in owned) or int(root,16)!=fs[-1] or int(root,16)==active or not 0<active<0x400000000 or active%4096:raise ValueError('family physical range/root')
        if tuple(map(int,a.groups()))!=(i,gen,state,1,free+len(owned),1):raise ValueError('family frame release/scrub')
        if not 0<free<free+len(owned)<=4194304:raise ValueError('family allocator bounds')
        calls=[f for f in frees if b.end()<=f.start()<a.start()];consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(i,f) for f in owned]:raise ValueError('family backend frees')
        if mode==8:native.append((slot,gen,state))
    if consumed!=len(frees) or native!=[(r['slot'],r['generation'],r['state']) for r in rows]:raise ValueError('family receipt/frame ordering')
    fm=list(re.finditer(r'FAMILY_FENCE slot=(\d+) gen=(\d+) ipc=1 heap=1 profile=1',trace))
    fence=[tuple(map(int,x.groups())) for x in fm]
    if fence!=[(r['slot'],r['generation']) for r in rows]:raise ValueError('family exact fencing')
    for i,f in enumerate(fm,17):
        if not afters[i-1].end()<f.start()<f.end()<starts[i].start():raise ValueError('family fence after free')
    sm=list(re.finditer(r'FAMILY_START slot=(\d+) gen=(\d+) image=(\d+) high=1 wx=1 argv=1',trace))
    expected={(r['slot'],r['generation'],3+r['slot']) for r in rows}
    if len(sm)!=len(rows) or {tuple(map(int,x.groups())) for x in sm}!=expected:raise ValueError('family mapped starts')
    for m in sm:
        index=next(i for i,r in enumerate(rows) if r['generation']==int(m[2]))
        if m.end()>fm[index].start():raise ValueError('family start after retirement')
    zeros=list(re.finditer(r'PROCESS_ZERO_OK run=(\d+) zero=(\d+) free=(\d+) initial=(\d+) reaps=(\d+) generation=(\d+) ticks=(\d+)',trace))
    if len(zeros)!=2 or re.findall(r'FAMILY_ZERO run=(\d+) complete=1',trace)!=['1','2']:raise ValueError('family final zero count')
    for n,z in enumerate(zeros,1):
        run,zero,free,initial,reaps,gen,ticks=map(int,z.groups())
        if (run,zero,reaps,gen)!=(n,1,count,n*count) or not 0<free==initial<=4194304 or not 0<ticks<1<<60:raise ValueError('family final balance')
        if afters[16+n*count].end()>z.start() or n==1 and z.end()>starts[17+count].start():raise ValueError('family zero ordering')
    cancels=[tuple(map(int,x)) for x in re.findall(r'FAMILY_CANCEL slot=(\d+) gen=(\d+) state=(\d+) ipc=(\d+) heap=(\d+) reason=(\d+)',trace)]
    if len(cancels)!=(4 if case==1 else 2) or any(x[-1]!=(3 if case==1 else 2) for x in cancels):raise ValueError('family cancellation ownership')
    targets={(s,r*count+s+1) for r in range(2) for s in ((2,3) if case==1 else (3,))}
    if {(x[0],x[1]) for x in cancels}!=targets or any(x[2] not in (1,6) or x[3] not in (0,1) or x[4] not in (0,1) for x in cancels):raise ValueError('family cancellation target/state')
    if case==5 and not all(x[4]==1 for x in cancels):raise ValueError('missing pending heap cancellation')
    if case in (0,1,2,3,4) and not all(x[3]==1 for x in cancels if x[0]==3):raise ValueError('missing blocked IPC cancellation')
    if re.findall(r'FAMILY_OOM acquired=(\d+)',trace)!=([str(oom)]*2 if oom is not None else []):raise ValueError('family OOM injection')
    for label,amount in (('TASK_FRAMES_BEFORE',len(starts)),('TASK_FRAMES_AFTER',len(afters)),('TASK_FRAMES_FREE',len(frees)),('FAMILY_START',len(sm)),('FAMILY_FENCE',len(fm)),('PROCESS_ZERO_OK',2),('FAMILY_ZERO',2),('FAMILY_CANCEL',len(cancels)),('FAMILY_OOM',2 if oom is not None else 0)):
        if trace.count(label)!=amount:raise ValueError('malformed '+label)
    return len(rows)

def evidence_directory(path):
    directory=Path(path).resolve()
    if not directory.is_relative_to(ROOT/'build/codex-agent'):
        raise ValueError('family evidence outside build/codex-agent')
    return directory

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True);p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args();d=evidence_directory(a.evidence)/('attempt-'+uuid.uuid4().hex);d.mkdir(parents=True)
    if a.diagnostic:
        serial,trace=programs.capture(a.image,d,observer(symbols(a.image),d),4096)
        print('FAMILY_CAPTURE',d);print(serial[-1800:]);print(trace[-4000:]);return
    started=time.monotonic();summary=dict(passed=False,cases=[])
    try:
        images={0:a.image.resolve()};expected=None
        for case in range(6):
            if case:
                out=d/f'build-{case}';out.mkdir()
                with (out/'build.log').open('wb') as f:
                    r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeLifecycle','-FamilyCase',str(case),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode:raise ValueError('family case build '+str(out))
                images[case]=out/'x86_64/reist-x86_64-bootstrap.elf'
            image=images[case];s=symbols(image)
            names=('cooperative_scheduler','syscall_profile','bootstrap_core','identity_core','queue_core','cpu_budget','task_frames','fp_context','timer_interrupt')
            hashes={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if expected is not None and expected!=hashes:raise ValueError('family mechanism drift across fixtures')
            expected=hashes
            inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=payload.validate(inner);payload.verify_outer(inner,payload.read_bounded(image))
            if c['layout_version']!=4:raise ValueError('family private layout')
            variants=[(4096,n) for n in (0,1,2,3,6,9)] if case==4 else [(4096,None)]+([(8192,None)] if case==0 else [])
            for ram,oom in variants:
                out=d/f'guest-{case}-{ram}-{oom}';out.mkdir()
                serial,trace=programs.capture(image,out,proof_observer(s,c,out,ram,oom),ram)
                count=validate(serial,trace,case,oom)
                summary['cases'].append(dict(case=case,ram=ram,oom=oom,tasks=count));print('FAMILY_GUEST_OK',case,ram,oom,flush=True)
        summary['passed']=True;summary['mechanisms']=expected
    finally:
        summary['elapsed']=round(time.monotonic()-started,3);(d/'summary.json').write_text(json.dumps(summary,indent=2))
        print('FAMILY_EVIDENCE',d)

if __name__=='__main__':main()
