"""Concurrent application/FS/ATA qualification; one image, bounded full evidence."""
from pathlib import Path
import argparse,ast,hashlib,inspect,json,re,struct,sys,time,uuid
import run_qemu_x86_64_file_launch as file
import run_qemu_x86_64_task_pool as pool
import run_qemu_x86_64_service_cpu as cpu
import run_qemu_x86_64_service_pio as service
import native_cpu_trace
ROOT=file.ROOT;BASE=ROOT/'build/codex-agent/r83ar-live-file/terminal-receipt'
wide=file.wide;pio=file.pio;media=file.media;once=file.once
CASES=tuple([(0,n,4096,None) for n in range(5)]+[(0,2,8192,None)]+
    [(n,2,4096,None) for n in range(1,8)]+[(8,2,4096,p) for p in ('first','middle','last')]+
    [(n,2,4096,None) for n in range(9,18)])

def roles(case):
    if type(case) is not int or case not in range(18):raise ValueError('live file case')
    entries=[dict(role='root',slot=0,round=0,status=134 if case in (7,15) else 84 if case in (4,9) else 83,state=3 if case in (7,15) else 4),
             dict(role='peer',slot=1,round=0,status=77,state=4)]
    for n in range(1 if case in (7,15) else 2):
        entries.append(dict(role='driver',slot=2,round=n,status=134 if not n and case==6 else 256 if not n and case==14 else 0,state=3))
        status=134 if not n and case==5 else 256 if not n and case==12 else 90 if not n and case in (6,13,14) else 0
        entries.append(dict(role='fs',slot=3,round=n,status=status,state=4 if status==90 else 3))
        if case in (4,7,9) or not n and case in (5,6,10,11,12,13,14):continue
        status={1:134,2:256,3:0,15:0}.get(case,82) if not n else 82
        entries.append(dict(role='program',slot=4,round=n,status=status,state=4 if status==82 else 3))
    return {run*len(entries)+n+1:dict(item,root=run*len(entries)+1)
            for run in range(2) for n,item in enumerate(entries)}

def function(code,name):
    node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name==name)
    return ast.get_source_segment(code,node)

def observer_body():
    code=file.observer_body()
    # Keep existing physical/ELF/RPC checks; explicitly extend the task layout.
    code=code[:code.index('\nimage_retirement=None')]
    for old,new in (("'FILE_LAUNCH '","'LIVE_FILE '"),('callbacks<=4096','callbacks<=8192'),
        ('assert slot<4 and task(slot)[1]==gen','assert slot<8 and task(slot)[1]==gen'),
        ('assert len(release_pending)<4','assert len(release_pending)<8'),
        ('allocation_slot in (2,3)','allocation_slot in (2,3,4)'),
        ('allocation_slot==2 and CONFIG','allocation_slot==4 and CONFIG'),
        ("create_watch_leave(reg('rax')==0xfffffffffffffff4 or CONFIG['roles'][reg('rax')>>32]['role']=='driver')",
         'create_watch_leave(False)'),
        ("            if r['slot']==2 and CASE!=7 and d(S['process_run_generation'])%PER_RUN!=0:create_watch()",''),
        ("    assert image_retirement is None or image_retirement['phase']=='done'",'')):
        code=once(code,old,new)
    old_start=function(code,'start')
    # The pool prefix adds full private-image context and cross-owner frame checks.
    prefix=pool.START.split('    argc=2 if slot<2 else 6',1)[0]
    tail=old_start[old_start.index("    info=CONFIG['roles'][gen]"):]
    tail=once(tail,"            option=16 if info['round'] else {5:1,6:5,7:6,10:4}.get(CASE,0)",
        "            option=(16 if info['round'] else {5:1,6:5,7:6,10:4,11:2,12:3,13:6,14:7}.get(CASE,0))|(CONFIG['layout']<<8)")
    tail=once(tail,"    starts[gen]=dict(slot=slot,owned=owned,live=True,record=record)",
        "    starts[gen]=dict(slot=slot,owned=owned,mapped=[f for p,f in image],live=True,record=record,parent=info['root'] if slot>=2 else 0)")
    tail=once(tail,'    if slot==0:create_watch()','')
    tail=once(tail,'for i in range(4)','for i in range(8)')
    tail+='\n    cpu_start(slot,gen)\n    if slot==0:select_case(t,gen,leaves)\n'
    code=file.replace_function(code,'start',prefix+tail)
    context=once(pool.IMAGE_CONTEXT,'==(4,272,8,0)','==(5,336,8,0)')
    finish=once(pool.FINISH,"gen=max(g for g,e in starts.items() if e['slot']==slot)",
        "gen=max((g for g,e in starts.items() if e['slot']==slot),default=0)")
    finish=once(finish,'per=9 if CASE==6 else 8','per=PER_RUN')
    finish=once(finish,'    global runs\n','    global runs\n    start_hook.enabled=True\n')
    finish=once(finish,"('process_run_plan',272)","('process_run_plan',336),('scheduler_cpu_windows',256)")
    finish=once(finish,"    if runs==2:gdb.execute('detach');gdb.execute('quit')",
        "    assert not cancel_pending and oom_before is None\n"
        "    assert pstate()==(0,0xffffffffffffffff,1,0,0,0,0,0) and not any(mem(S['native_pio_request'],64))\n"
        "    if runs==2:gdb.execute('detach');gdb.execute('quit')")
    finish=once(finish,"    emit('finish',run=runs", "    if runs==2:cpu_ledger.finish()\n    emit('finish',run=runs")
    code=file.replace_function(code,'finish',finish)
    code=once(code,'    pio_retire(slot,gen)\n','    cpu_final(slot,gen)\n    pio_retire(slot,gen)\n')
    code=once(code,"    if (version,length)==(1,16):program_ready(slot,t,gen,raw);return",
        "    if (version,length)==(1,16):\n        if slot==0:program_go(t,gen,raw)\n        else:program_ready(slot,t,gen,raw)\n        return")
    code=once(code,"                if result:assert CASE==6 and not CONFIG['roles'][gen]['round']",
        "                if result:assert CASE in (6,13,14) and not CONFIG['roles'][gen]['round']")
    code=once(code,"else:assert slot==2 and CASE==7 and phase==9",
        "else:assert slot==2 and CASE in (7,13,14) and phase==9")
    code=once(code,"        if sequence==len(CONFIG['requests']) or bad or CASE==9:cancel_watch([gen-1,gen])",'')
    for name in ('caller_result','fault','program_ready','cancel_watch','cancel'):
        code=file.replace_function(code,name,function(EXTRA,name))
    code+=context+'\n'+EXTRA[:EXTRA.index('def caller_result():')]
    code+=EXTRA[EXTRA.index('def select_case('):]
    for obj in (cpu.cpu_pack,cpu.CPULedger,cpu.cpu_snapshot_layout,cpu.ReadOnlyCPUStops):
        code+='\n'+inspect.getsource(obj)
    code+='\nfrom pathlib import Path\ncpu_ledger=CPULedger(Path(CONFIG[\'cpu_ledger\']),gdb.write)\n'+cpu.CPU_OBSERVER
    code=once(code,"path.open('xb')","path.open('xb',buffering=0)")
    code+='\n'+inspect.getsource(cpu.SameStopReads)+"\nstop_reads=SameStopReads(globals())\nHook.stop=stop_reads.wrap_stop(Hook.stop)\nReleaseEnd.stop=stop_reads.wrap_stop(ReleaseEnd.stop)\n"
    code=service.scope_reap_probe(code)
    return native_cpu_trace.scope_observer(cpu.defer_observer_callbacks(code,('Hook','ReleaseEnd')))

EXTRA=r'''
live_phases=set();live_programs=set();oom_before=None

def caller_result():
    root=task(0)
    if mode()!=8 or root[0] not in (1,2,6):return
    magic,phase,owner,driver,app,status,address,workspace,round_,layout=struct.unpack('<10Q',user(root,CONFIG['result_address'],80))
    if magic!=0x4c49564546494c31 or (owner,phase) in live_phases:return
    gen=owner>>32;info=CONFIG['roles'][gen]
    assert info['role']=='fs' and info['root']==root[1] and info['round']==round_ and owner&0xffffffff==3
    assert driver==((gen-1)<<32)|2 and layout==CONFIG['layout'] and phase in (1,2,3)
    if status>=1<<63:status-=1<<64
    if phase==1:
        expected=-22 if CASE==4 else -27 if CASE==9 else -71 if CASE==10 and not round_ else None if CASE in (5,6,11,12,13,14) and not round_ else 0
        if expected is None:assert status<0
        else:assert status==expected
        if CASE in (5,11,12) and not round_:assert status in (-32,-110)
        actual=user(root,address,266336)
        assert actual==(b'\xa5'*266336 if status else CONFIG['prepared'])
        raw=user(root,workspace,2048)+user(root,workspace+2048,266336)
        assert raw==(b'\x5a'*268384 if CASE in (6,13,14) and not round_ else bytes(268384))
        assert not app and owner not in results
        results.add(owner);emit('file_result',gen=gen,caller=root[1],status=status,sha=hashlib.sha256(actual).hexdigest(),scrub=int(not any(raw)))
    else:
        assert (owner,phase-1) in live_phases and status==0 and app==((gen+1)<<32)|4
        assert owner in results and app>>32 in proofs and user(root,address,266336)==b'\x5a'*266336
        assert not any(user(root,workspace,2048)+user(root,workspace+2048,266336))
        states=[]
        for identity in (driver,owner,app):
            slot=identity&0xffffffff;t=task(slot)
            assert t[1]==identity>>32 and t[0] in (1,2,6) and starts[t[1]]['live']
            assert q(S['family_records']+slot*64+8)==root[1]<<32
            states.append(t[0])
        assert pstate()[0]==driver and pstate()[2]==0
        if phase==3:
            assert states[2]==6 and (owner,len(CONFIG['requests'])) in fs_replies
            assert fs_replies[(owner,len(CONFIG['requests']))][0]==0
        emit('live',gen=gen,app=app>>32,driver=driver>>32,root=root[1],phase=phase,states=states)
    live_phases.add((owner,phase))

def fault():
    caller_result();trace_drain();slot=d(S['scheduler_current_slot']);gen=task(slot)[1];info=CONFIG['roles'][gen]
    f=struct.unpack('<22Q',mem(reg('rdi'),176))
    assert CASE in (1,5,6,7,15) and slot=={1:4,5:3,6:2,7:0,15:0}[CASE] and not info['round']
    assert f[15:17]==(6,0) and f[18]==0x33
    assert info['role']=={1:'program',5:'fs',6:'driver',7:'root',15:'root'}[CASE]
    emit('fault',gen=gen,slot=slot,vector=6)
    if slot==0:cancel_watch([task(s)[1] for s in (2,3,4) if task(s)[0] in (1,2,6)])

def program_ready(slot,t,gen,raw):
    info=CONFIG['roles'][gen]
    assert slot==4 and info['role']=='program' and gen not in proofs
    assert raw[12:28]==struct.pack('<Q',gen)+b'ELF64RO!'
    assert gen in copies and copies[gen]==CONFIG['prepared']
    assert user(task(0),created_sources[gen],266336)==b'\x5a'*266336
    assert not any(mem(S['family_extended_masks']+slot*16,16))
    record=copies[gen]
    for page in range(64):
        if record[24+page] in (4,5):assert user(t,0x400000+page*4096,4096)==record[96+page*4096:96+(page+1)*4096]
    proofs.add(gen);emit('program_ready',gen=gen,slot=slot,source=266336,device=0,sha=hashlib.sha256(record).hexdigest())

def cancel_watch(generations):
    assert not cancel_pending and not cancel_hook.enabled
    assert 1<=len(generations)<=3 and len(set(generations))==len(generations)
    live={task(slot)[1] for slot in (2,3,4) if task(slot)[0] in (1,2,6)}
    assert set(generations)<=live
    cancel_pending.update(generations);cancel_hook.enabled=True

def cancel():
    caller_result();trace_drain();slot=reg('rdi');t=task(slot)
    assert slot in (2,3,4) and t[1] in cancel_pending
    if slot in (2,3):assert pstate()[2]==1
    emit('cancel',gen=t[1],slot=slot,state=t[0])
    cancel_pending.remove(t[1]);cancel_hook.enabled=bool(cancel_pending)

def select_case(t,gen,leaves):
    a=CONFIG['selection_address'];raw=user(t,a,16)
    assert raw==struct.pack('<4I',1,0,2,0) and a&4095<=4080
    leaf=leaves[(a-0x400000)//4096];assert leaf&~MASK&~0x60==NX|7
    target=DM+(leaf&MASK)+(a&4095);value=struct.pack('<4I',1,CASE,CONFIG['layout'],0)
    stop_reads.before_write()
    gdb.selected_inferior().write_memory(target,value);assert mem(target,16)==value
    emit('mode',gen=gen,slot=0,case=CASE,layout=CONFIG['layout'],before=raw.hex(),after=value.hex())

def program_go(t,gen,raw):
    caller_result();app=task(4);ag=app[1];info=CONFIG['roles'][ag]
    assert info['root']==gen and info['role']=='program' and ag in proofs and ag not in live_programs
    assert raw[12:28]==struct.pack('<Q',ag)+b'LIVE64GO' and ((ag-1)<<32|3,3) in live_phases
    assert app[0]==6 and q(S['syscall_rdi'])>0
    live_programs.add(ag);emit('go',gen=ag,root=gen)

def control_syscall():
    if mode()!=8 or d(S['scheduler_current_slot'])!=0:return
    caller_result()
    if q(S['syscall_rax'])!=132:return
    raw=user(task(0),q(S['syscall_rdi']),64);header=struct.unpack_from('<4I',raw)
    if header in ((5,64,1,0),(6,80,1,0)):
        assert created is None and not create_begin_hook.enabled
        create_watch()
    if header==(1,64,3,0):
        identity=struct.unpack_from('<Q',raw,16)[0];slot=identity&0xffffffff
        assert slot in (2,3,4)
        t=task(slot)
        if t[0]==0 and t[1]==0:
            gen=identity>>32;assert 0<gen<0x80000000 and len(t)==128 and not any(t)
            info=CONFIG['roles'][gen];root=task(0)[1];entry=starts[gen]
            assert info['slot']==slot and info['root']==root
            assert entry['slot']==slot and entry['parent']==root and not entry['live']
            result=info['status']|((0 if info['state']==4 else 1 if info['status'] else 2)<<32)
            receipt=struct.unpack('<8Q',mem(S['family_records']+slot*64,64))
            assert receipt==(identity,root<<32,0,0,result,4,0,0)
            return
        assert slot in (2,3,4) and task(slot)[1]==identity>>32
        if task(slot)[0] in (1,2,6):cancel_watch([identity>>32])

def file_oom_begin():
    global oom_before
    assert oom_before is None
    if OOM is None or allocation_slot!=4 or allocation_owner in injected:return
    gen=d(S['process_run_generation']);info=CONFIG['roles'][gen+1]
    assert CASE==8 and info['role']=='program' and not info['round']
    assert info['root']<<32==allocation_owner
    selected=mem(S['elf_image_selector'],1)[0]
    address=S['elf_context_window'] if selected==9 else S['elf_context_store']+9*592
    raw=mem(address,592);assert not any(raw[:576]) and not any(raw[580:])
    neighbors=[mem(S['scheduler_tasks']+slot*1024,1024) for slot in (2,3)]
    assert all(struct.unpack_from('<Q',r)[0] in (1,6) for r in neighbors)
    oom_before=(gen,neighbors,user(task(0),source_pointer,266336),address,raw)

def file_oom_finish():
    global oom_before
    if oom_before is None:return
    gen,neighbors,source,address,raw=oom_before
    assert reg('rax')==0xfffffffffffffff4 and allocation_owner in injected and free()==allocation_before
    assert d(S['process_run_generation'])==gen and gen+1 not in copies
    assert neighbors==[mem(S['scheduler_tasks']+slot*1024,1024) for slot in (2,3)]
    assert user(task(0),source_pointer,266336)==source and mem(address,592)==raw
    emit('oom_isolation',owner=allocation_owner,generation=gen,slot=4,neighbors=2,source=266336,empty_context=1)
    oom_before=None

Hook('family_syscall64',control_syscall)
Hook('native_pio_apply64.fence_request',control_syscall)
'''

def frames(layout,raw,response=False):
    original=file.frames(layout,raw,response)
    return original+[original[0]]

def lifecycle_validator():
    code=inspect.getsource(file._validate)
    changes=[
        ("if ticks>32 or not 0x410000<=rip<0x440000 or status==256 and ticks!=32:",
         "if not 0x410000<=rip<0x440000 or info['role']=='program' and (ticks>32 or status==256 and ticks!=32):"),
        ("json.loads(line[12:]) for line in trace.splitlines() if line.startswith('FILE_LAUNCH ')",
         "json.loads(line[10:]) for line in trace.splitlines() if line.startswith('LIVE_FILE ')"),
        ("'file_result','program_ready'}","'file_result','program_ready','mode','live','go','oom_isolation'}|cpu.CPU_KINDS"),
        ('bad=case==6 and not plan', 'bad=case in (6,13,14) and not plan'),
        ('partial=case in (6,7)', 'partial=case in (6,7,13,14)'),
        ('n=0 if case==7 or case==6 and first else 1 if case==9 or case in (5,10) and first else len(canonical)',
         'n=0 if case==7 or case in (6,13,14) and first else 1 if case==9 or case in (5,10,11,12) and first else len(canonical)-int(case==4)'),
        ('nr=0 if case==5 and first else n','nr=0 if case in (5,11,12) and first else n'),
        ('None if case in (5,6) and first','None if case in (5,6,11,12,13,14) and first'),
        ('if case==5 and first and e[','if case in (5,11,12) and first and e['),
        ('int(not (case==6 and first))','int(not (case in (6,13,14) and first))'),
        ("retired=get('image_retire');expected=[(root<<32,root+2) for root in (1,per+1)] if oom is not None else []",
         "retired=get('image_retire');expected=[]"),
        ("            for kind,g in (('file_result',gen-1),('release',gen-1),('release',gen-2)):\n                if position(kind,g)>=position('copy',gen):raise ValueError('file dependency before execution')",
         "            if position('file_result',gen-1)>=position('copy',gen):raise ValueError('live capture before execution')\n"
         "            for dep in (gen-1,gen-2):\n                if not position('create',dep)<position('copy',gen)<position('program_ready',gen)<position('release',dep):raise ValueError('live dependency at entry')")]
    for old,new in changes:code=once(code,old,new)
    env=dict(vars(file),roles=roles,frames=frames,cpu=cpu)
    exec(compile(code,'<live file lifecycle oracle>','exec'),env)
    return env['_validate']

def validate_cpu(serial,events,case):
    plan=roles(case);per=len(plan)//2;previous={};final=set();charges={};last={}
    receipts={}
    for m in wide.process.REAP.finditer(serial):
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(m[1]));receipts[gen]=(slot,status,state,ticks)
    for pos,e in enumerate(events):
        kind=e['kind']
        if kind not in cpu.CPU_KINDS:continue
        gen=e['gen'];info=plan[gen];slot=info['slot'];now=e['now'];run=(gen-1)//per
        if e['slot']!=slot or type(now) is not int or not 0<=now<1<<60:raise ValueError('live CPU identity/time')
        if kind=='cpu_start':
            b=e['records'];period=0 if slot==4 else 100
            if gen in previous or len(b)!=8 or any(type(n) is not int for n in b):raise ValueError('live CPU bind shape')
            if b[:4]!=[gen,32,0,0] or b[4]!=period or b[6:]!=[0,0] or not 0<=b[5]<=now or not period and b[5]:raise ValueError('live CPU binding')
            if not any(r['kind']=='start' and r.get('gen')==gen for r in events[:pos]):raise ValueError('live CPU start order')
            previous[gen]=b;charges[gen]=0
        elif kind=='cpu_charge':
            if gen in final or e['before']!=previous[gen] or now<=last.get(run,-1):raise ValueError('live CPU continuity')
            after,result=cpu.charge_result(e['before'],now)
            if e['after']!=after or type(e['result']) is not int or e['result']!=result:raise ValueError('live CPU arithmetic')
            previous[gen]=after;charges[gen]+=1;last[run]=now
        else:
            if gen in final or e['records']!=previous[gen] or now<previous[gen][3]:raise ValueError('live CPU final')
            b=e['records'];rs,status,state,total=receipts[gen]
            if rs!=slot or total!=charges[gen] or b[2]!=total:raise ValueError('live CPU receipt')
            if status==256 and (b[7]!=32 if b[4] else total!=32):raise ValueError('live CPU exhaustion')
            if not any(r['kind']=='release' and r.get('gen')==gen for r in events[pos+1:]):raise ValueError('live CPU clear order')
            final.add(gen)
    if final!=set(plan) or sum(charges.values())>2048:raise ValueError('live CPU complete ledger')

def validate(serial,trace,case,layout,oom,counts,raw,ledger,raw_cpu):
    try:
        normalized=''.join('TASK_POOL '+line[10:] if line.startswith('LIVE_FILE ') else line for line in trace.splitlines(keepends=True))
        expanded=cpu.expand_cpu_trace(normalized,ledger)
        events=[json.loads(line[10:]) for line in expanded.splitlines() if line.startswith('TASK_POOL ')]
        native_cpu_trace.validate_trace_records(trace,raw_cpu,events)
        expanded=''.join('LIVE_FILE '+line[10:] if line.startswith('TASK_POOL ') else line for line in expanded.splitlines(keepends=True))
        rows=lifecycle_validator()(serial,expanded,case,layout,oom,counts,raw)
        validate_cpu(serial,events,case)
        plan=roles(case);per=len(plan)//2
        def get(kind):return [e for e in events if e['kind']==kind]
        modes=[dict(kind='mode',gen=g,slot=0,case=case,layout=layout,before=struct.pack('<4I',1,0,2,0).hex(),after=struct.pack('<4I',1,case,layout,0).hex()) for g in (1,per+1)]
        if get('mode')!=modes:raise ValueError('live immutable case selection')
        programs=[g for g,i in plan.items() if i['role']=='program']
        if [(e['gen'],e['phase']) for e in get('live')]!=[(g-1,p) for g in programs for p in (2,3)]:raise ValueError('live complete coexistence')
        for e in get('live'):
            g=e['app'];info=plan[g]
            if e['gen']!=g-1 or e['driver']!=g-2 or e['root']!=info['root'] or len(e['states'])!=3 or any(s not in (1,2,6) for s in e['states']):raise ValueError('live bound dependencies')
            if e['phase']==3 and e['states'][2]!=6:raise ValueError('live app actually blocked')
            pos=events.index(e)
            if any(r['kind']=='release' and r.get('gen') in (g-2,g-1,g) for r in events[:pos]):raise ValueError('live premature reap')
            if e['phase']==3 and not any(r['kind']=='fs_reply' and r.get('gen')==g-1 and r.get('sequence')==len(frames(layout,raw)) for r in events[:pos]):raise ValueError('live actual concurrent STAT')
        go=[g for g in programs if case!=15]
        if get('go')!=[dict(kind='go',gen=g,root=plan[g]['root']) for g in go]:raise ValueError('live continuation')
        for e in get('go'):
            prior=next(r for r in get('live') if r['app']==e['gen'] and r['phase']==3)
            if events.index(prior)>=events.index(e):raise ValueError('live probe before continuation')
        expected=[dict(kind='oom_isolation',owner=g<<32,generation=g+3,slot=4,neighbors=2,source=266336,empty_context=1) for g in (1,per+1)] if oom is not None else []
        if get('oom_isolation')!=expected:raise ValueError('live OOM neighbor/source isolation')
        return rows
    except (AssertionError,KeyError,TypeError,StopIteration,IndexError,struct.error) as error:
        raise ValueError('malformed live file evidence: '+str(error)) from error

def image_config(image):
    core_raw=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=wide.payload.validate(core_raw)
    if core['layout_version']!=5:raise ValueError('live file core layout5')
    wide.payload.verify_outer(core_raw,wide.payload.read_bounded(image,bits=32))
    catalog=(image.parent/'boot-programs.bin').read_bytes()
    attempts=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    if len(catalog)!=4*wide.SIZE or len(attempts)!=1:raise ValueError('live unique producer binding')
    folder=attempts[0];records={}
    raw=(folder/'file-program.prg').read_bytes()
    if not 64<=len(raw)<=1280:raise ValueError('live file reserves concurrent RPC')
    for n in range(4):
        blob=(folder/f'program{n}.prg').read_bytes()
        if n==0 and raw in blob:raise ValueError('live program must come from filesystem')
        if wide.producer.prepare(blob,[f'program{n}.prg',str(n)],True)!=catalog[n*wide.SIZE:(n+1)*wide.SIZE]:raise ValueError('live exact producer record')
        if n>=2:records['driver' if n==2 else 'fs']=wide.producer.prepare(blob,[],True)
    records['program']=wide.producer.prepare(raw,[],True)
    addresses={name:file.block.map_symbol(folder/f'program{n}.map',symbol) for name,n,symbol in (
        ('selection_address',0,'live_file_selection'),('result_address',0,'live_file_record'),
        ('block_address',2,'filesystem_block_service'),('fs_address',3,'filesystem_service'))}
    counts={name:wide.allocations(record) for name,record in records.items()}
    counts['sha']={name:hashlib.sha256(record).hexdigest() for name,record in records.items()}
    return dict(s=wide.transport.symbols(image),cs={n:v['value'] for n,v in core['symbols'].items()},prepared=records['program'],**addresses),counts,raw

def observer(config,folder,case,layout,oom,raw):
    program=file.program_variant(raw,case);disk=media.image(media.LAYOUTS[layout],program=program)
    sectors={n//512:disk[n:n+512].hex() for n in range(0,len(disk),512) if any(disk[n:n+512])}
    settings=dict(config,case=case,roles=roles(case),layout=layout,oom=oom,sectors=len(disk)//512,media=sectors,
                  requests=frames(layout,program),responses=frames(layout,program,True),cpu_ledger=(folder/cpu.CPU_FILE).as_posix())
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging redirect on\nset logging enabled on\npython\nCONFIG='+repr(settings)+'\n'+observer_body()+'\nend\ncontinue\n')

def main():
    from verify_x86_64_live_file import admit_runtime,source_binding,digest,link,need,reuse_prefix
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    args.image=args.image.resolve();args.evidence=args.evidence.resolve()
    frozen=admit_runtime(args.image,args.evidence);config,counts,raw=image_config(args.image)
    prefix=reuse_prefix(frozen)
    folder=args.evidence/('attempt-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    summary=dict(passed=False,closed=False,candidate=frozen['candidate'],cases=list(prefix),
                 guest_elapsed=sum(r['elapsed'] for r in prefix),image=link(args.image),
                 reused_guests=len(prefix),new_guests=0,new_guest_elapsed=0.0)
    begin=time.monotonic()
    try:
        for case,layout,ram,point in CASES[len(prefix):]:
            source_binding();need(len(summary['cases'])<25 and summary['guest_elapsed']+45<=1125,'live guest reserve')
            need(summary['new_guests']<14 and summary['new_guest_elapsed']+45<=630,'live fresh guest reserve')
            oom=None if point is None else 0 if point=='first' else counts['program']//2 if point=='middle' else counts['program']-1
            out=folder/f'guest-{case}-{layout}-{ram}-{point}';out.mkdir()
            row=dict(case=case,layout=layout,ram=ram,point=point,oom=oom,folder=out.relative_to(ROOT).as_posix(),passed=False,executed=True)
            started=time.monotonic();summary['cases'].append(row)
            summary['new_guests']+=1
            try:
                fixture=pio.Fixture(out,filesystem=media.LAYOUTS[layout],file_program=file.program_variant(raw,case))
                code=observer(config,out,case,layout,oom,raw)
                serial,trace=wide.transport.capture(args.image,out,code,ram,fixture,binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True)
                validate(serial,trace,case,layout,oom,counts,raw,(out/cpu.CPU_FILE).read_bytes(),(out/'cpu-trace-v1.bin').read_bytes())
                reads=cpu.binary_capacity(out)
                extra=[out/cpu.CPU_FILE,out/'cpu-trace-v1.bin']
                need(len(reads)+2<=2048 and sum(r['bytes'] for r in reads)+sum(p.stat().st_size for p in extra)<=128*1024*1024,'live aggregate proof bound')
                need(digest(args.image)==summary['image']['sha256'],'live same image')
                row['passed']=True
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed']
                summary['new_guest_elapsed']+=row['elapsed']
            need(row['elapsed']<=45,'live guest deadline including cleanup')
            print('LIVE_FILE_GUEST_OK',case,layout,ram,point,round(row['elapsed'],3),flush=True)
        need(len(summary['cases'])==25 and time.monotonic()-begin<=1200,'live complete matrix')
        summary['passed']=True;return 0
    except Exception as error:
        summary['error']=str(error);print('LIVE_FILE_FAIL',error,flush=True);return 1
    finally:
        summary.update(closed=True,elapsed=time.monotonic()-begin)
        with (folder/'summary.json').open('x') as stream:json.dump(summary,stream,indent=2)
        print('LIVE_FILE_EVIDENCE',folder,flush=True)

if __name__=='__main__':raise SystemExit(main())
