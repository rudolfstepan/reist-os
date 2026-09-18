"""One explicit periodic PIO image; original owner proof plus exact CPU ledger."""
from pathlib import Path
import argparse,hashlib,inspect,json,struct,sys,time,uuid,zlib
import run_qemu_x86_64_pool_pio as owner
import run_qemu_x86_64_service_cpu as cpu
import native_cpu_trace
ROOT=owner.ROOT;BASE=ROOT/'build/codex-agent/r83aq-service-pio/active-calibration'
IMAGE=BASE/'native/x86_64/reist-x86_64-bootstrap.elf'
helpers=owner.helpers;transport=owner.transport;pio=owner.pio
CASES=owner.CASES;FATAL_CASES=cpu.FATAL_CASES;CPU_FILE=cpu.CPU_FILE


def reap_probe_address(symbols):
    base=symbols['process_ipc_service64'];end=symbols['process_ipc_service64.not_reap']
    if type(base) is not int or type(end) is not int or not 0<=base<=(1<<64)-24 or end!=base+24:
        raise ValueError('service PIO reap probe layout')
    return base+19


def reap_probe_binding(read,symbols):
    address=reap_probe_address(symbols)
    # MOV EAX,7; TEST EDI,EDI; JNZ +5; MOV EAX,1;
    # CMP EDI,4; JNZ +5; MOV EAX,5. Only op4 reaches the last MOV.
    if read(address-19,24)!=bytes.fromhex('b80700000085ff7505b80100000083ff047505b805000000'):
        raise ValueError('service PIO reap probe instructions')
    return address


def scope_reap_probe(code):
    code=helpers.once(code,"Hook('process_ipc_service64',cold_reap)",
        "S['service_pio_reap_probe']=reap_probe_address(S)\nHook('service_pio_reap_probe',cold_reap)")
    code=helpers.once(code,'def cold_control_paths():\n',
        "def cold_control_paths():\n    assert reap_probe_binding(mem,S)==S['service_pio_reap_probe']\n")
    return inspect.getsource(reap_probe_address)+'\n'+inspect.getsource(reap_probe_binding)+'\n'+code


def observer_body():
    code=owner.observer_body()
    for old,new in (
        ('==(4,272,8,0)','==(5,336,8,0)'),
        ("('process_run_plan',272)","('process_run_plan',336),('scheduler_cpu_windows',256)"),
        ('header==(5,64,1,0)','header==(6,80,1,0)'),
        ('w[2]==25','w[2]==60'),('sleeps=25','sleeps=60'),
        ('callbacks<=4096','callbacks<=8192'),
        ("Hook('scheduler_enter_task64.state_published',start)","start_hook=Hook('scheduler_enter_task64.state_published',start)"),
        ("        created_sources[gen]=source_pointer;source_pending=gen",
         "        created_sources[gen]=source_pointer;source_pending=gen\n        start_hook.enabled=True"),
        ("    if slot==0:\n        address=CONFIG['pool_pio_root']",
         "    cpu_start(slot,gen)\n    if slot==0:\n        address=CONFIG['pool_pio_root']"),
        ("    if slot>=2:assert gen in proofs,'child witness before fence'",
         "    if slot>=2:assert gen in proofs,'child witness before fence'\n    cpu_final(slot,gen)"),
        ("    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512",
         "    start_hook.enabled=True\n    runs+=1;assert runs<=2 and not release and not created and not reg('eflags')&512"),
        ("    emit('finish',run=runs,free=free()",
         "    if runs==2:cpu_ledger.finish()\n    emit('finish',run=runs,free=free()"),
        ("        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))",
         "        stop_reads.before_write()\n        gdb.selected_inferior().write_memory(target,struct.pack('<Q',CASE))"),
        ("    assert release is None and not reg('eflags')&512\n",
         "    release_guard(release,reg,release_failure_path)\n")):
        code=helpers.once(code,old,new)
    code=helpers.replace_function(code,'user','def user(t,va,n):\n    return read_user_spans(t,va,n,mem)')
    # Keep the complete original witness until every created generation has
    # published it. Thereafter only GETPID/CREATE/CANCEL have syscall effects
    # in this observer. Never stop on each device/clock call after that proof.
    code=helpers.once(code,"Hook('process_run_syscall64',syscall)",
        "syscall_hook=Hook('process_run_syscall64',syscall)\n"
        "syscall_narrow=[Hook('process_run_syscall64.pid',syscall),Hook('family_syscall64',syscall)]\n"
        "for hook in syscall_narrow:hook.enabled=False\n"
        "def syscall_hooks(collect):\n"
        "    syscall_hook.enabled=collect\n"
        "    for hook in syscall_narrow:hook.enabled=not collect")
    code=helpers.once(code,"        proofs.add(gen);emit('witness',gen=gen,parent=entry['parent'],heap=8192,immutable=1,sha=hashlib.sha256(data).hexdigest())",
        "        proofs.add(gen);emit('witness',gen=gen,parent=entry['parent'],heap=8192,immutable=1,sha=hashlib.sha256(data).hexdigest())\n"
        "    if call not in (22,132) and created_sources and not source_pending and set(created_sources)<=proofs:\n"
        "        syscall_hooks(False)")
    code=helpers.once(code,'        start_hook.enabled=True','        start_hook.enabled=True\n        syscall_hooks(True)')
    code=helpers.once(code,'    start_hook.enabled=True\n    runs+=1','    start_hook.enabled=True\n    syscall_hooks(True)\n    runs+=1')
    code=helpers.once(code,"        assert gen==t[1] and kind==starts[gen]['kind'] and phase in (0,1)",
        "        if phase==2:\n"
        "            assert gen==t[1] and kind==starts[gen]['kind'] and value in (5,10,15,20,25,30,35,40)\n"
        "            previous=cpu_batches.get(gen,0);assert value==previous+5\n"
        "            assert not any(user(t,CONFIG['service'],128))\n"
        "            cpu_batches[gen]=value;emit('cpu_batch',gen=gen,bursts=value)\n"
        "            if value==40:\n"
        "                current,now,records=cpu_snapshot(slot);assert current==8\n"
        "                cpu_idle[gen]=0;emit('cpu_idle',slot=slot,gen=gen,step=0,now=now,records=records)\n"
        "            return\n"
        "        assert cpu_batches.get(gen)==40\n"
        "        if phase==3:\n"
        "            assert gen==t[1] and kind==starts[gen]['kind'] and value in (6,12) and value==cpu_idle[gen]+6\n"
        "            assert not any(user(t,CONFIG['service'],128))\n"
        "            current,now,records=cpu_snapshot(slot);assert current==8\n"
        "            cpu_idle[gen]=value;emit('cpu_idle',slot=slot,gen=gen,step=value,now=now,records=records);return\n"
        "        assert cpu_idle.get(gen)==12\n"
        "        assert gen==t[1] and kind==starts[gen]['kind'] and phase in (0,1)")
    code=helpers.once(code,"            emit('ready',gen=gen,limit=1,capacity=value,deadline=p[4])",
        "            emit('ready',gen=gen,limit=1,capacity=value,deadline=p[4])\n            if CASE!=12:service_pause_arm(gen,p)")
    code=helpers.once(code,"        emit('request',gen=pio_owner>>32,sequence=1,lba=1,deadline=h[7])",
        "        service_pause_request(pio_owner>>32)\n        emit('request',gen=pio_owner>>32,sequence=1,lba=1,deadline=h[7])")
    code=helpers.once(code,'    if runs==2:cpu_ledger.finish()',
        '    assert service_pause_pending is None and not pause_sleep_hook.enabled and not pause_block_hook.enabled and not pause_return_hook.enabled\n    if runs==2:cpu_ledger.finish()')
    body=code+'\nfrom pathlib import Path\n'
    for function in (cpu.read_user_spans,cpu.release_guard,cpu.cpu_pack,cpu.CPULedger,
                     cpu.cpu_snapshot_layout,cpu.ReadOnlyCPUStops):
        body+=inspect.getsource(function)+'\n'
    body+="release_failure_path=Path(CONFIG['cpu_ledger']).with_name('release-failure.json')\n"
    # Keep complete failed-prefix records too; a missing footer still fails.
    body=helpers.once(body,"path.open('xb')","path.open('xb',buffering=0)")
    body+="cpu_ledger=CPULedger(Path(CONFIG['cpu_ledger']),gdb.write)\ncpu_batches={}\ncpu_idle={}\n"
    body+=cpu.CPU_OBSERVER+'\n'+inspect.getsource(cpu.SameStopReads)
    body+="\nstop_reads=SameStopReads(globals())\nHook.stop=stop_reads.wrap_stop(Hook.stop)\nReleaseEnd.stop=stop_reads.wrap_stop(ReleaseEnd.stop)\n"
    return cpu.defer_observer_callbacks(scope_reap_probe(body+SERVICE_PAUSE_OBSERVER),('Hook','ReleaseEnd'))


SERVICE_PAUSE_OBSERVER=r'''
service_pause_pending=None
def service_pause_arm(gen,profile):
    global service_pause_pending
    assert service_pause_pending is None and not pause_sleep_hook.enabled and not pause_block_hook.enabled and not pause_return_hook.enabled
    assert gen in starts and starts[gen]['live'] and starts[gen]['slot']==DRIVER_SLOT and cpu_idle[gen]==12
    endpoint=q(S['syscall_rdi']);assert q(S['syscall_rax'])==53 and 0<endpoint<=0xffffffff
    service_pause_pending=dict(gen=gen,profile=tuple(profile),step=-1,attempts=0,endpoint=endpoint,completion=[])
    pause_sleep_hook.enabled=True

def service_pause_record(step):
    pending=service_pause_pending;assert pending is not None and pending['step']==step-1
    t=task(DRIVER_SLOT);gen=pending['gen'];assert t[1]==gen and not reg('eflags')&512
    current,now,records=cpu_snapshot(DRIVER_SLOT);assert current==8 and records[0]==gen
    profile=struct.unpack('<4IQ',user(t,CONFIG['service']+104,24))
    assert profile==pending['profile'] and now*10<profile[4]
    root=task(0);assert root[1]==starts[gen]['parent']
    if step==0:
        assert d(S['scheduler_current_slot'])==0 and root[0]==2
        assert q(S['syscall_rax'])==54 and q(S['syscall_rdi'])==pending['endpoint'] and q(S['syscall_rdx'])==800
        address=q(S['syscall_rsi'])
        assert user(root,address,140)==struct.pack('<3I',1,140,128)+bytes(128)
        pending['wait']=[54,pending['endpoint'],address,800]
        pending['sleep']=now
    elif step==1:
        assert root[0]==6 and t[0]==6 and pending['sleep']<=now<=pending['sleep']+10
        pending['blocked']=now;pending['records']=list(records)
    else:
        assert step==2 and t[0]==6 and now-pending['blocked']>=70 and now-pending['sleep']>=80
        assert records==pending['records'] and root[0]==2 and len(pending['completion'])==3
    pending['step']=step
    emit('cpu_pause',step=step,slot=DRIVER_SLOT,gen=gen,root=starts[gen]['parent'],now=now,
         records=records,state=t[0],ms=800,profile=list(profile),root_state=root[0],
         wait=list(pending['wait']),completion=list(pending['completion']))

def service_pause_sleep():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    service_pause_record(0);pause_sleep_hook.enabled=False;pause_block_hook.enabled=True;pause_return_hook.enabled=True

def service_pause_blocked():
    pending=service_pause_pending;assert pending is not None and pending['step']==0
    pending['attempts']+=1;assert pending['attempts']<=16
    if task(DRIVER_SLOT)[0]!=6 or task(0)[0]!=6:return
    service_pause_record(1);pause_block_hook.enabled=False

def service_pause_request(gen):
    global service_pause_pending
    assert service_pause_pending is not None and service_pause_pending['gen']==gen
    assert not pause_sleep_hook.enabled and not pause_block_hook.enabled and not pause_return_hook.enabled
    service_pause_record(2);service_pause_pending=None

def service_pause_return():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    pending=service_pause_pending;assert pending is not None and pending['step']==1 and not pending['completion']
    assert task(0)[1]==starts[pending['gen']]['parent'] and not reg('eflags')&512
    request=struct.unpack('<7Q',mem(reg('r13'),56))
    assert list(request[:4])==pending['wait'] and request[4]==0 and request[5]==(1<<64)-110
    assert request[6]==pending['sleep']+80 and q(reg('r13')+2128)==140
    now=q(S['scheduler_last_tick']);assert request[6]<=now and now*10<pending['profile'][4]
    pending['completion']=[now,request[6],-110];pause_return_hook.enabled=False

pause_sleep_hook=Hook('process_ipc_syscall64',service_pause_sleep);pause_sleep_hook.enabled=False
pause_block_hook=Hook('process_run_dispatch64',service_pause_blocked);pause_block_hook.enabled=False
pause_return_hook=Hook('process_ipc_take64.done',service_pause_return);pause_return_hook.enabled=False
'''


def observer(config,folder,case,oom):
    fillers,_,per=owner.dimensions(case)
    mask=sum(1<<n for n in (4,5,6,9,22,40,41,42,49,50,51,52,53,54,55,58))
    settings=dict(config,case=case,oom=oom,fillers=fillers,per=per,mask=mask,cpu_ledger=(folder/CPU_FILE).as_posix())
    record=settings.pop('child_record');packed=zlib.compress(record,9);sha=hashlib.sha256(record).hexdigest()
    if cpu.decode_child_record(packed,sha)!=record:raise ValueError('service PIO configuration')
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+
        '\n'+inspect.getsource(cpu.decode_child_record)+"\nCONFIG['child_record']=decode_child_record(bytes.fromhex("+
        repr(packed.hex())+'),'+repr(sha)+','+repr(sys.executable)+')\n'+native_cpu_trace.scope_observer(observer_body())+'\nend\ncontinue\n')


def owner_validator():
    code=inspect.getsource(owner._validate)
    for old,new in (("'trace_drained','trace_clean'}","'trace_drained','trace_clean','cpu_batch','cpu_idle','cpu_pause'}|CPU_KINDS"),
                    (' and ticks<=32 and ',' and '),
                    ("            need(status!=256 or ticks==32,'CPU exhaustion')",
                     "            # Complete periodic CPU proof is checked independently before return."),
                    ('sleeps=25','sleeps=60')):
        code=helpers.once(code,old,new)
    namespace=dict(vars(owner),CPU_KINDS=cpu.CPU_KINDS)
    exec(compile(code,'<periodic PIO original owner proof>','exec'),namespace)
    return namespace['_validate']


def validate_cpu(serial,events,case):
    _,driver,per=owner.dimensions(case)
    def need(ok,text):
        if not ok:raise ValueError('service PIO CPU '+text)
    starts={e['gen']:e for e in events if e['kind']=='start'}
    receipts={}
    for match in owner.wide.process.REAP.finditer(serial):
        slot,gen,status,state,total,rip=struct.unpack('<4I2Q',bytes.fromhex(match[1]))
        need(gen not in receipts,'duplicate receipt');receipts[gen]=(slot,status,state,total)
    previous={};position={};last_tick={};counts={};finished=set();batches={};ready=set();idle={}
    for index,event in enumerate(events):
        kind=event['kind']
        if kind not in cpu.CPU_KINDS|{'cpu_batch','cpu_idle','ready'}:continue
        gen=event['gen'];entry=starts[gen];slot=entry['slot'];run=(gen-1)//per
        if kind=='cpu_batch':
            need(slot==driver and gen in previous and gen not in finished and gen not in ready,'batch owner/state')
            value=event['bursts'];need(type(value) is int and value==batches.get(gen,0)+5 and value<=40,'batch order')
            batches[gen]=value;continue
        if kind=='ready':
            need(slot==driver and gen not in ready and batches.get(gen)==40 and counts[gen]>=40,'real work before ready')
            need(gen in idle and list(idle[gen])==[0,6,12],'complete idle before ready')
            need(previous[gen][6]>=1,'cross-period owner');ready.add(gen);continue
        now=event['now'];need(event['slot']==slot and type(now) is int and 0<=now<1<<60,'owner/time')
        for key in (('before','after') if kind=='cpu_charge' else ('records',)):
            words=event[key]
            need(type(words) is list and len(words)==8 and all(type(n) is int and 0<=n<1<<64 for n in words),'full words')
        if kind=='cpu_idle':
            step=event['step'];need(type(step) is int and step in (0,6,12),'idle step')
            need(slot==driver and gen not in finished and gen not in ready and batches.get(gen)==40 and counts[gen]>=40,'idle owner/order/work')
            need(event['records']==previous[gen] and now>=previous[gen][3],'idle exact CPU snapshot')
            entries=idle.setdefault(gen,{})
            need(step==len(entries)*6,'idle no missing/repeated step')
            if step:need(now-entries[step-6]>=60,'idle actual blocking time')
            entries[step]=now
            if step==12:
                origin=previous[gen][5];need((now-origin)//100>(entries[0]-origin)//100,'idle crosses immutable window')
        elif kind=='cpu_start':
            words=event['records'];need(gen not in previous and words[:5]==[gen,32,0,0,100] and
                0<=words[5]<=now and words[6:]==[0,0],'initial immutable binding')
            need(next(i for i,e in enumerate(events) if e['kind']=='start' and e['gen']==gen)<index,'start order')
            previous[gen]=words;counts[gen]=0;position[gen]=index
        elif kind=='cpu_charge':
            need(gen not in finished and event['before']==previous[gen] and now>last_tick.get(run,-1),'charge continuity')
            after,result=cpu.charge_result(event['before'],now)
            need(event['after']==after and type(event['result']) is int and event['result']==result,'exact pure charge')
            previous[gen]=after;counts[gen]+=1;last_tick[run]=now
        else:
            words=event['records'];need(gen not in finished and words==previous[gen] and now>=words[3] and
                position[gen]<index<next(i for i,e in enumerate(events) if e['kind']=='release' and e['gen']==gen),'retirement order')
            actual_slot,status,state,total=receipts[gen]
            need(actual_slot==slot and words[2]==total==counts[gen],'lifetime receipt')
            if status==256:need(case==9 and slot==driver and entry['round']==0 and words[7]==32,'window exhaustion')
            else:need(words[7]<32,'nonexhausted terminal')
            if slot==driver:need(gen in ready and total>=40,'device generation complete work')
            finished.add(gen)
    need(finished==set(starts) and sum(counts.values())<=2048,'complete bounded ledger')
    for gen in ready:
        positions=[i for i,e in enumerate(events) if e.get('gen')==gen and e['kind']=='cpu_batch']
        bound=next(i for i,e in enumerate(events) if e.get('gen')==gen and e['kind']=='bind')
        end=next(i for i,e in enumerate(events) if e.get('gen')==gen and e['kind']=='ready')
        need(len(positions)==8 and bound<positions[0]<positions[-1]<end,'bound device before warmup and self-test')


def validate_service_pause(events,case):
    def need(ok,message):
        if not ok:raise ValueError('service PIO client pause '+message)
    driver=owner.dimensions(case)[1];starts={e['gen']:e for e in events if e['kind']=='start'}
    ready={};records={};stages={};requests={}
    for index,event in enumerate(events):
        kind=event['kind'];gen=event.get('gen')
        if kind in cpu.CPU_KINDS:records[gen]=event['after'] if kind=='cpu_charge' else event['records']
        elif kind=='ready':ready[gen]=(index,event)
        elif kind=='request':requests[gen]=index
        elif kind=='cpu_pause':
            need(set(event)=={'kind','step','slot','gen','root','now','records','state','ms','profile','root_state','wait','completion'},'fields')
            need(all(type(event[n]) is int for n in ('step','slot','gen','root','now','state','ms','root_state')),'integer fields')
            need(case!=12 and gen in ready and gen in records and gen in starts and event['slot']==driver==starts[gen]['slot'] and
                event['root']==starts[gen]['parent'] and event['ms']==800 and event['now']>=records[gen][3],'owner/time')
            words=event['records'];profile=event['profile']
            need(type(words) is list and len(words)==8 and all(type(n) is int and 0<=n<1<<64 for n in words) and words==records[gen],'exact CPU snapshot')
            need(type(profile) is list and len(profile)==5 and all(type(n) is int and 0<=n<1<<64 for n in profile) and
                profile[:4]==[1,24,1,0] and profile[4]==ready[gen][1]['deadline'] and event['now']*10<profile[4],'immutable session')
            rows=stages.setdefault(gen,[]);step=event['step'];need(step==len(rows) and step<3,'step sequence')
            wait=event['wait'];completion=event['completion']
            need(type(wait) is list and len(wait)==4 and all(type(n) is int for n in wait) and
                wait[0]==54 and 0<wait[1]<=0xffffffff and 0x410000<=wait[2]<=0x440000-140 and wait[3]==800,'IPC wait binding')
            need(type(completion) is list and all(type(n) is int for n in completion),'IPC completion fields')
            if step==0:need(ready[gen][0]<index and event['state'] in (1,2,5,6) and event['root_state']==2 and not completion,'ready before root wait')
            elif step==1:need(event['state']==event['root_state']==6 and not completion and wait==rows[0]['wait'] and rows[0]['now']<=event['now']<=rows[0]['now']+10,'both blocked within100ms')
            else:
                need(event['state']==6 and event['now']-rows[1]['now']>=70 and event['now']-rows[0]['now']>=80,'real blocked/root delay')
                need(words==rows[1]['records'] and profile==rows[1]['profile'],'unchanged blocked state')
                need(event['root_state']==2 and wait==rows[0]['wait'] and len(completion)==3 and
                    completion[1]==rows[0]['now']+80 and completion[1]<=completion[0]<=event['now'] and completion[2]==-110,
                    'actual IPC timeout before request')
            rows.append(dict(event,position=index))
    expected=set() if case==12 else set(ready)
    need(set(stages)==expected and all(len(rows)==3 and rows[-1]['position']<requests.get(gen,-1) for gen,rows in stages.items()),'complete pause before every request')


def validate_capture(serial,trace,case,oom,count,sha,folder):
    try:
        failure=folder/'release-failure.json'
        if failure.exists() or failure.is_symlink():raise ValueError('service PIO release guard failure')
        path=folder/CPU_FILE
        if path.is_symlink() or not 0<path.stat().st_size<=2084*168:raise ValueError('service PIO CPU ledger extent')
        # Rename only the known event prefix for the existing strict codec;
        # bind mixed records and final closure before returning original names.
        normalized=''.join('TASK_POOL '+line[9:] if line.startswith('POOL_PIO ') else line for line in trace.splitlines(keepends=True))
        expanded=cpu.expand_cpu_trace(normalized,path.read_bytes())
        expanded=''.join('POOL_PIO '+line[10:] if line.startswith('TASK_POOL ') else line for line in expanded.splitlines(keepends=True))
        rows=owner_validator()(serial,expanded,case,oom,count,sha)
        events=[json.loads(line[9:]) for line in expanded.splitlines() if line.startswith('POOL_PIO ')]
        validate_cpu(serial,events,case)
        validate_service_pause(events,case)
        return rows
    except (KeyError,TypeError,StopIteration,struct.error,IndexError) as error:
        raise ValueError('malformed service PIO evidence: '+str(error)) from error


FATAL_RANGES=cpu.FATAL_RANGES+(('native_pio_state',64),('native_pio_request',64))


def fatal_mutation(kind,saved):
    if len(saved)!=len(FATAL_RANGES) or tuple(map(len,saved))!=tuple(n for _,n in FATAL_RANGES):
        raise ValueError('service PIO fatal extent')
    state=struct.unpack('<8Q',saved[9]);generation=struct.unpack_from('<Q',saved[0],7*1024+8)[0]
    owner_handle=(generation<<32)|7
    if not (state[0]==owner_handle and state[1]==owner_handle^0xffffffffffffffff and state[2]==0 and
            state[3]<=state[4]<1<<60 and state[5]<=64 and state[6]<=state[4] and state[7]==0):
        raise ValueError('service PIO fatal released owner')
    changed,writes=cpu.fatal_mutation(kind,saved[:9])
    return changed+saved[9:],writes


FATAL_BODY=r'''
from pathlib import Path
import gdb,struct,json,hashlib
S=CONFIG['s'];OUT=Path(CONFIG['out']);KIND=CONFIG['kind']
RANGES=[(S[name],size) for name,size in FATAL_RANGES]
inferior=gdb.selected_inferior()
configured=False;released=False;injected=False;fenced=False;diagnosed=False
saved=None;callbacks=0;ports=0
def reg(name):return int(gdb.parse_and_eval('$'+name))&0xffffffffffffffff
def mem(address,size):return bytes(inferior.read_memory(address,size))
def q(address):return struct.unpack('<Q',mem(address,8))[0]
def state():return [mem(a,n) for a,n in RANGES]
def event(kind,**values):gdb.write('SERVICE_PIO_FATAL '+json.dumps(dict(kind=kind,**values),sort_keys=True)+'\n')
def snapshot(name,values):
    raw=b''.join(values)
    with (OUT/(name+'.bin')).open('xb') as stream:assert stream.write(raw)==len(raw)
    return hashlib.sha256(raw).hexdigest()
class Probe(gdb.Breakpoint):
    def __init__(self,name,label,enabled=True):
        super().__init__('*'+hex(S[name]),internal=True);self.label=label;self.enabled=enabled
    def stop(self):
        global configured,released,injected,fenced,diagnosed,saved,callbacks,ports
        try:
            callbacks+=1;assert callbacks<=2048
            if self.label=='setup':
                if mem(S['scheduler_mode'],1)!=b'\x08' or struct.unpack('<I',mem(S['scheduler_current_slot'],4))[0]!=0:return False
                assert not configured and not reg('eflags')&512
                task=struct.unpack('<128Q',mem(S['scheduler_tasks'],1024))
                assert task[0]==2 and task[1]==1
                address=CONFIG['pool_pio_root'];assert not address&7 and 0x410000<=address<=0x440000-136
                assert read_user_spans(task,address,136,mem)==struct.pack('<Q',0x31544f4f52504950)+bytes(128)
                va=address+8;root=task[2];mask=0x3fffff000
                for shift in (39,30,21):
                    entry=q(0xffff800000000000+root+((va>>shift)&511)*8)
                    assert entry&7==7 and not entry&128;root=entry&mask
                entry=q(0xffff800000000000+root+((va>>12)&511)*8)
                assert entry&~mask&~0x60==(1<<63)|7 and (va&4095)<=4088
                physical=(entry&mask)+(va&4095)
                assert entry&mask==task[4+(va-0x400000)//4096] and 0x100000000<=physical<0x400000000
                target=0xffff800000000000+physical;assert mem(target,8)==bytes(8)
                inferior.write_memory(target,struct.pack('<Q',5));assert mem(target,8)==struct.pack('<Q',5)
                configured=True;self.enabled=False;event('mode',gen=1,address=va,physical=physical,before=0,value=5)
            elif self.label=='port':
                ports+=1;assert ports<=128 and mem(S['native_pio_out8.done']-1,1)==b'\xee'
                port=reg('edx')&65535;value=reg('eax')&255
                if injected:
                    assert not fenced and port==0x3f6 and value==6 and state()==saved
                    fenced=True;self.enabled=False;event('fence',physical=1,sha=snapshot('fenced',state()))
                elif port==0x3f6 and value==2:
                    assert configured and not released and q(S['native_pio_state'])&0xffffffff==7 and q(S['native_pio_state']+16)==0
                    released=True;self.enabled=False;trigger.enabled=True;event('release')
            elif self.label=='trigger':
                if mem(S['scheduler_mode'],1)!=b'\x08' or reg('rdi')!=S['scheduler_cpu_budgets']+7*32 or reg('rdx')!=0:return False
                assert configured and released and not injected and not reg('eflags')&512
                before=state();changed,writes=fatal_mutation(KIND,before)
                original=snapshot('before',before);assert len(writes)==1 and len(writes[0][2])==8
                for index,offset,raw in writes:inferior.write_memory(RANGES[index][0]+offset,raw)
                assert state()==changed;saved=changed;injected=True;self.enabled=False;port_hook.enabled=True
                for hook in forbidden:hook.enabled=True
                event('inject',case=KIND,original=original,sha=snapshot('damaged',saved),writes=8)
            elif self.label=='diagnostic':
                if not injected:return False
                assert fenced and not diagnosed and state()==saved and not reg('eflags')&512
                diagnosed=True;event('diagnostic',interrupts=0,sha=snapshot('diagnostic',state()))
            elif self.label=='halt':
                assert injected and fenced and diagnosed and state()==saved and not reg('eflags')&512
                assert mem(S['halt64'],4)==b'\xfa\xf4\xeb\xfd'
                event('halt',cli_hlt=1,sha=snapshot('halt',state()));gdb.execute('detach');gdb.execute('quit 0')
            else:raise AssertionError('cleanup/resume after CPU corruption')
        except Exception as error:
            event('OBSERVER_FAIL',where=self.label,error=repr(error));gdb.execute('quit 71')
        return False
Probe('scheduler_enter_task64.state_published','setup')
port_hook=Probe('native_pio_out8.done','port')
trigger=Probe('reist_x64_period_apply','trigger',False)
Probe('serial_init64','diagnostic');Probe('halt64','halt')
forbidden=[Probe(name,'forbidden',False) for name in ('process_run_resume64','family_terminal64',
    'scheduler_force_cleanup64','scheduler_release_task_frames64')]
'''


def fatal_observer(config,folder,kind):
    if kind not in FATAL_CASES:raise ValueError('service PIO fatal case')
    mutation=inspect.getsource(fatal_mutation).replace('cpu.fatal_mutation(kind,saved[:9])','cpu_fatal_mutation(kind,saved[:9])')
    original=inspect.getsource(cpu.fatal_mutation).replace('def fatal_mutation(','def cpu_fatal_mutation(').replace('FATAL_RANGES','CPU_FATAL_RANGES')
    body=('from types import SimpleNamespace\n'+inspect.getsource(cpu.charge_result)+'\n'+original+'\n'+mutation+'\n'+
          inspect.getsource(cpu.read_user_spans)+'\n'+FATAL_BODY)
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+
        repr(dict(s=config['s'],pool_pio_root=config['pool_pio_root'],kind=kind,out=folder.as_posix()))+
        '\nFATAL_CASES='+repr(FATAL_CASES)+'\nFATAL_RANGES='+repr(FATAL_RANGES)+'\nCPU_FATAL_RANGES='+repr(cpu.FATAL_RANGES)+
        '\n'+cpu.defer_observer_callbacks(body,('Probe',))+'\nend\ncontinue\n')


def validate_fatal(serial,trace,kind,folder):
    if kind not in FATAL_CASES or 'OBSERVER_FAIL' in trace:raise ValueError('service PIO fatal observer')
    events=[json.loads(line[18:]) for line in trace.splitlines() if line.startswith('SERVICE_PIO_FATAL ')]
    if [e['kind'] for e in events]!=['mode','release','inject','fence','diagnostic','halt']:
        raise ValueError('service PIO fatal exact path')
    mode=events[0]
    if set(mode)!={'kind','gen','address','physical','before','value'} or any(type(mode[n]) is not int for n in ('gen','address','physical','before','value')) or not (
        mode['gen']==1 and mode['before']==0 and mode['value']==5 and not mode['address']&7 and
        0x410008<=mode['address']<=0x440000-128 and 0x100000000<=mode['physical']<0x400000000):
        raise ValueError('service PIO fatal fixture binding')
    if events[1]!={'kind':'release'}:raise ValueError('service PIO fatal release')
    marker='REIST_X86_64_EXCEPTION_FATAL pio=1'
    if serial.count('REIST_X86_64_EXCEPTION_FATAL')!=1 or marker not in serial or any(s in serial for s in
        (owner.wide.process.DONE,owner.wide.process.SUCCESS,'PROCESS_REAP_OK')):raise ValueError('service PIO fatal serial')
    snapshots={};extent=sum(n for _,n in FATAL_RANGES)
    for name in ('before','damaged','fenced','diagnostic','halt'):
        path=folder/(name+'.bin');pio.regular(path,extent);raw=path.read_bytes()
        if len(raw)!=extent:raise ValueError('service PIO fatal snapshot extent')
        parts=[];position=0
        for _,n in FATAL_RANGES:parts.append(raw[position:position+n]);position+=n
        snapshots[name]=parts
    changed,writes=fatal_mutation(kind,snapshots['before']);damaged=b''.join(changed);sha=hashlib.sha256(damaged).hexdigest()
    if any(snapshots[n]!=changed for n in ('damaged','fenced','diagnostic','halt')):raise ValueError('service PIO fatal mutated metadata')
    if events[2:]!=[dict(kind='inject',case=kind,original=hashlib.sha256(b''.join(snapshots['before'])).hexdigest(),sha=sha,writes=8),
        dict(kind='fence',physical=1,sha=sha),dict(kind='diagnostic',interrupts=0,sha=sha),dict(kind='halt',cli_hlt=1,sha=sha)]:
        raise ValueError('service PIO fatal physical fence/binding')
    return len(writes)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path);parser.add_argument('--fatal',action='store_true')
    args=parser.parse_args();image=args.image.resolve();base=args.evidence.resolve()
    if image!=IMAGE.resolve() or base!=(BASE/('fatal-guests' if args.fatal else 'guests')).resolve():
        parser.error('service PIO evidence scope')
    import verify_x86_64_service_pio as verify
    frozen=verify.admit_runtime(image,args.fatal);verify.matrix_budget(frozen['candidate'],args.fatal,starting=True)
    folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True);pio.safe_folder(folder)
    result=dict(candidate=frozen['candidate'],image_sha256=owner.digest(image),fatal=args.fatal,passed=False,closed=False,cases=[])
    (folder/'summary.json').write_text(json.dumps(result,indent=2));spent=0;started=time.monotonic()
    try:
        config=owner.image_config(image);count=owner.wide.allocations(config['child_record']);sha=hashlib.sha256(config['child_record']).hexdigest()
        result.update(allocations=count,child_sha256=sha)
        for case,ram in (tuple((k,4096) for k in FATAL_CASES) if args.fatal else CASES):
            if owner.digest(image)!=result['image_sha256']:raise ValueError('service PIO image changed')
            oom=None if args.fatal else {13:0,14:count//2,15:count-1}.get(case)
            out=folder/f'guest-{case}-{ram}';out.mkdir();row=dict(case=case,ram=ram,oom=oom,passed=False);result['cases'].append(row)
            begin=time.monotonic()
            try:
                fixture=None if case==12 else pio.Fixture(out,block=True)
                code=fatal_observer(config,out,case) if args.fatal else observer(config,out,case,oom)
                serial,trace=transport.capture(image,out,code,ram,fixture,halt_witness=args.fatal,
                    binary_memory=None if args.fatal else 'equivalence',diagnostic_metrics=True,service_pio_budget=True)
                if not args.fatal:native_cpu_trace.validate_capture(out,trace,cpu)
                row['tasks']=validate_fatal(serial,trace,case,out) if args.fatal else len(validate_capture(serial,trace,case,oom,count,sha,out))
            finally:
                elapsed=time.monotonic()-begin;spent+=elapsed;row['elapsed']=round(elapsed,6)
            if elapsed>45 or spent>(90 if args.fatal else 720):raise ValueError('service PIO guest deadline')
            row['passed']=True;print('SERVICE_PIO_GUEST_OK',case,ram,row['elapsed'],flush=True)
        result['passed']=True;return 0
    except (ValueError,RuntimeError,OSError,KeyError,AssertionError) as error:
        result['error']=str(error);print('SERVICE_PIO_FAIL',str(error),flush=True);return 1
    finally:
        result.update(closed=True,elapsed=round(time.monotonic()-started,6),guest_elapsed=round(spent,6))
        (folder/'summary.json').write_text(json.dumps(result,indent=2));print('SERVICE_PIO_EVIDENCE',folder,flush=True)


if __name__=='__main__':raise SystemExit(main())
