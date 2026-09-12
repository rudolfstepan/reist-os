"""Bounded real independent-process runs; no shell dialogue or kernel test knobs."""
from pathlib import Path
import argparse, hashlib, json, queue, re, shutil, struct, subprocess, threading, time, uuid
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, FAILURES, REQUIRED_MARKERS
from run_qemu_x86_64_spawn_oom import symbols
from run_qemu_x86_64_task_frames import commands as frame_commands, BEFORE, FREE, AFTER
ROOT=Path(__file__).resolve().parents[1]
REAP=re.compile(r'REIST_X86_64_PROCESS_REAP_OK v1=([0-9A-F]{64})(?![0-9A-F])')
STATUS=(0,134,142,128,258,257,258,257,256)
NORMAL=(0,42,0x80000000,0xffffffff)
DONE='REIST_X86_64_PROCESS_RUN_OK'
SUCCESS='REIST_X86_64_NATIVE_PROCESSES_OK'


def validate(serial,case):
    if case not in range(9) or any(x in serial for x in FAILURES):
        raise RuntimeError('native process profile failed')
    common=[m for m in REQUIRED_MARKERS if 'SHELL' not in m]+[SUCCESS]
    positions=[serial.find(m) for m in common]
    if any(serial.count(m)!=1 for m in common) or positions!=sorted(positions):
        raise RuntimeError('missing/duplicate/out-of-order kernel progress')
    rows=list(REAP.finditer(serial));done=list(re.finditer(DONE,serial))
    if len(rows)!=8 or serial.count('PROCESS_REAP_OK')!=8 or len(done)!=2:
        raise RuntimeError('process receipt count')
    result=[]
    for run in range(2):
        seen=set()
        for row in rows[run*4:run*4+4]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(row[1]))
            target=(case+run)%4
            quota=4+slot*4+run*16
            if slot not in range(4) or slot in seen or gen!=run*4+slot+1:
                raise RuntimeError('slot/generation reuse')
            seen.add(slot)
            bad=case!=0 and slot==target
            if (status,state)!=(STATUS[case] if bad else NORMAL[slot],3 if bad else 4):
                raise RuntimeError(f'wrong task outcome {slot,gen,status,state}')
            if not 0x400000<=rip<0x408000 or ticks>quota or (bad and case==8 and ticks!=quota):
                raise RuntimeError('invalid RIP/CPU receipt')
            if not (done[run-1].end() if run else -1)<row.start()<row.end()<=done[run].start():
                raise RuntimeError('receipt before exact run completion')
            result.append(dict(slot=slot,generation=gen,status=status,state=state,ticks=ticks,rip=rip))
    if done[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):
        raise RuntimeError('run completion after caller progress')
    return result


def diagnostic_commands(s):
    return f'''break *{s['scheduler_fail']:#x}
commands
silent
printf "PROCESS_DIAG_FAIL stage=%u mode=%u slot=%u last=%u live=%u gen=%u rq=%u dl=%u\\n",*(unsigned char*){s['scheduler_failure_stage']:#x},*(unsigned char*){s['scheduler_mode']:#x},*(unsigned int*){s['scheduler_current_slot']:#x},*(unsigned int*){s['scheduler_last_tick']:#x},*(unsigned int*){s['process_run_live']:#x},*(unsigned int*){s['process_run_generation']:#x},*(unsigned char*){s['scheduler_runqueue_count']:#x},*(unsigned char*){s['scheduler_deadline_count']:#x}
info registers rax rbx rcx rdx rdi rsi r8 r9 r10 r11 r12 r13 r14 r15 rip rsp
x/8gx $rsp
detach
quit
end
continue
'''


def observer_commands(s,log):
    # Preserve the existing13-frame/backend/FP observation. This different
    # profile has17 legacy releases then8 independent releases, never20.
    code=frame_commands(s,log)
    boundary=f'break *{s["scheduler_return64"]:#x}'
    if code.count('$seq>=20')!=1 or code.count(boundary)!=1:
        raise RuntimeError('frame observer template drift')
    code=code.split(boundary,1)[0].replace('$seq>=20','$seq>=25')
    code=code.replace('set $seq=0\n','set $seq=0\nset $runs=0\n',1)
    def at(n,t='unsigned int'):return f'*({t}*){s[n]:#x}'
    fence=f'if {at("scheduler_mode","unsigned char")} == 8\n'
    fence+=f'set $profile={s["scheduler_syscall_profiles"]:#x}+$slot*16\n'
    fence+=f'if {at("scheduler_active","unsigned char")} != 1 || {at("scheduler_current_slot")} != $slot\nquit 6\nend\n'
    fence+=f'if *(unsigned char*)({s["scheduler_runqueue_membership"]:#x}+$slot)!=0 || *(unsigned char*)({s["scheduler_deadline_membership"]:#x}+$slot)!=0\nquit 7\nend\n'
    fence+='if *(unsigned long long*)$profile!=0 || *(unsigned long long*)($profile+8)!=0\nquit 8\nend\n'
    fence+=f'if *(unsigned long long*)($task+8)!=*(unsigned int*)({s["process_run_generations"]:#x}+$slot*4)\nquit 9\nend\n'
    fence+='printf "PROCESS_FENCE_OK seq=%u slot=%u gen=%u\\n",$seq,$slot,*(unsigned long long*)($task+8)\nend\n'
    needle='set $fp_nonzero=0\n'
    if code.count(needle)!=1:raise RuntimeError('frame observer fence position drift')
    code=code.replace(needle,fence+needle)
    code+=boundary+f' if {at("scheduler_mode","unsigned char")} == 8\ncommands 4\nsilent\n'
    code+='if $inside || $runs>=2 || ($eflags&512)!=0\nquit 10\nend\nset $runs=$runs+1\nset $zero=1\n'
    for n,size in (('scheduler_tasks',1024),('scheduler_fp_states',2048),('scheduler_table_frames',128),
                   ('scheduler_cpu_budgets',128),('scheduler_syscall_profiles',64),('scheduler_syscall_context',16),
                   ('syscall_rax',120),
                   ('process_run_plan',144),('process_run_generations',16),('process_run_receipt',32),
                   ('scheduler_runqueue_entries',32),('scheduler_deadline_entries',64),
                   ('scheduler_runqueue_membership',4),('scheduler_deadline_membership',4)):
        code+=f'set $i=0\nwhile $i<{size}\nif *(unsigned char*)({s[n]:#x}+$i)!=0\nset $zero=0\nend\nset $i=$i+1\nend\n'
    for n,t in (('scheduler_active','unsigned char'),('scheduler_syscalls_active','unsigned char'),
                ('timer_active','unsigned char'),('timer_generation','unsigned int'),('timer_mode','unsigned char'),
                ('timer_deadline','unsigned long long'),('timer_masks_saved','unsigned char'),
                ('process_run_live','unsigned int'),('process_run_build_slot','unsigned int'),
                ('scheduler_runqueue_count','unsigned char'),('scheduler_deadline_count','unsigned char')):
        code+=f'if {at(n,t)}!=0\nset $zero=0\nend\n'
    code+=f'if {at("timer_ticks")}!={at("timer_eoi_count")} || {at("timer_ticks")}>=256 || {at("scheduler_final_result","unsigned char")}!=1\nset $zero=0\nend\n'
    code+='printf "PROCESS_ZERO_OK run=%u zero=%u free=%u initial=%u reaps=%u generation=%u ticks=%u\\n",$runs,$zero,'
    code+=','.join(at(n) for n in ('free_frame_count','scheduler_initial_free','scheduler_reap_count','process_run_generation','timer_ticks'))+'\n'
    code+='if $runs==2\ndetach\nquit\nend\ncontinue\nend\ncontinue\n'
    return code


def validate_trace(trace,rows):
    before=list(BEFORE.finditer(trace));after=list(AFTER.finditer(trace));frees=list(FREE.finditer(trace))
    expected={(m,slot,1+slot):(4 if slot==0 else 3 if m==1 else 5) for m in (1,2,3) for slot in (0,1)}
    expected.update({(4,s,10+s):3 if s==3 else 4 for s in range(4)})
    expected.update({(5,s,20+s):4 for s in range(4)})
    expected.update({(6,0,30):4,(6,1,31):8,(6,1,32):8})
    expected.update({(8,r['slot'],r['generation']):r['state'] for r in rows})
    if len(before)!=25 or len(after)!=25 or len(frees)>325:raise RuntimeError('frame count')
    seen=set();consumed=0;native=[]
    for i,(b,a) in enumerate(zip(before,after)):
        seq,mode,slot,gen,state,root,active,free,fp,frames=b.groups()
        seq,mode,slot,gen,state,free,fp=map(int,(seq,mode,slot,gen,state,free,fp))
        frames=[int(f,16) for f in frames.split(',')];owned=[f for f in frames if f]
        if seq!=i+1 or (mode,slot,gen) in seen or expected.get((mode,slot,gen))!=state or fp!=1:
            raise RuntimeError('frame identity/state/FP')
        seen.add((mode,slot,gen))
        if mode==8:native.append((seq,slot,gen))
        if len(frames)!=13 or not all(frames[8:]) or len(set(owned))!=len(owned) or any(not 0<f<0x8000000 or f%4096 for f in owned):
            raise RuntimeError('frame ownership')
        root,active=int(root,16),int(active,16)
        if root!=frames[-1] or root==active or not 0<active<0x8000000 or active%4096:
            raise RuntimeError('active root')
        if tuple(map(int,a.groups()))!=(seq,gen,state,1,free+len(owned),1) or not 0<free<free+len(owned)<=32768:
            raise RuntimeError('frame balance/scrub')
        if not (after[i-1].end() if i else -1)<b.start()<b.end()<a.start():raise RuntimeError('frame order')
        calls=[f for f in frees if b.end()<=f.start()<a.start()];consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(seq,f) for f in owned]:raise RuntimeError('backend free order')
    if consumed!=len(frees) or seen!=set(expected):raise RuntimeError('unowned or missing release')
    if native!=[(18+i,r['slot'],r['generation']) for i,r in enumerate(rows)]:raise RuntimeError('serial/frame lifecycle mismatch')
    fences=list(re.finditer(r'PROCESS_FENCE_OK seq=(\d+) slot=(\d+) gen=(\d+)',trace))
    if [tuple(map(int,f.groups())) for f in fences]!=native:raise RuntimeError('exact independent fences')
    for f,(seq,_,_) in zip(fences,native):
        if not after[seq-2].end()<f.start()<f.end()<=before[seq-1].start():raise RuntimeError('fence after free')
    zeros=list(re.finditer(r'PROCESS_ZERO_OK run=(\d+) zero=(\d+) free=(\d+) initial=(\d+) reaps=(\d+) generation=(\d+) ticks=(\d+)',trace))
    if len(zeros)!=2:raise RuntimeError('final zero count')
    for i,z in enumerate(zeros):
        run,zero,free,initial,reaps,gen,ticks=map(int,z.groups())
        if (run,zero,reaps,gen)!=(i+1,1,4,4*(i+1)) or not 0<free==initial<=32768 or not 6<=ticks<256:
            raise RuntimeError('final generation/zero/frame balance')
        if not after[20+i*4].end()<z.start() or i==0 and z.end()>before[21].start():
            raise RuntimeError('run zero ordering')


def capture(image,folder,diagnose=False,observe=False):
    command=[str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m','128M','-smp','1',
             '-display','none','-monitor','none','-serial','stdio','-no-reboot','-no-shutdown','-kernel',str(image.resolve())]
    debugger=None
    if diagnose or observe:
        command+=['-S','-gdb','tcp:127.0.0.1:12489']
        s=symbols(image)
        code='set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12489\n'
        code+=diagnostic_commands(s) if diagnose else observer_commands(s,folder/'frame-trace.log')
        (folder/'observe.gdb').write_text(code,encoding='ascii')
    output=queue.Queue(maxsize=128);overflow=threading.Event();data=bytearray()
    (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
    with (folder/'stderr.log').open('wb') as errors, (folder/'observer.log').open('wb') as observer:
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,
                            bufsize=0,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            if diagnose or observe:
                debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(folder/'observe.gdb')],
                    stdout=observer,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError:
            vm.stdin.close();terminate_bounded(vm);vm.stdout.close();raise
        def reader():
            while chunk:=vm.stdout.read(256):
                try:output.put_nowait(chunk)
                except queue.Full:overflow.set();return
        thread=threading.Thread(target=reader,daemon=True);thread.start()
        deadline=time.monotonic()+10
        try:
            while time.monotonic()<deadline:
                try:data.extend(output.get(timeout=.02))
                except queue.Empty:pass
                if overflow.is_set() or len(data)>262144:raise RuntimeError('serial capacity')
                serial=data.decode('ascii',errors='replace')
                if SUCCESS in serial or any(m in serial for m in FAILURES):break
                if vm.poll() is not None or debugger and debugger.poll() not in (None,0):break
        finally:
            vm.stdin.close();terminate_bounded(vm)
            if debugger:
                try:debugger.wait(timeout=2)
                except subprocess.TimeoutExpired:terminate_bounded(debugger)
            thread.join(timeout=1)
            while not output.empty():data.extend(output.get_nowait())
            vm.stdout.close();(folder/'guest.log').write_bytes(data)
    if overflow.is_set() or len(data)>262144:raise RuntimeError('serial overflow')
    if observe and debugger.returncode:raise RuntimeError('observer did not detach cleanly')
    return data.decode('ascii',errors='replace')


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--image',type=Path);p.add_argument('--case',type=int,choices=range(9),default=0)
    p.add_argument('--diagnose',action='store_true');p.add_argument('--observe',action='store_true');args=p.parse_args()
    base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    started=time.monotonic();summary=dict(passed=False,cases=[])
    try:
        if args.image:
            serial=capture(args.image,attempt,args.diagnose,args.observe)
            rows=validate(serial,args.case);summary['cases'].append(rows)
            if args.observe:
                log=attempt/'frame-trace.log'
                if log.stat().st_size>65536:raise RuntimeError('frame trace capacity')
                validate_trace(log.read_text(),rows)
        else:
            expected=None
            for case in range(9):
                folder=attempt/str(case);folder.mkdir()
                command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                         '-OutputDirectory',folder.relative_to(ROOT).as_posix(),'-NativeProcesses','-ProcessCase',str(case)]
                with (folder/'build.log').open('wb') as out:
                    result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=90,
                                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if result.returncode:raise RuntimeError('build failed: '+str(folder/'build.log'))
                image=folder/'x86_64/reist-x86_64-bootstrap.elf'
                names=('cooperative_scheduler','timer_interrupt','bootstrap_core','identity_core','queue_core','context_core',
                       'cpu_budget','syscall_profile','task_frames','fp_context','user_fault','exceptions')
                hashes={name:hashlib.sha256((image.parent/(name+'.o')).read_bytes()).hexdigest() for name in names}
                if expected is not None and hashes!=expected:raise RuntimeError('kernel changed across user cases')
                expected=hashes
                serial=capture(image,folder)
                summary['cases'].append(dict(case=case,tasks=validate(serial,case)))
                print(f'PROCESS_CASE_OK case={case}',flush=True)
                if case in (0,1,6,7,8):
                    observed=folder/'observed';observed.mkdir()
                    serial=capture(image,observed,observe=True);rows=validate(serial,case)
                    log=observed/'frame-trace.log'
                    if log.stat().st_size>65536:raise RuntimeError('frame trace capacity')
                    validate_trace(log.read_text(),rows)
                    print(f'PROCESS_OBSERVED_OK case={case}',flush=True)
            summary['mechanisms']=expected
        summary['passed']=True
        print('PROCESS_RUN_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as exc:
        summary['error']=str(exc);print('PROCESS_RUN_RUNTIME_FAIL '+str(exc)+' evidence='+str(attempt));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
