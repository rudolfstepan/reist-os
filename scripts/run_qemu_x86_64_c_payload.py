"""Bounded real multipage C execution; poison only new BSS before startup."""
from pathlib import Path
import argparse, hashlib, json, queue, re, shutil, subprocess, threading, time, uuid
import build_x86_64_c_payload as payload
from run_qemu_x86_64_boot import resolve_qemu, terminate_bounded, REQUIRED_MARKERS, FAILURES, SUCCESS

ROOT=Path(__file__).resolve().parents[1]
HIGH=payload.HIGH
MARKER='REIST_X86_64_C_PAYLOAD_PAGES_OK'


def layout(inner,outer):
    payload.verify_outer(inner,outer)
    c=payload.validate(inner);o=payload.elf(outer,32)
    s=c['sections'];symbols=c['symbols']
    for name,size,section in (('payload_bss',12000,'.bss'),('payload_data',9000,'.data'),('payload_ro',9000,'.rodata')):
        sym=symbols[name]
        payload.require(sym['index']==s[section]['index'] and sym['size']==size and
                        s[section]['address']+32<=sym['value'] and
                        sym['value']+size<=s[section]['address']+s[section]['size'],'probe symbol range')
    for name in payload.LAYOUT:payload.require(s[name]['size']>4096,'probe must cross every section page')
    ranges=[(s[n]['address']-HIGH,s[n]['size'],1 if n=='.text' else (1<<63)|(1 if n=='.rodata' else 3)) for n in payload.LAYOUT]
    bridge=o['sections']['.c_core_bridge']
    ranges.extend(((0x184000,bridge['size'],1),(0x1ff000,192,(1<<63)|3)))
    leaves={address:address|flags for start,size,flags in ranges for address in range(start,start+size,4096)}
    return c,{n:v['value']+HIGH for n,v in o['symbols'].items()},leaves


def commands(c,s,leaves):
    sections=c['sections'];bss=sections['.bss'];data=sections['.data']
    poison=c['symbols']['payload_bss']['value']-HIGH
    # GDB Python performs bounded bulk reads, avoiding thousands of remote RTTs.
    code=f'''python
import gdb, hashlib
inferior=gdb.selected_inferior()
def memory(address,size):return bytes(inferior.read_memory(address,size))
def word(address):return int.from_bytes(memory(address,8),'little')
def reg(name):return int(gdb.parse_and_eval('$'+name))
def need(ok,message):
    if not ok:raise gdb.GdbError(message)
def stop(address):
    gdb.execute('tbreak *'+hex(address))
    gdb.execute('continue')
    need(reg('rip')==address,'wrong observation PC')
stop({s['x86_64_bootstrap_start']-HIGH})
for offset in (0,4095,8192,11999):
    inferior.write_memory({poison}+offset,b'\\xa5')
    need(memory({poison}+offset,1)==b'\\xa5','poison did not reach BSS')
print('C_PAYLOAD_POISON count=4')
stop({s['x86_64_c_core_handoff64']})
need(not any(memory({bss['address']},{bss['size']})),'whole C BSS not initialized')
need(not any(memory({HIGH+0x1ff000},192)),'handoff not initialized')
print('C_PAYLOAD_ZERO bss={bss['size']} handoff=192')
expected={leaves!r}
def protections(phase):
    need(reg('cr0')&(1<<16) and reg('efer')&(1<<11),'WP/NXE missing')
    need(reg('cr3')=={s['pml4_table']-HIGH},'foreign root')
    need(word({s['pml4_table']})==0,'low identity alias remains')
    for address,value in {[(s['pml4_table']+511*8,(s['pdpt_table']-HIGH)|3),(s['pdpt_table']+510*8,(s['high_page_directory']-HIGH)|3),(s['high_page_directory'],(s['high_page_table']-HIGH)|3)]!r}:
        need(word(address)&~0x60==value,'high parent authority')
    for address in range(0x184000,0x200000,4096):
        need(word({s['high_page_table']}+(address//4096)*8)&~0x60==expected.get(address,0),'C leaf/gap mismatch at '+hex(address))
    for address in range(0x100000,0x200000,4096):
        need(word({s['direct_page_tables']}+(address//4096)*8)==0,'bootstrap direct-map alias')
    print('C_PAYLOAD_LAYOUT phase=%d pages={len(leaves)} gaps={124-len(leaves)} wp=1 nxe=1 direct=0'%phase)
protections(1)
'''
    for name in ('.text','.rodata','.data'):
        section=sections[name];digest=hashlib.sha256(section['data']).hexdigest()
        code+=f"need(hashlib.sha256(memory({section['address']},{section['size']})).hexdigest()=={digest!r},'loaded {name} bytes')\n"
    code+=f'''stop({s['x86_64_c_core_handoff64.verify_handoff_zero']})
need(not any(memory({data['address']},{data['size']})),'C data cleanup')
need(not any(memory({bss['address']},{bss['size']})),'C BSS cleanup')
need(not any(memory({HIGH+0x1ff000},192)),'C handoff cleanup')
print('C_PAYLOAD_CLEAN data={data['size']} bss={bss['size']} handoff=192')
protections(2)
gdb.execute('detach')
end
quit
'''
    return code


def validate(serial,trace,c,leaves):
    if len(serial)>262144 or len(trace)>65536:raise ValueError('evidence capacity')
    if any(m in serial for m in FAILURES):raise ValueError('guest failure')
    positions=[serial.find(m) for m in REQUIRED_MARKERS]
    if min(positions)<0 or positions!=sorted(set(positions)):raise ValueError('incomplete/out of order legacy proof')
    for m in REQUIRED_MARKERS:
        if serial.count(m)!=(2 if m=='REIST_X86_64_RING3_SHELL_RUN_OK' else 1):raise ValueError('legacy marker count')
    if serial.count(MARKER)!=1 or not serial.index('REIST_X86_64_EXCEPTION_RECOVERY_OK')<serial.index(MARKER)<serial.index('REIST_X86_64_C_CALLBACK_OK'):
        raise ValueError('C multipage execution witness')
    bss=c['sections']['.bss']['size'];data=c['sections']['.data']['size']
    def proof(phase):return f'C_PAYLOAD_LAYOUT phase={phase} pages={len(leaves)} gaps={124-len(leaves)} wp=1 nxe=1 direct=0'
    expected=['C_PAYLOAD_POISON count=4',f'C_PAYLOAD_ZERO bss={bss} handoff=192',proof(1),
              f'C_PAYLOAD_CLEAN data={data} bss={bss} handoff=192',proof(2)]
    actual=[line for line in trace.splitlines() if line.startswith('C_PAYLOAD_')]
    if actual!=expected:raise ValueError('exact initialization/protection/cleanup witnesses missing')


def capture(image,folder,code):
    prefix='set confirm off\nset pagination off\nset architecture i386:x86-64\ntarget remote 127.0.0.1:12490\n'
    script=folder/'observe.gdb';script.write_text(prefix+code,encoding='ascii')
    cmd=[str(resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m','128M','-smp','1',
         '-display','none','-monitor','none','-serial','stdio','-no-reboot','-no-shutdown','-kernel',str(image.resolve()),
         '-S','-gdb','tcp:127.0.0.1:12490']
    (folder/'command.json').write_text(json.dumps(cmd),encoding='utf-8')
    chunks=queue.Queue(maxsize=128);overflow=threading.Event();data=bytearray();debugger=None;step=0
    with (folder/'stderr.log').open('wb') as errors,(folder/'observer.log').open('wb') as observer:
        vm=subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,bufsize=0,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            debugger=subprocess.Popen([shutil.which('gdb') or 'gdb','-q','-nx','-batch','-x',str(script)],
                stdout=observer,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError:
            vm.stdin.close();terminate_bounded(vm);vm.stdout.close();raise
        def reader():
            while chunk:=vm.stdout.read(256):
                try:chunks.put_nowait(chunk)
                except queue.Full:overflow.set();return
        thread=threading.Thread(target=reader,daemon=True);thread.start();deadline=time.monotonic()+10
        try:
            while time.monotonic()<deadline:
                try:data.extend(chunks.get(timeout=.01))
                except queue.Empty:pass
                if overflow.is_set() or len(data)>262144:raise ValueError('serial capacity')
                serial=data.decode('ascii',errors='replace')
                requests=[('RING3_SHELL_READY',b'INFO\n'),('RING3_SHELL_INFO_OK',b'RUN\n'),('RING3_SHELL_RUN_OK',b'RUN\n')]
                if step<3 and requests[step][0] in serial:
                    vm.stdin.write(requests[step][1]);vm.stdin.flush();step+=1
                if step==3 and serial.count('REIST_X86_64_RING3_SHELL_RUN_OK')==2:
                    vm.stdin.write(b'EXIT\n');vm.stdin.flush();step+=1
                if SUCCESS in serial or any(m in serial for m in FAILURES) or vm.poll() is not None or debugger.poll() not in (None,0):break
        finally:
            vm.stdin.close();terminate_bounded(vm)
            try:debugger.wait(timeout=2)
            except subprocess.TimeoutExpired:terminate_bounded(debugger)
            thread.join(timeout=1)
            while not chunks.empty():data.extend(chunks.get_nowait())
            vm.stdout.close();(folder/'guest.log').write_bytes(data)
    if overflow.is_set() or len(data)>262144:raise ValueError('serial overflow')
    if debugger.returncode or step!=4:raise ValueError('incomplete debugger detach/guest dialogue')
    log=folder/'observer.log'
    with log.open('rb') as stream:trace=stream.read(65537)
    if len(trace)>65536:raise ValueError('observer capacity')
    return data.decode('ascii',errors='replace'),trace.decode('utf-8',errors='replace')


def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True)
    args=p.parse_args();base=args.evidence.resolve()
    if not base.is_relative_to(ROOT/'build/codex-agent'):p.error('evidence outside workspace')
    attempt=base/('attempt-'+uuid.uuid4().hex);attempt.mkdir(parents=True)
    started=time.monotonic();summary=dict(passed=False)
    try:
        inner=payload.read_bounded(args.image.parent/'reist-x86_64-c-core.elf');outer=payload.read_bounded(args.image)
        c,s,leaves=layout(inner,outer)
        serial,trace=capture(args.image,attempt,commands(c,s,leaves));validate(serial,trace,c,leaves)
        summary.update(passed=True,pages=len(leaves),gaps=124-len(leaves),sha256=hashlib.sha256(outer).hexdigest())
        print('C_PAYLOAD_RUNTIME_OK evidence='+str(attempt));return 0
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.TimeoutExpired) as exc:
        summary['error']=str(exc);print('C_PAYLOAD_RUNTIME_FAIL '+str(exc)+' evidence='+str(attempt));return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3)
        (attempt/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
