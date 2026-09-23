"""Large-image guest observer; retained raw reads for independent qualification."""
from pathlib import Path
import argparse, hashlib, json, re, struct, subprocess, time, uuid
import build_x86_64_c_payload as payload
import build_x86_64_boot_programs as producer
import run_qemu_x86_64_boot_programs as transport
import run_qemu_x86_64_process_run as process
ROOT=Path(__file__).resolve().parents[1]
SIZE=1052960

def allocations(record):
    if len(record)!=SIZE or record[:16]!=b'RNPGv3\0\0'+struct.pack('<II',3,SIZE):
        raise ValueError('wide record identity')
    flags=record[24:280]
    if any(f not in (0,4,5,6) for f in flags) or flags[7:16]!=bytes([0,0]+[6]*7):
        raise ValueError('wide record rights')
    return sum(bool(f) for f in flags)+sum(f==6 for f in flags)+5

def observer(s,c,folder,case,oom,selection):
    config=dict(folder=str(folder),selection=selection,s=s,cs={n:v['value'] for n,v in c['symbols'].items()},case=case,oom=oom)
    (folder/'config.json').write_text(json.dumps(config,sort_keys=True),encoding='ascii')
    return ('set logging file '+(folder/'frame-trace.log').as_posix()+'\nset logging overwrite on\n'
            'set logging enabled on\npython\nCONFIG='+repr(config)+'\n'+OBSERVER+'\nend\ncontinue\n')

# This is debugger-side Python, never linked into the guest.
OBSERVER=r'''
import gdb,struct,hashlib,json
S=CONFIG['s'];CS=CONFIG['cs'];CASE=CONFIG['case'];OOM=CONFIG['oom']
DM=0xffff800000000000;HIGH=0xffffffff80000000;MASK=0x3fffff000;NX=1<<63
starts={};copies={};proofs=set();runs=0;release=None;created=None;injected=set();callbacks=0
raw_file=open(CONFIG['folder']+'/reads.bin','xb',buffering=0)
read_log=open(CONFIG['folder']+'/reads.jsonl','x',buffering=1)
def reg(n):
    value=int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
    read_log.write(json.dumps(dict(register=n,value=value))+'\n');return value
def mem(a,n):
    assert 0<=n<=1056768 and raw_file.tell()+n<=268435456
    value=bytes(gdb.selected_inferior().read_memory(a&0xffffffffffffffff,n))
    at=raw_file.tell();raw_file.write(value)
    read_log.write(json.dumps(dict(address=a&0xffffffffffffffff,offset=at,bytes=n))+'\n');return value
def q(a):return struct.unpack('<Q',mem(a,8))[0]
def d(a):return struct.unpack('<I',mem(a,4))[0]
def mode():return mem(S['scheduler_mode'],1)[0]
def task(slot):return struct.unpack('<512Q',mem(S['scheduler_tasks']+slot*4096,4096))
def free():return d(S['free_frame_count'])
def emit(kind,**fields):
    row=dict(kind=kind,**fields);read_log.write(json.dumps(dict(event=row))+'\n')
    gdb.write('WIDE '+json.dumps(row,sort_keys=True)+'\n')
def walk(root,va,direct=DM):
    for shift in (39,30,21):
        e=q(direct+root+((va>>shift)&511)*8)
        if not e&1:return 0
        assert not e&128
        root=e&MASK
    return q(direct+root+((va>>12)&511)*8)
def user(t,va,n):
    out=bytearray()
    while n:
        e=walk(t[2],va);assert e&5==5
        count=min(n,4096-(va&4095));out+=mem(DM+(e&MASK)+(va&4095),count)
        va+=count;n-=count
    return bytes(out)
class Hook(gdb.Breakpoint):
    def __init__(self,name,fn):
        super().__init__('*'+hex(S[name]),internal=True);self.fn=fn
    def stop(self):
        global callbacks
        try:
            callbacks+=1;assert callbacks<=4096
            read_log.write(json.dumps(dict(begin=self.fn.__name__))+'\n')
            self.fn()
            read_log.write(json.dumps(dict(end=self.fn.__name__))+'\n')
        except Exception as error:
            import traceback
            gdb.write(traceback.format_exc())
            emit('OBSERVER_FAIL',where=self.fn.__name__,error=repr(error))
            gdb.execute('quit 71')
        return False
def poison():
    gdb.selected_inferior().write_memory(0xb05000,bytes([0xa5])*1056768)
    emit('poison',bytes=1056768)
boot_entry=S['x86_64_bootstrap_start'];S['x86_64_bootstrap_start']=boot_entry-HIGH
Hook('x86_64_bootstrap_start',poison);S['x86_64_bootstrap_start']=boot_entry
boot_seen=False
def boot():
    global boot_seen
    if boot_seen:return
    boot_seen=True
    assert not reg('eflags')&512 and reg('cr0')&(1<<16),'boot IF/WP'
    assert not any(mem(HIGH+0xb05000,1056768)),'boot scratch zero'
    bitmap=mem(S['usable_bitmap'],(0xc07000//4096+7)//8)
    assert not int.from_bytes(bitmap,'little')&((1<<(0xc07000//4096))-1),'boot reserved frames'
    for addr,end,flags in ((0xa00000,0xb05000,1),(0xb05000,0xc07000,3)):
        for p in range(addr,end,4096):
            leaf=q(S['high_page_table']+(p>>12)*8)
            assert leaf&~0x60==p|flags|NX,('boot leaf',p,leaf)
            assert not walk(reg('cr3'),DM+p,HIGH),('boot direct alias',p)
    emit('boot',catalog=261,scratch=258,reserved=3079,zero=1,aliases=0)
Hook('x86_64_c_core_handoff64',boot)
def start():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    if gen in starts:return
    assert slot<4 and t[0]==2 and gen and not reg('eflags')&512
    record=mem(S['boot_program_catalog']+slot*266336,266336) if slot<2 else copies[gen]
    slots,header=(64,96) if slot<2 else (256,288)
    assert t[260]==struct.unpack_from('<Q',record,16)[0] and 0x410000<=t[260]<0x500000
    assert 0x40f000<=t[261]<0x410000 and not t[261]&15
    owned=[]
    for page in range(256):
        pf=6 if page==8 else record[24+page] if page<slots else 0;e=walk(t[2],0x400000+page*4096)
        if not pf:assert not e;continue
        frame=e&MASK;flags=5|(2 if pf==6 else 0)|(0 if pf==5 else NX)
        assert frame>=0x100000000 and e&~0x60==frame|flags
        if pf==6:
            assert frame==(t[3] if page==8 else t[4+page]);owned.append(frame)
        else:assert t[4+page]==0
        actual=mem(DM+frame,4096)
        if page==15:continue # Startup frame independently verified below.
        assert actual==(bytes(4096) if page==8 else record[header+page*4096:header+(page+1)*4096])
    assert len(owned)==len(set(owned)) and not t[12]
    for other,entry in starts.items():
        if entry['live']:assert not set(owned)&set(entry['owned'])
    argc=2 if slot<2 else 3
    values=struct.unpack('<'+'Q'*(argc+7),user(t,t[261],(argc+7)*8));assert values[0]==argc and values[argc+1:]==(0,0,0x52534901,0,0,0)
    args=[user(t,p,128).split(b'\0')[0] for p in values[1:argc+1]]
    expected=[('program%d.prg'%slot).encode(),str(slot).encode()] if slot<2 else [b'wide-child' if gen in (3,7) else b'wide-new',str(CASE if CASE<6 and (gen-1)%4==2 else 0).encode()]
    assert args[:2]==expected
    if slot==2:assert len(args[2])==8 and all(c in b'0123456789abcdef' for c in args[2]) and int(args[2],16)>0
    # No uninitialized data outside the exact canonical startup image.
    stack=user(t,0x408000,32768);assert not any(stack[:t[261]-0x408000])
    if slot==0:
        magic=struct.pack('<QQ',0x31474d494752414c,0)
        base=CONFIG['selection'];offset=base-0x400000
        assert 0<=offset<slots*4096-16 and not base&7
        assert record[24+offset//4096]==6 and record[header+offset:header+offset+16]==magic
        va=base+8;leaf=walk(t[2],va)
        target=DM+(leaf&MASK)+(va&4095)
        assert mem(target,8)==bytes(8)
        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))
        assert mem(target,8)==struct.pack('<Q',CASE)
    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)
    emit('start',slot=slot,gen=gen,pages=sum(bool(f) for f in record[24:24+slots])+1,private=len(owned))
Hook('scheduler_enter_task64.state_published',start)
def copy():
    t=struct.unpack('<512Q',mem(reg('r12'),4096));gen=t[1]
    assert gen not in copies and len(copies)<4
    record=mem(S['elf_import_record'],1052960)
    assert record[:16]==b'RNPGv3\0\0'+struct.pack('<II',3,1052960)
    copies[gen]=record
    emit('copy',gen=gen,bytes=len(record),sha=hashlib.sha256(record).hexdigest())
Hook('family_create64.stack_ready',copy)
def syscall():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot'])
    if slot!=2:return
    t=task(slot);gen=t[1]
    if gen in proofs:return
    record=copies[gen]
    # Find the exact witness magic in the immutable initialized RW template.
    hits=[288+p*4096 for p in range(16,256) if record[24+p]==6 and record[288+p*4096:296+p*4096]==struct.pack('<Q',0x31474d494752414c)]
    assert len(hits)==1
    addr=0x400000+hits[0]-288
    magic,owner,stack,n,checksum,case=struct.unpack('<6Q',user(t,addr,48))
    if not owner or not n:return
    assert owner and n==12288 and 0x408000<=stack and stack+n<=0x410000
    assert case==(CASE if CASE<6 and (gen-1)%4==2 else 0)
    expected=bytes(i^0x6a for i in range(256))*48
    assert user(t,stack,n)==expected and checksum==sum(expected)
    # The explicit IPC token admits exercise only after parent source mutation.
    parent=task(0);ptr=created_sources[gen]
    assert user(parent,ptr,1052960)==bytes([0x5a])*1052960
    for p in range(256):
        if record[24+p] in (4,5):assert user(t,0x400000+p*4096,4096)==record[288+p*4096:288+(p+1)*4096]
    assert user(t,0x480000,4096)==bytes(i^0x31 for i in range(256))*16
    assert user(t,0x4fe000,4096)==bytes(i^0x93 for i in range(256))*16
    proofs.add(gen);emit('stack',gen=gen,bytes=n,checksum=checksum,immutable=1,case=case)
Hook('process_run_syscall64',syscall)
def fault():
    assert mode()==8 and CASE in (1,2,3)
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    f=struct.unpack('<22Q',mem(reg('rdi'),176));address=reg('cr2')
    assert slot==2 and gen in (3,7) and gen in proofs and f[15]==14 and f[18]==0x33
    assert f[16]=={1:6,2:21,3:7}[CASE]
    assert address==0x407fff if CASE==1 else 0x408000<=address<0x410000 if CASE==2 else address==0x410000
    emit('fault',gen=gen,vector=f[15],error=f[16],address=address)
Hook('process_run_exception64',fault)
def cancel():
    slot=reg('rdi');t=task(slot)
    assert CASE==5 and slot==2 and t[1] in (3,7) and t[0] in (1,6)
    assert t[1] in proofs
    emit('cancel',gen=t[1],state=t[0])
Hook('family_cancel_one64',cancel)
created_sources={};source_pointer=0;allocation_count=0;allocation_before=0;allocation_owner=0
def create_begin():
    global created,source_pointer,allocation_count,allocation_before,allocation_owner
    assert created is None
    source_pointer=q(S['family_request']+24)
    created=True;allocation_count=0;allocation_before=free();allocation_owner=q(S['family_records'])
    allocator.enabled=True
def allocation():
    global allocation_count
    if OOM is not None and allocation_owner not in injected and allocation_count==OOM:
        ret=q(reg('rsp'));gdb.execute('set $rax=0');gdb.execute('set $rsp=$rsp+8');gdb.execute('set $rip='+hex(ret))
        injected.add(allocation_owner);allocator.enabled=False
        emit('oom',owner=allocation_owner,acquired=allocation_count)
    else:allocation_count+=1
allocator=Hook('physical_frame_alloc64',allocation);allocator.enabled=False
Hook('family_create64.found',create_begin)
def create_end():
    global created
    allocator.enabled=False;assert created
    if reg('rax')==0xfffffffffffffff4:
        assert OOM is not None and allocation_count==OOM and free()==allocation_before
        emit('rollback',owner=allocation_owner,acquired=allocation_count,free=free(),before=allocation_before)
    else:
        assert reg('rax')>0 and reg('rax')<1<<63
        gen=reg('rax')>>32;assert gen in copies
        created_sources[gen]=source_pointer
        emit('create',gen=gen,acquired=allocation_count)
    created=None
Hook('family_create64.parent_result',create_end)
def release_begin():
    global release
    if mode()!=8:return
    assert release is None and not reg('eflags')&512
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    assert t[0] in (3,4) and starts[gen]['live']
    tables=list(struct.unpack('<4Q',mem(S['scheduler_table_frames']+slot*32,32)))
    frames=[f for f in list(t[4:260])+[t[3]]+list(reversed(tables)) if f]
    assert len(frames)==len(set(frames)) and frames[-1]==t[2]!=reg('cr3')
    assert not any(mem(S['family_profiles']+slot*32,32))
    assert not any(mem(S['scheduler_syscall_profiles']+slot*16,16))
    assert not mem(S['scheduler_runqueue_membership']+slot,1)[0] and not mem(S['scheduler_deadline_membership']+slot,1)[0]
    assert not any(mem(CS['clients']+slot*108,108)) and not any(mem(CS['pending']+slot*2144,2144))
    hp=CS['native_heap_state']+232+slot*99368
    assert struct.unpack('<8Q',mem(hp,64))==(0,gen,0,0,0,0x20000000,0,0)
    assert not any(mem(hp+552,5120)) and not any(mem(hp+32808,12288))
    release=dict(slot=slot,gen=gen,frames=frames,freed=[],before=free(),ret=q(reg('rsp')))
    ReleaseEnd(release['ret']);free_hook.enabled=True
def freed():
    assert release is not None
    release['freed'].append(reg('rdi'));assert len(release['freed'])<=261
free_hook=Hook('physical_frame_free64',freed);free_hook.enabled=False
class ReleaseEnd(gdb.Breakpoint):
    def __init__(self,addr):super().__init__('*'+hex(addr),internal=True,temporary=True)
    def stop(self):
        global release
        self.enabled=False
        try:
            read_log.write(json.dumps(dict(begin='release_end'))+'\n')
            free_hook.enabled=False;r=release;assert reg('rax')==1
            assert r['freed']==r['frames'] and free()==r['before']+len(r['frames'])
            t=task(r['slot']);assert not any(t[2:260])
            assert not any(mem(S['scheduler_table_frames']+r['slot']*32,32))
            assert not any(mem(S['scheduler_fp_states']+r['slot']*512,512))
            starts[r['gen']]['live']=False
            emit('release',slot=r['slot'],gen=r['gen'],frames=len(r['frames']),before=r['before'],after=free(),fenced=1)
            release=None
            read_log.write(json.dumps(dict(end='release_end'))+'\n')
        except Exception as error:
            import traceback
            gdb.write(traceback.format_exc())
            emit('OBSERVER_FAIL',where='release_end',error=repr(error));gdb.execute('quit 72')
        return False
Hook('scheduler_release_task_frames64',release_begin)
def finish():
    global runs
    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512
    for name,n in [('scheduler_tasks',16384),('scheduler_fp_states',2048),('scheduler_table_frames',128),
      ('scheduler_cpu_budgets',128),('scheduler_syscall_profiles',64),('scheduler_syscall_context',16),
      ('syscall_rax',120),('process_run_plan',144),('process_run_generations',16),('process_run_receipt',32),
      ('scheduler_runqueue_entries',32),('scheduler_deadline_entries',64),('scheduler_runqueue_membership',4),
      ('scheduler_deadline_membership',4),('process_heap_pending_mask',8),('elf_import_record',1052960)]:
        assert not any(mem(S[name],n)),name
    assert not any(mem(S['family_begin'],S['family_end']-S['family_begin']))
    for a in [S['elf_context_window']]+[S['elf_context_store']+i*2320 for i in range(9)]:
        r=mem(a,2320);assert not any(r[:2304]) and not any(r[2308:])
    assert free()==d(S['scheduler_initial_free']) and d(S['scheduler_reap_count'])==4
    assert q(S['timer_runtime_ticks'])==q(S['timer_runtime_eois'])==q(S['scheduler_last_tick'])
    assert len(starts)==runs*4 and len(proofs)==runs*2 and not any(v['live'] for v in starts.values())
    emit('finish',run=runs,free=free(),initial=d(S['scheduler_initial_free']),tasks=4,generation=d(S['process_run_generation']))
    if runs==2:
        read_log.write(json.dumps(dict(end='finish'))+'\n')
        gdb.execute('detach');gdb.execute('quit')
Hook('x86_64_c_process_run64.restore',finish)
def fail():
    emit('OBSERVER_FAIL',where='kernel',stage=mem(S['scheduler_failure_stage'],1)[0],mode=mode(),rip=reg('rip'),rax=reg('rax'))
    gdb.execute('info registers rax rbx rcx rdx rsi rdi r8 r9 r10 r11 r12 r13 r14 r15 rsp')
    gdb.execute('x/6gx $rsp');gdb.execute('quit 73')
Hook('scheduler_fail',fail)
'''

def validate(serial,trace,case,oom,count):
    if case not in range(7) or (oom is not None)!=(case==6):raise ValueError('wide case')
    common=[m for m in transport.REQUIRED_MARKERS if 'SHELL' not in m]+[process.SUCCESS]
    if any(m in serial for m in transport.FAILURES) or 'OBSERVER_FAIL' in trace:
        raise ValueError('wide kernel/observer failure')
    if any(serial.count(m)!=1 for m in common) or [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):
        raise ValueError('wide kernel progress')
    receipts=list(process.REAP.finditer(serial));ends=list(re.finditer(process.DONE,serial))
    if len(receipts)!=8 or serial.count('PROCESS_REAP_OK')!=8 or len(ends)!=2:raise ValueError('wide receipts')
    rows=[]
    for run in range(2):
        seen=set()
        for row in receipts[run*4:run*4+4]:
            slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(row[1]));n=gen-run*4
            expected=78 if n==1 else 77 if n==2 else (142 if case in (1,2,3) else 256 if case==4 else 0 if case==5 else 80) if n==3 else 80
            if n not in (1,2,3,4) or n in seen or slot!=(n-1 if n<3 else 2):raise ValueError('wide generation/slot')
            if status!=expected or state!=(3 if n==3 and case in range(1,6) else 4) or ticks>32:raise ValueError('wide outcome '+str((slot,gen,status,state,ticks)))
            if case==4 and n==3 and ticks!=32:raise ValueError('wide CPU bound')
            if not (0x410000<=rip<0x500000 or case==2 and n==3 and 0x408000<=rip<0x410000):raise ValueError('wide instruction range')
            if not (ends[run-1].end() if run else -1)<row.start()<row.end()<=ends[run].start():raise ValueError('wide receipt ordering')
            rows.append((slot,gen));seen.add(n)
    events=[json.loads(line[5:]) for line in trace.splitlines() if line.startswith('WIDE ')]
    def get(kind):return [e for e in events if e['kind']==kind]
    if any(e['kind'] not in ('poison','boot','start','copy','stack','create','release','finish','oom','rollback','fault','cancel') for e in events):raise ValueError('wide event kind')
    if get('poison')!=[dict(kind='poison',bytes=1056768)] or get('boot')!=[dict(kind='boot',catalog=261,scratch=258,reserved=3079,zero=1,aliases=0)]:raise ValueError('wide boot proof')
    if len(get('start'))!=8 or {(e['slot'],e['gen']) for e in get('start')}!=set(rows):raise ValueError('wide starts')
    if [(e['slot'],e['gen']) for e in get('release')]!=rows:raise ValueError('wide release order')
    for e in get('release'):
        if not 0<e['frames']<=261 or e['fenced']!=1 or not 0<e['before']<e['after']==e['before']+e['frames']<=4194304:raise ValueError('wide release balance')
    for kind in ('copy','create','stack'):
        es=get(kind)
        if len(es)!=4 or [e['gen'] for e in es]!=[3,4,7,8]:raise ValueError('wide '+kind)
    if any(e['acquired']!=count for e in get('create')):raise ValueError('wide allocation count')
    if any(e['bytes']!=SIZE or not re.fullmatch('[0-9a-f]{64}',e['sha']) for e in get('copy')):raise ValueError('wide copy bytes')
    hashes=[e['sha'] for e in get('copy')]
    if hashes[0]!=hashes[2] or hashes[1]!=hashes[3] or hashes[0]==hashes[1]:raise ValueError('wide replacement bytes')
    if any(e['bytes']!=12288 or e['checksum']!=1566720 or e['immutable']!=1 or e['case']!=(case if case<6 and e['gen'] in (3,7) else 0) for e in get('stack')):raise ValueError('wide stack proof')
    if [e['gen'] for e in get('fault')]!=([3,7] if case in (1,2,3) else []):raise ValueError('wide exact faults')
    for e in get('fault'):
        if (e['vector'],e['error'])!=(14,{1:6,2:21,3:7}[case]):raise ValueError('wide fault reason')
        if not (e['address']==0x407fff if case==1 else 0x408000<=e['address']<0x410000 if case==2 else e['address']==0x410000):raise ValueError('wide fault address')
    if [e['gen'] for e in get('cancel')]!=([3,7] if case==5 else []) or any(e['state'] not in (1,6) for e in get('cancel')):raise ValueError('wide exact cancel')
    if len(get('finish'))!=2:raise ValueError('wide complete proof')
    for i,e in enumerate(get('finish'),1):
        if (e['run'],e['tasks'],e['generation'])!=(i,4,i*4) or not 0<e['free']==e['initial']<=4194304:raise ValueError('wide complete balance')
    for kind in ('oom','rollback'):
        es=get(kind)
        if [(e['owner'],e['acquired']) for e in es]!=([(1<<32,oom),(5<<32,oom)] if oom is not None else []):raise ValueError('wide injection scope')
        if kind=='rollback' and any(e['free']!=e['before'] for e in es):raise ValueError('wide rollback')
    # Every per-generation event is ordered around publication and retirement.
    for slot,gen in rows:
        def at(kind):return next(i for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen)
        if at('start')>=at('release'):raise ValueError('wide lifecycle order')
        if slot==2 and not at('copy')<at('create')<at('start')<at('stack')<at('release'):raise ValueError('wide immutable lifecycle order')
        if slot==2 and gen in (3,7) and case in (1,2,3,5):
            if not at('stack')<at('cancel' if case==5 else 'fault')<at('release'):raise ValueError('wide fault/fence ordering')
    return rows


def replay(folder,serial,trace,count):
    """Independent host oracle over bounded register and physical-read evidence."""
    folder=Path(folder);config=json.loads((folder/'config.json').read_text())
    s=config['s'];cs=config['cs'];case=config['case'];oom=config['oom']
    rows=validate(serial,trace,case,oom,count)
    raw=(folder/'reads.bin').read_bytes();index=(folder/'reads.jsonl').read_bytes()
    need=payload.require
    need(len(raw)<=268435456 and len(index)<=33554432,'large raw evidence capacity')
    blocks=[];events=[];current=None;cursor=0
    for line in index.splitlines():
        row=json.loads(line)
        if 'begin' in row:
            need(current is None,'non-nested raw callback');current=dict(name=row['begin'],reads=[],registers={},events=[])
        elif 'end' in row:
            need(current is not None and row['end']==current['name'],'paired raw callback')
            blocks.append(current);current=None
        elif 'event' in row:
            need(current is not None,'event inside raw callback');current['events'].append(row['event']);events.append(row['event'])
        elif 'address' in row:
            n=row['bytes'];at=row['offset'];need(current is not None and at==cursor and 0<=n<=1056768 and at+n<=len(raw),'exact raw extent')
            current['reads'].append((row['address'],raw[at:at+n]));cursor+=n
        else:
            need(current is not None and set(row)=={'register','value'},'raw register schema')
            current['registers'][row['register']]=row['value']
    need(current is None and cursor==len(raw) and len(blocks)<=8192,'complete raw stream')
    expected=[json.loads(x[5:]) for x in trace.splitlines() if x.startswith('WIDE ')]
    need(events==expected,'raw events bind complete diagnostic trace')
    DM=0xffff800000000000;HIGH=0xffffffff80000000;MASK=0x3fffff000;NX=1<<63
    copies={};started={};pending=None;free_calls=[];observed=set();creating=None;sources={}
    for block in blocks:
        reads=block['reads'];registers=block['registers'];name=block['name'];ev=block['events']
        def memory(address,n):
            for at,data in reads:
                if at<=address and n<=len(data)-(address-at):return data[address-at:address-at+n]
            raise ValueError('missing raw memory '+hex(address)+'/'+str(n)+' in '+name)
        def q(address):return struct.unpack('<Q',memory(address,8))[0]
        def d(address):return struct.unpack('<I',memory(address,4))[0]
        def task(slot):return struct.unpack('<512Q',memory(s['scheduler_tasks']+slot*4096,4096))
        def leaf(root,va,direct=DM):
            for shift in (39,30,21):
                entry=q(direct+root+((va>>shift)&511)*8)
                if not entry&1:return 0
                need(not entry&128,'no user huge page');root=entry&MASK
            return q(direct+root+((va>>12)&511)*8)
        def user(t,va,n):
            data=bytearray()
            while n:
                pte=leaf(t[2],va);take=min(n,4096-(va&4095));need(pte&5==5,'raw user page accessibility')
                data+=memory(DM+(pte&MASK)+(va&4095),take);n-=take;va+=take
            return bytes(data)
        if name=='boot' and ev:
            need(registers['eflags']&512==0 and registers['cr0']&65536,'boot IF/WP')
            need(not any(memory(HIGH+0xb05000,1056768)),'raw boot scrub')
            bitmap=memory(s['usable_bitmap'],385)
            need(int.from_bytes(bitmap,'little')&((1<<3079)-1)==0,'raw reserved extent')
            for address in range(0xa00000,0xc07000,4096):
                flags=1 if address<0xb05000 else 3
                need(q(s['high_page_table']+(address>>12)*8)&~0x60==address|flags|NX,'raw boot leaf')
                need(not leaf(registers['cr3'],DM+address,HIGH),'raw no direct alias')
        elif name=='copy':
            record=memory(s['elf_import_record'],SIZE);t=struct.unpack('<512Q',memory(registers['r12'],4096))
            need(t[0]==9 and allocations(record)==count and t[1] not in copies,'raw immutable admission')
            need(ev==[dict(kind='copy',gen=t[1],bytes=SIZE,sha=hashlib.sha256(record).hexdigest())],'raw copy digest')
            copies[t[1]]=record
        elif name=='start' and ev:
            slot=d(s['scheduler_current_slot']);t=task(slot);gen=t[1]
            need(t[0]==2 and gen not in started and registers['eflags']&512==0,'raw start state')
            record=memory(s['boot_program_catalog']+slot*266336,266336) if slot<2 else copies[gen]
            slots,header=(64,96) if slot<2 else (256,288)
            need(t[260]==struct.unpack_from('<Q',record,16)[0] and 0x40f000<=t[261]<0x410000 and not t[261]&15,'raw entry/stack')
            owned=[]
            for page in range(256):
                rights=6 if page==8 else record[24+page] if page<slots else 0
                pte=leaf(t[2],0x400000+page*4096)
                if not rights:need(not pte and not t[4+page],'raw absent high slot');continue
                frame=pte&MASK;flags=5|(2 if rights==6 else 0)|(0 if rights==5 else NX)
                need(frame>=0x100000000 and pte&~0x60==frame|flags,'raw exact user permissions')
                if rights==6:
                    need(frame==(t[3] if page==8 else t[4+page]),'raw private ownership');owned.append(frame)
                else:need(t[4+page]==0,'raw shared immutable frame')
                if page!=15:
                    expected_page=bytes(4096) if page==8 else record[header+page*4096:header+(page+1)*4096]
                    need(memory(DM+frame,4096)==expected_page,'raw initial page bytes')
            need(len(set(owned))==len(owned),'raw distinct private frames')
            for previous in started.values():
                if previous['live']:need(not set(previous['owned'])&set(owned),'raw cross-generation isolation')
            argc=2 if slot<2 else 3
            argv=struct.unpack('<'+'Q'*(argc+7),user(t,t[261],(argc+7)*8))
            need(argv[0]==argc and argv[argc+1:]==(0,0,0x52534901,0,0,0),'raw canonical startup')
            args=[user(t,p,128).split(b'\0')[0] for p in argv[1:argc+1]]
            wanted=[('program%d.prg'%slot).encode(),str(slot).encode()] if slot<2 else [b'wide-child' if gen in (3,7) else b'wide-new',str(case if case<6 and gen in (3,7) else 0).encode()]
            need(args[:2]==wanted,'raw startup arguments')
            need(not any(user(t,0x408000,32768)[:t[261]-0x408000]),'raw fresh stack')
            started[gen]=dict(live=True,owned=owned,slot=slot)
        elif name=='syscall' and ev:
            t=task(2);gen=t[1];record=copies[gen]
            need(t[0]==2,'raw live child state')
            hits=[p for p in range(16,256) if record[24+p]==6 and record[288+p*4096:296+p*4096]==struct.pack('<Q',0x31474d494752414c)]
            need(len(hits)==1,'raw witness binding')
            witness=struct.unpack('<6Q',user(t,0x400000+hits[0]*4096,48))
            magic,owner,stack,n,checksum,mode=witness
            need(owner and n==12288 and 0x408000<=stack<=0x410000-n and checksum==1566720,'raw stack witness')
            need(mode==(case if case<6 and gen in (3,7) else 0),'raw selected fault mode')
            need(user(t,stack,n)==bytes(i^0x6a for i in range(256))*48,'raw live stack bytes')
            need(user(t,0x480000,4096)==bytes(i^0x31 for i in range(256))*16,'raw middle RW')
            need(user(t,0x4fe000,4096)==bytes(i^0x93 for i in range(256))*16,'raw final RW')
            for page in range(256):
                if record[24+page] in (4,5):need(user(t,0x400000+page*4096,4096)==record[288+page*4096:288+(page+1)*4096],'raw immutable RX/R')
            need(user(task(0),sources[gen],SIZE)==bytes([0x5a])*SIZE,'raw entire source overwrite')
            observed.add(gen)
        elif name=='create_begin':
            need(creating is None,'raw serialized CREATE')
            creating=dict(source=q(s['family_request']+24),before=d(s['free_frame_count']),owner=q(s['family_records']))
        elif name=='create_end':
            need(creating is not None and len(ev)==1,'raw CREATE outcome')
            if registers['rax']==0xfffffffffffffff4:
                need(oom is not None and ev[0]['kind']=='rollback' and d(s['free_frame_count'])==creating['before'],'raw partial OOM rollback')
            else:
                gen=registers['rax']>>32
                need(ev[0]['kind']=='create' and ev[0]['gen']==gen and gen in copies,'raw generation publication')
                sources[gen]=creating['source']
            creating=None
        elif name=='fault':
            t=task(2);frame=struct.unpack('<22Q',memory(registers['rdi'],176))
            need(t[1] in (3,7) and t[1] in observed and frame[15]==14 and frame[18]==0x33,'raw contained page fault')
            need(frame[16]=={1:6,2:21,3:7}[case],'raw page fault rights')
            address=registers['cr2'];need(address==0x407fff if case==1 else 0x408000<=address<0x410000 if case==2 else address==0x410000,'raw fault address')
        elif name=='cancel':
            t=task(registers['rdi']);need(case==5 and registers['rdi']==2 and t[1] in observed and t[0] in (1,6),'raw cancellation target')
        elif name=='release_begin' and reads and any(a==s['scheduler_current_slot'] for a,b in reads):
            slot=d(s['scheduler_current_slot']);t=task(slot);tables=struct.unpack('<4Q',memory(s['scheduler_table_frames']+slot*32,32))
            frames=[x for x in list(t[4:260])+[t[3]]+list(reversed(tables)) if x]
            need(pending is None and t[0] in (3,4) and frames[-1]==t[2]!=registers['cr3'],'raw fenced release')
            need(registers['eflags']&512==0 and len(set(frames))==len(frames),'raw serialized release')
            for address,n in ((s['family_profiles']+slot*32,32),(s['scheduler_syscall_profiles']+slot*16,16),
                (s['scheduler_runqueue_membership']+slot,1),(s['scheduler_deadline_membership']+slot,1),
                (cs['clients']+slot*108,108),(cs['pending']+slot*2144,2144)):
                need(not any(memory(address,n)),'raw authority/IPC revocation')
            hp=cs['native_heap_state']+232+slot*99368
            need(struct.unpack('<8Q',memory(hp,64))==(0,t[1],0,0,0,0x20000000,0,0),'raw heap generation fence')
            need(not any(memory(hp+552,5120)) and not any(memory(hp+32808,12288)),'raw heap cleanup')
            pending=dict(slot=slot,gen=t[1],frames=frames,before=d(s['free_frame_count']));free_calls=[]
        elif name=='freed':
            need(pending is not None,'raw free within release');free_calls.append(registers['rdi'])
        elif name=='release_end':
            need(pending is not None and free_calls==pending['frames'] and registers['rax']==1,'raw exact free order')
            slot=pending['slot'];need(d(s['free_frame_count'])==pending['before']+len(free_calls),'raw frame balance')
            need(not any(task(slot)[2:260]) and not any(memory(s['scheduler_table_frames']+slot*32,32)) and not any(memory(s['scheduler_fp_states']+slot*512,512)),'raw frame/FP scrub')
            started[pending['gen']]['live']=False;pending=None
        elif name=='finish':
            need(pending is None and registers['eflags']&512==0,'raw finished boundary')
            nonzero={s['free_frame_count'],s['scheduler_initial_free'],s['scheduler_reap_count'],s['timer_runtime_ticks'],s['timer_runtime_eois'],s['scheduler_last_tick'],s['process_run_generation']}
            for address,data in reads:
                if address in nonzero:continue
                if address==s['elf_context_window'] or s['elf_context_store']<=address<s['elf_context_store']+9*2320:
                    need(len(data)==2320 and not any(data[:2304]) and not any(data[2308:]),'raw context scrub')
                else:need(not any(data),'raw final zeroed state')
            need(d(s['free_frame_count'])==d(s['scheduler_initial_free']) and d(s['scheduler_reap_count'])==4,'raw complete balance')
            need(q(s['timer_runtime_ticks'])==q(s['timer_runtime_eois'])==q(s['scheduler_last_tick']),'raw timer balance')
    need(len(started)==8 and observed=={3,4,7,8} and not any(x['live'] for x in started.values()) and pending is None,'raw complete lifecycle')
    return rows
