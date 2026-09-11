"""Execute production native IPC admission assembly, not a source-only model."""
from pathlib import Path
import os
import subprocess
import sys
import unittest
import uuid
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_user_program import find_zig
from measure_cpp_baseline import suppress_windows_test_dialogs
from run_qemu_x86_64_ipc_handoff import validate_trace


class HandoffTests(unittest.TestCase):
    def test_trace_oracle_rejects_missing_or_wrong_interleaving(self):
        for case in range(4):
            status = 77 if case == 0 else 90 + case
            serial = ''.join(f'CHILD_EXIT_REAP_OK status={status:08X} generation={g:02X} '
                'parent=01 queued=00 rip=0000000000400100\nREIST_X86_64_RING3_SHELL_RUN_OK\n'
                for g in (41,42))
            rows = [(52,3,40)]*2 if case == 0 else [(52,1,40)]*2 if case == 3 else \
                [(53,0 if case == 1 else 4,g) for g in (41,42)]
            if case:
                rows += [(op,bits,40) for op,bits in ((53,0),(53,1),(50,1),(51,0))]*2
            trace = ''.join(f'IPC_PLAN op={op} bits={bits} generation={g}\n' for op,bits,g in rows)
            validate_trace(serial,trace,case)
            for bad_serial,bad_trace in (
                (serial,trace.replace('IPC_PLAN','omitted',1)),
                (serial,trace.replace('bits=','wrong=',1)),
                (serial.replace('generation=2A','generation=29'),trace),
                (serial.replace('queued=00','queued=01'),trace),
                (serial.replace('rip=0000000000400100','rip=0000000000000000'),trace),
                (serial+serial,trace), (serial,trace*300)):
                with self.assertRaises(RuntimeError):
                    validate_trace(bad_serial,bad_trace,case)

    def test_actual_admission_and_queue_plan(self):
        suppress_windows_test_dialogs()
        folder = ROOT / 'build/codex-agent/r83j1-ipc' / ('host-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env = os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR'] = str(ROOT / 'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR'] = str(folder / 'cache')
        def run(command, timeout=90):
            result = subprocess.run(list(map(str, command)), cwd=ROOT, env=env,
                capture_output=True, text=True, timeout=timeout,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-4000:])
            return result.stdout
        obj = folder / 'ipc.o'
        run(['C:/tools/nasm-3.02/nasm.exe', '-f', 'win64',
             'arch/x86_64/proc/ipc_admission.asm', '-o', obj])
        for opt in ('-O0', '-O2'):
            exe = folder / (opt + '.exe')
            run([find_zig(), 'cc', '-target', 'x86_64-windows-gnu', opt,
                 '-mno-red-zone', '-fno-sanitize=all', '-Wall', '-Wextra', '-Werror',
                 '-Wno-unused-command-line-argument',
                 'test/x86_64_ipc_handoff_host.c', obj, '-o', exe])
            self.assertIn('X86_64_IPC_HANDOFF_HOST_OK', run([exe], 10))


if __name__ == '__main__':
    unittest.main()
