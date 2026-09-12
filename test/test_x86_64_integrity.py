"""Native IRQ-width regression, shared integrity identity and real guest oracle."""
from pathlib import Path
import os, subprocess, sys, unittest, uuid
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs
import run_qemu_x86_64_integrity as guest
BASELINE='12f93954'


class NativeIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        cls.folder=ROOT/'build/codex-agent/r83w-integrity'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True);cls.zig=find_zig()
        cls.env=os.environ.copy();cls.env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        cls.env['ZIG_LOCAL_CACHE_DIR']=str(cls.folder/'cache')
        cls.old=cls.folder/'old';header=cls.old/'arch/x86/include/interrupt.h';header.parent.mkdir(parents=True)
        header.write_bytes(subprocess.check_output(['git','show',BASELINE+':arch/x86/include/interrupt.h'],cwd=ROOT,timeout=10))

    def command(self,args,label):
        r=subprocess.run(list(map(str,args)),cwd=ROOT,env=self.env,timeout=60,capture_output=True,text=True,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (self.folder/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8');return r

    def compile(self,bits,old,label,preprocess=False):
        flags=['-g0','-ffreestanding','-fno-builtin','-fno-pic','-fno-stack-protector','-fno-unwind-tables','-fno-asynchronous-unwind-tables']
        if bits==64:flags+=['-mcmodel=kernel','-mno-red-zone','-mno-sse','-mno-sse2']
        args=[self.zig,'cc','-target','x86_64-freestanding-none' if bits==64 else 'x86-freestanding-none','-O2',*flags]
        if old:args+=['-I',self.old]
        args+=['-I',ROOT]
        args+=['-E','-P'] if preprocess else ['-c','-o',self.folder/(label+'.o')]
        return self.command([*args,'kernel/init/critical_object.c'],label)

    def test_real_native_compile_and_old_failure(self):
        before=self.compile(64,True,'native-before');self.assertNotEqual(before.returncode,0)
        self.assertRegex(before.stderr,r'Not 64-bit mode|invalid operand')
        after=self.compile(64,False,'native-after');self.assertEqual(after.returncode,0,after.stderr[-2500:])

    def test_i386_preprocessor_and_machine_code_unchanged(self):
        before=self.compile(32,True,'i386-before-pp',True);after=self.compile(32,False,'i386-after-pp',True)
        self.assertEqual((before.returncode,after.returncode),(0,0),before.stderr+after.stderr)
        self.assertEqual(before.stdout.split(),after.stdout.split())
        before=self.compile(32,True,'i386-before');after=self.compile(32,False,'i386-after')
        self.assertEqual((before.returncode,after.returncode),(0,0),before.stderr+after.stderr)
        self.assertEqual((self.folder/'i386-before.o').read_bytes(),(self.folder/'i386-after.o').read_bytes())

    def test_common_integrity_source_and_public_layout_unchanged(self):
        for name in ('kernel/init/critical_object.c','include/kernel/critical_object.h','lib/libc/string.c'):
            before=subprocess.check_output(['git','show',BASELINE+':'+name],cwd=ROOT,timeout=10).decode().replace('\r\n','\n')
            self.assertEqual(before,(ROOT/name).read_text(encoding='utf-8'))

    def test_exact_guest_oracle(self):
        serial='\n'.join(guest.REQUIRED_MARKERS).replace('REIST_X86_64_C_CALLBACK_OK',guest.MARKER+'\nREIST_X86_64_C_CALLBACK_OK')
        serial=serial.replace('REIST_X86_64_RING3_SHELL_RUN_OK','REIST_X86_64_RING3_SHELL_RUN_OK\nREIST_X86_64_RING3_SHELL_RUN_OK')
        lines=guest.expected_trace(1032);trace='\n'.join(lines)
        guest.validate(serial,trace,1032)
        for i in range(len(lines)):
            for bad in ('\n'.join(lines[:i]+lines[i+1:]),trace+'\n'+lines[i],'\n'.join(reversed(lines))):
                with self.assertRaises(ValueError):guest.validate(serial,bad,1032)
        for before,after in (('result=-1','result=0'),('if=0','if=1'),('stack=1','stack=0'),('count=1650','count=1649'),('lock=1','lock=0'),('bytes=1032','bytes=32')):
            with self.subTest(before=before):
                with self.assertRaises(ValueError):guest.validate(serial,trace.replace(before,after),1032)
        for bad in (serial.replace(guest.MARKER,''),serial+'\n'+guest.MARKER,serial+'\n'+guest.FAILURES[0]):
            with self.assertRaises(ValueError):guest.validate(bad,trace,1032)

    def test_actual_gdb_reader_normalizes_signed_register_views(self):
        debugger=mock.Mock();namespace={'gdb':debugger}
        exec(guest.REGISTER_READER,namespace)
        for value in (-0x7fe5ef90,0xffffffff801a1070):
            debugger.parse_and_eval.return_value=value
            self.assertEqual(namespace['reg']('rdi'),0xffffffff801a1070)
        debugger.parse_and_eval.return_value=-1
        self.assertEqual(namespace['reg']('rax'),0xffffffffffffffff)


if __name__=='__main__':unittest.main()
