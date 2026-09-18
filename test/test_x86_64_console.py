"""Execute the actual native console admission, mediator and SDK."""
from pathlib import Path
import copy,inspect,json,os,re,struct,subprocess,sys,textwrap,unittest,uuid
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'test'),str(ROOT/'scripts')]
import test_x86_64_task_frames as host_builder

class ConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=ROOT/'build/codex-agent/r83as-console/host'/uuid.uuid4().hex;cls.folder.mkdir(parents=True)

    def test_producer_rejection_before_effects(self):
        import build_x86_64_boot_programs as producer
        for change in (dict(console=1),dict(console='1'),dict(console=True,family=True),
                       dict(console=True,live_file=True),dict(console=True,filesystem_layout=1)):
            with patch.object(producer.subprocess,'run',side_effect=AssertionError('tool before validation')):
                with self.assertRaises(ValueError):producer.build(self.folder/'absent',['cc'],['nasm'],['ld'],0,**change)
            self.assertFalse((self.folder/'absent').exists())

    def test_make_profile_and_conflicts(self):
        from test_x86_64_file_launch import direct_make_plan,MAKE_FILE_PROFILE
        options={'X86_64_NATIVE_'+n:'0' for n in MAKE_FILE_PROFILE}
        options.update({'X86_64_NATIVE_'+n:'1' for n in ('PROCESSES','IPC','RAM','HEAP','RUNTIME','PROGRAMS','CONSOLE')})
        good=direct_make_plan(self.folder,options);self.assertEqual(good.returncode,0,good.stderr)
        self.assertIn('--console',good.stdout);self.assertIn('-DREIST_NATIVE_CONSOLE=1',good.stdout)
        for update in ({'X86_64_NATIVE_CONSOLE':'2'},{'X86_64_NATIVE_CONSOLE':'1 0'},
                       {'X86_64_NATIVE_LIFECYCLE':'1'},{'X86_64_NATIVE_PROGRAMS':'0'},
                       {'X86_64_NATIVE_PIO':'1'},{'X86_64_PROGRAM_CASE':'1'}):
            self.assertNotEqual(direct_make_plan(self.folder,dict(options,**update)).returncode,0)

    def test_powershell_conflict_before_outputs(self):
        for switch in ('NativePIO','NativeLifecycle','NativeLiveFile','NativeServiceCPU'):
            target=self.folder/('absent-'+switch)
            r=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
                '-NativeConsole','-'+switch,'-OutputDirectory',target.relative_to(ROOT).as_posix()],
                cwd=ROOT,capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/(switch+'.log')).write_bytes(r.stdout+r.stderr)
            self.assertNotEqual(r.returncode,0);self.assertIn(b'NativeConsole requires plain NativePrograms',r.stdout+r.stderr)
            self.assertFalse(target.exists())

    def test_old_producers_exact(self):
        import test_x86_64_live_file as old
        method=textwrap.dedent(inspect.getsource(old.LiveFileTests.test_old_producer_commands_exact_with_modeled_tool_outputs))
        method=method.replace("'c7e5e72a:scripts/build_x86_64_boot_programs.py'","'7d34f237:scripts/build_x86_64_boot_programs.py'")
        method=method.replace('    for index,profile in enumerate(profiles):',
            '    profiles.append(dict(pio_profile,filesystem=True,file_launch=True,live_file=True))\n    for index,profile in enumerate(profiles):')
        ns=dict(vars(old));exec(compile(method,'<console-default-producer-equivalence>','exec'),ns)
        ns['test_old_producer_commands_exact_with_modeled_tool_outputs'](self)

    def test_bounded_input_plan_and_default_adapter(self):
        import run_qemu_x86_64_boot_programs as boot
        import run_qemu_x86_64_console as console
        self.assertIsNone(boot.console_input_plan(None))
        for case in range(4):self.assertEqual(boot.console_input_plan(console.inputs(case)),console.inputs(case))
        for bad in ((),[],(b'N',console.NORMAL),(console.NORMAL,b'F'),(b'X',console.NORMAL),
                    (console.NORMAL,console.NORMAL,console.NORMAL)):
            with self.assertRaises(ValueError):boot.console_input_plan(bad)
        with patch.object(boot,'_capture',return_value=('serial','trace')) as call:
            self.assertEqual(boot.capture(Path('image'),Path('folder'),'code',4096),('serial','trace'))
            call.assert_called_once_with(Path('image'),Path('folder'),'code',4096,halt_witness=False)
        with patch.object(boot,'_capture',side_effect=AssertionError('effects before admission')):
            with self.assertRaises(ValueError):boot.capture(Path('image'),Path('folder'),'code',4096,console_input=(b'X',console.NORMAL))

    def test_actual_guest_oracle_and_mutations(self):
        import run_qemu_x86_64_console as console
        import test_x86_64_boot_programs as old
        sample=textwrap.dedent(inspect.getsource(old.BootProgramTests.sample)).replace('@staticmethod\n','')
        sample=sample.replace('ident=slot if run==0 else 3-slot;bad=case and ident==2','ident=slot;bad=case in (1,2) and run==0 and ident==0')
        sample=sample.replace('else 40+ident','else (65 if case==3 and run==0 and ident==0 else 61+ident)')
        sample=sample.replace('ident=s if run==1 else 3-s','ident=s')
        ns=dict(vars(old));exec(compile(sample,'<console-finite-model>','exec'),ns)
        for case in range(4):
            serial,trace=ns['sample'](case)
            self.assertEqual(len(console.base_validator()(serial,trace,case,4096)),8)
            for bad in (serial+serial,serial.replace('PROCESS_REAP_OK','BAD',1)):
                with self.assertRaises((ValueError,RuntimeError)):console.base_validator()(bad,trace,case,4096)
            for bad in (trace.replace('private=1','private=0',1),trace.replace('zero=1','zero=0',1)):
                with self.assertRaises((ValueError,RuntimeError)):console.base_validator()(serial,bad,case,4096)
            events=[]
            for run in (1,2):
                def event(op,fd,size,result,pointer=0x100000000,before=None,after=None,unused=None):
                    return dict(run=run,slot=0,gen=(run-1)*4+1,op=op,fd=fd,size=size,result=result,pointer=pointer,
                        before=before,after=after,unused=[0,0,0] if unused is None else unused)
                events += [event(15,1,1,-9),event(15,0,65,-22),event(15,0,0,0),event(15,0,1,-14,pointer=0)]
                mode=case if run==1 else 0;raw=console.inputs(mode)[0];ready=b'NATIVE_CONSOLE_READY\n'
                events.append(event(20,1,len(ready),len(ready),before=ready.hex(),after=ready.hex()))
                for part in (raw[:1],raw[1:]):
                    if part:events.append(event(15,0,len(part),len(part),before='a5'*len(part),after=part.hex()))
                if mode==0:events.append(event(20,1,64,64,before=console.NORMAL[1:].hex(),after=console.NORMAL[1:].hex()))
                if mode==3:events.append(event(15,0,64,-11,before='a5'*64,after='a5'*64))
            console.validate_io(events,case)
            for key,value in (('gen',99),('slot',1),('run',3),('result',1),('after','00')):
                bad=copy.deepcopy(events);bad[0][key]=value
                with self.assertRaises(ValueError):console.validate_io(bad,case)
            with self.assertRaises(ValueError):console.validate_io(events[:-1],case)
        self.assertEqual(len(console.CASES),7);self.assertEqual(len(set(console.CASES)),7)

    def test_generated_observer_compiles_and_binds_ownership(self):
        import run_qemu_x86_64_console as console
        import run_qemu_x86_64_boot_programs as boot
        image=ROOT/'build/codex-agent/r83ap-service-cpu/file-reference/x86_64/reist-x86_64-bootstrap.elf'
        s=boot.symbols(image);s['native_console_syscall64']=0x1234
        core=boot.payload.validate(boot.payload.read_bounded(image.parent/'reist-x86_64-c-core.elf'))
        for kind in (None,'peer-mask','legacy-mask'):
            code=console.observer(s,core,self.folder,4096) if kind is None else console.rejection_observer(s,core,self.folder,kind)
            blocks=re.findall(r'(?ms)^python\n(.*?)^end\n',code)
            self.assertTrue(blocks)
            for block in blocks:compile(block,'<actual console observer>','exec')
            self.assertIn("task[1]==(run-1)*4+1",code)
            self.assertIn("profile[0]==task[1]",code)
            self.assertIn('console_events<=512',code)
            self.assertIn('self.enabled=False',code)
            self.assertEqual(code.count('def mem(a,n):'),1)

    def test_actual_binary_setup_and_wrapped_callbacks(self):
        import types
        import run_qemu_x86_64_console as console
        import run_qemu_x86_64_boot_programs as boot
        import qemu_binary_memory as binary
        image=ROOT/'build/codex-agent/r83as-console/native/x86_64/reist-x86_64-bootstrap.elf'
        s,c=console.image_config(image)
        folder=self.folder/'actual-transport';folder.mkdir()
        code=console.observer(s,c,folder,4096)
        _,configured=binary.configure(code,folder,4096,'equivalence')
        block=re.findall(r'(?ms)^python\n(.*?)^end\n',configured)[-1]
        class Breakpoint:
            def __init__(self,*args,**kwargs):self.enabled=True
        output=[]
        fake=types.SimpleNamespace(Breakpoint=Breakpoint,write=output.append,
            execute=lambda command:(_ for _ in ()).throw(AssertionError(command)),MemoryError=MemoryError)
        task=[0]*32;task[:3]=[2,1,0x100001000]
        contents={s['scheduler_current_slot']:struct.pack('<I',0),s['scheduler_tasks']:struct.pack('<32Q',*task),
            s['process_run_generation']:struct.pack('<I',4),s['scheduler_syscall_profiles']:struct.pack('<2Q',1,(1<<15)|(1<<20)),
            0x100000000:b'xx'}
        for key,value in dict(syscall_rax=15,syscall_rdi=0,syscall_rsi=0x100000000,syscall_rdx=2,syscall_r10=0,syscall_r8=0,syscall_r9=0).items():
            contents[s[key]]=struct.pack('<Q',value)
        registers={'eflags':0,'cr3':task[2],'r12':s['scheduler_tasks'],'rax':2}
        namespace=dict(gdb=fake,struct=struct,mem=lambda a,n:contents[a][:n],reg=lambda n:registers[n])
        namespace['u64']=lambda a:struct.unpack('<Q',namespace['mem'](a,8))[0]
        exec(compile(block,'<actual binary setup>','exec'),namespace)
        self.assertIs(namespace['Hook'],namespace['ConsoleEntry'])
        self.assertIs(namespace['ReleaseEnd'],namespace['ConsoleResult'])
        entry=namespace['ConsoleEntry']()
        self.assertFalse(entry.stop());self.assertIsNotNone(namespace['console_pending'])
        self.assertFalse(namespace['binary_reader'].in_stop)
        contents[0x100000000]=b'ab'
        self.assertFalse(namespace['console_result'].stop());self.assertIsNone(namespace['console_pending'])
        self.assertFalse(namespace['console_result'].enabled);self.assertFalse(namespace['binary_reader'].in_stop)
        self.assertIsNone(namespace['binary_reader'].client)
        row=json.loads(output[0].removeprefix('CONSOLE_IO '))
        self.assertEqual((row['before'],row['after'],row['result'],row['gen']),('7878','6162',2,1))
    def test_actual_ramwatch_binary_transport(self):
        import types
        import run_qemu_x86_64_console as console
        import qemu_binary_memory as binary
        image=ROOT/'build/codex-agent/r83as-console/native/x86_64/reist-x86_64-bootstrap.elf'
        s,c=console.image_config(image);symbols=c['symbols']
        code=console.observer(s,c,self.folder,4096)
        block=next(b for b in re.findall(r'(?ms)^python\n(.*?)^end\n',code) if 'class RAMWatch' in b)
        state=symbols['native_memory_state']['value'];directory=s['native_direct_page_directory'] if 'native_direct_page_directory' in s else None
        # Read the addresses from the actual generated callback, not a replica.
        directory=int(re.search(r"entries=struct.unpack\('<8192Q',mem\((\d+),65536\)\)",block)[1])
        mixed=int(re.search(r'assert (\d+)<=physical',block)[1])
        count=(mixed+4095)//4096
        highpt=int(re.search(r"mem\((\d+)\+512\*8,count\*8\)",block)[1])+512*8
        usable=bytearray(524288);usable[64:2049*64]=b'\xff'*(2048*64);usable[64]=254
        entries=[0]*8192
        for region in range(1,2049):entries[region]=(1<<63)|(region<<21)|0x83
        entries[1]=(1<<63)|mixed|3
        leaves=[0]+[(1<<63)|(0x200000+i*4096)|3 for i in range(1,512)]
        allocations=bytes(524288);managed=2048*512-1
        memory={state:struct.pack('<4I',managed,managed,1,0xfffffffe)+bytes(48)+bytes(usable)+allocations,
                directory:struct.pack('<8192Q',*entries),binary.HIGH+mixed:struct.pack('<512Q',*leaves),
                highpt:struct.pack('<'+'Q'*count,*[(1<<63)|(0x200000+i*4096)|3 for i in range(count)])}
        # Actual Reader page walking through modeled supervisor tables.
        root=0x1000000
        tables={root:{511:root+4096|3,256:root+12288|3},
                root+4096:{510:root+8192|3},
                root+8192:{i:(i<<21)|0x83 for i in range(64)},
                root+12288:{4:root+16384|3},root+16384:{0:0x100000000|0x83}}
        for address,values in tables.items():
            page=[0]*512
            for index,value in values.items():page[index]=value
            memory[binary.HIGH+address]=struct.pack('<512Q',*page)
        high=binary.DM+0x100000000;memory[high]=bytes(n%251 for n in range(32768))
        class Breakpoint:
            def __init__(self,*args,**kwargs):self.enabled=True
        for mutation in (None,'usable','allocated','pde','high-mismatch','short'):
            with self.subTest(mutation=mutation):
                folder=self.folder/('ramwatch-'+str(mutation));folder.mkdir();raw=dict(memory)
                if mutation in ('usable','allocated'):
                    changed=bytearray(raw[state]);changed[64+(64 if mutation=='usable' else 524288)]=0x55;raw[state]=bytes(changed)
                if mutation=='pde':
                    changed=bytearray(raw[directory]);changed[2048*8]^=4;raw[directory]=bytes(changed)
                def original(address,size):
                    for start,data in raw.items():
                        if start<=address and address+size<=start+len(data):return data[address-start:address-start+size]
                    raise AssertionError(('unmapped',hex(address),size))
                class QMP:
                    def __init__(self,*args):self.closed=False
                    def stopped(self):pass
                    def close(self):self.closed=True
                    def save(self,physical,size,path):
                        address=(binary.DM if physical>=1<<32 else binary.HIGH)+physical
                        data=original(address,size)
                        if mutation=='high-mismatch' and physical>=1<<32:data=bytes([data[0]^1])+data[1:]
                        if mutation=='short':data=data[:-1]
                        path.write_bytes(data)
                output=[]
                fake=types.SimpleNamespace(Breakpoint=Breakpoint,write=output.append,
                    execute=lambda command:(_ for _ in ()).throw(AssertionError(command+' '+''.join(output))))
                reader=binary.Reader(1,'host',folder,4096,original,lambda:root,True)
                ns=dict(gdb=fake,struct=struct,mem=reader.read,reg=lambda name:0)
                exec(compile(block,'<actual console RAMWatch>','exec'),ns)
                with patch.object(binary,'QMP',QMP):
                    if mutation is not None:
                        with self.assertRaises(AssertionError):ns['RAMWatch']().stop()
                    else:
                        self.assertFalse(ns['RAMWatch']().stop())
                        rows=[json.loads(line) for line in (folder/'reads.jsonl').read_text().splitlines()]
                        self.assertEqual([r['bytes'] for r in rows],[262144]*4+[65536,32768])
                        self.assertEqual([r['equivalence'] for r in rows if r['equivalence']],['kernel','high'])
                        self.assertIn('NATIVE_MEMORY_MAP_OK',''.join(output))
                        self.assertEqual(b''.join((folder/r['file']).read_bytes() for r in rows[:2]),bytes(usable))
                        self.assertEqual(b''.join((folder/r['file']).read_bytes() for r in rows[2:4]),allocations)
                self.assertIsNone(reader.client)

    def test_acknowledged_console_feeder(self):
        import run_qemu_x86_64_boot_programs as boot
        import run_qemu_x86_64_console as console
        def receipt(run,raw):
            return 'CONSOLE_IO '+json.dumps(dict(run=run,slot=0,gen=(run-1)*4+1,op=15,fd=0,
                size=len(raw),result=len(raw),unused=[0,0,0],after=raw.hex()))+'\n'
        for case in range(4):
            feeder=boot.ConsoleFeeder(console.inputs(case));trace='';serial='';writes=[]
            def write(raw):writes.append(raw);return len(raw)
            elapsed=0.0
            for run,payload in enumerate(console.inputs(case),1):
                serial+='NATIVE_CONSOLE_READY\n';received=b''
                for _ in range(10):
                    before=len(writes);elapsed+=.01
                    feeder.pump(serial,trace,write,elapsed)
                    if len(writes)==before:break
                    raw=writes[-1];self.assertLessEqual(len(raw),8)
                    # No acknowledgement: never repeat or advance a send.
                    feeder.pump(serial,trace,write,elapsed)
                    self.assertEqual(len(writes),before+1)
                    trace+=receipt(run,raw);received+=raw
                self.assertEqual(received,payload)
            feeder.pump(serial,trace,write,elapsed)
            self.assertEqual([r['payload'] for r in feeder.sent],[p.hex() for p in console.inputs(case)])
            self.assertLessEqual(len(writes),18)
            boot.ConsoleFeeder.validate(console.inputs(case),trace,feeder.chunks,feeder.sent)
            broken=copy.deepcopy(feeder.chunks);broken[0]['offset']=1
            with self.assertRaises(ValueError):boot.ConsoleFeeder.validate(console.inputs(case),trace,broken,feeder.sent)
        for mutation in ('short','ahead','wrong','generation','rewind','capacity','future-ready','deadline'):
            feeder=boot.ConsoleFeeder(console.inputs(0));serial='NATIVE_CONSOLE_READY\n';trace=''
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                if mutation=='short':feeder.pump(serial,trace,lambda raw:len(raw)-1,.1);continue
                if mutation=='ahead':trace=receipt(1,console.NORMAL[:1])
                elif mutation=='capacity':trace='x'*(1024*1024+1)
                elif mutation=='future-ready':serial*=2
                elif mutation=='deadline':feeder.pump(serial,trace,lambda raw:len(raw),17);continue
                else:
                    feeder.pump(serial,trace,lambda raw:len(raw),.1)
                    trace=receipt(1,console.NORMAL[:8])
                    if mutation=='wrong':trace=receipt(1,b'X'*8)
                    if mutation=='generation':trace=trace.replace('"gen": 1','"gen": 5')
                    if mutation=='rewind':
                        feeder.pump(serial,trace,lambda raw:len(raw),.2);trace=''
                feeder.pump(serial,trace,lambda raw:len(raw),.3)

    def test_capture_default_provenance_with_trailing_comment(self):
        import verify_x86_64_console as verifier
        old=(ROOT/'build/codex-agent/r83as-console/bitmap-adapter/candidate-01/source/scripts__run_qemu_x86_64_boot_programs.py').read_text()
        current=(ROOT/'scripts/run_qemu_x86_64_boot_programs.py').read_text()
        verifier.capture_delta(old,current)
        for bad in (current.replace("time.monotonic()+20","time.monotonic()+21",1),
                    current.replace("raw=console_input[len(console_sent)]","raw=b''",1).replace('def process_cpu_ns(pid):','def changed_cpu_ns(pid):',1)):
            with self.assertRaises(ValueError):verifier.capture_delta(old,bad)

    def test_actual_console_output_loop(self):
        import ast,queue,threading,types
        import run_qemu_x86_64_boot_programs as boot
        tree=ast.parse(inspect.getsource(boot._capture_run))
        loop=next(n for n in ast.walk(tree) if isinstance(n,ast.While) and ast.unparse(n.test)=='time.monotonic() < deadline')
        cut=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.If) and ast.unparse(n.test)=='halt_witness')
        code=compile(ast.fix_missing_locations(ast.Module(body=loop.body[:cut],type_ignores=[])),'<actual capture loop>','exec')
        for console in (None,(b'F',b'N'+bytes(97+n%26 for n in range(64)))):
            output=queue.Queue(maxsize=128)
            for _ in range(128):output.put_nowait(b'x')
            feeder=Mock();feeder.sent=[]
            ns=dict(vars(boot),output=output,data=bytearray(),trace_sink=None,overflow=threading.Event(),
                console_input=console,console_feeder=feeder,metrics=None,folder=self.folder/'absent-trace',
                vm=types.SimpleNamespace(stdin=Mock()),console_started=boot.time.monotonic())
            exec(code,ns)
            self.assertEqual(len(ns['data']),128 if console is not None else 1)
            feeder.pump.assert_not_called()
            if console is not None:
                ns['data']=bytearray(b'NATIVE_CONSOLE_READY\n');exec(code,ns);feeder.pump.assert_called_once()
                ns['overflow'].set()
                with self.assertRaises(ValueError):exec(code,ns)
                ns['overflow'].clear();ns['data']=bytearray(262145)
                with self.assertRaises(ValueError):exec(code,ns)

    def test_actual_console_admission(self):
        source=(ROOT/'arch/x86_64/proc/process_run.inc').read_text()
        body=source.split('process_run_admit64:',1)[1].split('process_run_validate64:',1)[0]
        asm='''BITS 64
%define REIST_NATIVE_PROGRAMS 1
%define REIST_NATIVE_CONSOLE 1
section .text
global process_run_admit64
process_run_admit64:
'''+body
        host_builder.TaskFrameTests().build(asm,ROOT/'test/x86_64_console_host.c','CONSOLE_ADMISSION')

    def test_actual_mediator(self):
        source=(ROOT/'arch/x86_64/proc/native_console.inc').read_text()
        self.assertEqual(source.count('    in al,dx'),2)
        self.assertEqual(source.count('    out dx,al'),1)
        # Only privileged byte I/O is replaced. Every admission/branch/loop and
        # load/store is the actual production body; pointer policy is a boundary.
        source=source.replace('    in al,dx','    call port_in').replace('    out dx,al','    call port_out')
        asm='''BITS 64
REIST_SYS_READ equ 15
REIST_SYS_WRITE equ 20
PF_R equ 4
PF_W equ 2
COM1_DATA equ 0x3f8
COM1_LSR equ 0x3fd
section .bss
global scheduler_current_slot,syscall_rax,syscall_rdi,syscall_rsi,syscall_rdx,syscall_r10,syscall_r8,syscall_r9
scheduler_current_slot: resq 1
syscall_rax: resq 1
syscall_rdi: resq 1
syscall_rsi: resq 1
syscall_rdx: resq 1
syscall_r10: resq 1
syscall_r8: resq 1
syscall_r9: resq 1
section .text
global console_apply
extern host_in,host_out,host_range
console_apply:
    push rbp
    push rbx
    push r12
    push r13
    push r14
    push r15
    sub rsp,8
    jmp native_console_syscall64
process_run_resume64:
    add rsp,8
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbx
    pop rbp
    ret
scheduler_validate_shell_range64:
    push rbx
    mov rdi,rax
    mov rsi,rdx
    mov edx,ecx
    call host_range
    pop rbx
    ret
port_in:
    push rdx
    movzx edi,dx
    call host_in
    pop rdx
    ret
port_out:
    push rdx
    movzx edi,dx
    movzx esi,al
    call host_out
    pop rdx
    ret
'''+source
        c=(ROOT/'test/x86_64_console_host.c').read_text()
        c=c.replace('"../arch/x86_64/proc/process_run.h"','"'+(ROOT/'arch/x86_64/proc/process_run.h').as_posix()+'"')
        host_builder.TaskFrameTests().build(asm,'#define CONSOLE_MEDIATOR 1\n'+c,'CONSOLE_MEDIATOR')

    def test_actual_sdk(self):
        from build_user_program import find_zig
        folder=ROOT/'build/codex-agent/r83as-console/host'/uuid.uuid4().hex;folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            command=[str(find_zig()),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                '-fno-sanitize=all','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                'test/x86_64_console_sdk_host.c','-o',str(exe)]
            for suffix,args in (('build',command),('run',[str(exe)])):
                r=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,timeout=60,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                (folder/(opt+'-'+suffix+'.log')).write_bytes(r.stdout+r.stderr)
                self.assertEqual(r.returncode,0,(r.stdout+r.stderr).decode(errors='replace')[-2500:])
                if suffix=='run':self.assertIn(b'CONSOLE_SDK_OK',r.stdout)

if __name__=='__main__':unittest.main()
