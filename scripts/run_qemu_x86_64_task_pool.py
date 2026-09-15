"""One immutable native pool build, ten bounded guests, no device authority."""
from pathlib import Path
import argparse,hashlib,json,re,struct,time,uuid
import run_qemu_x86_64_file_launch as helpers
wide=helpers.wide;transport=wide.transport;payload=wide.payload;ROOT=wide.ROOT
SIZE=266336
CASES=tuple((case,8192 if case==1 else 4096) for case in range(10))


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observer_body():
    code=helpers.once(wide.OBSERVER,"'WIDE '","'TASK_POOL '")
    begin=code.index('def poison():');end=code.index('boot_seen=False',begin)
    code=code[:begin]+code[end:]
    code=helpers.replace_function(code,'user',helpers.FILE_USER_READ)
    for name,body in (('start',START),('copy',COPY),('syscall',SYSCALL),('fault',FAULT),
                      ('cancel',CANCEL),('create_begin',CREATE_BEGIN),('create_end',CREATE_END),('finish',FINISH)):
        code=helpers.replace_function(code,name,body)
    code=helpers.once(code,"    release=dict(slot=slot,gen=gen,frames=frames,freed=[],before=free(),ret=q(reg('rsp')))",
        "    if slot>=2:assert gen in proofs,'child witness before fence'\n"
        "    release=dict(slot=slot,gen=gen,frames=frames,freed=[],before=free(),ret=q(reg('rsp')))")
    code=helpers.once(code,"            starts[r['gen']]['live']=False",
        "            assert all(not any(raw) for raw in file_pages(r['frames'])),'freed bytes'\n"
        "            starts[r['gen']]['live']=False")
    return code+'\n'+helpers.FILE_RAM_BATCH+'\n'+IMAGE_CONTEXT+'\n'+EXTRA


IMAGE_CONTEXT=r'''
def image_context(slot,gen,record):
    assert type(slot) is int and 0<=slot<8 and type(gen) is int and 0<gen<0x80000000
    assert len(record)==266336 and record[:16]==b'RNPGv2\0\0'+struct.pack('<II',2,266336)
    assert struct.unpack('<4I',mem(S['process_run_plan'],16))==(4,272,8,0)
    image=q(S['process_run_plan']+16+slot*32+24)
    assert image==(slot+3 if slot<2 else slot+5),'private image owner'
    assert d(S['process_run_generations']+slot*4)==gen,'image generation'
    assert q(S['family_records']+slot*64)==(gen<<32)|slot,'image family generation'
    assert q(S['family_records']+slot*64+40)==(1 if slot<2 else 2),'image family phase'
    selected=mem(S['elf_image_selector'],1)[0]
    assert selected<13,'selected image range'
    # The current loader window may belong to another ready task. Its stored
    # copy is stale while selected; every other image lives in its store slot.
    address=S['elf_context_window'] if selected==image else S['elf_context_store']+image*592
    context=mem(address,592)
    assert len(context)==592 and context[512:576]==record[24:88],'image context flags'
    assert context[580:584]==bytes((1,1,0,1)),'image context state'
    assert struct.unpack_from('<Q',context,584)[0]==struct.unpack_from('<Q',record,16)[0],'image context entry'
    frames=struct.unpack_from('<64Q',context)
    for frame,flags in zip(frames,record[24:88]):
        assert flags in (0,4,5,6) and (frame==0 if flags==0 else 0x100000000<=frame<0x400000000 and not frame&4095),'image context frame'
    allocated=[frame for frame in frames if frame]
    assert len(allocated)==len(set(allocated)),'image context alias'
    return image,frames
'''


START=r'''
def start():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    if gen in starts:return
    assert slot<8 and t[0]==2 and gen and not reg('eflags')&512
    record=mem(S['boot_program_catalog']+slot*266336,266336) if slot<2 else copies[gen]
    assert t[68]==struct.unpack_from('<Q',record,16)[0] and 0x410000<=t[68]<0x440000
    assert 0x40f000<=t[69]<0x410000 and not t[69]&15
    owned=[];image=[];leaves=file_leaves(t)
    selector,staged=image_context(slot,gen,record)
    for page in range(64):
        pf=6 if page==8 else record[24+page];e=leaves[page]
        if not pf:assert not e;continue
        frame=e&MASK;flags=5|(2 if pf==6 else 0)|(0 if pf==5 else NX)
        assert frame>=0x100000000 and e&~0x60==frame|flags
        if pf==6:
            assert frame==(t[3] if page==8 else t[4+page]);owned.append(frame)
        else:assert t[4+page]==0 and frame==staged[page]
        image.append((page,frame))
    for (page,frame),actual in zip(image,file_pages([f for p,f in image])):
        if page==15:continue
        assert actual==(bytes(4096) if page==8 else record[96+page*4096:96+(page+1)*4096])
    assert len(owned)==len(set(owned)) and not t[12]
    for entry in starts.values():
        if entry['live']:assert not set(f for p,f in image)&set(entry['mapped'])
    argc=2 if slot<2 else 6
    values=struct.unpack('<'+'Q'*(argc+7),user(t,t[69],(argc+7)*8))
    assert values[0]==argc and values[argc+1:]==(0,0,0x52534901,0,0,0)
    args=[user(t,p,128).split(b'\0')[0] for p in values[1:argc+1]]
    parent=0;index=-1;role=slot
    if slot<2:assert args==[('program%d.prg'%slot).encode(),str(slot).encode()]
    else:
        assert args[0]==b'pool-child' and len(args[1])==len(args[2])==8
        assert all(c in b'0123456789abcdef' for a in args[1:3] for c in a)
        assert int(args[1],16)>0 and args[3] in (b'0',b'1',b'2') and args[5] in (b'0',b'1')
        parent=int(args[2],16);index=int(args[3]);role=int(args[5])
        assert task(role)[1]==parent and parent in starts and starts[parent]['live']
        assert q(S['family_records']+slot*64+8)==(parent<<32)|role
        expected=CASE if role==0 and index==0 and CASE in (2,3) else 0
        assert args[4]==str(expected).encode()
    stack=user(t,0x408000,32768);assert not any(stack[:t[69]-0x408000])
    starts[gen]=dict(slot=slot,owned=owned,mapped=[f for p,f in image],live=True,record=record,parent=parent,index=index,role=role)
    emit('start',slot=slot,gen=gen,parent=parent,index=index,role=role,image=selector,
         pages=len(image),private=len(owned),live=sum(e['live'] for e in starts.values()))
    if slot<2:
        address=CONFIG['root_data'][slot]
        raw=user(t,address,72);assert raw==struct.pack('<9Q',0x31544f4f524c4f50,0,0,0,0,0,0,0,0)
        leaf=leaves[(address+8-0x400000)//4096]
        assert leaf&~MASK&~0x60==NX|7 and (address+8)&4095<=4088
        target=DM+(leaf&MASK)+((address+8)&4095)
        assert mem(target,8)==bytes(8)
        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))
        assert mem(target,8)==struct.pack('<Q',CASE)
        emit('mode',slot=slot,gen=gen,address=address+8,physical=(leaf&MASK)+((address+8)&4095),before=0,value=CASE)
'''
COPY=r'''
def copy():
    t=struct.unpack('<128Q',mem(reg('r12'),1024));gen=t[1]
    assert gen not in copies and len(copies)<14
    record=mem(S['elf_import_record'],266336)
    assert record==CONFIG['child_record'] and record[:16]==b'RNPGv2\0\0'+struct.pack('<II',2,266336)
    copies[gen]=record
    emit('copy',gen=gen,bytes=len(record),sha=hashlib.sha256(record).hexdigest())
'''
SYSCALL=r'''
def syscall():
    if mode()!=8:return
    for gen,entry in list(starts.items()):
        if not entry['live'] or entry['slot']<2 or gen in proofs:continue
        parent=task(entry['role'])
        if parent[1]!=entry['parent'] or parent[0] not in (1,2,6):continue
        root=struct.unpack('<9Q',user(parent,CONFIG['root_data'][entry['role']],72))
        if root[3]<2:continue
        t=task(entry['slot']);w=struct.unpack('<8Q',user(t,CONFIG['child_data'],64))
        if w[5]==0:continue
        assert w[:5]==(0x31444c48434c4f50,gen,entry['parent'],entry['index'],entry['role']) and w[5] in (1,2,3)
        assert w[6]>=0x100000000
        private=user(t,CONFIG['child_bss'],4096);heap=user(t,w[6],8192)
        a=bytes((i^gen)&255 for i in range(4096))
        b=bytes((i+gen)&255 for i in range(4096))+bytes((i^entry['parent'])&255 for i in range(4096))
        assert private==a and heap==b and w[7]==sum(a)+sum(b)
        assert user(parent,created_sources[gen],266336)==bytes([0xa5])*266336
        leaves=file_leaves(t);pages=[p for p in range(64) if copies[gen][24+p] in (4,5)]
        for p,raw in zip(pages,file_pages([leaves[p]&MASK for p in pages])):
            assert raw==copies[gen][96+p*4096:96+(p+1)*4096]
        assert q(CS['native_heap_state']+232+entry['slot']*99368)==gen
        proofs.add(gen);emit('witness',gen=gen,parent=entry['parent'],index=entry['index'],role=entry['role'],heap=8192,private=4096,immutable=1,checksum=w[7])
'''
FAULT=r'''
def fault():
    assert mode()==8 and CASE in (2,5)
    syscall()
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1];entry=starts[gen]
    f=struct.unpack('<22Q',mem(reg('rdi'),176))
    assert f[15]==6 and f[18]==0x33
    assert slot==0 if CASE==5 else entry['role']==0 and entry['index']==0 and gen in proofs
    emit('fault',gen=gen,slot=slot,vector=f[15])
'''
CANCEL=r'''
def cancel():
    slot=reg('rdi');t=task(slot);gen=t[1];entry=starts[gen]
    assert CASE in (4,5) and slot>=2 and entry['role']==0 and t[0] in (1,6)
    assert CASE==5 or entry['index']==0
    assert gen in proofs and d(S['family_reasons']+slot*4)==(3 if CASE==5 else 2)
    emit('cancel',gen=gen,slot=slot,state=t[0],reason=3 if CASE==5 else 2)
'''
CREATE_BEGIN=r'''
def create_begin():
    global created,source_pointer,allocation_count,allocation_before,allocation_owner
    assert created is None
    source_pointer=q(S['family_request']+24)
    slot=d(S['scheduler_current_slot']);assert slot<2
    created=True;allocation_count=0;allocation_before=free();allocation_owner=q(S['family_records']+slot*64)
    allocator.enabled=True
'''
CREATE_END=r'''
def create_end():
    global created
    allocator.enabled=False;assert created
    if reg('rax')==0xfffffffffffffff4:
        assert OOM is not None and allocation_count==OOM and free()==allocation_before
        assert allocation_owner&0xffffffff==0
        emit('rollback',owner=allocation_owner,acquired=allocation_count,free=free(),before=allocation_before)
    else:
        assert 0<reg('rax')<1<<63
        gen=reg('rax')>>32;assert gen in copies
        created_sources[gen]=source_pointer
        emit('create',gen=gen,owner=allocation_owner,slot=reg('rax')&0xffffffff,acquired=allocation_count)
    created=None
'''
FINISH=r'''
def finish():
    global runs
    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512
    for name,n in [('scheduler_tasks',8192),('scheduler_fp_states',4096),('scheduler_table_frames',256),
      ('scheduler_cpu_budgets',256),('scheduler_syscall_profiles',128),('scheduler_syscall_context',16),
      ('syscall_rax',120),('process_run_plan',272),('process_run_generations',32),('process_run_receipt',32),
      ('scheduler_runqueue_entries',64),('scheduler_deadline_entries',128),('scheduler_runqueue_membership',8),
      ('scheduler_deadline_membership',8),('process_heap_pending_mask',8),('process_heap_receipts',256),('elf_import_record',266336)]:
        assert not any(mem(S[name],n)),name
    assert not any(mem(S['family_begin'],S['family_end']-S['family_begin']))
    for a in [S['elf_context_window']]+[S['elf_context_store']+i*592 for i in range(13)]:
        raw=mem(a,592);assert not any(raw[:576]) and not any(raw[580:])
    for slot in range(8):
        gen=max(g for g,e in starts.items() if e['slot']==slot)
        assert d(S['scheduler_identity_retired']+slot*4)==gen
        hp=CS['native_heap_state']+232+slot*99368
        assert struct.unpack('<8Q',mem(hp,64))==(0,gen,0,0,0,0x20000000,0,0)
        assert not any(mem(hp+552,5120)) and not any(mem(hp+32808,12288))
        assert not any(mem(CS['clients']+slot*108,108)) and not any(mem(CS['pending']+slot*2144,2144))
        assert d(CS['retired']+slot*4)==gen
        value,inverse,seal=struct.unpack('<3Q',mem(S['process_ipc_completions']+slot*24,24))
        assert value==gen<<32 and inverse==value^0xffffffffffffffff
        assert seal==(((value<<17)|(value>>47))&0xffffffffffffffff)^0x936da17cb852e40f
    per=9 if CASE==6 else 8
    assert free()==d(S['scheduler_initial_free']) and d(S['scheduler_reap_count'])==per
    assert q(S['timer_runtime_ticks'])==q(S['timer_runtime_eois'])==q(S['scheduler_last_tick'])
    assert len(starts)==runs*per and len(proofs)==runs*(per-2) and not any(v['live'] for v in starts.values())
    emit('finish',run=runs,free=free(),initial=d(S['scheduler_initial_free']),tasks=per,generation=d(S['process_run_generation']),zero=1)
    if runs==2:gdb.execute('detach');gdb.execute('quit')
'''
EXTRA=r'''
# OOM is armed only in a first root0 CREATE, never the unrelated root.
def allocation():
    global allocation_count
    if OOM is not None and not allocation_owner&0xffffffff and allocation_owner not in injected and allocation_count==OOM:
        ret=q(reg('rsp'));gdb.execute('set $rax=0');gdb.execute('set $rsp=$rsp+8');gdb.execute('set $rip='+hex(ret))
        injected.add(allocation_owner);allocator.enabled=False
        emit('oom',owner=allocation_owner,acquired=allocation_count)
    else:allocation_count+=1
allocator.fn=allocation

def receipt_capacity():
    if mode()!=8 or CASE!=6:return
    root=task(0)
    if root[0] not in (1,2,6):return
    w=struct.unpack('<9Q',user(root,CONFIG['root_data'][0],72))
    if w[3] not in (3,4):return
    key=(root[1],w[3])
    if key in capacity_seen:return
    records=[struct.unpack('<8Q',mem(S['family_records']+slot*64,64)) for slot in range(2,8)]
    assert all(record[5] in (2,4) for record in records)
    if w[3]==4:
        child=w[4]&0xffffffff;assert q(S['family_records']+child*64+40)==4 and task(child)[0]==0
    capacity_seen.add(key);emit('capacity',gen=root[1],phase=w[3],occupied=6,receipt=int(w[3]==4))
capacity_seen=set()
Hook('process_run_syscall64',receipt_capacity)
'''


def fixture_sections(raw):
    # PRGs are stripped ET_EXEC files. Keep the C payload's mandatory symbol
    # table admission unchanged; these section names only locate host witnesses.
    import build_x86_64_boot_programs as producer
    prepared=producer.prepare(raw,[],True)
    def need(value):
        if not value:raise ValueError('pool fixture section binding')
    off=struct.unpack_from('<Q',raw,40)[0]
    size,count,index=struct.unpack_from('<3H',raw,58)
    need(size==64 and 1<count<=128 and 0<index<count and 64<=off<=len(raw)-64*count)
    rows=[struct.unpack_from('<II4QII2Q',raw,off+i*64) for i in range(count)]
    need(rows[0]==(0,)*10)
    names=rows[index];need(names[1]==3 and 0<names[5]<=4096 and names[4]<=len(raw)-names[5])
    strings=raw[names[4]:names[4]+names[5]];need(strings[:1]==b'\0')
    sections={}
    for row in rows[1:]:
        n,typ,flags,address,offset,extent,_,_,align,_=row
        need(0<n<len(strings))
        end=strings.find(b'\0',n);need(n<end<=n+128)
        name=strings[n:end].decode('ascii');need(name not in sections)
        if name in ('.data','.bss'):
            need(typ==(1 if name=='.data' else 8) and flags==3 and
                 0x410000<=address<0x440000 and 0<extent<=0x440000-address and
                 align and not align&(align-1) and not address&(align-1))
            first=(address-0x400000)//4096;last=(address+extent-1-0x400000)//4096
            need(all(p==6 for p in prepared[24+first:25+last]))
            expected=bytes(extent)
            if typ==1:
                need(offset<=len(raw)-extent);expected=raw[offset:offset+extent]
            start=96+address-0x400000;need(prepared[start:start+extent]==expected)
        sections[name]=dict(address=address,size=extent)
    need('.data' in sections)
    return sections


def image_config(image):
    inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=payload.validate(inner)
    if core['layout_version']!=5:raise ValueError('pool layout5 required')
    payload.verify_outer(inner,payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    if len(catalog)!=4*SIZE:raise ValueError('pool catalog size')
    # Exactly one successful producer attempt belongs to a fresh candidate build.
    attempts=list(image.parent.glob('programs-*'))
    attempts=[p for p in attempts if p.is_dir() and (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(attempts)!=1:raise ValueError('pool producer attempt identity')
    programs=[fixture_sections((attempts[0]/f'program{n}.prg').read_bytes()) for n in range(3)]
    child=catalog[2*SIZE:3*SIZE-4096]+bytes(4096)
    addresses=dict(root_data=[p['.data']['address'] for p in programs[:2]],
        child_data=programs[2]['.data']['address'],child_bss=programs[2]['.bss']['address'])
    if programs[2]['.bss']['size']!=4096:raise ValueError('pool child private bytes')
    return dict(s=transport.symbols(image),cs={n:v['value'] for n,v in core['symbols'].items()},child_record=child,**addresses)


def observer(config,folder,case,oom):
    settings=dict(config,case=case,oom=oom)
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+
        '\n'+observer_body()+'\nend\ncontinue\n')


def _validate(serial,trace,case,oom,count,child_sha):
    if type(case) is not int or case not in range(10) or (oom is not None)!=(case>=7):raise ValueError('pool case')
    expected_oom={7:0,8:count//2,9:count-1}.get(case)
    if oom!=expected_oom:raise ValueError('pool OOM position')
    per=9 if case==6 else 8
    common=[m for m in transport.REQUIRED_MARKERS if 'SHELL' not in m]+[wide.process.SUCCESS]
    if any(m in serial for m in transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('pool kernel/observer failure')
    if any(serial.count(m)!=1 for m in common) or [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):raise ValueError('pool progress')
    receipts=list(wide.process.REAP.finditer(serial));ends=list(re.finditer(wide.process.DONE,serial))
    if len(receipts)!=2*per or serial.count('PROCESS_REAP_OK')!=2*per or len(ends)!=2:raise ValueError('pool receipt count')
    events=[json.loads(line[10:]) for line in trace.splitlines() if line.startswith('TASK_POOL ')]
    allowed={'boot','start','mode','copy','create','witness','release','finish','fault','cancel','oom','rollback','capacity'}
    if any(e.get('kind') not in allowed for e in events):raise ValueError('pool unknown event')
    def get(kind):return [e for e in events if e['kind']==kind]
    if get('boot')!=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]:raise ValueError('pool boot')
    starts=get('start');bygen={e['gen']:e for e in starts}
    if len(starts)!=2*per or len(bygen)!=2*per or sorted(bygen)!=list(range(1,2*per+1)):raise ValueError('pool unique lifetimes')
    children=[e['gen'] for e in starts if e['slot']>=2]
    roots=[e['gen'] for e in starts if e['slot']<2]
    if roots!=[1,2,per+1,per+2]:raise ValueError('pool roots')
    rows=[]
    for run in range(2):
        group=[e for e in starts if run*per<e['gen']<=(run+1)*per]
        if set(e['slot'] for e in group)!=set(range(8)) or max(e['live'] for e in group)!=8:raise ValueError('pool simultaneous eight')
        for role in (0,1):
            indices=sorted(e['index'] for e in group if e['slot']>=2 and e['role']==role)
            if indices!=([0,0,1,2] if case==6 and role==0 else [0,1,2]):raise ValueError('pool six owned children')
        for entry in group:
            s,g=entry['slot'],entry['gen']
            if not 0<s+1<=8 or not 1<=entry['private']<=entry['pages']<=65:raise ValueError('pool mapped capacity')
            if s<2:
                if (g,entry['parent'],entry['role'],entry['index'],entry['image'])!=(run*per+s+1,0,s,-1,s+3):raise ValueError('pool root mapping')
            elif (entry['parent'],entry['image'])!=(run*per+entry['role']+1,s+5):raise ValueError('pool child ownership')
        seen=set()
        for match in receipts[run*per:(run+1)*per]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(match[1]));entry=bygen[gen]
            if gen in seen or not run*per<gen<=(run+1)*per or slot!=entry['slot']:raise ValueError('pool receipt identity')
            seen.add(gen);bad=entry['role']==0 and entry['index']==0 and case in (2,3,4)
            expected=90+slot if slot<2 else 80+entry['index']+3*entry['role'];terminal=4
            if case==5 and entry['role']==0:expected=134 if slot==0 else 0;terminal=3
            if bad:expected={2:134,3:256,4:0}[case];terminal=3
            if (status,state)!=(expected,terminal) or ticks>32 or bad and case==3 and ticks!=32 or not 0x410000<=rip<0x440000:raise ValueError('pool terminal outcome')
            if not (ends[run-1].end() if run else -1)<match.start()<match.end()<=ends[run].start():raise ValueError('pool receipt order')
            rows.append((slot,gen))
    if [(e['slot'],e['gen']) for e in get('release')]!=rows:raise ValueError('pool release ledger')
    for e in get('release'):
        if e['fenced']!=1 or not 0<e['frames']<=69 or not 0<e['before']<e['after']==e['before']+e['frames']<=4194304:raise ValueError('pool frame balance')
    for kind in ('copy','create','witness'):
        es=get(kind)
        if len(es)!=len(children) or {e['gen'] for e in es}!=set(children):raise ValueError('pool '+kind+' lifetimes')
        for e in es:
            child=bygen[e['gen']]
            if kind=='copy' and (e['bytes']!=SIZE or e['sha']!=child_sha):raise ValueError('pool prepared bytes')
            if kind=='create' and (e['acquired']!=count or e['slot']!=child['slot'] or e['owner']!=(child['parent']<<32)|child['role']):raise ValueError('pool acquisition owner')
            if kind=='witness':
                checksum=sum(((i^e['gen'])&255)+((i+e['gen'])&255)+((i^child['parent'])&255) for i in range(4096))
                if (e['parent'],e['role'],e['index'],e['heap'],e['private'],e['immutable'],e['checksum'])!=(child['parent'],child['role'],child['index'],8192,4096,1,checksum):raise ValueError('pool isolated bytes')
    if [e['gen'] for e in get('mode')]!=roots:raise ValueError('pool exact mode writes')
    for e in get('mode'):
        if (e['slot'],e['before'],e['value'])!=(bygen[e['gen']]['slot'],0,case) or not 0x410000<=e['address']<0x440000 or e['address']&7 or not 0x100000000<=e['physical']<0x280000000:raise ValueError('pool fixture authority')
    fault_gens=[g for g,e in bygen.items() if e['role']==0 and (case==5 and e['slot']==0 or case==2 and e['index']==0)]
    if [e['gen'] for e in get('fault')]!=fault_gens or any(e['vector']!=6 or e['slot']!=bygen[e['gen']]['slot'] for e in get('fault')):raise ValueError('pool exact faults')
    cancel_gens=[g for g,e in bygen.items() if e['slot']>=2 and e['role']==0 and (case==5 or case==4 and e['index']==0)]
    if len(get('cancel'))!=len(cancel_gens) or {e['gen'] for e in get('cancel')}!=set(cancel_gens):raise ValueError('pool exact cancellation')
    if any(e['reason']!=(3 if case==5 else 2) or e['state'] not in (1,6) or e['slot']!=bygen[e['gen']]['slot'] for e in get('cancel')):raise ValueError('pool cancellation reason')
    for kind in ('oom','rollback'):
        es=get(kind)
        if [(e['owner'],e['acquired']) for e in es]!=([(1<<32,oom),((per+1)<<32,oom)] if oom is not None else []):raise ValueError('pool OOM scope')
        if kind=='rollback' and any(not 0<e['free']==e['before']<=4194304 for e in es):raise ValueError('pool OOM rollback')
    expected_capacity=[dict(kind='capacity',gen=g,phase=phase,occupied=6,receipt=int(phase==4)) for g in (1,per+1) for phase in (3,4)] if case==6 else []
    if get('capacity')!=expected_capacity:raise ValueError('pool retained receipt capacity')
    if len(get('finish'))!=2:raise ValueError('pool final count')
    for run,e in enumerate(get('finish'),1):
        if (e['run'],e['tasks'],e['generation'],e['zero'])!=(run,per,run*per,1) or not 0<e['free']==e['initial']<=4194304:raise ValueError('pool final zero/balance')
    def at(kind,gen):return next(i for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen)
    for gen,e in bygen.items():
        first,last=at('start',gen),at('release',gen)
        if first>=last:raise ValueError('pool lifecycle order')
        if gen in children and not at('copy',gen)<at('create',gen)<first<at('witness',gen)<last:raise ValueError('pool publication order')
        if gen in roots and not first<at('mode',gen)<last:raise ValueError('pool mode lifecycle')
        if gen in cancel_gens and not at('witness',gen)<at('cancel',gen)<last:raise ValueError('pool cancel fence order')
        if gen in fault_gens and not first<at('fault',gen)<last:raise ValueError('pool fault fence order')
        run=(gen-1)//per
        if not last<events.index(get('finish')[run]):raise ValueError('pool finish before release')
    return rows


def validate(*args):
    try:return _validate(*args)
    except (KeyError,TypeError,StopIteration,struct.error,IndexError) as error:raise ValueError('malformed pool evidence: '+str(error)) from error


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();image=args.image.resolve();base=args.evidence.resolve()
    if not image.is_relative_to(ROOT/'build') or base!=(ROOT/'build/codex-agent/r83an-task-pool/guests').resolve():parser.error('pool evidence scope')
    import verify_x86_64_task_pool as verify
    binding=verify.admit_runtime(image)
    previous=sorted(base.glob('attempt-*/summary.json'))
    if len(previous)>=3:raise ValueError('pool candidate matrix budget exhausted')
    for path in previous:
        old=json.loads(path.read_text())
        if old['candidate']==binding['candidate']:raise ValueError('pool unchanged candidate retry prohibited')
        if not old.get('closed'):raise ValueError('pool unfinished prior matrix')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    result=dict(passed=False,closed=False,candidate=binding['candidate'],image_sha256=digest(image),cases=[])
    (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    begin=time.monotonic();spent=0
    try:
        config=image_config(image);count=wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
        result.update(allocations=count,child_sha256=sha)
        for case,ram in CASES:
            if digest(image)!=result['image_sha256']:raise ValueError('pool image changed')
            oom={7:0,8:count//2,9:count-1}.get(case);out=folder/f'guest-{case}-{ram}';out.mkdir()
            row=dict(case=case,ram=ram,oom=oom,passed=False);result['cases'].append(row);started=time.monotonic()
            try:
                serial,trace=transport.capture(image,out,observer(config,out,case,oom),ram,binary_memory='equivalence',diagnostic_metrics=True)
                row['tasks']=len(validate(serial,trace,case,oom,count,sha));row['passed']=True
            finally:
                elapsed=time.monotonic()-started;spent+=elapsed;row['elapsed']=round(elapsed,6)
            if elapsed>20 or spent>200:raise ValueError('pool immutable guest deadline')
            print(f'TASK_POOL_GUEST_OK case={case} ram={ram} tasks={row["tasks"]} elapsed={elapsed:.3f}',flush=True)
        result['passed']=True;return 0
    except (ValueError,RuntimeError,OSError,KeyError) as error:
        result['error']=str(error);print('TASK_POOL_FAIL '+str(error),flush=True);return 1
    finally:
        result.update(closed=True,elapsed=round(time.monotonic()-begin,6),guest_elapsed=round(spent,6))
        (folder/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('TASK_POOL_EVIDENCE '+str(folder),flush=True)


if __name__=='__main__':raise SystemExit(main())
