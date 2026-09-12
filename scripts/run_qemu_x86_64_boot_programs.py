"""Multi-image native boot proof. Old guest runners and limits stay unchanged."""
from pathlib import Path
import argparse, hashlib, json, queue, re, shutil, struct, subprocess, threading, time, uuid
import build_x86_64_c_payload as payload
import run_qemu_x86_64_native_memory as memory
import run_qemu_x86_64_native_heap as heap
import run_qemu_x86_64_process_run as process
from run_qemu_x86_64_runtime_clock import once
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, FAILURES, REQUIRED_MARKERS
from run_qemu_x86_64_spawn_oom import symbols
from measure_cpp_baseline import suppress_windows_test_dialogs
ROOT=Path(__file__).resolve().parents[1]

def validate_preemption(trace):
    events=re.findall(r'PREEMPT_IF_ADMISSION slot=(\d+) if=(\d+) armed=(\d+)',trace)
    if events!=[('0','0','0'),('1','1','1'),('0','0','0')] or trace.count('PREEMPT_IF_ADMISSION')!=3:
        raise ValueError('exact preemption IF/timer admission')
    pending=re.findall(r'PREEMPT_PENDING_IRQ pending=([01]) unmasked=1',trace)
    if len(pending)!=1 or trace.count('PREEMPT_PENDING_IRQ')!=1:raise ValueError('pending IRQ observation')
    return int(pending[0])

def validate(serial,trace,case,ram):
    validate_preemption(trace)
    common=[m for m in REQUIRED_MARKERS if 'SHELL' not in m]+[process.SUCCESS]
    if any(m in serial for m in FAILURES) or any(serial.count(m)!=1 for m in common):raise ValueError('program kernel progress')
    positions=[serial.index(m) for m in common]
    if positions!=sorted(positions):raise ValueError('program progress ordering')
    ends=list(re.finditer(process.DONE,serial));receipts=list(process.REAP.finditer(serial));rows=[]
    if len(ends)!=2 or len(receipts)!=8 or serial.count('PROCESS_REAP_OK')!=8:raise ValueError('program receipt count')
    for run in range(2):
        seen=set()
        for m in receipts[run*4:run*4+4]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]))
            ident=slot if run==0 else 3-slot;bad=case and ident==2
            if slot not in range(4) or slot in seen or gen!=run*4+slot+1:raise ValueError('program generation')
            if (status,state)!=((134 if case==1 else 256) if bad else 40+ident,3 if bad else 4):raise ValueError('program outcome '+str((slot,gen,status,state)))
            if ticks>32 or bad and case==2 and ticks!=32 or not 0x400000<=rip<0x401000:raise ValueError('program CPU/RIP')
            if not (ends[run-1].end() if run else -1)<m.start()<m.end()<=ends[run].start():raise ValueError('program retire order')
            seen.add(slot);rows.append(dict(slot=slot,generation=gen,status=status,state=state,ticks=ticks,rip=rip))
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('program caller continuation')
    memory.validate_trace(trace,rows) # exact25 retirements/13 frames/fences/14 scrub ranges
    if 'OBSERVER_FAIL' in trace:raise ValueError('program observer failure')
    starts=re.findall(r'BOOT_PROGRAM_START run=(\d+) slot=(\d+) gen=(\d+) image=(\d+) layout=(\d+) argc=2 private=1',trace)
    expected=[(r+1,s,r*4+s+1,(s if r==0 else 3-s)+3,(s if r==0 else 3-s)+2) for r in range(2) for s in range(4)]
    if [tuple(map(int,x)) for x in starts]!=expected or trace.count('BOOT_PROGRAM_START')!=8:raise ValueError('program image/start witness')
    zeros=re.findall(r'BOOT_PROGRAM_ZERO run=(\d+) images=1 heap=1 tick=(\d+)',trace)
    if len(zeros)!=2 or trace.count('BOOT_PROGRAM_ZERO')!=2:raise ValueError('program complete zero witness')
    previous=0
    shared_zeros=list(re.finditer(r'PROCESS_ZERO_OK .*? ticks=(\d+)',trace))
    for run,(r,tick) in enumerate(zeros,1):
        if int(r)!=run or not previous+10<=int(tick)<256 or int(shared_zeros[run-1][1])!=int(tick):raise ValueError('program persistent clock')
        previous=int(tick)
    fences=re.findall(r'NATIVE_IPC_FENCE slot=(\d+) gen=(\d+)',trace)
    if [tuple(map(int,x)) for x in fences]!=[(r['slot'],r['generation']) for r in rows]:raise ValueError('program IPC fencing')
    maps=re.findall(r'NATIVE_MEMORY_MAP_OK ram=(\d+) managed=(\d+) huge=(\d+) mixed=(\d+) high=(\d+)',trace)
    if len(maps)!=1:raise ValueError('program physical map')
    actual,managed,huge,mixed,high=map(int,maps[0])
    if actual!=ram or not (ram-32)*256<managed<=ram*256 or huge<1 or not 0<mixed<=512 or high!=1:raise ValueError('program RAM bounds')
    for m in memory.BEFORE.finditer(trace):
        if any(0<int(f,16)<0x100000000 for f in m[10].split(',')):raise ValueError('program full-width frames')
    return rows

def observer(s,c,log,ram):
    code=heap.batch_zero_checks(memory.observer(s,c,log,ram))
    code=once(code,f'count=({payload.MEMORY_ARENA_BYTES}+4095)//4096',f'count=({payload.HEAP_ARENA_BYTES}+4095)//4096')
    def at(n,t='unsigned int'):return f'*({t}*){s[n]:#x}'
    old=f'if {at("timer_ticks")}!={at("timer_eoi_count")} || {at("timer_ticks")}>=256 || {at("scheduler_final_result","unsigned char")}!=1'
    new=f'if {at("timer_runtime_ticks","unsigned long long")}!={at("timer_runtime_eois","unsigned long long")} || {at("timer_runtime_ticks","unsigned long long")}>=256 || {at("scheduler_final_result","unsigned char")}!=1'
    code=once(code,old,new)
    code=once(code,'generation=%u ticks=%u\\n",$runs','generation=%u ticks=%llu\\n",$runs')
    code=once(code,at('process_run_generation')+','+at('timer_ticks'),at('process_run_generation')+','+at('timer_runtime_ticks','unsigned long long'))
    state=c['symbols']['native_heap_state']['value']
    # Run-final assertion is inside the SAME breakpoint as the14 scrub ranges,
    # before its detach; a second breakpoint at that address could be skipped.
    end=f'''python
try:
    run=int(gdb.parse_and_eval('$runs'))
    assert run in (1,2) and not reg('eflags')&512
    tick=u64({s['timer_runtime_ticks']})
    assert tick==u64({s['timer_runtime_eois']})==u64({s['scheduler_last_tick']}) and 0<tick<256
    assert mem({s['process_heap_pending_mask']},8)==bytes(8)
    for slot in range(4):
        task={state}+232+slot*99368
        ctl=struct.unpack('<16Q',mem(task,128))
        assert ctl[:8]==(0,(run-1)*4+slot+1,0,0,0,0x20000000,0,0) and not any(ctl[8:])
        assert not any(mem(task+552,5120)) and not any(mem(task+32808,12288))
    for address in [{s['elf_context_window']}]+[{s['elf_context_store']}+i*88 for i in range(7)]:
        record=mem(address,88)
        assert not any(record[:72]) and not any(record[76:])
    gdb.write('BOOT_PROGRAM_ZERO run=%d images=1 heap=1 tick=%d\\n'%(run,tick))
except Exception as error:
    gdb.write('BOOT_PROGRAM_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 41')
end
'''
    code=once(code,'if $runs==2\ndetach',end+'if $runs==2\ndetach')
    extra=f'''python
import re
program_seen=set()
class PreemptAdmission(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex({s['scheduler_enter_task64']}),internal=True);self.calls=0
    def stop(self):
        if mem({s['scheduler_mode']},1)!=bytes([2]):return False
        try:
            slot=reg('edi');assert slot in (0,1) and not reg('eflags')&512
            flags=u64({s['scheduler_tasks']}+slot*256+112)
            armed=mem({s['timer_active']},1)[0]
            assert flags&512==(512 if slot else 0) and armed==(1 if slot else 0)
            self.calls+=1;assert self.calls<=3
            if self.calls==1:
                pic=gdb.execute('monitor info pic',to_string=True)
                match=re.search(r'pic0: irr=([0-9a-f]+) imr=([0-9a-f]+)',pic)
                assert match is not None and not int(match[2],16)&1
                gdb.write('PREEMPT_PENDING_IRQ pending=%d unmasked=1\\n'%(int(match[1],16)&1))
            gdb.write('PREEMPT_IF_ADMISSION slot=%d if=%d armed=%d\\n'%(slot,bool(flags&512),armed))
        except Exception as error:
            gdb.write('BOOT_PROGRAM_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 45')
        return False
PreemptAdmission()
class ProgramStart(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['process_run_dispatch64']}),internal=True)
    def stop(self):
        run=struct.unpack('<I',mem({s['process_run_generation']},4))[0]//4
        if run in program_seen:return False
        try:
            assert run in (1,2) and not reg('eflags')&512
            program_seen.add(run);owned=set()
            for slot in range(4):
                ident=slot if run==1 else 3-slot
                t={s['scheduler_tasks']}+slot*256
                task=struct.unpack('<32Q',mem(t,256))
                assert task[0]==1 and task[1]==(run-1)*4+slot+1
                record=mem({s['boot_program_catalog']}+ident*36896,36896)
                assert task[12]==struct.unpack_from('<Q',record,16)[0]
                root=task[2];direct=0xffff800000000000;mask=0x3fffff000
                pdpt=u64(direct+root)&mask;pd=u64(direct+pdpt)&mask;pt=u64(direct+pd+2*8)&mask
                for page,pf in enumerate(record[24:32]):
                    pte=u64(direct+pt+page*8)
                    if not pf:assert pte==0;continue
                    frame=pte&mask;permission=5|(2 if pf==6 else 0)|(0 if pf==5 else 1<<63)
                    assert frame>=0x100000000 and pte&~0x60==frame|permission
                    assert mem(direct+frame,4096)==record[32+page*4096:32+(page+1)*4096]
                    if pf==6:
                        assert frame==task[4+page] and frame not in owned;owned.add(frame)
                    else:assert task[4+page]==0
                pte=u64(direct+pt+8*8)
                assert pte&~0x60==task[3]|0x8000000000000007 and task[3] not in owned
                owned.add(task[3]);rsp=task[13]
                assert 0x408000<=rsp<0x409000 and not rsp&15
                stack=mem(direct+task[3],4096);v=struct.unpack_from('<9Q',stack,rsp-0x408000)
                assert v[0]==2 and v[3:]==(0,0,0x52534901,0,0,0)
                for pointer,want in zip(v[1:3],('program%d.prg'%ident,str(ident))):
                    off=pointer-0x408000;assert 0<=off<4096
                    assert stack[off:off+len(want)+1]==want.encode()+bytes(1)
                gdb.write('BOOT_PROGRAM_START run=%d slot=%d gen=%d image=%d layout=%d argc=2 private=1\\n'%(run,slot,task[1],ident+3,ident+2))
        except Exception as error:
            import traceback
            gdb.write(traceback.format_exc());gdb.write('BOOT_PROGRAM_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 42')
        return False
ProgramStart()
end
continue
'''
    if not code.endswith('continue\n'):raise ValueError('program observer tail')
    return code[:-len('continue\n')]+extra

def rejection_observer(s,c,log,kind):
    if kind not in ('header','rights','arguments',0,1,2):raise ValueError('program injection kind')
    state=c['symbols']['native_memory_state']['value']
    # Keep the same baseline frame/RAM observers as the successful profile.
    # Negative admission does not excuse skipping the preceding boot proofs.
    code=observer(s,c,log,4096)
    extra=f'''python
import gdb,struct
def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a,n))
def u64(a):return struct.unpack('<Q',mem(a,8))[0]
injection={kind!r}
injected=False
class LoadResult(gdb.Breakpoint):
    def __init__(self,address,before):
        super().__init__('*'+hex(address),internal=True);self.before=before
    def stop(self):
        try:
            assert reg('rax')==0 and injected and not reg('eflags')&512
            after=struct.unpack('<I',mem({state}+4,4))[0]
            record=mem({s['elf_context_window']},88)
            assert after==self.before and not any(record[:72]) and not any(record[76:])
            assert not any(mem({s['scheduler_tasks']},1024))
            assert u64({s['elf_last_load_error']})==((-12 if isinstance(injection,int) else -4096)&0xffffffffffffffff)
            gdb.write('BOOT_PROGRAM_REJECT kind=%s before=%d after=%d zero=1\\n'%(injection,self.before,after))
            gdb.execute('detach');gdb.execute('quit')
        except Exception as error:
            gdb.write('BOOT_PROGRAM_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 43')
        return False
class AllocFail(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex({s['physical_frame_alloc64']}),internal=True);self.count=0;self.enabled=False
    def stop(self):
        global injected
        if self.count==injection:
            assert not injected
            injected=True;self.enabled=False
            address=u64(reg('rsp'))
            gdb.execute('set $rax=0');gdb.execute('set $rsp=$rsp+8');gdb.execute('set $rip='+hex(address))
            gdb.write('BOOT_PROGRAM_ALLOC_INJECT acquired=%d\\n'%self.count)
        self.count+=1
        return False
allocator=AllocFail()
class LoadStart(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['boot_program_load64']}),internal=True)
    def stop(self):
        global injected
        try:
            assert not injected and not reg('eflags')&512
            before=struct.unpack('<I',mem({state}+4,4))[0]
            LoadResult(u64(reg('rsp')),before);self.enabled=False
            if isinstance(injection,int):allocator.enabled=True
            else:
                offset,data={{'header':(8,struct.pack('<I',2)),'rights':(24,bytes([7])),
                             'arguments':(32808,struct.pack('<Q',0xffffffffffffffff))}}[injection]
                gdb.selected_inferior().write_memory({s['boot_program_catalog']}+offset,data);injected=True
        except Exception as error:
            gdb.write('BOOT_PROGRAM_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 44')
        return False
LoadStart()
end
break *{s['x86_64_scheduler_timer_validate64.invalid']:#x}
commands
silent
printf "BOOT_PROGRAM_BASELINE_DIAG\\n"
info registers rax rbx rcx rdx rsi rdi r8 r9 r10 r11 r12 r13 r14 r15 rip rsp cr3
x/24gx $rdi
x/32gx {s['scheduler_tasks']+256:#x}
detach
quit
end
break *{s['x86_64_timer_interrupt64.invalid']:#x}
commands
silent
printf "BOOT_PROGRAM_TIMER_DIAG\\n"
x/2gx {s['timer_original_cr3']:#x}
x/20bx {s['timer_ticks']:#x}
info registers rax rbx rcx rdx rsi rdi rip rsp cr3
x/24gx $rdi
detach
quit
end
continue
'''
    if not code.endswith('continue\n'):raise ValueError('rejection observer tail')
    return code[:-len('continue\n')]+extra

def validate_rejection(serial,trace,kind):
    validate_preemption(trace)
    if serial.count('REIST_X86_64_C_KERNEL_CONTROL_ERROR')!=1 or process.SUCCESS in serial or 'PROCESS_REAP_OK' in serial:
        raise ValueError('program invalid boot admission progressed')
    marks=re.findall(r'BOOT_PROGRAM_REJECT kind=(\w+) before=(\d+) after=(\d+) zero=1',trace)
    if len(marks)!=1 or trace.count('BOOT_PROGRAM_REJECT')!=1 or 'OBSERVER_FAIL' in trace:raise ValueError('program rejection witness')
    actual,before,after=marks[0]
    if actual!=str(kind) or not 0<int(before)==int(after)<=4194304:raise ValueError('program rejection balance')
    injections=re.findall(r'BOOT_PROGRAM_ALLOC_INJECT acquired=(\d+)',trace)
    if injections!=([str(kind)] if isinstance(kind,int) else []):raise ValueError('program exact allocation failure')

def capture(image,folder,code,ram):
    script=folder/'observe.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12491\n'+code,encoding='ascii')
    command=[str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m',str(ram)+'M','-smp','1',
             '-display','none','-monitor','none','-nic','none','-serial','stdio','-no-reboot','-no-shutdown',
             '-kernel',str(image),'-S','-gdb','tcp:127.0.0.1:12491']
    (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
    output=queue.Queue(maxsize=128);overflow=threading.Event();data=bytearray();debugger=None;thread=None
    with (folder/'stderr.log').open('wb') as errors,(folder/'observer.log').open('wb') as log:
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,bufsize=0,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
                                      stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            def reader():
                while chunk:=vm.stdout.read(256):
                    try:output.put_nowait(chunk)
                    except queue.Full:overflow.set();return
            thread=threading.Thread(target=reader,daemon=True);thread.start();deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                try:data.extend(output.get(timeout=.01))
                except queue.Empty:pass
                if overflow.is_set() or len(data)>262144:raise ValueError('program serial capacity')
                serial=data.decode('ascii',errors='replace')
                if process.SUCCESS in serial or any(m in serial for m in FAILURES) or vm.poll() is not None or debugger.poll() not in (None,0):break
        finally:
            vm.stdin.close();terminate_bounded(vm)
            if debugger is not None:
                try:debugger.wait(timeout=2)
                except subprocess.TimeoutExpired:terminate_bounded(debugger)
            if thread is not None:thread.join(timeout=1)
            while not output.empty():data.extend(output.get_nowait())
            vm.stdout.close();(folder/'guest.log').write_bytes(data)
    if overflow.is_set() or len(data)>262144 or debugger.returncode:raise ValueError('program capture/detach failure')
    for name in ('observer.log','frame-trace.log'):
        if (folder/name).stat().st_size>65536:raise ValueError('program observer capacity')
    return data.decode('ascii',errors='replace'),(folder/'frame-trace.log').read_text(encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    image=a.image.resolve();base=a.evidence.resolve()
    if not image.is_relative_to(ROOT/'build') or not base.is_relative_to(ROOT/'build/codex-agent'):p.error('program evidence scope')
    suppress_windows_test_dialogs();folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result={'passed':False,'cases':[]};started=time.monotonic()
    try:
        reference=None;pending_observations=0
        for case,ram in ((0,4096),(0,8192),(1,4096),(2,8192)):
            target=folder/f'{case}-{ram}';target.mkdir();selected=image
            if case:
                command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativePrograms',
                         '-ProgramCase',str(case),'-OutputDirectory',target.relative_to(ROOT).as_posix()]
                with (target/'build.log').open('wb') as log:
                    built=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if built.returncode:raise ValueError('program variant build')
                selected=target/'x86_64/reist-x86_64-bootstrap.elf'
            inner=payload.read_bounded(selected.parent/'reist-x86_64-c-core.elf');c=payload.validate(inner)
            payload.verify_outer(inner,payload.read_bounded(selected))
            if c['layout_version']!=4:raise ValueError('program private layout4')
            names=('cooperative_scheduler','timer_interrupt','bootstrap_core','identity_core','queue_core','context_core',
                   'cpu_budget','syscall_profile','task_frames','fp_context','user_fault','exceptions','user_access',
                   'native_ipc_pool','native_ipc','native_ipc_integrity','native_ipc_memory','native_memory','native_heap')
            hashes={n:hashlib.sha256((selected.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if reference is None:reference=hashes
            if hashes!=reference:raise ValueError('program fault changes kernel mechanisms')
            s=symbols(selected);serial,trace=capture(selected,target,observer(s,c,target/'frame-trace.log',ram),ram)
            rows=validate(serial,trace,case,ram);result['cases'].append(dict(case=case,ram_mib=ram,tasks=rows))
            pending_observations+=validate_preemption(trace)
            print(f'BOOT_PROGRAM_CASE_OK case={case} ram={ram}',flush=True)
        inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=payload.validate(inner);s=symbols(image)
        for kind in ('header','rights','arguments',0,1,2):
            target=folder/('reject-'+str(kind));target.mkdir()
            serial,trace=capture(image,target,rejection_observer(s,c,target/'frame-trace.log',kind),4096)
            validate_rejection(serial,trace,kind);result['cases'].append(dict(rejected=kind))
            pending_observations+=validate_preemption(trace)
            print('BOOT_PROGRAM_REJECT_OK kind='+str(kind),flush=True)
        if not pending_observations:raise ValueError('missing actual pending IRQ regression')
        result['pending_irq_guests']=pending_observations
        result['passed']=True;print('BOOT_PROGRAMS_OK evidence='+str(folder));return 0
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        result['error']=str(error);print('BOOT_PROGRAMS_FAIL '+str(error)+' evidence='+str(folder));return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,3);(folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

if __name__=='__main__':raise SystemExit(main())
