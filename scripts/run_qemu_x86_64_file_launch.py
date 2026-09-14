"""Actual immutable-file execution, bounded generated media and strict evidence."""
from pathlib import Path
import argparse,ast,hashlib,json,re,struct,subprocess,sys,time,uuid
import run_qemu_x86_64_filesystem as fs
block=fs.block;wide=fs.wide;pio=fs.pio;media=fs.media;ROOT=fs.ROOT;once=fs.once

def roles(case):
    if type(case) is not int or case not in range(11):raise ValueError('file launch case')
    entries=[dict(role='root',slot=0,round=0,status=134 if case==7 else 84 if case in (4,9) else 83,state=3 if case==7 else 4),
             dict(role='peer',slot=1,round=0,status=77,state=4)]
    for n in range(1 if case==7 else 2):
        entries.append(dict(role='driver',slot=2,round=n,status=134 if not n and case==6 else 0,state=3))
        entries.append(dict(role='fs',slot=3,round=n,status=134 if not n and case==5 else 90 if not n and case==6 else 0,state=4 if not n and case==6 else 3))
        if case in (4,7,9) or not n and case in (5,6,10):continue
        status={1:134,2:256,3:0}.get(case,82) if not n else 82
        entries.append(dict(role='program',slot=2,round=n,status=status,state=4 if status==82 else 3))
    count=len(entries)
    return {run*count+n+1:dict(item,root=run*count+1) for run in range(2) for n,item in enumerate(entries)}

def program_variant(raw,case):
    if not 64<=len(raw)<=1536:raise ValueError('file executable extent')
    wide.producer.prepare(raw,[],True)
    if case==4:raw=raw[:18]+bytes([raw[18]^1])+raw[19:]
    if case==9:raw=raw+bytes(1537-len(raw))
    return raw

def frames(layout,raw,response=False):
    name=b'/BOOT.PRG' if layout<2 else b'/boot.prg';result=[]
    for position in [None,*range(0,len(raw),256),len(raw)]:
        frame=bytearray(512);op=5 if position is None else 6
        struct.pack_into('<6I',frame,0,1,512,op,0,len(name),0)
        at=24 if op==5 else 36;frame[at:at+len(name)]=name
        if op==5 and response:
            frame[216:224]=b'BOOT.PRG' if layout<2 else b'boot.prg';struct.pack_into('<2I',frame,472,1,len(raw))
        if op==6:
            requested=min(256,len(raw)-position) if position<len(raw) else 1
            data=raw[position:position+requested] if response else b''
            struct.pack_into('<3I',frame,24,position,requested,len(data));frame[228:228+len(data)]=data
        result.append(bytes(frame))
    return result

def replace_function(code,name,new,*,last=False):
    nodes=[n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name==name]
    if not nodes or not last and len(nodes)!=1:raise ValueError('function boundary '+name)
    old=ast.get_source_segment(code,nodes[-1] if last else nodes[0]);return once(code,old,new.strip())

def observer_body():
    code=once(fs.observer_body(),"'FILESYSTEM '","'FILE_LAUNCH '")
    code=replace_function(code,'user',FILE_USER_READ,last=True)
    code=once(code,'    owned=[]', '    owned=[];image_pages=[];leaves=file_leaves(t)')
    code=once(code,'pf=6 if page==8 else record[24+page];e=walk(t[2],0x400000+page*4096)',
        'pf=6 if page==8 else record[24+page];e=leaves[page]')
    code=once(code,'        actual=mem(DM+frame,4096)\n',
        '        image_pages.append((page,frame))\n    for (page,frame),actual in zip(image_pages,file_pages([frame for page,frame in image_pages])):\n')
    code=once(code,"assert all(not any(mem(DM+f,4096)) for f in r['frames'])",
        "assert all(not any(raw) for raw in file_pages(r['frames']))")
    code=once(code,'PER_RUN=4 if CASE==6 else 6',"PER_RUN=len(CONFIG['roles'])//2")
    code=once(code,'len(copies)<8','len(copies)<12')
    first=code.index('    argc=2\n');end=code.index('    # No uninitialized',first)
    code=code[:first]+'''    info=CONFIG['roles'][gen];assert slot==info['slot']
    argc=3 if info['role']=='program' else 2
    values=struct.unpack('<'+'Q'*(argc+7),user(t,t[69],(argc+7)*8));assert values[0]==argc and values[argc+1:]==(0,0,0x52534901,0,0,0)
    args=[user(t,p,128).split(b'\\0')[0] for p in values[1:argc+1]]
    if slot<2:assert args==[('program%d.prg'%slot).encode(),str(slot).encode()]
    else:
        channel=args[1] if info['role']=='program' else args[0]
        assert len(channel)==8 and all(ch in b'0123456789abcdef' for ch in channel) and int(channel,16)>0
        if info['role']=='program':
            assert args[0]==b'/boot.prg' and args[2]==str(CASE if not info['round'] and CASE<=3 else 0).encode()
        else:
            option=16 if info['round'] else {5:1,6:5,7:6,10:4}.get(CASE,0)
            assert args[1]==('%08x'%option).encode()
'''+code[end:]
    code=once(code,"allocation_slot==3", "allocation_slot==2 and CONFIG['roles'][d(S['process_run_generation'])+1]['role']=='program'")
    for name,old,new in (
        ('create_begin','    allocator.enabled=True','    allocator.enabled=True\n    file_oom_begin()'),
        ('allocation','    global allocation_count','    global allocation_count\n    assert image_retirement is None or image_retirement[\'phase\']==\'done\''),
        ('create_end','    created=None','    file_oom_finish()\n    created=None')):
        node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name==name)
        original=ast.get_source_segment(code,node)
        code=replace_function(code,name,once(original,old,new))
    code=once(code,"create_watch_leave(reg('rax')==0xfffffffffffffff4 or reg('rax')&0xffffffff==2)",
        "create_watch_leave(reg('rax')==0xfffffffffffffff4 or CONFIG['roles'][reg('rax')>>32]['role']=='driver')")
    code=once(code,"r['slot']==2 and CASE!=6 and (r['gen']-3)%PER_RUN==0",
        "r['slot']==2 and CASE!=7 and d(S['process_run_generation'])%PER_RUN!=0")
    code=once(code,"    trace_drain();v=pstate()", "    caller_result();trace_drain();v=pstate()")
    code=once(code,"    if slot==3 and CASE==3 and (gen-4)%PER_RUN==0:cancel_watch([gen-1])",
        "    if CONFIG['roles'][gen]['role']=='program':return")
    code=once(code,"    assert length<=size-12 and not any(raw[12+length:])",
        "    assert length<=size-12 and not any(raw[12+length:])\n    if (version,length)==(1,16):program_ready(slot,t,gen,raw);return")
    code=once(code,"                if CASE==8 and result:cancel_watch([gen-1])", "                if result:assert CASE==6 and not CONFIG['roles'][gen]['round']")
    code=once(code,"else:assert slot==2 and CASE==6 and phase==9", "else:assert slot==2 and CASE==7 and phase==9")
    code=once(code,'1<=sequence<=9',"1<=sequence<=len(CONFIG['requests'])")
    code=once(code,"        if CASE==2 and ((owner>>32)-4)%PER_RUN==0:cancel_watch([(owner>>32)-1,owner>>32])",'')
    code=once(code,"bad=CASE==4 and (gen-4)%PER_RUN==0", "bad=CASE==10 and not CONFIG['roles'][gen]['round']")
    code=once(code,"assert h[9]==(1 if sequence==6 else -2 if sequence==7 else -11 if sequence==9 else 0)","assert h[9]==0")
    code=once(code,"emit('fs_reply',gen=gen,sequence=sequence,status=h[9],bad=int(bad))",
        "emit('fs_reply',gen=gen,sequence=sequence,status=h[9],bad=int(bad),sha=hashlib.sha256(raw[76:588]).hexdigest())")
    code=once(code,"        if sequence==9 or bad:cancel_watch([gen-1,gen] if bad else [gen-1])",
        "        if sequence==len(CONFIG['requests']) or bad or CASE==9:cancel_watch([gen-1,gen])")
    for name in ('caller_result','fault'):
        node=next(n for n in ast.parse(EXTRA).body if isinstance(n,ast.FunctionDef) and n.name==name)
        code=replace_function(code,name,ast.get_source_segment(EXTRA,node))
    tail=EXTRA[EXTRA.index('def program_ready'):]
    return code+tail+FILE_RAM_BATCH+FILE_OOM_RETIREMENT

FILE_OOM_RETIREMENT=r'''
image_retirement=None

def file_oom_begin():
    global image_retirement
    assert image_retirement is None
    assert not any(h.enabled for h in (image_retire_hook,image_retire_free_hook,image_retire_end_hook))
    if OOM is None or allocation_slot!=2 or allocation_owner in injected:return
    generation=d(S['process_run_generation']);info=CONFIG['roles'][generation+1]
    if info['role']!='program':return
    assert CASE==8 and not info['round'] and allocation_owner==info['root']<<32
    image_retirement=dict(phase='armed',generation=generation,owner=allocation_owner,before=allocation_before)
    image_retire_hook.enabled=True

def image_retire_begin():
    r=image_retirement
    assert r is not None and r['phase']=='armed' and created and not reg('eflags')&512
    assert mode()==8 and d(S['family_request'])==5 and d(S['family_build_slot'])==2
    assert mem(S['elf_image_selector'],1)==b'\x07' and free()==r['before'] and allocation_count==0
    gen=r['generation']-1;old=starts[gen];info=CONFIG['roles'][gen]
    assert info['role']=='driver' and info['root']<<32==r['owner'] and old['slot']==2 and not old['live']
    raw=mem(S['elf_context_window'],592);assert len(raw)==592 and raw[583]==1
    frames=struct.unpack('<64Q',raw[:512]);flags=raw[512:576]
    assert flags==old['record'][24:88] and all(f in (0,4,5,6) for f in flags)
    assert all(bool(f)==bool(flag) for f,flag in zip(frames,flags))
    owned=[f for f in frames if f]
    assert 0<len(owned)<=64 and len(set(owned))==len(owned)
    assert all(0x100000000<=f<=MASK and not f&4095 for f in owned)
    r.update(phase='release',gen=gen,frames=owned,freed=[])
    image_retire_hook.enabled=False;image_retire_free_hook.enabled=True;image_retire_end_hook.enabled=True

def image_retire_free():
    r=image_retirement
    assert r is not None and r['phase']=='release' and allocation_count==0
    index=len(r['freed']);assert index<len(r['frames']) and reg('rdi')==r['frames'][index]
    r['freed'].append(reg('rdi'))

def image_retire_end():
    global allocation_before
    r=image_retirement
    assert r is not None and r['phase']=='release' and allocation_count==0 and not reg('eflags')&512
    assert r['freed']==r['frames'] and free()==r['before']+len(r['frames'])
    assert mem(S['elf_image_selector'],1)==b'\x07' and d(S['family_initial_free'])==free()
    raw=mem(S['elf_context_window'],592)
    assert len(raw)==592 and not any(raw[:576]) and not any(raw[580:])
    assert all(not any(page) for page in file_pages(r['frames']))
    image_retire_free_hook.enabled=False;image_retire_end_hook.enabled=False
    allocation_before=free();r['phase']='done'
    emit('image_retire',owner=r['owner'],gen=r['gen'],slot=2,frames=len(r['frames']),before=r['before'],after=allocation_before,scrub=1)

def file_oom_finish():
    global image_retirement
    r=image_retirement
    if r is None:return
    assert r['phase']=='done' and reg('rax')==0xfffffffffffffff4 and r['owner'] in injected
    assert d(S['process_run_generation'])==r['generation'] and r['generation']+1 not in copies
    assert not any(h.enabled for h in (image_retire_hook,image_retire_free_hook,image_retire_end_hook))
    image_retirement=None

image_retire_hook=Hook('x86_64_elf64_release64',image_retire_begin);image_retire_hook.enabled=False
image_retire_free_hook=Hook('physical_frame_free64',image_retire_free);image_retire_free_hook.enabled=False
image_retire_end_hook=Hook('family_create64.cached_entry',image_retire_end);image_retire_end_hook.enabled=False
'''

FILE_RAM_BATCH=r'''
def file_leaves(t):
    # The fixed 0x400000..0x43ffff native image shares three parent entries.
    # Read every leaf, including absent ones; no state survives this stop.
    root=t[2]
    for shift in (39,30,21):
        e=q(DM+root+((0x400000>>shift)&511)*8)
        assert e&1 and not e&128
        root=e&MASK
    raw=mem(DM+root,64*8);assert len(raw)==64*8
    return struct.unpack('<64Q',raw)

def file_pages(frames):
    # Only validated physical RAM, never device memory or gaps. Preserve the
    # caller's order and every byte, with bounded contiguous wire transfers.
    assert len(frames)<=69 and all(type(f)==int and 0x100000000<=f<=MASK and not f&4095 for f in frames)
    assert len(set(frames))==len(frames)
    ordered=sorted(frames);pages={};index=0
    while index<len(ordered):
        end=index+1
        while end<len(ordered) and end-index<66 and ordered[end]==ordered[end-1]+4096:end+=1
        size=(end-index)*4096;raw=mem(DM+ordered[index],size);assert len(raw)==size
        for n in range(index,end):pages[ordered[n]]=raw[(n-index)*4096:(n-index+1)*4096]
        index=end
    return [pages[f] for f in frames]
'''

FILE_USER_READ=r'''
def user(t,va,n):
    # One paused read only. Fetch the exact needed entry span in each table,
    # then validate EVERY requested entry; tiny reads must not fetch16KiB.
    assert type(n)==int and 0<=n<=266336 and type(va)==int and 0<=va<1<<64 and n<=(1<<64)-va
    pages={};ranges=[]
    def entry(address,shift):
        base=address&~4095
        index=(address-base)//8
        if base not in pages:
            assert len(pages)<8
            count=min(512-index,((va+n-1)>>shift)-(va>>shift)+1)
            assert 1<=count<=512
            raw=mem(address,count*8);assert len(raw)==count*8
            pages[base]=(index,raw)
        first,raw=pages[base];offset=(index-first)*8
        assert 0<=offset<=len(raw)-8
        return struct.unpack_from('<Q',raw,offset)[0]
    while n:
        root=t[2]
        for shift in (39,30,21):
            e=entry(DM+root+((va>>shift)&511)*8,shift)
            assert e&1 and not e&128
            root=e&MASK
        e=entry(DM+root+((va>>12)&511)*8,12);assert e&5==5
        count=min(n,4096-(va&4095));address=DM+(e&MASK)+(va&4095)
        if ranges and ranges[-1][0]+ranges[-1][1]==address:ranges[-1][1]+=count
        else:ranges.append([address,count])
        va+=count;n-=count
    return b''.join(mem(a,size) for a,size in ranges)
'''

EXTRA=r'''
def caller_result():
    root=task(0)
    if mode()!=8 or root[0] not in (1,2,6):return
    magic,owner,status,address,workspace,driver,round_=struct.unpack('<7Q',user(root,CONFIG['result_address'],56))
    if magic!=0x46494c4550525032 or owner in results:return
    gen=owner>>32;info=CONFIG['roles'][gen]
    assert info['role']=='fs' and info['root']==root[1] and info['round']==round_ and owner&0xffffffff==3
    assert driver==((gen-1)<<32)|2
    if status>=1<<63:status-=1<<64
    expected=-22 if CASE==4 else -27 if CASE==9 else -71 if CASE==10 and not round_ else None if CASE in (5,6) and not round_ else 0
    if expected is None:assert status<0
    else:assert status==expected
    if CASE==5 and not round_:assert status in (-32,-110)
    actual=user(root,address,266336)
    assert actual==(b'\xa5'*266336 if status else CONFIG['prepared'])
    raw=user(root,workspace,2048)+user(root,workspace+2048,266336)
    assert raw==(b'\x5a'*268384 if CASE==6 and not round_ else bytes(268384))
    results.add(owner);emit('file_result',gen=gen,caller=root[1],status=status,sha=hashlib.sha256(actual).hexdigest(),scrub=int(not any(raw)))

def fault():
    trace_drain();slot=d(S['scheduler_current_slot']);gen=task(slot)[1];info=CONFIG['roles'][gen]
    f=struct.unpack('<22Q',mem(reg('rdi'),176))
    assert CASE in (1,5,6,7) and slot=={1:2,5:3,6:2,7:0}[CASE] and not info['round']
    assert f[15:17]==(6,0) and f[18]==0x33
    assert info['role']=={1:'program',5:'fs',6:'driver',7:'root'}[CASE]
    emit('fault',gen=gen,slot=slot,vector=6)
    if CASE==5:cancel_watch([gen-1])
    if CASE==7:cancel_watch([gen+2,gen+3])

def program_ready(slot,t,gen,raw):
    info=CONFIG['roles'][gen]
    assert slot==2 and info['role']=='program' and gen not in proofs
    assert raw[12:28]==struct.pack('<Q',gen)+b'ELF64RO!'
    assert gen in copies and copies[gen]==CONFIG['prepared']
    assert user(task(0),created_sources[gen],266336)==b'\x5a'*266336
    assert not any(mem(S['family_extended_masks']+slot*16,16))
    record=copies[gen]
    for page in range(64):
        if record[24+page] in (4,5):assert user(t,0x400000+page*4096,4096)==record[96+page*4096:96+(page+1)*4096]
    proofs.add(gen);emit('program_ready',gen=gen,slot=slot,source=266336,device=0,sha=hashlib.sha256(record).hexdigest())
    if CASE==3 and not info['round']:cancel_watch([gen])
'''

def _validate(serial,trace,case,layout,oom,counts,raw):
    plan=roles(case);per=len(plan)//2;image=program_variant(raw,case)
    if layout not in range(5) or (oom is not None)!=(case==8):raise ValueError('file selectors')
    common=[m for m in wide.transport.REQUIRED_MARKERS if 'SHELL' not in m]+[wide.process.SUCCESS]
    if any(m in serial for m in wide.transport.FAILURES) or 'OBSERVER_FAIL' in trace:raise ValueError('file kernel/observer failure')
    if any(serial.count(m)!=1 for m in common) or [serial.index(m) for m in common]!=sorted(serial.index(m) for m in common):raise ValueError('file kernel progress')
    matches=list(wide.process.REAP.finditer(serial));ends=list(re.finditer(wide.process.DONE,serial));rows=[]
    if len(matches)!=len(plan) or serial.count('PROCESS_REAP_OK')!=len(plan) or len(ends)!=2:raise ValueError('file complete receipt count')
    if ends[-1].end()>serial.index('REIST_X86_64_C_KERNEL_CONTROL_OK'):raise ValueError('file caller return order')
    for match in matches:
        slot,gen,status,state,ticks,rip=struct.unpack('<4I2Q',bytes.fromhex(match[1]));info=plan.get(gen);run=(gen-1)//per
        if info is None or gen in [r[1] for r in rows] or (slot,status,state)!=(info['slot'],info['status'],info['state']):raise ValueError('file outcome '+str((slot,gen,status,state,ticks)))
        if ticks>32 or not 0x410000<=rip<0x440000 or status==256 and ticks!=32:raise ValueError('file CPU/instruction bound')
        if not (ends[run-1].end() if run else -1)<match.start()<match.end()<=ends[run].start():raise ValueError('file receipt order')
        rows.append((slot,gen))
    events=[json.loads(line[12:]) for line in trace.splitlines() if line.startswith('FILE_LAUNCH ')]
    allowed={'poison','boot','start','copy','create','release','finish','oom','rollback','image_retire','fault','cancel','bind','immutable','driver_ready','fs_ready','block_request','block_reply','fs_request','fs_reply','retire','trace_drained','trace_clean','file_result','program_ready'}
    if any(e['kind'] not in allowed for e in events):raise ValueError('file unknown event')
    def get(kind):return [e for e in events if e['kind']==kind]
    def gens(kind):return [e['gen'] for e in get(kind)]
    children=[g for g,i in plan.items() if i['slot']>=2];drivers=[g for g,i in plan.items() if i['role']=='driver'];parsers=[g for g,i in plan.items() if i['role']=='fs'];programs=[g for g,i in plan.items() if i['role']=='program']
    if get('poison')!=[dict(kind='poison',bytes=270336)] or get('boot')!=[dict(kind='boot',catalog=261,scratch=66,reserved=2887,zero=1,aliases=0)]:raise ValueError('file boot proof')
    if len(get('start'))!=len(plan) or {(e['slot'],e['gen']) for e in get('start')}!=set(rows):raise ValueError('file starts')
    if [(e['slot'],e['gen']) for e in get('release')]!=rows:raise ValueError('file releases')
    for e in get('release'):
        if not 0<e['frames']<=69 or e['fenced']!=1 or not 0<e['before']<e['after']==e['before']+e['frames']<=4194304:raise ValueError('file frame balance')
    for kind in ('copy','create'):
        if gens(kind)!=children:raise ValueError('file '+kind+' generations')
        for e in get(kind):
            role=plan[e['gen']]['role']
            if kind=='copy' and (e['bytes']!=266336 or e['sha']!=counts['sha'][role]):raise ValueError('file copied ELF bytes')
            if kind=='create' and e['acquired']!=counts[role]:raise ValueError('file allocation count')
    for kind,expected in (('bind',drivers),('retire',drivers),('driver_ready',drivers),('immutable',[g for g in children if g not in programs]),('fs_ready',[] if case==7 else parsers),('program_ready',programs),('file_result',[] if case==7 else parsers)):
        if gens(kind)!=expected:raise ValueError('file '+kind+' sequence')
    for e in get('immutable')+get('program_ready'):
        if (e['slot'],e['source'],e['device'])!=(plan[e['gen']]['slot'],266336,int(e['gen'] in drivers)):raise ValueError('file explicit rights/immutability')
        if e['kind']=='program_ready' and e['sha']!=counts['sha']['program']:raise ValueError('file executed bytes')
    disk=media.image(media.LAYOUTS[layout],program=image);sectors=len(disk)//512
    for e in get('bind'):
        if e['owner']!=(e['gen']<<32)|2:raise ValueError('file device owner')
    for e in get('driver_ready'):
        if e['peer']!=((e['gen']+1)<<32)|3 or e['capacity']!=sectors or not 0<e['deadline']<1<<64:raise ValueError('file driver self-test')
    for e in get('fs_ready'):
        bad=case==6 and not plan[e['gen']]['round']
        if (e['status']<0)!=bad or not bad and e['status'] or e['peer']!=((e['gen']-1)<<32)|2:raise ValueError('file FS self-test')
        if e['cached']!=(0 if bad else 1 if layout<2 else 4):raise ValueError('file FS cache')
    for e in get('retire'):
        if e['identify']!=512 or e['fenced']!=1 or not e['lbas'] or e['lbas'][0]!=0 or len(e['lbas'])>17:raise ValueError('file physical admission')
        if any(type(lba)!=int or not 0<=lba<sectors for lba in e['lbas']):raise ValueError('file LBA extent')
        expected=b''.join(disk[lba*512:(lba+1)*512] for lba in e['lbas']);partial=case in (6,7) and not plan[e['gen']]['round']
        size=768 if partial else len(expected)
        if e['data']!=size or e['sha']!=hashlib.sha256(expected[:size]).hexdigest():raise ValueError('file physical bytes')
        requests=[r for r in get('block_request') if r['gen']==e['gen']];replies=[r for r in get('block_reply') if r['gen']==e['gen']]
        if [r['sequence'] for r in requests]!=list(range(1,len(requests)+1)) or [r['lba'] for r in requests]!=e['lbas'][1:] or any(r['client']!=e['gen']+1 for r in requests):raise ValueError('file block requests')
        if len(replies)!=len(requests)-int(partial):raise ValueError('file block reply count')
        for request,reply in zip(requests,replies):
            data=disk[request['lba']*512:(request['lba']+1)*512]
            if (reply['sequence'],reply['lba'],reply['sha'])!=(request['sequence'],request['lba'],hashlib.sha256(data).hexdigest()):raise ValueError('file block reply bytes')
    canonical=frames(layout,image);responses=frames(layout,image,True)
    for gen in parsers:
        first=not plan[gen]['round'];n=0 if case==7 or case==6 and first else 1 if case==9 or case in (5,10) and first else len(canonical)
        requests=[e for e in get('fs_request') if e['gen']==gen];replies=[e for e in get('fs_reply') if e['gen']==gen]
        if [e['sequence'] for e in requests]!=list(range(1,n+1)):raise ValueError('file FS request count')
        for i,e in enumerate(requests):
            if e['op']!=struct.unpack_from('<I',canonical[i],8)[0] or e['sha']!=hashlib.sha256(canonical[i]).hexdigest():raise ValueError('file canonical RPC')
        nr=0 if case==5 and first else n
        if [e['sequence'] for e in replies]!=list(range(1,nr+1)) or any(e['status'] or e['bad']!=int(case==10 and first) for e in replies):raise ValueError('file FS reply count/status')
        if any(e['sha']!=hashlib.sha256(responses[i]).hexdigest() for i,e in enumerate(replies)):raise ValueError('file FS reply data')
    for e in get('file_result'):
        first=not plan[e['gen']]['round'];expected=-22 if case==4 else -27 if case==9 else -71 if case==10 and first else None if case in (5,6) and first else 0
        if e['caller']!=plan[e['gen']]['root'] or (e['status']!=expected if expected is not None else e['status']>=0):raise ValueError('file capture result')
        if case==5 and first and e['status'] not in (-32,-110):raise ValueError('file FS fault result')
        digest=hashlib.sha256(b'\xa5'*266336).hexdigest() if e['status'] else counts['sha']['program']
        if e['sha']!=digest or e['scrub']!=int(not (case==6 and first)):raise ValueError('file staged output/scrub')
    faults=[g for g,i in plan.items() if i['status']==134]
    if gens('fault')!=faults or any(e['vector']!=6 or e['slot']!=plan[e['gen']]['slot'] for e in get('fault')):raise ValueError('file exact faults')
    cancelled=[g for g,i in plan.items() if i['slot']>=2 and i['status']==0]
    if len(get('cancel'))!=len(cancelled) or set(gens('cancel'))!=set(cancelled) or any(e['state'] not in (1,6) or e['slot']!=plan[e['gen']]['slot'] for e in get('cancel')):raise ValueError('file exact cancel')
    for kind in ('oom','rollback'):
        es=get(kind);expected=[(1<<32,oom),((per+1)<<32,oom)] if oom is not None else []
        if [(e['owner'],e['acquired']) for e in es]!=expected or kind=='rollback' and any(e['free']!=e['before'] for e in es):raise ValueError('file OOM rollback')
    retired=get('image_retire');expected=[(root<<32,root+2) for root in (1,per+1)] if oom is not None else []
    if [(e['owner'],e['gen']) for e in retired]!=expected:raise ValueError('file OOM retired image identity')
    for e,failed,rolled in zip(retired,get('oom'),get('rollback')):
        if e['slot']!=2 or e['scrub']!=1 or not 0<e['frames']<=64 or not 0<e['before']<e['after']==e['before']+e['frames']<=4194304 or rolled['before']!=e['after']:raise ValueError('file OOM retirement balance')
        release=next(p for p in get('release') if p['gen']==e['gen'])
        copied=next(p for p in get('copy') if p['gen']==e['gen']+2)
        if not events.index(release)<events.index(e)<events.index(failed)<events.index(rolled)<events.index(copied):raise ValueError('file OOM transaction order')
    if any(len(get(k))!=2 for k in ('finish','trace_drained','trace_clean')):raise ValueError('file final cleanup count')
    for run,(end,drain,clean) in enumerate(zip(get('finish'),get('trace_drained'),get('trace_clean')),1):
        if (end['run'],end['tasks'],end['generation'])!=(run,per,run*per) or not 0<end['free']==end['initial']<=4194304:raise ValueError('file final free balance')
        if drain['run']!=run or not 0<drain['events']<=4096 or not re.fullmatch('[0-9a-f]{64}',drain['sha']) or clean!=dict(kind='trace_clean',run=run,bytes=12304):raise ValueError('file final trace')
    def position(kind,gen):return next(i for i,e in enumerate(events) if e['kind']==kind and e.get('gen')==gen)
    for gen,info in plan.items():
        first=position('start',gen);last=position('release',gen)
        if first>=last:raise ValueError('file start/retire order')
        if info['slot']>=2:
            if not position('copy',gen)<position('create',gen)<first:raise ValueError('file copy/publication order')
            proof='program_ready' if info['role']=='program' else 'immutable'
            before=first if proof=='program_ready' else position('create',gen)
            if not before<position(proof,gen)<last:raise ValueError('file immutable lifetime')
        if info['role']=='driver' and not position('retire',gen)<last:raise ValueError('file fence/retire order')
        if info['role']=='driver' and not position('bind',gen)<position('driver_ready',gen)<position('retire',gen):raise ValueError('file physical lifecycle')
        if gen in cancelled and not first<position('cancel',gen)<last:raise ValueError('file cancellation lifetime')
        if gen in faults and not first<position('fault',gen)<last:raise ValueError('file fault lifetime')
        if info['role']=='program':
            for kind,g in (('file_result',gen-1),('release',gen-1),('release',gen-2)):
                if position(kind,g)>=position('copy',gen):raise ValueError('file dependency before execution')
        if info['role']=='fs' and case!=7:
            p=position('file_result',gen);root=info['root']
            if not position('start',root)<p<position('release',root):raise ValueError('file caller lifetime')
        for kind in ('block_request','block_reply','fs_request','fs_reply'):
            for index,e in enumerate(events):
                if e['kind']!=kind or e.get('gen')!=gen:continue
                if not first<index<last:raise ValueError('file RPC outside generation')
                earlier='block_request' if kind=='block_reply' else 'fs_request' if kind=='fs_reply' else None
                if earlier:
                    previous=[i for i,p in enumerate(events) if p['kind']==earlier and p.get('gen')==gen and p.get('sequence')==e['sequence']]
                    if len(previous)!=1 or previous[0]>=index:raise ValueError('file RPC causal order')
    return rows

def validate(*args):
    try:return _validate(*args)
    except (KeyError,TypeError,StopIteration,struct.error) as error:raise ValueError('malformed file evidence: '+str(error)) from error

def observer(symbols,core,folder,case,layout,oom,addresses,raw):
    program=program_variant(raw,case);disk=media.image(media.LAYOUTS[layout],program=program)
    sectors={n//512:disk[n:n+512].hex() for n in range(0,len(disk),512) if any(disk[n:n+512])}
    config=dict(s=symbols,cs={n:v['value'] for n,v in core['symbols'].items()},case=case,roles=roles(case),layout=layout,oom=oom,sectors=len(disk)//512,media=sectors,
        requests=frames(layout,program),responses=frames(layout,program,True),prepared=wide.producer.prepare(raw,[],True),**addresses)
    return ('set breakpoint always-inserted on\nset logging file '+(folder/'frame-trace.log').as_posix()+
        '\nset logging overwrite on\nset logging enabled on\npython\nCONFIG='+repr(config)+'\n'+observer_body()+'\nend\ncontinue\n')

def capture(image,folder,code,ram,fixture):
    """Use bounded binary reads and one log sink only in this file profile."""
    code=once(code,'set logging enabled on\n','set logging redirect on\nset logging enabled on\n')
    return wide.transport.capture(image,folder,code,ram,fixture,binary_memory='full')

NATIVE_CACHE=ROOT/'build/codex-agent/r83am-file-launch/native-build-reuse/catalog.json'
NATIVE_CACHE_SHA256='2d1b0e679afff17715c107651e2f83ebb1e65188ff92ffcc29d2f66b23f52ade'
NATIVE_CACHE_KEYS=frozenset([(0,n) for n in (0,1,3,4)]+[(n,2) for n in range(1,9)])
# One reviewed installation link, not a general symlink allowance.
NATIVE_TOOL_ALIASES={Path('C:/Users/oe3sr/AppData/Local/Microsoft/WinGet/Links/make.EXE'):
    (Path('C:/Users/oe3sr/AppData/Local/Microsoft/WinGet/Packages/ezwinports.make_Microsoft.Winget.Source_8wekyb3d8bbwe/bin/make.exe'),
     'cc6dc291113dcbcc7735835acbfc23c52ed037e4e124ff2d7a0aeae6df563a9f')}


def admit_native_builds(root,catalog):
    """Read-only admission; neither a successful compile nor a guest verdict."""
    from qualify_x86_64_reference_renewal import check_hashes,need,legacy
    need(isinstance(catalog,dict) and set(catalog)=={'version','profile','source_inputs','tools_sha256','entries','source_proof','runtime_accepted'},'native cache schema')
    need(type(catalog['version']) is int and catalog['version']==1 and catalog['profile']=='native-file-launch-v1'
         and catalog['runtime_accepted'] is False and isinstance(catalog['source_proof'],dict),'native cache profile')
    check_hashes(root,catalog['source_inputs'])
    tools=catalog['tools_sha256'];need(isinstance(tools,dict) and 0<len(tools)<=32,'native cache tool capacity')
    for name,sha in tools.items():
        need(isinstance(name,str) and isinstance(sha,str) and re.fullmatch('[0-9a-f]{64}',sha),'native cache tool record')
        path=Path(name)
        if path in NATIVE_TOOL_ALIASES:
            target,pinned=NATIVE_TOOL_ALIASES[path]
            def link_identity():
                info=path.lstat()
                return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns,getattr(info,'st_birthtime_ns',None))
            before=link_identity()
            need(path.is_absolute() and path.is_symlink() and not path.is_junction() and path.resolve()==target,'native cache tool alias')
            need(target.is_absolute() and target.resolve()==target and not target.is_symlink() and not target.is_junction(),'native cache tool target')
            need(sha==pinned and legacy.guard.digest(target)==pinned and legacy.guard.digest(path)==pinned,'native cache tool alias bytes')
            need(path.is_symlink() and path.resolve()==target and link_identity()==before,'native cache tool alias changed')
            continue
        need(path.is_absolute() and path.resolve()==path and not path.is_symlink() and not path.is_junction(),'native cache tool path')
        need(legacy.guard.digest(path)==sha,'native cache tool drift')
    rows=catalog['entries'];need(isinstance(rows,list) and len(rows)==len(NATIVE_CACHE_KEYS),'native cache variant count')
    result={}
    for row in rows:
        need(isinstance(row,dict) and set(row)=={'case','layout','image','artifacts','prior_build_log','runtime_accepted'},'native cache entry schema')
        need(type(row['case']) is int and type(row['layout']) is int and row['runtime_accepted'] is False,'native cache entry profile')
        key=(row['case'],row['layout']);need(key in NATIVE_CACHE_KEYS and key not in result,'native cache duplicate/profile')
        artifacts=row['artifacts'];need(isinstance(artifacts,dict) and 2<=len(artifacts)<=200,'native cache artifact capacity')
        check_hashes(root,artifacts)
        image=row['image'];need(isinstance(image,str) and image in artifacts,'native cache image binding')
        image_path=Path(image);base=image_path.parent.parent
        need(base.is_relative_to(Path('build')) and image_path.parent.name=='x86_64' and image_path.name=='reist-x86_64-bootstrap.elf','native cache image profile')
        need(all(Path(n).is_relative_to(base) for n in artifacts),'native cache output scope')
        receipt=row['prior_build_log'];need(isinstance(receipt,dict) and set(receipt)=={'path','sha256'},'native cache build receipt')
        need(receipt['path']==(base/'build.log').as_posix() and artifacts.get(receipt['path'])==receipt['sha256'],'native cache log binding')
        need((root/image).stat().st_size>0 and (root/receipt['path']).stat().st_size>0,'native cache empty artifact')
        result[key]=root/image
    need(set(result)==NATIVE_CACHE_KEYS,'native cache incomplete profiles')
    return result


def native_build_cache(*,required=False):
    from qualify_x86_64_reference_renewal import source_digest,read_json,need
    if not (NATIVE_CACHE.exists() or NATIVE_CACHE.is_symlink() or NATIVE_CACHE.is_junction()):
        need(not required,'native build catalog missing');return {}
    need(NATIVE_CACHE.resolve()==NATIVE_CACHE and NATIVE_CACHE.stat().st_size<=1048576,'native build catalog scope/size')
    need(source_digest(NATIVE_CACHE)==NATIVE_CACHE_SHA256,'native build catalog pin')
    catalog=read_json(NATIVE_CACHE);result=admit_native_builds(ROOT,catalog)
    need(source_digest(NATIVE_CACHE)==NATIVE_CACHE_SHA256,'native build catalog changed')
    return result


def main():
    if sys.argv[1:]==['--check-builds']:
        cached=native_build_cache(required=True)
        print('NATIVE_BUILDS_REUSED variants='+str(len(cached))+' new_builds=0 guests=0 runtime_accepted=false');return 0
    parser=argparse.ArgumentParser();parser.add_argument('--image',type=Path,required=True);parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    reference_image=args.image.resolve();base=args.evidence.absolute()
    if not reference_image.is_relative_to(ROOT/'build') or base!=base.resolve() or not base.is_relative_to(ROOT/'build/codex-agent') or base==ROOT/'build/codex-agent':raise ValueError('file evidence scope')
    cached=native_build_cache()
    base.mkdir(parents=True,exist_ok=True);pio.safe_folder(base);folder=base/('attempt-'+uuid.uuid4().hex);folder.mkdir()
    begin=time.monotonic();total=0;summary=dict(passed=False,cases=[],attempts=[],builds_reused=[]);builds={};reference=None
    matrix=[(0,n,4096,None) for n in range(5)]+[(0,2,8192,None)]+[(c,2,4096,None) for c in (1,2,3,4,5,6,7)]+[(8,2,4096,p) for p in ('first','middle','last')]+[(c,2,4096,None) for c in (9,10)]
    try:
        for case,layout,ram,point in matrix:
            key=(case,layout)
            if key not in builds:
                if key==(0,2):image=args.image
                elif key in cached:
                    image=cached[key];print('FILE_LAUNCH_BUILD_REUSED',case,layout,flush=True)
                    summary['builds_reused'].append(dict(case=case,layout=layout,image=str(image.relative_to(ROOT)),catalog_sha256=NATIVE_CACHE_SHA256))
                else:
                    out=folder/f'build-{case}-{layout}';out.mkdir()
                    with (out/'build.log').open('wb') as log:
                        result=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1','-NativeFileLaunch','-FileLaunchCase',str(case),'-FilesystemLayout',str(layout),'-OutputDirectory',out.relative_to(ROOT).as_posix()],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    if result.returncode:raise ValueError('file fixture build')
                    image=out/'x86_64/reist-x86_64-bootstrap.elf'
                inner=wide.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf');core=wide.payload.validate(inner);wide.payload.verify_outer(inner,wide.payload.read_bounded(image,bits=32))
                mechanisms={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in image.parent.glob('*.o') if f.name!='elf64_loader.o'}
                if reference is not None and reference!=mechanisms:raise ValueError('file mechanism drift')
                reference=mechanisms;catalog=(image.parent/'boot-programs.bin').read_bytes()
                candidates=[p for p in image.parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
                if len(catalog)!=4*wide.SIZE or not candidates:raise ValueError('file producer provenance')
                producer=candidates[0];raw=(producer/'file-program.prg').read_bytes();wide.producer.prepare(raw,[],True)
                if raw in (producer/'program0.prg').read_bytes():raise ValueError('file program embedded in supervisor')
                records={}
                for n in range(4):
                    prepared=wide.producer.prepare((producer/f'program{n}.prg').read_bytes(),[f'program{n}.prg',str(n)],True)
                    if prepared!=catalog[n*wide.SIZE:(n+1)*wide.SIZE]:raise ValueError('file producer bytes')
                    if n>=2:records['driver' if n==2 else 'fs']=wide.producer.prepare((producer/f'program{n}.prg').read_bytes(),[],True)
                records['program']=wide.producer.prepare(raw,[],True);counts={n:wide.allocations(record) for n,record in records.items()}
                counts['sha']={n:hashlib.sha256(record).hexdigest() for n,record in records.items()}
                addresses={name:block.map_symbol(producer/f'program{n}.map',symbol) for name,n,symbol in (
                    ('result_address',0,'file_launch_record'),('block_address',2,'filesystem_block_service'),('fs_address',3,'filesystem_service'))}
                builds[key]=(image,core,wide.transport.symbols(image),counts,addresses,raw)
            image,core,symbols,counts,addresses,raw=builds[key]
            oom=None if point is None else 0 if point=='first' else counts['program']//2 if point=='middle' else counts['program']-1
            out=folder/f'guest-{case}-{layout}-{ram}-{point}';out.mkdir();fixture=pio.Fixture(out,filesystem=media.LAYOUTS[layout],file_program=program_variant(raw,case))
            started=time.monotonic();trial=dict(case=case,layout=layout,ram=ram,oom=oom,passed=False,folder=str(out.relative_to(ROOT)))
            try:serial,trace=capture(image,out,observer(symbols,core,out,case,layout,oom,addresses,raw),ram,fixture)
            finally:
                elapsed=time.monotonic()-started;total+=elapsed;trial['elapsed']=round(elapsed,3);summary['attempts'].append(trial)
            if elapsed>20 or total>360:raise ValueError('file guest deadline')
            rows=validate(serial,trace,case,layout,oom,counts,raw);trial['passed']=True
            summary['cases'].append(dict(case=case,layout=layout,ram=ram,oom=oom,tasks=len(rows),elapsed=round(elapsed,3),image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),file_sha256=hashlib.sha256(raw).hexdigest()))
            print('FILE_LAUNCH_GUEST_OK',case,layout,ram,oom,flush=True)
        summary.update(passed=True,mechanisms=reference)
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.TimeoutExpired) as error:
        summary['error']=str(error);print('FILE_LAUNCH_FAIL',error);return 1
    finally:
        summary.update(elapsed=round(time.monotonic()-begin,3),guest_elapsed=round(total,3));(folder/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print('FILE_LAUNCH_EVIDENCE',folder)
    return 0
if __name__=='__main__':raise SystemExit(main())
