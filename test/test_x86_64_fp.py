"""Native instruction witness and ownership wiring for the isolated AMD64 kernel."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs


class FP64Tests(unittest.TestCase):
    def test_host_instructions(self):
        suppress_windows_test_dialogs()
        folder = ROOT/'build/codex-agent/r83b-fp'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(folder/'cache')
        def run(args, timeout=90):
            result = subprocess.run(list(map(str, args)), cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=timeout,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            return result.stdout
        nasm = Path('C:/tools/nasm-3.02/nasm.exe')
        for source, name in (('arch/x86_64/cpu/fp_context.asm', 'fp'),
                             ('test/x86_64_fp_host.asm', 'witness')):
            run([nasm, '-f', 'win64', '-DFP_HOST_TEST=1', source, '-o', folder/(name+'.o')])
        for opt in ('-O0', '-O2'):
            exe = folder/('fp'+opt+'.exe')
            run([find_zig(), 'cc', '-target', 'x86_64-windows-gnu', opt,
                 '-mno-red-zone', '-fno-sanitize=all', '-Wall', '-Wextra', '-Werror',
                 '-Wno-unused-command-line-argument', 'test/x86_64_fp_host.c',
                 folder/'fp.o', folder/'witness.o', '-o', exe])
            self.assertIn('X86_64_FP_HOST_OK', run([exe], 10))

    def test_ownership_edges(self):
        asm = (ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        self.assertIn('TASK_RECORD_SIZE           equ 256', asm)
        self.assertTrue('resb TASK_SLOT_CAPACITY * 512' in asm, 'missing private FP pool')
        for start, end, operation in (
            ('scheduler_syscall_entry64:', 'scheduler_save_syscall_context64:', 'call scheduler_fp_save64'),
            ('x86_64_scheduler_quantum_switch64:', 'x86_64_scheduler_quantum_validate64:', 'call scheduler_fp_save64'),
            ('scheduler_enter_task64:', 'scheduler_syscall_entry64:', 'call scheduler_fp_restore64'),
            ('scheduler_build_task64:', 'scheduler_build_shell_child_stack64:', 'call x86_64_fp_init64'),
            ('scheduler_release_task_frames64:', 'scheduler_verify_final_events64:', 'call x86_64_fp_clear64')):
            self.assertIn(operation, asm[asm.index(start):asm.index(end)])
        make = (ROOT/'Makefile').read_text()
        self.assertIn('arch/x86_64/cpu/fp_context.asm', make)
        self.assertIn('-mno-mmx -mno-sse -mno-sse2', make)
        fp = (ROOT/'arch/x86_64/cpu/fp_context.asm').read_text()
        self.assertIn('fxsave64', fp); self.assertIn('fxrstor64', fp)
        self.assertNotRegex(fp, r'(?m)^\s*xrstor\w*\s')
        fixture = (ROOT/'arch/x86_64/user/fp_probe.inc').read_text()
        # The old timer profile requires a fixed RSP even inside the witness.
        self.assertNotRegex(fixture, r'(?m)^\s*(push\w*|pop\w*|call)\s')
        for name in ('probe.asm', 'child.asm'):
            source = (ROOT/'arch/x86_64/user'/name).read_text()
            self.assertEqual(source.count('    syscall\n'), source.count('    syscall\n    FP_CHECK\n'))
        self.assertIn('call x86_64_fp_reset64',
            (ROOT/'arch/x86_64/proc/user_execution.asm').read_text())


if __name__ == '__main__': unittest.main()
