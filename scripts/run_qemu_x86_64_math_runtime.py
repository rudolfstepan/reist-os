"""BS numeric/FP evidence extending the accepted complete shell proof."""
from pathlib import Path
import inspect,linecache,struct,sys,types
import run_qemu_x86_64_cpp_runtime as prior
import build_x86_64_math_runtime_media as media
import check_x86_64_math_runtime_media as check
apps=prior.apps
wide=apps.wide
ROOT=apps.ROOT
require=apps.require
replace=wide.replace
CASES=(('healthy4g',0,4096,0),('healthy8g',5,8192,0),
       ('rounding-state',0,4096,1),('x87-fault',0,4096,2),
       ('mxcsr-fault',0,4096,3),('crash',0,4096,4),('hang',0,4096,5),
       ('cpu',0,4096,6),('owner-loss',15,4096,0),('repeated',6,4096,0))
OK=b'MATH_NUMERIC_OK functions=44\nMATH_FENV_OK rounding=4\nMATH_LP64_OK\nMATH_FP_STATE_OK\nMATH_RUNTIME_OK\n'
MAGIC=0x314854414d545352

def spec_for(label):
    found=[s for s in CASES if s[0]==label]
    require(len(found)==1,'BS explicit case');return found[0]

def input_plan(label):
    spec=spec_for(label)
    first=b'mathtest\n' if spec[1]==15 else (b'mathtest\n' if spec[1]==6 else b'')+b'mathtest\ncat /data.txt\nexit\n'
    second=b'mathtest\n'+(b'cat /data.txt\n' if spec[1]==15 else b'')+b'ls -1 /\nexit\n'
    return ((0,first),),((0,second),)

def tools_for(spec,run):
    if run==1 and spec[1]==15:return ('mathtest',)
    if run==1:return (('mathtest',) if spec[1]==6 else ())+('mathtest','cat')
    return ('mathtest',)+(('cat',) if spec[1]==15 else ())+('ls',)

def mode_for(spec,start):return spec[3] if start['run']==1 and apps.tool_name(start)=='mathtest' else 0

def outcome(spec,start):
    if spec[1]==15 and start['run']==1:return 0,3
    return {0:(0,4),1:(0,4),2:(144,3),3:(141,3),4:(134,3),5:(0,3),6:(256,3)}[mode_for(spec,start)]

def output(spec,start,files):
    if spec[1]==15 and start['run']==1:return b''
    name=apps.tool_name(start)
    if name=='mathtest':return OK if mode_for(spec,start)<2 else b''
    if name=='cat':return files['data.txt']
    if name=='probe':return b'APP_OBJECT_PROBE_OK\n'
    require(name=='ls','BS explicit output');return b''.join(n.encode()+b'\n' for n in check.NAMES)

def admit(files):
    require(type(files) is dict and set(files)==set(check.NAMES),'BS exact seven files')
    prior.admit({n:files[n] for n in prior.check.NAMES})
    check.validate_cpp_object(files['mathtest.prg'],architecture='x86_64')

def object_namespace():
    ns=dict(vars(apps));ns['media']=types.SimpleNamespace(NAMES=check.NAMES,admit=admit)
    for name in ('info','fs_expected_response','expected_reply','validate_capture_before_grant'):
        ns[name]=prior.rebound(getattr(apps,name),ns)
    source=inspect.getsource(apps.validate_objects)
    source=replace(source,"r['run']==run and r['slot']==4]","r['run']==run and r['slot']==4 and tool_name(r)!='mathtest']")
    ns['case_spec']=lambda label:('ext2-1k',spec_for(label)[1],2,spec_for(label)[2],())
    exec(compile(source,'<BS-retained-object-proof>','exec'),ns)
    return ns

matching_record=prior.matching_record

def entry_record(row,raw,records):
    if row['slot']!=4:return records[row['slot']]
    name=apps.tool_name(row);require(name in ('cat','ls','probe','mathtest'),'BS foreground executable')
    return records[dict(cat=5,ls=6,probe=7,mathtest=8)[name]]

SELECTION=prior.SELECTION.replace('cpp','math').replace('cpptest','mathtest').replace('0x3150504354525352','0x314854414d545352')
# Capture the kernel's initial state before any user instruction executes.
SELECTION=SELECTION.replace("        math_checkpoint.enabled=True", "        math_checkpoint.enabled=True\n        emit('math_fresh',gen=gen,run=runs+1,slot=slot,raw=snapshot(mem(S['scheduler_fp_states']+slot*512,512)))")

CHECKPOINT='''
class MathCheckpoint(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(CONFIG['math_checkpoint']),internal=True)
        self.enabled=False;self.count=0
    def stop(self):
        try:
            self.count+=1;assert self.count<=15
            slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
            assert mode()==8 and slot==4 and starts[gen]['live'] and starts[gen].get('math')
            assert reg('rip')==CONFIG['math_checkpoint'] and reg('cr3')&MASK==t[2]&MASK
            w=struct.unpack('<16Q',user(t,CONFIG['math_witness'],128))
            with (OUT/'math-checkpoint-debug.jsonl').open('a') as debug:
                debug.write(json.dumps(dict(gen=gen,run=runs+1,rip=reg('rip'),rsp=reg('rsp'),
                    flags=reg('eflags'),caller=user(t,reg('rsp'),8).hex(),witness=list(w)))+'\\n')
            math_block.enabled=w[0]==1 or w[0]==2 and w[12]<3
            emit('math_checkpoint',gen=gen,run=runs+1,slot=slot,pc=reg('rip'),root=t[2],
                 witness=snapshot(user(t,CONFIG['math_witness'],128)),
                 wanted=snapshot(user(t,CONFIG['math_wanted'],512)),
                 observed=snapshot(user(t,CONFIG['math_observed'],512)))
        except BaseException as error:
            import traceback
            gdb.write(traceback.format_exc());emit('OBSERVER_FAIL',where='math checkpoint',error=str(error)[:256])
            gdb.execute('quit 71')
        return False
math_checkpoint=MathCheckpoint()
class MathBlock(gdb.Breakpoint):
    def __init__(self):
        super().__init__('*'+hex(S['process_run_dispatch64']),internal=True)
        self.enabled=False;self.count=0
    def stop(self):
        try:
            slot=d(S['scheduler_current_slot']);t=task(slot);gen=t[1]
            if slot!=4 or not starts.get(gen,{}).get('math') or t[0]!=6:return False
            self.enabled=False;self.count+=1;assert self.count<=12
            assert q(S['syscall_rax'])==41 and q(S['syscall_rdi'])==10
            emit('math_blocked',gen=gen,run=runs+1,slot=slot,
                 task=snapshot(mem(S['scheduler_tasks']+slot*1024,1024)),
                 syscall=snapshot(mem(S['syscall_rax'],120)),
                 membership=mem(S['scheduler_deadline_membership']+slot,1).hex(),
                 wanted=snapshot(user(t,CONFIG['math_wanted'],512)),
                 saved=snapshot(mem(S['scheduler_fp_states']+slot*512,512)))
        except BaseException as error:
            emit('OBSERVER_FAIL',where='math blocked',error=str(error)[:256]);gdb.execute('quit 71')
        return False
math_block=MathBlock()
'''

def selected_source():
    source=apps.selected_source()
    for before,after in (
        ('slot not in (2,3,4,5,6,7)','slot not in (2,3,4,5,6,7,8)'),
        ('set(references)!={2,3,4,5,6,7}','set(references)!={2,3,4,5,6,7,8}'),
        ('[records[n] for n in (4,5,6,7)]','[records[n] for n in (4,5,6,7,8)]'),
        ('\ndef syscall(denied=False):',SELECTION+'\ndef syscall(denied=False):'),
        ("elif kind=='app_selection':", "elif kind.startswith('math_'):validate_math_event(row,starts,live,config,raw)\n        elif kind=='app_selection':"),
        ('frame[15:17]==(6,0)',"frame[15:17]==(math_vector(config,row),0)"),
        ('    validate_objects(combined,receipts,layout,app,config)',
         '    validate_objects(combined,receipts,layout,app,config)\n    validate_math_history(combined,receipts,config,raw)'),
        ('elapsed<297','elapsed<177'),('now<started+297','now<started+177'),
        ("'deadline=console_started+297'","'deadline=console_started+177'"),
        ("'time.monotonic()-console_started>300'","'time.monotonic()-console_started>180'"),
        ("'time.monotonic()-capture_started>300'","'time.monotonic()-capture_started>180'"),
        ('from run_qemu_x86_64_wide_file import configure_binary as configure',
         'from run_qemu_x86_64_math_runtime import configure_binary as configure')):
        source=replace(source,before,after)
    return source

configure_binary=prior.configure_binary

def math_vector(config,row):
    return {2:16,3:13,4:6}.get(config['math_mode'],6) if row['slot']==4 else 6

def fp_payload(mode):
    data=bytearray(512);struct.pack_into('<H',data,0,0x37f|mode);data[4]=255
    struct.pack_into('<I',data,24,0x1f80|(mode<<3))
    for n in range(8):
        data[32+16*n]=n+1;data[39+16*n]=128;data[40+16*n]=255;data[41+16*n]=63
    data[160:416]=bytes((n+0x31)&255 for n in range(256))
    return bytes(data)

def fp_equal(actual,wanted):
    require(len(actual)==len(wanted)==512,'BS FP extent')
    require(actual[:28]==wanted[:28] and actual[160:416]==wanted[160:416] and
            all(actual[32+n*16:42+n*16]==wanted[32+n*16:42+n*16] for n in range(8)),
            'BS x87/control/XMM0..15 preserved')

def validate_math_event(row,starts,live,config,raw):
    gen=row['gen'];require(gen in live and apps.tool_name(starts[gen])=='mathtest' and
        row['run']==starts[gen]['run'],'BS live numeric generation')
    kind=row['kind']
    if kind=='math_selection':
        selected=config['math_mode'] if row['run']==1 else 0
        require(bytes.fromhex(row['before'])==struct.pack('<2Q',MAGIC,0) and
                bytes.fromhex(row['after'])==struct.pack('<2Q',MAGIC,selected),'BS private selection');return
    require(row['slot']==4,'BS numeric slot')
    if kind=='math_fresh':
        data=raw.read(row['raw'],512);wanted=bytearray(512)
        struct.pack_into('<H',wanted,0,0x37f);struct.pack_into('<I',wanted,24,0x1f80)
        require(data==bytes(wanted),'BS fresh zero payload/default controls');return
    if kind=='math_reaped':
        require(not any(raw.read(row['raw'],512)),'BS actual FP generation scrub');return
    if kind=='math_blocked':
        task=struct.unpack('<128Q',raw.read(row['task'],1024))
        origin=struct.unpack('<128Q',raw.read(starts[gen]['task'],1024))
        call=struct.unpack('<15Q',raw.read(row['syscall'],120))
        require(task[:3]==(6,gen,origin[2]) and (call[0],call[6])==(41,10) and
                row['membership']=='01','BS actual blocked sleep/deadline membership')
        fp_equal(raw.read(row['saved'],512),raw.read(row['wanted'],512));return
    require(kind=='math_checkpoint' and row['pc']==config['math_checkpoint'],'BS checkpoint PC/kind')
    task=struct.unpack('<128Q',raw.read(starts[gen]['task'],1024))
    require(row['root']==task[2],'BS numeric address space')
    w=struct.unpack('<16Q',raw.read(row['witness'],128))
    require(w[0] in (1,2) and abs(w[1]-0x3fdeaee8744b05f0)<=4 and
        abs(w[2]-0x3ff6a09e667f3bcd)<=1 and w[3:10]==
        (1<<40,(-(1<<40))&((1<<64)-1),1,1<<63,44,8,8) and not any(w[13:]),
        'BS actual binary64/LP64 numeric results')
    wanted=raw.read(row['wanted'],512);observed=raw.read(row['observed'],512)
    # Earlier diagnostics also captured a post-resume kernel image. Consume its
    # bound bytes for complete historical snapshot accounting; preservation is
    # established at math_blocked, before user code restores ABI defaults.
    if 'saved' in row:raw.read(row['saved'],512)
    if w[0]==1:
        require(not any(w[10:]) and not any(wanted+observed),'BS initial witness');return
    require(w[10] in (0,0x400,0x800,0xc00) and w[11]==0 and w[12]<4,'BS completed roundtrip')
    require(wanted==fp_payload(w[10]),'BS independently expected FP payload')
    fp_equal(observed,wanted)
    # Kernel state is checked at the actual blocked transition. A timer after
    # the consumer restores ABI defaults may legitimately replace it here.

def validate_math_history(events,receipts,config,raw):
    spec=spec_for(config['app_case'])
    for start in events:
        if start['kind']!='start' or start['slot']!=4 or apps.tool_name(start)!='mathtest':continue
        gen=start['gen'];rows=[r for r in events if r.get('gen')==gen and r['kind'].startswith('math_')]
        kinds=[r['kind'] for r in rows]
        require(kinds[:2]==['math_fresh','math_selection'] and kinds[-1:] == ['math_reaped'],
                'BS complete selected generation lifecycle')
        checkpoints=[r for r in rows if r['kind']=='math_checkpoint']
        blocks=[r for r in rows if r['kind']=='math_blocked']
        lost=spec[1]==15 and start['run']==1
        require((len(checkpoints)<=5 if lost else len(checkpoints)==5) and
                (len(blocks)<=4 if lost else len(blocks)==4) and
                len(rows)==len(checkpoints)+len(blocks)+3,'BS exact checkpoint/lifecycle counts')
        order=[0xc00,0x800,0x400,0] if mode_for(spec,start)==1 else [0,0x400,0x800,0xc00]
        for n,row in enumerate(checkpoints):
            w=struct.unpack('<16Q',raw.read(row['witness'],128))
            require(w[0]==(1 if n==0 else 2) and (n==0 or (w[10],w[12])==(order[n-1],n-1)),
                    'BS all four modes in selected order')
        for n,row in enumerate(blocks):
            require(raw.read(row['wanted'],512)==fp_payload(order[n]),'BS blocked rounding order')
            require(rows.index(checkpoints[n])<rows.index(row) and
                    (n+1==len(checkpoints) or rows.index(row)<rows.index(checkpoints[n+1])),
                    'BS blocking occurs between numeric checkpoints')
        require((receipts[gen]['status'],receipts[gen]['state'])==outcome(spec,start),'BS numeric outcome')
        require(not any(r['kind']=='call' and r['op']==55 and r['args'][1]==gen for r in events),
                'BS no borrowed object authority')

def validate_io(module,spec,*args):
    source=inspect.getsource(prior.validate_io)
    source=source.replace('cpp_outcome','math_outcome').replace('cpp_output','math_output')
    source=source.replace("spec[3]==4", "spec[3] in (2,3,4)")
    ns=dict(globals());exec(compile(source,'<BS-exact-foreground-outcomes>','exec'),ns)
    ns['validate_io'](module,spec,*args)

def namespace(label):
    spec=spec_for(label);source=selected_source();filename='<reist-math-runtime-'+label+'>'
    module=types.ModuleType('_reist_math_runtime_'+label.replace('-','_'));module.__file__=filename
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename);sys.modules[module.__name__]=module
    exec(compile(source,filename,'exec'),module.__dict__)
    old=wide.namespace();module.ROOT=ROOT;module.file=types.SimpleNamespace(**vars(old.file))
    module.file.media=types.SimpleNamespace(LAYOUTS=apps.media.LAYOUTS,image=lambda layout,program:media.image(layout,program))
    for name in ('native_cpu_trace','wide_serial_capture','lossless_observer','decode_evidence'):setattr(module,name,getattr(old,name))
    module.CASES=((spec[1],2,spec[2]),);module.input_plan=lambda unused:input_plan(label)
    objects=object_namespace();module.fs_expected_response=objects['fs_expected_response'];module.validate_objects=objects['validate_objects']
    for name in ('matching_record','entry_record','validate_math_event','validate_math_history','math_vector'):setattr(module,name,globals()[name])
    module.tool_name=apps.tool_name;module.validate_probe_selection=apps.validate_probe_selection
    original=module.observer_body
    def observer_body(*args,**kwargs):
        body=original(*args,**kwargs)
        body=replace(body,'def before_release():','def before_release():\n    math_checkpoint.enabled=math_block.enabled=False')
        body=replace(body,"            starts[r['gen']]['live']=False",
            "            if starts[r['gen']].get('math'):\n"
            "                emit('math_reaped',gen=r['gen'],slot=r['slot'],run=runs+1,raw=snapshot(mem(S['scheduler_fp_states']+r['slot']*512,512)))\n"
            "            starts[r['gen']]['live']=False")
        return body+'\n'+CHECKPOINT
    module.observer_body=observer_body
    module.validate_io_and_faults=lambda *args:validate_io(module,spec,*args)
    return module

def image_config(image,label):
    config,records,files=apps.image_config(image,'ext2-1k')
    catalog=(Path(image).parent/'boot-programs.bin').read_bytes()
    folders=[p for p in Path(image).parent.glob('programs-*') if (p/'boot-programs.bin').is_file() and (p/'boot-programs.bin').read_bytes()==catalog]
    require(len(folders)==1,'BS unique native sysroot');folder=folders[0]
    for name in ('cpptest.prg','mathtest.prg'):
        files[name]=(folder/'root'/name).read_bytes()
        require(files[name]==(folder/name).read_bytes(),'BS exact packaged consumer')
    admit(files);records[8]=wide.old.admission.wide.producer.prepare(files['mathtest.prg'],[],True)
    for name in ('selection','checkpoint','witness','wanted','observed'):
        symbol='reist_math_runtime_'+name if name in ('selection','checkpoint','witness') else 'reist_math_fp_'+name
        config['math_'+name]=wide.old.file.block.map_symbol(folder/'math.map',symbol)
    config.update(math_mode=spec_for(label)[3],app_case=label,probe_modes=())
    return config,records,files

# Rebind the accepted bounded capture/fixture code to this module's exact media,
# observer and case specifications. No shared module or acceptance rule mutates.
bounded_fixture=prior.rebound(prior.bounded_fixture,dict(vars(prior),media=media))
run_case=prior.rebound(prior.run_case,dict(vars(prior),**globals()))


def hardware_bootstrap(command,folder,image):
    """Explicit WHPX qualification only: bounded pre-task pause and transcript."""
    import json,socket,time
    from qemu_binary_memory import QMP
    from run_qemu_x86_64_boot_programs import symbols
    started=time.monotonic();deadline=started+10
    endpoint=command[command.index('-qmp')+1]
    require(endpoint.startswith('tcp:127.0.0.1:') and endpoint.endswith(',server=on,wait=off'),
            'BS hardware loopback QMP')
    port=int(endpoint.split(':')[2].split(',')[0]);name=command[command.index('-name')+1]
    s=symbols(image);physical=s['native_math_hardware_ready']-0xffffffff80000000
    require(s['native_math_hardware_release']==s['native_math_hardware_ready']+8 and
            0x100000<=physical<0x8000000-16,'BS fixed bootstrap cells')
    transcript=dict(physical=physical,commands=[],reads=[],passed=False)
    class BootstrapQMP(QMP):
        def request(self,command,arguments):
            require(command in ('qmp_capabilities','query-name','query-status','pmemsave','cont','stop'),
                    'BS bootstrap command authority')
            self.identifier+=1;require(self.identifier<=140,'BS bootstrap command capacity')
            until=min(deadline,time.monotonic()+.5)
            self.peer.settimeout(self.remaining(until))
            self.peer.sendall(json.dumps(dict(execute=command,arguments=arguments,id=self.identifier)).encode()+b'\n')
            for _ in range(32):
                row=self.receive(until)
                if 'event' in row and not {'id','return','error'}&row.keys():continue
                require(row.get('id')==self.identifier and 'return' in row and 'error' not in row,
                        'BS bootstrap QMP reply')
                transcript['commands'].append(dict(command=command,result=row['return']))
                return row['return']
            raise ValueError('BS bootstrap QMP event bound')
    peer=None
    try:
        for _ in range(128):
            require(time.monotonic()<deadline,'BS bootstrap connect deadline')
            try:peer=BootstrapQMP(port,name,deadline);break
            except (ConnectionRefusedError,TimeoutError):time.sleep(.02)
        require(peer is not None,'BS bootstrap QMP connection')
        status=peer.request('query-status',{})
        require(status.get('running') is False and status.get('status')=='prelaunch','BS initial paused VM')
        require(peer.request('cont',{})=={},'BS bootstrap start')
        def read(index):
            target=folder/('hardware-cells-%03d.bin'%index)
            peer.save(physical,16,target)
            raw=target.read_bytes();require(len(raw)==16,'BS bootstrap fixed extent')
            values=struct.unpack('<2Q',raw)
            transcript['reads'].append(dict(file=target.name,values=values))
            require(values in ((0,0),(1,0)),'BS bootstrap fail closed')
            return values
        for index in range(127):
            if read(index)==(1,0):break
            time.sleep(.02)
        else:raise ValueError('BS bootstrap ready bound')
        require(peer.request('stop',{})=={},'BS bootstrap stop')
        peer.stopped();require(read(127)==(1,0),'BS stopped bootstrap cells')
        transcript['passed']=True
    finally:
        if peer:peer.close()
        transcript['elapsed']=time.monotonic()-started
        with (folder/'hardware-bootstrap.json').open('x',encoding='utf-8') as out:json.dump(transcript,out,indent=2)


def portable_toolchain(binding):
    """Admit one explicit workspace verifier and all its local binary inputs."""
    import json,hashlib
    binding=Path(binding).resolve()
    require(binding.is_relative_to(ROOT/'build/codex-agent') and binding.stat().st_size<=65536,
            'BS portable binding scope')
    row=json.loads(binding.read_text(encoding='utf-8'))
    def check(path,pin):
        path=Path(path).resolve()
        require(path.is_relative_to(binding.parent) and path.is_file() and
                hashlib.sha256(path.read_bytes()).hexdigest()==pin,'BS portable binary binding')
        return path
    exe=check(row['executable'],row['sha256'])
    require(exe.name=='qemu-system-x86_64.exe' and len(row['dlls'])<=96 and
            1<=len(row['firmware'])<=256,'BS portable input bounds')
    for name,data in row['dlls'].items():check(exe.parent/name,data['sha256'])
    firmware=Path(row['firmware_directory']).resolve()
    for name,pin in row['firmware'].items():check(firmware/name,pin)
    check(binding.parent/row['compiler_freeze_file'],row['compiler_freeze'])
    return exe,firmware


def hardware_namespace(label,*,toolchain=None,profile=False):
    """Install the original complete observer after the opt-in pre-task gate."""
    module=namespace(label);source=inspect.getsource(module.capture_namespace)
    marker='        source=inspect.getsource(function)'
    before='            debugger=subprocess.Popen('
    after=('            from run_qemu_x86_64_math_runtime import hardware_bootstrap\n'
           '            hardware_bootstrap(command,folder,image)\n'+before)
    extra=(marker+'\n        if function is boot._capture_run:\n'
        +'            source=once(source,"\'-machine\',\'pc,accel=tcg\'","\'-machine\',\'pc\',\'-accel\',\'whpx,kernel-irqchip=off\'")\n'
        +'            source=once(source,'+repr(before)+','+repr(after)+')')
    source=replace(source,marker,extra);filename='<BS-WHPX-bounded-capture>'
    if toolchain is not None:
        exe,firmware=portable_toolchain(toolchain)
        marker='    for function in (boot._capture_run,boot._capture,boot.capture):'
        source=replace(source,marker,'    ns[\'resolve_qemu\']=lambda unused:Path('+repr(str(exe))+')\n'+marker)
        marker='        source=inspect.getsource(function)'
        addition=(marker+'\n        if function is boot._capture_run:\n'
            +'            source=once(source,"    command+=binary_arguments",'
            +repr('    command+=binary_arguments\n    command+='+repr(['-L',str(firmware)]))+')')
        source=replace(source,marker,addition)
    linecache.cache[filename]=(len(source),None,source.splitlines(True),filename)
    exec(compile(source,filename,'exec'),module.__dict__)
    original=module.observer
    def observer(config,*args,**kwargs):
        code=original(config,*args,**kwargs)
        if toolchain is None:
            code=replace(code,'set breakpoint always-inserted on\n','set breakpoint always-inserted off\n')
        else:require('set breakpoint always-inserted on\n' in code,'BS registered execution probes')
        code='set remote software-breakpoint-packet on\n'+code
        require('gdb.BP_HARDWARE_BREAKPOINT' in code,'BS original execution probes')
        if toolchain is None:code=code.replace('gdb.BP_HARDWARE_BREAKPOINT','gdb.BP_BREAKPOINT')
        else:
            code=replace(code,"super().__init__('*'+hex(CONFIG['math_checkpoint']),internal=True)",
                "super().__init__('*'+hex(CONFIG['math_checkpoint']),type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)")
            code=replace(code,"def reg(n):return int(gdb.parse_and_eval('$'+n))&0xffffffffffffffff",
                "def reg(n):return int(gdb.selected_frame().read_register(n))&0xffffffffffffffff")
        if profile:
            code=replace(code,'def finish():\n    global runs',
                "def finish():\n    global runs\n    math_profile.disable()\n"
                "    math_profile.dump_stats(str(OUT/'observer-first-run.pstats'))\n"
                "    gdb.write('MATH_PROFILE_FIRST_RUN_STOP\\n')\n    gdb.execute('quit 71')")
        code=replace(code,"'received: \"0x7\"'","'received: \"0x1\"'")
        code=replace(code,'cold_step_mode=7','cold_step_mode=1')
        caller_check="            assert caller+struct.unpack('<i',instruction[1:])[0]==S[self.name.replace('_site64','64')],'static probe exact caller'"
        code=replace(code,caller_check,
            "            actual_caller=caller+struct.unpack('<i',instruction[1:])[0]\n"
            "            if actual_caller!=S[self.name.replace('_site64','64')]:\n"
            "                with (OUT/'hardware-caller-error.json').open('x') as f:json.dump(dict(hook=self.name,rip=reg('rip'),rsp=reg('rsp'),caller=caller,instruction=instruction.hex(),actual=actual_caller,expected=S[self.name.replace('_site64','64')]),f)\n"
            +caller_check)
        gate=config['s']['native_math_hardware_gate64.wait']
        end=config['s']['native_math_hardware_gate64.failed']
        ready=config['s']['native_math_hardware_ready'];release=ready+8
        code=replace(code,'def boot():',f"def boot():\n    cleared=mem({ready},16)\n    with (OUT/'hardware-cleared.bin').open('xb') as f:assert f.write(cleared)==16\n    assert cleared==bytes(16),'one-shot hardware gate cleared'")
        code=replace(code,'    assert mem(base,4096)==bytes([195])*7+bytes([144])*4089',
            "    hardware_page=mem(base,4096)\n"
            "    with (OUT/'hardware-probe-page.bin').open('xb') as f:assert f.write(hardware_page)==4096\n"
            "    assert hardware_page==bytes([195])*7+bytes([144])*4089")
        prelude=(f"assert {gate} <= int(gdb.parse_and_eval('$rip')) < {end}\n"
            +"assert int(gdb.parse_and_eval('$cs'))==8 and int(gdb.parse_and_eval('$cr0'))&0x80010000==0x80010000\n"
            +"assert int(gdb.parse_and_eval('$cr3'))>0\n"
            +f"assert bytes(gdb.selected_inferior().read_memory({ready},16))==struct.pack('<2Q',1,0)\n")
        # All constructors precede this sole write. No program counter changes.
        tail=(prelude+f"gdb.selected_inferior().write_memory({release},struct.pack('<Q',1))\n"
            +f"assert bytes(gdb.selected_inferior().read_memory({ready},16))==struct.pack('<2Q',1,1)\n"
            +"gdb.write('MATH_HARDWARE_BOOTSTRAP_V1 '+json.dumps(dict(rip=int(gdb.parse_and_eval('$rip')),cr0=int(gdb.parse_and_eval('$cr0')),cr3=int(gdb.parse_and_eval('$cr3')),release=1))+'\\n')\n")
        if profile:tail+='import cProfile\nmath_profile=cProfile.Profile()\nmath_profile.enable()\n'
        return replace(code,'\nend\ncontinue\n','\n'+tail+'end\ncontinue\n')
    module.observer=observer
    return module


run_hardware_case=prior.rebound(run_case,dict(run_case.__globals__,namespace=hardware_namespace))


def run_portable_hardware_case(image,folder,label,binding,*,profile=False):
    fn=prior.rebound(run_case,dict(run_case.__globals__,namespace=lambda name:hardware_namespace(name,toolchain=binding,profile=profile)))
    return fn(image,folder,label)


def validate_hardware_bootstrap(folder,config,*,require_cleared=True):
    """Replay actual QMP cells, release registers and pristine execution probes."""
    import json
    folder=Path(folder);row=json.loads((folder/'hardware-bootstrap.json').read_text())
    require(row['passed'] is True and 0<row['elapsed']<=10,'BS bounded hardware bootstrap')
    require(row['physical']==config['s']['native_math_hardware_ready']-0xffffffff80000000,
            'BS bootstrap physical binding')
    commands=row['commands'];reads=row['reads']
    require(7<=len(commands)<=140 and 1<=len(reads)<=128,'BS bootstrap transcript bounds')
    names=[r['command'] for r in commands]
    require(names[:4]==['qmp_capabilities','query-name','query-status','cont'] and
            names[-3:]==['stop','query-status','pmemsave'] and
            names[4:-3]==['pmemsave']*(len(reads)-1),'BS bootstrap exact command order')
    require(commands[2]['result']==dict(status='prelaunch',running=False) and
            commands[-2]['result']==dict(status='paused',running=False),'BS bootstrap paused states')
    for index,read in enumerate(reads):
        name='hardware-cells-%03d.bin'%(127 if index==len(reads)-1 else index)
        require(read['file']==name and read['values'] in ([0,0],[1,0]) and
                (folder/name).read_bytes()==struct.pack('<2Q',*read['values']),
                'BS bootstrap raw cell binding')
    require(reads[-1]['values']==[1,0],'BS ready while paused')
    trace=wide.decode_evidence((folder/'frame-trace.log').read_text(encoding='utf-8'))
    releases=[json.loads(line[len('MATH_HARDWARE_BOOTSTRAP_V1 '):]) for line in trace.splitlines()
              if line.startswith('MATH_HARDWARE_BOOTSTRAP_V1 ')]
    require(len(releases)==1,'BS sole bootstrap release')
    r=releases[0];s=config['s']
    require(s['native_math_hardware_gate64.wait']<=r['rip']<s['native_math_hardware_gate64.failed'] and
            r['cr0']&0x80010000==0x80010000 and r['cr3']>0 and r['release']==1,
            'BS actual hardware release registers')
    require((folder/'hardware-probe-page.bin').read_bytes()==bytes([195])*7+bytes([144])*4089,
            'BS pristine hardware probe page')
    if require_cleared:
        require((folder/'hardware-cleared.bin').read_bytes()==bytes(16),'BS raw cleared bootstrap')
        require('WHPX: Failed' not in (folder/'stderr.log').read_text(errors='replace'),
                'BS no ignored hardware verifier error')
        debug_file=folder/'math-checkpoint-debug.jsonl'
        require(debug_file.stat().st_size<=16384,'BS checkpoint debug capacity')
        debug=[json.loads(line) for line in debug_file.read_text().splitlines()]
        checkpoints=[json.loads(line[14:]) for line in trace.splitlines() if line.startswith('SHELL_SESSION ')
                     and json.loads(line[14:]).get('kind')=='math_checkpoint']
        require(1<=len(debug)==len(checkpoints)<=15,'BS complete checkpoint CPU witnesses')
        raw=wide.old.Snapshots(folder)
        for d,c in zip(debug,checkpoints):
            require((d['gen'],d['run'],d['rip'])==(c['gen'],c['run'],c['pc']) and
                    d['rip']==config['math_checkpoint'] and d['flags']&0x100==0 and
                    struct.pack('<16Q',*d['witness'])==raw.read(c['witness'],128),
                    'BS checkpoint CPU/witness correspondence and no leaked TF')
    return dict(physical=row['physical'],reads=len(reads),release=r,cleared=require_cleared)
