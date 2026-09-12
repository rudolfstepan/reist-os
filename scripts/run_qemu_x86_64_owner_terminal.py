"""Bounded owner/dependent terminal corpus; hidden QEMU, no guest disks."""
from pathlib import Path
import argparse, hashlib, json, queue, re, shutil, struct, subprocess, threading, time, uuid
from run_qemu_x86_64_spawn_oom import symbols
from run_qemu_x86_64_task_frames import commands as frame_commands, BEFORE, AFTER, FREE
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, SUCCESS, FAILURES
from run_qemu_x86_64_shell_exit import READY, RUN, ERROR, MAX_TRACE, COMMON, PARENT, REAP

ROOT = Path(__file__).resolve().parents[1]
STATUS = (42,134,128,142,141,257,258,257,258,256)
OWNER = re.compile(r'REIST_X86_64_OWNER_CONTAINED_OK v1=([0-9A-F]{80})(?:\r?\n)')


def observer_commands(s, log):
    # Retain the existing read-only13-frame observation, IRQ-off checks,
    # bounded20 entries and exact backend calls. Add the owner fence/zero proof.
    code=frame_commands(s,log)
    def at(n,t='unsigned int'): return f'*({t}*){s[n]:#x}'
    fence=f'if {at("scheduler_mode","unsigned char")} == 7 && {at("scheduler_owner_plan")} != 0\n'
    for n,size in (('scheduler_syscall_profiles',64),('scheduler_shell_ipc_begin',s['scheduler_shell_ipc_end']-s['scheduler_shell_ipc_begin'])):
        fence+=f'set $i=0\nwhile $i<{size}\nif *(unsigned char*)({s[n]:#x}+$i)!=0\nquit 6\nend\nset $i=$i+1\nend\n'
    fence+=f'if {at("scheduler_active","unsigned char")} != 0 || {at("scheduler_deadline_count","unsigned char")} != 0 || {at("scheduler_runqueue_count","unsigned char")} != 0\nquit 7\nend\n'
    fence+=f'printf "OWNER_FENCE_OK slot=%u plan=%u\\n",($r12-{s["scheduler_tasks"]:#x})/256,{at("scheduler_owner_plan")}\nend\n'
    needle='set $inside=1\n'
    if code.count(needle)!=1: raise RuntimeError('frame observer entry drift')
    code=code.replace(needle,needle+fence)
    zero='set $zero=1\n'
    for n,size in (('scheduler_tasks',1024),('scheduler_fp_states',2048),('scheduler_table_frames',128),
                   ('scheduler_cpu_budgets',128),('scheduler_syscall_profiles',64),
                   ('scheduler_owner_receipt',40),('scheduler_runqueue_entries',32),
                   ('scheduler_deadline_entries',64),('scheduler_child_terminal_generation',64),
                   ('scheduler_shell_ipc_begin',s['scheduler_shell_ipc_end']-s['scheduler_shell_ipc_begin'])):
        zero+=f'set $i=0\nwhile $i<{size}\nif *(unsigned char*)({s[n]:#x}+$i)!=0\nset $zero=0\nend\nset $i=$i+1\nend\n'
    for n,t in (('scheduler_active','unsigned char'),('scheduler_syscalls_active','unsigned char'),
                ('timer_active','unsigned char'),('timer_generation','unsigned int'),('timer_deadline','unsigned long long'),
                ('scheduler_dynamic_child_active','unsigned char'),('scheduler_dynamic_wait_status_direct','unsigned long long')):
        zero+=f'if {at(n,t)} != 0\nset $zero=0\nend\n'
    # Delivered/EOI totals are retained diagnostics, not live timer bindings.
    zero+=f'if {at("timer_ticks")} != {at("timer_eoi_count")} || {at("timer_ticks")} > 256\nset $zero=0\nend\n'
    zero+=f'printf "OWNER_ZERO_OK zero=%u frames=%u initial=%u reaps=%u parent=%u child=%u\\n",$zero,'
    zero+=','.join((at('free_frame_count'),at('scheduler_initial_free'),at('scheduler_reap_count'),
                   at('scheduler_identity_retired'),f'*(unsigned int*){s["scheduler_identity_retired"]+4:#x}'))+'\n'
    needle='detach\nquit\nend\ncontinue\n'
    if code.count(needle)!=1: raise RuntimeError('frame observer terminal drift')
    return code.replace(needle,zero+needle)


def validate_trace(trace,kind,phase,previous):
    children=previous+int(phase>=2)
    before=list(BEFORE.finditer(trace)); after=list(AFTER.finditer(trace)); frees=list(FREE.finditer(trace))
    expected={(m,slot,1+slot):(4 if slot==0 else 3 if m==1 else 5)
              for m in (1,2,3) for slot in (0,1)}
    expected.update({(4,slot,10+slot):(3 if slot==3 else 4) for slot in range(4)})
    expected.update({(5,slot,20+slot):4 for slot in range(4)})
    expected.update({(6,0,30):4,(6,1,31):8,(6,1,32):8,(7,0,40):3 if kind else 4})
    for i in range(children): expected[7,1,41+i]=3 if i==previous and phase in (2,3) else 8
    if len(before)!=len(expected) or len(after)!=len(expected) or len(frees)>260:
        raise RuntimeError('frame observation count')
    seen=set();consumed=0
    for i,(b,a) in enumerate(zip(before,after)):
        seq,mode,slot,gen,state,root,active,free,fp,frames=b.groups()
        seq,mode,slot,gen,state,free,fp=map(int,(seq,mode,slot,gen,state,free,fp))
        frames=[int(f,16) for f in frames.split(',')]; owned=[f for f in frames if f]
        if seq!=i+1 or (mode,slot,gen) in seen or expected.get((mode,slot,gen))!=state or fp!=1:
            raise RuntimeError('frame identity/state/FP')
        seen.add((mode,slot,gen))
        if len(frames)!=13 or len(set(owned))!=len(owned) or any(not 0<f<0x8000000 or f%4096 for f in owned):
            raise RuntimeError('frame ownership/alias')
        if int(root,16)!=frames[-1] or int(root,16)==int(active,16) or not 0<int(active,16)<0x8000000 or int(active,16)%4096:
            raise RuntimeError('active address space')
        if tuple(map(int,a.groups()))!=(seq,gen,state,1,free+len(owned),1) or not 0<free<free+len(owned)<=32768:
            raise RuntimeError('frame balance/scrub')
        if not (after[i-1].end() if i else -1)<b.start()<b.end()<a.start(): raise RuntimeError('frame ordering')
        calls=[f for f in frees if b.end()<=f.start()<a.start()];consumed+=len(calls)
        if [(int(f[1]),int(f[2],16)) for f in calls]!=[(seq,f) for f in owned]: raise RuntimeError('backend free sequence')
    if consumed!=len(frees) or seen!=set(expected): raise RuntimeError('unowned/missing frame release')
    fences=re.findall(r'OWNER_FENCE_OK slot=(\d+) plan=(\d+)',trace)
    plan=(1,1,2,3,4)[phase]
    if [(int(s),int(p)) for s,p in fences]!=([(1,plan)] if phase in (2,3) else [])+[(0,plan)]:
        raise RuntimeError('fencing before retirement')
    zeros=re.findall(r'OWNER_ZERO_OK zero=(\d+) frames=(\d+) initial=(\d+) reaps=(\d+) parent=(\d+) child=(\d+)',trace)
    if len(zeros)!=1: raise RuntimeError('final zero observation count')
    z,free,initial,reaps,parent,child=map(int,zeros[0])
    if z!=1 or not 0<free==initial<=32768 or (reaps,parent,child)!=(children+1,40,40+children if children else 0):
        raise RuntimeError('final ownership/zero/balance')


def validate(serial, kind, phase, previous):
    if kind not in range(10) or phase not in range(5) or previous not in (0,1):
        raise RuntimeError('invalid expected case')
    if any(m in serial for m in FAILURES if m != ERROR):
        raise RuntimeError('kernel failure during owner containment')
    positions = [serial.find(m) for m in COMMON]
    if any(serial.count(m)!=1 for m in COMMON) or positions!=sorted(positions):
        raise RuntimeError('missing/duplicate/out-of-order kernel progress')
    rows = list(OWNER.finditer(serial)); parents = list(PARENT.finditer(serial))
    if len(rows)!=1 or len(parents)!=1 or serial.count('OWNER_CONTAINED_OK')!=1:
        raise RuntimeError('owner receipt count')
    plan,cause,endpoint,queued,deadline,child,rip,ticks = struct.unpack('<6I2Q', bytes.fromhex(rows[0][1]))
    expected_plan = (1,1,2,3,4)[phase]
    expected_child = 41+previous if phase>=2 else 0
    expected_endpoint = ((previous+1)<<8)|1 if phase in (1,2,3) else 0
    if (plan,cause,endpoint,queued,deadline,child) != (expected_plan,int(kind!=0),expected_endpoint,
                                                   int(phase==3),int(phase==3),expected_child):
        raise RuntimeError(f'wrong owner dependency receipt {(plan,cause,endpoint,queued,deadline,child)}')
    if not 0x400000<=rip<0x408000 or ticks>128 or (kind==9 and ticks!=128):
        raise RuntimeError('owner instruction/budget receipt')
    n=previous+int(phase>=2)
    if tuple(int(v,16) for v in parents[0].groups()) != (STATUS[kind],n,n+1,40,40+n):
        raise RuntimeError('wrong owner status/generation/reap count')
    reaps=list(REAP.finditer(serial))
    if len(reaps)!=previous+int(phase==4) or serial.count(RUN)!=previous or serial.count(ERROR)!=1:
        raise RuntimeError('missing/extra child reap, RUN or observable owner error')
    for i,row in enumerate(reaps):
        status,gen,state,q,r=(int(v,16) for v in row.groups())
        if (status,gen,q)!=(77,41+i,0) or state not in (1,6,7) or not 0x400000<=r<0x408000:
            raise RuntimeError('wrong ordinary child terminal record')
        if row.end()>rows[0].start(): raise RuntimeError('child receipt after owner')
    if serial.count('CHILD_')!=len(reaps):
        # The pre-shell bootstrap has no CHILD_ receipt; cancelled dependents
        # must not be represented as successful user EXITs.
        raise RuntimeError('unexpected child failure/cancellation receipt')
    if not serial.index(READY)<rows[0].start()<rows[0].end()<=parents[0].start()<serial.index(ERROR):
        raise RuntimeError('owner cleanup receipt ordering')
    return dict(kind=kind,phase=phase,previous=previous,status=STATUS[kind],plan=plan,
                child=child,rip=hex(rip),cpu_ticks=ticks)


def capture(image, folder, kind, phase, previous, observe=False):
    command = [str(resolve_qemu(None)), '-machine', 'pc,accel=tcg', '-cpu', 'qemu64',
               '-m', '128M', '-smp', '1', '-display', 'none', '-monitor', 'none',
               '-serial', 'stdio', '-no-reboot', '-no-shutdown', '-kernel', str(image.resolve())]
    debugger = None
    if observe:
        command += ['-S','-gdb','tcp:127.0.0.1:12487']
        s=symbols(image)
        code='set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12487\n'
        code+=observer_commands(s,folder/'frame-trace.log')
        (folder/'observe.gdb').write_text(code, encoding='ascii')
    (folder/'command.json').write_text(json.dumps(command), encoding='utf-8')
    output = queue.Queue(maxsize=128)
    overflow = threading.Event()
    data = bytearray()
    with (folder/'stderr.log').open('wb') as errors, (folder/'observer.log').open('wb') as observer:
        p = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=errors, bufsize=0,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if observe:
            try:
                debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(folder/'observe.gdb')],
                    stdout=observer,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            except OSError:
                p.stdin.close()
                terminate_bounded(p)
                p.stdout.close()
                raise
        def reader():
            while chunk := p.stdout.read(256):
                try: output.put_nowait(chunk)
                except queue.Full:
                    overflow.set()
                    return
        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        actions = ([(READY, b'RUN\n')] if previous else [])
        actions += [(RUN if previous else READY, f'T{kind}{phase}\n'.encode())]
        sent = 0
        deadline = time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                try: data.extend(output.get(timeout=.02))
                except queue.Empty: pass
                if overflow.is_set() or len(data) > MAX_TRACE:
                    raise RuntimeError('serial capacity exceeded')
                serial = data.decode('ascii', errors='replace')
                if sent < len(actions) and actions[sent][0] in serial:
                    p.stdin.write(actions[sent][1]); p.stdin.flush(); sent += 1
                if SUCCESS in serial or any(m in serial for m in FAILURES if m != ERROR): break
                if p.poll() is not None: break
                if debugger and debugger.poll() not in (None,0): break
        finally:
            p.stdin.close()
            terminate_bounded(p)
            if debugger:
                try: debugger.wait(timeout=2)
                except subprocess.TimeoutExpired: terminate_bounded(debugger)
            thread.join(timeout=1)
            while not output.empty(): data.extend(output.get_nowait())
            p.stdout.close()
            (folder/'guest.log').write_bytes(data)
    if overflow.is_set() or len(data) > MAX_TRACE: raise RuntimeError('serial overflow')
    if debugger:
        if debugger.returncode: raise RuntimeError('observer did not detach cleanly')
        path=folder/'frame-trace.log'
        if not path.is_file() or path.stat().st_size>65536: raise RuntimeError('bounded frame trace missing/overflow')
        validate_trace(path.read_text(encoding='utf-8'),kind,phase,previous)
    return data.decode('ascii', errors='replace')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--legacy-image', type=Path)
    parser.add_argument('--image', type=Path, help='bounded focused diagnosis of an already built fixture')
    parser.add_argument('--case', nargs=3, type=int, metavar=('KIND','PHASE','PREVIOUS'))
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    base = args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'): parser.error('evidence outside workspace')
    attempt = base/('attempt-'+uuid.uuid4().hex)
    attempt.mkdir(parents=True)
    started = time.monotonic()
    summary = dict(passed=False)
    try:
        if args.legacy_image:
            serial = capture(args.legacy_image, attempt, 1, 0, False)
            if (READY not in serial or SUCCESS in serial or 'SHELL_REAP_OK' in serial or
                    not any(x in serial for x in ('EXCEPTION_FATAL', 'C_KERNEL_CONTROL_ERROR'))):
                raise RuntimeError('actual old owner-fault failure not reproduced')
            summary.update(passed=True, image_sha256=hashlib.sha256(args.legacy_image.read_bytes()).hexdigest())
            print('OWNER_TERMINAL_LEGACY_OK evidence='+str(attempt))
            return 0
        if args.image and args.case:
            serial = capture(args.image,attempt,*args.case,observe=args.observe)
            summary.update(passed=True,case=validate(serial,*args.case))
            print('OWNER_TERMINAL_CASE_OK evidence='+str(attempt))
            return 0
        command=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                 '-OutputDirectory',attempt.relative_to(ROOT).as_posix(),'-OwnerTerminal']
        with (attempt/'build.log').open('wb') as out:
            result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT,timeout=90,
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode: raise RuntimeError('fixture build failed: '+str(attempt/'build.log'))
        image=attempt/'x86_64/reist-x86_64-bootstrap.elf'
        summary['image_sha256']=hashlib.sha256(image.read_bytes()).hexdigest()
        summary['cases']=[]
        # Ten compatible terminal causes, both namespace histories; dependency
        # cancellation uses immediate EXIT/UD2, without racing IRQ wait expiry.
        cases=[(k,p,n) for k in range(10) for p in (0,1) for n in (0,1)]
        cases += [(k,p,n) for k in (0,1) for p in (2,3,4) for n in (0,1)]
        for kind,phase,previous in cases:
            folder=attempt/f'{kind}-{phase}-{previous}';folder.mkdir()
            serial=capture(image,folder,kind,phase,previous)
            summary['cases'].append(validate(serial,kind,phase,previous))
            print(f'OWNER_CASE_OK kind={kind} phase={phase} previous={previous}',flush=True)
        # Independent read-only resource observations, including the CPU tail,
        # IRQ-context tail, live/blocked cancellation and already-reaped child.
        summary['observations']=[]
        for kind,phase,previous in ((0,2,0),(1,3,1),(1,4,1),(7,0,0),(9,1,1)):
            folder=attempt/f'observe-{kind}-{phase}-{previous}';folder.mkdir()
            serial=capture(image,folder,kind,phase,previous,observe=True)
            summary['observations'].append(validate(serial,kind,phase,previous))
        summary['passed']=True
        print('OWNER_TERMINAL_RUNTIME_OK cases=52 observations=5 evidence='+str(attempt))
        return 0
    finally:
        summary['elapsed'] = round(time.monotonic()-started, 3)
        (attempt/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__': raise SystemExit(main())
