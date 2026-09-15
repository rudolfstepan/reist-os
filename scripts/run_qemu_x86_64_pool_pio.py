"""Same-image eight-task PIO qualification, fixed media/CPU/guest limits."""
from pathlib import Path
import argparse,hashlib,inspect,json,re,struct,time,uuid
import run_qemu_x86_64_task_pool as pool
import run_qemu_x86_64_block_profile as profile
helpers=pool.helpers;wide=pool.wide;transport=pool.transport;payload=pool.payload;pio=profile.pio
ROOT=pool.ROOT;SIZE=pool.SIZE;BASE=ROOT/'build/codex-agent/r83ao-pool-pio'
digest=pool.digest
CASES=tuple((n,8192 if n==6 else 4096) for n in range(16))
FATAL_CASES=('owner-slot8','retirement-slot7')
TRACE_CORE=helpers.once(profile.TRACE_CORE,'v[0]&0xffffffff not in (2,3)','not 2<=v[0]&0xffffffff<8')
TRACE_CORE=helpers.once(TRACE_CORE,'slot>3','slot>7')
exec(TRACE_CORE)


def dimensions(case):
    if type(case) is not int or case not in range(16):raise ValueError('pool PIO case')
    fillers=case if case<=5 else 5
    return fillers,fillers+2,fillers+(3 if case==11 else 4)


def image_config(image):
    inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=payload.validate(inner)
    if core['layout_version']!=5:raise ValueError('pool PIO layout5')
    payload.verify_outer(inner,payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    if len(catalog)!=4*SIZE:raise ValueError('pool PIO catalog')
    attempts=[p for p in image.parent.glob('programs-*') if p.is_dir() and
        (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(attempts)!=1:raise ValueError('pool PIO producer identity')
    folder=attempts[0]
    for n in range(4):
        raw=(folder/f'program{n}.prg').read_bytes()
        if n<3:pool.fixture_sections(raw)
        if wide.producer.prepare(raw,[f'program{n}.prg',str(n)],True)!=catalog[n*SIZE:(n+1)*SIZE]:
            raise ValueError('pool PIO producer bytes')
    child=catalog[2*SIZE:3*SIZE-4096]+bytes(4096)
    addresses={name:profile.map_symbol(folder/f'program{n}.map',name) for n,name in
        ((0,'pool_pio_root'),(1,'pool_pio_peer'),(2,'pool_pio_child'),(2,'service'))}
    for n,name,size,magic in ((0,'pool_pio_root',136,0x31544f4f52504950),
                             (1,'pool_pio_peer',24,0x3152454550504950),(2,'pool_pio_child',48,0x31444c4948504950)):
        a=addresses[name];start=n*SIZE+96+a-0x400000
        if a&7 or not 0x410000<=a<=0x440000-size or catalog[start:start+size]!=struct.pack('<Q',magic)+bytes(size-8):
            raise ValueError('pool PIO immutable fixture witness')
    return dict(s=transport.symbols(image),cs={n:v['value'] for n,v in core['symbols'].items()},
        child_record=child,**addresses)


START=pool.START.split('    argc=2 if slot<2 else 6',1)[0]+r'''
    argc=2 if slot<2 else 5
    values=struct.unpack('<'+'Q'*(argc+7),user(t,t[69],(argc+7)*8))
    assert values[0]==argc and values[argc+1:]==(0,0,0x52534901,0,0,0)
    args=[user(t,p,128).split(b'\0')[0] for p in values[1:argc+1]]
    parent=0;kind=-1;round_=-1
    if slot<2:assert args==[('program%d.prg'%slot).encode(),str(slot).encode()]
    else:
        assert all(len(a)==8 and all(c in b'0123456789abcdef' for c in a) for a in args)
        assert int(args[4],16)==slot
        kind=int(args[3],16);assert kind==256 if slot<DRIVER_SLOT else kind in (0,7,8,9,10)
        parent=task(0)[1];assert parent in starts and starts[parent]['live']
        assert q(S['family_records']+slot*64+8)==parent<<32
        if slot==DRIVER_SLOT:
            round_=sum(e['parent']==parent and e['kind']!=256 and e['slot']>=2 for e in starts.values())
            expected=0 if round_ else 8 if CASE==11 else CASE if CASE in (7,8,9,10) else 0
            assert kind==expected and round_<=1
        assert struct.unpack('<4Q',mem(S['family_profiles']+slot*32,32))==(gen,CONFIG['mask'],0 if kind==256 else 1<<49,0)
    stack=user(t,0x408000,32768);assert not any(stack[:t[69]-0x408000])
    starts[gen]=dict(slot=slot,owned=owned,mapped=[f for p,f in image],live=True,record=record,parent=parent,kind=kind,round=round_)
    emit('start',slot=slot,gen=gen,parent=parent,role=kind,round=round_,image=selector,
         pages=len(image),private=len(owned),live=sum(e['live'] for e in starts.values()))
    if slot==0:
        address=CONFIG['pool_pio_root'];raw=user(t,address,136)
        assert raw==struct.pack('<Q',0x31544f4f52504950)+bytes(128)
        leaf=leaves[(address+8-0x400000)//4096]
        assert leaf&~MASK&~0x60==NX|7 and (address+8)&4095<=4088
        target=DM+(leaf&MASK)+((address+8)&4095);assert mem(target,8)==bytes(8)
        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))
        assert mem(target,8)==struct.pack('<Q',CASE)
        emit('mode',slot=0,gen=gen,address=address+8,physical=(leaf&MASK)+((address+8)&4095),before=0,value=CASE)
'''

SYSCALL=r'''
def syscall():
    global source_pending
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);call=q(S['syscall_rax'])
    if slot==0 and call==132:
        header=struct.unpack('<4I',user(t,q(S['syscall_rdi']),16))
        if header==(5,64,1,0):
            assert created is None and not create_begin_hook.enabled
            create_begin_hook.enabled=True
        if header==(1,64,3,0):cancel_hook.enabled=True
    if slot==0 and call==22:
        if source_pending:
            gen=source_pending;assert user(t,created_sources[gen],266336)==bytes([0xa5])*266336
            poisoned.add(gen);source_pending=0;emit('source',gen=gen,bytes=266336,poison=165)
        result()
    if slot==1 and call==22:
        w=struct.unpack('<3Q',user(t,CONFIG['pool_pio_peer'],24))
        if w[2]==25 and t[1] not in peers:
            assert w[:2]==(0x3152454550504950,t[1]);peers.add(t[1]);emit('peer',gen=t[1],sleeps=25)
    for gen,entry in list(starts.items()):
        if not entry['live'] or entry['slot']<2 or gen in proofs or gen not in poisoned:continue
        t=task(entry['slot']);w=struct.unpack('<6Q',user(t,CONFIG['pool_pio_child'],48))
        if not w[3] or not w[5]:continue
        assert w[:3]==(0x31444c4948504950,(gen<<32)|entry['slot'],entry['kind']) and 1<=w[3]<=4
        # The current child reaches its next syscall only after its heap fill;
        # never inspect another task while it might be preempted mid-fill.
        if slot!=entry['slot']:continue
        data=user(t,w[5],8192);assert data==bytes((i^entry['slot']^0x5a)&255 for i in range(8192))
        leaves=file_leaves(t);pages=[p for p in range(64) if copies[gen][24+p] in (4,5)]
        for p,raw in zip(pages,file_pages([leaves[p]&MASK for p in pages])):
            assert raw==copies[gen][96+p*4096:96+(p+1)*4096]
        assert q(CS['native_heap_state']+232+entry['slot']*99368)==gen
        proofs.add(gen);emit('witness',gen=gen,parent=entry['parent'],heap=8192,immutable=1,sha=hashlib.sha256(data).hexdigest())
'''

CREATE_BEGIN=r'''
def create_begin():
    global created,source_pointer,allocation_count,allocation_before,allocation_owner,source_pending,inject_driver
    assert created is None and create_begin_hook.enabled and not copy_hook.enabled and not create_end_hook.enabled
    create_begin_hook.enabled=False;copy_hook.enabled=create_end_hook.enabled=True
    assert not source_pending and d(S['scheduler_current_slot'])==0
    source_pointer=q(S['family_request']+24);created=True;allocation_count=0
    allocation_before=free();allocation_owner=q(S['family_records'])
    root=struct.unpack('<17Q',user(task(0),CONFIG['pool_pio_root'],136))
    inject_driver=root[3]==2 and not root[4]
    allocator.enabled=True
'''
CREATE_END=pool.CREATE_END.replace('    global created','    global created,source_pending').replace(
    '    allocator.enabled=False;assert created','    allocator.enabled=False;assert created and copy_hook.enabled and create_end_hook.enabled\n    copy_hook.enabled=create_end_hook.enabled=False').replace(
    '        created_sources[gen]=source_pointer','        created_sources[gen]=source_pointer;source_pending=gen')

FAULT=r'''
def fault():
    assert mode()==8 and CASE in (7,11)
    trace_drain();syscall()
    slot=d(S['scheduler_current_slot']);gen=task(slot)[1];f=struct.unpack('<22Q',mem(reg('rdi'),176))
    assert f[15]==6 and f[18]==0x33
    assert slot==0 if CASE==11 else slot==DRIVER_SLOT and gen in proofs
    if CASE==11:cancel_hook.enabled=True
    emit('fault',gen=gen,slot=slot,vector=6)
'''
CANCEL=r'''
def cancel():
    trace_drain();slot=reg('rdi');t=task(slot);gen=t[1]
    assert 2<=slot<=DRIVER_SLOT and t[0] in (1,6) and gen in proofs
    assert slot<DRIVER_SLOT or CASE in (8,10,11)
    reason=3 if CASE==11 else 2;assert d(S['family_reasons']+slot*4)==reason
    emit('cancel',gen=gen,slot=slot,state=t[0],reason=reason)
    if CASE!=11:cancel_hook.enabled=False
'''
FINISH=helpers.once(pool.FINISH,"gen=max(g for g,e in starts.items() if e['slot']==slot)",
    "gen=max((g for g,e in starts.items() if e['slot']==slot),default=0)")
FINISH=helpers.once(FINISH,'per=9 if CASE==6 else 8','per=PER')
FINISH=helpers.once(FINISH,"    if runs==2:gdb.execute('detach');gdb.execute('quit')",r'''
    assert len(poisoned)==len(proofs) and len(peers)==runs
    assert pstate()==(0,0xffffffffffffffff,1,0,0,0,0,0) and not any(mem(S['native_pio_request'],64))
    assert not create_begin_hook.enabled and not copy_hook.enabled and not create_end_hook.enabled and not source_pending
    cancel_hook.enabled=False
    if runs==2:gdb.execute('detach');gdb.execute('quit')''')


def observer_body():
    code=pool.observer_body()
    code=helpers.once(code,"'TASK_POOL '","'POOL_PIO '")
    for name,body in (('start',START),('syscall',SYSCALL),('create_begin',CREATE_BEGIN),('create_end',CREATE_END),
                      ('fault',FAULT),('cancel',CANCEL),('finish',FINISH)):
        code=helpers.replace_function(code,name,body)
    # Pool-only receipt-capacity observer is not part of this workload; all
    # frame/context/completion checks above remain the actual shared source.
    begin=code.index('# OOM is armed only in a first root0 CREATE')
    code=code[:begin]
    allocation='def allocation():'+EXTRA.split('def allocation():',1)[1].split('allocator.fn=allocation',1)[0]
    code=helpers.replace_function(code,'allocation',allocation)
    code+=TRACE_CORE+EXTRA.replace(allocation,'')
    code=helpers.once(code,"    tables=list(struct.unpack('<4Q'", "    pio_retire(slot,gen)\n    tables=list(struct.unpack('<4Q'")
    code=profile.scope_validator_page_hooks(code)
    code=profile.scope_runtime_page_hooks(code)
    code=helpers.once(code,'assert slot<4 and task(slot)[1]==gen','assert slot<8 and task(slot)[1]==gen')
    code=helpers.once(code,'assert len(release_pending)<4','assert len(release_pending)<8')
    for symbol,fn,name in (('family_create64.found','create_begin','create_begin_hook'),
                          ('family_create64.stack_ready','copy','copy_hook'),('family_create64.parent_result','create_end','create_end_hook'),
                          ('family_cancel_one64','cancel','cancel_hook')):
        code=helpers.once(code,"Hook('"+symbol+"',"+fn+")",name+"=Hook('"+symbol+"',"+fn+");"+name+".enabled=False")
    for suffix,fn,name in (('before_clear','trace_before_clear','trace_before_hook'),('after_clear','trace_after_clear','trace_after_hook')):
        code=helpers.once(code,"Hook('native_pio_finish64.trace_"+suffix+"',"+fn+")",name+"=Hook('native_pio_finish64.trace_"+suffix+"',"+fn+");"+name+".enabled=False")
    code=helpers.once(code,"            starts[r['gen']]['live']=False", "            starts[r['gen']]['live']=False\n            if not any(e['live'] for e in starts.values()):trace_before_hook.enabled=trace_after_hook.enabled=True")
    return code


EXTRA=r'''
FILLERS=CONFIG['fillers'];DRIVER_SLOT=FILLERS+2;PER=CONFIG['per']
source_pending=0;poisoned=set();peers=set();inject_driver=False
devices={};pio_owner=0;port_events=0;trace_sequence=0;trace_digest=hashlib.sha256();results=set()
def allocation():
    global allocation_count
    if OOM is not None and inject_driver and allocation_owner not in injected and allocation_count==OOM:
        ret=q(reg('rsp'));gdb.execute('set $rax=0');gdb.execute('set $rsp=$rsp+8');gdb.execute('set $rip='+hex(ret))
        injected.add(allocation_owner);allocator.enabled=False;emit('oom',owner=allocation_owner,acquired=allocation_count)
    else:allocation_count+=1
allocator.fn=allocation
def pstate():
    v=struct.unpack('<8Q',mem(S['native_pio_state'],64))
    assert v[1]==v[0]^0xffffffffffffffff and v[2] in (0,1) and v[5]<=64 and not v[7]
    assert v[3]<=v[4]<1<<60 and v[6]<=v[4]
    assert 2<=v[0]&0xffffffff<8 and 0<v[0]>>32<=0x7fffffff if v[0] else v==(0,0xffffffffffffffff,1,0,0,0,0,0)
    return v
def trace_drain():
    global trace_sequence
    raw=trace_snapshot(mem,S['native_pio_trace'],trace_sequence)
    for event in trace_decode(raw,trace_sequence):
        (out if event[0]==1 else data)(event)
        offset=16+((event[1]-1)&63)*192;trace_digest.update(raw[offset:offset+192]);trace_sequence=event[1]
def trace_before_clear():
    trace_drain();assert trace_sequence and pstate()[2]==1
    emit('trace_drained',run=runs+1,events=trace_sequence,sha=trace_digest.hexdigest())
Hook('native_pio_finish64.trace_before_clear',trace_before_clear)
def trace_after_clear():
    global trace_sequence,trace_digest
    trace_clean(mem(S['native_pio_trace'],12304));emit('trace_clean',run=runs+1,bytes=12304)
    trace_sequence=0;trace_digest=hashlib.sha256();trace_before_hook.enabled=trace_after_hook.enabled=False
Hook('native_pio_finish64.trace_after_clear',trace_after_clear)
def out(event):
    global pio_owner,port_events
    port_events+=1;assert port_events<=512
    v=event[2];owner=v[0];port,value,slot,gen,parent=event[3]
    assert owner&0xffffffff==DRIVER_SLOT
    if port==0x3f6 and value==6:
        assert owner
        if owner!=pio_owner:
            if pio_owner:assert devices[pio_owner]['retired']
            assert slot==0 and not v[2] and owner not in devices and parent==gen<<32
            assert owner>>32 in starts and starts[owner>>32]['parent']==gen
            pio_owner=owner
            devices[owner]=dict(parent=parent,retired=False,released=False,reset=True,command=0,identify=bytearray(),data=bytearray(),lbas=[],lba=0,requests=0,pending=None)
            emit('bind',gen=owner>>32,owner=owner)
        else:devices[owner]['reset']=True
    else:
        assert owner==(gen<<32)|slot and slot==DRIVER_SLOT and not v[2]
        item=devices[owner];assert not item['retired']
        if port==0x3f6:assert value==2 and item['reset'] and v[4]>v[6];item['released']=True
        else:
            assert item['released']
            if port==0x1f7:
                assert value in (0xec,0x20)
                if value==0xec:assert item['command']==0
                else:
                    assert len(item['identify'])==512 and len(item['lbas'])<2
                    assert len(item['data'])==512*len(item['lbas']) and item['lba']<=1
                    item['lbas'].append(item['lba'])
                item['command']=value
            elif port==0x1f6:assert value==0xe0
            elif port==0x1f2:assert value==1
            elif port==0x1f3:assert value<=1;item['lba']=value
            else:assert port in (0x1f4,0x1f5) and value==0
    assert parent==devices[owner]['parent']
def data(event):
    v=event[2];request=event[3]
    assert request[:4]==(2,64,4,0) and request[4]==v[0] and not v[2]
    assert request[5:9]==(0x1f0,0,16,0) and not request[11] and event[5]==16
    assert v[4]*10<request[10]<=v[4]*10+1000
    item=devices[v[0]];assert item['released'] and not item['retired']
    key='identify' if item['command']==0xec else 'data'
    assert item['command'] in (0xec,0x20) and len(item[key])<=(480 if key=='identify' else 992)
    if key=='data':assert event[4]==bytes((n^(item['lba']*17)^0xa5)&255 for n in range(len(item[key])%512,len(item[key])%512+32))
    item[key].extend(event[4])
def pio_retire(slot,gen):
    trace_drain();v=pstate()
    assert not any(mem(S['native_pio_request'],64)) and not any(mem(S['family_extended_masks']+slot*16,16))
    if slot in (0,DRIVER_SLOT):assert v[2]==1
    if slot!=DRIVER_SLOT:return
    owner=(gen<<32)|slot;item=devices[owner]
    assert v[0]==owner and item['reset'] and item['released'] and not item['retired']
    item['retired']=True;ident=bytes(item['identify']);raw=bytes(item['data'])
    if CASE==12:assert not ident and not raw
    else:
        assert len(ident)==512 and struct.unpack_from('<H',ident,98)[0]&512 and struct.unpack_from('<I',ident,120)[0]==128
        expected=b''.join(bytes((n^(lba*17)^0xa5)&255 for n in range(512)) for lba in item['lbas'])
        assert raw==expected[:len(raw)]
    emit('retire',gen=gen,identify=len(ident),data=len(raw),lbas=item['lbas'],sha=hashlib.sha256(raw).hexdigest(),fenced=1)
def rpc():
    if mode()!=8 or q(S['syscall_rax'])!=53:return
    trace_drain();slot=d(S['scheduler_current_slot']);t=task(slot)
    assert slot in (0,DRIVER_SLOT) and pio_owner
    raw=user(t,q(S['syscall_rsi']),140);version,size,length=struct.unpack_from('<3I',raw)
    if slot==DRIVER_SLOT and (version,size,length)==(1,140,16):
        gen,kind,phase,value=struct.unpack_from('<4I',raw,12)
        assert gen==t[1] and kind==starts[gen]['kind'] and phase in (0,1)
        assert value==(256 if phase else 19 if CASE==12 else 128)
        if not phase:
            state=user(t,CONFIG['service'],128);p=struct.unpack_from('<4IQ',state,104)
            assert p[:4]==(1,24,1,0) and q(S['scheduler_last_tick'])*10<p[4]<=q(S['scheduler_last_tick'])*10+3000
            assert struct.unpack_from('<Q',state,72)[0]==pio_owner
            if CASE!=12:assert struct.unpack_from('<3Q3I',state)[:2]==(pio_owner,1) and struct.unpack_from('<3I',state,24)==(128,0,1)
            emit('ready',gen=gen,limit=1,capacity=value,deadline=p[4])
        else:emit('partial',gen=gen,bytes=256,mode=kind)
        return
    item=devices[pio_owner];h=struct.unpack_from('<4I4QIiQ',raw,12)
    if slot==0:
        assert (version,size,length)==(1,140,64) and not any(raw[76:])
        assert item['pending'] is None and item['requests']==0
        assert h[:7]==(1,64,1,0,pio_owner,1,1) and h[8:]==(512,0,0)
        assert q(S['scheduler_last_tick'])*10<h[7]<=q(S['scheduler_last_tick'])*10+1000
        item['requests']=1;item['pending']=(h,len(item['data']))
        emit('request',gen=pio_owner>>32,sequence=1,lba=1,deadline=h[7])
    else:
        assert (version,size,length)==(2,2060,576) and item['pending'] is not None
        previous,before=item['pending'];bad=starts[t[1]]['kind']==10
        assert h[:5]==(1,64,1,1,pio_owner) and h[5]==(0 if bad else 1) and h[6:8]==previous[6:8] and h[8:]==(512,0,0)
        full=user(t,q(S['syscall_rsi']),2060);assert not any(full[588:])
        assert full[76:588]==bytes(item['data'][-512:]) and len(item['data'])==before+512
        emit('reply',gen=t[1],sequence=1,status=0,bytes=512,bad=int(bad),deadline=h[7]);item['pending']=None
Hook('process_ipc_syscall64',rpc)
def result():
    root=task(0);w=struct.unpack('<17Q',user(root,CONFIG['pool_pio_root'],136))
    assert w[0]==0x31544f4f52504950 and w[1]==CASE
    if w[3]!=4 or (w[4],w[5]) in results:return
    owner,sequence,lba,status,address=w[4:9]
    assert owner==pio_owner and sequence==lba==1
    results.add((owner,sequence));actual=user(root,address,512)
    if status>=1<<63:status-=1<<64
    assert actual==(bytes([0xcc])*512 if status else bytes((n^17^0xa5)&255 for n in range(512)))
    emit('result',gen=owner>>32,sequence=sequence,status=status,bytes=512,sha=hashlib.sha256(actual).hexdigest())
    if status:devices[owner]['pending']=None
'''


def _validate(serial,trace,case,oom,count,child_sha):
    fillers,driver,per=dimensions(case)
    def need(value,message):
        if not value:raise ValueError('pool PIO '+message)
    need(oom=={13:0,14:count//2,15:count-1}.get(case),'OOM selector')
    common=[m for m in transport.REQUIRED_MARKERS if 'SHELL' not in m]+[wide.process.SUCCESS]
    need(not any(m in serial for m in transport.FAILURES) and 'OBSERVER_FAIL' not in trace,'kernel/observer failure')
    need(all(serial.count(m)==1 for m in common) and [serial.index(m) for m in common]==sorted(serial.index(m) for m in common),'progress')
    receipts=list(wide.process.REAP.finditer(serial));ends=list(re.finditer(wide.process.DONE,serial))
    need(len(receipts)==serial.count('PROCESS_REAP_OK')==2*per and len(ends)==2,'receipt count')
    events=[json.loads(line[9:]) for line in trace.splitlines() if line.startswith('POOL_PIO ')]
    allowed={'boot','start','mode','copy','create','source','witness','peer','release','finish','fault','cancel','oom','rollback',
             'bind','ready','partial','request','reply','result','retire','trace_drained','trace_clean'}
    need(all(e.get('kind') in allowed for e in events),'unknown event')
    def get(kind):return [e for e in events if e['kind']==kind]
    need(get('boot')==[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)],'boot mapping')
    starts=get('start');bygen={e['gen']:e for e in starts}
    need(len(starts)==len(bygen)==2*per and sorted(bygen)==list(range(1,2*per+1)),'unique generations')
    expected={};drivers=[];children=[];cancelled=[];faulted=[]
    for run in range(2):
        base=run*per;group=[e for e in starts if base<e['gen']<=base+per]
        need(set(e['slot'] for e in group)==set(range(driver+1)) and max(e['live'] for e in group)==driver+1,'simultaneous capacity')
        for slot,status in ((0,134 if case==11 else 79 if case==12 else 78),(1,77)):
            expected[base+slot+1]=(slot,0,-1,-1,slot+3,status,3 if case==11 and slot==0 else 4)
        for n in range(fillers):
            gen=base+n+3;expected[gen]=(n+2,base+1,256,-1,n+7,0,3);children.append(gen);cancelled.append(gen)
        for round_ in range(1 if case==11 else 2):
            gen=base+fillers+3+round_;kind=0 if round_ else 8 if case==11 else case if case in (7,8,9,10) else 0
            status=0 if case==11 or kind in (8,10) else 134 if kind==7 else 256 if kind==9 else 89 if case==12 else 80
            expected[gen]=(driver,base+1,kind,round_,driver+5,status,3 if case==11 or kind else 4)
            drivers.append(gen);children.append(gen)
            if case==11 or kind in (8,10):cancelled.append(gen)
            if kind==7:faulted.append(gen)
        if case==11:faulted.append(base+1)
    for gen,e in bygen.items():
        slot,parent,kind,round_,image,_,_=expected[gen]
        need((e['slot'],e['parent'],e['role'],e['round'],e['image'])==(slot,parent,kind,round_,image),'owner/image binding')
        need(1<=e['private']<=e['pages']<=65 and 1<=e['live']<=driver+1,'mapped bounds')
    rows=[]
    for run in range(2):
        seen=set()
        for m in receipts[run*per:(run+1)*per]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]))
            need(gen in expected and gen not in seen and run*per<gen<=(run+1)*per,'receipt generation')
            seen.add(gen);e=expected[gen]
            need((slot,status,state)==(e[0],e[5],e[6]) and ticks<=32 and 0x410000<=rip<0x440000,'terminal outcome')
            need(status!=256 or ticks==32,'CPU exhaustion')
            need((ends[run-1].end() if run else -1)<m.start()<m.end()<=ends[run].start(),'receipt order')
            rows.append((slot,gen))
    need([(e['slot'],e['gen']) for e in get('release')]==rows,'exact frame ledger')
    for e in get('release'):
        need(e['fenced']==1 and 0<e['frames']<=69 and 0<e['before']<e['after']==e['before']+e['frames']<=4194304,'frame balance')
    for kind in ('copy','create','source','witness'):
        group=get(kind);need(len(group)==len(children) and {e['gen'] for e in group}==set(children),'exact '+kind)
        for e in group:
            target=expected[e['gen']]
            if kind=='copy':need((e['bytes'],e['sha'])==(SIZE,child_sha),'immutable record')
            if kind=='create':need((e['slot'],e['owner'],e['acquired'])==(target[0],target[1]<<32,count),'construction owner/count')
            if kind=='source':need((e['bytes'],e['poison'])==(SIZE,165),'source overwrite')
            if kind=='witness':
                sha=hashlib.sha256(bytes((i^target[0]^0x5a)&255 for i in range(8192))).hexdigest()
                need((e['parent'],e['heap'],e['immutable'],e['sha'])==(target[1],8192,1,sha),'private heap/immutable image')
    need([e['gen'] for e in get('mode')]==[1,per+1],'mode count')
    for e in get('mode'):
        need((e['slot'],e['before'],e['value'])==(0,0,case) and 0x410000<=e['address']<0x440000 and not e['address']&7 and
             0x100000000<=e['physical']<0x400000000,'mode authority')
    need(get('peer')==[dict(kind='peer',gen=g,sleeps=25) for g in (2,per+2)],'unrelated peer progress')
    need(len(get('cancel'))==len(cancelled) and {e['gen'] for e in get('cancel')}==set(cancelled),'cancel count')
    for e in get('cancel'):need(e['slot']==expected[e['gen']][0] and e['reason']==(3 if case==11 else 2) and e['state'] in (1,6),'cancel reason')
    need(len(get('fault'))==len(faulted) and {e['gen'] for e in get('fault')}==set(faulted),'fault count')
    for e in get('fault'):need(e['slot']==expected[e['gen']][0] and e['vector']==6,'fault reason')
    for kind in ('oom','rollback'):
        group=get(kind);need([(e['owner'],e['acquired']) for e in group]==([(g<<32,oom) for g in (1,per+1)] if oom is not None else []),'OOM scope')
        if kind=='rollback':need(all(0<e['free']==e['before']<=4194304 for e in group),'OOM rollback')
    for kind in ('bind','ready','retire'):
        need([e['gen'] for e in get(kind)]==drivers,'device '+kind+' count')
    for e in get('bind'):need(e['owner']==(e['gen']<<32)|driver,'bound driver')
    for e in get('ready'):need((e['limit'],e['capacity'])==(1,19 if case==12 else 128) and 0<e['deadline']<(1<<60)*10,'fresh self-test')
    partial=[g for g in drivers if expected[g][2] in (7,8,9)]
    need(get('partial')==[dict(kind='partial',gen=g,bytes=256,mode=expected[g][2]) for g in partial],'partial transfer')
    requests=[] if case==12 else drivers
    replies=[g for g in requests if expected[g][2] in (0,10)]
    results=[] if case in (11,12) else requests
    for kind,gens in (('request',requests),('reply',replies),('result',results)):
        need([e['gen'] for e in get(kind)]==gens,'RPC '+kind+' count')
        for e in get(kind):
            need(e['sequence']==1,'RPC sequence')
            if kind=='request':need(e['lba']==1 and 0<e['deadline']<(1<<60)*10,'RPC deadline/LBA')
            if kind=='reply':
                req=next(r for r in get('request') if r['gen']==e['gen'])
                need((e['status'],e['bytes'],e['bad'],e['deadline'])==(0,512,int(expected[e['gen']][2]==10),req['deadline']),'RPC reply bytes/deadline')
            if kind=='result':
                fault=expected[e['gen']][2]
                need(e['status']==(-71 if fault==10 else 0) if fault in (0,10) else e['status'] in (-32,-110),'caller result')
                raw=bytes([0xcc])*512 if fault else bytes((i^17^0xa5)&255 for i in range(512))
                need(e['bytes']==512 and e['sha']==hashlib.sha256(raw).hexdigest(),'caller complete output')
    for e in get('retire'):
        partial_=expected[e['gen']][2] in (7,8,9)
        count_=0 if case==12 else 768 if partial_ else 1024
        raw=b''.join(bytes((i^(lba*17)^0xa5)&255 for i in range(512)) for lba in (0,1))[:count_]
        need((e['identify'],e['data'],e['lbas'],e['sha'],e['fenced'])==(0 if case==12 else 512,count_,[] if case==12 else [0,1],hashlib.sha256(raw).hexdigest(),1),'physical data/fence')
    need(len(get('finish'))==len(get('trace_drained'))==len(get('trace_clean'))==2,'final count')
    for run in range(1,3):
        e=get('finish')[run-1];need((e['run'],e['tasks'],e['generation'],e['zero'])==(run,per,run*per,1) and 0<e['free']==e['initial']<=4194304,'final zero/free')
        e=get('trace_drained')[run-1];need(e['run']==run and 0<e['events']<=4096 and re.fullmatch('[0-9a-f]{64}',e['sha']),'trace ledger')
        need(get('trace_clean')[run-1]==dict(kind='trace_clean',run=run,bytes=12304),'trace zero')
    def at(kind,gen):return next(i for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen)
    for gen,e in bygen.items():
        first,last=at('start',gen),at('release',gen);run=(gen-1)//per
        need(first<last<events.index(get('trace_drained')[run])<events.index(get('trace_clean')[run])<events.index(get('finish')[run]),'retirement/finish order')
        if gen in children:
            need(at('copy',gen)<at('create',gen)<first<at('witness',gen)<last,'publication order')
            need(at('create',gen)<at('source',gen)<at('witness',gen),'source isolation order')
        if e['slot']==0:need(first<at('mode',gen)<last,'mode lifetime')
        if e['slot']==1:need(first<at('peer',gen)<last,'peer lifetime')
        if gen in cancelled:need(at('witness',gen)<at('cancel',gen)<last,'cancel/fence order')
        if gen in faulted:need(first<at('fault',gen)<last,'fault/fence order')
        if gen in drivers:
            need(first<at('bind',gen)<at('ready',gen)<at('retire',gen)<last,'device lifecycle order')
            for kind in ('partial','request','reply','result'):
                group=[(i,r) for i,r in enumerate(events) if r['kind']==kind and r['gen']==gen]
                if group:
                    pos=group[0][0];need(at('ready',gen)<pos,'RPC after self-test')
                    if kind in ('partial','request','reply'):need(pos<at('retire',gen),'RPC before device reap')
                    if kind in ('partial','reply','result'):need(at('request',gen)<pos,'RPC cause')
            if e['round']==1:need(at('release',gen-1)<at('copy',gen),'replacement after reap')
    return rows


def validate(*args):
    try:return _validate(*args)
    except (KeyError,TypeError,StopIteration,struct.error,IndexError) as error:raise ValueError('malformed pool PIO evidence: '+str(error)) from error


def observer(config,folder,case,oom):
    fillers,_,per=dimensions(case)
    mask=sum(1<<n for n in (4,5,6,9,22,40,41,42,49,50,51,52,53,54,55,58))
    settings=dict(config,case=case,oom=oom,fillers=fillers,per=per,mask=mask)
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+
        '\n'+observer_body()+'\nend\ncontinue\n')


def fatal_mutation(kind,saved):
    """The complete, byte-exact authority for the two destructive guest edits."""
    sizes=(64,8192,512,256,128,192)
    if kind not in FATAL_CASES or len(saved)!=6 or tuple(map(len,saved))!=sizes:raise ValueError('fatal input')
    state=struct.unpack('<8Q',saved[0]);owner=state[0]
    if not (2<=owner&0xffffffff<8 and 0<owner>>32<=0x7fffffff and state[1]==owner^0xffffffffffffffff and
            state[2] in (0,1) and state[3]<=state[4]<1<<60 and state[5]<=64 and state[6]<=state[4] and not state[7]):
        raise ValueError('fatal original owner')
    result=list(saved)
    if kind=='owner-slot8':
        if state[2]:raise ValueError('fatal owner not released')
        value=(owner&0xffffffff00000000)|8
        result[0]=struct.pack('<2Q',value,value^0xffffffffffffffff)+saved[0][16:]
        writes=[(0,0,result[0][:16])]
    else:
        if not state[2] or any(struct.unpack_from('<Q',saved[1],slot*1024)[0] for slot in range(8)):
            raise ValueError('fatal pool not retired')
        result[1]=saved[1][:7168]+struct.pack('<Q',1)+saved[1][7176:]
        writes=[(1,7168,struct.pack('<Q',1))]
    return result,writes


FATAL_BODY=r'''
from pathlib import Path
import gdb,struct,json,hashlib
S=CONFIG['s'];KIND=CONFIG['kind'];OUT=Path(CONFIG['out'])
RANGES=[(S[name],size) for name,size in (
    ('native_pio_state',64),('scheduler_tasks',8192),('family_records',512),
    ('family_profiles',256),('family_extended_masks',128),('process_ipc_completions',192))]
released=False;injected=False;fenced=False;diagnosed=False;saved=None;ports=0;retired=[]
inferior=gdb.selected_inferior()
def reg(name):return int(gdb.parse_and_eval('$'+name))&0xffffffffffffffff
def mem(address,size):return bytes(inferior.read_memory(address,size))
def q(address):return struct.unpack('<Q',mem(address,8))[0]
def state():return [mem(a,n) for a,n in RANGES]
def event(kind,**values):gdb.write('POOL_PIO_FATAL '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\n')
def snapshot(name,values):
    raw=b''.join(values)
    with (OUT/(name+'.bin')).open('xb') as stream:stream.write(raw)
    return hashlib.sha256(raw).hexdigest()
class Probe(gdb.Breakpoint):
    def __init__(self,address,label,enabled=True):
        super().__init__('*'+hex(address),internal=True);self.label=label;self.enabled=enabled
    def stop(self):
        try:self.observe()
        except Exception as error:
            gdb.write('POOL_PIO_FATAL_OBSERVER_FAIL '+self.label+' '+repr(error)+'\n');gdb.execute('quit 71')
        return False
    def observe(self):
        global released,injected,fenced,diagnosed,saved,ports
        if self.label=='port':
            ports+=1;assert ports<=128
            port=reg('edx')&65535;value=reg('eax')&255
            assert mem(S['native_pio_out8.done']-1,1)==b'\xee' # Stop after actual OUT DX,AL.
            if injected:
                assert not fenced and port==0x3f6 and value==6 and state()==saved
                fenced=True;self.enabled=False
                event('fence',physical=1,sha=snapshot('fenced',state()))
            elif port==0x3f6 and value==2:
                assert not released and not q(S['native_pio_state']+16)
                released=True;self.enabled=False;event('release')
                if KIND=='owner-slot8':trigger.enabled=True
        elif self.label=='reap':
            if mem(S['scheduler_mode'],1)!=b'\x08' or reg('rdi')!=4:return
            assert not injected and released and len(retired)<4
            slot=reg('rsi');gen=reg('rdx');assert slot<8 and 0<gen<=4 and q(S['scheduler_tasks']+slot*1024+8)==gen
            assert (slot,gen) not in retired and not reg('eflags')&512
            retired.append((slot,gen));event('reap_before',slot=slot,gen=gen)
            if len(retired)==4:trigger.enabled=True;self.enabled=False
        elif self.label=='trigger':
            assert released and not injected
            assert len(retired)==(4 if KIND=='retirement-slot7' else 0)
            self.enabled=False;before=state();changed,writes=fatal_mutation(KIND,before)
            original=snapshot('before',before)
            for index,offset,raw in writes:inferior.write_memory(RANGES[index][0]+offset,raw)
            assert state()==changed
            saved=changed;injected=True;port_hook.enabled=True
            for hook in forbidden:hook.enabled=True
            event('inject',case=KIND,original=original,sha=snapshot('damaged',saved),writes=sum(len(w[2]) for w in writes))
        elif self.label=='diagnostic':
            if not released:return
            assert injected and fenced and not diagnosed and state()==saved and not reg('eflags')&512
            diagnosed=True;event('diagnostic',sha=snapshot('diagnostic',state()),interrupts=0)
        elif self.label=='halt':
            assert injected and fenced and diagnosed and state()==saved and not reg('eflags')&512
            assert mem(S['halt64'],4)==b'\xfa\xf4\xeb\xfd'
            event('halt',sha=snapshot('halt',state()),cli_hlt=1)
            gdb.execute('detach');gdb.execute('quit 0')
        elif self.label=='forbidden':raise AssertionError('cleanup/resume after fatal injection')
port_hook=Probe(S['native_pio_out8.done'],'port')
trigger=Probe(S['native_pio_syscall64'] if KIND=='owner-slot8' else S['native_pio_finish64'],'trigger',False)
Probe(S['process_ipc_service64'],'reap',KIND=='retirement-slot7')
Probe(S['serial_init64'],'diagnostic');Probe(S['halt64'],'halt')
forbidden=[Probe(S[name],'forbidden',False) for name in (
    'process_run_resume64','family_terminal64','scheduler_force_cleanup64','scheduler_release_task_frames64')]
'''


def fatal_observer(config,folder,kind):
    if kind not in FATAL_CASES:raise ValueError('fatal case')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+
        repr(dict(s=config['s'],kind=kind,out=folder.as_posix()))+'\nFATAL_CASES='+repr(FATAL_CASES)+'\n'+
        inspect.getsource(fatal_mutation)+FATAL_BODY+'\nend\ncontinue\n')


def validate_fatal(serial,trace,kind,folder):
    if kind not in FATAL_CASES or 'OBSERVER_FAIL' in trace:raise ValueError('fatal case/observer')
    events=[json.loads(line[15:]) for line in trace.splitlines() if line.startswith('POOL_PIO_FATAL ')]
    reaps=[e for e in events if e.get('kind')=='reap_before']
    kinds=['release']+(['reap_before']*4 if kind=='retirement-slot7' else [])+['inject','fence','diagnostic','halt']
    if [e.get('kind') for e in events]!=kinds:raise ValueError('fatal exact order')
    if events[0]!=dict(kind='release'):raise ValueError('fatal release')
    records=list(wide.process.REAP.finditer(serial))
    if len(records)!=serial.count('PROCESS_REAP_OK'):raise ValueError('fatal malformed receipt')
    if len(records)!=(4 if kind=='retirement-slot7' else 0):raise ValueError('fatal reap count')
    expected={1:(0,78),2:(1,77),3:(2,80),4:(2,80)};rows=[]
    for m in records:
        slot,gen,status,terminal,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]))
        if gen not in expected or expected[gen]!=(slot,status) or terminal!=4 or ticks>32 or not 0x410000<=rip<0x440000:
            raise ValueError('fatal prior outcome')
        rows.append((slot,gen))
    if len(set(rows))!=len(rows) or reaps!=[dict(kind='reap_before',slot=s,gen=g) for s,g in rows]:raise ValueError('fatal reap binding')
    marker='REIST_X86_64_EXCEPTION_FATAL pio=1'
    if serial.count('REIST_X86_64_EXCEPTION_FATAL')!=1 or marker not in serial or any(m in serial for m in (wide.process.DONE,wide.process.SUCCESS)):
        raise ValueError('fatal diagnostic/continued runtime')
    if any(m.end()>serial.index(marker) for m in records):raise ValueError('fatal later reap')
    sizes=(64,8192,512,256,128,192);total=sum(sizes)
    def read(name):
        path=folder/(name+'.bin');pio.regular(path,total)
        raw=path.read_bytes()
        if len(raw)!=total:raise ValueError('fatal snapshot length')
        pos=0;parts=[]
        for size in sizes:parts.append(raw[pos:pos+size]);pos+=size
        return raw,parts
    raw,before=read('before');changed,writes=fatal_mutation(kind,before);damaged=b''.join(changed)
    sha=hashlib.sha256(damaged).hexdigest()
    if events[-4]!=dict(kind='inject',case=kind,original=hashlib.sha256(raw).hexdigest(),sha=sha,writes=sum(len(w[2]) for w in writes)):
        raise ValueError('fatal write binding')
    if events[-3:]!=[dict(kind='fence',physical=1,sha=sha),dict(kind='diagnostic',sha=sha,interrupts=0),dict(kind='halt',sha=sha,cli_hlt=1)]:
        raise ValueError('fatal exact fence/diagnostic/halt')
    if any(read(name)[0]!=damaged for name in ('damaged','fenced','diagnostic','halt')):raise ValueError('fatal metadata changed')
    return rows


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--fatal',action='store_true')
    args=parser.parse_args();image=args.image.resolve();base=args.evidence.resolve()
    if base!=(BASE/('fatal-guests' if args.fatal else 'guests')).resolve():parser.error('pool PIO evidence scope')
    import verify_x86_64_pool_pio as verify
    binding=verify.admit_runtime(image,fatal=args.fatal)
    previous=sorted(base.glob('attempt-*/summary.json'))
    if len(previous)>=3:raise ValueError('pool PIO matrix budget exhausted')
    for path in previous:
        old=json.loads(path.read_text())
        if old['candidate']==binding['candidate'] or not old.get('closed'):raise ValueError('pool PIO unchanged/unfinished retry')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True);pio.safe_folder(folder)
    result=dict(passed=False,closed=False,candidate=binding['candidate'],image_sha256=digest(image),fatal=args.fatal,cases=[])
    (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    begin=time.monotonic();spent=0
    try:
        config=image_config(image);count=wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
        result.update(allocations=count,child_sha256=sha)
        for case,ram in (tuple((k,4096) for k in FATAL_CASES) if args.fatal else CASES):
            if digest(image)!=result['image_sha256']:raise ValueError('pool PIO image changed')
            oom={13:0,14:count//2,15:count-1}.get(case);out=folder/f'guest-{case}-{ram}';out.mkdir()
            row=dict(case=case,ram=ram,oom=oom,passed=False);result['cases'].append(row);started=time.monotonic()
            try:
                # Creating/checking/closing only this generated medium counts
                # against the same original20s, including failure cleanup.
                fixture=None if case==12 else pio.Fixture(out,block=True)
                code=fatal_observer(config,out,case) if args.fatal else observer(config,out,case,oom)
                serial,trace=transport.capture(image,out,code,ram,fixture,halt_witness=args.fatal,
                    diagnostic_metrics=True,**({} if args.fatal else dict(binary_memory='equivalence')))
                rows=validate_fatal(serial,trace,case,out) if args.fatal else validate(serial,trace,case,oom,count,sha)
                row['tasks']=len(rows)
            finally:
                elapsed=time.monotonic()-started;spent+=elapsed;row['elapsed']=round(elapsed,6)
            if elapsed>20 or spent>(40 if args.fatal else 320):raise ValueError('pool PIO immutable guest deadline')
            row['passed']=True
            print(f'POOL_PIO_GUEST_OK case={case} ram={ram} tasks={row["tasks"]} elapsed={elapsed:.3f}',flush=True)
        result['passed']=True;return 0
    except (ValueError,RuntimeError,OSError,KeyError,AssertionError) as error:
        result['error']=str(error);print('POOL_PIO_FAIL '+str(error),flush=True);return 1
    finally:
        result.update(closed=True,elapsed=round(time.monotonic()-begin,6),guest_elapsed=round(spent,6))
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('POOL_PIO_EVIDENCE '+str(folder),flush=True)


if __name__=='__main__':raise SystemExit(main())
