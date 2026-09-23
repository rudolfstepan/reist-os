"""Private BR extension of the accepted complete shell/device/CPU proof.

No shared observer is modified. Raw C++ checkpoints supplement, and never
replace, the original process, physical-device and generation cleanup proof.
"""
from pathlib import Path
import ast,hashlib,inspect,json,linecache,struct,sys,textwrap,time,types
import run_qemu_x86_64_app_files as apps
import build_x86_64_cpp_runtime_media as media
import check_x86_64_cpp_runtime_media as check
wide=apps.wide
ROOT=apps.ROOT
require=apps.require
replace=wide.replace
CASES=(('healthy4g',0,4096,0),('healthy8g',5,8192,0),
       ('realloc-failure',0,4096,1),('heap-fault',0,4096,2),
       ('new-oom',0,4096,3),('crash',0,4096,4),('hang',0,4096,5),
       ('cpu',0,4096,6),('owner-loss',15,4096,0),('repeated',6,4096,0))
NORMAL=b'cpptest\ncat /data.txt\nls -1 /\nprobe /data.txt\nexit\n'
OK=b'REIST_CPP_LIFETIME_OK\nREIST_CPP_BACKING_RETURN_OK\nREIST_CPP_TYPES_OK\nREIST_CPP_HANDLE_OWNERSHIP_OK\nREIST_CPP_RUNTIME_OK\n'

def spec_for(label):
    found=[s for s in CASES if s[0]==label]
    require(len(found)==1,'BR explicit case');return found[0]

def input_plan(label):
    spec=spec_for(label)
    first=b'cpptest\n' if spec[1]==15 else b'cpptest\n'+NORMAL if spec[1]==6 else NORMAL
    return ((0,first),),((0,NORMAL),)

def tools_for(spec,run):
    if run==1 and spec[1]==15:return ('cpptest',)
    return (('cpptest',) if run==1 and spec[1]==6 else ())+('cpptest','cat','ls','probe')

def mode_for(spec,start):return spec[3] if start['run']==1 and apps.tool_name(start)=='cpptest' else 0

def outcome(spec,start):
    if spec[1]==15 and start['run']==1:return 0,3
    return {0:(0,4),1:(0,4),2:(70,4),3:(71,4),4:(134,3),5:(0,3),6:(256,3)}[mode_for(spec,start)]

def output(spec,start,files):
    if spec[1]==15 and start['run']==1:return b''
    name=apps.tool_name(start)
    if name=='cpptest':return OK if mode_for(spec,start)<2 else b'REIST_LIBC_HEAP_FAULT\n' if mode_for(spec,start)==2 else b''
    if name=='cat':return files['data.txt']
    if name=='probe':return b'APP_OBJECT_PROBE_OK\n'
    require(name=='ls','BR explicit output');return b''.join(n.encode()+b'\n' for n in check.NAMES)

def admit(files):
    require(type(files) is dict and set(files)==set(check.NAMES),'BR exact six files')
    apps.media.admit({n:files[n] for n in apps.media.NAMES})
    check.validate_cpp_object(files['cpptest.prg'],architecture='x86_64')

def rebound(fn,namespace):
    return types.FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)

def object_namespace():
    ns=dict(vars(apps));ns['media']=types.SimpleNamespace(NAMES=check.NAMES,admit=admit)
    for name in ('info','fs_expected_response','expected_reply','validate_capture_before_grant'):
        ns[name]=rebound(getattr(apps,name),ns)
    source=inspect.getsource(apps.validate_objects)
    source=replace(source,"r['run']==run and r['slot']==4]","r['run']==run and r['slot']==4 and tool_name(r)!='cpptest']")
    # CPP commands do not acquire broker epochs; ordinary tools retain BC order.
    ns['case_spec']=lambda label:('ext2-1k',spec_for(label)[1],2,spec_for(label)[2],())
    exec(compile(source,'<BR-retained-object-proof>','exec'),ns)
    return ns

def matching_record(slot,actual,records):
    choices=[records[slot]] if slot in (2,3) else [records[n] for n in (4,5,6,7,8)]
    found=[r for r in choices if actual[:262240]==r[:262240]]
    require(len(found)==1,'BR exact imported executable');return found[0]

def entry_record(row,raw,records):
    if row['slot']!=4:return records[row['slot']]
    name=apps.tool_name(row);require(name in ('cat','ls','probe','cpptest'),'BR foreground executable')
    return records[dict(cat=5,ls=6,probe=7,cpptest=8)[name]]

SELECTION='''
    if slot==4 and args[0].lower().split('/')[-1] in ('cpptest','cpptest.prg'):
        address=CONFIG['cpp_selection'];original=user(t,address,16)
        assert original==struct.pack('<2Q',0x3150504354525352,0) and address&4095<=4080
        selected=CONFIG['cpp_mode'] if runs==0 else 0
        leaf=leaves[(address-0x400000)//4096];assert leaf&~MASK&~0x60==NX|7
        value=struct.pack('<2Q',0x3150504354525352,selected)
        target=DM+(leaf&MASK)+(address&4095)
        gdb.selected_inferior().write_memory(target,value);assert mem(target,16)==value
        starts[gen]['cpp']=True
        cpp_checkpoint.enabled=True
        emit('cpp_selection',gen=gen,run=runs+1,before=original.hex(),after=value.hex())
'''

CHECKPOINT='''
class CPPCheckpoint(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(CONFIG['cpp_checkpoint']),internal=True)
        self.enabled=False;self.count=0
    def stop(self):
        try:
            self.count+=1;assert self.count<=16
            slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
            assert mode()==8 and slot==4 and starts[gen]['live'] and starts[gen].get('cpp')
            assert reg('rip')==CONFIG['cpp_checkpoint'] and reg('cr3')&MASK==t[2]&MASK
            witness=user(t,CONFIG['cpp_witness'],64);w=struct.unpack('<8Q',witness)
            assert w[0] in (1,2,3) and w[2]==1024 and 0x100000000<w[1]<0x120000000
            hp=CS['native_heap_state']+232+slot*99368
            control=mem(hp,128);regions=mem(hp+552,5120);tables=mem(hp+32808,12288)
            addresses=(w[1]&~4095,(w[1]+1023)&~4095,w[6],w[7]&~4095)
            leaves=[];walks=[]
            for address in addresses:
                root=t[2]&MASK;leaf=0
                for shift in (39,30,21,12):
                    location=root+((address>>shift)&511)*8 if root else 0
                    entry=q(DM+location) if location else 0
                    walks.extend((location,entry))
                    assert not entry&128
                    root=(entry&MASK) if entry&1 else 0
                    if shift==12:leaf=entry
                leaves.append(leaf)
            chunks=[]
            for address,leaf in zip(addresses,leaves):
                if leaf:
                    assert leaf&~0x60==(leaf&MASK)|NX|7
                    chunks.append(mem(DM+(leaf&MASK),4096))
                else:chunks.append(bytes(4096))
            emit('cpp_checkpoint',gen=gen,run=runs+1,slot=slot,pc=reg('rip'),root=t[2],
                 witness=snapshot(witness),control=snapshot(control),regions=snapshot(regions),
                 tables=snapshot(tables),addresses=list(addresses),leaves=leaves,
                 walks=snapshot(struct.pack('<32Q',*walks)),pages=snapshot(b''.join(chunks)))
        except BaseException as error:
            import traceback
            gdb.write(traceback.format_exc());emit('OBSERVER_FAIL',where='cpp checkpoint',error=str(error)[:256])
            gdb.execute('quit 71')
        return False
cpp_checkpoint=CPPCheckpoint()
'''

def selected_source():
    source=apps.selected_source()
    # Each transformation fails closed if its retained source has drifted.
    for before,after in (
        ('slot not in (2,3,4,5,6,7)','slot not in (2,3,4,5,6,7,8)'),
        ('set(references)!={2,3,4,5,6,7}','set(references)!={2,3,4,5,6,7,8}'),
        ('[records[n] for n in (4,5,6,7)]','[records[n] for n in (4,5,6,7,8)]'),
        ('\ndef syscall(denied=False):',SELECTION+'\ndef syscall(denied=False):'),
        ("elif kind=='app_selection':", "elif kind=='cpp_selection':validate_cpp_selection(row,starts,live,config)\n        elif kind=='cpp_checkpoint':validate_checkpoint(row,starts,live,config,raw)\n        elif kind=='cpp_reaped':validate_reaped(row,starts,live,raw)\n        elif kind=='app_selection':"),
        ("    validate_objects(combined,receipts,layout,app,config)",
         "    validate_objects(combined,receipts,layout,app,config)\n    validate_cpp_history(combined,receipts,config,raw)"),
        ("            if len(data)==512:","            if slot==4 and tool_name(starts[gen])=='cpptest':\n                require(data==b'C','BR exact local C++ IPC payload')\n                continue\n            if len(data)==512:"),
        ("(row['op']<53 or 0<row['args'][2]<=1000)",
         "(row['op']<53 or 0<row['args'][2]<=1000 or row['op']==54 and row['args'][2]==0 and any(s['kind']=='start' and s['gen']==row['gen'] and s['slot']==4 and tool_name(s)=='cpptest' for s in events))"),
        ('elapsed<297','elapsed<177'),('now<started+297','now<started+177'),
        ("'deadline=console_started+297'","'deadline=console_started+177'"),
        ("'time.monotonic()-console_started>300'","'time.monotonic()-console_started>180'"),
        ("'time.monotonic()-capture_started>300'","'time.monotonic()-capture_started>180'"),
        ('from run_qemu_x86_64_wide_file import configure_binary as configure',
         'from run_qemu_x86_64_cpp_runtime import configure_binary as configure')):
        source=replace(source,before,after)
    return source

def configure_binary(*args,**kwargs):
    arguments,body=wide.configure_binary(*args,**kwargs)
    return arguments,replace(body,'binary_reader.deadline+=255','binary_reader.deadline+=135')

def validate_cpp_selection(row,starts,live,config):
    gen=row['gen'];require(gen in live and apps.tool_name(starts[gen])=='cpptest','BR live selected consumer')
    selected=config['cpp_mode'] if row['run']==1 else 0
    require(bytes.fromhex(row['before'])==struct.pack('<2Q',0x3150504354525352,0) and
            bytes.fromhex(row['after'])==struct.pack('<2Q',0x3150504354525352,selected),'BR exact private selection')

def validate_checkpoint(row,starts,live,config,raw):
    gen=row['gen'];require(gen in live and apps.tool_name(starts[gen])=='cpptest' and
        row['slot']==4 and row['run']==starts[gen]['run'] and row['pc']==config['cpp_checkpoint'],'BR checkpoint identity')
    w=struct.unpack('<8Q',raw.read(row['witness'],64));c=struct.unpack('<16Q',raw.read(row['control'],128))
    regions=raw.read(row['regions'],5120);tables=raw.read(row['tables'],12288);pages=raw.read(row['pages'],16384)
    task=struct.unpack('<128Q',raw.read(starts[gen]['task'],1024))
    require(row['root']==task[2]==c[2] and c[0]==gen and c[5]==0x20000000,'BR native heap owner/root/budget')
    require(w[0] in (1,2,3) and 0x100000000<w[1]<0x120000000 and w[2]==1024 and
        w[6]>=0x100000000 and w[6]%4096==0 and w[7]>=0x100000000 and w[7]%16==0,'BR LP64 object addresses/alignment')
    require(row['addresses']==[w[1]&~4095,(w[1]+1023)&~4095,w[6],w[7]&~4095] and len(row['leaves'])==4,'BR exact witnessed pages')
    require('walks' in row,'BR raw PTE paths required')
    paths=struct.unpack('<32Q',raw.read(row['walks'],256))
    for n,address in enumerate(row['addresses']):
        root=row['root']&0x3fffff000
        for level,shift in enumerate((39,30,21,12)):
            location,entry=paths[n*8+level*2:n*8+level*2+2]
            require(location==(root+((address>>shift)&511)*8 if root else 0) and
                not entry&128 and (location or not entry),'BR raw translation chain')
            if level<3 and entry:require(entry&7==7,'BR user translation rights')
            root=entry&0x3fffff000 if entry&1 else 0
        require(entry==row['leaves'][n],'BR actual final PTE')
    if w[0]==2:
        require(not any(w[3:6]) and c[6]==0 and not any(regions) and not any(tables) and
                not any(row['leaves']) and not any(pages),'BR actual empty provider and unmapped objects')
    else:
        require(0<w[3]<=8*1024*1024 and w[4]==4 and w[5]>=1024 and c[6]>=w[3],'BR live backing accounting')
        for leaf in row['leaves']:
            require(0x100000000<=leaf&0x3fffff000<0x400000000 and
                    leaf&~0x60==(leaf&0x3fffff000)|(1<<63)|7,'BR high private writable NX heap page')
        offset=w[1]&4095
        content=pages[offset:min(offset+1024,4096)]+pages[4096:4096+max(0,offset+1024-4096)]
        require(content==b'Z'*1024,'BR retained real allocation bytes')
        active=[struct.unpack_from('<5Q',regions,n*40) for n in range(128) if any(regions[n*40:(n+1)*40])]
        require(active and all(r[4]==2 and r[2]==r[3] for r in active) and
            all(any(r[0]<=p<r[0]+r[1] for r in active) for p in (w[1],w[6],w[7])), 'BR actual containing kernel regions')
    return w

def validate_cpp_history(events,receipts,config,raw):
    spec=spec_for(config['app_case']);starts=[r for r in events if r['kind']=='start' and r['slot']==4 and apps.tool_name(r)=='cpptest']
    require(starts,'BR nonempty C++ execution')
    for start in starts:
        gen=start['gen'];selected=[r for r in events if r['kind']=='cpp_selection' and r['gen']==gen]
        checkpoints=[r for r in events if r['kind']=='cpp_checkpoint' and r['gen']==gen]
        phases=[struct.unpack('<8Q',raw.read(r['witness'],64))[0] for r in checkpoints]
        require(len(selected)==1 and start['args']==['cpptest.prg'],'BR ordinary no-authority CLI launch')
        reaped=[r for r in events if r['kind']=='cpp_reaped' and r['gen']==gen]
        require(len(reaped)==1 and all(events.index(r)<events.index(reaped[0]) for r in checkpoints),
                'BR exact per-generation raw heap reap')
        if checkpoints:
            first=struct.unpack('<8Q',raw.read(checkpoints[0]['witness'],64))
            for row in checkpoints[1:]:
                current=struct.unpack('<8Q',raw.read(row['witness'],64))
                require(current[1:3]==first[1:3] and current[6:]==first[6:] and
                    (current[0]!=3 or current[3:6]==first[3:6]),'BR same allocation throughout realloc/release')
        mask=sum(1<<n for n in (4,5,6,9,15,20,22,40,41,42,49,50,51,52,53,54,55,58))
        require(struct.unpack('<4Q',bytes.fromhex(start['profile']))[1]==mask,'BR exact existing session rights')
        if spec[1]==15 and start['run']==1:
            require(phases in ([],[1],[1,2]),'BR owner loss bounded progress')
        else:
            mode=mode_for(spec,start)
            require(phases==([1,2] if mode==0 else [1,3,2] if mode==1 else [1]),'BR complete phase order')
        require((receipts[gen]['status'],receipts[gen]['state'])==outcome(spec,start),'BR exact C++ outcome')
        grants=[r for r in events if r['kind']=='call' and r['op']==55 and r['args'][1]==gen]
        require(not grants,'BR no borrowed object authority')
        if outcome(spec,start)==(0,4):
            calls=[r for r in events if r['kind']=='return' and r['gen']==gen and r['op'] in range(49,56)]
            require([(r['op'],r['result']) for r in calls]==
                [(49,0),(53,0),(54,-11),(52,0),(52,-9),(49,0),(53,-9),(53,0),(54,-11),(52,0)],
                'BR exact owned endpoint lifecycle/stale rejection')
            handles=[struct.unpack('<I',bytes.fromhex(r['after']))[0] for r in calls if r['op']==49]
            require(handles[0] and handles[1] and handles[0]!=handles[1],'BR fresh endpoint generations')
            require([r['args'][0] for r in calls if r['op']!=49]==
                [handles[0]]*5+[handles[1]]*3,'BR move/adopt ownership has no duplicate close')

def validate_reaped(row,starts,live,raw):
    gen=row['gen'];require(gen in live and row['slot']==4 and starts[gen]['run']==row['run'] and
        apps.tool_name(starts[gen])=='cpptest','BR live generation before image reap')
    data=raw.read(row['raw'],128+5120+12288)
    require(struct.unpack_from('<8Q',data)==(0,gen,0,0,0,0x20000000,0,0) and
        not any(data[64:]),'BR actual heap control/regions/tables reaped')

def validate_io(module,spec,*args):
    source=inspect.getsource(wide.namespace().validate_io_and_faults)
    changes=[
        ('expected_count=4 if case==6 and run==1 else 0 if case==16 and run==1 else 1','expected_count=len(tools_for(spec,run))'),
        ('expected=(134,3) if case==12 and run==1 else (256,3) if case==13 and run==1 else (0,3) if case in (14,15) and run==1 else (82,4)','expected=cpp_outcome(spec,app_start)'),
        ("written==(b'SESSION64\\n' if expected==(82,4) else b'')","written==cpp_output(spec,app_start,app_files)"),
        ("struct.unpack_from('<Q',request,32)[0]==1000","0<struct.unpack_from('<Q',request,32)[0]<=1000"),
        ('reason=0 if expected[1]==4 else 2 if case==14 and run==1 else 1','reason=0 if expected[1]==4 else 2 if mode_for(spec,app_start)==5 else 1'),
        ('case==14 and run==1','mode_for(spec,app_start)==5'),
        ("            reads=[r for r in root_io if r['op']==15 and r['result']>0]\n            require(reads and reads[0]['now']-root['now']>=5000 and attempts.get(root['gen'],0)>8,'persistent idle and cumulative construction proof')",
         "            require(attempts.get(root['gen'],0)>8,'BR repeated construction accounting')"),
        ('expected_faults={7:[2],9:[3],12:[4],15:[0],16:[3,3,3]}.get(case,[])','expected_faults=[4] if spec[3]==4 else [0] if case==15 else []')]
    for before,after in changes:
        if before=='case==14 and run==1':
            require(source.count(before)==2,'BR exact timeout predicates');source=source.replace(before,after)
        else:source=replace(source,before,after)
    ns=dict(vars(module),spec=spec,tools_for=tools_for,cpp_outcome=outcome,cpp_output=output,mode_for=mode_for)
    exec(compile(source,'<BR-exact-foreground-outcomes>','exec'),ns);ns['validate_io_and_faults'](*args)
    events=args[0]
    for run in (1,2):
        require(tuple(apps.tool_name(r) for r in events if r['kind']=='start' and r['run']==run and r['slot']==4)==tools_for(spec,run),'BR ordinary command order')

def namespace(label):
    spec=spec_for(label);source=selected_source();filename='<reist-cpp-runtime-'+label+'>'
    module=types.ModuleType('_reist_cpp_runtime_'+label.replace('-','_'));module.__file__=filename
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename);sys.modules[module.__name__]=module
    exec(compile(source,filename,'exec'),module.__dict__)
    prior=wide.namespace();module.ROOT=ROOT;module.file=types.SimpleNamespace(**vars(prior.file))
    module.file.media=types.SimpleNamespace(LAYOUTS=apps.media.LAYOUTS,image=lambda layout,program:media.image(layout,program))
    module.native_cpu_trace=prior.native_cpu_trace
    for name in ('wide_serial_capture','lossless_observer','decode_evidence'):setattr(module,name,getattr(prior,name))
    module.CASES=((spec[1],2,spec[2]),);module.input_plan=lambda unused:input_plan(label)
    objects=object_namespace();module.fs_expected_response=objects['fs_expected_response'];module.validate_objects=objects['validate_objects']
    for name in ('matching_record','entry_record','validate_cpp_selection','validate_checkpoint','validate_cpp_history','validate_reaped'):
        setattr(module,name,globals()[name])
    module.tool_name=apps.tool_name;module.validate_probe_selection=apps.validate_probe_selection
    original=module.observer_body
    def observer_body(*args,**kwargs):
        body=original(*args,**kwargs)
        # Disable the user breakpoint before pages are released or reused.
        body=replace(body,'def before_release():','def before_release():\n    cpp_checkpoint.enabled=False')
        body=replace(body,"    if gen in pending:emit('abandoned',**pending.pop(gen))",
            "    if starts.get(gen,{}).get('cpp'):\n"
            "        hp=CS['native_heap_state']+232+slot*99368\n"
            "        emit('cpp_reaped',gen=gen,slot=slot,run=runs+1,raw=snapshot(mem(hp,128)+mem(hp+552,5120)+mem(hp+32808,12288)))\n"
            "    if gen in pending:emit('abandoned',**pending.pop(gen))")
        return body+'\n'+CHECKPOINT
    module.observer_body=observer_body
    module.validate_io_and_faults=lambda *args:validate_io(module,spec,*args)
    return module

def image_config(image,label):
    config,records,files=apps.image_config(image,'ext2-1k')
    catalog=(Path(image).parent/'boot-programs.bin').read_bytes()
    folders=[p for p in Path(image).parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    require(len(folders)==1,'BR unique native sysroot');folder=folders[0]
    files['cpptest.prg']=(folder/'root/cpptest.prg').read_bytes();admit(files)
    require(files['cpptest.prg']==(folder/'cpptest.prg').read_bytes(),'BR exact packaged consumer')
    records[8]=wide.old.admission.wide.producer.prepare(files['cpptest.prg'],[],True)
    symbols={name:wide.old.file.block.map_symbol(folder/'cpp.map','reist_cpp_runtime_'+name) for name in ('selection','checkpoint','witness')}
    config.update({ 'cpp_'+name:value for name,value in symbols.items()})
    config.update(cpp_mode=spec_for(label)[3],app_case=label,probe_modes=())
    return config,records,files

def bounded_fixture(folder,files,started):
    cls=wide.old.file.pio.Fixture;fixture=cls.__new__(cls);fixture.started=started
    fixture.expected=lambda:media.image('ext2-1k',files)
    source=textwrap.dedent(inspect.getsource(wide.Fixture.run))
    source=replace(source,'limit=900 if self.wide_full else 300','limit=180')
    ns=dict(vars(wide));exec(compile(source,'<BR-180s-media>','exec'),ns)
    fixture.run=types.MethodType(ns['run'],fixture)
    cls.__init__(fixture,folder,filesystem='ext2-1k',file_program=files['boot.prg'])
    return fixture

def run_case(image,folder,label):
    image=Path(image).resolve();folder=Path(folder).resolve();spec=spec_for(label)
    require(image.is_relative_to(ROOT/'build') and folder.is_relative_to(ROOT/'build/codex-agent') and not folder.exists(),'BR fresh guest scope')
    module=namespace(label);config,records,files=image_config(image,label);module.app_files=files
    folder.mkdir(parents=True);started=time.monotonic();row=dict(label=label,passed=False,closed=False)
    try:
        code=module.observer(config,records,folder,spec[1],2)
        fixture=bounded_fixture(folder,files,started)
        module.stepped_capture_namespace(started)['capture'](image,folder,code,spec[2],fixture,
            binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True,console_input=input_plan(label))
        row['guest_elapsed']=time.monotonic()-started;require(row['guest_elapsed']<=180,'BR whole guest lease')
        row['proof']=module.evaluate(folder,config,records,(image.parent/'boot-programs.bin').read_bytes(),spec[1],2,files)
        row['passed']=True;return row
    except BaseException as error:row['error']=str(error);raise
    finally:
        row.update(closed=True,elapsed=time.monotonic()-started)
        with (folder/'summary.json').open('x',encoding='utf-8') as out:json.dump(row,out,indent=2,sort_keys=True)
