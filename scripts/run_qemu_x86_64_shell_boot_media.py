"""Ten finite BIOS integrations; reuse AY's complete raw runtime proof unchanged."""
from pathlib import Path
import hashlib,inspect,json,math,queue,shutil,subprocess,time,types
import check_x86_64_shell_media as check
import run_qemu_x86_64_boot_media as bios
import run_qemu_x86_64_shell_session as ay
ROOT=Path(__file__).resolve().parents[1]
CASES=(('hdd-fallback-recovery','hdd','a-signature',7,4096),
       ('hdd-long','hdd','normal',6,4096),
       ('hdd-healthy','hdd','normal',2,4096),('hdd-8g','hdd','normal',5,8192),
       ('floppy-app-hang','floppy','normal',13,4096),
       ('hdd-signatures','hdd','signatures',None,4096),('hdd-digest','hdd','digest',None,4096),
       ('hdd-manifest','hdd','manifest',None,4096),('floppy-signature','floppy','signatures',None,4096),
       ('floppy-digest','floppy','digest',None,4096))


def boot_arguments(overlay,layout):
    overlay=Path(overlay).absolute()
    check.need(layout in ('hdd','floppy') and overlay==overlay.resolve() and
        overlay.is_relative_to(ROOT/'build/codex-agent') and not any(c in str(overlay) for c in ',\r\n'),'boot attachment scope')
    base=overlay.parent/'base.raw'
    nodes=[{'driver':'file','filename':str(base),'node-name':'az-boot-file','read-only':True},
           {'driver':'raw','file':'az-boot-file','node-name':'az-boot-base','read-only':True},
           {'driver':'qcow2','file':{'driver':'file','filename':str(overlay)},
            'backing':'az-boot-base','node-name':'az-boot'}]
    args=[]
    for node in nodes:args+=['-blockdev',json.dumps(node,separators=(',',':'))]
    return args+(['-device','ide-hd,drive=az-boot,bus=ide.0,unit=1,bootindex=1'] if layout=='hdd' else
                 ['-device','floppy,drive=az-boot,unit=0','-boot','a'])


def validate_bios(serial,layout,case):
    check.need(layout in ('hdd','floppy') and case in ('normal','a-signature','signatures','digest','manifest'),'BIOS case')
    # The AB verified-entry/rejection oracle is unchanged. Its old heap runtime
    # suffix is replaced ONLY by a no-op here; full AY proof is required separately.
    namespace=dict(vars(bios),ipc=types.SimpleNamespace(validate=lambda text,mode: []))
    validator=types.FunctionType(bios.validate.__code__,namespace,bios.validate.__name__)
    return validator(serial,layout,case)


def mutate(source,destination,layout,case):
    check.need(not Path(destination).exists(),'fresh mutated boot base')
    # Old AB digest fault injector had a fixture-only1MiB admission. The boot
    # format already admits these unchanged A/B extents; change no mutation.
    source_code=ay.once(inspect.getsource(bios.mutate),'size<=1048576','size<=1540096')
    namespace=dict(vars(bios));exec(compile(source_code,'<AZ fixed-slot mutation>','exec'),namespace)
    namespace['mutate'](source,destination,layout,case)


class BootMedium:
    def __init__(self,source,folder,layout,case,deadline):
        self.folder=Path(folder);self.folder.mkdir();self.layout=layout;self.deadline=deadline
        self.base=self.folder/'base.raw';self.overlay=self.folder/'disposable.qcow2'
        self.commands=[];self.tool=ay.boot.resolve_qemu(None).parent/'qemu-img.exe'
        if case=='normal':shutil.copyfile(source,self.base)
        else:mutate(source,self.base,layout,case)
        self.expected=check.digest(self.base,536870912 if layout=='hdd' else 1474560)
        self.run('create','-f','qcow2','-F','raw','-b',str(self.base),str(self.overlay))

    def run(self,*args):
        left=self.deadline-time.monotonic();check.need(left>0,'boot media helper deadline')
        result=subprocess.run([str(self.tool),*args],cwd=ROOT,capture_output=True,text=True,timeout=min(10,left),
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.commands.append(dict(args=args,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr))
        (self.folder/'commands.json').write_text(json.dumps(self.commands,indent=2),encoding='utf-8')
        check.need(result.returncode==0,'boot media tool '+result.stderr[-500:]);return result.stdout

    def verify(self,phase):
        result=dict(passed=False,phase=phase)
        try:
            check.need(check.digest(self.base,self.expected['size'])==self.expected,'boot base unchanged')
            info=json.loads(self.run('info','--output=json','-f','qcow2',str(self.overlay)))
            extents=json.loads(self.run('map','--output=json','-f','qcow2',str(self.overlay)))
            check.need(info['format']=='qcow2' and info['virtual-size']==self.expected['size'] and
                Path(info['full-backing-filename'])==self.base and info['backing-filename-format']=='raw','boot backing identity')
            end=0
            for row in extents:
                check.need(row['start']==end and row['length']>0 and row['depth']==1,'boot medium written/incomplete mapping')
                end+=row['length']
            check.need(end==self.expected['size'],'boot complete mapping')
            self.run('compare','-f','qcow2','-F','raw',str(self.overlay),str(self.base))
            result.update(passed=True,base=self.expected,extents=extents,overlay_allocated_data=0)
        finally:(self.folder/(phase+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')


def bios_budget(case):
    check.need(case in ('normal','a-signature'),'positive BIOS case budget')
    return 30 if case=='a-signature' else 20


def entry_phase(record,started,now,case='normal'):
    budget=bios_budget(case)
    check.need(set(record)=={'version','entry','hits','registers','elapsed','guest_started','runtime_started','stop_sha256'},'entry phase fields')
    for name in ('elapsed','guest_started','runtime_started'):
        check.need(type(record[name]) in (int,float) and math.isfinite(record[name]),'finite entry clock')
    runtime=record['runtime_started'];regs=record['registers']
    check.need(record['version']==3 and record['hits']==1 and record['guest_started']==started and
        started<=runtime<=now<started+budget and 0<=record['elapsed']<budget,'actual BIOS/setup phase deadline')
    check.need(type(record['entry']) is int and 0x100000<=record['entry']<0x4000000 and
        regs['rip']==record['entry'] and regs['rax']==0x2badb002 and regs['cr0']&0x80000001==1 and
        regs['rsp']==0x90000 and not regs['eflags']&0x600,'actual first kernel instruction stop')
    return record


def await_entry(started,folder,output,data,overflow,vm,debugger,case='normal'):
    # The old feeder has never been pumped here. Drain, bound and retain all
    # BIOS serial bytes; only an atomically published real stop starts runtime.
    budget=bios_budget(case)
    for _ in range(budget*100+1):
        now=time.monotonic();check.need(now<started+budget,'BIOS/setup deadline')
        for _ in range(128):
            try:data.extend(output.get_nowait())
            except queue.Empty:break
        check.need(not overflow.is_set() and len(data)<=262144,'BIOS serial capacity')
        path=folder/'bios-stop.json'
        if path.exists():
            raw=check.bounded(path,1024);stop=check.object_json(raw)
            check.need(set(stop)=={'version','entry','hits','registers','elapsed','guest_started'} and
                stop['version']==1,'actual stop record')
            record=dict(stop,version=3,runtime_started=time.monotonic(),stop_sha256=hashlib.sha256(raw).hexdigest())
            entry_phase(record,started,time.monotonic(),case)
            # GDB remains stopped at the FIRST kernel instruction until this
            # acknowledgment. Only the parent QPC clock times both host phases;
            # the GDB-local duration is never subtracted from a parent clock.
            pending=folder/'bios-entry.pending';target=folder/'bios-entry.json'
            check.need(not target.exists(),'single phase acknowledgment')
            with pending.open('x',encoding='ascii') as stream:json.dump(record,stream,sort_keys=True)
            pending.rename(target)
            return record
        check.need(vm.poll() is None and debugger.poll() is None,'BIOS entry process exited')
        time.sleep(.01)
    raise ValueError('BIOS phase poll capacity')


def composed_capture_source():
    # Adapt the exact AY factory locally; shared profiles and observer are not
    # edited. Establish the runtime origin ONCE, before any old feeder call.
    source=inspect.getsource(ay.capture_namespace)
    source=ay.once(source,'session_origin=origin)',
        'session_origin=origin,session_step_loop=step_loop_tail,az_await_entry=await_entry)')
    transition=('            az_entry=az_await_entry(console_started,folder,output,data,overflow,vm,debugger)\n'
                '            if metrics is not None:metrics["bios_phase"]=az_entry\n'
                '            console_started=capture_started=az_entry["runtime_started"]\n')
    insertion=('        if function is boot._capture_run:\n'
        '            source=once(source,"    script=folder/\'observe.gdb\'",'+repr("    code=session_step_loop(code)\n    script=folder/'observe.gdb'")+')\n'
        '            source=once(source,"            deadline=capture_started+42",'+repr(transition+'            deadline=capture_started+42')+')\n')
    return ay.once(source,'        exec(compile(source,',insertion+'        exec(compile(source,')


def capture_namespace(started,medium,image,folder,case='normal'):
    check.need(not any((folder/name).exists() for name in ('bios-entry.json','bios-entry.pending','bios-stop.json','bios-stop.pending')),'fresh BIOS phase evidence')
    bios_budget(case)
    factory=dict(vars(ay),await_entry=lambda *args:await_entry(*args,case=case))
    exec(compile(composed_capture_source(),'<AZ composed phase factory>','exec'),factory)
    namespace=factory['capture_namespace'](started)
    def popen(command,*args,**kwargs):
        command=list(command)
        if '-kernel' in command:
            check.need(command.count('-kernel')==1 and command[command.index('-kernel')+1]==str(image),'exact original kernel argument')
            at=command.index('-kernel');del command[at:at+2]
            check.need('-device' in command and 'ide-hd,drive=pio-layer,bus=ide.0,unit=0' in command,'unchanged runtime primary master')
            command+=boot_arguments(medium.overlay,medium.layout)
            (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
        else:check.need(command[1:4]==['-q','-nx','-batch'],'only unchanged debugger spawn')
        return subprocess.Popen(command,*args,**kwargs)
    namespace['subprocess']=types.SimpleNamespace(**dict(vars(subprocess),Popen=popen))
    return namespace


def physical_entry(image,config):
    parsed=check.payload.elf(check.bounded(Path(image),check.KERNEL_LIMIT),32)
    entry=parsed['entry']
    check.need(type(entry) is int and 0x100000<=entry<0x4000000 and
        parsed['symbols']['x86_64_bootstrap_start']['value']==entry and
        config['s']['x86_64_bootstrap_start']==0xffffffff80000000+entry,'ELF entry and Higher-Half observer binding')
    return entry


def boot_entry_prefix(entry,folder,started,case='normal'):
    """Run BIOS with one stop only, then install every unchanged AY hook.

    The stop is BEFORE the first kernel instruction, not after a kernel probe.
    No target writes, skipped instruction, suppressed runtime event or new time.
    """
    budget=bios_budget(case);folder=Path(folder).absolute()
    check.need(type(entry) is int and 0x100000<=entry<0x4000000 and folder==folder.resolve() and
        folder.is_relative_to(ROOT/'build/codex-agent'),'cold BIOS entry binding')
    return f'''python
import gdb,json as _az_json,time as _az_time,os as _az_os,hashlib as _az_hashlib
_az_bp=None
try:
    assert not gdb.breakpoints()
    _az_start=_az_time.monotonic()
    _az_bp=gdb.Breakpoint('*0x{entry:x}',type=gdb.BP_HARDWARE_BREAKPOINT,internal=True)
    _az_bp.silent=True
    try:
        assert _az_bp.is_valid() and _az_bp.enabled and _az_bp.hit_count==0
        assert len(_az_bp.locations)==1 and _az_bp.locations[0].address=={entry} and _az_bp.locations[0].enabled
        _az_output=gdb.execute('continue',to_string=True)
        assert len(_az_output)<=2048 and _az_bp.is_valid() and _az_bp.hit_count==1
        _az_regs={{name:int(gdb.parse_and_eval('$'+name))&0xffffffff for name in ('rip','rax','rbx','cr0','rsp','eflags')}}
        assert _az_regs['rip']=={entry} and _az_regs['rax']==0x2badb002
        assert _az_regs['cr0']&0x80000001==1 and _az_regs['rsp']==0x90000 and not _az_regs['eflags']&0x600
        _az_elapsed=_az_time.monotonic()-_az_start
        assert 0<=_az_elapsed<{budget}
    finally:
        if _az_bp is not None and _az_bp.is_valid():_az_bp.delete()
    assert not gdb.breakpoints()
    _az_record=_az_json.dumps(dict(version=1,entry={entry},hits=1,registers=_az_regs,elapsed=_az_elapsed,
        guest_started={started!r}),sort_keys=True)
    assert len(_az_record)<=1024
    with open({str(folder/'bios-stop.pending')!r},'x',encoding='ascii') as _az_file:_az_file.write(_az_record)
    _az_os.rename({str(folder/'bios-stop.pending')!r},{str(folder/'bios-stop.json')!r})
    _az_ack=None
    for _az_poll in range({budget*100+1}):
        assert _az_time.monotonic()-_az_start<{budget}
        if _az_os.path.exists({str(folder/'bios-entry.json')!r}):
            with open({str(folder/'bios-entry.json')!r},'r',encoding='ascii') as _az_file:_az_raw=_az_file.read(1025)
            assert len(_az_raw)<=1024
            _az_ack=_az_json.loads(_az_raw)
            assert _az_ack['version']==3 and _az_ack['guest_started']=={started!r}
            assert _az_ack['stop_sha256']==_az_hashlib.sha256(_az_record.encode('ascii')).hexdigest()
            assert _az_ack['entry']=={entry} and _az_ack['registers']==_az_regs
            break
        _az_time.sleep(.01)
    assert _az_ack is not None
    assert int(gdb.parse_and_eval('$rip'))&0xffffffff=={entry}
except BaseException as _az_error:
    gdb.write('BIOS_ENTRY_FAIL '+str(_az_error)[:256]+'\\n')
    gdb.execute('quit 71')
end
'''


def live_serial(path):
    with Path(path).open('rb') as stream:raw=stream.read(262145)
    check.need(len(raw)<=262144,'live serial capacity')
    return raw


def negative_budget(layout,case):
    check.need((layout,case) in (('hdd','signatures'),('hdd','digest'),('hdd','manifest'),
        ('floppy','signatures'),('floppy','digest')),'negative BIOS case budget')
    return 30 if layout=='hdd' and case in ('signatures','digest') else 20


def negative(folder,medium,fixture,started,case):
    command=[str(ay.boot.resolve_qemu(None)),'-machine','pc,accel=tcg','-cpu','qemu64','-m','4096M','-smp','1',
             '-display','none','-monitor','none','-nic','none','-serial','file:'+str(folder/'guest.log'),'-no-reboot','-no-shutdown']
    command+=fixture.arguments(folder)+boot_arguments(medium.overlay,medium.layout)
    (folder/'command.json').write_text(json.dumps(command),encoding='utf-8')
    with (folder/'stderr.log').open('wb') as log:
        vm=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=log,
                            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            while time.monotonic()<started+negative_budget(medium.layout,case)-3:
                check.need(vm.poll() is None,'negative guest exited')
                if (folder/'guest.log').exists():
                    raw=live_serial(folder/'guest.log')
                    check.need(b'REIST_X86_64_' not in raw and b'Starting kernel...' not in raw,'rejected boot executed kernel')
                time.sleep(.02)
        finally:ay.boot.terminate_bounded(vm)
    return check.bounded(folder/'guest.log',262144).decode('ascii',errors='replace')


def composed_fixture(folder,app,started,case='normal'):
    limit=45+bios_budget(case)
    source=inspect.getsource(ay.bounded_fixture)
    source=ay.once(source,'started+45-time.monotonic()',f'started+{limit}-time.monotonic()')
    source=ay.once(source,'0<value<=45',f'0<value<={limit}')
    ns=dict(vars(ay));exec(compile(source,'<AZ composed media deadline>','exec'),ns)
    return ns['bounded_fixture'](folder,2,app,started)


def run_matrix(image,package,folder,binding,cases=CASES):
    image=Path(image).resolve();package=Path(package).resolve();folder=Path(folder).absolute()
    check.need(not folder.exists() and folder==folder.resolve() and folder.is_relative_to(ROOT/'build/codex-agent'),'fresh BIOS evidence')
    binding();config,records,app=ay.image_config(image);catalog=(image.parent/'boot-programs.bin').read_bytes()
    folder.mkdir(parents=True);result=dict(passed=False,cases=[],guest_seconds=0.0);begin=time.monotonic()
    try:
        for name,layout,case,session,ram in cases:
            binding();check.need(time.monotonic()-begin<560,'finite runtime host window')
            out=folder/name;out.mkdir();started=time.monotonic();limit=45+bios_budget(case) if session is not None else negative_budget(layout,case)
            trial=dict(name=name,layout=layout,case=case,session=session,ram=ram,passed=False);result['cases'].append(trial)
            medium=None;fixture=None
            try:
                source=package/('reist-x86_64.img' if layout=='hdd' else 'reist-x86_64-floppy.img')
                medium=BootMedium(source,out/'boot-medium',layout,case,started+limit);medium.verify('before')
                # This helper accepts a45s-origin. For negative BIOS-only tests,
                # map that origin to the stricter20s host deadline, never guest time.
                fixture=composed_fixture(out,app,started,case) if session is not None else ay.bounded_fixture(out,2,app,started-(45-limit))
                if session is not None:
                    code=boot_entry_prefix(physical_entry(image,config),out,started,case)+ay.observer(config,records,out,session,2)
                    capture_namespace(started,medium,image,out,case)['capture'](image,out,code,ram,fixture,
                        binary_memory='equivalence',diagnostic_metrics=True,service_pio_budget=True,console_input=ay.input_plan(session))
                else:
                    fixture.verify('before')
                    try:negative(out,medium,fixture,started,case)
                    finally:fixture.verify('after')
            finally:
                try:
                    if medium is not None:medium.verify('after')
                finally:
                    trial['elapsed']=time.monotonic()-started;result['guest_seconds']+=trial['elapsed']
            check.need(trial['elapsed']<=limit and result['guest_seconds']<=455,'whole BIOS guest deadline')
            serial=check.bounded(out/'guest.log',262144).decode('ascii',errors='replace');validate_bios(serial,layout,case)
            if session is not None:
                metrics=json.loads((out/'capture-metrics.json').read_text())
                phase=metrics['bios_phase'];bios_seconds=phase['runtime_started']-started
                check.need(check.object_json(check.bounded(out/'bios-entry.json',1024))==phase and
                    0<=bios_seconds<bios_budget(case) and 0<=metrics['observe_seconds']<=42 and
                    0<=trial['elapsed']-bios_seconds-metrics['observe_seconds']<=3,'composed phases include both media cleanup')
                trial['bios_seconds']=bios_seconds
                trial['proof']=ay.evaluate(out,config,records,catalog,session,2,app)
            trial['passed']=True;print('SHELL_BIOS_CASE_OK',name,round(trial['elapsed'],3),flush=True)
        result['passed']=True;return result
    except BaseException as error:result['error']=str(error);raise
    finally:
        result.update(elapsed=time.monotonic()-begin,closed=True)
        with (folder/'summary.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
