"""Bounded normal-shell qualification; one immutable image, eighteen cases.

The feeder acknowledges actual kernel RX records, not echoed serial text.
Existing captures remain unchanged; the local capture adapter binds its exact
source transformations and uses the existing 45s PIO/3s cleanup boundary.
"""
from pathlib import Path
import hashlib,inspect,json,re,struct,time,types,textwrap
import run_qemu_x86_64_boot_programs as boot
import run_qemu_x86_64_session_admission as admission
import run_qemu_x86_64_file_launch as file
import native_cpu_trace
from run_qemu_x86_64_runtime_clock import once

ROOT=Path(__file__).resolve().parents[1]
BANNER='REIST OS userspace shell\n'
HEALTHY=((0,b'cd /\npwd\npath\nboot\nhistory\nexit\n'),)
CASES=tuple((n,n if n<5 else 2,8192 if n==5 else 4096) for n in range(18))


def pio_record_decode(raw,sequence,run):
    if type(raw) is not bytes or len(raw)!=384 or type(sequence) is not int or not 1<=sequence<=2048 or type(run) is not int or run not in (1,2):
        raise ValueError('PIO record extent/sequence/run')
    version,denied,index,slot,gen,entered,now,result,reserved=struct.unpack_from('<2I7Q',raw)
    before_flags,after_flags,before_mode,after_mode=struct.unpack_from('<4Q',raw,352)
    if (version,denied,index,reserved)!=(1,0,sequence,0) or slot>=8 or not 0<gen<1<<31 or not 0<=entered<=now<1<<60:
        raise ValueError('PIO record header/identity/time')
    if before_flags&512 or after_flags&512 or (before_mode,after_mode)!=(8,8):raise ValueError('PIO record IF/mode')
    args=list(struct.unpack_from('<6Q',raw,64))
    call=dict(run=run,slot=slot,gen=gen,op=113,args=args,pointer=args[1],size=64,before=raw[112:176].hex(),
              fd=args[0],unused=args[3:],entered=entered*10,profile_denied=False,family_before=None,
              authority=None,terminal_before=raw[240:264].hex())
    reply=dict(call,result=result-(1<<64) if result>>63 else result,now=now*10,after=raw[176:240].hex(),
               terminal=raw[264:288].hex(),pio=raw[288:352].hex(),family=None)
    return call,reply


class PioCallReader:
    """Private non-authoritative records; no writes/acknowledgements to target."""
    def __init__(self,read,address,starts,clock,snapshot,emit,run):
        self.read=read;self.address=address;self.starts=starts;self.clock=clock
        self.snapshot=snapshot;self.emit=emit;self.run=run;self.sequence=0;self.await_reset=False

    def initialize(self):
        raw=self.read(self.address,12320)
        if len(raw)!=12320 or any(raw):raise ValueError('PIO capture initial zero')

    def drain(self):
        header=self.read(self.address,32)
        if len(header)!=32:raise ValueError('PIO capture header extent')
        total,error,pending,reserved=struct.unpack('<4Q',header)
        if self.await_reset:
            if any(header):raise ValueError('PIO capture reset boundary')
            self.sequence=0;self.await_reset=False;return
        if error or pending or reserved or not self.sequence<=total<=2048 or total-self.sequence>32:
            raise ValueError('PIO capture error/incomplete/gap')
        if total==self.sequence:return
        previous=self.sequence;records=[];cursor=previous
        for _ in range(2):
            if cursor==total:break
            index=cursor&31;count=min(total-cursor,32-index)
            part=self.read(self.address+32+index*384,count*384)
            if len(part)!=count*384:raise ValueError('PIO capture records extent')
            records.append(part);cursor+=count
        if cursor!=total:raise ValueError('PIO capture complete ring read')
        chunk=b''.join(records);decoded=[];run=self.run();now=self.clock()
        for offset in range(0,len(chunk),384):
            call,reply=pio_record_decode(chunk[offset:offset+384],previous+offset//384+1,run)
            owner=self.starts.get(call['gen'])
            if not owner or not owner['live'] or owner['slot']!=call['slot'] or reply['now']>now*10:
                raise ValueError('PIO capture live owner/clock')
            decoded.append((call,reply))
        self.emit('pio_calls',run=run,previous=previous,raw=self.snapshot(header+chunk))
        for call,reply in decoded:
            self.emit('call',**call);self.emit('return',**reply)
        self.sequence=total

    def finish_run(self):
        self.drain()
        if not self.sequence or self.await_reset:raise ValueError('PIO capture end boundary')
        self.emit('pio_calls_end',run=self.run(),total=self.sequence)
        self.await_reset=True

def input_plan(case):
    if type(case) is not int or case not in range(18):raise ValueError('session case')
    first=HEALTHY
    if case==6:
        first=((5000,b'pwd\n'),(6000,b'boot\n'),(7000,b'boot\n'),
               (8000,b'boot\n'),(9000,b'boot\nhistory\nexit\n'))
    elif case in range(7,12):first=((0,b'boot\nboot\nhelp\nexit\n'),)
    elif case in (12,13,14):first=((0,b'boot '+{12:b'u',13:b'q',14:b'c'}[case]+b'\nhelp\nexit\n'),)
    elif case==15:first=((0,b'boot\n'),)
    elif case==16:first=((0,b'boot\nboot\nboot\nboot\nhelp\nhistory\nexit\n'),)
    elif case==17:first=((0,b'boot\nboot\nhelp\nexit\n'),)
    return first,HEALTHY

def admitted_plan(value):
    if type(value) is not tuple or value not in tuple(input_plan(n) for n in range(18)):
        raise ValueError('session exact fixed input plan')
    # bool/int equality must not admit forged schedules.
    if any(type(run) is not tuple or any(type(t) is not int or type(raw) is not bytes for t,raw in run) for run in value):
        raise ValueError('session input types')
    return value

class SessionFeeder:
    """Fixed 2-run plans, <=64 chunks; no send until exact previous RX ack."""
    def __init__(self,plan):
        self.plan=admitted_plan(plan)
        self.payload=tuple(b''.join(raw for _,raw in run) for run in self.plan)
        self.offsets=[0,0];self.sent=[];self.chunks=[];self.trace=''
        self.calls=0;self.elapsed=0;self.ready=0
        self.roots={};self.received=[bytearray(),bytearray()];self.written=[bytearray(),bytearray()]
        self.clocks={};self.rows=0;self.prompt_floor=[0,0]

    def pump(self,serial,trace,write,elapsed):
        self.calls+=1
        if self.calls>4096 or not self.elapsed<=elapsed<42:raise ValueError('session feeder deadline/capacity')
        self.elapsed=elapsed
        if len(trace)>8*1024*1024:raise ValueError('session feeder trace capacity')
        complete=trace[:trace.rfind('\n')+1]
        if not complete.startswith(self.trace):raise ValueError('session feeder stale trace')
        # Only complete newly appended rows are decoded. The full prior byte
        # prefix must still match, and every bound is cumulative across polls.
        appended=complete[len(self.trace):];self.trace=complete
        roots=self.roots;received=self.received;written=self.written
        clocks=self.clocks;rows=self.rows;prompt_floor=self.prompt_floor
        for line in appended.splitlines():
            if line.startswith('SHELL_SESSION '):
                row=json.loads(line[14:])
                if row['kind']=='start' and row['slot']==0:
                    run=row['run']
                    if type(run) is not int or run!=len(roots)+1 or run>2 or row['gen'] in [r['gen'] for r in roots.values()]:
                        raise ValueError('session feeder root order')
                    if type(row['gen']) is not int or not 0<row['gen']<1<<31 or type(row['now']) is not int or row['now']<0:
                        raise ValueError('session feeder root identity/clock')
                    roots[run]=row;clocks[run]=row['now']
            if not line.startswith('CONSOLE_IO '):continue
            row=json.loads(line[11:]);rows+=1
            if rows>8192:raise ValueError('session feeder IO capacity')
            run=row['run'];size=row['size'];result=row['result']
            if (run not in roots or type(row['now']) is not int or row['now']<clocks[run] or
                row['op'] not in (15,20) or row['fd']!=int(row['op']==20) or any(row['unused']) or
                type(size) is not int or not 0<=size<=64 or type(result) is not int):
                raise ValueError('session feeder IO fields')
            clocks[run]=row['now']
            if row['slot']!=0:
                if row['op']==15 and result>0:raise ValueError('session feeder child consumed shell input')
                continue
            if row['gen']!=roots[run]['gen']:raise ValueError('session feeder acknowledgement generation')
            before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after'])
            if len(before)!=size or len(after)!=size:raise ValueError('session feeder complete IO bytes')
            if result>0:
                if result>size:raise ValueError('session feeder IO extent')
                if row['op']==15:
                    if before[result:]!=after[result:]:raise ValueError('session feeder read tail')
                    received[run-1].extend(after[:result])
                    if b'\n' in after[:result]:prompt_floor[run-1]=len(written[run-1])
                else:
                    if before!=after:raise ValueError('session feeder write mutation')
                    written[run-1].extend(before[:result])
            elif result not in (0,-11) or before!=after or result==0 and size:
                raise ValueError('session feeder IO failure')
        self.rows=rows
        for index,raw in enumerate(received):
            if len(raw)>self.offsets[index] or raw!=self.payload[index][:len(raw)]:
                raise ValueError('session feeder corrupt/ahead acknowledgement')
        ready=sum(raw.startswith(BANNER.encode()) for raw in written)
        if not self.ready<=ready<=min(2,self.ready+1):raise ValueError('session feeder readiness order')
        if ready>self.ready:
            if self.ready and received[self.ready-1]!=self.payload[self.ready-1]:
                raise ValueError('session feeder incomplete prior run')
            self.ready=ready
        if not ready:return
        index=ready-1;offset=self.offsets[index]
        if len(received[index])!=offset or offset==len(self.payload[index]):return
        # Ownership transfer deliberately drains unread RX. Do not pretype the
        # next command: its authority is a fresh root TX prompt after the last
        # acknowledged newline, never echoed serial text or an old prompt.
        if offset==0 or self.payload[index][offset-1:offset]==b'\n':
            if not written[index].endswith(b'C:\\>') or len(written[index])<prompt_floor[index]+4:return
        boundary=0
        for due,part in self.plan[index]:
            boundary+=len(part)
            if offset<boundary:break
        if clocks[ready]-roots[ready]['now']<due:return
        newline=self.payload[index].find(b'\n',offset,boundary)
        if newline<0:raise ValueError('session fixed command delimiter')
        raw=self.payload[index][offset:min(offset+8,boundary,newline+1)]
        if len(self.chunks)>=64:raise ValueError('session feeder chunk capacity')
        if write(raw)!=len(raw):raise ValueError('session short host input write')
        self.chunks.append(dict(run=ready,offset=offset,payload=raw.hex(),bytes=len(raw),
            acknowledged=len(received[index]),trace_bytes=len(complete),elapsed=elapsed))
        self.offsets[index]+=len(raw)
        if self.offsets[index]==len(self.payload[index]):
            self.sent.append(dict(run=ready,payload=self.payload[index].hex(),bytes=len(self.payload[index]),elapsed=elapsed))

    @staticmethod
    def validate(plan,trace,chunks,sent):
        if not 2<=len(chunks)<=64:raise ValueError('session complete chunk receipts')
        replay=SessionFeeder(plan)
        for row in chunks:
            count=row['trace_bytes']
            if type(count) is not int or not 0<=count<=len(trace):raise ValueError('session exact trace prefix')
            previous=len(replay.chunks)
            replay.pump('',trace[:count],lambda raw:len(raw),row['elapsed'])
            if len(replay.chunks)!=previous+1 or replay.chunks[-1]!=row:raise ValueError('session exact acknowledged chunk')
        replay.pump('',trace,lambda raw:(_ for _ in ()).throw(ValueError('session missing chunk')),chunks[-1]['elapsed'])
        if replay.sent!=sent or [r['payload'] for r in sent]!=[r.hex() for r in replay.payload]:
            raise ValueError('session complete sent input')
        # Require the final RX acknowledgement too, not merely sent input.
        for run in (1,2):
            raw=bytearray()
            for line in trace.splitlines():
                if line.startswith('CONSOLE_IO '):
                    row=json.loads(line[11:])
                    if row['run']==run and row['slot']==0 and row['op']==15 and row['result']>0:
                        raw.extend(bytes.fromhex(row['after'])[:row['result']])
            if raw!=replay.payload[run-1]:raise ValueError('session final RX acknowledgement')

def capture_namespace(started=None):
    def origin():
        now=time.monotonic()
        require(started is None or type(started) in (int,float) and 0<=started<=now<started+42,'capture setup deadline')
        return now if started is None else started
    ns=dict(vars(boot),console_input_plan=admitted_plan,ConsoleFeeder=SessionFeeder,session_origin=origin)
    for function in (boot._capture_run,boot._capture,boot.capture):
        source=inspect.getsource(function)
        if function in (boot._capture_run,boot.capture):
            clause='media_arguments' if function is boot._capture_run else 'media is not None'
            old=f'({clause} or halt_witness or service_cpu_budget or service_pio_budget or trace_continuation)'
            source=once(source,old,f'(not ({clause}) or halt_witness or service_cpu_budget or not service_pio_budget or trace_continuation)')
        if function is boot._capture_run:
            source=once(source,'console_started=time.monotonic() if console_input is not None else None',
                        'console_started=session_origin() if console_input is not None else None')
            source=once(source,'capture_started=time.monotonic() if service_cpu_budget or service_pio_budget else None',
                        'capture_started=console_started')
            source=once(source,'deadline=console_started+17','deadline=console_started+42')
            source=once(source,'time.monotonic()-console_started>20','time.monotonic()-console_started>45')
            source=once(source,"'NATIVE_CONSOLE_READY\\n' in serial",repr(BANNER)+' in serial')
            source=once(source,'source.read(1024*1024+1)','source.read(8*1024*1024+1)')
            source=once(source,"(folder/name).stat().st_size>65536", "(folder/name).stat().st_size>(8*1024*1024 if name=='frame-trace.log' else 65536)")
        exec(compile(source,'<native-shell-session-bounded-capture>','exec'),ns)
    return ns


def continuation_capture_namespace(started=None):
    """Diagnostic-only existing QEMU trace sink, same deadlines and capacities."""
    source=inspect.getsource(capture_namespace)
    source=once(source,
        "f'(not ({clause}) or halt_witness or service_cpu_budget or not service_pio_budget or trace_continuation)'",
        "f'(not ({clause}) or halt_witness or service_cpu_budget or not service_pio_budget)'")
    temporary=dict(globals());exec(compile(source,'<AY diagnostic QEMU trace admission>','exec'),temporary)
    namespace=temporary['capture_namespace'](started);original=namespace['capture']
    def capture(*args,**kwargs):
        if 'trace_continuation' in kwargs:raise ValueError('explicit diagnostic trace owns flag')
        return original(*args,**kwargs,trace_continuation=True)
    namespace['capture']=capture
    return namespace


# Debugger-side code. Reuse the accepted page-table, actual frame-retirement
# and raw CPU-ring mechanisms; this profile supplies its own dynamic lifecycle.
OBSERVER=r'''
from pathlib import Path
import gdb,struct,json,hashlib
S=CONFIG['s'];CS=CONFIG['cs'];OUT=Path(CONFIG['out'])
DM=0xffff800000000000;HIGH=0xffffffff80000000;MASK=0x3fffff000;NX=1<<63
starts={};copies={};pending={};runs=0;release=None;created=None;callbacks=0
snapshots=0;snapshot_bytes=0;cpu_events=0;pio_sequence=0;boot_seen=False
oom_armed=False;oom_injected=False;oom_count=0;oom_before=None

def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a&0xffffffffffffffff,n))
def q(a):return struct.unpack('<Q',mem(a,8))[0]
def d(a):return struct.unpack('<I',mem(a,4))[0]
def mode():return mem(S['scheduler_mode'],1)[0]
def task(slot):return struct.unpack('<128Q',mem(S['scheduler_tasks']+slot*1024,1024))
def free():return d(S['free_frame_count'])
def signed(value):return value-(1<<64) if value>>63 else value
def emit(kind,**values):gdb.write('SHELL_SESSION '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\n')
def snapshot(raw):
    global snapshots,snapshot_bytes
    snapshots+=1;snapshot_bytes+=len(raw)
    assert snapshots<=2048 and snapshot_bytes<=32*1024*1024 and len(raw)<=1024*1024
    name='session-%04d.bin'%snapshots
    with (OUT/name).open('xb') as stream:assert stream.write(raw)==len(raw)
    return dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def walk(root,va,direct=DM):
    for shift in (39,30,21):
        e=q(direct+root+((va>>shift)&511)*8)
        if not e&1:return 0
        assert not e&128;root=e&MASK
    return q(direct+root+((va>>12)&511)*8)
def family():return mem(S['family_records'],512)+mem(S['family_session_window'],56)+mem(S['family_total'],4)
def cpu_record(slot):
    return list(struct.unpack('<4Q',mem(S['scheduler_cpu_budgets']+slot*32,32))+
                struct.unpack('<4Q',mem(S['scheduler_cpu_windows']+slot*32,32)))
class CPUSink:
    def event(self,**event):
        global cpu_events
        cpu_events+=1;assert cpu_events<=2176
        emit(**event)
cpu_sink=CPUSink()

def drain():
    if boot_seen:cpu_reader.drain()
    if mode()!=8:return
    pio_reader.drain()
    global pio_sequence
    raw=trace_snapshot(mem,S['native_pio_trace'],pio_sequence)
    events=trace_decode(raw,pio_sequence)
    if events:
        emit('pio',run=runs+1,previous=pio_sequence,raw=snapshot(raw))
        pio_sequence=events[-1][1]

def boot():
    global boot_seen
    assert not boot_seen and not reg('eflags')&512 and reg('cr0')&(1<<16)
    assert not any(mem(HIGH+0xb05000,270336))
    cpu_reader.initialize();boot_seen=True
    emit('boot',zero=1)

def complete(slot,t):
    gen=t[1]
    if gen not in pending:return
    row=pending.pop(gen);assert row['slot']==slot
    result=signed(t[85]);row.update(result=result,now=q(S['scheduler_last_tick'])*10)
    pointer,size=row['pointer'],row['size']
    after=user(t,pointer,size) if size else b''
    row['after']=after.hex()
    if row['op'] in (15,20):gdb.write('CONSOLE_IO '+json.dumps(row,sort_keys=True)+'\n')
    else:emit('return',**row,terminal=mem(S['native_terminal_state'],24).hex(),
              pio=mem(S['native_pio_state'],64).hex(),family=snapshot(family()) if row['op']==132 else None)
def resume():
    slot=d(S['scheduler_current_slot']);t=task(slot);row=pending.get(t[1])
    if row:
        # Snapshot an immediate return exactly, before another task may
        # release a newly transferred terminal. Never alter guest registers.
        assert t[0]==2;t=list(t);t[85]=reg('rax');complete(slot,t)
    # A blocked invocation does not visit this PC; its saved completion is
    # observed at the next actual task entry. Do not leave a hot-page probe
    # enabled merely because some other process is waiting for IPC.
    resume_hook.enabled=False

def start():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);assert slot<8
    t=task(slot);gen=t[1];assert t[0]==2 and 0<gen<1<<31 and not reg('eflags')&512
    if gen in starts:complete(slot,t);return
    assert len(starts)<64
    record=mem(S['boot_program_catalog']+slot*266336,266336) if slot<2 else copies[gen]
    assert record[:16]==b'RNPGv2\0\0'+struct.pack('<II',2,266336)
    assert t[68]==struct.unpack_from('<Q',record,16)[0] and 0x410000<=t[68]<0x440000
    assert 0x40f000<=t[69]<0x410000 and not t[69]&15
    leaves=file_leaves(t);owned=[];mapped=[];pages=[]
    for page in range(64):
        pf=6 if page==8 else record[24+page];leaf=leaves[page]
        if not pf:assert not leaf;continue
        frame=leaf&MASK;flags=5|(2 if pf==6 else 0)|(0 if pf==5 else NX)
        assert 0x100000000<=frame<0x400000000 and leaf&~0x60==frame|flags
        if pf==6:assert frame==(t[3] if page==8 else t[4+page]);owned.append(frame)
        else:assert t[4+page]==0
        mapped.append(frame);pages.append(page)
    actual=file_pages(mapped)
    for page,raw in zip(pages,actual):
        if page!=15:assert raw==(bytes(4096) if page==8 else record[96+page*4096:96+(page+1)*4096])
    assert len(owned)==len(set(owned)) and not t[12]
    for entry in starts.values():
        if entry['live']:assert not set(mapped)&set(entry['mapped'])
    argc=q(DM+(leaves[15]&MASK)+(t[69]&4095));assert 1<=argc<=8
    values=struct.unpack('<'+'Q'*(argc+7),user(t,t[69],(argc+7)*8))
    assert values[0]==argc and values[argc+1:]==(0,0,0x52534901,0,0,0)
    args=[user(t,p,128).split(b'\0')[0].decode('ascii') for p in values[1:argc+1]]
    parent=q(S['family_records']+slot*64+8)
    if slot<2:assert not parent and args==['program%d.prg'%slot,str(slot)]
    else:assert parent==task(0)[1]<<32 and slot in (2,3,4)
    stack=user(t,0x408000,32768);assert not any(stack[:t[69]-0x408000])
    starts[gen]=dict(slot=slot,live=True,owned=owned,mapped=mapped,run=runs+1,parent=parent)
    emit('start',run=runs+1,slot=slot,gen=gen,parent=parent,args=args,now=q(S['scheduler_last_tick'])*10,
         task=snapshot(mem(S['scheduler_tasks']+slot*1024,1024)),family=snapshot(family()),
         pages=pages,mapped=mapped,image=snapshot(b''.join(actual)),record=snapshot(record),
         profile=mem(S['family_profiles']+slot*32,32).hex(),extended=mem(S['family_extended_masks']+slot*16,16).hex())
    cpu_sink.event(kind='cpu_start',slot=slot,gen=gen,now=q(S['scheduler_last_tick']),records=cpu_record(slot))
    if slot==0:
        address=CONFIG['selection'];raw=user(t,address,32)
        assert raw==struct.pack('<4Q',0x3153455353484c53,1,2,0) and address&4095<=4064
        leaf=leaves[(address-0x400000)//4096];assert leaf&~MASK&~0x60==NX|7
        value=struct.pack('<4Q',0x3153455353484c53,1,CONFIG['layout'],CONFIG['case'] if runs==0 else 0)
        target=DM+(leaf&MASK)+(address&4095)
        gdb.selected_inferior().write_memory(target,value);assert mem(target,32)==value
        emit('selection',gen=gen,run=runs+1,before=raw.hex(),after=value.hex())

def syscall(denied=False):
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1];op=q(S['syscall_rax'])
    assert gen in starts and starts[gen]['live'] and gen not in pending, ('request s=%s g=%s op=%s live=%s pending=%s' % (slot,gen,op,starts.get(gen,{}).get('live'),pending.get(gen,{}).get('op')))
    if op not in (9,15,20,49,50,51,52,53,54,55,113,114,127,132):
        if not (op==41 and CONFIG['case']==17 and runs==0 and slot==0 and
                q(S['syscall_rdi'])==100 and
                struct.unpack('<Q',user(t,CONFIG['service']+72,8))[0]==2):return
    args=[q(S['syscall_'+name]) for name in ('rdi','rsi','rdx','r10','r8','r9')]
    pointer=0;size=0
    if denied:pass # Kernel profile rejection precedes every user-memory read.
    elif op in (15,20):pointer=args[1];size=args[2];assert size<=64
    elif op==114:pointer=args[0];size=16
    elif op==127:pointer=args[0];size=24
    elif op==132:pointer=args[0];size=struct.unpack('<2I',user(t,pointer,8))[1];assert size in (64,80)
    elif op==49:pointer=args[0];size=4
    elif op==113:pointer=args[1];size=64
    elif op in (50,51,53,54):
        pointer=args[1];version,length=struct.unpack('<2I',user(t,pointer,8))
        assert (version,length) in ((1,140),(2,2060));size=length
    before=user(t,pointer,size) if size else b''
    row=dict(run=runs+1,slot=slot,gen=gen,op=op,args=args,pointer=pointer,size=size,before=before.hex(),
             fd=args[0],unused=args[3:],entered=q(S['scheduler_last_tick'])*10,profile_denied=denied,
             family_before=snapshot(family()) if op==132 else None,
             authority=snapshot(mem(S['scheduler_tasks'],8192)+mem(S['family_records'],512)) if op in (114,127) and not denied else None,
             terminal_before=mem(S['native_terminal_state'],24).hex())
    if op in (9,132) and slot==0:
        emit('policy',gen=gen,run=runs+1,now=q(S['scheduler_last_tick'])*10,
             policy=user(t,CONFIG['policy'],96).hex(),service=user(t,CONFIG['service'],104).hex())
    if op==53 and not denied and slot in (2,3) and size==140 and struct.unpack_from('<I',before,8)[0]==48:
        phase=struct.unpack_from('<I',before,48)[0]
        if phase==(2 if slot==2 else 4):
            emit('service_ready',gen=gen,slot=slot,run=runs+1,control=before.hex(),
                raw=snapshot(user(t,CONFIG['block_state'] if slot==2 else CONFIG['fs_state'],128 if slot==2 else 8400)))
    emit('call',**row)
    if op!=9:pending[gen]=row;resume_hook.enabled=True
def syscall_denied():syscall(True)

def copy():
    t=struct.unpack('<128Q',mem(reg('r12'),1024));gen=t[1]
    assert gen not in copies and len(copies)<60
    record=mem(S['elf_import_record'],266336)
    slot=d(S['family_build_slot']);assert slot in (2,3,4)
    # Startup is separately validated; the executable bytes must be exactly
    # the packaged service or the file from the immutable medium.
    reference=records[slot]
    assert record[:262240]==reference[:262240]
    copies[gen]=record;emit('copy',slot=slot,gen=gen,raw=snapshot(record))

def before_release():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);gen=task(slot)[1]
    if gen in pending:emit('abandoned',**pending.pop(gen))
    cpu_sink.event(kind='cpu_final',slot=slot,gen=gen,now=q(S['scheduler_last_tick']),records=cpu_record(slot))
    raw=mem(S['native_pio_state'],64);state=struct.unpack('<8Q',raw)
    if slot in (0,2):assert state[2]==1
    assert not any(mem(S['family_extended_masks']+slot*16,16))
    emit('fenced',slot=slot,gen=gen,pio=raw.hex(),terminal=mem(S['native_terminal_state'],24).hex())
    release_begin()

def fault():
    slot=d(S['scheduler_current_slot']);gen=task(slot)[1]
    raw=mem(reg('rdi'),176);frame=struct.unpack('<22Q',raw)
    assert frame[18]==0x33
    emit('fault',run=runs+1,slot=slot,gen=gen,raw=snapshot(raw))

def create_begin():
    global oom_armed,oom_count,oom_before
    assert not oom_armed and oom_before is None
    if CONFIG['case']!=17 or runs or oom_injected or d(S['family_build_slot'])!=3:return
    assert d(S['scheduler_current_slot'])==0
    if struct.unpack('<Q',user(task(0),CONFIG['service']+72,8))[0]!=2:return
    # CREATE-v6 first evicts its previous staging ELF. Match the kernel's
    # post-eviction transaction baseline, before any new allocation.
    assert reg('rip')==S['family_create64.cached_entry']
    assert free()==d(S['family_initial_free'])
    # Fail the fourth allocator call in FS construction, after real partial
    # allocation. Driver and parent cannot run while this IF=0 rollback executes.
    assert not reg('eflags')&512
    oom_before=(free(),d(S['process_run_generation']),mem(S['scheduler_tasks']+2*1024,1024),
                mem(S['scheduler_tasks'],1024),mem(S['family_records']+3*64,64))
    oom_count=0;oom_armed=True;allocator.enabled=True
def allocation():
    global oom_count,oom_injected
    assert oom_armed and not oom_injected and not reg('eflags')&512
    if oom_count==3:
        ret=q(reg('rsp'));gdb.execute('set $rax=0');gdb.execute('set $rsp=$rsp+8');gdb.execute('set $rip='+hex(ret))
        oom_injected=True;allocator.enabled=False
        emit('oom',run=runs+1,slot=3,acquired=oom_count,free=free())
    else:oom_count+=1
def create_end():
    global oom_armed,oom_before
    if not oom_armed:return
    allocator.enabled=False;assert oom_injected and oom_count==3 and signed(reg('rax'))==-12
    available,generation,driver,parent,record=oom_before
    assert free()==available and d(S['process_run_generation'])==generation
    assert mem(S['scheduler_tasks']+2*1024,1024)==driver
    # Saving the caller syscall context is expected; all live driver bytes and
    # the unpublished target family must remain exact, with full frame balance.
    assert task(0)[1]==struct.unpack_from('<Q',parent,8)[0]
    assert mem(S['family_records']+3*64,64)==record
    emit('rollback',run=runs+1,slot=3,generation=generation,free=free(),before=available,
         driver=snapshot(driver),family=snapshot(record))
    oom_armed=False;oom_before=None

def pio_before_clear():
    drain();emit('pio_end',run=runs+1,sequence=pio_sequence)
def pio_after_clear():
    global pio_sequence
    raw=mem(S['native_pio_trace'],12304);trace_clean(raw)
    emit('pio_clear',run=runs+1,raw=snapshot(raw));pio_sequence=0
    pio_reader.finish_run()

def finish():
    global runs
    runs+=1;assert runs<=2 and release is None and not pending and not oom_armed and oom_before is None and not reg('eflags')&512
    pieces=[]
    for name,n in ZERO_RANGES:
        raw=mem(S[name],n);assert not any(raw),name;pieces.append(raw)
    raw=mem(S['family_begin'],S['family_end']-S['family_begin']);assert not any(raw);pieces.append(raw)
    contexts=[]
    for address in [S['elf_context_window']]+[S['elf_context_store']+i*592 for i in range(13)]:
        raw=mem(address,592);assert not any(raw[:576]) and not any(raw[580:]);contexts.append(raw)
    assert not any(mem(S['native_terminal_state'],24))
    assert struct.unpack('<8Q',mem(S['native_pio_state'],64))==(0,0xffffffffffffffff,1,0,0,0,0,0)
    assert not any(mem(S['native_pio_request'],64))
    count=sum(e['run']==runs for e in starts.values())
    assert free()==d(S['scheduler_initial_free']) and d(S['scheduler_reap_count'])==count
    assert q(S['timer_runtime_ticks'])==q(S['timer_runtime_eois'])==q(S['scheduler_last_tick'])
    assert not any(v['live'] for v in starts.values())
    for slot in range(8):
        assert not any(mem(CS['clients']+slot*108,108)) and not any(mem(CS['pending']+slot*2144,2144))
        seen=[g for g,e in starts.items() if e['slot']==slot]
        if seen:
            gen=max(seen);assert d(S['scheduler_identity_retired']+slot*4)==gen
            hp=CS['native_heap_state']+232+slot*99368
            assert struct.unpack('<8Q',mem(hp,64))==(0,gen,0,0,0,0x20000000,0,0)
            assert not any(mem(hp+552,5120)) and not any(mem(hp+32808,12288))
            assert d(CS['retired']+slot*4)==gen
            value,inverse,seal=struct.unpack('<3Q',mem(S['process_ipc_completions']+slot*24,24))
            assert value==gen<<32 and inverse==value^0xffffffffffffffff
            assert seal==(((value<<17)|(value>>47))&0xffffffffffffffff)^0x936da17cb852e40f
    emit('finish',run=runs,tasks=count,free=free(),initial=d(S['scheduler_initial_free']),
         raw=snapshot(b''.join(pieces)),contexts=snapshot(b''.join(contexts)))
    if runs==2:cpu_reader.finish();gdb.execute('detach');gdb.execute('quit 0')
def fail():
    emit('OBSERVER_FAIL',where='kernel',stage=mem(S['scheduler_failure_stage'],1)[0]);gdb.execute('quit 73')
'''

def observer_body(cold=True):
    node=admission.source_node;cpu=admission.cpu
    inherited='\n'.join(node(admission.wide.OBSERVER,n) for n in ('Hook','release_begin','freed','ReleaseEnd'))
    inherited=once(inherited,'callbacks<=4096','callbacks<=32768')
    inherited=once(inherited,"            starts[r['gen']]['live']=False",
        "            assert all(not any(raw) for raw in file_pages(r['frames'])),'freed frame bytes'\n"
        "            starts[r['gen']]['live']=False")
    # CPU/PIO trace reads are complete before each state transition. The first
    # boot callback initializes the CPU reader instead of reading unbound data.
    inherited=once(inherited,'            self.fn()',
        '            if self.fn is not pio_after_clear:drain()\n            self.fn()')
    code=OBSERVER+'\n'+file.FILE_USER_READ+'\n'+file.FILE_RAM_BATCH+'\n'+inherited
    code+='\n'+file.block.TRACE_CORE
    for function in (native_cpu_trace.decode_trace_record,native_cpu_trace.CPUTraceReader):
        code+='\n'+inspect.getsource(function)
    code+='\n'+inspect.getsource(pio_record_decode)+'\n'+inspect.getsource(PioCallReader)
    code+='''
records={}
for slot,reference in CONFIG['records'].items():
    path=Path(reference['path']);assert path.stat().st_size==266336
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==reference['sha256'];records[slot]=raw
cpu_reader=CPUTraceReader(lambda a,n:mem(a,n),S['native_cpu_trace'],S['native_cpu_trace_end'],cpu_sink,
    starts,lambda:q(S['scheduler_last_tick']),OUT/'cpu-trace-v1.bin',gdb.write)
pio_reader=PioCallReader(lambda a,n:mem(a,n),S['native_session_pio_trace'],starts,
    lambda:q(S['scheduler_last_tick']),snapshot,emit,lambda:runs+1)
free_hook=Hook('physical_frame_free64',freed);free_hook.enabled=False
allocator=Hook('physical_frame_alloc64',allocation);allocator.enabled=False
resume_hook=Hook('process_run_resume64',resume);resume_hook.enabled=False
Hook('x86_64_c_core_handoff64',boot)
Hook('scheduler_enter_task64.state_published',start)
for name in ('native_console_syscall64','native_identity_syscall64','native_terminal_syscall64',
             'family_syscall64','process_ipc_syscall64','native_pio_syscall64','process_run_syscall64.exit'):
    Hook(name,syscall)
Hook('process_run_syscall64.denied',syscall_denied)
Hook('scheduler_release_task_frames64',before_release)
Hook('process_run_exception64',fault)
Hook('family_create64.stack_ready',copy)
Hook('family_create64.cached_entry',create_begin)
Hook('family_create64.parent_result',create_end)
Hook('native_pio_finish64.trace_before_clear',pio_before_clear)
Hook('native_pio_finish64.trace_after_clear',pio_after_clear)
Hook('x86_64_c_process_run64.restore',finish)
Hook('scheduler_fail',fail)
def cpu_trace_full():pass
Hook('native_cpu_trace_after64.full',cpu_trace_full)
def pio_capture_full():pass
Hook('native_session_probe_pio_site64',pio_capture_full)
'''
    if type(cold) is not bool:raise ValueError('session observer transport selection')
    if cold:
        code=once(code,"resume_hook=Hook('process_run_resume64',resume)",
                       "resume_hook=Hook('native_session_probe_return_site64',resume)")
        code=once(code,"Hook('scheduler_enter_task64.state_published',start)",
                       "Hook('native_session_probe_start_site64',start)")
        code=once(code,
            "for name in ('native_console_syscall64','native_identity_syscall64','native_terminal_syscall64',\n"
            "             'family_syscall64','process_ipc_syscall64','native_pio_syscall64','process_run_syscall64.exit'):\n"
            "    Hook(name,syscall)",
            "Hook('native_session_probe_request_site64',syscall)")
        code=once(code,"Hook('process_run_syscall64.denied',syscall_denied)",
                       "Hook('native_session_probe_denied_site64',syscall_denied)")
        code=once(code,"    cpu_reader.initialize();boot_seen=True",
            "    base=S['native_session_probe_page']\n"
            "    assert base%4096==0 and S['native_session_probe_page_end']==base+4096\n"
            "    assert [S['native_session_probe_'+n+'_site64'] for n in ('request','denied','return','start','pio','terminal','fault')]==list(range(base,base+7))\n"
            "    assert mem(base,4096)==bytes([195])*7+bytes([144])*4089\n"
            "    assert S['native_session_probe_pending']==S['native_session_probe_seen']+64\n"
            "    assert S['native_session_pio_trace']==S['native_session_probe_seen']+72\n"
            "    assert S['native_session_pio_trace_end']==S['native_session_pio_trace']+12320\n"
            "    assert S['native_session_read_tickets']==S['native_session_pio_trace_end']\n"
            "    assert not any(mem(S['native_session_probe_seen'],12408))\n"
            "    cpu_reader.initialize();boot_seen=True")
        code=once(code,"    contexts=[]",
            "    raw=mem(S['native_session_probe_seen'],12408);assert not any(raw);pieces.append(raw)\n    contexts=[]")
    return cpu.defer_observer_callbacks(code,('Hook','ReleaseEnd'))


def image_config(image):
    wide=admission.wide
    image=Path(image).resolve()
    inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf')
    core=wide.payload.validate(inner)
    if core['layout_version']!=5:raise ValueError('session native layout5 required')
    wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    if len(catalog)!=4*266336:raise ValueError('session exact catalog extent')
    attempts=[p for p in image.parent.glob('programs-*') if p.is_dir() and
        (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(attempts)!=1:raise ValueError('session unique producer')
    folder=attempts[0];records={};programs={}
    for slot in range(4):
        raw=(folder/f'program{slot}.prg').read_bytes();programs[slot]=raw
        if wide.producer.prepare(raw,[f'program{slot}.prg',str(slot)],True)!=catalog[slot*266336:(slot+1)*266336]:
            raise ValueError('session exact catalog program')
        if slot>=2:records[slot]=wide.producer.prepare(raw,[],True)
    app=(folder/'file-program.prg').read_bytes()
    if not 64<=len(app)<=1280 or app in programs[0]:raise ValueError('session file capacity/source boundary')
    records[4]=wide.producer.prepare(app,[],True)
    if (folder/'root/bin/shell.prg').read_bytes()!=programs[0]:raise ValueError('session normal shell image layout')
    addresses={name:file.block.map_symbol(folder/'program0.map',symbol) for name,symbol in (
        ('selection','reist_shell_session_selection'),('policy','session_policy'),('service','session_service'))}
    if len(set(addresses.values()))!=3:raise ValueError('session distinct private state')
    addresses['block_state']=file.block.map_symbol(folder/'program2.map','filesystem_block_service')
    addresses['fs_state']=file.block.map_symbol(folder/'program3.map','filesystem_service')
    c_symbols={name:value['value'] for name,value in core['symbols'].items()}
    if 'native_shell_session_profile_v1' not in c_symbols:raise ValueError('session explicit core profile')
    return dict(s=boot.symbols(image),cs=c_symbols,**addresses),records,app

def diagnostic_untraced_namespace(started):
    if type(started) not in (int,float) or not 0<=started<1e12:raise ValueError('diagnostic clock')
    ns=dict(vars(boot),probe_started=started)
    for name in ('capture','_capture','_capture_run'):
        source=textwrap.dedent(inspect.getsource(getattr(boot,name)))
        if name=='_capture_run':
            source=once(source,'else time.monotonic()+20','else probe_started+7')
            source=once(source,'else deadline-20;metrics','else probe_started;metrics')
        exec(compile(source,'<boot-only no-breakpoint diagnosis>','exec'),ns)
    return ns


def diagnostic_select_layout(config):
    # One first-entry stop only, with exactly the ordinary observer's private
    # layout selection. No quota, clock, executable or service-state write.
    body="""
import gdb,struct,json
def mem(address,size):return bytes(gdb.selected_inferior().read_memory(address,size))
def q(address):return struct.unpack('<Q',mem(address,8))[0]
S=CONFIG['s'];va=CONFIG['selection'];DM=0xffff800000000000;MASK=0x3fffff000
assert int(gdb.parse_and_eval('$rip'))&0xffffffffffffffff==S['native_session_probe_start_site64']
assert not int(gdb.parse_and_eval('$eflags'))&512
assert mem(S['scheduler_mode'],1)==b'\\x08'
assert mem(S['scheduler_current_slot'],4)==bytes(4)
t=struct.unpack('<128Q',mem(S['scheduler_tasks'],1024))
assert t[:2]==(2,1) and 0x410000<=va<=0x440000-32 and va&4095<=4064
root=t[2]
for shift in (39,30,21):
    e=q(DM+root+((va>>shift)&511)*8)
    assert e&7==7 and not e&128
    root=e&MASK
leaf=q(DM+root+((va>>12)&511)*8)
assert leaf&~MASK&~0x60==(1<<63)|7 and 0x100000000<=leaf&MASK<0x400000000
address=DM+(leaf&MASK)+(va&4095)
before=struct.pack('<4Q',0x3153455353484c53,1,2,0)
after=struct.pack('<4Q',0x3153455353484c53,1,0,0)
assert mem(address,32)==before
gdb.selected_inferior().write_memory(address,after)
assert mem(address,32)==after
gdb.write('AY_DIAGNOSTIC_LAYOUT '+json.dumps(dict(before=before.hex(),after=after.hex()))+'\\n')
"""
    return ('hbreak *'+hex(config['s']['native_session_probe_start_site64'])+'\ncontinue\npython\n'+
            'CONFIG='+repr(config)+'\n'+body+'\nend\n')


def diagnostic_untraced(image,folder,candidate,binding,layout=2):
    """Boot-only causal control, not a runtime or raw-memory proof."""
    require(type(layout) is int and layout in (0,2),'diagnostic fixed layout')
    binding();config,records,app=image_config(image)
    folder=Path(folder).resolve()
    require(folder.is_relative_to(ROOT/'build/codex-agent') and not folder.exists(),'fresh boot-only diagnosis')
    folder.mkdir(parents=True);started=time.monotonic()
    result=dict(candidate=candidate,qualification=False,layout=layout,ram=4096,
                debugger_breakpoints=int(layout==0),ongoing_breakpoints=0,input_bytes=0)
    try:
        fixture=bounded_fixture(folder,layout,app,started)
        code=('set logging file '+(folder/'frame-trace.log').as_posix()+
              '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\n'
              +(diagnostic_select_layout(config) if layout==0 else '')+
              'echo AY_DIAGNOSTIC_NO_BREAKPOINTS\\n\ndetach\nquit 0\n')
        serial,trace=diagnostic_untraced_namespace(started)['capture'](
            image,folder,code,4096,fixture,diagnostic_metrics=True)
        result['receipts']=[dict(zip(('slot','generation','status','state','ticks','rip'),
            struct.unpack('<4I2Q',bytes.fromhex(m[1])))) for m in boot.process.REAP.finditer(serial)]
        result['shell_banners']=serial.count(BANNER)
        result['healthy_prompt']='C:\\>' in serial
        require('AY_DIAGNOSTIC_NO_BREAKPOINTS' in trace,'actual detached observation')
        if layout==0:require('AY_DIAGNOSTIC_LAYOUT ' in trace,'actual same-layout selection')
        result['image_sha256']=hashlib.sha256(Path(image).read_bytes()).hexdigest()
        return result
    finally:
        result['elapsed']=time.monotonic()-started
        with (folder/'diagnostic.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2,sort_keys=True)
        require(result['elapsed']<=10,'boot-only total deadline')


class DiagnosticCommandFeeder:
    """Serial-only causal control. Deliberately inadmissible as raw proof."""
    def __init__(self,plan):
        if admitted_plan(plan)!=input_plan(0):raise ValueError('diagnostic healthy command plan')
        self.plan=plan;self.commands=HEALTHY[0][1].splitlines(keepends=True)
        self.counts=[0,0];self.sent=[];self.chunks=[];self.serial='';self.calls=0;self.elapsed=0

    def pump(self,serial,trace,write,elapsed):
        self.calls+=1
        if self.calls>4096 or not self.elapsed<=elapsed<42:raise ValueError('diagnostic command bound')
        self.elapsed=elapsed
        if len(serial)>262144 or not serial.startswith(self.serial):raise ValueError('diagnostic serial continuity')
        self.serial=serial;parts=serial.split(BANNER);ready=len(parts)-1
        if ready>2:raise ValueError('diagnostic root capacity')
        if not ready:return
        if ready==2 and self.counts[0]!=len(self.commands):raise ValueError('diagnostic incomplete first commands')
        index=ready-1;count=self.counts[index]
        if count==len(self.commands) or parts[ready].count('C:\\>')<=count:return
        raw=self.commands[count]
        if len(self.chunks)>=12 or not 0<len(raw)<=8 or sum(r['bytes'] for r in self.chunks)+len(raw)>64:
            raise ValueError('diagnostic command capacity')
        if write(raw)!=len(raw):raise ValueError('diagnostic short input')
        self.chunks.append(dict(run=ready,payload=raw.hex(),bytes=len(raw),elapsed=elapsed,qualification=False))
        self.counts[index]+=1
        if self.counts[index]==len(self.commands):
            self.sent.append(dict(run=ready,payload=HEALTHY[0][1].hex(),bytes=len(HEALTHY[0][1]),qualification=False))


def diagnostic_commands(image,folder,candidate,binding,layout=0):
    require(type(layout) is int and layout in (0,2),'diagnostic command layout')
    binding();config,records,app=image_config(image);folder=Path(folder).resolve()
    require(folder.is_relative_to(ROOT/'build/codex-agent') and not folder.exists(),'fresh command control')
    folder.mkdir(parents=True);started=time.monotonic()
    result=dict(candidate=candidate,qualification=False,first_layout=layout,second_layout=2,ongoing_breakpoints=0)
    try:
        fixture=bounded_fixture(folder,layout,app,started)
        code=('set logging file '+(folder/'frame-trace.log').as_posix()+
              '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\n'+
              (diagnostic_select_layout(config) if layout==0 else '')+'echo AY_DIAGNOSTIC_NO_BREAKPOINTS\\n\ndetach\nquit 0\n')
        ns=capture_namespace(started);ns['ConsoleFeeder']=DiagnosticCommandFeeder
        serial,trace=ns['capture'](image,folder,code,4096,fixture,diagnostic_metrics=True,
                                  service_pio_budget=True,console_input=input_plan(0))
        require('AY_DIAGNOSTIC_NO_BREAKPOINTS' in trace,'actual detached command control')
        if layout==0:require('AY_DIAGNOSTIC_LAYOUT ' in trace,'actual first-layout selection')
        result['receipts']=[dict(zip(('slot','generation','status','state','ticks','rip'),
            struct.unpack('<4I2Q',bytes.fromhex(m[1])))) for m in boot.process.REAP.finditer(serial)]
        result['file_markers']=serial.count('SESSION64\n');result['shell_banners']=serial.count(BANNER)
        result['image_sha256']=hashlib.sha256(Path(image).read_bytes()).hexdigest()
        return result
    finally:
        result['elapsed']=time.monotonic()-started
        with (folder/'diagnostic.json').open('x',encoding='utf-8') as out:json.dump(result,out,indent=2,sort_keys=True)
        require(result['elapsed']<=45,'command control total deadline')


def diagnostic_observer_body(version=1):
    """Differential transport probe only; all callbacks and oracles unchanged."""
    if type(version) is not int or version not in (1,2):raise ValueError('diagnostic observer version')
    code=observer_body(cold=False)
    if version==1:return once(code,
        "'process_ipc_syscall64','native_pio_syscall64','process_run_syscall64.exit'",
        "'process_ipc_syscall64','native_pio_apply64.bind','native_pio_apply64.fence_request','process_run_syscall64.exit'")
    code=once(code,
        "for name in ('native_console_syscall64','native_identity_syscall64','native_terminal_syscall64',\n"
        "             'family_syscall64','process_ipc_syscall64','native_pio_syscall64','process_run_syscall64.exit'):",
        "for name in ('native_console_syscall64',):")
    code=once(code,"Hook('scheduler_enter_task64.state_published',start)",
                   "start_hook=Hook('scheduler_enter_task64.state_published',start)")
    code=once(code,"    if gen in starts:complete(slot,t);return",
                   "    if gen in starts:complete(slot,t);diagnostic_start_scope();return")
    code=once(code,"        emit('selection',gen=gen,run=runs+1,before=raw.hex(),after=value.hex())",
                   "        emit('selection',gen=gen,run=runs+1,before=raw.hex(),after=value.hex())\n    diagnostic_start_scope()")
    code=once(code,"    copies[gen]=record;emit('copy',slot=slot,gen=gen,raw=snapshot(record))",
                   "    copies[gen]=record;emit('copy',slot=slot,gen=gen,raw=snapshot(record))\n    start_hook.enabled=True")
    code=once(code,"def finish():\n    global runs",
                   "def finish():\n    global runs\n    start_hook.enabled=True")
    return code+"""
def diagnostic_start_scope():
    raw=mem(S['scheduler_tasks'],8192)
    assert len(raw)==8192
    start_hook.enabled=any(state in (1,2,6) and gen not in starts
        for state,gen in (struct.unpack_from('<2Q',raw,slot*1024) for slot in range(8)))
def diagnostic_flush():pass
Hook('process_ipc_syscall64',diagnostic_flush)
"""


class DeferredReadSpans:
    """Read-only syscall data, one paused command-context callback at a time."""
    def __init__(self,namespace):self.namespace=namespace;self.active=False

    def wrap(self,action):
        def scoped(hook):
            if self.active:raise ValueError('nested deferred read scope')
            if hook.fn.__name__ not in ('syscall','syscall_denied','resume'):return action(hook)
            original=self.namespace['mem'];symbols=self.namespace['S']
            cache=SameStopReads(self.namespace);cache.original=original;cache.active=True
            groups=(('scheduler_mode','scheduler_current_slot','scheduler_last_tick'),
                    tuple('syscall_'+n for n in ('rax','rdi','rsi','rdx','r10','r8','r9')))
            spans=[]
            for names in groups:
                begin=min(symbols[n] for n in names);end=max(symbols[n] for n in names)+8
                if not 0<end-begin<=512 or begin>>12!=(end-1)>>12:raise ValueError('joined deferred kernel span')
                spans.append((begin,end))
            def joined(address,size):
                if type(address) is not int or type(size) is not int or not 0<=address<1<<64 or not 0<=size<=270336 or size>(1<<64)-address:
                    raise ValueError('deferred read range')
                for begin,end in spans:
                    if begin<=address<=end-size:return cache.read(begin,end-begin)[address-begin:address-begin+size]
                return cache.read(address,size)
            self.active=True;self.namespace['mem']=joined
            try:return action(hook)
            finally:
                self.namespace['mem']=original;self.active=False
                cache.entries.clear();cache.used=0;cache.active=False
        return scoped


def deferred_read_observer(code):
    return code+'\n'+inspect.getsource(admission.cpu.SameStopReads)+'\n'+inspect.getsource(DeferredReadSpans)+'''
deferred_reads=DeferredReadSpans(globals())
Hook.observe=deferred_reads.wrap(Hook.observe)
'''


def lifecycle_probe_observer(code):
    # Reuse the accepted off-page exception/fatal/revoke routes. Every original
    # callback still observes its original state; only hook lifetimes change.
    code=once(code,"Hook('scheduler_release_task_frames64',before_release)",
                   "Hook('scheduler_release_task_frames64',release_begin)")
    code=file.block.scope_validator_page_hooks(code)
    code=once(code,"release_hook=Hook('scheduler_release_task_frames64',release_begin)",
                   "release_hook=Hook('scheduler_release_task_frames64',before_release)")
    code=once(code,'    cpu_reader.initialize();boot_seen=True','    cpu_reader.initialize()\n    boot_seen=True')
    code=file.block.scope_runtime_page_hooks(code)
    code=once(code,'assert slot<4 and task(slot)[1]==gen','assert slot<8 and task(slot)[1]==gen')
    code=once(code,'assert len(release_pending)<4','assert len(release_pending)<8')
    for suffix,fn,name in (('before','pio_before_clear','trace_before_hook'),('after','pio_after_clear','trace_after_hook')):
        code=once(code,"Hook('native_pio_finish64.trace_"+suffix+"_clear',"+fn+")",
                       name+"=Hook('native_pio_finish64.trace_"+suffix+"_clear',"+fn+");"+name+'.enabled=False')
    code=once(code,"            starts[r['gen']]['live']=False",
                   "            starts[r['gen']]['live']=False\n            if not any(v['live'] for v in starts.values()):trace_before_hook.enabled=trace_after_hook.enabled=True")
    code=once(code,"    emit('pio_clear',run=runs+1,raw=snapshot(raw));pio_sequence=0",
                   "    emit('pio_clear',run=runs+1,raw=snapshot(raw));pio_sequence=0\n    trace_before_hook.enabled=trace_after_hook.enabled=False")
    for symbol,fn,name in (('family_create64.cached_entry','create_begin','create_begin_hook'),
                           ('family_create64.stack_ready','copy','copy_hook'),
                           ('family_create64.parent_result','create_end','create_end_hook')):
        code=once(code,"Hook('"+symbol+"',"+fn+")",name+"=Hook('"+symbol+"',"+fn+");"+name+'.enabled=False')
    code=once(code,"    if op!=9:pending[gen]=row;resume_hook.enabled=True",
                   "    if op!=9:pending[gen]=row;resume_hook.enabled=True\n    creation_enter(row)")
    code=once(code,"    row=pending.pop(gen);assert row['slot']==slot",
                   "    row=pending.pop(gen);assert row['slot']==slot\n    creation_leave(row)")
    return code+'''

def creation_enter(row):
    if row['op']!=132 or row['profile_denied'] or struct.unpack_from('<I',bytes.fromhex(row['before']),8)[0]!=1:return
    assert not any(h.enabled for h in (create_begin_hook,copy_hook,create_end_hook))
    create_begin_hook.enabled=copy_hook.enabled=create_end_hook.enabled=True

def creation_leave(row):
    if row['op']!=132 or row['profile_denied'] or struct.unpack_from('<I',bytes.fromhex(row['before']),8)[0]!=1:return
    assert all(h.enabled for h in (create_begin_hook,copy_hook,create_end_hook))
    create_begin_hook.enabled=copy_hook.enabled=create_end_hook.enabled=False
'''


def cached_probe_observer(code):
    # Reuse the qualified bounded read-through cache, with two explicitly
    # admitted contiguous symbol spans. Nothing survives one all-stop callback.
    code=once(code,'class ColdHook(gdb.Breakpoint):',
                   inspect.getsource(admission.cpu.SameStopReads)+'\nclass ColdHook(gdb.Breakpoint):')
    return once(code,"        globals()['mem']=bounded", """        cache=SameStopReads(globals());cache.original=bounded;cache.active=True
        groups=(('scheduler_mode','scheduler_current_slot','scheduler_last_tick'),
                tuple('syscall_'+n for n in ('rax','rdi','rsi','rdx','r10','r8','r9')))
        spans=[]
        for names in groups:
            begin=min(S[n] for n in names);end=max(S[n] for n in names)+8
            assert 0<end-begin<=512 and begin>>12==(end-1)>>12,'joined kernel span'
            spans.append((begin,end))
        def joined(address,size):
            assert type(address) is int and type(size) is int and 0<=size<32768
            for begin,end in spans:
                if begin<=address<=end-size:
                    return cache.read(begin,end-begin)[address-begin:address-begin+size]
            return cache.read(address,size)
        globals()['mem']=joined""")


def static_failure_context(error,hook):
    """Bounded host-only failure location; no target read/write or retry."""
    frames=[];tb=error.__traceback__
    for _ in range(16):
        if tb is None:break
        frames.append(tb.tb_frame.f_code.co_name[:32]+':'+str(tb.tb_lineno));tb=tb.tb_next
    return (type(error).__name__+': '+str(error)[:64]+' | hook='+hook.name[:48]+
            ' | frames='+' > '.join(frames[-8:])+(' > truncated' if tb else ''))[:512]


def static_probe_observer(code):
    code=once(code,'if op!=9:pending[gen]=row;resume_hook.enabled=True','if op!=9:pending[gen]=row')
    code=once(code,'    resume_hook.enabled=False','    pass')
    code=once(code,"resume_hook=Hook('native_session_probe_return_site64',resume);resume_hook.enabled=False",
                   "resume_hook=ColdHook('native_session_probe_return_site64',resume)")
    for name,callback in (('request','syscall'),('denied','syscall_denied')):
        code=once(code,"Hook('native_session_probe_"+name+"_site64',"+callback+")",
                       "ColdHook('native_session_probe_"+name+"_site64',"+callback+")")
    adapter=inspect.getsource(static_failure_context)+inspect.getsource(admission.cpu.ReadOnlyCPUStops)
    adapter=once(adapter,"if self.failed is None:self.failed=(type(error).__name__+': '+str(error))[:512]",
                        'if self.failed is None:self.failed=static_failure_context(error,hook)')+"""
cpu_stops=ReadOnlyCPUStops(globals())
class ColdHook(gdb.Breakpoint):
    def __init__(self,name,callback):
        super().__init__('*'+hex(S[name]),internal=True,type=gdb.BP_HARDWARE_BREAKPOINT)
        self.name=name;self.callback=callback;self.fn=self.read_only
        cpu_stops.bind(self)
    def read_only(self):
        original=globals()['mem']
        def bounded(address,size):
            assert type(size) is int and 0<=size<32768,'static probe forbids QMP/large reads'
            return original(address,size)
        globals()['mem']=bounded
        try:
            assert reg('rip')==S[self.name],'static probe exact PC'
            caller=q(reg('rsp'));instruction=mem(caller-5,5)
            assert instruction[0]==232
            assert caller+struct.unpack('<i',instruction[1:])[0]==S[self.name.replace('_site64','64')],'static probe exact caller'
            drain()
            self.callback()
        finally:globals()['mem']=original
    def stop(self):return cpu_stops.stop(self)
"""
    return once(code,"resume_hook=ColdHook('native_session_probe_return_site64',resume)",
                     adapter+"\nresume_hook=ColdHook('native_session_probe_return_site64',resume)")


def retirement_probe_observer(code):
    code=once(code,"Hook('process_ipc_service64',cold_reap)","Hook('native_session_probe_terminal_site64',terminal_pending)")
    code=once(code,"Hook('native_cpu_trace_after64.full',cpu_trace_full)",'')
    code=once(code,"Hook('x86_64_scheduler_user_exception64',cold_fault)",
                   "Hook('native_session_probe_fault_site64',cold_fault)")
    code=once(code,"    cold_control_paths();fault()",
        "    assert reg('rip')==S['native_session_probe_fault_site64'] and not reg('eflags')&512\n"
        "    assert q(reg('rsp'))==S['process_run_exception64']+5\n"
        "    branch_target('process_run_exception64',0xe8,'native_session_probe_fault_site64')\n"
        "    cold_control_paths();fault()")
    callback='''
def terminal_pending():
    if mode()!=8:return
    assert reg('rip')==S['native_session_probe_terminal_site64'] and not reg('eflags')&512
    probe=S['family_terminal64.session_probe']
    assert q(reg('rsp'))==probe+5
    for address,target in ((probe,S['native_session_probe_terminal_site64']),(probe-5,S['native_pio_terminal64'])):
        raw=mem(address,5)
        assert raw[0]==232 and address+5+struct.unpack('<i',raw[1:])[0]==target
    caller=q(reg('rsp')+8)
    routes=((S['process_run_retire64']+0x81,S['process_run_retire64']+0xd4,S['process_run_retire64']+0xc4),
            (S['family_cancel_one64.removed']+0x66,S['family_cancel_one64.removed']+0x9d,S['family_cancel_one64.removed']+0x91))
    matches=[r for r in routes if r[0]==caller];assert len(matches)==1
    _,revoke,operation=matches[0]
    for address,target in ((caller-5,S['family_terminal64']),(revoke,S['process_ipc_service64'])):
        raw=mem(address,5)
        assert len(raw)==5 and raw[0]==232 and address+5+struct.unpack('<i',raw[1:])[0]==target
    assert mem(operation,5)==bytes((191,4,0,0,0))
    slot=d(S['scheduler_current_slot']);assert slot<8
    assert reg('r12')==S['scheduler_tasks']+slot*1024
    t=task(slot);gen=t[1];assert t[0] in (3,4) and 0<gen<1<<31
    receipt=struct.unpack('<4I',mem(S['process_run_receipt'],16))
    assert receipt[:2]==(slot,gen) and receipt[3]==t[0]
    assert len(release_pending)<8 and (slot,gen) not in release_pending
    release_pending.add((slot,gen));release_arm_hook.enabled=True
'''
    # Definition must precede construction of its Hook.
    return once(code,"Hook('native_session_probe_terminal_site64',terminal_pending)",callback+"\nHook('native_session_probe_terminal_site64',terminal_pending)")


def hybrid_probe_observer(code):
    """Static read-only stops; only TASK_CONTROL needs breakpoint mutation."""
    code=cached_probe_observer(static_probe_observer(code))
    code=once(code,'        cpu_stops.bind(self)',
                   "        service_stops.bind(self)\n        self.commands='silent\\npython hybrid_dispatch()\\ncontinue';self.silent=True")
    code=once(code,'    def stop(self):return cpu_stops.stop(self)', '''    def observe(self):
        globals()['callbacks']+=1
        assert callbacks<=8192,'hybrid callback capacity'
        self.read_only()
        return False
    def stop(self):
        try:
            slot=d(S['scheduler_current_slot']);assert slot<8
            if self.name=='native_session_probe_return_site64':
                row=pending.get(task(slot)[1]);deferred=bool(row and row['op']==132)
            else:deferred=q(S['syscall_rax'])==132
            if deferred:return service_stops.collect(self)
            return cpu_stops.stop(self)
        except BaseException as error:
            if cpu_stops.failed is None:cpu_stops.failed=(type(error).__name__+': '+str(error))[:512]
            return True''')
    return code+'''
def hybrid_dispatch():
    if cpu_stops.failed is not None:cpu_stops.fail()
    else:service_stops.drain()
'''


def command_probe_observer(code):
    """One command-context dispatcher for every cold probe, no stop-time reads."""
    return code+'''
def command_probe_stop(self):
    return service_stops.collect(self)

def command_probe_observe(self):
    try:
        globals()['callbacks']+=1
        assert callbacks<=8192,'command callback capacity'
        self.read_only()
        return False
    except BaseException as error:
        try:emit('OBSERVER_FAIL',where='command probe',error=static_failure_context(error,self))
        finally:gdb.execute('quit 71')
        raise

ColdHook.stop=command_probe_stop
ColdHook.observe=command_probe_observe
'''


def failure_only_probe_observer(code):
    """No healthy-path target access; preserve the original fatal decision."""
    code=once(code,"        try:emit('OBSERVER_FAIL',where='command probe',error=static_failure_context(error,self))",
                   "        try:\n            failure_only_snapshot(self)\n            emit('OBSERVER_FAIL',where='command probe',error=static_failure_context(error,self))")
    support='''
def failure_only_snapshot(hook):
    try:
        used=0
        def raw(address,size):
            nonlocal used
            used+=size
            assert 0<size<=1024 and used<=2048
            value=bytes(gdb.selected_inferior().read_memory(address,size))
            assert len(value)==size
            return value
        slot=struct.unpack('<I',raw(S['scheduler_current_slot'],4))[0];assert slot<8
        t=struct.unpack('<128Q',raw(S['scheduler_tasks']+slot*1024,1024))
        row=pending.get(t[1],{})
        data=dict(hook=hook.name,callback=callbacks,batch=service_stops.batches,slot=slot,
            task=[t[n] for n in (0,1,2,68,69,70,85,86,87)],
            registers={n:reg(n) for n in ('rip','rsp','rax','rcx','eflags')},
            tick=struct.unpack('<Q',raw(S['scheduler_last_tick'],8))[0],
            kernel_pending=raw(S['native_session_probe_pending'],8).hex(),
            syscall={n:struct.unpack('<Q',raw(S['syscall_'+n],8))[0]
                     for n in ('rax','rcx','rdi','rsi','rdx')},
            pending={n:row.get(n) for n in ('gen','op','args','entered','pointer','size','before')},
            request_hook=[hook.number,hook.enabled,hook.hit_count],
            return_hook=[resume_hook.number,resume_hook.enabled,resume_hook.hit_count])
        encoded=json.dumps(data,sort_keys=True);assert len(encoded)<=4096
        gdb.write('PENDING_FAILURE '+encoded+'\\n')
    except BaseException as error:
        gdb.write('PENDING_FAILURE_UNAVAILABLE '+(type(error).__name__+': '+str(error))[:256]+'\\n')
'''
    return once(code,'def command_probe_stop(self):',support+'\ndef command_probe_stop(self):')


def stepped_loop_observer(code):
    """Own batch continuation after a command-list step discards its tail."""
    return step_loop_tail(stepped_probe_observer(code))


def stepped_capture_namespace(started=None):
    """Install the loop after the unchanged shared binary-reader setup."""
    source=inspect.getsource(capture_namespace)
    source=once(source,'session_origin=origin)',
                       'session_origin=origin,session_step_loop=step_loop_tail)')
    replacement="    code=session_step_loop(code)\n    script=folder/'observe.gdb'"
    insertion=('        if function is boot._capture_run:\n'
               '            source=once(source,"    script=folder/\'observe.gdb\'",'+repr(replacement)+')\n')
    source=once(source,'        exec(compile(source,',insertion+'        exec(compile(source,')
    namespace=dict(globals());exec(compile(source,'<explicit-step capture factory>','exec'),namespace)
    return namespace['capture_namespace'](started)


def probe_exit_capture_namespace(started=None):
    """Diagnosis only: filtered TCG exits, unchanged step guards and bounded sink."""
    source=inspect.getsource(capture_namespace)
    source=once(source,'session_origin=origin)',
                       'session_origin=origin,session_step_loop=step_loop_tail)')
    source=once(source,
        "f'(not ({clause}) or halt_witness or service_cpu_budget or not service_pio_budget or trace_continuation)'",
        "f'(not ({clause}) or halt_witness or service_cpu_budget or not service_pio_budget)'")
    replacement="    code=session_step_loop(code)\n    script=folder/'observe.gdb'"
    old="        for event in CONTINUATION_EVENTS:command+=['-trace','enable='+event]"
    new=("        command+=['-d','exec','-dfilter','0xffffffff80110000+3']\n"
         "        for event in ('gdbstub_op_stepping','gdbstub_hit_break'):command+=['-trace','enable='+event]")
    insertion=('        if function is boot._capture_run:\n'
               '            source=once(source,"    script=folder/\'observe.gdb\'",'+repr(replacement)+')\n'
               '            source=once(source,'+repr(old)+','+repr(new)+')\n')
    source=once(source,'        exec(compile(source,',insertion+'        exec(compile(source,')
    temporary=dict(globals());exec(compile(source,'<filtered probe-exit capture>','exec'),temporary)
    namespace=temporary['capture_namespace'](started);original=namespace['capture']
    def capture(*args,**kwargs):
        if 'trace_continuation' in kwargs:raise ValueError('explicit diagnostic trace owns flag')
        return original(*args,**kwargs,trace_continuation=True)
    namespace['capture']=capture
    return namespace


def step_loop_tail(code):
    """Append only the existing loop, after every observer reader is ready."""
    if not code.endswith('\nend\ncontinue\n'):raise ValueError('explicit step outer batch tail')
    loop='''
def stepped_probe_loop():
    try:
        for _ in range(8192):
            before=cold_step_count
            assert 0<=before<8192,'outer step capacity'
            gdb.execute('continue')
            assert cold_step_count==before+1,'exactly one verified RET before next continue'
            assert not service_stops.pending and not service_stops.running and not service_stops.failed,'outer step dispatch idle'
        raise AssertionError('outer step capacity')
    except BaseException as error:
        try:emit('OBSERVER_FAIL',where='explicit step loop',error=(type(error).__name__+': '+str(error))[:256])
        finally:gdb.execute('quit 71')
        raise
'''
    return code[:-len('continue\n')]+'python\n'+loop+'\nstepped_probe_loop()\nend\n'


def stepped_probe_observer(code):
    """Diagnostic real RET stepping; no skipped callbacks or inferred returns."""
    code=once(code,'python hybrid_dispatch()','python stepped_probe_dispatch()')
    code=once(code,'    if runs==2:cpu_reader.finish();',
        "    if runs==2:gdb.write('COLD_STEP_END_V1 '+str(cold_step_count)+'\\n');cpu_reader.finish();")
    support='''
cold_step_count=0
cold_step_mode=None
def stepped_probe_dispatch():
    global cold_step_count,cold_step_mode
    try:
        assert not service_stops.running and not service_stops.failed
        assert len(service_stops.pending)==1,'single cold step decision'
        hook=service_stops.pending[0]
        assert isinstance(hook,ColdHook) and hook.is_valid() and hook.enabled
        assert 0<=cold_step_count<8192,'cold step capacity'
        if cold_step_mode is None:
            reply=gdb.execute('maintenance packet qqemu.sstep',to_string=True)
            assert len(reply)<=256 and reply.splitlines()==['sending: qqemu.sstep','received: "0x7"'],'fixed QEMU step mode'
            cold_step_mode=7
        pc=reg('rip');sp=reg('rsp')
        assert pc==S[hook.name] and not reg('eflags')&512
        inferior=gdb.selected_inferior()
        assert bytes(inferior.read_memory(pc,1))==b'\\xc3','exact native RET probe'
        target=struct.unpack('<Q',bytes(inferior.read_memory(sp,8)))[0]
        names=('rax','rbx','rcx','rdx','rsi','rdi','rbp','r8','r9','r10','r11','r12','r13','r14','r15','eflags','cr3')
        before={n:reg(n) for n in names}
        hybrid_dispatch()
        assert not service_stops.pending and not service_stops.running and not service_stops.failed
        assert reg('rip')==pc and reg('rsp')==sp and {n:reg(n) for n in names}==before
        hook.enabled=False
        try:
            cold_step_count+=1
            output=gdb.execute('stepi',to_string=True)
            assert len(output)<=512,'bounded step output'
            assert reg('rip')==target and reg('rsp')==sp+8,'actual one-RET progress'
            assert {n:reg(n) for n in names}==before,'RET preserves CPU state'
            assert not service_stops.pending and not service_stops.running and not service_stops.failed,'unexpected step callback'
        finally:hook.enabled=True
        site=tuple('native_session_probe_'+n+'_site64' for n in ('request','denied','return')).index(hook.name)
        record=dict(step=cold_step_count,site=site,pc=pc,target=target,sp=sp,after_sp=reg('rsp'))
        encoded=json.dumps(record,sort_keys=True,separators=(',',':'));assert len(encoded)<=192
        gdb.write('COLD_STEP_V1 '+encoded+'\\n')
    except BaseException as error:
        try:emit('OBSERVER_FAIL',where='explicit cold step',error=(type(error).__name__+': '+str(error))[:256])
        finally:gdb.execute('quit 71')
        raise
'''
    return once(code,'def command_probe_stop(self):',support+'\ndef command_probe_stop(self):')


def persistent_target_observer(code):
    """Diagnostic transport optimization, only with actual return-target proof."""
    if "target_hook.hit_count==1,'actual single RET target hit'" not in code:
        raise ValueError('persistent insertion requires actual target proof')
    return once(code,'set breakpoint always-inserted off\n','set breakpoint always-inserted on\n')


def return_target_observer(code):
    """Diagnostic actual RET proof using one temporary-owned hardware target."""
    code=once(code,'        hook.enabled=False\n        try:',
                   '        hook.enabled=False\n        target_hook=None\n        try:')
    code=once(code,"            output=gdb.execute('stepi',to_string=True)",
        "            target_hook=gdb.Breakpoint('*0x%x'%target,type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)\n"
        "            assert target_hook.is_valid() and target_hook.enabled and target_hook.hit_count==0,'fresh RET target'\n"
        "            assert len(target_hook.locations)==1 and target_hook.locations[0].address==target,'exact RET target location'\n"
        "            output=gdb.execute('continue',to_string=True)\n"
        "            assert target_hook.is_valid() and target_hook.hit_count==1,'actual single RET target hit'")
    code=once(code,'        finally:hook.enabled=True',
        '        finally:\n'
        '            try:\n'
        '                if target_hook is not None and target_hook.is_valid():target_hook.delete()\n'
        '            finally:hook.enabled=True')
    return code


def transient_probe_observer(code):
    """Diagnostic isolation of GDB's standard remove-on-stop insertion mode."""
    return once(code,'set breakpoint always-inserted on\n','set breakpoint always-inserted off\n')


def ticket_probe_observer(code):
    """Independent kernel request identity; never skips a callback or guard."""
    code=failure_only_probe_observer(code)
    code=once(code,"    emit('call',**row)",
        "    if slot==0 and op==15:\n"
        "        row['read_ticket']=list(struct.unpack('<2Q',mem(S['native_session_read_tickets'],16)))\n"
        "        assert 0<row['read_ticket'][0]<=8192 and 0<=row['read_ticket'][1]<=8192\n"
        "    emit('call',**row)")
    code=once(code,"('gen','op','args','entered','pointer','size','before')",
                   "('gen','op','args','entered','pointer','size','before','read_ticket')")
    code=once(code,'        encoded=json.dumps(data,sort_keys=True);assert len(encoded)<=4096',
        "        data['read_ticket']=list(struct.unpack('<2Q',raw(S['native_session_read_tickets'],16)))\n"
        '        encoded=json.dumps(data,sort_keys=True);assert len(encoded)<=4096')
    return code


class ProbeAudit:
    """Diagnostic-only last sixteen stops; never supplies a missing completion."""
    def __init__(self,sample,write):
        self.sample=sample;self.write=write;self.rows=[];self.total=0;self.closed=False

    def record(self,hook):
        if self.closed:raise ValueError('probe audit closed')
        if self.total>=8192:raise ValueError('probe audit event capacity')
        row=self.sample(hook)
        if len(json.dumps(row))>4096:raise ValueError('probe audit record capacity')
        self.total+=1
        if len(self.rows)==16:self.rows.pop(0)
        self.rows.append(row)

    def dump(self):
        if self.closed:return
        self.closed=True
        self.write('PROBE_AUDIT '+json.dumps(dict(total=self.total,rows=self.rows),sort_keys=True)+'\n')


def audit_probe_observer(code):
    """Read-only stop snapshots plus bounded late-session GDB infrun logging."""
    code=once(code,'            drain()\n            self.callback()',
                   '            drain()\n            if probe_debug_armed:probe_audit.record(self)\n            self.callback()')
    code=once(code,"        try:emit('OBSERVER_FAIL',where='command probe',error=static_failure_context(error,self))",
                   "        try:\n            probe_audit.dump()\n            emit('OBSERVER_FAIL',where='command probe',error=static_failure_context(error,self))")
    code=once(code,'def finish():\n    global runs',
                   'def finish():\n    global runs\n    if runs==1:probe_audit.dump()')
    support=inspect.getsource(ProbeAudit)+'''
probe_debug_armed=False
probe_debug_count=0
def probe_audit_arm():
    gdb.execute('maintenance packet qqemu.sstep')
    gdb.execute('set debug infrun 1')
original_probe_complete=complete
def probe_audit_complete(slot,t):
    global probe_debug_armed
    row=pending.get(t[1])
    value=original_probe_complete(slot,t)
    if (not probe_debug_armed and runs==1 and slot==0 and row and row['op']==20 and
            row.get('result')==row['size'] and bytes.fromhex(row['before']).endswith(b'  history\\n')):
        probe_debug_armed=True
        probe_audit_arm()
    return value
complete=probe_audit_complete
def probe_audit_sample(hook):
    global probe_debug_count
    slot=d(S['scheduler_current_slot']);assert slot<8
    t=task(slot);row=pending.get(t[1],{})
    if probe_debug_armed:
        probe_debug_count+=1
        if probe_debug_count==64:gdb.execute('set debug infrun 0')
    return dict(hook=hook.name,callback=callbacks,batch=service_stops.batches,slot=slot,
        task=[t[n] for n in (0,1,68,69,70,85,86,87)],tick=q(S['scheduler_last_tick']),
        registers={n:reg(n) for n in ('rip','rsp','rax','rcx','eflags')},
        syscall={n:q(S['syscall_'+n]) for n in ('rax','rcx','rdi','rsi','rdx')},
        kernel_pending=mem(S['native_session_probe_pending'],8).hex(),
        pending_op=row.get('op'),return_hook=[resume_hook.number,resume_hook.enabled,resume_hook.hit_count],
        request_hook=[hook.number,hook.enabled,hook.hit_count])
probe_audit=ProbeAudit(probe_audit_sample,gdb.write)
'''
    return once(code,'class ColdHook(gdb.Breakpoint):',support+'\nclass ColdHook(gdb.Breakpoint):')


def watch_pending_observer(code):
    """Root-byte hardware watch only at the previously failing late boundary."""
    code=once(code,"            probe_audit.dump()\n            emit('OBSERVER_FAIL'",
                   "            pending_watch_audit.dump()\n            probe_audit.dump()\n            emit('OBSERVER_FAIL'")
    code=once(code,'    if runs==1:probe_audit.dump()',
                   '    if runs==1:pending_watch_audit.dump();probe_audit.dump()')
    support='''
pending_watch=None
def pending_watch_sample(hook):
    slot=d(S['scheduler_current_slot'])
    return dict(hook='pending_write',slot=slot,
        gen=q(S['scheduler_tasks']+slot*1024+8) if slot<8 else None,
        pc=reg('rip'),flags=reg('eflags'),tick=q(S['scheduler_last_tick']),
        kernel_pending=mem(S['native_session_probe_pending'],8).hex(),
        op=q(S['syscall_rax']),batch=service_stops.batches,callback=callbacks,
        hit=hook.hit_count,type=hook.type,enabled=hook.enabled)
pending_watch_audit=ProbeAudit(pending_watch_sample,
    lambda raw:gdb.write(raw.replace('PROBE_AUDIT ','PENDING_AUDIT ',1)))
original_probe_audit_sample=probe_audit.sample
original_probe_audit_arm=probe_audit_arm
def watched_probe_arm():
    global pending_watch
    assert probe_debug_armed and pending_watch is None,'single late audit arm'
    original_probe_audit_arm()
    assert mem(S['native_session_probe_pending'],1)==b'\\x00','idle root pending before watch'
    pending_watch=PendingWatch()
probe_audit_arm=watched_probe_arm
def watched_probe_sample(hook):
    row=original_probe_audit_sample(hook)
    row['pending_watch_total']=pending_watch_audit.total
    return row
probe_audit.sample=watched_probe_sample
class PendingWatch(gdb.Breakpoint):
    def __init__(self):
        assert S['native_session_probe_pending']%8==0
        super().__init__('*(unsigned char*)'+hex(S['native_session_probe_pending']),
                         type=gdb.BP_WATCHPOINT,wp_class=gdb.WP_WRITE,internal=True)
        service_stops.bind(self)
    def stop(self):return service_stops.collect(self)
    def observe(self):
        assert self.type==gdb.BP_HARDWARE_WATCHPOINT,'hardware pending watch required'
        globals()['callbacks']+=1
        assert callbacks<=8192,'watch callback capacity'
        pending_watch_audit.record(self)
        return False
'''
    return once(code,'class ColdHook(gdb.Breakpoint):',support+'\nclass ColdHook(gdb.Breakpoint):')


def hardware_probe_observer(code):
    return once(code,"super().__init__('*'+hex(S[name]),internal=True);self.fn=fn",
        "super().__init__('*'+hex(S[name]),internal=True,type=(gdb.BP_HARDWARE_BREAKPOINT if name in "
        "tuple('native_session_probe_'+n+'_site64' for n in ('request','denied','return','start','pio','terminal','fault')) else gdb.BP_BREAKPOINT));self.fn=fn")


def cold_probe_pc_diagnostic(code):
    return once(code,'            self.fn()',
        "            names={'syscall':'request','syscall_denied':'denied','resume':'return','start':'start'}\n"
        "            if self.fn.__name__ in names:\n"
        "                expected=S['native_session_probe_'+names[self.fn.__name__]+'_site64'];actual=reg('rip')\n"
        "                caller=q(reg('rsp'));instruction=mem(caller-5,5);assert instruction[0]==232\n"
        "                target=caller+struct.unpack('<i',instruction[1:])[0];helper=S['native_session_probe_'+names[self.fn.__name__]+'64']\n"
        "                gdb.write('PROBE_PC '+json.dumps(dict(callback=self.fn.__name__,actual=actual,expected=expected,caller=caller,target=target,helper=helper))+'\\n')\n"
        "                assert actual==expected,'PROBE_PC_MISMATCH'\n"
        "                assert target==helper,'PROBE_CALLER_MISMATCH'\n"
        "            self.fn()")


def observer(config,records,folder,case,layout,diagnostic=False,probe_pc=False,hardware_probes=False,static_probes=False,lifecycle_probes=False):
    if type(diagnostic) is not bool or diagnostic and (case,layout)!=(0,0):
        raise ValueError('session diagnostic fixed healthy case')
    if type(probe_pc) is not bool or probe_pc and not diagnostic:raise ValueError('PC diagnostic only')
    if type(hardware_probes) is not bool or hardware_probes and not probe_pc:raise ValueError('hardware diagnostic only')
    if type(static_probes) is not bool or static_probes and not hardware_probes:raise ValueError('static diagnostic only')
    if type(lifecycle_probes) is not bool or lifecycle_probes and (not hardware_probes or static_probes):raise ValueError('lifecycle deferred diagnostic only')
    if (case,layout,8192 if case==5 else 4096) not in CASES:raise ValueError('session observer case/layout')
    references={}
    for slot,raw in records.items():
        if slot not in (2,3,4) or len(raw)!=266336:raise ValueError('session observer record')
        path=folder/f'prepared-{slot}.bin'
        with path.open('xb') as stream:
            if stream.write(raw)!=len(raw):raise OSError('session record write')
        references[slot]=dict(path=path.as_posix(),sha256=hashlib.sha256(raw).hexdigest())
    if set(references)!={2,3,4}:raise ValueError('session all executable bindings')
    settings=dict(config,out=folder.as_posix(),case=case,layout=layout,records=references)
    body=observer_body() if not diagnostic or probe_pc else diagnostic_observer_body(2)
    if probe_pc:body=cold_probe_pc_diagnostic(body)
    if hardware_probes:body=hardware_probe_observer(body)
    if static_probes:body=cached_probe_observer(static_probe_observer(body))
    if lifecycle_probes:body=hybrid_probe_observer(retirement_probe_observer(lifecycle_probe_observer(body)))
    if not diagnostic:
        body=command_probe_observer(hybrid_probe_observer(retirement_probe_observer(lifecycle_probe_observer(hardware_probe_observer(cold_probe_pc_diagnostic(body))))))
        body=return_target_observer(stepped_probe_observer(body))
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+
        '\nZERO_RANGES='+repr(admission.ZERO_RANGES)+'\n'+
        body+'\nend\ncontinue\n')


def require(value,message):
    if not value:raise ValueError('shell session '+message)

def ipc_message(raw):
    """Decode the complete captured ABI object, including unused bytes."""
    require(type(raw) is bytes and len(raw) in (140,2060),'IPC object extent')
    version,size,length=struct.unpack_from('<3I',raw)
    require((version,size)==((1,140) if len(raw)==140 else (2,2060)) and
            length<=size-12 and not any(raw[12+length:]),'IPC canonical envelope')
    return raw[12:12+length]


def fs_request_frame(raw):
    require(type(raw) is bytes and len(raw)==512,'FS request frame extent')
    version,size,op,flags,length,result=struct.unpack_from('<6I',raw)
    require((version,size,flags,result)==(1,512,0,0) and op in (5,6,7) and 0<length<192,'FS request fields')
    offset={5:24,6:36,7:28}[op];path=raw[offset:offset+length]
    require(path.startswith(b'/') and b'\0' not in path,'FS absolute path')
    canonical=bytearray(512);struct.pack_into('<6I',canonical,0,1,512,op,0,length,0)
    canonical[offset:offset+length]=path
    if op==6:
        position,requested,transferred=struct.unpack_from('<3I',raw,24)
        require(1<=requested<=256 and not transferred,'FS read request capacity')
        struct.pack_into('<2I',canonical,24,position,requested)
    elif op==7:canonical[24:28]=raw[24:28]
    require(raw==canonical,'FS request unused bytes')
    return op,path


def fs_expected_response(request,layout,app):
    """Independent oracle for the sole file on the immutable generated disk."""
    require(type(layout) is int and layout in range(5) and type(app) is bytes and
            64<=len(app)<=1280,'FS generated medium parameters')
    op,path=fs_request_frame(request)
    file_name=b'BOOT.PRG' if layout<2 else b'boot.prg'
    root=path==b'/';found=(path.upper()==b'/BOOT.PRG' if layout<2 else path==b'/boot.prg')
    if not root and not found:return -2,b''
    result=bytearray(request);status=0
    if op==6:
        if root:return -21,b''
        position,requested=struct.unpack_from('<2I',request,24);data=app[position:position+requested]
        struct.pack_into('<I',result,32,len(data));result[228:228+len(data)]=data
    else:
        if op==7 and not root:return -20,b''
        if op==7 and struct.unpack_from('<I',request,24)[0]:status=1
        else:
            at=216 if op==5 else 220;is_root=op==5 and root
            name=b'/' if is_root else file_name
            result[at:at+len(name)]=name
            size=(0 if layout<2 else 1024<<(layout-2)) if is_root else len(app)
            struct.pack_into('<5I',result,at+256,2 if is_root else 1,size,0,0,0)
    struct.pack_into('<I',result,20,status)
    return status,bytes(result)


def validate_ipc_delivery(events):
    """Match actual sends, allowing a receiver to resume before its sender."""
    sends=[];receives=[];order=0;invocations={}
    for row in events:
        if row['kind']=='call':
            invocations[row['gen']]=order;order+=1
        if row['kind'] not in ('return','abandoned') or row['op'] not in (50,51,53,54):continue
        require(not row['profile_denied'],'service IPC authority')
        require(not any(row['args'][3:]) and (row['op']<53 or 0<row['args'][2]<=1000),'IPC bounded syscall')
        if row['kind']=='abandoned':continue
        result=row['result'];before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after'])
        require(result in (0,-9,-11,-32,-110,-116,-3,-13),'IPC result domain')
        if row['op'] in (50,53):
            require(after==before,'IPC send immutable input')
            payload=ipc_message(before)
            if not result:sends.append((invocations[row['gen']],row['args'][0],payload,row['gen']))
        elif result:require(after==before,'IPC receive failure nonpublication')
        else:receives.append((invocations[row['gen']],row['args'][0],ipc_message(after),row['gen'],order))
    used=set()
    for _,endpoint,payload,gen,completed in receives:
        candidates=[n for n,(entered,ep,data,sender) in enumerate(sends)
                    if n not in used and ep==endpoint and data==payload and sender!=gen and entered<completed]
        require(len(candidates)==1,'IPC receive exact live sender/endpoint/bytes');used.add(candidates[0])
    return sends,receives


def physical_oracle(layout,app):
    medium=file.media.image(file.media.LAYOUTS[layout],program=app);sectors=len(medium)//512
    ns=dict(struct=struct,devices={},pio_owner=0,physical_events=0,CONFIG=dict(sectors=sectors),
            expected_sector=lambda lba:medium[lba*512:(lba+1)*512],emit=lambda *a,**k:None)
    exec(file.block.TRACE_CORE,ns)
    for name in ('out','data'):exec(admission.source_node(file.fs.EXTRA,name),ns)
    return ns


def validate_storage(events,raw,layout,app,case):
    """Reconstruct physical ATA reads and both IPC protocol layers."""
    ns=physical_oracle(layout,app);sectors=ns['CONFIG']['sectors']
    starts={};live={};sequence=0;ended=set();cleared=set();health={};controls={}
    requests={};replies={};fs_sequence={};bad_replies=[];block_requests={};driver_faults=set()
    validate_ipc_delivery(events)
    for row in events:
        kind=row['kind']
        if kind=='start':
            starts[row['gen']]=row;live[row['slot']]=row['gen']
            if row['slot'] in (2,3):
                require(len(row['args'])==2 and all(re.fullmatch('[0-9a-f]{8}',s) for s in row['args']),'service startup words')
                options=int(row['args'][1],16)
                require(options>>8==layout and options&255 in (0,1,2,4,5,6),'service exact profile/options')
        elif kind=='pio':
            require(row['previous']==sequence and row['run'] not in ended,'PIO continuous generation trace')
            for event in ns['trace_decode'](raw.read(row['raw'],12304),sequence):
                owner=event[2][0];require(owner>>32==live.get(2),'PIO live driver')
                (ns['out'] if event[0]==1 else ns['data'])(event);sequence=event[1]
        elif kind=='pio_end':
            require(row['run'] not in ended and row['sequence']==sequence>0,'PIO complete run');ended.add(row['run'])
        elif kind=='pio_clear':
            require(row['run'] in ended-cleared,'PIO clear order');ns['trace_clean'](raw.read(row['raw'],12304))
            cleared.add(row['run']);sequence=0
        elif kind=='fenced' and row['slot']==2:
            owner=(row['gen']<<32)|2;device=ns['devices'].get(owner)
            if device is not None:
                state=struct.unpack('<8Q',bytes.fromhex(row['pio']))
                require(state[0]==owner and state[2]==1 and not device['retired'],'PIO final physical fence')
                require(device['reset'] and device['released'] and len(device['identify'])==512,'ATA initialized before retirement')
                require(struct.unpack_from('<H',device['identify'],98)[0]&512 and
                        struct.unpack_from('<I',device['identify'],120)[0]==sectors,'ATA actual capacity')
                expected=b''.join(ns['expected_sector'](lba) for lba in device['lbas'])
                require(bytes(device['data'])==expected[:len(device['data'])],'ATA complete immutable byte stream')
                options=int(starts[row['gen']]['args'][1],16)&255
                partial=options in (5,6)
                require(len(device['data'])==(768 if partial else len(expected)),'ATA selected physical completion boundary')
                if partial:driver_faults.add(row['gen'])
                device['retired']=True
        elif kind=='release':
            require(live.get(row['slot'])==row['gen'],'storage retirement identity');del live[row['slot']]
        elif kind=='service_ready':
            payload=ipc_message(bytes.fromhex(row['control']))
            require(len(payload)==48 and row['gen'] not in health,'one service health publication')
            owner,peer,deadline,rq,rp,count,phase,status,reserved=struct.unpack('<3Q4IiI',payload)
            require(owner==(row['gen']<<32)|row['slot'] and count==sectors and rq and rp and rq!=rp and not reserved,'health identity/channels')
            service=raw.read(row['raw'],128 if row['slot']==2 else 8400)
            if row['slot']==2:
                require(phase==2 and not status and struct.unpack_from('<2Q',service)==(owner,1) and
                        struct.unpack_from('<3I',service,24)==(sectors,0,1) and
                        struct.unpack_from('<4IQ',service,104)==(1,24,16,0,deadline),'driver health actual state')
            else:
                require(phase==4 and struct.unpack_from('<4I3Q',service)==
                        (1,40,1 if layout<2 else 2,sectors,owner,peer,deadline),'FS health actual profile')
                calls,ready,failed,busy,used=struct.unpack_from('<5I',service,120)
                require(not calls and not busy,'FS health before requests')
                if status:
                    require(-4095<=status<0 and (ready,failed,used)==(0,1,0) and not any(service[140:]),'FS failed selftest')
                else:
                    require((ready,failed,used)==(2,0,1 if layout<2 else 4) and
                            struct.unpack_from('<2Q',service,40)==(peer,used),'FS successful actual cache selftest')
            health[row['gen']]=status
        elif kind=='call' and row['op'] in (50,53) and not row['profile_denied']:
            data=ipc_message(bytes.fromhex(row['before']));slot=row['slot'];gen=row['gen'];now=row['entered']
            if len(data)==48:
                owner,peer,deadline,rq,rp,count,phase,status,reserved=struct.unpack('<3Q4IiI',data)
                require(not reserved and phase in (1,2,3,4,9),'control reserved/phase')
                if phase==9:
                    require(slot==2 and case==8 and row['run']==1 and
                            (owner,peer,deadline,rq,rp,count,status)==((gen<<32)|2,0,0,0,0,0,0),'hang notice actual owner')
                else:
                    require(slot==({1:0,2:2,3:0,4:3}[phase]) and owner==((live[2 if phase<3 else 3]<<32)|(2 if phase<3 else 3)) and
                            peer&0xffffffff==(3 if phase<3 else 2) and peer>>32 in starts and
                            starts[peer>>32]['parent']==starts[owner>>32]['parent'],'control actual dependency pair')
                    # A driver fault may already be reaped when FS reports its
                    # failed self-test; the immutable phase-1 pair still binds it.
                    pair=controls.get((owner if phase<3 else peer,1))
                    if phase!=1:
                        require(pair is not None and struct.unpack_from('<2Q',pair)==
                                ((owner,peer) if phase<3 else (peer,owner)),'control original dependency generation')
                    key=(owner,phase);require(key not in controls,'control publication once');controls[key]=data
                    if phase==1:require(not any((deadline,rq,rp,count,status)),'initial control canonical')
                    else:
                        require(now<deadline<=now+2800 and rq and rp and rq!=rp and count==sectors,'control finite profile')
                        previous=controls.get((peer,2)) if phase==3 else controls.get((owner,3)) if phase==4 else None
                        if phase in (3,4):
                            require(previous is not None,'health ordered dependencies')
                            fields=struct.unpack('<3Q4IiI',previous)
                            require((deadline,rq,rp,count)==fields[2:6],'immutable dependency deadline/channels')
                        if phase!=4:require(not status,'healthy control request')
                continue
            require(len(data) in (64,576),'storage protocol message extent')
            h=struct.unpack_from('<4I4QIiQ',data);owner=h[4];key=(owner,h[5])
            if slot==3 and row['size']==140:
                require(h[:4]==(1,64,1,0) and h[8:]==(512,0,0) and owner==(live[2]<<32)|2,'block request ABI/owner')
                device=ns['devices'][owner]
                require(h[5]==device['requests']+1<=16 and h[6]<sectors and now<h[7]<=now+1000 and device['pending'] is None,'block request sequence/deadline')
                device['requests']+=1;device['pending']=(h,len(device['data']))
                block_requests[key]=row
            elif slot==2:
                require(owner==(gen<<32)|2 and key in block_requests,'block reply owner/request')
                device=ns['devices'][owner];previous,before=device['pending']
                require(h[:5]==(1,64,1,1,owner) and h[5:8]==previous[5:8] and h[8:]==(512,0,0) and
                        len(data)==576 and len(device['data'])==before+512 and
                        data[64:]==bytes(device['data'][-512:])==ns['expected_sector'](h[6]),'block reply physical byte equality')
                device['pending']=None
            elif slot==0:
                require(h[:2]==(1,64) and h[2] in (5,6,7) and not h[3] and h[7:]==(0,512,0,0) and len(data)==576,'FS request ABI')
                require(owner==(live[3]<<32)|3 and health.get(live[3])==0 and h[5]==fs_sequence.get(owner,0)+1<=8 and
                        now<h[6]<=now+1000 and key not in requests,'FS healthy owner/sequence/deadline')
                require(fs_request_frame(data[64:])[0]==h[2],'FS operation/frame match')
                requests[key]=(h,data[64:],row);fs_sequence[owner]=h[5]
            else:
                require(slot==3,'FS reply source')
                actual=(gen<<32)|3;key=(actual,h[5]);require(key in requests and key not in replies,'FS reply matched once')
                previous,frame,request=requests[key]
                malformed=bool(int(starts[gen]['args'][1],16)&255==4)
                require(h[:4]==(1,64,previous[2],1) and owner==actual^int(malformed) and h[5:8]==previous[5:8] and not h[10],'FS reply immutable binding')
                status,answer=fs_expected_response(frame,layout,app)
                require(h[9]==status and h[8]==len(answer) and len(data)==64+len(answer) and data[64:]==answer,'FS reply actual media metadata/data')
                if malformed:bad_replies.append(row)
                replies[key]=row
    require(ended==cleared=={1,2} and ns['devices'] and all(d['retired'] for d in ns['devices'].values()),'complete physical storage lifecycle')
    require(len(driver_faults)==int(case in (7,8)) and len(bad_replies)==int(case==11),'selected storage fault occurred')
    for run in (1,2):
        require(any(r['run']==run and requests[k][0][2]==7 for k,r in replies.items()),'real directory RPC per root')
    return dict(devices=len(ns['devices']),fs_requests=len(requests),fs_replies=len(replies),physical_events=ns['physical_events'])


def validate_io_and_faults(events,receipts,case,attempts,policies,faults):
    starts={r['gen']:r for r in events if r['kind']=='start'}
    returned=[r for r in events if r['kind']=='return']
    denied=[r for r in events if r['kind']=='io' and r.get('profile_denied',False)]
    require(all(r['slot'] in (1,2,3) and r['op'] in (15,20) and r['result']==-13 and
                not r['size'] and r['before']==r['after']=='' for r in denied),'denied service console before access')
    for gen,start in starts.items():
        if start['slot'] in (1,2,3):
            require([r['op'] for r in denied if r['gen']==gen]==[15,20],'actual service/peer console denial')
    io=[r for r in events if r['kind']=='io' and not r.get('profile_denied',False)]
    require(all(r['slot'] in (0,4) and r['fd']==int(r['op']==20) and
                not any(r['unused']) and r['op'] in (15,20) for r in io),'console attenuated roles')
    for row in io:
        before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after']);result=row['result']
        require(len(before)==len(after)==row['size'] and 0<row['size']<=64 and
                (result==-11 or 0<result<=row['size']),'console exact partial result')
        require(after==before if row['op']==20 or result<0 else after[result:]==before[result:],'console untouched bytes')
        require(row['slot']==0 or row['op']==20,'ordinary app cannot consume command input')
    for run in (1,2):
        root=next(r for r in starts.values() if r['run']==run and r['slot']==0)
        root_io=[r for r in io if r['gen']==root['gen']]
        incoming=b''.join(bytes.fromhex(r['after'])[:r['result']] for r in root_io if r['op']==15 and r['result']>0)
        output=b''.join(bytes.fromhex(r['before'])[:r['result']] for r in root_io if r['op']==20 and r['result']>0)
        require(incoming==b''.join(data for _,data in input_plan(case)[run-1]),'actual complete command input')
        require(output.startswith(BANNER.encode()) and output.count(BANNER.encode())==1,'actual normal shell banner')
        apps=[r for r in starts.values() if r['run']==run and r['slot']==4]
        expected_count=4 if case==6 and run==1 else 0 if case==16 and run==1 else 1
        require(len(apps)==expected_count,'actual foreground construction count')
        for app_start in apps:
            gen=app_start['gen'];receipt=receipts[gen]
            expected=(134,3) if case==12 and run==1 else (256,3) if case==13 and run==1 else (0,3) if case in (14,15) and run==1 else (82,4)
            require((receipt['status'],receipt['state'])==expected,'ordinary foreground actual outcome')
            written=b''.join(bytes.fromhex(r['before'])[:r['result']] for r in io if r['gen']==gen and r['op']==20 and r['result']>0)
            require(written==(b'SESSION64\n' if expected==(82,4) else b''),'ordinary foreground byte stream')
            if case==15 and run==1:continue
            waits=[];cancels=[]
            for r in returned:
                if r['gen']!=root['gen'] or r['op']!=132:continue
                request=bytes.fromhex(r['before']);operation=struct.unpack_from('<I',request,8)[0]
                if struct.unpack_from('<Q',request,16)[0]!=(gen<<32)|4:continue
                if operation==2:
                    require(struct.unpack_from('<Q',request,32)[0]==1000,'foreground WAIT deadline');waits.append(r['result'])
                elif operation==3:cancels.append(r['result'])
            reason=0 if expected[1]==4 else 2 if case==14 and run==1 else 1
            receipt_value=(reason<<32)|expected[0]
            require(waits==([-110,receipt_value] if case==14 and run==1 else [receipt_value]) and
                    cancels==([0] if case==14 and run==1 else []),'foreground timeout/cancel/reap sequence')
            require(any(r['gen']==root['gen'] and r['op']==114 and r['args'][1]==gen and r['result']==-3 for r in returned) and
                    any(r['gen']==root['gen'] and r['op']==127 and r['result']==-116 and
                        struct.unpack_from('<2I',bytes.fromhex(r['before']),16)==(gen,gen) for r in returned),'actual stale child identity/lease rejection')
        policy=policies.get(root['gen']);require(policy is not None,'root final policy proof')
        require(policy[6:]==((2,1) if case==16 and run==1 else (1,0) if case in range(7,12) and run==1 else (0,0)),
                'exact automatic recovery budget/degraded outcome')
        if case==6 and run==1:
            reads=[r for r in root_io if r['op']==15 and r['result']>0]
            require(reads and reads[0]['now']-root['now']>=5000 and attempts.get(root['gen'],0)>8,'persistent idle and cumulative construction proof')
    expected_faults={7:[2],9:[3],12:[4],15:[0],16:[3,3,3]}.get(case,[])
    require([r['slot'] for r in faults]==expected_faults and all(r['run']==1 for r in faults),'actual selected UD2 sequence')
    for gen,start in starts.items():
        if start['slot'] not in (2,3):continue
        receipt=receipts[gen];outcome=(receipt['status'],receipt['state'])
        if any(r['gen']==gen for r in faults):require(outcome==(134,3),'service fault receipt')
        elif outcome==(90,4):
            require(any(r['kind']=='service_ready' and r['gen']==gen and
                        struct.unpack_from('<i',bytes.fromhex(r['control']),52)[0]<0 for r in events),'failed initialization receipt')
        elif outcome==(245,4):
            require(start['slot']==3 and any(r['gen']==gen and r['op']==54 and r['result']==-110 for r in returned),'finite FS receive timeout receipt')
        else:require(outcome==(0,3),'planned/isolated service cancellation')
    oom=[r for r in events if r['kind']=='oom'];rollback=[r for r in events if r['kind']=='rollback']
    require(len(oom)==len(rollback)==int(case==17),'selected OOM occurs once')
    if oom:
        a,b=oom[0],rollback[0]
        require(a['run']==b['run']==1 and a['slot']==b['slot']==3 and a['acquired']==3 and
                b['before']==b['free']==a['free']+3,'partial OOM full frame rollback')
        require(sum(r['op']==132 and r['result']==-12 for r in returned)==1,'actual OOM caller result')
    else:require(not any(r['op']==132 and r['result']==-12 for r in returned),'no unexpected allocation failure')
    for fault_case,slot in ((8,2),(10,3)):
        if case!=fault_case:continue
        failed=[s for s in starts.values() if s['run']==1 and s['slot']==slot and int(s['args'][1],16)&255]
        require(len(failed)==1,'one hanging service generation')
        gen=failed[0]['gen'];root=failed[0]['parent']>>32
        require(any(r['gen']==root and r['op']==54 and r['result']==-110 for r in returned),'hang detected by actual bounded IPC timeout')
        require((receipts[gen]['status'],receipts[gen]['state'])==(0,3),'hang isolated by cancellation')


def validate_oom_pause(events,case):
    """Real blocking sleep before OOM, not an exemption from denial proofs."""
    pauses=[(n,r) for n,r in enumerate(events) if r['kind']=='return' and r['op']==41]
    require(len(pauses)==int(case==17),'one selected OOM fixture pause')
    if case!=17:return
    end,pause=pauses[0];gen=pause['gen']
    require(pause['slot']==0 and pause['run']==1 and pause['args']==[100,0,0,0,0,0] and
            pause['result']==0 and 100<=pause['now']-pause['entered']<1000,
            'OOM fixture bounded sleep result/time')
    calls=[n for n,r in enumerate(events[:end]) if r['kind']=='call' and r['gen']==gen and r['op']==41]
    require(len(calls)==1,'OOM fixture matched sleep request')
    begin=calls[0]
    drivers=[r for r in events[:begin] if r['kind']=='start' and r['slot']==2 and r['run']==1]
    require(len(drivers)==2,'OOM fixture second driver generation')
    driver=drivers[-1]['gen']
    denied=[(n,r) for n,r in enumerate(events[:end]) if r['kind']=='io' and
            r['gen']==driver and r.get('profile_denied',False)]
    require([r['op'] for _,r in denied]==[15,20] and all(r['result']==-13 for _,r in denied),
            'OOM driver probes precede FS failure')
    require(not any(r['kind']=='cpu_charge' and r['gen']==gen and
                    pause['entered']<r['now']*10<pause['entered']+100 for r in events),
            'OOM root has no CPU charges during blocked interval')
    oom=[n for n,r in enumerate(events) if r['kind']=='oom']
    require(len(oom)==1 and end<oom[0],'OOM injected only after blocked pause')


def validate_cpu(events,receipts):
    """Every raw charge, anchored CPU window and terminal receipt must agree."""
    starts={};last={};finished=set();charges={};run_ticks={};released=set()
    for row in events:
        kind=row['kind']
        if kind=='start':
            gen=row['gen'];require(gen not in starts,'duplicate CPU owner')
            starts[gen]=row;charges[gen]=0
        elif kind in ('cpu_start','cpu_charge','cpu_final'):
            gen=row['gen'];require(gen in starts and gen not in released,'CPU live generation')
            start=starts[gen];slot=start['slot'];now=row['now'];run=start['run']
            require(row['slot']==slot and type(now) is int and 0<=now<1<<60,'CPU identity/time')
            if kind=='cpu_start':
                values=row['records'];period=0 if slot==4 else 100
                require(gen not in last and type(values) is list and len(values)==8 and
                    all(type(v) is int for v in values) and values[:5]==[gen,32,0,0,period] and
                    values[6:]==[0,0] and 0<=values[5]<=now and (period or values[5]==0),'CPU initial profile')
                last[gen]=values
            elif kind=='cpu_charge':
                require(gen in last and gen not in finished and row['before']==last[gen] and
                    now>run_ticks.get(run,-1),'CPU charge continuity')
                after,result=admission.cpu.charge_result(row['before'],now)
                require(row['after']==after and type(row['result']) is int and row['result']==result,'CPU charge result')
                last[gen]=after;charges[gen]+=1;run_ticks[run]=now
            else:
                require(gen in last and gen not in finished and row['records']==last[gen] and
                    now>=last[gen][3] and gen in receipts,'CPU final continuity')
                receipt=receipts[gen]
                require(receipt['slot']==slot and receipt['ticks']==last[gen][2]==charges[gen],'CPU receipt balance')
                if receipt['status']==256:
                    require(receipt['state']==3 and last[gen][7 if last[gen][4] else 2]==32,'actual CPU exhaustion')
                finished.add(gen)
        elif kind=='release':
            gen=row['gen'];require(gen in finished and gen not in released,'CPU fenced before release');released.add(gen)
    require(starts and set(starts)==finished==released==set(receipts) and sum(charges.values())<=2048,'complete CPU lifecycle')

def authority_state(raw):
    """READY children/peer already exist even before their first user entry."""
    require(type(raw) is bytes and len(raw)==8704,'authority snapshot extent')
    starts={};live=set()
    for slot in range(8):
        state,gen=struct.unpack_from('<2Q',raw,slot*1024)
        handle,parent=struct.unpack_from('<2Q',raw,8192+slot*64)
        if state not in (1,2,6):continue
        require(0<gen<1<<31 and gen not in starts and handle==(gen<<32)|slot,'live authority identity mirror')
        phase=struct.unpack_from('<Q',raw,8192+slot*64+40)[0]
        require(phase==(1 if slot<2 else 2) and (not parent if slot<2 else parent and not parent&0xffffffff),
                'live authority family phase/parent')
        starts[gen]=dict(slot=slot,gen=gen,parent=parent);live.add(gen)
    return starts,live


def validate_identity(row,starts,live):
    require(row['slot']==0 and not row['profile_denied'] and row['size']==16 and not any(row['args'][2:]),'identity root ABI')
    before=bytes.fromhex(row['before']);after=bytes.fromhex(row['after']);pid=row['args'][1] or row['gen']
    require(len(before)==len(after)==16,'identity whole publication')
    target=starts.get(pid);root=row['gen']<<32
    expected=-3 if target is None or pid not in live else -13 if target['gen']!=row['gen'] and target['parent']!=root else 0
    require(row['result']==expected,'identity actual liveness/parent')
    require(after==(struct.pack('<4I',1,16,pid,pid) if not expected else before),'identity untouched failure/output')

def validate_terminal(row,starts,live):
    require(row['op']==127 and not row['profile_denied'] and row['size']==24 and not any(row['args'][1:]),'terminal ABI')
    request=bytes.fromhex(row['before']);require(request.hex()==row['after'] and len(request)==24,'terminal immutable request')
    version,size,operation,reserved,pid,generation=struct.unpack('<6I',request)
    require((version,size,reserved)==(1,24,0) and operation in (1,2,3,5),'terminal v1 fields')
    if operation!=2:require(pid==generation==0,'terminal unused target')
    before=struct.unpack('<3Q',bytes.fromhex(row['terminal_before']))
    after=struct.unpack('<3Q',bytes.fromhex(row['terminal']))
    slot=row['slot'];gen=row['gen'];owner=(gen<<32)|slot
    root=gen<<32 if slot==0 else starts[gen]['parent']
    require(before[0]==root and not before[2] and slot in (0,4),'terminal current root')
    expected=0;wanted=before
    if operation==2:
        require(slot==0 and pid==generation and 0<pid<1<<31,'terminal explicit target')
        target=starts.get(pid)
        if target is None or pid not in live:expected=-116
        elif target['slot']<2 or target['parent']!=root or target['slot']!=4:expected=-13
        else:
            child=(pid<<32)|target['slot']
            if before[1] not in (0,child):expected=-16
            else:wanted=(root,child,0)
    elif operation==5:expected=0 if before[1]==(0 if slot==0 else owner) else -11
    elif operation==1:expected=0 if slot==0 else -13
    else:
        expected=-13 if slot==0 else 0
        if slot==4 and before[1]==owner:wanted=(root,0,0)
    require(row['result']==expected and after==wanted,'terminal exact transition')

def validate_policy(row,previous):
    raw=bytes.fromhex(row['policy']);require(len(raw)==96,'Ring3 policy extent')
    version,size=struct.unpack_from('<2I',raw)
    owner,last,anchor,restart_anchor,operations,received,written,restarts=struct.unpack_from('<8Q',raw,8)
    used,rx,tx,recovery,degraded,reserved=struct.unpack_from('<6I',raw,72)
    require((version,size,owner,reserved)==(1,96,row['gen'],0),'Ring3 policy version/owner')
    require(0<=anchor<=last<=row['now'] and 0<=restart_anchor<=last and last-anchor<1000 and
        used<=min(4096,operations) and rx<=min(1024,received) and tx<=min(16384,written) and
        recovery<=min(2,restarts) and degraded in (0,1),'Ring3 policy windows/budgets')
    state=(last,anchor,restart_anchor,operations,received,written,restarts,degraded)
    if previous is not None:
        require(all(a<=b for a,b in zip(previous,state)),'Ring3 cumulative policy/regression')
    service=bytes.fromhex(row['service']);require(len(service)==104,'Ring3 supervisor extent')
    v,n,phase,layout=struct.unpack_from('<4I',service)
    require(v==1 and n==104 and phase in range(4) and layout in range(5) and
            struct.unpack_from('<Q',service,16)[0]==owner,'Ring3 supervisor binding')
    return state


class Snapshots:
    def __init__(self,folder):self.folder=Path(folder);self.seen={};self.bytes=0
    def read(self,reference,size=None):
        require(type(reference) is dict and set(reference)=={'file','bytes','sha256'},'snapshot fields')
        name=reference['file'];require(type(name) is str and re.fullmatch(r'session-[0-9]{4}\.bin',name),'snapshot name')
        require(type(reference['bytes']) is int and 0<=reference['bytes']<=1024*1024,'snapshot capacity')
        if name not in self.seen:
            path=self.folder/name;require(not path.is_symlink() and path.stat().st_size==reference['bytes'],'snapshot path/extent')
            raw=path.read_bytes();require(hashlib.sha256(raw).hexdigest()==reference['sha256'],'snapshot hash')
            self.seen[name]=(reference.copy(),raw);self.bytes+=len(raw)
        old,raw=self.seen[name];require(old==reference and (size is None or len(raw)==size),'snapshot identity')
        require(len(self.seen)<=2048 and self.bytes<=32*1024*1024,'snapshot total capacity')
        return raw
    def finish(self):
        require(set(self.seen)=={p.name for p in self.folder.glob('session-*.bin')}==
                {f'session-{n:04d}.bin' for n in range(1,len(self.seen)+1)},'complete ordered snapshots')

def validate_image_start(row,raw,expected):
    task=struct.unpack('<128Q',raw.read(row['task'],1024));record=raw.read(row['record'],266336)
    family=raw.read(row['family'],572);slot=row['slot'];gen=row['gen']
    require(type(gen) is int and 0<gen<1<<31 and slot in range(5) and task[:2]==(2,gen),'task first entry')
    require(record[:262240]==expected[:262240] and record[:16]==b'RNPGv2\0\0'+struct.pack('<II',2,266336),'exact executable record')
    require(task[68]==struct.unpack_from('<Q',record,16)[0] and 0x410000<=task[68]<0x440000 and
            0x40f000<=task[69]<0x410000 and not task[69]&15,'task instruction/stack')
    identity,parent,_,_,_,phase,_,_=struct.unpack_from('<8Q',family,slot*64)
    require(identity==(gen<<32)|slot and parent==row['parent'] and phase==(1 if slot<2 else 2),'task exact family')
    pages=row['pages'];mapped=row['mapped'];require(len(pages)==len(mapped) and len(set(mapped))==len(mapped),'image page aliases')
    require(pages==[p for p in range(64) if record[24+p] or p==8] and
        all(type(f) is int and 0x100000000<=f<0x400000000 and not f&4095 for f in mapped),'image page layout')
    image=raw.read(row['image'],4096*len(pages));chunks={p:image[n*4096:(n+1)*4096] for n,p in enumerate(pages)}
    for p,frame in zip(pages,mapped):
        if p!=15:require(chunks[p]==(bytes(4096) if p==8 else record[96+p*4096:96+(p+1)*4096]),'image actual bytes')
        if p==8:require(task[3]==frame and not task[12],'stack frame ownership')
        elif record[24+p]==6:require(task[4+p]==frame,'writable page ownership')
        else:require(task[4+p]==0,'read-only page not privately writable')
    stack=b''.join(chunks[p] for p in range(8,16));offset=task[69]-0x408000
    require(not any(stack[:offset]),'initial stack zero')
    argc=struct.unpack_from('<Q',stack,offset)[0];require(1<=argc<=8,'argc bound')
    words=struct.unpack_from('<'+'Q'*(argc+7),stack,offset)
    require(words[argc+1:]==(0,0,0x52534901,0,0,0),'startup ABI')
    args=[]
    for pointer in words[1:argc+1]:
        require(0x40f000<=pointer<0x410000,'argument location')
        value=stack[pointer-0x408000:pointer-0x408000+128];end=value.find(b'\0')
        require(0<=end<128,'argument bound');args.append(value[:end].decode('ascii'))
    require(args==row['args'],'actual startup arguments')
    profile=struct.unpack('<4Q',bytes.fromhex(row['profile']));extended=struct.unpack('<2Q',bytes.fromhex(row['extended']))
    require(profile[0]==gen and profile[3]==(16 if slot<2 else 0),'task profile generation/control')
    want={0:(1<<49)|(1<<50)|(1<<63),1:0,2:1<<49,3:0,4:1<<63}[slot]
    require(profile[2]==want and extended==((1<<49 if slot==2 else 1<<63 if slot==4 else 0),0),'attenuated extended rights')
    io=(1<<15)|(1<<20)
    require(profile[1]&io==(io if slot in (0,4) else 0),'console authority attenuation')

def validate_capture(serial,trace,folder,config,records,catalog,case,layout,app):
    require(type(case) is int and (case,layout,8192 if case==5 else 4096) in CASES,'matrix member')
    require(len(trace.encode())<=8*1024*1024 and 'OBSERVER_FAIL' not in trace and
        not any(marker in serial for marker in boot.FAILURES),'kernel/observer failure')
    markers=[m for m in boot.REQUIRED_MARKERS if 'SHELL' not in m]+[admission.wide.process.SUCCESS]
    require(all(serial.count(m)==1 for m in markers) and
        [serial.index(m) for m in markers]==sorted(serial.index(m) for m in markers),'complete kernel progress')
    events=[];combined=[]
    for line in trace.splitlines():
        if line.startswith('SHELL_SESSION '):
            row=json.loads(line[14:]);events.append(row);combined.append(row)
        elif line.startswith('CONSOLE_IO '):
            row=json.loads(line[11:]);row['kind']='io';combined.append(row)
    require(trace.count('SHELL_SESSION ')==len(events) and len(combined)<=32768,'complete raw events')
    receipts={}
    for match in admission.wide.process.REAP.finditer(serial):
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(match[1]))
        require(gen not in receipts and slot<5 and state in (3,4) and 0x410000<=rip<0x440000,'terminal receipt ABI')
        receipts[gen]=dict(slot=slot,gen=gen,status=status,state=state,ticks=ticks,rip=rip)
    require(serial.count(admission.wide.process.DONE)==2 and serial.count('PROCESS_REAP_OK')==len(receipts),'two complete reap runs')
    raw=Snapshots(folder);starts={};live=set();calls={};finishes=[];policies={};selections=set();copied={};releases=set()
    terminal_seen=set();identity_seen=set();constructor_attempts={};faults=[]
    for row in combined:
        kind=row['kind']
        if kind=='boot':require(row==dict(kind='boot',zero=1) and not starts,'initial boot proof')
        elif kind=='start':
            gen=row['gen'];slot=row['slot'];run=row['run'];require(run==len(finishes)+1 and gen not in starts,'start run/generation')
            expected=catalog[slot*266336:(slot+1)*266336] if slot<2 else records[slot]
            validate_image_start(row,raw,expected)
            if slot<2:require(row['args']==[f'program{slot}.prg',str(slot)],'root normal entry arguments')
            else:require(gen in copied and copied[gen]==raw.read(row['record']),'constructed executable copy')
            for other in live:require(not set(row['mapped'])&set(starts[other]['mapped']),'live address-space isolation')
            starts[gen]=row;live.add(gen)
        elif kind=='copy':
            gen=row['gen'];slot=row['slot'];require(gen not in copied and slot in (2,3,4),'image construction identity')
            record=raw.read(row['raw'],266336);require(record[:262240]==records[slot][:262240],'image construction content');copied[gen]=record
        elif kind=='pio_calls':
            raw.read(row['raw']) # Complete inventory; independently decoded below.
        elif kind=='selection':
            gen=row['gen'];run=row['run'];require(gen in live and starts[gen]['slot']==0 and gen not in selections,'selection first entry')
            require(bytes.fromhex(row['before'])==struct.pack('<4Q',0x3153455353484c53,1,2,0) and
                bytes.fromhex(row['after'])==struct.pack('<4Q',0x3153455353484c53,1,layout,case if run==1 else 0),'exact one-time selection')
            selections.add(gen)
        elif kind=='policy':
            gen=row['gen'];require(gen in live and starts[gen]['slot']==0,'policy current root')
            policies[gen]=validate_policy(row,policies.get(gen))
        elif kind=='call':
            gen=row['gen'];require(gen in live and row['slot']==starts[gen]['slot'] and gen not in calls,'request live identity')
            require(row['run']==starts[gen]['run'] and type(row['entered']) is int and row['entered']>=starts[gen]['now'],'request clock')
            require(len(bytes.fromhex(row['before']))==row['size'] and len(row['args'])==6,'whole request')
            if row['family_before'] is not None:raw.read(row['family_before'],572)
            if row['authority'] is not None:authority_state(raw.read(row['authority'],8704))
            if row['op']!=9:calls[gen]=row
        elif kind in ('return','io','abandoned'):
            gen=row['gen'];require(gen in calls and gen in live,'return paired request')
            call=calls.pop(gen)
            require(all(row.get(key)==value for key,value in call.items() if key!='kind'),'return immutable request')
            if kind=='abandoned':continue
            require(type(row['result']) is int and row['now']>=row['entered'] and
                len(bytes.fromhex(row['after']))==row['size'],'complete return')
            if row['profile_denied']:require(row['result']==-13 and row['after']==row['before'],'profile denial before effects')
            elif row['op']==114:
                validate_identity(row,*authority_state(raw.read(row['authority'],8704)));identity_seen.add((row['run'],row['result']))
            elif row['op']==127:
                validate_terminal(row,*authority_state(raw.read(row['authority'],8704)));terminal_seen.add((row['run'],row['result']))
            if row['op']==132:
                before=raw.read(row['family_before'],572);after=raw.read(row['family'],572)
                request=bytes.fromhex(row['before']);version,size,operation,reserved=struct.unpack_from('<4I',request)
                require(not reserved and row['slot']==0 and not any(row['args'][1:]) and
                        row['before']==row['after'],'task-control root immutable request')
                if operation==1:
                    require((version,size) in ((5,64),(6,80)) and
                            (row['result'] in (-11,-12) or 0<row['result']<1<<63),'CREATE result/schema')
                    b=list(struct.unpack_from('<7Q',before,512));a=list(struct.unpack_from('<7Q',after,512))
                    charged=row['result']!=-11
                    require(a[5]==b[5]+charged,'cumulative CREATE attempt')
                    if charged:
                        # Kernel construction is IF=0. Its single admitted
                        # tick is the published window's last-charge timestamp.
                        admission.validate_charge(b,a,gen,a[3],1)
                    else:require(a==b,'uncharged capacity denial')
                    require(struct.unpack_from('<Q',after,48)[0]==a[5],'CREATE attempt mirror')
                    require(struct.unpack_from('<I',after,568)[0]==struct.unpack_from('<I',before,568)[0]+int(row['result']>0),
                            'actual constructor publication count')
                    if row['result']>0:
                        handle=row['result'];slot=handle&0xffffffff
                        require(slot in (2,3,4) and handle>>32>gen,'created child exact generation')
                        child=struct.unpack_from('<8Q',after,slot*64)
                        require(child[0]==handle and child[1]==gen<<32 and child[5]==2,'created family exact publication')
                    constructor_attempts[gen]=a[5]
                else:
                    require((version,size)==(1,64) and operation in (2,3),'bounded WAIT/CANCEL ABI')
                    target,prepared,timeout,profile,cpu,startup=struct.unpack_from('<6Q',request,16)
                    require(not any((prepared,profile,cpu,startup)) and target&0xffffffff in (2,3,4) and
                            timeout==(1000 if operation==2 else 0),'WAIT/CANCEL exact fixed fields')
        elif kind=='fenced':
            gen=row['gen'];require(gen in live and row['slot']==starts[gen]['slot'],'fence live owner')
            pio=struct.unpack('<8Q',bytes.fromhex(row['pio']));terminal=struct.unpack('<3Q',bytes.fromhex(row['terminal']))
            if row['slot'] in (0,2):require(pio[2]==1,'physical fence before frame release')
            require(terminal[1]!=(gen<<32)|row['slot'],'retired foreground revoked')
        elif kind=='release':
            gen=row['gen'];require(gen in live and gen not in releases and row['slot']==starts[gen]['slot'],'one generation reap')
            require(0<row['frames']<=69 and row['after']-row['before']==row['frames'] and row['fenced']==1,'actual frame balance')
            live.remove(gen);releases.add(gen)
        elif kind=='fault':
            frame=struct.unpack('<22Q',raw.read(row['raw'],176));require(row['gen'] in live and frame[15:17]==(6,0) and frame[18]==0x33,'actual Ring3 UD2')
            faults.append(row)
        elif kind=='finish':
            require(not live and not calls and row['run']==len(finishes)+1 and row['free']==row['initial'],'complete run cleanup')
            size=sum(n for _,n in admission.ZERO_RANGES)+config['s']['family_end']-config['s']['family_begin']+12408
            require(not any(raw.read(row['raw'],size)),'kernel cleanup bytes')
            contexts=raw.read(row['contexts'],14*592)
            require(all(not any(contexts[n:n+576]) and not any(contexts[n+580:n+592]) for n in range(0,len(contexts),592)),'ELF staging cleanup')
            require(row['tasks']==sum(s['run']==row['run'] for s in starts.values()),'run task balance');finishes.append(row)
        elif kind=='rollback':raw.read(row['driver'],1024);raw.read(row['family'],64)
        elif kind=='pio':raw.read(row['raw'],12304)
        elif kind=='pio_clear':require(not any(raw.read(row['raw'],12304)),'PIO trace cleanup')
        elif kind=='service_ready':raw.read(row['raw'],128 if row['slot']==2 else 8400)
        else:require(kind in ('cpu_start','cpu_charge','cpu_final','pio_end','oom','pio_calls_end'),'known event kind')
    require(len(finishes)==2 and starts and releases==set(starts)==set(receipts),'complete task/receipt correspondence')
    cpu_path=Path(folder)/'cpu-trace-v1.bin'
    require(not cpu_path.is_symlink() and 0<cpu_path.stat().st_size<=2048*192,'raw CPU file extent')
    native_cpu_trace.validate_trace_records(trace,cpu_path.read_bytes(),events)
    validate_cpu(events,receipts)
    validate_oom_pause(combined,case)
    for run in (1,2):
        roots=[s for s in starts.values() if s['run']==run and s['slot']==0];require(len(roots)==1,'one root per run')
        root=roots[0];receipt=receipts[root['gen']]
        require((receipt['status'],receipt['state'])==((134,3) if case==15 and run==1 else (0,4)),'root outcome')
        peer=[s for s in starts.values() if s['run']==run and s['slot']==1];require(len(peer)==1,'independent peer')
        require((receipts[peer[0]['gen']]['status'],receipts[peer[0]['gen']]['state'])==(77,4),'independent peer completes')
        require((run,0) in identity_seen and (run,-13) in identity_seen and (run,-13) in terminal_seen,'actual self/foreign authority')
    validate_pio_records(combined,raw)
    raw.finish()
    # Physical media/RPC/outcome proofs are mandatory separate predicates;
    # successful serial output or the generic cleanup oracle cannot replace them.
    validate_io_and_faults(combined,receipts,case,constructor_attempts,policies,faults)
    validate_storage(combined,raw,layout,app,case)
    return dict(tasks=len(starts),snapshots=len(raw.seen),bytes=raw.bytes)


def validate_pio_records(events,raw):
    sequences={1:0,2:0};closed=set();expected=[];actual=[];live={}
    for row in events:
        kind=row['kind']
        if kind=='start':live[row['gen']]=row['slot']
        elif kind=='release':del live[row['gen']]
        elif kind=='pio_calls':
            run=row['run'];require(type(run) is int and run in (1,2) and run not in closed,'PIO capture run')
            previous=row['previous'];require(type(previous) is int and previous==sequences[run],'PIO capture continuity')
            data=raw.read(row['raw']);require(32<len(data)<=12320 and (len(data)-32)%384==0,'PIO capture batch size')
            total,error,pending,reserved=struct.unpack_from('<4Q',data)
            require(not(error or pending or reserved) and total==previous+(len(data)-32)//384<=2048,'PIO capture committed header')
            for offset in range(32,len(data),384):
                call,reply=pio_record_decode(data[offset:offset+384],previous+(offset-32)//384+1,run)
                require(live.get(call['gen'])==call['slot'],'PIO capture raw live generation')
                expected.extend((dict(kind='call',**call),dict(kind='return',**reply)))
            sequences[run]=total
        elif kind=='pio_calls_end':
            run=row['run'];require(type(run) is int and run in (1,2) and run not in closed and
                type(row['total']) is int and row['total']==sequences[run]>0,'PIO capture final count')
            closed.add(run)
        elif kind in ('call','return') and row['op']==113 and not row['profile_denied']:actual.append(row)
    require(closed=={1,2} and actual==expected,'PIO capture exact complete request/return reconstruction')


def bounded_file(path,limit):
    path=Path(path);file.pio.regular(path,limit)
    return path.read_bytes()


def capture_text(raw):
    # Same universal-newline text representation as the live capture reader.
    # The bounded file, retained hashes and binary evidence remain untouched.
    if type(raw) is not bytes:raise ValueError('capture text bytes')
    return raw.decode('ascii').replace('\r\n','\n').replace('\r','\n')


def validate_probe_steps(trace,symbols):
    """Replay bounded private step receipts in addition to every old oracle."""
    total=0;ended=False;sites=set();request_target=None
    names=('request','denied','return')
    fields={'step','site','pc','target','sp','after_sp'}
    for line in trace.splitlines():
        if line.startswith('COLD_STEP_V1 '):
            encoded=line[len('COLD_STEP_V1 '):]
            require(not ended and len(encoded)<=192 and total<8192,'bounded live step sequence')
            row=json.loads(encoded)
            require(type(row) is dict and set(row)==fields and
                    all(type(n) is int and 0<=n<1<<64 for n in row.values()),'step fields/types')
            total+=1;site=row['site']
            require(row['step']==total and site in range(3),'step sequence/site')
            require(row['pc']==symbols['native_session_probe_'+names[site]+'_site64'],'actual step site PC')
            require(row['sp']%8==0 and row['after_sp']==row['sp']+8 and
                    row['sp']>=0xffffffff80000000,'actual RET stack progress')
            require(0xffffffff80000000<=row['target']!=row['pc'],'kernel RET target')
            if site==0:
                if request_target is None:request_target=row['target']
                require(row['target']==request_target,'single admitted request return route')
            else:
                target=symbols['process_run_syscall64.denied' if site==1 else 'process_run_resume64']+5
                require(row['target']==target,'exact denied/return continuation')
            sites.add(site)
        elif line.startswith('COLD_STEP_END_V1 '):
            require(not ended and total>0 and line=='COLD_STEP_END_V1 '+str(total),'complete step end count')
            ended=True
        elif line.startswith('COLD_STEP'):
            raise ValueError('shell session unknown step receipt version')
    require(ended and sites=={0,1,2},'complete step transport proof')
    return total


def evaluate(folder,config,records,catalog,case,layout,app):
    """Replay every persisted proof without starting a process or guest."""
    folder=Path(folder)
    serial=bounded_file(folder/'guest.log',262144).decode('ascii')
    trace=capture_text(bounded_file(folder/'frame-trace.log',8*1024*1024))
    steps=validate_probe_steps(trace,config['s'])
    read_json=lambda name,limit=1024*1024:json.loads(bounded_file(folder/name,limit))
    SessionFeeder.validate(input_plan(case),trace,read_json('console-chunks.json'),read_json('console-input.json'))
    proof=validate_capture(serial,trace,folder,config,records,catalog,case,layout,app)
    metrics=read_json('capture-metrics.json')
    require(metrics['spawned'] and not metrics['failed'] and metrics['debugger_exit']==0 and
            metrics['cleanup_seconds']<=3 and metrics['stop_reason']!='deadline','successful bounded process cleanup')
    reads=[json.loads(line) for line in bounded_file(folder/'binary-memory/reads.jsonl',1024*1024).splitlines()]
    require(0<len(reads)<=2048 and [r['equivalence'] for r in reads if r['equivalence'] is not None]==['kernel','high'],
            'independent kernel/high-memory byte equality')
    from qemu_binary_memory import MAX_READ
    total=0
    for n,row in enumerate(reads,1):
        require(row['sequence']==n and row['file']==f'ram-{n:04d}.bin' and 32768<=row['bytes']<=MAX_READ,'binary memory sequence/capacity')
        data=bounded_file(folder/'binary-memory'/row['file'],MAX_READ)
        require(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'binary memory actual bytes')
        total+=len(data)
    require(set(p.name for p in (folder/'binary-memory').glob('ram-*.bin'))=={r['file'] for r in reads},'complete memory dump inventory')
    cpu_bytes=(folder/'cpu-trace-v1.bin').stat().st_size
    require(len(reads)+proof['snapshots']+1<=4096 and total+proof['bytes']+cpu_bytes<=128*1024*1024,'aggregate raw memory capacity')
    expected=file.media.image(file.media.LAYOUTS[layout],program=app)
    require(bounded_file(folder/'generated.raw',70000*512)==expected,'immutable generated disk bytes')
    for phase in ('before','after'):
        media=read_json('media-'+phase+'.json')
        require(media['passed'] and media['phase']==phase and media['base_sha256']==hashlib.sha256(expected).hexdigest() and
                media['overlay_allocated_data']==0 and media['logical_bytes']==len(expected),'read-only media proof')
        end=0
        for extent in media['extents']:
            require(extent['start']==end and extent['length']>0 and extent['depth']==1,'complete unchanged media mapping')
            end+=extent['length']
        require(end==len(expected),'media mapped size')
    commands=read_json('media-commands.json')
    require(len(commands)==7 and all(r['returncode']==0 for r in commands),'all media commands completed')
    for at in (1,4):
        require([r['args'][0] for r in commands[at:at+3]]==['info','map','compare'],'actual media verification sequence')
        info=json.loads(commands[at]['stdout']);extents=json.loads(commands[at+1]['stdout'])
        require(info['format']=='qcow2' and info['virtual-size']==len(expected) and
                Path(info['full-backing-filename'])==folder/'generated.raw' and info['backing-filename-format']=='raw' and
                extents==read_json('media-'+('before' if at==1 else 'after')+'.json')['extents'],'actual qcow2 backing/map proof')
    return dict(proof,binary_reads=len(reads),binary_bytes=total,cpu_bytes=cpu_bytes,probe_steps=steps)


def bounded_fixture(folder,layout,app,started):
    """Keep the accepted media proof, cap each helper by the same guest end."""
    def remaining():
        value=started+45-time.monotonic()
        require(0<value<=45,'media helper absolute deadline')
        return min(10,value)
    ns=dict(vars(file.pio),session_media_remaining=remaining)
    source=once(textwrap.dedent(inspect.getsource(file.pio.Fixture.run)),'timeout=10,','timeout=session_media_remaining(),')
    exec(compile(source,'<session-bounded-media-helper>','exec'),ns)
    fixture=file.pio.Fixture.__new__(file.pio.Fixture)
    fixture.run=types.MethodType(ns['run'],fixture)
    file.pio.Fixture.__init__(fixture,folder,filesystem=file.media.LAYOUTS[layout],file_program=app)
    return fixture


def run_matrix(image,folder,candidate,binding,diagnostic=False,probe_pc=False,hardware_probes=False,static_probes=False,lifecycle_probes=False):
    """One exclusive eighteen-guest window; the frozen verifier owns admission."""
    require(type(candidate) is str and re.fullmatch('[0-9a-f]{64}',candidate) and callable(binding) and
            type(diagnostic) is bool and type(probe_pc) is bool and (not probe_pc or diagnostic) and
            type(hardware_probes) is bool and (not hardware_probes or probe_pc) and
            type(static_probes) is bool and (not static_probes or hardware_probes) and
            type(lifecycle_probes) is bool and (not lifecycle_probes or hardware_probes and not static_probes),'frozen runtime admission')
    image=Path(image).resolve();folder=Path(folder).absolute()
    require(image.is_relative_to(ROOT/'build') and folder==folder.resolve() and
            folder.is_relative_to(ROOT/'build/codex-agent') and not folder.exists(),'fresh runtime scope')
    binding();config,records,app=image_config(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    image_sha=hashlib.sha256(image.read_bytes()).hexdigest();folder.mkdir(parents=True);file.pio.safe_folder(folder)
    summary=dict(passed=False,closed=False,candidate=candidate,image_sha256=image_sha,cases=[],guest_elapsed=0.0,
                 diagnostic=diagnostic,qualification=False)
    begin=time.monotonic()
    try:
        capture=None
        for case,layout,ram in (CASES[:1] if diagnostic else CASES):
            binding();require(hashlib.sha256(image.read_bytes()).hexdigest()==image_sha,'common immutable runtime image')
            require(time.monotonic()-begin<855 and summary['guest_elapsed']+45<=810,'remaining full guest reservation')
            out=folder/f'guest-{case:02d}-{layout}-{ram}';started=time.monotonic();out.mkdir()
            trial=dict(case=case,layout=layout,ram=ram,passed=False,folder=out.relative_to(ROOT).as_posix())
            summary['cases'].append(trial)
            try:
                code=observer(config,records,out,case,layout,diagnostic=diagnostic,probe_pc=probe_pc,
                              hardware_probes=hardware_probes,static_probes=static_probes,lifecycle_probes=lifecycle_probes)
                fixture=bounded_fixture(out,layout,app,started)
                capture=(capture_namespace if diagnostic else stepped_capture_namespace)(started)['capture']
                capture(image,out,code,ram,fixture,binary_memory='equivalence',diagnostic_metrics=True,
                        service_pio_budget=True,console_input=input_plan(case))
            finally:
                trial['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=trial['elapsed']
            require(trial['elapsed']<=45 and summary['guest_elapsed']<=810,'whole guest setup/capture/cleanup deadline')
            metrics=json.loads((out/'capture-metrics.json').read_text())
            require(0<=trial['elapsed']-metrics['observe_seconds']<=3,'whole guest cleanup including media proof')
            trial['proof']=evaluate(out,config,records,catalog,case,layout,app);trial['passed']=True
            print('SHELL_SESSION_GUEST_PASS',case,layout,ram,round(trial['elapsed'],3),flush=True)
        require(time.monotonic()-begin<=900,'runtime gate deadline');summary['passed']=True
        summary['qualification']=not diagnostic
        return summary
    except BaseException as error:
        summary['error']=str(error);raise
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-begin)
        with (folder/'summary.json').open('x',encoding='utf-8') as out:json.dump(summary,out,indent=2,sort_keys=True)
