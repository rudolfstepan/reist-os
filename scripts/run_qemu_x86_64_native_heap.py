"""Native heap guest proof; retained traces and original10-second guest lease."""
from pathlib import Path
import argparse
import json
import hashlib
import re
import subprocess
import time
import uuid
import build_x86_64_c_payload as payload
import run_qemu_x86_64_native_ipc as ipc
import run_qemu_x86_64_native_memory as memory
from run_qemu_x86_64_spawn_oom import symbols
from measure_cpp_baseline import suppress_windows_test_dialogs
ROOT=Path(__file__).resolve().parents[1]


def batch_zero_checks(code):
    # Same14 ranges, every byte, at the identical stopped-CPU checkpoint.
    # Thousands of individual remote reads must not consume the guest lease.
    pattern=re.compile(r'set \$i=0\nwhile \$i<(\d+)\nif \*\(unsigned char\*\)\((0x[0-9a-f]+)\+\$i\)!=0\nset \$zero=0\nend\nset \$i=\$i\+1\nend\n')
    matches=list(pattern.finditer(code))
    if [int(m[1]) for m in matches]!=[1024,2048,128,128,64,16,120,144,16,32,32,64,4,4]:
        raise ValueError('heap exact legacy zero ranges')
    def replacement(match):
        size,address=match.groups()
        return ('python\nif any(gdb.selected_inferior().read_memory('+address+','+size+
                ').tobytes()): gdb.execute("set $zero=0")\nend\n')
    return pattern.sub(replacement,code)


def observer(s,c,log,ram,peer):
    code=batch_zero_checks(memory.observer(s,c,log,ram))
    old=f'count=({payload.MEMORY_ARENA_BYTES}+4095)//4096'
    if code.count(old)!=1:raise ValueError('heap arena observer binding')
    code=code.replace(old,f'count=({payload.HEAP_ARENA_BYTES}+4095)//4096')
    needle='assert mem(destination,capacity)==request[64:64+capacity]'
    if code.count(needle)!=1:raise ValueError('heap IPC witness binding')
    code=code.replace(needle,needle+'''
                assert 0x100000000<=destination<0x120000000
                assert (destination&4095)+capacity>4096
                pdpt=u64(0xffff800000000000+root)&0x3fffff000
                pd=u64(0xffff800000000000+pdpt+4*8)
                assert pd&~0x60==(pd&0x3fffff000)|0x8000000000000007
                table=u64(0xffff800000000000+(pd&0x3fffff000)+((destination>>21)&511)*8)
                assert table&~0x60==(table&0x3fffff000)|0x8000000000000007
                for a in (destination,destination+capacity-1):
                    pte=u64(0xffff800000000000+(table&0x3fffff000)+((a>>12)&511)*8)
                    assert pte&~0x60==(pte&0x3fffff000)|0x8000000000000007
                    assert pte&0x3fffff000>=0x100000000
                gdb.write('NATIVE_HEAP_BUFFER slot=%d gen=%d pages=2 high=1 nx=1\\n'%(slot,gen))''')
    state=c['symbols']['native_heap_state']['value']
    free=c['symbols']['native_memory_state']['value']+4
    extra=f'''python
heap_steps=heap_peers=heap_completed=heap_run=0
heap_before=None
class HeapWatch(gdb.Breakpoint):
    def __init__(self,address,kind):
        super().__init__('*'+hex(address),internal=True)
        self.kind=kind
    def stop(self):
        global heap_steps,heap_peers,heap_completed,heap_run,heap_before
        try:
            assert not reg('eflags')&512
            if self.kind in ('begin','reap'):
                assert heap_before is None
                slot=reg('rdi') if self.kind=='begin' else reg('rbx')
                assert 0<=slot<4
                heap_before=(slot,struct.unpack('<I',mem({free},4))[0])
            elif self.kind=='end':
                assert heap_before is not None
                slot,before=heap_before
                after=struct.unpack('<I',mem({free},4))[0]
                assert abs(after-before)<=64
                heap_steps+=1
                assert heap_steps<8192
                if reg('rax')!=0xfffffffffffff001:heap_completed+=1
                heap_before=None
            else:
                heap_run+=1
                assert heap_before is None and 1<=heap_run<=2
                assert heap_peers>=3 and heap_steps>=8 and heap_completed>=8
                assert mem({s['process_heap_pending_mask']},8)==bytes(8)
                for slot in range(4):
                    task={state}+232+slot*99368
                    ctl=struct.unpack('<16Q',mem(task,128))
                    assert ctl[:8]==(0,(heap_run-1)*4+slot+1,0,0,0,0x20000000,0,0)
                    assert not any(ctl[8:])
                    assert not any(mem(task+552,5120))
                    assert not any(mem(task+32808,12288))
                gdb.write('NATIVE_HEAP_RUNTIME_WITNESS run=%d peers=%d steps=%d completed=%d zero=1\\n'%(heap_run,heap_peers,heap_steps,heap_completed))
                heap_steps=heap_peers=heap_completed=0
        except Exception as e:
            import traceback
            gdb.write(traceback.format_exc())
            gdb.write('NATIVE_HEAP_OBSERVER_FAIL '+repr(e)+'\\n')
            gdb.execute('quit 33')
        return False
class HeapPeer(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex({peer}),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    def stop(self):
        global heap_peers
        slot=struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]
        pending=struct.unpack('<I',mem({s['process_heap_pending_mask']},4))[0]
        if reg('cs')&3!=3 or slot not in (1,3):gdb.execute('quit 34')
        if pending&~(1<<slot):heap_peers+=1
        return False
HeapWatch({s['process_heap_enter64']},'begin')
HeapWatch({s['process_heap_enter64.step_complete']},'end')
HeapWatch({s['process_heap_reapers64.found']},'reap')
HeapWatch({s['process_heap_reapers64.step_complete']},'end')
HeapWatch({s['process_run_finish64']},'finish')
HeapPeer()
end
continue
'''
    if not code.endswith('continue\n'):raise ValueError('heap observer tail')
    return code[:-len('continue\n')]+extra


def validate_heap(trace,rows,ram,case):
    memory.validate_trace(trace,rows)
    ipc.validate_ipc_trace(trace,rows,case)
    if 'OBSERVER_FAIL' in trace:raise ValueError('heap observer failed')
    marks=re.findall(r'NATIVE_MEMORY_MAP_OK ram=(\d+) managed=(\d+) huge=(\d+) mixed=(\d+) high=(\d+)',trace)
    if len(marks)!=1:raise ValueError('heap memory map witness')
    actual,managed,huge,mixed,high=map(int,marks[0])
    if actual!=ram or not (ram-32)*256<managed<=ram*256 or not 0<huge or not 0<mixed<=512 or high!=1:
        raise ValueError('heap physical profile')
    marks=re.findall(r'NATIVE_HEAP_RUNTIME_WITNESS run=(\d+) peers=(\d+) steps=(\d+) completed=(\d+) zero=(\d+)',trace)
    if len(marks)!=2 or trace.count('NATIVE_HEAP_RUNTIME_WITNESS')!=2:raise ValueError('heap completion witnesses')
    for run,mark in enumerate(marks,1):
        actual,peers,steps,completed,zero=map(int,mark)
        if actual!=run or peers<3 or not 8<=steps<8192 or completed<8 or zero!=1:
            raise ValueError('heap work/peer/cleanup bounds')
    buffers=re.findall(r'NATIVE_HEAP_BUFFER slot=(\d+) gen=(\d+) pages=2 high=1 nx=1',trace)
    copies=re.findall(r'NATIVE_IPC_COPYOUT slot=(\d+) gen=(\d+) bytes=140 cr3=1',trace)
    if buffers!=copies or trace.count('NATIVE_HEAP_BUFFER')!=len(buffers):raise ValueError('heap IPC mapping witnesses')
    for match in memory.BEFORE.finditer(trace):
        if any(0<int(f,16)<0x100000000 for f in match[10].split(',')):
            raise ValueError('heap full-width physical consumer proof')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence scope')
    suppress_windows_test_dialogs()
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result={'passed':False,'cases':[]};started=time.monotonic()
    try:
        image=args.image.resolve()
        inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
        c=payload.validate(inner);payload.verify_outer(inner,payload.read_bounded(image))
        if c['layout_version']!=4:raise ValueError('NativeHeap layout4 required')
        reference=None
        for case,ram in ((0,4096),(0,8192),(1,4096),(3,8192)):
            target=folder/(str(case)+'-'+str(ram));target.mkdir()
            selected=image
            if case:
                command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                         '-NativeProcesses','-NativeIPC','-NativeRAM','-NativeHeap','-NativeIPCCase',str(case),
                         '-OutputDirectory',target.relative_to(ROOT).as_posix()]
                with (target/'build.log').open('wb') as log:
                    built=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if built.returncode:raise ValueError('heap variant build')
                selected=target/'x86_64/reist-x86_64-bootstrap.elf'
            inner=payload.read_bounded(selected.parent/'reist-x86_64-c-core.elf')
            c=payload.validate(inner);payload.verify_outer(inner,payload.read_bounded(selected))
            names=('cooperative_scheduler','timer_interrupt','bootstrap_core','identity_core','queue_core','context_core',
                   'cpu_budget','syscall_profile','task_frames','fp_context','user_fault','exceptions','user_access',
                   'native_ipc_pool','native_ipc','native_ipc_integrity','native_ipc_memory','native_memory','native_heap')
            hashes={n:hashlib.sha256((selected.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if reference is None:reference=hashes
            if hashes!=reference:raise ValueError('heap mechanisms changed with user fault case')
            s=symbols(selected)
            user=payload.elf(payload.read_bounded(selected.parent/'reist-x86_64-user-probe.elf'),64)
            peer=user['symbols']['heap_demo.peer']['value']
            serial,trace=ipc.capture(selected,target,observer(s,c,target/'frame-trace.log',ram,peer),ram)
            rows=ipc.validate(serial,case);validate_heap(trace,rows,ram,case)
            result['cases'].append({'case':case,'ram_mib':ram,'tasks':rows})
            print('NATIVE_HEAP_CASE_OK case='+str(case)+' ram='+str(ram),flush=True)
        result['passed']=True
        print('NATIVE_HEAP_RUNTIME_OK evidence='+str(folder));return 0
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        result['error']=str(error)
        print('NATIVE_HEAP_RUNTIME_FAIL '+str(error)+' evidence='+str(folder));return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
