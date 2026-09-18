"""One-image native console proof; no rebuilds or marker-only acceptance."""
from pathlib import Path
import argparse,inspect,json,re,struct,time,uuid
import run_qemu_x86_64_boot_programs as boot
import build_x86_64_boot_programs as producer
from run_qemu_x86_64_runtime_clock import once
ROOT=Path(__file__).resolve().parents[1]
NORMAL=b'N'+bytes(97+n%26 for n in range(64))
CASES=((0,4096),(0,8192),(1,4096),(2,4096),(3,4096),('peer-mask',4096),('legacy-mask',4096))

def base_validator():
    source=inspect.getsource(boot.validate)
    source=once(source,'ident=slot if run==0 else 3-slot;bad=case and ident==2',
                'ident=slot;bad=case in (1,2) and run==0 and ident==0')
    source=once(source,'else 40+ident,3 if bad else 4','else (65 if case==3 and run==0 and ident==0 else 61+ident),3 if bad else 4')
    # The image assignment differs; retain every old raw mapping/cleanup check.
    source=once(source,'(s if r==0 else 3-s)+3,(s if r==0 else 3-s)+2','s+3,s+2')
    ns=dict(vars(boot));exec(compile(source,'<console-original-boot-oracle>','exec'),ns)
    return ns['validate']

def inputs(case):return ((NORMAL,b'F',b'C',b'T')[case],NORMAL)

def validate_io(events,case):
    if not events or len(events)>512:raise ValueError('console raw event capacity')
    for run in (1,2):
        rows=[r for r in events if r['run']==run]
        if not rows or any(r['slot']!=0 or r['gen']!=(run-1)*4+1 for r in rows):raise ValueError('console exact owner generation')
        writes=bytearray();reads=bytearray();errors=set()
        for r in rows:
            op,fd,size,result=r['op'],r['fd'],r['size'],r['result']
            if op not in (15,20):raise ValueError('console operation')
            before=None if r['before'] is None else bytes.fromhex(r['before'])
            after=None if r['after'] is None else bytes.fromhex(r['after'])
            if result>0:
                if any(r['unused']) or fd!=(op==20) or not 0<result<=size<=64 or before is None or after is None:
                    raise ValueError('console successful admission')
                if len(before)!=size or len(after)!=size:raise ValueError('console complete bytes')
                if op==20:
                    if before!=after:raise ValueError('console immutable write source')
                    writes.extend(before[:result])
                else:
                    if before[result:]!=after[result:]:raise ValueError('console untouched read tail')
                    reads.extend(after[:result])
            else:
                if before!=after:raise ValueError('console negative buffer mutation')
                if result not in (0,-9,-11,-14,-22):raise ValueError('console unexpected error')
                if result==0 and size:raise ValueError('console false EOF')
                expected=-22 if any(r['unused']) else -9 if fd!=(op==20) else -22 if size>64 else 0 if not size else -14 if before is None or op==15 and r['pointer']==0x400000 else -11
                if result!=expected:raise ValueError('console exact admission errno')
                errors.add(result)
        if not {0,-9,-14,-22}<=errors:raise ValueError('console negative runtime coverage')
        mode=case if run==1 else 0;expected=inputs(mode)[0]
        if bytes(reads)!=expected:raise ValueError('console exact UART receive bytes')
        wanted=b'NATIVE_CONSOLE_READY\n'+(NORMAL[1:] if mode==0 else b'')
        if bytes(writes)!=wanted:raise ValueError('console exact UART transmit bytes')
        if mode==3 and -11 not in errors:raise ValueError('console actual empty UART')
    if any(r['run'] not in (1,2) for r in events):raise ValueError('console unexpected run')

def validate(serial,trace,case,ram):
    rows=base_validator()(serial,trace,case,ram)
    events=[json.loads(m) for m in re.findall(r'^CONSOLE_IO (.+)$',trace,re.M)]
    if trace.count('CONSOLE_IO ')!=len(events):raise ValueError('console malformed raw event')
    validate_io(events,case)
    return rows

def image_config(image):
    core_raw=boot.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    core=boot.payload.validate(core_raw);boot.payload.verify_outer(core_raw,boot.payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    attempts=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(catalog)!=4*36896 or len(attempts)!=1:raise ValueError('console exact producer')
    for n in range(4):
        raw=(attempts[0]/f'program{n}.prg').read_bytes()
        if producer.prepare(raw,[f'program{n}.prg',str(n)])!=catalog[n*36896:(n+1)*36896]:
            raise ValueError('console mapped executable binding')
    return boot.symbols(image),core

def memory_adapter(code,c,ram):
    state=c['symbols']['native_memory_state']['value']
    for base in (f'{state}+64',f'{state}+64+524288'):
        code=once(code,f'mem({base},524288)',
                  f'(mem({base},262144)+mem({base}+262144,262144))')
    anchor=f'            assert above==({ram}>=4096)\n'
    # Same stopped map checkpoint; no ownership/allocation claim or guest write.
    proof=(f'            region=next((i for i in range(2048,min(8192,({ram}+1024)//2)) '
           "if usable[i*64:(i+1)*64]==b'\\xff'*64 and entries[i]&~0x60==(1<<63)|(i<<21)|0x83),None)\n"
           '            assert region is not None\n'
           '            assert len(mem(0xffff800000000000+(region<<21),32768))==32768\n')
    return once(code,anchor,anchor+proof)

def observer(s,c,folder,ram):
    code=boot.observer(s,c,folder/'frame-trace.log',ram)
    code=memory_adapter(code,c,ram)
    code=once(code,'ident=slot if run==1 else 3-slot','ident=slot')
    extra='''python
import json
CONSOLE_SYMBOLS=SYMBOLS_VALUE
console_pending=None
console_events=0
def console_buffer(address,size):
    if not 0<size<=64:return None
    # No invalid user pointer is dereferenced by the observer. Probe mappings
    # only within this profile's image/stack or native private heap window.
    if not (0x400000<=address and address+size<=0x409000 or
            0x100000000<=address and address+size<=0x120000000):return None
    try:return mem(address,size).hex()
    except gdb.MemoryError:return None
class ConsoleResult(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(CONSOLE_SYMBOLS['process_run_resume64']),internal=True);self.enabled=False
    def stop(self):
        global console_pending,console_events
        try:
            assert console_pending is not None and not reg('eflags')&512
            row=console_pending;result=reg('rax');row['result']=result if result<1<<63 else result-(1<<64)
            row['after']=console_buffer(row['pointer'],row['size'])
            console_events+=1;assert console_events<=512
            gdb.write('CONSOLE_IO '+json.dumps(row,sort_keys=True)+'\\n')
            console_pending=None;self.enabled=False
        except Exception as error:
            gdb.write('CONSOLE_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 61')
        return False
console_result=ConsoleResult()
class ConsoleEntry(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex(CONSOLE_SYMBOLS['native_console_syscall64']),internal=True)
    def stop(self):
        global console_pending
        try:
            assert console_pending is None and not reg('eflags')&512
            s=CONSOLE_SYMBOLS
            slot=struct.unpack('<I',mem(s['scheduler_current_slot'],4))[0]
            task=struct.unpack('<32Q',mem(s['scheduler_tasks']+slot*256,256))
            run=struct.unpack('<I',mem(s['process_run_generation'],4))[0]//4
            assert slot==0 and run in (1,2) and task[0]==2 and task[1]==(run-1)*4+1
            assert task[2]==reg('cr3') and reg('r12')==s['scheduler_tasks']
            op=u64(s['syscall_rax']);assert op in (15,20)
            profile=struct.unpack('<2Q',mem(s['scheduler_syscall_profiles'],16))
            assert profile[0]==task[1] and profile[1]&(1<<op)
            address=u64(s['syscall_rsi']);size=u64(s['syscall_rdx'])
            console_pending=dict(run=run,slot=slot,gen=task[1],op=op,fd=u64(s['syscall_rdi']),pointer=address,size=size,
                unused=[u64(s[name]) for name in ('syscall_r10','syscall_r8','syscall_r9')],before=console_buffer(address,size))
            console_result.enabled=True
        except Exception as error:
            gdb.write('CONSOLE_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 62')
        return False
ConsoleEntry()
# Bind the transport's stop scopes to these actual observer callbacks.
Hook=ConsoleEntry
ReleaseEnd=ConsoleResult
end
continue
'''.replace('SYMBOLS_VALUE',repr(s))
    if not code.endswith('continue\n'):raise ValueError('console observer continuation')
    return code[:-len('continue\n')]+extra

def rejection_observer(s,c,folder,kind):
    code=observer(s,c,folder,4096)
    state=c['symbols']['native_memory_state']['value']
    extra=f'''python
class ConsoleRejectResult(gdb.FinishBreakpoint):
    def __init__(self,pointer,before):
        super().__init__(internal=True);self.pointer=pointer;self.before=before
    def stop(self):
        try:
            assert reg('rax')==0 and struct.unpack('<I',mem({state}+4,4))[0]==self.before
            assert not any(mem({s['scheduler_tasks']},1024))
            gdb.write('CONSOLE_ADMISSION_REJECT kind={kind} free=%d zero=1\\n'%self.before)
            gdb.execute('detach');gdb.execute('quit')
        except Exception as error:
            gdb.write('CONSOLE_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 63')
        return False
class ConsoleReject(gdb.Breakpoint):
    def __init__(self):super().__init__('*'+hex({s['process_run_admit64']}),internal=True)
    def stop(self):
        try:
            p=reg('rdi');raw=mem(p,144)
            assert struct.unpack_from('<4I',raw)==(2,144,4,0)
            offset,data=({56},struct.pack('<Q',struct.unpack_from('<Q',raw,56)[0]|(1<<15))) if {kind!r}=='peer-mask' else (0,struct.pack('<I',1))
            gdb.selected_inferior().write_memory(p+offset,data)
            assert mem(p+offset,len(data))==data
            ConsoleRejectResult(p,struct.unpack('<I',mem({state}+4,4))[0]);self.enabled=False
        except Exception as error:
            gdb.write('CONSOLE_OBSERVER_FAIL '+repr(error)+'\\n');gdb.execute('quit 64')
        return False
ConsoleReject()
end
continue
'''
    return code[:-len('continue\n')]+extra

def validate_rejection(serial,trace,kind):
    if serial.count('REIST_X86_64_C_KERNEL_CONTROL_ERROR')!=1 or 'PROCESS_REAP_OK' in serial or boot.process.SUCCESS in serial:
        raise ValueError('console rejected before native effects')
    if len(re.findall(r'^CONSOLE_ADMISSION_REJECT kind='+re.escape(kind)+r' free=\d+ zero=1$',trace,re.M))!=1:
        raise ValueError('console exact rejected descriptor witness')
    if 'CONSOLE_IO ' in trace or 'CONSOLE_OBSERVER_FAIL' in trace:raise ValueError('console unauthorized effects')
    boot.validate_preemption(trace)

def main():
    from verify_x86_64_console import source_binding,prior_gates,BASE,IMAGE,need,link
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    image=args.image.resolve();base=args.evidence.resolve();f=source_binding();prior_gates(f,9)
    need(image==IMAGE and base==BASE/'guests' and not list(base.glob('attempt-*')),'console fixed one matrix')
    s,c=image_config(image);folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,closed=False,candidate=f['candidate'],image=link(image),cases=[],guest_elapsed=0.0)
    started=time.monotonic()
    try:
        for case,ram in CASES:
            source_binding();need(summary['guest_elapsed']+20<=140,'console finite reserve')
            target=folder/f'{case}-{ram}';target.mkdir();begin=time.monotonic()
            row=dict(case=case,ram=ram,passed=False,folder=target.relative_to(ROOT).as_posix());summary['cases'].append(row)
            try:
                negative=isinstance(case,str)
                code=rejection_observer(s,c,target,case) if negative else observer(s,c,target,ram)
                options={} if negative else dict(console_input=inputs(case))
                serial,trace=boot.capture(image,target,code,ram,diagnostic_metrics=True,binary_memory='equivalence',**options)
                if negative:validate_rejection(serial,trace,case)
                else:validate(serial,trace,case,ram)
                need(link(image)==summary['image'],'console same immutable image');row['passed']=True
            finally:
                row['elapsed']=time.monotonic()-begin;summary['guest_elapsed']+=row['elapsed']
            need(row['elapsed']<=20,'console guest including cleanup');print('CONSOLE_GUEST_OK',case,ram,round(row['elapsed'],3),flush=True)
        need(len(summary['cases'])==7 and time.monotonic()-started<=180,'console full matrix');summary['passed']=True;return 0
    except Exception as error:
        summary['error']=str(error);print('CONSOLE_FAIL',error,flush=True);return 1
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-started)
        with (folder/'summary.json').open('x') as out:json.dump(summary,out,indent=2)
if __name__=='__main__':raise SystemExit(main())
