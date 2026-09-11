"""Actual native terminal-reason/status mechanism and independent guest oracle."""
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


class ExitTests(unittest.TestCase):
    def test_exit_oracles(self):
        from run_qemu_x86_64_exit import STATUSES,RUN,fixture_bytes,validate_instructions,validate_receipts
        symbols=dict(child_exit_probe=0,child_exit_instruction=75,child_exit_return=77,child_exit_fail=77)
        for status in STATUSES:
            code=fixture_bytes(status)
            self.assertEqual(validate_instructions(code,symbols,status),77)
            for i in range(len(code)):
                changed=bytearray(code);changed[i]^=1
                with self.assertRaises(RuntimeError):validate_instructions(changed,symbols,status)
            for phase in range(4):
                text=''.join(f'REIST_X86_64_CHILD_EXIT_REAP_OK status={status:08X} generation={gen:02X} '
                    f'parent={(1,1,6,7)[phase]:02X} queued={int(phase==1):02X} rip=0000000000401234\n{RUN}\n' for gen in (41,42))
                validate_receipts(text,status,phase,0x401234)
                for bad in (text.replace('generation=2A','generation=29'),text+text,
                    text.replace('0000000000401234','0000000000401235'),text.replace(RUN,'',1),
                    text.replace('_EXIT_REAP_OK','_CPU_REAP_OK'),text.replace('parent=0','parent=F'),
                    text.replace(f'status={status:08X}',f'status={status^1:08X}')):
                    with self.assertRaises(RuntimeError):validate_receipts(bad,status,phase,0x401234)

    def test_shared_control_ownership(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        body=source.split('scheduler_handle_shell_yield64:',1)[1].split('scheduler_handle_shell_getpid64:',1)[0]
        self.assertNotIn('scheduler_shell_ipc_',body)
        self.assertNotIn('syscall_rdi',body)
        self.assertNotIn('budget',body.lower())
        child=source.split('scheduler_handle_shell_child_exit64:',1)[1].split('scheduler_shell_child_denied_resume64:',1)[0]
        self.assertIn('call reist_x64_terminal_status',child)
        self.assertIn('scheduler_retire_shell_child_fault64.normal_exit',child)
        self.assertNotIn('DYNAMIC_CHILD_EXIT_STATUS',child)
        self.assertIn('mov qword [rel scheduler_child_terminal_reason], 0',source)
        self.assertIn('cmp qword [rel scheduler_child_terminal_reason], 0',source)

    def test_host_terminal_status(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83i-control'/('host-'+uuid.uuid4().hex)
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
        obj=folder/'terminal.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',
             'arch/x86_64/proc/terminal_status.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                 '-fno-sanitize=all','-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','test/x86_64_exit_host.c',obj,
                 '-o',exe],opt+'-build')
            self.assertIn('X86_64_EXIT_STATUS_HOST_OK',run([exe],opt+'-run',10))


if __name__=='__main__': unittest.main()
