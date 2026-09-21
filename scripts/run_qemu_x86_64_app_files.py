"""BC private extension of the complete BA observer; no shared predicate edits.

Application frames have their own independent oracle, not storage-frame aliases.
Every generic CPU, page, PIO, terminal, IPC-delivery and cleanup check is retained.
"""
from pathlib import Path
import ast,hashlib,inspect,json,linecache,struct,sys,time,types
import run_qemu_x86_64_wide_file as wide
import build_x86_64_app_files_media as media
from check_x86_64_app_files_media import verify as verify_media
ROOT=Path(__file__).resolve().parents[1]
BUDGET_PROBE=ROOT/'build/codex-agent/r83bc-application-files/budget-probe-reuse'
require=wide.old.require
replace=wide.replace
NORMAL=b'cat /data.txt\nls -1 /\nprobe /data.txt\nexit\n'
# label, old root fault selector, layout, RAM, probe modes in first run.
CASES=tuple((name,0,n,4096,()) for n,name in enumerate(media.LAYOUTS))+(
    ('8g',5,2,8192,()),('repeated',6,2,4096,()),
    ('authority',0,2,4096,(1,2,3,4)),('crash',0,2,4096,(5,)),
    ('hang',0,2,4096,(6,)),('quota',0,2,4096,(7,)),
    ('owner-loss',15,2,4096,()),('driver-crash',7,2,4096,()),
    ('driver-hang',8,2,4096,()),('fs-reply',11,2,4096,()),
    ('request-budget',0,2,4096,(8,)))

def case_order(budget_first=False):
    require(type(budget_first) is bool,'BC explicit execution-order selector')
    return CASES[-1:]+CASES[:-1] if budget_first else CASES

def case_spec(label):
    matches=[s for s in CASES if s[0]==label]
    require(len(matches)==1,'BC declared case');return matches[0]

def input_plan(label):
    _,case,_,_,modes=case_spec(label)
    if modes:first=b'probe /data.txt\n'*len(modes)+b'cat /data.txt\nls -1 /\nexit\n'
    elif case==6:first=b'cat /data.txt\nls -1 /\ncat /data.txt\nls -1 /\nexit\n'
    elif case==15:first=b'cat /data.txt\n'
    elif case in (7,8,11):first=b'cat /data.txt\n'+NORMAL
    else:first=NORMAL
    return ((0,first),),((0,NORMAL),)

def info(layout,name,files):
    require(type(layout) is int and layout in range(5),'BC metadata layout')
    is_root=name=='/'
    require(is_root or name in media.NAMES,'BC metadata name')
    text=name.upper() if layout<2 else name
    size=(0 if layout<2 else 1024<<(layout-2)) if is_root else len(files[name])
    return text.encode().ljust(256,b'\0')+struct.pack('<5I',2 if is_root else 1,size,0,0,0)

def fs_expected_response(request,layout,files):
    """All five files and true directory EOF; independent from image producer."""
    media.admit(files);op,path=wide.old.fs_request_frame(request)
    names={('/'+n).encode():n for n in media.NAMES}
    if layout<2:names={k.upper():v for k,v in names.items()};path=path.upper()
    root=path==b'/';name=names.get(path)
    if not root and name is None:return -2,b''
    answer=bytearray(request);status=0
    if op==6:
        if root:return -21,b''
        offset,count=struct.unpack_from('<2I',request,24);data=files[name][offset:offset+count]
        struct.pack_into('<I',answer,32,len(data));answer[228:228+len(data)]=data
    elif op==7:
        if not root:return -20,b''
        index=struct.unpack_from('<I',request,24)[0]
        if index>=len(media.NAMES):status=1
        else:answer[220:496]=info(layout,media.NAMES[index],files)
    else:answer[216:492]=info(layout,'/' if root else name,files)
    struct.pack_into('<I',answer,20,status)
    return status,bytes(answer)

def frame(raw):
    require(type(raw) is bytes and len(raw)==512,'BC frame extent')
    h=struct.unpack_from('<4I5Qi3IQ',raw)
    require(h[0:2]==(1,512) and h[3] in (0,1) and h[10]<=432 and not h[13] and
            not any(raw[80+h[10]:]),'BC frame canonical header/tail')
    return h,raw[80:80+h[10]]

def expected_reply(request,root,child,epoch,deadline,sequence,layout,files,operand):
    """Pure independent wire oracle, deliberately not generated from C broker."""
    h,data=frame(request);op=h[2]
    require(op in range(5) and h[3]==0 and h[5]==child and h[7]==sequence and
            not any((h[9],h[10])) and not data,'BC request identity/sequence/canonical')
    if op==0:require(sequence==1 and h[4]==h[6]==h[8]==0,'BC initial binding')
    else:require(sequence>1 and (h[4],h[6],h[8])==(root,epoch,deadline),'BC bound generation/epoch/deadline')
    offset,count=h[11:13];status=0;payload=b''
    if op in (0,1):
        require(not offset and not count,'BC stat reserved range');payload=info(layout,operand,files)
    elif op==2:
        require(operand!='/' and 0<count<=256 and offset<=len(files[operand]),'BC bounded file read')
        payload=files[operand][offset:offset+count]
    elif op==3:
        require(operand=='/' and not count and offset<=len(media.NAMES),'BC directory index')
        if offset<len(media.NAMES):payload=info(layout,media.NAMES[offset],files);status=1
    else:require(not offset and not count,'BC close reserved range')
    values=(1,512,op,1,root,child,epoch,sequence,deadline,status,len(payload),offset,count,0)
    return struct.pack('<4I5Qi3IQ',*values)+payload.ljust(432,b'\0')

def matching_record(slot,actual,records):
    choices=[records[slot]] if slot in (2,3) else [records[n] for n in (4,5,6,7)]
    found=[r for r in choices if actual[:262240]==r[:262240]]
    require(len(found)==1,'BC exact imported executable');return found[0]

def entry_record(row,raw,records):
    if row['slot']!=4:return records[row['slot']]
    name=tool_name(row);require(name in ('cat','ls','probe'),'BC explicit foreground tool')
    return records[dict(cat=5,ls=6,probe=7)[name]]

def selected_source():
    source=wide.selected_source()
    def node(name,changes):
        nonlocal source
        item=next(n for n in ast.parse(source).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
        before=ast.get_source_segment(source,item);after=before
        for a,b in changes:after=replace(after,a,b)
        source=replace(source,before,after)
    node('observer',[
        ('slot not in (2,3,4)','slot not in (2,3,4,5,6,7)'),
        ('set(references)!={2,3,4}','set(references)!={2,3,4,5,6,7}')])
    node('validate_capture',[
        ('else records[slot]','else entry_record(row,raw,records)'),
        ("record[:262240]==records[slot][:262240]","record[:262240]==matching_record(slot,record,records)[:262240]"),
        ("timeout==(1000 if operation==2 else 0)",
         "((0<timeout<=1000 if target&0xffffffff==4 else timeout==1000) if operation==2 else timeout==0)"),
        ("elif kind=='policy':","elif kind=='app_selection':validate_probe_selection(row,starts,live,config)\n        elif kind=='policy':"),
        ("    validate_storage(combined,raw,layout,app,case)",
         "    validate_storage(combined,raw,layout,app,case)\n    validate_objects(combined,receipts,layout,app,config)")])
    node('validate_storage',[("            require(len(data) in (64,576),'storage protocol message extent')",
        "            if len(data)==512:\n                require(slot in (0,4),'BC separate object protocol role')\n                continue\n            require(len(data) in (64,576),'storage protocol message extent')")])
    # Actual observer compares all prepared tool bytes, not just executable entry.
    source=replace(source,'    reference=records[slot]\n    assert record[:262240]==reference[:262240]',
        '    candidates=[records[slot]] if slot in (2,3) else [records[n] for n in (4,5,6,7)]\n'
        '    assert sum(record[:262240]==r[:262240] for r in candidates)==1')
    selection="        emit('selection',gen=gen,run=runs+1,before=raw.hex(),after=value.hex())"
    source=replace(source,selection+'\n\ndef syscall(denied=False):',selection+'''
    if slot==4 and args[0].lower().split('/')[-1] in ('probe','probe.prg'):
        address=CONFIG['app_probe'];original=user(t,address,32)
        assert original==struct.pack('<4Q',0x3150464154534554,1,0,0) and address&4095<=4064
        modes=CONFIG['probe_modes'] if runs==0 else ()
        index=sum(v.get('probe',False) for v in starts.values() if v['run']==runs+1)
        selected=modes[index] if index<len(modes) else 0
        starts[gen]['probe']=True
        leaf=leaves[(address-0x400000)//4096];assert leaf&~MASK&~0x60==NX|7
        value=struct.pack('<4Q',0x3150464154534554,1,selected,0)
        target=DM+(leaf&MASK)+(address&4095)
        gdb.selected_inferior().write_memory(target,value);assert mem(target,32)==value
        emit('app_selection',gen=gen,run=runs+1,before=original.hex(),after=value.hex(),index=index)
\ndef syscall(denied=False):''')
    return source

def validate_probe_selection(row,starts,live,config):
    gen=row['gen'];require(gen in live and starts[gen]['slot']==4 and
        starts[gen]['args'][0].lower().split('/')[-1] in ('probe','probe.prg'),'BC selected live probe')
    previous=[s for g,s in starts.items() if g<gen and s['run']==row['run'] and s['slot']==4 and
        s['args'][0].lower().split('/')[-1] in ('probe','probe.prg')]
    require(row['index']==len(previous),'BC probe injection order')
    modes=config['probe_modes'] if row['run']==1 else ()
    mode=modes[len(previous)] if len(previous)<len(modes) else 0
    require(bytes.fromhex(row['before'])==struct.pack('<4Q',0x3150464154534554,1,0,0) and
        bytes.fromhex(row['after'])==struct.pack('<4Q',0x3150464154534554,1,mode,0),'BC exact first-entry probe selection')

def namespace(label):
    spec=case_spec(label);source=selected_source();filename='<reist-app-files-'+label+'>'
    module=types.ModuleType('_reist_app_files_'+label.replace('-','_'));module.__file__=filename
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename);sys.modules[module.__name__]=module
    exec(compile(source,filename,'exec'),module.__dict__)
    prior=wide.namespace();module.ROOT=ROOT;module.file=types.SimpleNamespace(**vars(prior.file))
    module.file.media=types.SimpleNamespace(LAYOUTS=media.LAYOUTS,image=lambda layout,program:media.image(layout,program))
    module.native_cpu_trace=prior.native_cpu_trace
    for name in ('wide_serial_capture','lossless_observer','decode_evidence'):setattr(module,name,getattr(prior,name))
    module.CASES=((spec[1],spec[2],spec[3]),)
    module.input_plan=lambda unused:input_plan(label)
    module.fs_expected_response=fs_expected_response
    module.matching_record=matching_record;module.entry_record=entry_record;module.validate_probe_selection=validate_probe_selection
    module.validate_objects=validate_objects
    module.validate_io_and_faults=lambda *args:validate_io_and_faults(module,spec,*args)
    return module

def image_config(image,label):
    module=namespace(label);config,records,_=module.image_config(image)
    catalog=(Path(image).parent/'boot-programs.bin').read_bytes()
    folders=[p for p in Path(image).parent.glob('programs-*') if p.is_dir() and
        (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    require(len(folders)==1,'BC unique programs');folder=folders[0]
    files={name:(folder/'root'/name).read_bytes() for name in media.NAMES};media.admit(files)
    require(files['boot.prg']==(folder/'file-program.prg').read_bytes() and files['data.txt']==media.DATA,'BC exact data inputs')
    for slot,name in ((5,'cat'),(6,'ls'),(7,'probe')):
        require(files[name+'.prg']==(folder/(name+'.prg')).read_bytes(),'BC packaged actual tool')
        records[slot]=module.admission.wide.producer.prepare(files[name+'.prg'],[],True)
    for layout in media.LAYOUTS:verify_media((folder/('app-files-'+layout+'.raw')).read_bytes(),layout,files)
    probe_map=folder/'app-probe.map'
    if label=='request-budget':
        files['probe.prg']=(BUDGET_PROBE/'probe.prg').read_bytes()
        records[7]=module.admission.wide.producer.prepare(files['probe.prg'],[],True)
        probe_map=BUDGET_PROBE/'app-probe.map'
    config.update(app_probe=module.file.block.map_symbol(probe_map,'reist_app_probe_selection'),
        probe_modes=case_spec(label)[4],app_case=label)
    return config,records,files

def expected_tools(spec,run):
    _,case,_,_,modes=spec
    if run==2:return ('cat','ls','probe')
    if modes:return ('probe',)*len(modes)+('cat','ls')
    if case==6:return ('cat','ls','cat','ls')
    if case==15:return ('cat',)
    return ('cat','ls','probe') # failed initial service start publishes no app

def validate_io_and_faults(module,spec,events,receipts,case,attempts,policies,faults):
    """Retain old IO/service predicates; replace only app count/outcome/deadline."""
    source=inspect.getsource(wide.namespace().validate_io_and_faults)
    source=replace(source,"expected_count=4 if case==6 and run==1 else 0 if case==16 and run==1 else 1",
        "expected_count=len(expected_tools(spec,run))")
    begin="            expected=(134,3) if case==12 and run==1 else (256,3) if case==13 and run==1 else (0,3) if case in (14,15) and run==1 else (82,4)"
    source=replace(source,begin,"            expected=qualified_outcome(spec,app_start,apps,events,receipts)")
    source=replace(source,"written==(b'SESSION64\\n' if expected==(82,4) else b'')",
        "written==app_output(spec,app_start,apps)")
    source=replace(source,"struct.unpack_from('<Q',request,32)[0]==1000","0<struct.unpack_from('<Q',request,32)[0]<=1000")
    source=replace(source,"reason=0 if expected[1]==4 else 2 if case==14 and run==1 else 1",
        "reason=0 if expected[1]==4 else 1 if expected[0] in (134,256) else 2")
    source=replace(source,"waits==([-110,receipt_value] if case==14 and run==1 else [receipt_value]) and\n                    cancels==([0] if case==14 and run==1 else [])",
        "waits==[receipt_value] and cancels==([0] if app_mode(spec,app_start,apps) in range(2,9) else [])")
    source=replace(source,"if case==6 and run==1:\n            reads=[r for r in root_io if r['op']==15 and r['result']>0]\n            require(reads and reads[0]['now']-root['now']>=5000 and attempts.get(root['gen'],0)>8,'persistent idle and cumulative construction proof')",
        "if case==6 and run==1:\n            require(attempts.get(root['gen'],0)>8,'BC repeated tools exceed lifetime construction count')")
    source=replace(source,"expected_faults={7:[2],9:[3],12:[4],15:[0],16:[3,3,3]}.get(case,[])",
        "expected_faults=[4] if 5 in spec[4] else {7:[2],15:[0]}.get(case,[])")
    ns=dict(vars(module),spec=spec,expected_tools=expected_tools,qualified_outcome=qualified_outcome,app_mode=app_mode,
        app_output=lambda s,a,apps:app_output(s,a,apps,module.app_files))
    exec(compile(source,'<BC-app-io-outcomes>','exec'),ns)
    ns['validate_io_and_faults'](events,receipts,case,attempts,policies,faults)
    for run in (1,2):
        apps=[r for r in events if r['kind']=='start' and r['run']==run and r['slot']==4]
        require(tuple(tool_name(r) for r in apps)==expected_tools(spec,run),'BC exact command dispatch order')

def tool_name(start):return start['args'][0].lower().replace('\\','/').split('/')[-1].removesuffix('.prg')

def app_mode(spec,start,apps):
    if start['run']!=1 or tool_name(start)!='probe':return 0
    index=[s['gen'] for s in apps if tool_name(s)=='probe'].index(start['gen'])
    return spec[4][index] if index<len(spec[4]) else 0

def app_outcome(spec,start,apps):
    if spec[1]==15 and start['run']==1:return 0,3
    mode=app_mode(spec,start,apps)
    return (134,3) if mode==5 else (256,3) if mode==7 else (0,3) if mode in (2,3,4,6,8) else (0,4)

def qualified_outcome(spec,start,apps,events,receipts):
    expected=app_outcome(spec,start,apps);receipt=receipts[start['gen']]
    actual=(receipt['status'],receipt['state'])
    if actual==expected:return expected
    mode=app_mode(spec,start,apps)
    require(mode in (2,3,4,6,8) and actual==(1,4),'BC declared revocation self-exit only')
    gen=start['gen'];root=start['parent']>>32;request,reply=(int(a[5:],16) for a in start['args'][-2:])
    failures=[r for r in events if r['kind']=='return' and r['gen']==gen and r['op'] in (53,54) and r['result']<0]
    if mode==8:
        answers=[r for r in events if r['kind']=='return' and r['gen']==gen and r['op']==54 and
            r['args'][0]==reply and r['result']==0]
        require(len(answers)==80,'BC all eighty replies actually received')
        sent=[r for r in events[events.index(answers[-1])+1:] if r['kind']=='return' and
            r['gen']==gen and r['op']==53 and r['args'][0]==request]
        require(len(sent)==1 and sent[0]['result'] in (0,-9),'BC exact final transport attempt')
        failed=sent[0];queued=failed['result']==0
        require(failures==([] if queued else [failed]),'BC only declared final transport outcome')
        h,payload=frame(wide.old.ipc_message(bytes.fromhex(failed['before'])))
        require(h[:6]==(1,512,1,0,root,gen) and h[6]>0 and h[7]==81 and h[8]>0 and
            not any(h[9:]) and not payload,'BC exact exhausted STAT request')
        last,_=frame(wide.old.ipc_message(bytes.fromhex(answers[-1]['after'])))
        require(last[:7]==(1,512,1,1,root,gen,h[6]) and last[7]==80 and last[8]==h[8],
            'BC final earned sequence and original deadline')
        closes=[r for r in events if r['kind']=='call' and r['gen']==root and r['op']==52 and r['args'][0]==request]
        require(len(closes)==1,'BC exhausted request channel revoked')
        require((events.index(failed)<events.index(closes[0])) if queued else
            (events.index(closes[0])<events.index(failed)),'BC exact enqueue/revoke ordering')
        if queued:
            require(failed['entered']<=failed['now']<h[8],'BC enqueue within original deadline')
            for op,endpoint in ((54,request),(53,reply)):
                broker=[r for r in events if r['kind']=='return' and r['gen']==root and
                    r['op']==op and r['args'][0]==endpoint and r['result']==0]
                require(len(broker)==80 and all(events.index(r)<events.index(failed) for r in broker),
                    'BC no consumption or reply for queued 81st request')
            for endpoint in (request,reply):
                calls=[r for r in events if r['kind']=='call' and r['gen']==root and r['op']==52 and r['args'][0]==endpoint]
                closed=[r for r in events if r['kind']=='return' and r['gen']==root and r['op']==52 and r['args'][0]==endpoint]
                require(len(calls)==len(closed)==1 and closed[0]['result']==0 and
                    failed['now']<=closed[0]['now']<h[8] and
                    events.index(failed)<events.index(calls[0])<events.index(closed[0]),
                    'BC queued request removed by successful endpoint revocation')
        exits=[r for r in events if r['kind']=='call' and r['gen']==gen and r['op']==9]
        require(len(exits)==1 and exits[0]['args']==[1,0,0,0,0,0] and events.index(failed)<events.index(exits[0]),
            'BC explicit local exhausted SDK close error exit')
        return actual
    if mode==6:
        require([(r['op'],r['args'][0],r['result']) for r in failures]==[(54,reply,-32)],
            'BC blocked hang released only by reply closure')
        grants=[r for r in events if r['kind']=='return' and r['gen']==root and r['op']==53 and
            r['args'][0]==reply and r['result']==0]
        require(grants,'BC hang actual grant')
        h,_=frame(wide.old.ipc_message(bytes.fromhex(grants[0]['before'])));end=h[8]
        require(h[:8]==(1,512,0,1,root,gen,h[6],1) and h[6]>0,'BC hang HELLO binding')
        timeouts=[r for r in events if r['kind']=='return' and r['gen']==root and r['op']==54 and
            r['args'][0]==request and r['result']==-110]
        require(len(timeouts)==1,'BC actual broker timeout')
        timeout=timeouts[0];failed=failures[0]
        require(0<timeout['args'][2]<=1000 and timeout['entered']+timeout['args'][2]==end==timeout['now'] and
            failed['args'][2]==1000 and timeout['entered']<=failed['entered']<end==failed['now'] and
            events.index(timeout)<events.index(failed),'BC unchanged absolute timeout and real blocked interval')
        for endpoint in (request,reply):
            closed=[r for r in events if r['kind']=='call' and r['gen']==root and r['op']==52 and r['args'][0]==endpoint]
            require(len(closed)==1 and closed[0]['entered']==end and
                events.index(timeout)<events.index(closed[0])<events.index(failed),'BC deadline revokes both endpoints')
        exits=[r for r in events if r['kind']=='call' and r['gen']==gen and r['op']==9]
        require(len(exits)==1 and exits[0]['args']==[1,0,0,0,0,0] and
            end<=exits[0]['entered']<=end+1000 and events.index(failed)<events.index(exits[0]),
            'BC expired SDK error exit within cleanup bound')
        return actual
    require([(r['op'],r['args'][0],r['result']) for r in failures]==[(54,reply,-32),(53,request,-9)],
        'BC actual reply closure then stale close-send rejection')
    h,payload=frame(wide.old.ipc_message(bytes.fromhex(failures[1]['before'])))
    require(h[:6]==(1,512,4,0,root,gen) and h[6]>0 and h[7]==3 and h[8]>0 and
        not any(h[9:]) and not payload,'BC failed canonical CLOSE after invalid request')
    exits=[r for r in events if r['kind']=='call' and r['gen']==gen and r['op']==9]
    require(len(exits)==1 and exits[0]['args']==[1,0,0,0,0,0] and
        events.index(failures[1])<events.index(exits[0]),'BC explicit SDK error exit, not successful operation')
    for endpoint in (request,reply):
        closed=[r for r in events if r['kind']=='call' and r['gen']==root and r['op']==52 and r['args'][0]==endpoint]
        require(len(closed)==1 and events.index(closed[0])<events.index(failures[1 if endpoint==request else 0]),
            'BC actual root revocation precedes failed child operation')
    return actual

def app_output(spec,start,apps,files):
    if app_outcome(spec,start,apps)!=(0,4):return b''
    name=tool_name(start)
    if name=='cat':return files['data.txt']
    if name=='probe':return b'APP_OBJECT_PROBE_OK\n'
    require(name=='ls','BC known tool output')
    return b''.join((n.upper() if spec[2]<2 else n).encode()+b'\n' for n in media.NAMES)

def relative_deadline(end,timeout,previous,entered,completed):
    # ABI uses relative milliseconds sampled in userspace, not an atomic
    # kernel absolute-deadline argument. Reconstruct that exact sample within
    # two real recorded events. Do not invent tick slack or renew the end.
    require(all(type(n) is int for n in (end,timeout,previous,entered,completed)) and
        0<timeout<=1000 and 0<=previous<=end-timeout<=entered<=completed<end,
        'BC original clock sample and completed absolute deadline')
    return True

def validate_objects(events,receipts,layout,files,config):
    """Reconstruct directed grants, all wire requests and revocation per child."""
    spec=case_spec(config['app_case']);starts={r['gen']:r for r in events if r['kind']=='start'}
    returned=[r for r in events if r['kind']=='return'];calls=[r for r in events if r['kind']=='call']
    previous={};pending={};sample_floor={}
    for row in events:
        gen=row.get('gen')
        if row['kind']=='call':pending[gen]=previous.get(gen,starts[gen]['now'])
        elif row['kind'] in ('return','io'):
            sample_floor[id(row)]=pending.pop(gen,previous.get(gen,starts[gen]['now']))
            previous[gen]=row['now']
    seen_epochs={};channels=set();validated=0
    for run in (1,2):
        apps=[r for r in starts.values() if r['run']==run and r['slot']==4]
        root=next(r for r in starts.values() if r['run']==run and r['slot']==0)
        for child in apps:
            gen=child['gen'];args=child['args'];mode=app_mode(spec,child,apps)
            require(len(args)>=4 and all(__import__('re').fullmatch('@af1:[0-9a-f]{8}',a) for a in args[-2:]),'BC actual startup channels')
            request,reply=[int(a[5:],16) for a in args[-2:]]
            require(request and reply and request!=reply and not {request,reply}&channels,'BC fresh distinct channels')
            channels.update((request,reply))
            profile=struct.unpack('<4Q',bytes.fromhex(child['profile']))
            mask=sum(1<<n for n in (4,5,6,9,15,20,22,40,41,42,50,51,53,54,58))
            require(profile[1]==mask,'BC exact least-authority tool profile')
            grants=[r for r in returned if r['gen']==root['gen'] and r['op']==55 and r['args'][1]==gen]
            require([(r['args'][:3],r['result']) for r in grants]==[([request,gen,1],0),([reply,gen,2],0)],'BC exact directed peer grants')
            for endpoint in (request,reply):
                created=[r for r in returned if r['gen']==root['gen'] and r['op']==49 and r['result']==0 and
                    struct.unpack('<I',bytes.fromhex(r['after']))[0]==endpoint]
                require(len(created)==1 and created[0]['now']<=child['now'],'BC root owns newly created endpoint')
            validate_capture_before_grant(events,root,child,layout,files)
            if spec[1]==15 and run==1:
                require(not any(r['gen']==gen and r['op'] in (53,54) for r in calls),'BC owner loss before terminal/object use')
                continue
            writes=[r for r in returned if r['op']==53 and r['gen']==root['gen'] and r['args'][0]==reply and r['result']==0]
            reads=[r for r in returned if r['op']==54 and r['gen']==root['gen'] and r['args'][0]==request and r['result']==0]
            require(writes and reads,'BC actual object handshake')
            first=wide.old.ipc_message(bytes.fromhex(writes[0]['before']));h,_=frame(first)
            epoch,end=h[6],h[8]
            require(h[4:6]==(root['gen'],gen) and epoch==seen_epochs.get(root['gen'],0)+1 and
                child['now']<end<=child['now']+1000,'BC grant identity/absolute lifetime')
            seen_epochs[root['gen']]=epoch
            operand='/' if tool_name(child)=='ls' else 'data.txt'
            requests=[wide.old.ipc_message(bytes.fromhex(r['after'])) for r in reads]
            for n,row in enumerate(writes,1):
                require(n<=80 and n<=len(reads),'BC reply budget/correspondence')
                q=requests[n-1]
                require(wide.old.ipc_message(bytes.fromhex(row['before']))==expected_reply(q,root['gen'],gen,epoch,end,n,layout,files,operand),'BC exact object reply bytes')
                for completed in (reads[n-1],row):
                    relative_deadline(end,completed['args'][2],sample_floor[id(completed)],completed['entered'],completed['now'])
                validated+=1
            closed=frame(wide.old.ipc_message(bytes.fromhex(writes[-1]['before'])))[0][2]==4
            if mode in (0,1):require(closed and len(reads)==len(writes),'BC normal close reply')
            elif mode in (2,3,4):
                require(not closed and len(reads)==len(writes)+1,'BC rejected request gets no reply')
                q=bytearray(requests[-1]);expected=bytearray(requests[1]);struct.pack_into('<Q',expected,40,3)
                if mode==2:struct.pack_into('<I',expected,8,5)
                elif mode==3:struct.pack_into('<Q',expected,32,epoch-1)
                else:struct.pack_into('<Q',expected,24,root['gen'])
                require(q==expected,'BC exact selected malformed/stale/foreign request')
            elif mode==8:require(len(writes)==len(reads)==80 and not closed,'BC actual request budget reached')
            else:require(len(writes)==len(reads)==2 and not closed,'BC child fault after real binding')
            closes=[r for r in returned if r['gen']==root['gen'] and r['op']==52 and r['args'][0] in (request,reply)]
            require([(r['args'][0],r['result']) for r in closes]==[(request,0),(reply,0)],'BC broker exact revoke/close')
            if mode==1:
                require([r['op'] for r in returned if r['gen']==gen and r['profile_denied']]==[49,52,55,113],
                    'BC forbidden create/close/delegate/PIO denied before access')
                denied=[r for r in returned if r['gen']==gen and r['op'] in (53,54) and r['result']==-13]
                require([(r['op'],r['args'][0]) for r in denied]==[(53,reply),(54,request)],'BC actual wrong-direction rejection')
            require(receipts[gen]['ticks']<=32,'BC original CPU bound')
    require(validated>0,'BC nonempty object proof');return validated

def validate_capture_before_grant(events,root,child,layout,files):
    """Actual FS request/receive chain including EOF precedes CREATE publication."""
    incoming={};completed=[];creation=None
    for row in events:
        if row.get('gen')!=root['gen']:continue
        if row['kind']=='call' and row['op']==53 and not row['profile_denied']:
            raw=wide.old.ipc_message(bytes.fromhex(row['before']))
            if len(raw)==576:
                h=struct.unpack_from('<4I4QIiQ',raw)
                if h[2] in (5,6,7) and h[3]==0:incoming[(h[4],h[5])]=(row,raw[64:])
        if row['kind']!='return':continue
        if row['op']==132 and row['result']==(child['gen']<<32)|4:
            creation=row;break
        if row['op']==54 and row['result']==0:
            raw=wide.old.ipc_message(bytes.fromhex(row['after']))
            if len(raw)==576:
                h=struct.unpack_from('<4I4QIiQ',raw);key=(h[4],h[5])
                if key in incoming:completed.append((incoming[key][0],incoming[key][1],row,raw[64:],h[4]))
    require(creation is not None,'BC constructor follows complete capture')
    operand=b'/' if tool_name(child)=='ls' else b'/data.txt'
    selected=[r for r in completed if wide.old.fs_request_frame(r[1])[1].lower()==operand]
    stats=[n for n,r in enumerate(selected) if wide.old.fs_request_frame(r[1])[0]==5]
    require(stats,'BC actual capture STAT');selected=selected[stats[-1]:]
    owner=selected[0][4];position=0;ended=False
    for n,(sent,q,received,answer,generation) in enumerate(selected):
        op,_=wide.old.fs_request_frame(q)
        require(generation==owner and received['now']<=creation['entered'] and not ended,'BC capture one live FS generation before import')
        status,expected=fs_expected_response(q,layout,files)
        require(answer==expected,'BC captured actual immutable bytes')
        if n==0:require(op==5 and status==0,'BC capture successful STAT');continue
        offset=struct.unpack_from('<I',q,24)[0]
        require(offset==position,'BC capture no gaps/overlap')
        if operand==b'/':
            require(op==7 and status in (0,1),'BC captured directory operation')
            if status==1:ended=True;require(position==len(media.NAMES),'BC actual directory EOF')
            else:position+=1
        else:
            require(op==6 and status==0,'BC captured file operation')
            count=struct.unpack_from('<I',answer,32)[0]
            if not count:ended=True;require(position==len(files['data.txt']),'BC actual file EOF')
            else:position+=count
    require(ended,'BC complete immutable capture, no truncated grant')
    # Code and object share one original command bound, not two renewed clocks.
    code=b'/'+tool_name(child).encode()+b'.prg'
    code_stats=[r for r in completed if wide.old.fs_request_frame(r[1])==(5,code)]
    require(code_stats and 0<=creation['now']-code_stats[-1][0]['entered']<120000,'BC whole code/object capture bound')

def bounded_fixture(folder,layout,files,started):
    fixture=wide.old.file.pio.Fixture.__new__(wide.old.file.pio.Fixture)
    fixture.started=started;fixture.wide_full=False
    fixture.expected=lambda:media.image(media.LAYOUTS[layout],files)
    fixture.run=types.MethodType(wide.Fixture.run,fixture)
    wide.old.file.pio.Fixture.__init__(fixture,folder,filesystem=media.LAYOUTS[layout],file_program=files['boot.prg'])
    return fixture

def run_matrix(image,folder,candidate,binding,reused_budget=None,budget_first=False):
    image=Path(image).resolve();folder=Path(folder).absolute()
    require(image.is_relative_to(ROOT/'build') and folder.is_relative_to(ROOT/'build/codex-agent') and
        folder==folder.resolve() and not folder.exists(),'BC fresh runtime scope')
    binding();image_sha=hashlib.sha256(image.read_bytes()).hexdigest();catalog=(image.parent/'boot-programs.bin').read_bytes()
    folder.mkdir(parents=True);wide.old.file.pio.safe_folder(folder)
    summary=dict(candidate=candidate,image_sha256=image_sha,cases=[],passed=False,closed=False,guest_elapsed=0.0)
    begin=time.monotonic()
    try:
        require(reused_budget is None or budget_first,'BC reuse only corrected budget case first')
        ordered=case_order(budget_first)
        if reused_budget is not None:
            row=dict(reused_budget);label,case,layout,ram,_=ordered[0]
            require(label=='request-budget' and row['passed'] and row['reused'] and
                tuple(row[k] for k in ('label','case','layout','ram'))==ordered[0][:4] and
                0<row['elapsed']<=300,'BC exact one captured budget case')
            module=namespace(label);config,records,files=image_config(image,label);module.app_files=files
            require(module.evaluate(ROOT/row['folder'],config,records,catalog,case,layout,files)==row['proof'],
                'BC complete independent corrected budget replay')
            summary['cases'].append(row);summary['guest_elapsed']=row['elapsed']
            ordered=ordered[1:]
        for label,case,layout,ram,modes in ordered:
            binding();require(hashlib.sha256(image.read_bytes()).hexdigest()==image_sha,'BC same image')
            require(summary['guest_elapsed']+300<=4800 and time.monotonic()-begin<5350,'BC finite matrix budget')
            module=namespace(label);config,records,files=image_config(image,label);module.app_files=files
            out=folder/label;out.mkdir();started=time.monotonic()
            row=dict(label=label,case=case,layout=layout,ram=ram,passed=False,reused=False,folder=out.relative_to(ROOT).as_posix())
            summary['cases'].append(row)
            try:
                code=module.observer(config,records,out,case,layout)
                fixture=bounded_fixture(out,layout,files,started)
                module.stepped_capture_namespace(started)['capture'](image,out,code,ram,fixture,
                    binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True,console_input=input_plan(label))
            finally:
                row['elapsed']=time.monotonic()-started;summary['guest_elapsed']+=row['elapsed']
            require(row['elapsed']<=300,'BC whole guest incl cleanup')
            row['proof']=module.evaluate(out,config,records,catalog,case,layout,files);row['passed']=True
            print('APP_FILES_GUEST_PASS',label,round(row['elapsed'],3),flush=True)
        summary['passed']=True;return summary
    except BaseException as error:summary['error']=str(error);raise
    finally:
        if budget_first:
            reused_count=int(reused_budget is not None)
            reused_seconds=reused_budget['elapsed'] if reused_count else 0
            previous_guests=19 if reused_count else 18
            previous_seconds=1669.1003875000752 if reused_count else 1588.3585832000244
            summary.update(previous_guests=previous_guests,previous_guest_elapsed=previous_seconds,
                cumulative_guests=previous_guests+len(summary['cases'])-reused_count,
                cumulative_guest_elapsed=previous_seconds+summary['guest_elapsed']-reused_seconds)
        summary.update(closed=True,elapsed=time.monotonic()-begin)
        with (folder/'summary.json').open('x',encoding='utf-8') as out:json.dump(summary,out,indent=2,sort_keys=True)
