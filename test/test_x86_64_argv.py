"""Actual bounded native initial-stack construction and guest argument proof."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class ArgvTests(unittest.TestCase):
    def test_fixture_modes_are_exclusive_before_build(self):
        result = subprocess.run(
            ['powershell', '-NoProfile', '-File',
             str(ROOT/'scripts/build-x86_64-bootstrap.ps1'),
             '-IpcCase', '1', '-ArgvCase', '1'],
            cwd=ROOT, timeout=10, capture_output=True, text=True,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('IpcCase is exclusive', result.stderr)

    def test_fixture_oracle(self):
        import struct
        from run_qemu_x86_64_argv import SIZES,validate_exit_code
        for case,size in SIZES.items():
            code=b'\x48\x81\xfc'+struct.pack('<I',0x409000-size)+b'\x90'*9
            code+=b'\xbf'+struct.pack('<I',90+case)+bytes.fromhex('b8090000000f050f0b')
            symbols=dict(child_argv_probe=0,child_argv_exit_instruction=26,child_argv_exit_return=28,child_argv_fail=28)
            self.assertEqual(validate_exit_code(code,symbols,case),28)
            for index in list(range(7))+list(range(16,30)):
                bad=bytearray(code);bad[index]^=1
                with self.assertRaises(RuntimeError):validate_exit_code(bad,symbols,case)

    def test_validation_before_allocation_and_real_copy(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        begin=source.index('scheduler_handle_shell_spawnv64:')
        validation=source.index('call scheduler_shell_startup_apply64',begin)
        allocation=source.index('call x86_64_elf64_load64',validation)
        self.assertLess(validation,allocation)
        builder=source.split('scheduler_build_shell_child_stack64:',1)[1].split('scheduler_verify_isolation64:',1)[0]
        self.assertIn('call scheduler_shell_startup_apply64',builder)
        self.assertIn('mov [r12 + TASK_RSP], rax',builder)
        self.assertNotIn('scheduler_validate_shell_token64:',source)

    def test_host_startup_stack(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83j-argv'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name,timeout=90):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:]);return r.stdout
        obj=folder/'startup.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/proc/startup_stack.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone','-fno-sanitize=all',
                '-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                'test/x86_64_argv_host.c',obj,'-o',exe],opt+'-build')
            self.assertIn('X86_64_ARGV_HOST_OK',run([exe],opt+'-run',10))


if __name__=='__main__':unittest.main()
