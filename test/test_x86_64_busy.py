"""Actual native sampled-budget mechanism and independent busy-guest oracle."""
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


class BusyTests(unittest.TestCase):
    def test_host_budget(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83g-preempt'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name,timeout=90):
            r=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,timeout=timeout,
                capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
            self.assertEqual(r.returncode,0,(r.stdout+r.stderr)[-3000:])
            return r.stdout
        obj=folder/'budget.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',
             'arch/x86_64/proc/cpu_budget.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                 '-fno-sanitize=all','-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','test/x86_64_budget_host.c',obj,
                 '-o',exe],opt+'-build')
            self.assertIn('X86_64_BUDGET_HOST_OK',run([exe],opt+'-run',10))

    def test_busy_receipt_oracle(self):
        from run_qemu_x86_64_busy import validate_receipts
        def receipt(gen):
            return f'REIST_X86_64_CHILD_CPU_REAP_OK generation={gen:02X} ticks=20 parent=07 rip=0000000000400123\nREIST_X86_64_RING3_SHELL_RUN_OK\n'
        good=receipt(41)+receipt(42)
        validate_receipts(good,0x400123,0x400128)
        for bad in (good[:len(good)//2],good+receipt(42),good.replace('ticks=20','ticks=1F'),
                    good.replace('generation=2A','generation=29'),good.replace('parent=07','parent=01'),
                    good.replace('0000000000400123','0000000000500123'),
                    good.replace('REIST_X86_64_RING3_SHELL_RUN_OK\n','',1)):
            with self.assertRaises(RuntimeError):validate_receipts(bad,0x400123,0x400128)
        stack=''.join(f'REIST_X86_64_CHILD_STACK_REAP_OK generation={gen:02X} parent=01 rip=0000000000400123\nREIST_X86_64_RING3_SHELL_RUN_OK\n' for gen in (41,42))
        validate_receipts(stack,0x400123,0x400128,True)
        for bad in (stack.replace('parent=01','parent=07'),stack.replace('generation=2A','generation=29'),
                    stack.replace('0000000000400123','0000000000400124'),stack+good):
            with self.assertRaises(RuntimeError):validate_receipts(bad,0x400123,0x400128,True)

    def test_clock_and_budget_ownership(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        timer=(ROOT/'arch/x86_64/cpu/timer_interrupt.asm').read_text()
        body=timer.split('.shell:',1)[1].split('.shell_invalid:',1)[0]
        self.assertLess(body.index('call x86_64_scheduler_shell_timer_validate64'),body.index('call x86_64_scheduler_deadline_tick64'))
        self.assertLess(body.index('call x86_64_scheduler_deadline_tick64'),body.index('out PIC1_COMMAND, al'))
        self.assertLess(body.index('out PIC1_COMMAND, al'),body.index('jmp x86_64_scheduler_shell_timer_tail64'))
        for forbidden in ('serial_write','physical_frame','fxsave','scheduler_reap'):
            self.assertNotIn(forbidden,body)
        tail=source.split('x86_64_scheduler_shell_timer_tail64:',1)[1].split('scheduler_save_syscall_context64:',1)[0]
        self.assertIn('call scheduler_context_apply64',tail)
        self.assertIn('call scheduler_budget_apply64',tail)
        self.assertIn('scheduler_retire_shell_context64',tail)
        route=source.split('scheduler_retire_shell_context64:',1)[1].split('scheduler_retire_shell_owner64:',1)[0]
        self.assertIn('jne scheduler_retire_shell_child_fault64.classified',route)
        complete=source.split('scheduler_shell_deadline_complete64:',1)[1].split('x86_64_scheduler_shell_timer_validate64:',1)[0]
        self.assertNotIn('cancel',complete)
        self.assertNotIn('mov dword [rel scheduler_last_tick], 0',source)


if __name__=='__main__': unittest.main()
