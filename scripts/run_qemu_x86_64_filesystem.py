"""Full native FS/driver isolation proof on finite generated read-only media."""
from pathlib import Path
import argparse,hashlib,json,re,struct,subprocess,time,uuid
import run_qemu_x86_64_block_profile as block
import build_x86_64_fs_media as media
wide=block.wide;pio=block.pio;ROOT=wide.ROOT
once=block.once

def file_frame(layout,sequence,response=False):
    if type(layout) is not int or layout not in range(5) or type(sequence) is not int or not 1<=sequence<=9:raise ValueError('FS frame selector')
    n=sequence-1;op=5 if n==1 or n>=6 else 7 if n in (2,5) else 6
    path=b'/' if op==7 else b'/absent' if n==6 else b'/README.TXT' if layout<2 else b'/readme.txt'
    frame=bytearray(512);status=1 if n==5 else -2 if n==6 else -11 if n==8 else 0
    struct.pack_into('<6I',frame,0,1,512,op,0,len(path),int(response and status==1))
    at=36 if op==6 else 28 if op==7 else 24
    frame[at:at+len(path)]=path
    if op==6:
        position=5 if n==3 else 0xffffffff if n==4 else 0;capacity=5 if n==3 else 256
        struct.pack_into('<2I',frame,24,position,capacity)
        if response:
            data=media.CONTENT[position:position+capacity];struct.pack_into('<I',frame,32,len(data));frame[228:228+len(data)]=data
    elif op==7:struct.pack_into('<I',frame,24,1 if n==5 else 0)
    if response and status==0 and op!=6:
        at=216 if op==5 else 220;name=b'README.TXT' if layout<2 else b'readme.txt'
        frame[at:at+len(name)]=name;struct.pack_into('<2I',frame,at+256,1,len(media.CONTENT))
    return bytes(frame)

def observer_body():
    code=once(wide.OBSERVER,"'WIDE '","'FILESYSTEM '")
    code=once(code,"S=CONFIG['s'];CS=CONFIG['cs'];CASE=CONFIG['case'];OOM=CONFIG['oom']",
        "S=CONFIG['s'];CS=CONFIG['cs'];CASE=CONFIG['case'];OOM=CONFIG['oom'];PER_RUN=4 if CASE==6 else 6")
    code=once(code,'argc=2 if slot<2 else 3','argc=2')
    first=code.index('    expected=[(');end=code.index('    # No uninitialized',first)
    code=code[:first]+'''    if slot<2:assert args==[('program%d.prg'%slot).encode(),str(slot).encode()]
    else:
        assert all(len(a)==8 and all(ch in b'0123456789abcdef' for ch in a) for a in args)
        assert int(args[0],16)>0
        relative=(gen-1)%PER_RUN+1
        expected=16 if relative>=5 else 0 if CASE==7 else CASE
        assert int(args[1],16)==expected
'''+code[end:]
    code=once(code,'len(copies)<4','len(copies)<8')
    first=code.index('def syscall():');end=code.index('created_sources={}',first)
    code=code[:first]+code[end:]
    code=once(code,"Hook('scheduler_enter_task64.state_published',start)","start_hook=Hook('scheduler_enter_task64.state_published',start)")
    code=once(code,"    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)",
        "    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)\n    live=[struct.unpack('<2Q',mem(S['scheduler_tasks']+i*1024,16)) for i in range(4)]\n    if all(state not in (1,2,6) or identity in starts for state,identity in live):start_hook.enabled=False")
    code=once(code,"    assert created is None\n    source_pointer=", "    assert created is None\n    start_hook.enabled=True\n    source_pointer=")
    code=once(code,"    runs+=1;assert runs<=2", "    start_hook.enabled=True\n    runs+=1;assert runs<=2")
    code=once(code,"and d(S['scheduler_reap_count'])==4","and d(S['scheduler_reap_count'])==PER_RUN")
    code=once(code,"assert len(starts)==runs*4 and len(proofs)==runs*2 and not any(v['live'] for v in starts.values())",
        "assert len(starts)==runs*PER_RUN and len(proofs)==runs*(PER_RUN-2) and not any(v['live'] for v in starts.values())\n    assert pstate()==(0,0xffffffffffffffff,1,0,0,0,0,0) and not any(mem(S['native_pio_request'],64))")
    code=once(code,"tasks=4,generation=d(S['process_run_generation'])","tasks=PER_RUN,generation=d(S['process_run_generation'])")
    code=once(code,"    tables=list(struct.unpack('<4Q'","    pio_retire(slot,gen)\n    tables=list(struct.unpack('<4Q'")
    # FS CREATE only: driver allocation is independently observed but not injected.
    code=once(code,"allocation_owner=0\n","allocation_owner=0;allocation_slot=0\n")
    code=once(code,"global created,source_pointer,allocation_count,allocation_before,allocation_owner",
        "global created,source_pointer,allocation_count,allocation_before,allocation_owner,allocation_slot")
    code=once(code,"    allocator.enabled=True\n", "    allocation_slot=reg('rdi');assert allocation_slot in (2,3)\n    allocator.enabled=True\n")
    code=once(code,"if OOM is not None and allocation_owner not in injected and allocation_count==OOM:",
        "if OOM is not None and allocation_slot==3 and allocation_owner not in injected and allocation_count==OOM:")
    # The existing allocator scrubs before release. Check every returned frame,
    # including parser cache pages, before it can be reused by a replacement.
    code=once(code,"            assert r['freed']==r['frames'] and free()==r['before']+len(r['frames'])",
        "            assert r['freed']==r['frames'] and free()==r['before']+len(r['frames'])\n            assert all(not any(mem(DM+f,4096)) for f in r['frames'])")
    code=block.scope_creation_page_hooks(block.scope_validator_page_hooks(code))
    code=once(code,"create_watch_leave(reg('rax')==0xfffffffffffffff4)",
        "create_watch_leave(reg('rax')==0xfffffffffffffff4 or reg('rax')&0xffffffff==2)")
    code=once(code,"(r['gen']-3)%4==0","(r['gen']-3)%PER_RUN==0")
    code=once(code,"            starts[r['gen']]['live']=False",
        "            starts[r['gen']]['live']=False\n            if not any(v['live'] for v in starts.values()):\n                assert not cancel_pending\n                trace_before_hook.enabled=trace_after_hook.enabled=True")
    # Fresh per-callback walk entries; no cache survives guest execution.
    code=once(code,"            self.fn()\n", "            walk_entries.clear()\n            self.fn()\n")
    code=once(code,"        e=q(direct+root+((va>>shift)&511)*8)","        e=walk_entry(direct+root+((va>>shift)&511)*8)")
    code=once(code,"    return q(direct+root+((va>>12)&511)*8)","    return walk_entry(direct+root+((va>>12)&511)*8)")
    burst=block.EXTRA[block.EXTRA.index('def user('):block.EXTRA.index('def trace_expected_rejection')]
    code=code+block.TRACE_CORE+burst+EXTRA
    return block.scope_runtime_page_hooks(code)

EXTRA=r'''
walk_entries={};devices={};pio_owner=0;trace_sequence=0;trace_digest=hashlib.sha256()
fs_requests={};fs_headers={};fs_replies={};results=set();health={};physical_events=0
cancel_pending=set()
def walk_entry(address):
    if address not in walk_entries:
        assert len(walk_entries)<512
        walk_entries[address]=q(address)
    return walk_entries[address]
def expected_sector(lba):
    assert type(lba)==int and 0<=lba<CONFIG['sectors']
    return bytes.fromhex(CONFIG['media'].get(lba,'00'*512))
def pstate():
    v=struct.unpack('<8Q',mem(S['native_pio_state'],64))
    assert v[1]==v[0]^0xffffffffffffffff and v[2] in (0,1) and v[5]<=64
    assert v[3]<=v[4]<1<<60 and v[6]<=v[4] and not v[7]
    return v
def out(event):
    global pio_owner,physical_events
    physical_events+=1;assert physical_events<=1024
    v=event[2];owner=v[0];port,value,slot,gen,parent=event[3]
    if port==0x3f6 and value==6:
        assert owner
        if owner!=pio_owner:
            if pio_owner:assert devices[pio_owner]['retired']
            assert slot==0 and not v[2] and owner not in devices and parent==gen<<32
            pio_owner=owner
            devices[owner]=dict(parent=parent,retired=False,released=False,reset=True,command=0,
                identify=bytearray(),data=bytearray(),lbas=[],ports={},lba=0,pending=None,requests=0)
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
                    assert len(item['identify'])==512 and len(item['lbas'])<17
                    assert len(item['data'])==512*len(item['lbas'])
                    p=item['ports'];assert set(p)=={0x1f2,0x1f3,0x1f4,0x1f5,0x1f6}
                    assert p[0x1f2]==1 and p[0x1f6]&0xf0==0xe0
                    item['lba']=p[0x1f3]|p[0x1f4]<<8|p[0x1f5]<<16|(p[0x1f6]&15)<<24
                    assert item['lba']<CONFIG['sectors'];item['lbas'].append(item['lba'])
                item['command']=value
            else:
                assert port in (0x1f2,0x1f3,0x1f4,0x1f5,0x1f6)
                item['ports'][port]=value
    assert parent==devices[owner]['parent']
def data(event):
    v=event[2];request=event[3];item=devices[v[0]]
    assert request[:4]==(2,64,4,0) and request[4]==v[0] and not v[2]
    assert request[5:9]==(0x1f0,0,16,0) and not request[11] and event[5]==16
    assert item['released'] and not item['retired'] and item['command'] in (0xec,0x20)
    key='identify' if item['command']==0xec else 'data'
    assert len(item[key])<=(480 if key=='identify' else 17*512-32)
    if key=='data':
        offset=len(item[key])%512
        assert event[4]==expected_sector(item['lba'])[offset:offset+32],'physical data'
    item[key].extend(event[4])
def trace_drain():
    global trace_sequence
    raw=trace_snapshot(mem,S['native_pio_trace'],trace_sequence)
    for event in trace_decode(raw,trace_sequence):
        (out if event[0]==1 else data)(event)
        offset=16+((event[1]-1)&63)*192
        trace_digest.update(raw[offset:offset+192]);trace_sequence=event[1]
def before_clear():
    trace_drain();assert trace_sequence and pstate()[2]==1
    emit('trace_drained',run=runs+1,events=trace_sequence,sha=trace_digest.hexdigest())
def after_clear():
    global trace_sequence,trace_digest
    trace_clean(mem(S['native_pio_trace'],12304));emit('trace_clean',run=runs+1,bytes=12304)
    trace_sequence=0;trace_digest=hashlib.sha256()
    trace_before_hook.enabled=trace_after_hook.enabled=False
trace_before_hook=Hook('native_pio_finish64.trace_before_clear',before_clear);trace_before_hook.enabled=False
trace_after_hook=Hook('native_pio_finish64.trace_after_clear',after_clear);trace_after_hook.enabled=False
def pio_retire(slot,gen):
    trace_drain();v=pstate()
    assert not any(mem(S['native_pio_request'],64)) and not any(mem(S['family_extended_masks']+slot*16,16))
    # FS owns IPC, not PIO. Its automatic fault retirement revokes that IPC
    # before freeing frames; the supervisor fences the dependent driver before
    # the driver's retirement. Do not invent PIO authority for the FS task.
    if slot in (0,2):assert v[2]==1
    if slot==3 and CASE==3 and (gen-4)%PER_RUN==0:cancel_watch([gen-1])
    if slot!=2:return
    owner=(gen<<32)|2;item=devices[owner]
    assert v[0]==owner and item['reset'] and item['released'] and not item['retired']
    item['retired']=True;ident=bytes(item['identify']);actual=bytes(item['data'])
    assert len(ident)==512 and struct.unpack_from('<H',ident,98)[0]&512
    assert struct.unpack_from('<I',ident,120)[0]==CONFIG['sectors']
    expected=b''.join(expected_sector(lba) for lba in item['lbas'])
    assert actual==expected[:len(actual)]
    emit('retire',gen=gen,identify=512,data=len(actual),lbas=item['lbas'],sha=hashlib.sha256(actual).hexdigest(),fenced=1)
def immutable_pair(owner,peer):
    for identity in (owner,peer):
        gen=identity>>32;slot=identity&0xffffffff;t=task(slot)
        assert t[1]==gen and gen in copies and gen not in proofs
        assert user(task(0),created_sources[gen],266336)==b'\x5a'*266336
        record=copies[gen]
        for page in range(64):
            if record[24+page] in (4,5):assert user(t,0x400000+page*4096,4096)==record[96+page*4096:96+(page+1)*4096]
        masks=struct.unpack('<2Q',mem(S['family_extended_masks']+slot*16,16))
        assert masks==((1<<49,0) if slot==2 else (0,0))
        proofs.add(gen);emit('immutable',gen=gen,slot=slot,source=266336,device=int(slot==2))
def ipc():
    # Drain the single fixed caller snapshot before the next real IPC can
    # produce/overwrite it. Every old byte/result/generation check is retained.
    if mode()==8 and d(S['scheduler_current_slot'])==0:caller_result()
    if mode()!=8 or q(S['syscall_rax'])!=53:return
    trace_drain();slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    prefix=user(t,q(S['syscall_rsi']),12);version,size,length=struct.unpack('<3I',prefix)
    assert (version,size) in ((1,140),(2,2060))
    raw=user(t,q(S['syscall_rsi']),size)
    assert length<=size-12 and not any(raw[12+length:])
    if (version,length)==(1,48):
        owner,peer,deadline,rq,rp,sectors,phase,result,reserved=struct.unpack_from('<3Q4IiI',raw,12)
        assert not reserved and phase in (1,2,3,4,9)
        if slot==0:
            assert phase in (1,3)
            if phase==1:immutable_pair(owner,peer)
        else:
            assert owner==(gen<<32)|slot
            if phase==2:
                assert slot==2 and sectors==CONFIG['sectors'] and not result
                service=user(t,CONFIG['block_address'],128)
                assert struct.unpack_from('<3Q3I',service)[:2]==(owner,1)
                assert struct.unpack_from('<3I',service,24)==(sectors,0,1)
                assert struct.unpack_from('<4IQ',service,104)==(1,24,16,0,deadline)
                emit('driver_ready',gen=gen,peer=peer,capacity=sectors,deadline=deadline)
            elif phase==4:
                assert slot==3 and sectors==CONFIG['sectors']
                service=user(t,CONFIG['fs_address'],8396)
                assert struct.unpack_from('<4I3Q',service)==(1,40,1 if CONFIG['layout']<2 else 2,sectors,owner,peer,deadline)
                requests,ready,failed,busy,used=struct.unpack_from('<5I',service,120)
                assert not requests and not busy
                if result:
                    assert (ready,failed,used)==(0,1,0) and not any(service[140:])
                else:
                    assert (ready,failed)==(2,0) and used==(1 if CONFIG['layout']<2 else 4)
                    assert struct.unpack_from('<Q',service,40)[0]==peer and struct.unpack_from('<Q',service,48)[0]==used
                health[gen]=result;emit('fs_ready',gen=gen,peer=peer,status=result,deadline=deadline,cached=used)
                if CASE==8 and result:cancel_watch([gen-1])
            else:assert slot==2 and CASE==6 and phase==9
        return
    if version==1:
        assert slot==3 and length==64
        h=struct.unpack_from('<4I4QIiQ',raw,12);item=devices[h[4]]
        assert h[:4]==(1,64,1,0) and h[8:]==(512,0,0) and item['pending'] is None
        assert h[5]==item['requests']+1 and h[5]<=16 and h[6]<CONFIG['sectors']
        assert q(S['scheduler_last_tick'])*10<h[7]<=q(S['scheduler_last_tick'])*10+1000
        item['requests']+=1;item['pending']=(h,len(item['data']),physical_events)
        emit('block_request',gen=h[4]>>32,client=gen,sequence=h[5],lba=h[6]);return
    assert length in (64,576)
    h=struct.unpack_from('<4I4QIiQ',raw,12)
    if slot==2:
        item=devices[(gen<<32)|2];previous,before,ports=item['pending']
        assert h[:5]==(1,64,1,1,(gen<<32)|2) and h[5:8]==previous[5:8] and h[10]==0
        assert h[9]==0 and h[8]==512 and length==576
        assert len(item['data'])==before+512 and raw[76:588]==bytes(item['data'][-512:])==expected_sector(h[6])
        item['pending']=None;emit('block_reply',gen=gen,sequence=h[5],lba=h[6],sha=hashlib.sha256(raw[76:588]).hexdigest());return
    # FS RPC has the same64-byte scalar shape but distinct field meanings.
    assert slot in (0,3)
    owner,sequence=h[4:6];key=(owner,sequence)
    if slot==0:
        assert h[:2]==(1,64) and h[2] in (5,6,7) and not h[3] and h[7:]==(0,512,0,0)
        assert length==576 and key not in fs_requests and 1<=sequence<=9
        assert owner==(task(3)[1]<<32)|3
        assert raw[76:588]==CONFIG['requests'][sequence-1]
        assert q(S['scheduler_last_tick'])*10<h[6]<=q(S['scheduler_last_tick'])*10+3000
        fs_headers[key]=h
        fs_requests[key]=raw[76:588];emit('fs_request',gen=owner>>32,sequence=sequence,op=h[2],sha=hashlib.sha256(raw[76:588]).hexdigest())
        if CASE==2 and ((owner>>32)-4)%PER_RUN==0:cancel_watch([(owner>>32)-1,owner>>32])
    else:
        expected_owner=(gen<<32)|3;bad=CASE==4 and (gen-4)%PER_RUN==0
        assert owner==(expected_owner^int(bad)) and (expected_owner,sequence) in fs_requests
        assert h[:2]==(1,64) and h[3]==1 and h[7]==0 and h[10]==0
        previous=fs_headers[(expected_owner,sequence)]
        assert h[2]==previous[2] and h[5:8]==previous[5:8]
        assert h[9]==(1 if sequence==6 else -2 if sequence==7 else -11 if sequence==9 else 0)
        assert (h[8],length)==((0,64) if h[9]<0 else (512,576))
        if h[9]>=0:assert raw[76:588]==CONFIG['responses'][sequence-1]
        fs_replies[(expected_owner,sequence)]=(h[9],raw[76:588] if length==576 else b'')
        emit('fs_reply',gen=gen,sequence=sequence,status=h[9],bad=int(bad))
        if sequence==9 or bad:cancel_watch([gen-1,gen] if bad else [gen-1])
Hook('process_ipc_syscall64',ipc)
def caller_result():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    values=struct.unpack('<7Q',user(task(0),CONFIG['result_address'],56))
    magic,owner,sequence,op,status,address,kind=values
    if magic!=0x4e46535250435631 or (owner,sequence) in results:return
    key=(owner,sequence);assert key in fs_requests
    if status>=1<<63:status-=1<<64
    actual=user(task(0),address,512);request=fs_requests[key]
    if status<0:assert actual==request
    else:
        assert key in fs_replies and fs_replies[key]==(status,actual)
        assert actual==CONFIG['responses'][sequence-1]
        if op==6:
            position,requested,got=struct.unpack_from('<3I',request,24)[0],struct.unpack_from('<I',request,28)[0],struct.unpack_from('<I',actual,32)[0]
            expected=CONFIG['content'][position:position+requested]
            assert got==len(expected) and actual[228:484]==expected+bytes(256-len(expected))
        elif status==0:
            at=216 if op==5 else 220
            name=actual[at:at+256].split(b'\0')[0]
            assert name.lower()==b'readme.txt' and struct.unpack_from('<2I',actual,at+256)==(1,len(CONFIG['content']))
    results.add(key);emit('result',gen=owner>>32,caller=task(0)[1],sequence=sequence,op=op,status=status,sha=hashlib.sha256(actual).hexdigest())
def fault():
    trace_drain();slot=d(S['scheduler_current_slot']);gen=task(slot)[1]
    f=struct.unpack('<22Q',mem(reg('rdi'),176))
    assert CASE in (1,5,6) and slot=={1:3,5:2,6:0}[CASE] and f[15:17]==(6,0) and f[18]==0x33
    emit('fault',gen=gen,slot=slot,vector=6)
    if CASE==1:cancel_watch([gen-1])
    if CASE==6:cancel_watch([gen+2,gen+3])
def cancel_watch(generations):
    # Parked traps share the hot PIO code page in this QEMU build. Arm only
    # after the exact response/fault that requires cancellation, keeping every
    # generation, physical fence and retirement assertion at the real entry.
    assert not cancel_pending and not cancel_hook.enabled
    assert 1<=len(generations)<=2 and len(set(generations))==len(generations)
    live={task(slot)[1] for slot in (2,3) if task(slot)[0] in (1,2,6)}
    assert set(generations)<=live
    cancel_pending.update(generations);cancel_hook.enabled=True

def cancel():
    trace_drain();slot=reg('rdi');t=task(slot)
    assert slot in (2,3) and pstate()[2]==1 and t[1] in cancel_pending
    emit('cancel',gen=t[1],slot=slot,state=t[0])
    cancel_pending.remove(t[1]);cancel_hook.enabled=bool(cancel_pending)
Hook('process_run_exception64',fault)
cancel_hook=Hook('family_cancel_one64',cancel);cancel_hook.enabled=False
'''

def observer(symbols,core,folder,case,layout,oom,addresses):
    raw=media.image(media.LAYOUTS[layout],case==8)
    sectors={n//512:raw[n:n+512].hex() for n in range(0,len(raw),512) if any(raw[n:n+512])}
    config=dict(s=symbols,cs={n:v['value'] for n,v in core['symbols'].items()},case=case,layout=layout,
        oom=oom,sectors=len(raw)//512,media=sectors,content=media.CONTENT,
        requests=[file_frame(layout,n) for n in range(1,10)],responses=[file_frame(layout,n,True) for n in range(1,10)],**addresses)
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+repr(config)+'\n'+observer_body()+'\nend\ncontinue\n')

def expected_receipts(case):
    if type(case) is not int or case not in range(9):raise ValueError('FS case')
    per_run=4 if case==6 else 6;result=[]
    for run in range(2):
        for relative in range(1,per_run+1):
            slot=relative-1 if relative<=4 else relative-3
            status=78 if slot==0 else 77 if slot==1 else 0 if slot==2 else 80
            state=3 if slot==2 else 4
            if case==8:
                if slot==0:status=81
                if slot==3:status=90
            if relative==4:
                if case in (1,2,3,4):status={1:134,2:0,3:256,4:0}[case];state=3
                if case==5:status=90
            if case==5 and relative==3:status=134
            if case==6:
                if slot==0:status=134;state=3
                if slot>=2:status=0;state=3
            result.append((slot,run*per_run+relative,status,state))
    return result

def validate(serial,trace,case,layout,oom,counts):
    expected=expected_receipts(case);per_run=len(expected)//2
    if layout not in range(5) or (oom is not None)!=(case==7):raise ValueError('FS matrix selector')
    common=[m for m in wide.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[wide.process.SUCCESS]
    if any(m in serial for m in wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('FS kernel/observer failure')
    if any(serial.count(m)!=1 for m in common) or [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):raise ValueError('FS kernel progress')
    receipts=list(wide.process.REAP.finditer(serial));ends=list(re.finditer(wide.process.DONE,serial))
    if len(receipts)!=len(expected) or serial.count('PROCESS_REAP_OK')!=len(expected) or len(ends)!=2:raise ValueError('FS receipt count')
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('FS caller return order')
    outcomes={gen:(slot,status,state) for slot,gen,status,state in expected};rows=[]
    for i,match in enumerate(receipts):
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(match[1]));run=i//per_run
        if outcomes.get(gen)!=(slot,status,state) or not run*per_run<gen<=(run+1)*per_run or gen in [r[1] for r in rows]:raise ValueError('FS outcome '+str((slot,gen,status,state)))
        if ticks>32 or not 0x410000<=rip<0x440000:raise ValueError('FS CPU/instruction bound')
        if case==3 and (gen-4)%per_run==0 and ticks!=32:raise ValueError('FS exact CPU exhaustion')
        if not (ends[run-1].end() if run else -1)<match.start()<match.end()<=ends[run].start():raise ValueError('FS receipt ordering')
        rows.append((slot,gen))
    events=[json.loads(line[len('FILESYSTEM '):]) for line in trace.splitlines() if line.startswith('FILESYSTEM ')]
    allowed={'poison','boot','start','copy','create','release','finish','oom','rollback','fault','cancel',
        'bind','retire','immutable','driver_ready','fs_ready','block_request','block_reply','fs_request','fs_reply','result','trace_drained','trace_clean'}
    if any(e.get('kind') not in allowed for e in events):raise ValueError('FS event kind')
    def get(kind):return [e for e in events if e['kind']==kind]
    if get('poison')!=[dict(kind='poison',bytes=270336)] or get('boot')!=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]:raise ValueError('FS boot proof')
    if len(get('start'))!=len(expected) or {(e['slot'],e['gen']) for e in get('start')}!=set(rows):raise ValueError('FS publication proof')
    if [(e['slot'],e['gen']) for e in get('release')]!=rows:raise ValueError('FS release order')
    for e in get('release'):
        if not 0<e['frames']<=69 or e['fenced']!=1 or not 0<e['before']<e['after']==e['before']+e['frames']<=4194304:raise ValueError('FS frame balance')
    children=[(slot,gen) for slot,gen,_,_ in expected if slot>=2];drivers=[gen for slot,gen in children if slot==2];parsers=[gen for slot,gen in children if slot==3]
    for kind in ('copy','create','immutable'):
        if [e['gen'] for e in get(kind)]!=[gen for _,gen in children]:raise ValueError('FS '+kind+' generations')
    for e in get('create'):
        if e['acquired']!=counts[outcomes[e['gen']][0]]:raise ValueError('FS allocation count')
    for e in get('copy'):
        if e['bytes']!=wide.SIZE or e['sha']!=counts['sha'][outcomes[e['gen']][0]]:raise ValueError('FS immutable record')
    for e in get('immutable'):
        if (e['slot'],e['source'],e['device'])!=(outcomes[e['gen']][0],wide.SIZE,int(outcomes[e['gen']][0]==2)):raise ValueError('FS source/authority')
    for kind in ('bind','driver_ready','retire'):
        if [e['gen'] for e in get(kind)]!=drivers:raise ValueError('FS '+kind+' driver lifecycle')
    media_bytes=media.image(media.LAYOUTS[layout],case==8);sectors=len(media_bytes)//512
    for e in get('driver_ready'):
        if e['capacity']!=sectors or not 0<e['deadline']<1<<64:raise ValueError('FS driver self-test')
    ready=get('fs_ready');expected_ready=[] if case==6 else parsers
    if [e['gen'] for e in ready]!=expected_ready:raise ValueError('FS readiness count')
    for e in ready:
        bad=case==8 or case==5 and (e['gen']-4)%per_run==0
        if (e['status']<0)!=bad or (not bad and e['status']!=0) or e['peer']!=((e['gen']-1)<<32)|2:raise ValueError('FS self-test status')
        if e['cached']!=(0 if bad else 1 if layout<2 else 4):raise ValueError('FS self-test cache')
    for e in get('retire'):
        if e['identify']!=512 or e['fenced']!=1 or not e['lbas'] or e['lbas'][0]!=0 or len(e['lbas'])>17:raise ValueError('FS physical retirement')
        expected_data=b''.join(media_bytes[lba*512:(lba+1)*512] for lba in e['lbas'] if type(lba)==int and 0<=lba<sectors)
        partial=case in (5,6) and (e['gen']-3)%per_run==0
        expected_size=768 if partial else len(e['lbas'])*512
        if e['data']!=expected_size or e['sha']!=hashlib.sha256(expected_data[:expected_size]).hexdigest():raise ValueError('FS physical bytes')
        requests=[r for r in get('block_request') if r['gen']==e['gen']]
        replies=[r for r in get('block_reply') if r['gen']==e['gen']]
        if [r['sequence'] for r in requests]!=list(range(1,len(requests)+1)) or [r['lba'] for r in requests]!=e['lbas'][1:]:raise ValueError('FS block request binding')
        if len(replies)!=len(requests)-int(partial):raise ValueError('FS block reply count')
        for request,reply in zip(requests,replies):
            sector=media_bytes[request['lba']*512:(request['lba']+1)*512]
            if reply['sequence']!=request['sequence'] or reply['lba']!=request['lba'] or reply['sha']!=hashlib.sha256(sector).hexdigest():raise ValueError('FS block reply bytes')
    for gen in parsers:
        first=(gen-4)%per_run==0
        n=0 if case in (6,8) or case==5 and first else 1 if case in (1,2,3,4) and first else 9
        for kind in ('fs_request','result'):
            current=[e for e in get(kind) if e['gen']==gen]
            if [e['sequence'] for e in current]!=list(range(1,n+1)):raise ValueError('FS '+kind+' sequence')
            for e in current:
                response=kind=='result' and e['status']>=0
                canonical=file_frame(layout,e['sequence'],response)
                if e['op']!=struct.unpack_from('<I',canonical,8)[0] or e['sha']!=hashlib.sha256(canonical).hexdigest():raise ValueError('FS canonical path/data')
                if kind=='result' and e['caller']!=((gen-1)//per_run)*per_run+1:raise ValueError('FS result caller generation')
        current=[e for e in get('result') if e['gen']==gen]
        if n==9 and [e['status'] for e in current]!=[0,0,0,0,0,1,-2,0,-11]:raise ValueError('FS normal file results')
        if n==1 and current[0]['status'] not in ([-71] if case==4 else [-32,-110]):raise ValueError('FS rejected result')
        replies=[e for e in get('fs_reply') if e['gen']==gen]
        expected_replies=0 if n==1 and case in (1,2,3) else n
        if [e['sequence'] for e in replies]!=list(range(1,expected_replies+1)):raise ValueError('FS reply sequence')
        if any(e['bad']!=int(case==4 and first) for e in replies):raise ValueError('FS reply corruption classification')
    if len(get('finish'))!=2 or len(get('trace_drained'))!=2 or len(get('trace_clean'))!=2:raise ValueError('FS complete cleanup count')
    for run,(finish,drained,clean) in enumerate(zip(get('finish'),get('trace_drained'),get('trace_clean')),1):
        if (finish['run'],finish['tasks'],finish['generation'])!=(run,per_run,run*per_run) or not 0<finish['free']==finish['initial']<=4194304:raise ValueError('FS final balance')
        if drained['run']!=run or not 0<drained['events']<=4096 or not re.fullmatch('[0-9a-f]{64}',drained['sha']):raise ValueError('FS trace drain')
        if clean!=dict(kind='trace_clean',run=run,bytes=12304):raise ValueError('FS trace clear')
    fault_gen=[gen for slot,gen in rows if case in (1,5,6) and slot=={1:3,5:2,6:0}[case] and (gen-1)%per_run<4]
    if [e['gen'] for e in get('fault')]!=fault_gen or any(e['vector']!=6 for e in get('fault')):raise ValueError('FS exact fault')
    cancelled=[gen for slot,gen,status,state in expected if slot>=2 and status==0 and state==3]
    if len(get('cancel'))!=len(cancelled) or {e['gen'] for e in get('cancel')}!=set(cancelled) or any(e['state'] not in (1,6) or e['slot']!=outcomes[e['gen']][0] for e in get('cancel')):raise ValueError('FS exact cancellation')
    for kind in ('oom','rollback'):
        current=get(kind)
        if [(e['owner'],e['acquired']) for e in current]!=([(1<<32,oom),((per_run+1)<<32,oom)] if oom is not None else []):raise ValueError('FS OOM scope')
        if kind=='rollback' and any(e['free']!=e['before'] for e in current):raise ValueError('FS OOM rollback')
    for slot,gen in rows:
        def at(kind):return next(i for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen)
        if at('start')>=at('release'):raise ValueError('FS publication/retirement order')
        if slot>=2 and not at('copy')<at('create')<at('immutable')<at('release'):raise ValueError('FS imported lifecycle order')
        if slot==2 and not at('bind')<at('driver_ready')<at('retire')<at('release'):raise ValueError('FS device lifecycle order')
        if slot==2 and not at('start')<at('driver_ready') or gen in cancelled and not at('cancel')<at('release'):raise ValueError('FS ready/fence order')
        if gen in fault_gen and not at('fault')<at('release'):raise ValueError('FS fault order')
        for kind in ('block_request','block_reply','fs_request','fs_reply','result'):
            current=[(i,e) for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen]
            for i,e in current:
                if kind=='result':
                    # The server may retire after sending its last reply or
                    # fault before a pending call fails. Publication belongs
                    # to the still-live caller, never resurrects the server.
                    bounds=[j for j,x in enumerate(events) if x['kind'] in ('start','release') and x.get('gen')==e['caller']]
                    if len(bounds)!=2 or not bounds[0]<i<bounds[1]:raise ValueError('FS result outside caller lifetime')
                elif not at('start')<i<at('release'):raise ValueError('FS event outside generation')
                earlier='block_request' if kind=='block_reply' else 'fs_request' if kind in ('fs_reply','result') else None
                if earlier:
                    previous=[j for j,x in enumerate(events) if x['kind']==earlier and x.get('gen')==gen and x.get('sequence')==e['sequence']]
                    if len(previous)!=1 or previous[0]>=i:raise ValueError('FS RPC causal order')
    return rows

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    reference_image=args.image.resolve();base=args.evidence.absolute()
    if not reference_image.is_relative_to(ROOT/'build') or base!=base.resolve() or not base.is_relative_to(ROOT/'build/codex-agent') or base==ROOT/'build/codex-agent':raise ValueError('FS evidence scope')
    base.mkdir(parents=True,exist_ok=True);pio.safe_folder(base)
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir();summary=dict(passed=False,cases=[],attempts=[]);begin=time.monotonic();total=0;reference=None
    matrix=[(0,layout,4096,None) for layout in range(5)]+[(0,2,8192,None)]+[(case,2,4096,None) for case in range(1,7)]+[(7,2,4096,point) for point in ('first','middle','last')]+[(8,layout,4096,None) for layout in (0,1,4)]
    builds={}
    try:
        for case,layout,ram,point in matrix:
            key=(case,layout)
            if key not in builds:
                if key==(0,2):image=reference_image
                else:
                    out=folder/f'build-{case}-{layout}';out.mkdir()
                    with (out/'build.log').open('wb') as log:
                        result=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeFilesystem','-FilesystemCase',str(case),'-FilesystemLayout',str(layout),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if result.returncode:raise ValueError('FS fixture build')
                    image=out/'x86_64/reist-x86_64-bootstrap.elf'
                inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=wide.payload.validate(inner);wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32))
                mechanisms={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in image.parent.glob('*.o') if f.name!='elf64_loader.o'}
                if reference is not None and reference!=mechanisms:raise ValueError('FS mechanism drift')
                reference=mechanisms;catalog=(image.parent/'boot-programs.bin').read_bytes()
                if len(catalog)!=4*wide.SIZE:raise ValueError('FS catalog size')
                candidates=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
                if not candidates:raise ValueError('FS producer provenance')
                producer=candidates[0]
                for n in range(4):
                    if wide.producer.prepare((producer/f'program{n}.prg').read_bytes(),[f'program{n}.prg',str(n)],True)!=catalog[n*wide.SIZE:(n+1)*wide.SIZE]:raise ValueError('FS producer bytes')
                counts={n:wide.allocations(catalog[n*wide.SIZE:(n+1)*wide.SIZE]) for n in (2,3)}
                counts['sha']={n:hashlib.sha256(wide.producer.prepare((producer/f'program{n}.prg').read_bytes(),[],True)).hexdigest() for n in (2,3)}
                addresses={name:block.map_symbol(producer/f'program{n}.map',symbol) for name,n,symbol in (
                    ('result_address',0,'filesystem_result_record'),('block_address',2,'filesystem_block_service'),('fs_address',3,'filesystem_service'))}
                builds[key]=(image,core,wide.transport.symbols(image),counts,addresses)
            image,core,symbols,counts,addresses=builds[key]
            oom=None if point is None else 0 if point=='first' else counts[3]//2 if point=='middle' else counts[3]-1
            out=folder/f'guest-{case}-{layout}-{ram}-{point}';out.mkdir();fixture=pio.Fixture(out,filesystem=media.LAYOUTS[layout],malformed=case==8)
            started=time.monotonic()
            trial=dict(case=case,layout=layout,ram=ram,oom=oom,passed=False,folder=str(out.relative_to(ROOT)))
            try:
                serial,trace=wide.transport.capture(image,out,observer(symbols,core,out,case,layout,oom,addresses),ram,fixture)
            finally:
                elapsed=time.monotonic()-started;total+=elapsed;trial['elapsed']=round(elapsed,3);summary['attempts'].append(trial)
            if elapsed>20 or total>360:raise ValueError('FS guest deadline')
            rows=validate(serial,trace,case,layout,oom,counts)
            trial['passed']=True
            summary['cases'].append(dict(case=case,layout=layout,ram=ram,oom=oom,tasks=len(rows),elapsed=round(elapsed,3),image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
            print('FILESYSTEM_GUEST_OK',case,layout,ram,oom,flush=True)
        summary.update(passed=True,mechanisms=reference)
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('FILESYSTEM_FAIL',error);return 1
    finally:
        summary.update(elapsed=round(time.monotonic()-begin,3),guest_elapsed=round(total,3));(folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('FILESYSTEM_EVIDENCE',folder)
    return 0
if __name__=='__main__':raise SystemExit(main())
