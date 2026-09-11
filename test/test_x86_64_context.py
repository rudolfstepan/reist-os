"""Actual assembly context transport; host nonmutation plus real guest wiring."""
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


class ContextTests(unittest.TestCase):
    def test_host_context(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83f-context'/('host-'+uuid.uuid4().hex)
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
        obj=folder/'context.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',
             'arch/x86_64/proc/context_core.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                 '-fno-sanitize=all','-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','test/x86_64_context_host.c',obj,
                 '-o',exe],opt+'-build')
            self.assertIn('X86_64_CONTEXT_HOST_OK',run([exe],opt+'-run',10))

    def test_context_consumers_and_live_stack_witness(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        for start,end in (
            ('scheduler_save_syscall_context64:','scheduler_validate_shell_syscall_profile64:'),
            ('x86_64_scheduler_quantum_switch64:','x86_64_scheduler_quantum_validate64:')):
            section=source.split(start,1)[1].split(end,1)[0]
            self.assertIn('call scheduler_context_apply64',section)
        core=(ROOT/'arch/x86_64/proc/context_core.asm').read_text()
        for forbidden in ('SCHEDULER_MODE','TASK_SHELL','physical_frame','section .bss'):
            self.assertNotIn(forbidden,core)
        fixture=(ROOT/'arch/x86_64/user/probe.asm').read_text()
        for label in ('quantum_task_a:','quantum_task_b:'):
            section=fixture.split(label,1)[1].split('\n\n',1)[0]
            self.assertIn('sub rsp, 64',section)
        self.assertIn('cmp qword [rsp], r14',fixture)
        self.assertIn('cmp qword [rsp + 56], r13',fixture)


if __name__=='__main__': unittest.main()
