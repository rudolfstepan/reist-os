"""Bounded wide-program guest matrix; immutable bytes and actual frame ledgers."""
from pathlib import Path
import argparse, hashlib, json, re, struct, subprocess, time, uuid
import build_x86_64_c_payload as payload
import build_x86_64_boot_programs as producer
import run_qemu_x86_64_boot_programs as transport
import run_qemu_x86_64_process_run as process
ROOT=Path(__file__).resolve().parents[1]
SIZE=266336

def allocations(record):
    if len(record)!=SIZE or record[:16]!=b'RNPGv2\0\0'+struct.pack('<II',2,SIZE):
        raise ValueError('wide record identity')
    flags=record[24:88]
    if any(f not in (0,4,5,6) for f in flags) or flags[7:16]!=bytes([0,0]+[6]*7):
        raise ValueError('wide record rights')
    return sum(bool(f) for f in flags)+sum(f==6 for f in flags)+5

def observer(s,c,folder,case,oom):
    config=dict(s=s,cs={n:v['value'] for n,v in c['symbols'].items()},case=case,oom=oom)
    return ('set logging file '+(folder/'frame-trace.log').as_posix()+'\nset logging overwrite on\n'
            'set logging enabled on\npython\nCONFIG='+repr(config)+'\n'+OBSERVER+'\nend\ncontinue\n')

# This is debugger-side Python, never linked into the guest.
OBSERVER=r'''
import gdb,struct,hashlib,json
S=CONFIG['s'];CS=CONFIG['cs'];CASE=CONFIG['case'];OOM=CONFIG['oom']
DM=0xffff800000000000;HIGH=0xffffffff80000000;MASK=0x3fffff000;NX=1<<63
starts={};copies={};proofs=set();runs=0;release=None;created=None;injected=set();callbacks=0
def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a&0xffffffffffffffff,n))
def q(a):return struct.unpack('<Q',mem(a,8))[0]
def d(a):return struct.unpack('<I',mem(a,4))[0]
def mode():return mem(S['scheduler_mode'],1)[0]
def task(slot):return struct.unpack('<128Q',mem(S['scheduler_tasks']+slot*1024,1024))
def free():return d(S['free_frame_count'])
def emit(kind,**fields):gdb.write('WIDE '+json.dumps(dict(kind=kind,**fields),sort_keys=True)+'\n')
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
            self.fn()
        except Exception as error:
            import traceback
            gdb.write(traceback.format_exc())
            emit('OBSERVER_FAIL',where=self.fn.__name__,error=repr(error))
            gdb.execute('quit 71')
        return False
def poison():
    gdb.selected_inferior().write_memory(0xb05000,bytes([0xa5])*270336)
    emit('poison',bytes=270336)
boot_entry=S['x86_64_bootstrap_start'];S['x86_64_bootstrap_start']=boot_entry-HIGH
Hook('x86_64_bootstrap_start',poison);S['x86_64_bootstrap_start']=boot_entry
boot_seen=False
def boot():
    global boot_seen
    if boot_seen:return
    boot_seen=True
    assert not reg('eflags')&512 and reg('cr0')&(1<<16),'boot IF/WP'
    assert not any(mem(HIGH+0xb05000,270336)),'boot scratch zero'
    bitmap=mem(S['usable_bitmap'],(0xb47000//4096+7)//8)
    assert not int.from_bytes(bitmap,'little')&((1<<(0xb47000//4096))-1),'boot reserved frames'
    for addr,end,flags in ((0xa00000,0xb05000,1),(0xb05000,0xb47000,3)):
        for p in range(addr,end,4096):
            leaf=q(S['high_page_table']+(p>>12)*8)
            assert leaf&~0x60==p|flags|NX,('boot leaf',p,leaf)
            assert not walk(reg('cr3'),DM+p,HIGH),('boot direct alias',p)
    emit('boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)
Hook('x86_64_c_core_handoff64',boot)
def start():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
    if gen in starts:return
    assert slot<4 and t[0]==2 and gen and not reg('eflags')&512
    record=mem(S['boot_program_catalog']+slot*266336,266336) if slot<2 else copies[gen]
    assert t[68]==struct.unpack_from('<Q',record,16)[0] and 0x410000<=t[68]<0x440000
    assert 0x40f000<=t[69]<0x410000 and not t[69]&15
    owned=[]
    for page in range(64):
        pf=6 if page==8 else record[24+page];e=walk(t[2],0x400000+page*4096)
        if not pf:assert not e;continue
        frame=e&MASK;flags=5|(2 if pf==6 else 0)|(0 if pf==5 else NX)
        assert frame>=0x100000000 and e&~0x60==frame|flags
        if pf==6:
            assert frame==(t[3] if page==8 else t[4+page]);owned.append(frame)
        else:assert t[4+page]==0
        actual=mem(DM+frame,4096)
        if page==15:continue # Startup frame independently verified below.
        assert actual==(bytes(4096) if page==8 else record[96+page*4096:96+(page+1)*4096])
    assert len(owned)==len(set(owned)) and not t[12]
    for other,entry in starts.items():
        if entry['live']:assert not set(owned)&set(entry['owned'])
    argc=2 if slot<2 else 3
    values=struct.unpack('<'+'Q'*(argc+7),user(t,t[69],(argc+7)*8));assert values[0]==argc and values[argc+1:]==(0,0,0x52534901,0,0,0)
    args=[user(t,p,128).split(b'\0')[0] for p in values[1:argc+1]]
    expected=[('program%d.prg'%slot).encode(),str(slot).encode()] if slot<2 else [b'wide-child' if gen in (3,7) else b'wide-new',str(CASE if CASE<6 and (gen-1)%4==2 else 0).encode()]
    assert args[:2]==expected
    if slot==2:assert len(args[2])==8 and all(c in b'0123456789abcdef' for c in args[2]) and int(args[2],16)>0
    # No uninitialized data outside the exact canonical startup image.
    stack=user(t,0x408000,32768);assert not any(stack[:t[69]-0x408000])
    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)
    emit('start',slot=slot,gen=gen,pages=sum(bool(f) for f in record[24:88])+1,private=len(owned))
Hook('scheduler_enter_task64.state_published',start)
def copy():
    t=struct.unpack('<128Q',mem(reg('r12'),1024));gen=t[1]
    assert gen not in copies and len(copies)<4
    record=mem(S['elf_import_record'],266336)
    assert record[:16]==b'RNPGv2\0\0'+struct.pack('<II',2,266336)
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
    hits=[96+p*4096 for p in range(16,64) if record[24+p]==6 and record[96+p*4096:104+p*4096]==struct.pack('<Q',0x594d454d45444957)]
    assert len(hits)==1
    addr=0x400000+hits[0]-96
    magic,owner,stack,n,checksum,case=struct.unpack('<6Q',user(t,addr,48))
    if not owner or not n:return
    assert owner and n==12288 and 0x408000<=stack and stack+n<=0x410000
    assert case==(CASE if CASE<6 and (gen-1)%4==2 else 0)
    expected=bytes(i^0x6a for i in range(256))*48
    assert user(t,stack,n)==expected and checksum==sum(expected)
    # The explicit IPC token admits exercise only after parent source mutation.
    parent=task(0);ptr=created_sources[gen]
    assert user(parent,ptr,266336)==bytes([0x5a])*266336
    for p in range(64):
        if record[24+p] in (4,5):assert user(t,0x400000+p*4096,4096)==record[96+p*4096:96+(p+1)*4096]
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
    frames=[f for f in list(t[4:68])+[t[3]]+list(reversed(tables)) if f]
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
    release['freed'].append(reg('rdi'));assert len(release['freed'])<=69
free_hook=Hook('physical_frame_free64',freed);free_hook.enabled=False
class ReleaseEnd(gdb.Breakpoint):
    def __init__(self,addr):super().__init__('*'+hex(addr),internal=True,temporary=True)
    def stop(self):
        global release
        self.enabled=False
        try:
            free_hook.enabled=False;r=release;assert reg('rax')==1
            assert r['freed']==r['frames'] and free()==r['before']+len(r['frames'])
            t=task(r['slot']);assert not any(t[2:68])
            assert not any(mem(S['scheduler_table_frames']+r['slot']*32,32))
            assert not any(mem(S['scheduler_fp_states']+r['slot']*512,512))
            starts[r['gen']]['live']=False
            emit('release',slot=r['slot'],gen=r['gen'],frames=len(r['frames']),before=r['before'],after=free(),fenced=1)
            release=None
        except Exception as error:
            import traceback
            gdb.write(traceback.format_exc())
            emit('OBSERVER_FAIL',where='release_end',error=repr(error));gdb.execute('quit 72')
        return False
Hook('scheduler_release_task_frames64',release_begin)
def finish():
    global runs
    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512
    for name,n in [('scheduler_tasks',4096),('scheduler_fp_states',2048),('scheduler_table_frames',128),
      ('scheduler_cpu_budgets',128),('scheduler_syscall_profiles',64),('scheduler_syscall_context',16),
      ('syscall_rax',120),('process_run_plan',144),('process_run_generations',16),('process_run_receipt',32),
      ('scheduler_runqueue_entries',32),('scheduler_deadline_entries',64),('scheduler_runqueue_membership',4),
      ('scheduler_deadline_membership',4),('process_heap_pending_mask',8),('elf_import_record',266336)]:
        assert not any(mem(S[name],n)),name
    assert not any(mem(S['family_begin'],S['family_end']-S['family_begin']))
    for a in [S['elf_context_window']]+[S['elf_context_store']+i*592 for i in range(9)]:
        r=mem(a,592);assert not any(r[:576]) and not any(r[580:])
    assert free()==d(S['scheduler_initial_free']) and d(S['scheduler_reap_count'])==4
    assert q(S['timer_runtime_ticks'])==q(S['timer_runtime_eois'])==q(S['scheduler_last_tick'])
    assert len(starts)==runs*4 and len(proofs)==runs*2 and not any(v['live'] for v in starts.values())
    emit('finish',run=runs,free=free(),initial=d(S['scheduler_initial_free']),tasks=4,generation=d(S['process_run_generation']))
    if runs==2:gdb.execute('detach');gdb.execute('quit')
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
            if not (0x410000<=rip<0x440000 or case==2 and n==3 and 0x408000<=rip<0x410000):raise ValueError('wide instruction range')
            if not (ends[run-1].end() if run else -1)<row.start()<row.end()<=ends[run].start():raise ValueError('wide receipt ordering')
            rows.append((slot,gen));seen.add(n)
    events=[json.loads(line[5:]) for line in trace.splitlines() if line.startswith('WIDE ')]
    def get(kind):return [e for e in events if e['kind']==kind]
    if any(e['kind'] not in ('poison','boot','start','copy','stack','create','release','finish','oom','rollback','fault','cancel') for e in events):raise ValueError('wide event kind')
    if get('poison')!=[dict(kind='poison',bytes=270336)] or get('boot')!=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]:raise ValueError('wide boot proof')
    if len(get('start'))!=8 or {(e['slot'],e['gen']) for e in get('start')}!=set(rows):raise ValueError('wide starts')
    if [(e['slot'],e['gen']) for e in get('release')]!=rows:raise ValueError('wide release order')
    for e in get('release'):
        if not 0<e['frames']<=69 or e['fenced']!=1 or not 0<e['before']<e['after']==e['before']+e['frames']<=4194304:raise ValueError('wide release balance')
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

def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    image=a.image.resolve();base=a.evidence.resolve()
    if not image.is_relative_to(ROOT/'build') or not base.is_relative_to(ROOT/'build/codex-agent'):p.error('wide evidence scope')
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,cases=[]);started=time.monotonic();guest_time=0;reference=None
    try:
        for case in range(7):
            if case:
                out=folder/('build-'+str(case));out.mkdir()
                with (out/'build.log').open('wb') as log:
                    r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeWide','-MemoryCase',str(case),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                if r.returncode:raise ValueError('wide fixture build')
                image=out/'x86_64/reist-x86_64-bootstrap.elf'
            inner=payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');c=payload.validate(inner)
            payload.verify_outer(inner,payload.read_bounded(image,bits=32))
            mechanisms={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in image.parent.glob('*.o') if f.name!='elf64_loader.o'}
            if reference is not None and mechanisms!=reference:raise ValueError('wide mechanism drift')
            reference=mechanisms
            catalog=(image.parent/'boot-programs.bin').read_bytes()
            if len(catalog)!=4*SIZE:raise ValueError('wide catalog length')
            record=catalog[2*SIZE:3*SIZE];count=allocations(record)
            points=[0,1,2,count//4,count//2,count-1]
            if len(set(points))!=6 or any(n>=count for n in points):raise ValueError('wide OOM positions')
            variants=[(4096,n) for n in points] if case==6 else [(4096,None),(8192,None)] if case==0 else [(4096,None)]
            s=transport.symbols(image)
            for ram,oom in variants:
                out=folder/f'guest-{case}-{ram}-{oom}';out.mkdir();begin=time.monotonic()
                serial,trace=transport.capture(image,out,observer(s,c,out,case,oom),ram)
                elapsed=time.monotonic()-begin;guest_time+=elapsed
                if elapsed>30 or guest_time>390:raise ValueError('wide guest deadline')
                rows=validate(serial,trace,case,oom,count)
                summary['cases'].append(dict(case=case,ram=ram,oom=oom,tasks=len(rows),elapsed=round(elapsed,3),image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
                print('WIDE_GUEST_OK',case,ram,oom,flush=True)
        summary['passed']=True;summary['mechanisms']=reference
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('WIDE_FAIL',error);return 1
    finally:
        summary['elapsed']=round(time.monotonic()-started,3);summary['guest_elapsed']=round(guest_time,3)
        (folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('WIDE_EVIDENCE',folder)
    return 0

if __name__=='__main__':raise SystemExit(main())
