"""Actual native task-identity mechanism, with identical host/guest assembly."""
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


class IdentityTests(unittest.TestCase):
    def test_native_lifecycle_is_not_a_parallel_state_table(self):
        source=(ROOT/'arch/x86_64/proc/cooperative_scheduler.asm').read_text()
        core=(ROOT/'arch/x86_64/proc/identity_core.asm').read_text()
        build=source.split('scheduler_build_task64:',1)[1].split('scheduler_build_shell_child_stack64:',1)[0]
        self.assertLess(build.index('call scheduler_identity_apply64'),build.index('call physical_frame_alloc64'))
        rollback=build.split('.fail:',1)[1]
        self.assertLess(rollback.index('call scheduler_release_task_frames64'),rollback.index('call scheduler_identity_apply64'))
        reap=source.split('scheduler_reap_terminal64:',1)[1].split('scheduler_release_task_frames64:',1)[0]
        self.assertLess(reap.index('call scheduler_clear_shell_syscall_profile64'),reap.index('call scheduler_release_task_frames64'))
        self.assertLess(reap.index('call scheduler_release_task_frames64'),reap.index('call scheduler_identity_apply64'))
        self.assertIn('cmp qword [r8 + TASK_STATE], TASK_RESERVED',source)
        self.assertIn('cmp dword [rel scheduler_identity_pool + 20], TASK_SHELL_CHILD_GEN2',source)
        for forbidden in ('SCHEDULER_MODE','TASK_SHELL','syscall','physical_frame','section .bss'):
            self.assertNotIn(forbidden,core)

    def test_native_identity_lifecycle(self):
        suppress_windows_test_dialogs()
        folder=ROOT/'build/codex-agent/r83e-identity'/('host-'+uuid.uuid4().hex)
        folder.mkdir(parents=True)
        env=os.environ.copy()
        env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'build/zig-global-cache')
        env['ZIG_LOCAL_CACHE_DIR']=str(folder/'cache')
        def run(args,name,timeout=90):
            result=subprocess.run(list(map(str,args)),cwd=ROOT,env=env,
                timeout=timeout,capture_output=True,text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (folder/(name+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
            self.assertEqual(result.returncode,0,(result.stdout+result.stderr)[-3000:])
            return result.stdout
        obj=folder/'identity.o'
        run(['C:/tools/nasm-3.02/nasm.exe','-f','win64',
             'arch/x86_64/proc/identity_core.asm','-o',obj],'assemble')
        for opt in ('-O0','-O2'):
            exe=folder/(opt+'.exe')
            run([find_zig(),'cc','-target','x86_64-windows-gnu',opt,'-mno-red-zone',
                 '-fno-sanitize=all','-Wall','-Wextra','-Werror',
                 '-Wno-unused-command-line-argument','test/x86_64_identity_host.c',obj,
                 '-o',exe],opt+'-build')
            self.assertIn('X86_64_IDENTITY_HOST_OK',run([exe],opt+'-run',10))


if __name__=='__main__': unittest.main()
