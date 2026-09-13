"""Bounded wide-task block sessions; physical data, RPC and retirement evidence."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid
import run_qemu_x86_64_program_memory as wide
import run_qemu_x86_64_pio as pio
ROOT=wide.ROOT

# Shared unchanged source in host mutation tests and the debugger. No guest ABI.
TRACE_CORE=r'''
def trace_decode(raw,last):
    if len(raw)!=12304 or type(last)!=int or not 0<=last<=4096:raise ValueError('trace metadata')
    end,error=struct.unpack_from('<2Q',raw)
    if error or not last<=end<=4096:raise ValueError('trace metadata')
    if end-last>64:raise ValueError('trace gap')
    events=[]
    for seq in range(last+1,end+1):
        r=raw[16+((seq-1)&63)*192:16+((seq-1)&63)*192+192]
        kind,actual=struct.unpack_from('<2Q',r);v=struct.unpack_from('<8Q',r,16)
        if actual!=seq or kind not in (1,2):raise ValueError('trace sequence/kind')
        if v[1]!=(v[0]^0xffffffffffffffff) or v[2] not in (0,1) or v[5]>64 or not v[3]<=v[4]<1<<60 or v[6]>v[4] or v[7]:raise ValueError('trace state')
        if v[0]&0xffffffff not in (2,3) or not 0<v[0]>>32<=0x7fffffff:raise ValueError('trace owner')
        if kind==1:
            fields=struct.unpack_from('<5Q',r,80);port,value,slot,gen,parent=fields
            if port>65535 or value>255 or slot>3 or not 0<gen<=0x7fffffff or parent&0xffffffff or not 0<parent>>32<=0x7fffffff or any(r[120:]):raise ValueError('trace out')
            events.append((kind,seq,v,fields,b'',0))
        else:
            q=struct.unpack_from('<4IQ4I3Q',r,80);words=struct.unpack_from('<Q',r,176)[0]
            if not 1<=words<=16 or q[:4]!=(2,64,4,0) or q[4]!=v[0] or v[2] or q[5:9]!=(0x1f0,0,words,0) or q[11] or not q[9] or q[9]&1 or q[9]+32>0xffffffffffffffff or not v[4]*10<q[10]<=v[4]*10+1000 or any(r[144+words*2:176]) or any(r[184:]):raise ValueError('trace request')
            events.append((kind,seq,v,q,r[144:144+words*2],words))
    return events

def trace_clean(raw):
    if len(raw)!=12304 or any(raw):raise ValueError('trace cleanup')

def trace_snapshot(read,address,last):
    raw=bytearray(12304);raw[:16]=read(address,16)
    end,error=struct.unpack_from('<2Q',raw)
    # Admit metadata before any computed diagnostic read. Unseen old slots are
    # never consumed; complete storage is still read by the cleanup proof.
    if error or type(last)!=int or not 0<=last<=end<=4096:raise ValueError('trace metadata')
    if end-last>64:raise ValueError('trace gap')
    remaining=end-last;slot=last&63
    while remaining:
        count=min(remaining,64-slot);offset=16+slot*192
        raw[offset:offset+count*192]=read(address+offset,count*192)
        remaining-=count;slot=0
    return bytes(raw)
'''
exec(TRACE_CORE)

def once(source,old,new):
    if source.count(old)!=1:raise ValueError('profile observer source boundary: '+old[:60])
    return source.replace(old,new,1)

def scope_pio_page_hooks(code):
    """Keep every lifecycle proof; arm dormant same-page traps when reachable."""
    if any(name in code for name in ('trace_before_hook','trace_after_hook','cancel_hook')):raise ValueError('already scoped PIO hooks')
    code=once(code,"Hook('native_pio_finish64.trace_before_clear',trace_before_clear)","trace_before_hook=Hook('native_pio_finish64.trace_before_clear',trace_before_clear);trace_before_hook.enabled=False")
    code=once(code,"Hook('native_pio_finish64.trace_after_clear',trace_after_clear)","trace_after_hook=Hook('native_pio_finish64.trace_after_clear',trace_after_clear);trace_after_hook.enabled=False")
    code=once(code,"            starts[r['gen']]['live']=False", "            starts[r['gen']]['live']=False\n            if not any(v['live'] for v in starts.values()):trace_before_hook.enabled=trace_after_hook.enabled=True")
    code=once(code,"    trace_sequence=0;trace_digest=hashlib.sha256()", "    trace_sequence=0;trace_digest=hashlib.sha256()\n    trace_before_hook.enabled=trace_after_hook.enabled=False")
    code=once(code,"Hook('family_cancel_one64',cancel)","cancel_hook=Hook('family_cancel_one64',cancel);cancel_hook.enabled=False")
    code=once(code,"    if status:devices[owner]['pending']=None", "    if status:devices[owner]['pending']=None\n    if CASE in (2,4) and status and ((owner>>32)-3)%4==0:cancel_hook.enabled=True")
    code=once(code,"    emit('fault',gen=gen,slot=slot,vector=6)","    if CASE==6:cancel_hook.enabled=True\n    emit('fault',gen=gen,slot=slot,vector=6)")
    return once(code,"    emit('cancel',gen=t[1],slot=slot,state=t[0])","    emit('cancel',gen=t[1],slot=slot,state=t[0])\n    cancel_hook.enabled=False")


def scope_validator_page_hooks(code):
    """Preserve release/fatal proofs without parked traps on the validator page."""
    if 'release_hook' in code:raise ValueError('already scoped validator hooks')
    code=once(code,"Hook('scheduler_release_task_frames64',release_begin)","release_hook=Hook('scheduler_release_task_frames64',release_begin);release_hook.enabled=False")
    code=once(code,"def release_begin():\n    global release\n    if mode()!=8:return", "def release_begin():\n    global release\n    if mode()!=8:return\n    release_hook.enabled=False")
    # NativePIO scheduler_fail immediately JMPs here, with registers/flags and
    # corruption diagnostics unchanged. This also catches direct PIO failures.
    code=once(code,"Hook('scheduler_fail',fail)","Hook('native_pio_fail64',fail)")
    return code+r'''

def branch_target(source,opcode,target):
    raw=mem(S[source],5)
    assert len(raw)==5 and raw[0]==opcode
    assert S[source]+5+struct.unpack_from('<i',raw,1)[0]==S[target]

def release_arm():
    assert mode()==8 and release is None and not release_hook.enabled
    # Stop before the exact CALL; the unchanged release observer still reads
    # its real return address and every frame before any helper side effect.
    branch_target('process_run_complete_retire64',0xe8,'scheduler_release_task_frames64')
    branch_target('scheduler_fail',0xe9,'native_pio_fail64')
    release_hook.enabled=True
Hook('process_run_complete_retire64',release_arm)
'''


def scope_creation_page_hooks(code):
    """Observe every CREATE/OOM transaction, not its shared validation page idle."""
    if 'create_begin_hook' in code:raise ValueError('already scoped creation hooks')
    for symbol,fn,name in (('family_create64.found','create_begin','create_begin_hook'),
                           ('family_create64.stack_ready','copy','copy_hook'),
                           ('family_create64.parent_result','create_end','create_end_hook')):
        code=once(code,"Hook('"+symbol+"',"+fn+")",name+"=Hook('"+symbol+"',"+fn+");"+name+".enabled=False")
    code=once(code,"    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)",
        "    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)\n    if slot==0:create_watch()")
    code=once(code,"    assert created is None\n    start_hook.enabled=True", "    assert created is None\n    create_watch_enter()\n    start_hook.enabled=True")
    code=once(code,"    created=None\ncreate_end_hook=", "    create_watch_leave(reg('rax')==0xfffffffffffffff4)\n    created=None\ncreate_end_hook=")
    code=once(code,"            starts[r['gen']]['live']=False", "            starts[r['gen']]['live']=False\n            if r['slot']==2 and CASE!=6 and (r['gen']-3)%4==0:create_watch()")
    return code+r'''

def create_watch():
    assert created is None and not create_begin_hook.enabled and not copy_hook.enabled and not create_end_hook.enabled
    create_begin_hook.enabled=True

def create_watch_enter():
    assert created is None and create_begin_hook.enabled and not copy_hook.enabled and not create_end_hook.enabled
    create_begin_hook.enabled=False;copy_hook.enabled=create_end_hook.enabled=True

def create_watch_leave(retry):
    assert created is True and not create_begin_hook.enabled and copy_hook.enabled and create_end_hook.enabled
    assert type(retry)==bool
    copy_hook.enabled=create_end_hook.enabled=False;create_begin_hook.enabled=retry
'''


def observer_body(*,scoped=True):
    code=once(wide.OBSERVER,"'WIDE '","'PROFILE '")
    # Match the accepted block observer: retain EVERY first publication proof,
    # but do not trap and reread a1024-byte task at every unrelated PIO resume.
    code=once(code,"Hook('scheduler_enter_task64.state_published',start)","start_hook=Hook('scheduler_enter_task64.state_published',start)")
    code=once(code,"    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)",
        "    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)\n    live=[struct.unpack('<2Q',mem(S['scheduler_tasks']+i*1024,16)) for i in range(4)]\n    if all(state not in (1,2,6) or identity in starts for state,identity in live):start_hook.enabled=False")
    code=once(code,"    assert created is None\n    source_pointer=", "    assert created is None\n    start_hook.enabled=True\n    source_pointer=")
    code=once(code,"    runs+=1;assert runs<=2", "    start_hook.enabled=True\n    runs+=1;assert runs<=2")
    code=once(code,'argc=2 if slot<2 else 3','argc=2 if slot<2 else 4')
    begin=code.index('    expected=[(');end=code.index('    # No uninitialized',begin)
    code=code[:begin]+'''    if slot<2:assert args==[('program%d.prg'%slot).encode(),str(slot).encode()]
    else:
        assert all(len(a)==8 and all(ch in b'0123456789abcdef' for ch in a) for a in args)
        assert all(int(a,16)>0 for a in args[:3])
        round_=0 if CASE==6 else (gen-3)%4
        mode_=0 if round_ or CASE in (0,5,7) else 2 if CASE==6 else CASE
        assert int(args[3],16)==mode_|(16 if round_ else 0)
'''+code[end:]
    begin=code.index('def syscall():');end=code.index('created_sources={}',begin)
    code=code[:begin]+code[end:]
    code=once(code,"    tables=list(struct.unpack('<4Q'","    pio_retire(slot,gen)\n    tables=list(struct.unpack('<4Q'")
    code=once(code,"and d(S['scheduler_reap_count'])==4","and d(S['scheduler_reap_count'])==(3 if CASE==6 else 4)")
    code=once(code,"assert len(starts)==runs*4 and len(proofs)==runs*2 and not any(v['live'] for v in starts.values())",
        "assert len(starts)==runs*(3 if CASE==6 else 4) and not any(v['live'] for v in starts.values())\n    assert pstate()==(0,0xffffffffffffffff,1,0,0,0,0,0) and not any(mem(S['native_pio_request'],64))")
    code=once(code,"tasks=4,generation=d(S['process_run_generation'])","tasks=3 if CASE==6 else 4,generation=d(S['process_run_generation'])")
    code=once(code,"            self.fn()\n        except Exception as error:\n            import traceback",
        "            self.fn()\n        except Exception as error:\n            if trace_expected_rejection(error):return False\n            import traceback")
    code=code+TRACE_CORE+EXTRA
    return scope_creation_page_hooks(scope_validator_page_hooks(code)) if scoped else code

def observer(s,c,folder,case,oom,result_address,service_address,trace_fault=None):
    config=dict(s=s,cs={n:v['value'] for n,v in c['symbols'].items()},case=case,oom=oom,result_address=result_address,service_address=service_address,trace_fault=trace_fault)
    # Keep the same breakpoints across stops; avoid whole-set removal/insertion
    # by GDB's default. No guest clock, quota or single-step policy change.
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+'\nset logging overwrite on\nset logging enabled on\n'
            'python\nCONFIG='+repr(config)+'\n'+observer_body()+'\nend\ncontinue\n')

EXTRA=r'''
devices={};pio_owner=0;port_events=0;results=set();trace_sequence=0;trace_injected=False;trace_digest=hashlib.sha256()

def user(t,va,n):
    # One paused callback, never a mapping cache across guest execution. Read
    # EVERY walked entry/byte, sharing repeated upper entries within this read.
    assert 0<=n<=266336
    entries={};ranges=[]
    def entry(a):
        if a not in entries:
            assert len(entries)<272
            entries[a]=q(a)
        return entries[a]
    while n:
        root=t[2]
        for shift in (39,30,21):
            e=entry(DM+root+((va>>shift)&511)*8)
            assert e&1 and not e&128
            root=e&MASK
        e=entry(DM+root+((va>>12)&511)*8);assert e&5==5
        count=min(n,4096-(va&4095));address=DM+(e&MASK)+(va&4095)
        if ranges and ranges[-1][0]+ranges[-1][1]==address:ranges[-1][1]+=count
        else:ranges.append([address,count])
        va+=count;n-=count
    return b''.join(mem(a,size) for a,size in ranges)

def trace_expected_rejection(error):
    expected={'gap':'trace gap','data':'trace data','cleanup':'trace cleanup'}.get(CONFIG['trace_fault'])
    if not trace_injected or not expected or type(error)!=ValueError or str(error)!=expected:return False
    emit('trace_reject',fault=CONFIG['trace_fault'],error=expected)
    gdb.execute('detach');gdb.execute('quit');return True

def trace_inject():
    global trace_injected,trace_sequence
    fault=CONFIG['trace_fault']
    if trace_injected or fault not in ('gap','data'):return
    address=S['native_pio_trace'];raw=mem(address,12304);seq=q(address)
    assert 0<seq-trace_sequence<=64
    if fault=='gap':gdb.selected_inferior().write_memory(address,struct.pack('<Q',trace_sequence+65))
    else:
        events=trace_decode(raw,trace_sequence)
        chosen=next(e for e in reversed(events) if e[0]==2)
        # Admit the valid prefix before injection. The altered record remains
        # unseen; its next drain must immediately reject without intervening
        # lifecycle publication. Preserve the strict inject/reject oracle.
        for event in events:
            if event[1]==chosen[1]:break
            (out if event[0]==1 else data)(event)
            offset=16+((event[1]-1)&63)*192
            trace_digest.update(raw[offset:offset+192]);trace_sequence=event[1]
        offset=16+((chosen[1]-1)&63)*192+144
        gdb.selected_inferior().write_memory(address+offset,bytes([raw[offset]^1]))
    trace_injected=True;emit('trace_inject',fault=fault)

def trace_drain():
    global trace_sequence
    raw=trace_snapshot(mem,S['native_pio_trace'],trace_sequence)
    for event in trace_decode(raw,trace_sequence):
        (out if event[0]==1 else data)(event)
        offset=16+((event[1]-1)&63)*192
        trace_digest.update(raw[offset:offset+192]);trace_sequence=event[1]

def trace_before_clear():
    trace_drain()
    assert trace_sequence and pstate()[2]==1
    emit('trace_drained',run=runs+1,events=trace_sequence,sha=trace_digest.hexdigest())
Hook('native_pio_finish64.trace_before_clear',trace_before_clear)

def trace_after_clear():
    global trace_sequence,trace_digest,trace_injected
    if CONFIG['trace_fault']=='cleanup' and not trace_injected:
        gdb.selected_inferior().write_memory(S['native_pio_trace']+12303,b'\x01')
        trace_injected=True;emit('trace_inject',fault='cleanup')
    trace_clean(mem(S['native_pio_trace'],12304))
    emit('trace_clean',run=runs+1,bytes=12304)
    trace_sequence=0;trace_digest=hashlib.sha256()
Hook('native_pio_finish64.trace_after_clear',trace_after_clear)
def pstate():
    v=struct.unpack('<8Q',mem(S['native_pio_state'],64))
    assert v[1]==(v[0]^0xffffffffffffffff) and v[2] in (0,1) and v[5]<=64
    assert v[3]<=v[4]<1<<60 and v[6]<=v[4] and not v[7]
    return v
def out(event):
    global pio_owner,port_events
    port_events+=1;assert port_events<=512
    v=event[2];owner=v[0];port,value,slot,gen,parent=event[3]
    if port==0x3f6 and value==6:
        assert owner
        if owner!=pio_owner:
            if pio_owner:assert devices[pio_owner]['retired']
            assert slot==0 and not v[2] and owner not in devices
            assert parent==gen<<32
            pio_owner=owner;devices[owner]=dict(parent=parent,retired=False,released=False,reset=True,command=0,identify=bytearray(),data=bytearray(),lbas=[],lba=0,requests=0,pending=None)
            emit('bind',gen=owner>>32,owner=owner)
        else:devices[owner]['reset']=True
    else:
        assert owner==(gen<<32)|slot and slot==2 and not v[2]
        item=devices[owner];assert not item['retired']
        if port==0x3f6:
            assert value==2 and item['reset'] and v[4]>v[6];item['released']=True
        else:
            assert item['released']
            if port==0x1f7:
                assert value in (0xec,0x20)
                if value==0xec:assert item['command']==0
                else:
                    assert len(item['identify'])==512 and len(item['lbas'])<10
                    assert len(item['data'])==512*len(item['lbas']) and item['lba']<=9
                    item['lbas'].append(item['lba'])
                item['command']=value
            elif port==0x1f6:assert value==0xe0
            elif port==0x1f2:assert value==1
            elif port==0x1f3:assert value<=9;item['lba']=value
            else:assert port in (0x1f4,0x1f5) and value==0
    assert parent==devices[owner]['parent']
def data(event):
    v=event[2];request=event[3]
    assert request[:4]==(2,64,4,0) and request[4]==v[0] and not v[2]
    assert request[5:9]==(0x1f0,0,16,0) and not request[11] and event[5]==16
    assert v[4]*10<request[10]<=v[4]*10+1000
    item=devices[v[0]];assert item['released'] and not item['retired']
    key='identify' if item['command']==0xec else 'data'
    assert item['command'] in (0xec,0x20) and len(item[key])<=(480 if key=='identify' else 5088)
    if key=='data':
        expected=bytes((n^(item['lba']*17)^0xa5)&255 for n in range(len(item[key])%512,len(item[key])%512+32))
        if event[4]!=expected:raise ValueError('trace data')
    item[key].extend(event[4])
def pio_retire(slot,gen):
    trace_drain()
    v=pstate();assert not any(mem(S['native_pio_request'],64))
    assert not any(mem(S['family_extended_masks']+slot*16,16))
    if slot in (0,2):assert v[2]==1
    if slot!=2:return
    owner=(gen<<32)|slot;item=devices[owner]
    assert v[0]==owner and item['reset'] and item['released'] and not item['retired']
    item['retired']=True;ident=bytes(item['identify']);payload=bytes(item['data'])
    if CASE==5:assert not ident and not payload
    else:
        assert len(ident)==512 and struct.unpack_from('<H',ident,98)[0]&512 and struct.unpack_from('<I',ident,120)[0]==128
        expected=b''.join(bytes((n^(lba*17)^0xa5)&255 for n in range(512)) for lba in item['lbas'])
        assert payload==expected[:len(payload)]
    emit('retire',gen=gen,identify=len(ident),data=len(payload),lbas=item['lbas'],sha=hashlib.sha256(payload).hexdigest(),fenced=1)
def rpc():
    if mode()!=8 or q(S['syscall_rax'])!=53:return
    if d(S['scheduler_current_slot'])==2:trace_inject()
    trace_drain()
    slot=d(S['scheduler_current_slot']);t=task(slot)
    gdb.write('PROFILE_SAMPLE '+json.dumps(dict(slot=slot,gen=t[1],tick=q(S['scheduler_last_tick']),cpu=q(S['scheduler_cpu_budgets']+slot*32+16),callbacks=callbacks,trace=trace_sequence))+'\n')
    raw=user(t,q(S['syscall_rsi']),140);version,size,length=struct.unpack_from('<3I',raw)
    if slot==2 and (version,size,length)==(1,140,16):
        gen,mode_,phase,value=struct.unpack_from('<4I',raw,12);assert gen==t[1]
        assert phase in (0,1) and value==(256 if phase else 19 if CASE==5 else 128)
        if phase==0:
            service=user(t,CONFIG['service_address'],128)
            profile=struct.unpack_from('<4IQ',service,104)
            limit=1 if CASE!=6 and (gen-3)%4 else 9
            assert profile[:4]==(1,24,limit,0) and profile[4]>q(S['scheduler_last_tick'])*10
            assert struct.unpack_from('<Q',service,72)[0]==(gen<<32)|2
            if CASE!=5:assert struct.unpack_from('<3Q3I',service)[:2]==((gen<<32)|2,1) and struct.unpack_from('<3I',service,24)==(128,0,1)
            assert user(task(0),created_sources[gen],266336)==bytes([0x5a])*266336
            emit('ready',gen=gen,limit=limit,capacity=value,deadline=profile[4])
        else:emit('partial',gen=gen,bytes=value,mode=mode_)
        return
    assert slot in (0,2) and pio_owner
    item=devices[pio_owner];h=struct.unpack_from('<4I4QIiQ',raw,12)
    if slot==0:
        assert (version,size,length)==(1,140,64) and not any(raw[76:])
        assert item['pending'] is None and item['requests']<10
        item['requests']+=1;n=item['requests']
        assert h[:4]==(1,64,1,0) and h[4]==pio_owner and h[5]==h[6]==n and h[8:]==(512,0,0)
        item['pending']=(h,len(item['data']),port_events)
        emit('request',gen=pio_owner>>32,sequence=n,lba=n)
    else:
        assert (version,size)==(2,2060) and item['pending'] is not None
        previous,before,ports=item['pending'];n=item['requests']
        limit=1 if CASE!=6 and ((pio_owner>>32)-3)%4 else 9;status=-11 if n==limit+1 else 0
        bad=CASE==4 and limit==9 and not status
        assert h[:5]==(1,64,1,1,pio_owner) and h[5]==(previous[5]^1 if bad else previous[5]) and h[6:8]==previous[6:8]
        assert h[8:]==(0 if status else 512,status,0) and length==(64 if status else 576)
        full=user(t,q(S['syscall_rsi']),2060);assert not any(full[12+length:])
        if status:assert len(item['data'])==before and port_events==ports
        else:assert full[76:588]==bytes(item['data'][-512:]) and len(item['data'])==before+512
        emit('reply',gen=pio_owner>>32,sequence=n,status=status,bytes=0 if status else 512,noio=int(bool(status)),bad=int(bad))
        item['pending']=None
Hook('process_ipc_syscall64',rpc)
def result():
    if CASE==5 or mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    magic,owner,sequence,lba,status,address=struct.unpack('<6Q',user(task(0),CONFIG['result_address'],48))
    if magic!=0x424c4b5052465631:return
    if (owner,sequence) in results:return
    results.add((owner,sequence));assert owner==pio_owner and sequence==lba
    if status>=1<<63:status-=1<<64
    actual=user(task(0),address,512)
    assert actual==(bytes([0xcc])*512 if status else bytes((n^(lba*17)^0xa5)&255 for n in range(512)))
    emit('result',gen=owner>>32,sequence=sequence,status=status,bytes=512,sha=hashlib.sha256(actual).hexdigest())
    if status:devices[owner]['pending']=None
Hook('process_run_syscall64.pid',result)
def fault():
    trace_drain()
    frame=struct.unpack('<22Q',mem(reg('rdi'),176));slot=d(S['scheduler_current_slot']);gen=task(slot)[1]
    assert CASE in (1,6) and slot==(0 if CASE==6 else 2) and frame[15:17]==(6,0) and frame[18]==0x33
    emit('fault',gen=gen,slot=slot,vector=6)
Hook('process_run_exception64',fault)
def cancel():
    trace_drain()
    slot=reg('rdi');t=task(slot);assert CASE in (2,4,6) and slot==2
    emit('cancel',gen=t[1],slot=slot,state=t[0])
Hook('family_cancel_one64',cancel)
'''

def receipts(serial,case):
    if case not in range(8):raise ValueError('profile case')
    common=[m for m in wide.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[wide.process.SUCCESS]
    if any(m in serial for m in wide.transport.FAILURES):raise ValueError('profile kernel/observer failure')
    if any(serial.count(m)!=1 for m in common) or [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):raise ValueError('profile progress')
    per=3 if case==6 else 4;receipts=list(wide.process.REAP.finditer(serial));ends=list(re.finditer(wide.process.DONE,serial));rows=[]
    if len(receipts)!=2*per or serial.count('PROCESS_REAP_OK')!=2*per or len(ends)!=2:raise ValueError('profile receipts')
    for run in range(2):
        base=run*per;expected={(0,base+1):(134,3) if case==6 else (79 if case==5 else 78,4),(1,base+2):(77,4),
            (2,base+3):(134,3) if case==1 else (0,3) if case in (2,4,6) else (256,3) if case==3 else (89 if case==5 else 80,4)}
        if per==4:expected[(2,base+4)]=(89 if case==5 else 80,4)
        for match in receipts[run*per:(run+1)*per]:
            slot,gen,status,state,ticks,rip=__import__('struct').unpack('<4I2Q',bytes.fromhex(match[1]))
            if expected.pop((slot,gen),None)!=(status,state) or ticks>32 or status==256 and ticks!=32:raise ValueError('profile outcome '+str((slot,gen,status,state,ticks,rip)))
            if not 0x410000<=rip<0x440000 or not (ends[run-1].end() if run else -1)<match.start()<match.end()<ends[run].start():raise ValueError('profile receipt boundary')
            rows.append((slot,gen))
        if expected:raise ValueError('profile missing lifetime')
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('profile completion order')
    return rows


def validate_trace_fault(serial,trace,fault):
    expected={'gap':'trace gap','data':'trace data','cleanup':'trace cleanup'}
    if fault not in expected or 'OBSERVER_FAIL' in trace:raise ValueError('trace fault scope')
    rows=receipts(serial,0)
    events=[json.loads(line[8:]) for line in trace.splitlines() if line.startswith('PROFILE ')]
    wanted=[dict(kind='trace_inject',fault=fault),dict(kind='trace_reject',fault=fault,error=expected[fault])]
    actual=[e for e in events if e['kind'] in ('trace_inject','trace_reject')]
    if actual!=wanted or events[-2:]!=wanted or any(e['kind'] in ('finish','trace_clean') for e in events):raise ValueError('trace exact rejection')
    return rows


def validate(serial,trace,case,oom,count):
    if (oom is not None)!=(case==7) or 'OBSERVER_FAIL' in trace:raise ValueError('profile case/observer')
    rows=receipts(serial,case);per=3 if case==6 else 4
    events=[json.loads(line[8:]) for line in trace.splitlines() if line.startswith('PROFILE ')]
    kinds={'poison','boot','start','copy','create','oom','rollback','release','finish','bind','ready','partial','request','reply','result','retire','fault','cancel','trace_drained','trace_clean'}
    if any(e['kind'] not in kinds for e in events):raise ValueError('profile event kind')
    def get(kind):return [e for e in events if e['kind']==kind]
    if get('poison')!=[dict(kind='poison',bytes=270336)] or get('boot')!=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]:raise ValueError('profile boot')
    if events[:2]!=get('poison')+get('boot'):raise ValueError('profile boot order')
    identities=sorted(rows);children=sorted(g for s,g in rows if s==2)
    for kind in ('start','release'):
        if sorted((e['slot'],e['gen']) for e in get(kind))!=identities:raise ValueError('profile lifecycle '+kind)
    for kind in ('copy','create','bind','ready','retire'):
        if [e['gen'] for e in get(kind)]!=children:raise ValueError('profile generation '+kind)
    if any(e['bytes']!=wide.SIZE or not re.fullmatch('[0-9a-f]{64}',e['sha']) for e in get('copy')) or any(e['acquired']!=count for e in get('create')):raise ValueError('profile admission')
    for e in get('release'):
        if not 5<=e['frames']<=69 or e['fenced']!=1 or e['after']!=e['before']+e['frames']:raise ValueError('profile frame balance')
    if len(get('finish'))!=2:raise ValueError('profile finish count')
    if len(get('trace_drained'))!=2 or get('trace_clean')!=[dict(kind='trace_clean',run=n,bytes=12304) for n in (1,2)]:raise ValueError('profile trace cleanup')
    for n,e in enumerate(get('finish'),1):
        if e['run']!=n or e['tasks']!=per or e['generation']!=n*per or e['free']!=e['initial']:raise ValueError('profile final balance')
        end=events.index(e);begin=events.index(get('finish')[n-2]) if n>1 else 1
        for i,event in enumerate(events):
            if (n-1)*per<event.get('gen',0)<=n*per and not begin<i<end:raise ValueError('profile event run boundary')
        drained=get('trace_drained')[n-1];clean=get('trace_clean')[n-1]
        retired=[r for r in get('retire') if (n-1)*per<r['gen']<=n*per]
        exact=sum((r['identify']+r['data'])//32+5+6*len(r['lbas']) for r in retired)
        if drained['run']!=n or drained['events']!=exact or not 0<exact<=4096 or not re.fullmatch('[0-9a-f]{64}',drained['sha']):raise ValueError('profile trace completeness')
        if not max(events.index(r) for r in get('release') if (n-1)*per<r['gen']<=n*per)<events.index(drained)<events.index(clean)<end:raise ValueError('profile trace cleanup order')
    for gen in children:
        first=(gen-3)%per==0;limit=9 if first else 1;mode=case if first and case in (1,2,3,4,6) else 0
        records={kind:[e for e in get(kind) if e.get('gen')==gen] for kind in ('ready','retire','request','reply','result','partial')}
        ready=records['ready'][0];retire=records['retire'][0]
        if ready['limit']!=limit or ready['capacity']!=(19 if case==5 else 128) or ready['deadline']<=0:raise ValueError('profile readiness')
        lbas=[] if case==5 else [0,1] if mode else list(range(limit+1));size=0 if case==5 else 768 if mode in (1,2,3,6) else 1024 if mode==4 else 512*(limit+1)
        expected=b''.join(bytes((n^(lba*17)^0xa5)&255 for n in range(512)) for lba in lbas)[:size]
        if retire['identify']!=(0 if case==5 else 512) or retire['data']!=size or retire['lbas']!=lbas or retire['sha']!=hashlib.sha256(expected).hexdigest() or retire['fenced']!=1:raise ValueError('profile physical data')
        requests=0 if case==5 else 1 if mode else limit+1
        if records['request']!=[dict(kind='request',gen=gen,sequence=n,lba=n) for n in range(1,requests+1)]:raise ValueError('profile request sequence')
        reply_count=0 if mode in (1,2,3,6) else requests
        wanted=[]
        for n in range(1,reply_count+1):
            error=n==limit+1;wanted.append(dict(kind='reply',gen=gen,sequence=n,status=-11 if error else 0,bytes=0 if error else 512,noio=int(error),bad=int(mode==4)))
        if records['reply']!=wanted:raise ValueError('profile exact replies')
        wanted_count=0 if case in (5,6) else requests
        if len(records['result'])!=wanted_count:raise ValueError('profile result count')
        for n,e in enumerate(records['result'],1):
            allowed=(-32,-110) if mode in (1,2,3) else (-71,) if mode==4 else (-11,) if n==limit+1 else (0,)
            data=bytes([0xcc])*512 if e['status'] else bytes((b^(n*17)^0xa5)&255 for b in range(512))
            if e['sequence']!=n or e['status'] not in allowed or e['bytes']!=512 or e['sha']!=hashlib.sha256(data).hexdigest():raise ValueError('profile client publication')
        if records['partial']!=([dict(kind='partial',gen=gen,bytes=256,mode=2 if mode==6 else mode)] if mode in (1,2,3,6) else []):raise ValueError('profile partial transfer')
        order={kind:next(i for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen) for kind in ('copy','create','start','bind','ready','retire','release')}
        if not order['copy']<order['create']<order['start']<order['ready']<order['retire']<order['release'] or not order['create']<order['bind']<order['ready']:raise ValueError('profile lifecycle order')
    faults=[e for e in get('fault')]
    wanted=[dict(kind='fault',gen=run*per+(1 if case==6 else 3),slot=0 if case==6 else 2,vector=6) for run in range(2)] if case in (1,6) else []
    if faults!=wanted:raise ValueError('profile fault')
    wanted_cancels=[3,6 if case==6 else 7] if case in (2,4,6) else []
    if [e['gen'] for e in get('cancel')]!=wanted_cancels or any(e['slot']!=2 or e['state'] not in (1,6) for e in get('cancel')):raise ValueError('profile cancellation')
    if oom is None:
        if get('oom') or get('rollback'):raise ValueError('profile unexpected OOM')
    else:
        owners=[(run*per+1)<<32 for run in range(2)]
        if get('oom')!=[dict(kind='oom',owner=owner,acquired=oom) for owner in owners] or [e['owner'] for e in get('rollback')]!=owners:raise ValueError('profile OOM')
        if any(e['acquired']!=oom or e['free']!=e['before'] for e in get('rollback')):raise ValueError('profile rollback')
    return rows

def map_symbol(path,name):
    matches=re.findall(r'^\s*(?:0x)?([0-9a-f]+)\s+(?:[0-9a-f]+\s+)*'+name+r'\s*$',path.read_text(),re.M)
    if len(matches)!=1:raise ValueError('profile link symbol '+name)
    return int(matches[0],16)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--trace-faults',action='store_true');args=parser.parse_args()
    image=args.image.resolve();base=args.evidence.absolute()
    if base!=base.resolve() or not base.is_relative_to(ROOT/'build/codex-agent') or base==ROOT/'build/codex-agent':raise ValueError('profile evidence scope')
    base.mkdir(parents=True,exist_ok=True);pio.safe_folder(base)
    if not image.is_relative_to(ROOT/'build'):raise ValueError('profile image scope')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir();summary=dict(passed=False,cases=[]);started=time.monotonic();total=0;reference=None
    try:
        for case in range(1 if args.trace_faults else 8):
            if case:
                out=folder/f'build-{case}';out.mkdir()
                with (out/'build.log').open('wb') as log:
                    build=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeBlockProfile','-BlockProfileCase',str(case),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if build.returncode:raise ValueError('profile fixture build')
                image=out/'x86_64/reist-x86_64-bootstrap.elf'
            inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=wide.payload.validate(inner);wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32))
            mechanisms={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in image.parent.glob('*.o') if f.name!='elf64_loader.o'}
            if reference is not None and reference!=mechanisms:raise ValueError('profile mechanism drift')
            reference=mechanisms;catalog=(image.parent/'boot-programs.bin').read_bytes()
            if len(catalog)!=4*wide.SIZE:raise ValueError('profile catalog size')
            candidates=[p for p in image.parent.glob('programs-*') if p.is_dir() and (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
            if not candidates:raise ValueError('profile catalog provenance')
            candidate=candidates[0]
            for n in range(4):
                if wide.producer.prepare((candidate/f'program{n}.prg').read_bytes(),[f'program{n}.prg',str(n)],True)!=catalog[n*wide.SIZE:(n+1)*wide.SIZE]:raise ValueError('profile producer bytes')
            count=wide.allocations(catalog[2*wide.SIZE:3*wide.SIZE]);s=wide.transport.symbols(image)
            result_address=0 if case==5 else map_symbol(candidate/'program0.map','block_profile_result_record')
            service_address=map_symbol(candidate/'program2.map','service')
            variants=[(4096,n) for n in (0,count//2,count-1)] if case==7 else [(4096,None),(8192,None)] if case==0 else [(4096,None)]
            variants=[(4096,None,f) for f in ('gap','data','cleanup')] if args.trace_faults else [(ram,oom,None) for ram,oom in variants]
            for ram,oom,trace_fault in variants:
                out=folder/f'guest-{case}-{ram}-{oom}-{trace_fault}';out.mkdir();fixture=None if case==5 else pio.Fixture(out,block=True);begin=time.monotonic()
                serial,trace=wide.transport.capture(image,out,observer(s,c,out,case,oom,result_address,service_address,trace_fault),ram,fixture)
                elapsed=time.monotonic()-begin;total+=elapsed
                if elapsed>20 or total>(60 if args.trace_faults else 220):raise ValueError('profile guest deadline')
                rows=validate_trace_fault(serial,trace,trace_fault) if trace_fault else validate(serial,trace,case,oom,count)
                summary['cases'].append(dict(case=case,ram=ram,oom=oom,trace_fault=trace_fault,tasks=len(rows),elapsed=round(elapsed,3),image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
                print('PROFILE_TRACE_REJECTION_OK' if trace_fault else 'PROFILE_GUEST_OK',case,ram,oom,trace_fault,flush=True)
        summary.update(passed=True,mechanisms=reference)
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('PROFILE_FAIL',error);return 1
    finally:
        summary.update(elapsed=round(time.monotonic()-started,3),guest_elapsed=round(total,3));(folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('PROFILE_EVIDENCE',folder)
    return 0

if __name__=='__main__':raise SystemExit(main())
