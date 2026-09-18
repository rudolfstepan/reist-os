"""Actual normal shell source/adapter, finite IO and unchanged build profiles."""
from pathlib import Path
import copy,inspect,json,os,struct,subprocess,sys,textwrap,unittest,uuid
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'test')]
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs

class ShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        cls.folder=ROOT/'build/codex-agent/r83at-shell/host'/uuid.uuid4().hex
        cls.folder.mkdir(parents=True)

    def test_shared_drive_enumerators_i386_amd64(self):
        source=(ROOT/'userspace/bin/shell.c').read_text()
        names=('lower','text_length','drive_letter','find_drive','path_has_mount','current_drive')
        bodies=[]
        for name in names:
            start=source.index('static ',source.rfind('\n',0,source.index(name+'(')))
            end=source.index('\n}',start)+2;bodies.append(source[start:end])
        (self.folder/'shell_drive_functions.h').write_text('\n'.join(bodies))
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(self.folder/'drive-cache')
        for arch in ('x86','x86_64'):
            for opt in ('O0','O2'):
                exe=self.folder/f'drives-{arch}-{opt}.exe'
                commands=([find_zig(),'cc','-target',arch+'-windows-gnu','-'+opt,'-fno-sanitize=all',
                    '-UNDEBUG','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include',
                    '-I'+str(self.folder),'test/shell_drives_host.c','-o',str(exe)],[str(exe)])
                for index,cmd in enumerate(commands):
                    p=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,timeout=60 if index==0 else 5,
                        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    (self.folder/f'drives-{arch}-{opt}-{index}.log').write_bytes(p.stdout+p.stderr)
                    self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[-3000:])
                    if index:self.assertIn(b'SHELL_DRIVES_HOST_OK',p.stdout)

    def test_shared_shell_source_boundary_utf8(self):
        from verify_x86_64_native_shell import shared_shell_delta
        old=subprocess.check_output(['git','show','f2e93446:userspace/bin/shell.c'],cwd=ROOT,timeout=10)
        current=(ROOT/'userspace/bin/shell.c').read_bytes()
        shared_shell_delta(old,current)
        with self.assertRaises(ValueError):shared_shell_delta(old,current.replace(b'REIST OS',b'OTHER OS'))
        with self.assertRaises(ValueError):shared_shell_delta(old,current.replace('geprüft'.encode(),b'checked'))

    def test_actual_shell_and_platform(self):
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(self.folder/'cache')
        def run(command,name):
            p=subprocess.run(list(map(str,command)),cwd=ROOT,env=env,capture_output=True,timeout=60,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (self.folder/(name+'.log')).write_bytes(p.stdout+p.stderr)
            self.assertEqual(p.returncode,0,(p.stdout+p.stderr)[-3000:]);return p.stdout
        for opt in ('O0','O2'):
            exe=self.folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu','-'+opt,'-fno-sanitize=all',
                '-UNDEBUG','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-Iuserspace/sdk/include','-Iuserspace/storage/include',
                'test/x86_64_shell_host.c','-o',exe],opt+'-build')
            for mode in range(19):self.assertIn(b'NATIVE_SHELL_HOST_OK',run([exe,str(mode)],f'{opt}-{mode}'))

    def test_selectors_before_effects(self):
        import build_x86_64_boot_programs as p
        for options in (dict(native_shell=1),dict(native_shell=True),dict(native_shell=True,console=True,wide=True)):
            with patch.object(p.subprocess,'run',side_effect=AssertionError('early tool')):
                with self.assertRaises(ValueError):p.build(self.folder/'absent',['cc'],['nasm'],['ld'],0,**options)
            self.assertFalse((self.folder/'absent').exists())
        from test_x86_64_file_launch import direct_make_plan,MAKE_FILE_PROFILE
        options={'X86_64_NATIVE_'+n:'0' for n in MAKE_FILE_PROFILE}
        options.update({'X86_64_NATIVE_'+n:'1' for n in ('PROCESSES','IPC','RAM','HEAP','RUNTIME','PROGRAMS','CONSOLE','SHELL')})
        good=direct_make_plan(self.folder,options);self.assertEqual(good.returncode,0,good.stderr)
        self.assertIn('--native-shell',good.stdout)
        for delta in ({'X86_64_NATIVE_SHELL':'2'},{'X86_64_NATIVE_SHELL':'1 0'},{'X86_64_NATIVE_CONSOLE':'0'}):
            self.assertNotEqual(direct_make_plan(self.folder,dict(options,**delta)).returncode,0)
        target=self.folder/'ps-absent'
        p=subprocess.run(['powershell.exe','-NoProfile','-File','scripts/build-x86_64-bootstrap.ps1',
            '-NativeShell','-NativePIO','-OutputDirectory',target.relative_to(ROOT).as_posix()],
            cwd=ROOT,capture_output=True,timeout=15)
        self.assertNotEqual(p.returncode,0);self.assertFalse(target.exists())

    def test_capture_adapter_and_plans(self):
        import run_qemu_x86_64_native_shell as shell
        ns=shell.capture_namespace()
        for case in range(3):
            plan=shell.inputs(case);self.assertEqual(shell.input_plan(plan),plan)
            self.assertLessEqual(sum(len(p) for p in plan),130)
            self.assertTrue(all(b'\r' not in p and b'\n' in p for p in plan))
        for bad in (None,(),(b'fake',shell.NORMAL),(shell.NORMAL,b'exit\r')):
            with self.assertRaises(ValueError):shell.input_plan(bad)
        feeder=ns['ConsoleFeeder'](shell.inputs(0));sent=[]
        feeder.pump(shell.BANNER,'',lambda raw:sent.append(raw) or len(raw),0.1)
        self.assertEqual(sent,[shell.NORMAL[:8]])
        feeder.pump(shell.BANNER,'',lambda raw:sent.append(raw) or len(raw),0.2)
        self.assertEqual(len(sent),1)
        with self.assertRaises(ValueError):feeder.pump(shell.BANNER,'',lambda raw:len(raw),17)

    def test_actual_entrypoint_resolves_relative_evidence(self):
        import run_qemu_x86_64_native_shell as shell
        import verify_x86_64_native_shell as verifier
        evidence=self.folder/'entrypoint';seen=[]
        def capture(image,folder,*args,**kwargs):
            self.assertTrue(folder.is_absolute());seen.append(folder)
            raise ValueError('host-only launch boundary')
        with patch.object(sys,'argv',['runner','--image','fake-image','--evidence',evidence.relative_to(ROOT).as_posix()]), \
             patch.object(verifier,'binding'),patch.object(verifier,'link',return_value={}), \
             patch.object(shell.console,'image_config',return_value=({},{})), \
             patch.object(shell.console,'observer',return_value=''), \
             patch.object(shell,'capture_namespace',return_value={'capture':capture}):
            self.assertEqual(shell.main(),1)
        self.assertEqual(len(seen),1)
        receipt=json.loads(next(evidence.glob('attempt-*/summary.json')).read_text())
        self.assertEqual(receipt['error'],'host-only launch boundary');self.assertEqual(len(receipt['cases']),1)

    def test_old_producers_and_staged_shell(self):
        import test_x86_64_live_file as old
        code=textwrap.dedent(inspect.getsource(old.LiveFileTests.test_old_producer_commands_exact_with_modeled_tool_outputs))
        code=code.replace('c7e5e72a:scripts/build_x86_64_boot_programs.py','f2e93446:scripts/build_x86_64_boot_programs.py')
        code=code.replace('    for index,profile in enumerate(profiles):',
            '    profiles.extend([dict(console=True),dict(pio_profile,filesystem=True,file_launch=True,live_file=True)])\n    for index,profile in enumerate(profiles):')
        ns=dict(vars(old));exec(code,ns);ns['test_old_producer_commands_exact_with_modeled_tool_outputs'](self)

    def test_raw_oracle_rejection(self):
        import run_qemu_x86_64_native_shell as shell
        import test_x86_64_boot_programs as old
        code=textwrap.dedent(inspect.getsource(old.BootProgramTests.sample)).replace('@staticmethod\n','')
        code=code.replace('ident=slot if run==0 else 3-slot;bad=case and ident==2','ident=slot;bad=False')
        code=code.replace('else 40+ident','else ((110 if case==2 and run==0 else 0) if ident==0 else 61+ident)')
        code=code.replace('ident=s if run==1 else 3-s','ident=s')
        ns=dict(vars(old));exec(code,ns)
        for case in range(3):
            serial,trace=ns['sample'](case)
            self.assertEqual(len(shell.base_validator()(serial,trace,case,4096)),8)
            for bad in (trace.replace('private=1','private=0',1),trace.replace('zero=1','zero=0',1)):
                with self.assertRaises((ValueError,RuntimeError)):shell.base_validator()(serial,bad,case,4096)
            events=[]
            for run in (1,2):
                output=(shell.BANNER+'Type HELP for available commands.\nUSB keyboard: diagnostics unavailable\n\n?>').encode()
                output+=b'Built-ins: cd path pwd history help exit\nPATH=\nProgram lookup unavailable.\nUnable to read working directory.\nexit\n'
                for op,raw in ((20,output),(15,shell.inputs(case)[run-1])):
                    for offset in range(0,len(raw),64):
                        part=raw[offset:offset+64]
                        events.append(dict(run=run,slot=0,gen=(run-1)*4+1,op=op,fd=int(op==20),size=len(part),
                            result=len(part),pointer=0x408100,unused=[0,0,0],before=part.hex(),after=part.hex()))
                events.append(dict(events[-1],op=15,fd=0,size=1,result=-11,before='00',after='00'))
            shell.validate_io(events,case)
            for key,value in (('slot',1),('gen',99),('fd',0),('result',65),('unused',[0,1,0]),('after','00')):
                wrong=copy.deepcopy(events);wrong[0][key]=value
                with self.assertRaises(ValueError):shell.validate_io(wrong,case)

if __name__=='__main__':unittest.main()
