"""Real compiled AMD64 register witness and freestanding LP64 boundary."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class SDK64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        suppress_windows_test_dialogs()
        cls.folder=ROOT/'build/codex-agent/r83a-sdk'/('host-'+uuid.uuid4().hex)
        cls.folder.mkdir(parents=True)
        cls.zig=find_zig();cls.env=os.environ.copy()
        cls.env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        cls.env['ZIG_LOCAL_CACHE_DIR']=str(cls.folder/'cache')

    def run_command(self,args,success=True,timeout=90):
        result=subprocess.run(list(map(str,args)),capture_output=True,text=True,env=self.env,
            timeout=timeout,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),cwd=ROOT)
        if success:self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        else:self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
        return result

    def test_native_register_witness_c_cpp_o0_o2(self):
        for lang,standard in (('c','c11'),('c++','c++20')):
            for opt in ('-O0','-O2'):
                with self.subTest(lang=lang,opt=opt):
                    exe=self.folder/(lang.replace('+','p')+opt+'.exe')
                    self.run_command([self.zig,'c++' if lang=='c++' else 'cc','-target','x86_64-windows-gnu','-x',lang,
                        '-std='+standard,opt,'-mno-red-zone','-fno-sanitize=all','-Wall','-Wextra','-Werror',
                        # Zig0.16 injects an unused rtlib driver option at O0;
                        # retain errors for actual source diagnostics.
                        '-Wno-unused-command-line-argument',
                        '-Iuserspace/sdk/include',ROOT/'test/x86_64_sdk_host.c','-o',exe])
                    self.assertIn('X86_64_SDK_HOST_OK',self.run_command([exe],timeout=10).stdout)

    def test_freestanding_lp64_and_wrong_architecture(self):
        source=self.folder/'lp64.c'
        source.write_text('#include <reist/x86_64/syscall.h>\n'
            '_Static_assert(sizeof(void*)==8 && sizeof(long)==8 && sizeof(uintptr_t)==8,"LP64");\n'
            '_Static_assert(REIST_X64_SYS_EXIT==9 && REIST_X64_SYS_IPC_RELEASE==58 && REIST_X64_SYS_TERMINAL_WRITE_COLOR==131,"numbers");\n'
            'int64_t probe(uintptr_t p){return reist_x64_syscall3(REIST_X64_SYS_WRITE,1,p,64);}\n')
        obj=self.folder/'lp64.o'
        base=[self.zig,'cc','-std=c11','-ffreestanding','-nostdlib','-mno-red-zone',
              '-fno-stack-protector','-O2','-Iuserspace/sdk/include','-c',source,'-o',obj]
        self.run_command(base+['-target','x86_64-freestanding-none'])
        data=obj.read_bytes();self.assertEqual(data[:5],b'\x7fELF\x02')
        self.assertEqual(int.from_bytes(data[18:20],'little'),62)
        self.assertIn(b'\x0f\x05',data) # Actual SYSCALL, not the host witness.
        result=self.run_command(base+['-target','x86-freestanding-none'],False)
        self.assertIn('native 64-bit pointers',result.stderr)

    def test_single_number_source_and_production_consumer(self):
        header=(ROOT/'userspace/sdk/include/reist/x86_64/syscall.h').read_text()
        shell=(ROOT/'arch/x86_64/user/shell.c').read_text()
        make=(ROOT/'Makefile').read_text()
        self.assertIn('REIST_SYSCALL_LIST(',header)
        self.assertIn('#include <reist/x86_64/syscall.h>',shell)
        self.assertNotIn('#define REIST_SYS_',shell)
        self.assertNotIn('"syscall"',shell)
        self.assertIn('reist_x64_syscall3(',shell)
        self.assertNotIn('REIST_X64_TEST_TRAP',make)
        self.assertNotIn('REIST_X64_TEST_TRAP',shell)
        build=(ROOT/'scripts/build-x86_64-bootstrap.ps1').read_text()
        for cache in ('ZIG_GLOBAL_CACHE_DIR','ZIG_LOCAL_CACHE_DIR'):
            self.assertIn('$env:'+cache+' = Join-Path',build)
            self.assertIn('$env:'+cache+' = $savedZig',build)
        self.assertIn('$outputRoot.StartsWith($buildRoot',build)
        self.assertEqual((ROOT/'include/reist/abi/syscall.h').read_bytes(),
                         (ROOT/'userspace/sdk/include/reist/abi/syscall.h').read_bytes())


if __name__=='__main__':unittest.main()
