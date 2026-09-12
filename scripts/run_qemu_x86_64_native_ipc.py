"""Bounded Ring3 shared-IPC proof, using the unchanged process/frame oracle."""
from pathlib import Path
import argparse, collections, hashlib, json, queue, re, shutil, struct, subprocess, threading, time, uuid
import run_qemu_x86_64_process_run as process
import build_x86_64_c_payload as payload
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, FAILURES, REQUIRED_MARKERS
from run_qemu_x86_64_spawn_oom import symbols
ROOT=Path(__file__).resolve().parents[1]


def validate(serial,case):
    if case not in range(4) or any(m in serial for m in FAILURES):raise ValueError('native IPC guest failed')
    common=[m for m in REQUIRED_MARKERS if 'SHELL' not in m]+[process.SUCCESS]
    positions=[serial.find(m) for m in common]
    if any(serial.count(m)!=1 for m in common) or positions!=sorted(positions):raise ValueError('native IPC kernel progress')
    receipts=list(process.REAP.finditer(serial));ends=list(re.finditer(process.DONE,serial));rows=[]
    if len(receipts)!=8 or serial.count('PROCESS_REAP_OK')!=8 or len(ends)!=2:raise ValueError('native IPC receipt count')
    for run in range(2):
        seen=set()
        for m in receipts[4*run:4*run+4]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]))
            if slot not in range(4) or slot in seen or gen!=4*run+slot+1:raise ValueError('native IPC generation')
            seen.add(slot);fault=slot==0 and case in (1,3);quota=32
            if (status,state)!=((134 if case==1 else 256) if fault else 0xc100+slot,3 if fault else 4):
                raise ValueError('native IPC task outcome '+str((slot,gen,hex(status),state)))
            if ticks>quota or fault and case==3 and ticks!=quota or not 0x400000<=rip<0x408000:
                raise ValueError('native IPC CPU/instruction bounds')
            if not (ends[run-1].end() if run else -1)<m.start()<m.end()<=ends[run].start():
                raise ValueError('native IPC completion ordering')
            rows.append(dict(slot=slot,generation=gen,status=status,state=state,ticks=ticks,rip=rip))
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('native IPC caller continuation')
    return rows


def observer_commands(s,c,log):
    code=process.observer_commands(s,log)
    native={n:c['symbols'][n] for n in ('clients','pending','ipc_capability_records')}
    if [native[n]['size'] for n in native] != [432,864,2048]:raise ValueError('native IPC object layout drift')
    client=native['clients']['value'];pending=native['pending']['value'];caps=native['ipc_capability_records']['value']
    fence=''
    for base,stride in ((client,108),(pending,216)):
        fence+=f'set $j=0\nwhile $j<{stride}\nif *(unsigned char*)({base:#x}+$slot*{stride}+$j)!=0\nquit 21\nend\nset $j=$j+1\nend\n'
    fence+=f'set $j=0\nwhile $j<64\nset $cap={caps:#x}+$j*32\n'
    fence+='if *(unsigned char*)$cap && *(unsigned int*)($cap+16)==*(unsigned long long*)($task+8) && *(unsigned int*)($cap+20)==*(unsigned long long*)($task+8)\nquit 22\nend\nset $j=$j+1\nend\n'
    fence+='printf "NATIVE_IPC_FENCE slot=%u gen=%u\\n",$slot,*(unsigned long long*)($task+8)\n'
    needle='printf "PROCESS_FENCE_OK'
    if code.count(needle)!=1 or not code.endswith('continue\n'):raise ValueError('process observer template drift')
    code=code.replace(needle,fence+needle)
    code=code[:-len('continue\n')]
    code+='python\nimport gdb,struct\n'
    code+=f'''def reg(n): return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def mem(a,n): return bytes(gdb.selected_inferior().read_memory(a,n))
def u64(a): return struct.unpack('<Q',mem(a,8))[0]
class IPCWatch(gdb.Breakpoint):
    def __init__(self,address,kind):
        super().__init__('*'+hex(address),internal=True)
        self.kind=kind;self.count=0
    def stop(self):
        self.count+=1
        try:
            assert self.count<=64 and not reg('eflags')&512
            task=reg('r12');slot=(task-{s['scheduler_tasks']})//256
            assert 0<=slot<4 and task=={s['scheduler_tasks']}+slot*256
            state,gen,root=struct.unpack('<3Q',mem(task,24))
            assert gen>0 and gen==struct.unpack('<I',mem({s['process_run_generations']}+slot*4,4))[0]
            if self.kind in ('BLOCK','READY'):
                data=mem({pending}+slot*216,216)
                nr,a0,a1,a2,a3,result,deadline,ready=struct.unpack('<5Qq2Q',data[:64])
                pgen,pstate=struct.unpack('<2I',data[208:216])
                assert pgen==gen and nr in (50,51,53,54) and 0<deadline<256 and a0<=0xffffffff
                if self.kind=='BLOCK':
                    assert state==2 and pstate==1 and result==-4095 and not ready
                    assert data[:208]==mem(reg('r13'),208)
                    assert deadline>struct.unpack('<I',mem({s['scheduler_last_tick']},4))[0]
                else:
                    assert state==6 and pstate==2 and result in (0,-32,-110)
                    tick,qgen,qslot=struct.unpack('<QIB',mem(reg('r14'),13))
                    assert (tick,qgen,qslot)==(deadline,gen,slot)
                gdb.write('NATIVE_IPC_'+self.kind+' slot=%d gen=%d nr=%d deadline=%d result=%d\\n'%(slot,gen,nr,deadline,result))
            else:
                request=mem(reg('r13'),208)
                nr,destination=struct.unpack_from('<Q',request)[0],struct.unpack_from('<Q',request,16)[0]
                assert state==2 and root==reg('cr3') and nr in (51,54)
                assert struct.unpack_from('<q',request,40)[0]==0
                assert mem(destination,140)==request[64:204]
                assert struct.unpack_from('<3I',request,64)==(1,140,4)
                gdb.write('NATIVE_IPC_COPYOUT slot=%d gen=%d bytes=140 cr3=1\\n'%(slot,gen))
        except Exception as e:
            gdb.write('NATIVE_IPC_OBSERVER_FAIL '+str(e)+'\\n')
            gdb.execute('quit 23')
        return False
IPCWatch({s['process_ipc_syscall64.block']},'BLOCK')
IPCWatch({s['process_ipc_ready64.found']},'READY')
IPCWatch({s['process_ipc_copyout64.message_written']},'COPYOUT')
end
continue
'''
    return code


def validate_trace(trace,rows,case):
    if 'NATIVE_IPC_OBSERVER_FAIL' in trace:raise ValueError('native IPC observer failure')
    process.validate_trace(trace,rows)
    validate_ipc_trace(trace,rows,case)


def validate_ipc_trace(trace,rows,case):
    fences=re.findall(r'NATIVE_IPC_FENCE slot=(\d+) gen=(\d+)',trace)
    if [tuple(map(int,x)) for x in fences]!=[(r['slot'],r['generation']) for r in rows]:raise ValueError('IPC fence before frame release')
    blocks=re.findall(r'NATIVE_IPC_BLOCK slot=(\d+) gen=(\d+) nr=(\d+) deadline=(\d+) result=(-?\d+)',trace)
    ready=re.findall(r'NATIVE_IPC_READY slot=(\d+) gen=(\d+) nr=(\d+) deadline=(\d+) result=(-?\d+)',trace)
    for label,records in (('FENCE',fences),('BLOCK',blocks),('READY',ready)):
        if trace.count('NATIVE_IPC_'+label)!=len(records):raise ValueError('malformed IPC observation')
    if not blocks or len(blocks)>64 or len(ready)!=len(blocks):raise ValueError('IPC wait completion count')
    if collections.Counter(b[:4] for b in blocks)!=collections.Counter(r[:4] for r in ready) or any(b[4]!='-4095' for b in blocks):raise ValueError('IPC exact wait lifetime')
    live=set()
    for event in re.finditer(r'NATIVE_IPC_(BLOCK|READY) slot=(\d+) gen=(\d+) nr=(\d+) deadline=(\d+) result=(-?\d+)',trace):
        key=event.groups()[1:5]
        if event[1]=='BLOCK':
            if key in live:raise ValueError('duplicate outstanding IPC wait')
            live.add(key)
        else:
            if key not in live or event[6] not in ('0','-32','-110'):raise ValueError('IPC completion before wait')
            if event[4]=='50' and event[6]!='0':raise ValueError('backpressure send not completed')
            live.remove(key)
    for gen in (1,3,5,7):
        if not any(int(b[1])==gen and b[2]=='50' for b in blocks):raise ValueError('missing backpressure sleep')
        result='-32' if case==2 and gen in (1,5) else '-110'
        if not any(int(r[1])==gen and r[2]=='54' and r[4]==result for r in ready):raise ValueError('missing deadline/release result')
    copies=re.findall(r'NATIVE_IPC_COPYOUT slot=(\d+) gen=(\d+) bytes=140 cr3=1',trace)
    if len(copies)!=28 or trace.count('NATIVE_IPC_COPYOUT')!=28:raise ValueError('IPC actual copied-message count')
    owners={(r['slot'],r['generation']) for r in rows}
    if any(tuple(map(int,c)) not in owners for c in copies):raise ValueError('IPC wrong copyout owner')
    for row in rows:
        if sum(int(g)==row['generation'] for _,g in copies)!=(5 if row['slot']&1 else 2):raise ValueError('IPC independent pair routing')


def capture(image,folder,code):
    script=folder/'observe.gdb'
    script.write_text('set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12491\n'+code,encoding='ascii')
    command=[str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m','128M','-smp','1',
             '-display','none','-monitor','none','-serial','stdio','-no-reboot','-no-shutdown','-kernel',str(image.resolve()),'-S','-gdb','tcp:127.0.0.1:12491']
    (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
    output=queue.Queue(maxsize=128);overflow=threading.Event();data=bytearray();debugger=None
    with (folder/'stderr.log').open('wb') as errors,(folder/'observer.log').open('wb') as observer:
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,bufsize=0,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],stdout=observer,stderr=subprocess.STDOUT,
                                      creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError:
            vm.stdin.close();terminate_bounded(vm);vm.stdout.close();raise
        def reader():
            while chunk:=vm.stdout.read(256):
                try:output.put_nowait(chunk)
                except queue.Full:overflow.set();return
        thread=threading.Thread(target=reader,daemon=True);thread.start();deadline=time.monotonic()+10
        try:
            while time.monotonic()<deadline:
                try:data.extend(output.get(timeout=.01))
                except queue.Empty:pass
                if overflow.is_set() or len(data)>262144:raise ValueError('IPC serial capacity')
                serial=data.decode('ascii',errors='replace')
                if process.SUCCESS in serial or any(m in serial for m in FAILURES) or vm.poll() is not None or debugger.poll() not in (None,0):break
        finally:
            vm.stdin.close();terminate_bounded(vm)
            try:debugger.wait(timeout=2)
            except subprocess.TimeoutExpired:terminate_bounded(debugger)
            thread.join(timeout=1)
            while not output.empty():data.extend(output.get_nowait())
            vm.stdout.close();(folder/'guest.log').write_bytes(data)
    if overflow.is_set() or len(data)>262144 or debugger.returncode:raise ValueError('IPC capture/detach failure')
    for name in ('observer.log','frame-trace.log'):
        if (folder/name).stat().st_size>65536:raise ValueError('IPC observer capacity')
    return data.decode('ascii',errors='replace'),(folder/'frame-trace.log').read_text(encoding='utf-8')


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);args=p.parse_args()
    base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True);started=time.monotonic()
    summary=dict(passed=False,cases=[]);expected=None
    try:
        for case in range(4):
            folder=attempt/str(case);folder.mkdir()
            cmd=['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeProcesses','-NativeIPC',
                 '-NativeIPCCase',str(case),'-OutputDirectory',folder.relative_to(ROOT).as_posix()]
            with (folder/'build.log').open('wb') as log:
                r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if r.returncode:raise ValueError('IPC build failed: '+str(folder/'build.log'))
            image=folder/'x86_64/reist-x86_64-bootstrap.elf';inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
            c=payload.validate(inner);payload.verify_outer(inner,payload.read_bounded(image))
            names=('cooperative_scheduler','timer_interrupt','bootstrap_core','identity_core','queue_core','context_core','cpu_budget',
                   'syscall_profile','task_frames','fp_context','user_fault','exceptions','user_access','native_ipc_pool','native_ipc','native_ipc_integrity','native_ipc_memory')
            hashes={n:hashlib.sha256((image.parent/(n+'.o')).read_bytes()).hexdigest() for n in names}
            if expected is not None and hashes!=expected:raise ValueError('IPC kernel changed across user fixtures')
            expected=hashes
            serial,trace=capture(image,folder,observer_commands(symbols(image),c,folder/'frame-trace.log'))
            rows=validate(serial,case);validate_trace(trace,rows,case)
            summary['cases'].append(dict(case=case,tasks=rows));print('NATIVE_IPC_CASE_OK case='+str(case),flush=True)
        summary.update(passed=True,mechanisms=expected)
        print('NATIVE_IPC_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,ValueError,RuntimeError,KeyError,subprocess.TimeoutExpired) as exc:
        summary['error']=str(exc);print('NATIVE_IPC_RUNTIME_FAIL '+str(exc)+' evidence='+str(attempt));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
