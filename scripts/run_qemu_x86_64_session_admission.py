"""AX adapters: unchanged CPU suite plus bounded cumulative-construction proof."""
from pathlib import Path
import ast,hashlib,inspect,json,re,struct,types
import run_qemu_x86_64_service_cpu as cpu
pool=cpu.pool;wide=pool.wide;transport=pool.transport;ROOT=pool.ROOT
FATAL_CASES=('session-generation','session-count')
FATAL_RANGES=cpu.FATAL_RANGES+(('family_session_window',56),)

def window_charge(before,generation,now):
    if (type(before) is not list or len(before)!=7 or
        any(type(v) is not int or not 0<=v<1<<64 for v in before) or
        type(generation) is not int or not 0<generation<1<<31 or
        type(now) is not int or not 0<=now<1<<60):raise ValueError('session window shape')
    gen,period,start,last,count,total,version=before
    if (gen!=generation or period!=100 or version!=1 or not start<=last<=now or
        last-start>=100 or not 0<=count<=8 or not count<=total<1<<31):
        raise ValueError('session window integrity')
    if total==0x7fffffff:return 2,before.copy()
    anchor=now-(now-start)%100
    used=count if anchor==start else 0
    if used==8:return 2,before.copy()
    return 1,[gen,100,anchor,now,used+1,total+1,1]

def validate_charge(before,after,generation,now,result):
    status,expected=window_charge(before,generation,now)
    if status!=result or expected!=after:raise ValueError('session charge publication')

def source_node(source,name):
    matches=[n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name]
    if len(matches)!=1:raise ValueError('exact observer node '+name)
    return ast.get_source_segment(source,matches[0])+'\n'

BODY=r'''
from pathlib import Path
import gdb,struct,hashlib,json
S=CONFIG['s'];CS=CONFIG['cs'];OUT=Path(CONFIG['out'])
DM=0xffff800000000000;MASK=0x3fffff000
starts={};runs=0;release=None;created=None;callbacks=0;snapshots=0;snapshot_bytes=0
def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff
def mem(a,n):return bytes(gdb.selected_inferior().read_memory(a&0xffffffffffffffff,n))
def q(a):return struct.unpack('<Q',mem(a,8))[0]
def d(a):return struct.unpack('<I',mem(a,4))[0]
def mode():return mem(S['scheduler_mode'],1)[0]
def task(slot):return struct.unpack('<128Q',mem(S['scheduler_tasks']+slot*1024,1024))
def free():return d(S['free_frame_count'])
def emit(kind,**values):gdb.write('SESSION '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\n')
def snapshot(raw):
    global snapshots,snapshot_bytes
    snapshots+=1;snapshot_bytes+=len(raw)
    assert snapshots<=512 and snapshot_bytes<=4*1024*1024 and len(raw)<=1024*1024
    name='session-%04d.bin'%snapshots
    with (OUT/name).open('xb') as stream:assert stream.write(raw)==len(raw)
    return dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def family():return mem(S['family_records'],512)+mem(S['family_session_window'],56)+mem(S['family_total'],4)
def walk(root,va):
    for shift in (39,30,21):
        e=q(DM+root+((va>>shift)&511)*8);assert e&1 and not e&128
        root=e&MASK
    return q(DM+root+((va>>12)&511)*8)
def start():
    if mode()!=8:return
    slot=d(S['scheduler_current_slot']);assert slot<8
    gen=q(S['scheduler_tasks']+slot*1024+8)
    if gen in starts:return
    t=task(slot);assert t[0]==2 and 0<gen<1<<31 and not reg('eflags')&512
    if slot<2:
        address=CONFIG['root_data'][slot]+8;entry=walk(t[2],address)
        assert entry&7==7 and address&4095<=4088
        physical=DM+(entry&MASK)+(address&4095)
        assert q(physical)==0
        gdb.selected_inferior().write_memory(physical,struct.pack('<Q',12))
        assert q(physical)==12
    else:assert q(S['process_run_plan']+16+slot*32+24)==6
    tables=mem(S['scheduler_table_frames']+slot*32,32)
    raw=mem(S['scheduler_tasks']+slot*1024,1024)+mem(S['family_records']+slot*64,64)+tables
    owned=[f for f in list(t[4:68])+[t[3]]+list(struct.unpack('<4Q',tables)) if f]
    assert len(owned)==len(set(owned)) and all(0x100000000<=f<0x400000000 and not f&4095 for f in owned)
    for e in starts.values():
        if e['live']:assert not set(e['owned'])&set(owned)
    starts[gen]=dict(slot=slot,live=True,owned=owned)
    emit('start',run=runs+1,slot=slot,gen=gen,raw=snapshot(raw))
def create_begin():
    global created
    assert mode()==8 and created is None and not reg('eflags')&512
    slot=d(S['scheduler_current_slot']);assert slot<2
    assert struct.unpack('<8Q',mem(S['family_request'],64))==(1|(64<<32),1,0,6,0,512,32,0)
    created=dict(slot=slot,now=q(S['scheduler_last_tick']),before=snapshot(family()))
def create_end():
    global created
    if created is None:return
    assert d(S['family_request']+8)==1 and not reg('eflags')&512
    assert d(S['scheduler_current_slot'])==created['slot'] and q(S['scheduler_last_tick'])==created['now']
    value=reg('rax');value=value-(1<<64) if value>>63 else value
    emit('create',run=runs+1,result=value,after=snapshot(family()),**created);created=None
def finish():
    global runs
    runs+=1;assert runs<=2 and release is None and created is None and not reg('eflags')&512
    pieces=[]
    for name,n in ZERO_RANGES:
        raw=mem(S[name],n);assert not any(raw),name;pieces.append(raw)
    raw=mem(S['family_begin'],S['family_end']-S['family_begin']);assert not any(raw);pieces.append(raw)
    assert free()==d(S['scheduler_initial_free']) and d(S['scheduler_reap_count'])==22
    assert q(S['timer_runtime_ticks'])==q(S['timer_runtime_eois'])==q(S['scheduler_last_tick'])
    assert len(starts)==22*runs and not any(v['live'] for v in starts.values())
    for slot in range(8):
        assert not any(mem(CS['clients']+slot*108,108)) and not any(mem(CS['pending']+slot*2144,2144))
        seen=[g for g,e in starts.items() if e['slot']==slot]
        if seen:
            gen=max(seen);assert d(S['scheduler_identity_retired']+slot*4)==gen
            hp=CS['native_heap_state']+232+slot*99368
            assert struct.unpack('<8Q',mem(hp,64))==(0,gen,0,0,0,0x20000000,0,0)
            assert not any(mem(hp+552,5120)) and not any(mem(hp+32808,12288))
            assert d(CS['retired']+slot*4)==gen
    emit('finish',run=runs,free=free(),initial=d(S['scheduler_initial_free']),tasks=22,raw=snapshot(b''.join(pieces)))
    if runs==2:gdb.execute('detach');gdb.execute('quit 0')
def fail():
    emit('OBSERVER_FAIL',where='kernel',stage=mem(S['scheduler_failure_stage'],1)[0]);gdb.execute('quit 73')
'''
ZERO_RANGES=(('scheduler_tasks',8192),('scheduler_fp_states',4096),('scheduler_table_frames',256),
 ('scheduler_cpu_budgets',256),('scheduler_cpu_windows',256),('scheduler_syscall_profiles',128),
 ('scheduler_syscall_context',16),('syscall_rax',120),('process_run_plan',336),
 ('process_run_generations',32),('process_run_receipt',32),('scheduler_runqueue_entries',64),
 ('scheduler_deadline_entries',128),('scheduler_runqueue_membership',8),('scheduler_deadline_membership',8),
 ('process_heap_pending_mask',8),('process_heap_receipts',256),('elf_import_record',266336))

def observer(config,folder):
    inherited='\n'.join(source_node(wide.OBSERVER,n) for n in ('Hook','release_begin','freed','ReleaseEnd'))
    # Reuse the accepted actual frame-free/IPC/heap/FP retirement observer.
    inherited=pool.helpers.once(inherited,"emit('release',slot=r['slot'],gen=r['gen'],frames=len(r['frames']),before=r['before'],after=free(),fenced=1)",
        "assert all(not any(mem(DM+f,4096)) for f in r['frames']),'freed frame bytes'\n            emit('release',slot=r['slot'],gen=r['gen'],frames=len(r['frames']),before=r['before'],after=free(),fenced=1)")
    code=BODY+'\n'+inherited+'''
free_hook=Hook('physical_frame_free64',freed);free_hook.enabled=False
Hook('scheduler_enter_task64.state_published',start)
Hook('family_create64',create_begin)
Hook('family_result64',create_end)
Hook('scheduler_release_task_frames64',release_begin)
Hook('x86_64_c_process_run64.restore',finish)
Hook('scheduler_fail',fail)
'''
    settings={k:v for k,v in config.items() if k!='child_record'};settings['out']=folder.as_posix()
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+
        '\nZERO_RANGES='+repr(ZERO_RANGES)+'\n'+cpu.defer_observer_callbacks(code,('Hook','ReleaseEnd'))+'\nend\ncontinue\n')

def validate(serial,trace,folder,config):
    if len(trace.encode())>131072 or 'OBSERVER_FAIL' in trace or any(m in serial for m in transport.FAILURES):
        raise ValueError('session failed capture')
    events=[json.loads(line[8:]) for line in trace.splitlines() if line.startswith('SESSION ')]
    starts={};released=set();successful={};attempts={};finishes=[];snapshot_count=0;total_bytes=0;rows=[]
    def need(value,message):
        if not value:raise ValueError('session '+message)
    def raw(ref,size):
        nonlocal snapshot_count,total_bytes
        snapshot_count+=1;total_bytes+=size
        path=folder/ref['file']
        need(ref['file']==f'session-{snapshot_count:04d}.bin' and not path.is_symlink(),'snapshot order')
        data=path.read_bytes()
        need(len(data)==size==ref['bytes'] and hashlib.sha256(data).hexdigest()==ref['sha256'],'snapshot binding')
        return data
    for event in events:
        kind=event['kind']
        if kind=='start':
            data=raw(event['raw'],1120);t=struct.unpack('<128Q',data[:1024]);f=struct.unpack('<8Q',data[1024:1088])
            gen=event['gen'];slot=event['slot'];need(gen not in starts and 0<=slot<8 and t[:2]==(2,gen),'start identity')
            need(f[0]==(gen<<32)|slot and f[5]==(1 if slot<2 else 2),'start family')
            if slot>=2:need(f[1] in starts and starts[f[1]]['slot']<2,'child owner')
            starts[(gen<<32)|slot]=event;starts[gen]=event # exact handles for parent lookup
        elif kind=='create':
            before=raw(event['before'],572);after=raw(event['after'],572)
            b=list(struct.unpack('<7Q',before[512:568]));a=list(struct.unpack('<7Q',after[512:568]));slot=event['slot'];need(slot<2,'creator')
            owner=struct.unpack_from('<Q',before,slot*64)[0];key=(event['run'],owner)
            spent=struct.unpack_from('<Q',before,slot*64+48)[0];new_spent=struct.unpack_from('<Q',after,slot*64+48)[0]
            result=event['result'];need(result==-11 or 0<result<1<<63,'creation result')
            attempts[key]=new_spent
            if result>0:
                need(new_spent==spent+1 and struct.unpack_from('<I',after,568)[0]==struct.unpack_from('<I',before,568)[0]+1,'cumulative charge')
                if slot==0:validate_charge(b,a,owner>>32,event['now'],1);need(a[5]==new_spent,'mirror')
                else:need(a==b and new_spent<=8,'finite peer')
                child=struct.unpack_from('<8Q',after,(result&0xffffffff)*64)
                need(child[0]==result and child[1]==owner and child[5]==2,'published child')
                successful[key]=successful.get(key,0)+1
            else:
                need(before==after,'denial nonmutation')
                if slot==1:need(spent==8,'peer lifetime exhaustion')
            rows.append(event)
        elif kind=='release':
            gen=event['gen'];need(gen in starts and gen not in released and starts[gen]['slot']==event['slot'],'release identity')
            need(event['frames']>0 and event['after']-event['before']==event['frames'] and event['fenced']==1,'frame balance');released.add(gen)
        elif kind=='finish':
            size=sum(n for _,n in ZERO_RANGES)+config['s']['family_end']-config['s']['family_begin']
            need(not any(raw(event['raw'],size)) and event['free']==event['initial'] and event['tasks']==22,'complete cleanup')
            finishes.append(event)
        else:raise ValueError('session unknown event')
    need(len(released)==44 and len(starts)==88 and [f['run'] for f in finishes]==[1,2],'two full runs')
    need(sorted(successful.values())==[8,8,12,12] and attempts==successful,'cumulative totals')
    need(sum(r['result']>0 for r in rows)==40 and sum(r['result']==-11 and r['slot']==1 for r in rows)==2,'finite peer rejection')
    need(snapshot_count<=512 and total_bytes<=4*1024*1024,'evidence bounds')
    receipts=list(wide.process.REAP.finditer(serial))
    need(len(receipts)==44 and serial.count(wide.process.DONE)==2 and serial.count(wide.process.SUCCESS)==1,'real complete serial receipts')
    for receipt in receipts:
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(receipt[1]))
        need(gen in released and starts[gen]['slot']==slot and state==4 and
             status==(90+slot if slot<2 else 97) and 0x400000<=rip<0x440000,'receipt ABI/outcome')
        if slot>=2:need(ticks<=32,'unchanged child CPU bound')
    return dict(tasks=44,creates=40,snapshots=snapshot_count)

def fatal_mutation(kind,saved):
    if kind not in FATAL_CASES or tuple(map(len,saved))!=tuple(n for _,n in FATAL_RANGES):raise ValueError('session fatal shape')
    values=list(struct.unpack('<7Q',saved[-1]));root=struct.unpack_from('<Q',saved[4])[0]
    window_charge(values,root>>32,values[3])
    index=0 if kind=='session-generation' else 4;value=values[0]+1 if index==0 else 9
    raw=struct.pack('<Q',value);changed=list(saved);changed[-1]=saved[-1][:index*8]+raw+saved[-1][index*8+8:]
    return changed,[(len(saved)-1,index*8,raw)]

def fatal_observer(config,folder,kind):
    body=cpu.FATAL_BODY
    body=pool.helpers.once(body,"if mem(S['scheduler_mode'],1)!=b'\\x08' or reg('rdi')!=S['scheduler_cpu_budgets']+7*32:return False",
        "if mem(S['scheduler_mode'],1)!=b'\\x08' or reg('rdi')!=S['family_session_window'] or reg('rsi')!=2:return False")
    body=pool.helpers.once(body,"and reg('rdx')==0","and reg('rdx')==q(S['family_session_window'])")
    body=pool.helpers.once(body,"trigger=Probe('reist_x64_period_apply','trigger',False)","trigger=Probe('session_admission64','trigger')")
    body=pool.helpers.once(body,"Probe('family_create64.parent_result','arm')",'')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+
        repr(dict(s=config['s'],kind=kind,out=folder.as_posix()))+'\nFATAL_CASES='+repr(FATAL_CASES)+
        '\nFATAL_RANGES='+repr(FATAL_RANGES)+'\n'+inspect.getsource(window_charge)+'\n'+inspect.getsource(fatal_mutation)+
        cpu.defer_observer_callbacks(body,('Probe',))+'\nend\ncontinue\n')

def validate_fatal(serial,trace,kind,folder):
    # Execute the unchanged exact fatal path/snapshot/hash oracle with only the
    # explicitly added private state range and fault transformation substituted.
    env=dict(cpu.__dict__,FATAL_CASES=FATAL_CASES,FATAL_RANGES=FATAL_RANGES,fatal_mutation=fatal_mutation)
    return types.FunctionType(cpu.validate_fatal.__code__,env)(serial,trace,kind,folder)
