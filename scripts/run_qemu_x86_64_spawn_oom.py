"""Inject allocator exhaustion before effects; require rollback and retry receipts."""
from pathlib import Path
import argparse, hashlib, json, queue, re, shutil, subprocess, threading, time, uuid
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, REQUIRED_MARKERS, FAILURES, SUCCESS
from run_qemu_x86_64_requests import exit_address, MECHANISMS
from run_qemu_x86_64_ipc_handoff import REAP
ROOT=Path(__file__).resolve().parents[1]
PREFIX='set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12485\n'

def symbols(image):
    data=subprocess.check_output(['nm',str(image)],text=True,timeout=10)
    if len(data)>2*1024*1024:raise RuntimeError('symbol limit')
    return {r[2]:int(r[0],16)+0xffffffff80000000 for line in data.splitlines() if len(r:=line.split())==3}

def observed_boot(image,folder,commands):
    script=folder/'inject.gdb';script.write_text(PREFIX+commands,encoding='ascii')
    no_window=getattr(subprocess,'CREATE_NO_WINDOW',0)
    vm=subprocess.Popen([str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64',
        '-m','128M','-smp','1','-display','none','-monitor','none','-serial','stdio',
        '-no-reboot','-no-shutdown','-kernel',str(image),'-S','-gdb','tcp:127.0.0.1:12485'],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=0,creationflags=no_window)
    chunks=queue.Queue();data=bytearray();debugger=None;trace='';step=0
    def read():
        for b in iter(lambda:vm.stdout.read(256),b''):chunks.put(b)
    reader=threading.Thread(target=read,daemon=True);reader.start();start=time.monotonic()
    try:
        debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=no_window)
        while time.monotonic()-start<10:
            try:data.extend(chunks.get(timeout=.01))
            except queue.Empty:pass
            text=data.decode('ascii',errors='replace')
            milestones=[('RING3_SHELL_READY',b'INFO\n'),('RING3_SHELL_INFO_OK',b'RUN\n'),('RING3_SHELL_RUN_OK',b'RUN\n')]
            if step<3 and milestones[step][0] in text:
                vm.stdin.write(milestones[step][1]);vm.stdin.flush();step+=1
            if step==3 and text.count('REIST_X86_64_RING3_SHELL_RUN_OK')==2:
                vm.stdin.write(b'EXIT\n');vm.stdin.flush();step+=1
            if SUCCESS in text or any(x in text for x in FAILURES) or vm.poll() is not None:break
    finally:
        terminate_bounded(vm);reader.join(timeout=1)
        while not chunks.empty():data.extend(chunks.get_nowait())
        if debugger:
            try:trace=debugger.communicate(timeout=2)[0].decode('utf-8',errors='replace')
            except subprocess.TimeoutExpired:
                terminate_bounded(debugger);trace=debugger.communicate(timeout=2)[0].decode('utf-8',errors='replace')
        (folder/'guest.log').write_bytes(data);(folder/'gdb.log').write_text(trace,encoding='utf-8')
    text=data.decode('ascii',errors='replace')
    positions=[text.find(x) for x in REQUIRED_MARKERS]
    if step!=4 or any(x in text for x in FAILURES) or min(positions)<0 or positions!=sorted(set(positions)):
        raise RuntimeError('guest failure/incomplete dialogue: '+text[-700:])
    if debugger.returncode:raise RuntimeError('injector did not detach: '+trace[-700:])
    return text,trace

def injection(s,ordinal):
    def addr(name):return f'{s[name]:#x}'
    gen=f'*(unsigned int*)({addr("scheduler_identity_pool")}+20)'
    active=f'*(unsigned char*){addr("scheduler_spawn_transaction_active")}'
    c='set $injected = 0\nset $count = 0\nset $hits = 0\n'
    c+=f'break *{addr("physical_frame_alloc64")} if {active} == 1\ncommands 1\nsilent\n'
    c+='set $hits = $hits + 1\nif $hits > 64\nquit 2\nend\n'
    c+=f'if $injected != {gen}\nset $count = $count + 1\nif $count == {ordinal}\n'
    c+=f'set $injected = {gen}\nset $count = 0\n'
    c+=f'printf "OOM_INJECT ordinal={ordinal} generation=%u\\n", {gen}\n'
    c+='set $pc = *(unsigned long long*)$rsp\nset $rsp = $rsp + 8\nset $rax = 0\nend\nend\ncontinue\nend\n'
    c+=f'break *{addr("scheduler_spawn_oom_verified64")}\ncommands 2\nsilent\n'
    c+='set $i = 0\n'
    c+=f'while $i < 15\nif *(unsigned long long*)({addr("scheduler_frame_claim")}+$i*8) != 0\nquit 3\nend\nset $i = $i+1\nend\n'
    c+='set $i = 0\n'
    c+=f'while $i < 12\nif *(unsigned long long*)({addr("scheduler_tasks")}+256+$i*8) != 0\nquit 4\nend\nset $i = $i+1\nend\n'
    c+=f'printf "OOM_ROLLBACK generation=%u saved=%u free=%u baseline=%u spawned=%u completed=%u active=%u claim=%u selector=%u\\n", {gen}, '
    names=['scheduler_spawn_initial_generation','free_frame_count','scheduler_spawn_initial_free','scheduler_dynamic_spawn_count','scheduler_dynamic_completed_count']
    c+=', '.join(f'*(unsigned int*){addr(n)}' for n in names)
    c+=f', {active}, *(unsigned char*){addr("scheduler_frame_claim_active")}, *(unsigned char*){addr("elf_image_selector")}\ncontinue\nend\n'
    c+=f'break *{addr("scheduler_return64")} if *(unsigned char*){addr("scheduler_mode")} == 7\ncommands 3\nsilent\ndetach\nquit\nend\ncontinue\n'
    return c

def validate(serial,trace,ordinal,rip):
    injections=list(re.finditer(r'OOM_INJECT ordinal=(\d+) generation=(\d+)',trace))
    rollbacks=list(re.finditer(r'OOM_ROLLBACK generation=(\d+) saved=(\d+) free=(\d+) baseline=(\d+) spawned=(\d+) completed=(\d+) active=(\d+) claim=(\d+) selector=(\d+)',trace))
    receipts=list(REAP.finditer(serial));runs=list(re.finditer('REIST_X86_64_RING3_SHELL_RUN_OK',serial));done=list(re.finditer('OOM_OK',serial))
    if any(len(x)!=2 for x in (injections,rollbacks,receipts,runs,done)) or len(re.findall(r'CHILD_[A-Z]+_REAP_OK',serial))!=2:
        raise RuntimeError('missing exact injection/rollback/reap/retry witnesses')
    for i in range(2):
        if tuple(map(int,injections[i].groups()))!=(ordinal,40+i):raise RuntimeError('wrong injection')
        g,s,f,b,spawned,completed,a,c,sel=map(int,rollbacks[i].groups())
        if (g,s,spawned,completed,a,c,sel)!=(40+i,40+i,i,i,0,0,1) or not f==b>0:
            raise RuntimeError('rollback changed ownership/free baseline')
        if not (rollbacks[i-1].end() if i else -1)<injections[i].start()<injections[i].end()<=rollbacks[i].start():
            raise RuntimeError('rollback order')
        status,g,parent,q,address=(int(v,16) for v in receipts[i].groups())
        if (status,g,q,address)!=(91,41+i,0,rip) or parent not in (1,6,7):raise RuntimeError('terminal ownership')
        if not (done[i-1].end() if i else -1)<receipts[i].start()<receipts[i].end()<=runs[i].start()<runs[i].end()<=done[i].start():
            raise RuntimeError('retry receipt order')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):parser.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    result=dict(passed=False,cases=[]);start=time.monotonic()
    try:
        with (attempt/'build.log').open('wb') as out:
            build=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-OutputDirectory',attempt.relative_to(ROOT).as_posix(),'-OomCase','1'],cwd=ROOT,
                stdout=out,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if build.returncode:raise RuntimeError('build failed: '+str(attempt/'build.log'))
        native=attempt/'x86_64';image=native/'reist-x86_64-bootstrap.elf';s=symbols(image);rip=exit_address(native)
        result['mechanism_sha256']={n:hashlib.sha256((native/(n+'.o')).read_bytes()).hexdigest() for n in (*MECHANISMS,'frame_claim')}
        for ordinal in range(1,7):
            folder=attempt/str(ordinal);folder.mkdir()
            serial,trace=observed_boot(image,folder,injection(s,ordinal))
            validate(serial,trace,ordinal,rip)
            result['cases'].append(dict(ordinal=ordinal,passed=True))
            print('X86_64_SPAWN_OOM_CASE_OK ordinal='+str(ordinal),flush=True)
        result.update(passed=True,generations=12)
        print('X86_64_SPAWN_OOM_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,RuntimeError,ValueError,KeyError,subprocess.TimeoutExpired) as e:
        print('X86_64_SPAWN_OOM_RUNTIME_FAIL '+str(e));return 1
    finally:
        result['elapsed']=round(time.monotonic()-start,3)
        (attempt/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')

if __name__=='__main__':raise SystemExit(main())
