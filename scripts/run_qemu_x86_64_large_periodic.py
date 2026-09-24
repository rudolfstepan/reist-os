"""Large-image ownership oracle plus explicit periodic CPU evidence.

Legacy observer files remain unchanged. Every adaptation below names its exact
old fragment; missing or duplicated fragments fail before launching a guest.
"""
from pathlib import Path
import hashlib, inspect, json, struct
import native_cpu_trace as cpu_trace
from check_x86_64_wide_shell_media import clone
import run_qemu_x86_64_large_image as legacy

ROOT = Path(__file__).resolve().parents[1]
need = legacy.payload.require
changes = [
    ("for i in range(9)", "for i in range(13)"),
    ("+9*2320", "+13*2320"),
    ("('scheduler_tasks',16384)", "('scheduler_tasks',32768)"),
    ("('scheduler_fp_states',2048)", "('scheduler_fp_states',4096)"),
    ("('scheduler_table_frames',128)", "('scheduler_table_frames',256)"),
    ("('scheduler_cpu_budgets',128)", "('scheduler_cpu_budgets',256),('scheduler_cpu_windows',256)"),
    ("('scheduler_syscall_profiles',64)", "('scheduler_syscall_profiles',128)"),
    ("('process_run_plan',144)", "('process_run_plan',336)"),
    ("('process_run_generations',16)", "('process_run_generations',32)"),
    ("('scheduler_runqueue_entries',32)", "('scheduler_runqueue_entries',64)"),
    ("('scheduler_deadline_entries',64)", "('scheduler_deadline_entries',128)"),
    ("('scheduler_runqueue_membership',4)", "('scheduler_runqueue_membership',8)"),
    ("('scheduler_deadline_membership',4)", "('scheduler_deadline_membership',8)"),
    ("or ticks>32:", "or ticks>256:"),
    ("'rollback','fault','cancel')", "'rollback','fault','cancel','cpu','phase')"),
]
changes.append(("    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)",
                "    cpu_initial(t,slot)\n    if slot==0:root_phase(t,cpu_states[t[1]][1])\n    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)"))
changes += [
    ("            read_log.write(json.dumps(dict(begin=self.fn.__name__))+'\\n')",
     "            trace_drain()\n            if self.fn is finish and runs==1:trace_close()\n            read_log.write(json.dumps(dict(begin=self.fn.__name__))+'\\n')"),
    ("            read_log.write(json.dumps(dict(end=self.fn.__name__))+'\\n')",
     "            read_log.write(json.dumps(dict(end=self.fn.__name__))+'\\n')\n            if self.fn is boot and not trace_reader.started:trace_initialize()"),
    ("            read_log.write(json.dumps(dict(begin='release_end'))+'\\n')",
     "            trace_drain()\n            read_log.write(json.dumps(dict(begin='release_end'))+'\\n')"),
]
base = clone(legacy, changes, 'large_periodic_ownership')
transport = clone(legacy.transport, [
    ('capture_started+27 if service_cpu_budget', 'capture_started+357 if service_cpu_budget'),
    ('time.monotonic()-capture_started>30:', 'time.monotonic()-capture_started>360:'),
], 'large_periodic_transport')

CPU_OBSERVER = r'''
def root_phase(t,window):
    assert window[0]==100 and window[1]<1<<60 and not window[2] and not window[3]
    address=CONFIG['selection']+16;e=walk(t[2],address)
    assert e&7==7 and e&NX
    target=DM+(e&MASK)+(address&4095)
    assert mem(target,8)==bytes(8)
    origin=window[1]*10
    gdb.selected_inferior().write_memory(target,struct.pack('<Q',origin))
    assert mem(target,8)==struct.pack('<Q',origin)
    emit('phase',gen=t[1],origin_ms=origin,address=target)
cpu_states={}
def cpu_initial(t,slot):
    assert t[1] not in cpu_states and len(cpu_states)<8
    budget=struct.unpack('<4Q',mem(S['scheduler_cpu_budgets']+slot*32,32))
    window=struct.unpack('<4Q',mem(S['scheduler_cpu_windows']+slot*32,32))
    plan=mem(S['process_run_plan'],336)
    assert struct.unpack_from('<4I',plan)==(5,336,8,0)
    assert struct.unpack_from('<Q',plan,16+slot*32)[0]==(1 if slot<2 else 0)
    assert struct.unpack_from('<Q',plan,272+slot*8)[0]==100
    assert struct.unpack_from('<Q',plan,32+slot*32)[0]==32
    assert budget==(t[1],32,0,0) and window[0]==100 and window[2:]==(0,0)
    assert t[0]==2 and window[1]<1<<60
    cpu_states[t[1]]=(budget,window,slot)
class TraceLedger:
    def event(self,**event):
        gen=event['gen'];slot=event['slot'];now=event['now']
        b,w,owner=cpu_states[gen];assert owner==slot
        assert event['before']==list(b+w)
        index=(now-w[1])//100;used=(w[3] if index==w[2] else 0)+1
        assert now>b[3] and now>w[1] and index>=w[2] and w[3]<32
        budget=(gen,32,b[2]+1,now);window=(100,w[1],index,used)
        assert 1<=used<=32 and event['after']==list(budget+window)
        result=event['result'];assert result==(2 if used==32 else 1)
        emit('cpu',slot=slot,gen=gen,total=budget[2],index=index,used=used,result=result)
        cpu_states[gen]=(budget,window,slot)

def trace_full():pass

def trace_drain():
    if not trace_reader.started:return
    read_log.write(json.dumps(dict(begin='trace_drain'))+'\n')
    trace_reader.drain()
    read_log.write(json.dumps(dict(end='trace_drain'))+'\n')

def trace_initialize():
    read_log.write(json.dumps(dict(begin='trace_initialize'))+'\n')
    trace_reader.initialize()
    read_log.write(json.dumps(dict(end='trace_initialize'))+'\n')

def trace_close():
    read_log.write(json.dumps(dict(begin='trace_close'))+'\n')
    trace_reader.finish()
    read_log.write(json.dumps(dict(end='trace_close'))+'\n')

'''
base.OBSERVER += '\nfrom pathlib import Path\nimport hashlib\n'+inspect.getsource(cpu_trace.decode_trace_record)+'\n'+inspect.getsource(cpu_trace.CPUTraceReader)+CPU_OBSERVER+"""
trace_reader=CPUTraceReader(mem,S['native_cpu_trace'],S['native_cpu_trace_end'],TraceLedger(),
    starts,lambda:q(S['scheduler_last_tick']),Path(CONFIG['folder'])/'cpu-trace-v1.bin',gdb.write)
Hook('native_cpu_trace_after64.full',trace_full)
"""


def guest_receipts(serial):
    return [struct.unpack('<4I2Q',bytes.fromhex(row[1])) for row in legacy.process.REAP.finditer(serial)]


def replay(folder, serial, trace, count):
    rows = base.replay(folder, serial, trace, count)
    folder = Path(folder)
    config = json.loads((folder/'config.json').read_text())
    symbols = config['s']; case = config['case']
    raw = (folder/'reads.bin').read_bytes()
    reads = []; registers = {}; totals = {}; current = None; events=[]; states={}
    live=set();sequence=0;record_events=[];boot_zero=False
    address=symbols['native_cpu_trace']
    need(symbols['native_cpu_trace_end']-address==32+257*192,'exact buffered trace extent')
    for line in (folder/'reads.jsonl').read_text().splitlines():
        row = json.loads(line)
        if 'begin' in row:
            current = row['begin']; reads = []; registers = {}; events=[]
        elif 'address' in row:
            reads.append((row['address'], raw[row['offset']:row['offset']+row['bytes']]))
        elif 'register' in row:
            registers[row['register']] = row['value']
        elif 'event' in row:
            events.append(row['event'])
        elif 'end' in row:
            # Replay exact producer ring bytes before this lifecycle callback.
            # Never trust emitted CPU markers or the separately saved trace alone.
            def one(at,size):
                hits=[data for a,data in reads if a==at and len(data)==size]
                need(len(hits)==1,'unique buffered CPU raw read');return hits[0]
            full=[data for at,data in reads if at==address and len(data)==32+257*192]
            if full:
                need(current=='trace_initialize' and not boot_zero and len(full)==1 and not any(full[0]),'initial CPU trace zero')
                boot_zero=True
            headers=[data for at,data in reads if at==address and len(data)==32]
            expected=[]
            if headers:
                need(boot_zero and len(headers)==1,'one trace drain per callback')
                total,error,pending,reserved=struct.unpack('<4Q',headers[0])
                need(not (error or pending or reserved) and sequence<=total<=2048 and total-sequence<=256,'CPU ring header')
                if total>sequence:
                    observed=struct.unpack('<Q',one(symbols['scheduler_last_tick'],8))[0]
                    while sequence<total:
                        index=sequence&255;n=min(total-sequence,256-index)
                        chunk=one(address+32+index*192,n*192)
                        for offset in range(0,len(chunk),192):
                            e=cpu_trace.decode_trace_record(chunk[offset:offset+192],sequence+1)
                            gen=e['gen'];slot=e['slot'];now=e['now']
                            need(gen in live and gen in states and now<=observed,'actual live trace generation/time')
                            before,w,owner=states[gen];need(slot==owner and e['before']==list(before+w),'exact CPU pre-state continuity')
                            index_=(now-w[1])//100;used=(w[3] if index_==w[2] else 0)+1
                            need(now>before[3] and now>w[1] and index_>=w[2] and w[3]<32 and 1<=used<=32,'bounded monotonic CPU charge')
                            after=(gen,32,before[2]+1,now);window=(100,w[1],index_,used)
                            need(e['after']==list(after+window) and e['result']==(2 if used==32 else 1),'actual full before/after CPU transition')
                            expected.append(dict(kind='cpu',slot=slot,gen=gen,total=after[2],index=index_,used=used,result=e['result']))
                            states[gen]=(after,window,slot);totals[gen]=after[2];record_events.append(e);sequence+=1
            need([e for e in events if e['kind']=='cpu']==expected,'every CPU marker bound to actual ring read')
            for event in events:
                if event['kind']=='release':
                    need(event['gen'] in live,'live generation release');live.remove(event['gen'])
            if current!='start':
                current=None;continue

            phase=[e for e in events if e['kind']=='phase']
            starts=[e for e in events if e['kind']=='start']
            if starts:
                slot=starts[0]['slot'];gen=starts[0]['gen']
                def initial(address,size):
                    hits=[data for at,data in reads if at==address and len(data)==size]
                    need(len(hits)==1,'unique initial CPU record');return hits[0]
                b=struct.unpack('<4Q',initial(symbols['scheduler_cpu_budgets']+slot*32,32))
                w=struct.unpack('<4Q',initial(symbols['scheduler_cpu_windows']+slot*32,32))
                plan=initial(symbols['process_run_plan'],336)
                need(struct.unpack_from('<4I',plan)==(5,336,8,0),'initial periodic plan')
                need(struct.unpack_from('<Q',plan,16+slot*32)[0]==(1 if slot<2 else 0),'initial root/dynamic kind')
                need(struct.unpack_from('<Q',plan,272+slot*8)[0]==100 and
                     struct.unpack_from('<Q',plan,32+slot*32)[0]==32,'immutable CPU limits')
                need(b==(gen,32,0,0) and w[0]==100 and w[1]<1<<60 and w[2:]==(0,0),'actual zero-use generation bind')
                need(gen not in states and len(states)<8,'unique CPU generation')
                states[gen]=(b,w,slot);live.add(gen)
            if starts and starts[0]['slot']==0:
                need(len(phase)==1, 'one actual root epoch input')
                windows=[data for at,data in reads if at==symbols['scheduler_cpu_windows'] and len(data)==32]
                need(len(windows)==1, 'authoritative root window')
                w=struct.unpack('<4Q',windows[0]);need(w[0]==100 and w[1]<1<<60 and w[2:]==(0,0), 'fresh root window')
                task=next(data for at,data in reads if at==symbols['scheduler_tasks'] and len(data)==4096)
                t=struct.unpack('<512Q',task);va=config['selection']+16;table=t[2]
                for shift in (39,30,21,12):
                    addr=0xffff800000000000+table+((va>>shift)&511)*8
                    entry=next(data for at,data in reads if at==addr and len(data)==8)
                    entry=struct.unpack('<Q',entry)[0];need(entry&1 and (shift==12 or not entry&128),'root epoch mapping')
                    table=entry&0x3fffff000
                need(entry&7==7 and entry&(1<<63), 'private writable epoch input')
                target=0xffff800000000000+table+(va&4095)
                observations=[data for at,data in reads if at==target and len(data)==8]
                need(observations==[bytes(8),struct.pack('<Q',w[1]*10)], 'exact epoch publication')
                need(phase==[dict(kind='phase',gen=t[1],origin_ms=w[1]*10,address=target)], 'epoch event from actual window')
            else:need(not phase,'no foreign root epoch publication')
            current=None
    need(boot_zero and not live and len(states)==8,'all eight CPU generation binds and retirements')
    cpu_trace.validate_trace_records(trace,(folder/'cpu-trace-v1.bin').read_bytes(),record_events)
    for receipt in guest_receipts(serial):
        slot,gen,status,state,ticks,rip=receipt
        need(gen in states and states[gen][2]==slot and totals.get(gen,0)==ticks,'complete charges through final reap')
    normal = {4,8} | ({3,7} if case in (0,6) else set())
    need(all(32<totals.get(gen,0)<=256 for gen in normal), 'large service crosses lifetime quota')
    if case==4:
        need(all(totals.get(gen)==32 for gen in (3,7)), 'same-window exhaustion')
    return dict(ownership=rows, cpu=totals)


def capture(image, folder, case=0, oom=None):
    image,folder=Path(image),Path(folder);folder.mkdir(parents=True,exist_ok=False)
    c=legacy.payload.validate((image.parent/'reist-x86_64-c-core.elf').read_bytes())
    symbols=legacy.transport.symbols(image)
    fixture=next(image.parent.glob('programs-*'))
    hits=[line.split()[0] for line in (fixture/'program0.map').read_text().splitlines()
          if line.split() and line.split()[-1]=='reist_large_image_selection']
    need(len(hits)==1,'exact selector')
    from build_x86_64_large_image import prepare
    count=legacy.allocations(prepare((fixture/'program2.prg').read_bytes(),[]))
    code=base.observer(symbols,c,folder,case,oom,int(hits[0],16))
    serial,trace=transport.capture(image,folder,code,4096,service_cpu_budget=True)
    (folder/'serial.txt').write_text(serial);(folder/'trace.txt').write_text(trace)
    return replay(folder,serial,trace,count)
