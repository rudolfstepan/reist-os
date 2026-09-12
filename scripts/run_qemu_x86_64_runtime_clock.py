"""Opt-in full-width runtime proof; legacy ten-second runners stay unchanged."""
from pathlib import Path
import argparse, hashlib, json, queue, re, shutil, struct, subprocess, threading, time, uuid
import build_x86_64_c_payload as payload
import run_qemu_x86_64_native_heap as heap
import run_qemu_x86_64_native_ipc as ipc
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, FAILURES
from run_qemu_x86_64_spawn_oom import symbols
from measure_cpp_baseline import suppress_windows_test_dialogs
ROOT=Path(__file__).resolve().parents[1]
HORIZON=1<<60
ZERO=re.compile(r'PROCESS_ZERO_OK run=(\d+) zero=(\d+) free=(\d+) initial=(\d+) reaps=(\d+) generation=(\d+) ticks=(\d+)')


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('runtime observer binding: '+old[:80])
    return text.replace(old,new)


def observer(s,c,log,seed,peer):
    code=heap.observer(s,c,log,4096,peer)
    code=once(code,'0<deadline<256','0<deadline<(1<<60)')
    code=once(code,f"struct.unpack('<I',mem({s['scheduler_last_tick']},4))[0]",
                   f"struct.unpack('<Q',mem({s['scheduler_last_tick']},8))[0]")
    # Only the opt-in timer witness is replaced. All14 exact scrub ranges,
    # old13-frame releases, heap ownership and IPC copyout proofs stay intact.
    def at(name,kind='unsigned int'):return f'*({kind}*){s[name]:#x}'
    old=f'if {at("timer_ticks")}!={at("timer_eoi_count")} || {at("timer_ticks")}>=256 || {at("scheduler_final_result","unsigned char")}!=1'
    new=f'if {at("timer_runtime_ticks","unsigned long long")}!={at("timer_runtime_eois","unsigned long long")} || {at("timer_runtime_ticks","unsigned long long")}>=1152921504606846976 || {at("scheduler_final_result","unsigned char")}!=1'
    code=once(code,old,new)
    code=once(code,'generation=%u ticks=%u\\n",$runs', 'generation=%u ticks=%llu\\n",$runs')
    code=once(code,at('process_run_generation')+','+at('timer_ticks'),
                   at('process_run_generation')+','+at('timer_runtime_ticks','unsigned long long'))
    extra=f'''python
runtime_runs=0
runtime_start=runtime_end=None
class RuntimeClock(gdb.Breakpoint):
    def __init__(self,address,kind):
        super().__init__('*'+hex(address),internal=True)
        self.kind=kind
    def stop(self):
        global runtime_runs,runtime_start,runtime_end
        try:
            assert not reg('eflags')&512
            tick=u64({s['timer_runtime_ticks']})
            assert tick==u64({s['timer_runtime_eois']}) and tick<(1<<60)
            if self.kind=='begin':
                assert runtime_runs<2 and runtime_start is None
                if runtime_runs==0:
                    assert tick==0
                    # Sole debugger mutation: coherent pre-start clock seed.
                    for address in ({s['timer_runtime_ticks']},{s['timer_runtime_eois']}):
                        gdb.selected_inferior().write_memory(address,struct.pack('<Q',{seed}))
                    tick={seed}
                else: assert tick==runtime_end
                runtime_runs+=1
                runtime_start=tick
                gdb.write('RUNTIME_CLOCK_BEGIN run=%d tick=%d\\n'%(runtime_runs,tick))
            else:
                assert runtime_start is not None and 300<=tick-runtime_start<600
                assert u64({s['scheduler_last_tick']})==tick
                assert u64({s['timer_deadline']})>0
                assert mem({s['timer_mode']},1)==bytes([6])
                assert mem({s['timer_generation']},4)==struct.pack('<I',6)
                gdb.write('RUNTIME_CLOCK_END run=%d tick=%d delta=%d\\n'%(runtime_runs,tick,tick-runtime_start))
                runtime_end=tick
                runtime_start=None
        except Exception as error:
            gdb.write('RUNTIME_CLOCK_OBSERVER_FAIL '+repr(error)+'\\n')
            gdb.execute('quit 35')
        return False
RuntimeClock({s['x86_64_process_run64']},'begin')
RuntimeClock({s['process_run_finish64']},'end')
class RuntimeBudget(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex({s['process_run_retire64']}),internal=True)
    def stop(self):
        try:
            slot=struct.unpack('<I',mem({s['scheduler_current_slot']},4))[0]
            assert 0<=slot<4 and runtime_start is not None
            gen,limit,used,last=struct.unpack('<4Q',mem({s['scheduler_cpu_budgets']}+slot*32,32))
            tick=u64({s['timer_runtime_ticks']})
            assert gen==(runtime_runs-1)*4+slot+1 and limit==32 and used<=limit
            assert (runtime_start<last<=tick) if used else last==0
            gdb.write('RUNTIME_CPU_WITNESS gen=%d used=%d last=%d now=%d\\n'%(gen,used,last,tick))
        except Exception as error:
            gdb.write('RUNTIME_CLOCK_OBSERVER_FAIL '+repr(error)+'\\n')
            gdb.execute('quit 36')
        return False
RuntimeBudget()
end
continue
'''
    if not code.endswith('continue\n'):raise ValueError('runtime observer tail')
    return code[:-len('continue\n')]+extra


def validate(trace,rows,case,seed):
    begins=list(re.finditer(r'RUNTIME_CLOCK_BEGIN run=(\d+) tick=(\d+)',trace))
    ends=list(re.finditer(r'RUNTIME_CLOCK_END run=(\d+) tick=(\d+) delta=(\d+)',trace))
    zeros=list(ZERO.finditer(trace))
    if len(begins)!=2 or len(ends)!=2 or len(zeros)!=2 or trace.count('RUNTIME_CLOCK_')!=4:
        raise ValueError('runtime clock witness count/failure')
    previous=seed
    for run,(begin,end,zero) in enumerate(zip(begins,ends,zeros),1):
        b,first=map(int,begin.groups());e,last,delta=map(int,end.groups())
        if b!=run or e!=run or first!=previous or not 300<=last-first==delta<600 or last>=HORIZON:
            raise ValueError('runtime persistent clock/progress')
        if int(zero[7])!=last or not begin.end()<end.start()<end.end()<=zero.start():
            raise ValueError('runtime final timer/EOI/cleanup ordering')
        if run==1 and zero.end()>begins[1].start():raise ValueError('runtime run overlap')
        previous=last
    if seed and not seed<(1<<32)<int(ends[0][2]):raise ValueError('runtime actual32-bit crossing')
    budgets=list(re.finditer(r'RUNTIME_CPU_WITNESS gen=(\d+) used=(\d+) last=(\d+) now=(\d+)',trace))
    if len(budgets)!=8 or trace.count('RUNTIME_CPU_WITNESS')!=8:raise ValueError('runtime CPU witness count')
    for budget,row in zip(budgets,rows):
        gen,used,last,now=map(int,budget.groups());run=(gen-1)//4
        if run not in (0,1) or (gen,used)!=(row['generation'],row['ticks']):raise ValueError('runtime CPU receipt')
        if not begins[run].end()<budget.start()<budget.end()<=ends[run].start():raise ValueError('runtime CPU order')
        if not int(begins[run][2])<=now<=int(ends[run][2]) or used>32:raise ValueError('runtime CPU clock bound')
        if not (int(begins[run][2])<last<=now if used else last==0):raise ValueError('runtime CPU full-width sample')
    # Project ONLY the already-proved clock field to the old bootstrap profile
    # to reuse its independent non-time oracles. Never alter retained evidence.
    # Every original byte of frame, fence, IPC, heap, zero and count evidence is
    # passed unchanged; the stronger persistent64-bit oracle above owns time.
    projected=ZERO.sub(lambda m:m[0][:m[0].rfind('=')+1]+'32',trace)
    heap.validate_heap(projected,rows,4096,case)


def capture(image,folder,code):
    script=folder/'observe.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12491\n'+code,encoding='ascii')
    command=[str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m','4096M','-smp','1',
             '-display','none','-monitor','none','-nic','none','-serial','stdio','-no-reboot','-no-shutdown',
             '-kernel',str(image),'-S','-gdb','tcp:127.0.0.1:12491']
    (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
    output=queue.Queue(maxsize=128);overflow=threading.Event();data=bytearray();debugger=None;thread=None
    with (folder/'stderr.log').open('wb') as errors,(folder/'observer.log').open('wb') as observer_log:
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,bufsize=0,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
                                      stdout=observer_log,stderr=subprocess.STDOUT,
                                      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            def reader():
                while chunk:=vm.stdout.read(256):
                    try:output.put_nowait(chunk)
                    except queue.Full:overflow.set();return
            thread=threading.Thread(target=reader,daemon=True);thread.start()
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                try:data.extend(output.get(timeout=.01))
                except queue.Empty:pass
                if overflow.is_set() or len(data)>262144:raise ValueError('runtime serial capacity')
                serial=data.decode('ascii',errors='replace')
                if ipc.process.SUCCESS in serial or any(m in serial for m in FAILURES) or vm.poll() is not None or debugger.poll() not in (None,0):break
        finally:
            vm.stdin.close();terminate_bounded(vm)
            if debugger is not None:
                try:debugger.wait(timeout=2)
                except subprocess.TimeoutExpired:terminate_bounded(debugger)
            if thread is not None:thread.join(timeout=1)
            while not output.empty():data.extend(output.get_nowait())
            vm.stdout.close();(folder/'guest.log').write_bytes(data)
    if overflow.is_set() or len(data)>262144 or debugger.returncode:raise ValueError('runtime capture/detach failure')
    for name in ('observer.log','frame-trace.log'):
        if (folder/name).stat().st_size>65536:raise ValueError('runtime observer capacity')
    return data.decode('ascii',errors='replace'),(folder/'frame-trace.log').read_text(encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    image=args.image.resolve();base=args.evidence.resolve()
    if not image.is_relative_to(ROOT/'build') or not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('runtime scope')
    suppress_windows_test_dialogs();folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result={'passed':False,'cases':[]};started=time.monotonic()
    try:
        reference=None
        for case,seed in ((0,0),(0,(1<<32)-200),(3,(1<<32)-200)):
            target=folder/(str(case)+'-'+str(seed));target.mkdir();selected=image
            if case:
                command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                         '-NativeRuntime','-NativeIPCCase',str(case),'-OutputDirectory',target.relative_to(ROOT).as_posix()]
                with (target/'build.log').open('wb') as log:
                    build=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,
                                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if build.returncode:raise ValueError('runtime variant build')
                selected=target/'x86_64/reist-x86_64-bootstrap.elf'
            inner=payload.read_bounded(selected.parent/'reist-x86_64-c-core.elf');c=payload.validate(inner)
            payload.verify_outer(inner,payload.read_bounded(selected))
            if c['layout_version']!=4:raise ValueError('runtime private layout4')
            names=('cooperative_scheduler','timer_interrupt','bootstrap_core','identity_core','queue_core','context_core',
                   'cpu_budget','syscall_profile','task_frames','fp_context','user_fault','exceptions','user_access',
                   'native_ipc_pool','native_ipc','native_ipc_integrity','native_ipc_memory','native_memory','native_heap')
            hashes={n:hashlib.sha256((selected.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if reference is None:reference=hashes
            if hashes!=reference:raise ValueError('runtime mechanisms depend on fixture fault')
            s=symbols(selected);user=payload.elf(payload.read_bounded(selected.parent/'reist-x86_64-user-probe.elf'),64)
            serial,trace=capture(selected,target,observer(s,c,target/'frame-trace.log',seed,user['symbols']['heap_demo.peer']['value']))
            rows=ipc.validate(serial,case);validate(trace,rows,case,seed)
            result['cases'].append({'case':case,'seed':seed,'tasks':rows})
            print(f'RUNTIME_CLOCK_CASE_OK case={case} seed={seed}',flush=True)
        result['passed']=True;print('RUNTIME_CLOCK_OK evidence='+str(folder));return 0
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        result['error']=str(error);print('RUNTIME_CLOCK_FAIL '+str(error)+' evidence='+str(folder));return 1
    finally:
        result['elapsed']=round(time.monotonic()-started,3)
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
