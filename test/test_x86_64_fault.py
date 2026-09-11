"""Actual native exception classifier and generation-retirement boundaries."""
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
from run_qemu_x86_64_fault import validate_receipts, MARKER, RUN


class FaultTests(unittest.TestCase):
    def test_fault_receipt_oracle_rejects_wrong_path_and_stale_generation(self):
        for phase in range(4):
            rows = ['REIST_X86_64_RING3_SHELL_INFO_OK\n']
            for generation in (41, 42):
                rows += [f'{MARKER} vector=03 generation={generation:02X} '
                         f'parent={(1, 1, 6, 7)[phase]:02X} queued={int(phase == 1):02X} '
                         'rip=0000000000400431\n', RUN + '\n']
            captured = ''.join(rows)
            validate_receipts(captured, 3, phase, 0x400431)
            for bad in (captured.replace('generation=2A', 'generation=29'),
                        captured.replace('vector=03', 'vector=0D'),
                        captured.replace('00400431', '00400430'),
                        captured.replace('parent=01', 'parent=07') if phase < 2
                        else captured.replace('parent=06', 'parent=01') if phase == 2
                        else captured.replace('parent=07', 'parent=01'),
                        captured.replace('queued=00', 'queued=01') if phase != 1
                        else captured.replace('queued=01', 'queued=00'),
                        captured.replace(rows[1], ''), captured + rows[1],
                        rows[0] + rows[2] + rows[1] + rows[3] + rows[4]):
                with self.assertRaises(RuntimeError):
                    validate_receipts(bad, 3, phase, 0x400431)

    def test_host_classifier(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83c-fault'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,timeout=90):
            result=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,
                capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-4000:])
            return result.stdout
        obj=folder/'fault.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64','arch/x86_64/cpu/user_fault.asm','-o',obj])
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                 '-fno-sanitize=all','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument',
                 'test/x86_64_fault_host.c',obj,'-o',exe])
            self.assertIn('X86_64_FAULT_HOST_OK',run([exe],10))

    def test_runtime_retirement_wiring(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        self.assertTrue('scheduler_retire_shell_child_fault64:' in source, 'missing fault retirement')
        body=source.split('scheduler_retire_shell_child_fault64:',1)[1].split('scheduler_consume_child_terminal64:',1)[0]
        for value in ('call x86_64_user_fault_status64', 'call scheduler_reap_terminal64',
                      'call x86_64_elf64_release64', 'scheduler_child_terminal_generation'):
            self.assertIn(value,body)
        self.assertLess(body.index('call scheduler_reap_terminal64'),body.index('call x86_64_elf64_release64'))
        self.assertLess(body.index('call x86_64_elf64_release64'),body.index('scheduler_child_fault_message'))
        self.assertNotIn('X86_64_FAULT_VECTOR',source)
        shell=source.split('x86_64_process_shell64:',1)[1].split('x86_64_process_runqueue_selftest64:',1)[0]
        self.assertIn('call scheduler_enable_user_breakpoint64',shell)
        cleanup=source.split('scheduler_cleanup_common64:',1)[1].split('scheduler_force_cleanup64:',1)[0]
        self.assertIn('call scheduler_disable_user_breakpoint64',cleanup)


if __name__=='__main__': unittest.main()
